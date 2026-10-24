# Deployment

Run one instance per user's Hadge repository and Dreeve destination. Give each destination separate persistent state. The connector requires outbound HTTPS to GitHub, no inbound port, and no Dreeve credentials.

## Standalone service

The release `docker-compose.yml` runs service `connector`, mounts `DREEVE_WATCH_PATH` at `/watch`, and creates named volume `connector-state` at `/state`. It uses `restart: unless-stopped` and `init: true`.

```sh
docker compose pull
docker compose up -d
docker compose logs --tail 100 connector
```

Use an absolute host watch path to avoid resolving it relative to the wrong Compose directory. Both Dreeve services must see the same host directory at `/var/www/watch`. See [Getting started](./getting-started.md).

## Merge into Dreeve Compose

Add this service under your existing `services:` and merge the state volume into the top-level `volumes:` map. This example assumes Dreeve already uses the host directory `./watch`:

```yaml title="docker-compose.yml additions"
services:
  hadge-connector:
    image: ghcr.io/willtheorangeguy/dreeve-hadge-connector:0.1.0
    restart: unless-stopped
    init: true
    environment:
      GITHUB_REPOSITORY: ${GITHUB_REPOSITORY:?Set GITHUB_REPOSITORY}
      GITHUB_TOKEN: ${GITHUB_TOKEN:?Set GITHUB_TOKEN}
      GITHUB_BRANCH: ${GITHUB_BRANCH:-}
      SYNC_INTERVAL_SECONDS: ${SYNC_INTERVAL_SECONDS:-300}
      EXPORT_SINCE: ${EXPORT_SINCE:-}
      WATCH_DIR: /watch
      STATE_DIR: /state
    volumes:
      - ./watch:/watch
      - hadge-connector-state:/state
volumes:
  hadge-connector-state:
```

If Dreeve uses a different bind source or named volume, use that same source for `/watch`. Do not use Dreeve's database or file-storage volume as connector state. Append connector credentials to the existing `.env` while retaining Dreeve settings:

```dotenv title=".env additions"
GITHUB_REPOSITORY=your-github-name/health
GITHUB_TOKEN=replace-with-your-read-only-token
```

```sh
docker compose pull hadge-connector
docker compose up -d hadge-connector
docker compose logs -f hadge-connector
```

## Use the release overlay

Instead of merging YAML, place the released `docker-compose.dreeve.yml` beside the existing Dreeve file:

```sh
docker compose -f docker-compose.yml -f docker-compose.dreeve.yml pull hadge-connector
docker compose -f docker-compose.yml -f docker-compose.dreeve.yml up -d hadge-connector
docker compose -f docker-compose.yml -f docker-compose.dreeve.yml logs -f hadge-connector
```

The overlay defaults to `./watch`; set `DREEVE_WATCH_PATH` in Dreeve's `.env` if needed. Keep both `-f` arguments for later commands. The overlay's state volume is `hadge-connector-state`, distinct from the standalone service's volume. Preserve or migrate state deliberately when switching installation methods.

## Permissions

The container runs as root by default to accommodate existing watch mounts. For a non-root deployment, add `user: "UID:GID"` using the numeric user/group appropriate to your host, and provision writable watch/state directories and readable secrets for that identity. Published FIT files use mode `0644` so Dreeve can read across user IDs. Restrict parent-directory access to protect workout data.

`check` uses a basic directory/access test. It does not prove that a subsequent atomic write, chmod, rename, fsync, or SQLite transaction will succeed. Use `preview` followed by a controlled `sync` when validating a deployment.

## Service lifecycle

```sh
docker compose stop connector
docker compose start connector
docker compose restart connector
```

`restart` rereads a mounted token file but does not apply changed Compose environment settings. Use `docker compose up -d` to recreate after `.env` or service-definition changes. Keep the Compose project name and state volume stable across deployments. See [Recovery](./recovery.md) before moving destinations or restoring state.
