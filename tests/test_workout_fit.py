import io
from dataclasses import replace
from datetime import UTC

import fitdecode
import pytest

from dreeve_hadge_connector.fit import build_fit
from dreeve_hadge_connector.workout import parse_csv

from .conftest import BASE, csv_bytes


def decode(data):
    with fitdecode.FitReader(io.BytesIO(data), check_crc=fitdecode.CrcCheck.RAISE) as reader:
        return [frame for frame in reader if isinstance(frame, fitdecode.FitDataMessage)]


def test_summary_independent_decoder(workout):
    data = build_fit(workout, "example/health")
    assert data == build_fit(workout, "example/health")
    frames = decode(data)
    assert not any(frame.name == "record" for frame in frames)
    session = next(frame for frame in frames if frame.name == "session")
    assert session.get_value("start_time") == workout.start
    assert session.get_value("total_timer_time") == 1700.5
    assert session.get_value("total_elapsed_time") == 1800
    assert session.get_value("total_distance") == 5000.25
    assert session.get_value("total_ascent") == 40
    assert session.get_value("total_calories") == 300
    details = next(frame for frame in frames if frame.name == "workout")
    assert details.get_value("wkt_name") == "Running"
    assert workout.uuid in details.get_value("wkt_description")


@pytest.mark.parametrize(("kind", "sport", "sub"), [
    (37, "running", "generic"), (13, "cycling", "generic"),
    (50, "training", "strength_training"), (99999, "fitness_equipment", "generic"),
    (57, "training", "yoga"), (66, "training", "pilates"),
])
def test_sports(workout, kind, sport, sub):
    session = next(f for f in decode(build_fit(replace(workout, type=kind), "x/y"))
                   if f.name == "session")
    assert session.get_value("sport") == sport
    assert session.get_value("sub_sport") == sub


def test_empty_metrics_and_unicode(workout):
    workout = replace(workout, name="Course à pied 🏃", distance=None, ascent=None, calories=None)
    session = next(f for f in decode(build_fit(workout, "x/y")) if f.name == "session")
    assert not session.has_field("total_distance")
    assert not session.has_field("total_calories")


@pytest.mark.parametrize(("key", "value"), [
    ("UUID", "bad"), ("Start Date", "2026-10-23T12:00:00"),
    ("End Date", "2026-10-23T11:00:00-06:00"), ("Duration", "1801"),
    ("Duration", "0"), ("Distance", "nan"), ("Distance", "-1"),
    ("Total Energy", "inf"), ("Type", "1.5"), ("Elevation Ascended", "65535"),
    ("Name", ""), ("Start Date", "1980-01-01T00:00:00Z"),
])
def test_invalid_rows_audited_without_raw_values(key, value):
    valid, errors = parse_csv(csv_bytes(BASE | {key: value}, BASE))
    assert len(valid) == 1
    assert len(errors) == 1
    assert errors[0].row == 2


def test_bom_optional_fields():
    rows, errors = parse_csv(b"\xef\xbb\xbf" + csv_bytes(BASE | {"Distance": "", "Total Energy": ""}))
    assert not errors
    assert rows[0][1].distance is None
    assert rows[0][1].start.tzinfo == UTC


def test_dst_transition():
    rows, errors = parse_csv(csv_bytes(BASE | {
        "Start Date": "2026-11-01T01:45:00-06:00",
        "End Date": "2026-11-01T01:15:00-07:00", "Duration": "1700",
    }))
    assert not errors
    assert (rows[0][1].end - rows[0][1].start).total_seconds() == 1800


@pytest.mark.parametrize("data", [b"bad,headers\n1,2\n", b"\xff", b'UUID,UUID\na,b\n'])
def test_bad_file(data):
    with pytest.raises(ValueError):
        parse_csv(data)
