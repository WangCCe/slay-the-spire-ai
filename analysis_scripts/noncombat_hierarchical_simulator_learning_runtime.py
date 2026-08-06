"""Torch runtime for the hierarchical non-combat simulator successor.

This module owns only synthetic/runtime behavior.  Cohort discovery, native
loading, authorization, publication, and terminal verification belong to the
separate standard-library control plane.
"""

from __future__ import annotations

import copy
import hashlib
import math
import random
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from numbers import Integral, Real
from typing import Any

import torch

from analysis_scripts import noncombat_action_family_distribution as family_distribution
from analysis_scripts import noncombat_formal_reward_contract as formal_reward_contract
from analysis_scripts import noncombat_hierarchical_policy_objective as hierarchical_objective
from analysis_scripts import noncombat_simulator_adapter as simulator_adapter
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    HASH_DIM,
    PolicyInputError,
    project_state_conditioned_policy_input,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    DEFAULT_HIDDEN_DIM,
    StateConditionedCandidateRanker,
    StateConditionedRankerError,
)


RUNTIME_SCHEMA_VERSION = "noncombat-hierarchical-simulator-learning-runtime-v1"
CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-runtime-checkpoint-v1"
)
TRAINING_ROW_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-training-row-v1"
)
CHUNK_SUMMARY_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-chunk-summary-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-evaluation-v1"
)
SAMPLING_VERSION = "family-first-then-conditional-v1"
DETERMINISTIC_SELECTION_VERSION = "unique-raw-score-maximum-v1"

MODEL_SEED = 0
PYTHON_RNG_SEED = 0
ACTION_GENERATOR_SEED = 0
LEARNING_RATE = 0.001
OPTIMIZER_BETAS = (0.9, 0.999)
OPTIMIZER_EPS = 1e-8
OPTIMIZER_WEIGHT_DECAY = 0.0
OPTIMIZER_AMSGRAD = False
OPTIMIZER_MAXIMIZE = False
OPTIMIZER_FOREACH = None
OPTIMIZER_CAPTURABLE = False
OPTIMIZER_DIFFERENTIABLE = False
OPTIMIZER_FUSED = None
DISCOUNT = 1.0
FAMILY_ENTROPY_COEFFICIENT = 0.01
CONDITIONAL_ENTROPY_COEFFICIENT = 0.01
GRADIENT_NORM_CEILING = 1.0

EPISODES_PER_UPDATE = 64
MAX_OPTIMIZER_UPDATES = 64
MAX_TRAINING_EPISODES = 4_096
MAX_EVALUATION_EPISODES = 2_560
MAX_TOTAL_EPISODES = 6_656
MAX_DECISIONS_PER_EPISODE = 500
MAX_WALL_SECONDS = 28_800.0

SATURATION_CATEGORIES = ("card_reward", "shop")
SATURATION_WINDOW_CHUNKS = 4
SATURATION_MINIMUM_MULTI_FAMILY_DECISIONS = 64
SATURATION_REQUIRED_SINGLETON_RATE = 1.0
CANARY_MINIMUM_MULTI_FAMILY_DECISIONS = 32
CANARY_MINIMUM_SELECTED_FAMILIES = 2
CANARY_MAXIMUM_SELECTED_FAMILY_RATE = 0.95
UNSUPPORTED_RATE_CEILING = 0.10
STATE_EFFECT_MINIMUM_ABSOLUTE_CHANGE = 1e-8
STATE_EFFECT_MINIMUM_DECISIONS = 4
STATE_EFFECT_MINIMUM_NONZERO_RATE = 0.25
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_CONFIDENCE = 0.95
BOOTSTRAP_SEED = 0
REGISTERED_SUPPORT_BLOCKERS = (
    "unsupported_shop_courier_restock_semantics",
)


class RuntimeBlocked(RuntimeError):
    """Raised when the successor runtime must fail closed."""


class RawScoreTieError(RuntimeBlocked):
    """Raised before evaluation applies an action with a tied raw maximum."""

    def __init__(self, action_ids: Sequence[str]) -> None:
        self.action_ids = tuple(sorted(action_ids))
        super().__init__(
            "raw-score maximum is tied across action IDs: "
            + ", ".join(self.action_ids)
        )


# A compatibility name for callers that use the control-plane failure label.
ExperimentBlocked = RuntimeBlocked


@dataclass(frozen=True)
class HierarchicalSample:
    """One replayable family draw followed by one conditional candidate draw."""

    selected_action_id: str
    selected_candidate_index: int
    selected_family: str
    selected_family_index: int
    family_member_indices: tuple[int, ...]
    conditional_draw_index: int
    distribution: family_distribution.ActionFamilyDistribution
    terms: hierarchical_objective.HierarchicalPolicyTerms
    generator_state_before_sha256: str
    generator_state_after_family_sha256: str
    generator_state_after_conditional_sha256: str


@dataclass(frozen=True)
class ScoredDecision:
    """Validated exact-API-v3 inputs and their CPU float32 scores."""

    decision_id: str
    category: str
    snapshot: dict[str, Any]
    candidates: tuple[dict[str, Any], ...]
    scores: torch.Tensor
    zero_state_scores: torch.Tensor
    state_effect: dict[str, Any]


@dataclass(frozen=True)
class RawScoreSelection:
    """A unique raw-score action plus complete maximum-set diagnostics."""

    selected_action_id: str
    selected_index: int
    selected_family: str
    maximum_action_ids: tuple[str, ...]
    maximum_family_ids: tuple[str, ...]
    distribution: family_distribution.ActionFamilyDistribution
    terms: hierarchical_objective.HierarchicalPolicyTerms


@dataclass(frozen=True)
class EpisodeRollout:
    """One cloned-branch simulator rollout."""

    seed: int
    training: bool
    decision_count: int
    transitions: tuple[dict[str, Any], ...]
    rewards: tuple[float, ...]
    selected_terms: tuple[hierarchical_objective.HierarchicalPolicyTerms, ...]
    diagnostic_rows: tuple[dict[str, Any], ...]
    formal_return: float
    floor_progress: float
    terminal_victory: int
    final_snapshot: dict[str, Any]
    unsupported_reason: str | None


@dataclass(frozen=True)
class ReinforceLoss:
    """The fixed split-entropy normalized-return objective."""

    loss: torch.Tensor
    policy_loss: torch.Tensor
    mean_family_entropy: torch.Tensor
    mean_conditional_entropy: torch.Tensor
    normalized_returns: torch.Tensor


@dataclass
class TrainingRuntime:
    """Mutable runtime state with immutable algorithm constants."""

    model: StateConditionedCandidateRanker
    optimizer: torch.optim.Adam
    python_rng: random.Random
    action_generator: torch.Generator
    next_chunk_index: int = 0
    completed_episodes: int = 0
    completed_decisions: int = 0
    optimizer_updates: int = 0
    training_episodes: int = 0
    evaluation_episodes: int = 0
    charged_seconds: float = 0.0
    family_entropy_coefficient: float = field(
        default=FAMILY_ENTROPY_COEFFICIENT, init=False
    )
    conditional_entropy_coefficient: float = field(
        default=CONDITIONAL_ENTROPY_COEFFICIENT, init=False
    )
    gradient_norm_ceiling: float = field(
        default=GRADIENT_NORM_CEILING, init=False
    )
    discount: float = field(default=DISCOUNT, init=False)


@dataclass(frozen=True)
class DecodedCheckpointState:
    """Strictly decoded tensors and coordinates ready for restoration."""

    model_state: dict[str, torch.Tensor]
    optimizer_state: dict[str, Any]
    python_rng_state: tuple[Any, ...]
    action_generator_state: torch.Tensor
    next_chunk_index: int
    completed_episodes: int
    completed_decisions: int
    optimizer_updates: int
    training_episodes: int
    evaluation_episodes: int
    charged_seconds: float


def runtime_metadata() -> dict[str, Any]:
    """Return the fixed runtime contract without granting execution authority."""
    return {
        "adapter_api_version": simulator_adapter.ADAPTER_API_VERSION,
        "algorithm": {
            "conditional_entropy_coefficient": CONDITIONAL_ENTROPY_COEFFICIENT,
            "discount": DISCOUNT,
            "family_entropy_coefficient": FAMILY_ENTROPY_COEFFICIENT,
            "gradient_norm_ceiling": GRADIENT_NORM_CEILING,
            "learning_rate": LEARNING_RATE,
            "normalized_returns": True,
            "optimizer": "adam",
            "optimizer_amsgrad": OPTIMIZER_AMSGRAD,
            "optimizer_betas": list(OPTIMIZER_BETAS),
            "optimizer_capturable": OPTIMIZER_CAPTURABLE,
            "optimizer_differentiable": OPTIMIZER_DIFFERENTIABLE,
            "optimizer_eps": OPTIMIZER_EPS,
            "optimizer_foreach": OPTIMIZER_FOREACH,
            "optimizer_fused": OPTIMIZER_FUSED,
            "optimizer_maximize": OPTIMIZER_MAXIMIZE,
            "optimizer_weight_decay": OPTIMIZER_WEIGHT_DECAY,
            "sampling": SAMPLING_VERSION,
        },
        "authority": {
            "cohort_access": False,
            "formal_rl": False,
            "gameplay": False,
            "model_loading": False,
            "native_loading": False,
            "policy_promotion": False,
            "qualification": False,
        },
        "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
        "device": "cpu",
        "evaluation_selection": DETERMINISTIC_SELECTION_VERSION,
        "runtime_schema_version": RUNTIME_SCHEMA_VERSION,
    }


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise RuntimeBlocked(f"{label} must be a non-negative integer")
    return int(value)


def _positive_int(value: object, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise RuntimeBlocked(f"{label} must be positive")
    return result


def _finite_float(value: object, label: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RuntimeBlocked(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise RuntimeBlocked(f"{label} must be finite")
    if minimum is not None and result < minimum:
        raise RuntimeBlocked(f"{label} must be at least {minimum}")
    return result


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise RuntimeBlocked(
            f"{label} keys mismatch; missing={sorted(expected - actual)!r}, "
            f"unexpected={sorted(actual - expected)!r}"
        )


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeBlocked(f"{label} must be an object")
    return value


def _sequence(value: object, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise RuntimeBlocked(f"{label} must be a sequence")
    return value


def _validate_generator(generator: object) -> torch.Generator:
    if not isinstance(generator, torch.Generator):
        raise RuntimeBlocked("action generator must be a Torch generator")
    if generator.device.type != "cpu":
        raise RuntimeBlocked("action generator must remain on CPU")
    state = generator.get_state()
    if state.device.type != "cpu" or state.dtype != torch.uint8 or state.numel() == 0:
        raise RuntimeBlocked("action generator state is invalid")
    return generator


def _validate_module_parameters(model: torch.nn.Module) -> None:
    for name, parameter in model.named_parameters():
        if parameter.device.type != "cpu" or parameter.dtype != torch.float32:
            raise RuntimeBlocked(f"model parameter {name} must be CPU float32")
        if not torch.isfinite(parameter).all().item():
            raise RuntimeBlocked(f"model parameter {name} must be finite")
        if parameter.grad is not None and not torch.isfinite(parameter.grad).all().item():
            raise RuntimeBlocked(f"model gradient {name} must be finite")
    for name, buffer in model.named_buffers():
        if buffer.device.type != "cpu" or not torch.isfinite(buffer).all().item():
            raise RuntimeBlocked(f"model buffer {name} must be finite on CPU")


def _validate_optimizer(runtime: TrainingRuntime) -> None:
    optimizer = runtime.optimizer
    if type(optimizer) is not torch.optim.Adam:
        raise RuntimeBlocked("optimizer must be exactly torch.optim.Adam")
    if len(optimizer.param_groups) != 1:
        raise RuntimeBlocked("optimizer must contain exactly one parameter group")
    group = optimizer.param_groups[0]
    expected = {
        "lr": LEARNING_RATE,
        "betas": OPTIMIZER_BETAS,
        "eps": OPTIMIZER_EPS,
        "weight_decay": OPTIMIZER_WEIGHT_DECAY,
        "amsgrad": OPTIMIZER_AMSGRAD,
        "maximize": OPTIMIZER_MAXIMIZE,
        "foreach": OPTIMIZER_FOREACH,
        "capturable": OPTIMIZER_CAPTURABLE,
        "differentiable": OPTIMIZER_DIFFERENTIABLE,
        "fused": OPTIMIZER_FUSED,
    }
    for name, expected_value in expected.items():
        actual = group.get(name)
        if name == "betas":
            actual = tuple(actual) if isinstance(actual, Sequence) else actual
        if actual != expected_value:
            raise RuntimeBlocked(f"Adam optimizer {name} mismatch")
    model_parameters = list(runtime.model.parameters())
    if len(group["params"]) != len(model_parameters) or any(
        actual is not expected_parameter
        for actual, expected_parameter in zip(
            group["params"], model_parameters, strict=True
        )
    ):
        raise RuntimeBlocked("optimizer parameters do not align with the model")
    for state in optimizer.state.values():
        for name, value in state.items():
            if isinstance(value, torch.Tensor):
                if value.device.type != "cpu" or not torch.isfinite(value).all().item():
                    raise RuntimeBlocked(f"optimizer state {name} must be finite on CPU")
            elif isinstance(value, Real) and not math.isfinite(float(value)):
                raise RuntimeBlocked(f"optimizer state {name} must be finite")


def _validate_runtime(runtime: TrainingRuntime) -> None:
    if not isinstance(runtime, TrainingRuntime):
        raise RuntimeBlocked("runtime type mismatch")
    if not isinstance(runtime.model, StateConditionedCandidateRanker):
        raise RuntimeBlocked("runtime model must use the state-conditioned ranker")
    expected_architecture = {
        "architecture_id": "state-conditioned-candidate-ranker-mlp-v1",
        "candidate_input_dim": HASH_DIM,
        "device": "cpu",
        "dtype": "float32",
        "hidden_dim": DEFAULT_HIDDEN_DIM,
        "state_conditioned": True,
        "state_input_dim": HASH_DIM,
    }
    if runtime.model.architecture_metadata() != expected_architecture:
        raise RuntimeBlocked("runtime model architecture mismatch")
    _validate_module_parameters(runtime.model)
    _validate_optimizer(runtime)
    if not isinstance(runtime.python_rng, random.Random):
        raise RuntimeBlocked("runtime Python RNG type mismatch")
    try:
        runtime.python_rng.getstate()
    except (TypeError, ValueError) as exc:
        raise RuntimeBlocked("runtime Python RNG state is invalid") from exc
    _validate_generator(runtime.action_generator)
    if runtime.family_entropy_coefficient != FAMILY_ENTROPY_COEFFICIENT:
        raise RuntimeBlocked("family entropy coefficient mismatch")
    if runtime.conditional_entropy_coefficient != CONDITIONAL_ENTROPY_COEFFICIENT:
        raise RuntimeBlocked("conditional entropy coefficient mismatch")
    if runtime.gradient_norm_ceiling != GRADIENT_NORM_CEILING:
        raise RuntimeBlocked("gradient norm ceiling mismatch")
    if runtime.discount != DISCOUNT:
        raise RuntimeBlocked("discount mismatch")

    runtime.next_chunk_index = _nonnegative_int(
        runtime.next_chunk_index, "next chunk index"
    )
    runtime.completed_episodes = _nonnegative_int(
        runtime.completed_episodes, "completed episodes"
    )
    runtime.completed_decisions = _nonnegative_int(
        runtime.completed_decisions, "completed decisions"
    )
    runtime.optimizer_updates = _nonnegative_int(
        runtime.optimizer_updates, "optimizer updates"
    )
    runtime.training_episodes = _nonnegative_int(
        runtime.training_episodes, "training resource episodes"
    )
    runtime.evaluation_episodes = _nonnegative_int(
        runtime.evaluation_episodes, "evaluation episodes"
    )
    runtime.charged_seconds = _finite_float(
        runtime.charged_seconds, "charged seconds", minimum=0.0
    )
    if runtime.next_chunk_index != runtime.optimizer_updates:
        raise RuntimeBlocked("chunk and optimizer coordinates differ")
    if runtime.completed_episodes != runtime.optimizer_updates * EPISODES_PER_UPDATE:
        raise RuntimeBlocked("completed episodes differ from durable updates")
    if runtime.training_episodes < runtime.completed_episodes:
        raise RuntimeBlocked("training resources precede completed episodes")
    if runtime.training_episodes > MAX_TRAINING_EPISODES:
        raise RuntimeBlocked("training episode resource limit exceeded")
    if runtime.evaluation_episodes > MAX_EVALUATION_EPISODES:
        raise RuntimeBlocked("evaluation episode resource limit exceeded")
    if runtime.training_episodes + runtime.evaluation_episodes > MAX_TOTAL_EPISODES:
        raise RuntimeBlocked("total episode resource limit exceeded")
    if runtime.optimizer_updates > MAX_OPTIMIZER_UPDATES:
        raise RuntimeBlocked("optimizer update resource limit exceeded")
    if runtime.charged_seconds > MAX_WALL_SECONDS:
        raise RuntimeBlocked("wall-time resource limit exceeded")


def initialize_training_runtime() -> TrainingRuntime:
    """Create the fixed CPU model, Adam optimizer, and both deterministic RNGs."""
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(MODEL_SEED)
        model = StateConditionedCandidateRanker(HASH_DIM, DEFAULT_HIDDEN_DIM)
    model.to(device="cpu", dtype=torch.float32)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        betas=OPTIMIZER_BETAS,
        eps=OPTIMIZER_EPS,
        weight_decay=OPTIMIZER_WEIGHT_DECAY,
        amsgrad=OPTIMIZER_AMSGRAD,
        maximize=OPTIMIZER_MAXIMIZE,
        foreach=OPTIMIZER_FOREACH,
        capturable=OPTIMIZER_CAPTURABLE,
        differentiable=OPTIMIZER_DIFFERENTIABLE,
        fused=OPTIMIZER_FUSED,
    )
    action_generator = torch.Generator(device="cpu")
    action_generator.manual_seed(ACTION_GENERATOR_SEED)
    runtime = TrainingRuntime(
        model=model,
        optimizer=optimizer,
        python_rng=random.Random(PYTHON_RNG_SEED),
        action_generator=action_generator,
    )
    _validate_runtime(runtime)
    return runtime


def runtime_resource_use(runtime: TrainingRuntime) -> dict[str, int | float]:
    """Expose the cumulative registered resource coordinates."""
    _validate_runtime(runtime)
    return {
        "charged_seconds": runtime.charged_seconds,
        "evaluation_episodes": runtime.evaluation_episodes,
        "optimizer_updates": runtime.optimizer_updates,
        "total_episodes": runtime.training_episodes + runtime.evaluation_episodes,
        "training_episodes": runtime.training_episodes,
    }


def _notify_resource_change(
    runtime: TrainingRuntime,
    observer: Callable[[dict[str, int | float], dict[str, Any]], None] | None,
    event: Mapping[str, Any],
) -> dict[str, int | float]:
    resources = runtime_resource_use(runtime)
    normalized_event = copy.deepcopy(dict(event))
    if observer is not None:
        try:
            observer(copy.deepcopy(resources), normalized_event)
        except BaseException as exc:
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            if isinstance(exc, RuntimeBlocked):
                raise
            raise RuntimeBlocked(str(exc)) from exc
    return resources


def _debit_episode_resource(
    runtime: TrainingRuntime,
    *,
    phase: str,
    seed: int,
    observer: Callable[[dict[str, int | float], dict[str, Any]], None] | None,
) -> dict[str, int | float]:
    _validate_runtime(runtime)
    if phase == "training":
        if runtime.training_episodes + 1 > MAX_TRAINING_EPISODES:
            raise RuntimeBlocked("training episode resource limit reached")
        runtime.training_episodes += 1
    else:
        if not isinstance(phase, str) or not phase:
            raise RuntimeBlocked("evaluation resource phase is invalid")
        if runtime.evaluation_episodes + 1 > MAX_EVALUATION_EPISODES:
            raise RuntimeBlocked("evaluation episode resource limit reached")
        runtime.evaluation_episodes += 1
    if runtime.training_episodes + runtime.evaluation_episodes > MAX_TOTAL_EPISODES:
        if phase == "training":
            runtime.training_episodes -= 1
        else:
            runtime.evaluation_episodes -= 1
        raise RuntimeBlocked("total episode resource limit reached")
    _validate_runtime(runtime)
    return _notify_resource_change(
        runtime,
        observer,
        {
            "kind": "episode_debited",
            "phase": phase,
            "seed": _nonnegative_int(seed, "resource seed"),
        },
    )


def _charge_wall_resource(
    runtime: TrainingRuntime,
    *,
    elapsed: Real,
    phase: str,
    observer: Callable[[dict[str, int | float], dict[str, Any]], None] | None,
) -> dict[str, int | float]:
    _validate_runtime(runtime)
    seconds = _finite_float(elapsed, "charged wall seconds", minimum=0.0)
    if not isinstance(phase, str) or not phase:
        raise RuntimeBlocked("wall resource phase is invalid")
    if seconds == 0.0:
        return runtime_resource_use(runtime)
    remaining = MAX_WALL_SECONDS - runtime.charged_seconds
    charged = min(seconds, remaining)
    runtime.charged_seconds += charged
    _validate_runtime(runtime)
    resources = _notify_resource_change(
        runtime,
        observer,
        {"kind": "wall_charged", "phase": phase, "seed": None},
    )
    if seconds > remaining:
        raise RuntimeBlocked("wall-time resource limit reached")
    return resources


def record_evaluation_resources(
    runtime: TrainingRuntime,
    *,
    episodes: int,
    charged_seconds: Real,
) -> dict[str, int | float]:
    """Atomically charge one durable canary or holdout evaluation prefix."""
    _validate_runtime(runtime)
    episode_count = _positive_int(episodes, "evaluation episodes")
    elapsed = _finite_float(
        charged_seconds, "evaluation charged seconds", minimum=0.0
    )
    previous_episodes = runtime.evaluation_episodes
    previous_seconds = runtime.charged_seconds
    try:
        runtime.evaluation_episodes += episode_count
        runtime.charged_seconds += elapsed
        _validate_runtime(runtime)
    except BaseException:
        runtime.evaluation_episodes = previous_episodes
        runtime.charged_seconds = previous_seconds
        raise
    return runtime_resource_use(runtime)


def restore_consumed_resource_prefix(
    runtime: TrainingRuntime, value: Mapping[str, Any]
) -> dict[str, int | float]:
    """Merge a durable monotonic resource prefix into restored logical state."""
    _validate_runtime(runtime)
    resources = dict(_mapping(value, "evaluation resource prefix"))
    _exact_keys(
        resources,
        {
            "charged_seconds",
            "evaluation_episodes",
            "optimizer_updates",
            "total_episodes",
            "training_episodes",
        },
        "resource prefix",
    )
    if _nonnegative_int(
        resources["optimizer_updates"], "optimizer updates"
    ) != runtime.optimizer_updates:
        raise RuntimeBlocked("resource prefix changes optimizer coordinates")
    training_episodes = _nonnegative_int(
        resources["training_episodes"], "training episodes"
    )
    evaluation_episodes = _nonnegative_int(
        resources["evaluation_episodes"], "evaluation episodes"
    )
    charged_seconds = _finite_float(
        resources["charged_seconds"], "charged seconds", minimum=0.0
    )
    if (
        training_episodes < runtime.training_episodes
        or training_episodes < runtime.completed_episodes
        or evaluation_episodes < runtime.evaluation_episodes
        or charged_seconds < runtime.charged_seconds
        or _nonnegative_int(resources["total_episodes"], "total episodes")
        != training_episodes + evaluation_episodes
    ):
        raise RuntimeBlocked("resource prefix is not monotonic")
    previous_training = runtime.training_episodes
    previous_episodes = runtime.evaluation_episodes
    previous_seconds = runtime.charged_seconds
    try:
        runtime.training_episodes = training_episodes
        runtime.evaluation_episodes = evaluation_episodes
        runtime.charged_seconds = charged_seconds
        _validate_runtime(runtime)
    except BaseException:
        runtime.training_episodes = previous_training
        runtime.evaluation_episodes = previous_episodes
        runtime.charged_seconds = previous_seconds
        raise
    return runtime_resource_use(runtime)


restore_evaluation_resource_prefix = restore_consumed_resource_prefix


_DTYPES = {
    "bool": torch.bool,
    "float32": torch.float32,
    "float64": torch.float64,
    "int32": torch.int32,
    "int64": torch.int64,
    "uint8": torch.uint8,
}


def encode_tensor(value: torch.Tensor) -> dict[str, Any]:
    """Encode a finite CPU tensor without pickle or device-dependent bytes."""
    if not isinstance(value, torch.Tensor):
        raise RuntimeBlocked("tensor encoding requires a tensor")
    tensor = value.detach().cpu().contiguous()
    dtype_name = str(tensor.dtype).removeprefix("torch.")
    if dtype_name not in _DTYPES:
        raise RuntimeBlocked(f"unsupported checkpoint tensor dtype: {dtype_name}")
    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
        raise RuntimeBlocked("checkpoint tensor must be finite")
    return {
        "dtype": dtype_name,
        "shape": list(tensor.shape),
        "values": tensor.reshape(-1).tolist(),
    }


def decode_tensor(value: object, label: str = "tensor") -> torch.Tensor:
    """Decode the exact inverse of :func:`encode_tensor`."""
    mapping = _mapping(value, label)
    _exact_keys(mapping, {"dtype", "shape", "values"}, label)
    dtype_name = mapping["dtype"]
    if not isinstance(dtype_name, str) or dtype_name not in _DTYPES:
        raise RuntimeBlocked(f"{label} dtype is unsupported")
    shape_values = _sequence(mapping["shape"], f"{label}.shape")
    shape = tuple(
        _nonnegative_int(dimension, f"{label}.shape[{index}]")
        for index, dimension in enumerate(shape_values)
    )
    values = list(_sequence(mapping["values"], f"{label}.values"))
    expected_count = math.prod(shape) if shape else 1
    if len(values) != expected_count:
        raise RuntimeBlocked(f"{label} value count does not match shape")
    try:
        tensor = torch.tensor(values, dtype=_DTYPES[dtype_name], device="cpu")
        tensor = tensor.reshape(shape)
    except (TypeError, ValueError, RuntimeError) as exc:
        raise RuntimeBlocked(f"{label} tensor decode failed") from exc
    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
        raise RuntimeBlocked(f"{label} must be finite")
    return tensor


def _encode_state_value(value: Any) -> dict[str, Any]:
    if isinstance(value, torch.Tensor):
        return {"type": "tensor", "value": encode_tensor(value)}
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
            {
                "key": _encode_state_value(key),
                "value": _encode_state_value(item),
            }
            for key, item in value.items()
        ]
        items.sort(
            key=lambda item: simulator_adapter.canonical_json_bytes(item["key"])
        )
        return {"type": "mapping", "items": items}
    if value is None or isinstance(value, (bool, int, str)):
        return {"type": "scalar", "value": value}
    if isinstance(value, Real):
        return {
            "type": "scalar",
            "value": _finite_float(value, "checkpoint scalar"),
        }
    raise RuntimeBlocked(f"unsupported checkpoint state type: {type(value).__name__}")


def _decode_state_value(value: object, label: str) -> Any:
    mapping = _mapping(value, label)
    state_type = mapping.get("type")
    if state_type == "tensor":
        _exact_keys(mapping, {"type", "value"}, label)
        return decode_tensor(mapping["value"], f"{label}.value")
    if state_type in {"tuple", "list"}:
        _exact_keys(mapping, {"type", "items"}, label)
        items = [
            _decode_state_value(item, f"{label}.items[{index}]")
            for index, item in enumerate(
                _sequence(mapping["items"], f"{label}.items")
            )
        ]
        return tuple(items) if state_type == "tuple" else items
    if state_type == "mapping":
        _exact_keys(mapping, {"type", "items"}, label)
        result: dict[Any, Any] = {}
        for index, raw_item in enumerate(
            _sequence(mapping["items"], f"{label}.items")
        ):
            item = _mapping(raw_item, f"{label}.items[{index}]")
            _exact_keys(item, {"key", "value"}, f"{label}.items[{index}]")
            key = _decode_state_value(item["key"], f"{label}.items[{index}].key")
            if key in result:
                raise RuntimeBlocked(f"{label} contains a duplicate key")
            result[key] = _decode_state_value(
                item["value"], f"{label}.items[{index}].value"
            )
        return result
    if state_type == "scalar":
        _exact_keys(mapping, {"type", "value"}, label)
        scalar = mapping["value"]
        if scalar is not None and not isinstance(scalar, (bool, int, float, str)):
            raise RuntimeBlocked(f"{label} scalar type is invalid")
        if isinstance(scalar, float) and not math.isfinite(scalar):
            raise RuntimeBlocked(f"{label} scalar must be finite")
        return scalar
    raise RuntimeBlocked(f"{label} state type is invalid")


def encode_model_state(model: torch.nn.Module) -> dict[str, Any]:
    """Encode model state in stable parameter/buffer-name order."""
    _validate_module_parameters(model)
    return {
        name: encode_tensor(tensor)
        for name, tensor in sorted(model.state_dict().items())
    }


def encode_optimizer_state(optimizer: torch.optim.Optimizer) -> dict[str, Any]:
    """Encode optimizer state with integer keys and tuple values preserved."""
    if not isinstance(optimizer, torch.optim.Optimizer):
        raise RuntimeBlocked("optimizer state encoding requires an optimizer")
    return _encode_state_value(optimizer.state_dict())


def decode_optimizer_state(value: object) -> dict[str, Any]:
    """Decode an optimizer state produced by :func:`encode_optimizer_state`."""
    decoded = _decode_state_value(value, "optimizer state")
    if not isinstance(decoded, dict):
        raise RuntimeBlocked("optimizer state must decode to an object")
    if set(decoded) != {"param_groups", "state"}:
        raise RuntimeBlocked("optimizer state keys mismatch")
    return decoded


def torch_generator_state_sha256(generator: torch.Generator) -> str:
    """Hash the exact CPU byte-generator state for replay diagnostics."""
    state = _validate_generator(generator).get_state().cpu()
    return hashlib.sha256(bytes(state.tolist())).hexdigest()


def _normalized_snapshot_and_candidates(
    snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_snapshot = copy.deepcopy(snapshot)
    source_candidates = copy.deepcopy(list(candidates))
    try:
        normalized_snapshot = simulator_adapter.validate_snapshot(
            copy.deepcopy(snapshot)
        )
        if (
            normalized_snapshot["adapter_api_version"]
            != simulator_adapter.ADAPTER_API_VERSION
        ):
            raise RuntimeBlocked("successor runtime requires exact adapter API v3")
        if normalized_snapshot["terminal"] is True:
            raise RuntimeBlocked("terminal snapshot cannot be scored")
        normalized_candidates = simulator_adapter.validate_candidates(
            copy.deepcopy(list(candidates)),
            category=normalized_snapshot["category"],
        )
    except RuntimeBlocked:
        raise
    except (simulator_adapter.SimulatorAdapterError, TypeError, ValueError) as exc:
        raise RuntimeBlocked(str(exc)) from exc
    if simulator_adapter.canonical_json_bytes(snapshot) != (
        simulator_adapter.canonical_json_bytes(source_snapshot)
    ):
        raise RuntimeBlocked("API v3 validation mutated the source snapshot")
    if simulator_adapter.canonical_json_bytes(list(candidates)) != (
        simulator_adapter.canonical_json_bytes(source_candidates)
    ):
        raise RuntimeBlocked("API v3 validation mutated the source candidates")
    return normalized_snapshot, normalized_candidates


def _state_effect(
    scores: torch.Tensor, zero_state_scores: torch.Tensor
) -> dict[str, Any]:
    actual = scores.detach().to(dtype=torch.float64)
    zero = zero_state_scores.detach().to(dtype=torch.float64)
    actual_relative = actual - actual.mean()
    zero_relative = zero - zero.mean()
    maximum_change = float(
        torch.amax(torch.abs(actual_relative - zero_relative)).item()
    )
    relative_order_changed = any(
        int(torch.sign(actual[left] - actual[right]).item())
        != int(torch.sign(zero[left] - zero[right]).item())
        for left in range(actual.shape[0])
        for right in range(left + 1, actual.shape[0])
    )
    if not math.isfinite(maximum_change):
        raise RuntimeBlocked("state-effect diagnostic must be finite")
    return {
        "actual_scores": [float(value) for value in actual.tolist()],
        "max_abs_relative_score_change": maximum_change,
        "nonzero": maximum_change >= STATE_EFFECT_MINIMUM_ABSOLUTE_CHANGE,
        "relative_order_changed": relative_order_changed,
        "zero_state_scores": [float(value) for value in zero.tolist()],
    }


def score_decision(
    model: torch.nn.Module,
    *,
    decision_id: str,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> ScoredDecision:
    """Project and score one exact API v3 decision without mutating sources."""
    if not isinstance(decision_id, str) or not decision_id:
        raise RuntimeBlocked("decision_id must be a nonempty string")
    if not isinstance(model, torch.nn.Module):
        raise RuntimeBlocked("model must be a Torch module")
    _validate_module_parameters(model)
    normalized_snapshot, normalized_candidates = _normalized_snapshot_and_candidates(
        snapshot, candidates
    )
    source_snapshot = copy.deepcopy(snapshot)
    source_candidates = copy.deepcopy(list(candidates))
    try:
        projected = project_state_conditioned_policy_input(
            copy.deepcopy(normalized_snapshot), copy.deepcopy(normalized_candidates)
        )
        scores = model(projected.state_features, projected.candidate_features)
        with torch.no_grad():
            zero_state_scores = model(
                torch.zeros_like(projected.state_features),
                projected.candidate_features,
            )
    except (PolicyInputError, StateConditionedRankerError, RuntimeError) as exc:
        raise RuntimeBlocked(str(exc)) from exc
    expected_shape = (len(normalized_candidates),)
    for label, value in (("scores", scores), ("zero-state scores", zero_state_scores)):
        if not isinstance(value, torch.Tensor) or value.shape != expected_shape:
            raise RuntimeBlocked(f"{label} shape is invalid")
        if value.device.type != "cpu" or value.dtype != torch.float32:
            raise RuntimeBlocked(f"{label} must be CPU float32")
        if not torch.isfinite(value).all().item():
            raise RuntimeBlocked(f"{label} must be finite")
    if simulator_adapter.canonical_json_bytes(snapshot) != (
        simulator_adapter.canonical_json_bytes(source_snapshot)
    ) or simulator_adapter.canonical_json_bytes(list(candidates)) != (
        simulator_adapter.canonical_json_bytes(source_candidates)
    ):
        raise RuntimeBlocked("score projection mutated source inputs")
    return ScoredDecision(
        decision_id=decision_id,
        category=normalized_snapshot["category"],
        snapshot=normalized_snapshot,
        candidates=tuple(normalized_candidates),
        scores=scores,
        zero_state_scores=zero_state_scores,
        state_effect=_state_effect(scores, zero_state_scores),
    )


def sample_hierarchical_action(
    scores: torch.Tensor,
    candidates: Sequence[Mapping[str, Any]],
    action_generator: torch.Generator,
) -> HierarchicalSample:
    """Draw family first, then an original-order member of that family."""
    generator = _validate_generator(action_generator)
    try:
        distribution = family_distribution.build_action_family_distribution(
            scores, candidates
        )
    except family_distribution.ActionFamilyDistributionError as exc:
        raise RuntimeBlocked(str(exc)) from exc
    before_sha256 = torch_generator_state_sha256(generator)
    family_draw = torch.multinomial(
        distribution.family_probabilities,
        num_samples=1,
        replacement=True,
        generator=generator,
    )
    family_index = int(family_draw.item())
    after_family_sha256 = torch_generator_state_sha256(generator)
    selected_family = distribution.family_order[family_index]
    member_indices = tuple(
        index
        for index, family in enumerate(distribution.candidate_families)
        if family == selected_family
    )
    conditional_probabilities = torch.stack(
        [
            distribution.conditional_log_probabilities[index].exp()
            for index in member_indices
        ]
    )
    conditional_draw = torch.multinomial(
        conditional_probabilities,
        num_samples=1,
        replacement=True,
        generator=generator,
    )
    conditional_index = int(conditional_draw.item())
    selected_index = member_indices[conditional_index]
    selected_action_id = distribution.action_ids[selected_index]
    after_conditional_sha256 = torch_generator_state_sha256(generator)
    try:
        terms = hierarchical_objective.build_hierarchical_policy_terms(
            scores, candidates, selected_action_id
        )
    except hierarchical_objective.HierarchicalPolicyObjectiveError as exc:
        raise RuntimeBlocked(str(exc)) from exc
    if (
        terms.action_ids != distribution.action_ids
        or terms.family_order != distribution.family_order
        or terms.selected_index != selected_index
        or terms.selected_family != selected_family
        or terms.selected_family_index != family_index
    ):
        raise RuntimeBlocked("sampled family/candidate metadata lost alignment")
    return HierarchicalSample(
        selected_action_id=selected_action_id,
        selected_candidate_index=selected_index,
        selected_family=selected_family,
        selected_family_index=family_index,
        family_member_indices=member_indices,
        conditional_draw_index=conditional_index,
        distribution=distribution,
        terms=terms,
        generator_state_before_sha256=before_sha256,
        generator_state_after_family_sha256=after_family_sha256,
        generator_state_after_conditional_sha256=after_conditional_sha256,
    )


def _maximum_family_ids(
    maximum_action_ids: Sequence[str], candidates: Sequence[Mapping[str, Any]]
) -> tuple[str, ...]:
    family_by_action = {
        str(candidate["action_id"]): str(candidate["kind"])
        for candidate in candidates
    }
    return tuple(sorted({family_by_action[action_id] for action_id in maximum_action_ids}))


def select_unique_raw_score_action(
    scores: torch.Tensor, candidates: Sequence[Mapping[str, Any]]
) -> RawScoreSelection:
    """Select only a unique raw maximum and fail closed on every tie."""
    if not candidates:
        raise RuntimeBlocked("raw-score selection requires candidates")
    first_action_id = candidates[0].get("action_id")
    try:
        terms = hierarchical_objective.build_hierarchical_policy_terms(
            scores, candidates, first_action_id
        )
        distribution = family_distribution.build_action_family_distribution(
            scores, candidates
        )
    except (
        hierarchical_objective.HierarchicalPolicyObjectiveError,
        family_distribution.ActionFamilyDistributionError,
    ) as exc:
        raise RuntimeBlocked(str(exc)) from exc
    maximum_action_ids = terms.score_greedy_action_ids
    maximum_family_ids = _maximum_family_ids(maximum_action_ids, candidates)
    if terms.unique_score_greedy_action_id is None:
        raise RawScoreTieError(maximum_action_ids)
    if terms.unique_two_stage_score_greedy_action_id != (
        terms.unique_score_greedy_action_id
    ):
        raise RuntimeBlocked("two-stage raw-score maximum differs")
    selected_action_id = terms.unique_score_greedy_action_id
    selected_terms = hierarchical_objective.build_hierarchical_policy_terms(
        scores, candidates, selected_action_id
    )
    selected_index = distribution.action_ids.index(selected_action_id)
    return RawScoreSelection(
        selected_action_id=selected_action_id,
        selected_index=selected_index,
        selected_family=distribution.candidate_families[selected_index],
        maximum_action_ids=maximum_action_ids,
        maximum_family_ids=maximum_family_ids,
        distribution=distribution,
        terms=selected_terms,
    )


def _score_margin(values: torch.Tensor) -> float | None:
    detached = values.detach().to(dtype=torch.float64)
    if detached.numel() < 2:
        return None
    sorted_values = torch.sort(detached, descending=True).values
    margin = float((sorted_values[0] - sorted_values[1]).item())
    if not math.isfinite(margin):
        raise RuntimeBlocked("score margin must be finite")
    return margin


def build_decision_diagnostic_row(
    scored: ScoredDecision,
    *,
    selected_action_id: str,
    selected_family: str,
    terms: hierarchical_objective.HierarchicalPolicyTerms,
    distribution: family_distribution.ActionFamilyDistribution,
    seed: int,
    decision_index: int,
    chunk_index: int | None,
    selection_mode: str,
    generator_hashes: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build one family-aware row with complete raw maximum sets."""
    if selected_action_id != terms.selected_action_id:
        raise RuntimeBlocked("diagnostic selected action mismatch")
    if selected_family != terms.selected_family:
        raise RuntimeBlocked("diagnostic selected family mismatch")
    if distribution.action_ids != terms.action_ids:
        raise RuntimeBlocked("diagnostic action alignment mismatch")
    maximum_family_ids = _maximum_family_ids(
        terms.score_greedy_action_ids, scored.candidates
    )
    candidate_scores = [float(value) for value in scored.scores.detach().tolist()]
    family_probabilities = {
        family: float(distribution.family_probabilities[index].detach().item())
        for index, family in enumerate(distribution.family_order)
    }
    conditional_probabilities = {
        action_id: float(
            distribution.conditional_log_probabilities[index].detach().exp().item()
        )
        for index, action_id in enumerate(distribution.action_ids)
    }
    joint_probabilities = {
        action_id: float(distribution.candidate_probabilities[index].detach().item())
        for index, action_id in enumerate(distribution.action_ids)
    }
    maximum_joint_probability = max(joint_probabilities.values())
    joint_probability_max_action_ids = sorted(
        action_id
        for action_id, probability in joint_probabilities.items()
        if probability == maximum_joint_probability
    )
    row = {
        "candidate_scores": {
            action_id: score
            for action_id, score in zip(
                distribution.action_ids, candidate_scores, strict=True
            )
        },
        "candidates": [
            {"action_id": candidate["action_id"], "kind": candidate["kind"]}
            for candidate in scored.candidates
        ],
        "category": scored.category,
        "chunk_index": chunk_index,
        "conditional_probabilities": conditional_probabilities,
        "decision_id": scored.decision_id,
        "decision_index": decision_index,
        "entropies": {
            "expected_conditional": float(
                terms.conditional_entropy.detach().item()
            ),
            "family": float(terms.family_entropy.detach().item()),
            "joint": float(terms.joint_entropy.detach().item()),
        },
        "family_order": list(distribution.family_order),
        "family_probabilities": family_probabilities,
        "family_score_margin": _score_margin(distribution.family_logits),
        "joint_probabilities": joint_probabilities,
        "joint_probability_max_action_ids": joint_probability_max_action_ids,
        "legal_action_ids": list(distribution.action_ids),
        "multi_family": len(distribution.family_order) > 1,
        "raw_score_max_action_ids": list(terms.score_greedy_action_ids),
        "raw_score_max_family_ids": list(maximum_family_ids),
        "schema_version": TRAINING_ROW_SCHEMA_VERSION,
        "score_greedy_action_ids": list(terms.score_greedy_action_ids),
        "score_greedy_family_ids": list(maximum_family_ids),
        "score_margin": _score_margin(scored.scores),
        "seed": seed,
        "selected_action_id": selected_action_id,
        "selected_family": selected_family,
        "selected_terms": {
            "conditional_log_probability": float(
                terms.selected_conditional_log_probability.detach().item()
            ),
            "family_log_probability": float(
                terms.selected_family_log_probability.detach().item()
            ),
            "joint_log_probability": float(
                terms.selected_joint_log_probability.detach().item()
            ),
        },
        "selection_mode": selection_mode,
        "state_effect": copy.deepcopy(scored.state_effect),
    }
    if generator_hashes is not None:
        expected_hash_keys = {
            "after_conditional",
            "after_family",
            "before_family",
        }
        if set(generator_hashes) != expected_hash_keys or any(
            not isinstance(value, str) or len(value) != 64
            for value in generator_hashes.values()
        ):
            raise RuntimeBlocked("generator diagnostic hashes are invalid")
        row["action_generator_state_sha256"] = dict(generator_hashes)
    return row


def formal_reward_channels(transition: Mapping[str, Any]) -> dict[str, float | int]:
    """Return the two public formal channels and their fixed scalar reward."""
    try:
        channels = formal_reward_contract.reward_channels(transition)
    except formal_reward_contract.RewardContractBlocked as exc:
        raise RuntimeBlocked(str(exc)) from exc
    if set(channels) != {"floor_progress", "terminal_victory"}:
        raise RuntimeBlocked("formal reward channel set mismatch")
    floor_progress = _finite_float(
        channels["floor_progress"], "formal floor progress", minimum=0.0
    )
    victory = channels["terminal_victory"]
    if type(victory) is not int or victory not in {0, 1}:
        raise RuntimeBlocked("formal terminal victory must be zero or one")
    scalar_reward = 2.0 * victory + floor_progress
    return {
        "floor_progress": floor_progress,
        "scalar_reward": scalar_reward,
        "terminal_victory": victory,
    }


def formal_reward(transition: Mapping[str, Any]) -> float:
    """Compute ``2 * terminal_victory + bounded_floor_progress`` exactly."""
    return float(formal_reward_channels(transition)["scalar_reward"])


def _environment_state(
    environment: Any,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for method_name in ("snapshot", "legal_actions", "clone", "step"):
        if not callable(getattr(environment, method_name, None)):
            raise RuntimeBlocked(f"environment.{method_name} must be callable")
    try:
        snapshot = simulator_adapter.validate_snapshot(environment.snapshot())
        if snapshot["adapter_api_version"] != simulator_adapter.ADAPTER_API_VERSION:
            raise RuntimeBlocked("environment must expose exact adapter API v3")
        candidates = simulator_adapter.validate_candidates(
            environment.legal_actions(), category=snapshot["category"]
        )
    except RuntimeBlocked:
        raise
    except (simulator_adapter.SimulatorAdapterError, TypeError, ValueError) as exc:
        raise RuntimeBlocked(str(exc)) from exc
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
        raise RuntimeBlocked("source environment could not be re-read") from exc
    if simulator_adapter.canonical_json_bytes(actual_snapshot) != (
        simulator_adapter.canonical_json_bytes(expected_snapshot)
    ) or simulator_adapter.canonical_json_bytes(actual_candidates) != (
        simulator_adapter.canonical_json_bytes(list(expected_candidates))
    ):
        raise RuntimeBlocked("cloned action application mutated the source environment")


def _validate_transition(
    transition: object,
    *,
    before: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    selected_action_id: str,
    after: Mapping[str, Any],
) -> dict[str, Any]:
    value = dict(_mapping(transition, "transition"))
    if value.get("selected_action_id") != selected_action_id:
        raise RuntimeBlocked("transition selected action mismatch")
    if value.get("category") != before["category"]:
        raise RuntimeBlocked("transition category mismatch")
    if simulator_adapter.canonical_json_bytes(value.get("candidate_actions")) != (
        simulator_adapter.canonical_json_bytes(list(candidates))
    ):
        raise RuntimeBlocked("transition candidate order mismatch")
    if simulator_adapter.canonical_json_bytes(value.get("source_state")) != (
        simulator_adapter.canonical_json_bytes(before["state"])
    ):
        raise RuntimeBlocked("transition source state mismatch")
    successor = _mapping(value.get("successor"), "transition.successor")
    expected_successor = {
        "category": after["category"],
        "state": after["state"],
        "terminal": after["terminal"],
    }
    if simulator_adapter.canonical_json_bytes(successor) != (
        simulator_adapter.canonical_json_bytes(expected_successor)
    ):
        raise RuntimeBlocked("transition successor mismatch")
    return value


def _check_deadline(
    deadline: float | None, clock: Callable[[], float], *, label: str
) -> None:
    if deadline is None:
        return
    now = _finite_float(clock(), "clock reading")
    if now > deadline:
        raise RuntimeBlocked(f"wall-time limit reached before {label}")


def _resolve_deadline(
    deadline: float | None,
    clock: Callable[[], float],
    *,
    label: str,
) -> float:
    now = _finite_float(clock(), "clock reading")
    if deadline is None:
        return now + MAX_WALL_SECONDS
    resolved = _finite_float(deadline, f"{label} deadline")
    if resolved < now:
        raise RuntimeBlocked(f"wall-time limit reached before {label}")
    if resolved - now > MAX_WALL_SECONDS:
        raise RuntimeBlocked(f"{label} deadline exceeds the wall-time ceiling")
    return resolved


def rollout_episode(
    model: torch.nn.Module,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    training: bool,
    action_generator: torch.Generator | None,
    chunk_index: int | None = None,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    before_environment: Callable[[int], None] | None = None,
) -> EpisodeRollout:
    """Run one episode by applying every selected action only to a clone."""
    active_deadline = _resolve_deadline(
        deadline, clock, label="episode environment construction"
    )
    seed_value = _nonnegative_int(seed, "episode seed")
    decision_limit = _positive_int(max_decisions, "max decisions")
    if decision_limit > MAX_DECISIONS_PER_EPISODE:
        raise RuntimeBlocked("max decisions exceeds the registered ceiling")
    if type(training) is not bool:
        raise RuntimeBlocked("training must be boolean")
    if not callable(environment_factory):
        raise RuntimeBlocked("environment_factory must be callable")
    if before_environment is not None and not callable(before_environment):
        raise RuntimeBlocked("before_environment must be callable")
    if training:
        if action_generator is None:
            raise RuntimeBlocked("training rollout requires an action generator")
        _validate_generator(action_generator)
    elif action_generator is not None:
        raise RuntimeBlocked("frozen evaluation must not consume an action generator")
    _check_deadline(active_deadline, clock, label="environment construction")
    if before_environment is not None:
        before_environment(seed_value)
    try:
        environment = environment_factory(seed_value)
    except Exception as exc:
        raise RuntimeBlocked("environment construction failed") from exc
    root_environment = environment
    root_snapshot, root_candidates = _environment_state(root_environment)

    transitions: list[dict[str, Any]] = []
    rewards: list[float] = []
    selected_terms: list[hierarchical_objective.HierarchicalPolicyTerms] = []
    diagnostic_rows: list[dict[str, Any]] = []
    last_supported_floor = 0.0
    terminal_victory = 0
    unsupported_reason: str | None = None

    while True:
        _check_deadline(active_deadline, clock, label="decision")
        snapshot, candidates = _environment_state(environment)
        if snapshot["terminal"]:
            break
        source_floor = snapshot["state"].get("floor")
        last_supported_floor = _finite_float(
            source_floor, "source floor", minimum=0.0
        )
        decision_index = len(diagnostic_rows)
        if decision_index >= decision_limit:
            raise RuntimeBlocked("episode decision resource limit reached")
        scored = score_decision(
            model,
            decision_id=f"seed-{seed_value}:decision-{decision_index}",
            snapshot=snapshot,
            candidates=candidates,
        )
        if training:
            assert action_generator is not None
            sample = sample_hierarchical_action(
                scored.scores, scored.candidates, action_generator
            )
            selected_action_id = sample.selected_action_id
            selected_family = sample.selected_family
            terms = sample.terms
            distribution = sample.distribution
            generator_hashes = {
                "after_conditional": (
                    sample.generator_state_after_conditional_sha256
                ),
                "after_family": sample.generator_state_after_family_sha256,
                "before_family": sample.generator_state_before_sha256,
            }
            selection_mode = SAMPLING_VERSION
        else:
            selection = select_unique_raw_score_action(
                scored.scores, scored.candidates
            )
            selected_action_id = selection.selected_action_id
            selected_family = selection.selected_family
            terms = selection.terms
            distribution = selection.distribution
            generator_hashes = None
            selection_mode = DETERMINISTIC_SELECTION_VERSION
        row = build_decision_diagnostic_row(
            scored,
            selected_action_id=selected_action_id,
            selected_family=selected_family,
            terms=terms,
            distribution=distribution,
            seed=seed_value,
            decision_index=decision_index,
            chunk_index=chunk_index,
            selection_mode=selection_mode,
            generator_hashes=generator_hashes,
        )
        source_snapshot = copy.deepcopy(snapshot)
        source_candidates = copy.deepcopy(candidates)
        try:
            successor = environment.clone()
        except Exception as exc:
            raise RuntimeBlocked("environment clone failed") from exc
        if successor is environment:
            raise RuntimeBlocked("environment clone must return a distinct branch")
        _assert_source_unchanged(environment, source_snapshot, source_candidates)
        try:
            transition = successor.step(selected_action_id)
            after = simulator_adapter.validate_snapshot(successor.snapshot())
        except simulator_adapter.SimulatorAdapterError as exc:
            raise RuntimeBlocked(str(exc)) from exc
        except RuntimeError as exc:
            reason = str(exc)
            if reason not in REGISTERED_SUPPORT_BLOCKERS:
                raise RuntimeBlocked(
                    f"unregistered simulator support blocker: {reason}"
                ) from exc
            _assert_source_unchanged(environment, source_snapshot, source_candidates)
            unsupported_reason = reason
            zero_channels = {
                "floor_progress": 0.0,
                "scalar_reward": 0.0,
                "terminal_victory": 0,
            }
            row["formal_reward"] = zero_channels
            row["unsupported_reason"] = reason
            rewards.append(0.0)
            selected_terms.append(terms)
            diagnostic_rows.append(row)
            break
        except (TypeError, ValueError) as exc:
            raise RuntimeBlocked(str(exc)) from exc
        except Exception as exc:
            raise RuntimeBlocked("cloned action application failed") from exc
        if after["adapter_api_version"] != simulator_adapter.ADAPTER_API_VERSION:
            raise RuntimeBlocked("successor branch drifted from exact adapter API v3")
        _assert_source_unchanged(environment, source_snapshot, source_candidates)
        normalized_transition = _validate_transition(
            transition,
            before=snapshot,
            candidates=candidates,
            selected_action_id=selected_action_id,
            after=after,
        )
        channels = formal_reward_channels(normalized_transition)
        row["formal_reward"] = channels
        transitions.append(normalized_transition)
        rewards.append(float(channels["scalar_reward"]))
        selected_terms.append(terms)
        diagnostic_rows.append(row)
        terminal_victory = max(
            terminal_victory, int(channels["terminal_victory"])
        )
        environment = successor

    _assert_source_unchanged(root_environment, root_snapshot, root_candidates)
    final_snapshot = simulator_adapter.validate_snapshot(environment.snapshot())
    if unsupported_reason is None:
        if final_snapshot["terminal"] is not True:
            raise RuntimeBlocked("supported episode did not reach a terminal state")
        outcome = final_snapshot["state"].get("outcome")
        if outcome not in {"player_loss", "player_victory"}:
            raise RuntimeBlocked("terminal episode outcome is invalid")
        last_supported_floor = _finite_float(
            final_snapshot["state"].get("floor"),
            "terminal floor",
            minimum=0.0,
        )
    formal_return = float(sum(rewards))
    if not all(
        math.isfinite(value) for value in (formal_return, last_supported_floor)
    ):
        raise RuntimeBlocked("episode reward must remain finite")
    return EpisodeRollout(
        seed=seed_value,
        training=training,
        decision_count=len(diagnostic_rows),
        transitions=tuple(transitions),
        rewards=tuple(rewards),
        selected_terms=tuple(selected_terms if training else ()),
        diagnostic_rows=tuple(diagnostic_rows),
        formal_return=formal_return,
        floor_progress=last_supported_floor,
        terminal_victory=terminal_victory,
        final_snapshot=final_snapshot,
        unsupported_reason=unsupported_reason,
    )


def episode_returns(rewards: Sequence[Real]) -> torch.Tensor:
    """Return fixed-discount return-to-go values for one episode."""
    if not rewards:
        return torch.empty(0, dtype=torch.float64, device="cpu")
    running = 0.0
    values: list[float] = []
    for index, reward in reversed(list(enumerate(rewards))):
        reward_value = _finite_float(reward, f"reward[{index}]")
        running = reward_value + DISCOUNT * running
        if not math.isfinite(running):
            raise RuntimeBlocked("episode return must remain finite")
        values.append(running)
    values.reverse()
    return torch.tensor(values, dtype=torch.float64, device="cpu")


def normalize_returns(returns: Sequence[Real] | torch.Tensor) -> torch.Tensor:
    """Preserve the consumed float32 population-variance normalization."""
    if isinstance(returns, torch.Tensor):
        if returns.device.type != "cpu" or returns.ndim != 1:
            raise RuntimeBlocked("returns tensor must be rank-1 on CPU")
        values = returns.to(dtype=torch.float32)
    else:
        values = torch.tensor(
            [
                _finite_float(value, f"return[{index}]")
                for index, value in enumerate(_sequence(returns, "returns"))
            ],
            dtype=torch.float32,
            device="cpu",
        )
    if values.numel() == 0:
        raise RuntimeBlocked("returns must be nonempty")
    if not torch.isfinite(values).all().item():
        raise RuntimeBlocked("returns must be finite")
    mean = values.mean()
    standard_deviation = values.std(unbiased=False)
    if float(standard_deviation.item()) > 1e-12:
        normalized = (values - mean) / (standard_deviation + 1e-8)
    else:
        normalized = torch.zeros_like(values)
    if not torch.isfinite(normalized).all().item():
        raise RuntimeBlocked("normalized returns must be finite")
    return normalized


def build_reinforce_loss(
    terms: Sequence[hierarchical_objective.HierarchicalPolicyTerms],
    normalized_returns: Sequence[Real] | torch.Tensor,
) -> ReinforceLoss:
    """Build the fixed joint-policy minus two separately weighted entropies."""
    term_values = list(_sequence(terms, "hierarchical terms"))
    if not term_values:
        raise RuntimeBlocked("hierarchical terms must be nonempty")
    if any(
        not isinstance(value, hierarchical_objective.HierarchicalPolicyTerms)
        for value in term_values
    ):
        raise RuntimeBlocked("hierarchical terms contain an invalid item")
    returns = (
        normalized_returns.to(dtype=torch.float64)
        if isinstance(normalized_returns, torch.Tensor)
        else torch.tensor(
            [
                _finite_float(value, f"normalized return[{index}]")
                for index, value in enumerate(
                    _sequence(normalized_returns, "normalized returns")
                )
            ],
            dtype=torch.float64,
            device="cpu",
        )
    )
    if returns.device.type != "cpu" or returns.ndim != 1:
        raise RuntimeBlocked("normalized returns must be rank-1 on CPU")
    if returns.shape[0] != len(term_values):
        raise RuntimeBlocked("normalized returns and selected terms must align")
    if not torch.isfinite(returns).all().item():
        raise RuntimeBlocked("normalized returns must be finite")
    joint_log_probabilities = torch.stack(
        [value.selected_joint_log_probability for value in term_values]
    )
    family_entropies = torch.stack([value.family_entropy for value in term_values])
    conditional_entropies = torch.stack(
        [value.conditional_entropy for value in term_values]
    )
    policy_loss = -(joint_log_probabilities * returns).mean()
    mean_family_entropy = family_entropies.mean()
    mean_conditional_entropy = conditional_entropies.mean()
    loss = (
        policy_loss
        - FAMILY_ENTROPY_COEFFICIENT * mean_family_entropy
        - CONDITIONAL_ENTROPY_COEFFICIENT * mean_conditional_entropy
    )
    exposed = (
        loss,
        policy_loss,
        mean_family_entropy,
        mean_conditional_entropy,
        joint_log_probabilities,
    )
    if any(not torch.isfinite(value).all().item() for value in exposed):
        raise RuntimeBlocked("REINFORCE objective must remain finite")
    return ReinforceLoss(
        loss=loss,
        policy_loss=policy_loss,
        mean_family_entropy=mean_family_entropy,
        mean_conditional_entropy=mean_conditional_entropy,
        normalized_returns=returns,
    )


def build_normalized_return_reinforce_loss(
    terms: Sequence[hierarchical_objective.HierarchicalPolicyTerms],
    returns: Sequence[Real] | torch.Tensor,
) -> ReinforceLoss:
    """Normalize raw returns and build the fixed successor loss."""
    normalized = normalize_returns(returns)
    return build_reinforce_loss(terms, normalized)


def _gradient_norm(parameters: Sequence[torch.nn.Parameter]) -> float:
    squared = torch.zeros((), dtype=torch.float64, device="cpu")
    for parameter in parameters:
        if parameter.grad is not None:
            if not torch.isfinite(parameter.grad).all().item():
                raise RuntimeBlocked("model gradients must remain finite")
            squared = squared + parameter.grad.detach().to(dtype=torch.float64).pow(2).sum()
    result = float(torch.sqrt(squared).item())
    if not math.isfinite(result):
        raise RuntimeBlocked("gradient norm must remain finite")
    return result


def _capture_runtime(runtime: TrainingRuntime) -> dict[str, Any]:
    """Capture rollback-safe logical state without cumulative resource use."""
    return {
        "action_generator_state": runtime.action_generator.get_state().clone(),
        "completed_decisions": runtime.completed_decisions,
        "completed_episodes": runtime.completed_episodes,
        "gradients": {
            name: None if parameter.grad is None else parameter.grad.detach().clone()
            for name, parameter in runtime.model.named_parameters()
        },
        "model_state": copy.deepcopy(runtime.model.state_dict()),
        "model_training": runtime.model.training,
        "next_chunk_index": runtime.next_chunk_index,
        "optimizer_state": copy.deepcopy(runtime.optimizer.state_dict()),
        "optimizer_updates": runtime.optimizer_updates,
        "python_rng_state": copy.deepcopy(runtime.python_rng.getstate()),
    }


def _restore_runtime(runtime: TrainingRuntime, snapshot: Mapping[str, Any]) -> None:
    runtime.model.load_state_dict(copy.deepcopy(snapshot["model_state"]), strict=True)
    runtime.optimizer.load_state_dict(copy.deepcopy(snapshot["optimizer_state"]))
    runtime.python_rng.setstate(copy.deepcopy(snapshot["python_rng_state"]))
    runtime.action_generator.set_state(snapshot["action_generator_state"].clone())
    runtime.next_chunk_index = int(snapshot["next_chunk_index"])
    runtime.completed_episodes = int(snapshot["completed_episodes"])
    runtime.completed_decisions = int(snapshot["completed_decisions"])
    runtime.optimizer_updates = int(snapshot["optimizer_updates"])
    runtime.model.train(bool(snapshot["model_training"]))
    gradients = snapshot["gradients"]
    for name, parameter in runtime.model.named_parameters():
        gradient = gradients[name]
        parameter.grad = None if gradient is None else gradient.clone()


def summarize_family_diagnostics(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Summarize category/family opportunities without treating entropy as success."""
    categories: dict[str, Any] = {}
    for category in simulator_adapter.TARGET_CATEGORIES:
        category_rows = [row for row in rows if row.get("category") == category]
        multi_family_rows = [
            row for row in category_rows if row.get("multi_family") is True
        ]
        selected_counts = Counter(
            str(row.get("selected_family")) for row in multi_family_rows
        )
        opportunity_counts: Counter[str] = Counter()
        for row in category_rows:
            for family in set(row.get("family_order", [])):
                opportunity_counts[str(family)] += 1
        maximum_set_counts = Counter(
            "|".join(row.get("raw_score_max_family_ids", []))
            for row in multi_family_rows
        )
        denominator = len(multi_family_rows)
        categories[category] = {
            "decisions": len(category_rows),
            "family_opportunities": dict(sorted(opportunity_counts.items())),
            "multi_family_decisions": denominator,
            "raw_score_max_family_sets": dict(sorted(maximum_set_counts.items())),
            "selected_families": {
                family: {
                    "count": count,
                    "rate": count / denominator if denominator else 0.0,
                }
                for family, count in sorted(selected_counts.items())
            },
        }
    return {"categories": categories}


def _validated_seed_sequence(seeds: Sequence[int], label: str) -> tuple[int, ...]:
    values = tuple(
        _nonnegative_int(seed, f"{label}[{index}]")
        for index, seed in enumerate(_sequence(seeds, label))
    )
    if not values:
        raise RuntimeBlocked(f"{label} must be nonempty")
    if len(set(values)) != len(values):
        raise RuntimeBlocked(f"{label} must be unique")
    return values


def run_training_chunk(
    runtime: TrainingRuntime,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    chunk_index: int,
    max_wall_seconds: float = MAX_WALL_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    on_resource_change: (
        Callable[[dict[str, int | float], dict[str, Any]], None] | None
    ) = None,
) -> dict[str, Any]:
    """Run one logical chunk while preserving every consumed resource debit."""
    _validate_runtime(runtime)
    expected_chunk = _nonnegative_int(chunk_index, "chunk index")
    if expected_chunk != runtime.next_chunk_index:
        raise RuntimeBlocked("chunk index does not match runtime coordinate")
    seed_values = _validated_seed_sequence(seeds, "training seeds")
    if len(seed_values) != EPISODES_PER_UPDATE:
        raise RuntimeBlocked(
            "training chunk must contain exactly the registered episodes per update"
        )
    if runtime.training_episodes + len(seed_values) > MAX_TRAINING_EPISODES:
        raise RuntimeBlocked("training episode resource limit would be exceeded")
    if (
        runtime.training_episodes
        + runtime.evaluation_episodes
        + len(seed_values)
        > MAX_TOTAL_EPISODES
    ):
        raise RuntimeBlocked("total episode resource limit would be exceeded")
    if runtime.optimizer_updates + 1 > MAX_OPTIMIZER_UPDATES:
        raise RuntimeBlocked("optimizer update resource limit would be exceeded")
    allowed_wall_seconds = _finite_float(
        max_wall_seconds, "max wall seconds", minimum=0.0
    )
    if allowed_wall_seconds <= 0.0 or allowed_wall_seconds > MAX_WALL_SECONDS:
        raise RuntimeBlocked("max wall seconds exceeds or empties the fixed ceiling")
    remaining_wall_seconds = MAX_WALL_SECONDS - runtime.charged_seconds
    if remaining_wall_seconds <= 0.0:
        raise RuntimeBlocked("wall-time resource limit reached")
    start = _finite_float(clock(), "clock reading")
    deadline = start + min(allowed_wall_seconds, remaining_wall_seconds)
    snapshot = _capture_runtime(runtime)
    wall_charge_attempted = False
    try:
        rollouts = []
        for seed in seed_values:
            rollouts.append(
                rollout_episode(
                    runtime.model,
                    environment_factory=environment_factory,
                    seed=seed,
                    training=True,
                    action_generator=runtime.action_generator,
                    chunk_index=expected_chunk,
                    max_decisions=MAX_DECISIONS_PER_EPISODE,
                    deadline=deadline,
                    clock=clock,
                    before_environment=lambda episode_seed: _debit_episode_resource(
                        runtime,
                        phase="training",
                        seed=episode_seed,
                        observer=on_resource_change,
                    ),
                )
            )
        selected_terms = [
            term for rollout in rollouts for term in rollout.selected_terms
        ]
        if not selected_terms:
            raise RuntimeBlocked("training chunk produced no policy decisions")
        raw_returns = torch.cat(
            [episode_returns(rollout.rewards) for rollout in rollouts]
        )
        objective = build_normalized_return_reinforce_loss(
            selected_terms, raw_returns
        )
        runtime.optimizer.zero_grad(set_to_none=True)
        objective.loss.backward()
        parameters = list(runtime.model.parameters())
        gradient_norm_before = _gradient_norm(parameters)
        torch.nn.utils.clip_grad_norm_(
            parameters,
            max_norm=GRADIENT_NORM_CEILING,
            error_if_nonfinite=True,
        )
        gradient_norm_after = _gradient_norm(parameters)
        if gradient_norm_after > GRADIENT_NORM_CEILING + 1e-6:
            raise RuntimeBlocked("gradient clipping ceiling was not enforced")
        runtime.optimizer.step()
        end = _finite_float(clock(), "clock reading")
        elapsed = end - start
        if elapsed < 0.0:
            raise RuntimeBlocked("clock moved backwards during training chunk")
        if end > deadline:
            raise RuntimeBlocked("wall-time limit reached during training chunk")
        wall_charge_attempted = True
        _charge_wall_resource(
            runtime,
            elapsed=elapsed,
            phase="training",
            observer=on_resource_change,
        )
        diagnostic_rows = [
            copy.deepcopy(row)
            for rollout in rollouts
            for row in rollout.diagnostic_rows
        ]
        runtime.next_chunk_index += 1
        runtime.completed_episodes += len(rollouts)
        runtime.completed_decisions += len(selected_terms)
        runtime.optimizer_updates += 1
        _validate_runtime(runtime)
        family_diagnostics = summarize_family_diagnostics(diagnostic_rows)
        resources = runtime_resource_use(runtime)
        summary = {
            "categories": sorted(
                {row["category"] for row in diagnostic_rows}
            ),
            "chunk_index": expected_chunk,
            "complete": True,
            "conditional_entropy_coefficient": (
                CONDITIONAL_ENTROPY_COEFFICIENT
            ),
            "decisions": len(selected_terms),
            "diagnostic_rows": diagnostic_rows,
            "episodes": len(rollouts),
            "episode_seeds": list(seed_values),
            "family_diagnostics": family_diagnostics,
            "family_entropy_coefficient": FAMILY_ENTROPY_COEFFICIENT,
            "gradient_norm_after_clip": gradient_norm_after,
            "gradient_norm_before_clip": gradient_norm_before,
            "loss": float(objective.loss.detach().item()),
            "mean_expected_conditional_entropy": float(
                objective.mean_conditional_entropy.detach().item()
            ),
            "mean_family_entropy": float(
                objective.mean_family_entropy.detach().item()
            ),
            "normalized_return_mean": float(
                objective.normalized_returns.mean().item()
            ),
            "normalized_return_std": float(
                objective.normalized_returns.std(unbiased=False).item()
            ),
            "optimizer_update": runtime.optimizer_updates,
            "policy_loss": float(objective.policy_loss.detach().item()),
            "resource_use": {
                **resources,
                "completed_decisions": runtime.completed_decisions,
            },
            "schema_version": CHUNK_SUMMARY_SCHEMA_VERSION,
        }
        if not all(
            math.isfinite(float(summary[field]))
            for field in (
                "gradient_norm_after_clip",
                "gradient_norm_before_clip",
                "loss",
                "mean_expected_conditional_entropy",
                "mean_family_entropy",
                "policy_loss",
            )
        ):
            raise RuntimeBlocked("chunk summary contains a non-finite value")
        return summary
    except BaseException as exc:
        _restore_runtime(runtime, snapshot)
        if not wall_charge_attempted:
            try:
                end = _finite_float(clock(), "clock reading")
                elapsed = end - start
                if elapsed < 0.0:
                    raise RuntimeBlocked(
                        "clock moved backwards during failed training chunk"
                    )
                wall_charge_attempted = True
                _charge_wall_resource(
                    runtime,
                    elapsed=elapsed,
                    phase="training",
                    observer=on_resource_change,
                )
            except BaseException as charge_exc:
                if isinstance(charge_exc, (KeyboardInterrupt, SystemExit)):
                    raise
                if isinstance(charge_exc, RuntimeBlocked):
                    raise
                raise RuntimeBlocked(str(charge_exc)) from charge_exc
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        if isinstance(exc, RuntimeBlocked):
            raise
        raise RuntimeBlocked(str(exc)) from exc


def classify_training_family_saturation(
    chunk_summaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply the exact four-durable-chunk, 64-decision saturation predicate."""
    summaries = list(_sequence(chunk_summaries, "chunk summaries"))
    result = {
        "categories": {},
        "saturated": False,
        "verdict": None,
        "window_chunk_indices": [],
    }
    if len(summaries) < SATURATION_WINDOW_CHUNKS:
        return result
    window = summaries[-SATURATION_WINDOW_CHUNKS:]
    indices: list[int] = []
    for offset, summary in enumerate(window):
        if not isinstance(summary, Mapping) or summary.get("complete") is not True:
            return result
        indices.append(
            _nonnegative_int(summary.get("chunk_index"), f"window chunk[{offset}]")
        )
    if indices != list(range(indices[0], indices[0] + SATURATION_WINDOW_CHUNKS)):
        return result
    result["window_chunk_indices"] = indices
    all_rows = [
        row
        for summary in window
        for row in _sequence(summary.get("diagnostic_rows"), "diagnostic rows")
        if isinstance(row, Mapping)
    ]
    for category in SATURATION_CATEGORIES:
        eligible = [
            row
            for row in all_rows
            if row.get("category") == category and row.get("multi_family") is True
        ]
        maximum_sets = [
            tuple(row.get("raw_score_max_family_ids", ())) for row in eligible
        ]
        singleton_families = [
            maximum_set[0] for maximum_set in maximum_sets if len(maximum_set) == 1
        ]
        saturated_family = (
            singleton_families[0]
            if len(eligible) >= SATURATION_MINIMUM_MULTI_FAMILY_DECISIONS
            and len(singleton_families) == len(eligible)
            and len(set(singleton_families)) == 1
            else None
        )
        category_result = {
            "multi_family_decisions": len(eligible),
            "saturated": saturated_family is not None,
            "saturated_family": saturated_family,
            "singleton_max_family_rate": (
                len(singleton_families) / len(eligible) if eligible else 0.0
            ),
        }
        result["categories"][category] = category_result
        if saturated_family is not None:
            result["saturated"] = True
    if result["saturated"]:
        result["verdict"] = (
            "experiment_stopped_during_training_for_family_saturation"
        )
    return result


def encode_checkpoint_state(runtime: TrainingRuntime) -> dict[str, Any]:
    """Encode every resumable runtime state and cumulative coordinate."""
    _validate_runtime(runtime)
    return {
        "algorithm": {
            "conditional_entropy_coefficient": (
                runtime.conditional_entropy_coefficient
            ),
            "family_entropy_coefficient": runtime.family_entropy_coefficient,
            "sampling": SAMPLING_VERSION,
        },
        "coordinates": {
            "completed_decisions": runtime.completed_decisions,
            "completed_episodes": runtime.completed_episodes,
            "next_chunk_index": runtime.next_chunk_index,
            "optimizer_updates": runtime.optimizer_updates,
        },
        "model_architecture": runtime.model.architecture_metadata(),
        "resource_use": {
            "charged_seconds": runtime.charged_seconds,
            "evaluation_episodes": runtime.evaluation_episodes,
            "optimizer_updates": runtime.optimizer_updates,
            "total_episodes": runtime.training_episodes + runtime.evaluation_episodes,
            "training_episodes": runtime.training_episodes,
        },
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "states": {
            "action_generator": encode_tensor(
                runtime.action_generator.get_state()
            ),
            "model": encode_model_state(runtime.model),
            "optimizer": encode_optimizer_state(runtime.optimizer),
            "python_rng": _encode_state_value(runtime.python_rng.getstate()),
        },
    }


def decode_checkpoint_state(value: object) -> DecodedCheckpointState:
    """Strictly decode a successor checkpoint without accepting drift."""
    checkpoint = _mapping(value, "checkpoint")
    _exact_keys(
        checkpoint,
        {
            "algorithm",
            "coordinates",
            "model_architecture",
            "resource_use",
            "schema_version",
            "states",
        },
        "checkpoint",
    )
    if checkpoint["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise RuntimeBlocked("checkpoint schema version mismatch")
    expected_algorithm = {
        "conditional_entropy_coefficient": CONDITIONAL_ENTROPY_COEFFICIENT,
        "family_entropy_coefficient": FAMILY_ENTROPY_COEFFICIENT,
        "sampling": SAMPLING_VERSION,
    }
    if checkpoint["algorithm"] != expected_algorithm:
        raise RuntimeBlocked("checkpoint algorithm or coefficient mismatch")
    expected_architecture = {
        "architecture_id": "state-conditioned-candidate-ranker-mlp-v1",
        "candidate_input_dim": HASH_DIM,
        "device": "cpu",
        "dtype": "float32",
        "hidden_dim": DEFAULT_HIDDEN_DIM,
        "state_conditioned": True,
        "state_input_dim": HASH_DIM,
    }
    if checkpoint["model_architecture"] != expected_architecture:
        raise RuntimeBlocked("checkpoint model architecture mismatch")
    coordinates = _mapping(checkpoint["coordinates"], "checkpoint.coordinates")
    _exact_keys(
        coordinates,
        {
            "completed_decisions",
            "completed_episodes",
            "next_chunk_index",
            "optimizer_updates",
        },
        "checkpoint.coordinates",
    )
    completed_decisions = _nonnegative_int(
        coordinates["completed_decisions"], "checkpoint completed decisions"
    )
    completed_episodes = _nonnegative_int(
        coordinates["completed_episodes"], "checkpoint completed episodes"
    )
    next_chunk_index = _nonnegative_int(
        coordinates["next_chunk_index"], "checkpoint next chunk index"
    )
    optimizer_updates = _nonnegative_int(
        coordinates["optimizer_updates"], "checkpoint optimizer updates"
    )
    if next_chunk_index != optimizer_updates:
        raise RuntimeBlocked("checkpoint chunk and optimizer coordinates differ")
    if completed_episodes != optimizer_updates * EPISODES_PER_UPDATE:
        raise RuntimeBlocked("checkpoint completed episode coordinate mismatch")
    resource_use = _mapping(checkpoint["resource_use"], "checkpoint.resource_use")
    _exact_keys(
        resource_use,
        {
            "charged_seconds",
            "evaluation_episodes",
            "optimizer_updates",
            "total_episodes",
            "training_episodes",
        },
        "checkpoint.resource_use",
    )
    evaluation_episodes = _nonnegative_int(
        resource_use["evaluation_episodes"], "checkpoint evaluation episodes"
    )
    training_episodes = _nonnegative_int(
        resource_use["training_episodes"], "checkpoint training episodes"
    )
    if training_episodes < completed_episodes:
        raise RuntimeBlocked("checkpoint training resources precede coordinates")
    if _nonnegative_int(
        resource_use["optimizer_updates"], "checkpoint resource optimizer updates"
    ) != optimizer_updates:
        raise RuntimeBlocked("checkpoint optimizer resource coordinate mismatch")
    if _nonnegative_int(
        resource_use["total_episodes"], "checkpoint total episodes"
    ) != training_episodes + evaluation_episodes:
        raise RuntimeBlocked("checkpoint total episode accounting mismatch")
    charged_seconds = _finite_float(
        resource_use["charged_seconds"],
        "checkpoint charged seconds",
        minimum=0.0,
    )
    states = _mapping(checkpoint["states"], "checkpoint.states")
    _exact_keys(
        states,
        {"action_generator", "model", "optimizer", "python_rng"},
        "checkpoint.states",
    )
    model_mapping = _mapping(states["model"], "checkpoint model state")
    model_state = {
        str(name): decode_tensor(tensor, f"checkpoint model state.{name}")
        for name, tensor in model_mapping.items()
    }
    python_rng_state = _decode_state_value(
        states["python_rng"], "checkpoint Python RNG"
    )
    if not isinstance(python_rng_state, tuple):
        raise RuntimeBlocked("checkpoint Python RNG must decode to a tuple")
    action_generator_state = decode_tensor(
        states["action_generator"], "checkpoint action generator"
    )
    if (
        action_generator_state.dtype != torch.uint8
        or action_generator_state.device.type != "cpu"
        or action_generator_state.ndim != 1
        or action_generator_state.numel() == 0
    ):
        raise RuntimeBlocked("checkpoint action generator state is invalid")
    return DecodedCheckpointState(
        model_state=model_state,
        optimizer_state=decode_optimizer_state(states["optimizer"]),
        python_rng_state=python_rng_state,
        action_generator_state=action_generator_state,
        next_chunk_index=next_chunk_index,
        completed_episodes=completed_episodes,
        completed_decisions=completed_decisions,
        optimizer_updates=optimizer_updates,
        training_episodes=training_episodes,
        evaluation_episodes=evaluation_episodes,
        charged_seconds=charged_seconds,
    )


def restore_training_runtime_from_checkpoint(value: object) -> TrainingRuntime:
    """Restore an exact runtime and reject any non-round-tripping state."""
    decoded = decode_checkpoint_state(value)
    runtime = initialize_training_runtime()
    try:
        runtime.model.load_state_dict(decoded.model_state, strict=True)
        runtime.optimizer.load_state_dict(decoded.optimizer_state)
        runtime.python_rng.setstate(decoded.python_rng_state)
        runtime.action_generator.set_state(decoded.action_generator_state)
    except (TypeError, ValueError, RuntimeError) as exc:
        raise RuntimeBlocked("checkpoint state restoration failed") from exc
    runtime.next_chunk_index = decoded.next_chunk_index
    runtime.completed_episodes = decoded.completed_episodes
    runtime.completed_decisions = decoded.completed_decisions
    runtime.optimizer_updates = decoded.optimizer_updates
    runtime.training_episodes = decoded.training_episodes
    runtime.evaluation_episodes = decoded.evaluation_episodes
    runtime.charged_seconds = decoded.charged_seconds
    _validate_runtime(runtime)
    if encode_checkpoint_state(runtime) != dict(_mapping(value, "checkpoint")):
        raise RuntimeBlocked("restored checkpoint does not round-trip exactly")
    return runtime


# Concise aliases for control-plane callers.
build_checkpoint_state = encode_checkpoint_state
restore_training_runtime = restore_training_runtime_from_checkpoint


def _model_state_sha256(model: torch.nn.Module) -> str:
    payload = simulator_adapter.canonical_json_bytes(encode_model_state(model))
    return hashlib.sha256(payload).hexdigest()


def evaluate_frozen_policy(
    model: torch.nn.Module,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    cohort: str,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    resource_runtime: TrainingRuntime | None = None,
    on_resource_change: (
        Callable[[dict[str, int | float], dict[str, Any]], None] | None
    ) = None,
) -> dict[str, Any]:
    """Evaluate unique raw-score actions once without model or RNG updates."""
    if resource_runtime is None and on_resource_change is not None:
        raise RuntimeBlocked("resource observer requires a resource runtime")
    resource_started = (
        _finite_float(clock(), "clock reading")
        if resource_runtime is not None
        else None
    )
    if resource_runtime is not None:
        _validate_runtime(resource_runtime)
    active_deadline = _resolve_deadline(
        deadline, clock, label=f"{cohort} evaluation"
    )
    seed_values = _validated_seed_sequence(seeds, "evaluation seeds")
    if len(seed_values) > MAX_EVALUATION_EPISODES:
        raise RuntimeBlocked("evaluation episode resource limit exceeded")
    if not isinstance(cohort, str) or not cohort:
        raise RuntimeBlocked("cohort must be a nonempty string")
    model_before = _model_state_sha256(model)
    was_training = model.training
    model.eval()
    try:
        with torch.no_grad():
            rollouts = []
            for seed in seed_values:
                rollouts.append(
                    rollout_episode(
                        model,
                        environment_factory=environment_factory,
                        seed=seed,
                        training=False,
                        action_generator=None,
                        deadline=active_deadline,
                        clock=clock,
                        before_environment=(
                            None
                            if resource_runtime is None
                            else lambda episode_seed: _debit_episode_resource(
                                resource_runtime,
                                phase=cohort,
                                seed=episode_seed,
                                observer=on_resource_change,
                            )
                        ),
                    )
                )
    finally:
        model.train(was_training)
        if resource_runtime is not None:
            assert resource_started is not None
            ended = _finite_float(clock(), "clock reading")
            if ended < resource_started:
                raise RuntimeBlocked("clock moved backwards during evaluation")
            _charge_wall_resource(
                resource_runtime,
                elapsed=ended - resource_started,
                phase=cohort,
                observer=on_resource_change,
            )
    if _model_state_sha256(model) != model_before:
        raise RuntimeBlocked("frozen evaluation mutated the model")
    episode_rows = [
        {
            "categories": sorted(
                {row["category"] for row in rollout.diagnostic_rows}
            ),
            "decisions": rollout.decision_count,
            "floor_progress": rollout.floor_progress,
            "formal_return": rollout.formal_return,
            "seed": rollout.seed,
            "terminal_victory": rollout.terminal_victory,
            "unsupported_reason": rollout.unsupported_reason,
        }
        for rollout in rollouts
    ]
    diagnostic_rows = [
        copy.deepcopy(row)
        for rollout in rollouts
        for row in rollout.diagnostic_rows
    ]
    return {
        "categories": sorted(
            {row["category"] for row in diagnostic_rows}
        ),
        "cohort": cohort,
        "diagnostic_rows": diagnostic_rows,
        "episode_rows": episode_rows,
        "episodes": len(rollouts),
        "floor_progress": float(sum(row["floor_progress"] for row in episode_rows)),
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "unsupported_episodes": sum(
            row["unsupported_reason"] is not None for row in episode_rows
        ),
        "victories": sum(row["terminal_victory"] for row in episode_rows),
    }


def _evaluation_with_replay(
    model: torch.nn.Module,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    cohort: str,
    deadline: float | None,
    clock: Callable[[], float],
    resource_runtime: TrainingRuntime | None,
    on_resource_change: (
        Callable[[dict[str, int | float], dict[str, Any]], None] | None
    ),
) -> dict[str, Any]:
    first = evaluate_frozen_policy(
        model,
        environment_factory=environment_factory,
        seeds=seeds,
        cohort=cohort,
        deadline=deadline,
        clock=clock,
        resource_runtime=resource_runtime,
        on_resource_change=on_resource_change,
    )
    replay = evaluate_frozen_policy(
        model,
        environment_factory=environment_factory,
        seeds=seeds,
        cohort=cohort,
        deadline=deadline,
        clock=clock,
        resource_runtime=resource_runtime,
        on_resource_change=on_resource_change,
    )
    replay_exact = simulator_adapter.canonical_json_bytes(first) == (
        simulator_adapter.canonical_json_bytes(replay)
    )
    return {
        **first,
        "replay_diagnostic_rows": replay["diagnostic_rows"],
        "replay_episode_rows": replay["episode_rows"],
        "replay_exact": replay_exact,
    }


def paired_bootstrap_interval(
    differences: Sequence[Real],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    confidence: float = BOOTSTRAP_CONFIDENCE,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Return a deterministic paired mean interval for synthetic replay evidence."""
    values = [
        _finite_float(value, f"paired difference[{index}]")
        for index, value in enumerate(_sequence(differences, "paired differences"))
    ]
    if not values:
        raise RuntimeBlocked("paired differences must be nonempty")
    resample_count = _positive_int(resamples, "bootstrap resamples")
    confidence_value = _finite_float(confidence, "bootstrap confidence")
    bootstrap_seed = _nonnegative_int(seed, "bootstrap seed")
    if (
        resample_count != BOOTSTRAP_RESAMPLES
        or confidence_value != BOOTSTRAP_CONFIDENCE
        or bootstrap_seed != BOOTSTRAP_SEED
    ):
        raise RuntimeBlocked("bootstrap controls differ from the registered contract")
    rng = random.Random(bootstrap_seed)
    sample_count = len(values)
    means = sorted(
        sum(values[rng.randrange(sample_count)] for _ in range(sample_count))
        / sample_count
        for _ in range(resample_count)
    )
    def quantile(probability: float) -> float:
        position = (len(means) - 1) * probability
        lower_index = math.floor(position)
        upper_index = math.ceil(position)
        if lower_index == upper_index:
            return means[lower_index]
        weight = position - lower_index
        return means[lower_index] * (1.0 - weight) + means[upper_index] * weight

    alpha = (1.0 - confidence_value) / 2.0
    return {
        "confidence": confidence_value,
        "lower": quantile(alpha),
        "mean": sum(values) / sample_count,
        "resamples": resample_count,
        "seed": bootstrap_seed,
        "upper": quantile(1.0 - alpha),
    }


def paired_policy_evaluation(
    initial_model: torch.nn.Module,
    trained_model: torch.nn.Module,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    cohort: str,
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    resource_runtime: TrainingRuntime | None = None,
    on_resource_change: (
        Callable[[dict[str, int | float], dict[str, Any]], None] | None
    ) = None,
) -> dict[str, Any]:
    """Evaluate initial/trained policies and exact replays on identical seeds."""
    if (
        bootstrap_resamples != BOOTSTRAP_RESAMPLES
        or bootstrap_seed != BOOTSTRAP_SEED
    ):
        raise RuntimeBlocked("bootstrap controls differ from the registered contract")
    active_deadline = _resolve_deadline(
        deadline, clock, label=f"{cohort} paired evaluation"
    )
    seed_values = _validated_seed_sequence(seeds, "paired evaluation seeds")
    evaluation_episodes = len(seed_values) * 4
    if evaluation_episodes > MAX_EVALUATION_EPISODES:
        raise RuntimeBlocked("paired evaluation episode resource limit exceeded")
    initial = _evaluation_with_replay(
        initial_model,
        environment_factory=environment_factory,
        seeds=seed_values,
        cohort=cohort,
        deadline=active_deadline,
        clock=clock,
        resource_runtime=resource_runtime,
        on_resource_change=on_resource_change,
    )
    trained = _evaluation_with_replay(
        trained_model,
        environment_factory=environment_factory,
        seeds=seed_values,
        cohort=cohort,
        deadline=active_deadline,
        clock=clock,
        resource_runtime=resource_runtime,
        on_resource_change=on_resource_change,
    )
    initial_by_seed = {row["seed"]: row for row in initial["episode_rows"]}
    trained_by_seed = {row["seed"]: row for row in trained["episode_rows"]}
    paired_rows = [
        {
            "floor_difference": (
                trained_by_seed[seed]["floor_progress"]
                - initial_by_seed[seed]["floor_progress"]
            ),
            "initial_floor_progress": initial_by_seed[seed]["floor_progress"],
            "seed": seed,
            "trained_floor_progress": trained_by_seed[seed]["floor_progress"],
        }
        for seed in seed_values
    ]
    interval = paired_bootstrap_interval(
        [row["floor_difference"] for row in paired_rows],
        resamples=bootstrap_resamples,
        confidence=BOOTSTRAP_CONFIDENCE,
        seed=bootstrap_seed,
    )
    unsupported_episodes = (
        initial["unsupported_episodes"] + trained["unsupported_episodes"]
    )
    unsupported_denominator = 2 * len(seed_values)
    return {
        "cohort": cohort,
        "evaluation_episodes": evaluation_episodes,
        "floor_difference_ci": interval,
        "initial": initial,
        "paired_rows": paired_rows,
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "trained": trained,
        "unsupported_rate": unsupported_episodes / unsupported_denominator,
        "unsupported_rate_denominator": unsupported_denominator,
    }


def classify_canary_family_gate(
    diagnostic_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply the fixed card-reward/shop family-diversity canary gates."""
    rows = list(_sequence(diagnostic_rows, "canary diagnostic rows"))
    blockers: list[str] = []
    categories: dict[str, Any] = {}
    for category in SATURATION_CATEGORIES:
        eligible = [
            row
            for row in rows
            if isinstance(row, Mapping)
            and row.get("category") == category
            and row.get("multi_family") is True
        ]
        selected_counts: Counter[str] = Counter()
        tie_count = 0
        alignment_failures = 0
        for row in eligible:
            maximum_families = tuple(row.get("raw_score_max_family_ids", ()))
            if len(maximum_families) != 1:
                tie_count += 1
                continue
            selected_family = str(row.get("selected_family"))
            if selected_family != maximum_families[0]:
                alignment_failures += 1
                continue
            selected_counts[selected_family] += 1
        maximum_rate = (
            max(selected_counts.values()) / len(eligible)
            if eligible and selected_counts
            else 0.0
        )
        if len(eligible) < CANARY_MINIMUM_MULTI_FAMILY_DECISIONS:
            blockers.append(f"{category}_multi_family_decisions")
        if len(selected_counts) < CANARY_MINIMUM_SELECTED_FAMILIES:
            blockers.append(f"{category}_selected_families")
        if maximum_rate > CANARY_MAXIMUM_SELECTED_FAMILY_RATE:
            blockers.append(f"{category}_selected_family_rate")
        if tie_count:
            blockers.append(f"{category}_raw_score_ties")
        if alignment_failures:
            blockers.append(f"{category}_raw_score_alignment")
        categories[category] = {
            "alignment_failures": alignment_failures,
            "largest_selected_family_rate": maximum_rate,
            "multi_family_decisions": len(eligible),
            "raw_score_ties": tie_count,
            "selected_families": dict(sorted(selected_counts.items())),
        }
    return {
        "blockers": sorted(set(blockers)),
        "categories": categories,
        "passed": not blockers,
    }


def _classify_state_effects(
    diagnostic_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    summaries: dict[str, Any] = {}
    blockers: list[str] = []
    for category in simulator_adapter.TARGET_CATEGORIES:
        rows = [
            row
            for row in diagnostic_rows
            if row.get("category") == category and len(row.get("candidates", ())) > 1
        ]
        nonzero = [
            row
            for row in rows
            if _finite_float(
                _mapping(row.get("state_effect"), "state effect").get(
                    "max_abs_relative_score_change"
                ),
                "state-effect change",
                minimum=0.0,
            )
            >= STATE_EFFECT_MINIMUM_ABSOLUTE_CHANGE
        ]
        order_changes = sum(
            _mapping(row.get("state_effect"), "state effect").get(
                "relative_order_changed"
            )
            is True
            for row in rows
        )
        nonzero_rate = len(nonzero) / len(rows) if rows else 0.0
        passed = (
            len(rows) >= STATE_EFFECT_MINIMUM_DECISIONS
            and nonzero_rate >= STATE_EFFECT_MINIMUM_NONZERO_RATE
            and order_changes >= 1
        )
        if not passed:
            blockers.append(f"{category}_state_effect")
        summaries[category] = {
            "decisions": len(rows),
            "nonzero_rate": nonzero_rate,
            "relative_order_changes": order_changes,
        }
    return summaries, blockers


def classify_canary_evaluation(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    """Classify the fixed structural, state, family, victory, and floor gates."""
    value = _mapping(evaluation, "canary evaluation")
    initial = _mapping(value.get("initial"), "canary initial policy")
    trained = _mapping(value.get("trained"), "canary trained policy")
    blockers: list[str] = []
    if initial.get("replay_exact") is not True or trained.get("replay_exact") is not True:
        blockers.append("exact_replay")
    if set(initial.get("categories", ())) != set(simulator_adapter.TARGET_CATEGORIES):
        blockers.append("initial_category_coverage")
    if set(trained.get("categories", ())) != set(simulator_adapter.TARGET_CATEGORIES):
        blockers.append("trained_category_coverage")
    unsupported_rate = _finite_float(
        value.get("unsupported_rate"), "unsupported rate", minimum=0.0
    )
    paired_rows = list(_sequence(value.get("paired_rows"), "paired rows"))
    if not paired_rows:
        raise RuntimeBlocked("paired rows must be nonempty")
    interval = _mapping(value.get("floor_difference_ci"), "floor difference CI")
    expected_interval = paired_bootstrap_interval(
        [
            _mapping(row, f"paired row[{index}]").get("floor_difference")
            for index, row in enumerate(paired_rows)
        ]
    )
    if dict(interval) != expected_interval:
        raise RuntimeBlocked("bootstrap evidence differs from the registered controls")
    unsupported_denominator = _positive_int(
        value.get("unsupported_rate_denominator"),
        "unsupported rate denominator",
    )
    if unsupported_denominator != 2 * len(paired_rows):
        raise RuntimeBlocked("unsupported rate denominator mismatch")
    unsupported_episodes = _nonnegative_int(
        initial.get("unsupported_episodes"), "initial unsupported episodes"
    ) + _nonnegative_int(
        trained.get("unsupported_episodes"), "trained unsupported episodes"
    )
    if unsupported_rate != unsupported_episodes / unsupported_denominator:
        raise RuntimeBlocked("unsupported rate evidence mismatch")
    if unsupported_rate > UNSUPPORTED_RATE_CEILING:
        blockers.append("unsupported_rate")
    trained_rows = list(
        _sequence(trained.get("diagnostic_rows"), "trained diagnostic rows")
    )
    if any(
        row.get("selected_action_id") not in row.get("legal_action_ids", ())
        for row in trained_rows
    ):
        blockers.append("legality")
    family_gate = classify_canary_family_gate(trained_rows)
    blockers.extend(family_gate["blockers"])
    state_effects, state_blockers = _classify_state_effects(trained_rows)
    blockers.extend(state_blockers)
    initial_victories = _nonnegative_int(
        initial.get("victories"), "initial victories"
    )
    trained_victories = _nonnegative_int(
        trained.get("victories"), "trained victories"
    )
    if trained_victories < initial_victories:
        blockers.append("victory_noninferiority")
    lower = _finite_float(interval.get("lower"), "floor difference lower bound")
    if lower <= 0.0:
        blockers.append("paired_floor_lower_bound")
    unique_blockers = sorted(set(blockers))
    return {
        "blockers": unique_blockers,
        "family_gate": family_gate,
        "passed": not unique_blockers,
        "state_effects": state_effects,
    }


def classify_terminal_verdict(
    *,
    complete: bool,
    structural_valid: bool,
    behavior_valid: bool,
    floor_signal: bool,
    initial_victories: int,
    trained_victories: int,
    blocked: bool = False,
) -> str:
    """Return only the bounded successor terminal verdict vocabulary."""
    flags = (complete, structural_valid, behavior_valid, floor_signal, blocked)
    if any(type(flag) is not bool for flag in flags):
        raise RuntimeBlocked("terminal verdict flags must be boolean")
    initial = _nonnegative_int(initial_victories, "initial victories")
    trained = _nonnegative_int(trained_victories, "trained victories")
    if blocked or not complete:
        return "experiment_blocked"
    if not structural_valid:
        return "experiment_invalid"
    if not behavior_valid or not floor_signal or trained < initial:
        return "experiment_valid_without_learning_signal"
    if trained > initial:
        return "experiment_valid_with_victory_signal"
    return "experiment_valid_with_floor_only_signal"


def run_conditional_evaluation(
    initial_model: torch.nn.Module,
    trained_model: torch.nn.Module,
    *,
    environment_factory: Callable[[int], Any],
    canary_seeds: Sequence[int],
    holdout_seeds: Sequence[int],
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    on_canary_complete: Callable[[dict[str, Any]], None] | None = None,
    on_holdout_start: Callable[[], None] | None = None,
    on_holdout_complete: Callable[[dict[str, Any]], None] | None = None,
    resource_runtime: TrainingRuntime | None = None,
    on_resource_change: (
        Callable[[dict[str, int | float], dict[str, Any]], None] | None
    ) = None,
) -> dict[str, Any]:
    """Evaluate holdout only after every fixed canary gate passes."""
    if bootstrap_resamples != BOOTSTRAP_RESAMPLES:
        raise RuntimeBlocked("bootstrap controls differ from the registered contract")
    active_deadline = _resolve_deadline(
        deadline, clock, label="conditional evaluation"
    )
    canary_values = _validated_seed_sequence(canary_seeds, "canary seeds")
    holdout_values = _validated_seed_sequence(holdout_seeds, "holdout seeds")
    if set(canary_values).intersection(holdout_values):
        raise RuntimeBlocked("canary and holdout seeds must be disjoint")
    prospective_episodes = 4 * (len(canary_values) + len(holdout_values))
    if prospective_episodes > MAX_EVALUATION_EPISODES:
        raise RuntimeBlocked("conditional evaluation resource limit exceeded")
    canary = paired_policy_evaluation(
        initial_model,
        trained_model,
        environment_factory=environment_factory,
        seeds=canary_values,
        cohort="canary",
        bootstrap_resamples=bootstrap_resamples,
        deadline=active_deadline,
        clock=clock,
        resource_runtime=resource_runtime,
        on_resource_change=on_resource_change,
    )
    canary_gate = classify_canary_evaluation(canary)
    prefix = {
        "canary": canary,
        "canary_gate": canary_gate,
        "holdout": {"accessed": False, "episode_count": 0},
        "verdict": (
            "canary_passed_pending_holdout"
            if canary_gate["passed"]
            else "experiment_stopped_at_canary"
        ),
    }
    if on_canary_complete is not None:
        on_canary_complete(copy.deepcopy(prefix))
    if not canary_gate["passed"]:
        return prefix
    _check_deadline(active_deadline, clock, label="holdout construction")
    if on_holdout_start is not None:
        on_holdout_start()
    holdout = paired_policy_evaluation(
        initial_model,
        trained_model,
        environment_factory=environment_factory,
        seeds=holdout_values,
        cohort="holdout",
        bootstrap_resamples=bootstrap_resamples,
        deadline=active_deadline,
        clock=clock,
        resource_runtime=resource_runtime,
        on_resource_change=on_resource_change,
    )
    holdout_gate = classify_canary_evaluation(holdout)
    structural_blockers = {
        "exact_replay",
        "initial_category_coverage",
        "legality",
        "trained_category_coverage",
    }
    observed_blockers = set(holdout_gate["blockers"])
    structural_valid = not observed_blockers.intersection(structural_blockers)
    behavior_valid = not (
        observed_blockers - structural_blockers - {"paired_floor_lower_bound"}
    )
    floor_signal = holdout["floor_difference_ci"]["lower"] > 0.0
    verdict = classify_terminal_verdict(
        complete=True,
        structural_valid=structural_valid,
        behavior_valid=behavior_valid,
        floor_signal=floor_signal,
        initial_victories=holdout["initial"]["victories"],
        trained_victories=holdout["trained"]["victories"],
    )
    result = {
        "canary": canary,
        "canary_gate": canary_gate,
        "holdout": {
            "accessed": True,
            "episode_count": holdout["evaluation_episodes"],
            "evaluation": holdout,
            "family_gate": holdout_gate["family_gate"],
            "gate": holdout_gate,
        },
        "verdict": verdict,
    }
    if on_holdout_complete is not None:
        on_holdout_complete(copy.deepcopy(result))
    return result
