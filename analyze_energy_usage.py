#!/usr/bin/env python3
"""
Analyze end-of-turn remaining energy from ai_debug.log.

Usage:
    python analyze_energy_usage.py
    python analyze_energy_usage.py --limit 2000
    python analyze_energy_usage.py --log /path/to/ai_debug.log
"""

import argparse
import re
from collections import Counter, defaultdict
from pathlib import Path


DEFAULT_LOG_WSL = "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/ai_debug.log"
DEFAULT_LOG_WIN = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log"


TURN_END_RE = re.compile(
    r"\[TURN_END\].*floor=(?P<floor>\d+).*turn=(?P<turn>\d+).*energy_remaining=(?P<energy>\d+)"
)


def parse_lines(lines):
    entries = []
    for line in lines:
        match = TURN_END_RE.search(line)
        if not match:
            continue
        entries.append(
            {
                "floor": int(match.group("floor")),
                "turn": int(match.group("turn")),
                "energy": int(match.group("energy")),
            }
        )
    return entries


def summarize(entries):
    total = len(entries)
    if total == 0:
        print("No TURN_END entries found.")
        return

    unused = [e for e in entries if e["energy"] > 0]
    unused_rate = len(unused) / total * 100
    avg_remaining = sum(e["energy"] for e in entries) / total

    print("=" * 80)
    print("ENERGY USAGE SUMMARY")
    print("=" * 80)
    print(f"Total turns analyzed: {total}")
    print(f"Turns with energy remaining: {len(unused)} ({unused_rate:.1f}%)")
    print(f"Average energy remaining: {avg_remaining:.2f}")

    max_remaining = max(e["energy"] for e in entries)
    print(f"Max energy remaining: {max_remaining}")

    by_floor = defaultdict(list)
    for e in entries:
        by_floor[e["floor"]].append(e["energy"])

    floor_unused = []
    for floor, energies in by_floor.items():
        unused_count = sum(1 for e in energies if e > 0)
        unused_rate_floor = unused_count / len(energies) * 100
        floor_unused.append((unused_rate_floor, floor, len(energies)))

    floor_unused.sort(reverse=True)
    print("\nTop floors by unused-energy rate:")
    for rate, floor, count in floor_unused[:10]:
        print(f"  Floor {floor:2d}: {rate:5.1f}% (n={count})")

    energy_counts = Counter(e["energy"] for e in entries)
    print("\nEnergy remaining distribution:")
    for energy in sorted(energy_counts.keys()):
        print(f"  {energy}: {energy_counts[energy]}")


def main():
    parser = argparse.ArgumentParser(description="Analyze remaining energy at turn end.")
    parser.add_argument("--log", type=str, default=None, help="Path to ai_debug.log")
    parser.add_argument("--limit", type=int, default=0, help="Only analyze last N lines")
    args = parser.parse_args()

    log_path = Path(args.log) if args.log else Path(
        DEFAULT_LOG_WSL if Path(DEFAULT_LOG_WSL).exists() else DEFAULT_LOG_WIN
    )

    if not log_path.exists():
        print(f"Log not found: {log_path}")
        return

    with log_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
        if args.limit and args.limit > 0:
            lines = lines[-args.limit :]

    entries = parse_lines(lines)
    summarize(entries)


if __name__ == "__main__":
    main()
