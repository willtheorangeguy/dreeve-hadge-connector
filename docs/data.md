# Data reference

The connector reads only files whose paths match `workouts/YYYY.csv`. Daily activity rings and daily step totals are outside its input contract. Each cycle reads file listings and contents from one immutable GitHub commit.

## CSV fields

Headers are case-sensitive. Every header below must exist, even when an optional metric is blank. Additional unique headers are allowed. Input must be UTF-8, with an optional byte-order mark. Blank optional metrics remain absent; numeric zero remains zero.

| Header | Required value | Units and validation |
| --- | --- | --- |
| `UUID` | Yes | UUID normalized to canonical form |
| `Start Date` | Yes | ISO timestamp with explicit UTC offset, within FIT timestamp range |
| `End Date` | Yes | Same timestamp rules; strictly after start |
| `Type` | Yes | Nonnegative integer HealthKit activity code |
| `Name` | Yes | Trimmed text, 1–200 UTF-8 bytes |
| `Duration` | Yes | Positive seconds, at most `4294967.294`, no more than elapsed time plus 0.001 seconds |
| `Distance` | No | Meters, from 0 through `42949672.94` |
| `Elevation Ascended` | No | Meters, from 0 through `65534` |
| `Flights Climbed` | No | Count, from 0 through `4294967294` |
| `Swim Strokes` | No | Count, from 0 through `4294967294` |
| `Total Energy` | No | Kilocalories, from 0 through `65534` |

All numeric values must be finite. Elapsed time must fit the same maximum as duration. The accepted timestamp range starts at 1989-12-31 UTC and ends at that epoch plus `0xFFFFFFFE` seconds. A duration within the 0.001 second tolerance is clamped to elapsed time.

This synthetic row comes from the unit-test fixture:

```csv title="workouts/2026.csv"
UUID,Start Date,End Date,Type,Name,Duration,Distance,Elevation Ascended,Flights Climbed,Swim Strokes,Total Energy
12345678-1234-4234-8234-123456789001,2026-10-23T12:00:00-06:00,2026-10-23T12:30:00-06:00,37,Running,1700.500,5000.25,40.00,2,0,300.25
```

Malformed CSV quoting, invalid UTF-8, missing or duplicate headers fail the whole file. Invalid individual rows are logged by file, CSV line number, and reason. Valid rows still proceed. A rejected file is not checkpointed and is retried next cycle.

## FIT output

Each new workout becomes one activity FIT file containing file identification, workout details, a lap, a session, and an activity summary. There are no sample records or invented device identities.

| Source | FIT behavior |
| --- | --- |
| Name | Workout name |
| Start/end | UTC instants encoded at FIT precision |
| Duration | Timer time |
| End minus start | Elapsed time |
| Distance | Total distance, retaining field precision |
| Ascent/calories | Rounded to supported integer precision |
| Type | Supported FIT sport/sub-sport mapping |
| UUID, type, repository, flights, strokes | Provenance description, truncated to 254 UTF-8 bytes |

Long descriptions can truncate trailing provenance or metric text. The description identifies the data as summary only. Hadge itself often exports zero for an unavailable metric, so zero is not proof that the source measured that value.

## Sport mapping

The mapping in `src/dreeve_hadge_connector/fit.py` is restricted to sports Dreeve resolves. Tested examples include running (HealthKit 37), cycling (13), walking (52), swimming (46), strength (50), yoga (57), and Pilates (66). Unmatched types fall back to Workout and retain the original name and type in the details.

Hadge does not export indoor/outdoor or pool/open-water metadata. The connector does not infer them. Dreeve labels generic swimming as Pool Swim.

## Identity and changes

The database key is GitHub's stable repository ID plus HealthKit UUID. Output names follow `hadge-{namespace}-{uuid}.fit`, where `namespace` is the first 16 hexadecimal characters of SHA-256 of the repository ID. CSV year and row order do not affect identity.

The fingerprint hashes normalized parsed workout fields. The first delivered version wins. Edits to a seen UUID generate warnings and do not replace the activity. Source deletion does not delete a Dreeve activity. See [Recovery](./recovery.md) for correction and replay behavior.
