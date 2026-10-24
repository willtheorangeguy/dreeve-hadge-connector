# Hadge → Dreeve connector

Deliver Apple Health workout summaries from [Hadge](https://github.com/ashtom/hadge) to Dreeve without changing either application. A Docker service reads your private GitHub workout exports and publishes summary FIT files into Dreeve's existing watch folder. Run it beside Dreeve v5.6.2 or newer, with Hadge already syncing from your iPhone.

## Key features

- Backfill all available workout history, or start at an inclusive UTC date.
- Poll immediately and then every five minutes by default.
- Preserve workout names, supported sports, timestamps, duration, distance, calories, and ascent.
- Preview deliveries without writing files or state.
- Recover pending deliveries after a restart using persistent SQLite state.
- Read one immutable GitHub commit per cycle and skip unchanged yearly files.
- Use an environment token or a token file that can rotate between cycles.

## Quick start

Download `docker-compose.yml` and `env.example` from [release v0.1.0](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/tag/v0.1.0). Rename `env.example` to `.env`, set your Hadge data repository, read-only token, and existing Dreeve watch-folder path, then run:

```sh
docker compose pull
docker compose run --rm connector check
docker compose run --rm connector preview
docker compose up -d
```

Follow [Getting started](./getting-started.md) for the complete sequence and how to verify an import. Connector success means delivery to the watch folder. Dreeve imports files separately.

## Where to next

<div class="grid cards" markdown>

- **Set up the connector**

    [Installation](./installation.md) covers standalone Docker, existing stacks, and source installs.

- **Choose settings**

    [Configuration](./configuration.md) lists every environment variable and token-file setup.

- **Understand your data**

    [Data reference](./data.md) covers accepted CSV fields, validation, and FIT output.

- **Operate and recover**

    [Recovery](./recovery.md) explains state, replay, backups, and source changes.

- **Modify the connector**

    [Architecture](./architecture.md) and [Development](./development.md) explain the implementation and checks.

- **Diagnose a failure**

    [Troubleshooting](./troubleshooting.md) maps log messages and import symptoms to actions.

</div>

## Support

Open a [GitHub Discussion](https://github.com/willtheorangeguy/dreeve-hadge-connector/discussions/new) or file an [issue](https://github.com/willtheorangeguy/dreeve-hadge-connector/issues/new/choose). Remove tokens, private repository details, workout names, and identifiers from diagnostics before sharing them.
