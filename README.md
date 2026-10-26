<!-- Logo -->
<h1 align="center">Hadge → Dreeve connector</h1>

<!-- Tagline -->
<h4 align="center">Deliver Apple Health workout summaries from Hadge to Dreeve's watch folder.</h4>

<!-- Badges -->
<div align="center">
  <a href="https://github.com/willtheorangeguy/dreeve-hadge-connector/issues"><img alt="GitHub Issues" src="https://img.shields.io/github/issues/willtheorangeguy/dreeve-hadge-connector"></a>
  <a href="https://github.com/willtheorangeguy/dreeve-hadge-connector/pulls"><img alt="GitHub Pull Requests" src="https://img.shields.io/github/issues-pr/willtheorangeguy/dreeve-hadge-connector"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <a href="https://github.com/willtheorangeguy/dreeve-hadge-connector/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/willtheorangeguy/dreeve-hadge-connector/actions/workflows/test.yml/badge.svg"></a>
  <a href="https://github.com/willtheorangeguy/dreeve-hadge-connector/actions/workflows/publish.yml"><img alt="Publish release image" src="https://github.com/willtheorangeguy/dreeve-hadge-connector/actions/workflows/publish.yml/badge.svg"></a>
  <a href="https://github.com/willtheorangeguy/dreeve-hadge-connector/actions/workflows/docs.yml"><img alt="Docs" src="https://github.com/willtheorangeguy/dreeve-hadge-connector/actions/workflows/docs.yml/badge.svg"></a>
  <a href="https://github.com/willtheorangeguy/dreeve-hadge-connector/actions/workflows/docs-lint.yml"><img alt="Docs Lint" src="https://github.com/willtheorangeguy/dreeve-hadge-connector/actions/workflows/docs-lint.yml/badge.svg"></a>
  <a href="https://github.com/willtheorangeguy/dreeve-hadge-connector/releases"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/willtheorangeguy/dreeve-hadge-connector"></a>
  <a href="https://williamvdg.me/dreeve-hadge-connector/"><img alt="Documentation" src="https://img.shields.io/badge/docs-online-c33207"></a>
</div>

<!-- Nav -->
<p align="center">
  <a href="#key-features">Key Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#documentation">Documentation</a> •
  <a href="#support">Support</a> •
  <a href="#contributing">Contributing</a> •
  <a href="#license">License</a> •
  <a href="#credits">Credits</a>
</p>

A separate Docker service reads your private [Hadge](https://github.com/ashtom/hadge)
GitHub exports and publishes summary-only FIT files into Dreeve's existing watch
folder. No changes to Hadge or Dreeve are needed.

## Key Features

- Backfill all available workout history, or start at an inclusive UTC date.
- Check immediately, then poll every five minutes by default.
- Preserve workout names, supported sports, timestamps, duration, distance, calories, and ascent.
- Preview deliveries without writing files or delivery state.
- Recover pending deliveries after a restart using persistent SQLite state.
- Read one immutable GitHub commit per cycle and skip unchanged yearly files.
- Rotate credentials through a token file reread each watcher cycle.

## Installation

Use Docker Compose v2 beside Dreeve **v5.6.2 or newer**, with `IMPORT_MODE=files`
and its daemon running. Hadge must already export `workouts/YYYY.csv` to GitHub.

1. Download [docker-compose.yml](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/download/v0.1.0/docker-compose.yml) and [env.example](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/download/v0.1.0/env.example) into a new directory. Rename `env.example` to `.env`.
2. Set `GITHUB_REPOSITORY` to your Hadge data repository and `GITHUB_TOKEN` to a fine-grained token with **Contents: Read-only** access to that repository.
3. Set `DREEVE_WATCH_PATH` to the existing host directory Dreeve's app and daemon watch, such as `/srv/dreeve/watch`. Keep `.env` private.

```sh
docker compose pull
docker compose run --rm connector check
docker compose run --rm connector preview
docker compose up -d
```

The public image supports Linux amd64 and arm64. Follow [Getting started](docs/getting-started.md)
for the complete setup. Other installation methods live in [Installation](docs/installation.md).

## Usage

Inspect automatic deliveries from the directory containing your Compose file:

```sh
docker compose logs --tail 100 connector
```

A `Watch delivery:` summary reports delivered, changed, and rejected workouts.
Delivery means a FIT file reached the watch folder; verify imports separately in
Dreeve's `/admin/file-imports`. Preserve the connector's state volume to prevent
historical redelivery. See [Usage](docs/usage.md) and [Recovery](docs/recovery.md).

## Documentation

Read the [documentation site](https://williamvdg.me/dreeve-hadge-connector/) or browse [`docs/`](docs/index.md):
[Installation](docs/installation.md) · [Usage](docs/usage.md) · [Configuration](docs/configuration.md) · [Troubleshooting](docs/troubleshooting.md).

## Support

File an [issue](https://github.com/willtheorangeguy/dreeve-hadge-connector/issues/new/choose).
Remove tokens and private health data from diagnostics before sharing them.

## Contributing

Contributions welcome. See the org-wide [Contributing Guide](https://github.com/willtheorangeguy/.github/blob/main/CONTRIBUTING.md) and [Code of Conduct](https://github.com/willtheorangeguy/.github/blob/main/CODE_OF_CONDUCT.md).
For local setup, tests, and documentation checks, read [Development](docs/development.md).

## License

MIT — see [`LICENSE`](LICENSE).

## Credits

Built with `requests`, community-maintained BSD-licensed `fit-tool` 0.9.16, and
`filelock`. This project does not bundle Hadge or Dreeve source code.
