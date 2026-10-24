# Hadge → Dreeve connector

[![Documentation](https://img.shields.io/badge/docs-online-c33207)](https://williamvdg.me/dreeve-hadge-connector/)

Read the [documentation site](https://williamvdg.me/dreeve-hadge-connector/) or browse
[the guides in this repository](docs/index.md).

Automatically deliver Apple Health workout summaries to Dreeve:

**Apple Health → [Hadge](https://github.com/ashtom/hadge) → your private GitHub
repository → this connector → Dreeve's watch folder.**

A separate Docker service checks immediately, then every five minutes. The first
run exports all available workout history. New workout UUIDs become summary-only
FIT files. No changes to Hadge or Dreeve are needed. Dreeve **v5.6.2 or newer** is
required for importing FIT sessions without sample records; earlier versions are
not supported. Your iPhone must already be running Hadge and syncing successfully.

## Install beside an existing Dreeve deployment

You need just **`docker-compose.yml` and `.env`** on the machine running Dreeve.
No source checkout, local image build, Python installation, or registry login is needed.

1. Download [docker-compose.yml](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/download/v0.1.0/docker-compose.yml)
   and [env.example](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/download/v0.1.0/env.example)
   from [release v0.1.0](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/tag/v0.1.0)
   into a new directory. Rename `env.example` to `.env`.
2. Set `GITHUB_REPOSITORY` in `.env` to your **Hadge data repository**
   (usually `your-name/health`, not `ashtom/hadge`).
3. Create a [fine-grained GitHub personal access token](https://github.com/settings/personal-access-tokens/new)
   restricted to that data repository, with **Contents: Read-only**. Put it in
   `GITHUB_TOKEN` in `.env`.
4. Set `DREEVE_WATCH_PATH` to the **existing host directory** your Dreeve app and
   daemon mount at `/var/www/watch`. The connector mounts that same directory at
   `/watch`. Use an absolute path, such as `/srv/dreeve/watch`, or on Windows,
   `C:/Users/you/dreeve/watch`. Keep Dreeve in `IMPORT_MODE=files` with its daemon running.

```sh
docker compose pull
docker compose up -d
docker compose logs -f connector
```

This pulls `ghcr.io/willtheorangeguy/dreeve-hadge-connector:0.1.0`, available for
Linux **amd64 and arm64**, and starts automatic synchronization. Keep `.env` private;
container environment variables are visible to users with Docker access.

Optional checks before starting the watcher:

```sh
docker compose run --rm connector check
docker compose run --rm connector preview
docker compose run --rm connector sync
```

`preview` validates and builds FIT bytes in memory, prints the workouts it would
deliver, and does not write output or delivery state. `check` verifies GitHub access
and basic watch-folder accessibility without writing a probe file. `sync` runs one
cycle; `watch` repeats it. One-shot commands exit 1 on rejected data or operational
errors. Changed, previously delivered workouts produce warnings, not failures.

Dreeve imports on its own schedule (normally every five minutes). Inspect
`/admin/file-imports` for the actual import result, or trigger an import from your
**Dreeve Compose directory**:

```sh
docker compose exec app bin/console app:import:files
```

Connector success means **delivered to the watch folder**, not confirmed imported.
After Hadge syncs, the default polling and Dreeve schedules add roughly up to ten
minutes. Hadge/iOS background scheduling can add more delay.

## Add it to your existing Dreeve Compose file

Add this service alongside your existing `app` and `daemon` entries under `services:`:

```yaml
  hadge-connector:
    image: ghcr.io/willtheorangeguy/dreeve-hadge-connector:0.1.0
    restart: unless-stopped
    init: true
    environment:
      GITHUB_REPOSITORY: ${GITHUB_REPOSITORY}
      GITHUB_TOKEN: ${GITHUB_TOKEN}
      SYNC_INTERVAL_SECONDS: ${SYNC_INTERVAL_SECONDS:-300}
      EXPORT_SINCE: ${EXPORT_SINCE:-}
      WATCH_DIR: /watch
      STATE_DIR: /state
    volumes:
      - ./watch:/watch
      - hadge-connector-state:/state
```

Merge this named volume into your existing top-level `volumes:` section, or add
that section if you do not have one:

```yaml
volumes:
  hadge-connector-state:
```

The `./watch` host directory must be the **same directory** used by your Dreeve
app and daemon. If those use another bind path or a named volume, use that same
source for the connector's `/watch` mount. The connector state volume stays separate.

Append these values to your existing Dreeve `.env`; keep your Dreeve settings:

```dotenv
GITHUB_REPOSITORY=your-github-name/health
GITHUB_TOKEN=replace-with-your-read-only-token
```

From your Dreeve Compose directory:

```sh
docker compose pull hadge-connector
docker compose up -d
docker compose logs -f hadge-connector
```

Alternatively, download [docker-compose.dreeve.yml](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/download/v0.1.0/docker-compose.dreeve.yml)
beside your existing `docker-compose.yml` and use it as an overlay. It defaults to
`./watch`; set `DREEVE_WATCH_PATH` in your existing `.env` if your host path differs.

```sh
docker compose -f docker-compose.yml -f docker-compose.dreeve.yml pull hadge-connector
docker compose -f docker-compose.yml -f docker-compose.dreeve.yml up -d
```

Keep using both `-f` arguments for later overlay updates. Copying the service and
volume into your main file instead lets you manage everything with plain `docker compose`.

## Updates

Download the setup files from the desired release, or update `CONNECTOR_VERSION`
in `.env` (or the pinned image tag in a combined stack), then run:

```sh
docker compose pull
docker compose up -d
```

Keep the state volume to prevent historical redelivery. The `0.1` and `latest`
image aliases are also published for stable releases; release downloads select
their matching version by default.

## Configuration

| Variable | Meaning / default |
| --- | --- |
| `GITHUB_REPOSITORY` | Required `owner/repository` |
| `GITHUB_TOKEN` | GitHub token; supplied through `.env` in the two-file setup |
| `GITHUB_TOKEN_FILE` | Optional token file inside the container; takes precedence over `GITHUB_TOKEN` |
| `GITHUB_BRANCH` | Blank follows the repository's default branch |
| `GITHUB_API_URL` | Advanced override for mock testing; defaults to `https://api.github.com` |
| `SYNC_INTERVAL_SECONDS` | `300`, minimum `30` |
| `EXPORT_SINCE` | Optional inclusive `YYYY-MM-DD` at midnight UTC; blank means all history |
| `WATCH_DIR` | `/watch`; must already exist |
| `STATE_DIR` | `/state`; persistent SQLite database and process lock |
| `DREEVE_WATCH_PATH` | Compose-only host path to Dreeve's existing watch folder |
| `CONNECTOR_VERSION` | Compose-only image version; release downloads choose their matching version |

To use a file-based secret, replace `GITHUB_TOKEN` in your service environment with
`GITHUB_TOKEN_FILE` and mount your token file at that path (or use a Compose secret).
The file is reread each cycle. A missing or invalid configured file is an error;
the connector does not fall back to an environment token. Changes to `.env` tokens
take effect when `docker compose up -d` recreates the service.

Run one instance per user's repository and Dreeve installation. For another user,
use another Compose project, separate state, and the correct watch folder. No
inbound network port or Dreeve credentials are required. Outbound HTTPS to GitHub
is required. GitHub Enterprise is not supported in v1. Keep `GITHUB_API_URL` at its
default in production: the configured endpoint receives your token. HTTP is used
only by the isolated synthetic integration fixture.

## What is preserved

The connector reads only `workouts/YYYY.csv`, with the headers produced by
[Hadge's exporter](https://github.com/ashtom/hadge/blob/main/Hadge/Models/Health.swift).
It preserves workout name, start/end instants, duration, distance in meters,
calories in kcal, and ascent in meters. Flights and swim stroke totals go into the
description. Empty optional metrics remain absent; numeric zeros are retained as
reported (Hadge itself often uses zero when a metric is unavailable).

Workout duration becomes FIT timer time; end minus start becomes elapsed time.
HealthKit type codes map to supported FIT sports, including running, cycling,
walking, swimming, strength, yoga, and Pilates. Unmatched codes become Workout and
retain their original name and type in the description. Hadge does not export
indoor/outdoor or pool/open-water metadata; the connector cannot distinguish them
(Dreeve labels generic swimming as Pool Swim).

Hadge's CSVs do not include GPS routes or heart-rate/power samples. No trackpoints,
sensor samples, or device identity are invented. Daily rings and daily step totals
are not imported. FIT encoding rounds timestamps and summary fields to each
field's supported precision.

## Delivery, recovery, and changes

- A workout is keyed by GitHub repository ID and HealthKit UUID, independent of
  CSV order or year. Stable filenames also make Dreeve retries deduplicatable.
- Each cycle reads a single GitHub commit. Unchanged yearly files are skipped;
  failed or rejected files are retried. Moving `EXPORT_SINCE` backwards rechecks
  history without redelivering known UUIDs.
- SQLite stores pending FIT bytes before publishing. Temporary `.tmp` files are
  created on the watch filesystem and renamed to `.fit` only when complete.
  A restart replays pending writes to the same filename. A crash between publication
  and the state commit can redeliver a file; Dreeve's duplicate detection handles
  this window. This is at-least-once delivery, not an atomic transaction with Dreeve.
  Published FIT files use mode `0644` so Dreeve can read them across user IDs;
  restrict access to the shared parent directory to protect workout data.
- The first delivered version wins. Later edits are reported for manual review;
  source deletions never delete activities. Correct existing activities in Dreeve.
- Preserve the state volume. Removing it causes history to be delivered again;
  Dreeve ordinarily skips duplicate activities. State is separate from the watch
  folder because Dreeve consumes imported files. Do not share state across different
  destination installations or change the destination while pending writes exist.
- Rejected rows are logged with file, row number, and reason, without raw row data.
  Fix them at the source and rerun. Names and identifiers still exist in the generated
  FIT files and state; protect those directories as health data.
- Network/server errors use bounded retries. Rate-limit reset and Retry-After
  headers delay the next watcher cycle. Token files are reread each cycle for rotation.

The container runs as root by default to accommodate existing watch-folder mounts.
For a non-root deployment, set Compose `user: "UID:GID"` and provision state, watch,
and secret-file permissions for that user. Keep the volume on a local filesystem
with reliable rename and SQLite locking semantics. Network filesystems are not a
supported state location.

## Troubleshooting

If no workout files are found, check Hadge has exported `workouts/YYYY.csv` to the
configured branch. If GitHub access fails, check token expiration, repository
selection, Contents permission, and any organization approval requirement.

If files arrive but Dreeve shows nothing, inspect `/admin/file-imports`, verify the
shared host directory, Dreeve version, import mode, and daemon. Permission failures
are retried without marking pending deliveries successful. An unchanged file
does not imply that Dreeve imported it; the connector does not query Dreeve.

## Development

Clone the repository for development. To build the connector locally with the
normal settings from `.env`, use the development overlay:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

```sh
uv venv --python 3.12
uv pip install -e '.[dev]'
uv run --no-project python -m pytest
uv run --no-project ruff check .
```

Alternatively activate the virtual environment and run `pytest` and `ruff check .`.
Tests use synthetic data, mocked GitHub responses, a separate FIT decoder, and an
optional full Docker workflow: a mock GitHub HTTP service backed by a real Git
repository, the packaged connector watcher, Dreeve's web app, and its real daemon.
It verifies historical and incremental imports through the authenticated web API,
token rotation, restart recovery, rejected rows, source edits, and duplicate replay.
No private health repository is needed.
See `tests/integration/README.md` for the integration procedure.
GitHub Actions runs the unit suite on Linux and Windows, builds the connector image,
and runs the complete four-service acceptance test with synthetic data. The latter
normally takes 6–11 minutes because it waits for Dreeve's actual five-minute schedule
for initial and incremental imports; the duplicate replay is triggered explicitly.

Runtime dependencies: `requests`, BSD-licensed community-maintained `fit-tool`
0.9.16, and `filelock` for cross-platform process coordination. This project is MIT
licensed and does not bundle Dreeve or Hadge source code.

## Publishing a release

Update the version in `pyproject.toml` and the setup-file defaults, commit, and
publish the matching `vX.Y.Z` GitHub release. The release workflow validates the
tag, runs the Windows/Linux unit suite and the full Dreeve integration test, then
publishes amd64/arm64 images to GHCR with provenance and an SBOM. After the image
is published it attaches the matching standalone Compose file, environment
template, and existing-Dreeve overlay to the release. No publishing secret is
required beyond the workflow's repository-scoped `GITHUB_TOKEN`.
