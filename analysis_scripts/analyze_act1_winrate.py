"""
Compute Act 1 win rate for AI games.

Usage (run from project directory or anywhere):
    python D:/PycharmProjects/slay-the-spire-ai/analysis_scripts/analyze_act1_winrate.py
    python D:/PycharmProjects/slay-the-spire-ai/analysis_scripts/analyze_act1_winrate.py --game-dir "D:/SteamLibrary/steamapps/common/SlayTheSpire"

Optional:
    --character IRONCLAD
    --window 200
    --tolerance 300
    --min-floor 17
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


def analyze_act1_winrate(
    game_dir: Path,
    character: str,
    window: int,
    tolerance: int,
    min_floor: int,
) -> None:
    runs_dir = game_dir / "runs"
    ai_games_file = runs_dir / "ai_games.txt"
    ai_game_ids = load_ai_games(ai_games_file)
    if not ai_game_ids:
        return

    if window > 0:
        ai_game_ids = ai_game_ids[-window:]

    timestamps, mapping = index_run_files(runs_dir, character)
    if not mapping:
        print(f"No run files found for character: {character}")
        return

    total = 0
    act1_wins = 0
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
        total += 1
        floor_reached = int(data.get("floor_reached", 0) or 0)
        if floor_reached >= min_floor:
            act1_wins += 1

    if total == 0:
        print("No AI runs matched to run files.")
        return

    win_rate = (act1_wins / total) * 100.0

    print("Act 1 Win Rate (AI)")
    print("=" * 50)
    print(f"Character: {character}")
    print(f"Samples: {total}")
    print(f"Act 1 wins: {act1_wins}")
    print(f"Act 1 win rate: {win_rate:.2f}%")
    if missing:
        print(f"Missing/unmatched runs: {missing}")
    print("=" * 50)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Act 1 win rate for AI runs.")
    parser.add_argument("--game-dir", default=str(DEFAULT_GAME_DIR), help="Slay the Spire game directory")
    parser.add_argument("--character", default="IRONCLAD", help="Character folder under runs/")
    parser.add_argument("--window", type=int, default=0, help="Analyze only last N AI games (0 = all)")
    parser.add_argument("--tolerance", type=int, default=300, help="Timestamp match tolerance in seconds")
    parser.add_argument("--min-floor", type=int, default=17, help="Floor threshold for Act 1 clear")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    analyze_act1_winrate(
        game_dir=Path(args.game_dir),
        character=args.character,
        window=args.window,
        tolerance=args.tolerance,
        min_floor=args.min_floor,
    )
