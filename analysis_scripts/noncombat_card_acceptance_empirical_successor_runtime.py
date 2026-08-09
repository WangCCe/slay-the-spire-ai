"""Torch runtime primitives for the card-acceptance empirical successor."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import copy
from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Integral, Real
import struct
import time
from typing import Any, Literal

import torch

from analysis_scripts import noncombat_formal_reward_contract as formal_reward_contract
from analysis_scripts import noncombat_simulator_adapter as simulator_adapter
from analysis_scripts.noncombat_hierarchical_advantage_attribution import (
    FEATURE_FIELDS,
    FEATURE_SCHEMA_VERSION,
    AdvantageAttributionError,
    AdvantageBatch,
    build_advantage_batch,
)
from analysis_scripts.noncombat_card_acceptance_objective import (
    CardAcceptanceObjectiveError,
    CardAcceptancePolicyTerms,
    build_card_acceptance_policy_terms,
)
from analysis_scripts.noncombat_card_acceptance_policy import (
    CardAcceptancePolicy,
    CardAcceptancePolicyError,
    CardAcceptancePolicyOutput,
    build_family_features,
)
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    HASH_DIM,
    PolicyInputError,
    project_state_conditioned_policy_input,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    DEFAULT_HIDDEN_DIM,
    StateConditionedCandidateRanker,
)


BOOTSTRAP_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-bootstrap-v1"
)
RUNTIME_METADATA_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-runtime-metadata-v1"
)
MODEL_SEED = 0
CARD_GENERATOR_SEED = 0
NONCARD_GENERATOR_SEED = 1
ENTROPY_COEFFICIENT = 0.01
LEARNING_RATE = 0.001
MAX_BOOTSTRAP_BYTES = 64 * 1024 * 1024
GRADIENT_RECONSTRUCTION_RTOL = 1e-6
GRADIENT_RECONSTRUCTION_ATOL = 1e-7
MAX_DECISIONS_PER_EPISODE = 500
MAX_CHARGED_SECONDS = 28_800.0
REGISTERED_SUPPORT_BLOCKERS = (
    "unsupported_shop_courier_restock_semantics",
)
BASELINE_FEATURE_SCHEMA_VERSION = "cross-fitted-baseline-state-features-v1"
BASELINE_FEATURE_DIM = 128
BASELINE_SOURCE_DIM = HASH_DIM
FOLD_COUNT = 4
TRAJECTORIES_PER_CHUNK = 64
HELD_OUT_TRAJECTORIES_PER_FOLD = 16
FIT_TRAJECTORIES_PER_FOLD = 48
RIDGE_COEFFICIENT = 0.001
RIDGE_RESIDUAL_ATOL = 1e-9
RIDGE_RESIDUAL_RTOL = 1e-9
PREDICTION_MIN = 0.0
PREDICTION_MAX = 3.0
ArmName = Literal["candidate", "control"]

_REGISTERED_ADAM_OPTIONS: dict[str, Any] = {
    "amsgrad": False,
    "betas": (0.9, 0.999),
    "capturable": False,
    "differentiable": False,
    "eps": 1e-8,
    "foreach": False,
    "fused": False,
    "lr": LEARNING_RATE,
    "maximize": False,
    "weight_decay": 0.0,
}


class SuccessorRuntimeError(ValueError):
    """Raised when the empirical-successor runtime contract is invalid."""


@dataclass(frozen=True)
class CandidateArm:
    card_policy: CardAcceptancePolicy
    frozen_noncard_ranker: StateConditionedCandidateRanker


@dataclass(frozen=True)
class ControlArm:
    shared_card_ranker: StateConditionedCandidateRanker
    frozen_noncard_ranker: StateConditionedCandidateRanker


@dataclass(frozen=True)
class PairedBootstrap:
    candidate: CandidateArm
    control: ControlArm
    generators: dict[str, torch.Generator]


@dataclass(frozen=True)
class ArmOptimizers:
    candidate: torch.optim.Adam
    control: torch.optim.Adam


@dataclass(frozen=True)
class ArmCardRewardObjective:
    card_decision_count: int
    family_policy_loss: torch.Tensor
    conditional_policy_loss: torch.Tensor
    family_entropy_loss: torch.Tensor
    conditional_entropy_loss: torch.Tensor
    total_loss: torch.Tensor


@dataclass(frozen=True)
class ArmOptimizerStepEvidence:
    component_order: tuple[str, ...]
    component_gradients: tuple[tuple[torch.Tensor | None, ...], ...]
    combined_gradients: tuple[torch.Tensor, ...]
    applied_gradients: tuple[torch.Tensor, ...]
    preclip_global_norm: float
    postclip_global_norm: float
    optimizer_state_before: dict[str, Any]
    optimizer_state_after: dict[str, Any]


@dataclass(frozen=True)
class ArmRolloutDecision:
    arm: ArmName
    category: str
    decision_id: str
    decision_index: int
    selected_action_id: str
    state_features: torch.Tensor
    card_terms: CardAcceptancePolicyTerms | None
    diagnostic: Mapping[str, Any]


@dataclass(frozen=True)
class ArmEpisodeRollout:
    arm: ArmName
    seed: int
    trajectory_id: str
    decisions: tuple[ArmRolloutDecision, ...]
    transitions: tuple[dict[str, Any], ...]
    rewards: tuple[float, ...]
    final_snapshot: dict[str, Any]
    floor_progress: float
    terminal_victory: int
    unsupported_reason: str | None


@dataclass(frozen=True)
class PairedEpisodeRollout:
    seed: int
    candidate: ArmEpisodeRollout
    control: ArmEpisodeRollout


@dataclass(frozen=True)
class ArmBaselineDecision:
    arm: ArmName
    category: str
    decision_id: str
    decision_index: int
    raw_return: float
    reward: float
    seed: int
    state_features: torch.Tensor
    trajectory_id: str


@dataclass(frozen=True)
class RidgeFoldModel:
    fold_id: str
    fit_trajectory_ids: tuple[str, ...]
    held_out_trajectory_ids: tuple[str, ...]
    coefficients: tuple[float, ...]
    kkt_residuals: tuple[float, ...]
    rhs: tuple[float, ...]
    absolute_product_sums: tuple[float, ...]


@dataclass(frozen=True)
class ArmBaselinePrediction:
    decision_id: str
    fold_id: str
    trajectory_id: str
    unclipped: float
    clipped: float
    was_clipped: bool
    preclip_little_endian_hex: str
    feature_sha256: str


@dataclass(frozen=True)
class ArmCrossFittedBaseline:
    arm: ArmName
    decisions: tuple[ArmBaselineDecision, ...]
    fold_trajectories: Mapping[str, tuple[str, ...]]
    models: tuple[RidgeFoldModel, ...]
    predictions: tuple[ArmBaselinePrediction, ...]
    advantage_batch: AdvantageBatch


@dataclass(frozen=True)
class PairedCrossFittedBaselines:
    seeds: tuple[int, ...]
    candidate: ArmCrossFittedBaseline
    control: ArmCrossFittedBaseline


_DTYPES: dict[str, torch.dtype] = {
    "bool": torch.bool,
    "float32": torch.float32,
    "float64": torch.float64,
    "int32": torch.int32,
    "int64": torch.int64,
    "uint8": torch.uint8,
}


def runtime_metadata() -> dict[str, Any]:
    """Return fresh runtime-owned metadata matching the source-only contract."""
    return {
        "algorithm": {
            "conditional_entropy_coefficient": ENTROPY_COEFFICIENT,
            "discount": 1.0,
            "family_entropy_coefficient": ENTROPY_COEFFICIENT,
            "gradient_norm_ceiling": 1.0,
            "learning_rate": LEARNING_RATE,
            "model_seed": MODEL_SEED,
            "optimizer": "adam",
            "optimizer_amsgrad": False,
            "optimizer_betas": [0.9, 0.999],
            "optimizer_eps": 1e-8,
            "optimizer_weight_decay": 0.0,
        },
        "architecture": {
            "candidate": "disjoint-family-and-conditional-heads",
            "control": "shared-card-ranker",
            "frozen_noncard_rankers": 2,
            "matched_rankers": 5,
        },
        "authority": {
            name: False
            for name in (
                "causal",
                "communication_mod",
                "environment_construction",
                "evaluation",
                "execution",
                "formal_rl",
                "gameplay",
                "model_fitting",
                "native_loading",
                "ope",
                "production_model_loading",
                "promotion",
                "qualification",
                "seed_access",
                "training",
            )
        },
        "baseline": {
            "feature_dim": BASELINE_FEATURE_DIM,
            "fit_trajectories_per_fold": FIT_TRAJECTORIES_PER_FOLD,
            "fold_count": FOLD_COUNT,
            "held_out_trajectories_per_fold": HELD_OUT_TRAJECTORIES_PER_FOLD,
            "prediction_bounds": [PREDICTION_MIN, PREDICTION_MAX],
            "ridge_coefficient": RIDGE_COEFFICIENT,
            "ridge_residual_atol": RIDGE_RESIDUAL_ATOL,
            "ridge_residual_rtol": RIDGE_RESIDUAL_RTOL,
            "scale": 1.0,
            "solver": "cpu-float64-cholesky-v1",
            "source_dim": BASELINE_SOURCE_DIM,
            "trajectory_weighting": "equal-trajectory-mean-squared-error-v1",
        },
        "device": "cpu",
        "dtype": "float32",
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "optimizer": {
            "amsgrad": False,
            "betas": [0.9, 0.999],
            "eps": 1e-8,
            "learning_rate": LEARNING_RATE,
            "name": "adam",
            "weight_decay": 0.0,
        },
        "schema_version": RUNTIME_METADATA_SCHEMA_VERSION,
    }


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SuccessorRuntimeError(f"duplicate checkpoint field: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise SuccessorRuntimeError(f"checkpoint constant is invalid: {value}")


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise SuccessorRuntimeError("checkpoint is not canonical JSON") from exc


def _rankers(bootstrap: PairedBootstrap) -> tuple[StateConditionedCandidateRanker, ...]:
    return (
        bootstrap.candidate.card_policy.family_head,
        bootstrap.candidate.card_policy.conditional_ranker,
        bootstrap.candidate.frozen_noncard_ranker,
        bootstrap.control.shared_card_ranker,
        bootstrap.control.frozen_noncard_ranker,
    )


def _new_ranker() -> StateConditionedCandidateRanker:
    return StateConditionedCandidateRanker(HASH_DIM, DEFAULT_HIDDEN_DIM)


def _new_generator(seed: int) -> torch.Generator:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return generator


def build_matched_bootstrap() -> PairedBootstrap:
    """Build five storage-disjoint rankers copied from one seed-zero base."""
    ambient_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(torch.float32)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(MODEL_SEED)
            base = _new_ranker()
            base_state = {
                name: value.detach().clone()
                for name, value in base.state_dict().items()
            }
            bootstrap = PairedBootstrap(
                candidate=CandidateArm(
                    card_policy=CardAcceptancePolicy(HASH_DIM, DEFAULT_HIDDEN_DIM),
                    frozen_noncard_ranker=_new_ranker(),
                ),
                control=ControlArm(
                    shared_card_ranker=_new_ranker(),
                    frozen_noncard_ranker=_new_ranker(),
                ),
                generators={
                    "candidate_card": _new_generator(CARD_GENERATOR_SEED),
                    "candidate_noncard": _new_generator(NONCARD_GENERATOR_SEED),
                    "control_card": _new_generator(CARD_GENERATOR_SEED),
                    "control_noncard": _new_generator(NONCARD_GENERATOR_SEED),
                },
            )
    finally:
        torch.set_default_dtype(ambient_dtype)

    for ranker in _rankers(bootstrap):
        ranker.load_state_dict(base_state, strict=True)
    for ranker in (
        bootstrap.candidate.frozen_noncard_ranker,
        bootstrap.control.frozen_noncard_ranker,
    ):
        ranker.requires_grad_(False)
        ranker.eval()
    return bootstrap


def _encode_tensor(value: torch.Tensor) -> dict[str, Any]:
    if not isinstance(value, torch.Tensor):
        raise SuccessorRuntimeError("tensor encoding requires a tensor")
    tensor = value.detach().cpu().contiguous()
    dtype_name = str(tensor.dtype).removeprefix("torch.")
    if dtype_name not in _DTYPES:
        raise SuccessorRuntimeError(f"unsupported tensor dtype: {dtype_name}")
    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
        raise SuccessorRuntimeError("checkpoint tensors must be finite")
    return {
        "dtype": dtype_name,
        "shape": list(tensor.shape),
        "values": tensor.reshape(-1).tolist(),
    }


def _decode_tensor(value: object, label: str) -> torch.Tensor:
    if not isinstance(value, Mapping) or set(value) != {"dtype", "shape", "values"}:
        raise SuccessorRuntimeError(f"{label} tensor fields differ")
    dtype_name = value["dtype"]
    if not isinstance(dtype_name, str) or dtype_name not in _DTYPES:
        raise SuccessorRuntimeError(f"{label} tensor dtype is unsupported")
    raw_shape = value["shape"]
    if isinstance(raw_shape, (str, bytes)) or not isinstance(raw_shape, Sequence):
        raise SuccessorRuntimeError(f"{label} tensor shape is invalid")
    shape: list[int] = []
    for index, dimension in enumerate(raw_shape):
        if (
            isinstance(dimension, bool)
            or not isinstance(dimension, Integral)
            or int(dimension) < 0
        ):
            raise SuccessorRuntimeError(
                f"{label} tensor shape[{index}] is invalid"
            )
        shape.append(int(dimension))
    raw_values = value["values"]
    if isinstance(raw_values, (str, bytes)) or not isinstance(raw_values, Sequence):
        raise SuccessorRuntimeError(f"{label} tensor values are invalid")
    expected_count = math.prod(shape) if shape else 1
    if len(raw_values) != expected_count:
        raise SuccessorRuntimeError(f"{label} tensor value count differs")
    try:
        tensor = torch.tensor(
            list(raw_values), dtype=_DTYPES[dtype_name], device="cpu"
        ).reshape(tuple(shape))
    except (TypeError, ValueError, RuntimeError) as exc:
        raise SuccessorRuntimeError(f"{label} tensor decode failed") from exc
    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
        raise SuccessorRuntimeError(f"{label} tensor must be finite")
    return tensor


def _encode_model_state(model: torch.nn.Module) -> dict[str, Any]:
    return {
        name: _encode_tensor(tensor)
        for name, tensor in sorted(model.state_dict().items())
    }


def _restore_model_state(
    model: torch.nn.Module, value: object, label: str
) -> None:
    if not isinstance(value, Mapping):
        raise SuccessorRuntimeError(f"{label} must be a mapping")
    expected = tuple(sorted(model.state_dict()))
    if tuple(sorted(value)) != expected:
        raise SuccessorRuntimeError(f"{label} state keys differ")
    expected_state = model.state_dict()
    state: dict[str, torch.Tensor] = {}
    for name in expected:
        tensor = _decode_tensor(value[name], f"{label}.{name}")
        registered = expected_state[name]
        if tensor.dtype != registered.dtype:
            raise SuccessorRuntimeError(
                f"{label}.{name} dtype must equal {registered.dtype}"
            )
        if tensor.shape != registered.shape:
            raise SuccessorRuntimeError(f"{label}.{name} shape differs")
        if tensor.device != registered.device:
            raise SuccessorRuntimeError(f"{label}.{name} device differs")
        state[name] = tensor
    try:
        model.load_state_dict(state, strict=True)
    except RuntimeError as exc:
        raise SuccessorRuntimeError(f"{label} state is incompatible") from exc


def _paired_bootstrap_object(bootstrap: PairedBootstrap) -> dict[str, Any]:
    """Build the canonical plain-object representation of paired state."""
    if not isinstance(bootstrap, PairedBootstrap):
        raise SuccessorRuntimeError("paired bootstrap has an invalid type")
    expected_generators = (
        "candidate_card",
        "candidate_noncard",
        "control_card",
        "control_noncard",
    )
    if tuple(bootstrap.generators) != expected_generators:
        raise SuccessorRuntimeError("paired bootstrap generators differ")
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "architecture": {
            "hidden_dim": DEFAULT_HIDDEN_DIM,
            "input_dim": HASH_DIM,
            "model_seed": MODEL_SEED,
        },
        "models": {
            "candidate": {
                "conditional_ranker": _encode_model_state(
                    bootstrap.candidate.card_policy.conditional_ranker
                ),
                "family_head": _encode_model_state(
                    bootstrap.candidate.card_policy.family_head
                ),
                "frozen_noncard_ranker": _encode_model_state(
                    bootstrap.candidate.frozen_noncard_ranker
                ),
            },
            "control": {
                "frozen_noncard_ranker": _encode_model_state(
                    bootstrap.control.frozen_noncard_ranker
                ),
                "shared_card_ranker": _encode_model_state(
                    bootstrap.control.shared_card_ranker
                ),
            },
        },
        "generators": {
            name: _encode_tensor(bootstrap.generators[name].get_state())
            for name in expected_generators
        },
    }


def encode_paired_bootstrap(bootstrap: PairedBootstrap) -> bytes:
    """Encode all model and generator state as bounded canonical bytes."""
    payload = _canonical_json_bytes(_paired_bootstrap_object(bootstrap))
    if len(payload) > MAX_BOOTSTRAP_BYTES:
        raise SuccessorRuntimeError("paired bootstrap exceeds its byte ceiling")
    return payload


def restore_paired_bootstrap(value: object) -> PairedBootstrap:
    """Restore the exact inverse of :func:`encode_paired_bootstrap`."""
    if not isinstance(value, bytes) or not value or len(value) > MAX_BOOTSTRAP_BYTES:
        raise SuccessorRuntimeError("paired bootstrap bytes are invalid")
    try:
        decoded_text = value.decode("ascii")
        parsed = json.loads(
            decoded_text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SuccessorRuntimeError("paired bootstrap JSON is invalid") from exc
    if _canonical_json_bytes(parsed) != value:
        raise SuccessorRuntimeError("paired bootstrap bytes are not canonical")
    if not isinstance(parsed, Mapping) or set(parsed) != {
        "schema_version",
        "architecture",
        "models",
        "generators",
    }:
        raise SuccessorRuntimeError("paired bootstrap fields differ")
    value = parsed
    if value["schema_version"] != BOOTSTRAP_SCHEMA_VERSION:
        raise SuccessorRuntimeError("paired bootstrap schema differs")
    if value["architecture"] != {
        "hidden_dim": DEFAULT_HIDDEN_DIM,
        "input_dim": HASH_DIM,
        "model_seed": MODEL_SEED,
    }:
        raise SuccessorRuntimeError("paired bootstrap architecture differs")
    models = value["models"]
    generators = value["generators"]
    if not isinstance(models, Mapping) or set(models) != {"candidate", "control"}:
        raise SuccessorRuntimeError("paired bootstrap model fields differ")
    candidate_models = models["candidate"]
    control_models = models["control"]
    if not isinstance(candidate_models, Mapping) or set(candidate_models) != {
        "conditional_ranker",
        "family_head",
        "frozen_noncard_ranker",
    }:
        raise SuccessorRuntimeError("candidate model fields differ")
    if not isinstance(control_models, Mapping) or set(control_models) != {
        "frozen_noncard_ranker",
        "shared_card_ranker",
    }:
        raise SuccessorRuntimeError("control model fields differ")
    expected_generators = {
        "candidate_card",
        "candidate_noncard",
        "control_card",
        "control_noncard",
    }
    if not isinstance(generators, Mapping) or set(generators) != expected_generators:
        raise SuccessorRuntimeError("paired bootstrap generator fields differ")

    bootstrap = build_matched_bootstrap()
    _restore_model_state(
        bootstrap.candidate.card_policy.family_head,
        candidate_models["family_head"],
        "candidate.family_head",
    )
    _restore_model_state(
        bootstrap.candidate.card_policy.conditional_ranker,
        candidate_models["conditional_ranker"],
        "candidate.conditional_ranker",
    )
    _restore_model_state(
        bootstrap.candidate.frozen_noncard_ranker,
        candidate_models["frozen_noncard_ranker"],
        "candidate.frozen_noncard_ranker",
    )
    _restore_model_state(
        bootstrap.control.shared_card_ranker,
        control_models["shared_card_ranker"],
        "control.shared_card_ranker",
    )
    _restore_model_state(
        bootstrap.control.frozen_noncard_ranker,
        control_models["frozen_noncard_ranker"],
        "control.frozen_noncard_ranker",
    )
    for name in bootstrap.generators:
        state = _decode_tensor(generators[name], f"generators.{name}")
        if state.dtype != torch.uint8 or state.ndim != 1:
            raise SuccessorRuntimeError(f"generator {name} state is invalid")
        try:
            bootstrap.generators[name].set_state(state)
        except RuntimeError as exc:
            raise SuccessorRuntimeError(f"generator {name} state is invalid") from exc
    return bootstrap


def _validated_arm(value: object) -> ArmName:
    if value not in {"candidate", "control"}:
        raise SuccessorRuntimeError("arm must equal candidate or control")
    return value  # type: ignore[return-value]


def _control_card_output(
    ranker: StateConditionedCandidateRanker,
    state_features: torch.Tensor,
    candidate_features: torch.Tensor,
    candidates: Sequence[Mapping[str, Any]],
) -> CardAcceptancePolicyOutput:
    family_batch = build_family_features(
        candidate_features, candidates, category="card_reward"
    )
    conditional_logits = ranker(state_features, candidate_features)
    family_logits = ranker(state_features, family_batch.family_features)
    if family_batch.family_order == ("take",):
        acceptance_active = False
        acceptance_coordinate = None
    else:
        take_index = family_batch.family_order.index("take")
        non_take_indices = torch.tensor(
            [
                index
                for index in range(len(family_batch.family_order))
                if index != take_index
            ],
            dtype=torch.long,
            device="cpu",
        )
        logits64 = family_logits.to(dtype=torch.float64)
        acceptance_active = True
        acceptance_coordinate = logits64[take_index] - torch.logsumexp(
            logits64.index_select(0, non_take_indices), dim=0
        )
    return CardAcceptancePolicyOutput(
        family_batch=family_batch,
        conditional_logits=conditional_logits,
        family_logits=family_logits,
        acceptance_active=acceptance_active,
        acceptance_coordinate=acceptance_coordinate,
    )


def forward_card_policy(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    state_features: torch.Tensor,
    candidate_features: torch.Tensor,
    candidates: Sequence[Mapping[str, Any]],
) -> CardAcceptancePolicyOutput:
    """Route card rewards through candidate dual heads or the control shared head."""
    normalized_arm = _validated_arm(arm)
    if normalized_arm == "candidate":
        return bootstrap.candidate.card_policy(
            state_features,
            candidate_features,
            candidates,
            category="card_reward",
        )
    return _control_card_output(
        bootstrap.control.shared_card_ranker,
        state_features,
        candidate_features,
        candidates,
    )


def build_arm_card_reward_objective(
    rows: Sequence[tuple[CardAcceptancePolicyTerms, Real]],
) -> ArmCardRewardObjective:
    """Build the registered four-component, decision-mean card objective."""
    normalized_rows = tuple(rows)
    if not normalized_rows:
        raise SuccessorRuntimeError("card reward objective requires decisions")
    for index, (terms, advantage) in enumerate(normalized_rows):
        if not isinstance(terms, CardAcceptancePolicyTerms):
            raise SuccessorRuntimeError(f"row {index} policy terms are invalid")
        if (
            isinstance(advantage, bool)
            or not isinstance(advantage, Real)
            or not math.isfinite(float(advantage))
        ):
            raise SuccessorRuntimeError(f"row {index} advantage must be finite")

    family_policy_loss = torch.stack(
        [
            -advantage * terms.selected_family_log_probability
            for terms, advantage in normalized_rows
        ]
    ).mean()
    conditional_policy_loss = torch.stack(
        [
            -advantage * terms.selected_conditional_log_probability
            for terms, advantage in normalized_rows
        ]
    ).mean()
    family_entropy_loss = -ENTROPY_COEFFICIENT * torch.stack(
        [terms.family_entropy for terms, _ in normalized_rows]
    ).mean()
    conditional_entropy_loss = -ENTROPY_COEFFICIENT * torch.stack(
        [
            terms.per_family_conditional_entropies.mean()
            for terms, _ in normalized_rows
        ]
    ).mean()
    total_loss = (
        family_policy_loss
        + conditional_policy_loss
        + family_entropy_loss
        + conditional_entropy_loss
    )
    return ArmCardRewardObjective(
        card_decision_count=len(normalized_rows),
        family_policy_loss=family_policy_loss,
        conditional_policy_loss=conditional_policy_loss,
        family_entropy_loss=family_entropy_loss,
        conditional_entropy_loss=conditional_entropy_loss,
        total_loss=total_loss,
    )


def build_arm_optimizers(bootstrap: PairedBootstrap) -> ArmOptimizers:
    """Build one fixed Adam group for each arm's trainable card parameters."""
    candidate_parameters = tuple(
        bootstrap.candidate.card_policy.family_head.parameters()
    ) + tuple(bootstrap.candidate.card_policy.conditional_ranker.parameters())
    control_parameters = tuple(bootstrap.control.shared_card_ranker.parameters())
    return ArmOptimizers(
        candidate=torch.optim.Adam(candidate_parameters, **_REGISTERED_ADAM_OPTIONS),
        control=torch.optim.Adam(control_parameters, **_REGISTERED_ADAM_OPTIONS),
    )


def _validated_registered_adam(
    optimizer: torch.optim.Optimizer,
) -> tuple[torch.nn.Parameter, ...]:
    if type(optimizer) is not torch.optim.Adam:
        raise SuccessorRuntimeError("optimizer must be the registered Adam type")
    if len(optimizer.param_groups) != 1:
        raise SuccessorRuntimeError("registered Adam must have one parameter group")
    group = optimizer.param_groups[0]
    for key, expected in _REGISTERED_ADAM_OPTIONS.items():
        if group.get(key) != expected or optimizer.defaults.get(key) != expected:
            raise SuccessorRuntimeError(f"registered Adam option {key} differs")
    parameters = tuple(group.get("params", ()))
    if not parameters or any(
        not isinstance(parameter, torch.nn.Parameter) for parameter in parameters
    ):
        raise SuccessorRuntimeError("registered Adam parameters are invalid")
    if len({id(parameter) for parameter in parameters}) != len(parameters):
        raise SuccessorRuntimeError("registered Adam parameter order is not unique")
    for parameter in parameters:
        if parameter.device.type != "cpu" or parameter.dtype != torch.float32:
            raise SuccessorRuntimeError(
                "registered Adam parameters must remain CPU float32"
            )
        if not parameter.requires_grad:
            raise SuccessorRuntimeError(
                "registered Adam cannot own a frozen parameter"
            )
    return parameters


def _encode_state_value(value: Any) -> dict[str, Any]:
    if isinstance(value, torch.Tensor):
        return {"type": "tensor", "value": _encode_tensor(value)}
    if isinstance(value, tuple):
        return {
            "type": "tuple",
            "items": [_encode_state_value(item) for item in value],
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "items": [_encode_state_value(item) for item in value],
        }
    if isinstance(value, Mapping):
        items = [
            {"key": _encode_state_value(key), "value": _encode_state_value(item)}
            for key, item in value.items()
        ]
        items.sort(
            key=lambda item: json.dumps(
                item["key"],
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return {"type": "mapping", "items": items}
    if value is None or isinstance(value, (bool, int, str)):
        return {"type": "scalar", "value": value}
    if isinstance(value, Real):
        converted = float(value)
        if not math.isfinite(converted):
            raise SuccessorRuntimeError("optimizer scalar must be finite")
        return {"type": "scalar", "value": converted}
    raise SuccessorRuntimeError(
        f"unsupported optimizer state type: {type(value).__name__}"
    )


def _decode_state_value(value: object, label: str) -> Any:
    if not isinstance(value, Mapping):
        raise SuccessorRuntimeError(f"{label} must be a mapping")
    state_type = value.get("type")
    if state_type == "tensor" and set(value) == {"type", "value"}:
        return _decode_tensor(value["value"], f"{label}.value")
    if state_type in {"tuple", "list"} and set(value) == {"type", "items"}:
        items = value["items"]
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise SuccessorRuntimeError(f"{label}.items must be a sequence")
        decoded = [
            _decode_state_value(item, f"{label}.items[{index}]")
            for index, item in enumerate(items)
        ]
        return tuple(decoded) if state_type == "tuple" else decoded
    if state_type == "mapping" and set(value) == {"type", "items"}:
        items = value["items"]
        if isinstance(items, (str, bytes)) or not isinstance(items, Sequence):
            raise SuccessorRuntimeError(f"{label}.items must be a sequence")
        decoded_mapping: dict[Any, Any] = {}
        for index, item in enumerate(items):
            item_label = f"{label}.items[{index}]"
            if not isinstance(item, Mapping) or set(item) != {"key", "value"}:
                raise SuccessorRuntimeError(f"{item_label} fields differ")
            key = _decode_state_value(item["key"], f"{item_label}.key")
            if key in decoded_mapping:
                raise SuccessorRuntimeError(f"{label} contains a duplicate key")
            decoded_mapping[key] = _decode_state_value(
                item["value"], f"{item_label}.value"
            )
        return decoded_mapping
    if state_type == "scalar" and set(value) == {"type", "value"}:
        scalar = value["value"]
        if scalar is not None and not isinstance(scalar, (bool, int, float, str)):
            raise SuccessorRuntimeError(f"{label} scalar is invalid")
        if isinstance(scalar, float) and not math.isfinite(scalar):
            raise SuccessorRuntimeError(f"{label} scalar must be finite")
        return scalar
    raise SuccessorRuntimeError(f"{label} state fields differ")


def encode_optimizer_state(optimizer: torch.optim.Optimizer) -> dict[str, Any]:
    """Encode Adam state without pickle while preserving tuple and key types."""
    _validated_registered_adam(optimizer)
    return _encode_state_value(optimizer.state_dict())


def _validate_decoded_adam_state(
    optimizer: torch.optim.Adam,
    decoded: dict[str, Any],
) -> None:
    expected = optimizer.state_dict()
    if decoded["param_groups"] != expected["param_groups"]:
        raise SuccessorRuntimeError(
            "optimizer parameter order or registered option differs"
        )
    state = decoded["state"]
    if not isinstance(state, dict):
        raise SuccessorRuntimeError("optimizer state entries must be a mapping")

    parameters = _validated_registered_adam(optimizer)
    parameter_indexes = tuple(expected["param_groups"][0]["params"])
    if len(parameter_indexes) != len(parameters):
        raise SuccessorRuntimeError("optimizer parameter order differs")
    parameter_by_index = dict(zip(parameter_indexes, parameters, strict=True))
    if any(
        isinstance(index, bool)
        or not isinstance(index, int)
        or index not in parameter_by_index
        for index in state
    ):
        raise SuccessorRuntimeError("optimizer state parameter index differs")

    expected_state_keys = {"step", "exp_avg", "exp_avg_sq"}
    for index, entry in state.items():
        if not isinstance(entry, dict) or set(entry) != expected_state_keys:
            raise SuccessorRuntimeError("optimizer Adam moment fields differ")
        parameter = parameter_by_index[index]
        step = entry["step"]
        if (
            not isinstance(step, torch.Tensor)
            or step.device.type != "cpu"
            or step.dtype != torch.float32
            or step.shape != torch.Size([])
            or not bool(torch.isfinite(step).item())
        ):
            raise SuccessorRuntimeError("optimizer Adam step tensor differs")
        for name in ("exp_avg", "exp_avg_sq"):
            moment = entry[name]
            if (
                not isinstance(moment, torch.Tensor)
                or moment.device != parameter.device
                or moment.dtype != parameter.dtype
                or moment.shape != parameter.shape
                or not bool(torch.isfinite(moment).all().item())
            ):
                raise SuccessorRuntimeError(
                    f"optimizer Adam {name} tensor differs"
                )


def restore_optimizer_state(
    optimizer: torch.optim.Optimizer, value: object
) -> torch.optim.Optimizer:
    """Restore optimizer moments encoded by :func:`encode_optimizer_state`."""
    _validated_registered_adam(optimizer)
    decoded = _decode_state_value(value, "optimizer state")
    if not isinstance(decoded, dict) or set(decoded) != {"param_groups", "state"}:
        raise SuccessorRuntimeError("optimizer state keys differ")
    _validate_decoded_adam_state(optimizer, decoded)
    try:
        optimizer.load_state_dict(decoded)
    except (TypeError, ValueError, RuntimeError) as exc:
        raise SuccessorRuntimeError("optimizer state is incompatible") from exc
    _validated_registered_adam(optimizer)
    return optimizer


def _global_gradient_norm(gradients: Sequence[torch.Tensor]) -> float:
    if not gradients:
        raise SuccessorRuntimeError("optimizer step requires gradients")
    norm = torch.linalg.vector_norm(
        torch.stack(
            [torch.linalg.vector_norm(gradient.detach(), 2) for gradient in gradients]
        ),
        2,
    )
    if not bool(torch.isfinite(norm).item()):
        raise SuccessorRuntimeError("optimizer gradient norm must be finite")
    return float(norm.item())


def apply_arm_optimizer_step(
    optimizer: torch.optim.Optimizer,
    objective: ArmCardRewardObjective,
    *,
    parameters: Sequence[torch.nn.Parameter],
) -> ArmOptimizerStepEvidence:
    """Validate, reconstruct, globally clip, and apply one registered arm step."""
    registered_parameters = _validated_registered_adam(optimizer)
    supplied_parameters = tuple(parameters)
    if len(supplied_parameters) != len(registered_parameters) or any(
        supplied is not registered
        for supplied, registered in zip(
            supplied_parameters, registered_parameters, strict=True
        )
    ):
        raise SuccessorRuntimeError("optimizer parameter order differs")
    if not isinstance(objective, ArmCardRewardObjective):
        raise SuccessorRuntimeError("optimizer objective type differs")
    if objective.card_decision_count <= 0:
        raise SuccessorRuntimeError("optimizer objective has no card decisions")

    component_order = (
        "family_policy",
        "conditional_policy",
        "family_entropy",
        "conditional_entropy",
    )
    components = (
        objective.family_policy_loss,
        objective.conditional_policy_loss,
        objective.family_entropy_loss,
        objective.conditional_entropy_loss,
    )
    losses = components + (objective.total_loss,)
    for loss in losses:
        if (
            not isinstance(loss, torch.Tensor)
            or loss.device.type != "cpu"
            or not loss.is_floating_point()
            or loss.shape != torch.Size([])
            or not bool(torch.isfinite(loss).item())
        ):
            raise SuccessorRuntimeError(
                "optimizer objective scalars must be finite CPU floating point"
            )
    reconstructed_loss = components[0]
    for component in components[1:]:
        reconstructed_loss = reconstructed_loss + component
    if not torch.equal(reconstructed_loss, objective.total_loss):
        raise SuccessorRuntimeError("optimizer objective reconstruction differs")

    raw_component_gradients = tuple(
        torch.autograd.grad(
            component,
            registered_parameters,
            allow_unused=True,
            retain_graph=True,
        )
        for component in components
    )
    total_gradients = torch.autograd.grad(
        objective.total_loss,
        registered_parameters,
        allow_unused=True,
    )
    component_gradients = tuple(
        tuple(
            None
            if gradient is None
            else gradient.detach().to(dtype=torch.float64).clone()
            for gradient in gradients
        )
        for gradients in raw_component_gradients
    )
    combined_gradients: list[torch.Tensor] = []
    for parameter_index, parameter in enumerate(registered_parameters):
        combined = torch.zeros_like(parameter, dtype=torch.float64)
        for raw_gradients, evidence_gradients in zip(
            raw_component_gradients, component_gradients, strict=True
        ):
            gradient = raw_gradients[parameter_index]
            if gradient is not None:
                if (
                    gradient.device != parameter.device
                    or gradient.dtype != parameter.dtype
                    or gradient.shape != parameter.shape
                    or not bool(torch.isfinite(gradient).all().item())
                ):
                    raise SuccessorRuntimeError(
                        "optimizer component gradient contract differs"
                    )
                evidence_gradient = evidence_gradients[parameter_index]
                if evidence_gradient is None:
                    raise SuccessorRuntimeError(
                        "optimizer component gradient evidence differs"
                    )
                combined = combined + evidence_gradient
        total = total_gradients[parameter_index]
        if total is None or not torch.allclose(
            combined,
            total.detach().to(dtype=torch.float64),
            rtol=GRADIENT_RECONSTRUCTION_RTOL,
            atol=GRADIENT_RECONSTRUCTION_ATOL,
        ):
            raise SuccessorRuntimeError(
                "optimizer total gradient reconstruction differs"
            )
        combined_gradients.append(combined.detach().clone())

    optimizer_state_before = encode_optimizer_state(optimizer)
    optimizer.zero_grad(set_to_none=True)
    for parameter, gradient in zip(
        registered_parameters, combined_gradients, strict=True
    ):
        parameter.grad = gradient.to(dtype=parameter.dtype).clone()
    preclip_global_norm = float(
        torch.nn.utils.clip_grad_norm_(registered_parameters, 1.0).item()
    )
    if not math.isfinite(preclip_global_norm):
        raise SuccessorRuntimeError("optimizer preclip gradient norm must be finite")
    applied_gradients = tuple(
        parameter.grad.detach().clone()
        for parameter in registered_parameters
        if parameter.grad is not None
    )
    if len(applied_gradients) != len(registered_parameters):
        raise SuccessorRuntimeError("optimizer clipped gradient coverage differs")
    postclip_global_norm = _global_gradient_norm(applied_gradients)
    if postclip_global_norm > 1.0 + 1e-6:
        raise SuccessorRuntimeError("optimizer gradient clipping ceiling exceeded")
    optimizer.step()
    optimizer_state_after = encode_optimizer_state(optimizer)

    return ArmOptimizerStepEvidence(
        component_order=component_order,
        component_gradients=component_gradients,
        combined_gradients=tuple(combined_gradients),
        applied_gradients=applied_gradients,
        preclip_global_norm=preclip_global_norm,
        postclip_global_norm=postclip_global_norm,
        optimizer_state_before=optimizer_state_before,
        optimizer_state_after=optimizer_state_after,
    )


def select_two_stage_action(
    terms: CardAcceptancePolicyTerms,
    *,
    generator: torch.Generator | None = None,
    greedy: bool,
) -> str:
    """Select a family first, then one candidate within that family."""
    if not isinstance(terms, CardAcceptancePolicyTerms):
        raise SuccessorRuntimeError("card policy terms are invalid")
    if not isinstance(greedy, bool):
        raise SuccessorRuntimeError("greedy must be boolean")

    if greedy:
        selected_family = terms.unique_greedy_family_id
        if selected_family is None:
            raise SuccessorRuntimeError("family maximum tie has no unique choice")
        action_ids = dict(terms.greedy_action_ids_by_family)[selected_family]
        if len(action_ids) != 1:
            raise SuccessorRuntimeError(
                "conditional maximum tie has no unique choice"
            )
        return action_ids[0]

    if not isinstance(generator, torch.Generator) or generator.device.type != "cpu":
        raise SuccessorRuntimeError("card generator must remain on CPU")
    family_index = int(
        torch.multinomial(
            terms.family_probabilities,
            1,
            generator=generator,
        ).item()
    )
    selected_family = terms.family_order[family_index]
    candidate_indices = tuple(
        index
        for index, family in enumerate(terms.candidate_families)
        if family == selected_family
    )
    index_tensor = torch.tensor(candidate_indices, dtype=torch.long, device="cpu")
    local_probabilities = terms.conditional_probabilities.index_select(
        0, index_tensor
    )
    local_index = int(
        torch.multinomial(
            local_probabilities,
            1,
            generator=generator,
        ).item()
    )
    return terms.action_ids[candidate_indices[local_index]]


def score_noncard_candidates(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    category: str,
    state_features: torch.Tensor,
    candidate_features: torch.Tensor,
) -> torch.Tensor:
    """Route non-card categories only through the selected arm's frozen ranker."""
    normalized_arm = _validated_arm(arm)
    if category == "card_reward":
        raise SuccessorRuntimeError("card_reward must use the card policy")
    if not isinstance(category, str) or not category:
        raise SuccessorRuntimeError("non-card category must be nonempty")
    ranker = (
        bootstrap.candidate.frozen_noncard_ranker
        if normalized_arm == "candidate"
        else bootstrap.control.frozen_noncard_ranker
    )
    return ranker(state_features, candidate_features)


def _generator_state_sha256(generator: torch.Generator) -> str:
    state = generator.get_state()
    return hashlib.sha256(bytes(state.tolist())).hexdigest()


def _arm_generator(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    card: bool,
) -> torch.Generator:
    name = f"{arm}_{'card' if card else 'noncard'}"
    generator = bootstrap.generators.get(name)
    if not isinstance(generator, torch.Generator) or generator.device.type != "cpu":
        raise SuccessorRuntimeError(f"generator {name} must remain on CPU")
    return generator


def _environment_state(
    environment: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for method_name in ("snapshot", "legal_actions", "clone", "step"):
        if not callable(getattr(environment, method_name, None)):
            raise SuccessorRuntimeError(
                f"environment.{method_name} must be callable"
            )
    try:
        snapshot = simulator_adapter.validate_snapshot(environment.snapshot())
        if snapshot["adapter_api_version"] != simulator_adapter.ADAPTER_API_VERSION:
            raise SuccessorRuntimeError("environment must expose exact adapter API v3")
        candidates = simulator_adapter.validate_candidates(
            environment.legal_actions(), category=snapshot["category"]
        )
    except simulator_adapter.SimulatorAdapterError as exc:
        raise SuccessorRuntimeError(str(exc)) from exc
    except SuccessorRuntimeError:
        raise
    except Exception as exc:
        raise SuccessorRuntimeError("environment state access failed") from exc
    return snapshot, candidates


def _assert_source_unchanged(
    environment: Any,
    expected_snapshot: Mapping[str, Any],
    expected_candidates: Sequence[Mapping[str, Any]],
) -> None:
    try:
        actual_snapshot = environment.snapshot()
        actual_candidates = environment.legal_actions()
    except Exception as exc:
        raise SuccessorRuntimeError(
            "source environment could not be re-read"
        ) from exc
    if simulator_adapter.canonical_json_bytes(actual_snapshot) != (
        simulator_adapter.canonical_json_bytes(expected_snapshot)
    ) or simulator_adapter.canonical_json_bytes(actual_candidates) != (
        simulator_adapter.canonical_json_bytes(list(expected_candidates))
    ):
        raise SuccessorRuntimeError(
            "cloned action application mutated the source environment"
        )


def _validate_transition(
    transition: Any,
    *,
    before: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    selected_action_id: str,
    after: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(transition, Mapping):
        raise SuccessorRuntimeError("transition must be a mapping")
    value = dict(transition)
    if value.get("selected_action_id") != selected_action_id:
        raise SuccessorRuntimeError("transition selected action differs")
    if value.get("category") != before["category"]:
        raise SuccessorRuntimeError("transition category differs")
    if simulator_adapter.canonical_json_bytes(value.get("candidate_actions")) != (
        simulator_adapter.canonical_json_bytes(list(candidates))
    ):
        raise SuccessorRuntimeError("transition candidate order differs")
    if simulator_adapter.canonical_json_bytes(value.get("source_state")) != (
        simulator_adapter.canonical_json_bytes(before["state"])
    ):
        raise SuccessorRuntimeError("transition source state differs")
    successor = value.get("successor")
    expected_successor = {
        "category": after["category"],
        "state": after["state"],
        "terminal": after["terminal"],
    }
    if not isinstance(successor, Mapping) or (
        simulator_adapter.canonical_json_bytes(dict(successor))
        != simulator_adapter.canonical_json_bytes(expected_successor)
    ):
        raise SuccessorRuntimeError("transition successor differs")
    return value


def _model_state_bytes(model: torch.nn.Module) -> bytes:
    return (
        json.dumps(
            _encode_model_state(model),
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        + b"\n"
    )


def _validate_rollout_bootstrap(bootstrap: PairedBootstrap) -> None:
    _paired_bootstrap_object(bootstrap)
    frozen_rankers = (
        bootstrap.candidate.frozen_noncard_ranker,
        bootstrap.control.frozen_noncard_ranker,
    )
    if _model_state_bytes(frozen_rankers[0]) != _model_state_bytes(
        frozen_rankers[1]
    ):
        raise SuccessorRuntimeError("frozen non-card ranker bytes differ")
    storage_pointers: set[int] = set()
    for ranker in _rankers(bootstrap):
        for parameter in ranker.parameters():
            if parameter.device.type != "cpu" or parameter.dtype != torch.float32:
                raise SuccessorRuntimeError(
                    "rollout ranker parameters must remain CPU float32"
                )
            pointer = parameter.untyped_storage().data_ptr()
            if pointer in storage_pointers:
                raise SuccessorRuntimeError(
                    "rollout ranker parameter storage must remain disjoint"
                )
            storage_pointers.add(pointer)
    for ranker in frozen_rankers:
        if ranker.training or any(
            parameter.requires_grad for parameter in ranker.parameters()
        ):
            raise SuccessorRuntimeError(
                "frozen non-card rankers must remain eval and gradient disabled"
            )


def _sample_arm_training_decision(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    seed: int,
    decision_index: int,
) -> ArmRolloutDecision:
    try:
        policy_input = project_state_conditioned_policy_input(snapshot, candidates)
    except PolicyInputError as exc:
        raise SuccessorRuntimeError(str(exc)) from exc

    decision_id = f"{arm}:seed-{seed}:decision-{decision_index}"
    category = snapshot["category"]
    if category not in simulator_adapter.TARGET_CATEGORIES:
        raise SuccessorRuntimeError("nonterminal episode category is unsupported")
    if category == "card_reward":
        generator = _arm_generator(bootstrap, arm=arm, card=True)
        before_generator = _generator_state_sha256(generator)
        try:
            output = forward_card_policy(
                bootstrap,
                arm=arm,
                state_features=policy_input.state_features,
                candidate_features=policy_input.candidate_features,
                candidates=candidates,
            )
            provisional = build_card_acceptance_policy_terms(
                output.family_logits,
                output.conditional_logits,
                candidates,
                str(candidates[0]["action_id"]),
                category="card_reward",
            )
            selected_action_id = select_two_stage_action(
                provisional,
                generator=generator,
                greedy=False,
            )
            terms = build_card_acceptance_policy_terms(
                output.family_logits,
                output.conditional_logits,
                candidates,
                selected_action_id,
                category="card_reward",
            )
        except (
            CardAcceptanceObjectiveError,
            CardAcceptancePolicyError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            raise SuccessorRuntimeError(str(exc)) from exc
        diagnostic: dict[str, Any] = {
            "action_generator_state_sha256": {
                "after": _generator_state_sha256(generator),
                "before": before_generator,
            },
            "category": category,
            "decision_id": decision_id,
            "decision_index": decision_index,
            "family_order": list(terms.family_order),
            "family_probabilities": {
                family: float(terms.family_probabilities[index].detach().item())
                for index, family in enumerate(terms.family_order)
            },
            "multi_family": len(terms.family_order) > 1,
            "selected_action_id": selected_action_id,
            "selected_family": terms.selected_family,
            "selection_mode": "family-first-then-conditional-v1",
            "unique_greedy_family_id": terms.unique_greedy_family_id,
        }
        card_terms: CardAcceptancePolicyTerms | None = terms
    else:
        generator = _arm_generator(bootstrap, arm=arm, card=False)
        before_generator = _generator_state_sha256(generator)
        try:
            scores = score_noncard_candidates(
                bootstrap,
                arm=arm,
                category=str(category),
                state_features=policy_input.state_features,
                candidate_features=policy_input.candidate_features,
            )
            probabilities = torch.softmax(scores, dim=0)
            if not bool(torch.isfinite(probabilities).all().item()):
                raise SuccessorRuntimeError(
                    "non-card probabilities must be finite"
                )
            selected_index = int(
                torch.multinomial(
                    probabilities.detach(), 1, generator=generator
                ).item()
            )
        except (RuntimeError, TypeError, ValueError) as exc:
            raise SuccessorRuntimeError(str(exc)) from exc
        selected_action_id = str(candidates[selected_index]["action_id"])
        diagnostic = {
            "action_generator_state_sha256": {
                "after": _generator_state_sha256(generator),
                "before": before_generator,
            },
            "candidate_probabilities": {
                str(candidate["action_id"]): float(
                    probabilities[index].detach().item()
                )
                for index, candidate in enumerate(candidates)
            },
            "candidate_scores": {
                str(candidate["action_id"]): float(scores[index].detach().item())
                for index, candidate in enumerate(candidates)
            },
            "category": category,
            "decision_id": decision_id,
            "decision_index": decision_index,
            "selected_action_id": selected_action_id,
            "selection_mode": "frozen-raw-score-softmax-v1",
        }
        card_terms = None

    return ArmRolloutDecision(
        arm=arm,
        category=str(category),
        decision_id=decision_id,
        decision_index=decision_index,
        selected_action_id=selected_action_id,
        state_features=policy_input.state_features.detach().clone(),
        card_terms=card_terms,
        diagnostic=diagnostic,
    )


def rollout_arm_training_episode(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    environment_factory: Callable[[int], Any],
    seed: int,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> ArmEpisodeRollout:
    """Run one clone-only arm trajectory with card-only trainable routing."""
    normalized_arm = _validated_arm(arm)
    _validate_rollout_bootstrap(bootstrap)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise SuccessorRuntimeError("episode seed must be a nonnegative integer")
    if (
        isinstance(max_decisions, bool)
        or not isinstance(max_decisions, int)
        or not 0 < max_decisions <= MAX_DECISIONS_PER_EPISODE
    ):
        raise SuccessorRuntimeError("episode decision ceiling is invalid")
    if not callable(environment_factory) or not callable(clock):
        raise SuccessorRuntimeError(
            "episode environment factory and clock must be callable"
        )
    now = float(clock())
    active_deadline = now + MAX_CHARGED_SECONDS if deadline is None else float(deadline)
    if (
        not math.isfinite(now)
        or not math.isfinite(active_deadline)
        or active_deadline < now
        or active_deadline > now + MAX_CHARGED_SECONDS
    ):
        raise SuccessorRuntimeError("episode deadline exceeds the registered bound")
    if float(clock()) > active_deadline:
        raise SuccessorRuntimeError(
            "wall-time limit reached before environment construction"
        )
    try:
        environment = environment_factory(seed)
    except Exception as exc:
        raise SuccessorRuntimeError("environment construction failed") from exc
    root_environment = environment
    root_snapshot, root_candidates = _environment_state(root_environment)
    frozen_ranker = (
        bootstrap.candidate.frozen_noncard_ranker
        if normalized_arm == "candidate"
        else bootstrap.control.frozen_noncard_ranker
    )
    frozen_before = _model_state_bytes(frozen_ranker)

    decisions: list[ArmRolloutDecision] = []
    transitions: list[dict[str, Any]] = []
    rewards: list[float] = []
    floor_progress = 0.0
    terminal_victory = 0
    unsupported_reason: str | None = None
    while True:
        if float(clock()) > active_deadline:
            raise SuccessorRuntimeError("wall-time limit reached before decision")
        snapshot, candidates = _environment_state(environment)
        if snapshot["terminal"]:
            break
        if len(decisions) >= max_decisions:
            raise SuccessorRuntimeError("episode decision ceiling reached")
        decision = _sample_arm_training_decision(
            bootstrap,
            arm=normalized_arm,
            snapshot=snapshot,
            candidates=candidates,
            seed=seed,
            decision_index=len(decisions),
        )
        source_snapshot = copy.deepcopy(snapshot)
        source_candidates = copy.deepcopy(candidates)
        try:
            successor = environment.clone()
        except Exception as exc:
            raise SuccessorRuntimeError("environment clone failed") from exc
        if successor is environment:
            raise SuccessorRuntimeError(
                "environment clone must return a distinct branch"
            )
        _assert_source_unchanged(environment, source_snapshot, source_candidates)
        try:
            transition = successor.step(decision.selected_action_id)
            after = simulator_adapter.validate_snapshot(successor.snapshot())
        except RuntimeError as exc:
            reason = str(exc)
            if reason not in REGISTERED_SUPPORT_BLOCKERS:
                raise SuccessorRuntimeError(
                    f"unregistered simulator support blocker: {reason}"
                ) from exc
            _assert_source_unchanged(
                environment, source_snapshot, source_candidates
            )
            unsupported_reason = reason
            decisions.append(decision)
            rewards.append(0.0)
            break
        except simulator_adapter.SimulatorAdapterError as exc:
            raise SuccessorRuntimeError(str(exc)) from exc
        except Exception as exc:
            raise SuccessorRuntimeError("cloned action application failed") from exc
        if after["adapter_api_version"] != simulator_adapter.ADAPTER_API_VERSION:
            raise SuccessorRuntimeError(
                "successor branch drifted from exact adapter API v3"
            )
        _assert_source_unchanged(environment, source_snapshot, source_candidates)
        normalized_transition = _validate_transition(
            transition,
            before=snapshot,
            candidates=candidates,
            selected_action_id=decision.selected_action_id,
            after=after,
        )
        try:
            channels = formal_reward_contract.reward_channels(
                normalized_transition
            )
            formal_reward_contract.validate_scalarization(
                "strict_primary_dominance", victory_weight=2.0
            )
        except formal_reward_contract.RewardContractBlocked as exc:
            raise SuccessorRuntimeError(str(exc)) from exc
        reward = 2.0 * float(channels["terminal_victory"]) + float(
            channels["floor_progress"]
        )
        if not math.isfinite(reward):
            raise SuccessorRuntimeError("formal reward must be finite")
        decisions.append(decision)
        transitions.append(normalized_transition)
        rewards.append(reward)
        floor_progress += float(channels["floor_progress"])
        terminal_victory = max(
            terminal_victory, int(channels["terminal_victory"])
        )
        environment = successor

    _assert_source_unchanged(root_environment, root_snapshot, root_candidates)
    try:
        final_snapshot = simulator_adapter.validate_snapshot(environment.snapshot())
    except simulator_adapter.SimulatorAdapterError as exc:
        raise SuccessorRuntimeError(str(exc)) from exc
    if unsupported_reason is None:
        if final_snapshot["terminal"] is not True:
            raise SuccessorRuntimeError("supported episode did not terminate")
        if final_snapshot["state"].get("outcome") not in {
            "player_loss",
            "player_victory",
        }:
            raise SuccessorRuntimeError("terminal episode outcome is invalid")
    if not decisions:
        raise SuccessorRuntimeError(
            "training episode must contain at least one decision"
        )
    _validate_rollout_bootstrap(bootstrap)
    if _model_state_bytes(frozen_ranker) != frozen_before:
        raise SuccessorRuntimeError("frozen non-card ranker changed during rollout")
    return ArmEpisodeRollout(
        arm=normalized_arm,
        seed=seed,
        trajectory_id=f"{normalized_arm}:seed-{seed}",
        decisions=tuple(decisions),
        transitions=tuple(transitions),
        rewards=tuple(rewards),
        final_snapshot=final_snapshot,
        floor_progress=floor_progress,
        terminal_victory=terminal_victory,
        unsupported_reason=unsupported_reason,
    )


def rollout_paired_training_episode(
    bootstrap: PairedBootstrap,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> PairedEpisodeRollout:
    """Run candidate then control from one seed using disjoint arm state."""
    if not callable(clock):
        raise SuccessorRuntimeError("paired episode clock must be callable")
    now = float(clock())
    paired_deadline = now + MAX_CHARGED_SECONDS if deadline is None else float(deadline)
    if (
        not math.isfinite(now)
        or not math.isfinite(paired_deadline)
        or paired_deadline < now
        or paired_deadline > now + MAX_CHARGED_SECONDS
    ):
        raise SuccessorRuntimeError(
            "paired episode deadline exceeds the registered bound"
        )
    candidate = rollout_arm_training_episode(
        bootstrap,
        arm="candidate",
        environment_factory=environment_factory,
        seed=seed,
        max_decisions=max_decisions,
        deadline=paired_deadline,
        clock=clock,
    )
    control = rollout_arm_training_episode(
        bootstrap,
        arm="control",
        environment_factory=environment_factory,
        seed=seed,
        max_decisions=max_decisions,
        deadline=paired_deadline,
        clock=clock,
    )
    return PairedEpisodeRollout(seed=seed, candidate=candidate, control=control)


def _validate_baseline_vector(
    value: Any,
    *,
    width: int,
    label: str,
) -> torch.Tensor:
    if not isinstance(value, torch.Tensor) or value.shape != (width,):
        raise SuccessorRuntimeError(f"{label} must have shape ({width},)")
    if value.device.type != "cpu" or value.dtype != torch.float32:
        raise SuccessorRuntimeError(f"{label} must be CPU float32")
    if not bool(torch.isfinite(value).all().item()):
        raise SuccessorRuntimeError(f"{label} must be finite")
    return value


def fold_baseline_state_features(source: torch.Tensor) -> torch.Tensor:
    """Fold the state-only 1,024-vector into 128 float32 coordinates."""
    source_value = _validate_baseline_vector(
        source,
        width=BASELINE_SOURCE_DIM,
        label="policy state features",
    )
    folded = torch.zeros(BASELINE_FEATURE_DIM, dtype=torch.float32, device="cpu")
    for source_index in range(BASELINE_SOURCE_DIM):
        target_index = source_index % BASELINE_FEATURE_DIM
        folded[target_index] = folded[target_index] + source_value[source_index]
    if not bool(torch.isfinite(folded).all().item()):
        raise SuccessorRuntimeError("folded state features must remain finite")
    return folded


def _sparse_state_feature_payload(value: torch.Tensor) -> dict[str, Any]:
    vector = _validate_baseline_vector(
        value,
        width=BASELINE_FEATURE_DIM,
        label="baseline state features",
    )
    entries = [
        [index, float(vector[index].item())]
        for index in range(BASELINE_FEATURE_DIM)
        if float(vector[index].item()) != 0.0
    ]
    identity = {
        "dense_dim": BASELINE_FEATURE_DIM,
        "dtype": "float32",
        "entries": entries,
        "folding": "ascending-source-index-modulo-128-float32-add-v1",
        "schema_version": BASELINE_FEATURE_SCHEMA_VERSION,
        "source_dim": BASELINE_SOURCE_DIM,
    }
    return {
        **identity,
        "sha256": hashlib.sha256(
            _canonical_json_bytes(identity) + b"\n"
        ).hexdigest(),
    }


def _build_arm_baseline_decisions(
    episodes: Sequence[ArmEpisodeRollout],
    *,
    arm: ArmName,
) -> tuple[ArmBaselineDecision, ...]:
    normalized_arm = _validated_arm(arm)
    if isinstance(episodes, (str, bytes)) or not isinstance(episodes, Sequence):
        raise SuccessorRuntimeError("arm episodes must be a sequence")
    source = tuple(episodes)
    if len(source) != TRAJECTORIES_PER_CHUNK:
        raise SuccessorRuntimeError(
            "cross-fitted baseline requires exactly 64 trajectories per arm"
        )
    seeds = tuple(episode.seed for episode in source)
    if any(
        isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
        for seed in seeds
    ) or seeds != tuple(sorted(set(seeds))):
        raise SuccessorRuntimeError(
            "arm trajectory seeds must be unique ascending nonnegative integers"
        )

    result: list[ArmBaselineDecision] = []
    for episode in source:
        if not isinstance(episode, ArmEpisodeRollout) or episode.arm != normalized_arm:
            raise SuccessorRuntimeError("arm episode identity differs")
        if episode.trajectory_id != f"{normalized_arm}:seed-{episode.seed}":
            raise SuccessorRuntimeError("arm trajectory identity differs")
        if episode.unsupported_reason is not None:
            raise SuccessorRuntimeError(
                "cross-fitted baseline requires complete supported trajectories"
            )
        if episode.final_snapshot.get("terminal") is not True:
            raise SuccessorRuntimeError(
                "cross-fitted baseline requires terminal trajectories"
            )
        if not episode.decisions or not (
            len(episode.decisions)
            == len(episode.rewards)
            == len(episode.transitions)
        ):
            raise SuccessorRuntimeError(
                "complete arm trajectory decision fields must align"
            )

        return_to_go = [0.0] * len(episode.rewards)
        running = 0.0
        for index in range(len(episode.rewards) - 1, -1, -1):
            reward = episode.rewards[index]
            if isinstance(reward, bool) or not isinstance(reward, Real):
                raise SuccessorRuntimeError("formal rewards must be finite")
            reward_value = float(reward)
            if not math.isfinite(reward_value):
                raise SuccessorRuntimeError("formal rewards must be finite")
            running = reward_value + running
            if not math.isfinite(running) or not 0.0 <= running <= 3.0:
                raise SuccessorRuntimeError(
                    "return-to-go must remain in [0, 3]"
                )
            return_to_go[index] = running

        for index, (decision, reward, raw_return) in enumerate(
            zip(
                episode.decisions,
                episode.rewards,
                return_to_go,
                strict=True,
            )
        ):
            expected_id = (
                f"{normalized_arm}:seed-{episode.seed}:decision-{index}"
            )
            if (
                not isinstance(decision, ArmRolloutDecision)
                or decision.arm != normalized_arm
                or decision.decision_index != index
                or decision.decision_id != expected_id
                or decision.category not in simulator_adapter.TARGET_CATEGORIES
            ):
                raise SuccessorRuntimeError("arm decision identity differs")
            if decision.category == "card_reward":
                if (
                    not isinstance(decision.card_terms, CardAcceptancePolicyTerms)
                    or decision.card_terms.selected_action_id
                    != decision.selected_action_id
                ):
                    raise SuccessorRuntimeError(
                        "card decision terms and selected action differ"
                    )
            elif decision.card_terms is not None:
                raise SuccessorRuntimeError(
                    "non-card decision cannot carry trainable card terms"
                )
            result.append(
                ArmBaselineDecision(
                    arm=normalized_arm,
                    category=decision.category,
                    decision_id=decision.decision_id,
                    decision_index=index,
                    raw_return=raw_return,
                    reward=float(reward),
                    seed=episode.seed,
                    state_features=fold_baseline_state_features(
                        decision.state_features
                    ),
                    trajectory_id=episode.trajectory_id,
                )
            )
    return tuple(result)


def _normalize_baseline_decisions(
    decisions: Sequence[ArmBaselineDecision],
    *,
    arm: ArmName,
) -> tuple[
    tuple[ArmBaselineDecision, ...],
    tuple[str, ...],
    dict[str, tuple[ArmBaselineDecision, ...]],
]:
    normalized_arm = _validated_arm(arm)
    source = tuple(decisions)
    by_trajectory: dict[str, list[ArmBaselineDecision]] = {}
    seen_decision_ids: set[str] = set()
    for decision in source:
        if not isinstance(decision, ArmBaselineDecision) or decision.arm != normalized_arm:
            raise SuccessorRuntimeError("baseline decision arm differs")
        if decision.decision_id in seen_decision_ids:
            raise SuccessorRuntimeError("baseline decision identities must be unique")
        seen_decision_ids.add(decision.decision_id)
        _validate_baseline_vector(
            decision.state_features,
            width=BASELINE_FEATURE_DIM,
            label="baseline state features",
        )
        by_trajectory.setdefault(decision.trajectory_id, []).append(decision)
    if len(by_trajectory) != TRAJECTORIES_PER_CHUNK:
        raise SuccessorRuntimeError(
            "cross-fitted baseline requires exactly 64 trajectories"
        )

    seed_by_trajectory: dict[str, int] = {}
    normalized_by_trajectory: dict[str, tuple[ArmBaselineDecision, ...]] = {}
    seen_seeds: set[int] = set()
    for trajectory_id, rows in by_trajectory.items():
        seeds = {row.seed for row in rows}
        if len(seeds) != 1:
            raise SuccessorRuntimeError("one trajectory must have exactly one seed")
        seed = next(iter(seeds))
        if seed in seen_seeds:
            raise SuccessorRuntimeError("trajectory seeds must be unique")
        seen_seeds.add(seed)
        seed_by_trajectory[trajectory_id] = seed
        ordered = tuple(sorted(rows, key=lambda row: row.decision_index))
        if [row.decision_index for row in ordered] != list(range(len(ordered))):
            raise SuccessorRuntimeError(
                "trajectory decision indices must be contiguous"
            )
        normalized_by_trajectory[trajectory_id] = ordered

    trajectory_order = tuple(
        sorted(seed_by_trajectory, key=lambda key: seed_by_trajectory[key])
    )
    canonical = tuple(
        decision
        for trajectory_id in trajectory_order
        for decision in normalized_by_trajectory[trajectory_id]
    )
    return canonical, trajectory_order, normalized_by_trajectory


def _fold_manifest(
    trajectory_order: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    manifest = {
        f"fold-{fold_index}": tuple(
            sorted(
                trajectory_id
                for position, trajectory_id in enumerate(trajectory_order)
                if position % FOLD_COUNT == fold_index
            )
        )
        for fold_index in range(FOLD_COUNT)
    }
    if any(
        len(trajectory_ids) != HELD_OUT_TRAJECTORIES_PER_FOLD
        for trajectory_ids in manifest.values()
    ):
        raise SuccessorRuntimeError(
            "every fold must hold out exactly 16 trajectories"
        )
    return manifest


def _augmented_sparse_float64_features(
    decision: ArmBaselineDecision,
) -> tuple[tuple[int, float], ...]:
    entries = [(0, 1.0)]
    for feature_index in range(BASELINE_FEATURE_DIM):
        value = float(decision.state_features[feature_index].item())
        if value != 0.0:
            entries.append((feature_index + 1, value))
    return tuple(entries)


def _fit_fold_model(
    *,
    fold_id: str,
    held_out_ids: tuple[str, ...],
    trajectory_order: Sequence[str],
    by_trajectory: Mapping[str, tuple[ArmBaselineDecision, ...]],
) -> RidgeFoldModel:
    held_out_set = set(held_out_ids)
    fit_ids = tuple(sorted(set(trajectory_order).difference(held_out_set)))
    if len(fit_ids) != FIT_TRAJECTORIES_PER_FOLD:
        raise SuccessorRuntimeError("every fold must fit exactly 48 trajectories")

    width = BASELINE_FEATURE_DIM + 1
    normal_matrix = torch.zeros((width, width), dtype=torch.float64)
    rhs = torch.zeros(width, dtype=torch.float64)
    for trajectory_id in trajectory_order:
        if trajectory_id in held_out_set:
            continue
        trajectory = by_trajectory[trajectory_id]
        weight = 1.0 / (FIT_TRAJECTORIES_PER_FOLD * len(trajectory))
        for decision in trajectory:
            target = float(decision.raw_return)
            features = _augmented_sparse_float64_features(decision)
            for row_index, row_value in features:
                rhs[row_index] = float(rhs[row_index].item()) + (
                    weight * target * row_value
                )
                for column_index, column_value in features:
                    normal_matrix[row_index, column_index] = float(
                        normal_matrix[row_index, column_index].item()
                    ) + (weight * row_value * column_value)
    ridge = torch.zeros(width, dtype=torch.float64)
    ridge[1:] = RIDGE_COEFFICIENT
    normal_matrix += torch.diag(ridge)
    try:
        factor = torch.linalg.cholesky(normal_matrix)
        coefficients = torch.cholesky_solve(
            rhs.reshape(width, 1), factor
        ).reshape(width)
    except RuntimeError as exc:
        raise SuccessorRuntimeError(
            "registered float64 Cholesky ridge solve failed"
        ) from exc
    if not bool(torch.isfinite(coefficients).all().item()):
        raise SuccessorRuntimeError("ridge coefficients must be finite")

    coefficient_values = tuple(float(value) for value in coefficients.tolist())
    product_sums = torch.tensor(
        [
            math.fsum(
                abs(
                    float(normal_matrix[row_index, column_index].item())
                    * coefficient_values[column_index]
                )
                for column_index in range(width)
            )
            for row_index in range(width)
        ],
        dtype=torch.float64,
    )
    residuals = torch.tensor(
        [
            math.fsum(
                float(normal_matrix[row_index, column_index].item())
                * coefficient_values[column_index]
                for column_index in range(width)
            )
            - float(rhs[row_index].item())
            for row_index in range(width)
        ],
        dtype=torch.float64,
    )
    for coordinate in range(width):
        scale = max(
            abs(float(rhs[coordinate].item())),
            float(product_sums[coordinate].item()),
        )
        limit = RIDGE_RESIDUAL_ATOL + RIDGE_RESIDUAL_RTOL * scale
        if abs(float(residuals[coordinate].item())) > limit:
            raise SuccessorRuntimeError(
                "ridge KKT residual exceeds the fixed boundary"
            )
    return RidgeFoldModel(
        fold_id=fold_id,
        fit_trajectory_ids=fit_ids,
        held_out_trajectory_ids=held_out_ids,
        coefficients=coefficient_values,
        kkt_residuals=tuple(float(value) for value in residuals.tolist()),
        rhs=tuple(float(value) for value in rhs.tolist()),
        absolute_product_sums=tuple(float(value) for value in product_sums.tolist()),
    )


def _predict_baseline(
    model: RidgeFoldModel,
    decision: ArmBaselineDecision,
) -> ArmBaselinePrediction:
    values = [1.0]
    values.extend(
        float(decision.state_features[index].item())
        for index in range(BASELINE_FEATURE_DIM)
    )
    unclipped = math.fsum(
        float(model.coefficients[index]) * values[index]
        for index in range(BASELINE_FEATURE_DIM + 1)
    )
    if not math.isfinite(unclipped):
        raise SuccessorRuntimeError("held-out ridge prediction must be finite")
    clipped = min(PREDICTION_MAX, max(PREDICTION_MIN, unclipped))
    return ArmBaselinePrediction(
        decision_id=decision.decision_id,
        fold_id=model.fold_id,
        trajectory_id=decision.trajectory_id,
        unclipped=unclipped,
        clipped=clipped,
        was_clipped=clipped != unclipped,
        preclip_little_endian_hex=struct.pack("<d", unclipped).hex(),
        feature_sha256=_sparse_state_feature_payload(
            decision.state_features
        )["sha256"],
    )


def _build_cross_fitted_arm_baseline(
    decisions: Sequence[ArmBaselineDecision],
    *,
    arm: ArmName,
) -> ArmCrossFittedBaseline:
    normalized_arm = _validated_arm(arm)
    canonical, trajectory_order, by_trajectory = _normalize_baseline_decisions(
        decisions,
        arm=normalized_arm,
    )
    fold_trajectories = _fold_manifest(trajectory_order)
    models = tuple(
        _fit_fold_model(
            fold_id=fold_id,
            held_out_ids=held_out_ids,
            trajectory_order=trajectory_order,
            by_trajectory=by_trajectory,
        )
        for fold_id, held_out_ids in fold_trajectories.items()
    )
    model_by_fold = {model.fold_id: model for model in models}
    fold_by_trajectory = {
        trajectory_id: fold_id
        for fold_id, trajectory_ids in fold_trajectories.items()
        for trajectory_id in trajectory_ids
    }

    predictions: list[ArmBaselinePrediction] = []
    records: list[dict[str, Any]] = []
    for decision in canonical:
        fold_id = fold_by_trajectory[decision.trajectory_id]
        model = model_by_fold[fold_id]
        prediction = _predict_baseline(model, decision)
        predictions.append(prediction)
        records.append(
            {
                "baseline_fit_trajectory_ids": list(model.fit_trajectory_ids),
                "baseline_mode": "cross_fitted",
                "baseline_prediction": prediction.clipped,
                "decision_id": decision.decision_id,
                "decision_index": decision.decision_index,
                "feature_fields": list(FEATURE_FIELDS),
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "feature_sha256": prediction.feature_sha256,
                "fold_id": fold_id,
                "raw_return": float(decision.raw_return),
                "scale": 1.0,
                "scale_fit_trajectory_ids": [],
                "scale_mode": "fixed_unit",
                "trajectory_id": decision.trajectory_id,
            }
        )
    try:
        advantage_batch = build_advantage_batch(
            records,
            fold_trajectories=fold_trajectories,
        )
    except AdvantageAttributionError as exc:
        raise SuccessorRuntimeError(str(exc)) from exc
    return ArmCrossFittedBaseline(
        arm=normalized_arm,
        decisions=canonical,
        fold_trajectories=fold_trajectories,
        models=models,
        predictions=tuple(predictions),
        advantage_batch=advantage_batch,
    )


def build_paired_cross_fitted_baselines(
    episodes: Sequence[PairedEpisodeRollout],
) -> PairedCrossFittedBaselines:
    """Fit independent arm-local baselines over one exact 64-seed pair slice."""
    if isinstance(episodes, (str, bytes)) or not isinstance(episodes, Sequence):
        raise SuccessorRuntimeError("paired episodes must be a sequence")
    source = tuple(episodes)
    if len(source) != TRAJECTORIES_PER_CHUNK:
        raise SuccessorRuntimeError(
            "paired cross-fitted baseline requires exactly 64 pairs"
        )
    seeds = tuple(pair.seed for pair in source)
    if any(
        not isinstance(pair, PairedEpisodeRollout)
        or isinstance(pair.seed, bool)
        or not isinstance(pair.seed, int)
        or pair.seed < 0
        or pair.candidate.seed != pair.seed
        or pair.control.seed != pair.seed
        for pair in source
    ) or seeds != tuple(sorted(set(seeds))):
        raise SuccessorRuntimeError(
            "paired episodes must use one unique ascending seed slice"
        )
    candidate_decisions = _build_arm_baseline_decisions(
        tuple(pair.candidate for pair in source),
        arm="candidate",
    )
    control_decisions = _build_arm_baseline_decisions(
        tuple(pair.control for pair in source),
        arm="control",
    )
    return PairedCrossFittedBaselines(
        seeds=seeds,
        candidate=_build_cross_fitted_arm_baseline(
            candidate_decisions,
            arm="candidate",
        ),
        control=_build_cross_fitted_arm_baseline(
            control_decisions,
            arm="control",
        ),
    )


def build_arm_card_reward_rows(
    episodes: Sequence[PairedEpisodeRollout],
    *,
    arm: ArmName,
    baseline: ArmCrossFittedBaseline,
) -> tuple[tuple[CardAcceptancePolicyTerms, float], ...]:
    """Align card terms with exact held-out residuals without post-processing."""
    normalized_arm = _validated_arm(arm)
    if not isinstance(baseline, ArmCrossFittedBaseline) or baseline.arm != normalized_arm:
        raise SuccessorRuntimeError("card reward baseline arm differs")
    source = tuple(episodes)
    if len(source) != TRAJECTORIES_PER_CHUNK:
        raise SuccessorRuntimeError("card reward rows require exactly 64 pairs")
    arm_episodes = tuple(
        pair.candidate if normalized_arm == "candidate" else pair.control
        for pair in source
    )
    rollout_decisions = tuple(
        decision for episode in arm_episodes for decision in episode.decisions
    )
    baseline_ids = tuple(decision.decision_id for decision in baseline.decisions)
    rollout_ids = tuple(decision.decision_id for decision in rollout_decisions)
    records = baseline.advantage_batch.records
    record_ids = tuple(record.decision_id for record in records)
    if baseline_ids != rollout_ids or record_ids != baseline_ids:
        raise SuccessorRuntimeError(
            "card reward rollout and baseline decision order differs"
        )

    rows: list[tuple[CardAcceptancePolicyTerms, float]] = []
    for decision, baseline_decision, record in zip(
        rollout_decisions,
        baseline.decisions,
        records,
        strict=True,
    ):
        if (
            record.raw_return != baseline_decision.raw_return
            or record.advantage
            != record.raw_return - record.baseline_prediction
            or record.scale != 1.0
            or record.scale_mode != "fixed_unit"
            or record.scale_fit_trajectory_ids
        ):
            raise SuccessorRuntimeError(
                "card reward advantage arithmetic differs from registration"
            )
        if decision.category != "card_reward":
            if decision.card_terms is not None:
                raise SuccessorRuntimeError(
                    "non-card decision carries card objective terms"
                )
            continue
        terms = decision.card_terms
        if (
            not isinstance(terms, CardAcceptancePolicyTerms)
            or terms.selected_action_id != decision.selected_action_id
        ):
            raise SuccessorRuntimeError("card reward policy term alignment differs")
        rows.append((terms, record.advantage))
    return tuple(rows)


__all__ = [
    "ArmBaselineDecision",
    "ArmBaselinePrediction",
    "ArmCardRewardObjective",
    "ArmCrossFittedBaseline",
    "ArmEpisodeRollout",
    "ArmOptimizerStepEvidence",
    "ArmOptimizers",
    "ArmRolloutDecision",
    "CandidateArm",
    "ControlArm",
    "PairedBootstrap",
    "PairedCrossFittedBaselines",
    "PairedEpisodeRollout",
    "RidgeFoldModel",
    "SuccessorRuntimeError",
    "apply_arm_optimizer_step",
    "build_arm_card_reward_rows",
    "build_arm_card_reward_objective",
    "build_arm_optimizers",
    "build_matched_bootstrap",
    "build_paired_cross_fitted_baselines",
    "encode_optimizer_state",
    "encode_paired_bootstrap",
    "fold_baseline_state_features",
    "forward_card_policy",
    "restore_optimizer_state",
    "restore_paired_bootstrap",
    "rollout_arm_training_episode",
    "rollout_paired_training_episode",
    "runtime_metadata",
    "score_noncard_candidates",
    "select_two_stage_action",
]
