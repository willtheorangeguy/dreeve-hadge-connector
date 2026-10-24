# FAQ

???+ question "Does delivered mean the activity is imported?"
    No. It means a complete FIT file reached the watch folder. Dreeve imports separately. Check `/admin/file-imports` for the result. Default connector and importer schedules can add roughly ten minutes after Hadge publishes; iOS scheduling can add more.

??? question "Why does the connector need its own state volume?"
    Dreeve consumes watch files, so that directory cannot tell the connector what was previously delivered. SQLite retains repository-ID/UUID identity and pending payloads across restarts. Losing it causes historical redelivery.

??? question "Can I import GPS, heart rate, power, daily rings, or step totals?"
    Hadge's workout CSVs contain summaries, not GPS routes or sensor samples. The connector creates no sample records or device identity. It does not read daily rings or daily step exports.

??? question "Why does swimming appear as Pool Swim?"
    Hadge does not export pool/open-water metadata. The connector emits generic swimming, which Dreeve labels Pool Swim. Indoor/outdoor classification is also unavailable.

??? question "Will editing or deleting a workout change Dreeve?"
    The first delivered version wins. A different fingerprint for a seen UUID produces a manual-review warning. Deleting the source does not delete a Dreeve activity. Correct existing activities in Dreeve.

??? question "Can I run multiple users through one instance?"
    Configure one instance per user's repository and destination, with separate state and the correct watch folder. Do not share state across different Dreeve installations.

??? question "Do I need Python, a GHCR login, or Dreeve API credentials?"
    The release Docker path needs none of those. The public image includes Python and dependencies. The connector needs a GitHub token and filesystem access to the watch directory, with no inbound port.

??? question "Does the Python CLI read my .env file?"
    No. Compose reads `.env` to interpolate its service configuration. A source-installed CLI requires process environment variables. Advanced values in `.env` must also be passed through the Compose service.

??? question "Can I extend a backfill without deleting state?"
    Yes. Move `EXPORT_SINCE` backwards or leave it blank, then recreate the service. The cache scope changes and history is reconsidered while known UUIDs remain deduplicated.

??? question "What license applies to the connector and its dependencies?"
    The connector is MIT licensed. Its runtime dependencies are `requests`, community-maintained BSD-licensed `fit-tool` 0.9.16, and `filelock`. It does not bundle Hadge or Dreeve source. See [License](./license.md).
