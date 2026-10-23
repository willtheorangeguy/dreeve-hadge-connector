"""Exercise GitHub HTTP -> packaged watcher -> watch folder -> Dreeve daemon -> web API."""

import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

TOKEN = "synthetic-github-token"
HARNESS = Path(__file__).resolve().parent
HEADERS = ["UUID", "Start Date", "End Date", "Type", "Name", "Duration", "Distance",
           "Elevation Ascended", "Flights Climbed", "Swim Strokes", "Total Energy"]
DEFINITIONS = [(37, "Hadge Run", "Run"), (13, "Hadge Ride", "Ride"),
               (50, "Hadge Strength", "WeightTraining"), (99999, "Hadge Unknown", "Workout"),
               (52, "Hadge New Walk", "Walk"), (37, "Hadge New Year Run", "Run")]


def command(*args, env=None, cwd=None, check=True, include_stderr=False):
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=300, env=env, cwd=cwd)
    if check and result.returncode:
        raise RuntimeError(f"Command failed: {args}\n{result.stdout}\n{result.stderr}")
    return result.stdout + (result.stderr if include_stderr or not check else "")


def row(index):
    kind, name, _ = DEFINITIONS[index]
    start = datetime(2026, 10, 23, 18, tzinfo=UTC) + timedelta(days=index)
    if index == 5:
        start = datetime(2027, 1, 1, 18, tzinfo=UTC)
    return dict(zip(HEADERS, [f"12345678-1234-4234-8234-{index + 1:012d}", start.isoformat(),
                             (start + timedelta(minutes=30)).isoformat(), str(kind), name,
                             "1700.500", "5000.25", "40", "2", "0", "300.25"], strict=True))


def write_csv(path, rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, HEADERS)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(output.getvalue(), encoding="utf-8", newline="")


def commit(repo, message):
    command("git", "-C", str(repo), "add", "workouts")
    command("git", "-C", str(repo), "-c", "user.name=Hadge Integration",
            "-c", "user.email=synthetic@example.invalid", "commit", "-m", message)
    return command("git", "-C", str(repo), "rev-parse", "HEAD").strip()


def wait_for(description, predicate, timeout=360):
    print(f"Waiting: {description}", flush=True)
    deadline = time.monotonic() + timeout
    last_heartbeat = time.monotonic()
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            print(f"PASS: {description}", flush=True)
            return result
        if time.monotonic() - last_heartbeat >= 30:
            print(f"Still waiting: {description}", flush=True)
            last_heartbeat = time.monotonic()
        time.sleep(2)
    raise AssertionError(f"Timed out after {timeout}s: {description}")


def main():
    project = "hadge-e2e-" + uuid4().hex[:12]
    report = HARNESS.parents[1] / "integration-artifacts" / project
    report.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix="hadge-e2e-") as temporary:
        root = Path(temporary)
        repo = root / "repo"
        (repo / "workouts").mkdir(parents=True)
        (root / "watch").mkdir()
        (root / "connector-token").write_text(TOKEN)
        (root / "fail-once").touch()
        command("git", "init", "-b", "main", str(repo))
        write_csv(repo / "workouts/2026.csv", [row(i) for i in range(4)])
        first_commit = commit(repo, "Hadge historical export")
        env = os.environ | {"HADGE_FIXTURE_DIR": str(root)}

        def compose(*args, check=True, include_stderr=False):
            return command("docker", "compose", "-f", str(HARNESS / "compose.yaml"),
                           "-p", project, *args, env=env, check=check, include_stderr=include_stderr)

        def audit():
            path = root / "requests.jsonl"
            if not path.exists():
                return []
            return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

        def logs(service, check=True):
            return compose("logs", "--no-color", service, check=check)

        def database():
            return json.loads(compose("exec", "-T", "app", "php", "/harness/read_database.php"))

        def http(path, authenticated=False):
            args = ["exec", "-T", "github", "python", "/harness/probe_http.py", path]
            if authenticated:
                args.append("--authenticated")
            return json.loads(compose(*args))

        def activities():
            response = http("/api/v1/activities", authenticated=True)
            assert response["status"] == 200, response
            return json.loads(response["body"])

        try:
            print("Building the four-service integration stack", flush=True)
            compose("build")
            compose("up", "-d", "--wait", "--wait-timeout", "180", "github", "app", "daemon")
            response = http("/admin/login")
            assert response["status"] == 200, response
            assert http("/api/v1/activities")["status"] == 401
            assert activities()["pagination"]["total"] == 0
            print("PASS: real Dreeve web app serves login and authenticated activities API", flush=True)
            compose("up", "-d", "--wait", "--wait-timeout", "60", "connector")
            wait_for("connector retries the synthetic GitHub 503 and delivers four FIT files",
                     lambda: "delivered=4" in logs("connector"), timeout=90)
            wait_for("Dreeve daemon automatically imports the initial four workouts",
                     lambda: activities()["pagination"]["total"] == 4)
            initial = database()
            initial_api = activities()
            assert {a["name"] for a in initial_api["activities"]} == {d[1] for d in DEFINITIONS[:4]}
            assert all(a["distanceInMeter"] == 5000 for a in initial_api["activities"])
            (report / "first-api.json").write_text(json.dumps(initial_api, indent=2), encoding="utf-8")
            (report / "first-import.json").write_text(json.dumps(initial, indent=2), encoding="utf-8")
            assert [entry["status"] for entry in initial["imports"]].count("success") == 4, initial
            for activity, (_, label, sport) in zip(initial["activities"], DEFINITIONS[:4], strict=True):
                assert activity["name"] == label, activity
                assert activity["sportType"] == sport, activity
                assert activity["distance"] == 5000, activity
                assert activity["elapsedTimeInSeconds"] == 1800, activity
                assert activity["movingTimeInSeconds"] == 1701, activity
                assert activity["calories"] == 300 and activity["elevation"] == 40, activity
                assert activity["averageHeartRate"] is None and activity["polyline"] is None, activity
                assert "Apple Health via Hadge" in activity["description"], activity
            assert not list((root / "watch").glob("*.fit")), "Dreeve must consume the delivered files"

            # Reboot the packaged watcher against an unchanged repo, with temporarily bad credentials.
            compose("stop", "connector")
            boundary = len(audit())
            (root / "connector-token").write_text("synthetic-wrong-token")
            compose("start", "connector")
            wait_for("GitHub rejects the incorrect token over HTTP",
                     lambda: any(r["status"] == 401 for r in audit()[boundary:]), timeout=60)
            (root / "connector-token").write_text(TOKEN)
            wait_for("watcher rereads the rotated token and reuses persisted delivery state",
                     lambda: any(r["authorized"] and r["path"].endswith("/contents/workouts")
                                 for r in audit()[boundary:]), timeout=60)
            assert not any(r["raw"] for r in audit()[boundary:]), "Unchanged CSV must stay cached"
            assert len(database()["activities"]) == 4

            # A new Hadge sync changes the yearly CSV, adds a new year, and contains one rejected row.
            write_csv(repo / "workouts/2026.csv", [row(0) | {"Distance": "9999"},
                      *[row(i) for i in range(1, 5)], row(4) | {"UUID": "invalid-uuid"}])
            write_csv(repo / "workouts/2027.csv", [row(5)])
            second_commit = commit(repo, "Hadge incremental export and year rollover")
            wait_for("HTTP polling discovers the new commit and delivers two new workouts",
                     lambda: "delivered=2" in logs("connector"), timeout=75)
            connector_log = logs("connector")
            assert "manual review required" in connector_log and "invalid workout UUID" in connector_log
            wait_for("Dreeve daemon automatically imports both incremental workouts",
                     lambda: activities()["pagination"]["total"] == 6)
            incremental = database()
            assert len(incremental["imports"]) == 6, incremental
            assert all(entry["status"] == "success" for entry in incremental["imports"]), incremental
            assert incremental["activities"][0]["distance"] == 5000, "Source edit must not replace data"
            assert {a["name"] for a in incremental["activities"]} == {item[1] for item in DEFINITIONS}
            (report / "incremental-import.json").write_text(
                json.dumps(incremental, indent=2), encoding="utf-8")

            # Remove the malformed row for a successful fresh-state replay of the same six UUIDs.
            write_csv(repo / "workouts/2026.csv", [row(i) for i in range(5)])
            commit(repo, "Correct rejected row before replay")
            compose("stop", "connector")
            replay_log = compose("run", "--rm", "-T", "-e", "STATE_DIR=/tmp/replay-state",
                                 "-e", "GITHUB_TOKEN_FILE=", "-e", f"GITHUB_TOKEN={TOKEN}",
                                 "connector", "sync", include_stderr=True)
            (report / "replay-delivery.log").write_text(replay_log, encoding="utf-8")
            assert "delivered=6" in replay_log
            compose("exec", "-T", "app", "bin/console", "app:import:files")
            wait_for("Dreeve skips all six redelivered workouts",
                     lambda: sum(r["status"] == "skipped" for r in database()["imports"]) == 6,
                     timeout=90)
            replay = database()
            assert len(replay["activities"]) == 6, replay
            assert [entry["status"] for entry in replay["imports"]].count("skipped") == 6, replay
            (report / "replay-import.json").write_text(json.dumps(replay, indent=2), encoding="utf-8")
            (report / "activities-api.json").write_text(json.dumps(activities(), indent=2), encoding="utf-8")
            raw_requests = [r for r in audit() if r["raw"]]
            assert raw_requests and all(r["authorized"] for r in raw_requests)
            assert {first_commit, second_commit}.issubset({r["query"]["ref"][0] for r in raw_requests})
            assert any(r["status"] == 503 for r in audit()), "Network retry was not exercised"
            assert "Cron configured" in logs("daemon") and "Imported 4" in logs("daemon")
            (report / "summary.json").write_text(json.dumps({
                "initial_activities": 4, "incremental_activities": 6, "replayed_duplicates_skipped": 6,
                "commits": [first_commit, second_commit], "automatic_imports": True,
                "web_api_verified": True, "token_rotation_verified": True,
                "restart_cache_verified": True, "http_retry_verified": True,
                "environment_token_verified": True,
            }, indent=2), encoding="utf-8")
            print("PASS: full HTTP workflow, automatic imports, recovery, and duplicate replay", flush=True)
        finally:
            # Keep diagnostics even on failed assertions, before removing only this test's resources.
            try:
                for service in ("app", "daemon", "connector", "github"):
                    (report / f"{service}.log").write_text(logs(service, check=False), encoding="utf-8")
                if (root / "requests.jsonl").exists():
                    (report / "github-requests.jsonl").write_bytes((root / "requests.jsonl").read_bytes())
                (report / "compose-status.json").write_text(
                    compose("ps", "-a", "--format", "json", check=False), encoding="utf-8")
            finally:
                compose("down", "--volumes", "--remove-orphans", check=False)
    print(f"Evidence: {report}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise
