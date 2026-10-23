import csv
import hashlib
import io
import json
import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import UUID

HEADERS = ["UUID", "Start Date", "End Date", "Type", "Name", "Duration", "Distance",
           "Elevation Ascended", "Flights Climbed", "Swim Strokes", "Total Energy"]
FIT_EPOCH = datetime(1989, 12, 31, tzinfo=UTC)
FIT_LAST = datetime.fromtimestamp(FIT_EPOCH.timestamp() + 0xFFFFFFFE, tz=UTC)


@dataclass(frozen=True)
class Workout:
    uuid: str
    start: datetime
    end: datetime
    type: int
    name: str
    duration: float
    distance: float | None
    ascent: float | None
    flights: float | None
    strokes: float | None
    calories: float | None

    def fingerprint(self):
        return hashlib.sha256(json.dumps(asdict(self), default=str, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Rejection:
    row: int
    reason: str


def _date(value):
    try:
        result = datetime.fromisoformat(value)
        if result.utcoffset() is None:
            raise ValueError
        result = result.astimezone(UTC)
        if not FIT_EPOCH <= result <= FIT_LAST:
            raise ValueError
        return result
    except (ValueError, OverflowError):
        raise ValueError("invalid or out-of-range timestamp (explicit offset required)") from None


def _number(row, key, maximum, required=False):
    raw = row[key].strip()
    if not raw and not required:
        return None
    try:
        value = float(raw)
    except ValueError:
        raise ValueError(f"{key}: expected a number") from None
    if not math.isfinite(value) or not 0 <= value <= maximum:
        raise ValueError(f"{key}: outside supported range")
    return value


def parse_csv(content: bytes):
    """Return valid rows and an audit; never include raw health values in errors."""
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
        if reader.fieldnames is None or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("missing or duplicate CSV headers")
        if not set(HEADERS).issubset(reader.fieldnames):
            raise ValueError("CSV does not have the Hadge workout headers")
        workouts, rejected = [], []
        for row in reader:
            number = reader.line_num
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("wrong number of CSV columns")
                try:
                    uuid = str(UUID(row["UUID"]))
                except ValueError:
                    raise ValueError("invalid workout UUID") from None
                start, end = _date(row["Start Date"]), _date(row["End Date"])
                duration = _number(row, "Duration", 4294967.294, required=True)
                elapsed = (end - start).total_seconds()
                if elapsed <= 0 or duration <= 0 or duration > elapsed + 0.001:
                    raise ValueError("inconsistent start, end, or duration")
                if elapsed > 4294967.294:
                    raise ValueError("elapsed time exceeds FIT range")
                try:
                    kind = int(row["Type"])
                    if kind < 0:
                        raise ValueError
                except ValueError:
                    raise ValueError("invalid HealthKit activity type") from None
                name = row["Name"].strip()
                if not name or len(name.encode("utf-8")) > 200:
                    raise ValueError("workout name must be 1–200 UTF-8 bytes")
                workouts.append((number, Workout(
                    uuid, start, end, kind, name, min(duration, elapsed),
                    _number(row, "Distance", 42949672.94),
                    _number(row, "Elevation Ascended", 65534),
                    _number(row, "Flights Climbed", 4294967294),
                    _number(row, "Swim Strokes", 4294967294),
                    _number(row, "Total Energy", 65534),
                )))
            except ValueError as exc:
                rejected.append(Rejection(number, str(exc)))
        return workouts, rejected
    except (UnicodeError, csv.Error):
        raise ValueError("invalid UTF-8 or malformed CSV quoting") from None
