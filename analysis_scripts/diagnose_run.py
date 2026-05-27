#!/usr/bin/env python3
"""
Print a compact evidence packet for one Slay the Spire AI run.

Use this after a batch-level report identifies a suspicious .run file. The
script summarizes the run record and extracts a small end-of-run window from
ai_debug.log using the run's local_time timestamp.
"""

import argparse
import json
import re
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


DEFAULT_GAME_DIR = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire")
DEFAULT_CHARACTER = "IRONCLAD"
SKIP_VALUES = {"", "SKIP", "SKIPPED", "NONE", "NULL"}
LOG_SIGNAL_PATTERNS = [
    "[COMBAT]",
    "[COMBAT_CANDIDATE]",
    "[TIMING_CLASSIFIER]",
    "[LOOKAHEAD]",
    "[FUTURE_DAMAGE_PENALTY]",
    "[ENERGY_GUARD]",
    "[REST_GUARD]",
    "[CARD_REWARD]",
    "[REWARD]",
    "[GAME_OVER]",
    "[TURN_END]",
    "Traceback",
    "Invalid command",
    "Game appears stuck",
    "Communication Mod not responding",
    "unsupported operand",
    "TypeError",
]
LOG_TIMESTAMP_RE = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
)


def load_run_record(
    game_dir: Path,
    character: str,
    run_ref: str,
) -> Tuple[Path, Dict]:
    run_file = resolve_run_file(game_dir, character, run_ref)
    try:
        record = json.loads(run_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON run file: {run_file}") from exc
    if not isinstance(record, dict):
        raise ValueError(f"Run file is not a JSON object: {run_file}")
    return run_file, record


def resolve_run_file(game_dir: Path, character: str, run_ref: str) -> Path:
    candidate = Path(run_ref)
    if candidate.exists():
        return candidate

    runs_dir = game_dir / "runs" / character
    exact = runs_dir / f"{run_ref}.run"
    if exact.exists():
        return exact

    matches = sorted(runs_dir.glob(f"*{run_ref}*.run"))
    if matches:
        return matches[-1]

    raise FileNotFoundError(f"Could not find run {run_ref!r} under {runs_dir}")


def extract_log_window(
    log_path: Path,
    local_time: str,
    before_seconds: int = 120,
    after_seconds: int = 15,
    signals_only: bool = True,
    max_lines: int = 120,
) -> List[str]:
    if not log_path.exists() or not local_time:
        return []

    end_time = _parse_run_local_time(local_time)
    if not end_time:
        return []

    start_time = end_time - timedelta(seconds=before_seconds)
    stop_time = end_time + timedelta(seconds=after_seconds)
    selected = []
    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line_time = _parse_log_timestamp(line)
            if not line_time or line_time < start_time:
                continue
            if line_time > stop_time:
                break
            if signals_only and not _is_signal_line(line):
                continue
            selected.append(line.rstrip())

    if len(selected) > max_lines:
        return list(deque(selected, maxlen=max_lines))
    return selected


def format_run_report(
    run_file: Path,
    record: Dict,
    log_lines: Sequence[str],
) -> str:
    victory = bool(record.get("victory"))
    result = "WIN" if victory else "LOSS"
    floor = _to_int(record.get("floor_reached"))
    killed_by = record.get("killed_by") or "-"
    playtime = _to_int(record.get("playtime"))
    deck = _as_list(record.get("master_deck"))
    relics = _as_list(record.get("relics"))
    card_picks, card_skips = _count_card_rewards(record.get("card_choices"))
    final_combat = _final_combat_line(record)

    lines = [
        "Run Diagnostic",
        "=" * 32,
        f"Run file: {run_file}",
        f"Result: {result} floor={floor} killed_by={killed_by} playtime={playtime}s",
        f"Seed: {record.get('seed_played') or '-'}",
        f"Neow: {record.get('neow_bonus') or '-'} / cost={record.get('neow_cost') or '-'}",
        "",
        "Deck And Relics",
        "-" * 16,
        f"Deck size: {len(deck)}",
        "Deck: " + _join_or_dash(deck),
        "Relics: " + _join_or_dash(relics),
        "Boss relics: " + _format_boss_relics(record.get("boss_relics")),
        "",
        "Run Choices",
        "-" * 16,
        f"Card rewards: {card_picks} picks, {card_skips} skips",
        "Recent card choices:",
    ]
    lines.extend(_format_recent_card_choices(record.get("card_choices"), limit=8))
    lines.append("Campfires:")
    lines.extend(_format_campfires(record.get("campfire_choices"), limit=8))
    lines.append("Damage taken:")
    lines.extend(_format_damage_taken(record.get("damage_taken"), limit=8))
    lines.append(final_combat)
    lines.extend([
        "",
        "Log Window",
        "-" * 16,
    ])
    lines.extend(log_lines if log_lines else ["none"])
    return "\n".join(lines).rstrip() + "\n"


def build_report(
    run_ref: str,
    game_dir: Path,
    character: str,
    before_seconds: int,
    after_seconds: int,
    signals_only: bool,
    max_log_lines: int,
) -> str:
    run_file, record = load_run_record(game_dir, character, run_ref)
    log_lines = extract_log_window_from_game_dir(
        game_dir,
        local_time=str(record.get("local_time") or ""),
        before_seconds=before_seconds,
        after_seconds=after_seconds,
        signals_only=signals_only,
        max_lines=max_log_lines,
    )
    return format_run_report(run_file, record, log_lines)


def extract_log_window_from_game_dir(
    game_dir: Path,
    local_time: str,
    before_seconds: int = 120,
    after_seconds: int = 15,
    signals_only: bool = True,
    max_lines: int = 120,
) -> List[str]:
    for log_path in _candidate_debug_logs(game_dir, local_time, before_seconds):
        lines = extract_log_window(
            log_path,
            local_time=local_time,
            before_seconds=before_seconds,
            after_seconds=after_seconds,
            signals_only=signals_only,
            max_lines=max_lines,
        )
        if lines:
            return [f"log source: {log_path.name}", *lines]
    return []


def _candidate_debug_logs(game_dir: Path, local_time: str, before_seconds: int) -> List[Path]:
    candidates = [game_dir / "ai_debug.log"]
    end_time = _parse_run_local_time(local_time)
    earliest_relevant_write = (
        end_time - timedelta(seconds=before_seconds)
        if end_time
        else None
    )
    archive_dir = game_dir / "logs_archive"
    if archive_dir.exists():
        archives = sorted(
            archive_dir.glob("ai_debug.log*.bak"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if earliest_relevant_write:
            archives = [
                path for path in archives
                if datetime.fromtimestamp(path.stat().st_mtime) >= earliest_relevant_write
            ]
        candidates.extend(archives)
    return candidates


def _parse_run_local_time(local_time: str) -> Optional[datetime]:
    try:
        return datetime.strptime(local_time, "%Y%m%d%H%M%S")
    except (TypeError, ValueError):
        return None


def _parse_log_timestamp(line: str) -> Optional[datetime]:
    match = LOG_TIMESTAMP_RE.match(line)
    if not match:
        return None
    try:
        return datetime.strptime(match.group("stamp"), "%Y-%m-%d %H:%M:%S,%f")
    except ValueError:
        return None


def _is_signal_line(line: str) -> bool:
    return any(pattern in line for pattern in LOG_SIGNAL_PATTERNS)


def _count_card_rewards(card_choices) -> Tuple[int, int]:
    picks = 0
    skips = 0
    for choice in _as_list(card_choices):
        if not isinstance(choice, dict):
            continue
        picked = str(choice.get("picked") or "").strip().upper()
        if picked in SKIP_VALUES:
            skips += 1
        else:
            picks += 1
    return picks, skips


def _format_recent_card_choices(card_choices, limit: int) -> List[str]:
    choices = [choice for choice in _as_list(card_choices) if isinstance(choice, dict)]
    if not choices:
        return ["none"]
    lines = []
    for choice in choices[-limit:]:
        floor = choice.get("floor", "?")
        picked = choice.get("picked") or "-"
        not_picked = _join_or_dash(_as_list(choice.get("not_picked")))
        lines.append(f"floor {floor}: picked {picked} over {not_picked}")
    return lines


def _format_campfires(campfires, limit: int) -> List[str]:
    entries = [entry for entry in _as_list(campfires) if isinstance(entry, dict)]
    if not entries:
        return ["none"]
    lines = []
    for entry in entries[-limit:]:
        floor = entry.get("floor", "?")
        key = entry.get("key") or "-"
        data = entry.get("data")
        suffix = f" {data}" if data else ""
        lines.append(f"floor {floor}: {key}{suffix}")
    return lines


def _format_damage_taken(damage_taken, limit: int) -> List[str]:
    entries = [entry for entry in _as_list(damage_taken) if isinstance(entry, dict)]
    if not entries:
        return ["none"]
    lines = []
    for entry in entries[-limit:]:
        floor = entry.get("floor", "?")
        enemies = entry.get("enemies") or "-"
        damage = _to_int(entry.get("damage"))
        turns = _to_int(entry.get("turns"))
        lines.append(f"floor {floor}: {enemies} damage={damage} turns={turns}")
    return lines


def _format_boss_relics(boss_relics) -> str:
    entries = [entry for entry in _as_list(boss_relics) if isinstance(entry, dict)]
    if not entries:
        return "-"
    parts = []
    for entry in entries:
        picked = entry.get("picked") or "-"
        not_picked = _join_or_dash(_as_list(entry.get("not_picked")))
        parts.append(f"{picked} over {not_picked}")
    return "; ".join(parts)


def _final_combat_line(record: Dict) -> str:
    damage_taken = [entry for entry in _as_list(record.get("damage_taken")) if isinstance(entry, dict)]
    if not damage_taken:
        return "Final combat: -"
    final = damage_taken[-1]
    return (
        f"Final combat: {final.get('enemies') or '-'} "
        f"damage={_to_int(final.get('damage'))} "
        f"turns={_to_int(final.get('turns'))}"
    )


def _join_or_dash(values: Sequence) -> str:
    clean = [str(value) for value in values if value not in (None, "")]
    return ", ".join(clean) if clean else "-"


def _as_list(value) -> List:
    return value if isinstance(value, list) else []


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", help="Run timestamp, partial timestamp, or .run file path")
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME_DIR)
    parser.add_argument("--character", default=DEFAULT_CHARACTER)
    parser.add_argument("--before-seconds", type=int, default=120)
    parser.add_argument("--after-seconds", type=int, default=15)
    parser.add_argument("--max-log-lines", type=int, default=120)
    parser.add_argument(
        "--all-log-lines",
        action="store_true",
        help="Show every log line in the time window instead of signal lines only",
    )
    args = parser.parse_args(argv)

    print(
        build_report(
            run_ref=args.run,
            game_dir=args.game_dir,
            character=args.character,
            before_seconds=args.before_seconds,
            after_seconds=args.after_seconds,
            signals_only=not args.all_log_lines,
            max_log_lines=args.max_log_lines,
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
