"""Run one provenance-bound, offline-only non-combat simulator RL smoke."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    NativeSimulatorEnvironment,
    TARGET_CATEGORIES,
    canonical_json_bytes,
    hash_compiled_simulator_sources,
    load_native_module,
    sha256_bytes,
    sha256_file,
    validate_provenance,
)


INPUT_SCHEMA_VERSION = "noncombat-simulator-training-smoke-input-v1"
FEATURE_VERSION = "noncombat-simulator-policy-features-v1"
ALGORITHM_VERSION = "candidate-masked-reinforce-smoke-v1"
REWARD_VERSION = "simulator-floor-progress-victory-v1"
EXECUTION_SCHEMA_VERSION = "noncombat-simulator-training-execution-v1"
MODEL_SCHEMA_VERSION = "noncombat-simulator-training-model-v1"
METRICS_SCHEMA_VERSION = "noncombat-simulator-training-metrics-v1"
TRAJECTORY_SCHEMA_VERSION = "noncombat-simulator-training-trajectories-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-simulator-training-smoke-artifact-manifest-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-simulator-training-smoke-journal-v1"

REGISTERED_TRAIN_SEEDS = tuple(range(1000, 1032))
REGISTERED_HOLDOUT_SEEDS = tuple(range(2000, 2064))
REGISTERED_SOURCE_FILES = (
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_training_smoke.py",
)
ADAPTER_SOURCE_FILES = (
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_fit.py",
    "simulator_adapters/sts_lightspeed/CMakeLists.txt",
    "simulator_adapters/sts_lightspeed/noncombat_adapter.cpp",
)
LEAKAGE_FIELDS = {
    "baseline_control",
    "baseline_history",
    "outcome",
    "provenance",
    "seed",
    "terminal",
}
CANONICAL_ARTIFACT_NAMES = (
    "metrics.json",
    "model.json",
    "report.md",
    "trajectories.json",
    "artifact_manifest.json",
)


class SmokeBlocked(RuntimeError):
    """Raised when the registered smoke must stop without adapting its contract."""


def _torch_module():
    import torch

    return torch


def _policy_model_symbols():
    from analysis_scripts.noncombat_policy_model import (
        CandidateRanker,
        FeatureConfig,
        candidate_feature_vector,
    )

    return CandidateRanker, FeatureConfig, candidate_feature_vector


def _authority() -> dict[str, bool]:
    return {
        "formal_noncombat_rl": False,
        "live_gameplay": False,
        "live_policy_loading": False,
        "live_study_launch": False,
        "ope_reinterpretation": False,
        "policy_promotion": False,
        "qualification": False,
        "simulator_training_smoke": False,
    }


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SmokeBlocked(f"{label} must be an object")
    return value


def _sequence(value: object, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SmokeBlocked(f"{label} must be an array")
    return value


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value.lower())
    )


def _is_commit(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(char in "0123456789abcdef" for char in value.lower())
    )


def _validate_binding(value: object, label: str) -> dict[str, Any]:
    binding = dict(_mapping(value, label))
    path = binding.get("path")
    if not isinstance(path, str) or not path:
        raise SmokeBlocked(f"{label}.path is required")
    pure_path = PurePosixPath(path.replace("\\", "/"))
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise SmokeBlocked(f"{label}.path must be repository-relative")
    if not _is_sha256(binding.get("sha256")):
        raise SmokeBlocked(f"{label}.sha256 is invalid")
    size = binding.get("size_bytes")
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise SmokeBlocked(f"{label}.size_bytes must be positive")
    return binding


def _require_exact(mapping: Mapping[str, Any], field: str, expected: Any, label: str) -> None:
    if mapping.get(field) != expected:
        raise SmokeBlocked(f"{label}.{field} must equal {expected!r}")


def validate_smoke_registration(value: object) -> dict[str, Any]:
    """Validate the one accepted smoke contract without filling any defaults."""
    registration = dict(_mapping(value, "registration"))
    if registration.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise SmokeBlocked("registration schema_version mismatch")

    identity = dict(_mapping(registration.get("identity"), "identity"))
    identity["adapter_fit_input"] = _validate_binding(
        identity.get("adapter_fit_input"), "identity.adapter_fit_input"
    )
    identity["adapter_fit_report"] = _validate_binding(
        identity.get("adapter_fit_report"), "identity.adapter_fit_report"
    )
    try:
        identity["adapter_provenance"] = validate_provenance(
            identity.get("adapter_provenance")
        )
    except (TypeError, ValueError) as exc:
        raise SmokeBlocked(f"identity.adapter_provenance is invalid: {exc}") from exc

    implementation = dict(
        _mapping(identity.get("implementation"), "identity.implementation")
    )
    if not _is_commit(implementation.get("commit")):
        raise SmokeBlocked("identity.implementation.commit is invalid")
    source_files = list(
        _sequence(
            implementation.get("source_files"),
            "identity.implementation.source_files",
        )
    )
    if source_files != list(REGISTERED_SOURCE_FILES):
        raise SmokeBlocked(
            "identity.implementation.source_files must equal the registered source list"
        )
    if not _is_sha256(implementation.get("source_sha256")):
        raise SmokeBlocked("identity.implementation.source_sha256 is invalid")
    implementation["source_files"] = source_files
    identity["implementation"] = implementation

    smoke = dict(_mapping(registration.get("smoke"), "smoke"))
    _require_exact(smoke, "ascension", 0, "smoke")

    cohorts = dict(_mapping(smoke.get("cohorts"), "smoke.cohorts"))
    train_seeds = list(_sequence(cohorts.get("train_seeds"), "train_seeds"))
    holdout_seeds = list(_sequence(cohorts.get("holdout_seeds"), "holdout_seeds"))
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in train_seeds):
        raise SmokeBlocked("train_seeds must contain only integers")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in holdout_seeds):
        raise SmokeBlocked("holdout_seeds must contain only integers")
    if len(train_seeds) != len(set(train_seeds)):
        raise SmokeBlocked("train_seeds must be unique")
    if len(holdout_seeds) != len(set(holdout_seeds)):
        raise SmokeBlocked("holdout_seeds must be unique")
    if set(train_seeds) & set(holdout_seeds):
        raise SmokeBlocked("train and holdout seeds must be disjoint")
    if train_seeds != list(REGISTERED_TRAIN_SEEDS):
        raise SmokeBlocked("train_seeds must equal 1000..1031")
    if holdout_seeds != list(REGISTERED_HOLDOUT_SEEDS):
        raise SmokeBlocked("holdout_seeds must equal 2000..2063")
    cohorts["train_seeds"] = train_seeds
    cohorts["holdout_seeds"] = holdout_seeds

    algorithm = dict(_mapping(smoke.get("algorithm"), "smoke.algorithm"))
    exact_algorithm = {
        "discount": 1.0,
        "feature_version": FEATURE_VERSION,
        "hash_dim": 1024,
        "learning_rate": 0.001,
        "model_seed": 0,
        "optimizer": "adam",
        "passes": 4,
        "standardize_returns": True,
        "version": ALGORITHM_VERSION,
    }
    for field, expected in exact_algorithm.items():
        _require_exact(algorithm, field, expected, "smoke.algorithm")

    reward = dict(_mapping(smoke.get("reward"), "smoke.reward"))
    exact_reward = {
        "max_floor": 57,
        "progress_divisor": 57.0,
        "victory_bonus": 1.0,
        "version": REWARD_VERSION,
    }
    for field, expected in exact_reward.items():
        _require_exact(reward, field, expected, "smoke.reward")

    limits = dict(_mapping(smoke.get("limits"), "smoke.limits"))
    exact_limits = {
        "max_decisions_per_episode": 500,
        "max_train_episodes": 128,
        "max_wall_seconds_per_execution": 600.0,
    }
    for field, expected in exact_limits.items():
        _require_exact(limits, field, expected, "smoke.limits")

    evaluation = dict(_mapping(smoke.get("evaluation"), "smoke.evaluation"))
    exact_evaluation = {
        "bootstrap_resamples": 10_000,
        "bootstrap_seed": 0,
        "confidence_level": 0.95,
        "policy": "greedy",
    }
    for field, expected in exact_evaluation.items():
        _require_exact(evaluation, field, expected, "smoke.evaluation")

    execution = dict(_mapping(smoke.get("execution"), "smoke.execution"))
    exact_execution = {
        "allow_parameter_retry": False,
        "primary_count": 1,
        "replay_count": 1,
    }
    for field, expected in exact_execution.items():
        _require_exact(execution, field, expected, "smoke.execution")

    smoke.update(
        {
            "algorithm": algorithm,
            "cohorts": cohorts,
            "evaluation": evaluation,
            "execution": execution,
            "limits": limits,
            "reward": reward,
        }
    )
    registration["identity"] = identity
    registration["smoke"] = smoke
    return copy.deepcopy(registration)


def _identity_mismatches(expected: Any, actual: Any, prefix: str = "identity") -> list[str]:
    mismatches: list[str] = []
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            return [prefix]
        for key in sorted(expected, key=str):
            child = f"{prefix}.{key}"
            if key not in actual:
                mismatches.append(child)
            else:
                mismatches.extend(_identity_mismatches(expected[key], actual[key], child))
        return mismatches
    if isinstance(expected, list):
        if not isinstance(actual, list) or expected != actual:
            mismatches.append(prefix)
        return mismatches
    if expected != actual:
        mismatches.append(prefix)
    return mismatches


def validate_bound_fit_evidence(
    fit_input: Mapping[str, Any],
    fit_report: Mapping[str, Any],
    adapter_provenance: Mapping[str, Any],
) -> None:
    """Require the bound fit artifacts to prove readiness for this identity."""
    if fit_input.get("schema_version") != "noncombat-simulator-fit-input-v1":
        raise SmokeBlocked("fit input schema mismatch")
    if fit_report.get("report_schema_version") != "noncombat-simulator-fit-report-v1":
        raise SmokeBlocked("fit report schema mismatch")
    try:
        expected = validate_provenance(adapter_provenance)
        input_provenance = validate_provenance(fit_input.get("registered_provenance"))
        report_provenance = validate_provenance(fit_report.get("provenance"))
    except (TypeError, ValueError) as exc:
        raise SmokeBlocked(f"bound fit provenance is invalid: {exc}") from exc

    input_mismatches = _identity_mismatches(expected, input_provenance, "fit input provenance")
    if input_mismatches:
        raise SmokeBlocked("fit input provenance mismatch: " + ", ".join(input_mismatches))
    report_mismatches = _identity_mismatches(
        expected, report_provenance, "fit report provenance"
    )
    if report_mismatches:
        raise SmokeBlocked(
            "fit report provenance mismatch: " + ", ".join(report_mismatches)
        )
    if fit_report.get("verdict") != "adapter_poc_ready":
        raise SmokeBlocked("fit report verdict must equal adapter_poc_ready")
    if fit_report.get("blockers") != [] or fit_report.get("provenance_mismatches") != []:
        raise SmokeBlocked("fit report contains blockers or provenance mismatches")
    checks = _mapping(fit_report.get("checks"), "fit report checks")
    if not checks or any(value is not True for value in checks.values()):
        raise SmokeBlocked("fit report checks must all pass")
    authority = _mapping(fit_report.get("authority"), "fit report authority")
    if not authority or any(value is not False for value in authority.values()):
        raise SmokeBlocked("fit report authority must remain false")


def _strip_leakage(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _strip_leakage(value[key])
            for key in sorted(value, key=str)
            if str(key) not in LEAKAGE_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [_strip_leakage(item) for item in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise SmokeBlocked(f"unsupported policy feature type: {type(value).__name__}")


def project_policy_view(
    state: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the exact simulator-only policy view, excluding leakage fields."""
    return {
        "candidate": _strip_leakage(_mapping(candidate, "candidate")),
        "state": _strip_leakage(_mapping(state, "state")),
    }


def _validate_candidates(candidates: object) -> list[dict[str, Any]]:
    rows = list(_sequence(candidates, "candidates"))
    if not rows:
        raise SmokeBlocked("candidate set must be nonempty")
    result: list[dict[str, Any]] = []
    action_ids: set[str] = set()
    for index, raw in enumerate(rows):
        candidate = dict(_mapping(raw, f"candidate[{index}]"))
        action_id = candidate.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise SmokeBlocked(f"candidate[{index}] action_id is required")
        if action_id in action_ids:
            raise SmokeBlocked(f"duplicate candidate action_id: {action_id}")
        action_ids.add(action_id)
        result.append(candidate)
    return result


def _candidate_features(
    state: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    hash_dim: int,
) -> Any:
    torch = _torch_module()
    _, FeatureConfig, candidate_feature_vector = _policy_model_symbols()
    projected = [project_policy_view(state, candidate) for candidate in candidates]
    config = FeatureConfig(version=FEATURE_VERSION, hash_dim=hash_dim)
    state_features = candidate_feature_vector(
        SimpleNamespace(state=projected[0]["state"]),
        {},
        config,
    )
    empty_state_row = SimpleNamespace(state={})
    return torch.stack(
        [
            state_features
            + candidate_feature_vector(empty_state_row, item["candidate"], config)
            for item in projected
        ]
    )


def _ensure_finite_tensor(value: Any, label: str) -> None:
    torch = _torch_module()
    if not torch.isfinite(value).all().item():
        raise SmokeBlocked(f"non-finite {label}")


def simulator_training_reward(transition: Mapping[str, Any]) -> float:
    """Compute the fixed training-only progress/victory reward."""
    source = _mapping(transition.get("source_state"), "transition.source_state")
    successor = _mapping(transition.get("successor"), "transition.successor")
    successor_state = _mapping(successor.get("state"), "transition.successor.state")
    before_floor = source.get("floor")
    after_floor = successor_state.get("floor")
    for label, value in (("source floor", before_floor), ("successor floor", after_floor)):
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(float(value)):
            raise SmokeBlocked(f"{label} must be finite")
    capped_before = min(max(float(before_floor), 0.0), 57.0)
    capped_after = min(max(float(after_floor), 0.0), 57.0)
    progress = max(0.0, capped_after - capped_before) / 57.0
    victory = (
        successor.get("terminal") is True
        and successor_state.get("outcome") == "player_victory"
    )
    return progress + (1.0 if victory else 0.0)


def _returns_to_go(rewards: Sequence[float], discount: float) -> tuple[float, ...]:
    if discount != 1.0:
        raise SmokeBlocked("discount must remain 1.0")
    result = [0.0] * len(rewards)
    running = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        reward = float(rewards[index])
        if not math.isfinite(reward):
            raise SmokeBlocked("non-finite reward")
        running = reward + discount * running
        result[index] = running
    return tuple(result)


def canonical_model_payload(model: Any) -> dict[str, Any]:
    """Serialize model tensors without zip metadata or platform timestamps."""
    state_dict: dict[str, Any] = {}
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().to(device="cpu").contiguous()
        _ensure_finite_tensor(value, f"model tensor {name}")
        state_dict[name] = {
            "dtype": str(value.dtype).removeprefix("torch."),
            "shape": list(value.shape),
            "values": [float(item).hex() for item in value.reshape(-1).tolist()],
        }
    return {
        "architecture": "candidate-ranker-linear-v1",
        "input_dim": model.scorer.in_features,
        "schema_version": MODEL_SCHEMA_VERSION,
        "state_dict": state_dict,
    }


@dataclass
class _EpisodeRollout:
    summary: dict[str, Any]
    log_probabilities: tuple[Any, ...]
    rewards: tuple[float, ...]


def _check_deadline(deadline: float, clock: Callable[[], float]) -> None:
    if clock() > deadline:
        raise SmokeBlocked("wall-time bound exceeded")


def _first_difference(before: Any, after: Any, path: str = "snapshot") -> str:
    if type(before) is not type(after):
        return f"{path} type {type(before).__name__} != {type(after).__name__}"
    if isinstance(before, Mapping):
        for key in sorted(
            set(before) | set(after),
            key=lambda value: (str(value).endswith("_sha256"), str(value)),
        ):
            child = f"{path}.{key}"
            if key not in before or key not in after:
                return f"{child} is missing on one branch"
            difference = _first_difference(before[key], after[key], child)
            if difference:
                return difference
        return ""
    if isinstance(before, list):
        if len(before) != len(after):
            return f"{path} length {len(before)} != {len(after)}"
        for index, (left, right) in enumerate(zip(before, after)):
            difference = _first_difference(left, right, f"{path}[{index}]")
            if difference:
                return difference
        return ""
    if before != after:
        return f"{path} {before!r} != {after!r}"
    return ""


def _rollout_episode(
    model: Any,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    hash_dim: int,
    training: bool,
    generator: Any | None,
    max_decisions_per_episode: int,
    deadline: float,
    clock: Callable[[], float],
) -> _EpisodeRollout:
    torch = _torch_module()
    environment = environment_factory(seed)
    categories: set[str] = set()
    action_rows: list[dict[str, Any]] = []
    rewards: list[float] = []
    log_probabilities: list[Any] = []
    decisions = 0

    while True:
        _check_deadline(deadline, clock)
        snapshot = dict(_mapping(environment.snapshot(), "environment snapshot"))
        if snapshot.get("terminal") is True:
            break
        if decisions >= max_decisions_per_episode:
            raise SmokeBlocked(
                f"seed {seed} exceeded max_decisions_per_episode={max_decisions_per_episode}"
            )
        category = snapshot.get("category")
        if category not in TARGET_CATEGORIES:
            raise SmokeBlocked(f"seed {seed} stopped outside a target category")
        categories.add(str(category))
        state = _mapping(snapshot.get("state"), "snapshot.state")
        candidates = _validate_candidates(environment.legal_actions())
        policy_views = [project_policy_view(state, candidate) for candidate in candidates]
        policy_input_sha256 = sha256_bytes(
            canonical_json_bytes(
                {
                    "candidates": [view["candidate"] for view in policy_views],
                    "state": policy_views[0]["state"],
                }
            )
        )
        original_snapshot = canonical_json_bytes(snapshot)

        branch = environment.clone()
        if canonical_json_bytes(branch.snapshot()) != original_snapshot:
            raise SmokeBlocked("clone snapshot differs before action")
        branch_candidates = _validate_candidates(branch.legal_actions())
        if canonical_json_bytes(branch_candidates) != canonical_json_bytes(candidates):
            raise SmokeBlocked("clone candidate set differs before action")

        logits = model(_candidate_features(state, candidates, hash_dim=hash_dim))
        _ensure_finite_tensor(logits, "policy logits")
        if training:
            if generator is None:
                raise SmokeBlocked("training generator is required")
            probabilities = torch.softmax(logits.detach(), dim=0)
            _ensure_finite_tensor(probabilities, "policy probabilities")
            selected_index = int(
                torch.multinomial(probabilities, 1, generator=generator).item()
            )
            log_probability = torch.log_softmax(logits, dim=0)[selected_index]
            _ensure_finite_tensor(log_probability, "selected log probability")
            log_probabilities.append(log_probability)
        else:
            selected_index = int(torch.argmax(logits.detach()).item())

        action_id = str(candidates[selected_index]["action_id"])
        try:
            transition = branch.step(action_id)
        except Exception as exc:
            raise SmokeBlocked(f"candidate rejected on fresh clone: {action_id}: {exc}") from exc
        source_after = environment.snapshot()
        if canonical_json_bytes(source_after) != original_snapshot:
            difference = _first_difference(snapshot, source_after)
            raise SmokeBlocked(
                "selected clone action mutated the source branch: " + difference
            )

        reward = simulator_training_reward(_mapping(transition, "transition"))
        rewards.append(reward)
        action_rows.append(
            {
                "action_id": action_id,
                "category": category,
                "decision": decisions,
                "policy_input_sha256": policy_input_sha256,
                "reward": reward,
            }
        )
        environment = branch
        decisions += 1

    terminal = dict(_mapping(environment.snapshot(), "terminal snapshot"))
    terminal_state = _mapping(terminal.get("state"), "terminal snapshot.state")
    outcome = terminal_state.get("outcome")
    if outcome not in {"player_loss", "player_victory"}:
        raise SmokeBlocked(f"seed {seed} did not produce a terminal outcome")
    floor = terminal_state.get("floor")
    if isinstance(floor, bool) or not isinstance(floor, Real):
        raise SmokeBlocked(f"seed {seed} terminal floor is invalid")
    return _EpisodeRollout(
        summary={
            "action_sequence_sha256": sha256_bytes(canonical_json_bytes(action_rows)),
            "categories": sorted(categories),
            "decisions": decisions,
            "outcome": outcome,
            "policy_input_sha256s": [
                row["policy_input_sha256"] for row in action_rows
            ],
            "seed": seed,
            "selected_action_ids": [row["action_id"] for row in action_rows],
            "terminal_floor": float(floor),
            "total_reward": sum(rewards),
        },
        log_probabilities=tuple(log_probabilities),
        rewards=tuple(rewards),
    )


def evaluate_greedy_policy(
    model: Any,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    hash_dim: int,
    max_decisions_per_episode: int,
    deadline: float,
    clock: Callable[[], float],
) -> dict[str, Any]:
    torch = _torch_module()
    rows: list[dict[str, Any]] = []
    categories: set[str] = set()
    model.eval()
    with torch.no_grad():
        for seed in seeds:
            rollout = _rollout_episode(
                model,
                environment_factory=environment_factory,
                seed=int(seed),
                hash_dim=hash_dim,
                training=False,
                generator=None,
                max_decisions_per_episode=max_decisions_per_episode,
                deadline=deadline,
                clock=clock,
            )
            rows.append(rollout.summary)
            categories.update(rollout.summary["categories"])
    return {
        "all_categories": sorted(categories),
        "candidate_legality": True,
        "rows": rows,
        "terminal_outcomes": all(
            row["outcome"] in {"player_loss", "player_victory"} for row in rows
        ),
    }


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def paired_bootstrap_interval(
    differences: Sequence[float],
    *,
    seed: int,
    resamples: int,
    confidence_level: float,
) -> dict[str, Any]:
    values = [float(value) for value in differences]
    if not values or any(not math.isfinite(value) for value in values):
        raise SmokeBlocked("paired differences must be finite and nonempty")
    if isinstance(resamples, bool) or not isinstance(resamples, int) or resamples <= 0:
        raise SmokeBlocked("bootstrap resamples must be positive")
    if not 0.0 < confidence_level < 1.0:
        raise SmokeBlocked("confidence_level must be between zero and one")
    generator = random.Random(seed)
    means = []
    for _ in range(resamples):
        means.append(
            sum(values[generator.randrange(len(values))] for _ in values) / len(values)
        )
    means.sort()
    tail = (1.0 - confidence_level) / 2.0
    return {
        "confidence_level": confidence_level,
        "lower": _quantile(means, tail),
        "mean": sum(values) / len(values),
        "resamples": resamples,
        "upper": _quantile(means, 1.0 - tail),
    }


def _validate_execution_bounds(
    *,
    train_seeds: Sequence[int],
    holdout_seeds: Sequence[int],
    passes: int,
    hash_dim: int,
    learning_rate: float,
    discount: float,
    max_decisions_per_episode: int,
    max_train_episodes: int,
    max_wall_seconds: float,
    bootstrap_resamples: int,
) -> None:
    if not train_seeds or not holdout_seeds:
        raise SmokeBlocked("train and holdout seeds must be nonempty")
    if len(set(train_seeds)) != len(train_seeds):
        raise SmokeBlocked("train seeds must be unique")
    if len(set(holdout_seeds)) != len(holdout_seeds):
        raise SmokeBlocked("holdout seeds must be unique")
    if set(train_seeds) & set(holdout_seeds):
        raise SmokeBlocked("train and holdout seeds must be disjoint")
    if isinstance(passes, bool) or not isinstance(passes, int) or not 1 <= passes <= 8:
        raise SmokeBlocked("passes must be between 1 and 8")
    if isinstance(hash_dim, bool) or not isinstance(hash_dim, int) or not 1 <= hash_dim <= 1024:
        raise SmokeBlocked("hash_dim must be between 1 and 1024")
    if not math.isfinite(float(learning_rate)) or float(learning_rate) <= 0.0:
        raise SmokeBlocked("learning_rate must be finite and positive")
    if discount != 1.0:
        raise SmokeBlocked("discount must remain 1.0")
    if not 1 <= max_decisions_per_episode <= 500:
        raise SmokeBlocked("max_decisions_per_episode must be between 1 and 500")
    required_episodes = len(train_seeds) * passes
    if required_episodes > max_train_episodes or max_train_episodes > 512:
        raise SmokeBlocked("max_train_episodes does not cover the registered bounded run")
    if not 0.0 < float(max_wall_seconds) <= 900.0:
        raise SmokeBlocked("max_wall_seconds must be positive and at most 900")
    if not 1 <= bootstrap_resamples <= 10_000:
        raise SmokeBlocked("bootstrap_resamples must be between 1 and 10000")


def run_policy_gradient_execution(
    *,
    environment_factory: Callable[[int], Any],
    train_seeds: Sequence[int],
    holdout_seeds: Sequence[int],
    passes: int,
    model_seed: int,
    hash_dim: int,
    learning_rate: float,
    discount: float,
    max_decisions_per_episode: int,
    max_train_episodes: int,
    max_wall_seconds: float,
    bootstrap_seed: int,
    bootstrap_resamples: int,
    confidence_level: float,
    ascension: int = 0,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Execute one closed, deterministic candidate-masked REINFORCE smoke."""
    torch = _torch_module()
    CandidateRanker, _, _ = _policy_model_symbols()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    _validate_execution_bounds(
        train_seeds=train_seeds,
        holdout_seeds=holdout_seeds,
        passes=passes,
        hash_dim=hash_dim,
        learning_rate=learning_rate,
        discount=discount,
        max_decisions_per_episode=max_decisions_per_episode,
        max_train_episodes=max_train_episodes,
        max_wall_seconds=max_wall_seconds,
        bootstrap_resamples=bootstrap_resamples,
    )
    if ascension != 0:
        raise SmokeBlocked("ascension must remain zero")
    if isinstance(model_seed, bool) or not isinstance(model_seed, int):
        raise SmokeBlocked("model_seed must be an integer")

    started = clock()
    deadline = started + float(max_wall_seconds)
    random.seed(model_seed)
    torch.manual_seed(model_seed)
    model = CandidateRanker(input_dim=hash_dim)
    if next(model.parameters()).device.type != "cpu":
        raise SmokeBlocked("smoke model must remain on CPU")
    initial_model = canonical_model_payload(model)
    initial_holdout = evaluate_greedy_policy(
        model,
        environment_factory=environment_factory,
        seeds=holdout_seeds,
        hash_dim=hash_dim,
        max_decisions_per_episode=max_decisions_per_episode,
        deadline=deadline,
        clock=clock,
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=float(learning_rate))
    action_generator = torch.Generator(device="cpu")
    action_generator.manual_seed(model_seed)
    pass_rows: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []

    for pass_index in range(passes):
        _check_deadline(deadline, clock)
        optimizer.zero_grad(set_to_none=True)
        log_probabilities: list[Any] = []
        returns: list[float] = []
        pass_episode_rows: list[dict[str, Any]] = []
        model.train()
        for seed in train_seeds:
            rollout = _rollout_episode(
                model,
                environment_factory=environment_factory,
                seed=int(seed),
                hash_dim=hash_dim,
                training=True,
                generator=action_generator,
                max_decisions_per_episode=max_decisions_per_episode,
                deadline=deadline,
                clock=clock,
            )
            episode_summary = dict(rollout.summary)
            episode_summary["pass"] = pass_index
            pass_episode_rows.append(episode_summary)
            episode_rows.append(episode_summary)
            log_probabilities.extend(rollout.log_probabilities)
            returns.extend(_returns_to_go(rollout.rewards, discount))

        if not log_probabilities or len(log_probabilities) != len(returns):
            raise SmokeBlocked("training pass produced no aligned policy decisions")
        return_tensor = torch.tensor(returns, dtype=torch.float32, device="cpu")
        _ensure_finite_tensor(return_tensor, "returns")
        standard_deviation = return_tensor.std(unbiased=False)
        if float(standard_deviation.item()) > 1e-12:
            normalized_returns = (
                return_tensor - return_tensor.mean()
            ) / (standard_deviation + 1e-8)
        else:
            normalized_returns = torch.zeros_like(return_tensor)
        stacked_log_probabilities = torch.stack(log_probabilities)
        loss = -(stacked_log_probabilities * normalized_returns.detach()).mean()
        _ensure_finite_tensor(loss, "policy loss")
        loss.backward()
        for name, parameter in model.named_parameters():
            if parameter.grad is None:
                raise SmokeBlocked(f"missing gradient for {name}")
            _ensure_finite_tensor(parameter.grad, f"gradient {name}")
        optimizer.step()
        for name, parameter in model.named_parameters():
            _ensure_finite_tensor(parameter, f"model tensor {name}")

        categories = sorted(
            {
                category
                for episode in pass_episode_rows
                for category in episode["categories"]
            }
        )
        pass_rows.append(
            {
                "categories": categories,
                "decisions": sum(row["decisions"] for row in pass_episode_rows),
                "episodes": len(pass_episode_rows),
                "loss": float(loss.item()),
                "mean_episode_return": sum(
                    row["total_reward"] for row in pass_episode_rows
                )
                / len(pass_episode_rows),
                "pass": pass_index,
            }
        )

    final_holdout = evaluate_greedy_policy(
        model,
        environment_factory=environment_factory,
        seeds=holdout_seeds,
        hash_dim=hash_dim,
        max_decisions_per_episode=max_decisions_per_episode,
        deadline=deadline,
        clock=clock,
    )
    initial_by_seed = {row["seed"]: row for row in initial_holdout["rows"]}
    final_by_seed = {row["seed"]: row for row in final_holdout["rows"]}
    paired_rows = []
    for seed in holdout_seeds:
        initial = initial_by_seed[int(seed)]
        final = final_by_seed[int(seed)]
        paired_rows.append(
            {
                "candidate_legality": bool(
                    initial_holdout["candidate_legality"]
                    and final_holdout["candidate_legality"]
                ),
                "decision_difference": final["decisions"] - initial["decisions"],
                "final_action_sequence_sha256": final["action_sequence_sha256"],
                "final_categories": final["categories"],
                "final_decisions": final["decisions"],
                "final_outcome": final["outcome"],
                "final_terminal_floor": final["terminal_floor"],
                "floor_difference": final["terminal_floor"]
                - initial["terminal_floor"],
                "initial_action_sequence_sha256": initial["action_sequence_sha256"],
                "initial_categories": initial["categories"],
                "initial_decisions": initial["decisions"],
                "initial_outcome": initial["outcome"],
                "initial_terminal_floor": initial["terminal_floor"],
                "seed": int(seed),
                "victory_difference": int(final["outcome"] == "player_victory")
                - int(initial["outcome"] == "player_victory"),
            }
        )
    floor_interval = paired_bootstrap_interval(
        [row["floor_difference"] for row in paired_rows],
        seed=bootstrap_seed,
        resamples=bootstrap_resamples,
        confidence_level=confidence_level,
    )
    all_categories = {
        category
        for row in episode_rows
        for category in row["categories"]
    }
    all_categories.update(initial_holdout["all_categories"])
    all_categories.update(final_holdout["all_categories"])
    all_terminal = all(
        row["outcome"] in {"player_loss", "player_victory"}
        for row in (
            *episode_rows,
            *initial_holdout["rows"],
            *final_holdout["rows"],
        )
    )
    return {
        "algorithm": {
            "discount": discount,
            "feature_version": FEATURE_VERSION,
            "hash_dim": hash_dim,
            "learning_rate": learning_rate,
            "model_seed": model_seed,
            "optimizer": "adam",
            "passes": passes,
            "standardize_returns": True,
            "version": ALGORITHM_VERSION,
        },
        "checks": {
            "candidate_legality": True,
            "four_category_coverage": all_categories == set(TARGET_CATEGORIES),
            "seed_disjoint": not (set(train_seeds) & set(holdout_seeds)),
            "terminal_outcomes": all_terminal,
            "within_bounds": len(episode_rows) <= max_train_episodes,
        },
        "execution_schema_version": EXECUTION_SCHEMA_VERSION,
        "holdout": {
            "final": final_holdout,
            "floor_improvement_ci": floor_interval,
            "initial": initial_holdout,
            "paired_rows": paired_rows,
        },
        "initial_model": initial_model,
        "limits": {
            "max_decisions_per_episode": max_decisions_per_episode,
            "max_train_episodes": max_train_episodes,
            "max_wall_seconds": max_wall_seconds,
        },
        "model": canonical_model_payload(model),
        "training": {"episodes": episode_rows, "passes": pass_rows},
    }


def run_registered_smoke(
    registration: Mapping[str, Any],
    *,
    actual_identity: Mapping[str, Any],
    environment_factory: Callable[[int], Any],
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Validate identity before constructing any environment, then run once."""
    validated = validate_smoke_registration(registration)
    mismatches = _identity_mismatches(validated["identity"], actual_identity)
    if mismatches:
        raise SmokeBlocked("runtime identity mismatch: " + ", ".join(mismatches))
    smoke = validated["smoke"]
    algorithm = smoke["algorithm"]
    cohorts = smoke["cohorts"]
    limits = smoke["limits"]
    evaluation = smoke["evaluation"]
    return run_policy_gradient_execution(
        environment_factory=environment_factory,
        train_seeds=cohorts["train_seeds"],
        holdout_seeds=cohorts["holdout_seeds"],
        passes=algorithm["passes"],
        model_seed=algorithm["model_seed"],
        hash_dim=algorithm["hash_dim"],
        learning_rate=algorithm["learning_rate"],
        discount=algorithm["discount"],
        max_decisions_per_episode=limits["max_decisions_per_episode"],
        max_train_episodes=limits["max_train_episodes"],
        max_wall_seconds=limits["max_wall_seconds_per_execution"],
        bootstrap_seed=evaluation["bootstrap_seed"],
        bootstrap_resamples=evaluation["bootstrap_resamples"],
        confidence_level=evaluation["confidence_level"],
        ascension=smoke["ascension"],
        clock=clock,
    )


def classify_smoke_results(
    primary: Mapping[str, Any], replay: Mapping[str, Any]
) -> dict[str, Any]:
    checks = dict(_mapping(primary.get("checks"), "primary.checks"))
    blockers = [name for name, value in sorted(checks.items()) if value is not True]
    replay_identity = canonical_json_bytes(primary) == canonical_json_bytes(replay)
    replay_difference = "" if replay_identity else _first_difference(
        primary, replay, "execution"
    )
    if not replay_identity:
        blockers.append("replay_identity")
    quality = "not_evaluated"
    if blockers:
        verdict = "blocked"
    else:
        interval = _mapping(
            _mapping(primary.get("holdout"), "primary.holdout").get(
                "floor_improvement_ci"
            ),
            "primary.holdout.floor_improvement_ci",
        )
        lower = interval.get("lower")
        if isinstance(lower, bool) or not isinstance(lower, Real):
            raise SmokeBlocked("holdout confidence interval lower bound is invalid")
        if float(lower) > 0.0:
            quality = "holdout_signal"
            verdict = "pipeline_demonstrated_with_holdout_signal"
        else:
            quality = "quality_not_demonstrated"
            verdict = "pipeline_demonstrated_quality_not_demonstrated"
    return {
        "authority": _authority(),
        "blockers": blockers,
        "checks": {**checks, "replay_identity": replay_identity},
        "quality": quality,
        "replay_difference": replay_difference,
        "verdict": verdict,
    }


def _render_report(metrics: Mapping[str, Any]) -> str:
    classification = metrics["classification"]
    interval = metrics["holdout"]["floor_improvement_ci"]
    lines = [
        "# Bounded Non-Combat Simulator Training Smoke",
        "",
        f"- Verdict: `{classification['verdict']}`",
        f"- Quality: `{classification['quality']}`",
        f"- Registration SHA-256: `{metrics['registration_sha256']}`",
        "- Candidate legality: `true`",
        f"- Paired holdout seeds: {metrics['holdout']['paired_seed_count']}",
        f"- Mean terminal-floor difference: {interval['mean']:.6f}",
        (
            "- 95% paired-bootstrap interval: "
            f"[{interval['lower']:.6f}, {interval['upper']:.6f}]"
        ),
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- {name}: `{str(value).lower()}`"
        for name, value in sorted(classification["checks"].items())
    )
    lines.extend(["", "## Blockers", ""])
    if classification["blockers"]:
        lines.extend(f"- {blocker}" for blocker in classification["blockers"])
    else:
        lines.append("- None")
    lines.extend(["", "## Authority", ""])
    lines.extend(
        f"- {name}: `{str(value).lower()}`"
        for name, value in sorted(classification["authority"].items())
    )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Rewards and outcomes are simulator-only evidence.",
            "- Combat and unsupported non-combat screens use the declared baseline.",
            "- This smoke does not authorize formal RL, live loading, OPE, qualification, gameplay, or promotion.",
            "- No hyperparameter, reward, seed, or cohort retry is permitted under this change.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_canonical_artifacts(
    *,
    registration: Mapping[str, Any],
    primary: Mapping[str, Any],
    replay: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, bytes]:
    validated_registration = validate_smoke_registration(registration)
    registration_sha256 = sha256_bytes(canonical_json_bytes(validated_registration))
    trajectories = {
        "holdout": primary["holdout"],
        "registration_sha256": registration_sha256,
        "replay_execution_sha256": sha256_bytes(canonical_json_bytes(replay)),
        "schema_version": TRAJECTORY_SCHEMA_VERSION,
        "training": primary["training"],
    }
    model = dict(primary["model"])
    model["registration_sha256"] = registration_sha256
    metrics = {
        "algorithm": primary["algorithm"],
        "authority": classification["authority"],
        "checks": primary["checks"],
        "classification": dict(classification),
        "holdout": {
            "floor_improvement_ci": primary["holdout"]["floor_improvement_ci"],
            "paired_seed_count": len(primary["holdout"]["paired_rows"]),
        },
        "registration_sha256": registration_sha256,
        "schema_version": METRICS_SCHEMA_VERSION,
    }
    payloads = {
        "metrics.json": canonical_json_bytes(metrics),
        "model.json": canonical_json_bytes(model),
        "report.md": _render_report(metrics).encode("utf-8"),
        "trajectories.json": canonical_json_bytes(trajectories),
    }
    manifest = {
        "artifact_hashes": {
            name: sha256_bytes(payload) for name, payload in sorted(payloads.items())
        },
        "authority": classification["authority"],
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": classification["verdict"],
    }
    payloads["artifact_manifest.json"] = canonical_json_bytes(manifest)
    return payloads


def _validate_artifact_payloads(artifacts: Mapping[str, bytes]) -> dict[str, Any]:
    if set(artifacts) != set(CANONICAL_ARTIFACT_NAMES):
        raise SmokeBlocked("canonical artifact set is incomplete")
    for name, payload in artifacts.items():
        if not isinstance(payload, bytes):
            raise SmokeBlocked(f"artifact {name} must be bytes")
    try:
        manifest = json.loads(artifacts["artifact_manifest.json"])
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SmokeBlocked(f"artifact manifest is invalid: {exc}") from exc
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise SmokeBlocked("artifact manifest schema mismatch")
    expected_hashes = {
        name: sha256_bytes(artifacts[name])
        for name in sorted(artifacts)
        if name != "artifact_manifest.json"
    }
    if manifest.get("artifact_hashes") != expected_hashes:
        raise SmokeBlocked("artifact manifest hash closure mismatch")
    if any(value is not False for value in manifest.get("authority", {}).values()):
        raise SmokeBlocked("artifact manifest authority must remain false")
    return manifest


def publish_canonical_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
) -> None:
    """Atomically replace the complete canonical set and restore it on failure."""
    _validate_artifact_payloads(artifacts)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise SmokeBlocked("output_dir must be a directory")
    order = sorted(name for name in artifacts if name != "artifact_manifest.json")
    order.append("artifact_manifest.json")
    destinations = {name: root / name for name in order}
    previous = {
        name: path.read_bytes() if path.is_file() else None
        for name, path in destinations.items()
    }
    temporary = {name: path.with_name(f".{path.name}.tmp") for name, path in destinations.items()}
    installed: list[str] = []
    try:
        for name in order:
            temporary[name].write_bytes(artifacts[name])
        for name in order:
            replace(temporary[name], destinations[name])
            installed.append(name)
    except Exception:
        for name in installed:
            destination = destinations[name]
            prior = previous[name]
            if prior is None:
                destination.unlink(missing_ok=True)
            else:
                restore = destination.with_name(f".{destination.name}.restore")
                restore.write_bytes(prior)
                os.replace(restore, destination)
        raise
    finally:
        for path in temporary.values():
            path.unlink(missing_ok=True)
        for path in destinations.values():
            path.with_name(f".{path.name}.restore").unlink(missing_ok=True)
    validate_artifact_directory(root)


def validate_artifact_directory(output_dir: Path | str) -> dict[str, Any]:
    root = Path(output_dir)
    manifest_path = root / "artifact_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SmokeBlocked(f"cannot load published artifact manifest: {exc}") from exc
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise SmokeBlocked("published artifact manifest schema mismatch")
    expected_hashes = manifest.get("artifact_hashes")
    if not isinstance(expected_hashes, dict):
        raise SmokeBlocked("published artifact hashes are missing")
    actual_hashes = {}
    for name in sorted(expected_hashes):
        path = root / name
        if not path.is_file():
            raise SmokeBlocked(f"published artifact is missing: {name}")
        actual_hashes[name] = sha256_file(path)
    if actual_hashes != expected_hashes:
        raise SmokeBlocked("published artifact hash closure mismatch")
    if any(value is not False for value in manifest.get("authority", {}).values()):
        raise SmokeBlocked("published authority must remain false")
    return manifest


def build_execution_journal(
    *,
    primary_elapsed_seconds: float,
    replay_elapsed_seconds: float,
    wall_time_budget_seconds: float,
) -> dict[str, Any]:
    for label, value in (
        ("primary_elapsed_seconds", primary_elapsed_seconds),
        ("replay_elapsed_seconds", replay_elapsed_seconds),
        ("wall_time_budget_seconds", wall_time_budget_seconds),
    ):
        if not isinstance(value, Real) or not math.isfinite(float(value)) or value < 0:
            raise SmokeBlocked(f"{label} must be finite and non-negative")
    return {
        "canonical": False,
        "primary_elapsed_seconds": float(primary_elapsed_seconds),
        "replay_elapsed_seconds": float(replay_elapsed_seconds),
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "wall_time_budget_seconds": float(wall_time_budget_seconds),
    }


def build_blocked_execution_journal(
    *,
    blocker: str,
    elapsed_seconds: float,
    phase: str,
    wall_time_budget_seconds: float,
) -> dict[str, Any]:
    if not isinstance(blocker, str) or not blocker:
        raise SmokeBlocked("blocked journal requires a blocker")
    if not isinstance(phase, str) or not phase:
        raise SmokeBlocked("blocked journal requires a phase")
    for label, value in (
        ("elapsed_seconds", elapsed_seconds),
        ("wall_time_budget_seconds", wall_time_budget_seconds),
    ):
        if not isinstance(value, Real) or not math.isfinite(float(value)) or value < 0:
            raise SmokeBlocked(f"{label} must be finite and non-negative")
    return {
        "blocker": blocker,
        "canonical": False,
        "elapsed_seconds": float(elapsed_seconds),
        "phase": phase,
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "verdict": "blocked",
        "wall_time_budget_seconds": float(wall_time_budget_seconds),
    }


def _publish_execution_journal(output_dir: Path | str, journal: Mapping[str, Any]) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / "execution_journal.json"
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_bytes(canonical_json_bytes(journal))
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SmokeBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_smoke_registration(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except SmokeBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SmokeBlocked(f"cannot load smoke input {path}: {exc}") from exc
    return validate_smoke_registration(value)


def hash_bound_files(repo_root: Path | str, source_files: Sequence[str]) -> str:
    root = Path(repo_root).resolve()
    digest = hashlib.sha256()
    for relative in source_files:
        path = (root / Path(relative)).resolve()
        try:
            canonical_relative = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise SmokeBlocked(f"bound source escapes repository: {relative}") from exc
        if not path.is_file():
            raise SmokeBlocked(f"bound source is missing: {relative}")
        relative_bytes = canonical_relative.encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative_bytes).to_bytes(4, "big"))
        digest.update(relative_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SmokeBlocked(f"git {' '.join(args)} failed in {repo}: {exc}") from exc
    return completed.stdout.strip()


def _verify_sources_at_commit(
    repo_root: Path, commit: str, source_files: Sequence[str]
) -> None:
    for relative in source_files:
        try:
            completed = subprocess.run(
                ["git", "show", f"{commit}:{relative}"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise SmokeBlocked(f"cannot bind {relative} at commit {commit}: {exc}") from exc
        if completed.stdout != (repo_root / relative).read_bytes():
            raise SmokeBlocked(f"bound source differs from commit {commit}: {relative}")


def _actual_binding(repo_root: Path, binding: Mapping[str, Any]) -> dict[str, Any]:
    path = (repo_root / str(binding["path"])).resolve()
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise SmokeBlocked(f"bound artifact escapes repository: {binding['path']}") from exc
    if not path.is_file():
        raise SmokeBlocked(f"bound artifact is missing: {binding['path']}")
    return {
        "path": str(binding["path"]),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _load_bound_json(
    repo_root: Path, binding: Mapping[str, Any], label: str
) -> Mapping[str, Any]:
    path = (repo_root / str(binding["path"])).resolve()
    try:
        path.relative_to(repo_root)
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except SmokeBlocked:
        raise
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SmokeBlocked(f"cannot load {label}: {exc}") from exc
    return _mapping(value, label)


def collect_actual_identity(
    registration: Mapping[str, Any],
    *,
    repo_root: Path | str,
    simulator_repo: Path | str,
    module_path: Path | str,
    native_module: Any,
) -> dict[str, Any]:
    """Collect physical identities while preserving historical adapter commit binding."""
    validated = validate_smoke_registration(registration)
    identity = validated["identity"]
    root = Path(repo_root).resolve()
    simulator = Path(simulator_repo).resolve()
    module_file = Path(module_path).resolve()

    adapter_commit = identity["adapter_provenance"]["adapter_commit"]
    fit_input = _load_bound_json(root, identity["adapter_fit_input"], "adapter fit input")
    fit_report = _load_bound_json(
        root, identity["adapter_fit_report"], "adapter fit report"
    )
    validate_bound_fit_evidence(
        fit_input, fit_report, identity["adapter_provenance"]
    )
    _verify_sources_at_commit(root, adapter_commit, ADAPTER_SOURCE_FILES)
    implementation = identity["implementation"]
    _verify_sources_at_commit(root, implementation["commit"], implementation["source_files"])

    simulator_source_sha256, simulator_source_file_count = hash_compiled_simulator_sources(
        simulator
    )
    build = json.loads(native_module.build_info_json())
    build["python"] = sys.version.split()[0]
    provenance = validate_provenance(
        {
            "adapter_commit": adapter_commit,
            "adapter_source_sha256": hash_bound_files(root, ADAPTER_SOURCE_FILES),
            "build": build,
            "module_sha256": sha256_file(module_file),
            "module_size_bytes": module_file.stat().st_size,
            "simulator_commit": _git(simulator, "rev-parse", "HEAD"),
            "simulator_dirty": bool(_git(simulator, "status", "--porcelain=v1")),
            "simulator_source_file_count": simulator_source_file_count,
            "simulator_source_sha256": simulator_source_sha256,
            "submodules": {
                "json": _git(simulator / "json", "rev-parse", "HEAD"),
                "pybind11": _git(simulator / "pybind11", "rev-parse", "HEAD"),
            },
        }
    )
    return {
        "adapter_fit_input": _actual_binding(root, identity["adapter_fit_input"]),
        "adapter_fit_report": _actual_binding(root, identity["adapter_fit_report"]),
        "adapter_provenance": provenance,
        "implementation": {
            "commit": implementation["commit"],
            "source_files": list(implementation["source_files"]),
            "source_sha256": hash_bound_files(root, implementation["source_files"]),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--simulator-repo", type=Path, required=True)
    parser.add_argument("--module", type=Path, required=True)
    parser.add_argument("--dll-directory", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    phase = "registration"
    phase_started = time.perf_counter()
    wall_time_budget = 600.0
    try:
        registration = load_smoke_registration(args.input)
        wall_time_budget = registration["smoke"]["limits"][
            "max_wall_seconds_per_execution"
        ]
        phase = "native_and_identity"
        phase_started = time.perf_counter()
        module = load_native_module(args.module, dll_directories=args.dll_directory)
        actual_identity = collect_actual_identity(
            registration,
            repo_root=repo_root,
            simulator_repo=args.simulator_repo,
            module_path=args.module,
            native_module=module,
        )
        provenance = actual_identity["adapter_provenance"]
        ascension = registration["smoke"]["ascension"]

        def environment_factory(seed: int) -> NativeSimulatorEnvironment:
            return NativeSimulatorEnvironment(
                module.Environment(seed, ascension),
                provenance,
            )

        phase = "primary"
        started = phase_started = time.perf_counter()
        primary = run_registered_smoke(
            registration,
            actual_identity=actual_identity,
            environment_factory=environment_factory,
        )
        primary_elapsed = time.perf_counter() - started
        phase = "replay"
        replay_started = phase_started = time.perf_counter()
        replay = run_registered_smoke(
            registration,
            actual_identity=actual_identity,
            environment_factory=environment_factory,
        )
        replay_elapsed = time.perf_counter() - replay_started
        phase = "classification_and_publication"
        phase_started = time.perf_counter()
        classification = classify_smoke_results(primary, replay)
        artifacts = build_canonical_artifacts(
            registration=registration,
            primary=primary,
            replay=replay,
            classification=classification,
        )
        publish_canonical_artifacts(args.output_dir, artifacts)
        journal = build_execution_journal(
            primary_elapsed_seconds=primary_elapsed,
            replay_elapsed_seconds=replay_elapsed,
            wall_time_budget_seconds=registration["smoke"]["limits"][
                "max_wall_seconds_per_execution"
            ],
        )
        _publish_execution_journal(args.output_dir, journal)
        validate_artifact_directory(args.output_dir)
    except SmokeBlocked as exc:
        try:
            journal = build_blocked_execution_journal(
                blocker=str(exc),
                elapsed_seconds=time.perf_counter() - phase_started,
                phase=phase,
                wall_time_budget_seconds=wall_time_budget,
            )
            _publish_execution_journal(args.output_dir, journal)
        except (OSError, SmokeBlocked):
            pass
        print(json.dumps({"blocker": str(exc), "verdict": "blocked"}, sort_keys=True))
        return 2

    print(
        json.dumps(
            {
                "blockers": classification["blockers"],
                "output_dir": str(args.output_dir),
                "quality": classification["quality"],
                "verdict": classification["verdict"],
            },
            sort_keys=True,
        )
    )
    return 0 if classification["verdict"] != "blocked" else 2


if __name__ == "__main__":
    raise SystemExit(main())
