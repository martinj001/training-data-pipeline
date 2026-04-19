import sqlite3
from database import initialize_db, get_connection
from client import whoop_get


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


def sync_recovery():
    print("Syncing recovery data...")
    records = fetch_all_pages("/recovery")
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


def sync_sleep():
    print("Syncing sleep data...")
    records = fetch_all_pages("/activity/sleep")
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


def sync_workouts():
    print("Syncing workout data...")
    records = fetch_all_pages("/activity/workout")
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


def sync_cycles():
    print("Syncing cycle data...")
    records = fetch_all_pages("/cycle")
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
    initialize_db()
    sync_recovery()
    sync_sleep()
    sync_workouts()
    sync_cycles()
    print("Full sync complete!")
