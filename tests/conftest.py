import csv
import io
from dataclasses import replace

import pytest

from dreeve_hadge_connector.config import Config
from dreeve_hadge_connector.github import Snapshot, SourceFile
from dreeve_hadge_connector.workout import HEADERS

BASE = {
    "UUID": "12345678-1234-4234-8234-123456789001",
    "Start Date": "2026-10-23T12:00:00-06:00",
    "End Date": "2026-10-23T12:30:00-06:00",
    "Type": "37", "Name": "Running", "Duration": "1700.500",
    "Distance": "5000.25", "Elevation Ascended": "40.00",
    "Flights Climbed": "2", "Swim Strokes": "0", "Total Energy": "300.25",
}


def csv_bytes(*rows):
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=HEADERS)
    writer.writeheader()
    writer.writerows(rows or [BASE])
    return output.getvalue().encode()


class FakeGitHub:
    def __init__(self, files=None):
        self.files = files or {"workouts/2026.csv": csv_bytes()}
        self.reads = []

    def snapshot(self):
        import hashlib
        return Snapshot("12345", "a" * 40, tuple(
            SourceFile(path, hashlib.sha1(data).hexdigest()) for path, data in self.files.items()))

    def read(self, source, commit):
        assert commit == "a" * 40
        self.reads.append(source.path)
        return self.files[source.path]


@pytest.fixture
def config(tmp_path):
    watch = tmp_path / "watch"
    watch.mkdir()
    token = tmp_path / "token.txt"
    token.write_text("fake-test-token")
    return Config("example/health", token, watch, tmp_path / "state")


@pytest.fixture
def workout():
    from dreeve_hadge_connector.workout import parse_csv
    return parse_csv(csv_bytes())[0][0][1]


@pytest.fixture
def varied():
    return replace
