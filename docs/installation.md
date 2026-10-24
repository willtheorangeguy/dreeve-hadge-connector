# Installation

<!-- markdownlint-disable MD046 -->

Use the release Docker image for production. Install from source to develop the connector or run its CLI with Python.

## Requirements

| Path | Requirements |
| --- | --- |
| Release Docker | Docker with Compose v2, Linux amd64 or arm64 containers, outbound HTTPS to GitHub |
| Source | Python 3.12 or newer, Git, and a writable local watch directory |
| Destination | Dreeve v5.6.2 or newer with file import enabled and daemon running |
| Source data | Hadge exporting `workouts/YYYY.csv`, read-only repository token |
| Persistence | Separate watch and state locations; reliable local rename and SQLite locking semantics |

The unit suite runs on Windows and Linux with Python 3.12. The Docker image uses Python 3.12. Network filesystems are not supported for state.

## Install methods

=== "Release Docker"

    Download `docker-compose.yml` and `env.example` from [v0.1.0](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases/tag/v0.1.0). Rename `env.example` to `.env`, configure credentials and `DREEVE_WATCH_PATH`, then run:

    ```sh
    docker compose pull
    docker compose run --rm connector check
    docker compose up -d
    ```

    [Getting started](./getting-started.md) contains the full procedure. The release image is public; no registry login is required.

=== "Existing Dreeve stack"

    Download `docker-compose.dreeve.yml` from the same release beside your Dreeve Compose file. Append `GITHUB_REPOSITORY` and `GITHUB_TOKEN` to the existing `.env`. Set `DREEVE_WATCH_PATH` if your existing host watch directory differs from `./watch`.

    ```sh
    docker compose -f docker-compose.yml -f docker-compose.dreeve.yml pull hadge-connector
    docker compose -f docker-compose.yml -f docker-compose.dreeve.yml up -d
    ```

    Keep both `-f` arguments for later management. [Deployment](./deployment.md) also shows how to merge the service into one file.

=== "Source"

    ```sh
    git clone https://github.com/willtheorangeguy/dreeve-hadge-connector.git
    cd dreeve-hadge-connector
    uv venv --python 3.12
    uv pip install -e .
    uv run --no-project dreeve-hadge-connector --help
    ```

    The package is installed from this checkout. No PyPI release is assumed. Set process environment variables as described in [Configuration](./configuration.md); the Python CLI does not load `.env`. Set `WATCH_DIR` to your existing directory and `STATE_DIR` to a separate persistent directory, then run:

    ```sh
    uv run --no-project dreeve-hadge-connector check
    uv run --no-project dreeve-hadge-connector watch
    ```

=== "Local Docker build"

    Clone the source as above, copy `.env.example` to `.env`, and fill in your settings. Use the development overlay to replace the release image with a local build:

    ```sh
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
    ```

## Verify the installation

```sh
docker compose run --rm connector --help
```

The help lists the positional commands `{check,preview,sync,watch}`. Then run `docker compose run --rm connector check`; a valid configuration reports GitHub access and watch-folder accessibility. Only `sync` or `watch` exercises actual file delivery.

## Upgrading

Select a published release and download its matching setup files, or update `CONNECTOR_VERSION` in `.env`. For a merged stack, update the image tag if it is hardcoded.

```sh
docker compose pull
docker compose up -d
```

Keep the same Compose project and state volume to retain delivery history. Stable releases publish exact version, minor-version, and `latest` image tags. Prereleases publish only their exact version. Source installations upgrade by checking out the desired revision and rerunning the installation command.

## Uninstalling

For a standalone installation:

```sh
docker compose down
```

This removes the service and network while retaining the state volume and host watch folder. Do not add `--volumes` if you may reinstall. In a shared Dreeve stack, remove the connector service and its unused state-volume declaration without stopping or deleting Dreeve's data. Remove the token from the local environment file and revoke it if no longer needed. For a source install, `uv pip uninstall dreeve-hadge-connector` removes the package from the selected environment.
