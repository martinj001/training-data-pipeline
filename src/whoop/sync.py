import sys
import argparse
import sqlite3
from datetime import datetime, timedelta
from database import initialize_db, get_connection, get_latest_updated_at
from client import whoop_get

# Whoop occasionally revises scores for a few days after the fact, so an
# incremental sync steps back this many days from the last synced record
# rather than resuming exactly where it left off.
OVERLAP_DAYS = 7


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--days", type=int, default=None)
    args, _ = parser.parse_known_args()
    return args.days


def get_sync_start(days=None, table=None):
    """Return ISO start timestamp, or None for full history.

    --days N: sync last N days.
    No flag: incremental -- resumes from the latest synced record in `table`,
    stepped back OVERLAP_DAYS to catch late score revisions. Falls back to
    full history if `table` is empty (first run).
    """
    if days is not None:
        return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    latest = get_latest_updated_at(table) if table else None
    if not latest:
        return None

    latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
    start_dt = latest_dt - timedelta(days=OVERLAP_DAYS)
    return start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def describe_start(start, days):
    if start is None:
        return "  Full history (first run)"
    if days is not None:
        return f"  From {start[:10]} (--days {days})"
    return f"  From {start[:10]} ({OVERLAP_DAYS}-day overlap to catch score revisions)"


def fetch_all_pages(endpoint, params=None):
    records = []
    next_token = None
    page = 1

    while True:
        p = {"limit": 25, **(params or {})}
        if next_token:
            p["nextToken"] = next_token

        data = whoop_get(endpoint, params=p)
        batch = data.get("records", [])
        records.extend(batch)
        print(f"  Page {page}: fetched {len(batch)} records (total so far: {len(records)})")

        next_token = data.get("next_token")
        if not next_token:
            break
        page += 1

    return records


def sync_recovery(days=None):
    print("Syncing recovery data...")
    start = get_sync_start(days, table="recovery")
    print(describe_start(start, days))
    params = {"start": start} if start else {}
    records = fetch_all_pages("/recovery", params)
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for r in records:
        score = r.get("score") or {}
        cursor.execute("""
            INSERT OR REPLACE INTO recovery (
                cycle_id, sleep_id, created_at, updated_at, score_state,
                recovery_score, resting_heart_rate, hrv_rmssd_milli,
                spo2_percentage, skin_temp_celsius
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r.get("cycle_id"), r.get("sleep_id"), r.get("created_at"),
            r.get("updated_at"), r.get("score_state"),
            score.get("recovery_score"), score.get("resting_heart_rate"),
            score.get("hrv_rmssd_milli"), score.get("spo2_percentage"),
            score.get("skin_temp_celsius"),
        ))
        inserted += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"Recovery sync complete: {inserted} records synced (new or updated).\n")


def sync_sleep(days=None):
    print("Syncing sleep data...")
    start = get_sync_start(days, table="sleep")
    print(describe_start(start, days))
    params = {"start": start} if start else {}
    records = fetch_all_pages("/activity/sleep", params)
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for r in records:
        score = r.get("score") or {}
        cursor.execute("""
            INSERT OR REPLACE INTO sleep (
                sleep_id, cycle_id, created_at, updated_at, start, end,
                score_state, total_in_bed_time_milli, total_awake_time_milli,
                total_light_sleep_time_milli, total_slow_wave_sleep_time_milli,
                total_rem_sleep_time_milli, sleep_performance_percentage,
                sleep_consistency_percentage, sleep_efficiency_percentage
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r.get("id"), r.get("cycle_id"), r.get("created_at"),
            r.get("updated_at"), r.get("start"), r.get("end"),
            r.get("score_state"),
            score.get("total_in_bed_time_milli"), score.get("total_awake_time_milli"),
            score.get("total_light_sleep_time_milli"), score.get("total_slow_wave_sleep_time_milli"),
            score.get("total_rem_sleep_time_milli"), score.get("sleep_performance_percentage"),
            score.get("sleep_consistency_percentage"), score.get("sleep_efficiency_percentage"),
        ))
        inserted += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"Sleep sync complete: {inserted} records synced (new or updated).\n")


def sync_workouts(days=None):
    print("Syncing workout data...")
    start = get_sync_start(days, table="workouts")
    print(describe_start(start, days))
    params = {"start": start} if start else {}
    records = fetch_all_pages("/activity/workout", params)
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for r in records:
        score = r.get("score") or {}
        zones = score.get("zone_duration") or {}
        cursor.execute("""
            INSERT OR REPLACE INTO workouts (
                workout_id, created_at, updated_at, start, end, sport_id,
                score_state, strain, average_heart_rate, max_heart_rate,
                kilojoule, percent_recorded, zone_zero_milli, zone_one_milli,
                zone_two_milli, zone_three_milli, zone_four_milli, zone_five_milli
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r.get("id"), r.get("created_at"), r.get("updated_at"),
            r.get("start"), r.get("end"), r.get("sport_id"),
            r.get("score_state"), score.get("strain"),
            score.get("average_heart_rate"), score.get("max_heart_rate"),
            score.get("kilojoule"), score.get("percent_recorded"),
            zones.get("zone_zero_milli"), zones.get("zone_one_milli"),
            zones.get("zone_two_milli"), zones.get("zone_three_milli"),
            zones.get("zone_four_milli"), zones.get("zone_five_milli"),
        ))
        inserted += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"Workout sync complete: {inserted} records synced (new or updated).\n")


def sync_cycles(days=None):
    print("Syncing cycle data...")
    start = get_sync_start(days, table="cycles")
    print(describe_start(start, days))
    params = {"start": start} if start else {}
    records = fetch_all_pages("/cycle", params)
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for r in records:
        score = r.get("score") or {}
        cursor.execute("""
            INSERT OR REPLACE INTO cycles (
                cycle_id, created_at, updated_at, start, end,
                score_state, strain, kilojoule, average_heart_rate, max_heart_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r.get("id"), r.get("created_at"), r.get("updated_at"),
            r.get("start"), r.get("end"), r.get("score_state"),
            score.get("strain"), score.get("kilojoule"),
            score.get("average_heart_rate"), score.get("max_heart_rate"),
        ))
        inserted += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"Cycle sync complete: {inserted} records synced (new or updated).\n")


if __name__ == "__main__":
    days = parse_args()
    initialize_db()
    sync_recovery(days)
    sync_sleep(days)
    sync_workouts(days)
    sync_cycles(days)
    print("Full sync complete!")
