#!/usr/bin/env python3
"""
Analyze recent Slay the Spire runs to track AI performance.

Usage:
    python analyze_runs.py              # Last 20 runs
    python analyze_runs.py 50           # Last 50 runs
    python analyze_runs.py 100 weekly   # Last 100 runs grouped by week
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def load_run(filepath):
    """Load a run JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load {filepath}: {e}", file=sys.stderr)
        return None


def analyze_runs(runs_dir, count=20, group_by=None):
    """Analyze recent run files.

    Args:
        runs_dir: Path to runs directory
        count: Number of recent runs to analyze
        group_by: Group results ('daily', 'weekly', None)
    """
    runs_path = Path(runs_dir) / "IRONCLAD"

    if not runs_path.exists():
        print(f"Error: Directory not found: {runs_path}")
        return

    # Get recent run files
    run_files = sorted(runs_path.glob("*.run"), key=os.path.getmtime, reverse=True)[:count]

    if not run_files:
        print(f"No run files found in {runs_path}")
        return

    print(f"\n{'='*70}")
    print(f"Analyzing {len(run_files)} recent runs from {runs_dir}")
    print(f"{'='*70}\n")

    # Collect statistics
    runs_data = []
    for run_file in run_files:
        run = load_run(run_file)
        if run:
            runs_data.append({
                'filename': run_file.name,
                'victory': run.get('victory', False),
                'floor': run.get('floor_reached', 0),
                'score': run.get('score', 0),
                'playtime': run.get('playtime', 0),
                'ascension': run.get('ascension_level', 0),
                'deck_size': len(run.get('master_deck', [])),
                'relics': len(run.get('relics', [])),
                'potions': len(run.get('potions_obtained', [])),
                'path': ''.join(run.get('path_per_floor', [])),
                'damage_taken': sum(d.get('damage', 0) for d in run.get('damage_taken', [])),
                'gold': run.get('gold_per_floor', [-1])[-1] if run.get('gold_per_floor') else 0,
                'max_hp': run.get('max_hp', 0),
                'character': run.get('character_chosen', 'UNKNOWN'),
                'local_time': run.get('local_time', ''),
            })

    if not runs_data:
        print("No valid run data found.")
        return

    # Reverse to show chronological order
    runs_data.reverse()

    # Print summary statistics
    print_summary(runs_data, group_by)

    # Print detailed run info
    print_detailed_runs(runs_data)


def print_summary(runs_data, group_by):
    """Print summary statistics."""
    total = len(runs_data)
    victories = sum(1 for r in runs_data if r['victory'])
    win_rate = victories / total * 100 if total > 0 else 0

    avg_floor = sum(r['floor'] for r in runs_data) / total if total > 0 else 0
    max_floor = max(r['floor'] for r in runs_data) if runs_data else 0

    avg_score = sum(r['score'] for r in runs_data) / total if total > 0 else 0

    floors_reached = defaultdict(int)
    for r in runs_data:
        floors_reached[r['floor']] += 1

    print("📊 Overall Statistics")
    print(f"  Total runs:        {total}")
    print(f"  Win rate:          {win_rate:.1f}% ({victories}/{total})")
    print(f"  Avg floor:         {avg_floor:.1f}")
    print(f"  Max floor:         {max_floor}")
    print(f"  Avg score:         {avg_score:.1f}")

    print("\n🏆 Floor Distribution (where games ended)")
    for floor in sorted(floors_reached.keys()):
        print(f"  Floor {floor:2d}:         {floors_reached[floor]:3d} runs")

    # Progress tracking
    print("\n📈 Recent Performance Trend (last 10 runs)")
    recent = runs_data[-10:]
    recent_wr = sum(1 for r in recent if r['victory']) / len(recent) * 100
    recent_floor = sum(r['floor'] for r in recent) / len(recent)
    all_wr = sum(1 for r in runs_data if r['victory']) / len(runs_data) * 100
    all_floor = sum(r['floor'] for r in runs_data) / len(runs_data)

    print(f"  Last 10 win rate:  {recent_wr:.1f}% (all: {all_wr:.1f}%)")
    print(f"  Last 10 avg floor: {recent_floor:.1f} (all: {all_floor:.1f})")

    if recent_wr > all_wr + 5:
        print(f"  ✅ Improving! ({recent_wr - all_wr:+.1f}% better)")
    elif recent_wr < all_wr - 5:
        print(f"  ⚠️  Declining ({recent_wr - all_wr:+.1f}% worse)")
    else:
        print(f"  ➡️  Stable")

    # Death analysis
    deaths = [r for r in runs_data if not r['victory']]
    if deaths:
        print("\n💀 Death Analysis")
        death_floors = [r['floor'] for r in deaths]
        avg_death_floor = sum(death_floors) / len(death_floors)

        # Find most common death floor
        floor_counts = defaultdict(int)
        for f in death_floors:
            floor_counts[f] += 1
        most_common = max(floor_counts.items(), key=lambda x: x[1])

        print(f"  Avg death floor:   {avg_death_floor:.1f}")
        print(f"  Most common death: Floor {most_common[0]} ({most_common[1]} times)")


def print_detailed_runs(runs_data):
    """Print detailed information for each run."""
    print("\n" + "="*70)
    print("📋 Detailed Run Information")
    print("="*70)

    for i, run in enumerate(runs_data, 1):
        status = "✅ WIN" if run['victory'] else "❌ LOSS"
        time_str = run['local_time']
        if len(time_str) >= 12:
            formatted_time = f"{time_str[8:10]}:{time_str[10:12]}"
        else:
            formatted_time = "??"

        print(f"\nRun {i}: {status}")
        print(f"  Time:    {formatted_time}")
        print(f"  Floor:   {run['floor']}")
        print(f"  Score:   {run['score']}")
        print(f"  HP:      {run['max_hp'] if 'max_hp' in run else 'N/A'}")
        print(f"  Path:    {run['path']}")
        print(f"  Deck:    {run['deck_size']} cards")
        print(f"  Relics:  {run['relics']}")
        print(f"  Damage:  {run['damage_taken']} total HP")
        print(f"  Gold:    {run['gold']}")


if __name__ == "__main__":
    # Default path (support both Windows and WSL)
    import os
    if os.path.exists("/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs"):
        runs_dir = "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs"
    else:
        runs_dir = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\runs"

    # Parse arguments
    count = 20
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
        except ValueError:
            print(f"Invalid count: {sys.argv[1]}")
            print("Usage: python analyze_runs.py [count] [group_by]")
            sys.exit(1)

    group_by = None
    if len(sys.argv) > 2:
        group_by = sys.argv[2]

    analyze_runs(runs_dir, count, group_by)
