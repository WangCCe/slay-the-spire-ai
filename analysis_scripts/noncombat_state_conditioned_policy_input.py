"""Validated separate policy inputs for state-conditioned non-combat ranking."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral
from types import SimpleNamespace
from typing import Any

import torch

from analysis_scripts.noncombat_policy_model import (
    FeatureConfig,
    candidate_feature_vector,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SimulatorAdapterError,
    TARGET_CATEGORIES,
    validate_candidates,
    validate_snapshot,
)
from analysis_scripts.noncombat_simulator_rl_experiment import (
    HASH_DIM as _EXPERIMENT_HASH_DIM,
    ExperimentBlocked,
    canonical_json_bytes,
    project_policy_view_v2,
)
from analysis_scripts.noncombat_state_conditioned_ranker import ARCHITECTURE_ID


POLICY_INPUT_SCHEMA_VERSION = "noncombat-state-conditioned-policy-input-v1"
PROJECTION_VERSION = "exact-api-v3-policy-projection-v1"
FEATURE_VERSION = "noncombat-state-conditioned-policy-features-v1"
HASH_DIM = _EXPERIMENT_HASH_DIM

_AUTHORITY = {
    "experiment_execution": False,
    "formal_rl": False,
    "gameplay": False,
    "model_loading": False,
    "native_loading": False,
    "policy_promotion": False,
    "qualification": False,
    "seed_access": False,
    "training": False,
}


class PolicyInputError(ValueError):
    """Raised when a state-conditioned policy input is incomplete or invalid."""


@dataclass(frozen=True)
class StateConditionedPolicyInput:
    """Separate state and candidate tensors for one validated decision."""

    state_features: torch.Tensor
    candidate_features: torch.Tensor


def policy_input_metadata() -> dict[str, Any]:
    """Return the stable, authority-free identity of this input boundary."""
    return {
        "architecture_id": ARCHITECTURE_ID,
        "authority": dict(_AUTHORITY),
        "channel_composition": "separate_state_and_candidate",
        "device": "cpu",
        "dtype": "float32",
        "feature_version": FEATURE_VERSION,
        "hash_dim": HASH_DIM,
        "projection_version": PROJECTION_VERSION,
        "schema_version": POLICY_INPUT_SCHEMA_VERSION,
    }


def _candidate_sequence(value: Any) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PolicyInputError("candidates must be a nonempty sequence")
    result = list(value)
    if not result:
        raise PolicyInputError("candidates must be nonempty")
    return result


def _validated_projection(
    snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate_values = _candidate_sequence(candidates)
    source_snapshot = copy.deepcopy(snapshot)
    source_candidates = copy.deepcopy(candidate_values)
    try:
        normalized_snapshot = validate_snapshot(copy.deepcopy(snapshot))
        if normalized_snapshot["adapter_api_version"] != ADAPTER_API_VERSION:
            raise PolicyInputError("policy input requires exact API v3")
        if normalized_snapshot["terminal"] is True:
            raise PolicyInputError("terminal snapshot cannot produce policy input")
        category = normalized_snapshot["category"]
        if category not in TARGET_CATEGORIES:
            raise PolicyInputError("snapshot category is not a target decision")
        normalized_candidates = validate_candidates(
            copy.deepcopy(candidate_values), category=category
        )
        projected = [
            project_policy_view_v2(normalized_snapshot, candidate)
            for candidate in normalized_candidates
        ]
        projected_state = projected[0]["state"]
        projected_state_bytes = canonical_json_bytes(projected_state)
        if any(
            canonical_json_bytes(row["state"]) != projected_state_bytes
            for row in projected[1:]
        ):
            raise PolicyInputError("projected state must match across candidates")
        if canonical_json_bytes(snapshot) != canonical_json_bytes(source_snapshot):
            raise PolicyInputError("policy projection mutated source snapshot")
        if canonical_json_bytes(candidate_values) != canonical_json_bytes(
            source_candidates
        ):
            raise PolicyInputError("policy projection mutated source candidates")
        return projected_state, [row["candidate"] for row in projected]
    except PolicyInputError:
        raise
    except (ExperimentBlocked, SimulatorAdapterError, TypeError, ValueError) as exc:
        raise PolicyInputError(str(exc)) from exc


def project_state_conditioned_policy_input(
    snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> StateConditionedPolicyInput:
    """Project one exact API v3 decision into separate deterministic tensors."""
    projected_state, projected_candidates = _validated_projection(
        snapshot, candidates
    )
    config = FeatureConfig(version=FEATURE_VERSION, hash_dim=HASH_DIM)
    try:
        state_features = candidate_feature_vector(
            SimpleNamespace(state=projected_state), {}, config
        )
        empty_state = SimpleNamespace(state={})
        candidate_features = torch.stack(
            [
                candidate_feature_vector(empty_state, candidate, config)
                for candidate in projected_candidates
            ]
        )
    except (TypeError, ValueError, RuntimeError) as exc:
        raise PolicyInputError(str(exc)) from exc
    if state_features.shape != (HASH_DIM,):
        raise PolicyInputError("state feature shape is invalid")
    if candidate_features.shape != (len(projected_candidates), HASH_DIM):
        raise PolicyInputError("candidate feature shape is invalid")
    for label, value in (
        ("state features", state_features),
        ("candidate features", candidate_features),
    ):
        if value.device.type != "cpu" or value.dtype != torch.float32:
            raise PolicyInputError(f"{label} must be CPU float32")
        if not torch.isfinite(value).all().item():
            raise PolicyInputError(f"{label} must be finite")
    return StateConditionedPolicyInput(
        state_features=state_features,
        candidate_features=candidate_features,
    )


def build_policy_diagnostic_row(
    *,
    decision_id: str,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    scores: torch.Tensor,
    selected_index: int,
) -> dict[str, Any]:
    """Build one validated scored-decision row for canonical diagnostics."""
    if not isinstance(decision_id, str) or not decision_id:
        raise PolicyInputError("decision_id must be a nonempty string")
    projected_state, projected_candidates = _validated_projection(
        snapshot, candidates
    )
    if not isinstance(scores, torch.Tensor) or scores.ndim != 1:
        raise PolicyInputError("scores must be a rank-1 tensor")
    if scores.device.type != "cpu" or scores.dtype != torch.float32:
        raise PolicyInputError("scores must be CPU float32")
    if scores.shape[0] != len(projected_candidates):
        raise PolicyInputError("score count must match candidate count")
    if not torch.isfinite(scores).all().item():
        raise PolicyInputError("scores must be finite")
    if (
        isinstance(selected_index, bool)
        or not isinstance(selected_index, Integral)
        or not 0 <= int(selected_index) < len(projected_candidates)
    ):
        raise PolicyInputError("selected_index must identify one candidate")

    candidate_rows = [
        {"action_id": candidate["action_id"], "kind": candidate["kind"]}
        for candidate in projected_candidates
    ]
    score_values = [float(value) for value in scores.tolist()]
    return {
        "candidate_scores": {
            candidate["action_id"]: score
            for candidate, score in zip(projected_candidates, score_values)
        },
        "candidates": candidate_rows,
        "category": projected_state["category"],
        "decision_id": decision_id,
        "selected_action_id": projected_candidates[int(selected_index)]["action_id"],
    }
