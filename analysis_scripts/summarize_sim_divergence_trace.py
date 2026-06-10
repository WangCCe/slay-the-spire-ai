#!/usr/bin/env python3
"""
Summarize fresh sim divergence JSONL traces.

The script is read-only and intended for short clean validation batches. It
groups divergence rows by reason, action/card, and diff key, while making the
freshness cutoff explicit so stale trace data is harder to mistake for current
evidence.
"""

import argparse
import json
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence


DEFAULT_GAME_DIR = Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire")
DEFAULT_TRACE = DEFAULT_GAME_DIR / "sim_divergence_trace_clean.jsonl"


@dataclass
class TraceLoadResult:
    path: Path
    total_lines: int = 0
    skipped_before_cutoff: int = 0
    malformed_lines: int = 0
    since_unix: Optional[float] = None
    events: List[Dict] = field(default_factory=list)


@dataclass
class DivergenceExample:
    unix_time: Optional[float]
    floor: int
    turn: int
    reason: str
    action_type: str
    card: str
    diff_keys: List[str]


@dataclass
class TraceSummary:
    path: Path
    total_lines: int
    events_analyzed: int
    skipped_before_cutoff: int
    malformed_lines: int
    since_unix: Optional[float]
    by_reason: Counter = field(default_factory=Counter)
    by_action_card: Counter = field(default_factory=Counter)
    by_diff_key: Counter = field(default_factory=Counter)
    by_floor: Counter = field(default_factory=Counter)
    latest_examples: List[DivergenceExample] = field(default_factory=list)


def load_trace(
    path: Path,
    since_unix: Optional[float] = None,
) -> TraceLoadResult:
    result = TraceLoadResult(path=Path(path), since_unix=since_unix)
    if not result.path.exists():
        return result

    with result.path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            result.total_lines += 1
            stripped = line.strip()
            if not stripped:
                continue
            try:
                event = json.loads(stripped)
            except json.JSONDecodeError:
                result.malformed_lines += 1
                continue
            if not isinstance(event, dict):
                result.malformed_lines += 1
                continue
            event_time = _event_unix_time(event)
            if (
                since_unix is not None
                and event_time is not None
                and event_time < since_unix
            ):
                result.skipped_before_cutoff += 1
                continue
            result.events.append(event)
    return result


def summarize_trace(
    loaded: TraceLoadResult,
    max_examples: int = 8,
) -> TraceSummary:
    examples = deque(maxlen=max(0, max_examples))
    summary = TraceSummary(
        path=loaded.path,
        total_lines=loaded.total_lines,
        events_analyzed=len(loaded.events),
        skipped_before_cutoff=loaded.skipped_before_cutoff,
        malformed_lines=loaded.malformed_lines,
        since_unix=loaded.since_unix,
    )

    for event in loaded.events:
        reason = _safe_text(event.get("reason")) or "unknown"
        action_type = _action_type(event)
        card = _action_card(event)
        diff_keys = _diff_keys(event)
        floor = _safe_int(event.get("floor"))

        summary.by_reason[reason] += 1
        summary.by_action_card[f"{action_type} | {card}"] += 1
        if floor:
            summary.by_floor[str(floor)] += 1
        for key in diff_keys:
            summary.by_diff_key[key] += 1

        examples.append(
            DivergenceExample(
                unix_time=_event_unix_time(event),
                floor=floor,
                turn=_safe_int(event.get("turn")),
                reason=reason,
                action_type=action_type,
                card=card,
                diff_keys=diff_keys,
            )
        )

    summary.latest_examples = list(examples)
    return summary


def format_report(summary: TraceSummary) -> str:
    lines = [
        "Sim Divergence Trace Summary",
        "=" * 32,
        f"Trace: {summary.path}",
    ]
    if summary.since_unix is not None:
        lines.append(f"Cutoff unix_time >= {summary.since_unix:g}")
    else:
        lines.append("Cutoff: none")
    lines.extend(
        [
            f"Lines read: {summary.total_lines}",
            f"Events analyzed: {summary.events_analyzed}",
            f"Skipped before cutoff: {summary.skipped_before_cutoff}",
            f"Malformed lines: {summary.malformed_lines}",
            "",
            "By Reason",
            "-" * 16,
        ]
    )
    lines.extend(_format_counter(summary.by_reason))
    lines.extend(["", "By Action / Card", "-" * 16])
    lines.extend(_format_counter(summary.by_action_card))
    lines.extend(["", "By Diff Key", "-" * 16])
    lines.extend(_format_counter(summary.by_diff_key))
    lines.extend(["", "By Floor", "-" * 16])
    lines.extend(_format_counter(summary.by_floor))
    lines.extend(["", "Latest Examples", "-" * 16])
    if summary.latest_examples:
        for example in summary.latest_examples:
            when = "-" if example.unix_time is None else f"{example.unix_time:g}"
            diffs = ", ".join(example.diff_keys) if example.diff_keys else "-"
            lines.append(
                f"t={when} floor={example.floor} turn={example.turn} "
                f"{example.reason} {example.action_type} | {example.card} "
                f"diffs={diffs}"
            )
    else:
        lines.append("none")
    return "\n".join(lines).rstrip() + "\n"


def parse_since(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    return datetime.fromisoformat(normalized).timestamp()


def _event_unix_time(event: Dict) -> Optional[float]:
    value = event.get("unix_time")
    if value is None:
        value = event.get("time")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _action_type(event: Dict) -> str:
    action = event.get("action") or {}
    if not isinstance(action, dict):
        return "-"
    return _safe_text(action.get("type")) or "-"


def _action_card(event: Dict) -> str:
    action = event.get("action") or {}
    if not isinstance(action, dict):
        return "-"
    card = action.get("card")
    if isinstance(card, dict):
        return (
            _safe_text(card.get("name"))
            or _safe_text(card.get("card_id"))
            or _safe_text(card.get("id"))
            or "-"
        )
    return (
        _safe_text(action.get("card_name"))
        or _safe_text(action.get("card_id"))
        or "-"
    )


def _diff_keys(event: Dict) -> List[str]:
    diffs = event.get("diffs") or {}
    if not isinstance(diffs, dict):
        return []
    return sorted(str(key) for key in diffs)


def _format_counter(counter: Counter, limit: int = 20) -> List[str]:
    if not counter:
        return ["none"]
    return [f"{key}: {value}" for key, value in counter.most_common(limit)]


def _safe_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def summary_to_jsonable(summary: TraceSummary) -> Dict:
    return {
        "trace": str(summary.path),
        "since_unix": summary.since_unix,
        "total_lines": summary.total_lines,
        "events_analyzed": summary.events_analyzed,
        "skipped_before_cutoff": summary.skipped_before_cutoff,
        "malformed_lines": summary.malformed_lines,
        "by_reason": dict(summary.by_reason),
        "by_action_card": dict(summary.by_action_card),
        "by_diff_key": dict(summary.by_diff_key),
        "by_floor": dict(summary.by_floor),
        "latest_examples": [
            {
                "unix_time": example.unix_time,
                "floor": example.floor,
                "turn": example.turn,
                "reason": example.reason,
                "action_type": example.action_type,
                "card": example.card,
                "diff_keys": example.diff_keys,
            }
            for example in summary.latest_examples
        ],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument(
        "--since-unix",
        type=float,
        default=None,
        help="Only include rows whose unix_time is at or after this value.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Unix timestamp or ISO datetime cutoff. Ignored if --since-unix is set.",
    )
    parser.add_argument("--limit-examples", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    since_unix = args.since_unix
    if since_unix is None:
        since_unix = parse_since(args.since)

    loaded = load_trace(args.trace, since_unix=since_unix)
    summary = summarize_trace(loaded, max_examples=args.limit_examples)
    if args.json:
        print(json.dumps(summary_to_jsonable(summary), indent=2, sort_keys=True))
    else:
        print(format_report(summary), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
