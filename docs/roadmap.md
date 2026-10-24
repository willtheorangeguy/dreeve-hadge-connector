# Limitations

These are current boundaries established by the implementation and README, not a promised release schedule. No dated future roadmap is recorded in the repository.

## Summary-only input

Hadge's workout CSVs do not contain GPS routes, heart-rate/power samples, indoor/outdoor flags, or pool/open-water flags. The connector cannot reconstruct those values. Daily rings and step totals are not imported. FIT fields round to supported precision, and the provenance description is limited to 254 UTF-8 bytes.

## Delivery and reconciliation

Delivery is at least once. There is no transaction with Dreeve and no confirmation that a delivered file became an activity. The first delivered UUID version wins. Source updates require manual review and source deletions do not propagate. One instance serves one configured repository/destination pair.

For example, changing the source row for a known UUID increments `changed`; it does not publish an updated FIT file. [Recovery](./recovery.md) describes the supported response.

## Compatibility and storage

Dreeve versions before v5.6.2 cannot import these sessions without sample records. GitHub Enterprise is not supported in v1. State needs a local filesystem with reliable SQLite locking and rename behavior; network filesystems are unsupported. Published images target Linux amd64 and arm64.

## Input limits

The client rejects workout-directory listings with 1,000 or more entries and responses exceeding 100 MiB. It does not paginate the workout listing. The parser enforces FIT timestamp and metric bounds. See [Data reference](./data.md) and [Troubleshooting](./troubleshooting.md).

## Proposing changes

Use the [issue tracker](https://github.com/willtheorangeguy/dreeve-hadge-connector/issues) to discuss a boundary that affects your deployment. Include synthetic examples and the expected result rather than private workout exports.
