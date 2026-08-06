"""Source-only advantage provenance and shared-gradient attribution contract."""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import torch

from analysis_scripts import noncombat_action_family_distribution as family_distribution
from analysis_scripts import noncombat_hierarchical_policy_objective as objective


CONTRACT_SCHEMA_VERSION = (
    "noncombat-hierarchical-advantage-attribution-contract-v1"
)
ADVANTAGE_SCHEMA_VERSION = "trajectory-disjoint-advantage-v1"
GRADIENT_SCHEMA_VERSION = "pre-clip-shared-parameter-attribution-v1"
FEATURE_SCHEMA_VERSION = "pre-decision-state-features-v1"
FEATURE_FIELDS = ("pre_decision_state_features",)
COMPONENT_NAMES = (
    "card_reward_family_policy",
    "card_reward_conditional_policy",
    "other_policy",
    "family_entropy_regularizer",
    "conditional_entropy_regularizer",
)
GRADIENT_NORM_CEILING = 1.0
CLIP_EPSILON = 1e-6
GRADIENT_ATOL = 1e-7
GRADIENT_RTOL = 1e-5
LOSS_ATOL = 1e-8
LOSS_RTOL = 1e-6

JSON_REPORT_PATH = (
    ROOT
    / "reports"
    / "noncombat_hierarchical_advantage_attribution_contract_20260806.json"
)
MARKDOWN_REPORT_PATH = (
    ROOT
    / "reports"
    / "noncombat_hierarchical_advantage_attribution_contract_20260806.md"
)

_ADVANTAGE_RECORD_FIELDS = {
    "baseline_fit_trajectory_ids",
    "baseline_mode",
    "baseline_prediction",
    "decision_id",
    "decision_index",
    "feature_fields",
    "feature_schema_version",
    "feature_sha256",
    "fold_id",
    "raw_return",
    "scale",
    "scale_fit_trajectory_ids",
    "scale_mode",
    "trajectory_id",
}
_AUTHORITY = {
    "baseline_fitting": False,
    "causal_claim": False,
    "checkpoint_loading": False,
    "cohort_materialization": False,
    "communication_mod": False,
    "environment_construction": False,
    "execution": False,
    "formal_rl": False,
    "gameplay": False,
    "model_loading": False,
    "native_loading": False,
    "ope": False,
    "optimizer_attribution": False,
    "policy_promotion": False,
    "qualification": False,
    "replay": False,
    "seed_access": False,
    "training": False,
}
_FUTURE_REGISTRATION_EVIDENCE = (
    "trajectory_fold_manifest",
    "baseline_fit_trajectory_manifest",
    "scale_fit_trajectory_manifest",
    "pre_decision_feature_schema_and_digest",
    "raw_return_baseline_scale_and_advantage",
    "ordered_parameter_names_shapes_and_dtypes",
    "five_raw_component_gradient_vectors",
    "independent_full_gradient_vector",
    "aggregate_first_clip_factor",
    "pre_and_post_clip_reconstruction_residuals",
    "exact_source_objective_optimizer_and_verifier_identity",
)


class AdvantageAttributionError(ValueError):
    """Raised when the source-only attribution boundary is invalid."""


@dataclass(frozen=True)
class AdvantageRecord:
    decision_id: str
    decision_index: int
    trajectory_id: str
    fold_id: str
    feature_schema_version: str
    feature_sha256: str
    feature_fields: tuple[str, ...]
    raw_return: float
    baseline_mode: str
    baseline_prediction: float
    baseline_fit_trajectory_ids: tuple[str, ...]
    baseline_fit_sha256: str
    scale_mode: str
    scale: float
    scale_fit_trajectory_ids: tuple[str, ...]
    scale_fit_sha256: str
    advantage: float
    confounding_reduction_claimed: bool


@dataclass(frozen=True)
class AdvantageBatch:
    records: tuple[AdvantageRecord, ...]
    fold_trajectories: tuple[tuple[str, tuple[str, ...]], ...]
    fold_manifest_sha256: str
    schema_version: str = ADVANTAGE_SCHEMA_VERSION


@dataclass(frozen=True)
class GradientLedger:
    component_names: tuple[str, ...]
    parameter_names: tuple[str, ...]
    parameter_shapes: tuple[tuple[int, ...], ...]
    component_vectors: Mapping[str, torch.Tensor]
    component_sum: torch.Tensor
    full_gradient: torch.Tensor
    component_norms: Mapping[str, float]
    pairwise_metrics: tuple[Mapping[str, Any], ...]
    pre_clip_norm: float
    clip_factor: float
    clipped_component_vectors: Mapping[str, torch.Tensor]
    clipped_component_sum: torch.Tensor
    clipped_full_gradient: torch.Tensor
    post_clip_norm: float
    pre_clip_reconstruction_max_abs: float
    post_clip_reconstruction_max_abs: float
    schema_version: str = GRADIENT_SCHEMA_VERSION


def canonical_json_bytes(value: Any) -> bytes:
    """Encode deterministic ASCII JSON with one trailing newline."""
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise AdvantageAttributionError("value is not canonical JSON") from exc
    return rendered.encode("ascii") + b"\n"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    return _sha256_bytes(canonical_json_bytes(value))


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AdvantageAttributionError(f"{label} must be a mapping")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise AdvantageAttributionError(f"{label} must be a sequence")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AdvantageAttributionError(f"{label} must be a nonempty string")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AdvantageAttributionError(f"{label} must be a nonnegative integer")
    return value


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdvantageAttributionError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise AdvantageAttributionError(f"{label} must be finite")
    return result


def _sha256(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AdvantageAttributionError(f"{label} must be lowercase sha256")
    return value


def _canonical_string_ids(
    value: Any,
    label: str,
    *,
    allow_empty: bool,
) -> tuple[str, ...]:
    values = tuple(
        _text(item, f"{label}[{index}]")
        for index, item in enumerate(_sequence(value, label))
    )
    if not values and not allow_empty:
        raise AdvantageAttributionError(f"{label} must be nonempty")
    if len(set(values)) != len(values):
        raise AdvantageAttributionError(f"{label} must contain unique identities")
    if values != tuple(sorted(values)):
        raise AdvantageAttributionError(f"{label} must use canonical order")
    return values


def _validate_fold_trajectories(
    value: Mapping[str, Sequence[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    source = _mapping(value, "fold_trajectories")
    if not source:
        raise AdvantageAttributionError("fold_trajectories must be nonempty")
    normalized: list[tuple[str, tuple[str, ...]]] = []
    seen: set[str] = set()
    for raw_fold_id in sorted(source):
        fold_id = _text(raw_fold_id, "fold_id")
        trajectories = _canonical_string_ids(
            source[raw_fold_id],
            f"fold {fold_id} trajectories",
            allow_empty=False,
        )
        overlap = seen.intersection(trajectories)
        if overlap:
            raise AdvantageAttributionError(
                "a trajectory must belong to exactly one fold"
            )
        seen.update(trajectories)
        normalized.append((fold_id, trajectories))
    return tuple(normalized)


def _validate_fit_ids(
    value: Any,
    label: str,
    *,
    data_derived: bool,
    known_trajectories: set[str],
    held_out_trajectories: set[str],
) -> tuple[str, ...]:
    identities = _canonical_string_ids(
        value,
        label,
        allow_empty=not data_derived,
    )
    if not data_derived:
        if identities:
            raise AdvantageAttributionError(
                f"{label} must be empty for a fixed mode"
            )
        return identities
    unknown = set(identities).difference(known_trajectories)
    if unknown:
        raise AdvantageAttributionError(
            f"{label} must reference a known trajectory"
        )
    if set(identities).intersection(held_out_trajectories):
        raise AdvantageAttributionError(
            f"{label} must exclude every held-out fold trajectory"
        )
    expected = known_trajectories.difference(held_out_trajectories)
    if set(identities) != expected:
        raise AdvantageAttributionError(
            f"{label} must contain the complete non-held-out trajectory set"
        )
    return identities


def build_advantage_batch(
    records: Sequence[Mapping[str, Any]],
    *,
    fold_trajectories: Mapping[str, Sequence[str]],
) -> AdvantageBatch:
    """Validate trajectory-disjoint provenance and compute supplied advantages."""
    source_records = _sequence(records, "records")
    if not source_records:
        raise AdvantageAttributionError("records must be nonempty")
    normalized_folds = _validate_fold_trajectories(fold_trajectories)
    fold_map = dict(normalized_folds)
    fold_by_trajectory = {
        trajectory_id: fold_id
        for fold_id, trajectory_ids in normalized_folds
        for trajectory_id in trajectory_ids
    }
    known_trajectories = set(fold_by_trajectory)
    seen_decision_ids: set[str] = set()
    observed_trajectories: set[str] = set()
    seen_fold_by_trajectory: dict[str, str] = {}
    indices_by_trajectory: dict[str, list[int]] = {}
    normalized_records: list[AdvantageRecord] = []

    for row_index, raw_record in enumerate(source_records):
        record = _mapping(raw_record, f"record[{row_index}]")
        if set(record) != _ADVANTAGE_RECORD_FIELDS:
            raise AdvantageAttributionError(
                f"record[{row_index}] fields must match the exact contract"
            )
        trajectory_id = _text(record["trajectory_id"], "trajectory_id")
        fold_id = _text(record["fold_id"], "fold_id")
        prior_fold = seen_fold_by_trajectory.get(trajectory_id)
        if prior_fold is not None and prior_fold != fold_id:
            raise AdvantageAttributionError(
                "every trajectory must use exactly one fold"
            )
        seen_fold_by_trajectory[trajectory_id] = fold_id
        if fold_id not in fold_map or trajectory_id not in fold_map[fold_id]:
            raise AdvantageAttributionError(
                "trajectory identity must belong to its declared fold"
            )
        observed_trajectories.add(trajectory_id)

        decision_id = _text(record["decision_id"], "decision_id")
        if decision_id in seen_decision_ids:
            raise AdvantageAttributionError("decision_id must be unique")
        seen_decision_ids.add(decision_id)
        decision_index = _nonnegative_int(
            record["decision_index"], "decision_index"
        )
        indices_by_trajectory.setdefault(trajectory_id, []).append(decision_index)

        feature_schema = _text(
            record["feature_schema_version"], "feature_schema_version"
        )
        if feature_schema != FEATURE_SCHEMA_VERSION:
            raise AdvantageAttributionError("feature schema version mismatch")
        feature_fields = tuple(
            _text(value, f"feature_fields[{index}]")
            for index, value in enumerate(
                _sequence(record["feature_fields"], "feature_fields")
            )
        )
        if feature_fields != FEATURE_FIELDS:
            raise AdvantageAttributionError(
                "feature fields must contain only pre-decision state features"
            )
        feature_sha256 = _sha256(record["feature_sha256"], "feature_sha256")

        raw_return = _finite(record["raw_return"], "raw_return")
        baseline_prediction = _finite(
            record["baseline_prediction"], "baseline_prediction"
        )
        scale = _finite(record["scale"], "scale")
        if scale <= 0.0:
            raise AdvantageAttributionError("scale must be positive")
        baseline_mode = _text(record["baseline_mode"], "baseline_mode")
        scale_mode = _text(record["scale_mode"], "scale_mode")
        if baseline_mode not in {"cross_fitted", "fixed_zero"}:
            raise AdvantageAttributionError("baseline_mode is invalid")
        if scale_mode not in {"cross_fitted", "fixed_unit"}:
            raise AdvantageAttributionError("scale_mode is invalid")
        if baseline_mode == "fixed_zero" and scale_mode != "fixed_unit":
            raise AdvantageAttributionError(
                "fixed_zero baseline requires fixed_unit scale_mode"
            )
        if baseline_mode == "fixed_zero" and baseline_prediction != 0.0:
            raise AdvantageAttributionError(
                "fixed_zero baseline_prediction must equal zero"
            )
        if scale_mode == "fixed_unit" and scale != 1.0:
            raise AdvantageAttributionError("fixed_unit scale must equal one")

        held_out = set(fold_map[fold_id])
        baseline_fit = _validate_fit_ids(
            record["baseline_fit_trajectory_ids"],
            "baseline fit identities",
            data_derived=baseline_mode == "cross_fitted",
            known_trajectories=known_trajectories,
            held_out_trajectories=held_out,
        )
        scale_fit = _validate_fit_ids(
            record["scale_fit_trajectory_ids"],
            "scale fit identities",
            data_derived=scale_mode == "cross_fitted",
            known_trajectories=known_trajectories,
            held_out_trajectories=held_out,
        )
        advantage = (raw_return - baseline_prediction) / scale
        if not math.isfinite(advantage):
            raise AdvantageAttributionError("advantage must remain finite")
        normalized_records.append(
            AdvantageRecord(
                decision_id=decision_id,
                decision_index=decision_index,
                trajectory_id=trajectory_id,
                fold_id=fold_id,
                feature_schema_version=feature_schema,
                feature_sha256=feature_sha256,
                feature_fields=feature_fields,
                raw_return=raw_return,
                baseline_mode=baseline_mode,
                baseline_prediction=baseline_prediction,
                baseline_fit_trajectory_ids=baseline_fit,
                baseline_fit_sha256=_canonical_sha256(list(baseline_fit)),
                scale_mode=scale_mode,
                scale=scale,
                scale_fit_trajectory_ids=scale_fit,
                scale_fit_sha256=_canonical_sha256(list(scale_fit)),
                advantage=advantage,
                confounding_reduction_claimed=False,
            )
        )

    if observed_trajectories != known_trajectories:
        raise AdvantageAttributionError(
            "records must cover every known trajectory in the fold manifest"
        )
    for trajectory_id, indices in indices_by_trajectory.items():
        if sorted(indices) != list(range(len(indices))):
            raise AdvantageAttributionError(
                f"trajectory {trajectory_id} decision indices must be contiguous"
            )
    fold_payload = {
        fold_id: list(trajectory_ids)
        for fold_id, trajectory_ids in normalized_folds
    }
    return AdvantageBatch(
        records=tuple(normalized_records),
        fold_trajectories=normalized_folds,
        fold_manifest_sha256=_canonical_sha256(fold_payload),
    )


def _validate_scalar(value: Any, label: str) -> torch.Tensor:
    if not isinstance(value, torch.Tensor) or value.ndim != 0:
        raise AdvantageAttributionError(f"{label} must be a scalar tensor")
    if value.device.type != "cpu" or not value.dtype.is_floating_point:
        raise AdvantageAttributionError(f"{label} must be a floating CPU tensor")
    if not torch.isfinite(value).item():
        raise AdvantageAttributionError(f"{label} must be finite")
    if not value.requires_grad:
        raise AdvantageAttributionError(f"{label} must remain gradient-connected")
    return value


def _validate_named_parameters(
    named_parameters: Sequence[tuple[str, torch.nn.Parameter]],
    parameter_order: Sequence[str],
) -> tuple[tuple[str, ...], tuple[torch.nn.Parameter, ...]]:
    order = tuple(
        _text(value, f"parameter_order[{index}]")
        for index, value in enumerate(_sequence(parameter_order, "parameter_order"))
    )
    if not order:
        raise AdvantageAttributionError("parameter order must be nonempty")
    if len(set(order)) != len(order):
        raise AdvantageAttributionError("parameter order must contain unique names")
    values = tuple(_sequence(named_parameters, "named_parameters"))
    if not values:
        raise AdvantageAttributionError("named_parameters must be nonempty")
    names: list[str] = []
    parameters: list[torch.nn.Parameter] = []
    for index, item in enumerate(values):
        pair = _sequence(item, f"named_parameters[{index}]")
        if len(pair) != 2:
            raise AdvantageAttributionError(
                "each named parameter must contain name and parameter"
            )
        name = _text(pair[0], f"named_parameters[{index}].name")
        parameter = pair[1]
        if not isinstance(parameter, torch.nn.Parameter):
            raise AdvantageAttributionError(
                f"parameter {name} must be a torch Parameter"
            )
        names.append(name)
        parameters.append(parameter)
    if len(set(names)) != len(names):
        raise AdvantageAttributionError("parameter names must be unique")
    if tuple(names) != order:
        raise AdvantageAttributionError("parameter order mismatch")
    if len({id(parameter) for parameter in parameters}) != len(parameters):
        raise AdvantageAttributionError("parameter identities must be unique")
    for name, parameter in zip(names, parameters, strict=True):
        if parameter.device.type != "cpu":
            raise AdvantageAttributionError(f"parameter {name} must remain on CPU")
        if parameter.dtype != torch.float32:
            raise AdvantageAttributionError(f"parameter {name} must be float32")
        if not parameter.requires_grad:
            raise AdvantageAttributionError(
                f"parameter {name} must require a gradient"
            )
        if not torch.isfinite(parameter).all().item():
            raise AdvantageAttributionError(f"parameter {name} must be finite")
    return tuple(names), tuple(parameters)


def _differentiate(
    scalar: torch.Tensor,
    parameters: tuple[torch.nn.Parameter, ...],
    label: str,
) -> torch.Tensor:
    try:
        gradients = torch.autograd.grad(
            scalar,
            parameters,
            retain_graph=True,
            allow_unused=True,
        )
    except RuntimeError as exc:
        raise AdvantageAttributionError(
            f"{label} gradient could not be reconstructed"
        ) from exc
    if all(gradient is None for gradient in gradients):
        raise AdvantageAttributionError(
            f"{label} must remain gradient-connected to a parameter"
        )
    flattened: list[torch.Tensor] = []
    for parameter, gradient in zip(parameters, gradients, strict=True):
        aligned = torch.zeros_like(parameter) if gradient is None else gradient
        if aligned.shape != parameter.shape or not torch.isfinite(aligned).all().item():
            raise AdvantageAttributionError(
                f"{label} gradient shape or finiteness mismatch"
            )
        flattened.append(aligned.detach().reshape(-1).to(dtype=torch.float64))
    return torch.cat(flattened)


def _vector_norm(value: torch.Tensor) -> float:
    result = float(torch.sqrt(torch.dot(value, value)).item())
    if not math.isfinite(result):
        raise AdvantageAttributionError("gradient norm must remain finite")
    return result


def _max_abs(left: torch.Tensor, right: torch.Tensor) -> float:
    if left.shape != right.shape:
        raise AdvantageAttributionError("gradient vector shape mismatch")
    return float(torch.max(torch.abs(left - right)).item())


def build_gradient_ledger(
    *,
    full_loss: torch.Tensor,
    components: Mapping[str, torch.Tensor],
    named_parameters: Sequence[tuple[str, torch.nn.Parameter]],
    parameter_order: Sequence[str],
) -> GradientLedger:
    """Reconstruct named pre-clip gradients and one aggregate clip factor."""
    source_components = _mapping(components, "components")
    actual_component_names = tuple(source_components)
    if set(actual_component_names) != set(COMPONENT_NAMES):
        raise AdvantageAttributionError("component identity mismatch")
    if actual_component_names != COMPONENT_NAMES:
        raise AdvantageAttributionError("component order mismatch")
    names, parameters = _validate_named_parameters(
        named_parameters, parameter_order
    )
    validated_full_loss = _validate_scalar(full_loss, "full loss")
    validated_components = OrderedDict(
        (
            name,
            _validate_scalar(source_components[name], f"component {name}"),
        )
        for name in COMPONENT_NAMES
    )
    component_loss_sum = next(iter(validated_components.values()))
    for component in tuple(validated_components.values())[1:]:
        component_loss_sum = component_loss_sum + component
    if not torch.allclose(
        validated_full_loss.detach().to(dtype=torch.float64),
        component_loss_sum.detach().to(dtype=torch.float64),
        atol=LOSS_ATOL,
        rtol=LOSS_RTOL,
    ):
        raise AdvantageAttributionError("full loss value differs from component sum")

    component_vectors = OrderedDict(
        (
            name,
            _differentiate(component, parameters, f"component {name}"),
        )
        for name, component in validated_components.items()
    )
    full_gradient = _differentiate(
        validated_full_loss, parameters, "full loss"
    )
    component_sum = torch.zeros_like(full_gradient)
    for vector in component_vectors.values():
        component_sum = component_sum + vector
    if not torch.allclose(
        component_sum,
        full_gradient,
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    ):
        raise AdvantageAttributionError(
            "component gradients do not reconstruct the full gradient"
        )
    pre_clip_error = _max_abs(component_sum, full_gradient)
    pre_clip_norm = _vector_norm(full_gradient)
    clip_factor = (
        1.0
        if pre_clip_norm <= GRADIENT_NORM_CEILING
        else GRADIENT_NORM_CEILING / (pre_clip_norm + CLIP_EPSILON)
    )
    clipped_components = OrderedDict(
        (name, vector * clip_factor)
        for name, vector in component_vectors.items()
    )
    clipped_component_sum = torch.zeros_like(full_gradient)
    for vector in clipped_components.values():
        clipped_component_sum = clipped_component_sum + vector
    clipped_full_gradient = full_gradient * clip_factor
    if not torch.allclose(
        clipped_component_sum,
        clipped_full_gradient,
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    ):
        raise AdvantageAttributionError(
            "clipped component gradients do not reconstruct the full gradient"
        )
    post_clip_error = _max_abs(
        clipped_component_sum, clipped_full_gradient
    )

    component_norms = OrderedDict(
        (name, _vector_norm(vector))
        for name, vector in component_vectors.items()
    )
    pairwise: list[Mapping[str, Any]] = []
    for left_index, left in enumerate(COMPONENT_NAMES):
        for right in COMPONENT_NAMES[left_index + 1 :]:
            dot = float(
                torch.dot(component_vectors[left], component_vectors[right]).item()
            )
            denominator = component_norms[left] * component_norms[right]
            cosine = None if denominator == 0.0 else dot / denominator
            pairwise.append(
                MappingProxyType(
                    {
                        "cosine": cosine,
                        "dot": dot,
                        "left": left,
                        "right": right,
                    }
                )
            )
    return GradientLedger(
        component_names=COMPONENT_NAMES,
        parameter_names=names,
        parameter_shapes=tuple(tuple(parameter.shape) for parameter in parameters),
        component_vectors=MappingProxyType(dict(component_vectors)),
        component_sum=component_sum,
        full_gradient=full_gradient,
        component_norms=MappingProxyType(dict(component_norms)),
        pairwise_metrics=tuple(pairwise),
        pre_clip_norm=pre_clip_norm,
        clip_factor=clip_factor,
        clipped_component_vectors=MappingProxyType(dict(clipped_components)),
        clipped_component_sum=clipped_component_sum,
        clipped_full_gradient=clipped_full_gradient,
        post_clip_norm=_vector_norm(clipped_full_gradient),
        pre_clip_reconstruction_max_abs=pre_clip_error,
        post_clip_reconstruction_max_abs=post_clip_error,
    )


class _TinySharedRanker(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.weight = torch.nn.Parameter(torch.zeros(1, dtype=torch.float32))

    def scores(self) -> torch.Tensor:
        return torch.stack((self.weight[0], self.weight[0] * 0.0))


def _candidate(action_id: str, kind: str) -> dict[str, str]:
    return {"action_id": action_id, "kind": kind}


def _gradient_case(*, opposing: bool) -> dict[str, Any]:
    ranker = _TinySharedRanker()
    candidates = (_candidate("take", "take"), _candidate("skip", "skip"))
    card_terms = objective.build_hierarchical_policy_terms(
        ranker.scores(), candidates, "take"
    )
    other_selected = "skip" if opposing else "take"
    other_advantage = 4.0 if opposing else 1.0
    other_terms = objective.build_hierarchical_policy_terms(
        ranker.scores(), candidates, other_selected
    )
    card_advantage = 1.0
    denominator = 2.0
    components = OrderedDict(
        (
            (
                "card_reward_family_policy",
                -card_terms.selected_family_log_probability
                * card_advantage
                / denominator,
            ),
            (
                "card_reward_conditional_policy",
                -card_terms.selected_conditional_log_probability
                * card_advantage
                / denominator,
            ),
            (
                "other_policy",
                -other_terms.selected_joint_log_probability
                * other_advantage
                / denominator,
            ),
            (
                "family_entropy_regularizer",
                -0.01
                * (card_terms.family_entropy + other_terms.family_entropy)
                / denominator,
            ),
            (
                "conditional_entropy_regularizer",
                -0.01
                * (
                    card_terms.conditional_entropy
                    + other_terms.conditional_entropy
                )
                / denominator,
            ),
        )
    )
    full_loss = (
        -(
            card_terms.selected_joint_log_probability * card_advantage
            + other_terms.selected_joint_log_probability * other_advantage
        )
        / denominator
        - 0.01
        * (card_terms.family_entropy + other_terms.family_entropy)
        / denominator
        - 0.01
        * (card_terms.conditional_entropy + other_terms.conditional_entropy)
        / denominator
    )
    ledger = build_gradient_ledger(
        full_loss=full_loss,
        components=components,
        named_parameters=(("weight", ranker.weight),),
        parameter_order=("weight",),
    )
    direct_gradient = torch.autograd.grad(
        components["card_reward_family_policy"],
        ranker.weight,
        retain_graph=True,
    )[0]
    direct_take_pressure = -float(direct_gradient[0].item())
    shared_probe_pressure = -float(ledger.full_gradient[0].item())
    return {
        "clip_factor": ledger.clip_factor,
        "component_gradients": {
            name: [float(value) for value in vector.tolist()]
            for name, vector in ledger.component_vectors.items()
        },
        "direct_take_pressure": direct_take_pressure,
        "full_gradient": [float(value) for value in ledger.full_gradient.tolist()],
        "other_selected_action": other_selected,
        "pre_clip_reconstruction_max_abs": (
            ledger.pre_clip_reconstruction_max_abs
        ),
        "shared_probe_pressure": shared_probe_pressure,
        "signs_disagree": (
            direct_take_pressure > 0.0 and shared_probe_pressure < 0.0
        ),
    }


def _tie_evidence() -> dict[str, Any]:
    within_scores = torch.tensor(
        [1.0, 1.0, 0.0], dtype=torch.float32, requires_grad=True
    )
    within_candidates = (
        _candidate("take-z", "take"),
        _candidate("take-a", "take"),
        _candidate("skip", "skip"),
    )
    within_terms = objective.build_hierarchical_policy_terms(
        within_scores, within_candidates, "skip"
    )
    within_distribution = family_distribution.build_action_family_distribution(
        within_scores, within_candidates
    )
    take_index = within_distribution.family_order.index("take")
    take_max_gradient = torch.autograd.grad(
        within_distribution.family_logits[take_index], within_scores
    )[0]

    across_scores = torch.tensor(
        [1.0, 1.0], dtype=torch.float32, requires_grad=True
    )
    across_candidates = (
        _candidate("take", "take"),
        _candidate("skip", "skip"),
    )
    across_terms = objective.build_hierarchical_policy_terms(
        across_scores, across_candidates, "take"
    )
    return {
        "across_family": {
            "score_greedy_action_ids": list(
                across_terms.score_greedy_action_ids
            ),
            "two_stage_score_greedy_action_ids": list(
                across_terms.two_stage_score_greedy_action_ids
            ),
        },
        "candidate_order_used_as_tie_break": False,
        "within_family": {
            "max_pool_score_gradient": [
                float(value) for value in take_max_gradient.tolist()
            ],
            "score_greedy_action_ids": list(
                within_terms.score_greedy_action_ids
            ),
            "two_stage_score_greedy_action_ids": list(
                within_terms.two_stage_score_greedy_action_ids
            ),
        },
    }


def _advantage_evidence() -> dict[str, Any]:
    folds = {
        "fold-a": ("trajectory-a0", "trajectory-a1"),
        "fold-b": ("trajectory-b0", "trajectory-b1"),
    }
    records: list[dict[str, Any]] = []
    returns = {
        "trajectory-a0": 3.0,
        "trajectory-a1": 5.0,
        "trajectory-b0": -1.0,
        "trajectory-b1": 1.0,
    }
    for fold_id, trajectory_ids in folds.items():
        fit_ids = folds["fold-b" if fold_id == "fold-a" else "fold-a"]
        for trajectory_id in trajectory_ids:
            records.append(
                {
                    "baseline_fit_trajectory_ids": list(fit_ids),
                    "baseline_mode": "cross_fitted",
                    "baseline_prediction": 1.0,
                    "decision_id": f"{trajectory_id}:decision-0",
                    "decision_index": 0,
                    "feature_fields": list(FEATURE_FIELDS),
                    "feature_schema_version": FEATURE_SCHEMA_VERSION,
                    "feature_sha256": _sha256_bytes(
                        f"{trajectory_id}:features".encode("ascii")
                    ),
                    "fold_id": fold_id,
                    "raw_return": returns[trajectory_id],
                    "scale": 2.0,
                    "scale_fit_trajectory_ids": list(fit_ids),
                    "scale_mode": "cross_fitted",
                    "trajectory_id": trajectory_id,
                }
            )
    batch = build_advantage_batch(records, fold_trajectories=folds)
    return {
        "advantages": [
            {
                "advantage": row.advantage,
                "baseline_fit_sha256": row.baseline_fit_sha256,
                "decision_id": row.decision_id,
                "fold_id": row.fold_id,
                "scale_fit_sha256": row.scale_fit_sha256,
                "trajectory_id": row.trajectory_id,
            }
            for row in batch.records
        ],
        "confounding_reduction_claimed": False,
        "fold_manifest_sha256": batch.fold_manifest_sha256,
        "formula": "(raw_return-baseline_prediction)/scale",
        "trajectory_count": len(batch.records),
    }


def contract_metadata() -> dict[str, Any]:
    """Return stable, JSON-compatible identity and no-authority metadata."""
    return {
        "advantage_formula": "(raw_return-baseline_prediction)/scale",
        "advantage_schema_version": ADVANTAGE_SCHEMA_VERSION,
        "authority": dict(_AUTHORITY),
        "clip_epsilon": CLIP_EPSILON,
        "clip_norm_ceiling": GRADIENT_NORM_CEILING,
        "clip_semantics": "aggregate-first-uniform-global-norm-v1",
        "component_names": list(COMPONENT_NAMES),
        "dependency_schema_versions": {
            "action_family_distribution": (
                family_distribution.distribution_metadata()["schema_version"]
            ),
            "hierarchical_policy_objective": (
                objective.objective_metadata()["schema_version"]
            ),
        },
        "feature_fields": list(FEATURE_FIELDS),
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "future_registration_evidence": list(_FUTURE_REGISTRATION_EVIDENCE),
        "gradient_schema_version": GRADIENT_SCHEMA_VERSION,
        "gradient_target": "pre-clip-model-parameter-gradient",
        "input_surface": {
            "checkpoints": False,
            "cohorts": False,
            "environments": False,
            "optimizer_state": False,
            "parameter_delta": False,
            "paths": False,
            "seeds": False,
        },
        "optimizer_attribution": False,
        "parameter_dtype": "float32",
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "tensor_device": "cpu",
    }


def build_design_evidence() -> dict[str, Any]:
    """Build deterministic synthetic evidence without empirical inputs."""
    return {
        "advantage_evidence": _advantage_evidence(),
        "limitations": [
            "Cross-fitting prevents held-out trajectory leakage but does not identify a causal card value.",
            "Pre-clip component gradients are not additive Adam updates or realized loss changes.",
            "Synthetic signs do not establish empirical policy quality.",
        ],
        "max_pool_tie_evidence": _tie_evidence(),
        "metadata": contract_metadata(),
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "synthetic_gradient_evidence": {
            "aligned": _gradient_case(opposing=False),
            "opposing": _gradient_case(opposing=True),
        },
    }


def _render_markdown(evidence: Mapping[str, Any]) -> bytes:
    gradients = evidence["synthetic_gradient_evidence"]
    advantage = evidence["advantage_evidence"]
    ties = evidence["max_pool_tie_evidence"]
    lines = [
        "# Hierarchical Advantage Attribution Contract",
        "",
        "## Boundary",
        "",
        "This is deterministic source-only design evidence. It authorizes no baseline fitting, model loading, training, seed access, gameplay, qualification, or promotion.",
        "",
        "## Advantage Provenance",
        "",
        f"- Trajectories: {advantage['trajectory_count']}",
        f"- Formula: `{advantage['formula']}`",
        f"- Fold manifest SHA-256: `{advantage['fold_manifest_sha256']}`",
        "- Causal or confounding-removal claim: `false`",
        "",
        "## Shared-Gradient Fixtures",
        "",
        "| Fixture | Direct take pressure | Shared probe pressure | Signs disagree |",
        "| --- | ---: | ---: | --- |",
    ]
    for name in ("aligned", "opposing"):
        row = gradients[name]
        lines.append(
            f"| {name} | {row['direct_take_pressure']:.9f} | "
            f"{row['shared_probe_pressure']:.9f} | "
            f"`{str(row['signs_disagree']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Max-Pool Ties",
            "",
            "- Within-family maxima: `"
            + "`, `".join(ties["within_family"]["score_greedy_action_ids"])
            + "`",
            "- Across-family maxima: `"
            + "`, `".join(ties["across_family"]["score_greedy_action_ids"])
            + "`",
            "- Candidate order used as tie-break: `false`",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {value}" for value in evidence["limitations"])
    lines.extend(["", "## Authority", ""])
    for name, value in sorted(evidence["metadata"]["authority"].items()):
        lines.append(f"- {name}: `{str(value).lower()}`")
    return ("\n".join(lines) + "\n").encode("ascii")


def render_design_report() -> tuple[bytes, bytes]:
    """Render canonical JSON and generated Markdown report bytes."""
    evidence = build_design_evidence()
    return canonical_json_bytes(evidence), _render_markdown(evidence)


def _write_atomic(destination: Path, payload: bytes) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)


def write_design_report() -> dict[str, str]:
    """Write the report only to its fixed repository-local publication paths."""
    json_bytes, markdown_bytes = render_design_report()
    _write_atomic(JSON_REPORT_PATH, json_bytes)
    _write_atomic(MARKDOWN_REPORT_PATH, markdown_bytes)
    return {
        "json_sha256": _sha256_bytes(json_bytes),
        "markdown_sha256": _sha256_bytes(markdown_bytes),
    }


def main() -> int:
    if len(sys.argv) != 1:
        raise AdvantageAttributionError("this source-only command accepts no arguments")
    summary = write_design_report()
    sys.stdout.write(canonical_json_bytes(summary).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
