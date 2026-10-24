# Getting started

This is the standalone Docker path for an existing Dreeve installation. You need two downloaded files and access to the same host directory Dreeve watches.

## Prerequisites

- Docker Engine or Docker Desktop with Docker Compose v2. Check with `docker --version` and `docker compose version`.
- Dreeve **v5.6.2 or newer**, configured with `IMPORT_MODE=files` and its daemon running. The acceptance test uses v5.6.2.
- Hadge already exporting `workouts/YYYY.csv` into your GitHub data repository.
- A fine-grained GitHub personal access token restricted to that repository with **Contents: Read-only**. Create it in [GitHub token settings](https://github.com/settings/personal-access-tokens/new). Complete any organization approval requirement.
- The existing host watch directory mounted at `/var/www/watch` by both Dreeve's app and daemon. The connector uses `/watch` inside its own container.

The published image supports Linux amd64 and arm64. Python and a source checkout are unnecessary for this path.

## Install

Create a directory for the connector. Download [docker-compose.yml](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/download/v0.1.0/docker-compose.yml) and [env.example](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/download/v0.1.0/env.example) into it. Rename `env.example` to `.env`.

Set these values, replacing the repository, token, and path with yours. Keep the other downloaded defaults:

```dotenv title=".env"
CONNECTOR_VERSION=0.1.0
GITHUB_REPOSITORY=your-github-name/health
GITHUB_TOKEN=replace-with-your-read-only-token
GITHUB_BRANCH=
DREEVE_WATCH_PATH=/srv/dreeve/watch
SYNC_INTERVAL_SECONDS=300
EXPORT_SINCE=
```

Use your **Hadge data repository**, usually `your-name/health`, rather than `ashtom/hadge`. On Windows Docker Desktop, a host path can use forward slashes, such as `C:/Users/you/dreeve/watch`. The directory must already exist. Keep `.env` private.

For other methods, see [Installation](./installation.md).

## First run

Run these commands from the directory containing the downloaded files.

1. Pull the release image:

    ```sh
    docker compose pull
    ```

    Compose pulls `ghcr.io/willtheorangeguy/dreeve-hadge-connector:0.1.0`.

2. Check credentials, the source listing, and basic watch-folder access:

    ```sh
    docker compose run --rm connector check
    ```

    A successful log contains `GitHub access OK`, a yearly-file count, and `watch folder accessible`. The check does not write a probe or validate workout rows.

3. Preview the first backfill:

    ```sh
    docker compose run --rm connector preview
    ```

    For each new valid workout, logs say `would deliver workout`, followed by a `Preview:` summary with `planned` and `rejected` counts. A successful preview exits 0. Nothing is written to the watch folder or delivery database.

4. Start automatic delivery:

    ```sh
    docker compose up -d
    docker compose logs -f connector
    ```

    The watcher runs immediately. A `Watch delivery:` summary reports `delivered`, `changed`, `rejected`, and other counters. Exit log-following with Ctrl+C; the detached service continues running.

5. Verify the result in Dreeve at `/admin/file-imports` and in its activities view. Its daemon normally imports every five minutes. To trigger it yourself, run this from your **Dreeve Compose directory**:

    ```sh
    docker compose exec app bin/console app:import:files
    ```

## What happened

The connector resolved one GitHub commit, validated Hadge's yearly CSVs, and delivered summary-only FIT files for new UUIDs. Its separate named state volume records successful deliveries. Dreeve consumes those files on its own schedule. A disappearing FIT file alone does not prove a successful import; inspect Dreeve's import results.

Blank `EXPORT_SINCE` backfills all history. After Hadge exports, default connector and Dreeve schedules can add roughly ten minutes. Hadge/iOS background scheduling can add further delay.

## Next steps

- [Usage](./usage.md) explains one-shot commands and summary counters.
- [Configuration](./configuration.md) covers date filters, branch selection, and token files.
- [Deployment](./deployment.md) covers combined stacks and permissions.
- [Recovery](./recovery.md) explains why you must retain the state volume.
