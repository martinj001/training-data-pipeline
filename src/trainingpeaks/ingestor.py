import os
import gzip
import zipfile
import hashlib
from fitparse import FitFile
from database import initialize_db, get_connection

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../data/trainingpeaks")


def make_workout_id(filename):
    """Stable unique ID derived from the filename."""
    return hashlib.md5(filename.encode()).hexdigest()


def parse_fit_file(fit_path, filename):
    """Parse a single FIT file and return (workout_summary, stream_rows)."""
    fitfile = FitFile(fit_path)

    summary = {}
    streams = []

    for record in fitfile.get_messages("session"):
        for field in record:
            summary[field.name] = field.value

    for record in fitfile.get_messages("record"):
        row = {}
        for field in record:
            row[field.name] = field.value
        streams.append(row)

    workout_id = make_workout_id(filename)

    def semi(key):
        return summary.get(key)

    workout_row = (
        workout_id,
        filename,
        semi("sport"),
        str(semi("start_time")),
        str(semi("timestamp")),
        semi("total_elapsed_time"),
        semi("total_distance"),
        semi("avg_heart_rate"),
        semi("max_heart_rate"),
        semi("avg_power"),
        semi("max_power"),
        semi("avg_cadence"),
        semi("total_ascent"),
        semi("total_calories"),
    )

    stream_rows = []
    for row in streams:
        def val(key):
            v = row.get(key)
            # Convert lat/long from semicircles to degrees
            if key in ("position_lat", "position_long") and v is not None:
                v = v * (180 / 2**31)
            return v

        stream_rows.append((
            workout_id,
            str(row.get("timestamp")),
            val("heart_rate"),
            val("power"),
            val("cadence"),
            val("speed"),
            val("distance"),
            val("altitude"),
            val("position_lat"),
            val("position_long"),
            val("temperature"),
        ))

    return workout_row, stream_rows


def ingest_fit_file(fit_path, filename, cursor):
    """Insert a single FIT file into the database. Skips if already loaded."""
    workout_id = make_workout_id(filename)

    cursor.execute("SELECT 1 FROM workouts WHERE workout_id = ?", (workout_id,))
    if cursor.fetchone():
        return 0  # already ingested

    try:
        workout_row, stream_rows = parse_fit_file(fit_path, filename)
    except Exception as e:
        print(f"  Skipping {filename} — parse error: {e}")
        return 0

    cursor.execute("""
        INSERT OR IGNORE INTO workouts (
            workout_id, filename, sport, start_time, end_time,
            total_elapsed_time_sec, total_distance_m,
            avg_heart_rate, max_heart_rate, avg_power, max_power,
            avg_cadence, total_ascent_m, total_calories
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, workout_row)

    cursor.executemany("""
        INSERT INTO streams (
            workout_id, timestamp, heart_rate, power, cadence,
            speed_ms, distance_m, altitude_m,
            position_lat, position_long, temperature_c
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, stream_rows)

    return 1


def ingest_zip(zip_path):
    """Extract and ingest all FIT files from a zip archive."""
    zip_name = os.path.basename(zip_path)
    print(f"\nProcessing {zip_name}...")

    conn = get_connection()
    cursor = conn.cursor()
    ingested = 0
    skipped = 0

    with zipfile.ZipFile(zip_path, "r") as zf:
        all_files = zf.namelist()
        fit_files = [f for f in all_files if f.lower().endswith(".fit") or f.lower().endswith(".fit.gz")]
        print(f"  Found {len(fit_files)} FIT files")

        for fit_name in fit_files:
            with zf.open(fit_name) as fit_data:
                import tempfile
                raw = fit_data.read()
                if fit_name.lower().endswith(".gz"):
                    raw = gzip.decompress(raw)
                with tempfile.NamedTemporaryFile(suffix=".fit", delete=False) as tmp:
                    tmp.write(raw)
                    tmp_path = tmp.name

            result = ingest_fit_file(tmp_path, fit_name, cursor)
            os.unlink(tmp_path)

            if result:
                ingested += 1
            else:
                skipped += 1

    conn.commit()
    conn.close()
    print(f"  Done: {ingested} new workouts ingested, {skipped} skipped.")
    return ingested


def ingest_all():
    """Process every zip file in data/trainingpeaks/."""
    initialize_db()

    zip_files = sorted([
        f for f in os.listdir(DATA_DIR) if f.lower().endswith(".zip")
    ])

    if not zip_files:
        print(f"No zip files found in {DATA_DIR}")
        return

    print(f"Found {len(zip_files)} zip file(s) to process.")
    total = 0
    for zf in zip_files:
        try:
            total += ingest_zip(os.path.join(DATA_DIR, zf))
        except Exception as e:
            print(f"  SKIPPING {zf} — {e}")

    print(f"\nAll done! {total} total new workouts ingested.")


if __name__ == "__main__":
    ingest_all()
