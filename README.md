# Training Data Pipeline

A personal training intelligence system that connects Whoop, Zwift, Garmin, and manual logs
to Claude via MCP — giving Claude live access to recovery, workouts, and training plans for
contextual, data-driven guidance.

---

## What it does

- **Tracks three training pillars** — Strength, Cardio, Mobility — across all data sources
- **Surfaces recovery context** — Whoop HRV, recovery score, sleep, and RHR
- **Generates bi-weekly training plans** — Claude reads your data and writes a complete plan
- **Gives daily guidance** — ask "what should I do today?" and Claude checks your recovery,
  recent workouts, and current plan before answering

---

## Data sources

| Source | What it tracks | How |
|--------|---------------|-----|
| Zwift | Indoor cycling (VirtualRide) | Syncs to Intervals.icu |
| Garmin | Outdoor cycling, running, hiking | Syncs to Intervals.icu |
| Whoop | Recovery, HRV, sleep, gym sessions | API sync |
| Manual Excel logs | Strength session detail (sets/reps/weight/RPE) | `data/manual/strength/` |
| TrainingPeaks | Historical workouts 2012–2026 (bridge only) | Loaded, subscription cancelled |

---

## Project structure

```
training-data-pipeline/
├── src/
│   ├── intervals/          # Intervals.icu API client and sync
│   │   ├── client.py
│   │   ├── database.py
│   │   └── sync.py
│   ├── whoop/              # Whoop API client, auth, and sync
│   │   ├── auth.py
│   │   ├── client.py
│   │   ├── database.py
│   │   └── sync.py
│   ├── trainingpeaks/      # TrainingPeaks .fit file ingestor
│   │   ├── database.py
│   │   └── ingestor.py
│   └── mcp/
│       └── server.py       # MCP server — 7 tools for Claude
├── data/
│   ├── whoop.db            # Whoop recovery, sleep, workouts
│   ├── intervals.db        # Intervals.icu activities
│   ├── trainingpeaks.db    # Historical TP workouts
│   ├── manual/strength/    # Excel strength logs (YYYY-MM-DD.xlsx)
│   └── plans/              # Bi-weekly training plans (YYYY-MM-DD.md)
└── docs/
    └── mcp-user-guide.md   # How to use the MCP with Claude
```

---

## MCP tools

Claude uses these automatically — you never call them directly.

| Tool | Description |
|------|-------------|
| `get_recent_workouts` | Last N days of activity across all sources |
| `get_recovery` | Whoop recovery score, HRV, RHR, sleep |
| `get_weekly_pillar_summary` | Strength / cardio / mobility balance this week |
| `get_strength_sessions` | Recent Excel strength logs with sets/reps/weight |
| `get_training_load_trend` | Week-by-week session counts and duration |
| `get_current_plan` | Active bi-weekly training plan |
| `write_plan` | Claude writes a new plan to data/plans/ |

---

## Setup

### Prerequisites
- Python 3.10+
- Claude desktop app or claude.ai with MCP support

### Install dependencies
```bash
pip install -r requirements.txt
```

### Configure credentials
```bash
cp .env.example .env
# Fill in your API keys
```

### Register the MCP server with Claude
```bash
claude mcp add training-data python src/mcp/server.py
```

### Sync data manually
```bash
python src/whoop/sync.py
python src/intervals/sync.py
```

---

## Daily workflow

Open Claude and ask naturally:
- *"What should I do today?"*
- *"How has my training looked this week?"*
- *"Let's plan the next two weeks — I have a work trip Wed–Fri."*

See `docs/mcp-user-guide.md` for the full guide.

---

## Logging gym sessions

Before picking up the first weight, open the Whoop app and manually start a workout.
Pick the sport type (Functional Fitness, Weight Training, etc.) so it's correctly tagged.

After the session, log sets/reps/weight in `data/manual/strength/YYYY-MM-DD.xlsx`.
A template is at `data/manual/strength/2026-05-24.example.xlsx`.
