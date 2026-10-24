# Usage

Use `preview` before changing backfill scope, and inspect Dreeve separately after delivery. See [CLI reference](./api.md) for the command contract.

## Inspect a planned backfill

```sh
docker compose run --rm connector preview
```

With blank `EXPORT_SINCE`, the first run considers every discovered yearly CSV. Set `EXPORT_SINCE=2026-01-01` to include workouts starting at or after midnight UTC on that date. Moving the date backwards changes the file-cache scope and rechecks older history. Known UUIDs remain deduplicated by delivery state.

## Run one cycle

If the watcher is already running, stop it first to avoid competing for the same state lock:

```sh
docker compose stop connector
docker compose run --rm connector sync
docker compose up -d
```

Valid new rows can be delivered even when other rows are rejected. A one-shot exit 1 therefore does not mean that no files were published.

## Read the summary

| Counter | Meaning |
| --- | --- |
| `delivered` | FIT files published this cycle, including replayed pending writes |
| `planned` | New valid workouts that preview would publish |
| `skipped` | Parsed rows whose UUID and fingerprint were already seen |
| `filtered` | Parsed rows starting before the inclusive filter |
| `changed` | Seen UUIDs with a different normalized fingerprint; manual review required |
| `rejected` | Rejected rows, file-level parse errors, or FIT encoding failures |
| `cached_files` | Yearly files skipped because their blob SHA matches the checkpoint |

Counters describe work performed in this cycle. A cached file contributes to `cached_files`, not its original number of workouts to `skipped`. A successful repeat run can therefore show zero delivered and one cached file. Changed rows warn without making one-shot commands fail.

## Run continuously

```sh
docker compose up -d
docker compose logs --tail 100 connector
docker compose ps
```

The container defaults to `watch`; a cycle starts immediately, then waits 300 seconds by default. A running container can still be logging repeated operational errors. Check logs and Dreeve's import status, rather than treating container uptime as a delivery guarantee.

## Verify an import

Connector logs confirm publication to the shared folder. In Dreeve, inspect `/admin/file-imports` for imported, failed, or duplicate entries. To import immediately, run from the Dreeve Compose directory:

```sh
docker compose exec app bin/console app:import:files
```

For a combined stack, the connector service is named `hadge-connector`. Substitute that name in connector commands. For an overlay installation, include both Compose file arguments. See [Deployment](./deployment.md).
