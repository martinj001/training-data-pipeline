import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/whoop.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recovery (
            cycle_id INTEGER PRIMARY KEY,
            sleep_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            score_state TEXT,
            recovery_score REAL,
            resting_heart_rate REAL,
            hrv_rmssd_milli REAL,
            spo2_percentage REAL,
            skin_temp_celsius REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sleep (
            sleep_id TEXT PRIMARY KEY,
            cycle_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            start TEXT,
            end TEXT,
            score_state TEXT,
            total_in_bed_time_milli INTEGER,
            total_awake_time_milli INTEGER,
            total_light_sleep_time_milli INTEGER,
            total_slow_wave_sleep_time_milli INTEGER,
            total_rem_sleep_time_milli INTEGER,
            sleep_performance_percentage REAL,
            sleep_consistency_percentage REAL,
            sleep_efficiency_percentage REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            workout_id TEXT PRIMARY KEY,
            created_at TEXT,
            updated_at TEXT,
            start TEXT,
            end TEXT,
            sport_id INTEGER,
            score_state TEXT,
            strain REAL,
            average_heart_rate INTEGER,
            max_heart_rate INTEGER,
            kilojoule REAL,
            percent_recorded REAL,
            zone_zero_milli INTEGER,
            zone_one_milli INTEGER,
            zone_two_milli INTEGER,
            zone_three_milli INTEGER,
            zone_four_milli INTEGER,
            zone_five_milli INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cycles (
            cycle_id TEXT PRIMARY KEY,
            created_at TEXT,
            updated_at TEXT,
            start TEXT,
            end TEXT,
            score_state TEXT,
            strain REAL,
            kilojoule REAL,
            average_heart_rate INTEGER,
            max_heart_rate INTEGER
        )
    """)

    conn.commit()
    conn.close()
    print("Database initialized.")


if __name__ == "__main__":
    initialize_db()
