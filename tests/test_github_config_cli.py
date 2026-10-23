import logging
from dataclasses import replace
from unittest.mock import Mock

import pytest
import requests

from dreeve_hadge_connector import cli
from dreeve_hadge_connector.config import Config
from dreeve_hadge_connector.github import GitHub, RemoteError

from .conftest import FakeGitHub


def response(status=200, data=None, content=b"csv", headers=None):
    result = Mock(status_code=status, content=content, headers=headers or {})
    result.json.return_value = data
    return result


def test_commit_snapshot_and_large_raw_file(config):
    client = GitHub(config)
    client.session.get = Mock(side_effect=[
        response(data={"id": 1, "default_branch": "main"}),
        response(data={"sha": "commit"}),
        response(data=[{"path": "workouts/2026.csv", "sha": "blob", "type": "file"},
                       {"path": "workouts/not-workouts.txt", "type": "file"}]),
        response(content=b"x" * (1024 * 1024 + 1)),
    ])
    snapshot = client.snapshot()
    assert len(snapshot.files) == 1
    assert len(client.read(snapshot.files[0], snapshot.commit)) > 1024 * 1024
    calls = client.session.get.call_args_list
    assert calls[2].kwargs["params"] == {"ref": "commit"}
    assert calls[3].kwargs["params"] == {"ref": "commit"}
    assert calls[3].kwargs["headers"]["Accept"] == "application/vnd.github.raw+json"
    assert calls[3].kwargs["allow_redirects"] is False
    client.close()


@pytest.mark.parametrize(("status", "message"), [(401, "expired"), (403, "denied"), (404, "not found")])
def test_api_auth_errors_sanitized(config, status, message):
    client = GitHub(config)
    client.session.get = Mock(return_value=response(status, content=b"private-health-and-token"))
    with pytest.raises(RemoteError, match=message) as caught:
        client.snapshot()
    assert "private-health-and-token" not in str(caught.value)
    assert "fake-test-token" not in str(caught.value)
    client.close()


@pytest.mark.parametrize("status", [403, 429])
def test_rate_limit_delays_next_cycle(config, status):
    client = GitHub(config)
    client.session.get = Mock(return_value=response(status, headers={"Retry-After": "600"}))
    with pytest.raises(RemoteError) as caught:
        client.snapshot()
    assert caught.value.retry_after >= 600
    assert client.session.get.call_count == 1
    client.close()


@pytest.mark.parametrize("failure", [response(503), requests.Timeout("private-url")])
def test_bounded_network_retries(config, monkeypatch, failure):
    sleeps = Mock()
    monkeypatch.setattr("dreeve_hadge_connector.github.time.sleep", sleeps)
    client = GitHub(config)
    if isinstance(failure, Exception):
        client.session.get = Mock(side_effect=failure)
    else:
        client.session.get = Mock(return_value=failure)
    with pytest.raises(RemoteError):
        client.snapshot()
    assert client.session.get.call_count == 4
    assert [call.args[0] for call in sleeps.call_args_list] == [1, 2, 4]
    client.close()


def test_config_defaults_and_date(config, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "Example/Health")
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(config.token_file))
    monkeypatch.setenv("EXPORT_SINCE", "2026-01-01")
    parsed = Config.from_env()
    assert parsed.repository == "example/health"
    assert parsed.interval == 300
    assert parsed.github_api_url == "https://api.github.com"
    assert parsed.since.isoformat() == "2026-01-01T00:00:00+00:00"


@pytest.mark.parametrize(("key", "value"), [
    ("GITHUB_REPOSITORY", "../bad/repo"), ("EXPORT_SINCE", "2026-1-1"),
    ("SYNC_INTERVAL_SECONDS", "0"), ("GITHUB_TOKEN_FILE", ""),
])
def test_bad_config(config, monkeypatch, key, value):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/health")
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(config.token_file))
    monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        Config.from_env()


def test_environment_token_needs_no_file(config, monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/health")
    monkeypatch.delenv("GITHUB_TOKEN_FILE", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-env-token")
    parsed = Config.from_env()
    assert parsed.token_file is None
    assert parsed.token() == "synthetic-env-token"
    assert "synthetic-env-token" not in repr(parsed)
    client = GitHub(parsed)
    assert client.session.headers["Authorization"] == "Bearer synthetic-env-token"
    client.close()


def test_token_file_takes_precedence(config, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ignored-env-token")
    assert config.token() == "fake-test-token"


@pytest.mark.parametrize("value", ["", "two tokens"])
def test_bad_environment_token(config, monkeypatch, value):
    monkeypatch.setenv("GITHUB_TOKEN", value)
    with pytest.raises(ValueError, match="GITHUB_TOKEN") as error:
        replace(config, token_file=None).token()
    assert "two tokens" not in str(error.value)


@pytest.mark.parametrize("value", ["file:///tmp/mock", "https://user:secret@example.test",
                                  "http://", "https://example.test?token=secret"])
def test_invalid_api_base(config, monkeypatch, value):
    monkeypatch.setenv("GITHUB_REPOSITORY", "example/health")
    monkeypatch.setenv("GITHUB_TOKEN_FILE", str(config.token_file))
    monkeypatch.setenv("GITHUB_API_URL", value)
    with pytest.raises(ValueError, match="GITHUB_API_URL"):
        Config.from_env()


def test_custom_github_endpoint_uses_real_http_client(config):
    client = GitHub(replace(config, github_api_url="http://github:8000"))
    client.session.get = Mock(return_value=response(data={"id": 12345}))
    client._get("")
    assert client.session.get.call_args.args[0] == "http://github:8000/repos/example/health"
    assert client.session.headers["Authorization"] == "Bearer fake-test-token"
    client.close()


def test_cli_preview_and_sync(config, monkeypatch, caplog):
    monkeypatch.setattr(Config, "from_env", lambda: config)
    monkeypatch.setattr(cli, "GitHub", lambda _: FakeClient())
    monkeypatch.setattr("sys.argv", ["connector", "preview"])
    assert cli.main() == 0
    assert not config.state_dir.exists()
    monkeypatch.setattr("sys.argv", ["connector", "sync"])
    assert cli.main() == 0
    assert len(list(config.watch_dir.glob("*.fit"))) == 1


def test_cli_progress_visible_with_dependency_logging_handler(config, monkeypatch, caplog):
    monkeypatch.setattr(Config, "from_env", lambda: config)
    monkeypatch.setattr(cli, "GitHub", lambda _: FakeClient())
    monkeypatch.setattr("sys.argv", ["connector", "preview"])
    root = logging.getLogger()
    previous = root.level
    try:
        # Reproduce a dependency configuring logging before CLI startup.
        root.setLevel(logging.WARNING)
        assert cli.main() == 0
        assert "planned=1" in caplog.text
    finally:
        root.setLevel(previous)


def test_watch_rate_limit_recovery_and_token_rotation(config, monkeypatch):
    tokens, delays = [], []

    class StopAfterTwoCycles:
        stopped = False

        def is_set(self):
            return self.stopped

        def set(self):
            self.stopped = True

        def wait(self, delay):
            delays.append(delay)
            config.token_file.write_text("rotated-test-token")
            if len(delays) == 2:
                self.set()

    class OnceLimited(FakeClient):
        def snapshot(self):
            if len(tokens) == 1:
                raise RemoteError("rate limited", retry_after=600)
            return super().snapshot()

    def client_factory(parsed):
        tokens.append(parsed.token())
        return OnceLimited()

    monkeypatch.setattr(Config, "from_env", lambda: config)
    monkeypatch.setattr(cli.threading, "Event", StopAfterTwoCycles)
    monkeypatch.setattr(cli, "GitHub", client_factory)
    monkeypatch.setattr("sys.argv", ["connector", "watch"])
    assert cli.main() == 0
    assert delays == [600, 300]
    assert tokens == ["fake-test-token", "rotated-test-token"]
    assert len(list(config.watch_dir.glob("*.fit"))) == 1


class FakeClient(FakeGitHub):
    def close(self):
        pass
