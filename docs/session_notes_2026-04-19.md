# Session Notes — April 19, 2026

## What We Accomplished

### 1. Project Setup
- Created GitHub repo `martinj001/training-data-pipeline` (public, MIT licence, Python gitignore)
- Enabled GitHub Pages for hosting privacy policy
- Set up project folder structure: `src/whoop/`, `docs/`, `data/`
- Added `.env` and `.tokens` to `.gitignore` — credentials never go to GitHub

### 2. Whoop Developer App Registered
- Created app at developer.whoop.com
- Privacy policy hosted at `https://martinj001.github.io/training-data-pipeline/docs/privacy-policy.html`
- All 6 scopes granted: recovery, cycles, sleep, workout, profile, body_measurement
- Redirect URI: `http://localhost:8000/callback`

### 3. OAuth Authentication Working (`src/whoop/auth.py`)
- Full OAuth 2.0 flow implemented — opens browser, catches callback, exchanges code for tokens
- Tokens saved to `.tokens` at project root (gitignored)

### 4. Whoop API Client Built (`src/whoop/client.py`)
- Fetches profile, recovery, sleep, workouts, cycles
- Auto-refreshes access token on expiry (401 response) — no need to re-run auth.py

### 5. SQLite Database Created (`src/whoop/database.py`)
- 4 tables: `recovery`, `sleep`, `workouts`, `cycles`
- Lives at `data/whoop.db` (gitignored — health data stays local)

### 6. Full Historical Sync Complete (`src/whoop/sync.py`)
- Paginated through entire Whoop history
- `INSERT OR IGNORE` prevents duplicates on future syncs

### Final Record Counts
| Table | Records |
|---|---|
| Recovery | 2,768 |
| Sleep | 2,834 |
| Workouts | 2,285 |
| Cycles | 2,798 |

Approximately 7-8 years of Whoop data now stored locally.

### 7. Documentation Added
- `docs/concept_map_apis_pipelines_mcps.md` — how APIs, pipelines, and MCPs fit together
- `docs/whoop_api_technical_walkthrough.md` — line-by-line walkthrough of auth.py and client.py
- `docs/privacy-policy.html` — hosted on GitHub Pages

---

## To Do (Next Sessions)

1. **Query the database** — explore the data, write some interesting SQL against `whoop.db`
2. **Add TrainingPeaks connection** — replicate the Whoop pipeline for TrainingPeaks data
3. **Build MCP server** — wire the database to Claude for conversational training analysis
4. **Automate the sync** — schedule `sync.py` to run daily via Windows Task Scheduler

## Notes
- Run `sync.py` manually each week until automation is set up
- `auth.py` should not need to be re-run — refresh token handles renewal automatically
