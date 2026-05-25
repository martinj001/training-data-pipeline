import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import initialize_db, get_connection
from client import fetch_activities


def get_latest_date(conn):
    row = conn.execute("SELECT MAX(start_date_local) FROM activities").fetchone()
    return row[0][:10] if row[0] else None


def sync_activities():
    print("Syncing Intervals.icu activities...")
    initialize_db()
    conn = get_connection()

    latest = get_latest_date(conn)
    if latest:
        # Step back 30 days from latest to catch any backfilled historical data
        from datetime import datetime, timedelta
        step_back = (datetime.strptime(latest[:10], "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
        oldest = step_back
        print(f"  Sync from {oldest} (30-day overlap to catch backfills)")
    else:
        oldest = "2024-01-01"
        print(f"  Full sync from {oldest} (first run)")

    activities = fetch_activities(oldest=oldest)
    print(f"  Fetched {len(activities)} activities from API")

    inserted = 0
    cursor = conn.cursor()
    for a in activities:
        cursor.execute("""
            INSERT OR IGNORE INTO activities (
                id, start_date, start_date_local, name, type,
                distance_m, moving_time_sec, elapsed_time_sec,
                total_elevation_gain_m, average_heartrate, max_heartrate,
                average_watts, kilojoules, average_speed_ms,
                trainer, device_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(a.get("id")),
            a.get("start_date"),
            a.get("start_date_local"),
            a.get("name"),
            a.get("type"),
            a.get("distance"),
            a.get("moving_time"),
            a.get("elapsed_time"),
            a.get("total_elevation_gain"),
            a.get("average_heartrate"),
            a.get("max_heartrate"),
            a.get("average_watts"),
            a.get("kilojoules"),
            a.get("average_speed"),
            1 if a.get("trainer") else 0,
            a.get("device_name"),
        ))
        inserted += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"  Done: {inserted} new activities saved.")


if __name__ == "__main__":
    sync_activities()
