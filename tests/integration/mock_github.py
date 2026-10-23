"""A GitHub REST subset backed by a real, synthetic Git repository.

Test infrastructure only. Records request metadata, never bearer tokens or CSV bodies.
"""

import hashlib
import hmac
import json
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path("/fixture")
AUDIT_LOCK = threading.Lock()
TOKEN = "synthetic-github-token"
PREFIX = "/repos/synthetic/health"


def git(*args):
    return subprocess.check_output(["git", "-c", "safe.directory=/fixture/repo",
                                    "-C", "/fixture/repo", *args], stderr=subprocess.DEVNULL)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_GET(self):
        url = urlsplit(self.path)
        path = unquote(url.path)
        query = parse_qs(url.query)
        authorized = hmac.compare_digest(self.headers.get("Authorization", ""), f"Bearer {TOKEN}")
        status, payload, raw = 404, {"message": "Not Found"}, False
        if path == "/health":
            status, payload = 200, {"ready": True}
        elif not authorized:
            status, payload = 401, {"message": "Bad credentials"}
        elif (ROOT / "fail-once").exists():
            (ROOT / "fail-once").unlink()
            status, payload = 503, {"message": "Synthetic temporary outage"}
        elif path == PREFIX:
            status, payload = 200, {"id": 12345, "full_name": "synthetic/health", "default_branch": "main"}
        elif path == PREFIX + "/commits/main":
            status, payload = 200, {"sha": git("rev-parse", "refs/heads/main").decode().strip()}
        elif path.startswith(PREFIX + "/contents/"):
            ref = query.get("ref", [""])[0]
            content_path = path.removeprefix(PREFIX + "/contents/")
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                status, payload = 400, {"message": "Tests require an immutable commit ref"}
            elif content_path == "workouts":
                entries = []
                for line in git("ls-tree", "-r", ref, "--", "workouts").decode().splitlines():
                    metadata, filename = line.split("\t")
                    _, kind, sha = metadata.split()
                    entries.append({"path": filename, "type": "file" if kind == "blob" else kind,
                                    "sha": sha, "name": filename.rsplit("/", 1)[-1]})
                status, payload = 200, entries
            elif re.fullmatch(r"workouts/\d{4}\.csv", content_path):
                if self.headers.get("Accept") != "application/vnd.github.raw+json":
                    status, payload = 406, {"message": "Raw media type required"}
                else:
                    try:
                        payload = git("show", f"{ref}:{content_path}")
                        status, raw = 200, True
                    except subprocess.CalledProcessError:
                        pass
        record = {"path": path, "query": query, "status": status, "authorized": authorized,
                  "raw": raw, "sha256": hashlib.sha256(payload).hexdigest() if raw else None}
        with AUDIT_LOCK:
            with (ROOT / "requests.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
        body = payload if raw else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/csv" if raw else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
