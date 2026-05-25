import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "intervals.db"


def get_connection():
    return sqlite3.connect(str(DB_PATH))


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
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
    print("Intervals.icu database initialized.")


if __name__ == "__main__":
    initialize_db()
