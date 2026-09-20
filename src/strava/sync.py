import sys
import os
import argparse
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.dirname(__file__))

from database import initialize_db, get_connection, get_latest_start_date
from client import fetch_activities

# Strava can reprocess/revise an activity after the fact (e.g. a device
# re-upload, gear/segment recalculation), so an incremental sync steps back
# this many days from the last synced record rather than resuming exactly
# where it left off -- same reasoning as Whoop's OVERLAP_DAYS.
OVERLAP_DAYS = 7


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--days", type=int, default=None)
    args, _ = parser.parse_known_args()
    return args.days


def to_epoch(dt):
    return int(dt.replace(tzinfo=timezone.utc).timestamp())


def get_sync_start(days, conn):
    """Return (epoch_seconds, description) for the `after` param, or (None, ...) for full history."""
    if days is not None:
        start = datetime.now() - timedelta(days=days)
        return to_epoch(start), f"  From {start.date()} (--days {days})"

    latest = get_latest_start_date(conn)
    if not latest:
        return None, "  Full history (first run)"

    latest_dt = datetime.fromisoformat(latest[:19])
    start = latest_dt - timedelta(days=OVERLAP_DAYS)
    return to_epoch(start), f"  From {start.date()} ({OVERLAP_DAYS}-day overlap to catch revisions)"


def sync_activities():
    print("Syncing Strava activities...")
    initialize_db()
    conn = get_connection()

    days = parse_args()
    after, description = get_sync_start(days, conn)
    print(description)

    activities = fetch_activities(after=after)
    print(f"  Fetched {len(activities)} activities from API")

    inserted = 0
    cursor = conn.cursor()
    for a in activities:
        cursor.execute("""
            INSERT OR REPLACE INTO activities (
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
            a.get("sport_type") or a.get("type"),
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
            None,  # device_name -- not in the list endpoint, not used downstream
        ))
        inserted += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"  Done: {inserted} activities saved (new or updated).")


if __name__ == "__main__":
    sync_activities()
