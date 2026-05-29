# Training Data MCP — User Guide

This system connects Claude to your real training data — Whoop recovery, Intervals.icu workouts,
strength logs, and bi-weekly plans. Claude can read all of it and give you specific, contextual
guidance rather than generic advice.

---

## Before you start — sync your data

Run these two commands from the `training-data-pipeline` folder to make sure Claude has
the latest data from all sources:

```bash
python src/whoop/sync.py
python src/intervals/sync.py
```

- **Whoop sync** — pulls latest recovery scores, HRV, sleep, and gym sessions
- **Intervals sync** — pulls latest Zwift rides and Garmin activities

Two commands, fully up to date. Do this before any planning session or if you haven't
synced in a few days.

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

## The 5 tools (what Claude sees)

You never call these directly — Claude uses them behind the scenes.

| Tool | What it does |
|------|-------------|
| `get_recovery` | Last N days of Whoop data: recovery score, HRV, resting HR, sleep |
| `get_recent_workouts` | Last N days of activity: Zwift rides, Garmin outdoor cardio, Whoop gym sessions |
| `get_weekly_pillar_summary` | This week's strength / cardio / mobility balance at a glance |
| `get_current_plan` | Reads your active bi-weekly training plan |
| `get_strength_sessions` | Reads your manual Excel strength logs with sets, reps, weight, RPE |
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

---

## Logging your strength sessions

After a gym session, log it in an Excel file so Claude can see your exercises, weights, and RPE.

**File location:** `data/manual/strength/YYYY-MM-DD.xlsx`

**Columns:** Exercise | Sets | Reps | Weight (kg) | RPE (1-10) | Done | Notes

A template is at `data/manual/strength/2026-05-24.example.xlsx` — copy it, rename to today's date,
fill in what you did. That's it.

Claude reads these automatically when you ask about strength sessions or when generating your next plan.

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
| Strength detail (sets/reps/weight) | Excel log | You write it after each session |

---

## Keeping data fresh

Run these from the project folder to sync the latest data before a planning conversation:

```bash
python src/whoop/sync.py
python src/intervals/sync.py
```

Run these manually before a planning session if you want the most up-to-date picture.

> **Daily email:** Your workout for the day is automatically emailed to you at 6:30 AM every morning — no need to open VS Code. See `docs/setup-daily-email.md` for details.
