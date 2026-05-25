import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WHOOP_DB = PROJECT_ROOT / "data" / "whoop.db"
INTERVALS_DB = PROJECT_ROOT / "data" / "intervals.db"
TP_DB = PROJECT_ROOT / "data" / "trainingpeaks.db"
STRENGTH_DIR = PROJECT_ROOT / "data" / "manual" / "strength"

mcp = FastMCP("training-data")

# Intervals.icu activity types → pillar
INTERVALS_PILLAR = {
    "Ride": "cardio",
    "VirtualRide": "cardio",
    "MountainBikeRide": "cardio",
    "GravelRide": "cardio",
    "Run": "cardio",
    "TrailRun": "cardio",
    "Hike": "cardio",
    "Walk": "cardio",
    "Swim": "cardio",
    "NordicSki": "cardio",
    "WeightTraining": "strength",
    "Workout": "strength",
    "Yoga": "mobility",
    "Pilates": "mobility",
    "Stretching": "mobility",
}


# Whoop cycling sport_ids — skip these, Intervals.icu (Zwift/Garmin) covers them
WHOOP_CYCLING_IDS = {1, 57}

# Whoop running sport_ids — show as cardio
WHOOP_RUNNING_IDS = {0}


def classify_pillar(activity_type: str) -> str:
    if activity_type in INTERVALS_PILLAR:
        return INTERVALS_PILLAR[activity_type]
    s = activity_type.lower()
    if any(k in s for k in ("strength", "weight", "functional", "crossfit", "gym")):
        return "strength"
    if any(k in s for k in ("yoga", "pilates", "stretch", "mobility", "foundation", "yin")):
        return "mobility"
    return "cardio"


def _count_recent_strength_files(days: int) -> int:
    if not STRENGTH_DIR.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    count = 0
    for f in STRENGTH_DIR.glob("*.xlsx"):
        try:
            if datetime.strptime(f.stem, "%Y-%m-%d") >= cutoff:
                count += 1
        except ValueError:
            pass
    return count


@mcp.tool()
def get_recent_workouts(days: int = 7) -> str:
    """
    Get workouts over the last N days.
    Cardio: Intervals.icu primary (Zwift + Garmin), TrainingPeaks fallback.
    Strength/mobility: Whoop workout log (log workouts in the Whoop app before the gym).
    Shows date, source, pillar, duration, distance/strain, and HR.
    """
    since = (datetime.now() - timedelta(days=days)).date().isoformat()
    rows_out = []

    # Primary: Intervals.icu (Zwift + Garmin)
    if INTERVALS_DB.exists():
        conn = sqlite3.connect(str(INTERVALS_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT start_date_local, name, type, moving_time_sec,
                   distance_m, average_heartrate, average_watts, trainer
            FROM activities
            WHERE date(start_date_local) >= ?
            ORDER BY start_date_local DESC
        """, (since,)).fetchall()
        conn.close()
        for r in rows:
            atype = r["type"] or "Unknown"
            if atype == "VirtualRide":
                source = "Zwift"
            elif atype in ("Ride", "MountainBikeRide", "GravelRide", "Run", "TrailRun", "Hike", "Walk"):
                source = "Garmin"
            else:
                source = atype
            mins = round((r["moving_time_sec"] or 0) / 60)
            dist = f"{r['distance_m']/1000:.1f}km" if r["distance_m"] else ""
            hr = f"avg HR {r['average_heartrate']:.0f}" if r["average_heartrate"] else ""
            watts = f"avg {r['average_watts']:.0f}w" if r["average_watts"] else ""
            line = f"  {r['start_date_local'][:10]} | {r['name'] or atype} [{classify_pillar(atype)}] via {source} | {mins}min"
            for extra in [dist, watts, hr]:
                if extra:
                    line += f" | {extra}"
            rows_out.append((r["start_date_local"][:10], line))

    # Fallback: TrainingPeaks for any dates not covered by Intervals.icu
    intervals_dates = {r[0] for r in rows_out}
    conn = sqlite3.connect(str(TP_DB))
    conn.row_factory = sqlite3.Row
    tp_rows = conn.execute("""
        SELECT start_time, sport, total_elapsed_time_sec, total_distance_m, avg_heart_rate
        FROM workouts WHERE start_time >= ? AND start_time NOT NULL ORDER BY start_time DESC
    """, (since,)).fetchall()
    conn.close()
    for r in tp_rows:
        date = str(r["start_time"])[:10]
        if date in intervals_dates:
            continue  # already covered
        sport = (r["sport"] or "cycling").title()
        mins = round((r["total_elapsed_time_sec"] or 0) / 60)
        dist = f"{r['total_distance_m']/1000:.1f}km" if r["total_distance_m"] else ""
        hr = f"avg HR {r['avg_heart_rate']}" if r["avg_heart_rate"] else ""
        line = f"  {date} | {sport} [{classify_pillar(sport)}] via TrainingPeaks | {mins}min"
        for extra in [dist, hr]:
            if extra:
                line += f" | {extra}"
        rows_out.append((date, line))

    # Whoop: strength and mobility sessions (gym, yoga, etc.)
    # Skip cardio sport_ids — those are already covered by Intervals.icu
    whoop_since = (datetime.now() - timedelta(days=days)).isoformat()
    if WHOOP_DB.exists():
        conn = sqlite3.connect(str(WHOOP_DB))
        conn.row_factory = sqlite3.Row
        whoop_rows = conn.execute("""
            SELECT start, end, sport_id, strain, average_heart_rate,
                   zone_zero_milli, zone_one_milli, zone_two_milli,
                   zone_three_milli, zone_four_milli, zone_five_milli
            FROM workouts WHERE start >= ? ORDER BY start DESC
        """, (whoop_since,)).fetchall()
        conn.close()
        for r in whoop_rows:
            sid = r["sport_id"]
            if sid in WHOOP_CYCLING_IDS:
                continue  # covered by Intervals.icu
            if sid in WHOOP_RUNNING_IDS:
                name, pillar = "Run", "cardio"
            else:
                name, pillar = "Gym", "strength"
            date = str(r["start"])[:10]
            total_milli = sum(r[k] or 0 for k in (
                "zone_zero_milli", "zone_one_milli", "zone_two_milli",
                "zone_three_milli", "zone_four_milli", "zone_five_milli"
            ))
            if total_milli > 0:
                mins = round(total_milli / 60000)
            elif r["start"] and r["end"]:
                start_dt = datetime.fromisoformat(r["start"].replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(r["end"].replace("Z", "+00:00"))
                mins = round((end_dt - start_dt).total_seconds() / 60)
            else:
                mins = 0
            strain = f"strain {r['strain']:.1f}" if r["strain"] else ""
            hr = f"avg HR {r['average_heart_rate']}" if r["average_heart_rate"] else ""
            line = f"  {date} | {name} [{pillar}] via Whoop | {mins}min"
            for extra in [strain, hr]:
                if extra:
                    line += f" | {extra}"
            rows_out.append((date, line))

    if not rows_out:
        return f"No workouts found in the last {days} days."

    rows_out.sort(key=lambda x: x[0], reverse=True)
    lines = [f"Workouts — last {days} days ({len(rows_out)} total):\n"]
    lines += [r[1] for r in rows_out]
    return "\n".join(lines)


@mcp.tool()
def get_recovery(days: int = 7) -> str:
    """
    Get Whoop recovery scores, HRV, resting heart rate, and sleep data
    for the last N days. Use this to understand how recovered the athlete
    is and whether the body is ready for a hard session.
    """
    since = (datetime.now() - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(str(WHOOP_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT r.created_at, r.recovery_score, r.hrv_rmssd_milli,
               r.resting_heart_rate, s.sleep_performance_percentage,
               s.total_in_bed_time_milli
        FROM recovery r
        LEFT JOIN sleep s ON r.sleep_id = s.sleep_id
        WHERE r.created_at >= ? ORDER BY r.created_at DESC
    """, (since,)).fetchall()
    conn.close()

    if not rows:
        return f"No recovery data found in the last {days} days."

    lines = [f"Recovery — last {days} days:\n"]
    for r in rows:
        date = r["created_at"][:10]
        rec = f"{r['recovery_score']:.0f}%" if r["recovery_score"] else "N/A"
        hrv = f"{r['hrv_rmssd_milli']:.1f}ms" if r["hrv_rmssd_milli"] else "N/A"
        rhr = f"{r['resting_heart_rate']:.0f}bpm" if r["resting_heart_rate"] else "N/A"
        sleep_h = f"{r['total_in_bed_time_milli']/3600000:.1f}h" if r["total_in_bed_time_milli"] else "N/A"
        sleep_p = f"{r['sleep_performance_percentage']:.0f}%" if r["sleep_performance_percentage"] else "N/A"
        lines.append(f"  {date} | Recovery {rec} | HRV {hrv} | RHR {rhr} | Sleep {sleep_h} ({sleep_p})")

    return "\n".join(lines)


@mcp.tool()
def get_weekly_pillar_summary() -> str:
    """
    Summarise the last 7 days of training by pillar: strength, cardio, mobility.
    Cardio comes from Intervals.icu (Zwift, Garmin) with TrainingPeaks fallback for dates not yet in Intervals.
    Strength comes from manual Excel logs.
    Mobility is currently tracked via manual logs only.
    Flags any pillar that has been missed this week.
    """
    since = (datetime.now() - timedelta(days=7)).date().isoformat()

    pillars: dict[str, list[str]] = {"strength": [], "cardio": [], "mobility": []}
    intervals_dates: set[str] = set()

    if INTERVALS_DB.exists():
        conn = sqlite3.connect(str(INTERVALS_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT start_date_local, name, type FROM activities
            WHERE date(start_date_local) >= ?
        """, (since,)).fetchall()
        conn.close()
        for r in rows:
            atype = r["type"] or "Unknown"
            label = r["name"] or atype
            pillars[classify_pillar(atype)].append(label)
            intervals_dates.add(r["start_date_local"][:10])

    # TrainingPeaks fallback for dates not yet in Intervals.icu
    if TP_DB.exists():
        conn = sqlite3.connect(str(TP_DB))
        conn.row_factory = sqlite3.Row
        tp_rows = conn.execute("""
            SELECT start_time, sport FROM workouts
            WHERE start_time >= ? AND start_time NOT NULL ORDER BY start_time DESC
        """, (since,)).fetchall()
        conn.close()
        for r in tp_rows:
            date = str(r["start_time"])[:10]
            if date in intervals_dates:
                continue
            sport = (r["sport"] or "cycling").title()
            pillars[classify_pillar(sport)].append(f"{sport} (TP)")

    # Whoop: strength and mobility sessions
    whoop_since = (datetime.now() - timedelta(days=7)).isoformat()
    if WHOOP_DB.exists():
        conn = sqlite3.connect(str(WHOOP_DB))
        conn.row_factory = sqlite3.Row
        w_rows = conn.execute("""
            SELECT start, sport_id FROM workouts WHERE start >= ? ORDER BY start DESC
        """, (whoop_since,)).fetchall()
        conn.close()
        for r in w_rows:
            sid = r["sport_id"]
            if sid in WHOOP_CYCLING_IDS:
                continue
            if sid in WHOOP_RUNNING_IDS:
                name, pillar = "Run", "cardio"
            else:
                name, pillar = "Gym", "strength"
            pillars[pillar].append(f"{name} (Whoop)")

    # Strength and mobility from manual Excel logs
    manual_strength = _count_recent_strength_files(days=7)

    # Recovery average from Whoop
    conn = sqlite3.connect(str(WHOOP_DB))
    avg_recovery = conn.execute("""
        SELECT AVG(recovery_score) FROM recovery WHERE created_at >= ?
    """, (whoop_since,)).fetchone()[0]
    conn.close()

    lines = ["Weekly Pillar Summary — last 7 days:\n"]
    for pillar, sessions in pillars.items():
        count = len(sessions) + (manual_strength if pillar == "strength" else 0)
        status = "MISSING" if count == 0 else ("light" if count == 1 else "good")
        detail = ", ".join(sessions) if sessions else "none logged"
        if pillar == "strength" and manual_strength:
            detail += f" + {manual_strength} manual log(s)"
        lines.append(f"  {pillar.upper():10} [{status}]  {count} session(s) — {detail}")

    if avg_recovery:
        lines.append(f"\n  Avg recovery this week: {avg_recovery:.0f}%")

    return "\n".join(lines)


@mcp.tool()
def get_strength_sessions(days: int = 14) -> str:
    """
    Read recent strength sessions from the manual Excel logs in data/manual/strength/.
    Returns exercises, sets, reps, weight, and RPE for each session.
    Mobility work (yoga, Foundation Training) logged in those files is also shown.
    """
    if not STRENGTH_DIR.exists():
        return "No strength log directory found. Start logging at data/manual/strength/YYYY-MM-DD.xlsx."

    try:
        import openpyxl
    except ImportError:
        return "openpyxl not installed."

    cutoff = datetime.now() - timedelta(days=days)
    recent = sorted(
        [(datetime.strptime(f.stem, "%Y-%m-%d"), f)
         for f in STRENGTH_DIR.glob("*.xlsx")
         if not f.name.startswith("~") and len(f.stem) == 10],
        reverse=True
    )
    recent = [(d, f) for d, f in recent if d >= cutoff]

    if not recent:
        return f"No strength sessions logged in the last {days} days."

    lines = [f"Strength/mobility sessions — last {days} days ({len(recent)} session(s)):\n"]
    for date, f in recent:
        lines.append(f"\n  {date.strftime('%Y-%m-%d')}:")
        try:
            wb = openpyxl.load_workbook(f, data_only=True)
            ws = wb.active
            for row in ws.iter_rows(min_row=2, values_only=True):
                cols = (list(row) + [None] * 7)[:7]
                exercise, sets, reps, weight, rpe, done, notes = cols
                if not exercise:
                    continue
                parts = [f"    {exercise}"]
                if sets and reps:
                    parts.append(f"{int(sets)}x{int(reps)}")
                if weight:
                    parts.append(f"@ {weight}kg")
                if rpe:
                    parts.append(f"RPE {rpe}")
                lines.append(" ".join(str(p) for p in parts))
        except Exception as e:
            lines.append(f"    (Could not read: {e})")

    return "\n".join(lines)


@mcp.tool()
def get_training_load_trend(weeks: int = 6) -> str:
    """
    Show a week-by-week breakdown of training over the last N weeks using Intervals.icu data.
    Reports session counts by pillar and total duration per week.
    Useful for spotting patterns — too many heavy weeks, missing pillars, etc.
    """
    if not INTERVALS_DB.exists():
        return "Intervals.icu database not found. Run src/intervals/sync.py first."

    conn = sqlite3.connect(str(INTERVALS_DB))
    conn.row_factory = sqlite3.Row
    lines = [f"Training load trend — last {weeks} weeks:\n"]

    for i in range(weeks - 1, -1, -1):
        week_end = (datetime.now() - timedelta(weeks=i)).date()
        week_start = week_end - timedelta(weeks=1)
        rows = conn.execute("""
            SELECT type, moving_time_sec FROM activities
            WHERE date(start_date_local) >= ? AND date(start_date_local) < ?
        """, (week_start.isoformat(), week_end.isoformat())).fetchall()

        counts = {"strength": 0, "cardio": 0, "mobility": 0}
        total_mins = 0
        for r in rows:
            counts[classify_pillar(r["type"] or "Unknown")] += 1
            total_mins += round((r["moving_time_sec"] or 0) / 60)

        label = week_start.strftime("%b %d")
        n = sum(counts.values())
        pillar_str = f"S:{counts['strength']} C:{counts['cardio']} M:{counts['mobility']}"
        time_str = f"{total_mins}min" if total_mins else "no data"
        lines.append(f"  {label}: {n} sessions | {pillar_str} | {time_str}")

    conn.close()
    return "\n".join(lines)


PLANS_DIR = PROJECT_ROOT / "data" / "plans"


@mcp.tool()
def get_current_plan() -> str:
    """
    Read the current bi-weekly training plan. Returns the most recent plan file
    from data/plans/. Use this alongside get_recovery() and get_recent_workouts()
    to give context-aware daily guidance.
    """
    if not PLANS_DIR.exists() or not list(PLANS_DIR.glob("*.md")):
        return "No training plan found. Ask Claude to generate one."

    latest = max(PLANS_DIR.glob("*.md"), key=lambda f: f.stem)
    return latest.read_text(encoding="utf-8")


@mcp.tool()
def write_plan(filename: str, content: str) -> str:
    """
    Write a bi-weekly training plan to data/plans/. Filename should be the
    start date of the block in YYYY-MM-DD format (e.g. '2026-05-26').
    Claude calls this after drafting a plan based on recovery and workout history.
    """
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    path = PLANS_DIR / f"{filename}.md"
    path.write_text(content, encoding="utf-8")
    return f"Plan written to {path.name}"


if __name__ == "__main__":
    mcp.run()
