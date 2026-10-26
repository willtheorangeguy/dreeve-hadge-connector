# Development

<!-- markdownlint-disable MD046 -- Material tabs contain indented fenced blocks. -->

Use Python 3.12 to match CI and the production image. The package uses a `src/` layout and Hatchling for builds.

## Set up

```sh
git clone https://github.com/willtheorangeguy/dreeve-hadge-connector.git
cd dreeve-hadge-connector
uv venv --python 3.12
uv pip install -e '.[dev]'
uv run --no-project dreeve-hadge-connector --help
```

The development extra installs pytest, Ruff, and the independent `fitdecode` decoder. Runtime dependencies are `requests`, `fit-tool==0.9.16`, and `filelock`. Supported Python versions start at 3.12; CI currently exercises 3.12 on Windows and Linux.

## Run checks

```sh
uv run --no-project python -m pytest -q
uv run --no-project ruff check .
```

Ruff targets Python 3.12, a 110-character line limit, and the E, F, I, UP, and B rule families. The unit suite uses synthetic data and does not need real GitHub credentials or Dreeve. See [Testing](./testing.md) for focused suites and Docker acceptance tests.

## Build a development container

Copy `.env.example` to `.env` and configure it for a controlled destination. Building the image alone does not need credentials:

```sh
docker build -t dreeve-hadge-connector:dev .
```

To run with the normal configuration through the development overlay:

```sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

This executes real synchronization against the configured repository. Use the isolated test harness for synthetic end-to-end checks.

## Change the implementation

Follow the boundaries in [Architecture](./architecture.md). Parser errors should identify file/row/reason without exposing raw health values. Keep preview read-only, preserve stable workout identity, and retain the pending-before-publication ordering. A sport mapping change must match Dreeve's resolver and have decoder coverage.

When changing behavior, update the relevant docs page and root changelog. Consult [Releases](./releases.md) before changing version defaults or setup assets. The docs site includes the root changelog by reference.

## Build the documentation

The site inherits the shared Material theme, extensions, macros, and validation from [willtheorangeguy/mkdocs](https://github.com/willtheorangeguy/mkdocs). The shared checkout and staged assets are ignored build inputs. Use the checked-in helper from the project root:

=== "Windows"

    ```powershell
    .\scripts\docs-serve.ps1 -Build
    .\scripts\docs-serve.ps1
    ```

=== "macOS / Linux"

    ```bash
    bash scripts/docs-serve.sh --build
    bash scripts/docs-serve.sh
    ```

Activate your Python virtual environment first so the helper finds its documentation tools. It clones/updates `.mkdocs-shared`, stages the design system, and installs shared dependencies if `mkdocs` is absent. For an existing toolchain after shared requirements change, reinstall them explicitly:

```sh
uv pip install -r .mkdocs-shared/shared/requirements-docs.txt
uv run --no-project mkdocs build --strict
```

The default preview port is 8000. Read `docs/docs.instructions.md` before writing prose. Do not redeclare `plugins` or `markdown_extensions` in the project `mkdocs.yml`: lists replace the inherited settings. All authored site pages belong in the nav; `internal/` and the writing standard are excluded.

### Check a documentation change

Run the strict build above and the shared Markdown rules before submitting documentation changes. The Markdown check requires Node.js and npm:

```sh
npx --yes markdownlint-cli2 --config .mkdocs-shared/shared/lint/.markdownlint.jsonc "docs/**/*.md"
```

Keep the following sources aligned when behavior changes:

| Change | Documentation to review |
| --- | --- |
| Environment setting or default | [Configuration](./configuration.md), `.env.example`, and Compose definitions |
| CLI command, exit code, or counter | [CLI reference](./api.md), [Usage](./usage.md), and [Troubleshooting](./troubleshooting.md) |
| CSV validation or FIT output | [Data reference](./data.md) and [Limitations](./roadmap.md) |
| Delivery, persistence, or replay | [Architecture](./architecture.md) and [Recovery](./recovery.md) |
| Release version or workflow | [Releases](./releases.md), [CI/CD](./ci-cd.md), and pinned installation examples |

Add each new public page to `mkdocs.yml` and update inbound links when renaming a page. Keep changelog and license pages as includes of the root files. The pull-request workflow also checks external links; a local strict build checks internal documentation targets but does not request external URLs.

## Contribution policy

Follow the account-wide [Contributing guide](https://github.com/willtheorangeguy/.github/blob/main/CONTRIBUTING.md) and [Code of conduct](https://github.com/willtheorangeguy/.github/blob/main/CODE_OF_CONDUCT.md). Report sensitive issues using the [Security policy](https://github.com/willtheorangeguy/.github/blob/main/SECURITY.md). Keep credentials, health exports, state databases, and local artifacts out of commits.
