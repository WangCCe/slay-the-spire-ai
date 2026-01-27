"""
Analyze combat turn skips (EndTurnAction with no plays) from ai_debug.log.

Usage:
  python analysis_scripts/analyze_turn_skips.py
  python analysis_scripts/analyze_turn_skips.py --log-path "D:/SteamLibrary/steamapps/common/SlayTheSpire/ai_debug.log"
  python analysis_scripts/analyze_turn_skips.py --tail-lines 200000
"""

import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional


DEFAULT_LOG = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log")

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


def analyze_turns(lines: List[str]) -> Dict[str, float]:
    total_turns = 0
    skipped_turns = 0
    action_counts: Dict[str, int] = {}
    actions_this_turn: List[str] = []

    for line in lines:
        action_match = ACTION_RE.search(line)
        if action_match:
            action = action_match.group(1)
            actions_this_turn.append(action)
            action_counts[action] = action_counts.get(action, 0) + 1
            continue

        turn_match = TURN_END_RE.search(line)
        if turn_match:
            total_turns += 1
            played_any = any(a in ("PlayCardAction", "PotionAction") for a in actions_this_turn)
            if not played_any:
                skipped_turns += 1
            actions_this_turn = []

    skip_rate = (skipped_turns / total_turns * 100.0) if total_turns else 0.0
    avg_actions = (sum(action_counts.values()) / total_turns) if total_turns else 0.0

    return {
        "total_turns": total_turns,
        "skipped_turns": skipped_turns,
        "skip_rate": skip_rate,
        "avg_actions": avg_actions,
        "action_counts": action_counts,
    }


def print_report(stats: Dict[str, float]) -> None:
    print("Turn Skip Analysis")
    print("=" * 60)
    print(f"Total turns: {stats['total_turns']}")
    print(f"Skipped turns (no play/potion): {stats['skipped_turns']}")
    print(f"Skip rate: {stats['skip_rate']:.2f}%")
    print(f"Avg actions per turn: {stats['avg_actions']:.2f}")
    print("=" * 60)

    action_counts = stats.get("action_counts", {})
    if action_counts:
        print("Action counts")
        for name, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {name}: {count}")
        print("=" * 60)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze turn skips from ai_debug.log.")
    parser.add_argument("--log-path", default=str(DEFAULT_LOG), help="Path to ai_debug.log")
    parser.add_argument("--tail-lines", type=int, default=200000, help="Analyze only last N lines (0 = all)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    lines = load_lines(Path(args.log_path), args.tail_lines)
    if not lines:
        raise SystemExit(1)
    stats = analyze_turns(lines)
    print_report(stats)
