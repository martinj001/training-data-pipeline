"""
CLI dispatcher for training-data-pipeline.

Usage:
  python sync.py whoop                  — incremental sync (auto-detects last record)
  python sync.py whoop --days 30        — sync last 30 days regardless of DB state
  python sync.py intervals              — sync Intervals.icu (Zwift + Garmin activities)
  python sync.py intervals --days 60    — sync last 60 days
  python sync.py trainingpeaks          — ingest all TrainingPeaks zip files
  python sync.py all                    — run whoop + intervals (incremental)
  python sync.py all --days 14          — run whoop + intervals for last 14 days
"""
import sys
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SOURCES = {
    "whoop": ROOT / "src" / "whoop" / "sync.py",
    "intervals": ROOT / "src" / "intervals" / "sync.py",
    "trainingpeaks": ROOT / "src" / "trainingpeaks" / "ingestor.py",
}


def run(name, script, days=None):
    print(f"\n{'='*40}", flush=True)
    print(f"  {name}", flush=True)
    print(f"{'='*40}", flush=True)
    cmd = [sys.executable, str(script)]
    if days is not None:
        cmd += ["--days", str(days)]
    result = subprocess.run(cmd, cwd=str(script.parent))
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("source", nargs="?", default=None)
    parser.add_argument("--days", type=int, default=None)
    args, _ = parser.parse_known_args()

    if not args.source:
        print(__doc__)
        sys.exit(0)

    source = args.source.lower()
    if source not in SOURCES and source != "all":
        print(f"Unknown source '{source}'. Options: {', '.join(SOURCES)} or 'all'")
        sys.exit(1)

    if source == "all":
        for name in ["whoop", "intervals"]:
            run(name, SOURCES[name], args.days)
    else:
        run(source, SOURCES[source], args.days)
