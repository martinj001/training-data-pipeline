# Training Data MCP — User Guide

This system connects Claude to your real training data — Whoop recovery, Intervals.icu workouts,
strength logs, and bi-weekly plans. Claude can read all of it and give you specific, contextual
guidance rather than generic advice.

---

## Before you start — sync your data

Make sure Claude has the latest data from all sources before a planning session.
You have two ways to do this:

**Option A — Terminal**

Activate the project venv first, then run:

```bat
cd C:\Users\marti\dev\training-data-pipeline
.venv\Scripts\activate.bat
python sync.py all
```

Your prompt will show `(.venv)` confirming the right Python is active.

**Option B — Ask Claude directly**

Just say it in the conversation:

> "Sync my data before we start."

Claude will call `sync_data()` behind the scenes and show you the output inline.
No terminal needed.

---

Either way, what gets synced:

- **Whoop** — pulls latest recovery scores, HRV, sleep, and gym sessions
- **Intervals** — pulls latest Zwift rides and Garmin activities
- **Manual** — ingests strength logs and body metrics Excel files into the database

**Adjusting the sync window** — by default, sync picks up from where it left off. Use `--days` to go back further:

```bash
python sync.py all --days 14     # re-sync last 14 days
python sync.py whoop --days 30   # re-sync Whoop only, last 30 days
python sync.py manual --days 0   # re-ingest all manual logs ever
```

In a conversation you can also say:
> "Re-sync the last 14 days" and Claude will pass `--days 14` through automatically.

---

## How to start a conversation

Open Claude (desktop app or claude.ai) and just talk naturally. You don't need any special commands.

Some good openers:
- "What should I do today?"
- "How has my training looked this week?"
- "I want to plan the next two weeks."
- "My hamstrings are tight — what's the right session for today?"
- "I skipped Wednesday, how do I adjust the rest of the week?"

Claude will pull your data automatically in the background before answering.

---

## The tools (what Claude sees)

You never call these directly — Claude uses them behind the scenes.

| Tool | What it does |
|------|-------------|
| `get_recovery` | Last N days of Whoop data: recovery score, HRV, resting HR, sleep |
| `get_recent_workouts` | Last N days of activity: Zwift rides, Garmin outdoor cardio, Whoop gym sessions |
| `get_weekly_pillar_summary` | This week's strength / cardio / mobility balance at a glance |
| `get_current_plan` | Reads your active bi-weekly training plan |
| `get_strength_sessions` | Strength and mobility sessions from the database: exercises, sets, reps, weight, RPE, done/skipped |
| `get_body_metrics` | Bodyweight, calories, protein, and sleep from the database |
| `get_training_load_trend` | Week-by-week session counts and duration over the last N weeks |

---

## The daily workflow

**"What should I do today?"** is all you need to say. Claude will:

1. Check your Whoop recovery score from this morning
2. Look at what you've done so far this week
3. Read the current plan to see what's scheduled
4. Give you a specific recommendation — including whether to scale back if recovery is low

Example response you might get:
> "Recovery is 88% today, HRV looks solid. You're on Session B (lower/posterior chain) per the plan
> and haven't hit legs yet this week. Good day for it. RDL is the priority — take your time on the
> hinge, feel the hamstring load."

---

## Bi-weekly plans

Every two weeks Claude generates a new plan based on your recent training, recovery trend, and
anything coming up in your life (travel, busy periods, events).

**To get a new plan:**
Tell Claude at the end of a block or whenever you're ready:
> "Let's plan the next two weeks. I have a work trip Wed–Fri in week 2."

Claude will pull your data, ask any clarifying questions, then write the plan to `data/plans/`.

**Plans live at:** `data/plans/YYYY-MM-DD.md` (start date of the block)

You can open them in VS Code anytime to read or review. If you want a change, just tell Claude:
> "Swap Thursday and Friday in week 2" or "Add an extra run in week 1."

Once the plan is finalized, generate the strength workbooks for the block:

```bash
python src/manual/build_workbooks.py
```

---

## Logging your strength sessions

At the start of each block, pre-populated workbooks are generated automatically — one per strength
session, with target exercises, sets, reps, and weights already filled in.

**Generate workbooks for the current block:**

```bash
python src/manual/build_workbooks.py
```

This reads the most recent plan file and creates one xlsx per strength day in `data/manual/strength/`.
Run it once per block (every other Sunday). Use `--force` to regenerate if the plan changed.

**During the session:**

Open today's file (e.g. `data/manual/strength/2026-06-08.xlsx`). You'll see:

| Column | Pre-filled? | You fill in |
|--------|-------------|-------------|
| Exercise | ✓ | — |
| Set | ✓ | — |
| Reps | ✓ target | adjust if you did more/fewer |
| Weight (lbs) | ✓ target | adjust if you went up/down |
| RPE (1-10) | — | after every set |
| Done | — | Y when the set is complete |
| Time (seconds) | ✓ for timed exercises | — |
| Notes | ✓ cues on key sets | add anything useful |

**After the session, load it into the database:**

```bash
python sync.py manual
```

Do the same after updating `body_metrics.xlsx`.

---

## Logging gym sessions on Whoop

Before you pick up the first weight, open the Whoop app and start a workout:

1. Tap **+** on the main screen
2. Select **Log a Workout**
3. Pick your sport type (Functional Fitness, Weight Training, etc.)
4. Hit start — then end it when you're done

This gives Claude accurate duration and strain data for the session. Without it, Whoop may
auto-detect only a portion of the workout (or misidentify it as swimming).

---

## Data sources at a glance

| What | Source | How it gets in |
|------|--------|---------------|
| Indoor cycling | Zwift | Auto-syncs to Intervals.icu |
| Outdoor cycling, running, hiking | Garmin | Auto-syncs to Intervals.icu |
| Gym sessions | Whoop app (manual start) | Auto-syncs to Whoop DB |
| Recovery, HRV, sleep | Whoop | Auto-syncs to Whoop DB |
| Strength detail (sets/reps/weight) | Excel log | You write it, then run `sync.py manual` |
| Body metrics (weight, calories, sleep) | Excel log | You write it, then run `sync.py manual` |

---

## Keeping data fresh

Run this from the project folder to sync the latest data before a planning conversation:

```bash
python sync.py all           # incremental — picks up from last record
python sync.py all --days 7  # force re-sync last 7 days
```

Run manually before a planning session if you want the most up-to-date picture.

> **Daily email:** Your workout for the day is automatically emailed to you at 6:30 AM every morning — no need to open VS Code. See `docs/setup-daily-email.md` for details.
