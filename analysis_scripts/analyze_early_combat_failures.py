"""
Analyze early combat failures for AI training runs.

Outputs:
  - Death floor distribution
  - Killed-by distribution
  - Average damage/turns for first N combats

Usage:
  python analysis_scripts/analyze_early_combat_failures.py
  python analysis_scripts/analyze_early_combat_failures.py --window 300 --first-combats 3 --series
"""

import argparse
import bisect
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DEFAULT_GAME_DIR = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire")


def load_ai_games(ai_file: Path) -> List[int]:
    if not ai_file.exists():
        print(f"AI game list not found: {ai_file}")
        return []
    ids = []
    for line in ai_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ids.append(int(line))
        except ValueError:
            continue
    return ids


def index_run_files(runs_dir: Path, character: str) -> Tuple[List[int], Dict[int, Path]]:
    run_root = runs_dir / character
    timestamps: List[int] = []
    mapping: Dict[int, Path] = {}
    if not run_root.exists():
        return timestamps, mapping
    for run_file in run_root.glob("*.run"):
        try:
            ts = int(run_file.stem)
        except ValueError:
            continue
        timestamps.append(ts)
        mapping[ts] = run_file
    timestamps.sort()
    return timestamps, mapping


def find_run_file(
    game_timestamp: int,
    timestamps: List[int],
    mapping: Dict[int, Path],
    tolerance: int,
) -> Optional[Path]:
    if game_timestamp in mapping:
        return mapping[game_timestamp]
    if not timestamps:
        return None
    pos = bisect.bisect_left(timestamps, game_timestamp)
    candidates = []
    if pos < len(timestamps):
        candidates.append(timestamps[pos])
    if pos > 0:
        candidates.append(timestamps[pos - 1])
    if not candidates:
        return None
    closest = min(candidates, key=lambda ts: abs(ts - game_timestamp))
    if abs(closest - game_timestamp) <= tolerance:
        return mapping.get(closest)
    return None


def load_run_data(run_file: Path) -> Optional[dict]:
    try:
        return json.loads(run_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def extract_first_combat_stats(run: dict, first_n: int) -> Tuple[int, float, float]:
    combats = run.get("damage_taken", []) or []
    if not combats:
        return 0, 0.0, 0.0
    total_turns = 0
    total_damage = 0
    count = min(first_n, len(combats))
    for entry in combats[:count]:
        total_turns += int(entry.get("turns", 0) or 0)
        total_damage += int(entry.get("damage", 0) or 0)
    avg_turns = total_turns / count if count else 0.0
    avg_damage = total_damage / count if count else 0.0
    return count, avg_turns, avg_damage


def summarize_runs(runs: List[dict], first_n: int) -> dict:
    death_floors = Counter()
    killed_by = Counter()
    total_first_combats = 0
    total_first_turns = 0.0
    total_first_damage = 0.0

    for run in runs:
        floor = int(run.get("floor_reached", 0) or 0)
        death_floors[floor] += 1
        killer = run.get("killed_by") or "UNKNOWN"
        killed_by[str(killer)] += 1

        combats, avg_turns, avg_damage = extract_first_combat_stats(run, first_n)
        if combats:
            total_first_combats += combats
            total_first_turns += avg_turns
            total_first_damage += avg_damage

    samples = len(runs)
    avg_first_turns = total_first_turns / samples if samples else 0.0
    avg_first_damage = total_first_damage / samples if samples else 0.0

    return {
        "samples": samples,
        "death_floors": death_floors,
        "killed_by": killed_by,
        "avg_first_turns": avg_first_turns,
        "avg_first_damage": avg_first_damage,
        "avg_first_combats": total_first_combats / samples if samples else 0.0,
    }


def analyze_early_failures(
    game_dir: Path,
    character: str,
    window: int,
    step: int,
    tolerance: int,
    first_n: int,
    series: bool,
    top_n: int,
) -> None:
    runs_dir = game_dir / "runs"
    ai_games_file = runs_dir / "ai_games.txt"
    ai_game_ids = load_ai_games(ai_games_file)
    if not ai_game_ids:
        return

    timestamps, mapping = index_run_files(runs_dir, character)
    if not mapping:
        print(f"No run files found for character: {character}")
        return

    matched_runs = []
    missing = 0
    for game_id in ai_game_ids:
        run_file = find_run_file(game_id, timestamps, mapping, tolerance)
        if not run_file:
            missing += 1
            continue
        data = load_run_data(run_file)
        if not data:
            missing += 1
            continue
        matched_runs.append(data)

    if not matched_runs:
        print("No AI runs matched to run files.")
        return

    if window > 0 and len(matched_runs) > window:
        recent_runs = matched_runs[-window:]
    else:
        recent_runs = matched_runs

    summary = summarize_runs(recent_runs, first_n)

    print("Early Combat Failure Summary")
    print("=" * 70)
    print(f"Character: {character}")
    print(f"Samples: {summary['samples']}")
    print(f"Avg first {first_n} combats: {summary['avg_first_combats']:.2f}")
    print(f"Avg turns (first {first_n} combats): {summary['avg_first_turns']:.2f}")
    print(f"Avg damage (first {first_n} combats): {summary['avg_first_damage']:.2f}")
    if missing:
        print(f"Missing/unmatched runs: {missing}")
    print("=" * 70)

    print("Top Death Floors")
    for floor, count in summary["death_floors"].most_common(top_n):
        print(f"  Floor {floor:2d}: {count}")
    print("=" * 70)

    print("Top Killed-By")
    for name, count in summary["killed_by"].most_common(top_n):
        print(f"  {name}: {count}")
    print("=" * 70)

    if series and window > 0 and step > 0:
        print("Rolling Window Series (avg early damage/turns)")
        print("=" * 70)
        start = max(0, len(matched_runs) - window)
        for idx in range(start, len(matched_runs) + 1, step):
            chunk = matched_runs[max(0, idx - window):idx]
            if not chunk:
                continue
            roll = summarize_runs(chunk, first_n)
            end_idx = idx
            print(
                f"End {end_idx:5d} | samples={roll['samples']:4d} "
                f"turns={roll['avg_first_turns']:.2f} "
                f"dmg={roll['avg_first_damage']:.2f}"
            )
        print("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze early combat failures for AI runs.")
    parser.add_argument("--game-dir", default=str(DEFAULT_GAME_DIR), help="Slay the Spire game directory")
    parser.add_argument("--character", default="IRONCLAD", help="Character folder under runs/")
    parser.add_argument("--window", type=int, default=300, help="Window size for recent stats (0 = all)")
    parser.add_argument("--step", type=int, default=50, help="Step size for rolling series")
    parser.add_argument("--series", action="store_true", help="Print rolling window series")
    parser.add_argument("--tolerance", type=int, default=300, help="Timestamp match tolerance in seconds")
    parser.add_argument("--first-combats", type=int, default=3, help="Number of early combats to average")
    parser.add_argument("--top", type=int, default=10, help="Top N entries to show for floor/killer lists")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    analyze_early_failures(
        game_dir=Path(args.game_dir),
        character=args.character,
        window=args.window,
        step=args.step,
        tolerance=args.tolerance,
        first_n=args.first_combats,
        series=args.series,
        top_n=args.top,
    )
