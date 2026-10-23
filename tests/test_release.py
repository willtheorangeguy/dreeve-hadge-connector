import pytest

from scripts.release_assets import setup_assets
from scripts.release_metadata import release_metadata


def test_stable_release_metadata():
    assert release_metadata("v0.1.0", "Example/Connector", "0.1.0") == {
        "version": "0.1.0", "minor": "0.1", "image": "ghcr.io/example/connector", "stable": "true"}


def test_prerelease_does_not_move_stable_aliases():
    assert release_metadata("v0.2.0-rc.1", "example/connector", "0.2.0-rc.1", True)["stable"] == "false"


@pytest.mark.parametrize(("tag", "version", "prerelease"), [
    ("0.1.0", "0.1.0", False), ("v0.2.0", "0.1.0", False),
    ("v0.2.0-rc.1", "0.2.0-rc.1", False),
])
def test_invalid_release_cannot_publish(tag, version, prerelease):
    with pytest.raises(ValueError):
        release_metadata(tag, "example/connector", version, prerelease)


def test_setup_assets_match_published_image():
    assets = setup_assets("0.2.0", "ghcr.io/example/connector")
    assert set(assets) == {"docker-compose.yml", "docker-compose.dreeve.yml", "env.example"}
    for name in ("docker-compose.yml", "docker-compose.dreeve.yml"):
        assert "ghcr.io/example/connector:${CONNECTOR_VERSION:-0.2.0}" in assets[name]
        assert "build:" not in assets[name] and "secrets:" not in assets[name]
    assert "CONNECTOR_VERSION=0.2.0" in assets["env.example"]
    assert "GITHUB_TOKEN=replace-with-your-read-only-token" in assets["env.example"]
