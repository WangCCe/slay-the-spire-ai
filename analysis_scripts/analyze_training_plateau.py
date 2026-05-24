#!/usr/bin/env python3
"""
Analyze recent Slay the Spire RL training runs for plateaus and route risk.

Usage:
    python analysis_scripts/analyze_training_plateau.py
    python analysis_scripts/analyze_training_plateau.py --count 500 --bucket 50
    python analysis_scripts/analyze_training_plateau.py --json
"""

import argparse
import json
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


DEFAULT_RUNS_DIR_WSL = "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs"
DEFAULT_RUNS_DIR_WIN = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\runs"
DEFAULT_LOG_WIN = r"D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log"

ACT1_ELITES = {"Gremlin Nob", "Lagavulin", "3 Sentries"}
ACT1_BOSSES = {"Slime Boss", "Hexaghost", "The Guardian"}


@dataclass
class RunSummary:
    filename: str
    mtime: float
    victory: bool
    floor: int
    score: int
    playtime: int
    killed_by: str
    ascension: Optional[int]
    path: List[str]
    deck_size: int
    relic_count: int
    damage_taken: int

    @property
    def act1_elites_taken(self) -> int:
        return sum(1 for symbol in self.path[:16] if symbol == "E")

    @property
    def reached_act1_boss(self) -> bool:
        return self.floor >= 16 or self.killed_by in ACT1_BOSSES

    @property
    def died_to_act1_elite(self) -> bool:
        return (not self.victory) and self.killed_by in ACT1_ELITES


def default_runs_dir() -> Path:
    if os.path.exists(DEFAULT_RUNS_DIR_WSL):
        return Path(DEFAULT_RUNS_DIR_WSL)
    return Path(DEFAULT_RUNS_DIR_WIN)


def load_run(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_run(path: Path) -> Optional[RunSummary]:
    data = load_run(path)
    if not data:
        return None

    path_taken = data.get("path_taken") or []
    if not isinstance(path_taken, list):
        path_taken = []

    damage_taken = 0
    for entry in data.get("damage_taken", []) or []:
        try:
            damage_taken += int(entry.get("damage", 0))
        except Exception:
            pass

    return RunSummary(
        filename=path.name,
        mtime=path.stat().st_mtime,
        victory=bool(data.get("victory", False)),
        floor=int(data.get("floor_reached", 0) or 0),
        score=int(data.get("score", 0) or 0),
        playtime=int(data.get("playtime", 0) or 0),
        killed_by=str(data.get("killed_by", "") or "UNKNOWN"),
        ascension=data.get("ascension_level"),
        path=[str(symbol) for symbol in path_taken],
        deck_size=len(data.get("master_deck", []) or []),
        relic_count=len(data.get("relics", []) or []),
        damage_taken=damage_taken,
    )


def collect_runs(runs_dir: Path, character: str, count: int) -> List[RunSummary]:
    runs_path = runs_dir / character
    if not runs_path.exists():
        raise FileNotFoundError(f"Directory not found: {runs_path}")

    files = sorted(runs_path.glob("*.run"), key=os.path.getmtime, reverse=True)[:count]
    summaries = [summary for path in files if (summary := summarize_run(path)) is not None]
    summaries.sort(key=lambda run: run.mtime)
    return summaries


def compute_slope(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    xs = list(range(1, len(values) + 1))
    mean_x = sum(xs) / len(xs)
    mean_y = sum(values) / len(values)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    return numerator / denominator if denominator else 0.0


def bucket_runs(runs: List[RunSummary], bucket_size: int) -> List[List[RunSummary]]:
    return [runs[i : i + bucket_size] for i in range(0, len(runs), bucket_size) if runs[i : i + bucket_size]]


def summarize_bucket(bucket: List[RunSummary], index_start: int) -> Dict[str, object]:
    total = len(bucket)
    wins = sum(1 for run in bucket if run.victory)
    floors = [run.floor for run in bucket]
    deaths = [run for run in bucket if not run.victory]
    elite_deaths = sum(1 for run in deaths if run.died_to_act1_elite)
    boss_reaches = sum(1 for run in bucket if run.reached_act1_boss)
    avg_elites = sum(run.act1_elites_taken for run in bucket) / total

    return {
        "index_start": index_start,
        "index_end": index_start + total - 1,
        "total": total,
        "wins": wins,
        "win_rate": (wins / total) * 100,
        "avg_floor": sum(floors) / total,
        "max_floor": max(floors),
        "boss_reach_rate": (boss_reaches / total) * 100,
        "elite_death_rate": (elite_deaths / total) * 100,
        "avg_act1_elites": avg_elites,
        "top_death": Counter(run.killed_by for run in deaths).most_common(1),
    }


def analyze_plateau(
    bucket_summaries: List[Dict[str, object]],
    elite_death_threshold: float = 45.0,
    floor_variance_threshold: float = 2.0,
    slope_threshold: float = 0.25,
    lookback: int = 5,
) -> Dict[str, object]:
    if not bucket_summaries:
        return {"plateau": False, "reason": "No buckets available."}

    recent = bucket_summaries[-lookback:]
    floors = [float(item["avg_floor"]) for item in recent]
    slope = compute_slope(floors)
    floor_range = max(floors) - min(floors) if floors else 0.0
    elite_death_rate = float(bucket_summaries[-1]["elite_death_rate"])
    win_rate = float(bucket_summaries[-1]["win_rate"])
    recent_win_rate = sum(float(item["win_rate"]) for item in recent) / len(recent)
    recent_elite_death_rate = sum(float(item["elite_death_rate"]) for item in recent) / len(recent)

    flat_floor = abs(slope) <= slope_threshold and floor_range <= floor_variance_threshold
    elite_wall = (
        elite_death_rate >= elite_death_threshold
        and recent_elite_death_rate >= elite_death_threshold
    )
    no_recent_wins = win_rate == 0.0
    no_lookback_wins = recent_win_rate == 0.0

    reasons = []
    if flat_floor:
        reasons.append(
            f"avg_floor flat over last {len(recent)} buckets "
            f"(range={floor_range:.2f}, slope={slope:+.3f})"
        )
    if elite_wall:
        reasons.append(
            f"elite wall persists (latest={elite_death_rate:.1f}%, "
            f"lookback_avg={recent_elite_death_rate:.1f}%)"
        )
    if no_recent_wins:
        reasons.append("latest bucket has 0 wins")
    if no_lookback_wins and len(recent) > 1:
        reasons.append(f"last {len(recent)} buckets have 0 wins")

    plateau = (flat_floor and (elite_wall or no_recent_wins)) or (elite_wall and no_lookback_wins)
    return {
        "plateau": plateau,
        "slope": slope,
        "floor_range": floor_range,
        "elite_wall": elite_wall,
        "recent_win_rate": recent_win_rate,
        "recent_elite_death_rate": recent_elite_death_rate,
        "reason": "; ".join(reasons) if reasons else "No plateau detected.",
    }


def parse_action_hints(log_path: Path, tail_lines: int) -> Dict[str, object]:
    if not log_path.exists():
        return {"log_found": False}

    try:
        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception as exc:
        return {"log_found": False, "error": str(exc)}

    if tail_lines > 0:
        lines = lines[-tail_lines:]

    patterns = {
        "command_errors": re.compile(r"command error|Game error|ERROR", re.IGNORECASE),
        "failed_actions": re.compile(r"failed action|consecutive_failures|invalid action", re.IGNORECASE),
        "skip_turns": re.compile(r"skip_rate|EndTurnAction", re.IGNORECASE),
        "stability_waits": re.compile(r"\[STABILITY_WAIT\]"),
    }
    counts = {name: 0 for name in patterns}
    for line in lines:
        for name, pattern in patterns.items():
            if pattern.search(line):
                counts[name] += 1

    counts["log_found"] = True
    counts["lines_analyzed"] = len(lines)
    return counts


def make_report(
    runs: List[RunSummary],
    bucket_size: int,
    action_hints: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    buckets = bucket_runs(runs, bucket_size)
    bucket_summaries = []
    index = 1
    for bucket in buckets:
        summary = summarize_bucket(bucket, index)
        bucket_summaries.append(summary)
        index += len(bucket)

    deaths = [run for run in runs if not run.victory]
    wins = sum(1 for run in runs if run.victory)
    total = len(runs)
    overall = {
        "total_runs": total,
        "wins": wins,
        "win_rate": (wins / total) * 100 if total else 0.0,
        "avg_floor": sum(run.floor for run in runs) / total if total else 0.0,
        "max_floor": max((run.floor for run in runs), default=0),
        "avg_playtime": sum(run.playtime for run in runs) / total if total else 0.0,
        "avg_act1_elites": sum(run.act1_elites_taken for run in runs) / total if total else 0.0,
        "boss_reach_rate": (
            sum(1 for run in runs if run.reached_act1_boss) / total * 100 if total else 0.0
        ),
        "elite_death_rate": (
            sum(1 for run in deaths if run.died_to_act1_elite) / total * 100 if total else 0.0
        ),
        "top_death_causes": Counter(run.killed_by for run in deaths).most_common(10),
        "ascensions": Counter(str(run.ascension) for run in runs).most_common(),
    }

    return {
        "overall": overall,
        "buckets": bucket_summaries,
        "plateau": analyze_plateau(bucket_summaries),
        "action_hints": action_hints or {},
    }


def print_report(report: Dict[str, object]) -> None:
    overall = report["overall"]
    print("=" * 88)
    print("TRAINING PLATEAU DIAGNOSTICS")
    print("=" * 88)
    print(
        "Runs={total_runs} Wins={wins} WinRate={win_rate:.1f}% "
        "AvgFloor={avg_floor:.2f} MaxFloor={max_floor} AvgPlaytime={avg_playtime:.1f}s".format(
            **overall
        )
    )
    print(
        "BossReach={boss_reach_rate:.1f}% EliteDeath={elite_death_rate:.1f}% "
        "AvgAct1Elites={avg_act1_elites:.2f}".format(**overall)
    )
    if overall["ascensions"]:
        asc = ", ".join(f"A{name}:{count}" for name, count in overall["ascensions"])
        print(f"Ascensions: {asc}")

    print("\nBucket Trend")
    print("-" * 88)
    print(
        f"{'Bucket':<12} {'Runs':<5} {'Win%':<6} {'AvgFloor':<9} {'Max':<4} "
        f"{'Boss%':<6} {'EliteDeath%':<11} {'Act1E':<6} TopDeath"
    )
    for item in report["buckets"]:
        top_death = item["top_death"][0][0] if item["top_death"] else "-"
        print(
            f"{item['index_start']:>3}-{item['index_end']:<7} "
            f"{item['total']:<5} {item['win_rate']:<6.1f} {item['avg_floor']:<9.2f} "
            f"{item['max_floor']:<4} {item['boss_reach_rate']:<6.1f} "
            f"{item['elite_death_rate']:<11.1f} {item['avg_act1_elites']:<6.2f} {top_death}"
        )

    print("\nTop Death Causes")
    print("-" * 88)
    for cause, count in overall["top_death_causes"]:
        print(f"  {cause}: {count}")

    plateau = report["plateau"]
    print("\nPlateau")
    print("-" * 88)
    verdict = "YES" if plateau["plateau"] else "NO"
    print(f"Plateau detected: {verdict}")
    print(f"Reason: {plateau['reason']}")

    hints = report.get("action_hints") or {}
    if hints:
        print("\nAction Failure Hints")
        print("-" * 88)
        if not hints.get("log_found"):
            print("  ai_debug.log not found or unreadable.")
        else:
            print(f"  lines_analyzed: {hints.get('lines_analyzed', 0)}")
            for key in ("command_errors", "failed_actions", "skip_turns", "stability_waits"):
                print(f"  {key}: {hints.get(key, 0)}")
    print("=" * 88)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze RL training plateau and route risk.")
    parser.add_argument("--runs-dir", default=str(default_runs_dir()), help="Path to runs directory.")
    parser.add_argument("--character", default="IRONCLAD", help="Character folder to analyze.")
    parser.add_argument("--count", type=int, default=500, help="Most recent runs to include.")
    parser.add_argument("--bucket", type=int, default=50, help="Runs per trend bucket.")
    parser.add_argument("--log-path", default=DEFAULT_LOG_WIN, help="Path to ai_debug.log.")
    parser.add_argument("--tail-lines", type=int, default=200000, help="Log tail lines for action hints.")
    parser.add_argument("--no-log", action="store_true", help="Skip ai_debug.log action hint parsing.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runs = collect_runs(Path(args.runs_dir), args.character, args.count)
    if not runs:
        print("No runs found.")
        return 1

    action_hints = None
    if not args.no_log:
        action_hints = parse_action_hints(Path(args.log_path), args.tail_lines)

    report = make_report(runs, args.bucket, action_hints)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
