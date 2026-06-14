#!/usr/bin/env python3
"""Offline operating-decision comparator against Bottled-style references."""

from __future__ import annotations

import argparse
import json
import re
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


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


def load_jsonl_samples(path: Path | str, tail: int = 2000) -> List[DecisionSample]:
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
        sample = _sample_from_trace_event(event, index)
        if sample:
            samples.append(sample)
    return samples


def compare_samples(samples: Iterable[DecisionSample]) -> List[ComparisonRow]:
    rows: List[ComparisonRow] = []
    for sample in samples:
        reference = _reference_for_sample(sample)
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
                limitations=sample.limitations,
            )
        )
    return rows


def rank_issues(rows: Sequence[ComparisonRow], max_issues: int = 5) -> List[ComparisonRow]:
    priority = {"shop": 0, "event": 1, "route": 2, "card_reward": 3}
    confidence_score = {"high": 0, "medium": 1, "low": 2}
    candidates = [
        row for row in rows
        if not row.match and row.confidence in {"high", "medium"}
    ]
    candidates.sort(
        key=lambda row: (
            confidence_score.get(row.confidence, 3),
            priority.get(row.category, 9),
            row.floor if row.floor is not None else 999,
            row.sample_id,
        )
    )
    return candidates[:max_issues]


def render_markdown_report(
    rows: Sequence[ComparisonRow],
    issues: Optional[Sequence[ComparisonRow]] = None,
) -> str:
    issue_rows = list(rank_issues(rows) if issues is None else issues)
    lines = [
        "# Offline Decision Comparator POC",
        "",
        "Reference: Bottled-style Ironclad `REQUESTED_STRIKE` handlers encoded locally for analysis only.",
        "No gameplay-code fix is applied by this report.",
        "",
        "## Summary",
        "",
    ]
    by_category: Dict[str, int] = {}
    by_evidence: Dict[str, int] = {}
    mismatches = 0
    for row in rows:
        by_category[row.category] = by_category.get(row.category, 0) + 1
        by_evidence[row.evidence_quality] = by_evidence.get(row.evidence_quality, 0) + 1
        if not row.match:
            mismatches += 1
    lines.extend(
        [
            f"- Samples: {len(rows)}",
            f"- Differences: {mismatches}",
            f"- Categories: {_format_counts(by_category)}",
            f"- Evidence quality: {_format_counts(by_evidence)}",
            "",
            "## Comparison Rows",
            "",
            "| Category | Source | Floor | Evidence | Current Choice | Bottled Reference | Confidence | Reason |",
            "|---|---|---:|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {category} | {source} | {floor} | {evidence} | {current} | {reference} | {confidence} | {reason} |".format(
                category=_md(row.category),
                source=_md(row.source),
                floor="" if row.floor is None else row.floor,
                evidence=_md(row.evidence_quality),
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

    lines.extend(
        [
            "",
            "## Repair Gate",
            "",
            "No gameplay-code fix is applied. Treat these rows as candidates for later test-first review only when they repeat, remain high confidence, and are relevant to the first Ironclad win objective.",
            "",
        ]
    )
    return "\n".join(lines)


def build_report(
    fixture_paths: Sequence[Path],
    run_paths: Sequence[Path],
    trace_paths: Sequence[Path],
) -> str:
    samples: List[DecisionSample] = []
    for path in fixture_paths:
        samples.extend(load_fixture_samples(path))
    for path in run_paths:
        samples.extend(load_run_samples(path))
    for path in trace_paths:
        samples.extend(load_jsonl_samples(path))
    rows = compare_samples(samples)
    return render_markdown_report(rows, rank_issues(rows))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", action="append", type=Path, default=[])
    parser.add_argument("--run", action="append", type=Path, default=[])
    parser.add_argument("--trace", action="append", type=Path, default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = build_report(args.fixture, args.run, args.trace)
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
    screen_type = str(event.get("screen_type") or "")
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

    if event_name == "shining light":
        target_index = 0 if hp_pct >= 50 else 1
        target_label = _choice_label(choices, target_index)
        reason = "Bottled REQUESTED_STRIKE enters Shining Light at 50%+ HP, otherwise leaves."
        return ReferenceDecision(f"choose {target_index}: {target_label}", reason, "high")
    if event_name in {"dead adventurer", "the mausoleum", "golden shrine"}:
        index = _choice_index_by_keywords(choices, ["leave", "ignore"], default=1 if len(choices) > 1 else 0)
        return ReferenceDecision(f"choose {index}: {_choice_label(choices, index)}", f"Bottled common event handling avoids {ctx.get('event_name')} risk.", "high")
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


def _list_get(values: Sequence[Any], index: int) -> Any:
    return values[index] if 0 <= index < len(values) else None


def _to_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
    try:
        return int(value)
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


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _reason_with_limitations(row: ComparisonRow) -> str:
    if not row.limitations:
        return row.reason
    return f"{row.reason} Limitations: {'; '.join(row.limitations)}"


if __name__ == "__main__":
    raise SystemExit(main())
