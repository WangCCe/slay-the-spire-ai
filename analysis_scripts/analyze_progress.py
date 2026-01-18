#!/usr/bin/env python3
"""
Analyze training progress by bucketing recent Slay the Spire runs.

Usage:
    python analyze_progress.py
    python analyze_progress.py --count 500 --bucket 50
    python analyze_progress.py --character IRONCLAD
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path


DEFAULT_RUNS_DIR_WSL = "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs"
DEFAULT_RUNS_DIR_WIN = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\runs"


def load_run(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def parse_local_time(value):
    if not value or len(value) < 12:
        return None
    try:
        return datetime.strptime(value[:12], "%Y%m%d%H%M")
    except ValueError:
        return None


def format_time(value):
    if not value:
        return "unknown"
    return value.strftime("%m-%d %H:%M")


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
        if not run:
            continue
        runs.append(
            {
                "filename": path.name,
                "victory": run.get("victory", False),
                "floor": run.get("floor_reached", 0),
                "score": run.get("score", 0),
                "deck_size": len(run.get("master_deck", [])),
                "relics": len(run.get("relics", [])),
                "damage_taken": sum(
                    d.get("damage", 0) for d in run.get("damage_taken", [])
                ),
                "local_time": parse_local_time(run.get("local_time", "")),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime),
            }
        )
    return runs


def bucket_runs(runs, bucket_size):
    buckets = []
    for i in range(0, len(runs), bucket_size):
        chunk = runs[i : i + bucket_size]
        if chunk:
            buckets.append(chunk)
    return buckets


def summarize_bucket(bucket, index_start):
    total = len(bucket)
    wins = sum(1 for r in bucket if r["victory"])
    avg_floor = sum(r["floor"] for r in bucket) / total
    max_floor = max(r["floor"] for r in bucket)
    avg_score = sum(r["score"] for r in bucket) / total
    avg_damage = sum(r["damage_taken"] for r in bucket) / total

    times = [r["local_time"] for r in bucket if r["local_time"]]
    time_start = min(times) if times else None
    time_end = max(times) if times else None

    return {
        "index_start": index_start,
        "index_end": index_start + total - 1,
        "total": total,
        "win_rate": (wins / total) * 100,
        "avg_floor": avg_floor,
        "max_floor": max_floor,
        "avg_score": avg_score,
        "avg_damage": avg_damage,
        "time_start": time_start,
        "time_end": time_end,
    }


def print_progress(buckets):
    print("=" * 80)
    print("TRAINING PROGRESS DASHBOARD")
    print("=" * 80)
    print(
        f"{'Bucket':<12} {'Runs':<6} {'Win%':<6} {'AvgFloor':<9} "
        f"{'Max':<5} {'AvgScore':<9} {'AvgDmg':<8} {'TimeRange'}"
    )
    print("-" * 80)

    summaries = []
    run_index = 1
    for bucket in buckets:
        summary = summarize_bucket(bucket, run_index)
        summaries.append(summary)
        time_range = f"{format_time(summary['time_start'])} - {format_time(summary['time_end'])}"
        print(
            f"{summary['index_start']:>3}-{summary['index_end']:<6} "
            f"{summary['total']:<6} "
            f"{summary['win_rate']:<6.1f} "
            f"{summary['avg_floor']:<9.2f} "
            f"{summary['max_floor']:<5} "
            f"{summary['avg_score']:<9.1f} "
            f"{summary['avg_damage']:<8.1f} "
            f"{time_range}"
        )
        run_index += summary["total"]

    print("-" * 80)
    print_trend(summaries)


def print_trend(summaries):
    if len(summaries) < 2:
        print("Not enough buckets to assess trend.")
        return

    last = summaries[-1]
    prev = summaries[-2]
    delta_floor = last["avg_floor"] - prev["avg_floor"]
    delta_win = last["win_rate"] - prev["win_rate"]

    trend = "stable"
    if delta_floor >= 1.0 or delta_win >= 2.0:
        trend = "improving"
    elif delta_floor <= -1.0 or delta_win <= -2.0:
        trend = "declining"

    print(
        f"Recent trend: {trend} "
        f"(avg_floor {delta_floor:+.2f}, win_rate {delta_win:+.1f}%)"
    )

    if len(summaries) >= 3:
        last_three = summaries[-3:]
        floors = [s["avg_floor"] for s in last_three]
        span = max(floors) - min(floors)
        if span <= 0.5:
            print("Plateau hint: last 3 buckets show <= 0.5 avg_floor variance.")


def main():
    parser = argparse.ArgumentParser(description="Training progress dashboard.")
    parser.add_argument("--count", type=int, default=300, help="Runs to include.")
    parser.add_argument("--bucket", type=int, default=50, help="Bucket size.")
    parser.add_argument(
        "--character",
        type=str,
        default="IRONCLAD",
        help="Character folder to analyze.",
    )
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

    buckets = bucket_runs(runs, args.bucket)
    print_progress(buckets)


if __name__ == "__main__":
    main()
