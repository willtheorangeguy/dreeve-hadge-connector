# Configuration

The connector reads process environment variables at startup. It has no configuration file and no setting flags. Docker Compose reads `.env` for interpolation and passes the explicitly listed settings into the container. A source-installed CLI does **not** read `.env`.

## Precedence

For credentials, a nonempty `GITHUB_TOKEN_FILE` takes precedence over `GITHUB_TOKEN`. A missing, unreadable, empty, or invalid configured file is an error; there is no token fallback. The file is reread whenever a GitHub client is created, including every watcher cycle. Other settings use the process environment or their defaults and require a restart to change.

For supplied Compose files, shell variables override `.env` interpolation values. A setting in `.env` only reaches the connector if the service passes it through. Advanced settings such as `GITHUB_TOKEN_FILE` require a Compose edit or override.

## Connector environment

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `GITHUB_REPOSITORY` | string | Required | Hadge data repository, for example `your-github-name/health`. Must match `owner/repository`; normalized to lowercase. |
| `GITHUB_TOKEN` | string | Required unless token file configured | One nonempty token without whitespace, for example a fine-grained read-only token from GitHub settings. |
| `GITHUB_TOKEN_FILE` | path | Unset | Token path visible inside the container, for example `/run/secrets/github_token`. |
| `GITHUB_BRANCH` | string | Repository default branch | Explicit branch or ref, for example `main`. Blank uses repository metadata each cycle. |
| `SYNC_INTERVAL_SECONDS` | integer | `300` | Delay after each watcher cycle, for example `600`. Minimum `30`. |
| `EXPORT_SINCE` | date | All history | Inclusive workout start date at midnight UTC, for example `2026-01-01`. Blank disables filtering. Format must be `YYYY-MM-DD`. |
| `WATCH_DIR` | path | `/watch` | Existing destination directory, for example `/srv/dreeve/watch` for a source install. |
| `STATE_DIR` | path | `/state` | Persistent SQLite and lock directory, for example `/srv/hadge-state` for a source install. Must differ from `WATCH_DIR`. |
| `GITHUB_API_URL` | HTTP(S) URL | `https://api.github.com` | Advanced test override. The integration fixture uses `http://github:8000`. Production must retain the default. |

Invalid repository syntax, dates, API URLs, missing credentials, and intervals below 30 fail with exit 1. API URLs cannot contain embedded credentials, query strings, or fragments. Configured token content is validated when a client opens. Filesystem access errors surface when the relevant command uses the path.

The configured API receives the bearer token. GitHub Enterprise is not supported in v1; the test override is not an Enterprise compatibility guarantee.

## Compose interpolation

| Option | Type | Default | Description |
| --- | --- | --- | --- |
| `CONNECTOR_VERSION` | image tag | `0.1.0` in checkout | Published image version, for example `0.1.0`. Release downloads select the matching version. |
| `DREEVE_WATCH_PATH` | host path | Required standalone; `./watch` in Dreeve overlay | Existing Dreeve watch directory, for example `/srv/dreeve/watch` or `C:/Users/you/dreeve/watch`. |

These two values configure Compose; the connector does not read them. Supplied files fix `WATCH_DIR=/watch` and `STATE_DIR=/state` inside the container. Bind mounts use `create_host_path: false` so a mistyped source path fails instead of creating an empty directory.

## Examples

### Environment token

```dotenv title=".env"
CONNECTOR_VERSION=0.1.0
GITHUB_REPOSITORY=your-github-name/health
GITHUB_TOKEN=replace-with-your-read-only-token
GITHUB_BRANCH=
DREEVE_WATCH_PATH=/srv/dreeve/watch
SYNC_INTERVAL_SECONDS=300
EXPORT_SINCE=2026-01-01
```

Replace the token placeholder with a token restricted to the data repository, with **Contents: Read-only**. Container environment variables are visible to users with Docker access. Keep `.env` private and outside version control.

### Token file

The supplied service requires `GITHUB_TOKEN` during Compose interpolation. For a file secret, **replace that service definition**, removing its required `GITHUB_TOKEN` environment entry. Adding a token file only to `.env` or layering a second credential on top is insufficient. This standalone definition uses the existing token file `./secrets/github_token`:

```yaml title="compose.secret.yml"
services:
  connector:
    image: ghcr.io/willtheorangeguy/dreeve-hadge-connector:0.1.0
    restart: unless-stopped
    init: true
    environment:
      GITHUB_REPOSITORY: ${GITHUB_REPOSITORY:?Set GITHUB_REPOSITORY}
      GITHUB_TOKEN_FILE: /run/secrets/github_token
      WATCH_DIR: /watch
      STATE_DIR: /state
      SYNC_INTERVAL_SECONDS: ${SYNC_INTERVAL_SECONDS:-300}
      EXPORT_SINCE: ${EXPORT_SINCE:-}
    secrets:
      - github_token
    volumes:
      - type: bind
        source: ${DREEVE_WATCH_PATH:?Set DREEVE_WATCH_PATH}
        target: /watch
        bind:
          create_host_path: false
      - connector-state:/state
secrets:
  github_token:
    file: ./secrets/github_token
volumes:
  connector-state:
```

```sh
docker compose -f compose.secret.yml run --rm connector check
docker compose -f compose.secret.yml up -d
```

Use the same project and state volume if converting an existing standalone installation. Keep the host secret file private and readable by the container user. Replace its contents to rotate the token; the watcher reads it on its next cycle. Recreate the service after changing an environment token:

```sh
docker compose up -d
```

See [Troubleshooting](./troubleshooting.md) for credential and mount errors.
