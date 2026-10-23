import sqlite3
from dataclasses import replace
from datetime import UTC, datetime

import pytest
from filelock import FileLock

from dreeve_hadge_connector.state import State, atomic_write
from dreeve_hadge_connector.sync import run_sync

from .conftest import BASE, FakeGitHub, csv_bytes


def test_preview_is_read_only(config):
    before = sorted(config.watch_dir.parent.rglob("*"))
    result = run_sync(config, FakeGitHub(), preview=True)
    assert result.planned == 1
    assert result.delivered == 0
    assert sorted(config.watch_dir.parent.rglob("*")) == before


def test_sync_restart_and_consumed_output(config):
    api = FakeGitHub()
    assert run_sync(config, api).delivered == 1
    files = list(config.watch_dir.glob("*.fit"))
    assert len(files) == 1
    files[0].unlink()  # Dreeve consumes successfully imported files.
    assert run_sync(config, api).cached_files == 1
    assert not list(config.watch_dir.iterdir())
    assert len(api.reads) == 1


def test_backfill_filter_can_move_backwards(config):
    future = replace(config, since=datetime(2027, 1, 1, tzinfo=UTC))
    assert run_sync(future, FakeGitHub()).filtered == 1
    assert run_sync(config, FakeGitHub()).delivered == 1


def test_history_year_rollover_and_duplicate_uuid(config):
    old = BASE | {"UUID": "12345678-1234-4234-8234-123456789002",
                  "Start Date": "2025-12-31T23:45:00Z", "End Date": "2026-01-01T00:15:00Z"}
    api = FakeGitHub({"workouts/2025.csv": csv_bytes(old), "workouts/2026.csv": csv_bytes(BASE, old)})
    result = run_sync(config, api)
    assert result.delivered == 2
    assert result.skipped == 1


def test_preview_deduplicates(config):
    result = run_sync(config, FakeGitHub({"workouts/2026.csv": csv_bytes(BASE, BASE)}), preview=True)
    assert result.planned == 1
    assert result.skipped == 1


def test_changed_and_deleted_source_no_mutation(config, caplog):
    run_sync(config, FakeGitHub())
    output = next(config.watch_dir.iterdir())
    original = output.read_bytes()
    result = run_sync(config, FakeGitHub({"workouts/2026.csv": csv_bytes(BASE | {"Distance": "6000"})}))
    assert result.changed == 1
    assert "manual review" in caplog.text
    assert output.read_bytes() == original
    api = FakeGitHub()
    api.files = {}
    assert run_sync(config, api).delivered == 0
    assert output.read_bytes() == original


def test_rejections_retried_valid_rows_not_repeated(config):
    api = FakeGitHub({"workouts/2026.csv": csv_bytes(BASE, BASE | {"UUID": "bad"})})
    assert run_sync(config, api).rejected == 1
    result = run_sync(config, api)
    assert result.delivered == 0
    assert result.skipped == 1
    assert result.rejected == 1
    assert len(api.reads) == 2


def test_permission_failure_keeps_pending_and_recovers(config, monkeypatch):
    def fail(*_):
        raise PermissionError("synthetic denied write")
    with monkeypatch.context() as patch:
        patch.setattr("dreeve_hadge_connector.state.atomic_write", fail)
        with pytest.raises(PermissionError):
            run_sync(config, FakeGitHub())
    state = State(config.state_dir)
    assert len(state.pending()) == 1
    state.close()
    result = run_sync(config, FakeGitHub())
    assert result.delivered == 1
    assert len(list(config.watch_dir.glob("*.fit"))) == 1


def test_crash_after_publication_before_ack(config, monkeypatch):
    from dreeve_hadge_connector import state as state_module
    original = state_module.atomic_write

    def crash(path, data):
        original(path, data)
        raise OSError("synthetic crash after publish")

    with monkeypatch.context() as patch:
        patch.setattr(state_module, "atomic_write", crash)
        with pytest.raises(OSError):
            run_sync(config, FakeGitHub())
    first = next(config.watch_dir.glob("*.fit"))
    data = first.read_bytes()
    assert run_sync(config, FakeGitHub()).delivered == 1
    assert list(config.watch_dir.glob("*.fit")) == [first]
    assert first.read_bytes() == data


def test_same_filesystem_staging_and_no_partial_files(config, monkeypatch):
    import os
    replace_file = os.replace
    called = []

    def inspect(source, target):
        from pathlib import Path
        assert Path(source).parent == target.parent
        assert Path(source).suffix == ".tmp"
        assert not target.exists()
        called.append(True)
        replace_file(source, target)

    monkeypatch.setattr("dreeve_hadge_connector.state.os.replace", inspect)
    atomic_write(config.watch_dir / "test.fit", b"complete")
    assert called
    assert [p.name for p in config.watch_dir.iterdir()] == ["test.fit"]


def test_concurrent_sync_refused(config):
    config.state_dir.mkdir()
    with FileLock(config.state_dir / "sync.lock"):
        with pytest.raises(RuntimeError, match="Another sync"):
            run_sync(config, FakeGitHub())


def test_preview_existing_database_unchanged(config):
    run_sync(config, FakeGitHub())
    path = config.state_dir / "state.sqlite3"
    before = path.read_bytes()
    assert run_sync(config, FakeGitHub(), preview=True).cached_files == 1
    assert path.read_bytes() == before
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM workouts").fetchone()[0] == 1


def test_same_watch_and_state_rejected(config):
    with pytest.raises(ValueError, match="separate"):
        run_sync(replace(config, state_dir=config.watch_dir), FakeGitHub())
