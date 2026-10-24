# CI/CD

The repository runs code checks, full Dreeve acceptance tests, release publication, and documentation workflows. The docs workflows call the shared MkDocs repository rather than copying its build logic.

## Tests

`.github/workflows/test.yml` runs on pushes, pull requests, and reusable-workflow calls. Its unit job runs Python 3.12 on Ubuntu and Windows, installs `.[dev]`, executes pytest, and runs Ruff. Its Ubuntu Dreeve job pulls v5.6.2, runs the complete acceptance harness, and always attempts to upload `integration-artifacts/` as `full-workflow-evidence`. The acceptance job has a 20-minute timeout.

Run the same unit checks locally:

```sh
uv run --no-project python -m pytest -q
uv run --no-project ruff check .
```

## Release publication

`.github/workflows/release.yml` responds to a published GitHub release. It validates tag/package metadata, calls the test workflow, then builds and publishes the image. Setup assets upload only after the image publication succeeds. See [Releases](./releases.md) for prerequisites and artifacts.

The workflow grants package write access only to image publication and content write access only to release-asset upload. The repository-scoped `GITHUB_TOKEN` supplies publication credentials. Concurrent releases queue rather than cancelling an in-progress publication.

## Documentation deployment

`.github/workflows/docs.yml` runs on relevant pushes to `main`/`master` or manual dispatch. It grants `contents: read`, `pages: write`, and `id-token: write`, then calls `willtheorangeguy/mkdocs/.github/workflows/docs-build.yml@main`.

The shared workflow checks out full project history and the shared configuration, installs the shared requirements, stages design assets, builds strictly, uploads a Pages artifact, and deploys it through the `github-pages` environment. There is one Pages deployment workflow and docs own the repository's Pages root.

Trigger and inspect a documentation build with GitHub CLI:

```sh
gh workflow run docs.yml
gh run list --workflow docs.yml --limit 5
```

The canonical site is [the documentation site](https://williamvdg.me/dreeve-hadge-connector/). Pages must use the **GitHub Actions** source; pushing workflows alone does not enable it.

## Documentation checks

`.github/workflows/docs-lint.yml` runs on relevant pull requests or manual dispatch. It calls the shared lint workflow for Markdown style, a strict site build, and external link checks. Root `CHANGELOG.md` and `LICENSE` changes trigger docs checks because snippet pages include them. The writing standard stays in the repository but is excluded from the rendered site.

```sh
gh workflow run docs-lint.yml
gh run list --workflow docs-lint.yml --limit 5
```

Local `mkdocs build --strict` validates authored links, anchors, snippet paths, macros, and configuration warnings. It does not replace the external HTTP link check or prove a successful Pages deployment.
