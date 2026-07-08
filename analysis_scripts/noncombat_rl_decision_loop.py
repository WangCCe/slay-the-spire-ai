#!/usr/bin/env python3
"""Export non-combat operating decisions as RL-readiness samples."""

from __future__ import annotations

import json
import argparse
import re
import sys
from collections import Counter, deque
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.offline_decision_comparator import (
    compare_samples,
    sample_from_trace_event,
)


SCHEMA_VERSION = "noncombat-rl-decision-v1"
SUPPORTED_CATEGORIES = ("shop", "event", "route", "card_reward")


def export_samples_from_trace(
    path,
    tail: int = 2000,
    since_unix: Optional[float] = None,
    reference_mode: str = "bottled_style",
    bottled_repo_path=None,
):
    return export_samples_from_trace_with_reference(
        path,
        tail=tail,
        since_unix=since_unix,
        reference_mode=reference_mode,
        bottled_repo_path=bottled_repo_path,
    )


def export_samples_from_trace_with_reference(
    path,
    tail: int = 2000,
    since_unix: Optional[float] = None,
    reference_mode: str = "bottled_style",
    bottled_repo_path=None,
):
    rows: deque[str] = deque(maxlen=max(1, tail))
    with Path(path).open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            rows.append(line)

    exported = []
    for index, line in enumerate(rows):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_time = _to_float(event.get("unix_time"))
        if since_unix is not None and (event_time is None or event_time < since_unix):
            continue
        decision_sample = sample_from_trace_event(event, index)
        if decision_sample is None:
            continue
        comparison_row = compare_samples(
            [decision_sample],
            reference_mode=reference_mode,
            bottled_repo_path=bottled_repo_path,
        )[0]
        exported.append(
            build_trainable_sample(
                decision_sample,
                comparison_row,
                trace_event=event,
            )
        )
    return exported


def build_trainable_sample(decision_sample, comparison_row, trace_event=None):
    candidates = normalize_candidates(decision_sample)
    selected_id = _selected_action_id(decision_sample, candidates)
    bottled_id = _label_to_candidate_id(comparison_row.reference_choice, candidates)
    selected_label = _candidate_label(selected_id, candidates) or comparison_row.current_choice

    return {
        "schema_version": SCHEMA_VERSION,
        "sample_id": decision_sample.sample_id,
        "category": decision_sample.category,
        "source": decision_sample.source,
        "floor": decision_sample.floor,
        "act": decision_sample.act,
        "unix_time": _to_float((trace_event or {}).get("unix_time")),
        "state": _state_snapshot(decision_sample, trace_event or {}),
        "candidate_actions": candidates,
        "selected_action_id": selected_id,
        "current_policy_label": {
            "label": selected_label,
            "action_id": selected_id,
        },
        "bottled_label": {
            "label": comparison_row.reference_choice,
            "action_id": bottled_id,
            "confidence": comparison_row.confidence,
            "reason": comparison_row.reason,
            "oracle_mode": getattr(comparison_row, "oracle_mode", "bottled_style"),
            "source": dict(getattr(comparison_row, "oracle_source", {}) or {}),
            "raw": dict(getattr(comparison_row, "raw_reference", {}) or {}),
            "limitations": list(getattr(comparison_row, "limitations", []) or []),
        },
        "evidence_quality": decision_sample.evidence_quality,
        "limitations": list(decision_sample.limitations),
        "outcome": {"join_status": "missing", "included_in_gate": False},
    }


def normalize_candidates(decision_sample):
    category = decision_sample.category
    ctx = decision_sample.context
    if category == "card_reward":
        candidates = [
            _candidate(
                f"card_reward:take:{_slug(card)}",
                "take",
                str(card),
                True,
                {"name": card},
            )
            for card in ctx.get("offered", [])
        ]
        if ctx.get("can_bowl"):
            candidates.append(_candidate("card_reward:bowl", "bowl", "bowl", True, {}))
        if ctx.get("can_skip", True):
            candidates.append(_candidate("card_reward:skip", "skip", "skip", True, {}))
        return candidates

    if category == "shop":
        candidates = []
        for card in ctx.get("cards", []):
            candidates.append(
                _candidate(
                    f"shop:buy_card:{_slug(card.get('name'))}",
                    "buy_card",
                    card.get("name", ""),
                    True,
                    dict(card),
                )
            )
        for relic in ctx.get("relics", []):
            candidates.append(
                _candidate(
                    f"shop:buy_relic:{_slug(relic.get('name'))}",
                    "buy_relic",
                    relic.get("name", ""),
                    True,
                    dict(relic),
                )
            )
        for potion in ctx.get("potions", []):
            candidates.append(
                _candidate(
                    f"shop:buy_potion:{_slug(potion.get('name'))}",
                    "buy_potion",
                    potion.get("name", ""),
                    True,
                    dict(potion),
                )
            )
        if ctx.get("purge_available"):
            purge_target = _first_removable_card(ctx.get("deck", []))
            candidates.append(
                _candidate(
                    f"shop:purge:{_slug(purge_target)}",
                    "purge",
                    f"purge {purge_target}",
                    True,
                    {"cost": ctx.get("purge_cost")},
                )
            )
        candidates.append(_candidate("shop:leave", "leave", "leave", True, {}))
        return candidates

    if category == "event":
        return [
            _candidate(
                f"event:choice:{index}",
                "choose",
                f"choose {index}: {label}",
                True,
                {"index": index, "label": label},
            )
            for index, label in enumerate(ctx.get("choices", []))
        ]

    if category == "route":
        seen = set()
        candidates = []
        for path in ctx.get("paths", []):
            choice = _to_int(path.get("choice"), len(candidates)) or 0
            if choice in seen:
                continue
            seen.add(choice)
            candidates.append(
                _candidate(
                    f"route:choice:{choice}",
                    "map_node",
                    f"route {choice}: {path.get('label', '')}",
                    True,
                    dict(path),
                )
            )
        return candidates

    return []


def attach_live_outcomes(samples, outcomes, tolerance_seconds: int = 30):
    joined = []
    for sample in samples:
        sample_copy = dict(sample)
        sample_time = _to_float(sample_copy.get("unix_time"))
        matches = [
            outcome
            for outcome in outcomes
            if outcome.get("ai_marked", True)
            and sample_time is not None
            and outcome.get("start_unix") is not None
            and outcome.get("end_unix") is not None
            and outcome["start_unix"] - tolerance_seconds
            <= sample_time
            <= outcome["end_unix"] + tolerance_seconds
        ]
        if len(matches) == 1:
            outcome = dict(matches[0])
            sample_copy["outcome"] = {
                "join_status": "matched",
                "included_in_gate": True,
                "run_file": outcome.get("run_file"),
                "victory": bool(outcome.get("victory")),
                "floor_reached": outcome.get("floor_reached"),
                "killed_by": outcome.get("killed_by") or "",
                "playtime": outcome.get("playtime"),
            }
        elif len(matches) > 1:
            sample_copy["outcome"] = {
                "join_status": "ambiguous",
                "included_in_gate": False,
            }
        else:
            sample_copy["outcome"] = {
                "join_status": "missing",
                "included_in_gate": False,
            }
        joined.append(sample_copy)
    return joined


def load_run_outcomes(
    runs_dir,
    character: str = "IRONCLAD",
    limit: int = 20,
    ai_markers_path=None,
):
    runs_root = Path(runs_dir)
    character_dir = runs_root / character
    marker_path = Path(ai_markers_path) if ai_markers_path else runs_root / "ai_games.txt"
    ai_markers = _load_ai_markers(marker_path)
    run_files = sorted(
        character_dir.glob("*.run"),
        key=lambda path: path.stat().st_mtime,
    )
    if limit > 0:
        run_files = run_files[-limit:]

    outcomes = []
    for run_file in run_files:
        start_unix = _to_int(run_file.stem, default=None)
        if start_unix is None:
            continue
        try:
            record = json.loads(run_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        playtime = _to_int(record.get("playtime"), 0) or 0
        outcomes.append(
            {
                "run_file": run_file.name,
                "start_unix": start_unix,
                "end_unix": start_unix + playtime,
                "victory": bool(record.get("victory")),
                "floor_reached": _to_int(record.get("floor_reached"), 0) or 0,
                "killed_by": str(record.get("killed_by") or ""),
                "playtime": playtime,
                "ai_marked": _is_ai_marked(start_unix, ai_markers),
            }
        )
    return outcomes


def default_reward_contract():
    return {
        "version": "noncombat-reward-readiness-v1",
        "components": [
            {
                "name": "run_victory",
                "required_outcome_field": "victory",
                "direction": "positive",
            },
            {
                "name": "floor_reached",
                "required_outcome_field": "floor_reached",
                "direction": "positive",
            },
            {
                "name": "decision_survival",
                "required_outcome_field": "killed_by",
                "direction": "diagnostic",
            },
        ],
        "exclusions": [
            "combat card play reward shaping",
            "Bottled label as direct reward",
        ],
        "unresolved_gaps": [
            "No learned non-combat policy is trained by this change.",
        ],
    }


def evaluate_promotion(
    samples,
    reward_contract=None,
    min_complete_per_category: int = 1,
    min_matched_outcomes: int = 1,
):
    category_counts = Counter(sample.get("category") for sample in samples)
    complete_counts = Counter(
        sample.get("category")
        for sample in samples
        if sample.get("evidence_quality") == "complete"
    )
    matched = [
        sample
        for sample in samples
        if sample.get("outcome", {}).get("included_in_gate")
    ]
    blocking_reasons = []

    for category in SUPPORTED_CATEGORIES:
        if complete_counts.get(category, 0) < min_complete_per_category:
            blocking_reasons.append(f"missing_complete_{category}_samples")

    action_categories = {
        sample.get("category")
        for sample in samples
        if sample.get("candidate_actions")
    }
    missing_action_categories = [
        category for category in SUPPORTED_CATEGORIES if category not in action_categories
    ]
    if missing_action_categories:
        blocking_reasons.append("candidate_actions_missing")

    if len(matched) < min_matched_outcomes:
        blocking_reasons.append("matched_live_outcomes_missing")
    if not reward_contract:
        blocking_reasons.append("reward_contract_missing")

    status = "allowed" if not blocking_reasons else "blocked"
    return {
        "status": status,
        "blocking_reasons": blocking_reasons,
        "readiness": {
            "state": "present" if samples else "missing",
            "action": "present" if not missing_action_categories else "missing",
            "reward": "present" if reward_contract else "missing",
            "evaluation": "present" if matched else "missing",
        },
        "metrics": {
            "sample_count": len(samples),
            "category_counts": dict(category_counts),
            "complete_category_counts": dict(complete_counts),
            "matched_outcomes": len(matched),
        },
        "formal_noncombat_rl_training_ready": False,
        "formal_noncombat_rl_training_guard": "not_started_by_this_change",
    }


def render_readiness_report(samples, gate_result):
    category_counts = Counter(sample.get("category") for sample in samples)
    evidence_counts = Counter(sample.get("evidence_quality") for sample in samples)
    oracle_mode_counts = Counter(
        sample.get("bottled_label", {}).get("oracle_mode", "bottled_style")
        for sample in samples
    )
    disagreements = _current_vs_bottled_disagreements(samples)
    disagreement_counts = Counter(sample.get("category") for sample in disagreements)
    high_confidence_disagreements = [
        sample
        for sample in disagreements
        if sample.get("evidence_quality") == "complete"
        and sample.get("bottled_label", {}).get("confidence") == "high"
    ]
    matched = [
        sample
        for sample in samples
        if sample.get("outcome", {}).get("included_in_gate")
    ]
    bottled_matches = sum(
        1
        for sample in samples
        if sample.get("current_policy_label", {}).get("action_id")
        and sample.get("current_policy_label", {}).get("action_id")
        == sample.get("bottled_label", {}).get("action_id")
    )
    smoke = combat_rl_smoke_command(
        r"D:\anaconda\envs\stsai\python.exe",
        r"D:\SteamLibrary\steamapps\common\SlayTheSpire",
    )

    lines = [
        "# Non-Combat RL Decision Loop Readiness",
        "",
        "## Summary",
        "",
        f"- Promotion status: {gate_result.get('status', 'blocked')}",
        f"- Samples: {len(samples)}",
        f"- Blocking reasons: {_format_list(gate_result.get('blocking_reasons', []))}",
        "",
        "## Sample Coverage",
        "",
        f"- Categories: {_format_counts(category_counts)}",
        f"- Evidence quality: {_format_counts(evidence_counts)}",
        "",
        "## Bottled Agreement",
        "",
        f"- Current/Bottled action-id matches: {bottled_matches}/{len(samples)}",
        f"- Oracle modes: {_format_counts(oracle_mode_counts)}",
        "",
        "## Current-vs-Bottled Disagreements",
        "",
        f"- Action-id disagreements: {len(disagreements)}/{len(samples)}",
        f"- Complete high-confidence disagreements: {len(high_confidence_disagreements)}",
        f"- By category: {_format_counts(disagreement_counts)}",
        "",
        "### Top Disagreement Pairs",
        "",
        *_render_disagreement_pairs(disagreements),
        "",
        "## Live Outcomes",
        "",
        f"- Matched outcomes included in gate: {len(matched)}",
        "",
        "## Reward readiness",
        "",
        f"- Status: {gate_result.get('readiness', {}).get('reward', 'missing')}",
        "",
        "## Promotion Gate",
        "",
        f"- Readiness: {gate_result.get('readiness', {})}",
        f"- Metrics: {gate_result.get('metrics', {})}",
        "",
        "## Training Guard",
        "",
        "- Formal non-combat RL training: blocked",
        f"- Guard: {gate_result.get('formal_noncombat_rl_training_guard', 'not_started_by_this_change')}",
        "",
        "## Combat RL Smoke",
        "",
        f"- Command: `{smoke}`",
        "",
    ]
    return "\n".join(lines)


def _current_vs_bottled_disagreements(samples):
    disagreements = []
    for sample in samples:
        current_id = (
            sample.get("current_policy_label", {}).get("action_id")
            or sample.get("selected_action_id")
        )
        bottled_id = sample.get("bottled_label", {}).get("action_id")
        if current_id and bottled_id and current_id != bottled_id:
            disagreements.append(sample)
    return disagreements


def _render_disagreement_pairs(samples, limit: int = 12):
    if not samples:
        return ["No current-vs-bottled action-id disagreement is present."]

    groups = {}
    for sample in samples:
        category = str(sample.get("category") or "unknown")
        current_id = str(
            sample.get("current_policy_label", {}).get("action_id")
            or sample.get("selected_action_id")
            or "unknown"
        )
        bottled_id = str(sample.get("bottled_label", {}).get("action_id") or "unknown")
        key = (category, current_id, bottled_id)
        group = groups.setdefault(
            key,
            {
                "count": 0,
                "high": 0,
                "complete": 0,
                "examples": [],
            },
        )
        group["count"] += 1
        if sample.get("bottled_label", {}).get("confidence") == "high":
            group["high"] += 1
        if sample.get("evidence_quality") == "complete":
            group["complete"] += 1
        if len(group["examples"]) < 3:
            group["examples"].append(str(sample.get("sample_id") or "unknown"))

    ranked = sorted(
        groups.items(),
        key=lambda item: (-item[1]["count"], item[0][0], item[0][1], item[0][2]),
    )
    lines = []
    for (category, current_id, bottled_id), group in ranked[:limit]:
        lines.append(
            f"- {category}: {current_id} -> {bottled_id} "
            f"({group['count']}x, high={group['high']}, complete={group['complete']}, "
            f"examples={_format_list(group['examples'])})"
        )
    return lines


def combat_rl_smoke_command(python, game_dir, max_games: int = 1):
    return (
        f'"{python}" scripts\\run_training_batch.py '
        f'--python "{python}" '
        f'--game-dir "{game_dir}" '
        f"--agent combat_rl --eval --max-games {max_games} --dry-run"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Export non-combat RL decision samples and readiness report."
    )
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--trace-tail", type=int, default=2000)
    parser.add_argument("--since-unix", type=float, default=None)
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--character", default="IRONCLAD")
    parser.add_argument(
        "--reference-mode",
        choices=["bottled-style", "bottled_style", "native-bottled", "native_bottled"],
        default="bottled-style",
    )
    parser.add_argument("--bottled-repo", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json-output", type=Path, default=None)
    args = parser.parse_args(argv)

    samples = export_samples_from_trace(
        args.trace,
        tail=args.trace_tail,
        since_unix=args.since_unix,
        reference_mode=args.reference_mode,
        bottled_repo_path=args.bottled_repo,
    )
    if args.runs_dir:
        outcomes = load_run_outcomes(args.runs_dir, character=args.character)
        samples = attach_live_outcomes(samples, outcomes)

    gate_result = evaluate_promotion(samples, reward_contract=default_reward_contract())
    report = render_readiness_report(samples, gate_result)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(
            "\n".join(json.dumps(sample, sort_keys=True) for sample in samples)
            + ("\n" if samples else ""),
            encoding="utf-8",
        )

    print(f"Promotion status: {gate_result['status']}")
    if gate_result["blocking_reasons"]:
        print(f"Blocking reasons: {', '.join(gate_result['blocking_reasons'])}")
    return 0


def _candidate(action_id: str, kind: str, label: str, available: bool, raw: Dict[str, Any]):
    return {
        "action_id": action_id,
        "kind": kind,
        "label": label,
        "available": bool(available),
        "raw": raw,
    }


def _selected_action_id(decision_sample, candidates: List[Dict[str, Any]]) -> Optional[str]:
    choice = decision_sample.our_choice
    category = decision_sample.category
    kind = str(choice.get("kind") or "")
    name = str(choice.get("name") or "")

    if category == "card_reward":
        if kind == "take":
            return _candidate_by_kind_and_slug(candidates, "take", name)
        if kind in {"skip", "bowl"}:
            return f"card_reward:{kind}"
    if category == "shop":
        if kind == "buy_card":
            return _candidate_by_kind_and_slug(candidates, "buy_card", name)
        if kind == "purge":
            if _slug(name) in {"", "purge"}:
                return _candidate_by_kind(candidates, "purge")
            return _candidate_by_kind_and_slug(candidates, "purge", name)
        if kind == "leave":
            return "shop:leave"
        if kind == "purchase":
            return _candidate_by_slug(candidates, name)
    if category == "event" and kind == "choose":
        return f"event:choice:{_to_int(choice.get('index'), 0) or 0}"
    if category == "route" and kind == "map_node":
        return f"route:choice:{_to_int(choice.get('choice'), 0) or 0}"
    return _candidate_by_slug(candidates, name)


def _label_to_candidate_id(label: str, candidates: List[Dict[str, Any]]) -> Optional[str]:
    normalized = _normalize_text(label)
    for candidate in candidates:
        if _normalize_text(candidate.get("label")) == normalized:
            return str(candidate.get("action_id"))
    for candidate in candidates:
        raw = candidate.get("raw") or {}
        if _normalize_text(raw.get("name")) == normalized:
            return str(candidate.get("action_id"))
    if normalized.startswith("choose "):
        match = re.match(r"choose\s+(\d+)", normalized)
        if match:
            return f"event:choice:{match.group(1)}"
    if normalized.startswith("choice "):
        match = re.match(r"choice\s+(\d+)", normalized)
        if match:
            return f"route:choice:{match.group(1)}"
    if normalized == "skip":
        return _candidate_by_kind(candidates, "skip")
    if normalized == "bowl":
        return _candidate_by_kind(candidates, "bowl")
    if normalized == "leave":
        return _candidate_by_kind(candidates, "leave")
    if normalized == "purge":
        return _candidate_by_kind(candidates, "purge")
    return _candidate_by_slug(candidates, label)


def _state_snapshot(decision_sample, trace_event: Dict[str, Any]):
    ctx = decision_sample.context
    return {
        "player": dict(trace_event.get("player") or {}),
        "gold": trace_event.get("gold", ctx.get("gold")),
        "deck": _names(trace_event.get("deck")) or list(ctx.get("deck", [])),
        "relics": _names(trace_event.get("relics")) or list(ctx.get("relics", [])),
        "potions": _names(trace_event.get("potions")),
        "screen": dict(trace_event.get("screen") or {}),
        "context": dict(ctx),
    }


def _candidate_label(action_id: Optional[str], candidates: List[Dict[str, Any]]) -> Optional[str]:
    for candidate in candidates:
        if candidate.get("action_id") == action_id:
            return str(candidate.get("label") or "")
    return None


def _candidate_by_kind(candidates: List[Dict[str, Any]], kind: str) -> Optional[str]:
    for candidate in candidates:
        if candidate.get("kind") == kind:
            return str(candidate.get("action_id"))
    return None


def _candidate_by_kind_and_slug(
    candidates: List[Dict[str, Any]],
    kind: str,
    value: Any,
) -> Optional[str]:
    target = _slug(value)
    for candidate in candidates:
        if candidate.get("kind") != kind:
            continue
        raw = candidate.get("raw") or {}
        if _slug(raw.get("name") or candidate.get("label")) == target:
            return str(candidate.get("action_id"))
        if _slug(str(candidate.get("label")).replace("purge ", "")) == target:
            return str(candidate.get("action_id"))
    return None


def _candidate_by_slug(candidates: List[Dict[str, Any]], value: Any) -> Optional[str]:
    target = _slug(value)
    for candidate in candidates:
        raw = candidate.get("raw") or {}
        if _slug(raw.get("name") or candidate.get("label")) == target:
            return str(candidate.get("action_id"))
    return None


def _first_removable_card(deck: List[Any]) -> str:
    normalized = [_name(card) for card in deck]
    for name in normalized:
        if _normalize_text(name) in {"curse", "injury", "shame", "doubt", "regret", "pain"}:
            return name
    for name in normalized:
        if _normalize_text(name) in {"strike", "defend"}:
            return name
    return normalized[0] if normalized else "card"


def _names(values: Any) -> List[str]:
    return [_name(item) for item in values] if isinstance(values, list) else []


def _format_counts(counter: Counter) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter))


def _format_list(values: List[str]) -> str:
    return ", ".join(values) if values else "none"


def _load_ai_markers(path: Path) -> List[int]:
    if not path.exists():
        return []
    markers = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        value = _to_int(line.strip(), default=None)
        if value is not None:
            markers.append(value)
    return markers


def _is_ai_marked(run_timestamp: int, markers: List[int], tolerance_seconds: int = 300) -> bool:
    return any(abs(marker - run_timestamp) <= tolerance_seconds for marker in markers)


def _name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("id") or "")
    return str(item or "")


def _slug(value: Any) -> str:
    text = _normalize_text(value)
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text or "unknown"


def _normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\+\d*$", "", text)
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _to_int(value: Any, default: Optional[int] = 0) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


if __name__ == "__main__":
    raise SystemExit(main())
