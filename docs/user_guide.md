# Training Data Pipeline — User Guide

*A practical guide to pulling, storing, and exploring your health data.*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Prerequisites & First-Time Setup](#2-prerequisites--first-time-setup)
3. [Whoop: Authenticate with the API](#3-whoop-authenticate-with-the-api)
4. [Whoop: Sync Your Data](#4-whoop-sync-your-data)
5. [Whoop: Explore the Database](#5-whoop-explore-the-database)
6. [Troubleshooting](#6-troubleshooting)
7. [Reference: What Data Gets Stored](#7-reference-what-data-gets-stored)

---

## 1. Project Overview

This pipeline pulls your personal training and recovery data from wearable APIs and stores it locally in a SQLite database. From there, you can query it, visualize it, or wire it up to an AI assistant for conversational analysis.

**Current data sources:**
- Whoop *(live)*

**Coming soon:**
- TrainingPeaks

**Project structure:**
```
training-data-pipeline/
├── docs/               ← guides and documentation
├── src/
│   └── whoop/
│       ├── auth.py     ← run once to authenticate
│       ├── client.py   ← handles all API requests
│       ├── database.py ← creates and manages the local database
│       └── sync.py     ← pulls data from Whoop and saves it
├── data/
│   └── whoop.db        ← your local database (never pushed to GitHub)
├── .env                ← your credentials (never pushed to GitHub)
└── .tokens             ← your OAuth tokens (never pushed to GitHub)
```

---

## 2. Prerequisites & First-Time Setup

### Requirements
- Python 3.10+
- A [Whoop developer app](https://developer.whoop.com) registered with your account

### Install dependencies
From the project root:
```bash
pip install -r requirements.txt
```

### Set up your `.env` file
Create a file named `.env` in the project root (copy `.env.example` as a starting point):
```
WHOOP_CLIENT_ID=your_client_id_here
WHOOP_CLIENT_SECRET=your_client_secret_here
WHOOP_REDIRECT_URI=http://localhost:8000/callback
```

Your Client ID and Secret come from the Whoop developer portal. These are never committed to GitHub.

---

## 3. Whoop: Authenticate with the API

Authentication only needs to happen **once** (or if your refresh token is ever revoked). After that, the pipeline handles token renewal automatically.

### Run auth
```bash
cd src/whoop
python auth.py
```

**What happens:**
1. Your browser opens to the Whoop login page
2. You log in and approve the requested permissions
3. Whoop redirects back to `localhost:8000/callback` — the script catches this automatically
4. Your tokens are saved to `.tokens` in the project root

You should see:
```
Opening Whoop login in your browser...
Waiting for authentication...
Authentication successful! Tokens saved to .tokens
```

### What are tokens?

| Token | Lifespan | Purpose |
|---|---|---|
| Access token | ~1 hour | Sent with every API request to prove identity |
| Refresh token | Long-lived | Used to get a new access token without logging in again |

You never need to run `auth.py` again under normal conditions — `client.py` refreshes your access token automatically whenever it expires.

---

## 4. Whoop: Sync Your Data

The sync script pulls your full Whoop history and stores it in `data/whoop.db`. It's safe to run repeatedly — duplicate records are automatically skipped.

### Run a full sync
```bash
cd src/whoop
python sync.py
```

**What happens:**
- All 4 data types are synced in sequence: recovery → sleep → workouts → cycles
- Each type paginates through your entire history (25 records per page)
- New records are inserted; existing records are skipped
- Record counts are printed as it goes

**Example output:**
```
Syncing recovery data...
  Page 1: fetched 25 records (total so far: 25)
  Page 2: fetched 25 records (total so far: 50)
  ...
Recovery sync complete: 12 new records saved.

Syncing sleep data...
  ...
Full sync complete!
```

### How often should I sync?

Run `sync.py` whenever you want fresh data. A weekly manual run is enough for most analysis. Automation (Windows Task Scheduler) is on the roadmap.

---

## 5. Whoop: Explore the Database

The database lives at `data/whoop.db`. You can query it with any SQLite tool.

### Option A: Python (in the project)
```bash
cd src/whoop
python
```
```python
import sqlite3
conn = sqlite3.connect("../../data/whoop.db")
cursor = conn.cursor()

# Example: last 10 recovery scores
cursor.execute("SELECT created_at, recovery_score, hrv_rmssd_milli FROM recovery ORDER BY created_at DESC LIMIT 10")
for row in cursor.fetchall():
    print(row)
```

### Option B: SQLite CLI
```bash
sqlite3 data/whoop.db
```
```sql
-- Check how many records are in each table
SELECT 'recovery', COUNT(*) FROM recovery
UNION ALL SELECT 'sleep', COUNT(*) FROM sleep
UNION ALL SELECT 'workouts', COUNT(*) FROM workouts
UNION ALL SELECT 'cycles', COUNT(*) FROM cycles;

-- Recent recovery trend
SELECT DATE(created_at), recovery_score, hrv_rmssd_milli, resting_heart_rate
FROM recovery
ORDER BY created_at DESC
LIMIT 14;
```

### Option C: DB Browser for SQLite *(recommended for beginners)*
A free GUI app — download at [sqlitebrowser.org](https://sqlitebrowser.org). Open `data/whoop.db`, browse tables visually, and run queries with a point-and-click interface.

---

## 6. Troubleshooting

### `ModuleNotFoundError`
Make sure you're running scripts from inside `src/whoop/`, not the project root:
```bash
cd src/whoop
python sync.py   # correct
```

### `FileNotFoundError: .tokens`
Your tokens file is missing — run `auth.py` first:
```bash
cd src/whoop
python auth.py
```

### `401 Unauthorized` (persistent)
The auto-refresh usually handles this. If it persists, your refresh token may have expired — re-run `auth.py` to re-authenticate.

### `KeyError` in `.env` variables
Check that your `.env` file exists in the project root and contains all three variables:
```
WHOOP_CLIENT_ID=...
WHOOP_CLIENT_SECRET=...
WHOOP_REDIRECT_URI=http://localhost:8000/callback
```

---

## 7. Reference: What Data Gets Stored

### `recovery` table
| Column | Description |
|---|---|
| cycle_id | Links to the daily cycle |
| sleep_id | Links to the sleep record |
| created_at | Timestamp |
| recovery_score | 0–100 recovery score |
| resting_heart_rate | Beats per minute |
| hrv_rmssd_milli | Heart rate variability (ms) |
| spo2_percentage | Blood oxygen saturation |
| skin_temp_celsius | Skin temperature |

### `sleep` table
| Column | Description |
|---|---|
| sleep_id | Unique sleep record ID |
| start / end | Sleep window timestamps |
| total_in_bed_time_milli | Total time in bed (ms) |
| total_light_sleep_time_milli | Light sleep duration (ms) |
| total_slow_wave_sleep_time_milli | Deep sleep duration (ms) |
| total_rem_sleep_time_milli | REM sleep duration (ms) |
| sleep_performance_percentage | Whoop's sleep performance score |
| sleep_efficiency_percentage | Time asleep vs. time in bed |

### `workouts` table
| Column | Description |
|---|---|
| workout_id | Unique workout ID |
| sport_id | Activity type (mapped to sport name by Whoop) |
| start / end | Workout timestamps |
| strain | Whoop strain score (0–21) |
| average_heart_rate | Avg HR during workout |
| max_heart_rate | Peak HR during workout |
| kilojoule | Energy output |
| zone_*_milli | Time in each of 6 heart rate zones (ms) |

### `cycles` table
| Column | Description |
|---|---|
| cycle_id | Unique daily cycle ID |
| start / end | Cycle timestamps |
| strain | Day strain score |
| kilojoule | Total daily energy output |
| average_heart_rate | Daily average HR |
| max_heart_rate | Daily peak HR |

---

*Last updated: 2026-05-24*
