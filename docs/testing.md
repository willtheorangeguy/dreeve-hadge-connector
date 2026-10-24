# Testing

The unit suite checks parsing, encoding, synchronization, HTTP behavior, CLI behavior, and release tooling. A separate Docker acceptance harness verifies actual imports through Dreeve's web app and daemon. All fixtures are synthetic.

## Unit suite

Install development dependencies as described in [Development](./development.md), then run:

```sh
uv run --no-project python -m pytest -q
uv run --no-project ruff check .
```

| File | Coverage |
| --- | --- |
| `tests/test_workout_fit.py` | CSV validation, offsets/DST, missing metrics, Unicode, sport mapping, independent FIT decoding |
| `tests/test_sync.py` | Read-only preview, backfill, rollover, deduplication, changed/deleted source, rejection retries, process lock, crash/permission recovery |
| `tests/test_github_config_cli.py` | Commit snapshots, raw reads, sanitized errors, retries/rate limits, configuration, token precedence/rotation, CLI progress |
| `tests/test_release.py` | Release metadata validation and versioned setup assets |
| `tests/test_integration_harness.py` | Harness subprocess output/diagnostics behavior |

Run a focused suite while working on a boundary:

```sh
uv run --no-project python -m pytest tests/test_sync.py -q
uv run --no-project python -m pytest tests/test_workout_fit.py -q
```

The normal pytest run does not start the Docker acceptance stack. Production `run_sync` is exercised with fake GitHub snapshots in unit tests; the acceptance harness uses the packaged HTTP client instead.

## Full Docker acceptance test

You need Git, Docker Compose v2, and the development dependencies. From the project root:

```sh
docker pull ghcr.io/dreeveapp/dreeve:v5.6.2
uv run --no-project python -m tests.integration.run
```

The harness starts a uniquely named Compose project with four services:

- A bearer-authenticated mock GitHub HTTP service backed by a real temporary Git repository and real commit/blob SHAs.
- The built connector image running production `watch` code.
- Dreeve v5.6.2's real web application with migrations and storage.
- Dreeve's daemon sharing the app database, storage, and watch directory.

Initial and incremental imports wait for the daemon's actual five-minute schedule. Expect 6–11 minutes plus initial downloads/builds. Each scheduled import has a six-minute deadline. Only the final duplicate-replay import is triggered explicitly.

## Acceptance scenarios

1. Verify login behavior, rejection of an unauthenticated API request, and an authenticated empty activities response.
2. Recover from HTTP 503 and import four historical workouts through the daemon.
3. Check names, sports, times, metrics, provenance, and absence of sensor samples in imported activities.
4. Restart with persistent state, test HTTP 401, rotate the token file, and verify no redelivery or unnecessary CSV downloads.
5. Commit new history with a changed UUID, new workouts/yearly CSV, and malformed row; import only new UUIDs while reporting edits/rejection.
6. Replay six valid workouts with fresh state, trigger the final import, and verify six skipped duplicates with six activities retained.

The test inspects authenticated HTTP responses and Dreeve's SQLite/import records. Mock request audits establish bearer authentication, raw response negotiation, immutable refs, and actual HTTP retries. There are no private health credentials or production data.

## Isolation and evidence

The acceptance stack uses an internal network with no published ports. An HTTP probe inside that network exercises Dreeve. Logs, request audits, API results, database snapshots, and a result summary are saved under ignored `integration-artifacts/` before the test containers and volumes are removed.

CI uploads this directory as `full-workflow-evidence`, including on failures. The existing [harness README](https://github.com/willtheorangeguy/dreeve-hadge-connector/blob/HEAD/tests/integration/README.md) contains its detailed contract. The only connector test seam is `GITHUB_API_URL=http://github:8000`; production retains GitHub's HTTPS endpoint.
