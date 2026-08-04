"""Canonical standard-library diagnostics for non-combat policy decisions."""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any


DIAGNOSTIC_SCHEMA_VERSION = "noncombat-policy-anti-collapse-diagnostics-v1"
TARGET_CATEGORIES = frozenset({"card_reward", "event", "route", "shop"})
CARD_REWARD_KINDS = ("bowl", "skip", "take")


class PolicyDiagnosticError(ValueError):
    """Raised when a diagnostic decision record is incomplete or invalid."""


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PolicyDiagnosticError(f"{label} must be a mapping")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PolicyDiagnosticError(f"{label} must be a sequence")
    return value


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyDiagnosticError(f"{label} must be a nonempty string")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise PolicyDiagnosticError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise PolicyDiagnosticError(f"{label} must be a finite number")
    return 0.0 if result == 0.0 else result


def _distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "max": None, "mean": None, "median": None, "min": None}
    return {
        "count": len(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
    }


def _validated_row(value: Any) -> dict[str, Any]:
    row = _mapping(value, "decision row")
    decision_id = _nonempty_string(row.get("decision_id"), "decision_id")
    category = _nonempty_string(row.get("category"), "category")
    if category not in TARGET_CATEGORIES:
        raise PolicyDiagnosticError(f"unsupported category: {category}")
    candidates = _sequence(row.get("candidates"), "candidates")
    if not candidates:
        raise PolicyDiagnosticError("candidates must be nonempty")

    candidate_rows = []
    candidate_ids = set()
    for index, candidate_value in enumerate(candidates):
        candidate = _mapping(candidate_value, f"candidate[{index}]")
        action_id = _nonempty_string(
            candidate.get("action_id"), f"candidate[{index}].action_id"
        )
        kind = _nonempty_string(candidate.get("kind"), f"candidate[{index}].kind")
        if action_id in candidate_ids:
            raise PolicyDiagnosticError(f"duplicate candidate action_id: {action_id}")
        candidate_ids.add(action_id)
        candidate_rows.append({"action_id": action_id, "kind": kind})

    selected_action_id = _nonempty_string(
        row.get("selected_action_id"), "selected_action_id"
    )
    if selected_action_id not in candidate_ids:
        raise PolicyDiagnosticError(
            "selected_action_id must identify exactly one candidate"
        )

    raw_scores = _mapping(row.get("candidate_scores"), "candidate_scores")
    if set(raw_scores) != candidate_ids:
        raise PolicyDiagnosticError(
            "candidate_scores keys must exactly match candidate action ids"
        )
    scores = {
        action_id: _finite_number(raw_scores[action_id], f"score {action_id}")
        for action_id in sorted(candidate_ids)
    }
    return {
        "candidate_scores": scores,
        "candidates": tuple(sorted(candidate_rows, key=lambda row: row["action_id"])),
        "category": category,
        "decision_id": decision_id,
        "selected_action_id": selected_action_id,
    }


def _category_summary(rows: Sequence[Mapping[str, Any]], category: str) -> dict[str, Any]:
    opportunity_counts: Counter[str] = Counter()
    occurrence_counts: Counter[str] = Counter()
    selected_counts: Counter[str] = Counter()
    top_margins = []
    selected_margins = []
    single_candidate_decisions = 0

    for row in rows:
        candidate_kinds = {
            candidate["action_id"]: candidate["kind"] for candidate in row["candidates"]
        }
        occurrence_counts.update(candidate_kinds.values())
        opportunity_counts.update(set(candidate_kinds.values()))
        selected_kind = candidate_kinds[row["selected_action_id"]]
        selected_counts[selected_kind] += 1

        scores = row["candidate_scores"]
        if len(scores) == 1:
            single_candidate_decisions += 1
            continue
        ordered_scores = sorted(scores.values(), reverse=True)
        top_margins.append(ordered_scores[0] - ordered_scores[1])
        alternatives = [
            score for action_id, score in scores.items() if action_id != row["selected_action_id"]
        ]
        selected_margins.append(scores[row["selected_action_id"]] - max(alternatives))

    decision_count = len(rows)
    result = {
        "candidate_kind_occurrences": dict(sorted(occurrence_counts.items())),
        "candidate_kind_opportunities": dict(sorted(opportunity_counts.items())),
        "decision_count": decision_count,
        "distinct_selected_kinds": sorted(selected_counts),
        "exact_single_kind_saturation": len(selected_counts) == 1,
        "selected_kinds": {
            kind: {"count": count, "rate": count / decision_count}
            for kind, count in sorted(selected_counts.items())
        },
        "selected_score_margin": _distribution(selected_margins),
        "single_candidate_decisions": single_candidate_decisions,
        "top_score_margin": _distribution(top_margins),
    }
    if category == "card_reward":
        result["card_reward"] = {
            "availability_decisions": {
                kind: opportunity_counts.get(kind, 0) for kind in CARD_REWARD_KINDS
            },
            "selections": {
                kind: selected_counts.get(kind, 0) for kind in CARD_REWARD_KINDS
            },
        }
    return result


def summarize_policy_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Return deterministic opportunity, selection, and raw-margin diagnostics."""
    values = _sequence(rows, "rows")
    if not values:
        raise PolicyDiagnosticError("rows must be nonempty")
    normalized = [_validated_row(row) for row in values]
    decision_ids = [row["decision_id"] for row in normalized]
    if len(set(decision_ids)) != len(decision_ids):
        raise PolicyDiagnosticError("decision_id values must be unique")

    by_category: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in normalized:
        by_category[row["category"]].append(row)
    categories = {
        category: _category_summary(
            sorted(category_rows, key=lambda row: row["decision_id"]), category
        )
        for category, category_rows in sorted(by_category.items())
    }
    return {
        "authority": {
            "experiment_execution": False,
            "formal_rl": False,
            "gameplay": False,
            "model_loading": False,
            "new_cohort": False,
            "policy_promotion": False,
            "qualification": False,
            "training": False,
        },
        "categories": categories,
        "decision_count": len(normalized),
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
    }
