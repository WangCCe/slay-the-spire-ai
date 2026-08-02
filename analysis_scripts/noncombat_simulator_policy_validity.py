"""Evaluate one frozen non-combat simulator policy against fixed baselines."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from numbers import Real
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    NATIVE_TARGET_POLICY_ID,
    NativeSimulatorEnvironment,
    SimulatorAdapterError,
    TARGET_CATEGORIES,
    canonical_json_bytes,
    hash_compiled_simulator_sources,
    load_native_module,
    sha256_bytes,
    sha256_file,
    validate_provenance,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    ADAPTER_SOURCE_FILES,
    FEATURE_VERSION,
    SmokeBlocked,
    _actual_binding,
    _check_deadline,
    _first_difference,
    _git,
    _identity_mismatches,
    _load_bound_json,
    _mapping,
    _validate_binding,
    _verify_sources_at_commit,
    canonical_model_payload,
    evaluate_greedy_policy,
    hash_bound_files,
    paired_bootstrap_interval,
    simulator_training_reward,
    validate_artifact_directory as validate_smoke_artifact_directory,
    validate_bound_fit_evidence,
    validate_smoke_registration,
)


INPUT_SCHEMA_VERSION = "noncombat-simulator-policy-validity-input-v1"
EXECUTION_SCHEMA_VERSION = "noncombat-simulator-policy-validity-execution-v1"
TRAJECTORY_SCHEMA_VERSION = "noncombat-simulator-policy-validity-trajectories-v1"
METRICS_SCHEMA_VERSION = "noncombat-simulator-policy-validity-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-simulator-policy-validity-manifest-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-simulator-policy-validity-journal-v1"

POLICY_IDS = (
    "smoke_trained",
    "seeded_initial",
    "native_simple_agent",
)
COMPATIBILITY_SEEDS = tuple(range(2000, 2004))
FRESH_SEEDS = tuple(range(3000, 3064))
FIT_SEEDS = tuple(range(20))
SMOKE_TRAIN_SEEDS = tuple(range(1000, 1032))
SMOKE_HOLDOUT_SEEDS = tuple(range(2000, 2064))
REGISTERED_SOURCE_FILES = (
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_fit.py",
    "analysis_scripts/noncombat_simulator_policy_validity.py",
    "analysis_scripts/noncombat_simulator_training_smoke.py",
)
CANONICAL_ARTIFACT_NAMES = (
    "metrics.json",
    "report.md",
    "trajectories.json",
    "artifact_manifest.json",
)


class PolicyValidityBlocked(RuntimeError):
    """Raised when the frozen study must stop without adapting its contract."""


def _torch_module():
    import torch

    return torch


def _authority() -> dict[str, bool]:
    return {
        "formal_noncombat_rl": False,
        "live_gameplay": False,
        "live_policy_loading": False,
        "live_study_launch": False,
        "ope_reinterpretation": False,
        "policy_promotion": False,
        "qualification": False,
        "simulator_policy_validity": False,
        "simulator_training": False,
    }


def _require_exact(
    mapping: Mapping[str, Any], field: str, expected: Any, label: str
) -> None:
    if mapping.get(field) != expected:
        raise PolicyValidityBlocked(f"{label}.{field} must equal {expected!r}")


def _validated_binding(value: object, label: str) -> dict[str, Any]:
    try:
        return _validate_binding(value, label)
    except SmokeBlocked as exc:
        raise PolicyValidityBlocked(str(exc)) from exc


def _validate_seed_array(
    value: object,
    *,
    expected: Sequence[int],
    label: str,
) -> list[int]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise PolicyValidityBlocked(f"{label} must be an array")
    seeds = list(value)
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise PolicyValidityBlocked(f"{label} must contain only integers")
    if len(seeds) != len(set(seeds)):
        raise PolicyValidityBlocked(f"{label} must be unique")
    if seeds != list(expected):
        raise PolicyValidityBlocked(
            f"{label} must equal {expected[0]}..{expected[-1]}"
        )
    return seeds


def validate_policy_validity_registration(value: object) -> dict[str, Any]:
    """Validate the immutable study registration without filling defaults."""
    if not isinstance(value, Mapping):
        raise PolicyValidityBlocked("registration must be an object")
    registration = copy.deepcopy(dict(value))
    if registration.get("schema_version") != INPUT_SCHEMA_VERSION:
        raise PolicyValidityBlocked("registration schema_version mismatch")

    identity_value = registration.get("identity")
    if not isinstance(identity_value, Mapping):
        raise PolicyValidityBlocked("identity must be an object")
    identity = dict(identity_value)
    identity["adapter_fit_input"] = _validated_binding(
        identity.get("adapter_fit_input"), "identity.adapter_fit_input"
    )
    identity["adapter_fit_report"] = _validated_binding(
        identity.get("adapter_fit_report"), "identity.adapter_fit_report"
    )
    try:
        identity["adapter_provenance"] = validate_provenance(
            identity.get("adapter_provenance")
        )
    except (TypeError, ValueError) as exc:
        raise PolicyValidityBlocked(f"identity.adapter_provenance is invalid: {exc}") from exc
    build = identity["adapter_provenance"]["build"]
    if build.get("native_target_policy_id") != NATIVE_TARGET_POLICY_ID:
        raise PolicyValidityBlocked(
            "identity.adapter_provenance.build.native_target_policy_id mismatch"
        )

    smoke_artifacts_value = identity.get("smoke_artifacts")
    if not isinstance(smoke_artifacts_value, Mapping):
        raise PolicyValidityBlocked("identity.smoke_artifacts must be an object")
    smoke_artifacts = dict(smoke_artifacts_value)
    if set(smoke_artifacts) != {"manifest", "model", "registration", "trajectories"}:
        raise PolicyValidityBlocked("identity.smoke_artifacts keys mismatch")
    for name in sorted(smoke_artifacts):
        smoke_artifacts[name] = _validated_binding(
            smoke_artifacts[name], f"identity.smoke_artifacts.{name}"
        )
    identity["smoke_artifacts"] = smoke_artifacts

    implementation_value = identity.get("implementation")
    if not isinstance(implementation_value, Mapping):
        raise PolicyValidityBlocked("identity.implementation must be an object")
    implementation = dict(implementation_value)
    commit = implementation.get("commit")
    if (
        not isinstance(commit, str)
        or len(commit) != 40
        or any(char not in "0123456789abcdef" for char in commit.lower())
    ):
        raise PolicyValidityBlocked("identity.implementation.commit is invalid")
    source_files = implementation.get("source_files")
    if source_files != list(REGISTERED_SOURCE_FILES):
        raise PolicyValidityBlocked(
            "identity.implementation.source_files must equal the registered source list"
        )
    source_sha256 = implementation.get("source_sha256")
    if (
        not isinstance(source_sha256, str)
        or len(source_sha256) != 64
        or any(char not in "0123456789abcdef" for char in source_sha256.lower())
    ):
        raise PolicyValidityBlocked("identity.implementation.source_sha256 is invalid")
    identity["implementation"] = implementation

    runtime_value = identity.get("runtime")
    if not isinstance(runtime_value, Mapping):
        raise PolicyValidityBlocked("identity.runtime must be an object")
    runtime = dict(runtime_value)
    if set(runtime) != {"python", "torch"}:
        raise PolicyValidityBlocked("identity.runtime keys mismatch")
    for field in ("python", "torch"):
        if not isinstance(runtime.get(field), str) or not runtime[field]:
            raise PolicyValidityBlocked(f"identity.runtime.{field} is required")
    identity["runtime"] = runtime

    excluded_value = identity.get("excluded_baselines")
    if not isinstance(excluded_value, Mapping):
        raise PolicyValidityBlocked("identity.excluded_baselines must be an object")
    excluded = dict(excluded_value)
    if set(excluded) != {"bottled", "current"}:
        raise PolicyValidityBlocked("identity.excluded_baselines keys mismatch")
    for name in ("bottled", "current"):
        entry_value = excluded[name]
        if not isinstance(entry_value, Mapping):
            raise PolicyValidityBlocked(
                f"identity.excluded_baselines.{name} must be an object"
            )
        entry = dict(entry_value)
        _require_exact(
            entry,
            "feature_version",
            "noncombat-policy-features-v1",
            f"identity.excluded_baselines.{name}",
        )
        _require_exact(
            entry,
            "reason",
            "unvalidated_simulator_feature_action_bridge",
            f"identity.excluded_baselines.{name}",
        )
        entry["model"] = _validated_binding(
            entry.get("model"), f"identity.excluded_baselines.{name}.model"
        )
        excluded[name] = entry
    identity["excluded_baselines"] = excluded

    study_value = registration.get("study")
    if not isinstance(study_value, Mapping):
        raise PolicyValidityBlocked("study must be an object")
    study = dict(study_value)
    _require_exact(study, "ascension", 0, "study")
    _require_exact(study, "policies", list(POLICY_IDS), "study")

    cohorts_value = study.get("cohorts")
    if not isinstance(cohorts_value, Mapping):
        raise PolicyValidityBlocked("study.cohorts must be an object")
    cohorts = dict(cohorts_value)
    cohorts["fit_seeds"] = _validate_seed_array(
        cohorts.get("fit_seeds"), expected=FIT_SEEDS, label="study.cohorts.fit_seeds"
    )
    cohorts["smoke_train_seeds"] = _validate_seed_array(
        cohorts.get("smoke_train_seeds"),
        expected=SMOKE_TRAIN_SEEDS,
        label="study.cohorts.smoke_train_seeds",
    )
    cohorts["smoke_holdout_seeds"] = _validate_seed_array(
        cohorts.get("smoke_holdout_seeds"),
        expected=SMOKE_HOLDOUT_SEEDS,
        label="study.cohorts.smoke_holdout_seeds",
    )
    cohorts["compatibility_seeds"] = _validate_seed_array(
        cohorts.get("compatibility_seeds"),
        expected=COMPATIBILITY_SEEDS,
        label="study.cohorts.compatibility_seeds",
    )
    cohorts["fresh_seeds"] = _validate_seed_array(
        cohorts.get("fresh_seeds"),
        expected=FRESH_SEEDS,
        label="study.cohorts.fresh_seeds",
    )
    prior = set(FIT_SEEDS) | set(SMOKE_TRAIN_SEEDS) | set(SMOKE_HOLDOUT_SEEDS)
    if set(FRESH_SEEDS) & prior:
        raise PolicyValidityBlocked("study.cohorts.fresh_seeds overlap prior cohorts")
    if not set(COMPATIBILITY_SEEDS).issubset(SMOKE_HOLDOUT_SEEDS):
        raise PolicyValidityBlocked("compatibility seeds must be smoke holdout seeds")
    study["cohorts"] = cohorts

    model_value = study.get("model")
    if not isinstance(model_value, Mapping):
        raise PolicyValidityBlocked("study.model must be an object")
    model = dict(model_value)
    expected_model = {
        "architecture": "candidate-ranker-linear-v1",
        "feature_version": FEATURE_VERSION,
        "hash_dim": 1024,
        "model_seed": 0,
    }
    for field, expected in expected_model.items():
        _require_exact(model, field, expected, "study.model")
    study["model"] = model

    evaluation_value = study.get("evaluation")
    if not isinstance(evaluation_value, Mapping):
        raise PolicyValidityBlocked("study.evaluation must be an object")
    evaluation = dict(evaluation_value)
    expected_evaluation = {
        "bootstrap_resamples": 10_000,
        "bootstrap_seed": 0,
        "confidence_level": 0.95,
        "primary_comparison": "trained_minus_native_simple_agent",
        "secondary_comparison": "trained_minus_seeded_initial",
    }
    for field, expected in expected_evaluation.items():
        _require_exact(evaluation, field, expected, "study.evaluation")
    study["evaluation"] = evaluation

    limits_value = study.get("limits")
    if not isinstance(limits_value, Mapping):
        raise PolicyValidityBlocked("study.limits must be an object")
    limits = dict(limits_value)
    expected_limits = {
        "max_decisions_per_episode": 500,
        "max_episodes_per_execution": 192,
        "max_wall_seconds_per_execution": 480.0,
    }
    for field, expected in expected_limits.items():
        _require_exact(limits, field, expected, "study.limits")
    study["limits"] = limits

    execution_value = study.get("execution")
    if not isinstance(execution_value, Mapping):
        raise PolicyValidityBlocked("study.execution must be an object")
    execution = dict(execution_value)
    expected_execution = {
        "allow_alternate_cohort": False,
        "allow_model_update": False,
        "allow_parameter_retry": False,
        "primary_count": 1,
        "replay_count": 1,
    }
    for field, expected in expected_execution.items():
        _require_exact(execution, field, expected, "study.execution")
    study["execution"] = execution

    registration["identity"] = identity
    registration["study"] = study
    return registration


def build_initial_model(*, hash_dim: int, model_seed: int):
    if model_seed != 0:
        raise PolicyValidityBlocked("initial model seed must equal 0")
    if hash_dim != 1024:
        raise PolicyValidityBlocked("initial model hash_dim must equal 1024")
    torch = _torch_module()
    from analysis_scripts.noncombat_policy_model import CandidateRanker

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(model_seed)
    torch.manual_seed(model_seed)
    model = CandidateRanker(input_dim=hash_dim)
    if next(model.parameters()).device.type != "cpu":
        raise PolicyValidityBlocked("initial model must remain on CPU")
    model.requires_grad_(False)
    model.eval()
    return model


def canonical_model_sha256(model: Any) -> str:
    return sha256_bytes(canonical_json_bytes(canonical_model_payload(model)))


def load_frozen_model(payload: Mapping[str, Any], *, expected_hash_dim: int):
    if payload.get("schema_version") != "noncombat-simulator-training-model-v1":
        raise PolicyValidityBlocked("frozen model schema mismatch")
    if payload.get("architecture") != "candidate-ranker-linear-v1":
        raise PolicyValidityBlocked("frozen model architecture mismatch")
    if payload.get("input_dim") != expected_hash_dim:
        raise PolicyValidityBlocked("frozen model input dimension mismatch")
    state_value = payload.get("state_dict")
    if not isinstance(state_value, Mapping) or set(state_value) != {
        "scorer.bias",
        "scorer.weight",
    }:
        raise PolicyValidityBlocked("frozen model state_dict keys mismatch")

    torch = _torch_module()
    from analysis_scripts.noncombat_policy_model import CandidateRanker

    expected_shapes = {
        "scorer.bias": [1],
        "scorer.weight": [1, expected_hash_dim],
    }
    tensors = {}
    for name in ("scorer.bias", "scorer.weight"):
        entry = state_value[name]
        if not isinstance(entry, Mapping):
            raise PolicyValidityBlocked(f"frozen model tensor {name} is invalid")
        if entry.get("dtype") != "float32" or entry.get("shape") != expected_shapes[name]:
            raise PolicyValidityBlocked(f"frozen model tensor {name} metadata mismatch")
        values = entry.get("values")
        expected_count = math.prod(expected_shapes[name])
        if not isinstance(values, list) or len(values) != expected_count:
            raise PolicyValidityBlocked(f"frozen model tensor {name} value count mismatch")
        parsed = []
        for value in values:
            if not isinstance(value, str):
                raise PolicyValidityBlocked(f"frozen model tensor {name} value is invalid")
            try:
                numeric = float.fromhex(value)
            except ValueError as exc:
                raise PolicyValidityBlocked(
                    f"frozen model tensor {name} value is invalid"
                ) from exc
            if not math.isfinite(numeric):
                raise PolicyValidityBlocked(
                    f"frozen model tensor {name} values must be finite"
                )
            parsed.append(numeric)
        tensors[name] = torch.tensor(parsed, dtype=torch.float32).reshape(
            expected_shapes[name]
        )

    model = CandidateRanker(input_dim=expected_hash_dim)
    model.load_state_dict(tensors, strict=True)
    if next(model.parameters()).device.type != "cpu":
        raise PolicyValidityBlocked("frozen model must remain on CPU")
    model.requires_grad_(False)
    model.eval()
    core_payload = {
        key: copy.deepcopy(payload[key])
        for key in ("architecture", "input_dim", "schema_version", "state_dict")
    }
    if canonical_model_payload(model) != core_payload:
        raise PolicyValidityBlocked("frozen model canonical round trip mismatch")
    return model


def _rows_by_seed(value: Mapping[str, Any], label: str) -> dict[int, Mapping[str, Any]]:
    rows = value.get("rows")
    if not isinstance(rows, list):
        raise PolicyValidityBlocked(f"{label}.rows must be an array")
    result: dict[int, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or isinstance(row.get("seed"), bool) or not isinstance(
            row.get("seed"), int
        ):
            raise PolicyValidityBlocked(f"{label} row seed is invalid")
        seed = int(row["seed"])
        if seed in result:
            raise PolicyValidityBlocked(f"{label} has duplicate seed {seed}")
        result[seed] = row
    return result


def run_compatibility_gate(
    *,
    environment_factory: Callable[[int], Any],
    initial_model: Any,
    trained_model: Any,
    published_trajectories: Mapping[str, Any],
    seeds: Sequence[int],
    hash_dim: int,
    max_decisions_per_episode: int,
    deadline: float,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    try:
        holdout = published_trajectories.get("holdout")
        if not isinstance(holdout, Mapping):
            raise PolicyValidityBlocked("published trajectories holdout is missing")
        published_initial = _rows_by_seed(
            _mapping(holdout.get("initial"), "published holdout.initial"),
            "published holdout.initial",
        )
        published_trained = _rows_by_seed(
            _mapping(holdout.get("final"), "published holdout.final"),
            "published holdout.final",
        )
        initial_before = canonical_model_sha256(initial_model)
        trained_before = canonical_model_sha256(trained_model)
        actual_initial = evaluate_greedy_policy(
            initial_model,
            environment_factory=environment_factory,
            seeds=seeds,
            hash_dim=hash_dim,
            max_decisions_per_episode=max_decisions_per_episode,
            deadline=deadline,
            clock=clock,
        )
        actual_trained = evaluate_greedy_policy(
            trained_model,
            environment_factory=environment_factory,
            seeds=seeds,
            hash_dim=hash_dim,
            max_decisions_per_episode=max_decisions_per_episode,
            deadline=deadline,
            clock=clock,
        )
    except (SmokeBlocked, SimulatorAdapterError) as exc:
        raise PolicyValidityBlocked(f"compatibility rollout failed: {exc}") from exc
    if (
        canonical_model_sha256(initial_model) != initial_before
        or canonical_model_sha256(trained_model) != trained_before
    ):
        raise PolicyValidityBlocked("compatibility rollout changed a frozen model")

    actual_sets = {
        "initial": _rows_by_seed(actual_initial, "actual initial"),
        "final": _rows_by_seed(actual_trained, "actual final"),
    }
    published_sets = {"initial": published_initial, "final": published_trained}
    for policy_name in ("initial", "final"):
        for seed in seeds:
            if seed not in published_sets[policy_name]:
                raise PolicyValidityBlocked(
                    f"published {policy_name} compatibility seed {seed} is missing"
                )
            if seed not in actual_sets[policy_name]:
                raise PolicyValidityBlocked(
                    f"actual {policy_name} compatibility seed {seed} is missing"
                )
            expected = published_sets[policy_name][seed]
            actual = actual_sets[policy_name][seed]
            for field in (
                "policy_input_sha256s",
                "selected_action_ids",
                "action_sequence_sha256",
                "outcome",
                "terminal_floor",
            ):
                if actual.get(field) != expected.get(field):
                    raise PolicyValidityBlocked(
                        f"compatibility {policy_name} seed {seed} {field} mismatch"
                    )
    return {
        "initial_model_sha256": initial_before,
        "matched": True,
        "quality_rows_included": 0,
        "seeds": list(seeds),
        "trained_model_sha256": trained_before,
    }


def _validate_bound_smoke_artifacts(
    repo_root: Path,
    smoke_artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    expected_names = {
        "manifest": "artifact_manifest.json",
        "model": "model.json",
        "trajectories": "trajectories.json",
    }
    paths: dict[str, Path] = {}
    for name, binding in smoke_artifacts.items():
        try:
            actual = _actual_binding(repo_root, binding)
        except SmokeBlocked as exc:
            raise PolicyValidityBlocked(str(exc)) from exc
        if actual != dict(binding):
            raise PolicyValidityBlocked(f"smoke artifact {name} binding mismatch")
        paths[name] = (repo_root / binding["path"]).resolve()

    artifact_root = paths["manifest"].parent
    for name, expected_name in expected_names.items():
        if paths[name].parent != artifact_root or paths[name].name != expected_name:
            raise PolicyValidityBlocked(
                f"smoke artifact {name} must be {expected_name} beside the manifest"
            )
    try:
        manifest = validate_smoke_artifact_directory(artifact_root)
        smoke_registration = validate_smoke_registration(
            _load_bound_json(
                repo_root,
                smoke_artifacts["registration"],
                "smoke registration",
            )
        )
    except SmokeBlocked as exc:
        raise PolicyValidityBlocked(f"smoke artifact bundle is invalid: {exc}") from exc

    registration_sha256 = sha256_bytes(canonical_json_bytes(smoke_registration))
    bound_payloads = {
        "manifest": manifest,
        "model": _load_bound_artifact_json(
            repo_root, smoke_artifacts["model"], "smoke model"
        ),
        "trajectories": _load_bound_artifact_json(
            repo_root, smoke_artifacts["trajectories"], "smoke trajectories"
        ),
    }
    for name, payload in bound_payloads.items():
        if payload.get("registration_sha256") != registration_sha256:
            raise PolicyValidityBlocked(
                f"smoke artifact {name} registration SHA-256 mismatch"
            )
    artifact_hashes = manifest.get("artifact_hashes")
    if not isinstance(artifact_hashes, Mapping):
        raise PolicyValidityBlocked("smoke manifest artifact hashes are missing")
    for name in ("model", "trajectories"):
        filename = expected_names[name]
        if artifact_hashes.get(filename) != smoke_artifacts[name]["sha256"]:
            raise PolicyValidityBlocked(
                f"smoke manifest does not bind {filename}"
            )
    return manifest


def _rollout_native_policy(
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    max_decisions_per_episode: int,
    deadline: float,
    clock: Callable[[], float],
) -> dict[str, Any]:
    environment = environment_factory(seed)
    categories: set[str] = set()
    action_rows: list[dict[str, Any]] = []
    rewards: list[float] = []
    decisions = 0
    while True:
        try:
            _check_deadline(deadline, clock)
        except SmokeBlocked as exc:
            raise PolicyValidityBlocked(str(exc)) from exc
        snapshot = environment.snapshot()
        if snapshot.get("terminal") is True:
            break
        if decisions >= max_decisions_per_episode:
            raise PolicyValidityBlocked(
                f"native baseline seed {seed} exceeded max decisions"
            )
        category = snapshot.get("category")
        if category not in TARGET_CATEGORIES:
            raise PolicyValidityBlocked(
                f"native baseline seed {seed} stopped outside a target category"
            )
        candidates = environment.legal_actions()
        if not isinstance(candidates, list) or not candidates:
            raise PolicyValidityBlocked("native baseline candidate set is empty")
        candidate_ids = [candidate.get("action_id") for candidate in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise PolicyValidityBlocked("native baseline candidate ids are duplicated")
        before_snapshot_bytes = canonical_json_bytes(snapshot)
        before_candidate_bytes = canonical_json_bytes(candidates)
        action = environment.native_baseline_action()
        if canonical_json_bytes(environment.snapshot()) != before_snapshot_bytes:
            raise PolicyValidityBlocked("native baseline query mutated source snapshot")
        if canonical_json_bytes(environment.legal_actions()) != before_candidate_bytes:
            raise PolicyValidityBlocked("native baseline query mutated source candidates")
        if not isinstance(action, Mapping) or action.get("policy_id") != NATIVE_TARGET_POLICY_ID:
            raise PolicyValidityBlocked("native baseline policy identity mismatch")
        action_id = action.get("action_id")
        if candidate_ids.count(action_id) != 1:
            raise PolicyValidityBlocked(
                "native baseline action is not exactly one current candidate"
            )
        transition = environment.step_native_baseline()
        if transition.get("selected_action_id") != action_id:
            raise PolicyValidityBlocked("native baseline query and step differ")
        reward = simulator_training_reward(transition)
        action_rows.append(
            {
                "action_id": action_id,
                "category": category,
                "decision": decisions,
                "native_action_sha256": sha256_bytes(canonical_json_bytes(action)),
                "reward": reward,
            }
        )
        rewards.append(reward)
        categories.add(str(category))
        decisions += 1

    terminal = environment.snapshot()
    state = terminal.get("state")
    if not isinstance(state, Mapping):
        raise PolicyValidityBlocked("native baseline terminal state is invalid")
    outcome = state.get("outcome")
    floor = state.get("floor")
    if outcome not in {"player_loss", "player_victory"}:
        raise PolicyValidityBlocked("native baseline did not reach a terminal outcome")
    if isinstance(floor, bool) or not isinstance(floor, Real) or not math.isfinite(float(floor)):
        raise PolicyValidityBlocked("native baseline terminal floor is invalid")
    return {
        "action_sequence_sha256": sha256_bytes(canonical_json_bytes(action_rows)),
        "candidate_legality": True,
        "categories": sorted(categories),
        "decisions": decisions,
        "native_action_sha256s": [row["native_action_sha256"] for row in action_rows],
        "outcome": outcome,
        "seed": seed,
        "selected_action_ids": [row["action_id"] for row in action_rows],
        "terminal_floor": float(floor),
        "total_reward": sum(rewards),
    }


def evaluate_native_policy(
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    max_decisions_per_episode: int,
    deadline: float,
    clock: Callable[[], float],
) -> dict[str, Any]:
    rows = []
    categories: set[str] = set()
    for seed in seeds:
        row = _rollout_native_policy(
            environment_factory=environment_factory,
            seed=int(seed),
            max_decisions_per_episode=max_decisions_per_episode,
            deadline=deadline,
            clock=clock,
        )
        rows.append(row)
        categories.update(row["categories"])
    return {
        "all_categories": sorted(categories),
        "candidate_legality": True,
        "policy_id": NATIVE_TARGET_POLICY_ID,
        "rows": rows,
        "terminal_outcomes": all(
            row["outcome"] in {"player_loss", "player_victory"} for row in rows
        ),
    }


def _paired_comparison(
    trained: Mapping[str, Any],
    baseline: Mapping[str, Any],
    *,
    comparison_id: str,
    seeds: Sequence[int],
    bootstrap_seed: int,
    bootstrap_resamples: int,
    confidence_level: float,
) -> dict[str, Any]:
    trained_rows = _rows_by_seed(trained, "trained policy")
    baseline_rows = _rows_by_seed(baseline, comparison_id)
    paired_rows = []
    for seed in seeds:
        if int(seed) not in trained_rows or int(seed) not in baseline_rows:
            raise PolicyValidityBlocked(
                f"{comparison_id} is missing paired seed {int(seed)}"
            )
        trained_row = trained_rows[int(seed)]
        baseline_row = baseline_rows[int(seed)]
        paired_rows.append(
            {
                "baseline_outcome": baseline_row["outcome"],
                "baseline_terminal_floor": baseline_row["terminal_floor"],
                "floor_difference": trained_row["terminal_floor"]
                - baseline_row["terminal_floor"],
                "seed": int(seed),
                "trained_outcome": trained_row["outcome"],
                "trained_terminal_floor": trained_row["terminal_floor"],
                "victory_difference": int(trained_row["outcome"] == "player_victory")
                - int(baseline_row["outcome"] == "player_victory"),
            }
        )
    try:
        interval = paired_bootstrap_interval(
            [row["floor_difference"] for row in paired_rows],
            seed=bootstrap_seed,
            resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        )
    except (SmokeBlocked, SimulatorAdapterError) as exc:
        raise PolicyValidityBlocked(str(exc)) from exc
    return {
        "comparison_id": comparison_id,
        "floor_difference_ci": interval,
        "paired_rows": paired_rows,
    }


def run_policy_validity_execution(
    *,
    environment_factory: Callable[[int], Any],
    fresh_seeds: Sequence[int],
    trained_model: Any,
    initial_model: Any,
    hash_dim: int,
    max_decisions_per_episode: int,
    max_episodes: int,
    max_wall_seconds: float,
    bootstrap_seed: int,
    bootstrap_resamples: int,
    confidence_level: float,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    seeds = list(fresh_seeds)
    if not seeds or len(seeds) != len(set(seeds)):
        raise PolicyValidityBlocked("fresh seeds must be nonempty and unique")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise PolicyValidityBlocked("fresh seeds must contain only integers")
    required_episodes = len(seeds) * len(POLICY_IDS)
    if required_episodes > max_episodes or max_episodes > 192:
        raise PolicyValidityBlocked("max episodes does not cover the fixed policies")
    if not 1 <= max_decisions_per_episode <= 500:
        raise PolicyValidityBlocked("max decisions must be between 1 and 500")
    if not 0.0 < float(max_wall_seconds) <= 480.0:
        raise PolicyValidityBlocked("max wall seconds must be positive and at most 480")
    if not 1 <= bootstrap_resamples <= 10_000:
        raise PolicyValidityBlocked("bootstrap resamples must be between 1 and 10000")
    if confidence_level != 0.95 or bootstrap_seed != 0:
        raise PolicyValidityBlocked("bootstrap contract mismatch")

    torch = _torch_module()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    started = clock()
    deadline = started + float(max_wall_seconds)
    initial_before = canonical_model_sha256(initial_model)
    trained_before = canonical_model_sha256(trained_model)
    try:
        with torch.inference_mode():
            trained = evaluate_greedy_policy(
                trained_model,
                environment_factory=environment_factory,
                seeds=seeds,
                hash_dim=hash_dim,
                max_decisions_per_episode=max_decisions_per_episode,
                deadline=deadline,
                clock=clock,
            )
            initial = evaluate_greedy_policy(
                initial_model,
                environment_factory=environment_factory,
                seeds=seeds,
                hash_dim=hash_dim,
                max_decisions_per_episode=max_decisions_per_episode,
                deadline=deadline,
                clock=clock,
            )
            native = evaluate_native_policy(
                environment_factory=environment_factory,
                seeds=seeds,
                max_decisions_per_episode=max_decisions_per_episode,
                deadline=deadline,
                clock=clock,
            )
    except (SmokeBlocked, SimulatorAdapterError) as exc:
        raise PolicyValidityBlocked(str(exc)) from exc

    policies = {
        "smoke_trained": trained,
        "seeded_initial": initial,
        "native_simple_agent": native,
    }
    for policy in policies.values():
        for row in policy["rows"]:
            row["candidate_legality"] = policy.get("candidate_legality") is True
    initial_after = canonical_model_sha256(initial_model)
    trained_after = canonical_model_sha256(trained_model)
    model_immutability = initial_before == initial_after and trained_before == trained_after
    no_gradients = all(
        parameter.grad is None
        for model in (initial_model, trained_model)
        for parameter in model.parameters()
    )
    all_rows = [row for policy in policies.values() for row in policy["rows"]]
    finite_metrics = all(
        not isinstance(row.get("terminal_floor"), bool)
        and isinstance(row.get("terminal_floor"), Real)
        and math.isfinite(float(row["terminal_floor"]))
        and not isinstance(row.get("total_reward"), bool)
        and isinstance(row.get("total_reward"), Real)
        and math.isfinite(float(row["total_reward"]))
        and not isinstance(row.get("decisions"), bool)
        and isinstance(row.get("decisions"), int)
        and 0 <= row["decisions"] <= max_decisions_per_episode
        for row in all_rows
    )
    if not finite_metrics:
        raise PolicyValidityBlocked("policy terminal metrics must be finite and bounded")
    all_categories = {
        category
        for policy in policies.values()
        for category in policy["all_categories"]
    }
    comparisons = {
        "trained_minus_native_simple_agent": _paired_comparison(
            trained,
            native,
            comparison_id="trained_minus_native_simple_agent",
            seeds=seeds,
            bootstrap_seed=bootstrap_seed,
            bootstrap_resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        ),
        "trained_minus_seeded_initial": _paired_comparison(
            trained,
            initial,
            comparison_id="trained_minus_seeded_initial",
            seeds=seeds,
            bootstrap_seed=bootstrap_seed,
            bootstrap_resamples=bootstrap_resamples,
            confidence_level=confidence_level,
        ),
    }
    return {
        "checks": {
            "candidate_legality": all(
                policy.get("candidate_legality") is True for policy in policies.values()
            ),
            "episode_count": len(all_rows) == required_episodes,
            "finite_metrics": finite_metrics,
            "four_category_coverage": all_categories == set(TARGET_CATEGORIES),
            "model_immutability": model_immutability,
            "no_gradients": no_gradients,
            "terminal_outcomes": all(
                row["outcome"] in {"player_loss", "player_victory"} for row in all_rows
            ),
            "within_bounds": (
                len(all_rows) <= max_episodes
                and all(row["decisions"] <= max_decisions_per_episode for row in all_rows)
            ),
        },
        "comparisons": comparisons,
        "execution_schema_version": EXECUTION_SCHEMA_VERSION,
        "fresh_seeds": seeds,
        "limits": {
            "max_decisions_per_episode": max_decisions_per_episode,
            "max_episodes": max_episodes,
            "max_wall_seconds": max_wall_seconds,
        },
        "model_hashes": {
            "seeded_initial": initial_after,
            "smoke_trained": trained_after,
        },
        "policies": policies,
        "victories": {
            policy_id: sum(row["outcome"] == "player_victory" for row in policy["rows"])
            for policy_id, policy in sorted(policies.items())
        },
    }


def classify_policy_validity_results(
    primary: Mapping[str, Any], replay: Mapping[str, Any]
) -> dict[str, Any]:
    checks_value = primary.get("checks")
    if not isinstance(checks_value, Mapping):
        raise PolicyValidityBlocked("primary checks are missing")
    checks = dict(checks_value)
    blockers = [name for name, passed in sorted(checks.items()) if passed is not True]
    replay_identity = canonical_json_bytes(primary) == canonical_json_bytes(replay)
    replay_difference = "" if replay_identity else _first_difference(
        primary, replay, "execution"
    )
    if not replay_identity:
        blockers.append("replay_identity")
    if blockers:
        quality = "not_evaluated"
        verdict = "blocked"
    else:
        comparisons = primary.get("comparisons")
        if not isinstance(comparisons, Mapping):
            raise PolicyValidityBlocked("primary comparisons are missing")
        primary_comparison = comparisons.get("trained_minus_native_simple_agent")
        if not isinstance(primary_comparison, Mapping):
            raise PolicyValidityBlocked("primary comparison is missing")
        interval = primary_comparison.get("floor_difference_ci")
        if not isinstance(interval, Mapping):
            raise PolicyValidityBlocked("primary interval is missing")
        lower = interval.get("lower")
        if isinstance(lower, bool) or not isinstance(lower, Real) or not math.isfinite(
            float(lower)
        ):
            raise PolicyValidityBlocked("primary lower bound is invalid")
        if float(lower) > 0.0:
            quality = "baseline_signal"
            verdict = "study_valid_with_baseline_signal"
        else:
            quality = "baseline_signal_not_demonstrated"
            verdict = "study_valid_without_baseline_signal"
    return {
        "authority": _authority(),
        "blockers": blockers,
        "checks": {**checks, "replay_identity": replay_identity},
        "quality": quality,
        "replay_difference": replay_difference,
        "verdict": verdict,
    }


def _mean_floor(policy: Mapping[str, Any]) -> float:
    rows = policy["rows"]
    return sum(float(row["terminal_floor"]) for row in rows) / len(rows)


def _render_report(metrics: Mapping[str, Any]) -> str:
    classification = metrics["classification"]
    primary = metrics["comparisons"]["trained_minus_native_simple_agent"]
    secondary = metrics["comparisons"]["trained_minus_seeded_initial"]
    lines = [
        "# Non-Combat Simulator Policy Validity Study",
        "",
        f"- Verdict: `{classification['verdict']}`",
        f"- Quality: `{classification['quality']}`",
        f"- Registration SHA-256: `{metrics['registration_sha256']}`",
        f"- Fresh paired seeds: {metrics['fresh_seed_count']}",
        (
            "- Primary trained-minus-SimpleAgent floor interval: "
            f"[{primary['floor_difference_ci']['lower']:.6f}, "
            f"{primary['floor_difference_ci']['upper']:.6f}]"
        ),
        (
            "- Secondary trained-minus-initial floor interval: "
            f"[{secondary['floor_difference_ci']['lower']:.6f}, "
            f"{secondary['floor_difference_ci']['upper']:.6f}]"
        ),
        "",
        "## Policies",
        "",
    ]
    for policy_id in POLICY_IDS:
        summary = metrics["policy_summaries"][policy_id]
        lines.append(
            f"- {policy_id}: mean floor {summary['mean_terminal_floor']:.6f}, "
            f"victories {summary['victories']}/{summary['episodes']}, "
            f"categories {', '.join(summary['categories'])}"
        )
    lines.extend(["", "## Checks", ""])
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
            "- Floors and victories are simulator-only evidence.",
            "- Combat and unsupported non-combat screens use the declared adapter baseline.",
            "- Current and Bottled pilot models are excluded because no simulator feature/action bridge is validated.",
            "- A floor signal does not authorize training, live loading, OPE, qualification, gameplay, or promotion.",
            "- No alternate model, metric, seed cohort, or parameter retry is permitted under this change.",
        ]
    )
    if metrics["policy_summaries"]["smoke_trained"]["victories"] == 0:
        lines.append("- The trained policy recorded zero simulator victories in this cohort.")
    return "\n".join(lines) + "\n"


def build_canonical_artifacts(
    *,
    registration: Mapping[str, Any],
    compatibility: Mapping[str, Any],
    primary: Mapping[str, Any],
    replay: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, bytes]:
    validated = validate_policy_validity_registration(registration)
    registration_sha256 = sha256_bytes(canonical_json_bytes(validated))
    trajectories = {
        "compatibility": dict(compatibility),
        "comparisons": primary["comparisons"],
        "policies": primary["policies"],
        "registration_sha256": registration_sha256,
        "replay_execution_sha256": sha256_bytes(canonical_json_bytes(replay)),
        "schema_version": TRAJECTORY_SCHEMA_VERSION,
    }
    policy_summaries = {
        policy_id: {
            "categories": primary["policies"][policy_id]["all_categories"],
            "episodes": len(primary["policies"][policy_id]["rows"]),
            "mean_terminal_floor": _mean_floor(primary["policies"][policy_id]),
            "victories": primary["victories"][policy_id],
        }
        for policy_id in POLICY_IDS
    }
    metrics = {
        "authority": classification["authority"],
        "checks": primary["checks"],
        "classification": dict(classification),
        "comparisons": {
            name: {
                "floor_difference_ci": value["floor_difference_ci"],
                "paired_seed_count": len(value["paired_rows"]),
            }
            for name, value in sorted(primary["comparisons"].items())
        },
        "fresh_seed_count": len(primary["fresh_seeds"]),
        "model_hashes": primary["model_hashes"],
        "policy_summaries": policy_summaries,
        "registration_sha256": registration_sha256,
        "schema_version": METRICS_SCHEMA_VERSION,
    }
    payloads = {
        "metrics.json": canonical_json_bytes(metrics),
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
        raise PolicyValidityBlocked("canonical artifact set is incomplete")
    if any(not isinstance(payload, bytes) for payload in artifacts.values()):
        raise PolicyValidityBlocked("canonical artifacts must be bytes")
    try:
        manifest = json.loads(artifacts["artifact_manifest.json"])
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyValidityBlocked(f"artifact manifest is invalid: {exc}") from exc
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise PolicyValidityBlocked("artifact manifest schema mismatch")
    expected_hashes = {
        name: sha256_bytes(artifacts[name])
        for name in sorted(artifacts)
        if name != "artifact_manifest.json"
    }
    if manifest.get("artifact_hashes") != expected_hashes:
        raise PolicyValidityBlocked("artifact manifest hash closure mismatch")
    authority = manifest.get("authority")
    if not isinstance(authority, Mapping) or any(value is not False for value in authority.values()):
        raise PolicyValidityBlocked("artifact manifest authority must remain false")
    return manifest


def publish_canonical_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
) -> None:
    _validate_artifact_payloads(artifacts)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    order = sorted(name for name in artifacts if name != "artifact_manifest.json")
    order.append("artifact_manifest.json")
    destinations = {name: root / name for name in order}
    previous = {
        name: path.read_bytes() if path.is_file() else None
        for name, path in destinations.items()
    }
    temporary = {
        name: path.with_name(f".{path.name}.tmp") for name, path in destinations.items()
    }
    installed = []
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
    try:
        manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyValidityBlocked(f"cannot load artifact manifest: {exc}") from exc
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise PolicyValidityBlocked("published artifact manifest schema mismatch")
    expected = manifest.get("artifact_hashes")
    if not isinstance(expected, Mapping):
        raise PolicyValidityBlocked("published artifact hashes are missing")
    actual = {}
    for name in sorted(expected):
        path = root / name
        if not path.is_file():
            raise PolicyValidityBlocked(f"published artifact is missing: {name}")
        actual[name] = sha256_file(path)
    if actual != dict(expected):
        raise PolicyValidityBlocked("published artifact hash closure mismatch")
    authority = manifest.get("authority")
    if not isinstance(authority, Mapping) or any(value is not False for value in authority.values()):
        raise PolicyValidityBlocked("published authority must remain false")
    return manifest


def run_registered_study(
    registration: Mapping[str, Any],
    *,
    actual_identity: Mapping[str, Any],
    environment_factory: Callable[[int], Any],
    initial_model: Any,
    trained_model: Any,
    published_trajectories: Mapping[str, Any],
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    validated = validate_policy_validity_registration(registration)
    mismatches = _identity_mismatches(validated["identity"], actual_identity)
    if mismatches:
        raise PolicyValidityBlocked("runtime identity mismatch: " + ", ".join(mismatches))
    study = validated["study"]
    started = clock()
    compatibility = run_compatibility_gate(
        environment_factory=environment_factory,
        initial_model=initial_model,
        trained_model=trained_model,
        published_trajectories=published_trajectories,
        seeds=study["cohorts"]["compatibility_seeds"],
        hash_dim=study["model"]["hash_dim"],
        max_decisions_per_episode=study["limits"]["max_decisions_per_episode"],
        deadline=started + study["limits"]["max_wall_seconds_per_execution"],
        clock=clock,
    )
    execution = run_policy_validity_execution(
        environment_factory=environment_factory,
        fresh_seeds=study["cohorts"]["fresh_seeds"],
        trained_model=trained_model,
        initial_model=initial_model,
        hash_dim=study["model"]["hash_dim"],
        max_decisions_per_episode=study["limits"]["max_decisions_per_episode"],
        max_episodes=study["limits"]["max_episodes_per_execution"],
        max_wall_seconds=study["limits"]["max_wall_seconds_per_execution"],
        bootstrap_seed=study["evaluation"]["bootstrap_seed"],
        bootstrap_resamples=study["evaluation"]["bootstrap_resamples"],
        confidence_level=study["evaluation"]["confidence_level"],
        clock=clock,
    )
    return {"compatibility": compatibility, "execution": execution}


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyValidityBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_policy_validity_registration(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except PolicyValidityBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PolicyValidityBlocked(f"cannot load study input {path}: {exc}") from exc
    return validate_policy_validity_registration(value)


def _load_bound_artifact_json(
    repo_root: Path, binding: Mapping[str, Any], label: str
) -> Mapping[str, Any]:
    try:
        return _load_bound_json(repo_root, binding, label)
    except SmokeBlocked as exc:
        raise PolicyValidityBlocked(str(exc)) from exc


def collect_actual_identity(
    registration: Mapping[str, Any],
    *,
    repo_root: Path | str,
    simulator_repo: Path | str,
    module_path: Path | str,
    native_module: Any,
) -> dict[str, Any]:
    validated = validate_policy_validity_registration(registration)
    identity = validated["identity"]
    root = Path(repo_root).resolve()
    simulator = Path(simulator_repo).resolve()
    module_file = Path(module_path).resolve()

    fit_input = _load_bound_artifact_json(
        root, identity["adapter_fit_input"], "adapter fit input"
    )
    fit_report = _load_bound_artifact_json(
        root, identity["adapter_fit_report"], "adapter fit report"
    )
    _validate_bound_smoke_artifacts(root, identity["smoke_artifacts"])
    try:
        validate_bound_fit_evidence(
            fit_input, fit_report, identity["adapter_provenance"]
        )
    except SmokeBlocked as exc:
        raise PolicyValidityBlocked(str(exc)) from exc
    required_fit_checks = {
        "native_baseline_candidate_mapping",
        "native_baseline_four_category_coverage",
        "native_baseline_non_mutation",
        "native_baseline_repeated_seed_determinism",
        "native_baseline_terminal_outcomes",
    }
    checks = fit_report.get("checks")
    if not isinstance(checks, Mapping) or any(checks.get(name) is not True for name in required_fit_checks):
        raise PolicyValidityBlocked("adapter fit lacks native baseline checks")

    adapter_commit = identity["adapter_provenance"]["adapter_commit"]
    try:
        _verify_sources_at_commit(root, adapter_commit, ADAPTER_SOURCE_FILES)
        _verify_sources_at_commit(
            root,
            identity["implementation"]["commit"],
            identity["implementation"]["source_files"],
        )
    except SmokeBlocked as exc:
        raise PolicyValidityBlocked(str(exc)) from exc

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
    torch = _torch_module()
    return {
        "adapter_fit_input": _actual_binding(root, identity["adapter_fit_input"]),
        "adapter_fit_report": _actual_binding(root, identity["adapter_fit_report"]),
        "adapter_provenance": provenance,
        "excluded_baselines": {
            name: {
                "feature_version": entry["feature_version"],
                "model": _actual_binding(root, entry["model"]),
                "reason": entry["reason"],
            }
            for name, entry in sorted(identity["excluded_baselines"].items())
        },
        "implementation": {
            "commit": identity["implementation"]["commit"],
            "source_files": list(identity["implementation"]["source_files"]),
            "source_sha256": hash_bound_files(
                root, identity["implementation"]["source_files"]
            ),
        },
        "runtime": {"python": sys.version.split()[0], "torch": torch.__version__},
        "smoke_artifacts": {
            name: _actual_binding(root, binding)
            for name, binding in sorted(identity["smoke_artifacts"].items())
        },
    }


def _build_execution_journal(
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
            raise PolicyValidityBlocked(f"{label} must be finite and non-negative")
    return {
        "canonical": False,
        "primary_elapsed_seconds": float(primary_elapsed_seconds),
        "replay_elapsed_seconds": float(replay_elapsed_seconds),
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "wall_time_budget_seconds": float(wall_time_budget_seconds),
    }


def _publish_journal(output_dir: Path | str, journal: Mapping[str, Any]) -> None:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / "execution_journal.json"
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_bytes(canonical_json_bytes(journal))
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


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
    wall_time_budget = 480.0
    try:
        registration = load_policy_validity_registration(args.input)
        wall_time_budget = registration["study"]["limits"][
            "max_wall_seconds_per_execution"
        ]
        phase = "native_and_identity"
        module = load_native_module(args.module, dll_directories=args.dll_directory)
        actual_identity = collect_actual_identity(
            registration,
            repo_root=repo_root,
            simulator_repo=args.simulator_repo,
            module_path=args.module,
            native_module=module,
        )
        mismatches = _identity_mismatches(registration["identity"], actual_identity)
        if mismatches:
            raise PolicyValidityBlocked(
                "runtime identity mismatch: " + ", ".join(mismatches)
            )

        smoke_model = _load_bound_artifact_json(
            repo_root,
            registration["identity"]["smoke_artifacts"]["model"],
            "smoke model",
        )
        smoke_trajectories = _load_bound_artifact_json(
            repo_root,
            registration["identity"]["smoke_artifacts"]["trajectories"],
            "smoke trajectories",
        )
        initial_model = build_initial_model(hash_dim=1024, model_seed=0)
        trained_model = load_frozen_model(smoke_model, expected_hash_dim=1024)
        provenance = actual_identity["adapter_provenance"]

        def environment_factory(seed: int) -> NativeSimulatorEnvironment:
            return NativeSimulatorEnvironment(module.Environment(seed, 0), provenance)

        phase = "compatibility"
        compatibility_started = time.perf_counter()
        compatibility = run_compatibility_gate(
            environment_factory=environment_factory,
            initial_model=initial_model,
            trained_model=trained_model,
            published_trajectories=smoke_trajectories,
            seeds=COMPATIBILITY_SEEDS,
            hash_dim=1024,
            max_decisions_per_episode=500,
            deadline=compatibility_started + wall_time_budget,
        )

        study = registration["study"]
        phase = "primary"
        primary_started = time.perf_counter()
        primary = run_policy_validity_execution(
            environment_factory=environment_factory,
            fresh_seeds=study["cohorts"]["fresh_seeds"],
            trained_model=trained_model,
            initial_model=initial_model,
            hash_dim=study["model"]["hash_dim"],
            max_decisions_per_episode=study["limits"]["max_decisions_per_episode"],
            max_episodes=study["limits"]["max_episodes_per_execution"],
            max_wall_seconds=wall_time_budget,
            bootstrap_seed=study["evaluation"]["bootstrap_seed"],
            bootstrap_resamples=study["evaluation"]["bootstrap_resamples"],
            confidence_level=study["evaluation"]["confidence_level"],
        )
        primary_elapsed = time.perf_counter() - primary_started

        phase = "replay"
        replay_started = time.perf_counter()
        replay = run_policy_validity_execution(
            environment_factory=environment_factory,
            fresh_seeds=study["cohorts"]["fresh_seeds"],
            trained_model=trained_model,
            initial_model=initial_model,
            hash_dim=study["model"]["hash_dim"],
            max_decisions_per_episode=study["limits"]["max_decisions_per_episode"],
            max_episodes=study["limits"]["max_episodes_per_execution"],
            max_wall_seconds=wall_time_budget,
            bootstrap_seed=study["evaluation"]["bootstrap_seed"],
            bootstrap_resamples=study["evaluation"]["bootstrap_resamples"],
            confidence_level=study["evaluation"]["confidence_level"],
        )
        replay_elapsed = time.perf_counter() - replay_started

        phase = "classification_and_publication"
        classification = classify_policy_validity_results(primary, replay)
        artifacts = build_canonical_artifacts(
            registration=registration,
            compatibility=compatibility,
            primary=primary,
            replay=replay,
            classification=classification,
        )
        publish_canonical_artifacts(args.output_dir, artifacts)
        _publish_journal(
            args.output_dir,
            _build_execution_journal(
                primary_elapsed_seconds=primary_elapsed,
                replay_elapsed_seconds=replay_elapsed,
                wall_time_budget_seconds=wall_time_budget,
            ),
        )
        validate_artifact_directory(args.output_dir)
    except (
        ImportError,
        OSError,
        PolicyValidityBlocked,
        SimulatorAdapterError,
        SmokeBlocked,
    ) as exc:
        try:
            _publish_journal(
                args.output_dir,
                {
                    "blocker": str(exc),
                    "canonical": False,
                    "elapsed_seconds": time.perf_counter() - phase_started,
                    "phase": phase,
                    "schema_version": JOURNAL_SCHEMA_VERSION,
                    "verdict": "blocked",
                    "wall_time_budget_seconds": wall_time_budget,
                },
            )
        except (OSError, PolicyValidityBlocked):
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
