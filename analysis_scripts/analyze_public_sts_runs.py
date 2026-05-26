#!/usr/bin/env python3
"""
Analyze public Slay the Spire run dumps.

The 77M run dump is distributed as many JSON/GZIP chunks. This script keeps the
first pass deliberately simple: stream local files, filter to a character, and
summarize decisions that can inform non-combat strategy.
"""

import argparse
import gzip
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence


SKIP_VALUES = {"", "SKIP", "SKIPPED", "NONE", "NULL"}
SUPPORTED_SUFFIXES = {".json", ".jsonl", ".run", ".gz"}


@dataclass
class ChoiceStats:
    offered: int = 0
    selected: int = 0
    selected_wins: int = 0
    selected_floor_total: int = 0

    @property
    def selected_win_rate(self) -> float:
        if self.selected == 0:
            return 0.0
        return self.selected_wins / self.selected * 100.0

    @property
    def selected_avg_floor(self) -> float:
        if self.selected == 0:
            return 0.0
        return self.selected_floor_total / self.selected


@dataclass
class BucketStats:
    runs: int = 0
    wins: int = 0
    floor_total: int = 0

    @property
    def win_rate(self) -> float:
        if self.runs == 0:
            return 0.0
        return self.wins / self.runs * 100.0

    @property
    def avg_floor(self) -> float:
        if self.runs == 0:
            return 0.0
        return self.floor_total / self.runs


@dataclass
class RunSummary:
    run_count: int = 0
    victories: int = 0
    floor_total: int = 0
    playtime_total: int = 0
    card_reward_choices: int = 0
    skipped_card_rewards: int = 0
    card_pick_counts: Dict[str, ChoiceStats] = field(
        default_factory=lambda: defaultdict(ChoiceStats)
    )
    boss_relic_counts: Dict[str, ChoiceStats] = field(
        default_factory=lambda: defaultdict(ChoiceStats)
    )
    neow_counts: Dict[str, BucketStats] = field(
        default_factory=lambda: defaultdict(BucketStats)
    )
    act1_node_counts: Counter = field(default_factory=Counter)
    death_causes: Counter = field(default_factory=Counter)

    @property
    def win_rate(self) -> float:
        if self.run_count == 0:
            return 0.0
        return self.victories / self.run_count * 100.0

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


def iter_run_records(paths: Sequence[Path]) -> Iterator[dict]:
    """Yield normalized run records from files or directories."""
    for path in _expand_input_paths(paths):
        for raw_record in _load_records_from_file(path):
            record = _unwrap_metrics_event(raw_record)
            if isinstance(record, dict):
                yield record


def summarize_runs(
    records: Iterable[dict],
    character: str = "IRONCLAD",
    ascension_level: Optional[int] = None,
    min_build_version: Optional[str] = None,
    include_daily: bool = False,
    include_endless: bool = False,
    include_seeded: bool = False,
    limit: Optional[int] = None,
) -> RunSummary:
    summary = RunSummary()
    character = character.upper()

    for record in records:
        if not _matches_filters(
            record,
            character=character,
            ascension_level=ascension_level,
            min_build_version=min_build_version,
            include_daily=include_daily,
            include_endless=include_endless,
            include_seeded=include_seeded,
        ):
            continue

        _add_run(summary, record)
        if limit is not None and summary.run_count >= limit:
            break

    return summary


def format_summary(summary: RunSummary, top_n: int = 10) -> str:
    lines = [
        "Public STS Run Dump Summary",
        "=" * 32,
        f"Runs analyzed: {summary.run_count}",
        f"Victories: {summary.victories} ({summary.win_rate:.1f}%)",
        f"Average floor: {summary.avg_floor:.1f}",
        f"Average playtime: {summary.avg_playtime:.0f}s",
        (
            "Card rewards: "
            f"{summary.card_reward_choices} choices, "
            f"{summary.skipped_card_rewards} skips"
        ),
        "",
    ]

    lines.extend(_format_choice_table("Top card picks", summary.card_pick_counts, top_n))
    lines.extend(_format_choice_table("Top boss relics", summary.boss_relic_counts, top_n))
    lines.extend(_format_bucket_table("Top Neow bonuses", summary.neow_counts, top_n))
    lines.extend(_format_counter_table("Act 1 path nodes", summary.act1_node_counts, top_n))
    lines.extend(_format_counter_table("Death causes", summary.death_causes, top_n))
    return "\n".join(lines).rstrip() + "\n"


def _add_run(summary: RunSummary, record: dict) -> None:
    victory = bool(record.get("victory"))
    floor = _to_int(record.get("floor_reached"), default=0)
    playtime = _to_int(record.get("playtime"), default=0)

    summary.run_count += 1
    summary.victories += 1 if victory else 0
    summary.floor_total += floor
    summary.playtime_total += playtime

    _add_card_choices(summary, record, victory, floor)
    _add_boss_relic_choices(summary, record, victory, floor)
    _add_neow(summary, record, victory, floor)
    _add_act1_nodes(summary, record)
    _add_death_cause(summary, record, victory)


def _add_card_choices(summary: RunSummary, record: dict, victory: bool, floor: int) -> None:
    for choice in record.get("card_choices") or []:
        if not isinstance(choice, dict):
            continue

        picked = _clean_name(choice.get("picked"))
        not_picked = [_clean_name(card) for card in choice.get("not_picked") or []]
        not_picked = [card for card in not_picked if card]
        offered = set(not_picked)

        if picked and not _is_skip(picked):
            offered.add(picked)

        if not offered and not picked:
            continue

        summary.card_reward_choices += 1
        for card in offered:
            summary.card_pick_counts[card].offered += 1

        if picked and not _is_skip(picked):
            stats = summary.card_pick_counts[picked]
            stats.selected += 1
            stats.selected_wins += 1 if victory else 0
            stats.selected_floor_total += floor
        else:
            summary.skipped_card_rewards += 1


def _add_boss_relic_choices(
    summary: RunSummary, record: dict, victory: bool, floor: int
) -> None:
    for choice in record.get("boss_relics") or []:
        if not isinstance(choice, dict):
            continue

        picked = _clean_name(choice.get("picked"))
        not_picked = [_clean_name(relic) for relic in choice.get("not_picked") or []]
        offered = set(relic for relic in not_picked if relic)
        if picked and not _is_skip(picked):
            offered.add(picked)

        for relic in offered:
            summary.boss_relic_counts[relic].offered += 1

        if picked and not _is_skip(picked):
            stats = summary.boss_relic_counts[picked]
            stats.selected += 1
            stats.selected_wins += 1 if victory else 0
            stats.selected_floor_total += floor


def _add_neow(summary: RunSummary, record: dict, victory: bool, floor: int) -> None:
    bonus = _clean_name(record.get("neow_bonus")) or "UNKNOWN"
    bucket = summary.neow_counts[bonus]
    bucket.runs += 1
    bucket.wins += 1 if victory else 0
    bucket.floor_total += floor


def _add_act1_nodes(summary: RunSummary, record: dict) -> None:
    for raw_symbol in (record.get("path_taken") or [])[:16]:
        symbol = _clean_name(raw_symbol)
        if not symbol:
            continue
        if symbol == "BOSS":
            symbol = "B"
        summary.act1_node_counts[symbol] += 1
        if symbol == "B":
            break


def _add_death_cause(summary: RunSummary, record: dict, victory: bool) -> None:
    if victory:
        return

    killed_by = _clean_name(record.get("killed_by"))
    if not killed_by:
        damage_taken = record.get("damage_taken") or []
        if damage_taken and isinstance(damage_taken[-1], dict):
            killed_by = _clean_name(damage_taken[-1].get("enemies"))

    if killed_by:
        summary.death_causes[killed_by] += 1


def _matches_filters(
    record: dict,
    character: str,
    ascension_level: Optional[int],
    min_build_version: Optional[str],
    include_daily: bool,
    include_endless: bool,
    include_seeded: bool,
) -> bool:
    if _clean_name(record.get("character_chosen")).upper() != character:
        return False
    if ascension_level is not None:
        if _to_int(record.get("ascension_level"), default=-1) != ascension_level:
            return False
    if min_build_version is not None:
        build_version = _clean_name(record.get("build_version"))
        if build_version and build_version < min_build_version:
            return False
    if not include_daily and bool(record.get("is_daily")):
        return False
    if not include_endless and bool(record.get("is_endless")):
        return False
    if not include_seeded and bool(record.get("chose_seed")):
        return False
    return True


def _expand_input_paths(paths: Sequence[Path]) -> Iterator[Path]:
    for input_path in paths:
        path = Path(input_path)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and _is_supported_file(child):
                    yield child
        elif path.is_file():
            yield path


def _is_supported_file(path: Path) -> bool:
    if path.suffix == ".gz" and path.name.endswith(".json.gz"):
        return True
    return path.suffix in SUPPORTED_SUFFIXES


def _load_records_from_file(path: Path) -> Iterator[dict]:
    text = _read_text(path)
    stripped = text.strip()
    if not stripped:
        return

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        for line in stripped.splitlines():
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)
        return

    if isinstance(parsed, list):
        for item in parsed:
            yield item
    elif isinstance(parsed, dict):
        yield parsed


def _read_text(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return f.read()
    return path.read_text(encoding="utf-8")


def _unwrap_metrics_event(record):
    if isinstance(record, dict) and isinstance(record.get("event"), dict):
        return dict(record["event"])
    return record


def _format_choice_table(
    title: str, stats_by_name: Dict[str, ChoiceStats], top_n: int
) -> List[str]:
    lines = [title]
    rows = sorted(
        stats_by_name.items(),
        key=lambda item: (item[1].selected, item[1].offered, item[0]),
        reverse=True,
    )
    if not rows:
        return lines + ["  (none)", ""]

    for name, stats in rows[:top_n]:
        lines.append(
            "  {name}: selected={selected}, offered={offered}, "
            "win_rate={win_rate:.1f}%, avg_floor={avg_floor:.1f}".format(
                name=name,
                selected=stats.selected,
                offered=stats.offered,
                win_rate=stats.selected_win_rate,
                avg_floor=stats.selected_avg_floor,
            )
        )
    lines.append("")
    return lines


def _format_bucket_table(
    title: str, stats_by_name: Dict[str, BucketStats], top_n: int
) -> List[str]:
    lines = [title]
    rows = sorted(
        stats_by_name.items(),
        key=lambda item: (item[1].runs, item[1].wins, item[0]),
        reverse=True,
    )
    if not rows:
        return lines + ["  (none)", ""]

    for name, stats in rows[:top_n]:
        lines.append(
            "  {name}: runs={runs}, wins={wins}, "
            "win_rate={win_rate:.1f}%, avg_floor={avg_floor:.1f}".format(
                name=name,
                runs=stats.runs,
                wins=stats.wins,
                win_rate=stats.win_rate,
                avg_floor=stats.avg_floor,
            )
        )
    lines.append("")
    return lines


def _format_counter_table(title: str, counter: Counter, top_n: int) -> List[str]:
    lines = [title]
    if not counter:
        return lines + ["  (none)", ""]

    for name, count in counter.most_common(top_n):
        lines.append(f"  {name}: {count}")
    lines.append("")
    return lines


def _clean_name(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _is_skip(value: str) -> bool:
    return _clean_name(value).upper() in SKIP_VALUES


def _to_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze local chunks from the public Slay the Spire run dump."
    )
    parser.add_argument("paths", nargs="+", help="JSON, JSONL, JSON.GZ, .run, or directories")
    parser.add_argument("--character", default="IRONCLAD", help="Character to analyze")
    parser.add_argument("--ascension", type=int, default=None, help="Filter to one ascension")
    parser.add_argument(
        "--min-build-version",
        default=None,
        help="Keep runs with build_version >= this YYYY-MM-DD value",
    )
    parser.add_argument("--include-daily", action="store_true")
    parser.add_argument("--include-endless", action="store_true")
    parser.add_argument("--include-seeded", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="Stop after N matching runs")
    parser.add_argument("--top", type=int, default=10, help="Rows per report section")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    paths = [Path(path) for path in args.paths]
    summary = summarize_runs(
        iter_run_records(paths),
        character=args.character,
        ascension_level=args.ascension,
        min_build_version=args.min_build_version,
        include_daily=args.include_daily,
        include_endless=args.include_endless,
        include_seeded=args.include_seeded,
        limit=args.limit,
    )
    print(format_summary(summary, top_n=args.top), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
