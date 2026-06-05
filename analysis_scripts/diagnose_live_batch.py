#!/usr/bin/env python3
"""
Print a compact diagnostic report for recent local AI runs.

The script is intentionally read-only. It gathers the evidence that is usually
checked by hand while diagnosing a live Slay the Spire AI batch: recent .run
files, AI game markers, death causes, card reward pick/skip counts, and common
danger signals in the debug/error logs.
"""

import argparse
import json
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


DEFAULT_GAME_DIR = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire")
DEFAULT_CHARACTER = "IRONCLAD"
AI_MARKER_TOLERANCE_SECONDS = 300
SKIP_VALUES = {"", "SKIP", "SKIPPED", "NONE", "NULL"}
SIGNAL_PATTERNS = [
    "victory=true",
    "Traceback",
    "Game appears stuck",
    "Communication Mod not responding",
    "READY_WAIT_STATE_POLL",
    "IDLE_STATE_POLL",
    "Index out of bounds",
    "Invalid command",
    "unsupported operand",
    "TypeError",
    "Max games reached",
    "CARD_REWARD",
    "POTION_GUARD",
    "ENERGY_GUARD",
    "REST_GUARD",
]


@dataclass
class RunFileSummary:
    file_name: str
    path: Path
    modified_timestamp: float
    victory: bool
    floor: int
    killed_by: str
    playtime: int
    ai_marked: bool
    card_reward_picks: int = 0
    card_reward_skips: int = 0
    deck_size: int = 0
    potions_obtained: int = 0
    campfire_smiths: int = 0
    campfire_rests: int = 0


@dataclass
class BatchSummary:
    run_count: int = 0
    victories: int = 0
    best_floor: int = 0
    floor_total: int = 0
    playtime_total: int = 0
    ai_marked_count: int = 0
    card_reward_picks: int = 0
    card_reward_skips: int = 0
    death_causes: Counter = field(default_factory=Counter)
    recent_runs: List[RunFileSummary] = field(default_factory=list)

    @property
    def avg_floor(self) -> float:
        if self.run_count == 0:
            return 0.0
        return self.floor_total / self.run_count

    @property
    def avg_playtime(self) -> float:
        if self.run_count == 0:
            return 0.0
        return self.playtime_total / self.run_count


def load_run_summaries(
    game_dir: Path,
    character: str = DEFAULT_CHARACTER,
    since_timestamp: Optional[float] = None,
    since_run_timestamp: Optional[int] = None,
    limit: int = 20,
) -> List[RunFileSummary]:
    runs_dir = game_dir / "runs" / character
    if not runs_dir.exists():
        return []

    ai_markers = _load_ai_markers(game_dir / "runs" / "ai_games.txt")
    run_files = sorted(
        runs_dir.glob("*.run"),
        key=lambda path: path.stat().st_mtime,
    )
    if since_timestamp is not None:
        run_files = [
            path for path in run_files
            if path.stat().st_mtime >= since_timestamp
        ]
    if since_run_timestamp is not None:
        run_files = [
            path for path in run_files
            if _run_stem_timestamp(path) is not None
            and _run_stem_timestamp(path) > since_run_timestamp
        ]
    elif limit > 0:
        run_files = run_files[-limit:]

    if limit > 0:
        run_files = run_files[-limit:]

    ai_marked_stems = _match_ai_marked_run_stems(run_files, ai_markers)
    summaries = []
    for run_file in run_files:
        record = _load_json(run_file)
        if not isinstance(record, dict):
            continue
        summaries.append(_summarize_run_file(run_file, record, ai_marked_stems))
    return summaries


def summarize_run_batch(runs: Iterable[RunFileSummary]) -> BatchSummary:
    summary = BatchSummary()
    for run in runs:
        summary.run_count += 1
        summary.victories += 1 if run.victory else 0
        summary.best_floor = max(summary.best_floor, run.floor)
        summary.floor_total += run.floor
        summary.playtime_total += run.playtime
        summary.ai_marked_count += 1 if run.ai_marked else 0
        summary.card_reward_picks += run.card_reward_picks
        summary.card_reward_skips += run.card_reward_skips
        if not run.victory and run.killed_by:
            summary.death_causes[run.killed_by] += 1
        summary.recent_runs.append(run)
    return summary


def scan_text_for_signals(text: str) -> Counter:
    signals = Counter()
    for pattern in SIGNAL_PATTERNS:
        count = text.count(pattern)
        if count:
            signals[pattern] = count
    return signals


def format_report(
    game_dir: Path,
    character: str,
    since_label: str,
    summary: BatchSummary,
    log_signals: Counter,
    error_signals: Counter,
    recent_error_tail: Sequence[str],
) -> str:
    lines = [
        "Live Batch Diagnostic",
        "=" * 32,
        f"Game dir: {game_dir}",
        f"Character: {character}",
        f"Window: {since_label}",
        "",
        "Run Summary",
        "-" * 16,
        f"Runs analyzed: {summary.run_count}",
        f"AI-marked runs: {summary.ai_marked_count}",
        f"Victories: {summary.victories}",
        f"Best floor: {summary.best_floor}",
        f"Average floor: {summary.avg_floor:.1f}",
        f"Average playtime: {summary.avg_playtime:.0f}s",
        (
            "Card rewards: "
            f"{summary.card_reward_picks} picks, "
            f"{summary.card_reward_skips} skips"
        ),
        "",
        "Death Causes",
        "-" * 16,
    ]
    lines.extend(_format_counter(summary.death_causes, empty="none"))
    lines.extend([
        "",
        "Recent Runs",
        "-" * 16,
    ])
    if summary.recent_runs:
        for run in summary.recent_runs[-10:]:
            result = "WIN" if run.victory else "LOSS"
            marker = "ai" if run.ai_marked else "unmarked"
            lines.append(
                f"{run.file_name}: {result} floor={run.floor} "
                f"killed_by={run.killed_by or '-'} playtime={run.playtime}s "
                f"deck={run.deck_size} potions={run.potions_obtained} "
                f"smith/rest={run.campfire_smiths}/{run.campfire_rests} {marker}"
            )
    else:
        lines.append("none")

    lines.extend([
        "",
        "Log Signals",
        "-" * 16,
        "ai_debug.log:",
    ])
    lines.extend(_format_counter(log_signals, empty="none"))
    lines.append("communication_mod_errors.log:")
    lines.extend(_format_counter(error_signals, empty="none"))

    lines.extend([
        "",
        "Recent Error Tail",
        "-" * 16,
    ])
    tail = [line.rstrip() for line in recent_error_tail if line.rstrip()]
    lines.extend(tail[-10:] if tail else ["none"])
    return "\n".join(lines).rstrip() + "\n"


def parse_since(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    text = value.strip()
    if text.isdigit():
        return float(text)

    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    return datetime.fromisoformat(normalized).timestamp()


def read_tail(path: Path, line_count: int) -> List[str]:
    if not path.exists() or line_count <= 0:
        return []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return list(deque(handle, maxlen=line_count))


def read_debug_log_tails(
    game_dir: Path,
    line_count: int,
    rotated_count: int = 2,
) -> List[str]:
    lines: List[str] = []
    for path in _debug_log_paths(game_dir, rotated_count=rotated_count):
        lines.extend(read_tail(path, line_count))
    return lines


def build_report(
    game_dir: Path,
    character: str,
    since: Optional[str],
    since_run: Optional[int],
    limit: int,
    tail_lines: int,
    rotated_log_count: int = 2,
) -> str:
    since_timestamp = parse_since(since)
    since_label = (
        f"run timestamp > {since_run}"
        if since_run is not None
        else since or f"last {limit} runs"
    )
    runs = load_run_summaries(
        game_dir,
        character=character,
        since_timestamp=since_timestamp,
        since_run_timestamp=since_run,
        limit=limit,
    )
    summary = summarize_run_batch(runs)
    debug_tail = read_debug_log_tails(
        game_dir,
        line_count=tail_lines,
        rotated_count=rotated_log_count,
    )
    error_tail = read_tail(game_dir / "communication_mod_errors.log", tail_lines)
    return format_report(
        game_dir=game_dir,
        character=character,
        since_label=since_label,
        summary=summary,
        log_signals=scan_text_for_signals("".join(debug_tail)),
        error_signals=scan_text_for_signals("".join(error_tail)),
        recent_error_tail=error_tail,
    )


def _load_ai_markers(path: Path) -> set:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    }


def _match_ai_marked_run_stems(run_files: Sequence[Path], ai_markers: set) -> set:
    run_values = []
    for run_file in run_files:
        try:
            run_values.append((int(run_file.stem), run_file.stem))
        except ValueError:
            continue

    marked = set()
    for marker in ai_markers:
        try:
            marker_value = int(marker)
        except ValueError:
            continue
        if not run_values:
            continue
        closest_value, closest_stem = min(
            run_values,
            key=lambda item: abs(item[0] - marker_value),
        )
        if abs(closest_value - marker_value) <= AI_MARKER_TOLERANCE_SECONDS:
            marked.add(closest_stem)
    return marked


def _debug_log_paths(game_dir: Path, rotated_count: int) -> List[Path]:
    paths = [game_dir / "ai_debug.log"]
    if rotated_count > 0:
        paths.extend(
            game_dir / f"ai_debug.log.{index}"
            for index in range(1, rotated_count + 1)
        )
    return paths


def _run_stem_timestamp(path: Path) -> Optional[int]:
    try:
        return int(path.stem)
    except ValueError:
        return None


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _summarize_run_file(
    run_file: Path,
    record: Dict,
    ai_marked_stems: set,
) -> RunFileSummary:
    picks, skips = _count_card_rewards(record.get("card_choices", []))
    smiths, rests = _count_campfires(record.get("campfire_choices", []))
    killed_by = record.get("killed_by") or _last_damage_enemies(record) or ""
    return RunFileSummary(
        file_name=run_file.name,
        path=run_file,
        modified_timestamp=run_file.stat().st_mtime,
        victory=bool(record.get("victory")),
        floor=_to_int(record.get("floor_reached")),
        killed_by=str(killed_by or ""),
        playtime=_to_int(record.get("playtime")),
        ai_marked=run_file.stem in ai_marked_stems,
        card_reward_picks=picks,
        card_reward_skips=skips,
        deck_size=_sequence_length(record.get("master_deck")),
        potions_obtained=_sequence_length(record.get("potions_obtained")),
        campfire_smiths=smiths,
        campfire_rests=rests,
    )


def _count_card_rewards(card_choices) -> tuple:
    picks = 0
    skips = 0
    if not isinstance(card_choices, list):
        return picks, skips
    for choice in card_choices:
        if not isinstance(choice, dict):
            continue
        picked = str(choice.get("picked") or "").strip().upper()
        if picked in SKIP_VALUES:
            skips += 1
        else:
            picks += 1
    return picks, skips


def _count_campfires(campfire_choices) -> tuple:
    smiths = 0
    rests = 0
    if not isinstance(campfire_choices, list):
        return smiths, rests
    for choice in campfire_choices:
        if not isinstance(choice, dict):
            continue
        key = str(choice.get("key") or choice.get("choice") or "").strip().upper()
        if key == "SMITH":
            smiths += 1
        elif key == "REST":
            rests += 1
    return smiths, rests


def _last_damage_enemies(record: Dict) -> str:
    damage_taken = record.get("damage_taken", [])
    if not isinstance(damage_taken, list) or not damage_taken:
        return ""
    last = damage_taken[-1]
    if not isinstance(last, dict):
        return ""
    return str(last.get("enemies") or "")


def _format_counter(counter: Counter, empty: str) -> List[str]:
    if not counter:
        return [empty]
    return [f"{key}: {value}" for key, value in counter.most_common()]


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _sequence_length(value) -> int:
    return len(value) if isinstance(value, list) else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    parser.add_argument("--character", default=DEFAULT_CHARACTER)
    parser.add_argument("--since", help="Unix timestamp or ISO datetime")
    parser.add_argument(
        "--since-run",
        type=int,
        help="Only include .run files whose numeric filename timestamp is greater than this value",
    )
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--tail-lines", type=int, default=400)
    parser.add_argument("--rotated-log-count", type=int, default=2)
    args = parser.parse_args(argv)

    print(
        build_report(
            game_dir=args.game_dir,
            character=args.character,
            since=args.since,
            since_run=args.since_run,
            limit=args.limit,
            tail_lines=args.tail_lines,
            rotated_log_count=args.rotated_log_count,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
