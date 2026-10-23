# Full workflow acceptance test

From the project root, with Git, Docker Compose v2, and development dependencies installed:

```sh
docker pull ghcr.io/dreeveapp/dreeve:v5.6.2
python -m tests.integration.run
```

This starts four services in a uniquely named Compose project:

- A mock GitHub REST service backed by a **real temporary Git repository**, with
  Hadge's `workouts/YYYY.csv` layout and real commit/blob SHAs. It requires a
  synthetic bearer token and serves repository metadata, branch resolution,
  directory listings, and raw CSV downloads pinned to immutable commits.
- The **built connector image**, running its production `watch` command, HTTP
  client, parser, FIT writer, SQLite state, and process locking.
- Dreeve **v5.6.2's web application**, using the release image and normal entrypoint,
  database migration, named storage volumes, and HTTP server.
- Dreeve's **real daemon**, sharing the app's database, file storage, and watch folder.

Initial and incremental imports wait for the daemon's actual five-minute schedule.
No call to `run_sync`, fake in-process GitHub client, source monkeypatch, synthetic
clock, or direct invocation of the initial/incremental Dreeve import is used.
The whole test normally takes **6–11 minutes**, plus the first image build/download.
Readiness uses health checks; each scheduled import has a six-minute deadline.

The test verifies:

1. Dreeve serves its login page, rejects an unauthenticated API request, and serves
   the authenticated activities API with an initially empty database.
2. The connector recovers from an HTTP 503 and automatically delivers four historical
   workouts; the daemon imports them and they appear through the web API.
3. Names, sport mappings, elapsed/timer times, distance, calories, ascent, missing
   sensor data, and provenance match the synthetic source. Dreeve consumes the FIT files.
4. Restarting the connector preserves state. An invalid token gets HTTP 401; replacing
   the token file recovers on the next cycle without CSV downloads or redelivery.
5. A second Git commit changes an existing workout, adds another workout, creates
   a new yearly CSV, and includes a malformed row. The watcher reports the edit and
   rejection, delivers only the two new UUIDs, and the daemon imports them automatically.
6. A fresh-state invocation of the packaged `sync` command redelivers the six valid
   workouts. An **explicit import command for this final replay only** verifies Dreeve
   records six skipped duplicates and keeps six activities.

Assertions inspect both the public HTTP API and the real Dreeve SQLite/import log.
The mock's request audit proves authentication, raw media negotiation, immutable
commit refs, and actual HTTP retries. There are no real GitHub credentials or health data.

The stack uses an internal network with no published ports. An HTTP probe inside
that network checks the real Dreeve web server. No production containers or volumes are accessed. Logs, request
audits, API responses, database snapshots, and a result summary are saved under
the ignored `integration-artifacts/` directory before the test stack and volumes
are removed. GitHub Actions runs this test and uploads those diagnostics even on failure.

`GITHUB_API_URL=http://github:8000` is the only connector test seam; the default
remains GitHub's HTTPS API. The mock service is test infrastructure, not a general
GitHub emulator: it intentionally implements only the endpoints this connector uses.
