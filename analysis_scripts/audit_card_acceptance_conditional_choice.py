"""Source-only acceptance-versus-conditional audit for the sealed r2 run."""

from __future__ import annotations

import argparse
import array
import base64
from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analysis_scripts import audit_cross_fitted_baseline_support as baseline  # noqa: E402


AuditError = baseline.AuditError
AUDIT_SCHEMA_VERSION = "noncombat-card-acceptance-conditional-choice-audit-v1"
LOGICAL_EXECUTION_ID = baseline.LOGICAL_EXECUTION_ID
EXPECTED_IDENTITY = baseline.EXPECTED_IDENTITY
EXPECTED_TERMINAL_SHA256 = baseline.EXPECTED_TERMINAL_SHA256
EXPECTED_MANIFEST_SHA256 = baseline.EXPECTED_MANIFEST_SHA256
EXPECTED_VERDICT = baseline.EXPECTED_VERDICT

EXPECTED_PRIOR_JSON_SHA256 = (
    "0f63681aea43e197bba0d5fcd8b0a6f759c4fe27a3646a6648b2cbad87d968c0"
)
EXPECTED_PRIOR_MARKDOWN_SHA256 = (
    "43e566dd5d838ae5710adfaac52d276a9c1a1e469e697a663c2341a0aa98dd7e"
)
EXPECTED_PRIOR_VERDICT = "take_pressure_persists_on_supported_unclipped_rows"

DEFAULT_SOURCE_PATH = "analysis_scripts/audit_card_acceptance_conditional_choice.py"
DEFAULT_BASELINE_SOURCE_PATH = "analysis_scripts/audit_cross_fitted_baseline_support.py"
DEFAULT_VERIFIER_SOURCE_PATH = (
    "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py"
)
DEFAULT_SPEC_PATH = (
    "openspec/changes/audit-card-acceptance-conditional-choice/specs/"
    "noncombat-card-acceptance-conditional-choice-audit/spec.md"
)
SOURCE_BINDING_PATHS = (
    DEFAULT_SOURCE_PATH,
    DEFAULT_BASELINE_SOURCE_PATH,
    DEFAULT_VERIFIER_SOURCE_PATH,
    DEFAULT_SPEC_PATH,
)
DEFAULT_TERMINAL_ROOT = baseline.DEFAULT_TERMINAL_ROOT
DEFAULT_POSTMORTEM_PATH = baseline.DEFAULT_POSTMORTEM_PATH
DEFAULT_PRIOR_JSON_PATH = (
    "reports/noncombat_cross_fitted_baseline_support_audit_20260809.json"
)
DEFAULT_PRIOR_MARKDOWN_PATH = (
    "reports/noncombat_cross_fitted_baseline_support_audit_20260809.md"
)
DEFAULT_JSON_NAME = (
    "noncombat_card_acceptance_conditional_choice_audit_20260809.json"
)
DEFAULT_MARKDOWN_NAME = (
    "noncombat_card_acceptance_conditional_choice_audit_20260809.md"
)

COMPONENT_NAMES = (
    "card_reward_family_policy",
    "card_reward_conditional_policy",
    "other_policy",
    "family_entropy_regularizer",
    "conditional_entropy_regularizer",
)
AUTHORITY_NAMES = (
    "causal",
    "causal_claim",
    "cohort_materialization",
    "communication_mod",
    "environment_construction",
    "evaluation",
    "execution",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "model_loading",
    "native_loading",
    "ope",
    "policy_quality",
    "policy_promotion",
    "qualification",
    "replay",
    "seed_access",
    "training",
)
LIMITATIONS = (
    "Acceptance and conditional pressures are descriptive row-local score-space "
    "coordinates, not causal effects or optimizer updates.",
    "Shared-parameter gradient geometry cannot identify a candidate-score effect "
    "because the sealed bundle contains no per-row score Jacobian.",
    "Repeated decisions within one trajectory are not independent samples.",
    "The exploratory probe used to scope this known-data audit was not a blind "
    "preregistration and selected no magnitude threshold.",
    "The audit estimates no policy value, confidence interval, OPE quantity, "
    "target-supported outcome, or live-game effect.",
    "No verdict authorizes fitting, training, replay, evaluation, model loading, "
    "gameplay, qualification, or promotion.",
)
EXPLORATORY_PROBE = {
    "card_reward_rows": 3536,
    "conditional_take_candidates": {"3": 3522, "4": 14},
    "disclosed_before_publication": True,
    "magnitude_threshold_selected": False,
    "observation": (
        "near-uniform conditional distributions with monotonic chunk-level "
        "entropy/gap movement and mixed final-window direct margin signs"
    ),
}

SUPPORT_MINIMUM_ROWS = 64
SUPPORT_MINIMUM_UNIQUE_GREEDY_ROWS = 64
SUPPORT_MINIMUM_SIDE_ROWS = 16
FAMILY_ENTROPY_COEFFICIENT = 0.01
CONDITIONAL_ENTROPY_COEFFICIENT = 0.01
FLOAT_ATOL = 1e-12
VECTOR_ATOL = 1e-9
GRADIENT_ATOL = 1e-7
GRADIENT_RTOL = 1e-5
GRADIENT_NORM_CEILING = 1.0
GRADIENT_CLIP_EPSILON = 1e-6
MAX_VECTOR_BYTES = 64 * 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
EXPECTED_CHUNKS = 8
EXPECTED_TRAJECTORIES = 512
EXPECTED_DECISIONS = 11729
EXPECTED_CARD_REWARD_ROWS = 3536


def audit_authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def audit_scope() -> dict[str, bool]:
    return {
        "artifact_mutation": False,
        "environment_construction": False,
        "evaluation": False,
        "model_loading": False,
        "native_loading": False,
        "new_seed_access": False,
        "source_only": True,
        "training_or_replay": False,
    }


def forbidden_loaded_modules() -> list[str]:
    return baseline.forbidden_loaded_modules()


def canonical_json_bytes(value: object) -> bytes:
    return baseline.canonical_json_bytes(value)


def parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    return baseline.parse_json_bytes(raw, label)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    return baseline._mapping(value, label)


def _sequence(value: Any, label: str) -> Sequence[Any]:
    return baseline._sequence(value, label)


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    return baseline._integer(value, label, minimum=minimum)


def _finite(value: Any, label: str) -> float:
    return baseline._finite(value, label)


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _close(actual: Any, expected: float, label: str) -> None:
    value = _finite(actual, label)
    if not math.isclose(value, expected, rel_tol=0.0, abs_tol=FLOAT_ATOL):
        raise AuditError(f"{label} mismatch")


def _softmax(values: Sequence[float]) -> list[float]:
    if not values:
        raise AuditError("softmax input must be nonempty")
    maximum = max(values)
    weights = [math.exp(value - maximum) for value in values]
    denominator = math.fsum(weights)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise AuditError("softmax denominator must be finite and positive")
    return [weight / denominator for weight in weights]


def _entropy(probabilities: Sequence[float]) -> float:
    if not probabilities:
        raise AuditError("entropy input must be nonempty")
    if not math.isclose(
        math.fsum(probabilities), 1.0, rel_tol=0.0, abs_tol=FLOAT_ATOL
    ):
        raise AuditError("probabilities do not sum to one")
    return -math.fsum(
        probability * math.log(probability)
        for probability in probabilities
        if probability > 0.0
    )


def reconstruct_distribution(
    candidates: Sequence[Mapping[str, Any]],
    candidate_scores: Mapping[str, Any],
) -> dict[str, Any]:
    rows = list(_sequence(candidates, "candidates"))
    if not rows:
        raise AuditError("candidates must be nonempty")
    scores = _mapping(candidate_scores, "candidate scores")
    action_ids: list[str] = []
    families_by_action: dict[str, str] = {}
    normalized_scores: dict[str, float] = {}
    family_members: dict[str, list[str]] = {}
    for index, raw in enumerate(rows):
        candidate = _mapping(raw, f"candidate[{index}]")
        action_id = candidate.get("action_id")
        family = candidate.get("kind")
        if not isinstance(action_id, str) or not action_id:
            raise AuditError("candidate identity is invalid")
        if not isinstance(family, str) or not family:
            raise AuditError("candidate family identity is invalid")
        if action_id in families_by_action:
            raise AuditError("duplicate candidate identity")
        if action_id not in scores:
            raise AuditError("candidate score coverage differs")
        score = _finite(scores[action_id], f"candidate score {action_id}")
        action_ids.append(action_id)
        families_by_action[action_id] = family
        normalized_scores[action_id] = score
        family_members.setdefault(family, []).append(action_id)
    if set(scores) != set(action_ids):
        raise AuditError("candidate score coverage differs")

    family_order = sorted(family_members)
    family_scores = {
        family: max(normalized_scores[action] for action in family_members[family])
        for family in family_order
    }
    family_values = _softmax([family_scores[family] for family in family_order])
    family_probabilities = dict(zip(family_order, family_values, strict=True))

    conditional_probabilities: dict[str, float] = {}
    conditional_entropies: dict[str, float] = {}
    for family in family_order:
        members = family_members[family]
        probabilities = _softmax([normalized_scores[action] for action in members])
        for action, probability in zip(members, probabilities, strict=True):
            conditional_probabilities[action] = probability
        conditional_entropies[family] = _entropy(probabilities)
    joint_probabilities = {
        action: family_probabilities[families_by_action[action]]
        * conditional_probabilities[action]
        for action in action_ids
    }
    family_entropy = _entropy(list(family_probabilities.values()))
    expected_conditional_entropy = math.fsum(
        family_probabilities[family] * conditional_entropies[family]
        for family in family_order
    )
    maximum_score = max(normalized_scores.values())
    maximum_action_ids = sorted(
        action
        for action, score in normalized_scores.items()
        if score == maximum_score
    )
    maximum_families = sorted(
        {families_by_action[action] for action in maximum_action_ids}
    )
    return {
        "action_ids": list(action_ids),
        "candidate_families": dict(families_by_action),
        "conditional_entropies": conditional_entropies,
        "conditional_probabilities": conditional_probabilities,
        "expected_conditional_entropy": expected_conditional_entropy,
        "family_entropy": family_entropy,
        "family_order": family_order,
        "family_probabilities": family_probabilities,
        "family_scores": family_scores,
        "joint_probabilities": joint_probabilities,
        "raw_score_max_action_ids": maximum_action_ids,
        "raw_score_max_family_ids": maximum_families,
    }


def _compare_float_mapping(
    actual: Any, expected: Mapping[str, float], label: str
) -> None:
    values = _mapping(actual, label)
    if set(values) != set(expected):
        raise AuditError(f"{label} identity mismatch")
    for key, expected_value in expected.items():
        _close(values[key], expected_value, f"{label} {key}")


def _validated_row_distribution(row: Mapping[str, Any]) -> dict[str, Any]:
    diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
    candidates = _sequence(diagnostic.get("candidates"), "candidates")
    scores = _mapping(diagnostic.get("candidate_scores"), "candidate scores")
    distribution = reconstruct_distribution(candidates, scores)
    if diagnostic.get("family_order") != distribution["family_order"]:
        raise AuditError("family order mismatch")
    if diagnostic.get("raw_score_max_action_ids") != distribution[
        "raw_score_max_action_ids"
    ]:
        raise AuditError("raw score maximum action identities mismatch")
    if diagnostic.get("raw_score_max_family_ids") != distribution[
        "raw_score_max_family_ids"
    ]:
        raise AuditError("raw score maximum family identities mismatch")
    _compare_float_mapping(
        diagnostic.get("family_probabilities"),
        distribution["family_probabilities"],
        "family probabilities",
    )
    _compare_float_mapping(
        diagnostic.get("conditional_probabilities"),
        distribution["conditional_probabilities"],
        "conditional probabilities",
    )
    _compare_float_mapping(
        diagnostic.get("joint_probabilities"),
        distribution["joint_probabilities"],
        "joint probabilities",
    )
    selected_action = diagnostic.get("selected_action_id")
    if (
        not isinstance(selected_action, str)
        or selected_action not in distribution["candidate_families"]
    ):
        raise AuditError("selected action identity mismatch")
    selected_family = distribution["candidate_families"][selected_action]
    if diagnostic.get("selected_family") != selected_family:
        raise AuditError("selected family identity mismatch")
    if diagnostic.get("multi_family") is not (
        len(distribution["family_order"]) > 1
    ):
        raise AuditError("multi-family marker mismatch")
    if diagnostic.get("selection_mode") != "family-first-then-conditional-v1":
        raise AuditError("selection mode mismatch")

    terms = _mapping(row.get("policy_terms"), "policy terms")
    if terms.get("selected_action_id") != selected_action:
        raise AuditError("policy selected action mismatch")
    if terms.get("selected_family") != selected_family:
        raise AuditError("policy selected family mismatch")
    _close(terms.get("family_entropy"), distribution["family_entropy"], "family entropy")
    _close(
        terms.get("conditional_entropy"),
        distribution["expected_conditional_entropy"],
        "conditional entropy",
    )
    _close(
        terms.get("selected_conditional_log_probability"),
        math.log(distribution["conditional_probabilities"][selected_action]),
        "selected conditional log probability",
    )
    _close(
        terms.get("selected_family_log_probability"),
        math.log(distribution["family_probabilities"][selected_family]),
        "selected family log probability",
    )
    _close(
        terms.get("selected_joint_log_probability"),
        math.log(distribution["joint_probabilities"][selected_action]),
        "selected joint log probability",
    )
    return distribution


def direct_acceptance_pressure(
    row: Mapping[str, Any], *, total_chunk_decisions: int
) -> dict[str, float]:
    if total_chunk_decisions <= 0:
        raise AuditError("chunk decision count must be positive")
    distribution = _validated_row_distribution(row)
    diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
    if "take" not in distribution["family_probabilities"]:
        raise AuditError("card reward lacks take family")
    p_take = distribution["family_probabilities"]["take"]
    if not 0.0 < p_take < 1.0:
        raise AuditError("take family probability must be interior")
    advantage = _finite(row.get("advantage"), "advantage")
    selected_take = diagnostic.get("selected_family") == "take"
    policy = advantage * ((1.0 if selected_take else 0.0) - p_take)
    policy /= total_chunk_decisions
    family_entropy = (
        -FAMILY_ENTROPY_COEFFICIENT
        * p_take
        * (math.log(p_take) + distribution["family_entropy"])
        / total_chunk_decisions
    )
    conditional_entropy = (
        CONDITIONAL_ENTROPY_COEFFICIENT
        * p_take
        * (
            distribution["conditional_entropies"]["take"]
            - distribution["expected_conditional_entropy"]
        )
        / total_chunk_decisions
    )
    return {
        "combined": policy + family_entropy + conditional_entropy,
        "conditional_entropy": conditional_entropy,
        "family_entropy": family_entropy,
        "policy": policy,
        "take_probability": p_take,
    }


def direct_conditional_pressure(
    row: Mapping[str, Any], *, total_chunk_decisions: int
) -> dict[str, Any]:
    if total_chunk_decisions <= 0:
        raise AuditError("chunk decision count must be positive")
    distribution = _validated_row_distribution(row)
    diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
    take_actions = [
        action
        for action in distribution["action_ids"]
        if distribution["candidate_families"][action] == "take"
    ]
    if len(take_actions) < 2:
        raise AuditError("conditional audit requires at least two take candidates")
    p_take = distribution["family_probabilities"].get("take")
    if p_take is None:
        raise AuditError("card reward lacks take family")
    q = distribution["conditional_probabilities"]
    h_take = distribution["conditional_entropies"]["take"]
    advantage = _finite(row.get("advantage"), "advantage")
    selected_take = diagnostic.get("selected_family") == "take"
    selected_action = diagnostic.get("selected_action_id")
    pressures: dict[str, dict[str, float]] = {}
    for action in take_actions:
        probability = q[action]
        policy = 0.0
        if selected_take:
            policy = advantage * (
                (1.0 if action == selected_action else 0.0) - probability
            ) / total_chunk_decisions
        conditional_entropy = (
            -CONDITIONAL_ENTROPY_COEFFICIENT
            * p_take
            * probability
            * (math.log(probability) + h_take)
            / total_chunk_decisions
        )
        pressures[action] = {
            "combined": policy + conditional_entropy,
            "conditional_entropy": conditional_entropy,
            "policy": policy,
        }
    scores = _mapping(diagnostic.get("candidate_scores"), "candidate scores")
    maximum = max(_finite(scores[action], f"score {action}") for action in take_actions)
    greedy = sorted(
        action
        for action in take_actions
        if _finite(scores[action], f"score {action}") == maximum
    )
    margin: float | None = None
    if len(greedy) == 1:
        greedy_action = greedy[0]
        peer_values = [
            pressures[action]["combined"]
            for action in take_actions
            if action != greedy_action
        ]
        margin = pressures[greedy_action]["combined"] - math.fsum(peer_values) / len(
            peer_values
        )
    probabilities = sorted((q[action] for action in take_actions), reverse=True)
    return {
        "candidate_pressures": pressures,
        "greedy_action_ids": greedy,
        "greedy_margin_pressure": margin,
        "max_conditional_probability": probabilities[0],
        "normalized_take_entropy": h_take / math.log(len(take_actions)),
        "take_candidate_count": len(take_actions),
        "take_entropy": h_take,
        "top_two_probability_gap": probabilities[0] - probabilities[1],
    }


def reconcile_scalar_components(
    rows: Sequence[Mapping[str, Any]],
    stored: Mapping[str, Any],
    stored_full: Any,
) -> dict[str, float]:
    values = list(_sequence(rows, "decision rows"))
    if not values:
        raise AuditError("decision rows must be nonempty")
    count = len(values)
    calculated = {
        "card_reward_conditional_policy": math.fsum(
            -_finite(row.get("advantage"), "advantage")
            * _finite(
                _mapping(row.get("policy_terms"), "policy terms").get(
                    "selected_conditional_log_probability"
                ),
                "selected conditional log probability",
            )
            for row in values
            if row.get("category") == "card_reward"
        )
        / count,
        "card_reward_family_policy": math.fsum(
            -_finite(row.get("advantage"), "advantage")
            * _finite(
                _mapping(row.get("policy_terms"), "policy terms").get(
                    "selected_family_log_probability"
                ),
                "selected family log probability",
            )
            for row in values
            if row.get("category") == "card_reward"
        )
        / count,
        "conditional_entropy_regularizer": -CONDITIONAL_ENTROPY_COEFFICIENT
        * math.fsum(
            _finite(
                _mapping(row.get("policy_terms"), "policy terms").get(
                    "conditional_entropy"
                ),
                "conditional entropy",
            )
            for row in values
        )
        / count,
        "family_entropy_regularizer": -FAMILY_ENTROPY_COEFFICIENT
        * math.fsum(
            _finite(
                _mapping(row.get("policy_terms"), "policy terms").get(
                    "family_entropy"
                ),
                "family entropy",
            )
            for row in values
        )
        / count,
        "other_policy": math.fsum(
            -_finite(row.get("advantage"), "advantage")
            * _finite(
                _mapping(row.get("policy_terms"), "policy terms").get(
                    "selected_joint_log_probability"
                ),
                "selected joint log probability",
            )
            for row in values
            if row.get("category") != "card_reward"
        )
        / count,
    }
    stored_values = _mapping(stored, "scalar components")
    if set(stored_values) != set(COMPONENT_NAMES):
        raise AuditError("scalar component identity mismatch")
    for name, value in calculated.items():
        if not math.isclose(
            value,
            _finite(stored_values[name], f"stored scalar component {name}"),
            rel_tol=0.0,
            abs_tol=FLOAT_ATOL,
        ):
            raise AuditError(f"scalar component mismatch: {name}")
    reconstructed_full = math.fsum(calculated.values())
    if not math.isclose(
        reconstructed_full,
        _finite(stored_full, "scalar full loss"),
        rel_tol=0.0,
        abs_tol=FLOAT_ATOL,
    ):
        raise AuditError("scalar full loss mismatch")
    return calculated


def decode_float_vector(
    payload: Mapping[str, Any], label: str, *, dtype: str
) -> tuple[float, ...]:
    value = _mapping(payload, label)
    formats = {"float32": ("f", 4), "float64": ("d", 8)}
    if dtype not in formats:
        raise AuditError(f"unsupported vector dtype: {dtype}")
    if value.get("dtype") != dtype:
        raise AuditError(f"{label} dtype mismatch")
    if value.get("byte_order") != "little":
        raise AuditError(f"{label} byte order mismatch")
    encoded = value.get("data_base64")
    if not isinstance(encoded, str):
        raise AuditError(f"{label} base64 payload is invalid")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise AuditError(f"{label} base64 payload is invalid") from exc
    typecode, item_size = formats[dtype]
    if len(raw) > MAX_VECTOR_BYTES or len(raw) % item_size:
        raise AuditError(f"{label} byte size is invalid")
    digest = value.get("data_sha256")
    if not isinstance(digest, str) or _digest(raw) != digest:
        raise AuditError(f"{label} data digest mismatch")
    shape = value.get("shape")
    if shape != [len(raw) // item_size]:
        raise AuditError(f"{label} shape mismatch")
    result = array.array(typecode)
    result.frombytes(raw)
    if sys.byteorder != "little":
        result.byteswap()
    values = tuple(float(item) for item in result)
    if any(not math.isfinite(item) for item in values):
        raise AuditError(f"{label} contains a non-finite value")
    return values


def decode_float64_vector(payload: Mapping[str, Any], label: str) -> tuple[float, ...]:
    return decode_float_vector(payload, label, dtype="float64")


def _maximum_vector_residual(
    actual: Sequence[float], expected: Sequence[float], label: str
) -> float:
    if len(actual) != len(expected) or not actual:
        raise AuditError(f"{label} shape mismatch")
    residuals = [
        abs(left - right) for left, right in zip(actual, expected, strict=True)
    ]
    if any(
        not math.isclose(
            left,
            right,
            rel_tol=GRADIENT_RTOL,
            abs_tol=GRADIENT_ATOL,
        )
        for left, right in zip(actual, expected, strict=True)
    ):
        raise AuditError(f"{label} mismatch")
    return max(residuals, default=0.0)


def vector_geometry(left: Sequence[float], right: Sequence[float]) -> dict[str, Any]:
    if len(left) != len(right) or not left:
        raise AuditError("gradient vector shapes differ")
    left_norm_sq = math.fsum(value * value for value in left)
    right_norm_sq = math.fsum(value * value for value in right)
    dot = math.fsum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(left_norm_sq)
    right_norm = math.sqrt(right_norm_sq)
    cosine = None
    if left_norm > 0.0 and right_norm > 0.0:
        cosine = dot / (left_norm * right_norm)
    return {
        "cosine": cosine,
        "dot": dot,
        "left_norm": left_norm,
        "right_norm": right_norm,
    }


def reconcile_gradient_vectors(gradients: Mapping[str, Any]) -> dict[str, Any]:
    value = _mapping(gradients, "gradients")
    if value.get("component_order") != list(COMPONENT_NAMES):
        raise AuditError("gradient component order mismatch")
    payloads = _mapping(value.get("component_vectors"), "component vectors")
    if set(payloads) != set(COMPONENT_NAMES):
        raise AuditError("gradient component identity mismatch")
    components = {
        name: decode_float64_vector(
            _mapping(payloads[name], f"component {name}"), f"component {name}"
        )
        for name in COMPONENT_NAMES
    }
    full = decode_float64_vector(_mapping(value.get("full"), "full gradient"), "full gradient")
    if any(len(vector) != len(full) for vector in components.values()):
        raise AuditError("gradient component shape mismatch")
    reconstructed = tuple(
        math.fsum(components[name][index] for name in COMPONENT_NAMES)
        for index in range(len(full))
    )
    residuals = [abs(actual - expected) for actual, expected in zip(reconstructed, full, strict=True)]
    maximum_residual = max(residuals, default=0.0)
    if maximum_residual > VECTOR_ATOL:
        raise AuditError("gradient components do not reconstruct full gradient")
    full_norm = math.sqrt(math.fsum(item * item for item in full))
    clip_factor = _finite(value.get("clip_factor"), "clip factor")
    if not 0.0 < clip_factor <= 1.0:
        raise AuditError("clip factor is outside (0, 1]")
    expected_clip_factor = (
        1.0
        if full_norm <= GRADIENT_NORM_CEILING
        else GRADIENT_NORM_CEILING / (full_norm + GRADIENT_CLIP_EPSILON)
    )
    if not math.isclose(
        clip_factor,
        expected_clip_factor,
        rel_tol=0.0,
        abs_tol=FLOAT_ATOL,
    ):
        raise AuditError("clip factor mismatch")
    clipped_full = decode_float64_vector(
        _mapping(value.get("clipped_full"), "clipped full gradient"),
        "clipped full gradient",
    )
    expected_clipped = tuple(item * clip_factor for item in full)
    uniform_clip_max_abs = _maximum_vector_residual(
        clipped_full, expected_clipped, "uniform clipping"
    )
    installed = decode_float_vector(
        _mapping(value.get("installed"), "installed gradient"),
        "installed gradient",
        dtype="float32",
    )
    expected_installed = tuple(
        struct.unpack("<f", struct.pack("<f", item))[0]
        for item in expected_clipped
    )
    if installed != expected_installed:
        raise AuditError("installed gradient mismatch")
    consumed = decode_float_vector(
        _mapping(
            value.get("consumed_torch_clipped"), "consumed gradient"
        ),
        "consumed gradient",
        dtype="float32",
    )
    if consumed != installed:
        raise AuditError("consumed gradient mismatch")
    norms = {
        name: math.sqrt(math.fsum(item * item for item in vector))
        for name, vector in components.items()
    }
    pairwise: dict[str, Any] = {}
    for left_index, left_name in enumerate(COMPONENT_NAMES):
        for right_name in COMPONENT_NAMES[left_index + 1 :]:
            pairwise[f"{left_name}__{right_name}"] = vector_geometry(
                components[left_name], components[right_name]
            )
    full_geometry = {
        name: vector_geometry(components[name], full) for name in COMPONENT_NAMES
    }
    return {
        "clip_factor": clip_factor,
        "component_norms": norms,
        "family_conditional": vector_geometry(
            components["card_reward_family_policy"],
            components["card_reward_conditional_policy"],
        ),
        "clipped_full_norm": math.sqrt(
            math.fsum(item * item for item in clipped_full)
        ),
        "full_norm": full_norm,
        "installed_matches_consumed": True,
        "pairwise": pairwise,
        "reconstruction_max_abs": maximum_residual,
        "to_full": full_geometry,
        "uniform_clip_max_abs": uniform_clip_max_abs,
    }


def summarize_windows(
    chunks: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    values = list(_sequence(chunks, "chunk summaries"))
    if [row.get("chunk_index") for row in values] != list(range(EXPECTED_CHUNKS)):
        raise AuditError("chunk indices must be exactly 0..7")

    def summarize(start: int, stop: int) -> dict[str, Any]:
        window = values[start:stop]
        return {
            "acceptance_pressure_sum": math.fsum(
                _finite(row.get("acceptance_pressure_sum"), "acceptance pressure")
                for row in window
            ),
            "chunk_indices": list(range(start, stop)),
            "conditional_margin_pressure_sum": math.fsum(
                _finite(
                    row.get("conditional_margin_pressure_sum"),
                    "conditional margin pressure",
                )
                for row in window
            ),
            "eligible_rows": sum(
                _integer(row.get("eligible_rows"), "eligible rows")
                for row in window
            ),
            "mean_max_conditional_probability": _mean(
                [
                    _finite(
                        row.get("mean_max_conditional_probability"),
                        "maximum conditional probability",
                    )
                    for row in window
                ],
                "maximum conditional probabilities",
            ),
            "mean_normalized_take_entropy": _mean(
                [
                    _finite(
                        row.get("mean_normalized_take_entropy"),
                        "normalized take entropy",
                    )
                    for row in window
                ],
                "normalized take entropies",
            ),
            "mean_top_two_probability_gap": _mean(
                [
                    _finite(
                        row.get("mean_top_two_probability_gap"),
                        "top-two probability gap",
                    )
                    for row in window
                ],
                "top-two probability gaps",
            ),
            "selected_non_take_rows": sum(
                _integer(row.get("selected_non_take_rows"), "selected non-take rows")
                for row in window
            ),
            "selected_take_rows": sum(
                _integer(row.get("selected_take_rows"), "selected take rows")
                for row in window
            ),
            "take_tie_rows": sum(
                _integer(row.get("take_tie_rows"), "take tie rows")
                for row in window
            ),
            "unique_greedy_rows": sum(
                _integer(row.get("unique_greedy_rows"), "unique greedy rows")
                for row in window
            ),
        }

    return {"early": summarize(0, 4), "final": summarize(4, 8)}


def classify_verdict(
    chunks: Sequence[Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    values = list(_sequence(chunks, "chunk summaries"))
    indices = [_integer(row.get("chunk_index"), "chunk index") for row in values]
    if indices != list(range(EXPECTED_CHUNKS)):
        raise AuditError("chunk indices must be exactly 0..7")
    support = "supported"
    for row in values:
        if (
            _integer(row.get("eligible_rows"), "eligible rows")
            < SUPPORT_MINIMUM_ROWS
            or _integer(row.get("unique_greedy_rows"), "unique greedy rows")
            < SUPPORT_MINIMUM_UNIQUE_GREEDY_ROWS
            or _integer(row.get("selected_take_rows"), "selected take rows")
            < SUPPORT_MINIMUM_SIDE_ROWS
            or _integer(
                row.get("selected_non_take_rows"), "selected non-take rows"
            )
            < SUPPORT_MINIMUM_SIDE_ROWS
        ):
            support = "insufficient"
    acceptance = [
        _finite(row.get("acceptance_pressure_sum"), "acceptance pressure")
        for row in values
    ]
    conditional = [
        _finite(
            row.get("conditional_margin_pressure_sum"),
            "conditional margin pressure",
        )
        for row in values
    ]
    entropies = [
        _finite(row.get("mean_normalized_take_entropy"), "normalized entropy")
        for row in values
    ]
    gaps = [
        _finite(row.get("mean_top_two_probability_gap"), "top-two gap")
        for row in values
    ]
    acceptance_consistent = all(value > 0.0 for value in acceptance)
    concentration_progresses = all(
        entropies[index + 1] < entropies[index]
        and gaps[index + 1] > gaps[index]
        for index in range(EXPECTED_CHUNKS - 1)
    )
    conditional_consistent = all(value > 0.0 for value in conditional[4:8])
    inputs = {
        "acceptance_pressure_consistent": acceptance_consistent,
        "conditional_concentration_progresses": concentration_progresses,
        "conditional_pressure_consistent": conditional_consistent,
        "support": support,
    }
    if support != "supported":
        return "insufficient_support_or_evidence", inputs
    if not acceptance_consistent:
        return "acceptance_pressure_not_consistent", inputs
    if not concentration_progresses:
        return (
            "acceptance_pressure_without_monotonic_conditional_concentration",
            inputs,
        )
    if conditional_consistent:
        return "acceptance_and_conditional_pressure_consistently_aligned", inputs
    return (
        "acceptance_pressure_with_conditional_concentration_but_"
        "mixed_direct_pressure",
        inputs,
    )


def _git(repo_root: Path, *args: str, allow_failure: bool = False) -> bytes:
    process = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if process.returncode and not allow_failure:
        message = process.stderr.decode("utf-8", errors="replace").strip()
        raise AuditError(f"git {' '.join(args)} failed: {message}")
    return process.stdout


def verify_pushed_source(repo_root: Path | str, source_commit: str) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    if not isinstance(source_commit, str) or len(source_commit) not in (40, 64):
        raise AuditError("source commit is invalid")
    head = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    origin = _git(root, "rev-parse", "origin/master").decode("ascii").strip()
    if head != source_commit or origin != source_commit:
        raise AuditError("source commit must match HEAD and origin/master")
    status = _git(root, "status", "--porcelain", "--", *SOURCE_BINDING_PATHS)
    if status.strip():
        raise AuditError("source worktree differs from the pushed commit")
    bindings: dict[str, dict[str, Any]] = {}
    for relative in SOURCE_BINDING_PATHS:
        path = baseline._regular_file(root / relative, relative)
        raw = path.read_bytes()
        committed = _git(root, "show", f"{head}:{relative}")
        if raw != committed:
            raise AuditError(f"source Git blob mismatch: {relative}")
        bindings[relative] = {"sha256": _digest(raw), "size_bytes": len(raw)}
    return {"bindings": bindings, "commit": head, "origin_master": origin}


def validate_prior_audit_bytes(raw: bytes) -> dict[str, Any]:
    if _digest(raw) != EXPECTED_PRIOR_JSON_SHA256:
        raise AuditError("prior audit JSON binding mismatch")
    report = parse_json_bytes(raw, "prior baseline-support audit")
    if canonical_json_bytes(report) != raw:
        raise AuditError("prior audit JSON is not canonical")
    if (
        report.get("schema_version")
        != baseline.AUDIT_SCHEMA_VERSION
        or report.get("identity") != EXPECTED_IDENTITY
        or report.get("verdict") != EXPECTED_PRIOR_VERDICT
        or report.get("authority") != baseline.audit_authority()
    ):
        raise AuditError("prior audit identity or verdict mismatch")
    return report


def _mean(values: Sequence[float], label: str) -> float:
    if not values:
        raise AuditError(f"{label} must be nonempty")
    return math.fsum(values) / len(values)


def _analyze_chunks(terminal_root: Path) -> dict[str, Any]:
    chunks: list[dict[str, Any]] = []
    total_decisions = 0
    total_trajectories = 0
    total_card_rewards = 0
    multiplicity: Counter[int] = Counter()

    for checkpoint_number in range(1, EXPECTED_CHUNKS + 1):
        checkpoint_path = baseline._regular_file(
            terminal_root
            / "checkpoints"
            / f"checkpoint_{checkpoint_number:04d}.json",
            f"checkpoint {checkpoint_number}",
        )
        checkpoint = baseline.verifier._parse_canonical_json(
            checkpoint_path.read_bytes(), label=f"checkpoint {checkpoint_number}"
        )
        document = baseline._read_bound_chunk(terminal_root, checkpoint)
        evidence = _mapping(document.get("evidence"), "chunk evidence")
        chunk_index = _integer(evidence.get("chunk_index"), "chunk index")
        if chunk_index != checkpoint_number - 1:
            raise AuditError("chunk order mismatch")
        rows = [
            _mapping(row, f"chunk {chunk_index} decision")
            for row in _sequence(evidence.get("decisions"), "decisions")
        ]
        baseline_data = _mapping(evidence.get("baseline"), "baseline")
        folds = {
            str(key): list(_sequence(value, f"{key} trajectories"))
            for key, value in _mapping(
                baseline_data.get("fold_trajectories"), "fold trajectories"
            ).items()
        }
        models = {
            str(model["fold_id"]): _mapping(model, "baseline model")
            for model in _sequence(baseline_data.get("models"), "baseline models")
        }
        baseline.validate_fold_rows(
            rows, folds, models, expected_held_out=16, expected_fit=48
        )
        total_chunk_decisions = len(rows)
        trajectories = {str(row.get("trajectory_id")) for row in rows}
        if len(trajectories) != 64:
            raise AuditError("chunk trajectory count mismatch")
        gradients = _mapping(evidence.get("gradients"), "gradients")
        scalar_components = reconcile_scalar_components(
            rows,
            _mapping(gradients.get("scalar_components"), "scalar components"),
            gradients.get("scalar_full_loss"),
        )
        gradient_geometry = reconcile_gradient_vectors(gradients)

        acceptance_values: list[float] = []
        acceptance_policy: list[float] = []
        acceptance_family_entropy: list[float] = []
        acceptance_conditional_entropy: list[float] = []
        conditional_values: list[float] = []
        normalized_entropies: list[float] = []
        maximum_probabilities: list[float] = []
        top_two_gaps: list[float] = []
        eligible_rows = 0
        unique_greedy_rows = 0
        selected_take_rows = 0
        selected_non_take_rows = 0
        take_ties = 0
        greedy_families: Counter[str] = Counter()
        selected_families: Counter[str] = Counter()

        for row in rows:
            baseline.validate_baseline_row(row, str(row.get("decision_id")))
            if row.get("category") != "card_reward":
                continue
            diagnostic = _mapping(row.get("diagnostic"), "diagnostic")
            candidates = [
                _mapping(candidate, "candidate")
                for candidate in _sequence(diagnostic.get("candidates"), "candidates")
            ]
            take_count = sum(candidate.get("kind") == "take" for candidate in candidates)
            if (
                diagnostic.get("multi_family") is not True
                or take_count < 2
                or "take"
                not in _mapping(
                    diagnostic.get("family_probabilities"), "family probabilities"
                )
            ):
                raise AuditError("card-reward eligibility contract mismatch")
            eligible_rows += 1
            multiplicity[take_count] += 1
            selected_family = diagnostic.get("selected_family")
            if not isinstance(selected_family, str):
                raise AuditError("selected family is invalid")
            selected_families[selected_family] += 1
            if selected_family == "take":
                selected_take_rows += 1
            else:
                selected_non_take_rows += 1
            raw_greedy = list(
                _sequence(
                    diagnostic.get("raw_score_max_family_ids"), "greedy families"
                )
            )
            greedy_key = raw_greedy[0] if len(raw_greedy) == 1 else "tie"
            greedy_families[str(greedy_key)] += 1

            acceptance = direct_acceptance_pressure(
                row, total_chunk_decisions=total_chunk_decisions
            )
            conditional = direct_conditional_pressure(
                row, total_chunk_decisions=total_chunk_decisions
            )
            acceptance_values.append(acceptance["combined"])
            acceptance_policy.append(acceptance["policy"])
            acceptance_family_entropy.append(acceptance["family_entropy"])
            acceptance_conditional_entropy.append(
                acceptance["conditional_entropy"]
            )
            normalized_entropies.append(conditional["normalized_take_entropy"])
            maximum_probabilities.append(
                conditional["max_conditional_probability"]
            )
            top_two_gaps.append(conditional["top_two_probability_gap"])
            margin = conditional["greedy_margin_pressure"]
            if margin is None:
                take_ties += 1
            else:
                unique_greedy_rows += 1
                conditional_values.append(_finite(margin, "conditional margin"))

        chunk_result = {
            "acceptance_pressure_components": {
                "conditional_entropy_sum": math.fsum(
                    acceptance_conditional_entropy
                ),
                "family_entropy_sum": math.fsum(acceptance_family_entropy),
                "policy_sum": math.fsum(acceptance_policy),
            },
            "acceptance_pressure_sum": math.fsum(acceptance_values),
            "chunk_index": chunk_index,
            "conditional_margin_pressure_sum": math.fsum(conditional_values),
            "eligible_rows": eligible_rows,
            "gradient_geometry": gradient_geometry,
            "greedy_families": dict(sorted(greedy_families.items())),
            "mean_max_conditional_probability": _mean(
                maximum_probabilities, "maximum conditional probabilities"
            ),
            "mean_normalized_take_entropy": _mean(
                normalized_entropies, "normalized take entropies"
            ),
            "mean_top_two_probability_gap": _mean(
                top_two_gaps, "top-two probability gaps"
            ),
            "scalar_components": scalar_components,
            "selected_families": dict(sorted(selected_families.items())),
            "selected_non_take_rows": selected_non_take_rows,
            "selected_take_rows": selected_take_rows,
            "take_tie_rows": take_ties,
            "total_decisions": total_chunk_decisions,
            "trajectories": len(trajectories),
            "unique_greedy_rows": unique_greedy_rows,
        }
        chunks.append(chunk_result)
        total_decisions += total_chunk_decisions
        total_trajectories += len(trajectories)
        total_card_rewards += eligible_rows

    if (
        len(chunks) != EXPECTED_CHUNKS
        or total_decisions != EXPECTED_DECISIONS
        or total_trajectories != EXPECTED_TRAJECTORIES
        or total_card_rewards != EXPECTED_CARD_REWARD_ROWS
    ):
        raise AuditError("sealed execution count mismatch")
    verdict, verdict_inputs = classify_verdict(chunks)
    return {
        "chunk_results": chunks,
        "execution_counts": {
            "card_reward_rows": total_card_rewards,
            "chunks": len(chunks),
            "decisions": total_decisions,
            "take_candidate_multiplicity": {
                str(key): value for key, value in sorted(multiplicity.items())
            },
            "trajectories": total_trajectories,
        },
        "exploratory_probe": dict(EXPLORATORY_PROBE),
        "windows": summarize_windows(chunks),
        "verdict": verdict,
        "verdict_inputs": verdict_inputs,
    }


def build_repository_audit(
    repo_root: Path | str, *, source_commit: str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    terminal_root = (root / DEFAULT_TERMINAL_ROOT).resolve()
    try:
        verification = baseline.verifier.verify_terminal_bundle(
            terminal_root, repo_root=root
        )
    except (OSError, baseline.verifier.VerifierError) as exc:
        raise AuditError(f"independent terminal verification failed: {exc}") from exc
    baseline.validate_verifier_result(verification)
    with baseline.hold_inactive_lease(terminal_root / ".execution.lease"):
        source = verify_pushed_source(root, source_commit)
        prior_json_path = baseline._regular_file(
            root / DEFAULT_PRIOR_JSON_PATH, "prior baseline-support JSON"
        )
        prior_markdown_path = baseline._regular_file(
            root / DEFAULT_PRIOR_MARKDOWN_PATH, "prior baseline-support Markdown"
        )
        prior_json_raw = prior_json_path.read_bytes()
        prior_markdown_raw = prior_markdown_path.read_bytes()
        prior = validate_prior_audit_bytes(prior_json_raw)
        if _digest(prior_markdown_raw) != EXPECTED_PRIOR_MARKDOWN_SHA256:
            raise AuditError("prior audit Markdown binding mismatch")

        postmortem_path = baseline._regular_file(
            root / DEFAULT_POSTMORTEM_PATH, "r2 postmortem"
        )
        postmortem_raw = postmortem_path.read_bytes()
        if _digest(postmortem_raw) != baseline.EXPECTED_POSTMORTEM_SHA256:
            raise AuditError("r2 postmortem binding mismatch")
        postmortem = parse_json_bytes(postmortem_raw, "r2 postmortem")
        if (
            postmortem.get("identity") != EXPECTED_IDENTITY
            or _mapping(
                postmortem.get("classification"), "classification"
            ).get("verdict")
            != EXPECTED_VERDICT
        ):
            raise AuditError("r2 postmortem identity mismatch")

        baseline._validate_snapshot(terminal_root)
        analysis = _analyze_chunks(terminal_root)
    forbidden = forbidden_loaded_modules()
    if forbidden:
        raise AuditError(f"forbidden modules loaded: {forbidden}")
    return {
        "authority": audit_authority(),
        "evidence": analysis,
        "identity": EXPECTED_IDENTITY,
        "input_bindings": {
            "prior_json": {
                "path": DEFAULT_PRIOR_JSON_PATH,
                "sha256": EXPECTED_PRIOR_JSON_SHA256,
                "size_bytes": len(prior_json_raw),
                "verdict": prior["verdict"],
            },
            "prior_markdown": {
                "path": DEFAULT_PRIOR_MARKDOWN_PATH,
                "sha256": EXPECTED_PRIOR_MARKDOWN_SHA256,
                "size_bytes": len(prior_markdown_raw),
            },
            "r2_postmortem": {
                "path": DEFAULT_POSTMORTEM_PATH,
                "sha256": baseline.EXPECTED_POSTMORTEM_SHA256,
                "size_bytes": len(postmortem_raw),
            },
            "terminal_manifest": {
                "manifest_sha256": EXPECTED_MANIFEST_SHA256,
                "terminal_sha256": EXPECTED_TERMINAL_SHA256,
            },
        },
        "limitations": list(LIMITATIONS),
        "schema_version": AUDIT_SCHEMA_VERSION,
        "scope": audit_scope(),
        "source": source,
        "terminal_verification": {
            "checkpoint_count": verification["checkpoint_count"],
            "completed_chunk_indices": verification["completed_chunk_indices"],
            "manifest_sha256": verification["manifest_sha256"],
            "terminal_sha256": verification["terminal_sha256"],
            "verdict": verification["verdict"],
        },
        "verdict": analysis["verdict"],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    verdict = str(report.get("verdict", "unknown"))
    evidence = report.get("evidence")
    if not isinstance(evidence, Mapping):
        return (
            "# Card Acceptance And Conditional Choice Audit\n\n"
            f"Verdict: `{verdict}`\n\n"
            "All downstream authority remains false.\n"
        )
    counts = _mapping(evidence.get("execution_counts"), "execution counts")
    verdict_inputs = _mapping(evidence.get("verdict_inputs"), "verdict inputs")
    chunks = list(_sequence(evidence.get("chunk_results"), "chunk results"))
    lines = [
        "# Card Acceptance And Conditional Choice Audit",
        "",
        "## Decision",
        "",
        f"The bounded descriptive verdict is `{verdict}`.",
        "It grants no training, evaluation, OPE, model loading, gameplay,",
        "qualification, promotion, policy-quality, causal, or formal-RL authority.",
        "",
        "## Verified Evidence",
        "",
        f"- Trajectories: {counts.get('trajectories', 'unknown')}",
        f"- Decisions: {counts.get('decisions', 'unknown')}",
        f"- Eligible card rewards: {counts.get('card_reward_rows', 'unknown')}",
        f"- Chunks: {counts.get('chunks', 'unknown')}",
        "",
        "## Mechanism Split",
        "",
        f"- Acceptance pressure consistent: `{verdict_inputs.get('acceptance_pressure_consistent')}`",
        f"- Conditional concentration progresses: `{verdict_inputs.get('conditional_concentration_progresses')}`",
        f"- Conditional pressure consistent: `{verdict_inputs.get('conditional_pressure_consistent')}`",
        f"- Support: `{verdict_inputs.get('support')}`",
        "",
        "| Chunk | Rows | Acceptance pressure | Conditional margin pressure | Normalized take entropy | Top-two gap |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for raw in chunks:
        chunk = _mapping(raw, "chunk")
        lines.append(
            "| {chunk} | {rows} | {acceptance:.15g} | {conditional:.15g} | "
            "{entropy:.15g} | {gap:.15g} |".format(
                chunk=chunk.get("chunk_index"),
                rows=chunk.get("eligible_rows"),
                acceptance=_finite(
                    chunk.get("acceptance_pressure_sum"), "acceptance pressure"
                ),
                conditional=_finite(
                    chunk.get("conditional_margin_pressure_sum"),
                    "conditional pressure",
                ),
                entropy=_finite(
                    chunk.get("mean_normalized_take_entropy"), "take entropy"
                ),
                gap=_finite(
                    chunk.get("mean_top_two_probability_gap"), "top-two gap"
                ),
            )
        )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "The conditional trend and row-local pressure are separate observations.",
            "Shared-parameter gradients cannot identify a candidate-score effect",
            "without retained per-row score Jacobians.",
            "",
            "## Next Gate",
            "",
            "Any objective, architecture, coefficient, experiment, evaluation, or",
            "live-policy change requires a separate reviewed proposal.",
            "",
        ]
    )
    return "\n".join(lines)


def _binding(raw: bytes) -> dict[str, Any]:
    return {"sha256": _digest(raw), "size_bytes": len(raw)}


def publish_reports(
    report: Mapping[str, Any],
    output_dir: Path | str,
    *,
    consumed_root: Path | str | None = None,
) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    if consumed_root is not None:
        consumed = Path(consumed_root).resolve()
        if output == consumed or output.is_relative_to(consumed):
            raise AuditError("output directory is inside consumed evidence")
    if output.exists():
        raise AuditError("output directory already exists")
    json_raw = canonical_json_bytes(dict(report))
    markdown_raw = render_markdown(report).encode("utf-8")
    if len(json_raw) > MAX_REPORT_BYTES or len(markdown_raw) > MAX_REPORT_BYTES:
        raise AuditError("report exceeds publication size bound")
    output.mkdir(parents=True)
    json_path = output / DEFAULT_JSON_NAME
    markdown_path = output / DEFAULT_MARKDOWN_NAME
    json_temp = output / f".{DEFAULT_JSON_NAME}.tmp"
    markdown_temp = output / f".{DEFAULT_MARKDOWN_NAME}.tmp"
    try:
        json_temp.write_bytes(json_raw)
        markdown_temp.write_bytes(markdown_raw)
        os.replace(json_temp, json_path)
        os.replace(markdown_temp, markdown_path)
    except OSError:
        for path in (json_temp, markdown_temp, json_path, markdown_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        try:
            output.rmdir()
        except OSError:
            pass
        raise
    return {"json": _binding(json_raw), "markdown": _binding(markdown_raw)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        report = build_repository_audit(
            arguments.repo_root, source_commit=arguments.source_commit
        )
        bindings = publish_reports(
            report,
            arguments.output_dir,
            consumed_root=arguments.repo_root / DEFAULT_TERMINAL_ROOT,
        )
    except (AuditError, OSError) as exc:
        print(f"audit blocked: {exc}", file=sys.stderr)
        return 2
    print(canonical_json_bytes(bindings).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
