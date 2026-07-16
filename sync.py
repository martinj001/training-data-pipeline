"""
CLI dispatcher for training-data-pipeline.

Usage:
  python sync.py whoop                  — incremental sync (auto-detects last record)
  python sync.py whoop --days 30        — sync last 30 days regardless of DB state
  python sync.py intervals              — sync Intervals.icu (Zwift + Garmin activities)
  python sync.py intervals --days 60    — sync last 60 days
  python sync.py trainingpeaks          — ingest all TrainingPeaks zip files
  python sync.py manual                 — ingest manual Excel logs (last 30 days)
  python sync.py manual --days 0        — ingest all manual logs
  python sync.py all                    — run whoop + intervals + manual (incremental)
  python sync.py all --days 14          — run all sources for last 14 days
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SOURCES = {
    "whoop": ROOT / "src" / "whoop" / "sync.py",
    "intervals": ROOT / "src" / "intervals" / "sync.py",
    "trainingpeaks": ROOT / "src" / "trainingpeaks" / "ingestor.py",
    "manual": ROOT / "src" / "manual" / "sync.py",
}

ALL_SOURCES = ["whoop", "intervals", "manual"]

# Always use THIS repo's own venv, regardless of whatever python happens to be
# active in the calling shell -- a different repo's venv being active (e.g.
# after cd-ing over from another project) silently used the wrong
# interpreter here before, causing ModuleNotFoundError for deps (openpyxl)
# that only this repo's venv has installed.
VENV_PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _python() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    print(f"Warning: {VENV_PYTHON} not found -- falling back to sys.executable ({sys.executable})", file=sys.stderr)
    return sys.executable


def run(name, script, days=None):
    print(f"\n{'='*40}", flush=True)
    print(f"  {name}", flush=True)
    print(f"{'='*40}", flush=True)
    cmd = [_python(), str(script)]
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
        for name in ALL_SOURCES:
            run(name, SOURCES[name], args.days)
    else:
        run(source, SOURCES[source], args.days)
