import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/trainingpeaks.db")


def get_connection():
    return sqlite3.connect(DB_PATH)


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    # One row per workout file
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            workout_id TEXT PRIMARY KEY,
            filename TEXT,
            sport TEXT,
            start_time TEXT,
            end_time TEXT,
            total_elapsed_time_sec REAL,
            total_distance_m REAL,
            avg_heart_rate INTEGER,
            max_heart_rate INTEGER,
            avg_power INTEGER,
            max_power INTEGER,
            avg_cadence INTEGER,
            total_ascent_m REAL,
            total_calories INTEGER
        )
    """)

    # One row per second of data per workout
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id TEXT,
            timestamp TEXT,
            heart_rate INTEGER,
            power INTEGER,
            cadence INTEGER,
            speed_ms REAL,
            distance_m REAL,
            altitude_m REAL,
            position_lat REAL,
            position_long REAL,
            temperature_c REAL,
            FOREIGN KEY (workout_id) REFERENCES workouts(workout_id)
        )
    """)

    conn.commit()
    conn.close()
    print("TrainingPeaks database initialized.")


if __name__ == "__main__":
    initialize_db()
