"""
Analyze AI training progress for Act 1 win rate and combat metrics.

Usage:
  python analysis_scripts/analyze_training_progress.py
  python analysis_scripts/analyze_training_progress.py --window 200 --step 50 --series
  python analysis_scripts/analyze_training_progress.py --game-dir "D:/SteamLibrary/steamapps/common/SlayTheSpire"
"""

import argparse
import bisect
import json
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


def extract_combat_stats(run: dict) -> Tuple[int, float, float]:
    combats = run.get("damage_taken", []) or []
    if not combats:
        return 0, 0.0, 0.0
    total_turns = 0
    total_damage = 0
    for entry in combats:
        total_turns += int(entry.get("turns", 0) or 0)
        total_damage += int(entry.get("damage", 0) or 0)
    num = len(combats)
    avg_turns = total_turns / num if num else 0.0
    avg_damage = total_damage / num if num else 0.0
    return num, avg_turns, avg_damage


def summarize_window(runs: List[dict], min_floor: int) -> dict:
    if not runs:
        return {
            "samples": 0,
            "act1_win_rate": 0.0,
            "avg_combat_turns": 0.0,
            "avg_combat_damage": 0.0,
            "avg_combats_per_run": 0.0,
        }
    wins = 0
    total_combats = 0
    total_avg_turns = 0.0
    total_avg_damage = 0.0

    for run in runs:
        floor_reached = int(run.get("floor_reached", 0) or 0)
        if floor_reached >= min_floor:
            wins += 1
        combats, avg_turns, avg_damage = extract_combat_stats(run)
        total_combats += combats
        total_avg_turns += avg_turns
        total_avg_damage += avg_damage

    samples = len(runs)
    return {
        "samples": samples,
        "act1_win_rate": (wins / samples) * 100.0,
        "avg_combat_turns": total_avg_turns / samples,
        "avg_combat_damage": total_avg_damage / samples,
        "avg_combats_per_run": total_combats / samples,
    }


def analyze_training_progress(
    game_dir: Path,
    character: str,
    window: int,
    step: int,
    tolerance: int,
    min_floor: int,
    series: bool,
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

    summary = summarize_window(recent_runs, min_floor)

    print("Training Progress Summary")
    print("=" * 60)
    print(f"Character: {character}")
    print(f"Samples: {summary['samples']}")
    print(f"Act 1 win rate: {summary['act1_win_rate']:.2f}% (min floor {min_floor})")
    print(f"Avg combat turns: {summary['avg_combat_turns']:.2f}")
    print(f"Avg damage per combat: {summary['avg_combat_damage']:.2f}")
    print(f"Avg combats per run: {summary['avg_combats_per_run']:.2f}")
    if missing:
        print(f"Missing/unmatched runs: {missing}")
    print("=" * 60)

    if series and window > 0 and step > 0:
        print("Rolling Window Series")
        print("=" * 60)
        start = max(0, len(matched_runs) - window)
        for idx in range(start, len(matched_runs) + 1, step):
            chunk = matched_runs[max(0, idx - window):idx]
            if not chunk:
                continue
            roll = summarize_window(chunk, min_floor)
            end_idx = idx
            print(
                f"End {end_idx:5d} | samples={roll['samples']:4d} "
                f"act1_win={roll['act1_win_rate']:.2f}% "
                f"turns={roll['avg_combat_turns']:.2f} "
                f"dmg={roll['avg_combat_damage']:.2f} "
                f"combats={roll['avg_combats_per_run']:.2f}"
            )
        print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze AI training progress metrics.")
    parser.add_argument("--game-dir", default=str(DEFAULT_GAME_DIR), help="Slay the Spire game directory")
    parser.add_argument("--character", default="IRONCLAD", help="Character folder under runs/")
    parser.add_argument("--window", type=int, default=200, help="Window size for recent stats (0 = all)")
    parser.add_argument("--step", type=int, default=50, help="Step size for rolling series")
    parser.add_argument("--series", action="store_true", help="Print rolling window series")
    parser.add_argument("--tolerance", type=int, default=300, help="Timestamp match tolerance in seconds")
    parser.add_argument("--min-floor", type=int, default=17, help="Floor threshold for Act 1 clear")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    analyze_training_progress(
        game_dir=Path(args.game_dir),
        character=args.character,
        window=args.window,
        step=args.step,
        tolerance=args.tolerance,
        min_floor=args.min_floor,
        series=args.series,
    )
