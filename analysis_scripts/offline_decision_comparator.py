#!/usr/bin/env python3
"""Offline operating-decision comparator against Bottled-style references."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


REQUESTED_STRIKE_DESIRED_CARDS = {
    "perfected strike": 5,
    "offering": 1,
    "battle trance": 2,
    "reaper": 2,
    "twin strike": 2,
    "shockwave": 2,
    "thunderclap": 2,
    "dropkick": 2,
    "pommel strike": 2,
    "shrug it off": 2,
    "impervious": 2,
    "ghostly armor": 1,
    "flame barrier": 1,
    "blind": 1,
    "apotheosis": 1,
    "handofgreed": 1,
    "master of strategy": 1,
    "flash of steel": 1,
    "trip": 1,
    "dark shackles": 1,
    "swift strike": 1,
    "dramatic entrance": 1,
    "finesse": 1,
}

SHOP_REMOVAL_PRIORITY = {"defend", "strike", "defend+", "strike+"}
SHOP_RELIC_PRIORITY = [
    "bag of marbles",
    "pen nib",
    "strike dummy",
    "paper phrog",
    "preserved insect",
    "red skull",
    "meat on the bone",
    "eternal feather",
    "regal pillow",
    "lee's waffle",
    "lee\u2019s waffle",
    "meal ticket",
    "strawberry",
    "toy ornithopter",
    "pantograph",
    "pear",
    "orichalcum",
    "anchor",
    "horn cleat",
    "self-forming clay",
    "thread and needle",
    "lantern",
    "happy flower",
    "bag of preparation",
    "centennial puzzle",
]
SHOP_CARD_PRIORITY = ["offering", "battle trance", "shockwave"]
CURSE_NAMES = {
    "ascendersbane",
    "ascender's bane",
    "curse of the bell",
    "clumsy",
    "decay",
    "doubt",
    "injury",
    "normality",
    "pain",
    "parasite",
    "regret",
    "shame",
    "writhe",
}


@dataclass(frozen=True)
class DecisionSample:
    sample_id: str
    category: str
    source: str
    floor: Optional[int]
    act: Optional[int]
    evidence_quality: str
    our_choice: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReferenceDecision:
    choice: str
    reason: str
    confidence: str
    oracle_mode: str = "bottled_style"
    raw: Dict[str, Any] = field(default_factory=dict)
    source: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ComparisonRow:
    sample_id: str
    category: str
    source: str
    floor: Optional[int]
    act: Optional[int]
    evidence_quality: str
    current_choice: str
    reference_choice: str
    match: bool
    confidence: str
    reason: str
    oracle_mode: str = "bottled_style"
    oracle_source: Dict[str, Any] = field(default_factory=dict)
    raw_reference: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)


def load_fixture_samples(path: Path | str) -> List[DecisionSample]:
    data = _load_json_object(Path(path))
    raw_samples = data.get("samples", data if isinstance(data, list) else [])
    if not isinstance(raw_samples, list):
        raise ValueError(f"Fixture must contain a samples list: {path}")
    return [_sample_from_mapping(item) for item in raw_samples]


def load_run_samples(path: Path | str, limit: Optional[int] = None) -> List[DecisionSample]:
    run_path = Path(path)
    record = _load_json_object(run_path)
    samples: List[DecisionSample] = []
    source = f"run:{run_path.name}"
    act = _to_int(record.get("act"), default=None)

    card_choices = _as_list(record.get("card_choices"))
    for index, choice in enumerate(card_choices):
        if not isinstance(choice, dict):
            continue
        picked = str(choice.get("picked") or "SKIP")
        not_picked = [str(card) for card in _as_list(choice.get("not_picked"))]
        offered = [picked] + not_picked if _normalize_name(picked) != "skip" else not_picked
        samples.append(
            DecisionSample(
                sample_id=f"{run_path.stem}:card_reward:{index}",
                category="card_reward",
                source=source,
                floor=_to_int(choice.get("floor"), default=None),
                act=act,
                evidence_quality="partial",
                our_choice={"kind": "skip" if _normalize_name(picked) == "skip" else "take", "name": picked},
                context={
                    "offered": offered,
                    "deck": _as_list(record.get("master_deck")),
                    "can_skip": True,
                },
                limitations=["missing deck snapshot at reward time"],
            )
        )

    event_choices = _as_list(record.get("event_choices"))
    for index, event in enumerate(event_choices):
        if not isinstance(event, dict):
            continue
        player_choice = str(event.get("player_choice") or "")
        samples.append(
            DecisionSample(
                sample_id=f"{run_path.stem}:event:{index}",
                category="event",
                source=source,
                floor=_to_int(event.get("floor"), default=None),
                act=act,
                evidence_quality="partial",
                our_choice={"kind": "outcome", "label": player_choice},
                context={
                    "event_name": event.get("event_name") or "",
                    "choices": [],
                    "current_hp": None,
                    "max_hp": None,
                },
                limitations=["missing event option labels and hp at decision time"],
            )
        )

    purchase_floors = _as_list(record.get("item_purchase_floors"))
    for index, item in enumerate(_as_list(record.get("items_purchased"))):
        samples.append(
            DecisionSample(
                sample_id=f"{run_path.stem}:shop_purchase:{index}",
                category="shop",
                source=source,
                floor=_to_int(_list_get(purchase_floors, index), default=None),
                act=act,
                evidence_quality="partial",
                our_choice={"kind": "purchase", "name": str(item)},
                context={"cards": [], "relics": [], "potions": [], "deck": _as_list(record.get("master_deck"))},
                limitations=["missing full shop offer"],
            )
        )

    purge_floors = _as_list(record.get("items_purged_floors"))
    for index, item in enumerate(_as_list(record.get("items_purged"))):
        samples.append(
            DecisionSample(
                sample_id=f"{run_path.stem}:shop_purge:{index}",
                category="shop",
                source=source,
                floor=_to_int(_list_get(purge_floors, index), default=None),
                act=act,
                evidence_quality="partial",
                our_choice={"kind": "purge", "name": str(item)},
                context={"deck": _as_list(record.get("master_deck"))},
                limitations=["missing full shop offer"],
            )
        )

    path_taken = _as_list(record.get("path_taken") or record.get("path_per_floor"))
    if path_taken:
        samples.append(
            DecisionSample(
                sample_id=f"{run_path.stem}:route:path_taken",
                category="route",
                source=source,
                floor=1,
                act=act,
                evidence_quality="partial",
                our_choice={"kind": "path_summary", "choice": "actual path"},
                context={"path_taken": [str(node) for node in path_taken if node is not None]},
                limitations=["missing route candidate map at decision time"],
            )
        )

    return samples[:limit] if limit else samples


def load_jsonl_samples(
    path: Path | str,
    tail: int = 2000,
    since_unix: Optional[float] = None,
) -> List[DecisionSample]:
    rows: deque[str] = deque(maxlen=max(1, tail))
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            rows.append(line)

    samples: List[DecisionSample] = []
    for index, line in enumerate(rows):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if since_unix is not None:
            event_time = _to_float(event.get("unix_time"), default=None)
            if event_time is None or event_time < since_unix:
                continue
        sample = _sample_from_trace_event(event, index)
        if sample:
            samples.append(sample)
    return samples


def compare_samples(
    samples: Iterable[DecisionSample],
    reference_mode: str = "bottled_style",
    bottled_repo_path: Optional[Path | str] = None,
) -> List[ComparisonRow]:
    rows: List[ComparisonRow] = []
    normalized_mode = _normalize_reference_mode(reference_mode)
    oracle = None
    if normalized_mode == "native_bottled":
        from analysis_scripts.bottled_policy_oracle import BottledPolicyOracle

        oracle = BottledPolicyOracle(bottled_repo_path)
    for sample in samples:
        reference = (
            _native_bottled_reference_for_sample(sample, oracle)
            if oracle is not None
            else _reference_for_sample(sample)
        )
        current = _current_choice_text(sample)
        match = _choices_match(current, reference.choice)
        confidence = _combined_confidence(sample.evidence_quality, reference.confidence, match)
        rows.append(
            ComparisonRow(
                sample_id=sample.sample_id,
                category=sample.category,
                source=sample.source,
                floor=sample.floor,
                act=sample.act,
                evidence_quality=sample.evidence_quality,
                current_choice=current,
                reference_choice=reference.choice,
                match=match,
                confidence=confidence,
                reason=reference.reason,
                oracle_mode=reference.oracle_mode,
                oracle_source=dict(reference.source),
                raw_reference=dict(reference.raw),
                limitations=list(sample.limitations) + list(reference.limitations),
            )
        )
    return rows


def rank_issues(rows: Sequence[ComparisonRow], max_issues: int = 5) -> List[ComparisonRow]:
    priority = {"shop": 0, "event": 1, "route": 2, "card_reward": 3}
    confidence_score = {"high": 0, "medium": 1, "low": 2}
    groups: Dict[tuple[str, str, str], Dict[tuple[str, str, Optional[int], str, str, str], ComparisonRow]] = {}
    for row in rows:
        if row.match or row.confidence not in {"high", "medium"}:
            continue
        if _is_fixture_source(row.source):
            continue
        groups.setdefault(_issue_signature(row), {}).setdefault(_issue_occurrence_key(row), row)

    repeated_groups = [list(members_by_occurrence.values()) for members_by_occurrence in groups.values() if len(members_by_occurrence) >= 2]
    repeated_groups.sort(
        key=lambda members: (
            confidence_score.get(_best_confidence(members), 3),
            priority.get(members[0].category, 9),
            -len(members),
            min(row.floor if row.floor is not None else 999 for row in members),
            sorted(row.sample_id for row in members)[0],
        )
    )

    issues: List[ComparisonRow] = []
    for members in repeated_groups[:max_issues]:
        representative = sorted(
            members,
            key=lambda row: (
                row.floor if row.floor is not None else 999,
                row.sample_id,
            ),
        )[0]
        issues.append(
            replace(
                representative,
                reason=f"{representative.reason} Repeated {len(members)}x in non-fixture evidence.",
            )
        )
    return issues


def render_markdown_report(
    rows: Sequence[ComparisonRow],
    issues: Optional[Sequence[ComparisonRow]] = None,
) -> str:
    issue_rows = list(rank_issues(rows) if issues is None else issues)
    lines = [
        "# Offline Decision Comparator POC",
        "",
        _reference_summary(rows),
        "No gameplay-code fix is applied by this report.",
        "",
        "## Summary",
        "",
    ]
    by_category: Dict[str, int] = {}
    by_evidence: Dict[str, int] = {}
    by_oracle_mode: Dict[str, int] = {}
    mismatches = 0
    for row in rows:
        by_category[row.category] = by_category.get(row.category, 0) + 1
        by_evidence[row.evidence_quality] = by_evidence.get(row.evidence_quality, 0) + 1
        by_oracle_mode[row.oracle_mode] = by_oracle_mode.get(row.oracle_mode, 0) + 1
        if not row.match:
            mismatches += 1
    lines.extend(
        [
            f"- Samples: {len(rows)}",
            f"- Differences: {mismatches}",
            f"- Categories: {_format_counts(by_category)}",
            f"- Evidence quality: {_format_counts(by_evidence)}",
            f"- Oracle modes: {_format_counts(by_oracle_mode)}",
            "",
            "## Comparison Rows",
            "",
            "| Category | Source | Floor | Evidence | Oracle Mode | Current Choice | Bottled Reference | Confidence | Reason |",
            "|---|---|---:|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {category} | {source} | {floor} | {evidence} | {oracle_mode} | {current} | {reference} | {confidence} | {reason} |".format(
                category=_md(row.category),
                source=_md(row.source),
                floor="" if row.floor is None else row.floor,
                evidence=_md(row.evidence_quality),
                oracle_mode=_md(row.oracle_mode),
                current=_md(row.current_choice),
                reference=_md(row.reference_choice),
                confidence=_md(row.confidence),
                reason=_md(_reason_with_limitations(row)),
            )
        )

    lines.extend(["", "## Most Worth Fixing", ""])
    if issue_rows:
        for index, row in enumerate(issue_rows, start=1):
            lines.append(
                f"{index}. **{_md(row.category)} floor {row.floor or '?'}**: "
                f"current `{_md(row.current_choice)}` vs reference `{_md(row.reference_choice)}` "
                f"({row.confidence}). {_md(row.reason)}"
            )
    else:
        lines.append("No repeated high-confidence operating-decision fix is recommended yet.")

    lines.extend(["", "## Repair Gate", ""])
    if issue_rows:
        lines.append(
            "Repair is justified by repeated high-confidence non-fixture evidence. "
            "This report does not change gameplay code; apply one minimal strategy fix test-first, "
            "starting from the top-ranked candidate."
        )
    else:
        lines.append(
            "No gameplay-code fix is applied. No repeated high-confidence non-fixture operating-decision "
            "candidate is available yet."
        )
    lines.append("")
    return "\n".join(lines)


def build_report(
    fixture_paths: Sequence[Path],
    run_paths: Sequence[Path],
    trace_paths: Sequence[Path],
    trace_tail: int = 2000,
    since_unix: Optional[float] = None,
    reference_mode: str = "bottled_style",
    bottled_repo_path: Optional[Path | str] = None,
) -> str:
    samples: List[DecisionSample] = []
    for path in fixture_paths:
        samples.extend(load_fixture_samples(path))
    for path in run_paths:
        samples.extend(load_run_samples(path))
    for path in trace_paths:
        samples.extend(load_jsonl_samples(path, tail=trace_tail, since_unix=since_unix))
    rows = compare_samples(samples, reference_mode=reference_mode, bottled_repo_path=bottled_repo_path)
    return render_markdown_report(rows, rank_issues(rows))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", action="append", type=Path, default=[])
    parser.add_argument("--run", action="append", type=Path, default=[])
    parser.add_argument("--trace", action="append", type=Path, default=[])
    parser.add_argument("--trace-tail", type=int, default=2000)
    parser.add_argument("--since-unix", type=float)
    parser.add_argument(
        "--reference-mode",
        choices=["bottled-style", "bottled_style", "native-bottled", "native_bottled"],
        default="bottled-style",
    )
    parser.add_argument("--bottled-repo", type=Path, default=None)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = build_report(
        args.fixture,
        args.run,
        args.trace,
        trace_tail=args.trace_tail,
        since_unix=args.since_unix,
        reference_mode=args.reference_mode,
        bottled_repo_path=args.bottled_repo,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report)
    return 0


def _sample_from_mapping(item: Dict[str, Any]) -> DecisionSample:
    return DecisionSample(
        sample_id=str(item.get("id") or item.get("sample_id") or ""),
        category=str(item.get("category") or ""),
        source=str(item.get("source") or "fixture"),
        floor=_to_int(item.get("floor"), default=None),
        act=_to_int(item.get("act"), default=None),
        evidence_quality=str(item.get("evidence_quality") or "complete"),
        our_choice=dict(item.get("our_choice") or {}),
        context=dict(item.get("context") or {}),
        limitations=[str(value) for value in _as_list(item.get("limitations"))],
    )


def _sample_from_trace_event(event: Dict[str, Any], index: int) -> Optional[DecisionSample]:
    screen = _as_mapping(event.get("screen"))
    screen_type = str(event.get("screen_type") or screen.get("type") or "")
    category = ""
    if "SHOP_SCREEN" in screen_type:
        category = "shop"
    elif "EVENT" in screen_type:
        category = "event"
    elif "MAP" in screen_type:
        category = "route"
    elif "CARD_REWARD" in screen_type:
        category = "card_reward"
    if not category:
        return None

    action = dict(event.get("action") or {})
    if category == "card_reward":
        return _trace_card_reward_sample(event, screen, action, index)
    if category == "shop":
        return _trace_shop_sample(event, screen, action, index)
    if category == "event":
        return _trace_event_sample(event, screen, action, index)
    if category == "route":
        return _trace_route_sample(event, screen, action, index)

    return DecisionSample(
        sample_id=f"trace:{index}",
        category=category,
        source="decision_trace",
        floor=_to_int(event.get("floor"), default=None),
        act=_to_int(event.get("act"), default=None),
        evidence_quality="partial",
        our_choice={"kind": action.get("type") or "action", "name": action.get("command") or ""},
        context={"trace_event": event},
        limitations=["trace row lacks normalized operating-decision context"],
    )


def sample_from_trace_event(event: Dict[str, Any], index: int = 0) -> Optional[DecisionSample]:
    return _sample_from_trace_event(event, index)


def _trace_card_reward_sample(
    event: Dict[str, Any],
    screen: Dict[str, Any],
    action: Dict[str, Any],
    index: int,
) -> DecisionSample:
    offered = [_item_name(card) for card in _as_list(screen.get("cards"))]
    deck = [_item_name(card) for card in _as_list(event.get("deck"))]
    action_name = _action_name(action)
    action_type = str(action.get("type") or "")
    if action_type == "CancelAction" or _normalize_name(action_name) == "skip":
        our_choice = {"kind": "skip", "name": "skip"}
    elif _normalize_name(action_name) == "bowl":
        our_choice = {"kind": "bowl", "name": "bowl"}
    else:
        our_choice = {"kind": "take", "name": action_name}

    limitations = []
    if not offered:
        limitations.append("missing card reward options")
    if "deck" not in event:
        limitations.append("missing deck snapshot at reward time")
    evidence_quality = "complete" if not limitations else "partial"
    return DecisionSample(
        sample_id=f"trace:{index}",
        category="card_reward",
        source="decision_trace",
        floor=_to_int(event.get("floor"), default=None),
        act=_to_int(event.get("act"), default=None),
        evidence_quality=evidence_quality,
        our_choice=our_choice,
        context={
            "offered": offered,
            "deck": deck,
            "can_skip": bool(screen.get("can_skip", True)),
            "can_bowl": bool(screen.get("can_bowl", False)),
        },
        limitations=limitations,
    )


def _trace_shop_sample(
    event: Dict[str, Any],
    screen: Dict[str, Any],
    action: Dict[str, Any],
    index: int,
) -> DecisionSample:
    action_type = str(action.get("type") or "")
    action_name = _action_name(action)
    if action_type == "BuyCardAction":
        our_choice = {"kind": "buy_card", "name": action_name}
    elif action_type == "BuyPurgeAction" or _normalize_name(action_name) == "purge":
        purge_target = _item_name(action.get("card_to_purge")) or action_name or "purge"
        our_choice = {"kind": "purge", "name": purge_target}
    elif action_type in {"BuyRelicAction", "BuyPotionAction"}:
        our_choice = {"kind": "purchase", "name": action_name}
    elif action_type in {"LeaveAction", "CancelAction"}:
        our_choice = {"kind": "leave", "name": "leave"}
    else:
        our_choice = {"kind": "action", "name": action_name or str(action.get("command") or "")}

    required_screen_keys = {"cards", "relics", "potions", "purge_available", "purge_cost"}
    limitations = []
    missing_screen = sorted(key for key in required_screen_keys if key not in screen)
    if missing_screen:
        limitations.append(f"missing shop screen fields: {', '.join(missing_screen)}")
    if "gold" not in event:
        limitations.append("missing gold at shop decision time")
    if "deck" not in event:
        limitations.append("missing deck snapshot at shop decision time")

    evidence_quality = "complete" if not limitations else "partial"
    return DecisionSample(
        sample_id=f"trace:{index}",
        category="shop",
        source="decision_trace",
        floor=_to_int(event.get("floor"), default=None),
        act=_to_int(event.get("act"), default=None),
        evidence_quality=evidence_quality,
        our_choice=our_choice,
        context={
            "gold": _to_int(event.get("gold"), 0) or 0,
            "purge_available": bool(screen.get("purge_available")),
            "purge_cost": _to_int(screen.get("purge_cost"), 10**9) or 10**9,
            "deck": [_item_name(card) for card in _as_list(event.get("deck"))],
            "cards": [_priced_item(card) for card in _as_list(screen.get("cards"))],
            "relics": [_priced_item(relic) for relic in _as_list(screen.get("relics"))],
            "potions": [_priced_item(potion) for potion in _as_list(screen.get("potions"))],
        },
        limitations=limitations,
    )


def _trace_event_sample(
    event: Dict[str, Any],
    screen: Dict[str, Any],
    action: Dict[str, Any],
    index: int,
) -> DecisionSample:
    options = []
    for option_index, option in enumerate(_as_mapping_list(screen.get("options"))):
        disabled = option.get("disabled")
        if disabled is True or str(disabled).lower() == "true":
            continue
        options.append(
            str(
                option.get("label")
                or option.get("text")
                or option.get("choice_index")
                or option_index
            )
        )
    choice_index = _to_int(action.get("choice_index"), default=0) or 0
    player = _as_mapping(event.get("player"))
    limitations = []
    if not screen.get("event_name"):
        limitations.append("missing event name")
    if not options:
        limitations.append("missing event option labels")
    if player.get("current_hp") is None or player.get("max_hp") is None:
        limitations.append("missing hp at event decision time")
    if "relics" not in event:
        limitations.append("missing relic snapshot at event decision time")

    evidence_quality = "complete" if not limitations else "partial"
    return DecisionSample(
        sample_id=f"trace:{index}",
        category="event",
        source="decision_trace",
        floor=_to_int(event.get("floor"), default=None),
        act=_to_int(event.get("act"), default=None),
        evidence_quality=evidence_quality,
        our_choice={
            "kind": "choose",
            "index": choice_index,
            "label": _choice_label(options, choice_index),
        },
        context={
            "event_name": screen.get("event_name") or "",
            "choices": options,
            "current_hp": _to_int(player.get("current_hp"), default=None),
            "max_hp": _to_int(player.get("max_hp"), default=None),
            "relics": [_item_name(relic) for relic in _as_list(event.get("relics"))],
        },
        limitations=limitations,
    )


def _trace_route_sample(
    event: Dict[str, Any],
    screen: Dict[str, Any],
    action: Dict[str, Any],
    index: int,
) -> DecisionSample:
    player = _as_mapping(event.get("player"))
    paths, has_route_context = _route_paths_from_trace_screen(screen)
    choice_index = _to_int(action.get("choice_index"), default=0) or 0
    limitations = []
    if not paths or not has_route_context:
        limitations.append("missing route candidate paths at decision time")
    if player.get("current_hp") is None or player.get("max_hp") is None:
        limitations.append("missing hp at route decision time")
    if "gold" not in event:
        limitations.append("missing gold at route decision time")
    if "relics" not in event:
        limitations.append("missing relic snapshot at route decision time")

    evidence_quality = "complete" if not limitations else "partial"
    return DecisionSample(
        sample_id=f"trace:{index}",
        category="route",
        source="decision_trace",
        floor=_to_int(event.get("floor"), default=None),
        act=_to_int(event.get("act"), default=None),
        evidence_quality=evidence_quality,
        our_choice={"kind": "map_node", "choice": choice_index},
        context={
            "paths": paths,
            "current_hp": _to_int(player.get("current_hp"), default=None),
            "max_hp": _to_int(player.get("max_hp"), default=None),
            "gold": _to_int(event.get("gold"), default=0) or 0,
            "relics": [_item_name(relic) for relic in _as_list(event.get("relics"))],
        },
        limitations=limitations,
    )


def _route_paths_from_trace_screen(screen: Dict[str, Any]) -> tuple[List[Dict[str, Any]], bool]:
    explicit_paths = [
        {
            "choice": _to_int(path.get("choice"), default=path_index),
            "label": path.get("label") or f"choice {path_index}",
            "nodes": [str(node) for node in _as_list(path.get("nodes"))],
        }
        for path_index, path in enumerate(_as_mapping_list(screen.get("paths")))
    ]
    if explicit_paths and any(len(path["nodes"]) > 1 for path in explicit_paths):
        return explicit_paths, True

    reconstructed = _reconstruct_route_paths_from_map(screen)
    if reconstructed:
        return reconstructed, True
    return explicit_paths, False


def _reconstruct_route_paths_from_map(
    screen: Dict[str, Any],
    max_depth: int = 6,
    max_paths_per_choice: int = 4,
) -> List[Dict[str, Any]]:
    nodes_by_coord = _trace_map_nodes_by_coord(screen)
    if not nodes_by_coord:
        return []

    paths: List[Dict[str, Any]] = []
    for choice, next_node in enumerate(_as_mapping_list(screen.get("next_nodes"))):
        start = nodes_by_coord.get(_trace_node_key(next_node))
        if not start:
            continue
        collected: List[List[Dict[str, Any]]] = []
        _collect_trace_route_paths(start, nodes_by_coord, [], collected, max_depth, max_paths_per_choice)
        for path in collected:
            paths.append(
                {
                    "choice": choice,
                    "label": " -> ".join(_trace_node_label(node) for node in path),
                    "nodes": [str(node.get("symbol") or "") for node in path],
                }
            )
    return paths


def _trace_map_nodes_by_coord(screen: Dict[str, Any]) -> Dict[tuple[Optional[int], Optional[int]], Dict[str, Any]]:
    map_summary = _as_mapping(screen.get("map"))
    nodes = {}
    for node in _as_mapping_list(map_summary.get("nodes")):
        nodes[_trace_node_key(node)] = node
    return nodes


def _trace_node_key(node: Dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    return (
        _to_int(node.get("x"), default=None),
        _to_int(node.get("y"), default=None),
    )


def _trace_node_label(node: Dict[str, Any]) -> str:
    return f"{node.get('symbol') or ''}@{node.get('x')},{node.get('y')}"


def _collect_trace_route_paths(
    node: Dict[str, Any],
    nodes_by_coord: Dict[tuple[Optional[int], Optional[int]], Dict[str, Any]],
    prefix: List[Dict[str, Any]],
    paths: List[List[Dict[str, Any]]],
    max_depth: int,
    max_paths: int,
) -> None:
    if len(paths) >= max_paths:
        return
    current = prefix + [node]
    children = [
        nodes_by_coord.get(_trace_node_key(child))
        for child in _as_mapping_list(node.get("children"))
    ]
    children = [child for child in children if child is not None]
    if not children or len(current) >= max_depth:
        paths.append(current)
        return
    for child in children:
        _collect_trace_route_paths(child, nodes_by_coord, current, paths, max_depth, max_paths)
        if len(paths) >= max_paths:
            break


def _reference_for_sample(sample: DecisionSample) -> ReferenceDecision:
    if sample.category == "shop":
        return _reference_shop(sample)
    if sample.category == "event":
        return _reference_event(sample)
    if sample.category == "route":
        return _reference_route(sample)
    if sample.category == "card_reward":
        return _reference_card_reward(sample)
    return ReferenceDecision("unknown", "Unsupported category.", "low")


def _native_bottled_reference_for_sample(sample: DecisionSample, oracle: Any) -> ReferenceDecision:
    result = oracle.evaluate(sample)
    return ReferenceDecision(
        choice=result.label,
        reason=result.reason,
        confidence=result.confidence,
        oracle_mode=(result.source or {}).get("mode") or "native_bottled",
        raw=dict(result.raw or {}),
        source=dict(result.source or {}),
        limitations=list(result.limitations or []),
    )


def _reference_shop(sample: DecisionSample) -> ReferenceDecision:
    ctx = sample.context
    if sample.evidence_quality != "complete":
        return ReferenceDecision(
            "unknown",
            "Partial shop evidence: full offer and prices are required for a high-confidence Bottled-style shop comparison.",
            "low",
        )

    gold = _to_int(ctx.get("gold"), 0) or 0
    purge_available = bool(ctx.get("purge_available"))
    purge_cost = _to_int(ctx.get("purge_cost"), 10**9) or 10**9
    deck = [_normalize_name(card) for card in _as_list(ctx.get("deck"))]
    cards = [item for item in _as_list(ctx.get("cards")) if isinstance(item, dict)]
    relics = [item for item in _as_list(ctx.get("relics")) if isinstance(item, dict)]

    can_purge = purge_available and gold >= purge_cost
    if can_purge and any(card in CURSE_NAMES or "curse" in card for card in deck):
        return ReferenceDecision("purge", "Bottled REQUESTED_STRIKE shop priority removes curses first.", "high")

    for card in cards:
        if _normalize_name(card.get("id") or card.get("name")) == "perfected strike" and gold >= (_to_int(card.get("price"), 10**9) or 10**9):
            return ReferenceDecision("Perfected Strike", "Bottled REQUESTED_STRIKE buys affordable Perfected Strike before general purge.", "high")

    for relic in relics:
        if _normalize_name(relic.get("name")) == "membership card" and gold >= (_to_int(relic.get("price"), 10**9) or 10**9):
            return ReferenceDecision("Membership Card", "Bottled shop priority buys affordable Membership Card.", "high")

    if can_purge and any(card in SHOP_REMOVAL_PRIORITY for card in deck):
        return ReferenceDecision("purge", "Bottled REQUESTED_STRIKE shop priority prefers starter removal before optional purchases.", "high")

    for desired in SHOP_RELIC_PRIORITY:
        for relic in relics:
            if _normalize_name(relic.get("name")) == desired and gold >= (_to_int(relic.get("price"), 10**9) or 10**9):
                return ReferenceDecision(str(relic.get("name")), f"Bottled shop relic list ranks {relic.get('name')} as buyable.", "high")

    deck_set = set(deck)
    for desired in SHOP_CARD_PRIORITY:
        for card in cards:
            if _normalize_name(card.get("id") or card.get("name")) == desired and gold >= (_to_int(card.get("price"), 10**9) or 10**9):
                if desired not in deck_set:
                    return ReferenceDecision(str(card.get("name") or card.get("id")), f"Bottled shop card list ranks {card.get('name') or card.get('id')} as buyable.", "high")

    return ReferenceDecision("leave", "Bottled shop handler leaves when no priority purchase is affordable.", "high")


def _reference_event(sample: DecisionSample) -> ReferenceDecision:
    ctx = sample.context
    event_name = _normalize_event_name(ctx.get("event_name"))
    choices = [str(choice) for choice in _as_list(ctx.get("choices"))]
    hp_pct = _hp_percent(ctx)

    if sample.evidence_quality != "complete":
        return ReferenceDecision(
            "unknown",
            "Partial event evidence: option labels and hp at decision time are required for high-confidence comparison.",
            "low",
        )
    if len(choices) <= 1:
        return ReferenceDecision(
            f"choose 0: {_choice_label(choices, 0)}",
            "Forced single available event option; not a strategic Bottled choice.",
            "low",
        )

    if event_name == "shining light":
        target_index = 0 if hp_pct >= 50 else 1
        target_label = _choice_label(choices, target_index)
        reason = "Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves."
        return ReferenceDecision(f"choose {target_index}: {target_label}", reason, "high")
    if event_name == "dead adventurer":
        index = _choice_index_by_keywords(choices, ["leave", "ignore"], default=1 if len(choices) > 1 else 0)
        return ReferenceDecision(f"choose {index}: {_choice_label(choices, index)}", f"Bottled common event handling avoids {ctx.get('event_name')} risk.", "high")
    if event_name == "golden shrine":
        relics = {_normalize_name(relic) for relic in _as_list(ctx.get("relics"))}
        index = 1 if "omamori" in relics and "ectoplasm" not in relics and len(choices) > 1 else 0
        return ReferenceDecision(
            f"choose {index}: {_choice_label(choices, index)}",
            "Bottled common event handling takes Golden Shrine gold, using Omamori for the curse option when available.",
            "high",
        )
    if event_name == "the mausoleum":
        relics = {_normalize_name(relic) for relic in _as_list(ctx.get("relics"))}
        index = 0 if "omamori" in relics else 1 if len(choices) > 1 else 0
        return ReferenceDecision(
            f"choose {index}: {_choice_label(choices, index)}",
            "Bottled common event handling opens The Mausoleum only when Omamori can absorb the curse.",
            "high",
        )
    if event_name == "world of goop":
        index = 0 if hp_pct >= 70 else 1
        return ReferenceDecision(f"choose {index}: {_choice_label(choices, index)}", "Bottled REQUESTED_STRIKE takes Goop gold only at 70%+ HP.", "high")
    if event_name == "wing statue":
        index = 0 if hp_pct >= 60 else 1
        return ReferenceDecision(f"choose {index}: {_choice_label(choices, index)}", "Bottled REQUESTED_STRIKE purges at Wing Statue only at 60%+ HP.", "high")
    if event_name in {"nest", "lab", "drug dealer"}:
        return ReferenceDecision(f"choose 0: {_choice_label(choices, 0)}", f"Bottled common event handling takes the main {ctx.get('event_name')} reward.", "medium")
    return ReferenceDecision(f"choose 0: {_choice_label(choices, 0)}", "Bottled common event fallback chooses the first option.", "medium")


def _reference_route(sample: DecisionSample) -> ReferenceDecision:
    ctx = sample.context
    paths = [path for path in _as_list(ctx.get("paths")) if isinstance(path, dict)]
    if not paths:
        return ReferenceDecision(
            "unknown",
            "Partial route evidence: candidate map paths are required for Bottled reward-to-survivability scoring.",
            "low",
        )

    scored = []
    for path in paths:
        score, detail = _score_route_path(path, ctx, sample.act)
        scored.append((score, path, detail))
    scored.sort(key=lambda item: item[0], reverse=True)
    best_score, best_path, detail = scored[0]
    return ReferenceDecision(
        f"choice {best_path.get('choice')}",
        f"Bottled common map scoring prefers reward-to-survivability {best_score:.2f}: {detail}",
        "high",
    )


def _reference_card_reward(sample: DecisionSample) -> ReferenceDecision:
    ctx = sample.context
    offered = [str(card) for card in _as_list(ctx.get("offered"))]
    deck = [_normalize_name(card) for card in _as_list(ctx.get("deck"))]
    deck_counts: Dict[str, int] = {}
    for card in deck:
        deck_counts[card] = deck_counts.get(card, 0) + 1

    if not offered:
        return ReferenceDecision("skip", "No offered cards are available.", "low")

    for card in offered:
        key = _normalize_name(card)
        limit = REQUESTED_STRIKE_DESIRED_CARDS.get(key)
        compact_limit = REQUESTED_STRIKE_DESIRED_CARDS.get(_compact_key(card))
        desired_limit = limit if limit is not None else compact_limit
        if desired_limit is None:
            continue
        if deck_counts.get(key, 0) < desired_limit:
            confidence = "high" if sample.evidence_quality == "complete" else "medium"
            return ReferenceDecision(
                card,
                f"Bottled REQUESTED_STRIKE desired-card list wants up to {desired_limit} copy/copies of {card}.",
                confidence,
            )

    if ctx.get("can_bowl"):
        return ReferenceDecision("bowl", "Bottled card reward handler uses Singing Bowl when no desired card is offered.", "medium")
    return ReferenceDecision("skip", "Bottled card reward handler skips when no desired card is offered.", "medium")


def _score_route_path(path: Dict[str, Any], ctx: Dict[str, Any], act_value: Optional[int]) -> tuple[float, str]:
    nodes = [str(node) for node in _as_list(path.get("nodes"))]
    act = max(1, _to_int(act_value or ctx.get("act"), 1) or 1)
    max_hp = max(1.0, float(_to_int(ctx.get("max_hp"), 80) or 80))
    hp = float(_to_int(ctx.get("current_hp"), int(max_hp)) or int(max_hp))
    gold = float(_to_int(ctx.get("gold"), 0) or 0)
    relics = {_normalize_name(relic) for relic in _as_list(ctx.get("relics"))}
    reward = 0.0
    survivability = 1.0

    for node in nodes:
        symbol = node.upper()
        if symbol == "M":
            reward += 1.0
            gold += 15
            hp -= act * 5
            if "burning blood" in relics:
                hp += 6
        elif symbol == "E":
            reward += 2.5
            gold += 30
            hp -= (act + 1) * 15
            if "burning blood" in relics:
                hp += 6
        elif symbol == "T":
            reward += 1.5
        elif symbol == "?":
            reward += 1.0 if act == 1 else 1.5
        elif symbol == "R":
            if hp / max_hp >= 0.6:
                reward += 1.1
            else:
                hp += max_hp * 0.3
        elif symbol == "$":
            gold_to_spend = min(gold, 300 if "membership card" in relics else 200)
            if "membership card" not in relics:
                gold_to_spend *= 2
            reward += gold_to_spend / 100
            gold -= gold_to_spend / (1 if "membership card" in relics else 2)

        barrier = max_hp / 4
        if hp < barrier:
            survivability *= max((hp + barrier * 2) / (barrier * 3), 0)
        hp = min(max(hp, 0), max_hp)

    score = reward + (survivability - 1) * 15
    detail = f"{path.get('label') or nodes}: reward={reward:.2f}, survivability={survivability:.2f}"
    return score, detail


def _current_choice_text(sample: DecisionSample) -> str:
    choice = sample.our_choice
    kind = str(choice.get("kind") or "")
    if sample.category == "event" and "index" in choice:
        label = choice.get("label") or _choice_label(_as_list(sample.context.get("choices")), _to_int(choice.get("index"), 0) or 0)
        return f"choose {choice.get('index')}: {label}"
    if sample.category == "route":
        value = choice.get("choice") or choice.get("name") or kind
        return f"choice {value}" if kind == "map_node" else str(value)
    if kind in {"skip", "take", "buy_card", "purchase", "purge"}:
        return str(choice.get("name") or kind)
    return str(choice.get("label") or choice.get("name") or choice.get("choice") or kind or "unknown")


def _choices_match(current: str, reference: str) -> bool:
    if _normalize_name(reference) == "unknown":
        return True
    return _normalize_name(current) == _normalize_name(reference)


def _normalize_reference_mode(value: str) -> str:
    normalized = str(value or "bottled_style").replace("-", "_").lower()
    if normalized in {"native_bottled", "bottled_style"}:
        return normalized
    raise ValueError(f"Unsupported reference mode: {value}")


def _combined_confidence(evidence_quality: str, reference_confidence: str, match: bool) -> str:
    if evidence_quality != "complete":
        return "low" if not match else "low"
    return reference_confidence


def _load_json_object(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path}") from exc


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _as_mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_mapping_list(value: Any) -> List[Dict[str, Any]]:
    return [item for item in _as_list(value) if isinstance(item, dict)]


def _item_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("id") or "")
    return str(value or "")


def _priced_item(value: Any) -> Dict[str, Any]:
    mapping = _as_mapping(value)
    return {
        "name": str(mapping.get("name") or mapping.get("id") or ""),
        "id": str(mapping.get("id") or mapping.get("name") or ""),
        "price": _to_int(mapping.get("price"), default=0) or 0,
    }


def _action_name(action: Dict[str, Any]) -> str:
    card = _as_mapping(action.get("card"))
    potion = _as_mapping(action.get("potion"))
    relic = _as_mapping(action.get("relic"))
    return str(
        action.get("name")
        or card.get("name")
        or potion.get("name")
        or relic.get("name")
        or ""
    )


def _list_get(values: Sequence[Any], index: int) -> Any:
    return values[index] if 0 <= index < len(values) else None


def _to_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: Optional[float] = 0.0) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_name(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\+\d*$", "", text)
    text = text.replace("_R", "").replace("_G", "").replace("_B", "").replace("_P", "")
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _compact_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _normalize_event_name(value: Any) -> str:
    text = _normalize_name(value)
    aliases = {
        "goldenshrine": "golden shrine",
        "shininglight": "shining light",
        "deadadventurer": "dead adventurer",
        "mausoleum": "the mausoleum",
        "the mushroom lair": "mushrooms",
        "drug dealer": "drug dealer",
    }
    return aliases.get(_compact_key(text), text)


def _hp_percent(ctx: Dict[str, Any]) -> float:
    current = _to_int(ctx.get("current_hp"), None)
    maximum = _to_int(ctx.get("max_hp"), None)
    if current is None or maximum in (None, 0):
        return 100.0
    return current / maximum * 100


def _choice_label(choices: Sequence[Any], index: int) -> str:
    if 0 <= index < len(choices):
        return str(choices[index])
    return str(index)


def _choice_index_by_keywords(choices: Sequence[str], keywords: Sequence[str], default: int = 0) -> int:
    for index, choice in enumerate(choices):
        lowered = choice.lower()
        if any(keyword in lowered for keyword in keywords):
            return index
    return default


def _format_counts(counts: Dict[str, int]) -> str:
    if not counts:
        return "-"
    return ", ".join(f"{key}={counts[key]}" for key in sorted(counts))


def _reference_summary(rows: Sequence[ComparisonRow]) -> str:
    modes = {row.oracle_mode for row in rows}
    if "native_bottled" in modes:
        paths = sorted(
            {
                str(row.oracle_source.get("path"))
                for row in rows
                if row.oracle_source.get("path")
            }
        )
        path_text = f" from `{paths[0]}`" if len(paths) == 1 else ""
        return (
            "Reference: native Bottled Ironclad `REQUESTED_STRIKE` oracle"
            f"{path_text}; unsupported rows are explicit and not treated as high-confidence labels."
        )
    return "Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only."


def _is_fixture_source(source: str) -> bool:
    return str(source or "").startswith("fixture")


def _issue_signature(row: ComparisonRow) -> tuple[str, str, str]:
    return (
        row.category,
        _normalize_name(row.reference_choice),
        _normalize_name(row.reason),
    )


def _issue_occurrence_key(row: ComparisonRow) -> tuple[str, str, Optional[int], str, str, str]:
    return (
        row.category,
        row.source,
        row.floor,
        _normalize_name(row.current_choice),
        _normalize_name(row.reference_choice),
        _normalize_name(row.reason),
    )


def _best_confidence(rows: Sequence[ComparisonRow]) -> str:
    confidence_score = {"high": 0, "medium": 1, "low": 2}
    return min(
        (row.confidence for row in rows),
        key=lambda confidence: confidence_score.get(confidence, 3),
    )


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _reason_with_limitations(row: ComparisonRow) -> str:
    if not row.limitations:
        return row.reason
    return f"{row.reason} Limitations: {'; '.join(row.limitations)}"


if __name__ == "__main__":
    raise SystemExit(main())
