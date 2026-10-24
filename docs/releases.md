# Releases

A published GitHub release triggers validation, tests, GHCR image publication, and version-matched setup-file attachments. No registry or release secret beyond the workflow's repository-scoped `GITHUB_TOKEN` is required.

## Prepare a version

Update `project.version` in `pyproject.toml` and the setup defaults in `.env.example`, `docker-compose.yml`, and `docker-compose.dreeve.yml`. Update pinned installation examples and the changelog for the selected release. Keep the version in the HTTP User-Agent under review when changing package versions. Commit the intended source revision before tagging.

The current release is `0.1.0`. Its matching tag is `v0.1.0`. `scripts/release_metadata.py` rejects invalid or mismatched release metadata before any image can publish.

Run release-tool tests with the rest of the unit suite:

```sh
uv run --no-project python -m pytest tests/test_release.py -q
```

Create the matching `vX.Y.Z` GitHub release using your normal release process. Publishing the release, rather than merely pushing a tag, triggers the workflow. Prerelease metadata and tag syntax must agree with the validation script.

## Publication sequence

1. Validate release tag, package version, prerelease status, and target image name.
2. Run the reusable Windows/Linux unit checks and full Dreeve acceptance test.
3. Build Linux amd64 and arm64 images with Docker Buildx/QEMU.
4. Publish to `ghcr.io/willtheorangeguy/dreeve-hadge-connector` with provenance and a software bill of materials (SBOM).
5. Run `scripts/release_assets.py` and upload setup files to the release after image publication.

Stable versions publish the exact version, a minor alias such as `0.1`, and `latest`. Prereleases publish the exact version without advancing stable aliases. The workflow records the published image digest in its run summary.

## Release assets

| Asset | Use |
| --- | --- |
| `docker-compose.yml` | Standalone two-file installation |
| `env.example` | Rename to `.env` and fill in local credentials/path |
| `docker-compose.dreeve.yml` | Overlay for an existing Dreeve stack |

The asset generator substitutes the published version/image into setup defaults. End users do not need a source checkout or local image build. Inspect the [release history](https://github.com/willtheorangeguy/dreeve-hadge-connector/releases) and Actions evidence before selecting a version.

## Upgrade an installation

Set `CONNECTOR_VERSION` to the desired published version or obtain that release's setup files, then:

```sh
docker compose pull
docker compose up -d
```

Retain state and review [Recovery](./recovery.md) before changing a Compose project or deployment method. There is no documented general database-downgrade procedure; do not assume that switching to an older image can read future state formats.
