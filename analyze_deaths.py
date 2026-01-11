#!/usr/bin/env python3
"""
Analyze death patterns from recent Slay the Spire runs.

Usage:
    python analyze_deaths.py
    python analyze_deaths.py --count 300 --character IRONCLAD
"""

import argparse
import json
import os
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_RUNS_DIR_WSL = "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs"
DEFAULT_RUNS_DIR_WIN = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\runs"


def load_run(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def collect_runs(runs_dir, character, count):
    runs_path = Path(runs_dir) / character
    if not runs_path.exists():
        raise FileNotFoundError(f"Directory not found: {runs_path}")

    run_files = sorted(
        runs_path.glob("*.run"),
        key=os.path.getmtime,
        reverse=True,
    )[:count]
    run_files.reverse()

    runs = []
    for path in run_files:
        run = load_run(path)
        if run:
            runs.append(run)
    return runs


def print_death_summary(runs):
    deaths = [r for r in runs if not r.get("victory", False)]
    total = len(runs)
    if not deaths:
        print("No deaths found in the selected runs.")
        return

    print("=" * 80)
    print("DEATH PATTERN SUMMARY")
    print("=" * 80)
    print(f"Runs analyzed: {total}")
    print(f"Deaths:        {len(deaths)}")

    floor_counts = Counter(r.get("floor_reached", 0) for r in deaths)
    top_floors = floor_counts.most_common(10)

    print("\nMost common death floors:")
    for floor, count in top_floors:
        print(f"  Floor {floor:3d}: {count}")

    cause_counts = Counter(r.get("killed_by", "UNKNOWN") for r in deaths)
    top_causes = cause_counts.most_common(10)

    print("\nMost common death causes:")
    for cause, count in top_causes:
        print(f"  {cause}: {count}")

    enemy_counts = Counter()
    for run in deaths:
        for entry in run.get("damage_taken", []):
            enemy = entry.get("enemies")
            if enemy:
                enemy_counts[enemy] += 1

    if enemy_counts:
        print("\nMost frequent enemies in damage logs (deaths only):")
        for enemy, count in enemy_counts.most_common(10):
            print(f"  {enemy}: {count}")


def print_floor_histogram(runs, bucket=5):
    deaths = [r for r in runs if not r.get("victory", False)]
    if not deaths:
        return

    buckets = defaultdict(int)
    for run in deaths:
        floor = run.get("floor_reached", 0)
        bucket_floor = (floor // bucket) * bucket
        buckets[bucket_floor] += 1

    print("\nDeath floor histogram:")
    for bucket_floor in sorted(buckets.keys()):
        start = bucket_floor
        end = bucket_floor + bucket - 1
        print(f"  Floors {start:2d}-{end:2d}: {buckets[bucket_floor]}")


def main():
    parser = argparse.ArgumentParser(description="Analyze death patterns.")
    parser.add_argument("--count", type=int, default=300, help="Runs to include.")
    parser.add_argument(
        "--character",
        type=str,
        default="IRONCLAD",
        help="Character folder to analyze.",
    )
    parser.add_argument("--bucket", type=int, default=5, help="Histogram bucket size.")
    args = parser.parse_args()

    runs_dir = (
        DEFAULT_RUNS_DIR_WSL
        if os.path.exists(DEFAULT_RUNS_DIR_WSL)
        else DEFAULT_RUNS_DIR_WIN
    )

    runs = collect_runs(runs_dir, args.character, args.count)
    if not runs:
        print("No runs found.")
        return

    print_death_summary(runs)
    print_floor_histogram(runs, args.bucket)


if __name__ == "__main__":
    main()
