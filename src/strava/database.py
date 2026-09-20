import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "strava.db"


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Same shape as the old Intervals.icu `activities` table, so downstream
    # consumers (mcp/server.py, review.py) only need a DB-path rename, not a
    # schema rewrite. `type` is populated from Strava's `sport_type` field
    # (not the legacy `type` field) -- sport_type is the more granular
    # vocabulary (MountainBikeRide/GravelRide/VirtualRide etc.) that the
    # pillar-classification dicts already expect.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id TEXT PRIMARY KEY,
            start_date TEXT,
            start_date_local TEXT,
            name TEXT,
            type TEXT,
            distance_m REAL,
            moving_time_sec INTEGER,
            elapsed_time_sec INTEGER,
            total_elevation_gain_m REAL,
            average_heartrate REAL,
            max_heartrate REAL,
            average_watts REAL,
            kilojoules REAL,
            average_speed_ms REAL,
            trainer INTEGER,
            device_name TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("Strava database initialized.")


def get_latest_start_date(conn):
    row = conn.execute("SELECT MAX(start_date_local) FROM activities").fetchone()
    return row[0] if row else None


if __name__ == "__main__":
    initialize_db()
