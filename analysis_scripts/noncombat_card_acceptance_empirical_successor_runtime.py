"""Torch runtime primitives for the card-acceptance empirical successor."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import copy
from dataclasses import dataclass, field
import gzip
import hashlib
import io
import json
import math
from numbers import Integral, Real
import random
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
TRAINING_CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-training-checkpoint-v1"
)
RUNTIME_METADATA_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-runtime-metadata-v1"
)
CANARY_COMMITMENT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-canary-commitment-v1"
)
CANARY_REPLAY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-canary-replay-v1"
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
MAX_TRAINING_ENVIRONMENT_ACCESSES = 1_024
MAX_TRAINING_OPTIMIZER_STEPS = 16
MAX_SHADOW_OPTIMIZER_STEPS = 1
MAX_CANARY_ENVIRONMENT_ACCESSES = 512
MAX_HOLDOUT_ENVIRONMENT_ACCESSES = 1_024
MAX_TOTAL_ENVIRONMENT_ACCESSES = 2_560
CANARY_PAIR_COUNT = 128
CANARY_MIN_FAMILY_DENOMINATOR = 64
CANARY_MIN_FAMILY_COUNT = 2
CANARY_MAX_FAMILY_RATE = 0.95
HOLDOUT_PAIR_COUNT = 512
HOLDOUT_BOOTSTRAP_SEED = 0
HOLDOUT_BOOTSTRAP_RESAMPLES = 10_000
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
    parameter_names: tuple[str, ...]
    component_order: tuple[str, ...]
    component_gradients: tuple[tuple[torch.Tensor | None, ...], ...]
    combined_gradients: tuple[torch.Tensor, ...]
    applied_gradients: tuple[torch.Tensor, ...]
    pre_parameters: tuple[torch.Tensor, ...]
    post_parameters: tuple[torch.Tensor, ...]
    preclip_global_norm: float
    postclip_global_norm: float
    optimizer_state_before: dict[str, Any]
    optimizer_state_after: dict[str, Any]


@dataclass(frozen=True)
class _PreparedArmOptimizerStep:
    parameters: tuple[torch.nn.Parameter, ...]
    parameter_names: tuple[str, ...]
    component_order: tuple[str, ...]
    component_gradients: tuple[tuple[torch.Tensor | None, ...], ...]
    combined_gradients: tuple[torch.Tensor, ...]
    applied_gradients: tuple[torch.Tensor, ...]
    pre_parameters: tuple[torch.Tensor, ...]
    preclip_global_norm: float
    postclip_global_norm: float
    optimizer_state_before: dict[str, Any]


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
    candidate_features: torch.Tensor | None = None
    candidates: tuple[Mapping[str, Any], ...] = ()


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


@dataclass(frozen=True)
class ArmChunkUpdateEvidence:
    arm: ArmName
    decision_ids: tuple[str, ...]
    objective: ArmCardRewardObjective
    optimizer_step: ArmOptimizerStepEvidence


@dataclass(frozen=True)
class PairedChunkUpdateEvidence:
    seeds: tuple[int, ...]
    baselines: PairedCrossFittedBaselines
    candidate: ArmChunkUpdateEvidence
    control: ArmChunkUpdateEvidence


@dataclass
class PairedTrainingRuntime:
    bootstrap: PairedBootstrap
    optimizers: ArmOptimizers
    next_chunk_index: int = 0
    completed_pairs: int = 0
    completed_decisions: int = 0
    training_environment_accesses: int = 0
    candidate_optimizer_updates: int = 0
    control_optimizer_updates: int = 0
    training_optimizer_steps: int = 0
    completed_chunk_summaries: list[dict[str, Any]] = field(default_factory=list)
    stopped_for_family_saturation: bool = False


@dataclass(frozen=True)
class CompletedPairedTrainingChunk:
    chunk_index: int
    seeds: tuple[int, ...]
    episodes: tuple[PairedEpisodeRollout, ...]
    update: PairedChunkUpdateEvidence
    saturation: Mapping[str, Any]
    checkpoint: bytes


@dataclass(frozen=True)
class BoundedTrainingResult:
    verdict: str
    chunks: tuple[CompletedPairedTrainingChunk, ...]
    resource_use: Mapping[str, int]
    checkpoint: bytes


@dataclass(frozen=True)
class StructuralCanaryResult:
    verdict: str
    seeds: tuple[int, ...]
    commitments: tuple[Mapping[str, Any], ...]
    replays: tuple[Mapping[str, Any], ...]
    concentration: Mapping[str, Any]
    shadow_step: Mapping[str, Any] | None
    resource_use: Mapping[str, int]


@dataclass(frozen=True)
class UntouchedHoldoutResult:
    verdict: str
    outcome_class: str | None
    seeds: tuple[int, ...]
    pairs: tuple[Mapping[str, Any], ...]
    family_observations: tuple[Mapping[str, Any], ...]
    concentration: Mapping[str, Any]
    bootstrap: Mapping[str, Any] | None
    victory_counts: Mapping[str, int]
    arm_bindings: Mapping[str, Mapping[str, str]]
    verified_canary: Mapping[str, Any]
    resource_use: Mapping[str, int]


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


def canonical_runtime_sha256(value: object) -> str:
    """Return the runtime's canonical SHA-256 for reviewable evidence objects."""
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _deterministic_gzip_bytes(payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        fileobj=buffer,
        mode="wb",
        filename="",
        mtime=0,
    ) as handle:
        handle.write(payload)
    return buffer.getvalue()


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


def _validated_parameter_names(
    value: Sequence[str] | None,
    *,
    count: int,
) -> tuple[str, ...]:
    if value is None:
        return tuple(f"parameter-{index:04d}" for index in range(count))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SuccessorRuntimeError("optimizer parameter names must be a sequence")
    names = tuple(value)
    if (
        len(names) != count
        or len(set(names)) != count
        or any(not isinstance(name, str) or not name for name in names)
    ):
        raise SuccessorRuntimeError(
            "optimizer parameter names must be unique and aligned"
        )
    return names


def _prepare_arm_optimizer_step(
    optimizer: torch.optim.Optimizer,
    objective: ArmCardRewardObjective,
    *,
    parameters: Sequence[torch.nn.Parameter],
    parameter_names: Sequence[str] | None,
    reconstruct_components: bool = True,
) -> _PreparedArmOptimizerStep:
    """Validate and clip one arm without changing parameters or Adam moments."""
    registered_parameters = _validated_registered_adam(optimizer)
    supplied_parameters = tuple(parameters)
    if len(supplied_parameters) != len(registered_parameters) or any(
        supplied is not registered
        for supplied, registered in zip(
            supplied_parameters, registered_parameters, strict=True
        )
    ):
        raise SuccessorRuntimeError("optimizer parameter order differs")
    normalized_parameter_names = _validated_parameter_names(
        parameter_names,
        count=len(registered_parameters),
    )
    if not isinstance(objective, ArmCardRewardObjective):
        raise SuccessorRuntimeError("optimizer objective type differs")
    if objective.card_decision_count <= 0:
        raise SuccessorRuntimeError("optimizer objective has no card decisions")

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

    if reconstruct_components:
        component_order = (
            "family_policy",
            "conditional_policy",
            "family_entropy",
            "conditional_entropy",
        )
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
    else:
        component_order = ("total_loss",)
        total_gradients = torch.autograd.grad(
            objective.total_loss,
            registered_parameters,
            allow_unused=True,
        )
        raw_component_gradients = (total_gradients,)
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
    pre_parameters = tuple(
        parameter.detach().clone() for parameter in registered_parameters
    )
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
    return _PreparedArmOptimizerStep(
        parameters=registered_parameters,
        parameter_names=normalized_parameter_names,
        component_order=component_order,
        component_gradients=component_gradients,
        combined_gradients=tuple(combined_gradients),
        applied_gradients=applied_gradients,
        pre_parameters=pre_parameters,
        preclip_global_norm=preclip_global_norm,
        postclip_global_norm=postclip_global_norm,
        optimizer_state_before=optimizer_state_before,
    )


def _commit_prepared_arm_step(
    optimizer: torch.optim.Optimizer,
    prepared: _PreparedArmOptimizerStep,
) -> ArmOptimizerStepEvidence:
    registered_parameters = _validated_registered_adam(optimizer)
    if len(registered_parameters) != len(prepared.parameters) or any(
        actual is not expected
        for actual, expected in zip(
            registered_parameters, prepared.parameters, strict=True
        )
    ):
        raise SuccessorRuntimeError("prepared optimizer parameter order differs")
    if encode_optimizer_state(optimizer) != prepared.optimizer_state_before:
        raise SuccessorRuntimeError("optimizer state changed after preparation")
    if any(
        not torch.equal(parameter.detach(), expected)
        for parameter, expected in zip(
            registered_parameters, prepared.pre_parameters, strict=True
        )
    ):
        raise SuccessorRuntimeError("parameters changed after preparation")

    optimizer.zero_grad(set_to_none=True)
    for parameter, gradient in zip(
        registered_parameters, prepared.applied_gradients, strict=True
    ):
        if (
            gradient.device != parameter.device
            or gradient.dtype != parameter.dtype
            or gradient.shape != parameter.shape
            or not bool(torch.isfinite(gradient).all().item())
        ):
            raise SuccessorRuntimeError("prepared applied gradient differs")
        parameter.grad = gradient.detach().clone()
    optimizer.step()
    post_parameters = tuple(
        parameter.detach().clone() for parameter in registered_parameters
    )
    optimizer_state_after = encode_optimizer_state(optimizer)
    return ArmOptimizerStepEvidence(
        parameter_names=prepared.parameter_names,
        component_order=prepared.component_order,
        component_gradients=prepared.component_gradients,
        combined_gradients=prepared.combined_gradients,
        applied_gradients=prepared.applied_gradients,
        pre_parameters=prepared.pre_parameters,
        post_parameters=post_parameters,
        preclip_global_norm=prepared.preclip_global_norm,
        postclip_global_norm=prepared.postclip_global_norm,
        optimizer_state_before=prepared.optimizer_state_before,
        optimizer_state_after=optimizer_state_after,
    )


def apply_arm_optimizer_step(
    optimizer: torch.optim.Optimizer,
    objective: ArmCardRewardObjective,
    *,
    parameters: Sequence[torch.nn.Parameter],
    parameter_names: Sequence[str] | None = None,
) -> ArmOptimizerStepEvidence:
    """Validate, reconstruct, globally clip, and apply one registered arm step."""
    prepared = _prepare_arm_optimizer_step(
        optimizer,
        objective,
        parameters=parameters,
        parameter_names=parameter_names,
    )
    return _commit_prepared_arm_step(optimizer, prepared)


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
        candidate_features=policy_input.candidate_features.detach().clone(),
        candidates=tuple(copy.deepcopy(candidates)),
    )


def _select_arm_frozen_decision(
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

    with torch.no_grad():
        if category == "card_reward":
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
                    greedy=True,
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
                "category": category,
                "decision_id": decision_id,
                "decision_index": decision_index,
                "family_order": list(terms.family_order),
                "family_probabilities": {
                    family: float(terms.family_probabilities[index].item())
                    for index, family in enumerate(terms.family_order)
                },
                "multi_family": len(terms.family_order) > 1,
                "selected_action_id": selected_action_id,
                "selected_family": terms.selected_family,
                "selection_mode": "unique-two-stage-greedy-v1",
                "two_stage_greedy_action_ids": list(
                    terms.two_stage_greedy_action_ids
                ),
                "unique_greedy_family_id": terms.unique_greedy_family_id,
            }
            card_terms: CardAcceptancePolicyTerms | None = terms
        else:
            try:
                scores = score_noncard_candidates(
                    bootstrap,
                    arm=arm,
                    category=str(category),
                    state_features=policy_input.state_features,
                    candidate_features=policy_input.candidate_features,
                )
            except (RuntimeError, TypeError, ValueError) as exc:
                raise SuccessorRuntimeError(str(exc)) from exc
            if not bool(torch.isfinite(scores).all().item()):
                raise SuccessorRuntimeError("non-card scores must be finite")
            maximum = torch.max(scores)
            maximum_indices = torch.nonzero(
                scores == maximum,
                as_tuple=False,
            ).reshape(-1)
            maximum_action_ids = [
                str(candidates[int(index.item())]["action_id"])
                for index in maximum_indices
            ]
            if len(maximum_action_ids) != 1:
                raise SuccessorRuntimeError(
                    "non-card raw-score maximum tie has no unique choice"
                )
            selected_action_id = maximum_action_ids[0]
            diagnostic = {
                "candidate_scores": {
                    str(candidate["action_id"]): float(scores[index].item())
                    for index, candidate in enumerate(candidates)
                },
                "category": category,
                "decision_id": decision_id,
                "decision_index": decision_index,
                "raw_score_max_action_ids": maximum_action_ids,
                "selected_action_id": selected_action_id,
                "selection_mode": "unique-raw-score-greedy-v1",
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
        candidate_features=policy_input.candidate_features.detach().clone(),
        candidates=tuple(copy.deepcopy(candidates)),
    )


def _select_native_baseline_decision(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    environment: Any,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    seed: int,
    decision_index: int,
) -> ArmRolloutDecision:
    del bootstrap
    try:
        policy_input = project_state_conditioned_policy_input(snapshot, candidates)
    except PolicyInputError as exc:
        raise SuccessorRuntimeError(str(exc)) from exc
    query = getattr(environment, "native_baseline_action", None)
    if not callable(query):
        raise SuccessorRuntimeError(
            "environment.native_baseline_action must be callable"
        )
    source_snapshot = copy.deepcopy(snapshot)
    source_candidates = copy.deepcopy(candidates)
    try:
        raw_action = query()
    except Exception as exc:
        raise SuccessorRuntimeError(f"native baseline query failed: {exc}") from exc
    _assert_source_unchanged(environment, source_snapshot, source_candidates)
    try:
        action = simulator_adapter.validate_native_baseline_action(
            raw_action,
            category=snapshot["category"],
            candidates=candidates,
        )
    except simulator_adapter.SimulatorAdapterError as exc:
        raise SuccessorRuntimeError(str(exc)) from exc
    decision_id = f"{arm}:seed-{seed}:decision-{decision_index}"
    return ArmRolloutDecision(
        arm=arm,
        category=str(snapshot["category"]),
        decision_id=decision_id,
        decision_index=decision_index,
        selected_action_id=action["action_id"],
        state_features=policy_input.state_features.detach().clone(),
        card_terms=None,
        diagnostic={
            "category": snapshot["category"],
            "decision_id": decision_id,
            "decision_index": decision_index,
            "native_policy_id": action["policy_id"],
            "selected_action_id": action["action_id"],
            "selection_mode": "native-simple-agent-v1",
        },
        candidate_features=policy_input.candidate_features.detach().clone(),
        candidates=tuple(copy.deepcopy(candidates)),
    )


def _rollout_arm_episode(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    environment_factory: Callable[[int], Any],
    seed: int,
    decision_selector: Callable[..., ArmRolloutDecision],
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    native_baseline_categories: Sequence[str] = (),
) -> ArmEpisodeRollout:
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
    if isinstance(native_baseline_categories, (str, bytes)):
        raise SuccessorRuntimeError("native baseline categories must be a sequence")
    native_categories = tuple(native_baseline_categories)
    if len(set(native_categories)) != len(native_categories) or any(
        category not in simulator_adapter.TARGET_CATEGORIES
        for category in native_categories
    ):
        raise SuccessorRuntimeError("native baseline categories are invalid")
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
        if snapshot["category"] in native_categories:
            decision = _select_native_baseline_decision(
                bootstrap,
                arm=normalized_arm,
                environment=environment,
                snapshot=snapshot,
                candidates=candidates,
                seed=seed,
                decision_index=len(decisions),
            )
        else:
            decision = decision_selector(
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
            "episode must contain at least one decision"
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


def rollout_arm_training_episode(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    environment_factory: Callable[[int], Any],
    seed: int,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    native_baseline_categories: Sequence[str] = (),
) -> ArmEpisodeRollout:
    """Run one clone-only arm trajectory with card-only trainable routing."""
    return _rollout_arm_episode(
        bootstrap,
        arm=arm,
        environment_factory=environment_factory,
        seed=seed,
        decision_selector=_sample_arm_training_decision,
        max_decisions=max_decisions,
        deadline=deadline,
        clock=clock,
        native_baseline_categories=native_baseline_categories,
    )


def rollout_arm_frozen_evaluation(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
    environment_factory: Callable[[int], Any],
    seed: int,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    native_baseline_categories: Sequence[str] = (),
) -> ArmEpisodeRollout:
    """Run one clone-only arm trajectory without sampling or mutation."""
    return _rollout_arm_episode(
        bootstrap,
        arm=arm,
        environment_factory=environment_factory,
        seed=seed,
        decision_selector=_select_arm_frozen_decision,
        max_decisions=max_decisions,
        deadline=deadline,
        clock=clock,
        native_baseline_categories=native_baseline_categories,
    )


def _rollout_paired_card_only_native_baseline(
    bootstrap: PairedBootstrap,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    frozen: bool,
    max_decisions: int,
    deadline: float | None,
    clock: Callable[[], float],
) -> PairedEpisodeRollout:
    if not callable(clock):
        raise SuccessorRuntimeError("paired episode clock must be callable")
    before = encode_paired_bootstrap(bootstrap) if frozen else None
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
    rollout = rollout_arm_frozen_evaluation if frozen else rollout_arm_training_episode
    candidate = rollout(
        bootstrap,
        arm="candidate",
        environment_factory=environment_factory,
        seed=seed,
        max_decisions=max_decisions,
        deadline=paired_deadline,
        clock=clock,
        native_baseline_categories=tuple(
            category
            for category in simulator_adapter.TARGET_CATEGORIES
            if category != "card_reward"
        ),
    )
    control = rollout(
        bootstrap,
        arm="control",
        environment_factory=environment_factory,
        seed=seed,
        max_decisions=max_decisions,
        deadline=paired_deadline,
        clock=clock,
        native_baseline_categories=simulator_adapter.TARGET_CATEGORIES,
    )
    if before is not None and encode_paired_bootstrap(bootstrap) != before:
        raise SuccessorRuntimeError("frozen evaluation mutated bootstrap state")
    return PairedEpisodeRollout(seed=seed, candidate=candidate, control=control)


def rollout_paired_card_only_native_baseline_training_episode(
    bootstrap: PairedBootstrap,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> PairedEpisodeRollout:
    """Sample candidate cards while native SimpleAgent owns every other action."""
    return _rollout_paired_card_only_native_baseline(
        bootstrap,
        environment_factory=environment_factory,
        seed=seed,
        frozen=False,
        max_decisions=max_decisions,
        deadline=deadline,
        clock=clock,
    )


def rollout_paired_card_only_native_baseline_frozen_evaluation(
    bootstrap: PairedBootstrap,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> PairedEpisodeRollout:
    """Greedily evaluate candidate cards against an all-native frozen control."""
    return _rollout_paired_card_only_native_baseline(
        bootstrap,
        environment_factory=environment_factory,
        seed=seed,
        frozen=True,
        max_decisions=max_decisions,
        deadline=deadline,
        clock=clock,
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


def rollout_paired_frozen_evaluation(
    bootstrap: PairedBootstrap,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> PairedEpisodeRollout:
    """Evaluate both arms greedily while preserving every bootstrap byte."""
    if not callable(clock):
        raise SuccessorRuntimeError("paired evaluation clock must be callable")
    before = encode_paired_bootstrap(bootstrap)
    now = float(clock())
    paired_deadline = now + MAX_CHARGED_SECONDS if deadline is None else float(deadline)
    if (
        not math.isfinite(now)
        or not math.isfinite(paired_deadline)
        or paired_deadline < now
        or paired_deadline > now + MAX_CHARGED_SECONDS
    ):
        raise SuccessorRuntimeError(
            "paired evaluation deadline exceeds the registered bound"
        )
    candidate = rollout_arm_frozen_evaluation(
        bootstrap,
        arm="candidate",
        environment_factory=environment_factory,
        seed=seed,
        max_decisions=max_decisions,
        deadline=paired_deadline,
        clock=clock,
    )
    control = rollout_arm_frozen_evaluation(
        bootstrap,
        arm="control",
        environment_factory=environment_factory,
        seed=seed,
        max_decisions=max_decisions,
        deadline=paired_deadline,
        clock=clock,
    )
    if encode_paired_bootstrap(bootstrap) != before:
        raise SuccessorRuntimeError("frozen evaluation mutated bootstrap state")
    return PairedEpisodeRollout(seed=seed, candidate=candidate, control=control)


def _card_terms_evidence(terms: CardAcceptancePolicyTerms) -> dict[str, Any]:
    return {
        "action_ids": list(terms.action_ids),
        "candidate_families": list(terms.candidate_families),
        "conditional_log_probabilities": _encode_tensor(
            terms.conditional_log_probabilities
        ),
        "conditional_probabilities": _encode_tensor(terms.conditional_probabilities),
        "family_entropy": _encode_tensor(terms.family_entropy),
        "family_log_probabilities": _encode_tensor(terms.family_log_probabilities),
        "family_order": list(terms.family_order),
        "family_probabilities": _encode_tensor(terms.family_probabilities),
        "selected_action_id": terms.selected_action_id,
        "selected_conditional_log_probability": _encode_tensor(
            terms.selected_conditional_log_probability
        ),
        "selected_family": terms.selected_family,
        "selected_family_log_probability": _encode_tensor(
            terms.selected_family_log_probability
        ),
        "two_stage_greedy_action_ids": list(terms.two_stage_greedy_action_ids),
        "unique_greedy_family_id": terms.unique_greedy_family_id,
        "unique_two_stage_greedy_action_id": (
            terms.unique_two_stage_greedy_action_id
        ),
    }


def _arm_canary_output(rollout: ArmEpisodeRollout) -> dict[str, Any]:
    if not isinstance(rollout, ArmEpisodeRollout):
        raise SuccessorRuntimeError("canary rollout type differs")
    if rollout.unsupported_reason is not None:
        raise SuccessorRuntimeError("canary rollout has an unsupported outcome")
    decisions: list[dict[str, Any]] = []
    for expected_index, decision in enumerate(rollout.decisions):
        if (
            decision.arm != rollout.arm
            or decision.decision_index != expected_index
            or decision.decision_id
            != f"{rollout.arm}:seed-{rollout.seed}:decision-{expected_index}"
        ):
            raise SuccessorRuntimeError("canary decision coordinate differs")
        if decision.category == "card_reward":
            if (
                not isinstance(decision.card_terms, CardAcceptancePolicyTerms)
                or decision.card_terms.selected_action_id
                != decision.selected_action_id
            ):
                raise SuccessorRuntimeError("canary card policy terms differ")
            card_terms = _card_terms_evidence(decision.card_terms)
        else:
            if decision.card_terms is not None:
                raise SuccessorRuntimeError("canary non-card decision has card terms")
            card_terms = None
        decisions.append(
            {
                "candidate_features": (
                    None
                    if decision.candidate_features is None
                    else _encode_tensor(decision.candidate_features)
                ),
                "candidates": copy.deepcopy(list(decision.candidates)),
                "card_terms": card_terms,
                "category": decision.category,
                "decision_id": decision.decision_id,
                "decision_index": decision.decision_index,
                "diagnostic": copy.deepcopy(dict(decision.diagnostic)),
                "selected_action_id": decision.selected_action_id,
                "state_features": _encode_tensor(decision.state_features),
            }
        )
    output = {
        "arm": rollout.arm,
        "decisions": decisions,
        "seed": rollout.seed,
        "terminal": {
            "final_snapshot": copy.deepcopy(rollout.final_snapshot),
            "floor_progress": float(rollout.floor_progress),
            "rewards": [float(value) for value in rollout.rewards],
            "terminal_victory": rollout.terminal_victory,
            "trajectory_id": rollout.trajectory_id,
            "transitions": copy.deepcopy(list(rollout.transitions)),
            "unsupported_reason": rollout.unsupported_reason,
        },
    }
    _canonical_json_bytes(output)
    return output


def _normalize_canary_arm_bindings(value: object) -> dict[str, dict[str, str]]:
    if not isinstance(value, Mapping) or set(value) != {"candidate", "control"}:
        raise SuccessorRuntimeError("canary arm bindings differ")
    normalized: dict[str, dict[str, str]] = {}
    for arm in ("candidate", "control"):
        binding = value[arm]
        if not isinstance(binding, Mapping) or set(binding) != {
            "checkpoint_sha256",
            "configuration_sha256",
            "source_sha256",
        }:
            raise SuccessorRuntimeError(f"{arm} canary binding fields differ")
        normalized[arm] = {}
        for name in (
            "checkpoint_sha256",
            "configuration_sha256",
            "source_sha256",
        ):
            digest = binding[name]
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise SuccessorRuntimeError(f"{arm} canary binding digest differs")
            normalized[arm][name] = digest
    return normalized


def _build_canary_commitment(
    *,
    rollout: ArmEpisodeRollout,
    arm_binding: Mapping[str, str],
    seed_index: int,
    sequence_index: int,
    previous_sha256: str,
) -> tuple[dict[str, Any], bytes]:
    output = _arm_canary_output(rollout)
    output_bytes = _canonical_json_bytes(output)
    stored = _deterministic_gzip_bytes(output_bytes)
    if max(len(output_bytes), len(stored)) > MAX_BOOTSTRAP_BYTES:
        raise SuccessorRuntimeError("canary output exceeds its artifact byte ceiling")
    output_artifact = {
        "encoding": "deterministic-gzip-v1",
        "path": (
            f"canary/outputs/{sequence_index:04d}-{rollout.arm}.json.gz"
        ),
        "stored_sha256": hashlib.sha256(stored).hexdigest(),
        "stored_size_bytes": len(stored),
        "uncompressed_sha256": hashlib.sha256(output_bytes).hexdigest(),
        "uncompressed_size_bytes": len(output_bytes),
    }
    body = {
        "arm": rollout.arm,
        "arm_binding": copy.deepcopy(dict(arm_binding)),
        "output_artifact": output_artifact,
        "output_sha256": output_artifact["uncompressed_sha256"],
        "previous_commitment_sha256": previous_sha256,
        "schema_version": CANARY_COMMITMENT_SCHEMA_VERSION,
        "seed": rollout.seed,
        "seed_index": seed_index,
        "sequence_index": sequence_index,
    }
    return (
        {**body, "commitment_sha256": canonical_runtime_sha256(body)},
        stored,
    )


def _family_concentration_gate(values: Sequence[str]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    denominator = len(values)
    maximum_count = max(counts.values(), default=0)
    maximum_rate = 0.0 if denominator == 0 else maximum_count / denominator
    passed = (
        denominator >= CANARY_MIN_FAMILY_DENOMINATOR
        and len(counts) >= CANARY_MIN_FAMILY_COUNT
        and maximum_rate <= CANARY_MAX_FAMILY_RATE
    )
    return {
        "counts": {key: counts[key] for key in sorted(counts)},
        "denominator": denominator,
        "family_count": len(counts),
        "maximum_count": maximum_count,
        "maximum_rate": maximum_rate,
        "passed": passed,
    }


def classify_canary_concentration(
    candidate_rollouts: Sequence[ArmEpisodeRollout],
) -> dict[str, Any]:
    """Apply the two fixed 64/2/0.95 candidate-family canary gates."""
    selected_families: list[str] = []
    greedy_families: list[str] = []
    for rollout in candidate_rollouts:
        if not isinstance(rollout, ArmEpisodeRollout) or rollout.arm != "candidate":
            raise SuccessorRuntimeError("canary concentration requires candidate rollouts")
        if rollout.unsupported_reason is not None:
            raise SuccessorRuntimeError("canary concentration has unsupported rollout")
        for decision in rollout.decisions:
            if decision.category != "card_reward":
                continue
            terms = decision.card_terms
            if not isinstance(terms, CardAcceptancePolicyTerms):
                raise SuccessorRuntimeError("canary card decision terms differ")
            if len(terms.family_order) < CANARY_MIN_FAMILY_COUNT:
                continue
            if terms.selected_family not in terms.family_order:
                raise SuccessorRuntimeError("canary selected family is invalid")
            selected_families.append(terms.selected_family)
            if terms.unique_greedy_family_id is not None:
                if terms.unique_greedy_family_id not in terms.family_order:
                    raise SuccessorRuntimeError("canary greedy family is invalid")
                greedy_families.append(terms.unique_greedy_family_id)
    selected_gate = _family_concentration_gate(selected_families)
    greedy_gate = _family_concentration_gate(greedy_families)
    return {
        "passed": selected_gate["passed"] and greedy_gate["passed"],
        "selected_family": selected_gate,
        "unique_greedy_family": greedy_gate,
    }


def _optimizer_parameter_state(
    optimizer: torch.optim.Optimizer,
    named_parameters: Sequence[tuple[str, torch.nn.Parameter]],
    *,
    prefix: str,
) -> dict[str, Any]:
    return {
        name: _encode_state_value(optimizer.state.get(parameter, {}))
        for name, parameter in named_parameters
        if name.startswith(prefix)
    }


def _conditional_output_evidence(
    output: CardAcceptancePolicyOutput,
    terms: CardAcceptancePolicyTerms,
) -> dict[str, Any]:
    return {
        "conditional_logits": _encode_tensor(output.conditional_logits),
        "conditional_probabilities": _encode_tensor(terms.conditional_probabilities),
        "selected_conditional_log_probability": _encode_tensor(
            terms.selected_conditional_log_probability
        ),
    }


def apply_family_only_shadow_step(
    bootstrap: PairedBootstrap,
    *,
    candidate_optimizer: torch.optim.Optimizer,
    decision: ArmRolloutDecision,
) -> dict[str, Any]:
    """Apply one registered family-only Adam step to an isolated candidate clone."""
    _validate_rollout_bootstrap(bootstrap)
    original_named = _arm_named_trainable_parameters(bootstrap, arm="candidate")
    if tuple(parameter for _, parameter in original_named) != _validated_registered_adam(
        candidate_optimizer
    ):
        raise SuccessorRuntimeError("shadow candidate optimizer ownership differs")
    if (
        not isinstance(decision, ArmRolloutDecision)
        or decision.arm != "candidate"
        or decision.category != "card_reward"
        or not isinstance(decision.card_terms, CardAcceptancePolicyTerms)
        or len(decision.card_terms.family_order) < CANARY_MIN_FAMILY_COUNT
        or decision.card_terms.selected_action_id != decision.selected_action_id
        or decision.candidate_features is None
        or not decision.candidates
        or sum(
            candidate.get("action_id") == decision.selected_action_id
            for candidate in decision.candidates
        )
        != 1
    ):
        raise SuccessorRuntimeError("shadow decision is not a valid multi-family card reward")

    original_bootstrap = encode_paired_bootstrap(bootstrap)
    original_optimizer = encode_optimizer_state(candidate_optimizer)
    shadow_bootstrap = restore_paired_bootstrap(original_bootstrap)
    shadow_optimizers = build_arm_optimizers(shadow_bootstrap)
    shadow_optimizer = restore_optimizer_state(
        shadow_optimizers.candidate,
        original_optimizer,
    )
    named = _arm_named_trainable_parameters(shadow_bootstrap, arm="candidate")
    parameters = tuple(parameter for _, parameter in named)
    if parameters != _validated_registered_adam(shadow_optimizer):
        raise SuccessorRuntimeError("shadow optimizer parameter order differs")

    output_before = forward_card_policy(
        shadow_bootstrap,
        arm="candidate",
        state_features=decision.state_features.detach().clone(),
        candidate_features=decision.candidate_features.detach().clone(),
        candidates=decision.candidates,
    )
    terms_before = build_card_acceptance_policy_terms(
        output_before.family_logits,
        output_before.conditional_logits,
        decision.candidates,
        decision.selected_action_id,
        category="card_reward",
    )
    if terms_before.selected_family != decision.card_terms.selected_family:
        raise SuccessorRuntimeError("shadow selected family differs from sealed decision")
    family_loss = -terms_before.selected_family_log_probability
    entropy_loss = -ENTROPY_COEFFICIENT * terms_before.family_entropy
    loss = family_loss + entropy_loss
    if not bool(torch.isfinite(loss).item()):
        raise SuccessorRuntimeError("shadow family-only loss is not finite")

    family_before = _encode_model_state(
        shadow_bootstrap.candidate.card_policy.family_head
    )
    conditional_before = _encode_model_state(
        shadow_bootstrap.candidate.card_policy.conditional_ranker
    )
    conditional_optimizer_before = _optimizer_parameter_state(
        shadow_optimizer,
        named,
        prefix="conditional_ranker.",
    )
    optimizer_before = encode_optimizer_state(shadow_optimizer)
    conditional_output_before = _conditional_output_evidence(
        output_before,
        terms_before,
    )

    shadow_optimizer.zero_grad(set_to_none=True)
    gradients = torch.autograd.grad(loss, parameters, allow_unused=True)
    family_gradients: list[torch.Tensor] = []
    encoded_gradients: dict[str, Any] = {}
    for (name, parameter), gradient in zip(named, gradients, strict=True):
        if name.startswith("family_head."):
            if gradient is None or not bool(torch.isfinite(gradient).all().item()):
                raise SuccessorRuntimeError("shadow family gradient is invalid")
            parameter.grad = gradient.detach().clone()
            family_gradients.append(parameter.grad)
            encoded_gradients[name] = _encode_tensor(parameter.grad)
        else:
            if gradient is not None and bool(torch.count_nonzero(gradient).item()):
                raise SuccessorRuntimeError("shadow conditional gradient is nonzero")
            parameter.grad = None
    if not family_gradients or not any(
        bool(torch.count_nonzero(gradient).item()) for gradient in family_gradients
    ):
        raise SuccessorRuntimeError("shadow family gradient must be finite and nonzero")
    preclip_global_norm = float(
        torch.nn.utils.clip_grad_norm_(parameters, 1.0).item()
    )
    applied = tuple(
        parameter.grad
        for parameter in parameters
        if parameter.grad is not None
    )
    postclip_global_norm = _global_gradient_norm(applied)
    if (
        not math.isfinite(preclip_global_norm)
        or postclip_global_norm > 1.0 + 1e-6
    ):
        raise SuccessorRuntimeError("shadow global gradient clip differs")
    shadow_optimizer.step()

    family_after = _encode_model_state(
        shadow_bootstrap.candidate.card_policy.family_head
    )
    conditional_after = _encode_model_state(
        shadow_bootstrap.candidate.card_policy.conditional_ranker
    )
    conditional_optimizer_after = _optimizer_parameter_state(
        shadow_optimizer,
        named,
        prefix="conditional_ranker.",
    )
    optimizer_after = encode_optimizer_state(shadow_optimizer)
    with torch.no_grad():
        output_after = forward_card_policy(
            shadow_bootstrap,
            arm="candidate",
            state_features=decision.state_features.detach().clone(),
            candidate_features=decision.candidate_features.detach().clone(),
            candidates=decision.candidates,
        )
        terms_after = build_card_acceptance_policy_terms(
            output_after.family_logits,
            output_after.conditional_logits,
            decision.candidates,
            decision.selected_action_id,
            category="card_reward",
        )
    conditional_output_after = _conditional_output_evidence(
        output_after,
        terms_after,
    )
    family_changed = family_after != family_before
    conditional_unchanged = conditional_after == conditional_before
    conditional_optimizer_unchanged = (
        conditional_optimizer_after == conditional_optimizer_before
    )
    conditional_output_unchanged = (
        conditional_output_after == conditional_output_before
    )
    if (
        not family_changed
        or not conditional_unchanged
        or not conditional_optimizer_unchanged
        or not conditional_output_unchanged
    ):
        raise SuccessorRuntimeError("shadow family-only invariance differs")
    if (
        encode_paired_bootstrap(bootstrap) != original_bootstrap
        or encode_optimizer_state(candidate_optimizer) != original_optimizer
    ):
        raise SuccessorRuntimeError("shadow step mutated a sealed arm")
    evidence = {
        "advantage": 1.0,
        "candidate_optimizer_state_after": optimizer_after,
        "candidate_optimizer_state_before": optimizer_before,
        "conditional_optimizer_state_unchanged": conditional_optimizer_unchanged,
        "conditional_output_after": conditional_output_after,
        "conditional_output_before": conditional_output_before,
        "conditional_output_unchanged": conditional_output_unchanged,
        "conditional_parameter_unchanged": conditional_unchanged,
        "decision_id": decision.decision_id,
        "entropy_coefficient": ENTROPY_COEFFICIENT,
        "entropy_loss": float(entropy_loss.detach().item()),
        "family_gradient_nonzero": True,
        "family_gradients": encoded_gradients,
        "family_loss": float(family_loss.detach().item()),
        "family_parameter_changed": family_changed,
        "family_state_after": family_after,
        "family_state_before": family_before,
        "loss": float(loss.detach().item()),
        "postclip_global_norm": postclip_global_norm,
        "preclip_global_norm": preclip_global_norm,
        "selected_family": terms_before.selected_family,
        "gradient_reset_mode": "set_to_none=true",
        "shadow_optimizer_steps": 1,
    }
    return {**evidence, "evidence_sha256": canonical_runtime_sha256(evidence)}


def _validated_canary_seeds(value: Sequence[int]) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SuccessorRuntimeError("canary seeds must be a sequence")
    seeds = tuple(value)
    if (
        len(seeds) != CANARY_PAIR_COUNT
        or any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in seeds
        )
        or seeds != tuple(sorted(set(seeds)))
    ):
        raise SuccessorRuntimeError("canary requires 128 ascending unique seeds")
    return seeds


def run_structural_canary(
    bootstrap: PairedBootstrap,
    *,
    candidate_optimizer: torch.optim.Optimizer,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    arm_bindings: Mapping[str, Mapping[str, str]],
    publish_commitment: Callable[[Mapping[str, Any], bytes], None],
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> StructuralCanaryResult:
    """Run the fixed first-output, exact-replay, structural 128-pair canary."""
    _validate_rollout_bootstrap(bootstrap)
    normalized_seeds = _validated_canary_seeds(seeds)
    normalized_bindings = _normalize_canary_arm_bindings(arm_bindings)
    if not callable(environment_factory) or not callable(publish_commitment):
        raise SuccessorRuntimeError("canary factory and publisher must be callable")
    expected_parameters = tuple(
        parameter
        for _, parameter in _arm_named_trainable_parameters(
            bootstrap,
            arm="candidate",
        )
    )
    if expected_parameters != _validated_registered_adam(candidate_optimizer):
        raise SuccessorRuntimeError("canary candidate optimizer ownership differs")
    if not callable(clock):
        raise SuccessorRuntimeError("canary clock must be callable")
    now = float(clock())
    active_deadline = now + MAX_CHARGED_SECONDS if deadline is None else float(deadline)
    if (
        not math.isfinite(now)
        or not math.isfinite(active_deadline)
        or active_deadline < now
        or active_deadline > now + MAX_CHARGED_SECONDS
    ):
        raise SuccessorRuntimeError("canary deadline exceeds the registered bound")
    original_bootstrap = encode_paired_bootstrap(bootstrap)
    original_optimizer = encode_optimizer_state(candidate_optimizer)
    commitments: list[dict[str, Any]] = []
    replays: list[dict[str, Any]] = []
    candidate_rollouts: list[ArmEpisodeRollout] = []
    previous_sha256 = "0" * 64

    for seed_index, seed in enumerate(normalized_seeds):
        first = rollout_paired_frozen_evaluation(
            bootstrap,
            environment_factory=environment_factory,
            seed=seed,
            deadline=active_deadline,
            clock=clock,
        )
        if first.seed != seed:
            raise SuccessorRuntimeError("canary first-run seed differs")
        first_by_arm = {
            "candidate": first.candidate,
            "control": first.control,
        }
        first_commitments: dict[str, dict[str, Any]] = {}
        for arm in ("candidate", "control"):
            rollout = first_by_arm[arm]
            if rollout.arm != arm or rollout.seed != seed:
                raise SuccessorRuntimeError("canary first-run arm coordinate differs")
            commitment, stored_output = _build_canary_commitment(
                rollout=rollout,
                arm_binding=normalized_bindings[arm],
                seed_index=seed_index,
                sequence_index=len(commitments),
                previous_sha256=previous_sha256,
            )
            publish_commitment(copy.deepcopy(commitment), stored_output)
            commitments.append(commitment)
            first_commitments[arm] = commitment
            previous_sha256 = commitment["commitment_sha256"]

        replay = rollout_paired_frozen_evaluation(
            bootstrap,
            environment_factory=environment_factory,
            seed=seed,
            deadline=active_deadline,
            clock=clock,
        )
        if replay.seed != seed:
            raise SuccessorRuntimeError("canary replay seed differs")
        replay_by_arm = {
            "candidate": replay.candidate,
            "control": replay.control,
        }
        for arm in ("candidate", "control"):
            replay_output_sha256 = canonical_runtime_sha256(
                _arm_canary_output(replay_by_arm[arm])
            )
            if replay_output_sha256 != first_commitments[arm]["output_sha256"]:
                raise SuccessorRuntimeError(
                    f"canary {arm} replay differs from first-output commitment"
                )
            replay_body = {
                "arm": arm,
                "first_commitment_sha256": first_commitments[arm][
                    "commitment_sha256"
                ],
                "output_sha256": replay_output_sha256,
                "schema_version": CANARY_REPLAY_SCHEMA_VERSION,
                "seed": seed,
                "seed_index": seed_index,
                "sequence_index": first_commitments[arm]["sequence_index"],
            }
            replays.append(
                {
                    **replay_body,
                    "replay_sha256": canonical_runtime_sha256(replay_body),
                }
            )
        candidate_rollouts.append(first.candidate)

    concentration = classify_canary_concentration(candidate_rollouts)
    shadow_step: Mapping[str, Any] | None = None
    verdict = "canary_failed_concentration"
    shadow_optimizer_steps = 0
    if concentration["passed"]:
        first_valid = next(
            decision
            for rollout in candidate_rollouts
            for decision in rollout.decisions
            if decision.category == "card_reward"
            and isinstance(decision.card_terms, CardAcceptancePolicyTerms)
            and len(decision.card_terms.family_order) >= CANARY_MIN_FAMILY_COUNT
        )
        shadow_step = apply_family_only_shadow_step(
            bootstrap,
            candidate_optimizer=candidate_optimizer,
            decision=first_valid,
        )
        if shadow_step.get("shadow_optimizer_steps") != 1:
            raise SuccessorRuntimeError("canary shadow step count differs")
        shadow_optimizer_steps = 1
        verdict = "canary_passed"

    if (
        encode_paired_bootstrap(bootstrap) != original_bootstrap
        or encode_optimizer_state(candidate_optimizer) != original_optimizer
    ):
        raise SuccessorRuntimeError("structural canary mutated a sealed arm")
    return StructuralCanaryResult(
        verdict=verdict,
        seeds=normalized_seeds,
        commitments=tuple(commitments),
        replays=tuple(replays),
        concentration=concentration,
        shadow_step=shadow_step,
        resource_use={
            "canary_environment_accesses": 4 * len(normalized_seeds),
            "shadow_optimizer_steps": shadow_optimizer_steps,
        },
    )


def paired_floor_bootstrap_interval(
    differences: Sequence[float],
) -> dict[str, int | float | str]:
    """Reproduce the fixed seed-0, 10,000-resample paired-floor interval."""
    if isinstance(differences, (str, bytes)) or not isinstance(
        differences, Sequence
    ):
        raise SuccessorRuntimeError("paired floor differences must be a sequence")
    normalized: list[float] = []
    for value in differences:
        if isinstance(value, bool) or not isinstance(value, Real):
            raise SuccessorRuntimeError("paired floor difference must be numeric")
        converted = float(value)
        if not math.isfinite(converted):
            raise SuccessorRuntimeError("paired floor difference must be finite")
        normalized.append(converted)
    if len(normalized) != HOLDOUT_PAIR_COUNT:
        raise SuccessorRuntimeError("paired floor bootstrap requires 512 values")

    generator = random.Random(HOLDOUT_BOOTSTRAP_SEED)
    means: list[float] = []
    for _ in range(HOLDOUT_BOOTSTRAP_RESAMPLES):
        total = 0.0
        for _ in range(HOLDOUT_PAIR_COUNT):
            total += normalized[generator.randrange(HOLDOUT_PAIR_COUNT)]
        means.append(total / HOLDOUT_PAIR_COUNT)
    means.sort()

    def quantile(probability: float) -> float:
        position = (HOLDOUT_BOOTSTRAP_RESAMPLES - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        fraction = position - lower
        return means[lower] + fraction * (means[upper] - means[lower])

    return {
        "bootstrap_seed": HOLDOUT_BOOTSTRAP_SEED,
        "lower": quantile(0.025),
        "pair_count": HOLDOUT_PAIR_COUNT,
        "quantile_method": "linear-position-(n-1)-p-v1",
        "resample_count": HOLDOUT_BOOTSTRAP_RESAMPLES,
        "upper": quantile(0.975),
    }


def classify_holdout_outcome(
    *,
    candidate_victories: int,
    control_victories: int,
    paired_floor_lower: float,
) -> dict[str, Any]:
    """Classify one of the six victory-comparison x floor-signal cells."""
    for label, value in (
        ("candidate", candidate_victories),
        ("control", control_victories),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= HOLDOUT_PAIR_COUNT
        ):
            raise SuccessorRuntimeError(f"{label} victory count is invalid")
    if isinstance(paired_floor_lower, bool) or not isinstance(
        paired_floor_lower, Real
    ):
        raise SuccessorRuntimeError("paired floor lower bound is invalid")
    lower = float(paired_floor_lower)
    if not math.isfinite(lower):
        raise SuccessorRuntimeError("paired floor lower bound must be finite")

    if candidate_victories > control_victories:
        comparison = "greater"
    elif candidate_victories == control_victories:
        comparison = "equal"
    else:
        comparison = "fewer"
    floor_signal = lower > 0.0
    if comparison == "greater" and floor_signal:
        outcome = "victory_and_floor_signal"
    elif comparison == "equal" and floor_signal:
        outcome = "floor_only_signal"
    elif (comparison == "greater" and not floor_signal) or (
        comparison == "fewer" and floor_signal
    ):
        outcome = "inconclusive_signal"
    else:
        outcome = "no_learning_signal"
    return {
        "candidate_victories": candidate_victories,
        "control_victories": control_victories,
        "floor_signal": floor_signal,
        "outcome_class": outcome,
        "paired_floor_lower": lower,
        "victory_comparison": comparison,
    }


def _validated_holdout_seeds(value: Sequence[int]) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SuccessorRuntimeError("holdout seeds must be a sequence")
    seeds = tuple(value)
    if (
        len(seeds) != HOLDOUT_PAIR_COUNT
        or any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in seeds
        )
        or seeds != tuple(sorted(set(seeds)))
    ):
        raise SuccessorRuntimeError("holdout requires 512 ascending unique seeds")
    return seeds


def _normalize_verified_canary(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {
        "terminal_sha256",
        "verdict",
        "verified",
    }:
        raise SuccessorRuntimeError("verified canary binding is missing or incomplete")
    digest = value["terminal_sha256"]
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
        or value["verdict"] != "canary_passed"
        or value["verified"] is not True
    ):
        raise SuccessorRuntimeError("verified canary did not pass exactly")
    return {
        "terminal_sha256": digest,
        "verdict": "canary_passed",
        "verified": True,
    }


def _validated_terminal_victory(rollout: ArmEpisodeRollout) -> int:
    value = rollout.terminal_victory
    if isinstance(value, bool) or not isinstance(value, int) or value not in {0, 1}:
        raise SuccessorRuntimeError("holdout terminal victory is invalid")
    state = rollout.final_snapshot.get("state")
    if not isinstance(state, Mapping):
        raise SuccessorRuntimeError("holdout terminal state is invalid")
    expected_outcome = "player_victory" if value else "player_loss"
    if state.get("outcome") != expected_outcome:
        raise SuccessorRuntimeError("holdout victory and terminal outcome differ")
    return value


def _holdout_pair_evidence(
    pair: PairedEpisodeRollout,
    *,
    expected_seed: int,
    seed_index: int,
) -> dict[str, Any]:
    if not isinstance(pair, PairedEpisodeRollout) or pair.seed != expected_seed:
        raise SuccessorRuntimeError("holdout pair seed differs")
    if (
        pair.candidate.arm != "candidate"
        or pair.control.arm != "control"
        or pair.candidate.seed != expected_seed
        or pair.control.seed != expected_seed
    ):
        raise SuccessorRuntimeError("holdout pair arm coordinate differs")
    candidate_output = _arm_canary_output(pair.candidate)
    control_output = _arm_canary_output(pair.control)
    candidate_floor = float(pair.candidate.floor_progress)
    control_floor = float(pair.control.floor_progress)
    difference = candidate_floor - control_floor
    if not all(
        math.isfinite(value)
        for value in (candidate_floor, control_floor, difference)
    ):
        raise SuccessorRuntimeError("holdout floor_progress must be finite")
    return {
        "candidate_floor_progress": candidate_floor,
        "candidate_output_sha256": canonical_runtime_sha256(candidate_output),
        "candidate_victory": _validated_terminal_victory(pair.candidate),
        "control_floor_progress": control_floor,
        "control_output_sha256": canonical_runtime_sha256(control_output),
        "control_victory": _validated_terminal_victory(pair.control),
        "floor_progress_difference": difference,
        "seed": expected_seed,
        "seed_index": seed_index,
    }


def _holdout_family_observations(
    rollouts: Sequence[ArmEpisodeRollout],
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for rollout in rollouts:
        for decision in rollout.decisions:
            terms = decision.card_terms
            if (
                decision.category != "card_reward"
                or not isinstance(terms, CardAcceptancePolicyTerms)
                or len(terms.family_order) < CANARY_MIN_FAMILY_COUNT
            ):
                continue
            rows.append(
                {
                    "decision_id": decision.decision_id,
                    "decision_index": decision.decision_index,
                    "family_order": list(terms.family_order),
                    "seed": rollout.seed,
                    "selected_family": terms.selected_family,
                    "unique_greedy_family_id": terms.unique_greedy_family_id,
                }
            )
    rows.sort(key=lambda row: (row["seed"], row["decision_index"], row["decision_id"]))
    return tuple(rows)


def run_untouched_holdout(
    bootstrap: PairedBootstrap,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    arm_bindings: Mapping[str, Mapping[str, str]],
    verified_canary: Mapping[str, Any],
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> UntouchedHoldoutResult:
    """Run both frozen arms once on each untouched registered holdout seed."""
    _validate_rollout_bootstrap(bootstrap)
    normalized_canary = _normalize_verified_canary(verified_canary)
    normalized_seeds = _validated_holdout_seeds(seeds)
    normalized_bindings = _normalize_canary_arm_bindings(arm_bindings)
    if not callable(environment_factory) or not callable(clock):
        raise SuccessorRuntimeError("holdout factory and clock must be callable")
    now = float(clock())
    active_deadline = now + MAX_CHARGED_SECONDS if deadline is None else float(deadline)
    if (
        not math.isfinite(now)
        or not math.isfinite(active_deadline)
        or active_deadline < now
        or active_deadline > now + MAX_CHARGED_SECONDS
    ):
        raise SuccessorRuntimeError("holdout deadline exceeds the registered bound")
    original_bootstrap = encode_paired_bootstrap(bootstrap)
    pair_rows: list[dict[str, Any]] = []
    candidate_rollouts: list[ArmEpisodeRollout] = []
    for seed_index, seed in enumerate(normalized_seeds):
        pair = rollout_paired_frozen_evaluation(
            bootstrap,
            environment_factory=environment_factory,
            seed=seed,
            deadline=active_deadline,
            clock=clock,
        )
        pair_rows.append(
            _holdout_pair_evidence(
                pair,
                expected_seed=seed,
                seed_index=seed_index,
            )
        )
        candidate_rollouts.append(pair.candidate)
    if encode_paired_bootstrap(bootstrap) != original_bootstrap:
        raise SuccessorRuntimeError("holdout mutated a frozen arm")

    concentration = classify_canary_concentration(candidate_rollouts)
    family_observations = _holdout_family_observations(candidate_rollouts)
    victory_counts = {
        "candidate": sum(row["candidate_victory"] for row in pair_rows),
        "control": sum(row["control_victory"] for row in pair_rows),
    }
    common = {
        "seeds": normalized_seeds,
        "pairs": tuple(pair_rows),
        "family_observations": family_observations,
        "concentration": concentration,
        "victory_counts": victory_counts,
        "arm_bindings": normalized_bindings,
        "verified_canary": normalized_canary,
        "resource_use": {"holdout_environment_accesses": 2 * len(normalized_seeds)},
    }
    if not concentration["passed"]:
        return UntouchedHoldoutResult(
            verdict="holdout_failed_concentration",
            outcome_class=None,
            bootstrap=None,
            **common,
        )

    interval = paired_floor_bootstrap_interval(
        tuple(row["floor_progress_difference"] for row in pair_rows)
    )
    outcome = classify_holdout_outcome(
        candidate_victories=victory_counts["candidate"],
        control_victories=victory_counts["control"],
        paired_floor_lower=float(interval["lower"]),
    )
    return UntouchedHoldoutResult(
        verdict="holdout_completed",
        outcome_class=outcome["outcome_class"],
        bootstrap=interval,
        **common,
    )


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
    folded = source_value[:BASELINE_FEATURE_DIM].clone()
    for offset in range(BASELINE_FEATURE_DIM, BASELINE_SOURCE_DIM, BASELINE_FEATURE_DIM):
        folded.add_(source_value[offset : offset + BASELINE_FEATURE_DIM])
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


def _build_fold_normal_equations(
    *,
    held_out_ids: tuple[str, ...],
    trajectory_order: Sequence[str],
    by_trajectory: Mapping[str, tuple[ArmBaselineDecision, ...]],
) -> tuple[torch.Tensor, torch.Tensor]:
    """Accumulate the registered trajectory-weighted ridge moments in batches."""
    held_out_set = set(held_out_ids)
    width = BASELINE_FEATURE_DIM + 1
    normal_matrix = torch.zeros((width, width), dtype=torch.float64)
    rhs = torch.zeros(width, dtype=torch.float64)
    for trajectory_id in trajectory_order:
        if trajectory_id in held_out_set:
            continue
        trajectory = by_trajectory[trajectory_id]
        state_features = torch.stack(
            tuple(decision.state_features for decision in trajectory)
        ).to(dtype=torch.float64)
        intercept = torch.ones((len(trajectory), 1), dtype=torch.float64)
        augmented = torch.cat((intercept, state_features), dim=1)
        targets = torch.tensor(
            tuple(float(decision.raw_return) for decision in trajectory),
            dtype=torch.float64,
        )
        weight = 1.0 / (FIT_TRAJECTORIES_PER_FOLD * len(trajectory))
        normal_matrix.addmm_(
            augmented.transpose(0, 1),
            augmented,
            beta=1.0,
            alpha=weight,
        )
        rhs.addmv_(
            augmented.transpose(0, 1),
            targets,
            beta=1.0,
            alpha=weight,
        )
    return normal_matrix, rhs


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
    normal_matrix, rhs = _build_fold_normal_equations(
        held_out_ids=held_out_ids,
        trajectory_order=trajectory_order,
        by_trajectory=by_trajectory,
    )
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
    product_sums = torch.sum(
        torch.abs(normal_matrix) * torch.abs(coefficients).unsqueeze(0),
        dim=1,
    )
    residuals = torch.mv(normal_matrix, coefficients) - rhs
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


def _arm_named_trainable_parameters(
    bootstrap: PairedBootstrap,
    *,
    arm: ArmName,
) -> tuple[tuple[str, torch.nn.Parameter], ...]:
    normalized_arm = _validated_arm(arm)
    if normalized_arm == "candidate":
        rows = tuple(
            (f"family_head.{name}", parameter)
            for name, parameter in (
                bootstrap.candidate.card_policy.family_head.named_parameters()
            )
        ) + tuple(
            (f"conditional_ranker.{name}", parameter)
            for name, parameter in (
                bootstrap.candidate.card_policy.conditional_ranker.named_parameters()
            )
        )
    else:
        rows = tuple(
            (f"shared_card_ranker.{name}", parameter)
            for name, parameter in (
                bootstrap.control.shared_card_ranker.named_parameters()
            )
        )
    names = tuple(name for name, _ in rows)
    if not rows or len(set(names)) != len(rows):
        raise SuccessorRuntimeError("arm trainable parameter names differ")
    return rows


def _apply_paired_cross_fitted_chunk_update(
    bootstrap: PairedBootstrap,
    optimizers: ArmOptimizers,
    episodes: Sequence[PairedEpisodeRollout],
    *,
    reconstruct_components: bool,
) -> PairedChunkUpdateEvidence:
    """Validate both arm updates before applying exactly one Adam step per arm."""
    _validate_rollout_bootstrap(bootstrap)
    if not isinstance(optimizers, ArmOptimizers):
        raise SuccessorRuntimeError("paired update optimizers differ")
    baselines = build_paired_cross_fitted_baselines(episodes)
    candidate_rows = build_arm_card_reward_rows(
        episodes,
        arm="candidate",
        baseline=baselines.candidate,
    )
    control_rows = build_arm_card_reward_rows(
        episodes,
        arm="control",
        baseline=baselines.control,
    )
    candidate_objective = build_arm_card_reward_objective(candidate_rows)
    control_objective = build_arm_card_reward_objective(control_rows)

    candidate_named = _arm_named_trainable_parameters(
        bootstrap,
        arm="candidate",
    )
    control_named = _arm_named_trainable_parameters(
        bootstrap,
        arm="control",
    )
    frozen_before = (
        _model_state_bytes(bootstrap.candidate.frozen_noncard_ranker),
        _model_state_bytes(bootstrap.control.frozen_noncard_ranker),
    )
    generator_before = {
        name: generator.get_state().clone()
        for name, generator in bootstrap.generators.items()
    }
    try:
        candidate_prepared = _prepare_arm_optimizer_step(
            optimizers.candidate,
            candidate_objective,
            parameters=tuple(parameter for _, parameter in candidate_named),
            parameter_names=tuple(name for name, _ in candidate_named),
            reconstruct_components=reconstruct_components,
        )
        control_prepared = _prepare_arm_optimizer_step(
            optimizers.control,
            control_objective,
            parameters=tuple(parameter for _, parameter in control_named),
            parameter_names=tuple(name for name, _ in control_named),
            reconstruct_components=reconstruct_components,
        )
    except Exception:
        optimizers.candidate.zero_grad(set_to_none=True)
        optimizers.control.zero_grad(set_to_none=True)
        raise

    candidate_step = _commit_prepared_arm_step(
        optimizers.candidate,
        candidate_prepared,
    )
    control_step = _commit_prepared_arm_step(
        optimizers.control,
        control_prepared,
    )
    _validate_rollout_bootstrap(bootstrap)
    frozen_after = (
        _model_state_bytes(bootstrap.candidate.frozen_noncard_ranker),
        _model_state_bytes(bootstrap.control.frozen_noncard_ranker),
    )
    if frozen_after != frozen_before:
        raise SuccessorRuntimeError("paired update changed frozen non-card bytes")
    if any(
        not torch.equal(bootstrap.generators[name].get_state(), before)
        for name, before in generator_before.items()
    ):
        raise SuccessorRuntimeError("paired update changed an arm generator")

    return PairedChunkUpdateEvidence(
        seeds=baselines.seeds,
        baselines=baselines,
        candidate=ArmChunkUpdateEvidence(
            arm="candidate",
            decision_ids=tuple(
                decision.decision_id
                for decision in baselines.candidate.decisions
                if decision.category == "card_reward"
            ),
            objective=candidate_objective,
            optimizer_step=candidate_step,
        ),
        control=ArmChunkUpdateEvidence(
            arm="control",
            decision_ids=tuple(
                decision.decision_id
                for decision in baselines.control.decisions
                if decision.category == "card_reward"
            ),
            objective=control_objective,
            optimizer_step=control_step,
        ),
    )


def apply_paired_cross_fitted_chunk_update(
    bootstrap: PairedBootstrap,
    optimizers: ArmOptimizers,
    episodes: Sequence[PairedEpisodeRollout],
) -> PairedChunkUpdateEvidence:
    """Apply the full qualification-grade gradient evidence update."""
    return _apply_paired_cross_fitted_chunk_update(
        bootstrap,
        optimizers,
        episodes,
        reconstruct_components=True,
    )


def apply_paired_cross_fitted_chunk_update_exploratory(
    bootstrap: PairedBootstrap,
    optimizers: ArmOptimizers,
    episodes: Sequence[PairedEpisodeRollout],
) -> PairedChunkUpdateEvidence:
    """Apply the same total loss with one backward pass per exploratory arm."""
    return _apply_paired_cross_fitted_chunk_update(
        bootstrap,
        optimizers,
        episodes,
        reconstruct_components=False,
    )


def classify_candidate_family_saturation(
    completed_chunks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply the candidate-only exact trailing-four family saturation rule."""
    if isinstance(completed_chunks, (str, bytes)) or not isinstance(
        completed_chunks, Sequence
    ):
        raise SuccessorRuntimeError("completed chunks must be a sequence")
    chunks = tuple(completed_chunks)
    if len(chunks) > 8:
        raise SuccessorRuntimeError("completed chunks exceed the registered bound")
    normalized: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, Mapping) or set(chunk) != {
            "candidate_card_decisions",
            "chunk_index",
        }:
            raise SuccessorRuntimeError("completed chunk fields differ")
        if chunk["chunk_index"] != index:
            raise SuccessorRuntimeError(
                "completed chunk indices must be contiguous"
            )
        decisions = chunk["candidate_card_decisions"]
        if isinstance(decisions, (str, bytes)) or not isinstance(
            decisions, Sequence
        ):
            raise SuccessorRuntimeError(
                "candidate card decisions must be a sequence"
            )
        normalized_rows: list[dict[str, Any]] = []
        for row in decisions:
            if not isinstance(row, Mapping) or set(row) != {
                "multi_family",
                "unique_greedy_family_id",
            }:
                raise SuccessorRuntimeError(
                    "candidate family diagnostic fields differ"
                )
            if not isinstance(row["multi_family"], bool):
                raise SuccessorRuntimeError(
                    "candidate multi-family diagnostic must be boolean"
                )
            family = row["unique_greedy_family_id"]
            if family is not None and (
                not isinstance(family, str) or not family
            ):
                raise SuccessorRuntimeError(
                    "candidate unique greedy family is invalid"
                )
            normalized_rows.append(dict(row))
        normalized.append(
            {
                "candidate_card_decisions": normalized_rows,
                "chunk_index": index,
            }
        )

    window = normalized[-4:]
    window_indices = [int(chunk["chunk_index"]) for chunk in window]
    if len(window) < 4:
        return {
            "family": None,
            "multi_family_decisions": 0,
            "stop": False,
            "window_chunk_indices": window_indices,
        }
    rows = [
        row
        for chunk in window
        for row in chunk["candidate_card_decisions"]
        if row["multi_family"] is True
    ]
    families = [row["unique_greedy_family_id"] for row in rows]
    if (
        len(rows) >= 64
        and all(isinstance(family, str) and family for family in families)
        and len(set(families)) == 1
    ):
        return {
            "family": families[0],
            "multi_family_decisions": len(rows),
            "stop": True,
            "window_chunk_indices": window_indices,
        }
    return {
        "family": None,
        "multi_family_decisions": len(rows),
        "stop": False,
        "window_chunk_indices": window_indices,
    }


def initialize_paired_training_runtime() -> PairedTrainingRuntime:
    """Create the matched zero-progress runtime before any environment access."""
    bootstrap = build_matched_bootstrap()
    return PairedTrainingRuntime(
        bootstrap=bootstrap,
        optimizers=build_arm_optimizers(bootstrap),
    )


def _validate_optimizer_step_coordinate(
    optimizer: torch.optim.Optimizer,
    *,
    expected_steps: int,
) -> None:
    parameters = _validated_registered_adam(optimizer)
    _validate_decoded_adam_state(optimizer, optimizer.state_dict())
    if expected_steps == 0:
        if optimizer.state:
            raise SuccessorRuntimeError(
                "zero-update optimizer cannot contain Adam moments"
            )
        return
    if len(optimizer.state) != len(parameters):
        raise SuccessorRuntimeError("Adam moment parameter coverage differs")
    for parameter in parameters:
        state = optimizer.state.get(parameter)
        if not isinstance(state, dict) or set(state) != {
            "step",
            "exp_avg",
            "exp_avg_sq",
        }:
            raise SuccessorRuntimeError("Adam moment fields differ")
        step = state["step"]
        if (
            not isinstance(step, torch.Tensor)
            or step.shape != torch.Size([])
            or float(step.item()) != float(expected_steps)
        ):
            raise SuccessorRuntimeError("Adam step coordinate differs")


def _validate_paired_training_runtime(runtime: PairedTrainingRuntime) -> None:
    if not isinstance(runtime, PairedTrainingRuntime):
        raise SuccessorRuntimeError("paired training runtime type differs")
    _validate_rollout_bootstrap(runtime.bootstrap)
    if not isinstance(runtime.optimizers, ArmOptimizers):
        raise SuccessorRuntimeError("paired training optimizers differ")
    for arm, optimizer in (
        ("candidate", runtime.optimizers.candidate),
        ("control", runtime.optimizers.control),
    ):
        expected_parameters = tuple(
            parameter
            for _, parameter in _arm_named_trainable_parameters(
                runtime.bootstrap,
                arm=arm,
            )
        )
        actual_parameters = _validated_registered_adam(optimizer)
        if len(actual_parameters) != len(expected_parameters) or any(
            actual is not expected
            for actual, expected in zip(
                actual_parameters, expected_parameters, strict=True
            )
        ):
            raise SuccessorRuntimeError(
                f"{arm} optimizer parameter ownership differs"
            )

    coordinates = (
        runtime.next_chunk_index,
        runtime.completed_pairs,
        runtime.completed_decisions,
        runtime.training_environment_accesses,
        runtime.candidate_optimizer_updates,
        runtime.control_optimizer_updates,
        runtime.training_optimizer_steps,
    )
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in coordinates
    ):
        raise SuccessorRuntimeError("training runtime coordinate is invalid")
    if not 0 <= runtime.next_chunk_index <= 8:
        raise SuccessorRuntimeError("training chunk coordinate exceeds eight")
    expected_chunk_count = runtime.next_chunk_index
    if (
        runtime.completed_pairs != 64 * expected_chunk_count
        or runtime.training_environment_accesses != 128 * expected_chunk_count
        or runtime.candidate_optimizer_updates != expected_chunk_count
        or runtime.control_optimizer_updates != expected_chunk_count
        or runtime.training_optimizer_steps != 2 * expected_chunk_count
    ):
        raise SuccessorRuntimeError("training resource coordinates differ")
    if runtime.completed_decisions > (
        runtime.training_environment_accesses * MAX_DECISIONS_PER_EPISODE
    ):
        raise SuccessorRuntimeError("training decision coordinate exceeds bound")
    if not isinstance(runtime.completed_chunk_summaries, list) or len(
        runtime.completed_chunk_summaries
    ) != expected_chunk_count:
        raise SuccessorRuntimeError("training chunk summaries differ")
    saturation = classify_candidate_family_saturation(
        runtime.completed_chunk_summaries
    )
    if not isinstance(runtime.stopped_for_family_saturation, bool) or (
        runtime.stopped_for_family_saturation is not bool(saturation["stop"])
    ):
        raise SuccessorRuntimeError("training saturation coordinate differs")
    _validate_optimizer_step_coordinate(
        runtime.optimizers.candidate,
        expected_steps=runtime.candidate_optimizer_updates,
    )
    _validate_optimizer_step_coordinate(
        runtime.optimizers.control,
        expected_steps=runtime.control_optimizer_updates,
    )


def _candidate_chunk_summary(
    episodes: Sequence[PairedEpisodeRollout],
    *,
    chunk_index: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for pair in episodes:
        for decision in pair.candidate.decisions:
            if decision.category != "card_reward":
                continue
            terms = decision.card_terms
            if not isinstance(terms, CardAcceptancePolicyTerms):
                raise SuccessorRuntimeError(
                    "candidate card decision lacks policy terms"
                )
            rows.append(
                {
                    "multi_family": len(terms.family_order) > 1,
                    "unique_greedy_family_id": terms.unique_greedy_family_id,
                }
            )
    return {
        "candidate_card_decisions": rows,
        "chunk_index": chunk_index,
    }


def _paired_training_checkpoint_object(
    runtime: PairedTrainingRuntime,
) -> dict[str, Any]:
    _validate_paired_training_runtime(runtime)
    return {
        "bootstrap": _paired_bootstrap_object(runtime.bootstrap),
        "completed_chunk_summaries": copy.deepcopy(
            runtime.completed_chunk_summaries
        ),
        "coordinates": {
            "candidate_optimizer_updates": runtime.candidate_optimizer_updates,
            "completed_decisions": runtime.completed_decisions,
            "completed_pairs": runtime.completed_pairs,
            "control_optimizer_updates": runtime.control_optimizer_updates,
            "next_chunk_index": runtime.next_chunk_index,
            "training_environment_accesses": runtime.training_environment_accesses,
            "training_optimizer_steps": runtime.training_optimizer_steps,
        },
        "optimizers": {
            "candidate": encode_optimizer_state(runtime.optimizers.candidate),
            "control": encode_optimizer_state(runtime.optimizers.control),
        },
        "schema_version": TRAINING_CHECKPOINT_SCHEMA_VERSION,
        "stopped_for_family_saturation": runtime.stopped_for_family_saturation,
    }


def encode_paired_training_checkpoint(runtime: PairedTrainingRuntime) -> bytes:
    """Encode one exact complete-boundary paired training checkpoint."""
    payload = _canonical_json_bytes(_paired_training_checkpoint_object(runtime))
    if len(payload) > MAX_BOOTSTRAP_BYTES:
        raise SuccessorRuntimeError("training checkpoint exceeds its byte ceiling")
    return payload


def restore_paired_training_checkpoint(value: object) -> PairedTrainingRuntime:
    """Restore only a canonical complete-boundary paired training checkpoint."""
    if not isinstance(value, bytes) or not value or len(value) > MAX_BOOTSTRAP_BYTES:
        raise SuccessorRuntimeError("training checkpoint bytes are invalid")
    try:
        parsed = json.loads(
            value.decode("ascii"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SuccessorRuntimeError("training checkpoint JSON is invalid") from exc
    if _canonical_json_bytes(parsed) != value:
        raise SuccessorRuntimeError("training checkpoint bytes are not canonical")
    if not isinstance(parsed, Mapping) or set(parsed) != {
        "bootstrap",
        "completed_chunk_summaries",
        "coordinates",
        "optimizers",
        "schema_version",
        "stopped_for_family_saturation",
    }:
        raise SuccessorRuntimeError("training checkpoint fields differ")
    if parsed["schema_version"] != TRAINING_CHECKPOINT_SCHEMA_VERSION:
        raise SuccessorRuntimeError("training checkpoint schema differs")
    coordinates = parsed["coordinates"]
    optimizers_value = parsed["optimizers"]
    summaries = parsed["completed_chunk_summaries"]
    if not isinstance(coordinates, Mapping) or set(coordinates) != {
        "candidate_optimizer_updates",
        "completed_decisions",
        "completed_pairs",
        "control_optimizer_updates",
        "next_chunk_index",
        "training_environment_accesses",
        "training_optimizer_steps",
    }:
        raise SuccessorRuntimeError("training checkpoint coordinates differ")
    if not isinstance(optimizers_value, Mapping) or set(optimizers_value) != {
        "candidate",
        "control",
    }:
        raise SuccessorRuntimeError("training checkpoint optimizers differ")
    if not isinstance(summaries, list):
        raise SuccessorRuntimeError("training checkpoint summaries differ")

    bootstrap = restore_paired_bootstrap(
        _canonical_json_bytes(parsed["bootstrap"])
    )
    optimizers = build_arm_optimizers(bootstrap)
    restore_optimizer_state(optimizers.candidate, optimizers_value["candidate"])
    restore_optimizer_state(optimizers.control, optimizers_value["control"])
    runtime = PairedTrainingRuntime(
        bootstrap=bootstrap,
        optimizers=optimizers,
        next_chunk_index=coordinates["next_chunk_index"],
        completed_pairs=coordinates["completed_pairs"],
        completed_decisions=coordinates["completed_decisions"],
        training_environment_accesses=coordinates[
            "training_environment_accesses"
        ],
        candidate_optimizer_updates=coordinates[
            "candidate_optimizer_updates"
        ],
        control_optimizer_updates=coordinates["control_optimizer_updates"],
        training_optimizer_steps=coordinates["training_optimizer_steps"],
        completed_chunk_summaries=copy.deepcopy(summaries),
        stopped_for_family_saturation=parsed[
            "stopped_for_family_saturation"
        ],
    )
    _validate_paired_training_runtime(runtime)
    return runtime


def _complete_paired_training_chunk(
    runtime: PairedTrainingRuntime,
    episodes: Sequence[PairedEpisodeRollout],
    *,
    chunk_index: int,
    exploratory: bool,
) -> CompletedPairedTrainingChunk:
    """Apply and checkpoint one exact 64-pair complete training chunk."""
    _validate_paired_training_runtime(runtime)
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or chunk_index != runtime.next_chunk_index
    ):
        raise SuccessorRuntimeError("training chunk index differs")
    if runtime.stopped_for_family_saturation:
        raise SuccessorRuntimeError("training already stopped for family saturation")
    if chunk_index >= 8:
        raise SuccessorRuntimeError("training already completed eight chunks")
    source = tuple(episodes)
    update_operation = (
        apply_paired_cross_fitted_chunk_update_exploratory
        if exploratory
        else apply_paired_cross_fitted_chunk_update
    )
    update = update_operation(runtime.bootstrap, runtime.optimizers, source)
    summary = _candidate_chunk_summary(source, chunk_index=chunk_index)
    runtime.completed_chunk_summaries.append(summary)
    runtime.next_chunk_index += 1
    runtime.completed_pairs += 64
    runtime.completed_decisions += sum(
        len(pair.candidate.decisions) + len(pair.control.decisions)
        for pair in source
    )
    runtime.training_environment_accesses += 128
    runtime.candidate_optimizer_updates += 1
    runtime.control_optimizer_updates += 1
    runtime.training_optimizer_steps += 2
    saturation = classify_candidate_family_saturation(
        runtime.completed_chunk_summaries
    )
    runtime.stopped_for_family_saturation = bool(saturation["stop"])
    _validate_paired_training_runtime(runtime)
    checkpoint = encode_paired_training_checkpoint(runtime)
    return CompletedPairedTrainingChunk(
        chunk_index=chunk_index,
        seeds=update.seeds,
        episodes=source,
        update=update,
        saturation=saturation,
        checkpoint=checkpoint,
    )


def complete_paired_training_chunk(
    runtime: PairedTrainingRuntime,
    episodes: Sequence[PairedEpisodeRollout],
    *,
    chunk_index: int,
) -> CompletedPairedTrainingChunk:
    """Apply and checkpoint one qualification-grade training chunk."""
    return _complete_paired_training_chunk(
        runtime,
        episodes,
        chunk_index=chunk_index,
        exploratory=False,
    )


def complete_paired_training_chunk_exploratory(
    runtime: PairedTrainingRuntime,
    episodes: Sequence[PairedEpisodeRollout],
    *,
    chunk_index: int,
) -> CompletedPairedTrainingChunk:
    """Apply and checkpoint one total-loss-only exploratory training chunk."""
    return _complete_paired_training_chunk(
        runtime,
        episodes,
        chunk_index=chunk_index,
        exploratory=True,
    )


def collect_and_complete_paired_training_chunk(
    runtime: PairedTrainingRuntime,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    chunk_index: int,
    before_environment: Callable[[ArmName, int], None],
    after_environment: Callable[[ArmName, int], None],
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
) -> CompletedPairedTrainingChunk:
    """Collect candidate then control for 64 seeds and checkpoint the update."""
    _validate_paired_training_runtime(runtime)
    if (
        not callable(environment_factory)
        or not callable(before_environment)
        or not callable(after_environment)
    ):
        raise SuccessorRuntimeError("training collection hooks must be callable")
    if not callable(clock):
        raise SuccessorRuntimeError("training collection clock must be callable")
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or chunk_index != runtime.next_chunk_index
    ):
        raise SuccessorRuntimeError("training collection chunk index differs")
    seed_values = tuple(seeds)
    if (
        len(seed_values) != 64
        or any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in seed_values
        )
        or seed_values != tuple(sorted(set(seed_values)))
    ):
        raise SuccessorRuntimeError(
            "training chunk seeds must be 64 unique ascending integers"
        )
    active_deadline = float(deadline)
    now = float(clock())
    if (
        not math.isfinite(active_deadline)
        or not math.isfinite(now)
        or active_deadline < now
        or active_deadline > now + MAX_CHARGED_SECONDS
    ):
        raise SuccessorRuntimeError(
            "training collection deadline exceeds the registered bound"
        )

    episodes: list[PairedEpisodeRollout] = []
    for seed in seed_values:
        before_environment("candidate", seed)
        candidate = rollout_arm_training_episode(
            runtime.bootstrap,
            arm="candidate",
            environment_factory=environment_factory,
            seed=seed,
            deadline=active_deadline,
            clock=clock,
        )
        after_environment("candidate", seed)
        before_environment("control", seed)
        control = rollout_arm_training_episode(
            runtime.bootstrap,
            arm="control",
            environment_factory=environment_factory,
            seed=seed,
            deadline=active_deadline,
            clock=clock,
        )
        after_environment("control", seed)
        episodes.append(
            PairedEpisodeRollout(
                seed=seed,
                candidate=candidate,
                control=control,
            )
        )
    return complete_paired_training_chunk(
        runtime,
        tuple(episodes),
        chunk_index=chunk_index,
    )


def training_progress_verdict(runtime: PairedTrainingRuntime) -> str:
    """Classify only exact complete-boundary training progress."""
    _validate_paired_training_runtime(runtime)
    if runtime.stopped_for_family_saturation:
        return "experiment_stopped_during_training_for_family_saturation"
    if runtime.next_chunk_index == 8:
        if (
            runtime.completed_pairs != 512
            or runtime.training_environment_accesses != 1_024
            or runtime.candidate_optimizer_updates != 8
            or runtime.control_optimizer_updates != 8
            or runtime.training_optimizer_steps != 16
        ):
            raise SuccessorRuntimeError(
                "complete training coordinates differ"
            )
        return "training_completed_without_family_saturation"
    return "training_incomplete"


def training_resource_use(runtime: PairedTrainingRuntime) -> dict[str, int]:
    """Return the exact training prefix with downstream access fixed at zero."""
    _validate_paired_training_runtime(runtime)
    return {
        "canary_environment_accesses": 0,
        "candidate_optimizer_updates": runtime.candidate_optimizer_updates,
        "completed_pairs": runtime.completed_pairs,
        "control_optimizer_updates": runtime.control_optimizer_updates,
        "holdout_environment_accesses": 0,
        "training_environment_accesses": runtime.training_environment_accesses,
        "training_optimizer_steps": runtime.training_optimizer_steps,
    }


def build_successor_resource_ledger(
    *,
    training_environment_accesses: int,
    training_optimizer_steps: int,
    shadow_optimizer_steps: int,
    canary_environment_accesses: int,
    holdout_environment_accesses: int,
) -> dict[str, int]:
    """Validate and total the complete successor resource coordinates."""
    values = {
        "training_environment_accesses": training_environment_accesses,
        "training_optimizer_steps": training_optimizer_steps,
        "shadow_optimizer_steps": shadow_optimizer_steps,
        "canary_environment_accesses": canary_environment_accesses,
        "holdout_environment_accesses": holdout_environment_accesses,
    }
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SuccessorRuntimeError(
                f"{name.replace('_', ' ')} must be a nonnegative integer"
            )
    ceilings = {
        "training_environment_accesses": MAX_TRAINING_ENVIRONMENT_ACCESSES,
        "training_optimizer_steps": MAX_TRAINING_OPTIMIZER_STEPS,
        "shadow_optimizer_steps": MAX_SHADOW_OPTIMIZER_STEPS,
        "canary_environment_accesses": MAX_CANARY_ENVIRONMENT_ACCESSES,
        "holdout_environment_accesses": MAX_HOLDOUT_ENVIRONMENT_ACCESSES,
    }
    for name, ceiling in ceilings.items():
        if values[name] > ceiling:
            raise SuccessorRuntimeError(
                f"{name.replace('_', ' ')} exceeds the registered ceiling"
            )

    total_environment_accesses = (
        training_environment_accesses
        + canary_environment_accesses
        + holdout_environment_accesses
    )
    if total_environment_accesses > MAX_TOTAL_ENVIRONMENT_ACCESSES:
        raise SuccessorRuntimeError(
            "total environment accesses exceed the registered ceiling"
        )
    return {
        "canary_environment_accesses": canary_environment_accesses,
        "holdout_environment_accesses": holdout_environment_accesses,
        "shadow_optimizer_steps": shadow_optimizer_steps,
        "total_environment_accesses": total_environment_accesses,
        "total_optimizer_steps": training_optimizer_steps + shadow_optimizer_steps,
        "training_environment_accesses": training_environment_accesses,
        "training_optimizer_steps": training_optimizer_steps,
    }


def run_bounded_paired_training(
    runtime: PairedTrainingRuntime,
    *,
    environment_factory: Callable[[int], Any],
    remaining_seeds: Sequence[int],
    before_environment: Callable[[ArmName, int], None],
    after_environment: Callable[[ArmName, int], None],
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
) -> BoundedTrainingResult:
    """Run the remaining registered chunks, stopping only for exact saturation."""
    _validate_paired_training_runtime(runtime)
    if runtime.stopped_for_family_saturation or runtime.next_chunk_index >= 8:
        raise SuccessorRuntimeError("training identity cannot start another schedule")
    seeds = tuple(remaining_seeds)
    expected_count = (8 - runtime.next_chunk_index) * 64
    if (
        len(seeds) != expected_count
        or any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in seeds
        )
        or seeds != tuple(sorted(set(seeds)))
    ):
        raise SuccessorRuntimeError(
            "remaining training seeds differ from the exact schedule"
        )

    completed: list[CompletedPairedTrainingChunk] = []
    offset = 0
    while runtime.next_chunk_index < 8:
        chunk_index = runtime.next_chunk_index
        chunk_seeds = seeds[offset : offset + 64]
        chunk = collect_and_complete_paired_training_chunk(
            runtime,
            environment_factory=environment_factory,
            seeds=chunk_seeds,
            chunk_index=chunk_index,
            before_environment=before_environment,
            after_environment=after_environment,
            deadline=deadline,
            clock=clock,
        )
        completed.append(chunk)
        offset += 64
        if chunk.saturation["stop"] is True:
            break
    verdict = training_progress_verdict(runtime)
    if verdict == "training_incomplete":
        raise SuccessorRuntimeError("bounded training stopped without a verdict")
    return BoundedTrainingResult(
        verdict=verdict,
        chunks=tuple(completed),
        resource_use=training_resource_use(runtime),
        checkpoint=encode_paired_training_checkpoint(runtime),
    )


__all__ = [
    "ArmBaselineDecision",
    "ArmBaselinePrediction",
    "ArmCardRewardObjective",
    "ArmChunkUpdateEvidence",
    "ArmCrossFittedBaseline",
    "ArmEpisodeRollout",
    "ArmOptimizerStepEvidence",
    "ArmOptimizers",
    "ArmRolloutDecision",
    "BoundedTrainingResult",
    "CandidateArm",
    "CompletedPairedTrainingChunk",
    "ControlArm",
    "PairedBootstrap",
    "PairedChunkUpdateEvidence",
    "PairedCrossFittedBaselines",
    "PairedEpisodeRollout",
    "PairedTrainingRuntime",
    "RidgeFoldModel",
    "SuccessorRuntimeError",
    "apply_arm_optimizer_step",
    "apply_paired_cross_fitted_chunk_update",
    "apply_paired_cross_fitted_chunk_update_exploratory",
    "build_arm_card_reward_rows",
    "build_arm_card_reward_objective",
    "build_arm_optimizers",
    "build_matched_bootstrap",
    "build_paired_cross_fitted_baselines",
    "build_successor_resource_ledger",
    "classify_candidate_family_saturation",
    "collect_and_complete_paired_training_chunk",
    "complete_paired_training_chunk",
    "complete_paired_training_chunk_exploratory",
    "encode_optimizer_state",
    "encode_paired_bootstrap",
    "encode_paired_training_checkpoint",
    "fold_baseline_state_features",
    "forward_card_policy",
    "initialize_paired_training_runtime",
    "restore_optimizer_state",
    "restore_paired_bootstrap",
    "restore_paired_training_checkpoint",
    "rollout_arm_frozen_evaluation",
    "rollout_arm_training_episode",
    "rollout_paired_frozen_evaluation",
    "rollout_paired_training_episode",
    "run_bounded_paired_training",
    "runtime_metadata",
    "score_noncard_candidates",
    "select_two_stage_action",
    "training_progress_verdict",
    "training_resource_use",
]
