# Project Backlog

## In Progress
*(nothing currently active)*

## Backlog

### CLI dispatcher — `python sync.py <source>`
Root-level `sync.py` that accepts a source name as an argument (e.g. `python sync.py whoop`) and dispatches to the right sync workflow. Designed with `elif` slots so TrainingPeaks and future sources drop in cleanly. See wireframe in conversation (2026-05-24).

### TrainingPeaks — FIT file ingestor
Parse bulk-exported FIT files (zipped, 1 year per zip) from TrainingPeaks into SQLite. Pipeline should handle zips directly, extract second-by-second streams (power, HR, cadence, altitude, etc.), and store in a `trainingpeaks` table alongside Whoop data. Drop files into `data/trainingpeaks/`. ~15 years of history to ingest.

### Ongoing sync — Intervals.icu API (parked)
Once TrainingPeaks historical export is complete and verified, set up Intervals.icu as the ongoing sync target. Plan: sync Garmin only (simpler than dual Garmin+Wahoo), Garmin auto-syncs to Intervals.icu, we hit the Intervals.icu API (API key, no approval). Cancel TrainingPeaks after data verified. Decision: Garmin-only device going forward if possible.

### Excel ingestor — strength & body metrics
Parse `data/manual/strength_log.xlsx` and `data/manual/body_metrics.xlsx` into SQLite tables (`strength_sessions`, `body_metrics`). Safe to re-run — duplicate rows skipped. Add openpyxl to requirements.

### MCP server
Wire all databases (Whoop, TrainingPeaks, strength, body metrics) to Claude for conversational training analysis and programme planning.

### Automate the sync
Schedule `sync.py` to run daily via Windows Task Scheduler so data stays fresh without manual runs.

## Completed
- Whoop OAuth authentication
- Whoop data pipeline (recovery, sleep, workouts, cycles)
- SQLite database with full history (~7-8 years of data)
- Auto token refresh on 401
- User guide (`docs/user_guide.md`)
- TrainingPeaks FIT file ingestor (built, tested, handles .fit.gz inside zips)
- Excel templates for strength log and body metrics (`data/manual/`)
