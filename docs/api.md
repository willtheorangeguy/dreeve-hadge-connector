# CLI reference

The supported public interface is the `dreeve-hadge-connector` executable. It exposes four positional commands and no HTTP server. All settings come from the [environment](./configuration.md). The Python modules are implementation details rather than a separately versioned library API.

## Help

```sh
docker compose run --rm connector --help
```

| Argument or flag | Type | Default | Description |
| --- | --- | --- | --- |
| `command` | positional choice | Required | One of `check`, `preview`, `sync`, `watch`. The Docker image supplies `watch` as its default command. |
| `-h`, `--help` | flag | Off | Print argparse help and exit 0 without reading connector configuration. |

A source install uses `dreeve-hadge-connector check` instead of the Docker wrapper. Invalid or missing command arguments produce argparse usage and exit 2.

## Check

```sh
docker compose run --rm connector check
```

| Aspect | Behavior |
| --- | --- |
| GitHub | Authenticate, resolve a commit, list yearly files |
| Filesystem | Check existing writable watch directory and separate state path |
| Writes | No probe, FIT output, or state writes |
| Result | Exit 0 on success; exit 1 on configuration, access, or operational error |

With one yearly file, successful messages include:

```text
GitHub access OK; 1 yearly workout files; watch folder accessible
check does not write files; sync verifies actual delivery permissions
```

It does not parse CSV rows, test SQLite writability, or confirm Dreeve imports.

## Preview

```sh
docker compose run --rm connector preview
```

| Aspect | Behavior |
| --- | --- |
| Validation | Parse uncached files and build FIT bytes in memory for new workouts |
| State | Read an existing database in read-only mode; use an in-memory database if none exists |
| Pending deliveries | Leave pending files unwritten |
| Writes | No output, delivery-state changes, file checkpoints, or process lock |
| Result | Exit 1 for rejected data or operational errors; otherwise 0 |

For the synthetic running fixture with no existing state, the summary message is:

```text
Preview: delivered=0, planned=1, skipped=0, filtered=0, changed=0, rejected=0, cached_files=0
```

Individual planning messages contain workout UUIDs. Treat these logs as sensitive. Preview uses existing file checkpoints, so it does not force a reparse of unchanged files.

## Sync

```sh
docker compose run --rm connector sync
```

| Aspect | Behavior |
| --- | --- |
| Work | Replay pending deliveries, then process one snapshot |
| State | Acquire a nonblocking process lock; persist pending and delivered records |
| Writes | Publish complete FIT files and checkpoint fully processed source files |
| Result | Exit 1 for rejected data or operational errors; otherwise 0 |

For the same single-workout fixture, the first successful run reports:

```text
Watch delivery: delivered=1, planned=0, skipped=0, filtered=0, changed=0, rejected=0, cached_files=0
```

Stop a running watcher before a one-shot `sync` if you need to avoid lock contention. The command does not wait for Dreeve.

## Watch

```sh
docker compose run --rm connector watch
```

| Aspect | Behavior |
| --- | --- |
| First cycle | Immediate |
| Later cycles | Wait `SYNC_INTERVAL_SECONDS` after each completed or failed cycle |
| Rate limits | Wait at least the interval or GitHub's indicated delay, whichever is longer |
| Errors during cycles | Log and retry on the next cycle |
| Invalid startup configuration | Exit 1 |
| Shutdown | SIGINT or SIGTERM requests a stop; normal shutdown exits 0 |

For normal detached operation, use `docker compose up -d` instead of a foreground one-off container. Each cycle emits the same counter summary as `sync` unless an operational error interrupts it. Logs use INFO level with timestamps and go to stderr.

## External API consumed

The connector sends authenticated GET requests to GitHub's REST API with API version `2022-11-28`. It uses these repository-relative paths:

| Path | Purpose | Consumed response |
| --- | --- | --- |
| `/repos/{owner}/{repo}` | Find stable repository ID and default branch | JSON `id`, `default_branch` |
| `/repos/{owner}/{repo}/commits/{ref}` | Resolve configured/default ref | JSON `sha` |
| `/repos/{owner}/{repo}/contents/workouts?ref={commit}` | List source files at that commit | JSON array with `type`, `path`, `sha` |
| `/repos/{owner}/{repo}/contents/workouts/2026.csv?ref={commit}` | Read one discovered file | Raw CSV bytes using `application/vnd.github.raw+json` |

Run `check` to exercise the first three requests and `preview` to exercise raw reads. The source contract is in [Data reference](./data.md). Requests disable redirects and use connect/read timeouts of 10/60 seconds. Network failures and server errors retry up to four attempts with 1, 2, and 4 second waits. HTTP 401, 403, 404, rate limits, malformed responses, and responses over 100 MiB become sanitized errors; the connector does not log HTTP bodies or tokens.
