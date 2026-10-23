import os
import sqlite3
import tempfile
from pathlib import Path


def atomic_write(path: Path, data: bytes):
    """Same-filesystem staging; Dreeve must never see partial .fit files."""
    fd, temporary = tempfile.mkstemp(prefix=".hadge-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        # Dreeve may run as another UID. Protect health data with directory permissions.
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        if os.name != "nt":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        Path(temporary).unlink(missing_ok=True)


class State:
    def __init__(self, directory, *, readonly=False):
        path = directory / "state.sqlite3"
        self.readonly = readonly
        if readonly and not path.exists():
            self.db = sqlite3.connect(":memory:")
            self._create()
        elif readonly:
            self.db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        else:
            directory.mkdir(parents=True, exist_ok=True)
            self.db = sqlite3.connect(path)
            self._create()
        self.db.row_factory = sqlite3.Row

    def _create(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS workouts (
                repo TEXT NOT NULL, uuid TEXT NOT NULL, fingerprint TEXT NOT NULL,
                filename TEXT NOT NULL, payload BLOB, status TEXT NOT NULL,
                PRIMARY KEY (repo, uuid));
            CREATE TABLE IF NOT EXISTS files (
                repo TEXT NOT NULL, path TEXT NOT NULL, sha TEXT NOT NULL,
                PRIMARY KEY (repo, path));
        """)

    def close(self):
        self.db.close()

    def get(self, repo, uuid):
        return self.db.execute("SELECT * FROM workouts WHERE repo=? AND uuid=?", (repo, uuid)).fetchone()

    def cached(self, repo, path, sha):
        row = self.db.execute("SELECT sha FROM files WHERE repo=? AND path=?", (repo, path)).fetchone()
        return row is not None and row["sha"] == sha

    def checkpoint(self, repo, path, sha):
        assert not self.readonly
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO files VALUES (?, ?, ?)", (repo, path, sha))

    def prepare(self, repo, workout, filename, payload):
        assert not self.readonly
        with self.db:
            self.db.execute("INSERT INTO workouts VALUES (?, ?, ?, ?, ?, 'pending')",
                            (repo, workout.uuid, workout.fingerprint(), filename, payload))

    def pending(self):
        return self.db.execute("SELECT * FROM workouts WHERE status='pending'").fetchall()

    def deliver(self, row, watch_dir):
        assert not self.readonly
        atomic_write(watch_dir / row["filename"], row["payload"])
        with self.db:
            self.db.execute("UPDATE workouts SET status='delivered', payload=NULL WHERE repo=? AND uuid=?",
                            (row["repo"], row["uuid"]))
