# Project Backlog

## In Progress
*(nothing currently active)*

## Backlog

### CLI dispatcher — `python sync.py <source>`
Root-level `sync.py` that accepts a source name as an argument (e.g. `python sync.py whoop`) and dispatches to the right sync workflow. Designed with `elif` slots so TrainingPeaks and future sources drop in cleanly. See wireframe in conversation (2026-05-24).

### TrainingPeaks connection
Replicate the Whoop pipeline for TrainingPeaks data — auth, client, database tables, sync script.

### MCP server
Wire `whoop.db` to Claude for conversational training analysis.

### Automate the sync
Schedule `sync.py` to run daily via Windows Task Scheduler so data stays fresh without manual runs.

## Completed
- Whoop OAuth authentication
- Whoop data pipeline (recovery, sleep, workouts, cycles)
- SQLite database with full history (~7-8 years of data)
- Auto token refresh on 401
- User guide (`docs/user_guide.md`)
