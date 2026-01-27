"""
Analyze action distribution from ai_debug.log, grouped by game and floor.

Usage:
  python analysis_scripts/analyze_action_distribution.py
  python analysis_scripts/analyze_action_distribution.py --tail-lines 200000 --top 10
"""

import argparse
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_LOG = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log")

GAME_RE = re.compile(r"Starting game #(\d+)")
ACTION_RE = re.compile(r"Got action:\s+([A-Za-z_]+)")
TURN_END_RE = re.compile(r"\[TURN_END\]\s+floor=(\d+)\s+turn=(\d+)")


def load_lines(path: Path, tail_lines: int) -> List[str]:
    if not path.exists():
        print(f"Log not found: {path}")
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if tail_lines > 0:
        return lines[-tail_lines:]
    return lines


def analyze(lines: List[str]) -> Dict[Tuple[int, int], dict]:
    current_game = None
    actions_this_turn: List[str] = []
    stats: Dict[Tuple[int, int], dict] = {}

    for line in lines:
        match_game = GAME_RE.search(line)
        if match_game:
            current_game = int(match_game.group(1))
            actions_this_turn = []
            continue

        match_action = ACTION_RE.search(line)
        if match_action:
            actions_this_turn.append(match_action.group(1))
            continue

        match_turn = TURN_END_RE.search(line)
        if match_turn:
            if current_game is None:
                actions_this_turn = []
                continue
            floor = int(match_turn.group(1))
            key = (current_game, floor)
            if key not in stats:
                stats[key] = {
                    "turns": 0,
                    "turns_with_play": 0,
                    "actions": defaultdict(int),
                }
            entry = stats[key]
            entry["turns"] += 1
            played = any(a in ("PlayCardAction", "PotionAction") for a in actions_this_turn)
            if played:
                entry["turns_with_play"] += 1
            for action in actions_this_turn:
                entry["actions"][action] += 1
            actions_this_turn = []

    return stats


def print_summary(stats: Dict[Tuple[int, int], dict], top_n: int) -> None:
    if not stats:
        print("No turn/action data found.")
        return

    rows = []
    for (game_id, floor), entry in stats.items():
        turns = entry["turns"]
        played = entry["turns_with_play"]
        skip_rate = (1 - (played / turns)) * 100 if turns else 0.0
        rows.append((skip_rate, game_id, floor, turns, played))

    rows.sort(reverse=True)

    print("Worst Skip-Rate Floors")
    print("=" * 70)
    for skip_rate, game_id, floor, turns, played in rows[:top_n]:
        print(
            f"Game {game_id:3d} Floor {floor:2d} | turns={turns:2d} "
            f"played={played:2d} skip_rate={skip_rate:6.2f}%"
        )
    print("=" * 70)

    print("Last 10 Floors (chronological)")
    print("=" * 70)
    tail = sorted(rows, key=lambda r: (r[1], r[2]))[-10:]
    for skip_rate, game_id, floor, turns, played in tail:
        print(
            f"Game {game_id:3d} Floor {floor:2d} | turns={turns:2d} "
            f"played={played:2d} skip_rate={skip_rate:6.2f}%"
        )
    print("=" * 70)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze action distribution per floor.")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG), help="Path to ai_debug.log")
    parser.add_argument("--tail-lines", type=int, default=200000, help="Analyze only last N lines (0 = all)")
    parser.add_argument("--top", type=int, default=10, help="Top N worst floors to display")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    lines = load_lines(Path(args.log_path), args.tail_lines)
    if not lines:
        raise SystemExit(1)
    stats = analyze(lines)
    print_summary(stats, args.top)
