"""Read-only audit of card-reward collapse in a consumed simulator experiment."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import statistics
import struct
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path, PurePosixPath
from typing import Any


AUDIT_SCHEMA_VERSION = "noncombat-state-conditioned-collapse-audit-v1"
MANIFEST_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-manifest-v2"
)
TRAINING_SCHEMA_VERSION = "noncombat-state-conditioned-training-rows-v1"
CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-checkpoint-v1"
)
DIAGNOSTICS_SCHEMA_VERSION = (
    "noncombat-state-conditioned-terminal-diagnostics-v1"
)
METRICS_SCHEMA_VERSION = "noncombat-state-conditioned-terminal-metrics-v1"
FINAL_MODEL_SCHEMA_VERSION = "noncombat-state-conditioned-final-model-v1"
EVALUATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-paired-evaluation-v1"
)
TERMINAL_VERDICT = "experiment_stopped_at_canary"
TERMINAL_BLOCKER = "card_reward_selected_kind_saturation"
TARGET_CATEGORIES = frozenset({"card_reward", "event", "route", "shop"})
CARD_REWARD_KINDS = frozenset({"bowl", "skip", "take"})
MODEL_PARAMETER_KEYS = frozenset(
    {"hidden.bias", "hidden.weight", "scorer.bias", "scorer.weight"}
)
ARCHITECTURE_ID = "state-conditioned-candidate-ranker-mlp-v1"
AUTHORITY_NAMES = (
    "causal_claim_authorized",
    "cohort_materialization_authorized",
    "communication_mod_authorized",
    "environment_construction_authorized",
    "execution_authorized",
    "formal_rl_authorized",
    "fresh_evidence_authorized",
    "gameplay_authorized",
    "live_execution_authorized",
    "model_fitting_authorized",
    "native_loading_authorized",
    "ope_authorized",
    "policy_loading_authorized",
    "production_checkpoint_mutation_authorized",
    "promotion_authorized",
    "qualification_authorized",
    "seed_access_authorized",
    "target_supported_outcome_authorized",
    "training_authorized",
)
CHECKPOINT_RE = re.compile(r"checkpoints/checkpoint_(\d{4})\.json\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
EXECUTION_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}\Z")

MANIFEST_KEYS = {
    "artifact_count",
    "artifacts",
    "authority",
    "logical_execution_id",
    "manifest_kind",
    "schema_version",
    "verdict",
}
CHUNK_KEYS = {
    "categories",
    "chunk_index",
    "diagnostic_rows",
    "entropy_coefficient",
    "episode_end",
    "episode_rows",
    "episode_start",
    "episodes",
    "gradient_norm_after_clip",
    "gradient_norm_before_clip",
    "loss",
    "mean_entropy",
    "mean_episode_return",
    "optimizer_update",
    "pass_index",
    "unsupported_episodes",
    "victories",
}
DECISION_KEYS = {
    "candidate_scores",
    "candidates",
    "category",
    "decision_id",
    "selected_action_id",
    "state_effect",
}
TRAIN_EPISODE_KEYS = {
    "action_sequence_sha256",
    "candidate_legality",
    "categories",
    "chunk_index",
    "decisions",
    "last_supported_floor",
    "outcome",
    "retained",
    "seed",
    "selected_action_ids",
    "terminal_floor",
    "total_reward",
    "unsupported_reason",
    "victory",
}
EVAL_EPISODE_KEYS = TRAIN_EPISODE_KEYS - {"chunk_index"}
CHECKPOINT_KEYS = {
    "checkpoint_index",
    "identity",
    "initial_model_sha256",
    "previous_checkpoint_sha256",
    "runtime",
    "schema_version",
    "training_chunk",
}
RUNTIME_KEYS = {
    "action_generator",
    "completed_episodes",
    "cumulative_wall_seconds",
    "entropy_coefficient",
    "gradient_norm_ceiling",
    "model",
    "next_chunk_index",
    "optimizer",
    "optimizer_updates",
    "python_random",
}
MODEL_TENSOR_KEYS = {
    "byte_order",
    "data_base64",
    "data_sha256",
    "dtype",
    "shape",
}


class CollapseAuditError(ValueError):
    """Raised when frozen audit evidence is incomplete or inconsistent."""


def _reject_constant(value: str) -> None:
    raise CollapseAuditError(f"JSON contains non-finite constant: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CollapseAuditError(f"JSON contains duplicate key: {key}")
        result[key] = value
    return result


def canonical_json_bytes(value: object) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        ) + "\n"
    except (TypeError, ValueError) as exc:
        raise CollapseAuditError(f"value is not canonical JSON: {exc}") from exc
    return text.encode("utf-8")


def _load_canonical_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise CollapseAuditError(f"{label} must be a regular non-symlink file")
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CollapseAuditError(f"{label} is invalid JSON: {exc}") from exc
    result = _mapping(value, label)
    if canonical_json_bytes(result) != raw:
        raise CollapseAuditError(f"{label} is not canonical JSON")
    return dict(result), raw


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CollapseAuditError(f"{label} must be a mapping")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CollapseAuditError(f"{label} must be a sequence")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise CollapseAuditError(
            f"{label} keys mismatch: missing={missing}, extra={extra}"
        )


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CollapseAuditError(f"{label} must be a nonempty string")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise CollapseAuditError(f"{label} must be boolean")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CollapseAuditError(f"{label} must be an integer >= {minimum}")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise CollapseAuditError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise CollapseAuditError(f"{label} must be a finite number")
    return 0.0 if result == 0.0 else result


def _sha256(value: Any, label: str) -> str:
    text = _nonempty_string(value, label)
    if not SHA256_RE.fullmatch(text):
        raise CollapseAuditError(f"{label} must be a lowercase SHA-256")
    return text


def _commit(value: Any, label: str) -> str:
    text = _nonempty_string(value, label)
    if not COMMIT_RE.fullmatch(text):
        raise CollapseAuditError(f"{label} must be a lowercase git commit")
    return text


def _execution_id(value: Any, label: str) -> str:
    text = _nonempty_string(value, label)
    if not EXECUTION_ID_RE.fullmatch(text):
        raise CollapseAuditError(f"{label} is invalid")
    return text


def _all_false_authority(value: Any, label: str) -> None:
    authority = _mapping(value, label)
    if set(authority) != set(AUTHORITY_NAMES) or any(
        authority[name] is not False for name in AUTHORITY_NAMES
    ):
        raise CollapseAuditError(f"{label} must be the exact all-false authority")


def _distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "max": None, "mean": None, "median": None, "min": None}
    finite = [_finite(value, "distribution value") for value in values]
    return {
        "count": len(finite),
        "max": max(finite),
        "mean": statistics.fmean(finite),
        "median": float(statistics.median(finite)),
        "min": min(finite),
    }


def _rates(counter: Counter[str], denominator: int) -> dict[str, dict[str, float | int]]:
    if denominator <= 0:
        return {}
    return {
        kind: {"count": counter[kind], "rate": counter[kind] / denominator}
        for kind in sorted(counter)
        if counter[kind]
    }


def _softmax(scores: Sequence[float]) -> list[float]:
    if not scores:
        raise CollapseAuditError("softmax scores must be nonempty")
    maximum = max(scores)
    weights = [math.exp(score - maximum) for score in scores]
    denominator = math.fsum(weights)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise CollapseAuditError("softmax denominator must be finite and positive")
    return [weight / denominator for weight in weights]


def _entropy(probabilities: Sequence[float]) -> float:
    return -math.fsum(
        probability * math.log(probability)
        for probability in probabilities
        if probability > 0.0
    )


def _validated_decision(value: Any, label: str) -> dict[str, Any]:
    row = _mapping(value, label)
    _exact_keys(row, DECISION_KEYS, label)
    decision_id = _nonempty_string(row["decision_id"], f"{label}.decision_id")
    category = _nonempty_string(row["category"], f"{label}.category")
    if category not in TARGET_CATEGORIES:
        raise CollapseAuditError(f"{label}.category is unsupported: {category}")

    candidate_values = _sequence(row["candidates"], f"{label}.candidates")
    if not candidate_values:
        raise CollapseAuditError(f"{label}.candidates must be nonempty")
    candidates: list[dict[str, str]] = []
    candidate_ids: set[str] = set()
    for index, candidate_value in enumerate(candidate_values):
        candidate = _mapping(candidate_value, f"{label}.candidates[{index}]")
        _exact_keys(
            candidate,
            {"action_id", "kind"},
            f"{label}.candidates[{index}]",
        )
        action_id = _nonempty_string(
            candidate["action_id"], f"{label}.candidates[{index}].action_id"
        )
        kind = _nonempty_string(
            candidate["kind"], f"{label}.candidates[{index}].kind"
        )
        if action_id in candidate_ids:
            raise CollapseAuditError(f"{label} has duplicate candidate: {action_id}")
        candidate_ids.add(action_id)
        candidates.append({"action_id": action_id, "kind": kind})

    if category == "card_reward":
        kinds = [candidate["kind"] for candidate in candidates]
        if not set(kinds).issubset(CARD_REWARD_KINDS):
            raise CollapseAuditError(f"{label} has invalid card-reward kind")
        alternative_count = kinds.count("skip") + kinds.count("bowl")
        if (
            kinds.count("take") < 1
            or kinds.count("skip") > 1
            or kinds.count("bowl") > 1
            or alternative_count != 1
        ):
            raise CollapseAuditError(
                f"{label} has incomplete card-reward alternative candidate contract"
            )

    selected_action_id = _nonempty_string(
        row["selected_action_id"], f"{label}.selected_action_id"
    )
    if selected_action_id not in candidate_ids:
        raise CollapseAuditError(f"{label}.selected_action_id is not a candidate")

    raw_scores = _mapping(row["candidate_scores"], f"{label}.candidate_scores")
    if set(raw_scores) != candidate_ids:
        raise CollapseAuditError(
            f"{label}.candidate_scores keys must exactly match candidates"
        )
    scores = {
        candidate["action_id"]: _finite(
            raw_scores[candidate["action_id"]],
            f"{label}.candidate_scores.{candidate['action_id']}",
        )
        for candidate in candidates
    }

    effect = _mapping(row["state_effect"], f"{label}.state_effect")
    _exact_keys(
        effect,
        {
            "category",
            "decision_id",
            "max_abs_relative_score_change",
            "relative_order_changed",
            "zero_state_scores",
        },
        f"{label}.state_effect",
    )
    if effect["category"] != category or effect["decision_id"] != decision_id:
        raise CollapseAuditError(f"{label}.state_effect identity mismatch")
    _finite(
        effect["max_abs_relative_score_change"],
        f"{label}.state_effect.max_abs_relative_score_change",
    )
    _bool(
        effect["relative_order_changed"],
        f"{label}.state_effect.relative_order_changed",
    )
    zero_scores = _sequence(
        effect["zero_state_scores"], f"{label}.state_effect.zero_state_scores"
    )
    if len(zero_scores) != len(candidates):
        raise CollapseAuditError(f"{label}.state_effect score count mismatch")
    for index, score in enumerate(zero_scores):
        _finite(score, f"{label}.state_effect.zero_state_scores[{index}]")

    return {
        "candidate_scores": scores,
        "candidates": candidates,
        "category": category,
        "decision_id": decision_id,
        "selected_action_id": selected_action_id,
    }


def _decision_metrics(row: Mapping[str, Any]) -> dict[str, Any]:
    candidates = row["candidates"]
    action_ids = [candidate["action_id"] for candidate in candidates]
    kinds = [candidate["kind"] for candidate in candidates]
    scores = [row["candidate_scores"][action_id] for action_id in action_ids]
    probabilities = _softmax(scores)
    selected_index = action_ids.index(row["selected_action_id"])
    greedy_index = max(range(len(scores)), key=scores.__getitem__)
    kind_probability: defaultdict[str, float] = defaultdict(float)
    for kind, probability in zip(kinds, probabilities):
        kind_probability[kind] += probability

    ordered_scores = sorted(scores, reverse=True)
    top_margin = None
    selected_margin = None
    if len(scores) > 1:
        top_margin = ordered_scores[0] - ordered_scores[1]
        selected_margin = scores[selected_index] - max(
            score for index, score in enumerate(scores) if index != selected_index
        )

    result = {
        "candidate_entropy": _entropy(probabilities),
        "candidate_kinds": kinds,
        "greedy_kind": kinds[greedy_index],
        "kind_entropy": _entropy(list(kind_probability.values())),
        "kind_probability": dict(sorted(kind_probability.items())),
        "selected_kind": kinds[selected_index],
        "selected_score_margin": selected_margin,
        "top_score_margin": top_margin,
    }
    if row["category"] == "card_reward":
        take_indices = [index for index, kind in enumerate(kinds) if kind == "take"]
        alternative_kind = "skip" if "skip" in kinds else "bowl"
        alternative_index = kinds.index(alternative_kind)
        best_take_score = max(scores[index] for index in take_indices)
        result["card_reward"] = {
            "alternative_kind": alternative_kind,
            "best_take_minus_alternative": best_take_score - scores[alternative_index],
            "take_candidate_count": len(take_indices),
            "take_candidate_share": len(take_indices) / len(candidates),
            "take_probability_excess_over_candidate_share": (
                kind_probability["take"] - len(take_indices) / len(candidates)
            ),
            "take_probability_mass": kind_probability["take"],
        }
    return result


def _validated_decisions(
    rows: Any,
    *,
    label: str,
    require_greedy: bool = False,
) -> list[dict[str, Any]]:
    values = _sequence(rows, label)
    normalized = [
        _validated_decision(value, f"{label}[{index}]")
        for index, value in enumerate(values)
    ]
    decision_ids = [row["decision_id"] for row in normalized]
    if len(set(decision_ids)) != len(decision_ids):
        raise CollapseAuditError(f"{label} contain duplicate decision_id values")
    if require_greedy:
        for index, row in enumerate(normalized):
            action_ids = [candidate["action_id"] for candidate in row["candidates"]]
            scores = [row["candidate_scores"][action_id] for action_id in action_ids]
            greedy_index = max(range(len(scores)), key=scores.__getitem__)
            if row["selected_action_id"] != action_ids[greedy_index]:
                raise CollapseAuditError(
                    f"{label}[{index}] selected action is not deterministic greedy"
                )
    return normalized


def analyze_decision_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize candidate and action-family dynamics from retained rows."""
    normalized = _validated_decisions(rows, label="decision_rows")

    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized:
        grouped[row["category"]].append(_decision_metrics(row))

    result: dict[str, Any] = {"decision_count": len(normalized)}
    for category in sorted(grouped):
        metrics = grouped[category]
        selected: Counter[str] = Counter(row["selected_kind"] for row in metrics)
        greedy: Counter[str] = Counter(row["greedy_kind"] for row in metrics)
        occurrences: Counter[str] = Counter()
        opportunities: Counter[str] = Counter()
        probability_values: defaultdict[str, list[float]] = defaultdict(list)
        for row in metrics:
            occurrences.update(row["candidate_kinds"])
            opportunities.update(set(row["candidate_kinds"]))
            for kind, probability in row["kind_probability"].items():
                probability_values[kind].append(probability)
        category_summary: dict[str, Any] = {
            "candidate_entropy": _distribution(
                [row["candidate_entropy"] for row in metrics]
            ),
            "candidate_kind_occurrences": dict(sorted(occurrences.items())),
            "candidate_kind_opportunities": dict(sorted(opportunities.items())),
            "candidate_minus_kind_entropy": _distribution(
                [row["candidate_entropy"] - row["kind_entropy"] for row in metrics]
            ),
            "decision_count": len(metrics),
            "greedy_kinds": _rates(greedy, len(metrics)),
            "kind_entropy": _distribution([row["kind_entropy"] for row in metrics]),
            "probability_mass_by_kind": {
                kind: _distribution(values)
                for kind, values in sorted(probability_values.items())
            },
            "selected_kinds": _rates(selected, len(metrics)),
            "selected_score_margin": _distribution(
                [
                    row["selected_score_margin"]
                    for row in metrics
                    if row["selected_score_margin"] is not None
                ]
            ),
            "top_score_margin": _distribution(
                [
                    row["top_score_margin"]
                    for row in metrics
                    if row["top_score_margin"] is not None
                ]
            ),
        }
        if category == "card_reward":
            eligible_metrics = [
                row
                for row in metrics
                if row["card_reward"]["alternative_kind"] == "skip"
            ]
            card_rows = [row["card_reward"] for row in eligible_metrics]
            selected_take_only = bool(eligible_metrics) and all(
                row["selected_kind"] == "take" for row in eligible_metrics
            )
            greedy_take_only = bool(eligible_metrics) and all(
                row["greedy_kind"] == "take"
                and row["card_reward"]["best_take_minus_alternative"] > 0.0
                for row in eligible_metrics
            )
            category_summary.update(
                {
                    "bowl_alternative_decisions": sum(
                        row["card_reward"]["alternative_kind"] == "bowl"
                        for row in metrics
                    ),
                    "eligible_take_skip_decisions": len(card_rows),
                    "greedy_take_only": greedy_take_only,
                    "selected_take_only": selected_take_only,
                    "take_candidate_count": _distribution(
                        [float(row["take_candidate_count"]) for row in card_rows]
                    ),
                    "take_candidate_share": _distribution(
                        [row["take_candidate_share"] for row in card_rows]
                    ),
                    "take_probability_excess_over_candidate_share": _distribution(
                        [
                            row["take_probability_excess_over_candidate_share"]
                            for row in card_rows
                        ]
                    ),
                    "take_probability_mass": _distribution(
                        [row["take_probability_mass"] for row in card_rows]
                    ),
                    "best_take_minus_skip_score": _distribution(
                        [row["best_take_minus_alternative"] for row in card_rows]
                    ),
                }
            )
        result[category] = category_summary
    return result


def locate_saturation_boundaries(
    chunk_summaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Locate exact first and persistent take-only boundaries."""
    chunks = _sequence(chunk_summaries, "chunk summaries")
    normalized: list[dict[str, Any]] = []
    for position, value in enumerate(chunks):
        row = _mapping(value, f"chunk_summaries[{position}]")
        chunk_index = _integer(
            row.get("chunk_index"), f"chunk_summaries[{position}].chunk_index"
        )
        if chunk_index != position:
            raise CollapseAuditError("chunk summaries must be contiguous and ordered")
        normalized.append(
            {
                "chunk_index": chunk_index,
                "greedy_take_only": _bool(
                    row.get("greedy_take_only"),
                    f"chunk_summaries[{position}].greedy_take_only",
                ),
                "selected_take_only": _bool(
                    row.get("selected_take_only"),
                    f"chunk_summaries[{position}].selected_take_only",
                ),
            }
        )

    result: dict[str, Any] = {}
    for field in ("selected_take_only", "greedy_take_only"):
        observed = [row["chunk_index"] for row in normalized if row[field]]
        persistent = None
        for position, row in enumerate(normalized):
            if all(later[field] for later in normalized[position:]):
                persistent = row["chunk_index"]
                break
        result[field] = {
            "earliest_persistent_chunk": persistent,
            "first_observed_chunk": observed[0] if observed else None,
            "observed_chunks": observed,
        }
    return result


def _validated_episode_rows(
    values: Any,
    *,
    label: str,
    chunk_index: int | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _sequence(values, label)
    normalized: list[dict[str, Any]] = []
    for position, value in enumerate(rows):
        row_label = f"{label}[{position}]"
        row = _mapping(value, row_label)
        if set(row) not in (TRAIN_EPISODE_KEYS, EVAL_EPISODE_KEYS):
            raise CollapseAuditError(f"{row_label} keys mismatch")
        if chunk_index is not None:
            if set(row) != TRAIN_EPISODE_KEYS or row["chunk_index"] != chunk_index:
                raise CollapseAuditError(f"{row_label}.chunk_index mismatch")
        _sha256(row["action_sequence_sha256"], f"{row_label}.action_sequence_sha256")
        if _bool(row["candidate_legality"], f"{row_label}.candidate_legality") is not True:
            raise CollapseAuditError(f"{row_label} candidate legality is false")
        categories = [
            _nonempty_string(category, f"{row_label}.categories")
            for category in _sequence(row["categories"], f"{row_label}.categories")
        ]
        if categories != sorted(set(categories)) or not set(categories).issubset(
            TARGET_CATEGORIES
        ):
            raise CollapseAuditError(f"{row_label}.categories are invalid")
        decisions = _integer(row["decisions"], f"{row_label}.decisions")
        selected_ids = [
            _nonempty_string(action_id, f"{row_label}.selected_action_ids")
            for action_id in _sequence(
                row["selected_action_ids"], f"{row_label}.selected_action_ids"
            )
        ]
        if decisions != len(selected_ids):
            raise CollapseAuditError(f"{row_label} decision count mismatch")
        expected_action_hash = hashlib.sha256(
            canonical_json_bytes(selected_ids)
        ).hexdigest()
        if row["action_sequence_sha256"] != expected_action_hash:
            raise CollapseAuditError(f"{row_label} action sequence hash mismatch")
        seed = _integer(row["seed"], f"{row_label}.seed")
        last_floor = _finite(
            row["last_supported_floor"], f"{row_label}.last_supported_floor"
        )
        terminal_floor = row["terminal_floor"]
        effective_floor = last_floor
        if terminal_floor is not None:
            effective_floor = _finite(terminal_floor, f"{row_label}.terminal_floor")
        unsupported = row["unsupported_reason"]
        if unsupported is not None:
            unsupported = _nonempty_string(unsupported, f"{row_label}.unsupported_reason")
        outcome = row["outcome"]
        if outcome is not None:
            outcome = _nonempty_string(outcome, f"{row_label}.outcome")
        if _bool(row["retained"], f"{row_label}.retained") is not True:
            raise CollapseAuditError(f"{row_label} is not retained")
        normalized.append(
            {
                "categories": categories,
                "decisions": decisions,
                "effective_floor": effective_floor,
                "outcome": outcome,
                "seed": seed,
                "selected_action_ids": selected_ids,
                "total_reward": _finite(row["total_reward"], f"{row_label}.total_reward"),
                "unsupported_reason": unsupported,
                "victory": _bool(row["victory"], f"{row_label}.victory"),
            }
        )
    outcomes = Counter(
        row["outcome"] for row in normalized if row["outcome"] is not None
    )
    unsupported = Counter(
        row["unsupported_reason"]
        for row in normalized
        if row["unsupported_reason"] is not None
    )
    summary = {
        "effective_floor": _distribution([row["effective_floor"] for row in normalized]),
        "episode_count": len(normalized),
        "outcomes": dict(sorted(outcomes.items())),
        "total_reward": _distribution([row["total_reward"] for row in normalized]),
        "unsupported_episodes": sum(unsupported.values()),
        "unsupported_reasons": dict(sorted(unsupported.items())),
        "victories": sum(row["victory"] for row in normalized),
    }
    return normalized, summary


def _align_diagnostics_to_episodes(
    diagnostic_values: Any,
    episodes: Sequence[Mapping[str, Any]],
    *,
    label: str,
    chunk_index: int | None,
    require_greedy: bool,
) -> list[dict[str, Any]]:
    diagnostics = _validated_decisions(
        diagnostic_values,
        label=label,
        require_greedy=require_greedy,
    )
    expected_count = sum(int(episode["decisions"]) for episode in episodes)
    if len(diagnostics) != expected_count:
        raise CollapseAuditError(f"{label} count does not match episode decisions")
    position = 0
    for episode_index, episode in enumerate(episodes):
        count = int(episode["decisions"])
        episode_rows = diagnostics[position : position + count]
        prefix = "" if chunk_index is None else f"chunk-{chunk_index}:"
        expected_ids = [
            f"{prefix}seed-{episode['seed']}:decision-{decision_index}"
            for decision_index in range(count)
        ]
        if [row["decision_id"] for row in episode_rows] != expected_ids:
            raise CollapseAuditError(
                f"{label} episode {episode_index} decision coordinates mismatch"
            )
        if [row["selected_action_id"] for row in episode_rows] != episode[
            "selected_action_ids"
        ]:
            raise CollapseAuditError(
                f"{label} episode {episode_index} selected actions mismatch"
            )
        observed_categories = sorted({row["category"] for row in episode_rows})
        if observed_categories != episode["categories"]:
            raise CollapseAuditError(
                f"{label} episode {episode_index} categories mismatch"
            )
        position += count
    return diagnostics


def _validated_chunk(value: Any, index: int, previous_end: int) -> tuple[dict[str, Any], dict[str, Any]]:
    label = f"training.chunks[{index}]"
    chunk = _mapping(value, label)
    _exact_keys(chunk, CHUNK_KEYS, label)
    if _integer(chunk["chunk_index"], f"{label}.chunk_index") != index:
        raise CollapseAuditError(f"{label}.chunk_index mismatch")
    episode_start = _integer(chunk["episode_start"], f"{label}.episode_start")
    episodes = _integer(chunk["episodes"], f"{label}.episodes", minimum=1)
    episode_end = _integer(chunk["episode_end"], f"{label}.episode_end")
    if episode_start != previous_end or episode_end != episode_start + episodes:
        raise CollapseAuditError(f"{label} episode interval is not contiguous")
    if _integer(chunk["optimizer_update"], f"{label}.optimizer_update", minimum=1) != index + 1:
        raise CollapseAuditError(f"{label}.optimizer_update mismatch")
    pass_index = _integer(chunk["pass_index"], f"{label}.pass_index")
    categories = [
        _nonempty_string(category, f"{label}.categories")
        for category in _sequence(chunk["categories"], f"{label}.categories")
    ]
    if categories != sorted(set(categories)) or not set(categories).issubset(
        TARGET_CATEGORIES
    ):
        raise CollapseAuditError(f"{label}.categories are invalid")
    for key in (
        "entropy_coefficient",
        "gradient_norm_after_clip",
        "gradient_norm_before_clip",
        "loss",
        "mean_entropy",
        "mean_episode_return",
    ):
        _finite(chunk[key], f"{label}.{key}")

    decision_rows = _sequence(chunk["diagnostic_rows"], f"{label}.diagnostic_rows")
    normalized_episodes, outcome_summary = _validated_episode_rows(
        chunk["episode_rows"], label=f"{label}.episode_rows", chunk_index=index
    )
    _align_diagnostics_to_episodes(
        decision_rows,
        normalized_episodes,
        label=f"{label}.diagnostic_rows",
        chunk_index=index,
        require_greedy=False,
    )
    decision_summary = analyze_decision_rows(decision_rows)
    observed_categories = sorted(
        category for category in TARGET_CATEGORIES if category in decision_summary
    )
    if categories != observed_categories:
        raise CollapseAuditError(f"{label}.categories do not match diagnostic rows")
    if outcome_summary["episode_count"] != episodes:
        raise CollapseAuditError(f"{label} episode row count mismatch")
    unsupported = _integer(
        chunk["unsupported_episodes"], f"{label}.unsupported_episodes"
    )
    victories = _integer(chunk["victories"], f"{label}.victories")
    if unsupported != outcome_summary["unsupported_episodes"] or victories != outcome_summary["victories"]:
        raise CollapseAuditError(f"{label} outcome summary mismatch")

    summary = {
        "card_reward": decision_summary.get("card_reward"),
        "chunk_index": index,
        "controls": {
            category: decision_summary[category]
            for category in ("event", "route", "shop")
            if category in decision_summary
        },
        "decision_count": decision_summary["decision_count"],
        "outcomes": outcome_summary,
        "registered_training": {
            "entropy_coefficient": float(chunk["entropy_coefficient"]),
            "gradient_norm_after_clip": float(chunk["gradient_norm_after_clip"]),
            "gradient_norm_before_clip": float(chunk["gradient_norm_before_clip"]),
            "loss": float(chunk["loss"]),
            "mean_entropy": float(chunk["mean_entropy"]),
            "mean_episode_return": float(chunk["mean_episode_return"]),
        },
        "coordinates": {
            "episode_end": episode_end,
            "episode_start": episode_start,
            "optimizer_update": index + 1,
            "pass_index": pass_index,
        },
    }
    return dict(chunk), summary


def _validate_architecture(value: Any) -> dict[str, tuple[int, ...]]:
    architecture = _mapping(value, "final model.architecture")
    _exact_keys(
        architecture,
        {
            "architecture_id",
            "candidate_input_dim",
            "device",
            "dtype",
            "hidden_dim",
            "state_conditioned",
            "state_input_dim",
        },
        "final model.architecture",
    )
    if (
        architecture["architecture_id"] != ARCHITECTURE_ID
        or architecture["device"] != "cpu"
        or architecture["dtype"] != "float32"
        or architecture["state_conditioned"] is not True
    ):
        raise CollapseAuditError("final model architecture identity mismatch")
    candidate_dim = _integer(
        architecture["candidate_input_dim"],
        "final model.architecture.candidate_input_dim",
        minimum=1,
    )
    state_dim = _integer(
        architecture["state_input_dim"],
        "final model.architecture.state_input_dim",
        minimum=1,
    )
    hidden_dim = _integer(
        architecture["hidden_dim"],
        "final model.architecture.hidden_dim",
        minimum=1,
    )
    if candidate_dim != state_dim:
        raise CollapseAuditError("final model state/candidate dimensions differ")
    return {
        "hidden.bias": (hidden_dim,),
        "hidden.weight": (hidden_dim, state_dim + candidate_dim),
        "scorer.bias": (1,),
        "scorer.weight": (1, hidden_dim),
    }


def _decode_model(
    value: Any,
    label: str,
    *,
    expected_shapes: Mapping[str, tuple[int, ...]],
) -> tuple[dict[str, tuple[float, ...]], dict[str, Any]]:
    model = _mapping(value, label)
    if set(model) != MODEL_PARAMETER_KEYS:
        raise CollapseAuditError(f"{label} parameter keys mismatch")
    decoded: dict[str, tuple[float, ...]] = {}
    tensor_summaries: dict[str, Any] = {}
    for name in sorted(model):
        tensor_label = f"{label}.{name}"
        tensor = _mapping(model[name], tensor_label)
        _exact_keys(tensor, MODEL_TENSOR_KEYS, tensor_label)
        if tensor["byte_order"] != "little" or tensor["dtype"] != "float32":
            raise CollapseAuditError(f"{tensor_label} encoding mismatch")
        shape = [
            _integer(dimension, f"{tensor_label}.shape", minimum=1)
            for dimension in _sequence(tensor["shape"], f"{tensor_label}.shape")
        ]
        if not shape:
            raise CollapseAuditError(f"{tensor_label}.shape must be nonempty")
        if tuple(shape) != expected_shapes[name]:
            raise CollapseAuditError(f"{tensor_label}.shape differs from architecture")
        encoded = _nonempty_string(tensor["data_base64"], f"{tensor_label}.data_base64")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise CollapseAuditError(f"{tensor_label}.data_base64 is invalid") from exc
        if base64.b64encode(data).decode("ascii") != encoded:
            raise CollapseAuditError(f"{tensor_label}.data_base64 is not canonical")
        if hashlib.sha256(data).hexdigest() != _sha256(
            tensor["data_sha256"], f"{tensor_label}.data_sha256"
        ):
            raise CollapseAuditError(f"{tensor_label} data hash mismatch")
        count = math.prod(shape)
        if len(data) != count * 4:
            raise CollapseAuditError(f"{tensor_label} byte count mismatch")
        values = struct.unpack(f"<{count}f", data)
        if not all(math.isfinite(item) for item in values):
            raise CollapseAuditError(f"{tensor_label} contains nonfinite values")
        decoded[name] = values
        tensor_summaries[name] = {
            "element_count": count,
            "l2_norm": math.sqrt(math.fsum(item * item for item in values)),
            "shape": shape,
        }
    all_values = [item for name in sorted(decoded) for item in decoded[name]]
    return decoded, {
        "model_l2_norm": math.sqrt(math.fsum(item * item for item in all_values)),
        "parameter_count": len(all_values),
        "tensors": tensor_summaries,
    }


def _model_delta(current: Mapping[str, tuple[float, ...]], previous: Mapping[str, tuple[float, ...]]) -> float:
    if set(current) != set(previous):
        raise CollapseAuditError("checkpoint model parameter keys drifted")
    squared: list[float] = []
    for name in sorted(current):
        if len(current[name]) != len(previous[name]):
            raise CollapseAuditError("checkpoint model tensor shape drifted")
        squared.extend(
            (current_value - previous_value) ** 2
            for current_value, previous_value in zip(current[name], previous[name])
        )
    return math.sqrt(math.fsum(squared))


class _BundleReader:
    def __init__(self, source_root: Path | str) -> None:
        source = Path(source_root)
        if source.is_symlink() or not source.is_dir():
            raise CollapseAuditError("source bundle must be a regular directory")
        self.source = source.resolve()
        self.source_identities: list[dict[str, Any]] = []
        manifest, manifest_raw = _load_canonical_json(
            self.source / "artifact_manifest.json", "artifact manifest"
        )
        _exact_keys(manifest, MANIFEST_KEYS, "artifact manifest")
        if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
            raise CollapseAuditError("artifact manifest schema mismatch")
        if manifest["manifest_kind"] != "full_terminal":
            raise CollapseAuditError("artifact manifest is not full terminal")
        if manifest["verdict"] != TERMINAL_VERDICT:
            raise CollapseAuditError("artifact manifest verdict mismatch")
        _all_false_authority(manifest["authority"], "artifact manifest.authority")
        manifest["logical_execution_id"] = _execution_id(
            manifest["logical_execution_id"], "artifact manifest.logical_execution_id"
        )
        artifacts = _sequence(manifest["artifacts"], "artifact manifest.artifacts")
        entries: dict[str, dict[str, Any]] = {}
        ordered_paths: list[str] = []
        for index, value in enumerate(artifacts):
            label = f"artifact manifest.artifacts[{index}]"
            entry = _mapping(value, label)
            _exact_keys(entry, {"path", "sha256", "size_bytes"}, label)
            path = _nonempty_string(entry["path"], f"{label}.path")
            pure = PurePosixPath(path)
            if (
                pure.is_absolute()
                or pure.as_posix() != path
                or "\\" in path
                or any(part in ("", ".", "..") for part in pure.parts)
            ):
                raise CollapseAuditError(f"{label}.path is not canonical relative")
            if path in entries:
                raise CollapseAuditError(f"duplicate manifest artifact: {path}")
            entries[path] = {
                "path": path,
                "sha256": _sha256(entry["sha256"], f"{label}.sha256"),
                "size_bytes": _integer(entry["size_bytes"], f"{label}.size_bytes"),
            }
            ordered_paths.append(path)
        if ordered_paths != sorted(ordered_paths):
            raise CollapseAuditError("artifact manifest paths are not sorted")
        if _integer(manifest["artifact_count"], "artifact manifest.artifact_count") != len(entries):
            raise CollapseAuditError("artifact manifest count mismatch")
        self.manifest = manifest
        self.entries = entries
        self.source_identities.append(
            {
                "path": "artifact_manifest.json",
                "sha256": hashlib.sha256(manifest_raw).hexdigest(),
                "size_bytes": len(manifest_raw),
            }
        )

    def load(self, relative: str, label: str) -> tuple[dict[str, Any], bytes]:
        if relative not in self.entries:
            raise CollapseAuditError(f"manifest lacks required artifact: {relative}")
        pure = PurePosixPath(relative)
        path = self.source.joinpath(*pure.parts)
        value, raw = _load_canonical_json(path, label)
        entry = self.entries[relative]
        if len(raw) != entry["size_bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise CollapseAuditError(f"{label} does not match manifest identity")
        self.source_identities.append(dict(entry))
        return value, raw

    def checkpoint_paths(self) -> list[str]:
        indexed: list[tuple[int, str]] = []
        for path in self.entries:
            match = CHECKPOINT_RE.fullmatch(path)
            if match:
                indexed.append((int(match.group(1)), path))
        indexed.sort()
        if not indexed or [index for index, _ in indexed] != list(
            range(1, len(indexed) + 1)
        ):
            raise CollapseAuditError("checkpoint manifest entries are not contiguous")
        directory = self.source / "checkpoints"
        if directory.is_symlink() or not directory.is_dir():
            raise CollapseAuditError("checkpoint directory is invalid")
        children = list(directory.iterdir())
        if any(path.is_symlink() or not path.is_file() for path in children):
            raise CollapseAuditError("physical checkpoint inventory contains a non-file")
        physical = sorted(path.name for path in children)
        expected = [PurePosixPath(path).name for _, path in indexed]
        if physical != expected:
            raise CollapseAuditError("physical checkpoint inventory differs from manifest")
        return [path for _, path in indexed]


def _validate_terminal_metadata(
    diagnostics: Mapping[str, Any],
    metrics: Mapping[str, Any],
    *,
    episode_count: int,
    chunk_count: int,
    unsupported_episodes: int,
    victories: int,
) -> None:
    _exact_keys(
        diagnostics,
        {"authority", "evaluation", "schema_version", "training"},
        "terminal diagnostics",
    )
    if diagnostics["schema_version"] != DIAGNOSTICS_SCHEMA_VERSION:
        raise CollapseAuditError("terminal diagnostics schema mismatch")
    _all_false_authority(
        diagnostics["authority"], "terminal diagnostics.authority"
    )
    training_diagnostics = _mapping(
        diagnostics["training"], "terminal diagnostics.training"
    )
    _all_false_authority(
        training_diagnostics.get("authority"),
        "terminal diagnostics.training.authority",
    )
    evaluation = _mapping(diagnostics["evaluation"], "terminal diagnostics.evaluation")
    _exact_keys(
        evaluation,
        {
            "canary_initial",
            "canary_trained",
            "holdout_accessed",
            "holdout_initial",
            "holdout_trained",
        },
        "terminal diagnostics.evaluation",
    )
    if (
        evaluation["holdout_accessed"] is not False
        or evaluation["holdout_initial"] is not None
        or evaluation["holdout_trained"] is not None
    ):
        raise CollapseAuditError("terminal diagnostics indicate holdout access")
    for name in ("canary_initial", "canary_trained"):
        summary = _mapping(
            evaluation[name], f"terminal diagnostics.evaluation.{name}"
        )
        _all_false_authority(
            summary.get("authority"),
            f"terminal diagnostics.evaluation.{name}.authority",
        )

    expected_metric_keys = {
        "authority",
        "blocked_reason",
        "completed_training_episodes",
        "cumulative_wall_seconds",
        "formal_readiness_unchanged",
        "isolation_unchanged",
        "optimizer_updates",
        "policy_quality_baseline_established",
        "schema_version",
        "target_supported_outcomes_established",
        "training_observed_only_floor_shaping",
        "training_unsupported_episodes",
        "training_victories",
        "verdict",
    }
    _exact_keys(metrics, expected_metric_keys, "terminal metrics")
    _all_false_authority(metrics["authority"], "terminal metrics.authority")
    if metrics["schema_version"] != METRICS_SCHEMA_VERSION or metrics["verdict"] != TERMINAL_VERDICT:
        raise CollapseAuditError("terminal metrics identity mismatch")
    expected_values = {
        "completed_training_episodes": episode_count,
        "optimizer_updates": chunk_count,
        "training_unsupported_episodes": unsupported_episodes,
        "training_victories": victories,
    }
    for key, expected in expected_values.items():
        if _integer(metrics[key], f"terminal metrics.{key}") != expected:
            raise CollapseAuditError(f"terminal metrics.{key} mismatch")
    if (
        metrics["blocked_reason"] is not None
        or metrics["formal_readiness_unchanged"] is not True
        or metrics["isolation_unchanged"] is not True
        or metrics["policy_quality_baseline_established"] is not False
        or metrics["target_supported_outcomes_established"] is not False
        or metrics["training_observed_only_floor_shaping"] is not True
    ):
        raise CollapseAuditError("terminal metrics authority or outcome boundary drifted")
    _finite(metrics["cumulative_wall_seconds"], "terminal metrics.cumulative_wall_seconds")


def _validate_evaluation(value: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _exact_keys(value, {"canary", "canary_gate", "holdout", "verdict"}, "evaluation")
    if value["verdict"] != TERMINAL_VERDICT:
        raise CollapseAuditError("evaluation verdict mismatch")
    holdout = _mapping(value["holdout"], "evaluation.holdout")
    _exact_keys(holdout, {"accessed", "episode_count"}, "evaluation.holdout")
    holdout_episode_count = _integer(
        holdout["episode_count"], "evaluation.holdout.episode_count"
    )
    if holdout["accessed"] is not False or holdout_episode_count != 0:
        raise CollapseAuditError("evaluation indicates holdout access")
    gate = _mapping(value["canary_gate"], "evaluation.canary_gate")
    _exact_keys(
        gate,
        {
            "behavior_gate",
            "blockers",
            "floor_difference_ci",
            "initial_victories",
            "passed",
            "trained_victories",
            "unsupported_rate",
            "verdict",
        },
        "evaluation.canary_gate",
    )
    blockers = list(_sequence(gate.get("blockers"), "evaluation.canary_gate.blockers"))
    if blockers != [TERMINAL_BLOCKER] or gate.get("passed") is not False or gate.get("verdict") != TERMINAL_VERDICT:
        raise CollapseAuditError("evaluation canary blocker mismatch")
    behavior_gate = _mapping(
        gate["behavior_gate"], "evaluation.canary_gate.behavior_gate"
    )
    _exact_keys(
        behavior_gate,
        {"blockers", "passed", "schema_version"},
        "evaluation.canary_gate.behavior_gate",
    )
    if (
        behavior_gate["blockers"] != [TERMINAL_BLOCKER]
        or behavior_gate["passed"] is not False
    ):
        raise CollapseAuditError("evaluation behavior gate mismatch")

    canary = _mapping(value["canary"], "evaluation.canary")
    _exact_keys(
        canary,
        {
            "cohort",
            "floor_difference_ci",
            "initial",
            "paired_rows",
            "schema_version",
            "seeds",
            "trained",
            "unsupported_rate",
            "unsupported_rate_denominator",
        },
        "evaluation.canary",
    )
    if canary["cohort"] != "canary" or canary["schema_version"] != EVALUATION_SCHEMA_VERSION:
        raise CollapseAuditError("canary evaluation identity mismatch")
    seeds = _sequence(canary["seeds"], "evaluation.canary.seeds")
    for index, seed in enumerate(seeds):
        _integer(seed, f"evaluation.canary.seeds[{index}]")
    if len(set(seeds)) != len(seeds):
        raise CollapseAuditError("evaluation.canary.seeds contain duplicates")

    policy_keys = {
        "categories",
        "diagnostic_rows",
        "diagnostics",
        "episode_rows",
        "replay_diagnostic_rows",
        "replay_episode_rows",
        "replay_exact",
        "unsupported_episodes",
        "victories",
    }
    summaries: dict[str, Any] = {}
    for policy_name in ("initial", "trained"):
        label = f"evaluation.canary.{policy_name}"
        policy = _mapping(canary[policy_name], label)
        _exact_keys(policy, policy_keys, label)
        if policy["replay_exact"] is not True:
            raise CollapseAuditError(f"{label} replay is not exact")
        if policy["diagnostic_rows"] != policy["replay_diagnostic_rows"]:
            raise CollapseAuditError(f"{label} replay diagnostic rows differ")
        if policy["episode_rows"] != policy["replay_episode_rows"]:
            raise CollapseAuditError(f"{label} replay episode rows differ")
        normalized_episodes, outcome_summary = _validated_episode_rows(
            policy["episode_rows"], label=f"{label}.episode_rows", chunk_index=None
        )
        _align_diagnostics_to_episodes(
            policy["diagnostic_rows"],
            normalized_episodes,
            label=f"{label}.diagnostic_rows",
            chunk_index=None,
            require_greedy=True,
        )
        decision_summary = analyze_decision_rows(policy["diagnostic_rows"])
        declared_categories = [
            _nonempty_string(category, f"{label}.categories")
            for category in _sequence(policy["categories"], f"{label}.categories")
        ]
        observed_categories = sorted(
            category for category in TARGET_CATEGORIES if category in decision_summary
        )
        if (
            declared_categories != sorted(set(declared_categories))
            or declared_categories != observed_categories
        ):
            raise CollapseAuditError(f"{label}.categories do not match decision rows")
        policy_diagnostics = _mapping(policy["diagnostics"], f"{label}.diagnostics")
        _all_false_authority(
            policy_diagnostics.get("authority"), f"{label}.diagnostics.authority"
        )
        if outcome_summary["episode_count"] != len(seeds):
            raise CollapseAuditError(f"{label} episode count differs from canary seeds")
        if (
            _integer(policy["unsupported_episodes"], f"{label}.unsupported_episodes")
            != outcome_summary["unsupported_episodes"]
            or _integer(policy["victories"], f"{label}.victories")
            != outcome_summary["victories"]
        ):
            raise CollapseAuditError(f"{label} outcome summary mismatch")
        summaries[policy_name] = {
            "card_reward": decision_summary.get("card_reward"),
            "controls": {
                category: decision_summary[category]
                for category in ("event", "route", "shop")
                if category in decision_summary
            },
            "decision_count": decision_summary["decision_count"],
            "outcomes": outcome_summary,
        }
    trained_card = summaries["trained"].get("card_reward")
    computed_blockers = []
    if (
        trained_card is not None
        and set(trained_card["selected_kinds"]) == {"take"}
        and trained_card["candidate_kind_opportunities"].get("skip", 0) > 0
    ):
        computed_blockers.append(TERMINAL_BLOCKER)
    if blockers != computed_blockers or behavior_gate["blockers"] != computed_blockers:
        raise CollapseAuditError("evaluation canary blocker does not recompute")
    return summaries["initial"], summaries["trained"], dict(gate)


def _authority() -> dict[str, bool]:
    return {
        "causal_claim": False,
        "communication_mod": False,
        "formal_rl": False,
        "gameplay": False,
        "holdout_access": False,
        "model_fitting": False,
        "model_loading": False,
        "native_loading": False,
        "policy_promotion": False,
        "qualification": False,
        "seed_replay": False,
        "successor_experiment": False,
        "threshold_change": False,
        "training": False,
    }


def _normalized_command(command: Sequence[str]) -> list[str]:
    values = _sequence(command, "command")
    if not values:
        raise CollapseAuditError("command must be nonempty")
    return [_nonempty_string(value, f"command[{index}]") for index, value in enumerate(values)]


def audit_bundle(
    source_root: Path | str,
    *,
    command: Sequence[str],
) -> dict[str, Any]:
    """Audit a terminal bundle without executing or mutating experiment code."""
    reader = _BundleReader(source_root)
    training, _ = reader.load("training_rows.json", "training rows")
    _exact_keys(training, {"chunks", "episode_count", "schema_version"}, "training rows")
    if training["schema_version"] != TRAINING_SCHEMA_VERSION:
        raise CollapseAuditError("training rows schema mismatch")
    chunk_values = _sequence(training["chunks"], "training rows.chunks")
    if not chunk_values:
        raise CollapseAuditError("training rows contain no chunks")

    raw_chunks: list[dict[str, Any]] = []
    chunk_summaries: list[dict[str, Any]] = []
    all_decision_rows: list[Mapping[str, Any]] = []
    all_episode_rows: list[Mapping[str, Any]] = []
    previous_end = 0
    for index, value in enumerate(chunk_values):
        raw_chunk, summary = _validated_chunk(value, index, previous_end)
        raw_chunks.append(raw_chunk)
        chunk_summaries.append(summary)
        all_decision_rows.extend(raw_chunk["diagnostic_rows"])
        all_episode_rows.extend(raw_chunk["episode_rows"])
        previous_end = raw_chunk["episode_end"]
    episode_count = _integer(training["episode_count"], "training rows.episode_count")
    if episode_count != previous_end or episode_count != len(all_episode_rows):
        raise CollapseAuditError("training episode count mismatch")
    aggregate_decisions = analyze_decision_rows(all_decision_rows)
    _, aggregate_outcomes = _validated_episode_rows(
        all_episode_rows, label="training aggregate episode rows", chunk_index=None
    )

    checkpoint_paths = reader.checkpoint_paths()
    if len(checkpoint_paths) != len(raw_chunks):
        raise CollapseAuditError("checkpoint and chunk counts differ")

    final_model, _ = reader.load("final_model.json", "final model")
    _exact_keys(
        final_model,
        {
            "architecture",
            "authority",
            "initial_model_sha256",
            "model",
            "model_loading_authorized",
            "schema_version",
        },
        "final model",
    )
    if (
        final_model["schema_version"] != FINAL_MODEL_SCHEMA_VERSION
        or final_model["model_loading_authorized"] is not False
    ):
        raise CollapseAuditError("final model identity mismatch")
    _all_false_authority(final_model["authority"], "final model.authority")
    expected_shapes = _validate_architecture(final_model["architecture"])
    initial_model_sha256 = _sha256(
        final_model["initial_model_sha256"], "final model.initial_model_sha256"
    )
    _decode_model(
        final_model["model"],
        "final model.model",
        expected_shapes=expected_shapes,
    )

    previous_raw_hash: str | None = None
    previous_model: dict[str, tuple[float, ...]] | None = None
    checkpoint_identity: Mapping[str, Any] | None = None
    last_model_json: Mapping[str, Any] | None = None
    for index, (relative, raw_chunk, summary) in enumerate(
        zip(checkpoint_paths, raw_chunks, chunk_summaries), start=1
    ):
        checkpoint, raw = reader.load(relative, f"checkpoint {index}")
        _exact_keys(checkpoint, CHECKPOINT_KEYS, f"checkpoint {index}")
        if checkpoint["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
            raise CollapseAuditError(f"checkpoint {index} schema mismatch")
        if _integer(
            checkpoint["checkpoint_index"], f"checkpoint {index}.checkpoint_index", minimum=1
        ) != index:
            raise CollapseAuditError(f"checkpoint {index} index mismatch")
        if canonical_json_bytes(checkpoint["training_chunk"]) != canonical_json_bytes(
            raw_chunk
        ):
            raise CollapseAuditError(f"checkpoint {index} training chunk mismatch")
        previous_value = checkpoint["previous_checkpoint_sha256"]
        if index == 1:
            if previous_value is not None:
                raise CollapseAuditError("checkpoint 1 chain mismatch")
        elif _sha256(
            previous_value, f"checkpoint {index}.previous_checkpoint_sha256"
        ) != previous_raw_hash:
            raise CollapseAuditError(f"checkpoint {index} chain mismatch")
        current_initial_hash = _sha256(
            checkpoint["initial_model_sha256"],
            f"checkpoint {index}.initial_model_sha256",
        )
        if current_initial_hash != initial_model_sha256:
            raise CollapseAuditError("initial model hash drifted across checkpoints")
        identity = _mapping(checkpoint["identity"], f"checkpoint {index}.identity")
        _exact_keys(
            identity,
            {"implementation_commit", "logical_execution_id", "registration_sha256"},
            f"checkpoint {index}.identity",
        )
        normalized_identity = {
            "implementation_commit": _commit(
                identity["implementation_commit"],
                f"checkpoint {index}.identity.implementation_commit",
            ),
            "logical_execution_id": _execution_id(
                identity["logical_execution_id"],
                f"checkpoint {index}.identity.logical_execution_id",
            ),
            "registration_sha256": _sha256(
                identity["registration_sha256"],
                f"checkpoint {index}.identity.registration_sha256",
            ),
        }
        registration_entry = reader.entries.get("registration.json")
        if registration_entry is None:
            raise CollapseAuditError("manifest lacks registration identity")
        if (
            normalized_identity["logical_execution_id"]
            != reader.manifest["logical_execution_id"]
            or normalized_identity["registration_sha256"]
            != registration_entry["sha256"]
        ):
            raise CollapseAuditError(f"checkpoint {index} identity mismatch")
        if checkpoint_identity is None:
            checkpoint_identity = normalized_identity
        elif normalized_identity != checkpoint_identity:
            raise CollapseAuditError("checkpoint identity drifted")
        runtime = _mapping(checkpoint["runtime"], f"checkpoint {index}.runtime")
        _exact_keys(runtime, RUNTIME_KEYS, f"checkpoint {index}.runtime")
        completed_episodes = _integer(
            runtime["completed_episodes"],
            f"checkpoint {index}.runtime.completed_episodes",
        )
        next_chunk_index = _integer(
            runtime["next_chunk_index"],
            f"checkpoint {index}.runtime.next_chunk_index",
            minimum=1,
        )
        optimizer_updates = _integer(
            runtime["optimizer_updates"],
            f"checkpoint {index}.runtime.optimizer_updates",
            minimum=1,
        )
        runtime_entropy = _finite(
            runtime["entropy_coefficient"],
            f"checkpoint {index}.runtime.entropy_coefficient",
        )
        if (
            completed_episodes != raw_chunk["episode_end"]
            or next_chunk_index != index
            or optimizer_updates != index
            or runtime_entropy != float(raw_chunk["entropy_coefficient"])
        ):
            raise CollapseAuditError(f"checkpoint {index} runtime coordinate mismatch")
        _finite(
            runtime["cumulative_wall_seconds"],
            f"checkpoint {index}.runtime.cumulative_wall_seconds",
        )
        gradient_ceiling = _finite(
            runtime["gradient_norm_ceiling"],
            f"checkpoint {index}.runtime.gradient_norm_ceiling",
        )
        if gradient_ceiling <= 0.0:
            raise CollapseAuditError(
                f"checkpoint {index}.runtime.gradient_norm_ceiling must be positive"
            )
        model, model_summary = _decode_model(
            runtime["model"],
            f"checkpoint {index}.runtime.model",
            expected_shapes=expected_shapes,
        )
        delta = None if previous_model is None else _model_delta(model, previous_model)
        summary["checkpoint"] = {
            "checkpoint_index": index,
            "initial_tensor_gap": index == 1,
            "model_delta_l2_from_previous_checkpoint": delta,
            "model_l2_norm": model_summary["model_l2_norm"],
            "model_sha256": hashlib.sha256(
                canonical_json_bytes(runtime["model"])
            ).hexdigest(),
            "parameter_count": model_summary["parameter_count"],
            "post_update_optimizer_update": index,
            "pre_update_chunk_index": index - 1,
        }
        previous_model = model
        last_model_json = runtime["model"]
        previous_raw_hash = hashlib.sha256(raw).hexdigest()

    if canonical_json_bytes(final_model["model"]) != canonical_json_bytes(
        last_model_json
    ):
        raise CollapseAuditError("final model does not match the terminal checkpoint")

    diagnostics, _ = reader.load("diagnostics.json", "terminal diagnostics")
    metrics, _ = reader.load("metrics.json", "terminal metrics")
    _validate_terminal_metadata(
        diagnostics,
        metrics,
        episode_count=episode_count,
        chunk_count=len(raw_chunks),
        unsupported_episodes=aggregate_outcomes["unsupported_episodes"],
        victories=aggregate_outcomes["victories"],
    )
    evaluation, _ = reader.load("evaluation.json", "paired evaluation")
    initial_canary, trained_canary, canary_gate = _validate_evaluation(evaluation)

    card_chunks: list[dict[str, Any]] = []
    for summary in chunk_summaries:
        card = summary["card_reward"]
        if card is None:
            raise CollapseAuditError(
                f"training chunk {summary['chunk_index']} lacks card-reward decisions"
            )
        card_chunks.append(
            {
                "chunk_index": summary["chunk_index"],
                "greedy_take_only": card["greedy_take_only"],
                "selected_take_only": card["selected_take_only"],
            }
        )
    boundaries = locate_saturation_boundaries(card_chunks)
    aggregate_card = aggregate_decisions.get("card_reward")
    if aggregate_card is None or initial_canary["card_reward"] is None or trained_canary["card_reward"] is None:
        raise CollapseAuditError("card-reward evidence is missing")

    interpretations = []
    if aggregate_card["take_candidate_share"]["mean"] > 0.5:
        interpretations.append(
            "take_family_candidate_multiplicity_is_a_structural_probability_pressure"
        )
    if aggregate_card["take_probability_excess_over_candidate_share"]["mean"] > 0.0:
        interpretations.append(
            "recorded_scores_amplify_take_probability_beyond_candidate_multiplicity"
        )
    if aggregate_card["candidate_minus_kind_entropy"]["mean"] > 0.0:
        interpretations.append(
            "candidate_entropy_overstates_action_family_diversity"
        )
    if trained_canary["card_reward"]["greedy_take_only"]:
        interpretations.append("terminal_greedy_canary_is_take_family_saturated")

    source_identities = sorted(reader.source_identities, key=lambda row: row["path"])
    result = {
        "authority": _authority(),
        "canary": {
            "blockers": list(canary_gate["blockers"]),
            "initial": initial_canary,
            "trained": trained_canary,
            "verdict": canary_gate["verdict"],
        },
        "command": _normalized_command(command),
        "conclusion": {
            "bounded_interpretations": interpretations,
            "prohibited_claims": [
                "formal_rl_readiness",
                "intervention_effectiveness",
                "live_policy_value",
                "optimizer_or_reward_causality",
                "successor_experiment_authority",
            ],
            "status": "mechanism_narrowed_causality_unresolved",
            "unresolved_hypotheses": [
                "candidate_space_objective_causality",
                "entropy_coefficient_or_entropy_target_causality",
                "floor_only_reward_credit_causality",
                "optimizer_dynamics_causality",
                "proposed_correction_effect",
            ],
        },
        "integrity": {
            "checkpoint_count": len(checkpoint_paths),
            "checkpoint_identity": dict(checkpoint_identity or {}),
            "holdout_accessed": False,
            "initial_model_sha256": initial_model_sha256,
            "logical_execution_id": reader.manifest["logical_execution_id"],
            "source_artifacts": source_identities,
            "source_root": reader.source.as_posix(),
            "status": "valid",
            "terminal_verdict": reader.manifest["verdict"],
        },
        "schema_version": AUDIT_SCHEMA_VERSION,
        "trajectory": {
            "aggregate": {
                "card_reward": aggregate_card,
                "controls": {
                    category: aggregate_decisions[category]
                    for category in ("event", "route", "shop")
                    if category in aggregate_decisions
                },
                "decision_count": aggregate_decisions["decision_count"],
                "outcomes": aggregate_outcomes,
            },
            "boundaries": boundaries,
            "chunk_count": len(chunk_summaries),
            "chunks": chunk_summaries,
            "initial_tensor_gap": (
                "initial weights were not retained; checkpoint 1 has no parameter delta"
            ),
            "pre_update_post_update_alignment": (
                "chunk n rows precede optimizer update n+1; checkpoint n+1 follows it"
            ),
        },
    }
    return json.loads(canonical_json_bytes(result).decode("utf-8"))


def _fmt(value: Any) -> str:
    if value is None:
        return "not observed"
    if isinstance(value, float):
        return format(value, ".12g")
    return str(value)


def render_markdown(result: Mapping[str, Any]) -> str:
    trajectory = result["trajectory"]
    aggregate = trajectory["aggregate"]["card_reward"]
    initial = result["canary"]["initial"]["card_reward"]
    trained = result["canary"]["trained"]["card_reward"]
    boundaries = trajectory["boundaries"]
    lines = [
        "# State-Conditioned Card-Reward Collapse Audit",
        "",
        "## Result",
        "",
        f"- Status: `{result['conclusion']['status']}`",
        f"- Terminal verdict: `{result['integrity']['terminal_verdict']}`",
        f"- Canary blocker: `{result['canary']['blockers'][0]}`",
        f"- Training chunks: `{trajectory['chunk_count']}`",
        f"- Holdout accessed: `{str(result['integrity']['holdout_accessed']).lower()}`",
        "",
        "## Exact Boundaries",
        "",
        "| Predicate | First observed chunk | Earliest persistent chunk |",
        "| --- | ---: | ---: |",
    ]
    for name in ("selected_take_only", "greedy_take_only"):
        boundary = boundaries[name]
        lines.append(
            f"| `{name}` | {_fmt(boundary['first_observed_chunk'])} | "
            f"{_fmt(boundary['earliest_persistent_chunk'])} |"
        )
    lines.extend(
        [
            "",
            "## Action-Family Evidence",
            "",
            f"- Training card-reward decisions: `{aggregate['decision_count']}`",
            f"- Mean take candidate share: `{_fmt(aggregate['take_candidate_share']['mean'])}`",
            f"- Mean take probability mass: `{_fmt(aggregate['take_probability_mass']['mean'])}`",
            "- Mean take probability excess over candidate share: "
            f"`{_fmt(aggregate['take_probability_excess_over_candidate_share']['mean'])}`",
            "- Mean candidate entropy minus kind entropy: "
            f"`{_fmt(aggregate['candidate_minus_kind_entropy']['mean'])}`",
            f"- Initial canary selected kinds: `{json.dumps(initial['selected_kinds'], sort_keys=True)}`",
            f"- Trained canary selected kinds: `{json.dumps(trained['selected_kinds'], sort_keys=True)}`",
            f"- Initial canary greedy take-only: `{str(initial['greedy_take_only']).lower()}`",
            f"- Trained canary greedy take-only: `{str(trained['greedy_take_only']).lower()}`",
            "",
            "## Training Outcomes And Controls",
            "",
            f"- Outcomes: `{json.dumps(trajectory['aggregate']['outcomes'], sort_keys=True)}`",
        ]
    )
    controls = trajectory["aggregate"]["controls"]
    for category in ("event", "route", "shop"):
        if category in controls:
            lines.append(
                f"- `{category}` decisions: `{controls[category]['decision_count']}`; "
                f"selected kinds: `{json.dumps(controls[category]['selected_kinds'], sort_keys=True)}`"
            )
    lines.extend(
        [
            "",
            "## Chunk Trajectory",
            "",
            "| Chunk | Pass | Eligible cards | Selected take rate | Greedy take rate | "
            "Mean take probability | Min take-skip margin | Mean floor | Unsupported | "
            "Post-update model delta L2 |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for chunk in trajectory["chunks"]:
        card = chunk["card_reward"]
        selected_rate = card["selected_kinds"].get("take", {}).get("rate", 0.0)
        greedy_rate = card["greedy_kinds"].get("take", {}).get("rate", 0.0)
        lines.append(
            f"| {chunk['chunk_index']} | {chunk['coordinates']['pass_index']} | "
            f"{card['eligible_take_skip_decisions']} | {_fmt(selected_rate)} | "
            f"{_fmt(greedy_rate)} | {_fmt(card['take_probability_mass']['mean'])} | "
            f"{_fmt(card['best_take_minus_skip_score']['min'])} | "
            f"{_fmt(chunk['outcomes']['effective_floor']['mean'])} | "
            f"{chunk['outcomes']['unsupported_episodes']} | "
            f"{_fmt(chunk['checkpoint']['model_delta_l2_from_previous_checkpoint'])} |"
        )
    lines.extend(
        [
            "",
            "## Evidence Gaps",
            "",
            f"- Initial tensor gap: {trajectory['initial_tensor_gap']}.",
            f"- Alignment: {trajectory['pre_update_post_update_alignment']}.",
            "- Checkpoint implementation commit is internally consistent; the audit binds "
            "its logical execution and registration hash through the terminal manifest.",
            "- No retained counterfactual identifies reward, optimizer, entropy, or "
            "intervention causality.",
            "",
            "## Bounded Interpretations",
            "",
        ]
    )
    lines.extend(
        f"- `{interpretation}`"
        for interpretation in result["conclusion"]["bounded_interpretations"]
    )
    lines.extend(["", "## Unresolved", ""])
    lines.extend(
        f"- `{hypothesis}`"
        for hypothesis in result["conclusion"]["unresolved_hypotheses"]
    )
    lines.extend(
        [
            "",
            "The retained evidence is descriptive. It does not establish reward, "
            "optimizer, architecture, or intervention causality and grants no "
            "successor execution authority.",
            "",
            "## Sources",
            "",
            "| Path | Bytes | SHA-256 |",
            "| --- | ---: | --- |",
        ]
    )
    for source in result["integrity"]["source_artifacts"]:
        lines.append(
            f"| `{source['path']}` | {source['size_bytes']} | `{source['sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Invocation",
            "",
            "```json",
            json.dumps(result["command"], ensure_ascii=True),
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise CollapseAuditError(f"output path is a symlink: {path}")
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.is_symlink():
        raise CollapseAuditError(f"temporary output path is a symlink: {temporary}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def publish_audit(
    source_root: Path | str,
    output_json: Path | str,
    output_markdown: Path | str,
) -> dict[str, Any]:
    source = Path(source_root).resolve()
    json_path = Path(output_json).resolve()
    markdown_path = Path(output_markdown).resolve()
    if json_path == markdown_path:
        raise CollapseAuditError("JSON and Markdown output paths must differ")
    if _is_within(json_path, source) or _is_within(markdown_path, source):
        raise CollapseAuditError("outputs must remain outside the source bundle")
    command = [
        str(Path(sys.executable).resolve()),
        str(Path(__file__).resolve()),
        "--source",
        str(source),
        "--output-json",
        str(json_path),
        "--output-markdown",
        str(markdown_path),
    ]
    result = audit_bundle(source, command=command)
    json_payload = canonical_json_bytes(result)
    markdown_payload = render_markdown(result).encode("utf-8")
    json_temp = json_path.with_name(f".{json_path.name}.tmp")
    markdown_temp = markdown_path.with_name(f".{markdown_path.name}.tmp")
    try:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        if any(path.is_symlink() for path in (json_path, markdown_path, json_temp, markdown_temp)):
            raise CollapseAuditError("output or temporary path is a symlink")
        json_temp.write_bytes(json_payload)
        markdown_temp.write_bytes(markdown_payload)
        os.replace(json_temp, json_path)
        os.replace(markdown_temp, markdown_path)
    finally:
        for temporary in (json_temp, markdown_temp):
            if temporary.exists() and not temporary.is_symlink():
                temporary.unlink()
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--output-markdown", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = publish_audit(args.source, args.output_json, args.output_markdown)
    except (CollapseAuditError, OSError) as exc:
        print(f"collapse audit failed: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "chunk_count": result["trajectory"]["chunk_count"],
                "output_json": str(args.output_json.resolve()),
                "output_markdown": str(args.output_markdown.resolve()),
                "status": result["conclusion"]["status"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
