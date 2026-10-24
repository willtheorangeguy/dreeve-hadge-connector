# Recovery

Preserve connector state independently of the watch folder. It records what was delivered even after Dreeve consumes the files.

## Restart after a failure

```sh
docker compose restart connector
docker compose logs --tail 100 connector
```

The next mutating cycle replays pending database rows before reading GitHub. Each row contains the stable filename and complete FIT bytes. Failed writes remain pending. A crash after a successful rename but before the state acknowledgment can deliver the same filename again; Dreeve ordinarily skips the duplicate activity.

Do not change the destination while pending rows exist. Those rows refer to the original destination's delivery history even though only the configured filesystem path controls where they are replayed.

## Correct source data

Fix rejected CSV rows in the Hadge source and let Hadge publish a new commit. Rejected files remain eligible for retry; valid workouts already delivered from them are deduplicated. A changed previously seen UUID is reported for manual review and is not overwritten. Correct an existing activity in Dreeve. Deleting a source row never deletes its Dreeve activity.

## Backfill older history

Move `EXPORT_SINCE` backwards, or make it blank, in `.env`, then recreate the service:

```sh
docker compose up -d
```

The cache scope changes, causing historical files to be reconsidered. Existing repository-ID/UUID delivery records still prevent ordinary redelivery. You do not need to delete state to extend a backfill.

## Back up state

Stop the standalone connector to prevent concurrent writes. From its Compose directory, this streams the mounted state directory into a local archive:

```sh
docker compose stop connector
docker compose run --rm --no-deps --entrypoint tar connector -C /state -cf - . > connector-state.tar
```

Use a shell that preserves binary native-command redirection, such as a POSIX shell or PowerShell 7.4 or newer. Keep the service stopped while backing up the matching Dreeve database and file storage using Dreeve's own procedures, then restart it:

```sh
docker compose up -d
```

Protect the archive as health data. It contains UUIDs, filenames, fingerprints, and possibly pending FIT payloads. Save the nonsecret Compose configuration and separately safeguard credentials. A state backup alone does not back up imported Dreeve activities.

## Restore state

Restore into the same destination installation and the intended Compose project's state volume while the watcher is stopped:

```sh
docker compose stop connector
docker compose run --rm --no-deps --entrypoint tar connector -C /state -xf - < connector-state.tar
docker compose up -d
```

The input-redirection command above uses a POSIX shell. Restore to a fresh state volume or one known to contain the matching stopped state; do not overlay a live database. An older backup may replay workouts delivered since that backup. Dreeve's duplicate detection is part of recovery.

If Dreeve was restored to an earlier point than the connector, state may mark lost Dreeve activities as already delivered. Coordinate backups and restores so both histories describe the same destination. The connector cannot reconcile Dreeve's database.

## State loss or intentional replay

A new empty state location treats history as undelivered and republishes valid workouts within the filter. Dreeve ordinarily detects duplicates, but the connector does not verify this outcome. Inspect its import log. Do not remove production state to fix credentials, rejected rows, or a date filter. The synthetic [acceptance test](./testing.md) verifies replay against an isolated Dreeve installation.
