import sys
import argparse
import sqlite3
from datetime import datetime, timedelta
from database import initialize_db, get_connection
from client import whoop_get


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--days", type=int, default=None)
    args, _ = parser.parse_known_args()
    return args.days


def get_sync_start(days=None):
    """Return ISO start timestamp, or None for full history.

    --days N: sync last N days.
    No flag: full history (no start filter).
    """
    if days is not None:
        return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return None


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
    start = get_sync_start(days)
    print(f"  From {start[:10]}" if start else "  Full history")
    params = {"start": start} if start else {}
    records = fetch_all_pages("/recovery", params)
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for r in records:
        score = r.get("score") or {}
        cursor.execute("""
            INSERT OR IGNORE INTO recovery (
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
    print(f"Recovery sync complete: {inserted} new records saved.\n")


def sync_sleep(days=None):
    print("Syncing sleep data...")
    start = get_sync_start(days)
    print(f"  From {start[:10]}" if start else "  Full history")
    params = {"start": start} if start else {}
    records = fetch_all_pages("/activity/sleep", params)
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for r in records:
        score = r.get("score") or {}
        cursor.execute("""
            INSERT OR IGNORE INTO sleep (
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
    print(f"Sleep sync complete: {inserted} new records saved.\n")


def sync_workouts(days=None):
    print("Syncing workout data...")
    start = get_sync_start(days)
    print(f"  From {start[:10]}" if start else "  Full history")
    params = {"start": start} if start else {}
    records = fetch_all_pages("/activity/workout", params)
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for r in records:
        score = r.get("score") or {}
        zones = score.get("zone_duration") or {}
        cursor.execute("""
            INSERT OR IGNORE INTO workouts (
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
    print(f"Workout sync complete: {inserted} new records saved.\n")


def sync_cycles(days=None):
    print("Syncing cycle data...")
    start = get_sync_start(days)
    print(f"  From {start[:10]}" if start else "  Full history")
    params = {"start": start} if start else {}
    records = fetch_all_pages("/cycle", params)
    conn = get_connection()
    cursor = conn.cursor()
    inserted = 0

    for r in records:
        score = r.get("score") or {}
        cursor.execute("""
            INSERT OR IGNORE INTO cycles (
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
    print(f"Cycle sync complete: {inserted} new records saved.\n")


if __name__ == "__main__":
    days = parse_args()
    initialize_db()
    sync_recovery(days)
    sync_sleep(days)
    sync_workouts(days)
    sync_cycles(days)
    print("Full sync complete!")
