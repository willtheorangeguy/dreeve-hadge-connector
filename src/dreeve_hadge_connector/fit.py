from fit_tool import FitFileBuilder
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_tool.profile.profile_type import Activity, FileType, Manufacturer

from .workout import Workout

# HealthKit raw activity values -> FIT sport/sub-sport, restricted to Dreeve's resolver.
# Hadge does not export indoor/outdoor or pool/open-water metadata; do not infer it.
SPORTS = {
    1: (0, 0), 2: (0, 0), 3: (0, 0),
    4: (64, 95), 6: (6, 0), 8: (47, 0), 9: (31, 0), 10: (71, 0),
    13: (2, 0), 14: (83, 0), 15: (83, 0), 16: (4, 15),
    20: (10, 20), 21: (25, 0), 24: (17, 0), 31: (19, 0),
    34: (64, 96), 35: (15, 0), 37: (1, 0), 38: (32, 0),
    41: (7, 0), 43: (64, 94), 44: (4, 16), 45: (38, 0),
    46: (5, 0), 47: (64, 97), 48: (8, 0), 50: (10, 20),
    51: (75, 0), 52: (11, 0), 57: (10, 43), 60: (12, 0),
    61: (13, 0), 63: (62, 70), 65: (47, 0), 66: (10, 44),
    67: (14, 0), 68: (4, 16), 70: (65, 0), 71: (66, 0), 74: (2, 12),
}


def build_fit(workout: Workout, repository: str) -> bytes:
    sport, sub_sport = SPORTS.get(workout.type, (4, 0))
    # Unmapped sports use the stable fitness-equipment -> Workout fallback.
    if sport == 0:
        sport = 4
    start = round(workout.start.timestamp() * 1000)
    end = round(workout.end.timestamp() * 1000)
    builder = FitFileBuilder(auto_define=True)
    file_id = FileIdMessage()
    file_id.type = FileType.ACTIVITY
    file_id.manufacturer = Manufacturer.DEVELOPMENT
    file_id.product = 0
    file_id.time_created = start
    builder.add(file_id)

    details = WorkoutMessage()
    details.workout_name = workout.name
    details.sport = sport
    details.num_valid_steps = 0
    description = (
        f"Apple Health via Hadge; UUID {workout.uuid}; "
        f"HealthKit type {workout.type}; summary only. "
        f"Flights climbed: {workout.flights}; swim strokes: {workout.strokes}; source {repository}."
    )
    details.workout_description = description.encode("utf-8")[:254].decode("utf-8", errors="ignore")
    builder.add(details)

    lap = LapMessage()
    session = SessionMessage()
    for message in (lap, session):
        message.message_index = 0
        message.timestamp = end
        message.start_time = start
        message.total_elapsed_time = (workout.end - workout.start).total_seconds()
        message.total_timer_time = workout.duration
        message.sport = sport
        message.sub_sport = sub_sport
        if workout.distance is not None:
            message.total_distance = workout.distance
        if workout.ascent is not None:
            message.total_ascent = round(workout.ascent)
        if workout.calories is not None:
            message.total_calories = round(workout.calories)
    builder.add(lap)
    session.first_lap_index = 0
    session.num_laps = 1
    builder.add(session)
    activity = ActivityMessage()
    activity.timestamp = end
    activity.total_timer_time = workout.duration
    activity.num_sessions = 1
    activity.type = Activity.MANUAL
    builder.add(activity)
    return builder.build().to_bytes()
