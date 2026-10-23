# Changelog

## 0.1.0 — 2026-10-23

- Import Apple Health workout summaries from Hadge's GitHub CSV exports into Dreeve's watch folder.
- Preserve workout names, sports, timestamps, duration, distance, calories, and ascent in summary FIT files.
- Poll automatically with durable delivery state, atomic output, restart recovery, and duplicate prevention.
- Support historical backfill, a start-date filter, previews, environment tokens, and rotating token files.
- Provide two-file Docker installation and an overlay for existing Dreeve Compose deployments.
- Validate the complete HTTP workflow with a real Git fixture, mock GitHub, packaged watcher, and Dreeve web/daemon.
- Publish tested amd64/arm64 GHCR images and matching setup-file downloads on GitHub releases.
