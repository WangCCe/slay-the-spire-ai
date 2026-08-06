"""Torch runtime primitives for cross-fitted hierarchical learning."""

from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import math
import random
import struct
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import torch

from analysis_scripts import noncombat_action_family_distribution as family_distribution
from analysis_scripts import noncombat_formal_reward_contract as formal_reward_contract
from analysis_scripts.noncombat_hierarchical_advantage_attribution import (
    COMPONENT_NAMES,
    FEATURE_FIELDS,
    FEATURE_SCHEMA_VERSION,
    AdvantageAttributionError,
    AdvantageBatch,
    GradientLedger,
    build_advantage_batch,
    build_gradient_ledger,
)
from analysis_scripts import noncombat_hierarchical_policy_objective as objective_contract
from analysis_scripts import noncombat_hierarchical_simulator_learning_runtime as consumed_runtime
from analysis_scripts import noncombat_simulator_adapter as simulator_adapter
from analysis_scripts.noncombat_state_conditioned_policy_input import (
    HASH_DIM,
    PolicyInputError,
    project_state_conditioned_policy_input,
)
from analysis_scripts.noncombat_state_conditioned_ranker import (
    DEFAULT_HIDDEN_DIM,
    StateConditionedCandidateRanker,
)


RUNTIME_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-runtime-v1"
)
BASELINE_FEATURE_SCHEMA_VERSION = "cross-fitted-baseline-state-features-v1"
BASELINE_FEATURE_DIM = 128
BASELINE_SOURCE_DIM = 1024
FOLD_COUNT = 4
TRAJECTORIES_PER_CHUNK = 64
HELD_OUT_TRAJECTORIES_PER_FOLD = 16
FIT_TRAJECTORIES_PER_FOLD = 48
RIDGE_COEFFICIENT = 0.001
RIDGE_RESIDUAL_ATOL = 1e-9
RIDGE_RESIDUAL_RTOL = 1e-9
PREDICTION_MIN = 0.0
PREDICTION_MAX = 3.0
FAMILY_ENTROPY_COEFFICIENT = 0.01
CONDITIONAL_ENTROPY_COEFFICIENT = 0.01
GRADIENT_NORM_CEILING = 1.0
GRADIENT_CLIP_EPSILON = 1e-6
ADAM_LEARNING_RATE = 0.001
ADAM_BETAS = (0.9, 0.999)
ADAM_EPSILON = 1e-8
ADAM_WEIGHT_DECAY = 0.0
MODEL_SEED = 0
PYTHON_RNG_SEED = 0
ACTION_GENERATOR_SEED = 0
ASCENSION = 0
CHUNK_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-chunk-evidence-v1"
)
CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-runtime-checkpoint-v1"
)
MAX_BINARY_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_DECISIONS_PER_EPISODE = 500
MAX_CHARGED_SECONDS = 14_400.0
REGISTERED_SUPPORT_BLOCKERS = (
    "unsupported_shop_courier_restock_semantics",
)

if HASH_DIM != BASELINE_SOURCE_DIM:
    raise RuntimeError("registered policy-input width changed")


class RuntimeBlocked(ValueError):
    """Raised when a runtime mechanism input violates the frozen contract."""


@dataclass(frozen=True)
class BaselineDecision:
    """One complete pre-decision feature and return record."""

    category: str
    decision_id: str
    decision_index: int
    raw_return: float
    seed: int
    state_features: torch.Tensor
    trajectory_id: str
    reward: float | None = None


@dataclass(frozen=True)
class RidgeFoldModel:
    """One held-out fold's independently replayable ridge fit."""

    fold_id: str
    fit_trajectory_ids: tuple[str, ...]
    held_out_trajectory_ids: tuple[str, ...]
    coefficients: tuple[float, ...]
    kkt_residuals: tuple[float, ...]
    rhs: tuple[float, ...]
    absolute_product_sums: tuple[float, ...]


@dataclass(frozen=True)
class BaselinePrediction:
    """One exact held-out linear prediction and clipping diagnostic."""

    decision_id: str
    fold_id: str
    trajectory_id: str
    unclipped: float
    clipped: float
    was_clipped: bool
    preclip_little_endian_hex: str
    feature_sha256: str


@dataclass(frozen=True)
class CrossFittedBaselineResult:
    """Validated four-fold models, predictions, and advantages."""

    fold_trajectories: Mapping[str, tuple[str, ...]]
    models: tuple[RidgeFoldModel, ...]
    predictions: tuple[BaselinePrediction, ...]
    advantage_batch: AdvantageBatch


@dataclass(frozen=True)
class CrossFittedObjective:
    """The exact five-component fixed-unit residual objective."""

    full_loss: torch.Tensor
    components: Mapping[str, torch.Tensor]
    advantages: torch.Tensor
    decision_ids: tuple[str, ...]


@dataclass(frozen=True)
class LegacyObjectiveDiagnostic:
    """Consumed normalized-return objective differentiated without a step."""

    normalized_returns: torch.Tensor
    loss_value: float
    gradient: torch.Tensor
    gradient_norm: float
    clip_factor: float


@dataclass(frozen=True)
class GradientUpdateEvidence:
    """Pre-step gradient ledger, dual clipping paths, and legacy diagnostic."""

    ledger: GradientLedger
    parameter_names: tuple[str, ...]
    parameter_shapes: tuple[tuple[int, ...], ...]
    pre_parameter_sha256: str
    installed_gradient: torch.Tensor
    consumed_torch_clipped_gradient: torch.Tensor
    clip_comparison: Mapping[str, float]
    legacy_normalized_returns: torch.Tensor
    legacy_gradient: torch.Tensor
    legacy_loss_value: float
    gradient_comparison: Mapping[str, float | None]


@dataclass(frozen=True)
class AdamStepEvidence:
    """One exact Adam transition after installing the validated gradient."""

    parameter_names: tuple[str, ...]
    installed_gradient: torch.Tensor
    pre_parameters: tuple[torch.Tensor, ...]
    pre_steps: tuple[int, ...]
    pre_exp_avg: tuple[torch.Tensor, ...]
    pre_exp_avg_sq: tuple[torch.Tensor, ...]
    post_parameters: tuple[torch.Tensor, ...]
    post_steps: tuple[int, ...]
    post_exp_avg: tuple[torch.Tensor, ...]
    post_exp_avg_sq: tuple[torch.Tensor, ...]


@dataclass
class CrossFittedTrainingRuntime:
    """Fixed model, optimizer, and RNG state before any authorized execution."""

    model: StateConditionedCandidateRanker
    optimizer: torch.optim.Adam
    python_rng: random.Random
    action_generator: torch.Generator
    next_chunk_index: int = 0
    completed_episodes: int = 0
    completed_decisions: int = 0
    optimizer_updates: int = 0


@dataclass(frozen=True)
class CrossFittedTrainingDecision:
    """One selected policy term aligned with its baseline decision evidence."""

    baseline_decision: BaselineDecision
    terms: objective_contract.HierarchicalPolicyTerms
    diagnostic: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class CrossFittedChunkUpdate:
    """One complete in-memory cross-fitted update and its retained evidence."""

    chunk_index: int
    baseline: CrossFittedBaselineResult
    objective: CrossFittedObjective
    gradient: GradientUpdateEvidence
    adam: AdamStepEvidence
    decisions: tuple[CrossFittedTrainingDecision, ...]


@dataclass(frozen=True)
class CrossFittedEpisodeRollout:
    """One complete clone-only training trajectory with retained decision inputs."""

    seed: int
    trajectory_id: str
    decisions: tuple[CrossFittedTrainingDecision, ...]
    transitions: tuple[dict[str, Any], ...]
    rewards: tuple[float, ...]
    final_snapshot: dict[str, Any]
    floor_progress: float
    terminal_victory: int
    unsupported_reason: str | None


@dataclass(frozen=True)
class CrossFittedCollectedChunk:
    """Exactly 64 completed trajectories and their single optimizer update."""

    chunk_index: int
    seeds: tuple[int, ...]
    episodes: tuple[CrossFittedEpisodeRollout, ...]
    update: CrossFittedChunkUpdate


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeBlocked("value is not canonical JSON") from exc
    return rendered.encode("ascii") + b"\n"


def _validate_float32_vector(
    value: Any, *, width: int, label: str
) -> torch.Tensor:
    if not isinstance(value, torch.Tensor) or value.shape != (width,):
        raise RuntimeBlocked(f"{label} must have shape ({width},)")
    if value.device.type != "cpu" or value.dtype != torch.float32:
        raise RuntimeBlocked(f"{label} must be CPU float32")
    if not torch.isfinite(value).all().item():
        raise RuntimeBlocked(f"{label} must be finite")
    return value


def fold_state_features(source: torch.Tensor) -> torch.Tensor:
    """Fold 1,024 state-only float32 values into 128 in source-index order."""
    source_value = _validate_float32_vector(
        source, width=BASELINE_SOURCE_DIM, label="policy state features"
    )
    folded = torch.zeros(BASELINE_FEATURE_DIM, dtype=torch.float32, device="cpu")
    for source_index in range(BASELINE_SOURCE_DIM):
        target_index = source_index % BASELINE_FEATURE_DIM
        folded[target_index] = folded[target_index] + source_value[source_index]
    if not torch.isfinite(folded).all().item():
        raise RuntimeBlocked("folded state features must remain finite")
    return folded


def project_baseline_state_features(
    snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> torch.Tensor:
    """Project only the consumed exact-API-v3 pre-decision state channel."""
    try:
        policy_input = project_state_conditioned_policy_input(snapshot, candidates)
    except (PolicyInputError, TypeError, ValueError, RuntimeError) as exc:
        raise RuntimeBlocked(str(exc)) from exc
    return fold_state_features(policy_input.state_features)


def sparse_state_feature_payload(value: torch.Tensor) -> dict[str, Any]:
    """Encode canonical nonzero float32 entries and their deterministic identity."""
    vector = _validate_float32_vector(
        value, width=BASELINE_FEATURE_DIM, label="baseline state features"
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
        "sha256": hashlib.sha256(_canonical_json_bytes(identity)).hexdigest(),
    }


def runtime_metadata() -> dict[str, Any]:
    """Return the frozen runtime mechanism identity without execution authority."""
    return {
        "adapter_api_version": simulator_adapter.ADAPTER_API_VERSION,
        "algorithm": {
            "architecture": "state-conditioned-candidate-ranker-mlp-v1",
            "conditional_entropy_coefficient": CONDITIONAL_ENTROPY_COEFFICIENT,
            "discount": 1.0,
            "family_entropy_coefficient": FAMILY_ENTROPY_COEFFICIENT,
            "gradient_norm_ceiling": GRADIENT_NORM_CEILING,
            "learning_rate": ADAM_LEARNING_RATE,
            "model_seed": MODEL_SEED,
            "optimizer": "adam",
            "optimizer_amsgrad": False,
            "optimizer_betas": list(ADAM_BETAS),
            "optimizer_eps": ADAM_EPSILON,
            "optimizer_weight_decay": ADAM_WEIGHT_DECAY,
            "sampling": "family-first-then-conditional-v1",
        },
        "authority": {
            "communication_mod": False,
            "environment_construction": False,
            "evaluation": False,
            "execution": False,
            "formal_rl": False,
            "gameplay": False,
            "model_fitting": False,
            "model_loading": False,
            "native_loading": False,
            "policy_promotion": False,
            "qualification": False,
            "seed_access": False,
            "training": False,
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
            "trajectory_weighting": "equal-trajectory-mean-squared-error-v1",
        },
        "baseline_feature_dim": BASELINE_FEATURE_DIM,
        "baseline_feature_schema_version": BASELINE_FEATURE_SCHEMA_VERSION,
        "device": "cpu",
        "environment": {
            "adapter_api_version": simulator_adapter.ADAPTER_API_VERSION,
            "ascension": ASCENSION,
            "device": "cpu",
        },
        "fold_count": FOLD_COUNT,
        "rng": {
            "action_generator_seed": ACTION_GENERATOR_SEED,
            "python_rng_seed": PYTHON_RNG_SEED,
        },
        "ridge_coefficient": RIDGE_COEFFICIENT,
        "schema_version": RUNTIME_SCHEMA_VERSION,
    }


def initialize_training_runtime() -> CrossFittedTrainingRuntime:
    """Create the unchanged CPU ranker, Adam controls, and deterministic RNGs."""
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(MODEL_SEED)
        model = StateConditionedCandidateRanker(HASH_DIM, DEFAULT_HIDDEN_DIM)
    model.to(device="cpu", dtype=torch.float32)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=ADAM_LEARNING_RATE,
        betas=ADAM_BETAS,
        eps=ADAM_EPSILON,
        weight_decay=ADAM_WEIGHT_DECAY,
        amsgrad=False,
        maximize=False,
        foreach=None,
        capturable=False,
        differentiable=False,
        fused=None,
    )
    action_generator = torch.Generator(device="cpu")
    action_generator.manual_seed(ACTION_GENERATOR_SEED)
    return CrossFittedTrainingRuntime(
        model=model,
        optimizer=optimizer,
        python_rng=random.Random(PYTHON_RNG_SEED),
        action_generator=action_generator,
    )


def build_trajectory_baseline_decisions(
    *,
    seed: int,
    trajectory_id: str,
    decision_ids: Sequence[str],
    categories: Sequence[str],
    state_features: Sequence[torch.Tensor],
    rewards: Sequence[float],
) -> tuple[BaselineDecision, ...]:
    """Build complete per-decision records using undiscounted return-to-go."""
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise RuntimeBlocked("trajectory seed must be a nonnegative integer")
    if not isinstance(trajectory_id, str) or not trajectory_id:
        raise RuntimeBlocked("trajectory identity must be nonempty")
    sequences = (decision_ids, categories, state_features, rewards)
    if any(
        isinstance(value, (str, bytes)) or not isinstance(value, Sequence)
        for value in sequences
    ):
        raise RuntimeBlocked("trajectory decision fields must be sequences")
    counts = {len(value) for value in sequences}
    if counts != {len(decision_ids)} or not decision_ids:
        raise RuntimeBlocked("complete trajectory decision fields must align")
    if len(set(decision_ids)) != len(decision_ids) or any(
        not isinstance(value, str) or not value for value in decision_ids
    ):
        raise RuntimeBlocked("decision identities must be nonempty and unique")
    if any(not isinstance(value, str) or not value for value in categories):
        raise RuntimeBlocked("decision categories must be nonempty")

    return_to_go = [0.0] * len(rewards)
    running = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        reward = rewards[index]
        if isinstance(reward, bool):
            raise RuntimeBlocked("formal rewards must be finite")
        try:
            reward_value = float(reward)
        except (TypeError, ValueError) as exc:
            raise RuntimeBlocked("formal rewards must be finite") from exc
        if not math.isfinite(reward_value):
            raise RuntimeBlocked("formal rewards must be finite")
        running = float(reward_value) + float(running)
        if not math.isfinite(running) or not 0.0 <= running <= 3.0:
            raise RuntimeBlocked("return-to-go must remain in [0, 3]")
        return_to_go[index] = running

    decisions: list[BaselineDecision] = []
    for index, (decision_id, category, features, raw_return) in enumerate(
        zip(decision_ids, categories, state_features, return_to_go, strict=True)
    ):
        validated = _validate_float32_vector(
            features,
            width=BASELINE_FEATURE_DIM,
            label="baseline state features",
        )
        decisions.append(
            BaselineDecision(
                category=category,
                decision_id=decision_id,
                decision_index=index,
                raw_return=raw_return,
                seed=seed,
                state_features=validated.detach().clone(),
                trajectory_id=trajectory_id,
                reward=float(rewards[index]),
            )
        )
    return tuple(decisions)


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
    except simulator_adapter.SimulatorAdapterError as exc:
        raise RuntimeBlocked(str(exc)) from exc
    except RuntimeBlocked:
        raise
    except Exception as exc:
        raise RuntimeBlocked("environment state access failed") from exc
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
    transition: Any,
    *,
    before: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    selected_action_id: str,
    after: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(transition, Mapping):
        raise RuntimeBlocked("transition must be a mapping")
    value = dict(transition)
    if value.get("selected_action_id") != selected_action_id:
        raise RuntimeBlocked("transition selected action differs")
    if value.get("category") != before["category"]:
        raise RuntimeBlocked("transition category differs")
    if simulator_adapter.canonical_json_bytes(value.get("candidate_actions")) != (
        simulator_adapter.canonical_json_bytes(list(candidates))
    ):
        raise RuntimeBlocked("transition candidate order differs")
    if simulator_adapter.canonical_json_bytes(value.get("source_state")) != (
        simulator_adapter.canonical_json_bytes(before["state"])
    ):
        raise RuntimeBlocked("transition source state differs")
    successor = value.get("successor")
    if not isinstance(successor, Mapping):
        raise RuntimeBlocked("transition successor must be a mapping")
    expected_successor = {
        "category": after["category"],
        "state": after["state"],
        "terminal": after["terminal"],
    }
    if simulator_adapter.canonical_json_bytes(dict(successor)) != (
        simulator_adapter.canonical_json_bytes(expected_successor)
    ):
        raise RuntimeBlocked("transition successor differs")
    return value


def _generator_state_sha256(generator: torch.Generator) -> str:
    state = generator.get_state()
    return hashlib.sha256(bytes(state.tolist())).hexdigest()


def _sample_training_decision(
    model: StateConditionedCandidateRanker,
    *,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    action_generator: torch.Generator,
    seed: int,
    chunk_index: int,
    decision_index: int,
) -> tuple[torch.Tensor, objective_contract.HierarchicalPolicyTerms, dict[str, Any]]:
    if not isinstance(action_generator, torch.Generator) or action_generator.device.type != "cpu":
        raise RuntimeBlocked("action generator must remain on CPU")
    try:
        policy_input = project_state_conditioned_policy_input(snapshot, candidates)
        scores = model(
            policy_input.state_features, policy_input.candidate_features
        )
        distribution = family_distribution.build_action_family_distribution(
            scores, candidates
        )
    except (
        PolicyInputError,
        family_distribution.ActionFamilyDistributionError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        raise RuntimeBlocked(str(exc)) from exc

    before_family = _generator_state_sha256(action_generator)
    family_draw = torch.multinomial(
        distribution.family_probabilities,
        num_samples=1,
        replacement=True,
        generator=action_generator,
    )
    family_index = int(family_draw.item())
    after_family = _generator_state_sha256(action_generator)
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
        generator=action_generator,
    )
    selected_index = member_indices[int(conditional_draw.item())]
    selected_action_id = distribution.action_ids[selected_index]
    after_conditional = _generator_state_sha256(action_generator)
    try:
        terms = objective_contract.build_hierarchical_policy_terms(
            scores, candidates, selected_action_id
        )
    except objective_contract.HierarchicalPolicyObjectiveError as exc:
        raise RuntimeBlocked(str(exc)) from exc
    if (
        terms.selected_family != selected_family
        or terms.selected_index != selected_index
        or terms.family_order != distribution.family_order
        or terms.action_ids != distribution.action_ids
    ):
        raise RuntimeBlocked("sampled policy metadata differs")

    maximum_score = torch.max(scores.detach())
    maximum_action_ids = tuple(
        sorted(
            distribution.action_ids[index]
            for index in range(scores.shape[0])
            if bool(torch.eq(scores.detach()[index], maximum_score).item())
        )
    )
    family_by_action = {
        candidate["action_id"]: candidate["kind"] for candidate in candidates
    }
    maximum_family_ids = sorted(
        {family_by_action[action_id] for action_id in maximum_action_ids}
    )
    diagnostic = {
        "action_generator_state_sha256": {
            "after_conditional": after_conditional,
            "after_family": after_family,
            "before_family": before_family,
        },
        "candidate_scores": {
            action_id: float(scores[index].detach().item())
            for index, action_id in enumerate(distribution.action_ids)
        },
        "candidates": [
            {"action_id": candidate["action_id"], "kind": candidate["kind"]}
            for candidate in candidates
        ],
        "category": snapshot["category"],
        "chunk_index": chunk_index,
        "conditional_probabilities": {
            action_id: float(
                distribution.conditional_log_probabilities[index]
                .detach()
                .exp()
                .item()
            )
            for index, action_id in enumerate(distribution.action_ids)
        },
        "decision_id": f"seed-{seed}:decision-{decision_index}",
        "decision_index": decision_index,
        "family_order": list(distribution.family_order),
        "family_probabilities": {
            family: float(distribution.family_probabilities[index].detach().item())
            for index, family in enumerate(distribution.family_order)
        },
        "joint_probabilities": {
            action_id: float(
                distribution.candidate_probabilities[index].detach().item()
            )
            for index, action_id in enumerate(distribution.action_ids)
        },
        "multi_family": len(distribution.family_order) > 1,
        "raw_score_max_action_ids": list(maximum_action_ids),
        "raw_score_max_family_ids": maximum_family_ids,
        "selected_action_id": selected_action_id,
        "selected_family": selected_family,
        "selection_mode": "family-first-then-conditional-v1",
    }
    return fold_state_features(policy_input.state_features), terms, diagnostic


def rollout_training_episode(
    runtime: CrossFittedTrainingRuntime,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    chunk_index: int,
    before_environment: Callable[[int], None] | None = None,
    max_decisions: int = MAX_DECISIONS_PER_EPISODE,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> CrossFittedEpisodeRollout:
    """Run one registered clone-only trajectory and retain every pre-action input."""
    _validate_training_runtime(runtime)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise RuntimeBlocked("episode seed must be a nonnegative integer")
    if isinstance(chunk_index, bool) or not isinstance(chunk_index, int) or chunk_index != runtime.next_chunk_index:
        raise RuntimeBlocked("episode chunk index differs from runtime coordinate")
    if (
        isinstance(max_decisions, bool)
        or not isinstance(max_decisions, int)
        or not 0 < max_decisions <= MAX_DECISIONS_PER_EPISODE
    ):
        raise RuntimeBlocked("episode decision ceiling is invalid")
    if not callable(environment_factory) or not callable(clock):
        raise RuntimeBlocked("episode environment factory and clock must be callable")
    if before_environment is not None and not callable(before_environment):
        raise RuntimeBlocked("before-environment hook must be callable")
    now = float(clock())
    if not math.isfinite(now):
        raise RuntimeBlocked("clock reading must be finite")
    active_deadline = now + MAX_CHARGED_SECONDS if deadline is None else float(deadline)
    if (
        not math.isfinite(active_deadline)
        or active_deadline < now
        or active_deadline - now > MAX_CHARGED_SECONDS
    ):
        raise RuntimeBlocked("episode deadline exceeds the registered bound")
    if before_environment is not None:
        before_environment(seed)
    if float(clock()) > active_deadline:
        raise RuntimeBlocked("wall-time limit reached before environment construction")
    try:
        environment = environment_factory(seed)
    except Exception as exc:
        raise RuntimeBlocked("environment construction failed") from exc
    root_environment = environment
    root_snapshot, root_candidates = _environment_state(root_environment)

    pending: list[
        tuple[
            str,
            str,
            torch.Tensor,
            objective_contract.HierarchicalPolicyTerms,
            dict[str, Any],
        ]
    ] = []
    rewards: list[float] = []
    transitions: list[dict[str, Any]] = []
    terminal_victory = 0
    floor_progress = 0.0
    unsupported_reason: str | None = None
    while True:
        if float(clock()) > active_deadline:
            raise RuntimeBlocked("wall-time limit reached before decision")
        snapshot, candidates = _environment_state(environment)
        if snapshot["terminal"]:
            break
        decision_index = len(pending)
        if decision_index >= max_decisions:
            raise RuntimeBlocked("episode decision ceiling reached")
        state_features, terms, diagnostic = _sample_training_decision(
            runtime.model,
            snapshot=snapshot,
            candidates=candidates,
            action_generator=runtime.action_generator,
            seed=seed,
            chunk_index=chunk_index,
            decision_index=decision_index,
        )
        selected_action_id = terms.selected_action_id
        source_snapshot = copy.deepcopy(snapshot)
        source_candidates = copy.deepcopy(candidates)
        try:
            successor = environment.clone()
        except Exception as exc:
            raise RuntimeBlocked("environment clone failed") from exc
        if successor is environment:
            raise RuntimeBlocked("environment clone must return a distinct branch")
        _assert_source_unchanged(
            environment, source_snapshot, source_candidates
        )
        try:
            transition = successor.step(selected_action_id)
            after = simulator_adapter.validate_snapshot(successor.snapshot())
        except RuntimeError as exc:
            reason = str(exc)
            if reason not in REGISTERED_SUPPORT_BLOCKERS:
                raise RuntimeBlocked(
                    f"unregistered simulator support blocker: {reason}"
                ) from exc
            _assert_source_unchanged(
                environment, source_snapshot, source_candidates
            )
            unsupported_reason = reason
            diagnostic["formal_reward"] = {
                "floor_progress": 0.0,
                "scalar_reward": 0.0,
                "terminal_victory": 0,
            }
            diagnostic["unsupported_reason"] = reason
            rewards.append(0.0)
            pending.append(
                (
                    snapshot["category"],
                    diagnostic["decision_id"],
                    state_features,
                    terms,
                    diagnostic,
                )
            )
            break
        except simulator_adapter.SimulatorAdapterError as exc:
            raise RuntimeBlocked(str(exc)) from exc
        except Exception as exc:
            raise RuntimeBlocked("cloned action application failed") from exc
        if after["adapter_api_version"] != simulator_adapter.ADAPTER_API_VERSION:
            raise RuntimeBlocked("successor branch drifted from exact adapter API v3")
        _assert_source_unchanged(
            environment, source_snapshot, source_candidates
        )
        normalized_transition = _validate_transition(
            transition,
            before=snapshot,
            candidates=candidates,
            selected_action_id=selected_action_id,
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
            raise RuntimeBlocked(str(exc)) from exc
        reward = 2.0 * float(channels["terminal_victory"]) + float(
            channels["floor_progress"]
        )
        if not math.isfinite(reward):
            raise RuntimeBlocked("formal reward must be finite")
        diagnostic["formal_reward"] = {
            **channels,
            "scalar_reward": reward,
        }
        pending.append(
            (
                snapshot["category"],
                diagnostic["decision_id"],
                state_features,
                terms,
                diagnostic,
            )
        )
        rewards.append(reward)
        transitions.append(normalized_transition)
        terminal_victory = max(
            terminal_victory, int(channels["terminal_victory"])
        )
        floor_progress += float(channels["floor_progress"])
        environment = successor

    _assert_source_unchanged(root_environment, root_snapshot, root_candidates)
    try:
        final_snapshot = simulator_adapter.validate_snapshot(environment.snapshot())
    except simulator_adapter.SimulatorAdapterError as exc:
        raise RuntimeBlocked(str(exc)) from exc
    if unsupported_reason is None:
        if final_snapshot["terminal"] is not True:
            raise RuntimeBlocked("supported episode did not terminate")
        if final_snapshot["state"].get("outcome") not in {
            "player_loss",
            "player_victory",
        }:
            raise RuntimeBlocked("terminal episode outcome is invalid")
    if not pending:
        raise RuntimeBlocked("training episode must contain at least one decision")
    baseline_decisions = build_trajectory_baseline_decisions(
        seed=seed,
        trajectory_id=f"seed-{seed}",
        decision_ids=tuple(item[1] for item in pending),
        categories=tuple(item[0] for item in pending),
        state_features=tuple(item[2] for item in pending),
        rewards=tuple(rewards),
    )
    training_decisions = tuple(
        CrossFittedTrainingDecision(
            baseline_decision=baseline,
            terms=item[3],
            diagnostic=item[4],
        )
        for baseline, item in zip(baseline_decisions, pending, strict=True)
    )
    return CrossFittedEpisodeRollout(
        seed=seed,
        trajectory_id=f"seed-{seed}",
        decisions=training_decisions,
        transitions=tuple(transitions),
        rewards=tuple(rewards),
        final_snapshot=final_snapshot,
        floor_progress=floor_progress,
        terminal_victory=terminal_victory,
        unsupported_reason=unsupported_reason,
    )


def collect_and_update_training_chunk(
    runtime: CrossFittedTrainingRuntime,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    chunk_index: int,
    before_environment: Callable[[int], None],
    after_environment: Callable[[int], None],
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
) -> CrossFittedCollectedChunk:
    """Collect exactly one registered chunk, then perform its sole update."""
    _validate_training_runtime(runtime)
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise RuntimeBlocked("training chunk seeds must be a sequence")
    seed_values = tuple(seeds)
    if (
        len(seed_values) != TRAJECTORIES_PER_CHUNK
        or any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in seed_values
        )
        or len(set(seed_values)) != TRAJECTORIES_PER_CHUNK
        or seed_values != tuple(sorted(seed_values))
    ):
        raise RuntimeBlocked("training chunk requires 64 unique ascending seeds")
    if not callable(before_environment) or not callable(after_environment):
        raise RuntimeBlocked("training chunk journal hooks must be callable")
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or chunk_index != runtime.next_chunk_index
    ):
        raise RuntimeBlocked("training chunk index differs from runtime coordinate")
    try:
        deadline_value = float(deadline)
    except (TypeError, ValueError) as exc:
        raise RuntimeBlocked("training chunk deadline must be finite") from exc
    now = float(clock())
    if (
        not math.isfinite(now)
        or not math.isfinite(deadline_value)
        or deadline_value < now
        or deadline_value - now > MAX_CHARGED_SECONDS
    ):
        raise RuntimeBlocked("training chunk deadline exceeds the registered bound")

    episodes: list[CrossFittedEpisodeRollout] = []
    decisions: list[CrossFittedTrainingDecision] = []
    for seed in seed_values:
        rollout = rollout_training_episode(
            runtime,
            environment_factory=environment_factory,
            seed=seed,
            chunk_index=chunk_index,
            before_environment=before_environment,
            deadline=deadline_value,
            clock=clock,
        )
        after_environment(seed)
        episodes.append(rollout)
        decisions.extend(rollout.decisions)
        if runtime.completed_decisions + len(decisions) > 32_768:
            raise RuntimeBlocked("retained decision ceiling would be exceeded")
    update = run_cross_fitted_chunk_update(
        runtime,
        chunk_index=chunk_index,
        decisions=tuple(decisions),
    )
    return CrossFittedCollectedChunk(
        chunk_index=chunk_index,
        seeds=seed_values,
        episodes=tuple(episodes),
        update=update,
    )


def _normalized_decisions(
    decisions: Sequence[BaselineDecision],
) -> tuple[
    tuple[BaselineDecision, ...],
    tuple[str, ...],
    dict[str, tuple[BaselineDecision, ...]],
]:
    if isinstance(decisions, (str, bytes)) or not isinstance(decisions, Sequence):
        raise RuntimeBlocked("baseline decisions must be a sequence")
    source = tuple(decisions)
    if not source:
        raise RuntimeBlocked("baseline decisions must be nonempty")

    by_trajectory: dict[str, list[BaselineDecision]] = {}
    seen_decision_ids: set[str] = set()
    for index, decision in enumerate(source):
        if not isinstance(decision, BaselineDecision):
            raise RuntimeBlocked(f"baseline decision {index} has the wrong type")
        if not decision.trajectory_id or not decision.decision_id:
            raise RuntimeBlocked("trajectory and decision identities must be nonempty")
        if decision.decision_id in seen_decision_ids:
            raise RuntimeBlocked("decision identities must be unique")
        seen_decision_ids.add(decision.decision_id)
        if not decision.category:
            raise RuntimeBlocked("decision category must be nonempty")
        if (
            isinstance(decision.decision_index, bool)
            or not isinstance(decision.decision_index, int)
            or decision.decision_index < 0
        ):
            raise RuntimeBlocked("decision index must be nonnegative")
        if isinstance(decision.seed, bool) or not isinstance(decision.seed, int):
            raise RuntimeBlocked("trajectory seed must be an integer")
        if isinstance(decision.raw_return, bool):
            raise RuntimeBlocked("raw return must be finite and bounded")
        try:
            raw_return = float(decision.raw_return)
        except (TypeError, ValueError) as exc:
            raise RuntimeBlocked("raw return must be finite and bounded") from exc
        if not math.isfinite(raw_return) or not 0.0 <= raw_return <= 3.0:
            raise RuntimeBlocked("raw return must be finite and bounded in [0, 3]")
        if decision.reward is not None:
            if isinstance(decision.reward, bool):
                raise RuntimeBlocked("decision reward must be finite")
            try:
                reward = float(decision.reward)
            except (TypeError, ValueError) as exc:
                raise RuntimeBlocked("decision reward must be finite") from exc
            if not math.isfinite(reward):
                raise RuntimeBlocked("decision reward must be finite")
        _validate_float32_vector(
            decision.state_features,
            width=BASELINE_FEATURE_DIM,
            label="baseline state features",
        )
        by_trajectory.setdefault(decision.trajectory_id, []).append(decision)

    if len(by_trajectory) != TRAJECTORIES_PER_CHUNK:
        raise RuntimeBlocked("cross-fitted baseline requires exactly 64 trajectories")

    seed_by_trajectory: dict[str, int] = {}
    seen_seeds: set[int] = set()
    normalized_by_trajectory: dict[str, tuple[BaselineDecision, ...]] = {}
    for trajectory_id, trajectory_decisions in by_trajectory.items():
        seeds = {decision.seed for decision in trajectory_decisions}
        if len(seeds) != 1:
            raise RuntimeBlocked("one trajectory must have exactly one seed")
        seed = next(iter(seeds))
        if seed in seen_seeds:
            raise RuntimeBlocked("trajectory seeds must be unique")
        seen_seeds.add(seed)
        seed_by_trajectory[trajectory_id] = seed
        ordered = tuple(
            sorted(trajectory_decisions, key=lambda item: item.decision_index)
        )
        indices = [decision.decision_index for decision in ordered]
        if indices != list(range(len(ordered))):
            raise RuntimeBlocked("trajectory decision indices must be contiguous")
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


def _fold_manifest(trajectory_order: Sequence[str]) -> dict[str, tuple[str, ...]]:
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
        len(identities) != HELD_OUT_TRAJECTORIES_PER_FOLD
        for identities in manifest.values()
    ):
        raise RuntimeBlocked("every fold must hold out exactly 16 trajectories")
    return manifest


def _augmented_sparse_float64_features(
    decision: BaselineDecision,
) -> tuple[tuple[int, float], ...]:
    entries = [(0, 1.0)]
    for feature_index in range(BASELINE_FEATURE_DIM):
        value = float(decision.state_features[feature_index].item())
        if value != 0.0:
            entries.append((feature_index + 1, float(value)))
    return tuple(entries)


def _fit_fold_model(
    *,
    fold_id: str,
    held_out_ids: tuple[str, ...],
    trajectory_order: Sequence[str],
    by_trajectory: Mapping[str, tuple[BaselineDecision, ...]],
) -> RidgeFoldModel:
    held_out_set = set(held_out_ids)
    fit_ids = tuple(sorted(set(trajectory_order).difference(held_out_set)))
    if len(fit_ids) != FIT_TRAJECTORIES_PER_FOLD:
        raise RuntimeBlocked("every fold must fit exactly 48 trajectories")

    width = BASELINE_FEATURE_DIM + 1
    normal_matrix = torch.zeros((width, width), dtype=torch.float64)
    rhs = torch.zeros(width, dtype=torch.float64)
    for trajectory_id in trajectory_order:
        if trajectory_id in held_out_set:
            continue
        trajectory = by_trajectory[trajectory_id]
        weight = torch.tensor(
            1.0 / (FIT_TRAJECTORIES_PER_FOLD * len(trajectory)),
            dtype=torch.float64,
        )
        for decision in trajectory:
            weight_value = float(weight.item())
            target_value = float(decision.raw_return)
            sparse_features = _augmented_sparse_float64_features(decision)
            for row_index, row_value in sparse_features:
                rhs[row_index] = float(rhs[row_index].item()) + (
                    (weight_value * target_value) * float(row_value)
                )
                for column_index, column_value in sparse_features:
                    normal_matrix[row_index, column_index] = float(
                        normal_matrix[row_index, column_index].item()
                    ) + (
                        (weight_value * float(row_value)) * float(column_value)
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
        raise RuntimeBlocked("registered float64 Cholesky ridge solve failed") from exc
    if not torch.isfinite(coefficients).all().item():
        raise RuntimeBlocked("ridge coefficients must be finite")

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
            raise RuntimeBlocked("ridge KKT residual exceeds the fixed boundary")
    return RidgeFoldModel(
        fold_id=fold_id,
        fit_trajectory_ids=fit_ids,
        held_out_trajectory_ids=held_out_ids,
        coefficients=coefficient_values,
        kkt_residuals=tuple(float(value) for value in residuals.tolist()),
        rhs=tuple(float(value) for value in rhs.tolist()),
        absolute_product_sums=tuple(
            float(value) for value in product_sums.tolist()
        ),
    )


def _predict(model: RidgeFoldModel, decision: BaselineDecision) -> BaselinePrediction:
    values = [1.0]
    values.extend(
        float(decision.state_features[index].item())
        for index in range(BASELINE_FEATURE_DIM)
    )
    unclipped = math.fsum(
        float(model.coefficients[index]) * float(values[index])
        for index in range(BASELINE_FEATURE_DIM + 1)
    )
    if not math.isfinite(unclipped):
        raise RuntimeBlocked("held-out ridge prediction must be finite")
    clipped = min(PREDICTION_MAX, max(PREDICTION_MIN, unclipped))
    feature_sha256 = sparse_state_feature_payload(decision.state_features)["sha256"]
    return BaselinePrediction(
        decision_id=decision.decision_id,
        fold_id=model.fold_id,
        trajectory_id=decision.trajectory_id,
        unclipped=unclipped,
        clipped=clipped,
        was_clipped=clipped != unclipped,
        preclip_little_endian_hex=struct.pack("<d", unclipped).hex(),
        feature_sha256=feature_sha256,
    )


def build_cross_fitted_baseline(
    decisions: Sequence[BaselineDecision],
) -> CrossFittedBaselineResult:
    """Fit four trajectory-disjoint ridge models and build fixed-unit advantages."""
    canonical, trajectory_order, by_trajectory = _normalized_decisions(decisions)
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

    predictions: list[BaselinePrediction] = []
    records: list[dict[str, Any]] = []
    for decision in canonical:
        fold_id = fold_by_trajectory[decision.trajectory_id]
        model = model_by_fold[fold_id]
        prediction = _predict(model, decision)
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
            records, fold_trajectories=fold_trajectories
        )
    except AdvantageAttributionError as exc:
        raise RuntimeBlocked(str(exc)) from exc
    return CrossFittedBaselineResult(
        fold_trajectories=fold_trajectories,
        models=models,
        predictions=tuple(predictions),
        advantage_batch=advantage_batch,
    )


def _validated_objective_inputs(
    *,
    terms: Sequence[objective_contract.HierarchicalPolicyTerms],
    categories: Sequence[str],
    advantage_batch: AdvantageBatch,
) -> tuple[
    tuple[objective_contract.HierarchicalPolicyTerms, ...],
    tuple[str, ...],
    tuple[float, ...],
    tuple[str, ...],
]:
    if not isinstance(advantage_batch, AdvantageBatch):
        raise RuntimeBlocked("advantage batch must use the checked-in contract")
    if isinstance(terms, (str, bytes)) or not isinstance(terms, Sequence):
        raise RuntimeBlocked("hierarchical terms must be a sequence")
    if isinstance(categories, (str, bytes)) or not isinstance(categories, Sequence):
        raise RuntimeBlocked("decision categories must be a sequence")
    term_values = tuple(terms)
    category_values = tuple(categories)
    records = tuple(advantage_batch.records)
    if not records or len(term_values) != len(records) or len(category_values) != len(records):
        raise RuntimeBlocked("terms, categories, and advantages must align")
    if any(
        not isinstance(value, objective_contract.HierarchicalPolicyTerms)
        for value in term_values
    ):
        raise RuntimeBlocked("hierarchical terms contain an invalid item")
    if any(not isinstance(value, str) or not value for value in category_values):
        raise RuntimeBlocked("decision categories must be nonempty strings")

    advantages: list[float] = []
    decision_ids: list[str] = []
    for record in records:
        if (
            record.baseline_mode != "cross_fitted"
            or record.scale_mode != "fixed_unit"
            or record.scale != 1.0
        ):
            raise RuntimeBlocked("advantage provenance must use cross-fitted fixed-unit mode")
        expected = record.raw_return - record.baseline_prediction
        if not math.isfinite(expected) or record.advantage != expected:
            raise RuntimeBlocked("advantage differs from the held-out residual")
        if record.confounding_reduction_claimed:
            raise RuntimeBlocked("advantage evidence cannot make a causal claim")
        advantages.append(float(record.advantage))
        decision_ids.append(record.decision_id)
    if len(set(decision_ids)) != len(decision_ids):
        raise RuntimeBlocked("advantage decision identities must be unique")
    return term_values, category_values, tuple(advantages), tuple(decision_ids)


def _graph_connected_zero(
    terms: Sequence[objective_contract.HierarchicalPolicyTerms],
) -> torch.Tensor:
    zero = terms[0].selected_joint_log_probability * 0.0
    for term in terms[1:]:
        zero = zero + term.selected_joint_log_probability * 0.0
    return zero


def build_cross_fitted_objective(
    *,
    terms: Sequence[objective_contract.HierarchicalPolicyTerms],
    categories: Sequence[str],
    advantage_batch: AdvantageBatch,
) -> CrossFittedObjective:
    """Build the frozen five components without a second normalization."""
    term_values, category_values, advantages, decision_ids = (
        _validated_objective_inputs(
            terms=terms,
            categories=categories,
            advantage_batch=advantage_batch,
        )
    )
    denominator = float(len(term_values))
    zero = _graph_connected_zero(term_values)

    card_family = zero
    card_conditional = zero
    other = zero
    for term, category, advantage in zip(
        term_values, category_values, advantages, strict=True
    ):
        weight = float(advantage) / denominator
        if category == "card_reward":
            card_family = card_family - term.selected_family_log_probability * weight
            card_conditional = (
                card_conditional
                - term.selected_conditional_log_probability * weight
            )
        else:
            other = other - term.selected_joint_log_probability * weight

    family_entropy = -FAMILY_ENTROPY_COEFFICIENT * torch.stack(
        [term.family_entropy for term in term_values]
    ).mean()
    conditional_entropy = -CONDITIONAL_ENTROPY_COEFFICIENT * torch.stack(
        [term.conditional_entropy for term in term_values]
    ).mean()
    components = OrderedDict(
        (
            ("card_reward_family_policy", card_family),
            ("card_reward_conditional_policy", card_conditional),
            ("other_policy", other),
            ("family_entropy_regularizer", family_entropy),
            ("conditional_entropy_regularizer", conditional_entropy),
        )
    )
    if tuple(components) != COMPONENT_NAMES:
        raise RuntimeBlocked("objective component identity drifted")
    full_loss = next(iter(components.values()))
    for component in tuple(components.values())[1:]:
        full_loss = full_loss + component
    if any(
        value.ndim != 0
        or not value.requires_grad
        or not torch.isfinite(value).item()
        for value in (full_loss, *components.values())
    ):
        raise RuntimeBlocked("cross-fitted objective must remain finite and connected")
    return CrossFittedObjective(
        full_loss=full_loss,
        components=MappingProxyType(dict(components)),
        advantages=torch.tensor(advantages, dtype=torch.float64, device="cpu"),
        decision_ids=decision_ids,
    )


def _validated_named_parameters(
    named_parameters: Sequence[tuple[str, torch.nn.Parameter]],
) -> tuple[tuple[str, ...], tuple[torch.nn.Parameter, ...]]:
    if isinstance(named_parameters, (str, bytes)) or not isinstance(
        named_parameters, Sequence
    ):
        raise RuntimeBlocked("named parameters must be a sequence")
    names: list[str] = []
    parameters: list[torch.nn.Parameter] = []
    for index, item in enumerate(named_parameters):
        if (
            not isinstance(item, Sequence)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            or not isinstance(item[1], torch.nn.Parameter)
        ):
            raise RuntimeBlocked(f"named parameter {index} is invalid")
        name, parameter = item
        if parameter.device.type != "cpu" or parameter.dtype != torch.float32:
            raise RuntimeBlocked("model parameters must be CPU float32")
        if not parameter.requires_grad or not torch.isfinite(parameter).all().item():
            raise RuntimeBlocked("model parameters must be finite and trainable")
        names.append(name)
        parameters.append(parameter)
    if not names or len(set(names)) != len(names):
        raise RuntimeBlocked("parameter identities must be nonempty and unique")
    return tuple(names), tuple(parameters)


def _flatten_parameter_values(
    parameters: Sequence[torch.nn.Parameter],
) -> torch.Tensor:
    return torch.cat(
        [parameter.detach().reshape(-1).to(dtype=torch.float32) for parameter in parameters]
    )


def _float32_vector_sha256(value: torch.Tensor) -> str:
    vector = value.detach().to(device="cpu", dtype=torch.float32).reshape(-1)
    if not torch.isfinite(vector).all().item():
        raise RuntimeBlocked("float32 vector must be finite")
    payload = struct.pack(f"<{vector.numel()}f", *vector.tolist())
    return hashlib.sha256(payload).hexdigest()


def encode_float_tensor(value: torch.Tensor) -> dict[str, Any]:
    """Encode one finite CPU float tensor as canonical little-endian bytes."""
    if not isinstance(value, torch.Tensor):
        raise RuntimeBlocked("binary evidence value must be a tensor")
    if value.device.type != "cpu" or value.dtype not in {
        torch.float32,
        torch.float64,
    }:
        raise RuntimeBlocked("binary evidence tensor must be CPU float32 or float64")
    tensor = value.detach().contiguous()
    if not torch.isfinite(tensor).all().item():
        raise RuntimeBlocked("binary evidence tensor must be finite")
    dtype = "float32" if tensor.dtype == torch.float32 else "float64"
    format_code = "f" if dtype == "float32" else "d"
    item_size = 4 if dtype == "float32" else 8
    byte_count = tensor.numel() * item_size
    if byte_count > MAX_BINARY_PAYLOAD_BYTES:
        raise RuntimeBlocked("binary evidence tensor exceeds the artifact bound")
    raw = struct.pack(
        f"<{tensor.numel()}{format_code}", *tensor.reshape(-1).tolist()
    )
    return {
        "byte_order": "little",
        "data_base64": base64.b64encode(raw).decode("ascii"),
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "dtype": dtype,
        "shape": list(tensor.shape),
    }


def _decode_float_tensor(
    value: Any,
    *,
    label: str,
    expected_dtype: torch.dtype,
    expected_shape: Sequence[int],
) -> torch.Tensor:
    if not isinstance(value, Mapping):
        raise RuntimeBlocked(f"{label} must be a binary payload")
    payload = dict(value)
    expected_fields = {
        "byte_order",
        "data_base64",
        "data_sha256",
        "dtype",
        "shape",
    }
    if set(payload) != expected_fields or payload.get("byte_order") != "little":
        raise RuntimeBlocked(f"{label} binary fields differ")
    dtype_name = "float32" if expected_dtype == torch.float32 else "float64"
    if payload.get("dtype") != dtype_name or payload.get("shape") != list(expected_shape):
        raise RuntimeBlocked(f"{label} dtype or shape differs")
    encoded = payload.get("data_base64")
    if not isinstance(encoded, str):
        raise RuntimeBlocked(f"{label} base64 is invalid")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise RuntimeBlocked(f"{label} base64 is invalid") from exc
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise RuntimeBlocked(f"{label} base64 is not canonical")
    digest = payload.get("data_sha256")
    if not isinstance(digest, str) or hashlib.sha256(raw).hexdigest() != digest:
        raise RuntimeBlocked(f"{label} digest differs")
    item_size = 4 if expected_dtype == torch.float32 else 8
    count = math.prod(expected_shape) if expected_shape else 1
    if len(raw) != count * item_size:
        raise RuntimeBlocked(f"{label} byte count differs")
    format_code = "f" if expected_dtype == torch.float32 else "d"
    values = [item[0] for item in struct.iter_unpack("<" + format_code, raw)]
    tensor = torch.tensor(values, dtype=expected_dtype).reshape(tuple(expected_shape))
    if not torch.isfinite(tensor).all().item():
        raise RuntimeBlocked(f"{label} must be finite")
    return tensor


def _encode_random_state(value: Any) -> Any:
    if isinstance(value, tuple):
        return {"items": [_encode_random_state(item) for item in value], "type": "tuple"}
    if value is None or isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            raise RuntimeBlocked("Python RNG state must be finite")
        return value
    raise RuntimeBlocked("Python RNG state contains an unsupported value")


def _decode_random_state(value: Any) -> Any:
    if isinstance(value, Mapping):
        source = dict(value)
        if set(source) != {"items", "type"} or source["type"] != "tuple":
            raise RuntimeBlocked("Python RNG tuple encoding is invalid")
        if not isinstance(source["items"], list):
            raise RuntimeBlocked("Python RNG tuple items are invalid")
        return tuple(_decode_random_state(item) for item in source["items"])
    if value is None or isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise RuntimeBlocked("Python RNG state encoding is invalid")


def _encode_generator_state(generator: torch.Generator) -> dict[str, Any]:
    state = generator.get_state()
    if state.device.type != "cpu" or state.dtype != torch.uint8 or state.ndim != 1:
        raise RuntimeBlocked("Torch generator state must be a CPU byte vector")
    raw = bytes(state.tolist())
    return {
        "data_base64": base64.b64encode(raw).decode("ascii"),
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "dtype": "uint8",
        "shape": [len(raw)],
    }


def _decode_generator_state(value: Any) -> torch.Tensor:
    if not isinstance(value, Mapping):
        raise RuntimeBlocked("Torch generator state must be a mapping")
    payload = dict(value)
    if set(payload) != {"data_base64", "data_sha256", "dtype", "shape"}:
        raise RuntimeBlocked("Torch generator state fields differ")
    if payload["dtype"] != "uint8" or not isinstance(payload["shape"], list) or len(payload["shape"]) != 1:
        raise RuntimeBlocked("Torch generator state shape or dtype differs")
    count = payload["shape"][0]
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise RuntimeBlocked("Torch generator state shape is invalid")
    encoded = payload["data_base64"]
    if not isinstance(encoded, str):
        raise RuntimeBlocked("Torch generator state base64 is invalid")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise RuntimeBlocked("Torch generator state base64 is invalid") from exc
    if base64.b64encode(raw).decode("ascii") != encoded or len(raw) != count:
        raise RuntimeBlocked("Torch generator state bytes differ")
    if hashlib.sha256(raw).hexdigest() != payload["data_sha256"]:
        raise RuntimeBlocked("Torch generator state digest differs")
    return torch.tensor(list(raw), dtype=torch.uint8)


def _differentiate_complete(
    loss: torch.Tensor,
    parameters: Sequence[torch.nn.Parameter],
    *,
    label: str,
) -> torch.Tensor:
    if not isinstance(loss, torch.Tensor) or loss.ndim != 0 or not loss.requires_grad:
        raise RuntimeBlocked(f"{label} must be a connected scalar")
    try:
        gradients = torch.autograd.grad(
            loss,
            tuple(parameters),
            retain_graph=True,
            allow_unused=True,
        )
    except RuntimeError as exc:
        raise RuntimeBlocked(f"{label} gradient construction failed") from exc
    if all(gradient is None for gradient in gradients):
        raise RuntimeBlocked(f"{label} must connect to a parameter")
    flattened = torch.cat(
        [
            (torch.zeros_like(parameter) if gradient is None else gradient)
            .detach()
            .reshape(-1)
            .to(dtype=torch.float64)
            for parameter, gradient in zip(parameters, gradients, strict=True)
        ]
    )
    if not torch.isfinite(flattened).all().item():
        raise RuntimeBlocked(f"{label} gradient must be finite")
    return flattened


def _vector_norm(value: torch.Tensor) -> float:
    result = float(torch.linalg.vector_norm(value.to(dtype=torch.float64)).item())
    if not math.isfinite(result):
        raise RuntimeBlocked("gradient norm must remain finite")
    return result


def build_legacy_objective_diagnostic(
    *,
    terms: Sequence[objective_contract.HierarchicalPolicyTerms],
    raw_returns: Sequence[float] | torch.Tensor,
    named_parameters: Sequence[tuple[str, torch.nn.Parameter]],
) -> LegacyObjectiveDiagnostic:
    """Call the consumed public normalization and loss builders without stepping."""
    _, parameters = _validated_named_parameters(named_parameters)
    try:
        normalized = consumed_runtime.normalize_returns(raw_returns)
        legacy_loss = consumed_runtime.build_reinforce_loss(terms, normalized)
    except (consumed_runtime.RuntimeBlocked, TypeError, ValueError) as exc:
        raise RuntimeBlocked(str(exc)) from exc
    gradient = _differentiate_complete(
        legacy_loss.loss, parameters, label="legacy objective"
    )
    norm = _vector_norm(gradient)
    clip_factor = (
        1.0
        if norm <= GRADIENT_NORM_CEILING
        else GRADIENT_NORM_CEILING / (norm + GRADIENT_CLIP_EPSILON)
    )
    return LegacyObjectiveDiagnostic(
        normalized_returns=normalized.detach().clone(),
        loss_value=float(legacy_loss.loss.detach().item()),
        gradient=gradient,
        gradient_norm=norm,
        clip_factor=clip_factor,
    )


def _consumed_torch_clip_vector(
    raw_gradient: torch.Tensor,
    parameters: Sequence[torch.nn.Parameter],
) -> torch.Tensor:
    temporary: list[torch.nn.Parameter] = []
    offset = 0
    for parameter in parameters:
        count = parameter.numel()
        clone = torch.nn.Parameter(torch.zeros_like(parameter), requires_grad=True)
        clone.grad = (
            raw_gradient[offset : offset + count]
            .reshape(parameter.shape)
            .to(dtype=torch.float32)
            .clone()
        )
        temporary.append(clone)
        offset += count
    if offset != raw_gradient.numel():
        raise RuntimeBlocked("gradient vector length differs from parameter layout")
    torch.nn.utils.clip_grad_norm_(temporary, max_norm=GRADIENT_NORM_CEILING)
    result = torch.cat([parameter.grad.detach().reshape(-1) for parameter in temporary])
    if not torch.isfinite(result).all().item():
        raise RuntimeBlocked("consumed Torch clipping result must be finite")
    return result


def _gradient_comparison(
    cross_fitted: torch.Tensor, legacy: torch.Tensor
) -> dict[str, float | None]:
    if cross_fitted.shape != legacy.shape:
        raise RuntimeBlocked("objective gradient shapes must match")
    cross_norm = _vector_norm(cross_fitted)
    legacy_norm = _vector_norm(legacy)
    difference_norm = _vector_norm(cross_fitted - legacy)
    dot = float(torch.dot(cross_fitted, legacy).item())
    cosine = None if cross_norm == 0.0 or legacy_norm == 0.0 else dot / (
        cross_norm * legacy_norm
    )
    return {
        "cosine": cosine,
        "cross_fitted_norm": cross_norm,
        "difference_norm": difference_norm,
        "dot": dot,
        "legacy_norm": legacy_norm,
    }


def build_gradient_update_evidence(
    *,
    objective: CrossFittedObjective,
    terms: Sequence[objective_contract.HierarchicalPolicyTerms],
    raw_returns: Sequence[float] | torch.Tensor,
    named_parameters: Sequence[tuple[str, torch.nn.Parameter]],
) -> GradientUpdateEvidence:
    """Build all pre-step gradient evidence without mutating model gradients."""
    if not isinstance(objective, CrossFittedObjective):
        raise RuntimeBlocked("cross-fitted objective has the wrong type")
    names, parameters = _validated_named_parameters(named_parameters)
    parameter_order = names
    try:
        ledger = build_gradient_ledger(
            full_loss=objective.full_loss,
            components=objective.components,
            named_parameters=tuple(zip(names, parameters, strict=True)),
            parameter_order=parameter_order,
        )
    except AdvantageAttributionError as exc:
        raise RuntimeBlocked(str(exc)) from exc
    installed = ledger.clipped_full_gradient.to(dtype=torch.float32)
    consumed_clipped = _consumed_torch_clip_vector(
        ledger.full_gradient, parameters
    )
    differences = torch.abs(
        installed.to(dtype=torch.float64)
        - consumed_clipped.to(dtype=torch.float64)
    )
    denominators = torch.maximum(
        torch.abs(installed.to(dtype=torch.float64)),
        torch.abs(consumed_clipped.to(dtype=torch.float64)),
    )
    relative = torch.where(
        denominators == 0.0,
        torch.zeros_like(differences),
        differences / denominators,
    )
    legacy = build_legacy_objective_diagnostic(
        terms=terms,
        raw_returns=raw_returns,
        named_parameters=tuple(zip(names, parameters, strict=True)),
    )
    return GradientUpdateEvidence(
        ledger=ledger,
        parameter_names=names,
        parameter_shapes=tuple(tuple(parameter.shape) for parameter in parameters),
        pre_parameter_sha256=_float32_vector_sha256(
            _flatten_parameter_values(parameters)
        ),
        installed_gradient=installed.detach().clone(),
        consumed_torch_clipped_gradient=consumed_clipped.detach().clone(),
        clip_comparison=MappingProxyType(
            {
                "max_abs_difference": float(torch.max(differences).item()),
                "max_relative_difference": float(torch.max(relative).item()),
            }
        ),
        legacy_normalized_returns=legacy.normalized_returns,
        legacy_gradient=legacy.gradient,
        legacy_loss_value=legacy.loss_value,
        gradient_comparison=MappingProxyType(
            _gradient_comparison(ledger.full_gradient, legacy.gradient)
        ),
    )


def _validate_exact_adam(
    optimizer: torch.optim.Optimizer,
    parameters: Sequence[torch.nn.Parameter],
) -> None:
    if not isinstance(optimizer, torch.optim.Adam) or len(optimizer.param_groups) != 1:
        raise RuntimeBlocked("optimizer must be the registered Adam")
    group = optimizer.param_groups[0]
    if [id(value) for value in group["params"]] != [id(value) for value in parameters]:
        raise RuntimeBlocked("Adam parameter order differs from the model")
    expected = {
        "lr": ADAM_LEARNING_RATE,
        "betas": ADAM_BETAS,
        "eps": ADAM_EPSILON,
        "weight_decay": ADAM_WEIGHT_DECAY,
        "amsgrad": False,
        "maximize": False,
        "foreach": None,
        "capturable": False,
        "differentiable": False,
        "fused": None,
    }
    if any(group.get(key) != value for key, value in expected.items()):
        raise RuntimeBlocked("Adam controls differ from the registered values")


def _optimizer_state_snapshot(
    optimizer: torch.optim.Optimizer,
    parameters: Sequence[torch.nn.Parameter],
) -> tuple[tuple[int, ...], tuple[torch.Tensor, ...], tuple[torch.Tensor, ...]]:
    steps: list[int] = []
    first_moments: list[torch.Tensor] = []
    second_moments: list[torch.Tensor] = []
    for parameter in parameters:
        state = optimizer.state.get(parameter, {})
        raw_step = state.get("step", 0)
        step = int(float(raw_step.item())) if isinstance(raw_step, torch.Tensor) else int(raw_step)
        exp_avg = state.get("exp_avg", torch.zeros_like(parameter)).detach().clone()
        exp_avg_sq = state.get("exp_avg_sq", torch.zeros_like(parameter)).detach().clone()
        if (
            exp_avg.shape != parameter.shape
            or exp_avg_sq.shape != parameter.shape
            or exp_avg.dtype != torch.float32
            or exp_avg_sq.dtype != torch.float32
            or not torch.isfinite(exp_avg).all().item()
            or not torch.isfinite(exp_avg_sq).all().item()
        ):
            raise RuntimeBlocked("Adam moment state is invalid")
        steps.append(step)
        first_moments.append(exp_avg)
        second_moments.append(exp_avg_sq)
    return tuple(steps), tuple(first_moments), tuple(second_moments)


def apply_validated_adam_step(
    *,
    optimizer: torch.optim.Optimizer,
    named_parameters: Sequence[tuple[str, torch.nn.Parameter]],
    evidence: GradientUpdateEvidence,
) -> AdamStepEvidence:
    """Install the ledger gradient and apply exactly one registered Adam step."""
    if not isinstance(evidence, GradientUpdateEvidence):
        raise RuntimeBlocked("gradient evidence has the wrong type")
    names, parameters = _validated_named_parameters(named_parameters)
    if names != evidence.parameter_names or tuple(
        tuple(parameter.shape) for parameter in parameters
    ) != evidence.parameter_shapes:
        raise RuntimeBlocked("gradient parameter identity drifted")
    _validate_exact_adam(optimizer, parameters)
    current_sha256 = _float32_vector_sha256(_flatten_parameter_values(parameters))
    if current_sha256 != evidence.pre_parameter_sha256:
        raise RuntimeBlocked("parameter drift detected before gradient installation")
    if evidence.installed_gradient.numel() != sum(
        parameter.numel() for parameter in parameters
    ):
        raise RuntimeBlocked("installed gradient length differs from parameters")

    pre_parameters = tuple(parameter.detach().clone() for parameter in parameters)
    pre_steps, pre_exp_avg, pre_exp_avg_sq = _optimizer_state_snapshot(
        optimizer, parameters
    )
    offset = 0
    for parameter in parameters:
        count = parameter.numel()
        gradient = (
            evidence.installed_gradient[offset : offset + count]
            .reshape(parameter.shape)
            .to(dtype=torch.float32)
            .clone()
        )
        if not torch.isfinite(gradient).all().item():
            raise RuntimeBlocked("installed gradient must be finite")
        parameter.grad = gradient
        offset += count
    installed = torch.cat(
        [parameter.grad.detach().reshape(-1) for parameter in parameters]
    )
    if not torch.equal(installed, evidence.installed_gradient):
        raise RuntimeBlocked("installed gradient differs from ledger evidence")
    optimizer.step()
    post_parameters = tuple(parameter.detach().clone() for parameter in parameters)
    post_steps, post_exp_avg, post_exp_avg_sq = _optimizer_state_snapshot(
        optimizer, parameters
    )
    if any(after != before + 1 for before, after in zip(pre_steps, post_steps, strict=True)):
        raise RuntimeBlocked("Adam step counter did not advance exactly once")
    if any(not torch.isfinite(value).all().item() for value in post_parameters):
        raise RuntimeBlocked("post-step parameters must remain finite")
    return AdamStepEvidence(
        parameter_names=names,
        installed_gradient=installed.detach().clone(),
        pre_parameters=pre_parameters,
        pre_steps=pre_steps,
        pre_exp_avg=pre_exp_avg,
        pre_exp_avg_sq=pre_exp_avg_sq,
        post_parameters=post_parameters,
        post_steps=post_steps,
        post_exp_avg=post_exp_avg,
        post_exp_avg_sq=post_exp_avg_sq,
    )


def _validate_training_runtime(runtime: CrossFittedTrainingRuntime) -> None:
    if not isinstance(runtime, CrossFittedTrainingRuntime):
        raise RuntimeBlocked("training runtime has the wrong type")
    metadata = runtime.model.architecture_metadata()
    if (
        metadata.get("candidate_input_dim") != HASH_DIM
        or metadata.get("state_input_dim") != HASH_DIM
        or metadata.get("hidden_dim") != DEFAULT_HIDDEN_DIM
        or metadata.get("device") != "cpu"
        or metadata.get("dtype") != "float32"
    ):
        raise RuntimeBlocked("ranker architecture differs from the registered model")
    names, parameters = _validated_named_parameters(
        tuple(runtime.model.named_parameters())
    )
    if not names:
        raise RuntimeBlocked("ranker parameter inventory must be nonempty")
    _validate_exact_adam(runtime.optimizer, parameters)
    counters = (
        runtime.next_chunk_index,
        runtime.completed_episodes,
        runtime.completed_decisions,
        runtime.optimizer_updates,
    )
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in counters):
        raise RuntimeBlocked("runtime counters must be nonnegative integers")
    if runtime.next_chunk_index != runtime.optimizer_updates:
        raise RuntimeBlocked("chunk and optimizer coordinates differ")
    if runtime.completed_episodes != runtime.optimizer_updates * TRAJECTORIES_PER_CHUNK:
        raise RuntimeBlocked("completed episodes differ from complete updates")
    if runtime.optimizer_updates > 8:
        raise RuntimeBlocked("optimizer update ceiling exceeded")
    if runtime.completed_decisions > 32_768:
        raise RuntimeBlocked("retained decision ceiling exceeded")


def run_cross_fitted_chunk_update(
    runtime: CrossFittedTrainingRuntime,
    *,
    chunk_index: int,
    decisions: Sequence[CrossFittedTrainingDecision],
) -> CrossFittedChunkUpdate:
    """Apply one complete 64-trajectory mechanism update without environment I/O."""
    _validate_training_runtime(runtime)
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or chunk_index != runtime.next_chunk_index
    ):
        raise RuntimeBlocked("chunk index does not match runtime coordinate")
    if runtime.optimizer_updates >= 8:
        raise RuntimeBlocked("optimizer update ceiling reached")
    if isinstance(decisions, (str, bytes)) or not isinstance(decisions, Sequence):
        raise RuntimeBlocked("chunk decisions must be a sequence")
    traces = tuple(decisions)
    if any(not isinstance(trace, CrossFittedTrainingDecision) for trace in traces):
        raise RuntimeBlocked("chunk decisions contain an invalid trace")
    trajectory_ids = {
        trace.baseline_decision.trajectory_id for trace in traces
    }
    if len(trajectory_ids) != TRAJECTORIES_PER_CHUNK:
        raise RuntimeBlocked("chunk update requires exactly 64 complete trajectories")
    trace_by_decision_id: dict[str, CrossFittedTrainingDecision] = {}
    for trace in traces:
        decision_id = trace.baseline_decision.decision_id
        if decision_id in trace_by_decision_id:
            raise RuntimeBlocked("chunk decision identities must be unique")
        if not isinstance(trace.terms, objective_contract.HierarchicalPolicyTerms):
            raise RuntimeBlocked("chunk policy terms have the wrong type")
        trace_by_decision_id[decision_id] = trace

    baseline = build_cross_fitted_baseline(
        tuple(trace.baseline_decision for trace in traces)
    )
    ordered_records = baseline.advantage_batch.records
    try:
        ordered_traces = tuple(
            trace_by_decision_id[record.decision_id] for record in ordered_records
        )
    except KeyError as exc:
        raise RuntimeBlocked("baseline and policy decision identities differ") from exc
    if len(ordered_traces) != len(traces):
        raise RuntimeBlocked("baseline and policy decision counts differ")
    next_decision_count = runtime.completed_decisions + len(ordered_traces)
    if next_decision_count > 32_768:
        raise RuntimeBlocked("retained decision ceiling would be exceeded")

    term_values = tuple(trace.terms for trace in ordered_traces)
    objective = build_cross_fitted_objective(
        terms=term_values,
        categories=tuple(
            trace.baseline_decision.category for trace in ordered_traces
        ),
        advantage_batch=baseline.advantage_batch,
    )
    named_parameters = tuple(runtime.model.named_parameters())
    gradient = build_gradient_update_evidence(
        objective=objective,
        terms=term_values,
        raw_returns=tuple(record.raw_return for record in ordered_records),
        named_parameters=named_parameters,
    )
    adam = apply_validated_adam_step(
        optimizer=runtime.optimizer,
        named_parameters=named_parameters,
        evidence=gradient,
    )
    runtime.next_chunk_index += 1
    runtime.completed_episodes += TRAJECTORIES_PER_CHUNK
    runtime.completed_decisions = next_decision_count
    runtime.optimizer_updates += 1
    return CrossFittedChunkUpdate(
        chunk_index=chunk_index,
        baseline=baseline,
        objective=objective,
        gradient=gradient,
        adam=adam,
        decisions=ordered_traces,
    )


def _detached_scalar(value: torch.Tensor, label: str) -> float:
    if not isinstance(value, torch.Tensor) or value.ndim != 0:
        raise RuntimeBlocked(f"{label} must be a scalar tensor")
    result = float(value.detach().item())
    if not math.isfinite(result):
        raise RuntimeBlocked(f"{label} must be finite")
    return result


def _canonical_diagnostic(value: Mapping[str, Any] | None) -> Any:
    if value is None:
        raise RuntimeBlocked("publishable decision diagnostic is required")
    if not isinstance(value, Mapping):
        raise RuntimeBlocked("decision diagnostic must be a mapping")
    try:
        return json.loads(_canonical_json_bytes(dict(value)).decode("ascii"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeBlocked("decision diagnostic is not canonical JSON") from exc


def build_chunk_evidence(update: CrossFittedChunkUpdate) -> dict[str, Any]:
    """Encode one completed update into bounded, independently readable evidence."""
    if not isinstance(update, CrossFittedChunkUpdate):
        raise RuntimeBlocked("chunk update evidence has the wrong type")
    records = tuple(update.baseline.advantage_batch.records)
    predictions = {value.decision_id: value for value in update.baseline.predictions}
    traces = {value.baseline_decision.decision_id: value for value in update.decisions}
    if set(predictions) != {record.decision_id for record in records} or set(traces) != set(predictions):
        raise RuntimeBlocked("chunk evidence decision identities differ")

    decision_rows: list[dict[str, Any]] = []
    for record in records:
        trace = traces[record.decision_id]
        source = trace.baseline_decision
        prediction = predictions[record.decision_id]
        terms = trace.terms
        if source.reward is None or not math.isfinite(float(source.reward)):
            raise RuntimeBlocked("publishable decision reward is required")
        diagnostic = _canonical_diagnostic(trace.diagnostic)
        required_diagnostic_fields = {
            "candidate_scores",
            "candidates",
            "category",
            "conditional_probabilities",
            "family_order",
            "family_probabilities",
            "joint_probabilities",
            "multi_family",
            "raw_score_max_action_ids",
            "raw_score_max_family_ids",
            "selected_action_id",
            "selected_family",
            "selection_mode",
        }
        if not required_diagnostic_fields.issubset(diagnostic):
            raise RuntimeBlocked("publishable decision diagnostic is incomplete")
        if (
            diagnostic["category"] != source.category
            or diagnostic["selected_action_id"] != terms.selected_action_id
            or diagnostic["selected_family"] != terms.selected_family
        ):
            raise RuntimeBlocked("publishable decision diagnostic differs from terms")
        decision_rows.append(
            {
                "advantage": record.advantage,
                "baseline_fit_trajectory_ids": list(
                    record.baseline_fit_trajectory_ids
                ),
                "baseline_prediction": record.baseline_prediction,
                "category": source.category,
                "decision_id": source.decision_id,
                "decision_index": source.decision_index,
                "diagnostic": diagnostic,
                "feature": sparse_state_feature_payload(source.state_features),
                "fold_id": record.fold_id,
                "policy_terms": {
                    "conditional_entropy": _detached_scalar(
                        terms.conditional_entropy, "conditional entropy"
                    ),
                    "family_entropy": _detached_scalar(
                        terms.family_entropy, "family entropy"
                    ),
                    "selected_action_id": terms.selected_action_id,
                    "selected_conditional_log_probability": _detached_scalar(
                        terms.selected_conditional_log_probability,
                        "selected conditional log probability",
                    ),
                    "selected_family": terms.selected_family,
                    "selected_family_log_probability": _detached_scalar(
                        terms.selected_family_log_probability,
                        "selected family log probability",
                    ),
                    "selected_joint_log_probability": _detached_scalar(
                        terms.selected_joint_log_probability,
                        "selected joint log probability",
                    ),
                },
                "prediction": {
                    "clipped": prediction.clipped,
                    "preclip_little_endian_hex": (
                        prediction.preclip_little_endian_hex
                    ),
                    "unclipped": prediction.unclipped,
                    "was_clipped": prediction.was_clipped,
                },
                "raw_return": record.raw_return,
                "reward": source.reward,
                "scale": record.scale,
                "scale_mode": record.scale_mode,
                "seed": source.seed,
                "trajectory_id": source.trajectory_id,
            }
        )

    model_rows = [
        {
            "absolute_product_sums": encode_float_tensor(
                torch.tensor(model.absolute_product_sums, dtype=torch.float64)
            ),
            "coefficients": encode_float_tensor(
                torch.tensor(model.coefficients, dtype=torch.float64)
            ),
            "fit_trajectory_ids": list(model.fit_trajectory_ids),
            "fold_id": model.fold_id,
            "held_out_trajectory_ids": list(model.held_out_trajectory_ids),
            "kkt_residuals": encode_float_tensor(
                torch.tensor(model.kkt_residuals, dtype=torch.float64)
            ),
            "rhs": encode_float_tensor(
                torch.tensor(model.rhs, dtype=torch.float64)
            ),
        }
        for model in update.baseline.models
    ]

    component_vectors = {
        name: encode_float_tensor(update.gradient.ledger.component_vectors[name])
        for name in COMPONENT_NAMES
    }
    parameter_rows: list[dict[str, Any]] = []
    offset = 0
    for index, (name, shape) in enumerate(
        zip(
            update.adam.parameter_names,
            update.gradient.parameter_shapes,
            strict=True,
        )
    ):
        count = math.prod(shape)
        installed = update.adam.installed_gradient[offset : offset + count].reshape(
            shape
        )
        parameter_rows.append(
            {
                "installed_gradient": encode_float_tensor(installed),
                "name": name,
                "post_exp_avg": encode_float_tensor(update.adam.post_exp_avg[index]),
                "post_exp_avg_sq": encode_float_tensor(
                    update.adam.post_exp_avg_sq[index]
                ),
                "post_parameter": encode_float_tensor(
                    update.adam.post_parameters[index]
                ),
                "post_step": update.adam.post_steps[index],
                "pre_exp_avg": encode_float_tensor(update.adam.pre_exp_avg[index]),
                "pre_exp_avg_sq": encode_float_tensor(
                    update.adam.pre_exp_avg_sq[index]
                ),
                "pre_parameter": encode_float_tensor(
                    update.adam.pre_parameters[index]
                ),
                "pre_step": update.adam.pre_steps[index],
                "shape": list(shape),
            }
        )
        offset += count
    if offset != update.adam.installed_gradient.numel():
        raise RuntimeBlocked("Adam evidence differs from the parameter layout")

    content = {
        "adam": {
            "betas": list(ADAM_BETAS),
            "epsilon": ADAM_EPSILON,
            "learning_rate": ADAM_LEARNING_RATE,
            "parameters": parameter_rows,
            "weight_decay": ADAM_WEIGHT_DECAY,
        },
        "baseline": {
            "fold_trajectories": {
                fold_id: list(trajectory_ids)
                for fold_id, trajectory_ids in update.baseline.fold_trajectories.items()
            },
            "models": model_rows,
        },
        "chunk_index": update.chunk_index,
        "decisions": decision_rows,
        "gradients": {
            "clip_comparison": dict(update.gradient.clip_comparison),
            "clip_factor": update.gradient.ledger.clip_factor,
            "clipped_full": encode_float_tensor(
                update.gradient.ledger.clipped_full_gradient
            ),
            "component_order": list(COMPONENT_NAMES),
            "component_vectors": component_vectors,
            "consumed_torch_clipped": encode_float_tensor(
                update.gradient.consumed_torch_clipped_gradient
            ),
            "full": encode_float_tensor(update.gradient.ledger.full_gradient),
            "gradient_comparison": dict(update.gradient.gradient_comparison),
            "installed": encode_float_tensor(update.gradient.installed_gradient),
            "legacy": encode_float_tensor(update.gradient.legacy_gradient),
            "legacy_loss_value": update.gradient.legacy_loss_value,
            "legacy_normalized_returns": encode_float_tensor(
                update.gradient.legacy_normalized_returns
            ),
            "parameter_names": list(update.gradient.parameter_names),
            "parameter_shapes": [
                list(shape) for shape in update.gradient.parameter_shapes
            ],
            "pre_parameter_sha256": update.gradient.pre_parameter_sha256,
            "scalar_components": {
                name: _detached_scalar(value, f"component {name}")
                for name, value in update.objective.components.items()
            },
            "scalar_full_loss": _detached_scalar(
                update.objective.full_loss, "full loss"
            ),
        },
        "schema_version": CHUNK_EVIDENCE_SCHEMA_VERSION,
        "torch_version": str(torch.__version__),
    }
    return {
        **content,
        "content_sha256": hashlib.sha256(_canonical_json_bytes(content)).hexdigest(),
    }


def encode_runtime_checkpoint(
    runtime: CrossFittedTrainingRuntime,
) -> dict[str, Any]:
    """Capture exact model, Adam, RNG, and complete-chunk coordinates."""
    _validate_training_runtime(runtime)
    named_parameters = tuple(runtime.model.named_parameters())
    model_rows = [
        {"name": name, "tensor": encode_float_tensor(parameter.detach())}
        for name, parameter in named_parameters
    ]
    optimizer_rows: list[dict[str, Any]] = []
    for name, parameter in named_parameters:
        state = runtime.optimizer.state.get(parameter, {})
        if not state:
            optimizer_rows.append(
                {
                    "exp_avg": None,
                    "exp_avg_sq": None,
                    "initialized": False,
                    "name": name,
                    "step": 0,
                }
            )
            continue
        if set(state) != {"step", "exp_avg", "exp_avg_sq"}:
            raise RuntimeBlocked("Adam checkpoint state fields differ")
        raw_step = state["step"]
        step = int(float(raw_step.item())) if isinstance(raw_step, torch.Tensor) else int(raw_step)
        if step <= 0:
            raise RuntimeBlocked("initialized Adam checkpoint step must be positive")
        optimizer_rows.append(
            {
                "exp_avg": encode_float_tensor(state["exp_avg"]),
                "exp_avg_sq": encode_float_tensor(state["exp_avg_sq"]),
                "initialized": True,
                "name": name,
                "step": step,
            }
        )
    body = {
        "action_generator_state": _encode_generator_state(
            runtime.action_generator
        ),
        "coordinates": {
            "completed_decisions": runtime.completed_decisions,
            "completed_episodes": runtime.completed_episodes,
            "next_chunk_index": runtime.next_chunk_index,
            "optimizer_updates": runtime.optimizer_updates,
        },
        "model": model_rows,
        "optimizer": {
            "betas": list(ADAM_BETAS),
            "epsilon": ADAM_EPSILON,
            "learning_rate": ADAM_LEARNING_RATE,
            "parameters": optimizer_rows,
            "weight_decay": ADAM_WEIGHT_DECAY,
        },
        "python_rng_state": _encode_random_state(runtime.python_rng.getstate()),
        "runtime_metadata": runtime_metadata(),
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
    }
    return {
        **body,
        "checkpoint_sha256": hashlib.sha256(_canonical_json_bytes(body)).hexdigest(),
    }


def restore_training_runtime_from_checkpoint(
    value: Mapping[str, Any],
) -> CrossFittedTrainingRuntime:
    """Restore an exact checkpoint without constructing an environment."""
    if not isinstance(value, Mapping):
        raise RuntimeBlocked("checkpoint must be a mapping")
    checkpoint = dict(value)
    expected_fields = {
        "action_generator_state",
        "checkpoint_sha256",
        "coordinates",
        "model",
        "optimizer",
        "python_rng_state",
        "runtime_metadata",
        "schema_version",
    }
    if set(checkpoint) != expected_fields:
        raise RuntimeBlocked("checkpoint fields differ")
    digest = checkpoint.pop("checkpoint_sha256")
    if (
        not isinstance(digest, str)
        or hashlib.sha256(_canonical_json_bytes(checkpoint)).hexdigest() != digest
    ):
        raise RuntimeBlocked("checkpoint digest differs")
    if checkpoint["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise RuntimeBlocked("checkpoint schema differs")
    if checkpoint["runtime_metadata"] != runtime_metadata():
        raise RuntimeBlocked("checkpoint runtime metadata differs")

    runtime = initialize_training_runtime()
    named_parameters = tuple(runtime.model.named_parameters())
    expected_names = tuple(name for name, _ in named_parameters)
    model_rows = checkpoint["model"]
    if not isinstance(model_rows, list) or tuple(
        row.get("name") if isinstance(row, Mapping) else None for row in model_rows
    ) != expected_names:
        raise RuntimeBlocked("checkpoint model parameter order differs")
    for row, (name, parameter) in zip(model_rows, named_parameters, strict=True):
        if not isinstance(row, Mapping) or set(row) != {"name", "tensor"}:
            raise RuntimeBlocked("checkpoint model row fields differ")
        restored = _decode_float_tensor(
            row["tensor"],
            label=f"checkpoint model {name}",
            expected_dtype=torch.float32,
            expected_shape=tuple(parameter.shape),
        )
        with torch.no_grad():
            parameter.copy_(restored)

    optimizer = checkpoint["optimizer"]
    if not isinstance(optimizer, Mapping) or set(optimizer) != {
        "betas",
        "epsilon",
        "learning_rate",
        "parameters",
        "weight_decay",
    }:
        raise RuntimeBlocked("checkpoint Adam fields differ")
    if {
        "betas": optimizer["betas"],
        "epsilon": optimizer["epsilon"],
        "learning_rate": optimizer["learning_rate"],
        "weight_decay": optimizer["weight_decay"],
    } != {
        "betas": list(ADAM_BETAS),
        "epsilon": ADAM_EPSILON,
        "learning_rate": ADAM_LEARNING_RATE,
        "weight_decay": ADAM_WEIGHT_DECAY,
    }:
        raise RuntimeBlocked("checkpoint Adam controls differ")
    optimizer_rows = optimizer["parameters"]
    if not isinstance(optimizer_rows, list) or tuple(
        row.get("name") if isinstance(row, Mapping) else None
        for row in optimizer_rows
    ) != expected_names:
        raise RuntimeBlocked("checkpoint Adam parameter order differs")
    for row, (name, parameter) in zip(
        optimizer_rows, named_parameters, strict=True
    ):
        if not isinstance(row, Mapping) or set(row) != {
            "exp_avg",
            "exp_avg_sq",
            "initialized",
            "name",
            "step",
        }:
            raise RuntimeBlocked("checkpoint Adam row fields differ")
        initialized = row["initialized"]
        if type(initialized) is not bool:
            raise RuntimeBlocked("checkpoint Adam initialized flag is invalid")
        step = row["step"]
        if isinstance(step, bool) or not isinstance(step, int) or step < 0:
            raise RuntimeBlocked("checkpoint Adam step is invalid")
        if not initialized:
            if step != 0 or row["exp_avg"] is not None or row["exp_avg_sq"] is not None:
                raise RuntimeBlocked("uninitialized Adam checkpoint row differs")
            continue
        if step <= 0:
            raise RuntimeBlocked("initialized Adam checkpoint step is invalid")
        runtime.optimizer.state[parameter] = {
            "step": torch.tensor(float(step), dtype=torch.float32),
            "exp_avg": _decode_float_tensor(
                row["exp_avg"],
                label=f"checkpoint Adam first moment {name}",
                expected_dtype=torch.float32,
                expected_shape=tuple(parameter.shape),
            ),
            "exp_avg_sq": _decode_float_tensor(
                row["exp_avg_sq"],
                label=f"checkpoint Adam second moment {name}",
                expected_dtype=torch.float32,
                expected_shape=tuple(parameter.shape),
            ),
        }

    coordinates = checkpoint["coordinates"]
    if not isinstance(coordinates, Mapping) or set(coordinates) != {
        "completed_decisions",
        "completed_episodes",
        "next_chunk_index",
        "optimizer_updates",
    }:
        raise RuntimeBlocked("checkpoint coordinates differ")
    for name, coordinate in coordinates.items():
        if isinstance(coordinate, bool) or not isinstance(coordinate, int) or coordinate < 0:
            raise RuntimeBlocked(f"checkpoint coordinate {name} is invalid")
        setattr(runtime, name, coordinate)
    try:
        runtime.python_rng.setstate(
            _decode_random_state(checkpoint["python_rng_state"])
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeBlocked("checkpoint Python RNG state is invalid") from exc
    try:
        runtime.action_generator.set_state(
            _decode_generator_state(checkpoint["action_generator_state"])
        )
    except RuntimeError as exc:
        raise RuntimeBlocked("checkpoint Torch generator state is invalid") from exc
    _validate_training_runtime(runtime)
    return runtime


def classify_family_saturation(
    completed_chunks: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Apply the unchanged exact trailing-four family saturation rule."""
    if isinstance(completed_chunks, (str, bytes)) or not isinstance(
        completed_chunks, Sequence
    ):
        raise RuntimeBlocked("completed chunks must be a sequence")
    chunks = tuple(completed_chunks)
    for index, chunk in enumerate(chunks):
        if not isinstance(chunk, Mapping):
            raise RuntimeBlocked("completed chunk must be a mapping")
        if chunk.get("chunk_index") != index:
            raise RuntimeBlocked("completed chunk indices must be contiguous")
        if not isinstance(chunk.get("decisions"), list):
            raise RuntimeBlocked("completed chunk decisions must be a list")
    window = chunks[-4:]
    window_indices = [int(chunk["chunk_index"]) for chunk in window]
    if len(window) < 4:
        return {
            "category": None,
            "family": None,
            "multi_family_decisions": 0,
            "stop": False,
            "window_chunk_indices": window_indices,
        }
    for category in ("card_reward", "shop"):
        rows: list[Mapping[str, Any]] = []
        for chunk in window:
            for raw_row in chunk["decisions"]:
                if not isinstance(raw_row, Mapping):
                    raise RuntimeBlocked("completed decision row must be a mapping")
                diagnostic = raw_row.get("diagnostic")
                if (
                    raw_row.get("category") == category
                    and isinstance(diagnostic, Mapping)
                    and diagnostic.get("multi_family") is True
                ):
                    rows.append(diagnostic)
        if len(rows) < 64:
            continue
        maxima = [row.get("raw_score_max_family_ids") for row in rows]
        if any(
            not isinstance(value, list)
            or len(value) != 1
            or not isinstance(value[0], str)
            or not value[0]
            for value in maxima
        ):
            continue
        families = {value[0] for value in maxima}
        if len(families) == 1:
            return {
                "category": category,
                "family": next(iter(families)),
                "multi_family_decisions": len(rows),
                "stop": True,
                "window_chunk_indices": window_indices,
            }
    return {
        "category": None,
        "family": None,
        "multi_family_decisions": 0,
        "stop": False,
        "window_chunk_indices": window_indices,
    }
