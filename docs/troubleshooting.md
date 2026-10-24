# Troubleshooting

Start with connector logs and Dreeve's `/admin/file-imports`. Connector delivery and Dreeve import are separate operations.

```sh
docker compose logs --tail 100 connector
docker compose run --rm connector check
docker compose run --rm connector preview
```

For a combined stack, use service `hadge-connector`. For an overlay, retain both Compose file arguments. Do not share tokens or raw health data in reports.

## Configuration and credentials

| Message or symptom | Meaning | Action |
| --- | --- | --- |
| `GITHUB_REPOSITORY must be owner/repository` | Missing or malformed repository | Set the Hadge data repository, such as `your-name/health`, not a URL. |
| `Set GITHUB_TOKEN or GITHUB_TOKEN_FILE` | No credential source | Supply a token or pass a mounted token file through the service environment. |
| `Cannot read GITHUB_TOKEN_FILE` | Configured path cannot be read | Check container path, mount, existence, and permissions. There is no fallback to the environment token. |
| `must contain one nonempty token` | Empty or whitespace-containing credential | Store only the token; remove embedded spaces or extra values. Surrounding whitespace is stripped. |
| `GitHub token expired or invalid` | HTTP 401 | Replace or renew the token. Recreate for an environment-token change. |
| `GitHub access denied` | HTTP 403 without rate-limit indicators | Check repository selection, Contents read permission, and organization approval. |
| `GitHub repository, branch, or workouts folder not found` | HTTP 404 at one of those lookups | Check credentials, data repository, branch, and Hadge export path. |
| `SYNC_INTERVAL_SECONDS must be at least 30` | Interval too small | Use `300` or another integer at least 30. |
| `EXPORT_SINCE must be YYYY-MM-DD` | Wrong date syntax | Use a valid date such as `2026-01-01`, or leave blank. |

## Filesystem and state

| Message or symptom | Meaning | Action |
| --- | --- | --- |
| Compose reports a missing bind source | Host watch path does not exist | Set `DREEVE_WATCH_PATH` to Dreeve's existing directory. Supplied binds do not create it. |
| `WATCH_DIR must be an existing writable directory` | Basic `check` access test failed | Confirm the mounted directory and container-user permissions. |
| `WATCH_DIR must be an existing directory mounted from Dreeve` | Mutating sync has no destination directory | Repair the bind mount before retrying. |
| `STATE_DIR must be separate from WATCH_DIR` | Resolved paths are identical | Mount independent state storage. Dreeve consumes the watch contents. |
| `Another sync process is using this state directory` | The nonblocking lock is held | Stop the watcher before manual sync, or use a separate state location for a separate destination. |
| Permission, chmod, rename, or SQLite error | Actual publication or persistence failed | Provision writable local watch/state storage for the container user. Pending rows retry after repair. |
| State volume appears empty after redeploy | Compose project or volume changed | Locate and reuse the original volume before allowing historical replay. |

## Source validation

| Message | Action |
| --- | --- |
| `CSV does not have the Hadge workout headers` | Check the case-sensitive required fields in [Data reference](./data.md). |
| `missing or duplicate CSV headers` | Restore a header row with unique names. |
| `invalid UTF-8 or malformed CSV quoting` | Repair file encoding or quoting at the source. |
| `wrong number of CSV columns` | Repair the reported row's field count. |
| `invalid or out-of-range timestamp (explicit offset required)` | Supply an in-range ISO timestamp with UTC offset. |
| `inconsistent start, end, or duration` | Ensure positive elapsed/timer duration and timer time no greater than elapsed time beyond the accepted tolerance. |
| `outside supported range` or `values could not be encoded as FIT` | Correct the metric using the documented FIT bounds. |
| `previously seen UUID changed; manual review required` | Review the existing Dreeve activity. The connector keeps the first delivered version. |

Rows are reported by CSV line number without raw row data. A one-shot command exits 1 when any data is rejected, even when other valid rows were delivered. Changed UUIDs warn without making the command fail.

## No activities in Dreeve

If zero yearly files are found, verify Hadge exports files named `workouts/YYYY.csv` on the selected branch. Other names and directories are ignored. Check `EXPORT_SINCE` and `cached_files` before assuming a cycle should deliver new files.

If the connector reports delivery, confirm Dreeve v5.6.2 or newer, `IMPORT_MODE=files`, a running daemon, and the same host watch source in both deployments. Inspect `/admin/file-imports` for failed or duplicate imports. From the Dreeve Compose directory, trigger:

```sh
docker compose exec app bin/console app:import:files
```

Dreeve may have consumed a file already, so an empty watch directory does not establish whether delivery failed. Check Dreeve's activity and import records.

## GitHub delays and safety limits

`GitHub rate limit reached; waiting before the next cycle` means `watch` delays according to `Retry-After` or reset headers, at least as long as its configured interval. A one-shot command exits 1; retry later. Network/server errors have bounded request retries. Do not run many redundant instances against the same repository.

`Unexpected or truncated workouts directory listing` rejects a non-array listing or one with 1,000 or more entries. `GitHub response exceeds the 100 MiB safety limit` rejects an oversized response. These are input limits, not permission problems. The client does not paginate or split those inputs.
