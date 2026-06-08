"""
Training block review.

Usage:
  python review.py                         # auto-detects most recent plan block
  python review.py --start 2026-05-25      # specific block start
  python review.py --start 2026-05-25 --end 2026-06-07

  Add --sync to refresh manual.db from Excel files first.

Data sources:
  data/whoop.db      recovery, HRV, RHR
  data/intervals.db  cardio activities (runs, rides, MTB)
  data/manual.db     strength sessions (sync with src/manual/sync.py)
  data/plans/*.md    block plan and pillar targets
"""

import argparse
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT         = Path(__file__).resolve().parent
WHOOP_DB     = ROOT / "data" / "whoop.db"
INTERVALS_DB = ROOT / "data" / "intervals.db"
MANUAL_DB    = ROOT / "data" / "manual.db"
PLANS_DIR    = ROOT / "data" / "plans"

W   = 62
SEP = "─" * W

CARDIO_LABELS = {
    "Run":              "Run",
    "TrailRun":         "Trail Run",
    "VirtualRide":      "Zwift",
    "Ride":             "Ride",
    "MountainBikeRide": "MTB",
    "Hike":             "Hike",
    "Walk":             "Walk",
}

MOBILITY_EXERCISES = {"mobility", "foundation training", "mobility training"}


# ── helpers ───────────────────────────────────────────────────────────────────

def fmt(d: date) -> str:
    return d.strftime("%b ") + str(d.day)


def find_plan(start: date) -> Path | None:
    candidate = None
    for p in sorted(PLANS_DIR.glob("*.md")):
        try:
            if date.fromisoformat(p.stem) <= start:
                candidate = p
        except ValueError:
            pass
    return candidate


def parse_plan_targets(path: Path) -> dict[str, int]:
    targets, in_table = {}, False
    for line in path.read_text(encoding="utf-8").splitlines():
        low = line.lower()
        if "| pillar | sessions |" in low:
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 2 and "---" not in parts[0]:
                try:
                    targets[parts[0]] = int(parts[1])
                except ValueError:
                    pass
    return targets


def hdr(title: str) -> None:
    print(f"\n{title}")
    print(SEP)


# ── recovery ──────────────────────────────────────────────────────────────────

def recovery_section(start: date, end: date) -> None:
    conn = sqlite3.connect(str(WHOOP_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT
            date(r.created_at)               AS day,
            r.recovery_score                 AS score,
            r.hrv_rmssd_milli                AS hrv,
            r.resting_heart_rate             AS rhr,
            s.sleep_performance_percentage   AS sleep_pct
        FROM recovery r
        LEFT JOIN sleep s ON s.sleep_id = r.sleep_id
        WHERE date(r.created_at) BETWEEN ? AND ?
        ORDER BY r.created_at
    """, (start.isoformat(), end.isoformat())).fetchall()
    conn.close()

    hdr(f"RECOVERY  {fmt(start)} – {fmt(end)}")
    if not rows:
        print("  No data.")
        return

    print(f"  {'Date':<8} {'Day':<4} {'Rec':>5}    {'HRV':>5}  {'RHR':>3}  {'Sleep':>5}")
    print(f"  {SEP}")

    scores, hrvs, red_days = [], [], []
    for r in rows:
        score = r["score"] or 0
        hrv   = r["hrv"]   or 0.0
        rhr   = r["rhr"]   or 0
        sleep = r["sleep_pct"]

        day_date  = date.fromisoformat(r["day"])
        dow       = day_date.strftime("%a")
        dot       = "●" if score >= 67 else ("○" if score >= 34 else "·")
        day_str   = r["day"][5:]
        sleep_str = f"{sleep:.0f}%" if sleep else "  –"

        print(f"  {day_str:<8} {dow:<4} {score:>3.0f}% {dot}  {hrv:>5.1f}  {rhr:>3.0f}  {sleep_str:>5}")

        scores.append(score)
        if hrv:
            hrvs.append(hrv)
        if score < 50:
            red_days.append(day_str)

    print(f"  {SEP}")
    if scores:
        print(f"  Avg {sum(scores)/len(scores):.0f}%"
              f"   HRV {sum(hrvs)/len(hrvs):.1f} avg  [{min(hrvs):.1f}–{max(hrvs):.1f}]")
    if red_days:
        print(f"  Red (<50%): {', '.join(red_days)}")


# ── cardio activities ─────────────────────────────────────────────────────────

def activities_section(start: date, end: date) -> None:
    conn = sqlite3.connect(str(INTERVALS_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT
            date(start_date_local)            AS day,
            type,
            name,
            round(elapsed_time_sec / 60.0)    AS mins,
            round(distance_m / 1609.34, 1)    AS miles,
            round(average_heartrate)          AS avg_hr
        FROM activities
        WHERE date(start_date_local) BETWEEN ? AND ?
        ORDER BY start_date_local
    """, (start.isoformat(), end.isoformat())).fetchall()
    conn.close()

    hdr(f"CARDIO  {fmt(start)} – {fmt(end)}")
    if not rows:
        print("  None recorded in Intervals.")
        return

    print(f"  {'Date':<8} {'Day':<4} {'Type':<10} {'Min':>4}  {'Miles':>5}  {'Avg HR':>6}")
    print(f"  {SEP}")

    run_mins = []
    for r in rows:
        label    = CARDIO_LABELS.get(r["type"], r["type"])
        miles    = f"{r['miles']:.1f}" if r["miles"] else "  –"
        hr_str   = f"{r['avg_hr']:.0f}" if r["avg_hr"] else "  –"
        day_str  = r["day"][5:]
        dow      = date.fromisoformat(r["day"]).strftime("%a")
        print(f"  {day_str:<8} {dow:<4} {label:<10} {r['mins']:>4.0f}  {miles:>5}  {hr_str:>6}")
        if r["type"] in ("Run", "TrailRun"):
            run_mins.append(r["mins"] or 0)

    print(f"  {SEP}")
    print(f"  {len(rows)} session(s)")
    if run_mins:
        longest = max(run_mins)
        arrow   = "✓" if longest >= 30 else f"→ target 30 min (gap: {30 - longest:.0f} min)"
        print(f"  Runs: {len(run_mins)}  ·  longest {longest:.0f} min  {arrow}")


# ── strength progression ──────────────────────────────────────────────────────

def strength_section(start: date, end: date) -> None:
    conn = sqlite3.connect(str(MANUAL_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT date, exercise, set_num, reps, weight, rpe
        FROM strength_sessions
        WHERE date BETWEEN ? AND ?
          AND upper(done) = 'Y'
          AND lower(exercise) NOT IN ('mobility', 'foundation training', 'mobility training')
        ORDER BY date, exercise, CAST(set_num AS INTEGER)
    """, (start.isoformat(), end.isoformat())).fetchall()
    conn.close()

    hdr(f"STRENGTH  {fmt(start)} – {fmt(end)}")
    if not rows:
        print("  No data. Run `python src/manual/sync.py` to load Excel files.")
        return

    # Group: exercise → date → list of sets
    ex_data: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    session_dates: set[str] = set()

    for r in rows:
        ex_data[r["exercise"]][r["date"]].append({
            "reps":   r["reps"],
            "weight": r["weight"],
            "rpe":    r["rpe"],
        })
        session_dates.add(r["date"])

    session_list = sorted(session_dates)
    print(f"  Sessions ({len(session_list)}): {' · '.join(d[5:] for d in session_list)}")
    print()

    for exercise in sorted(ex_data.keys()):
        dates = sorted(ex_data[exercise].keys())
        print(f"  {exercise}")
        prev_vol = None
        for d in dates:
            sets        = ex_data[exercise][d]
            display, vol = _fmt_sets(sets)
            arrow       = _arrow(prev_vol, vol) if prev_vol is not None else ""
            rpe_vals    = [s["rpe"] for s in sets if s["rpe"] is not None]
            rpe_str     = f"  RPE {sum(rpe_vals)/len(rpe_vals):.1f}" if rpe_vals else ""
            print(f"    {d[5:]}  {display}{rpe_str}  {arrow}")
            prev_vol = vol
        print()


def _fmt_sets(sets: list[dict]) -> tuple[str, float]:
    n          = len(sets)
    reps_list  = [s["reps"] for s in sets if s["reps"] is not None]
    weights    = [s["weight"] for s in sets]
    is_bw      = any(w and "body" in str(w).lower() for w in weights)

    # Reps string
    if reps_list:
        unique = set(reps_list)
        reps_str = f"{n}×{reps_list[0]}" if len(unique) == 1 else f"{n} sets [{','.join(str(r) for r in reps_list)}]"
    else:
        reps_str = f"{n} set{'s' if n > 1 else ''}"

    if is_bw:
        return f"{reps_str} @ bodyweight", float(sum(reps_list)) if reps_list else float(n)

    numeric = []
    for w in weights:
        try:
            numeric.append(float(str(w).replace("lbs", "").strip()))
        except (ValueError, TypeError, AttributeError):
            pass

    if not numeric:
        return reps_str, float(sum(reps_list)) if reps_list else float(n)

    if len(set(numeric)) == 1:
        w_str = f"{numeric[0]:.0f} lbs"
    else:
        w_str = "/".join(f"{w:.0f}" for w in numeric) + " lbs"

    vol = sum(
        (r or 1) * (w or 0)
        for r, w in zip(reps_list or [1] * n, numeric)
    )
    return f"{reps_str} @ {w_str}", vol


def _arrow(prev: float, curr: float) -> str:
    if curr > prev * 1.02:
        return "↑"
    if curr < prev * 0.98:
        return "↓"
    return "→"


# ── pillar balance ────────────────────────────────────────────────────────────

def pillar_section(start: date, end: date, plan_path: Path | None) -> None:
    targets = parse_plan_targets(plan_path) if plan_path else {}

    conn = sqlite3.connect(str(MANUAL_DB))
    strength_dates = {row[0] for row in conn.execute("""
        SELECT DISTINCT date FROM strength_sessions
        WHERE date BETWEEN ? AND ?
          AND upper(done) = 'Y'
          AND lower(exercise) NOT IN ('mobility', 'foundation training', 'mobility training')
    """, (start.isoformat(), end.isoformat()))}
    mobility_dates = {row[0] for row in conn.execute("""
        SELECT DISTINCT date FROM strength_sessions
        WHERE date BETWEEN ? AND ?
          AND upper(done) = 'Y'
          AND lower(exercise) IN ('mobility', 'foundation training', 'mobility training')
    """, (start.isoformat(), end.isoformat()))}
    conn.close()

    conn = sqlite3.connect(str(INTERVALS_DB))
    cardio_count = conn.execute("""
        SELECT COUNT(*) FROM activities
        WHERE date(start_date_local) BETWEEN ? AND ?
    """, (start.isoformat(), end.isoformat())).fetchone()[0]
    conn.close()

    actual = {
        "Strength": len(strength_dates),
        "Cardio":   cardio_count,
        "Mobility": len(mobility_dates),
    }

    hdr(f"PILLAR BALANCE  {fmt(start)} – {fmt(end)}")
    print(f"  {'Pillar':<12} {'Target':>6}  {'Done':>4}  {'':>8}")
    print(f"  {SEP}")

    for pillar in ["Strength", "Cardio", "Mobility"]:
        t    = targets.get(pillar)
        done = actual[pillar]
        if t is not None:
            diff   = done - t
            status = ("✓ +" if diff >= 0 else "✗ ") + str(abs(diff))
        else:
            status = ""
        t_str = str(t) if t is not None else "–"
        print(f"  {pillar:<12} {t_str:>6}  {done:>4}  {status}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Training block review")
    parser.add_argument("--start", help="Block start YYYY-MM-DD (default: most recent plan)")
    parser.add_argument("--end",   help="Block end   YYYY-MM-DD (default: start + 13 days)")
    parser.add_argument("--sync",  action="store_true", help="Sync manual.db from Excel first")
    args = parser.parse_args()

    if args.sync:
        print("Syncing manual data…")
        subprocess.run([sys.executable, "src/manual/sync.py", "--days", "60"], check=True)

    if args.start:
        start = date.fromisoformat(args.start)
    else:
        plans = sorted(PLANS_DIR.glob("*.md"))
        if not plans:
            sys.exit("No plan files found in data/plans/")
        start = date.fromisoformat(plans[-1].stem)

    end = date.fromisoformat(args.end) if args.end else start + timedelta(days=13)

    plan_path = find_plan(start)

    print("=" * W)
    print(f"  BLOCK REVIEW  {fmt(start)} – {fmt(end)}")
    if plan_path:
        print(f"  Plan: {plan_path.name}")
    print("=" * W)

    recovery_section(start, end)
    activities_section(start, end)
    strength_section(start, end)
    pillar_section(start, end, plan_path)

    print()


if __name__ == "__main__":
    main()
