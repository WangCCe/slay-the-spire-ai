"""Bounded, simulator-only non-combat RL experiment contracts and runtime."""

from __future__ import annotations

import copy
import base64
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
from typing import Any, Callable

from analysis_scripts.noncombat_formal_reward_contract import (
    RewardContractBlocked,
    reward_channels,
    validate_scalarization,
)
from analysis_scripts.noncombat_policy_model import (
    CandidateRanker,
    FeatureConfig,
    candidate_feature_vector,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    NATIVE_TARGET_POLICY_ID,
    TARGET_CATEGORIES,
    SimulatorAdapterError,
    validate_candidates,
    validate_provenance,
    validate_snapshot,
)


EXPERIMENT_SCHEMA_VERSION = "noncombat-simulator-rl-experiment-registration-v1"
AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-simulator-rl-experiment-authorization-v1"
)
FEATURE_VERSION = "noncombat-simulator-policy-features-v2"
ALGORITHM_VERSION = "candidate-masked-reinforce-experiment-v1"
REWARD_VERSION = "formal-victory-primary-scalar-v1"
CHECKPOINT_SCHEMA_VERSION = "noncombat-simulator-rl-checkpoint-v1"
CHECKPOINT_STATE_SCHEMA_VERSION = "noncombat-simulator-rl-checkpoint-state-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-simulator-rl-journal-v1"
LEASE_SCHEMA_VERSION = "noncombat-simulator-rl-lease-v1"
METRICS_SCHEMA_VERSION = "noncombat-simulator-rl-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-simulator-rl-manifest-v1"
EVALUATION_SCHEMA_VERSION = "noncombat-simulator-rl-paired-evaluation-v1"
TRAINING_CHUNK_SCHEMA_VERSION = "noncombat-simulator-rl-training-chunk-v1"
CONFIGURATION_SCHEMA_VERSION = "noncombat-simulator-rl-configuration-v1"
FINAL_MODEL_SCHEMA_VERSION = "noncombat-simulator-rl-final-model-v1"
TERMINAL_EVALUATION_SCHEMA_VERSION = "noncombat-simulator-rl-evaluation-v1"
PREFIX_REPLAY_SCHEMA_VERSION = "noncombat-simulator-rl-prefix-replay-v1"
PENDING_CHUNK_SCHEMA_VERSION = "noncombat-simulator-rl-pending-chunk-v1"
FORMAL_READINESS_VERDICT = "not_ready_for_bounded_training_proposal"
TERMINAL_VERDICTS = (
    "experiment_blocked",
    "experiment_stopped_at_canary",
    "experiment_valid_without_learning_signal",
    "experiment_valid_with_learning_signal",
)

TRAIN_SEEDS = tuple(range(50000, 51024))
CANARY_SEEDS = tuple(range(51024, 51152))
HOLDOUT_SEEDS = tuple(range(51152, 51664))
TRAIN_PASSES = 4
TRAINING_EPISODES = len(TRAIN_SEEDS) * TRAIN_PASSES
CHECKPOINT_INTERVAL_EPISODES = 64
TRAINING_CHUNKS = TRAINING_EPISODES // CHECKPOINT_INTERVAL_EPISODES
HASH_DIM = 1024
LEARNING_RATE = 0.001
DISCOUNT = 1.0
MODEL_SEED = 0
MAX_DECISIONS_PER_EPISODE = 500
MAX_WALL_SECONDS = 28_800.0
BOOTSTRAP_SEED = 0
BOOTSTRAP_RESAMPLES = 10_000
CONFIDENCE_LEVEL = 0.95
UNSUPPORTED_RATE_CEILING = 0.10
VICTORY_WEIGHT = 2.0
MAX_FLOOR = 57
REGISTERED_SUPPORT_BLOCKERS = (
    "unsupported_shop_courier_restock_semantics",
)
SIMULATOR_BASELINE_POLICY_ID = "sts_lightspeed_simple_agent_no_potions_v1"

IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_formal_reward_contract.py",
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_rl_experiment.py",
    "analysis_scripts/verify_noncombat_simulator_rl_experiment.py",
    "scripts/run_noncombat_simulator_rl_experiment.py",
)
EVIDENCE_BINDING_NAMES = (
    "formal_readiness_manifest",
    "formal_reward_manifest",
    "simulator_smoke_manifest",
    "simulator_smoke_registration",
)
AUTHORITY_NAMES = (
    "experiment_execution",
    "formal_noncombat_rl",
    "live_gameplay",
    "live_policy_loading",
    "live_study_launch",
    "ope_estimation",
    "ope_reinterpretation",
    "policy_promotion",
    "qualification",
)
POLICY_LEAKAGE_FIELDS = frozenset(
    {
        "baseline_control",
        "baseline_history",
        "bottled_label",
        "current_label",
        "live_outcome",
        "ope_value",
        "outcome",
        "provenance",
        "reward",
        "seed",
        "simple_agent_score",
        "target_action_id",
        "target_label",
        "terminal",
        "terminal_floor",
        "victory",
    }
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_EXECUTION_ID_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")


class ExperimentBlocked(RuntimeError):
    """Raised when the registered simulator experiment must fail closed."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the only accepted JSON encoding for control and evidence files."""
    try:
        return (
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ExperimentBlocked(f"value is not canonical JSON: {exc}") from exc


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExperimentBlocked(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ExperimentBlocked(f"non-finite JSON constant: {value}")


def load_canonical_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    """Parse duplicate-free JSON and require byte-for-byte canonical encoding."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExperimentBlocked(f"{label} must be UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except ExperimentBlocked:
        raise
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ExperimentBlocked(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ExperimentBlocked(f"{label} must be a JSON object")
    if canonical_json_bytes(value) != payload:
        raise ExperimentBlocked(f"{label} must use canonical JSON encoding")
    return value


def registration_authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def execution_authority() -> dict[str, bool]:
    result = registration_authority()
    result["experiment_execution"] = True
    return result


def experiment_contract() -> dict[str, Any]:
    """Return a fresh copy of the immutable experiment contract."""
    return {
        "algorithm": {
            "discount": DISCOUNT,
            "feature_version": FEATURE_VERSION,
            "hash_dim": HASH_DIM,
            "learning_rate": LEARNING_RATE,
            "model_seed": MODEL_SEED,
            "optimizer": "adam",
            "passes": TRAIN_PASSES,
            "standardize_returns": True,
            "version": ALGORITHM_VERSION,
        },
        "ascension": 0,
        "cohorts": {
            "canary_seeds": list(CANARY_SEEDS),
            "holdout_seeds": list(HOLDOUT_SEEDS),
            "train_seeds": list(TRAIN_SEEDS),
        },
        "evaluation": {
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "confidence_level": CONFIDENCE_LEVEL,
            "holdout_access": "only_after_canary_pass",
            "policy": "greedy",
            "trained_victories_must_exceed_initial": True,
            "unsupported_rate_denominator": "policy_episodes",
        },
        "execution": {
            "allow_parameter_retry": False,
            "logical_execution_count": 1,
            "prefix_replay_chunks": 2,
        },
        "limits": {
            "checkpoint_interval_episodes": CHECKPOINT_INTERVAL_EPISODES,
            "max_decisions_per_episode": MAX_DECISIONS_PER_EPISODE,
            "max_train_episodes": TRAINING_EPISODES,
            "max_wall_seconds": MAX_WALL_SECONDS,
            "unsupported_rate_ceiling": UNSUPPORTED_RATE_CEILING,
        },
        "reward": {
            "discount": DISCOUNT,
            "max_floor": MAX_FLOOR,
            "maximum_episode_floor_progress": 1.0,
            "progress_divisor": float(MAX_FLOOR),
            "strict_primary_dominance": True,
            "version": REWARD_VERSION,
            "victory_weight": VICTORY_WEIGHT,
        },
        "support": {
            "registered_blockers": list(REGISTERED_SUPPORT_BLOCKERS),
            "retain_in_denominator": True,
            "unsupported_disposition": "non_victory_at_last_supported_floor",
        },
    }


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExperimentBlocked(f"{label} must be an object")
    return value


def _require_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ExperimentBlocked(
            f"{label} fields mismatch: missing={missing}, extra={extra}"
        )


def _first_difference(before: Any, after: Any, path: str = "value") -> str:
    if type(before) is not type(after):
        return f"{path} type {type(before).__name__} != {type(after).__name__}"
    if isinstance(before, Mapping):
        for key in sorted(set(before) | set(after), key=str):
            child = f"{path}.{key}"
            if key not in before or key not in after:
                return f"{child} is missing on one side"
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


def _canonical_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExperimentBlocked(f"{label} path must be nonempty")
    if "\\" in value or ":" in value or value.startswith("/"):
        raise ExperimentBlocked(f"{label} path must be repository-relative POSIX")
    path = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in path.parts) or path.as_posix() != value:
        raise ExperimentBlocked(f"{label} path must be canonical")
    return value


def _validate_binding(value: object, label: str) -> dict[str, Any]:
    binding = dict(_mapping(value, label))
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    binding["path"] = _canonical_relative_path(binding["path"], label)
    if not isinstance(binding["sha256"], str) or not _SHA256_RE.fullmatch(
        binding["sha256"]
    ):
        raise ExperimentBlocked(f"{label} sha256 must be lowercase hex")
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ExperimentBlocked(f"{label} size_bytes must be positive")
    return binding


def _validate_implementation(value: object) -> dict[str, Any]:
    implementation = dict(_mapping(value, "implementation"))
    _require_keys(
        implementation, {"commit", "source_files", "source_sha256"}, "implementation"
    )
    if not isinstance(implementation["commit"], str) or not _COMMIT_RE.fullmatch(
        implementation["commit"]
    ):
        raise ExperimentBlocked("implementation commit must be lowercase git hex")
    if implementation["source_files"] != list(IMPLEMENTATION_SOURCE_FILES):
        raise ExperimentBlocked("implementation source_files mismatch")
    if not isinstance(implementation["source_sha256"], str) or not _SHA256_RE.fullmatch(
        implementation["source_sha256"]
    ):
        raise ExperimentBlocked("implementation source_sha256 must be lowercase hex")
    return implementation


def _validate_runtime(value: object) -> dict[str, Any]:
    runtime = dict(_mapping(value, "runtime"))
    _require_keys(
        runtime,
        {"executable", "platform", "python_version", "torch_version"},
        "runtime",
    )
    executable = runtime["executable"]
    if (
        not isinstance(executable, str)
        or not re.fullmatch(r"[A-Za-z]:/[A-Za-z0-9_./-]+", executable)
        or ".." in PurePosixPath(executable[2:]).parts
    ):
        raise ExperimentBlocked("runtime executable must be a canonical Windows path")
    if runtime["platform"] != "win32":
        raise ExperimentBlocked("runtime platform must be win32")
    for field in ("python_version", "torch_version"):
        if not isinstance(runtime[field], str) or not runtime[field]:
            raise ExperimentBlocked(f"runtime {field} must be nonempty")
    return runtime


def _validate_adapter_provenance(value: object) -> dict[str, Any]:
    try:
        provenance = dict(validate_provenance(value))
    except SimulatorAdapterError as exc:
        raise ExperimentBlocked(f"adapter provenance invalid: {exc}") from exc
    _require_keys(
        provenance,
        {
            "adapter_commit",
            "adapter_source_sha256",
            "build",
            "module_sha256",
            "module_size_bytes",
            "simulator_commit",
            "simulator_dirty",
            "simulator_source_file_count",
            "simulator_source_sha256",
            "submodules",
        },
        "adapter provenance",
    )
    for field in ("adapter_commit", "simulator_commit"):
        if not isinstance(provenance[field], str) or not _COMMIT_RE.fullmatch(
            provenance[field]
        ):
            raise ExperimentBlocked(f"adapter provenance {field} is invalid")
    for field in (
        "adapter_source_sha256",
        "module_sha256",
        "simulator_source_sha256",
    ):
        if not isinstance(provenance[field], str) or not _SHA256_RE.fullmatch(
            provenance[field]
        ):
            raise ExperimentBlocked(f"adapter provenance {field} is invalid")
    for field in ("module_size_bytes", "simulator_source_file_count"):
        if (
            isinstance(provenance[field], bool)
            or not isinstance(provenance[field], int)
            or provenance[field] <= 0
        ):
            raise ExperimentBlocked(f"adapter provenance {field} is invalid")
    if type(provenance["simulator_dirty"]) is not bool:
        raise ExperimentBlocked("adapter provenance simulator_dirty is invalid")

    submodules = dict(_mapping(provenance["submodules"], "adapter submodules"))
    _require_keys(submodules, {"json", "pybind11"}, "adapter submodules")
    for name, commit in submodules.items():
        if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
            raise ExperimentBlocked(f"adapter submodule {name} commit is invalid")
    provenance["submodules"] = submodules

    build = dict(_mapping(provenance["build"], "adapter build"))
    _require_keys(
        build,
        {
            "adapter_api_version",
            "baseline_policy_id",
            "compiler",
            "cpp_standard",
            "native_target_policy_id",
            "pybind11_version",
            "python",
        },
        "adapter build",
    )
    if build["adapter_api_version"] != ADAPTER_API_VERSION:
        raise ExperimentBlocked("adapter provenance must bind exact API v3")
    if build["baseline_policy_id"] != SIMULATOR_BASELINE_POLICY_ID:
        raise ExperimentBlocked("adapter baseline policy identity mismatch")
    if build["native_target_policy_id"] != NATIVE_TARGET_POLICY_ID:
        raise ExperimentBlocked("adapter native target policy identity mismatch")
    for field in ("compiler", "pybind11_version", "python"):
        if not isinstance(build[field], str) or not build[field]:
            raise ExperimentBlocked(f"adapter build {field} is invalid")
    if (
        isinstance(build["cpp_standard"], bool)
        or not isinstance(build["cpp_standard"], int)
        or build["cpp_standard"] < 201703
    ):
        raise ExperimentBlocked("adapter build cpp_standard is invalid")
    provenance["build"] = build
    return provenance


def _validate_authority(value: object, expected: Mapping[str, bool]) -> dict[str, bool]:
    authority = dict(_mapping(value, "authority"))
    if authority != dict(expected):
        difference = _first_difference(dict(expected), authority, "authority")
        raise ExperimentBlocked(f"authority mismatch: {difference}")
    return authority


def validate_registration(value: object) -> dict[str, Any]:
    """Validate the closed, all-false source-only preregistration schema."""
    registration = dict(_mapping(value, "registration"))
    _require_keys(
        registration,
        {"authority", "experiment", "identity", "schema_version"},
        "registration",
    )
    if registration["schema_version"] != EXPERIMENT_SCHEMA_VERSION:
        raise ExperimentBlocked("registration schema_version mismatch")
    registration["authority"] = _validate_authority(
        registration["authority"], registration_authority()
    )
    expected_contract = experiment_contract()
    if registration["experiment"] != expected_contract:
        difference = _first_difference(
            expected_contract, registration["experiment"], "experiment"
        )
        raise ExperimentBlocked(f"experiment contract drift: {difference}")

    identity = dict(_mapping(registration["identity"], "identity"))
    _require_keys(
        identity,
        {
            "adapter_provenance",
            "evidence",
            "implementation",
            "runtime",
            "seed_inventory",
        },
        "identity",
    )
    identity["adapter_provenance"] = _validate_adapter_provenance(
        identity["adapter_provenance"]
    )

    evidence = dict(_mapping(identity["evidence"], "evidence"))
    _require_keys(evidence, set(EVIDENCE_BINDING_NAMES), "evidence")
    identity["evidence"] = {
        name: _validate_binding(evidence[name], f"evidence.{name}")
        for name in EVIDENCE_BINDING_NAMES
    }
    identity["implementation"] = _validate_implementation(identity["implementation"])
    identity["runtime"] = _validate_runtime(identity["runtime"])
    if (
        identity["adapter_provenance"]["build"]["python"]
        != identity["runtime"]["python_version"]
    ):
        raise ExperimentBlocked("adapter and runtime Python versions differ")
    identity["seed_inventory"] = _validate_binding(
        identity["seed_inventory"], "seed_inventory"
    )
    registration["identity"] = identity
    return copy.deepcopy(registration)


def _validate_registration_binding(value: object) -> dict[str, Any]:
    binding = dict(_mapping(value, "authorization.registration"))
    _require_keys(
        binding, {"commit", "path", "sha256", "size_bytes"}, "authorization.registration"
    )
    if not isinstance(binding["commit"], str) or not _COMMIT_RE.fullmatch(
        binding["commit"]
    ):
        raise ExperimentBlocked("authorization registration commit is invalid")
    path = _canonical_relative_path(binding["path"], "authorization.registration")
    if not (
        path.startswith("reports/noncombat_simulator_rl_experiment_")
        and path.endswith("_registration.json")
    ):
        raise ExperimentBlocked("authorization registration path is outside the contract")
    if not isinstance(binding["sha256"], str) or not _SHA256_RE.fullmatch(
        binding["sha256"]
    ):
        raise ExperimentBlocked("authorization registration sha256 is invalid")
    if (
        isinstance(binding["size_bytes"], bool)
        or not isinstance(binding["size_bytes"], int)
        or binding["size_bytes"] <= 0
    ):
        raise ExperimentBlocked("authorization registration size_bytes is invalid")
    return binding


def build_execution_authorization(
    *,
    registration_binding: Mapping[str, Any],
    logical_execution_id: str,
    output_directory: str,
) -> dict[str, Any]:
    value = {
        "authority": execution_authority(),
        "logical_execution_id": logical_execution_id,
        "output_directory": output_directory,
        "registration": dict(registration_binding),
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
    }
    return _validate_authorization_shape(value)


def _validate_authorization_shape(value: object) -> dict[str, Any]:
    authorization = dict(_mapping(value, "authorization"))
    _require_keys(
        authorization,
        {
            "authority",
            "logical_execution_id",
            "output_directory",
            "registration",
            "schema_version",
        },
        "authorization",
    )
    if authorization["schema_version"] != AUTHORIZATION_SCHEMA_VERSION:
        raise ExperimentBlocked("authorization schema_version mismatch")
    authorization["authority"] = _validate_authority(
        authorization["authority"], execution_authority()
    )
    execution_id = authorization["logical_execution_id"]
    if not isinstance(execution_id, str) or not _EXECUTION_ID_RE.fullmatch(execution_id):
        raise ExperimentBlocked("logical_execution_id is invalid")
    output = _canonical_relative_path(
        authorization["output_directory"], "authorization.output_directory"
    )
    if not output.startswith("reports/noncombat_simulator_rl_experiment_"):
        raise ExperimentBlocked("output_directory is outside the registered report root")
    if "checkpoints" in PurePosixPath(output).parts:
        raise ExperimentBlocked("output_directory must remain outside live checkpoints")
    authorization["registration"] = _validate_registration_binding(
        authorization["registration"]
    )
    return copy.deepcopy(authorization)


def validate_execution_authorization(
    value: object,
    *,
    registration: Mapping[str, Any],
    registration_bytes: bytes,
) -> dict[str, Any]:
    """Validate a separate one-shot authorization against canonical registration bytes."""
    validate_registration(registration)
    if canonical_json_bytes(registration) != registration_bytes:
        raise ExperimentBlocked("registration bytes are not canonical or do not match")
    authorization = _validate_authorization_shape(value)
    binding = authorization["registration"]
    if binding["sha256"] != hashlib.sha256(registration_bytes).hexdigest():
        raise ExperimentBlocked("authorization registration sha256 mismatch")
    if binding["size_bytes"] != len(registration_bytes):
        raise ExperimentBlocked("authorization registration size_bytes mismatch")
    return authorization


def _validate_json_value(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ExperimentBlocked(f"{label} keys must be strings")
            _validate_json_value(child, f"{label}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_json_value(child, f"{label}[{index}]")
        return
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, Real):
        try:
            finite = math.isfinite(float(value))
        except (OverflowError, ValueError):
            finite = False
        if not finite:
            raise ExperimentBlocked(f"{label} numeric values must be finite")
        return
    raise ExperimentBlocked(f"{label} contains unsupported {type(value).__name__}")


def _strip_policy_leakage(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _strip_policy_leakage(value[key])
            for key in sorted(value)
            if key.casefold() not in POLICY_LEAKAGE_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [_strip_policy_leakage(item) for item in value]
    return value


def _project_validated_policy_view(
    snapshot: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    state = _mapping(snapshot["state"], "snapshot.state")
    decision_count = snapshot.get("decision_count")
    if (
        isinstance(decision_count, bool)
        or not isinstance(decision_count, int)
        or decision_count < 0
    ):
        raise ExperimentBlocked("snapshot decision_count must be nonnegative")
    return {
        "candidate": _strip_policy_leakage(candidate),
        "state": {
            "category": snapshot["category"],
            "decision_count": decision_count,
            "state": _strip_policy_leakage(state),
        },
    }


def project_policy_view_v2(
    snapshot: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    """Project one exact API v3 decision without outcome or teacher leakage."""
    _validate_json_value(snapshot, "snapshot")
    _validate_json_value(candidate, "candidate")
    before_snapshot = canonical_json_bytes(snapshot)
    before_candidate = canonical_json_bytes(candidate)
    try:
        normalized_snapshot = validate_snapshot(copy.deepcopy(snapshot))
        if normalized_snapshot["adapter_api_version"] != ADAPTER_API_VERSION:
            raise ExperimentBlocked("policy projection requires exact API v3")
        if normalized_snapshot["terminal"] is True:
            raise ExperimentBlocked("terminal snapshot cannot produce policy features")
        category = normalized_snapshot["category"]
        if category not in TARGET_CATEGORIES:
            raise ExperimentBlocked("snapshot category is not a target decision")
        normalized_candidate = validate_candidates(
            [copy.deepcopy(candidate)], category=category
        )[0]
    except SimulatorAdapterError as exc:
        raise ExperimentBlocked(str(exc)) from exc
    projected = _project_validated_policy_view(
        normalized_snapshot, normalized_candidate
    )
    if canonical_json_bytes(snapshot) != before_snapshot:
        raise ExperimentBlocked("policy projection mutated source snapshot")
    if canonical_json_bytes(candidate) != before_candidate:
        raise ExperimentBlocked("policy projection mutated source candidate")
    return projected


def candidate_feature_matrix_v2(
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    hash_dim: int = HASH_DIM,
) -> Any:
    """Encode the registered candidate set into deterministic CPU float32 rows."""
    if hash_dim != HASH_DIM:
        raise ExperimentBlocked(f"hash_dim must remain {HASH_DIM}")
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
        raise ExperimentBlocked("candidates must be a nonempty sequence")
    if not candidates:
        raise ExperimentBlocked("candidates must be nonempty")
    _validate_json_value(snapshot, "snapshot")
    _validate_json_value(candidates, "candidates")
    before_snapshot = canonical_json_bytes(snapshot)
    before_candidates = canonical_json_bytes(list(candidates))
    try:
        normalized_snapshot = validate_snapshot(copy.deepcopy(snapshot))
        if normalized_snapshot["adapter_api_version"] != ADAPTER_API_VERSION:
            raise ExperimentBlocked("policy features require exact API v3")
        if normalized_snapshot["terminal"] is True:
            raise ExperimentBlocked("terminal snapshot cannot produce policy features")
        category = normalized_snapshot["category"]
        normalized_candidates = validate_candidates(
            copy.deepcopy(list(candidates)), category=category
        )
    except SimulatorAdapterError as exc:
        raise ExperimentBlocked(str(exc)) from exc

    projected = [
        _project_validated_policy_view(normalized_snapshot, candidate)
        for candidate in normalized_candidates
    ]
    config = FeatureConfig(version=FEATURE_VERSION, hash_dim=hash_dim)
    state_features = candidate_feature_vector(
        SimpleNamespace(state=projected[0]["state"]), {}, config
    )
    empty_state = SimpleNamespace(state={})
    import torch

    result = torch.stack(
        [
            state_features
            + candidate_feature_vector(empty_state, row["candidate"], config)
            for row in projected
        ]
    )
    if not torch.isfinite(result).all().item():
        raise ExperimentBlocked("policy feature matrix must be finite")
    if canonical_json_bytes(snapshot) != before_snapshot:
        raise ExperimentBlocked("policy features mutated source snapshot")
    if canonical_json_bytes(list(candidates)) != before_candidates:
        raise ExperimentBlocked("policy features mutated source candidates")
    return result


def simulator_experiment_reward(transition: Mapping[str, Any]) -> float:
    """Compute the fixed scalar reward from the formal two-channel contract."""
    try:
        channels = reward_channels(transition)
        scalarization = validate_scalarization(
            "strict_primary_dominance", victory_weight=VICTORY_WEIGHT
        )
    except RewardContractBlocked as exc:
        raise ExperimentBlocked(str(exc)) from exc
    if scalarization["strict_dominance_proved"] is not True:
        raise ExperimentBlocked("formal reward strict dominance was not proved")
    result = float(channels["floor_progress"]) + VICTORY_WEIGHT * int(
        channels["terminal_victory"]
    )
    if not math.isfinite(result):
        raise ExperimentBlocked("experiment reward must be finite")
    return result


@dataclass
class TrainingRuntime:
    """Mutable in-memory state for one authorized logical execution."""

    model: Any
    optimizer: Any
    action_generator: Any
    python_random: random.Random
    next_chunk_index: int = 0
    completed_episodes: int = 0
    optimizer_updates: int = 0
    cumulative_wall_seconds: float = 0.0


@dataclass(frozen=True)
class _EpisodeRollout:
    summary: dict[str, Any]
    log_probabilities: tuple[Any, ...]
    rewards: tuple[float, ...]


def _torch_module():
    import torch

    return torch


def initialize_training_runtime() -> TrainingRuntime:
    """Create the only registered model, optimizer, and random generators."""
    torch = _torch_module()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(MODEL_SEED)
    torch.manual_seed(MODEL_SEED)
    model = CandidateRanker(input_dim=HASH_DIM)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    action_generator = torch.Generator(device="cpu")
    action_generator.manual_seed(MODEL_SEED)
    runtime = TrainingRuntime(
        model=model,
        optimizer=optimizer,
        action_generator=action_generator,
        python_random=random.Random(MODEL_SEED),
    )
    _validate_training_runtime(runtime)
    return runtime


def registered_chunk_coordinates(chunk_index: int) -> dict[str, Any]:
    """Return the unique registered pass and seed coordinates for one chunk."""
    if (
        isinstance(chunk_index, bool)
        or not isinstance(chunk_index, int)
        or not 0 <= chunk_index < TRAINING_CHUNKS
    ):
        raise ExperimentBlocked(
            f"chunk_index must be an integer from 0 through {TRAINING_CHUNKS - 1}"
        )
    chunks_per_pass = len(TRAIN_SEEDS) // CHECKPOINT_INTERVAL_EPISODES
    pass_index = chunk_index // chunks_per_pass
    chunk_in_pass = chunk_index % chunks_per_pass
    seed_start = chunk_in_pass * CHECKPOINT_INTERVAL_EPISODES
    seeds = TRAIN_SEEDS[seed_start : seed_start + CHECKPOINT_INTERVAL_EPISODES]
    episode_start = chunk_index * CHECKPOINT_INTERVAL_EPISODES
    return {
        "chunk_index": chunk_index,
        "episode_end": episode_start + CHECKPOINT_INTERVAL_EPISODES,
        "episode_start": episode_start,
        "pass_index": pass_index,
        "seeds": seeds,
    }


def _ensure_finite_tensor(value: Any, label: str) -> None:
    torch = _torch_module()
    if not torch.is_tensor(value) or not torch.isfinite(value).all().item():
        raise ExperimentBlocked(f"non-finite {label}")


def _ensure_finite_tree(value: Any, label: str) -> None:
    torch = _torch_module()
    if torch.is_tensor(value):
        _ensure_finite_tensor(value, label)
        if value.device.type != "cpu":
            raise ExperimentBlocked(f"{label} must remain on CPU")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            _ensure_finite_tree(child, f"{label}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _ensure_finite_tree(child, f"{label}[{index}]")
        return
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, Real) and not math.isfinite(float(value)):
        raise ExperimentBlocked(f"non-finite {label}")


def _validate_training_runtime(runtime: TrainingRuntime) -> None:
    torch = _torch_module()
    if not isinstance(runtime.model, CandidateRanker):
        raise ExperimentBlocked("training model must be CandidateRanker")
    if runtime.model.scorer.in_features != HASH_DIM:
        raise ExperimentBlocked(f"training model input dimension must remain {HASH_DIM}")
    for name, parameter in runtime.model.named_parameters():
        if parameter.device.type != "cpu":
            raise ExperimentBlocked(f"model tensor {name} must remain on CPU")
        _ensure_finite_tensor(parameter, f"model tensor {name}")
    if not isinstance(runtime.optimizer, torch.optim.Adam):
        raise ExperimentBlocked("optimizer must remain Adam")
    if len(runtime.optimizer.param_groups) != 1:
        raise ExperimentBlocked("optimizer must have one parameter group")
    if runtime.optimizer.param_groups[0].get("lr") != LEARNING_RATE:
        raise ExperimentBlocked(
            f"optimizer learning rate must remain {LEARNING_RATE}"
        )
    _ensure_finite_tree(runtime.optimizer.state_dict(), "optimizer state")
    if str(runtime.action_generator.device) != "cpu":
        raise ExperimentBlocked("action generator must remain on CPU")
    for label, value in (
        ("next_chunk_index", runtime.next_chunk_index),
        ("completed_episodes", runtime.completed_episodes),
        ("optimizer_updates", runtime.optimizer_updates),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ExperimentBlocked(f"runtime {label} must be nonnegative")
    if runtime.next_chunk_index != runtime.optimizer_updates:
        raise ExperimentBlocked("runtime chunk and optimizer coordinates differ")
    if runtime.completed_episodes != (
        runtime.next_chunk_index * CHECKPOINT_INTERVAL_EPISODES
    ):
        raise ExperimentBlocked("runtime episode coordinate mismatch")
    if not math.isfinite(runtime.cumulative_wall_seconds) or not (
        0.0 <= runtime.cumulative_wall_seconds <= MAX_WALL_SECONDS
    ):
        raise ExperimentBlocked("runtime cumulative wall time is invalid")


def _exact_v3_snapshot(value: object, label: str) -> dict[str, Any]:
    _validate_json_value(value, label)
    try:
        snapshot = validate_snapshot(copy.deepcopy(value))
    except SimulatorAdapterError as exc:
        raise ExperimentBlocked(f"{label} invalid: {exc}") from exc
    if snapshot["adapter_api_version"] != ADAPTER_API_VERSION:
        raise ExperimentBlocked(f"{label} must use exact API v3")
    return snapshot


def _finite_floor(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ExperimentBlocked(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise ExperimentBlocked(f"{label} must be finite")
    return result


def _returns_to_go(rewards: Sequence[float]) -> tuple[float, ...]:
    result = [0.0] * len(rewards)
    running = 0.0
    for index in range(len(rewards) - 1, -1, -1):
        reward = float(rewards[index])
        if not math.isfinite(reward):
            raise ExperimentBlocked("training reward must be finite")
        running = reward + DISCOUNT * running
        result[index] = running
    return tuple(result)


def _check_deadline(deadline: float, clock: Callable[[], float]) -> None:
    current = float(clock())
    if not math.isfinite(current):
        raise ExperimentBlocked("wall clock must be finite")
    if current > deadline:
        raise ExperimentBlocked("cumulative wall-time bound exceeded")


def _episode_summary(
    *,
    seed: int,
    categories: set[str],
    action_rows: Sequence[Mapping[str, Any]],
    rewards: Sequence[float],
    outcome: str | None,
    terminal_floor: float | None,
    last_supported_floor: float,
    unsupported_reason: str | None,
) -> dict[str, Any]:
    return {
        "action_sequence_sha256": hashlib.sha256(
            canonical_json_bytes(list(action_rows))
        ).hexdigest(),
        "candidate_legality": True,
        "categories": sorted(categories),
        "decisions": len(action_rows),
        "last_supported_floor": last_supported_floor,
        "outcome": outcome,
        "policy_input_sha256s": [
            str(row["policy_input_sha256"]) for row in action_rows
        ],
        "retained": True,
        "seed": seed,
        "selected_action_ids": [str(row["action_id"]) for row in action_rows],
        "terminal_floor": terminal_floor,
        "total_reward": sum(float(value) for value in rewards),
        "unsupported_reason": unsupported_reason,
        "victory": outcome == "player_victory",
    }


def _rollout_episode(
    model: Any,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    training: bool,
    action_generator: Any | None,
    deadline: float,
    clock: Callable[[], float],
) -> _EpisodeRollout:
    torch = _torch_module()
    try:
        environment = environment_factory(seed)
    except Exception as exc:
        raise ExperimentBlocked(f"seed {seed} environment construction failed: {exc}") from exc
    categories: set[str] = set()
    action_rows: list[dict[str, Any]] = []
    rewards: list[float] = []
    log_probabilities: list[Any] = []

    while True:
        _check_deadline(deadline, clock)
        try:
            snapshot = _exact_v3_snapshot(environment.snapshot(), "environment snapshot")
        except Exception as exc:
            if isinstance(exc, ExperimentBlocked):
                raise
            raise ExperimentBlocked(f"seed {seed} snapshot failed: {exc}") from exc
        if snapshot["terminal"] is True:
            break
        if len(action_rows) >= MAX_DECISIONS_PER_EPISODE:
            raise ExperimentBlocked(
                f"seed {seed} exceeded max_decisions_per_episode={MAX_DECISIONS_PER_EPISODE}"
            )
        category = snapshot["category"]
        if category not in TARGET_CATEGORIES:
            raise ExperimentBlocked(f"seed {seed} stopped outside a target category")
        categories.add(str(category))
        source_floor = _finite_floor(snapshot["state"].get("floor"), "source floor")
        try:
            raw_candidates = environment.legal_actions()
        except Exception as exc:
            raise ExperimentBlocked(f"seed {seed} candidate query failed: {exc}") from exc
        features = candidate_feature_matrix_v2(snapshot, raw_candidates)
        try:
            candidates = validate_candidates(
                copy.deepcopy(list(raw_candidates)), category=category
            )
        except SimulatorAdapterError as exc:
            raise ExperimentBlocked(str(exc)) from exc
        projected = [
            project_policy_view_v2(snapshot, candidate) for candidate in candidates
        ]
        policy_input_sha256 = hashlib.sha256(
            canonical_json_bytes(
                {
                    "candidates": [row["candidate"] for row in projected],
                    "state": projected[0]["state"],
                }
            )
        ).hexdigest()
        original_snapshot = canonical_json_bytes(snapshot)
        original_candidates = canonical_json_bytes(candidates)
        try:
            branch = environment.clone()
            branch_snapshot = _exact_v3_snapshot(
                branch.snapshot(), "cloned environment snapshot"
            )
            branch_candidates = validate_candidates(
                copy.deepcopy(list(branch.legal_actions())), category=category
            )
        except (SimulatorAdapterError, ExperimentBlocked) as exc:
            raise ExperimentBlocked(f"seed {seed} clone validation failed: {exc}") from exc
        except Exception as exc:
            raise ExperimentBlocked(f"seed {seed} clone failed: {exc}") from exc
        if canonical_json_bytes(branch_snapshot) != original_snapshot:
            raise ExperimentBlocked("clone snapshot differs before action")
        if canonical_json_bytes(branch_candidates) != original_candidates:
            raise ExperimentBlocked("clone candidate set differs before action")

        logits = model(features)
        _ensure_finite_tensor(logits, "policy logits")
        if training:
            if action_generator is None:
                raise ExperimentBlocked("training action generator is required")
            probabilities = torch.softmax(logits.detach(), dim=0)
            _ensure_finite_tensor(probabilities, "policy probabilities")
            selected_index = int(
                torch.multinomial(probabilities, 1, generator=action_generator).item()
            )
            log_probability = torch.log_softmax(logits, dim=0)[selected_index]
            _ensure_finite_tensor(log_probability, "selected log probability")
            log_probabilities.append(log_probability)
        else:
            selected_index = int(torch.argmax(logits.detach()).item())
        action_id = str(candidates[selected_index]["action_id"])
        action_row = {
            "action_id": action_id,
            "category": category,
            "decision": len(action_rows),
            "policy_input_sha256": policy_input_sha256,
        }
        try:
            transition = branch.step(action_id)
        except RuntimeError as exc:
            reason = str(exc)
            if reason not in REGISTERED_SUPPORT_BLOCKERS:
                raise ExperimentBlocked(
                    f"seed {seed} reached unregistered blocker: {reason}"
                ) from exc
            source_after = _exact_v3_snapshot(
                environment.snapshot(), "source snapshot after blocker"
            )
            if canonical_json_bytes(source_after) != original_snapshot:
                raise ExperimentBlocked("selected clone action mutated the source branch")
            rewards.append(0.0)
            action_rows.append({**action_row, "reward": 0.0})
            return _EpisodeRollout(
                summary=_episode_summary(
                    seed=seed,
                    categories=categories,
                    action_rows=action_rows,
                    rewards=rewards,
                    outcome=None,
                    terminal_floor=None,
                    last_supported_floor=source_floor,
                    unsupported_reason=reason,
                ),
                log_probabilities=tuple(log_probabilities),
                rewards=tuple(rewards),
            )
        except Exception as exc:
            raise ExperimentBlocked(
                f"seed {seed} candidate rejected on fresh clone: {action_id}: {exc}"
            ) from exc
        source_after = _exact_v3_snapshot(
            environment.snapshot(), "source snapshot after clone action"
        )
        if canonical_json_bytes(source_after) != original_snapshot:
            raise ExperimentBlocked("selected clone action mutated the source branch")
        reward = simulator_experiment_reward(_mapping(transition, "transition"))
        rewards.append(reward)
        action_rows.append({**action_row, "reward": reward})
        environment = branch

    if not action_rows:
        raise ExperimentBlocked(f"seed {seed} produced no policy decisions")
    terminal_state = _mapping(snapshot["state"], "terminal snapshot.state")
    outcome = terminal_state.get("outcome")
    if outcome not in {"player_loss", "player_victory"}:
        raise ExperimentBlocked(f"seed {seed} did not produce a terminal outcome")
    terminal_floor = _finite_floor(terminal_state.get("floor"), "terminal floor")
    return _EpisodeRollout(
        summary=_episode_summary(
            seed=seed,
            categories=categories,
            action_rows=action_rows,
            rewards=rewards,
            outcome=str(outcome),
            terminal_floor=terminal_floor,
            last_supported_floor=terminal_floor,
            unsupported_reason=None,
        ),
        log_probabilities=tuple(log_probabilities),
        rewards=tuple(rewards),
    )


def _runtime_snapshot(runtime: TrainingRuntime) -> dict[str, Any]:
    return {
        "action_generator": runtime.action_generator.get_state().clone(),
        "model": copy.deepcopy(runtime.model.state_dict()),
        "optimizer": copy.deepcopy(runtime.optimizer.state_dict()),
        "python_random": runtime.python_random.getstate(),
    }


def _restore_runtime(runtime: TrainingRuntime, snapshot: Mapping[str, Any]) -> None:
    runtime.model.load_state_dict(snapshot["model"])
    runtime.optimizer.load_state_dict(snapshot["optimizer"])
    runtime.action_generator.set_state(snapshot["action_generator"])
    runtime.python_random.setstate(snapshot["python_random"])
    runtime.optimizer.zero_grad(set_to_none=True)


def run_registered_training_chunk(
    runtime: TrainingRuntime,
    *,
    environment_factory: Callable[[int], Any],
    chunk_index: int | None = None,
    seed_override: Sequence[int] | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Run exactly one registered 64-episode REINFORCE optimizer update."""
    _validate_training_runtime(runtime)
    selected_chunk = runtime.next_chunk_index if chunk_index is None else chunk_index
    if selected_chunk != runtime.next_chunk_index:
        raise ExperimentBlocked(
            f"requested chunk is not the unique next chunk {runtime.next_chunk_index}"
        )
    coordinates = registered_chunk_coordinates(selected_chunk)
    seeds = tuple(coordinates["seeds"] if seed_override is None else seed_override)
    if len(seeds) != CHECKPOINT_INTERVAL_EPISODES:
        raise ExperimentBlocked(
            f"training chunk must retain exactly {CHECKPOINT_INTERVAL_EPISODES} episodes"
        )
    if seeds != coordinates["seeds"]:
        raise ExperimentBlocked("training chunk seeds differ from registered coordinates")
    remaining = MAX_WALL_SECONDS - runtime.cumulative_wall_seconds
    if remaining <= 0.0:
        raise ExperimentBlocked("cumulative wall-time bound exceeded")
    started = float(clock())
    if not math.isfinite(started):
        raise ExperimentBlocked("wall clock must be finite")
    deadline = started + remaining
    rollback = _runtime_snapshot(runtime)
    torch = _torch_module()

    try:
        runtime.model.train()
        runtime.optimizer.zero_grad(set_to_none=True)
        episode_rows: list[dict[str, Any]] = []
        log_probabilities: list[Any] = []
        returns: list[float] = []
        for seed in seeds:
            rollout = _rollout_episode(
                runtime.model,
                environment_factory=environment_factory,
                seed=int(seed),
                training=True,
                action_generator=runtime.action_generator,
                deadline=deadline,
                clock=clock,
            )
            row = dict(rollout.summary)
            row["chunk_index"] = selected_chunk
            row["pass_index"] = coordinates["pass_index"]
            episode_rows.append(row)
            log_probabilities.extend(rollout.log_probabilities)
            returns.extend(_returns_to_go(rollout.rewards))
        if len(episode_rows) != CHECKPOINT_INTERVAL_EPISODES:
            raise ExperimentBlocked("training chunk episode denominator drifted")
        if not log_probabilities or len(log_probabilities) != len(returns):
            raise ExperimentBlocked("training chunk produced no aligned policy decisions")
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
        for name, parameter in runtime.model.named_parameters():
            if parameter.grad is None:
                raise ExperimentBlocked(f"missing gradient for {name}")
            _ensure_finite_tensor(parameter.grad, f"gradient {name}")
        _check_deadline(deadline, clock)
        runtime.optimizer.step()
        for name, parameter in runtime.model.named_parameters():
            _ensure_finite_tensor(parameter, f"model tensor {name}")
        _ensure_finite_tree(runtime.optimizer.state_dict(), "optimizer state")
        finished = float(clock())
        if not math.isfinite(finished) or finished < started:
            raise ExperimentBlocked("wall clock moved backwards or became non-finite")
        elapsed = finished - started
        if runtime.cumulative_wall_seconds + elapsed > MAX_WALL_SECONDS:
            raise ExperimentBlocked("cumulative wall-time bound exceeded")
    except BaseException:
        _restore_runtime(runtime, rollback)
        raise

    runtime.next_chunk_index += 1
    runtime.completed_episodes += CHECKPOINT_INTERVAL_EPISODES
    runtime.optimizer_updates += 1
    runtime.cumulative_wall_seconds += elapsed
    _validate_training_runtime(runtime)
    categories = sorted(
        {category for row in episode_rows for category in row["categories"]}
    )
    return {
        "candidate_legality": all(row["candidate_legality"] for row in episode_rows),
        "categories": categories,
        "chunk_index": selected_chunk,
        "episode_rows": episode_rows,
        "episodes": len(episode_rows),
        "loss": float(loss.item()),
        "mean_episode_return": sum(row["total_reward"] for row in episode_rows)
        / len(episode_rows),
        "optimizer_update": runtime.optimizer_updates,
        "pass_index": coordinates["pass_index"],
        "unsupported_episodes": sum(
            row["unsupported_reason"] is not None for row in episode_rows
        ),
        "victories": sum(row["victory"] for row in episode_rows),
    }


_TORCH_DTYPE_NAMES = {
    "bool": "bool",
    "float32": "float32",
    "float64": "float64",
    "int32": "int32",
    "int64": "int64",
    "uint8": "uint8",
}
_TORCH_DTYPE_SIZES = {
    "bool": 1,
    "float32": 4,
    "float64": 8,
    "int32": 4,
    "int64": 8,
    "uint8": 1,
}


def encode_tensor(tensor: Any) -> dict[str, Any]:
    """Encode one finite CPU tensor with explicit little-endian bytes."""
    torch = _torch_module()
    if not torch.is_tensor(tensor):
        raise ExperimentBlocked("tensor codec requires a tensor")
    value = tensor.detach().to(device="cpu").contiguous()
    dtype = str(value.dtype).removeprefix("torch.")
    if dtype not in _TORCH_DTYPE_NAMES:
        raise ExperimentBlocked(f"unsupported tensor dtype: {dtype}")
    if value.is_floating_point():
        _ensure_finite_tensor(value, "encoded tensor")
    if sys.byteorder != "little":
        raise ExperimentBlocked("tensor codec requires a little-endian runtime")
    try:
        data = value.numpy().tobytes(order="C")
    except (TypeError, RuntimeError) as exc:
        raise ExperimentBlocked(f"tensor byte encoding failed: {exc}") from exc
    return {
        "byte_order": "little",
        "data_base64": base64.b64encode(data).decode("ascii"),
        "data_sha256": hashlib.sha256(data).hexdigest(),
        "dtype": dtype,
        "shape": list(value.shape),
    }


def decode_tensor(value: object, label: str) -> Any:
    """Validate and decode one canonical tensor payload onto CPU."""
    torch = _torch_module()
    payload = dict(_mapping(value, label))
    _require_keys(
        payload,
        {"byte_order", "data_base64", "data_sha256", "dtype", "shape"},
        label,
    )
    if payload["byte_order"] != "little":
        raise ExperimentBlocked(f"{label} byte_order must be little")
    dtype_name = payload["dtype"]
    if dtype_name not in _TORCH_DTYPE_NAMES:
        raise ExperimentBlocked(f"{label} dtype is unsupported")
    shape = payload["shape"]
    if not isinstance(shape, list) or any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0
        for item in shape
    ):
        raise ExperimentBlocked(f"{label} shape is invalid")
    try:
        data = base64.b64decode(payload["data_base64"], validate=True)
    except (TypeError, ValueError) as exc:
        raise ExperimentBlocked(f"{label} data_base64 is invalid base64") from exc
    digest = payload["data_sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ExperimentBlocked(f"{label} data_sha256 is invalid")
    if hashlib.sha256(data).hexdigest() != digest:
        raise ExperimentBlocked(f"{label} data_sha256 mismatch")
    elements = math.prod(shape) if shape else 1
    expected_bytes = elements * _TORCH_DTYPE_SIZES[dtype_name]
    if len(data) != expected_bytes:
        raise ExperimentBlocked(
            f"{label} byte length mismatch: {len(data)} != {expected_bytes}"
        )
    dtype = getattr(torch, _TORCH_DTYPE_NAMES[dtype_name])
    try:
        tensor = torch.frombuffer(bytearray(data), dtype=dtype).clone().reshape(shape)
    except (RuntimeError, ValueError) as exc:
        raise ExperimentBlocked(f"{label} tensor decode failed: {exc}") from exc
    if tensor.is_floating_point():
        _ensure_finite_tensor(tensor, label)
    return tensor


def _encode_state_value(value: Any) -> dict[str, Any]:
    torch = _torch_module()
    if torch.is_tensor(value):
        return {"kind": "tensor", "value": encode_tensor(value)}
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ExperimentBlocked("checkpoint mapping keys must be strings")
        return {
            "items": [
                {"key": key, "value": _encode_state_value(value[key])}
                for key in sorted(value)
            ],
            "kind": "mapping",
        }
    if isinstance(value, tuple):
        return {
            "items": [_encode_state_value(item) for item in value],
            "kind": "tuple",
        }
    if isinstance(value, list):
        return {
            "items": [_encode_state_value(item) for item in value],
            "kind": "list",
        }
    if value is None or isinstance(value, (bool, int, str)):
        return {"kind": "scalar", "value": value}
    if isinstance(value, Real):
        number = float(value)
        if not math.isfinite(number):
            raise ExperimentBlocked("checkpoint scalar must be finite")
        return {"kind": "scalar", "value": number}
    raise ExperimentBlocked(
        f"unsupported checkpoint state value: {type(value).__name__}"
    )


def _decode_state_value(value: object, label: str) -> Any:
    payload = dict(_mapping(value, label))
    kind = payload.get("kind")
    if kind == "tensor":
        _require_keys(payload, {"kind", "value"}, label)
        return decode_tensor(payload["value"], f"{label}.value")
    if kind == "mapping":
        _require_keys(payload, {"items", "kind"}, label)
        items = payload["items"]
        if not isinstance(items, list):
            raise ExperimentBlocked(f"{label}.items must be a list")
        result: dict[str, Any] = {}
        previous: str | None = None
        for index, raw in enumerate(items):
            item = dict(_mapping(raw, f"{label}.items[{index}]"))
            _require_keys(item, {"key", "value"}, f"{label}.items[{index}]")
            key = item["key"]
            if not isinstance(key, str) or not key:
                raise ExperimentBlocked(f"{label} mapping key is invalid")
            if previous is not None and key <= previous:
                raise ExperimentBlocked(f"{label} mapping keys are not canonical")
            previous = key
            result[key] = _decode_state_value(
                item["value"], f"{label}.{key}"
            )
        return result
    if kind in {"tuple", "list"}:
        _require_keys(payload, {"items", "kind"}, label)
        if not isinstance(payload["items"], list):
            raise ExperimentBlocked(f"{label}.items must be a list")
        items = [
            _decode_state_value(item, f"{label}[{index}]")
            for index, item in enumerate(payload["items"])
        ]
        return tuple(items) if kind == "tuple" else items
    if kind == "scalar":
        _require_keys(payload, {"kind", "value"}, label)
        scalar = payload["value"]
        _validate_json_value(scalar, label)
        if isinstance(scalar, (Mapping, list, tuple)):
            raise ExperimentBlocked(f"{label} scalar is not scalar")
        return scalar
    raise ExperimentBlocked(f"{label} kind is unsupported")


def _encode_optimizer_state(optimizer: Any) -> dict[str, Any]:
    state = optimizer.state_dict()
    rows = []
    for parameter_id in sorted(state["state"]):
        if isinstance(parameter_id, bool) or not isinstance(parameter_id, int):
            raise ExperimentBlocked("optimizer parameter id must be an integer")
        rows.append(
            {
                "parameter_id": parameter_id,
                "state": _encode_state_value(state["state"][parameter_id]),
            }
        )
    return {
        "param_groups": _encode_state_value(state["param_groups"]),
        "state": rows,
    }


def _decode_optimizer_state(value: object) -> dict[str, Any]:
    payload = dict(_mapping(value, "optimizer"))
    _require_keys(payload, {"param_groups", "state"}, "optimizer")
    state_rows = payload["state"]
    if not isinstance(state_rows, list):
        raise ExperimentBlocked("optimizer.state must be a list")
    state: dict[int, Any] = {}
    previous = -1
    for index, raw in enumerate(state_rows):
        row = dict(_mapping(raw, f"optimizer.state[{index}]"))
        _require_keys(
            row, {"parameter_id", "state"}, f"optimizer.state[{index}]"
        )
        parameter_id = row["parameter_id"]
        if (
            isinstance(parameter_id, bool)
            or not isinstance(parameter_id, int)
            or parameter_id <= previous
        ):
            raise ExperimentBlocked("optimizer parameter ids are not canonical")
        previous = parameter_id
        state[parameter_id] = _decode_state_value(
            row["state"], f"optimizer.state[{parameter_id}]"
        )
    param_groups = _decode_state_value(
        payload["param_groups"], "optimizer.param_groups"
    )
    if not isinstance(param_groups, list):
        raise ExperimentBlocked("optimizer.param_groups must decode to a list")
    return {"param_groups": param_groups, "state": state}


def _validate_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ExperimentBlocked(f"{label} must be lowercase sha256")
    return value


def _validate_commit(value: object, label: str) -> str:
    if not isinstance(value, str) or not _COMMIT_RE.fullmatch(value):
        raise ExperimentBlocked(f"{label} must be lowercase git commit hex")
    return value


def _validate_execution_id(value: object) -> str:
    if not isinstance(value, str) or not _EXECUTION_ID_RE.fullmatch(value):
        raise ExperimentBlocked("logical_execution_id is invalid")
    return value


def _next_coordinate(runtime: TrainingRuntime) -> dict[str, Any]:
    if runtime.next_chunk_index == TRAINING_CHUNKS:
        return {"phase": "canary"}
    coordinates = registered_chunk_coordinates(runtime.next_chunk_index)
    return {
        "chunk_index": coordinates["chunk_index"],
        "episode_start": coordinates["episode_start"],
        "pass_index": coordinates["pass_index"],
        "phase": "training",
        "seed_end": coordinates["seeds"][-1],
        "seed_start": coordinates["seeds"][0],
    }


def build_checkpoint_state_payload(
    runtime: TrainingRuntime,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> dict[str, Any]:
    """Build the deterministic replay target, excluding measured wall time."""
    _validate_training_runtime(runtime)
    registration_sha256 = _validate_sha256(
        registration_sha256, "registration_sha256"
    )
    implementation_commit = _validate_commit(
        implementation_commit, "implementation_commit"
    )
    logical_execution_id = _validate_execution_id(logical_execution_id)
    torch = _torch_module()
    model_state = {
        name: encode_tensor(tensor)
        for name, tensor in sorted(runtime.model.state_dict().items())
    }
    return {
        "coordinate": {
            "completed_episodes": runtime.completed_episodes,
            "next": _next_coordinate(runtime),
            "next_chunk_index": runtime.next_chunk_index,
            "optimizer_updates": runtime.optimizer_updates,
        },
        "identity": {
            "implementation_commit": implementation_commit,
            "logical_execution_id": logical_execution_id,
            "registration_sha256": registration_sha256,
        },
        "model": {
            "architecture": "candidate-ranker-linear-v1",
            "input_dim": HASH_DIM,
            "state_dict": model_state,
        },
        "optimizer": _encode_optimizer_state(runtime.optimizer),
        "random": {
            "action_generator": encode_tensor(
                runtime.action_generator.get_state()
            ),
            "python": _encode_state_value(runtime.python_random.getstate()),
            "torch_global": encode_tensor(torch.get_rng_state()),
        },
        "schema_version": CHECKPOINT_STATE_SCHEMA_VERSION,
    }


def _validate_checkpoint_state_payload(
    value: object,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> dict[str, Any]:
    payload = dict(_mapping(value, "checkpoint state payload"))
    _require_keys(
        payload,
        {"coordinate", "identity", "model", "optimizer", "random", "schema_version"},
        "checkpoint state payload",
    )
    if payload["schema_version"] != CHECKPOINT_STATE_SCHEMA_VERSION:
        raise ExperimentBlocked("checkpoint state schema_version mismatch")
    identity = dict(_mapping(payload["identity"], "checkpoint identity"))
    _require_keys(
        identity,
        {"implementation_commit", "logical_execution_id", "registration_sha256"},
        "checkpoint identity",
    )
    if identity != {
        "implementation_commit": implementation_commit,
        "logical_execution_id": logical_execution_id,
        "registration_sha256": registration_sha256,
    }:
        raise ExperimentBlocked("checkpoint state identity mismatch")
    coordinate = dict(_mapping(payload["coordinate"], "checkpoint coordinate"))
    _require_keys(
        coordinate,
        {"completed_episodes", "next", "next_chunk_index", "optimizer_updates"},
        "checkpoint coordinate",
    )
    next_chunk = coordinate["next_chunk_index"]
    if (
        isinstance(next_chunk, bool)
        or not isinstance(next_chunk, int)
        or not 0 <= next_chunk <= TRAINING_CHUNKS
    ):
        raise ExperimentBlocked("checkpoint next_chunk_index is invalid")
    if coordinate["optimizer_updates"] != next_chunk:
        raise ExperimentBlocked("checkpoint optimizer coordinate mismatch")
    if coordinate["completed_episodes"] != (
        next_chunk * CHECKPOINT_INTERVAL_EPISODES
    ):
        raise ExperimentBlocked("checkpoint episode coordinate mismatch")
    expected_next = (
        {"phase": "canary"}
        if next_chunk == TRAINING_CHUNKS
        else {
            "chunk_index": registered_chunk_coordinates(next_chunk)["chunk_index"],
            "episode_start": registered_chunk_coordinates(next_chunk)["episode_start"],
            "pass_index": registered_chunk_coordinates(next_chunk)["pass_index"],
            "phase": "training",
            "seed_end": registered_chunk_coordinates(next_chunk)["seeds"][-1],
            "seed_start": registered_chunk_coordinates(next_chunk)["seeds"][0],
        }
    )
    if coordinate["next"] != expected_next:
        raise ExperimentBlocked("checkpoint next coordinate mismatch")
    model = dict(_mapping(payload["model"], "checkpoint model"))
    _require_keys(model, {"architecture", "input_dim", "state_dict"}, "checkpoint model")
    if model["architecture"] != "candidate-ranker-linear-v1" or model["input_dim"] != HASH_DIM:
        raise ExperimentBlocked("checkpoint model contract mismatch")
    state_dict = dict(_mapping(model["state_dict"], "checkpoint model.state_dict"))
    if set(state_dict) != {"scorer.bias", "scorer.weight"}:
        raise ExperimentBlocked("checkpoint model state_dict fields mismatch")
    for name, tensor in state_dict.items():
        decode_tensor(tensor, f"checkpoint model.{name}")
    _decode_optimizer_state(payload["optimizer"])
    random_payload = dict(_mapping(payload["random"], "checkpoint random"))
    _require_keys(
        random_payload,
        {"action_generator", "python", "torch_global"},
        "checkpoint random",
    )
    decode_tensor(random_payload["action_generator"], "checkpoint action generator")
    python_state = _decode_state_value(random_payload["python"], "checkpoint python random")
    if not isinstance(python_state, tuple) or len(python_state) != 3:
        raise ExperimentBlocked("checkpoint Python random state is invalid")
    decode_tensor(random_payload["torch_global"], "checkpoint torch global RNG")
    return copy.deepcopy(payload)


def build_checkpoint_envelope(
    runtime: TrainingRuntime,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
    previous_checkpoint_bytes: bytes | None,
) -> dict[str, Any]:
    """Build one canonical chain envelope around deterministic runtime state."""
    _validate_training_runtime(runtime)
    state_payload = build_checkpoint_state_payload(
        runtime,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    previous_sha256 = (
        None
        if previous_checkpoint_bytes is None
        else hashlib.sha256(previous_checkpoint_bytes).hexdigest()
    )
    if runtime.next_chunk_index <= 1 and previous_sha256 is not None:
        raise ExperimentBlocked("first checkpoint cannot have a previous checkpoint")
    if runtime.next_chunk_index > 1 and previous_sha256 is None:
        raise ExperimentBlocked("checkpoint chain requires previous checkpoint bytes")
    state_bytes = canonical_json_bytes(state_payload)
    return {
        "checkpoint_index": runtime.next_chunk_index,
        "cumulative_wall_seconds": runtime.cumulative_wall_seconds,
        "logical_execution_id": logical_execution_id,
        "previous_checkpoint_sha256": previous_sha256,
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "state_payload": state_payload,
        "state_payload_sha256": hashlib.sha256(state_bytes).hexdigest(),
    }


def _validate_checkpoint_envelope(
    value: object,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
    previous_checkpoint_bytes: bytes | None,
) -> dict[str, Any]:
    envelope = dict(_mapping(value, "checkpoint"))
    _require_keys(
        envelope,
        {
            "checkpoint_index",
            "cumulative_wall_seconds",
            "logical_execution_id",
            "previous_checkpoint_sha256",
            "schema_version",
            "state_payload",
            "state_payload_sha256",
        },
        "checkpoint",
    )
    if envelope["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise ExperimentBlocked("checkpoint schema_version mismatch")
    if envelope["logical_execution_id"] != logical_execution_id:
        raise ExperimentBlocked("checkpoint logical execution id mismatch")
    payload = _validate_checkpoint_state_payload(
        envelope["state_payload"],
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    index = envelope["checkpoint_index"]
    if index != payload["coordinate"]["next_chunk_index"]:
        raise ExperimentBlocked("checkpoint index and state coordinate differ")
    state_digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    if envelope["state_payload_sha256"] != state_digest:
        raise ExperimentBlocked("checkpoint state_payload_sha256 mismatch")
    elapsed = envelope["cumulative_wall_seconds"]
    if (
        isinstance(elapsed, bool)
        or not isinstance(elapsed, Real)
        or not math.isfinite(float(elapsed))
        or not 0.0 <= float(elapsed) <= MAX_WALL_SECONDS
    ):
        raise ExperimentBlocked("checkpoint cumulative wall time is invalid")
    expected_previous = (
        None
        if previous_checkpoint_bytes is None
        else hashlib.sha256(previous_checkpoint_bytes).hexdigest()
    )
    if envelope["previous_checkpoint_sha256"] != expected_previous:
        raise ExperimentBlocked("checkpoint previous_checkpoint_sha256 mismatch")
    return copy.deepcopy(envelope)


def _atomic_write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ExperimentBlocked(f"refusing to replace existing artifact: {path.name}")
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise ExperimentBlocked(f"partial artifact already exists: {temporary.name}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise ExperimentBlocked(f"artifact appeared concurrently: {path.name}")
        os.replace(temporary, path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise


def publish_checkpoint(output_dir: Path | str, envelope: Mapping[str, Any]) -> Path:
    output = Path(output_dir)
    index = envelope.get("checkpoint_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index <= TRAINING_CHUNKS:
        raise ExperimentBlocked("published checkpoint index is invalid")
    path = output / "checkpoints" / f"checkpoint_{index:04d}.json"
    _atomic_write_once(path, canonical_json_bytes(dict(envelope)))
    return path


def publish_training_chunk_summary(
    output_dir: Path | str,
    summary: Mapping[str, Any],
    *,
    checkpoint_bytes: bytes,
) -> Path:
    """Publish one retained trajectory summary bound to its checkpoint bytes."""
    artifact = _build_training_chunk_artifact(
        summary, checkpoint_bytes=checkpoint_bytes
    )
    index = artifact["summary"]["chunk_index"]
    path = Path(output_dir) / "training" / f"chunk_{index:04d}.json"
    _atomic_write_once(path, canonical_json_bytes(artifact))
    return path


def _build_training_chunk_artifact(
    summary: Mapping[str, Any], *, checkpoint_bytes: bytes
) -> dict[str, Any]:
    value = copy.deepcopy(dict(summary))
    index = value.get("chunk_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < TRAINING_CHUNKS:
        raise ExperimentBlocked("training summary chunk_index is invalid")
    if value.get("episodes") != CHECKPOINT_INTERVAL_EPISODES:
        raise ExperimentBlocked("training summary episode denominator mismatch")
    rows = value.get("episode_rows")
    if not isinstance(rows, list) or len(rows) != CHECKPOINT_INTERVAL_EPISODES:
        raise ExperimentBlocked("training summary episode_rows mismatch")
    if any(row.get("chunk_index") != index for row in rows if isinstance(row, Mapping)):
        raise ExperimentBlocked("training summary row coordinate mismatch")
    checkpoint = load_canonical_json_bytes(
        checkpoint_bytes, f"checkpoint_{index + 1:04d}.json"
    )
    if checkpoint.get("checkpoint_index") != index + 1:
        raise ExperimentBlocked("training summary checkpoint coordinate mismatch")
    artifact = {
        "checkpoint_index": index + 1,
        "checkpoint_sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
        "schema_version": TRAINING_CHUNK_SCHEMA_VERSION,
        "summary": value,
    }
    return artifact


def validate_training_chunk_summaries(
    output_dir: Path | str, checkpoint_paths: Sequence[Path]
) -> list[dict[str, Any]]:
    directory = Path(output_dir) / "training"
    if not directory.exists():
        if checkpoint_paths:
            raise ExperimentBlocked("training summary directory is missing")
        return []
    paths = sorted(directory.glob("chunk_*.json"))
    entries = list(directory.iterdir())
    if any(not path.is_file() for path in entries) or {path.name for path in entries} != {
        path.name for path in paths
    }:
        raise ExperimentBlocked("training summary inventory mismatch")
    if len(paths) != len(checkpoint_paths):
        raise ExperimentBlocked("training summary and checkpoint counts differ")
    artifacts = []
    for index, (path, checkpoint_path) in enumerate(zip(paths, checkpoint_paths)):
        if path.name != f"chunk_{index:04d}.json":
            raise ExperimentBlocked("training summary inventory is not contiguous")
        artifact = load_canonical_json_bytes(path.read_bytes(), path.name)
        _require_keys(
            artifact,
            {"checkpoint_index", "checkpoint_sha256", "schema_version", "summary"},
            "training summary",
        )
        if artifact["schema_version"] != TRAINING_CHUNK_SCHEMA_VERSION:
            raise ExperimentBlocked("training summary schema_version mismatch")
        if artifact["checkpoint_index"] != index + 1:
            raise ExperimentBlocked("training summary checkpoint index mismatch")
        checkpoint_bytes = checkpoint_path.read_bytes()
        if artifact["checkpoint_sha256"] != hashlib.sha256(checkpoint_bytes).hexdigest():
            raise ExperimentBlocked("training summary checkpoint hash mismatch")
        summary = artifact["summary"]
        if not isinstance(summary, Mapping) or summary.get("chunk_index") != index:
            raise ExperimentBlocked("training summary chunk coordinate mismatch")
        if summary.get("episodes") != CHECKPOINT_INTERVAL_EPISODES:
            raise ExperimentBlocked("training summary episode count mismatch")
        rows = summary.get("episode_rows")
        if not isinstance(rows, list) or len(rows) != CHECKPOINT_INTERVAL_EPISODES:
            raise ExperimentBlocked("training summary retained rows mismatch")
        artifacts.append(artifact)
    return artifacts


def persist_completed_training_chunk(
    output_dir: Path | str,
    runtime: TrainingRuntime,
    summary: Mapping[str, Any],
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> dict[str, Any]:
    """Commit one update through a recoverable canonical pending record."""
    output = Path(output_dir)
    pending_path = output / "pending_chunk.json"
    if pending_path.exists():
        raise ExperimentBlocked("pending training chunk requires recovery")
    existing = validate_checkpoint_chain(
        output,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    if len(existing) != runtime.next_chunk_index - 1:
        raise ExperimentBlocked("durable checkpoint coordinate precedes runtime incorrectly")
    checkpoint_paths = [
        output / "checkpoints" / f"checkpoint_{index:04d}.json"
        for index in range(1, len(existing) + 1)
    ]
    validate_training_chunk_summaries(output, checkpoint_paths)
    journal = validate_journal(output, logical_execution_id)
    if len(journal) != len(existing) + 1 or journal[-1]["phase"] in {
        "terminal",
        "blocked",
    }:
        raise ExperimentBlocked("durable journal coordinate precedes runtime incorrectly")
    previous_bytes = (
        None
        if not existing
        else (
            output
            / "checkpoints"
            / f"checkpoint_{len(existing):04d}.json"
        ).read_bytes()
    )
    envelope = build_checkpoint_envelope(
        runtime,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
        previous_checkpoint_bytes=previous_bytes,
    )
    checkpoint_bytes = canonical_json_bytes(envelope)
    training_artifact = _build_training_chunk_artifact(
        summary, checkpoint_bytes=checkpoint_bytes
    )
    training_bytes = canonical_json_bytes(training_artifact)
    pending = {
        "checkpoint": envelope,
        "checkpoint_sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
        "journal_details": {
            "checkpoint_index": runtime.next_chunk_index,
            "checkpoint_sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
            "training_summary_sha256": hashlib.sha256(training_bytes).hexdigest(),
        },
        "logical_execution_id": logical_execution_id,
        "schema_version": PENDING_CHUNK_SCHEMA_VERSION,
        "training_artifact": training_artifact,
        "training_summary_sha256": hashlib.sha256(training_bytes).hexdigest(),
    }
    _atomic_write_once(pending_path, canonical_json_bytes(pending))
    return recover_pending_training_chunk(
        output,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )


def _install_exact_artifact(path: Path, payload: bytes) -> None:
    if path.exists():
        if not path.is_file() or path.read_bytes() != payload:
            raise ExperimentBlocked(f"pending artifact differs: {path.name}")
        return
    _atomic_write_once(path, payload)


def recover_pending_training_chunk(
    output_dir: Path | str,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> dict[str, Any]:
    """Idempotently finish one already-durable chunk publication."""
    output = Path(output_dir)
    pending_path = output / "pending_chunk.json"
    if not pending_path.is_file():
        raise ExperimentBlocked("pending training chunk is missing")
    pending = load_canonical_json_bytes(
        pending_path.read_bytes(), "pending_chunk.json"
    )
    _require_keys(
        pending,
        {
            "checkpoint",
            "checkpoint_sha256",
            "journal_details",
            "logical_execution_id",
            "schema_version",
            "training_artifact",
            "training_summary_sha256",
        },
        "pending training chunk",
    )
    if pending["schema_version"] != PENDING_CHUNK_SCHEMA_VERSION:
        raise ExperimentBlocked("pending training chunk schema mismatch")
    if pending["logical_execution_id"] != logical_execution_id:
        raise ExperimentBlocked("pending training chunk execution id mismatch")
    envelope = dict(_mapping(pending["checkpoint"], "pending checkpoint"))
    index = envelope.get("checkpoint_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index <= TRAINING_CHUNKS:
        raise ExperimentBlocked("pending checkpoint index is invalid")
    previous_path = output / "checkpoints" / f"checkpoint_{index - 1:04d}.json"
    previous_bytes = None if index == 1 else previous_path.read_bytes()
    _validate_checkpoint_envelope(
        envelope,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
        previous_checkpoint_bytes=previous_bytes,
    )
    checkpoint_bytes = canonical_json_bytes(envelope)
    checkpoint_sha256 = hashlib.sha256(checkpoint_bytes).hexdigest()
    if pending["checkpoint_sha256"] != checkpoint_sha256:
        raise ExperimentBlocked("pending checkpoint hash mismatch")
    training_artifact = dict(
        _mapping(pending["training_artifact"], "pending training artifact")
    )
    expected_training = _build_training_chunk_artifact(
        _mapping(training_artifact.get("summary"), "pending training summary"),
        checkpoint_bytes=checkpoint_bytes,
    )
    if training_artifact != expected_training:
        raise ExperimentBlocked("pending training artifact mismatch")
    training_bytes = canonical_json_bytes(training_artifact)
    training_sha256 = hashlib.sha256(training_bytes).hexdigest()
    if pending["training_summary_sha256"] != training_sha256:
        raise ExperimentBlocked("pending training summary hash mismatch")
    expected_details = {
        "checkpoint_index": index,
        "checkpoint_sha256": checkpoint_sha256,
        "training_summary_sha256": training_sha256,
    }
    if pending["journal_details"] != expected_details:
        raise ExperimentBlocked("pending journal details mismatch")

    chain = validate_checkpoint_chain(
        output,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    if len(chain) not in {index - 1, index}:
        raise ExperimentBlocked("pending checkpoint coordinate mismatch")
    checkpoint_path = output / "checkpoints" / f"checkpoint_{index:04d}.json"
    _install_exact_artifact(checkpoint_path, checkpoint_bytes)
    training_path = output / "training" / f"chunk_{index - 1:04d}.json"
    _install_exact_artifact(training_path, training_bytes)

    checkpoint_paths = [
        output / "checkpoints" / f"checkpoint_{position:04d}.json"
        for position in range(1, index + 1)
    ]
    chain = validate_checkpoint_chain(
        output,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    if len(chain) != index:
        raise ExperimentBlocked("recovered checkpoint coordinate mismatch")
    validate_training_chunk_summaries(output, checkpoint_paths)
    records = validate_journal(output, logical_execution_id)
    if len(records) == index:
        append_journal_record(
            output,
            phase="continued",
            logical_execution_id=logical_execution_id,
            details=expected_details,
        )
    elif len(records) == index + 1:
        if records[-1]["phase"] != "continued" or records[-1]["details"] != expected_details:
            raise ExperimentBlocked("recovered journal record mismatch")
    else:
        raise ExperimentBlocked("pending journal coordinate mismatch")
    pending_path.unlink()
    return envelope


def publish_prefix_replay_result(
    output_dir: Path | str,
    checkpoint_two: Mapping[str, Any],
    *,
    replay_wall_seconds: float,
    cumulative_wall_seconds: float,
) -> dict[str, Any]:
    if checkpoint_two.get("checkpoint_index") != 2:
        raise ExperimentBlocked("prefix replay publication requires checkpoint 2")
    state_payload = checkpoint_two.get("state_payload")
    state_sha256 = hashlib.sha256(canonical_json_bytes(state_payload)).hexdigest()
    if checkpoint_two.get("state_payload_sha256") != state_sha256:
        raise ExperimentBlocked("prefix replay checkpoint state hash mismatch")
    checkpoint_path = Path(output_dir) / "checkpoints" / "checkpoint_0002.json"
    checkpoint_bytes = checkpoint_path.read_bytes()
    if load_canonical_json_bytes(checkpoint_bytes, checkpoint_path.name) != checkpoint_two:
        raise ExperimentBlocked("prefix replay checkpoint bytes differ from durable chain")
    if (
        isinstance(replay_wall_seconds, bool)
        or not isinstance(replay_wall_seconds, Real)
        or not math.isfinite(float(replay_wall_seconds))
        or float(replay_wall_seconds) < 0.0
    ):
        raise ExperimentBlocked("prefix replay wall time is invalid")
    if (
        isinstance(cumulative_wall_seconds, bool)
        or not isinstance(cumulative_wall_seconds, Real)
        or not math.isfinite(float(cumulative_wall_seconds))
        or not 0.0 <= float(cumulative_wall_seconds) <= MAX_WALL_SECONDS
    ):
        raise ExperimentBlocked("prefix replay cumulative wall time is invalid")
    checkpoint_wall_seconds = float(checkpoint_two["cumulative_wall_seconds"])
    replay_wall_seconds = float(replay_wall_seconds)
    cumulative_wall_seconds = float(cumulative_wall_seconds)
    if cumulative_wall_seconds != checkpoint_wall_seconds + replay_wall_seconds:
        raise ExperimentBlocked("prefix replay cumulative wall time mismatch")
    result = {
        "checkpoint_index": 2,
        "checkpoint_sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
        "cumulative_wall_seconds": cumulative_wall_seconds,
        "replay_wall_seconds": replay_wall_seconds,
        "schema_version": PREFIX_REPLAY_SCHEMA_VERSION,
        "state_payload_sha256": state_sha256,
        "verified": True,
    }
    _atomic_write_once(
        Path(output_dir) / "prefix_replay.json", canonical_json_bytes(result)
    )
    return result


def validate_prefix_replay_result(output_dir: Path | str) -> dict[str, Any]:
    output = Path(output_dir)
    path = output / "prefix_replay.json"
    result = load_canonical_json_bytes(path.read_bytes(), path.name)
    _require_keys(
        result,
        {
            "checkpoint_index",
            "checkpoint_sha256",
            "cumulative_wall_seconds",
            "replay_wall_seconds",
            "schema_version",
            "state_payload_sha256",
            "verified",
        },
        "prefix replay",
    )
    if result["schema_version"] != PREFIX_REPLAY_SCHEMA_VERSION:
        raise ExperimentBlocked("prefix replay schema mismatch")
    if result["checkpoint_index"] != 2 or result["verified"] is not True:
        raise ExperimentBlocked("prefix replay verdict mismatch")
    checkpoint_path = output / "checkpoints" / "checkpoint_0002.json"
    if not checkpoint_path.is_file():
        raise ExperimentBlocked("prefix replay checkpoint 2 is missing")
    checkpoint_bytes = checkpoint_path.read_bytes()
    if result["checkpoint_sha256"] != hashlib.sha256(checkpoint_bytes).hexdigest():
        raise ExperimentBlocked("prefix replay checkpoint hash mismatch")
    checkpoint = load_canonical_json_bytes(checkpoint_bytes, checkpoint_path.name)
    state_sha256 = hashlib.sha256(
        canonical_json_bytes(checkpoint["state_payload"])
    ).hexdigest()
    if result["state_payload_sha256"] != state_sha256:
        raise ExperimentBlocked("prefix replay state payload hash mismatch")
    replay_wall_seconds = result["replay_wall_seconds"]
    cumulative_wall_seconds = result["cumulative_wall_seconds"]
    if (
        isinstance(replay_wall_seconds, bool)
        or not isinstance(replay_wall_seconds, Real)
        or not math.isfinite(float(replay_wall_seconds))
        or float(replay_wall_seconds) < 0.0
    ):
        raise ExperimentBlocked("prefix replay wall time is invalid")
    if (
        isinstance(cumulative_wall_seconds, bool)
        or not isinstance(cumulative_wall_seconds, Real)
        or not math.isfinite(float(cumulative_wall_seconds))
        or not 0.0 <= float(cumulative_wall_seconds) <= MAX_WALL_SECONDS
    ):
        raise ExperimentBlocked("prefix replay cumulative wall time is invalid")
    checkpoint_wall_seconds = float(checkpoint["cumulative_wall_seconds"])
    if float(cumulative_wall_seconds) != (
        checkpoint_wall_seconds + float(replay_wall_seconds)
    ):
        raise ExperimentBlocked("prefix replay cumulative wall time mismatch")
    return result


def validate_checkpoint_chain(
    output_dir: Path | str,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> list[dict[str, Any]]:
    """Validate every canonical checkpoint and its exact predecessor digest."""
    registration_sha256 = _validate_sha256(registration_sha256, "registration_sha256")
    implementation_commit = _validate_commit(implementation_commit, "implementation_commit")
    logical_execution_id = _validate_execution_id(logical_execution_id)
    directory = Path(output_dir) / "checkpoints"
    if not directory.exists():
        return []
    partials = sorted(directory.glob("*.tmp"))
    if partials:
        raise ExperimentBlocked(f"partial checkpoint exists: {partials[0].name}")
    paths = sorted(directory.glob("checkpoint_*.json"))
    entries = list(directory.iterdir())
    if any(not path.is_file() for path in entries) or {path.name for path in entries} != {
        path.name for path in paths
    }:
        raise ExperimentBlocked("checkpoint directory inventory mismatch")
    envelopes: list[dict[str, Any]] = []
    previous_bytes: bytes | None = None
    previous_elapsed = 0.0
    for expected_index, path in enumerate(paths, start=1):
        if path.name != f"checkpoint_{expected_index:04d}.json":
            raise ExperimentBlocked("checkpoint inventory is not contiguous")
        payload = path.read_bytes()
        value = load_canonical_json_bytes(payload, path.name)
        envelope = _validate_checkpoint_envelope(
            value,
            registration_sha256=registration_sha256,
            implementation_commit=implementation_commit,
            logical_execution_id=logical_execution_id,
            previous_checkpoint_bytes=previous_bytes,
        )
        if envelope["checkpoint_index"] != expected_index:
            raise ExperimentBlocked("checkpoint filename and index differ")
        elapsed = float(envelope["cumulative_wall_seconds"])
        if elapsed < previous_elapsed:
            raise ExperimentBlocked("checkpoint cumulative wall time regressed")
        previous_elapsed = elapsed
        previous_bytes = payload
        envelopes.append(envelope)
    return envelopes


def restore_training_runtime(
    envelope: Mapping[str, Any],
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> TrainingRuntime:
    """Restore the exact runtime from one already chain-validated checkpoint."""
    payload = _validate_checkpoint_state_payload(
        envelope.get("state_payload"),
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    if envelope.get("state_payload_sha256") != hashlib.sha256(
        canonical_json_bytes(payload)
    ).hexdigest():
        raise ExperimentBlocked("checkpoint state payload digest mismatch")
    runtime = initialize_training_runtime()
    model_state = {
        name: decode_tensor(value, f"checkpoint model.{name}")
        for name, value in payload["model"]["state_dict"].items()
    }
    expected = runtime.model.state_dict()
    for name in expected:
        if model_state[name].dtype != expected[name].dtype or model_state[name].shape != expected[name].shape:
            raise ExperimentBlocked(f"checkpoint model tensor contract mismatch: {name}")
    runtime.model.load_state_dict(model_state)
    runtime.optimizer.load_state_dict(_decode_optimizer_state(payload["optimizer"]))
    random_payload = payload["random"]
    runtime.action_generator.set_state(
        decode_tensor(random_payload["action_generator"], "checkpoint action generator")
    )
    python_state = _decode_state_value(random_payload["python"], "checkpoint python random")
    runtime.python_random.setstate(python_state)
    _torch_module().set_rng_state(
        decode_tensor(random_payload["torch_global"], "checkpoint torch global RNG")
    )
    coordinate = payload["coordinate"]
    runtime.next_chunk_index = coordinate["next_chunk_index"]
    runtime.completed_episodes = coordinate["completed_episodes"]
    runtime.optimizer_updates = coordinate["optimizer_updates"]
    runtime.cumulative_wall_seconds = float(envelope["cumulative_wall_seconds"])
    _validate_training_runtime(runtime)
    return runtime


def _journal_directory(output_dir: Path | str) -> Path:
    return Path(output_dir) / "journal"


def validate_journal(
    output_dir: Path | str, logical_execution_id: str
) -> list[dict[str, Any]]:
    logical_execution_id = _validate_execution_id(logical_execution_id)
    directory = _journal_directory(output_dir)
    if not directory.exists():
        return []
    partials = sorted(directory.glob("*.tmp"))
    if partials:
        raise ExperimentBlocked(f"partial journal record exists: {partials[0].name}")
    paths = sorted(directory.glob("record_*.json"))
    entries = list(directory.iterdir())
    if any(not path.is_file() for path in entries) or {path.name for path in entries} != {
        path.name for path in paths
    }:
        raise ExperimentBlocked("journal directory inventory mismatch")
    records = []
    previous_bytes: bytes | None = None
    terminal_seen = False
    for expected_index, path in enumerate(paths):
        if path.name != f"record_{expected_index:06d}.json":
            raise ExperimentBlocked("journal inventory is not contiguous")
        payload = path.read_bytes()
        record = load_canonical_json_bytes(payload, path.name)
        _require_keys(
            record,
            {
                "details",
                "index",
                "logical_execution_id",
                "phase",
                "previous_record_sha256",
                "schema_version",
            },
            "journal record",
        )
        if record["schema_version"] != JOURNAL_SCHEMA_VERSION:
            raise ExperimentBlocked("journal schema_version mismatch")
        if record["index"] != expected_index:
            raise ExperimentBlocked("journal index mismatch")
        if record["logical_execution_id"] != logical_execution_id:
            raise ExperimentBlocked("journal logical execution id mismatch")
        phase = record["phase"]
        if phase not in {"started", "continued", "terminal", "blocked"}:
            raise ExperimentBlocked("journal phase is invalid")
        if expected_index == 0 and phase != "started":
            raise ExperimentBlocked("journal must begin with started")
        if expected_index > 0 and phase == "started":
            raise ExperimentBlocked("journal contains a second started record")
        if terminal_seen:
            raise ExperimentBlocked("journal contains a record after terminal")
        terminal_seen = phase in {"terminal", "blocked"}
        expected_previous = (
            None
            if previous_bytes is None
            else hashlib.sha256(previous_bytes).hexdigest()
        )
        if record["previous_record_sha256"] != expected_previous:
            raise ExperimentBlocked("journal previous_record_sha256 mismatch")
        _validate_json_value(record["details"], "journal details")
        if not isinstance(record["details"], Mapping):
            raise ExperimentBlocked("journal details must be an object")
        previous_bytes = payload
        records.append(record)
    return records


def append_journal_record(
    output_dir: Path | str,
    *,
    phase: str,
    logical_execution_id: str,
    details: Mapping[str, Any],
) -> Path:
    """Append one hash-linked journal record without rewriting prior records."""
    records = validate_journal(output_dir, logical_execution_id)
    if records and records[-1]["phase"] in {"terminal", "blocked"}:
        raise ExperimentBlocked("journal is already terminal")
    if not records and phase != "started":
        raise ExperimentBlocked("first journal phase must be started")
    if records and phase == "started":
        raise ExperimentBlocked("journal already has a started record")
    if phase not in {"started", "continued", "terminal", "blocked"}:
        raise ExperimentBlocked("journal phase is invalid")
    _validate_json_value(details, "journal details")
    index = len(records)
    previous_path = (
        None
        if index == 0
        else _journal_directory(output_dir) / f"record_{index - 1:06d}.json"
    )
    previous_bytes = None if previous_path is None else previous_path.read_bytes()
    record = {
        "details": copy.deepcopy(dict(details)),
        "index": index,
        "logical_execution_id": _validate_execution_id(logical_execution_id),
        "phase": phase,
        "previous_record_sha256": (
            None
            if previous_bytes is None
            else hashlib.sha256(previous_bytes).hexdigest()
        ),
        "schema_version": JOURNAL_SCHEMA_VERSION,
    }
    path = _journal_directory(output_dir) / f"record_{index:06d}.json"
    _atomic_write_once(path, canonical_json_bytes(record))
    return path


class ExecutionLease:
    """Windows process lease released by the OS after interruption or crash."""

    def __init__(self, path: Path, handle: Any) -> None:
        self.path = path
        self._handle = handle

    @classmethod
    def acquire(
        cls, output_dir: Path | str, logical_execution_id: str
    ) -> "ExecutionLease":
        import msvcrt

        execution_id = _validate_execution_id(logical_execution_id)
        path = Path(output_dir) / ".execution.lease"
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ExperimentBlocked("execution lease is already held") from exc
            handle.seek(0)
            existing = handle.read()
            expected = canonical_json_bytes(
                {
                    "logical_execution_id": execution_id,
                    "schema_version": LEASE_SCHEMA_VERSION,
                }
            )
            if existing in {b"", b"\0"}:
                handle.seek(0)
                handle.truncate()
                handle.write(expected)
                handle.flush()
                os.fsync(handle.fileno())
            elif existing != expected:
                raise ExperimentBlocked("execution lease belongs to another logical id")
            return cls(path, handle)
        except BaseException:
            try:
                handle.close()
            finally:
                pass
            raise

    def close(self) -> None:
        if self._handle is None:
            return
        import msvcrt

        handle = self._handle
        self._handle = None
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            handle.close()

    def read_payload(self) -> bytes:
        if self._handle is None:
            raise ExperimentBlocked("execution lease is closed")
        self._handle.seek(0)
        return self._handle.read()

    def __enter__(self) -> "ExecutionLease":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()


def resume_training_runtime_from_output(
    output_dir: Path | str,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
    active_lease: ExecutionLease | None = None,
) -> TrainingRuntime:
    """Validate the complete resumable inventory before restoring any runtime."""
    output = Path(output_dir)
    if not output.is_dir():
        raise ExperimentBlocked("resume output directory is missing")
    allowed_root_entries = {
        ".execution.lease",
        "authorization.json",
        "checkpoints",
        "configuration.json",
        "journal",
        "prefix_replay.json",
        "registration.json",
        "training",
    }
    entries = {path.name: path for path in output.iterdir()}
    unexpected = sorted(set(entries) - allowed_root_entries)
    if unexpected:
        raise ExperimentBlocked(f"resume output inventory has extra entries: {unexpected}")
    if "journal" not in entries:
        raise ExperimentBlocked("resume journal is missing")
    if "checkpoints" in entries and not entries["checkpoints"].is_dir():
        raise ExperimentBlocked("resume checkpoints entry is not a directory")
    if not entries["journal"].is_dir():
        raise ExperimentBlocked("resume journal entry is not a directory")
    if ".execution.lease" in entries:
        lease_path = entries[".execution.lease"].resolve()
        if active_lease is not None and active_lease.path.resolve() != lease_path:
            raise ExperimentBlocked("active execution lease path mismatch")
        lease = load_canonical_json_bytes(
            (
                active_lease.read_payload()
                if active_lease is not None
                else entries[".execution.lease"].read_bytes()
            ),
            "execution lease",
        )
        if lease != {
            "logical_execution_id": logical_execution_id,
            "schema_version": LEASE_SCHEMA_VERSION,
        }:
            raise ExperimentBlocked("resume execution lease identity mismatch")
    elif active_lease is not None:
        raise ExperimentBlocked("active execution lease is missing from output")

    records = validate_journal(output, logical_execution_id)
    if not records:
        raise ExperimentBlocked("resume journal is empty")
    if records[-1]["phase"] in {"terminal", "blocked"}:
        raise ExperimentBlocked("cannot resume a terminal journal")
    started = records[0]
    if started["details"] != {"registration_sha256": registration_sha256}:
        raise ExperimentBlocked("started journal registration identity mismatch")
    chain = validate_checkpoint_chain(
        output,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    checkpoint_paths = [
        output / "checkpoints" / f"checkpoint_{index:04d}.json"
        for index in range(1, len(chain) + 1)
    ]
    training_summaries = validate_training_chunk_summaries(
        output, checkpoint_paths
    )
    continued = records[1:]
    if any(record["phase"] != "continued" for record in continued):
        raise ExperimentBlocked("nonterminal resume journal phase mismatch")
    if len(continued) != len(chain):
        raise ExperimentBlocked("checkpoint and journal counts differ")
    checkpoint_directory = output / "checkpoints"
    for index, (record, envelope) in enumerate(zip(continued, chain), start=1):
        checkpoint_path = checkpoint_directory / f"checkpoint_{index:04d}.json"
        training_path = output / "training" / f"chunk_{index - 1:04d}.json"
        expected_details = {
            "checkpoint_index": index,
            "checkpoint_sha256": hashlib.sha256(
                checkpoint_path.read_bytes()
            ).hexdigest(),
            "training_summary_sha256": hashlib.sha256(
                training_path.read_bytes()
            ).hexdigest(),
        }
        if record["details"] != expected_details:
            raise ExperimentBlocked("checkpoint journal binding mismatch")
        if envelope["checkpoint_index"] != index:
            raise ExperimentBlocked("checkpoint chain coordinate mismatch")
        if training_summaries[index - 1]["checkpoint_index"] != index:
            raise ExperimentBlocked("training summary coordinate mismatch")
    if not chain and "prefix_replay.json" in entries:
        raise ExperimentBlocked("resume prefix replay has no checkpoint chain")
    if not chain:
        return initialize_training_runtime()
    if len(chain) > 2 and "prefix_replay.json" not in entries:
        raise ExperimentBlocked("resume prefix replay evidence is missing")
    prefix_replay = None
    if "prefix_replay.json" in entries:
        prefix_replay = validate_prefix_replay_result(output)
        if len(chain) > 2 and float(chain[2]["cumulative_wall_seconds"]) < float(
            prefix_replay["cumulative_wall_seconds"]
        ):
            raise ExperimentBlocked("checkpoint wall time precedes prefix replay")
    runtime = restore_training_runtime(
        chain[-1],
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    if prefix_replay is not None and len(chain) == 2:
        runtime.cumulative_wall_seconds = float(
            prefix_replay["cumulative_wall_seconds"]
        )
        _validate_training_runtime(runtime)
    return runtime


def _model_state_bytes(model: Any) -> bytes:
    return canonical_json_bytes(
        {
            name: encode_tensor(tensor)
            for name, tensor in sorted(model.state_dict().items())
        }
    )


def evaluate_frozen_policy(
    model: Any,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    deadline: float,
    clock: Callable[[], float] = time.perf_counter,
) -> list[dict[str, Any]]:
    """Evaluate one frozen policy greedily without changing model parameters."""
    if not isinstance(model, CandidateRanker):
        raise ExperimentBlocked("evaluation model must be CandidateRanker")
    if next(model.parameters()).device.type != "cpu":
        raise ExperimentBlocked("evaluation model must remain on CPU")
    before = _model_state_bytes(model)
    was_training = model.training
    rows: list[dict[str, Any]] = []
    torch = _torch_module()
    model.eval()
    try:
        with torch.no_grad():
            for seed in seeds:
                rollout = _rollout_episode(
                    model,
                    environment_factory=environment_factory,
                    seed=int(seed),
                    training=False,
                    action_generator=None,
                    deadline=deadline,
                    clock=clock,
                )
                rows.append(copy.deepcopy(rollout.summary))
    finally:
        model.train(was_training)
    if _model_state_bytes(model) != before:
        raise ExperimentBlocked("frozen evaluation changed model parameters")
    return rows


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    position = probability * (len(sorted_values) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(
        sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight
    )


def paired_bootstrap_interval(differences: Sequence[float]) -> dict[str, Any]:
    """Return the one registered paired bootstrap interval."""
    values = [float(value) for value in differences]
    if not values or any(not math.isfinite(value) for value in values):
        raise ExperimentBlocked("paired floor differences must be finite and nonempty")
    if all(value == values[0] for value in values[1:]):
        return {
            "confidence_level": CONFIDENCE_LEVEL,
            "lower": values[0],
            "mean": values[0],
            "resamples": BOOTSTRAP_RESAMPLES,
            "upper": values[0],
        }
    generator = random.Random(BOOTSTRAP_SEED)
    means = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        means.append(
            sum(values[generator.randrange(len(values))] for _ in values)
            / len(values)
        )
    means.sort()
    tail = (1.0 - CONFIDENCE_LEVEL) / 2.0
    return {
        "confidence_level": CONFIDENCE_LEVEL,
        "lower": _quantile(means, tail),
        "mean": sum(values) / len(values),
        "resamples": BOOTSTRAP_RESAMPLES,
        "upper": _quantile(means, 1.0 - tail),
    }


def _cohort_seeds(cohort: str) -> tuple[int, ...]:
    if cohort == "canary":
        return CANARY_SEEDS
    if cohort == "holdout":
        return HOLDOUT_SEEDS
    raise ExperimentBlocked(f"unsupported evaluation cohort: {cohort!r}")


def _validate_evaluation_row(
    row: object, *, expected_seed: int, label: str
) -> dict[str, Any]:
    value = dict(_mapping(row, label))
    _require_keys(
        value,
        {
            "action_sequence_sha256",
            "candidate_legality",
            "categories",
            "decisions",
            "last_supported_floor",
            "outcome",
            "policy_input_sha256s",
            "retained",
            "seed",
            "selected_action_ids",
            "terminal_floor",
            "total_reward",
            "unsupported_reason",
            "victory",
        },
        label,
    )
    if value["seed"] != expected_seed:
        raise ExperimentBlocked(f"{label} seed order mismatch")
    if value["candidate_legality"] is not True or value["retained"] is not True:
        raise ExperimentBlocked(f"{label} is not a retained legal episode")
    decisions = value["decisions"]
    if (
        isinstance(decisions, bool)
        or not isinstance(decisions, int)
        or not 1 <= decisions <= MAX_DECISIONS_PER_EPISODE
    ):
        raise ExperimentBlocked(f"{label} decision count is invalid")
    action_ids = value["selected_action_ids"]
    policy_hashes = value["policy_input_sha256s"]
    if (
        not isinstance(action_ids, list)
        or len(action_ids) != decisions
        or any(not isinstance(item, str) or not item for item in action_ids)
    ):
        raise ExperimentBlocked(f"{label} action sequence is invalid")
    if (
        not isinstance(policy_hashes, list)
        or len(policy_hashes) != decisions
        or any(
            not isinstance(item, str) or not _SHA256_RE.fullmatch(item)
            for item in policy_hashes
        )
    ):
        raise ExperimentBlocked(f"{label} policy input hashes are invalid")
    if not isinstance(value["action_sequence_sha256"], str) or not _SHA256_RE.fullmatch(
        value["action_sequence_sha256"]
    ):
        raise ExperimentBlocked(f"{label} action sequence hash is invalid")
    categories = value["categories"]
    if (
        not isinstance(categories, list)
        or not categories
        or any(category not in TARGET_CATEGORIES for category in categories)
        or categories != sorted(set(categories))
    ):
        raise ExperimentBlocked(f"{label} categories are invalid")
    last_supported_floor = _finite_floor(
        value["last_supported_floor"], f"{label} last_supported_floor"
    )
    if not 0.0 <= last_supported_floor <= MAX_FLOOR:
        raise ExperimentBlocked(f"{label} last_supported_floor is outside bounds")
    total_reward = value["total_reward"]
    if (
        isinstance(total_reward, bool)
        or not isinstance(total_reward, Real)
        or not math.isfinite(float(total_reward))
        or not 0.0 <= float(total_reward) <= VICTORY_WEIGHT + 1.0
    ):
        raise ExperimentBlocked(f"{label} total reward is invalid")
    if type(value["victory"]) is not bool:
        raise ExperimentBlocked(f"{label} victory flag is invalid")
    unsupported_reason = value["unsupported_reason"]
    if unsupported_reason is None:
        if value["outcome"] not in {"player_loss", "player_victory"}:
            raise ExperimentBlocked(f"{label} terminal outcome is invalid")
        terminal_floor = _finite_floor(
            value["terminal_floor"], f"{label} terminal_floor"
        )
        if terminal_floor != last_supported_floor:
            raise ExperimentBlocked(f"{label} terminal and supported floors differ")
        if value["victory"] is not (value["outcome"] == "player_victory"):
            raise ExperimentBlocked(f"{label} victory flag mismatch")
    else:
        if unsupported_reason not in REGISTERED_SUPPORT_BLOCKERS:
            raise ExperimentBlocked(f"{label} has an unregistered support blocker")
        if value["outcome"] is not None or value["terminal_floor"] is not None:
            raise ExperimentBlocked(f"{label} unsupported disposition is invalid")
        if value["victory"] is not False:
            raise ExperimentBlocked(f"{label} unsupported episode cannot be a victory")
    _validate_json_value(value, label)
    return copy.deepcopy(value)
def build_paired_evaluation(
    initial_rows: Sequence[Mapping[str, Any]],
    trained_rows: Sequence[Mapping[str, Any]],
    *,
    cohort: str,
) -> dict[str, Any]:
    """Build canonical paired metrics while retaining every policy episode."""
    seeds = _cohort_seeds(cohort)
    if len(initial_rows) != len(seeds) or len(trained_rows) != len(seeds):
        raise ExperimentBlocked(f"{cohort} evaluation row count mismatch")
    initial = [
        _validate_evaluation_row(row, expected_seed=seed, label=f"initial[{index}]")
        for index, (seed, row) in enumerate(zip(seeds, initial_rows))
    ]
    trained = [
        _validate_evaluation_row(row, expected_seed=seed, label=f"trained[{index}]")
        for index, (seed, row) in enumerate(zip(seeds, trained_rows))
    ]
    paired_rows = []
    for seed, initial_row, trained_row in zip(seeds, initial, trained):
        initial_floor = float(initial_row["last_supported_floor"])
        trained_floor = float(trained_row["last_supported_floor"])
        paired_rows.append(
            {
                "floor_difference": trained_floor - initial_floor,
                "initial_floor": initial_floor,
                "initial_outcome": initial_row["outcome"],
                "initial_unsupported_reason": initial_row["unsupported_reason"],
                "initial_victory": bool(initial_row["victory"]),
                "seed": int(seed),
                "trained_floor": trained_floor,
                "trained_outcome": trained_row["outcome"],
                "trained_unsupported_reason": trained_row["unsupported_reason"],
                "trained_victory": bool(trained_row["victory"]),
                "victory_difference": int(trained_row["victory"])
                - int(initial_row["victory"]),
            }
        )
    initial_categories = sorted(
        {category for row in initial for category in row["categories"]}
    )
    trained_categories = sorted(
        {category for row in trained for category in row["categories"]}
    )
    initial_unsupported = sum(row["unsupported_reason"] is not None for row in initial)
    trained_unsupported = sum(row["unsupported_reason"] is not None for row in trained)
    denominator = 2 * len(seeds)
    return {
        "cohort": cohort,
        "floor_difference_ci": paired_bootstrap_interval(
            [row["floor_difference"] for row in paired_rows]
        ),
        "initial": {
            "categories": initial_categories,
            "rows": initial,
            "unsupported_episodes": initial_unsupported,
            "victories": sum(row["victory"] for row in initial),
        },
        "paired_rows": paired_rows,
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "trained": {
            "categories": trained_categories,
            "rows": trained,
            "unsupported_episodes": trained_unsupported,
            "victories": sum(row["victory"] for row in trained),
        },
        "unsupported_rate": (initial_unsupported + trained_unsupported)
        / denominator,
        "unsupported_rate_denominator": denominator,
    }


def _validate_paired_evaluation(value: object, cohort: str) -> dict[str, Any]:
    evaluation = dict(_mapping(value, f"{cohort} evaluation"))
    _require_keys(
        evaluation,
        {
            "cohort",
            "floor_difference_ci",
            "initial",
            "paired_rows",
            "schema_version",
            "trained",
            "unsupported_rate",
            "unsupported_rate_denominator",
        },
        f"{cohort} evaluation",
    )
    if evaluation["schema_version"] != EVALUATION_SCHEMA_VERSION:
        raise ExperimentBlocked(f"{cohort} evaluation schema mismatch")
    if evaluation["cohort"] != cohort:
        raise ExperimentBlocked(f"{cohort} evaluation cohort mismatch")
    initial = _mapping(evaluation["initial"], "initial evaluation")
    trained = _mapping(evaluation["trained"], "trained evaluation")
    rebuilt = build_paired_evaluation(
        initial.get("rows", []), trained.get("rows", []), cohort=cohort
    )
    if canonical_json_bytes(evaluation) != canonical_json_bytes(rebuilt):
        difference = _first_difference(rebuilt, evaluation, f"{cohort} evaluation")
        raise ExperimentBlocked(f"{cohort} evaluation recomputation mismatch: {difference}")
    return rebuilt


def paired_policy_evaluation(
    initial_model: Any,
    trained_model: Any,
    *,
    environment_factory: Callable[[int], Any],
    cohort: str,
    deadline: float | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Evaluate frozen initialization and trained policies on one exact cohort."""
    seeds = _cohort_seeds(cohort)
    if deadline is None:
        started = float(clock())
        if not math.isfinite(started):
            raise ExperimentBlocked("evaluation wall clock must be finite")
        deadline = started + MAX_WALL_SECONDS
    initial_rows = evaluate_frozen_policy(
        initial_model,
        environment_factory=environment_factory,
        seeds=seeds,
        deadline=deadline,
        clock=clock,
    )
    trained_rows = evaluate_frozen_policy(
        trained_model,
        environment_factory=environment_factory,
        seeds=seeds,
        deadline=deadline,
        clock=clock,
    )
    return build_paired_evaluation(initial_rows, trained_rows, cohort=cohort)


def classify_canary_evaluation(value: object) -> dict[str, Any]:
    evaluation = _validate_paired_evaluation(value, "canary")
    blockers = []
    required_categories = list(TARGET_CATEGORIES)
    if evaluation["initial"]["categories"] != required_categories:
        blockers.append("initial_four_category_coverage")
    if evaluation["trained"]["categories"] != required_categories:
        blockers.append("trained_four_category_coverage")
    if evaluation["unsupported_rate"] > UNSUPPORTED_RATE_CEILING:
        blockers.append("unsupported_rate")
    if evaluation["trained"]["victories"] < evaluation["initial"]["victories"]:
        blockers.append("trained_victory_noninferiority")
    if evaluation["floor_difference_ci"]["lower"] <= 0.0:
        blockers.append("paired_floor_lower_bound")
    return {
        "blockers": blockers,
        "floor_difference_ci": evaluation["floor_difference_ci"],
        "initial_victories": evaluation["initial"]["victories"],
        "passed": not blockers,
        "trained_victories": evaluation["trained"]["victories"],
        "unsupported_rate": evaluation["unsupported_rate"],
        "unsupported_rate_denominator": evaluation[
            "unsupported_rate_denominator"
        ],
        "verdict": "canary_passed" if not blockers else "experiment_stopped_at_canary",
    }


def classify_holdout_evaluation(value: object) -> dict[str, Any]:
    evaluation = _validate_paired_evaluation(value, "holdout")
    victory_signal = (
        evaluation["trained"]["victories"] > evaluation["initial"]["victories"]
    )
    floor_signal = evaluation["floor_difference_ci"]["lower"] > 0.0
    learning_signal = victory_signal and floor_signal
    return {
        "floor_difference_ci": evaluation["floor_difference_ci"],
        "floor_signal": floor_signal,
        "initial_victories": evaluation["initial"]["victories"],
        "trained_victories": evaluation["trained"]["victories"],
        "unsupported_rate": evaluation["unsupported_rate"],
        "verdict": (
            "experiment_valid_with_learning_signal"
            if learning_signal
            else "experiment_valid_without_learning_signal"
        ),
        "victory_signal": victory_signal,
    }


def run_conditional_evaluation(
    initial_model: Any,
    trained_model: Any,
    *,
    environment_factory: Callable[[int], Any],
    deadline: float | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> dict[str, Any]:
    """Run canary and access holdout only after every registered gate passes."""
    if deadline is None:
        started = float(clock())
        if not math.isfinite(started):
            raise ExperimentBlocked("evaluation wall clock must be finite")
        deadline = started + MAX_WALL_SECONDS
    canary = paired_policy_evaluation(
        initial_model,
        trained_model,
        environment_factory=environment_factory,
        cohort="canary",
        deadline=deadline,
        clock=clock,
    )
    canary_gate = classify_canary_evaluation(canary)
    if not canary_gate["passed"]:
        return {
            "canary": canary,
            "canary_gate": canary_gate,
            "holdout": {"accessed": False, "episode_count": 0},
            "verdict": "experiment_stopped_at_canary",
        }
    holdout = paired_policy_evaluation(
        initial_model,
        trained_model,
        environment_factory=environment_factory,
        cohort="holdout",
        deadline=deadline,
        clock=clock,
    )
    holdout_classification = classify_holdout_evaluation(holdout)
    return {
        "canary": canary,
        "canary_gate": canary_gate,
        "holdout": {
            "accessed": True,
            "classification": holdout_classification,
            "episode_count": 2 * len(HOLDOUT_SEEDS),
            "evaluation": holdout,
        },
        "verdict": holdout_classification["verdict"],
    }


def _load_control_files(
    output_dir: Path | str,
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes, dict[str, Any]]:
    output = Path(output_dir)
    registration_bytes = (output / "registration.json").read_bytes()
    authorization_bytes = (output / "authorization.json").read_bytes()
    configuration_bytes = (output / "configuration.json").read_bytes()
    registration = validate_registration(
        load_canonical_json_bytes(registration_bytes, "registration.json")
    )
    authorization = validate_execution_authorization(
        load_canonical_json_bytes(authorization_bytes, "authorization.json"),
        registration=registration,
        registration_bytes=registration_bytes,
    )
    configuration = load_canonical_json_bytes(
        configuration_bytes, "configuration.json"
    )
    expected_configuration = {
        "authority": registration_authority(),
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "experiment": experiment_contract(),
        "formal_readiness_verdict": FORMAL_READINESS_VERDICT,
        "identity": registration["identity"],
        "logical_execution_id": authorization["logical_execution_id"],
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
    }
    if configuration != expected_configuration:
        difference = _first_difference(
            expected_configuration, configuration, "configuration"
        )
        raise ExperimentBlocked(f"configuration mismatch: {difference}")
    return (
        registration,
        registration_bytes,
        authorization,
        authorization_bytes,
        configuration,
    )


def initialize_experiment_output(
    output_dir: Path | str,
    *,
    registration_bytes: bytes,
    authorization_bytes: bytes,
) -> dict[str, Any]:
    """Create the absent working directory from canonical reviewed controls."""
    registration = validate_registration(
        load_canonical_json_bytes(registration_bytes, "registration")
    )
    authorization = validate_execution_authorization(
        load_canonical_json_bytes(authorization_bytes, "authorization"),
        registration=registration,
        registration_bytes=registration_bytes,
    )
    output = Path(output_dir)
    if output.exists():
        raise ExperimentBlocked("experiment output must be absent before initialization")
    registered_name = PurePosixPath(authorization["output_directory"]).name
    if output.name != registered_name:
        raise ExperimentBlocked("experiment output basename differs from authorization")
    output.mkdir(parents=True)
    registration_sha256 = hashlib.sha256(registration_bytes).hexdigest()
    configuration = {
        "authority": registration_authority(),
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "experiment": experiment_contract(),
        "formal_readiness_verdict": FORMAL_READINESS_VERDICT,
        "identity": registration["identity"],
        "logical_execution_id": authorization["logical_execution_id"],
        "registration_sha256": registration_sha256,
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
    }
    _atomic_write_once(output / "registration.json", registration_bytes)
    _atomic_write_once(output / "authorization.json", authorization_bytes)
    _atomic_write_once(
        output / "configuration.json", canonical_json_bytes(configuration)
    )
    (output / "checkpoints").mkdir()
    (output / "training").mkdir()
    append_journal_record(
        output,
        phase="started",
        logical_execution_id=authorization["logical_execution_id"],
        details={"registration_sha256": registration_sha256},
    )
    _load_control_files(output)
    return configuration


def _validate_terminal_evaluation(value: object) -> tuple[dict[str, Any], str]:
    result = dict(_mapping(value, "terminal evaluation"))
    _require_keys(
        result,
        {"canary", "canary_gate", "holdout", "verdict"},
        "terminal evaluation",
    )
    canary = _validate_paired_evaluation(result["canary"], "canary")
    canary_gate = classify_canary_evaluation(canary)
    if result["canary_gate"] != canary_gate:
        raise ExperimentBlocked("terminal canary classification mismatch")
    verdict = result["verdict"]
    if not canary_gate["passed"]:
        if verdict != "experiment_stopped_at_canary":
            raise ExperimentBlocked("failed canary verdict mismatch")
        if result["holdout"] != {"accessed": False, "episode_count": 0}:
            raise ExperimentBlocked("failed canary must preserve untouched holdout")
        return copy.deepcopy(result), verdict
    holdout = dict(_mapping(result["holdout"], "terminal holdout"))
    _require_keys(
        holdout,
        {"accessed", "classification", "episode_count", "evaluation"},
        "terminal holdout",
    )
    if holdout["accessed"] is not True or holdout["episode_count"] != 2 * len(
        HOLDOUT_SEEDS
    ):
        raise ExperimentBlocked("terminal holdout access contract mismatch")
    holdout_evaluation = _validate_paired_evaluation(
        holdout["evaluation"], "holdout"
    )
    classification = classify_holdout_evaluation(holdout_evaluation)
    if holdout["classification"] != classification or verdict != classification["verdict"]:
        raise ExperimentBlocked("terminal holdout classification mismatch")
    return copy.deepcopy(result), verdict


def _training_aggregates(training: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summaries = [dict(row["summary"]) for row in training]
    episode_rows = [
        episode for summary in summaries for episode in summary["episode_rows"]
    ]
    return {
        "categories": sorted(
            {category for summary in summaries for category in summary["categories"]}
        ),
        "episodes": len(episode_rows),
        "optimizer_updates": len(summaries),
        "unsupported_episodes": sum(
            row.get("unsupported_reason") is not None for row in episode_rows
        ),
        "victories": sum(bool(row.get("victory")) for row in episode_rows),
    }


def _render_terminal_report(metrics: Mapping[str, Any]) -> bytes:
    lines = [
        "# Bounded Non-Combat Simulator RL Experiment",
        "",
        f"- Verdict: `{metrics['verdict']}`",
        f"- Formal readiness: `{FORMAL_READINESS_VERDICT}`",
        f"- Training episodes: {metrics['training']['episodes']}",
        f"- Training optimizer updates: {metrics['training']['optimizer_updates']}",
    ]
    if "canary" in metrics:
        lines.extend(
            [
                f"- Canary initial victories: {metrics['canary']['initial_victories']}",
                f"- Canary trained victories: {metrics['canary']['trained_victories']}",
                f"- Canary paired floor CI lower: {metrics['canary']['floor_difference_ci']['lower']}",
            ]
        )
    if "holdout" in metrics:
        lines.extend(
            [
                f"- Holdout initial victories: {metrics['holdout']['initial_victories']}",
                f"- Holdout trained victories: {metrics['holdout']['trained_victories']}",
                f"- Holdout paired floor CI lower: {metrics['holdout']['floor_difference_ci']['lower']}",
            ]
        )
    if metrics.get("blocked_reason"):
        lines.append(f"- Blocked reason: `{metrics['blocked_reason']}`")
    lines.extend(
        [
            "",
            "This result is simulator-only. It grants no Current, live, OPE, causal,",
            "qualification, loading, formal-RL, or promotion authority.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def _terminal_payloads(
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
    runtime: TrainingRuntime,
    training: Sequence[Mapping[str, Any]],
    evaluation: Mapping[str, Any] | None,
    blocked_reason: str | None,
    prefix_replay_verified: bool,
) -> tuple[dict[str, bytes], str]:
    aggregates = _training_aggregates(training)
    if blocked_reason is not None:
        if not isinstance(blocked_reason, str) or not blocked_reason:
            raise ExperimentBlocked("blocked terminal requires a reason")
        if evaluation is not None:
            raise ExperimentBlocked("blocked terminal cannot publish evaluation")
        verdict = "experiment_blocked"
        validated_evaluation = None
    else:
        if prefix_replay_verified is not True:
            raise ExperimentBlocked("terminal evaluation requires verified prefix replay")
        if runtime.next_chunk_index != TRAINING_CHUNKS:
            raise ExperimentBlocked("terminal evaluation requires complete training")
        if len(training) != TRAINING_CHUNKS:
            raise ExperimentBlocked("terminal evaluation requires all training summaries")
        validated_evaluation, verdict = _validate_terminal_evaluation(evaluation)
    metrics: dict[str, Any] = {
        "authority": registration_authority(),
        "blocked_reason": blocked_reason,
        "formal_readiness_verdict": FORMAL_READINESS_VERDICT,
        "logical_execution_id": logical_execution_id,
        "prefix_replay_verified": prefix_replay_verified,
        "cumulative_wall_seconds": runtime.cumulative_wall_seconds,
        "registration_sha256": registration_sha256,
        "schema_version": METRICS_SCHEMA_VERSION,
        "training": aggregates,
        "verdict": verdict,
    }
    payloads: dict[str, bytes] = {}
    if validated_evaluation is not None:
        evaluation_payload = {
            "authority": registration_authority(),
            "formal_readiness_verdict": FORMAL_READINESS_VERDICT,
            "registration_sha256": registration_sha256,
            "result": validated_evaluation,
            "schema_version": TERMINAL_EVALUATION_SCHEMA_VERSION,
        }
        payloads["evaluation.json"] = canonical_json_bytes(evaluation_payload)
        metrics["canary"] = validated_evaluation["canary_gate"]
        if validated_evaluation["holdout"]["accessed"]:
            metrics["holdout"] = validated_evaluation["holdout"]["classification"]
    state_payload = build_checkpoint_state_payload(
        runtime,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    model_payload = {
        "architecture": state_payload["model"]["architecture"],
        "authority": registration_authority(),
        "input_dim": state_payload["model"]["input_dim"],
        "registration_sha256": registration_sha256,
        "schema_version": FINAL_MODEL_SCHEMA_VERSION,
        "state_dict": state_payload["model"]["state_dict"],
        "verdict": verdict,
    }
    payloads["metrics.json"] = canonical_json_bytes(metrics)
    payloads["model.json"] = canonical_json_bytes(model_payload)
    payloads["report.md"] = _render_terminal_report(metrics)
    return payloads, verdict


def _artifact_inventory(output_dir: Path | str) -> list[dict[str, Any]]:
    output = Path(output_dir)
    rows = []
    for path in sorted(output.rglob("*"), key=lambda item: item.relative_to(output).as_posix()):
        if path.is_dir():
            continue
        relative = path.relative_to(output).as_posix()
        if relative in {".execution.lease", "artifact_manifest.json"}:
            continue
        if path.is_symlink() or relative.endswith(".tmp"):
            raise ExperimentBlocked(f"noncanonical artifact inventory entry: {relative}")
        data = path.read_bytes()
        rows.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
        )
    return rows


def publish_terminal_artifacts(
    output_dir: Path | str,
    *,
    runtime: TrainingRuntime,
    evaluation: Mapping[str, Any] | None = None,
    blocked_reason: str | None = None,
    prefix_replay_verified: bool = False,
) -> dict[str, Any]:
    """Publish a terminal result once, with the manifest installed last."""
    output = Path(output_dir)
    registration, registration_bytes, authorization, _, _ = _load_control_files(output)
    registration_sha256 = hashlib.sha256(registration_bytes).hexdigest()
    implementation_commit = registration["identity"]["implementation"]["commit"]
    logical_execution_id = authorization["logical_execution_id"]
    chain = validate_checkpoint_chain(
        output,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    checkpoint_paths = [
        output / "checkpoints" / f"checkpoint_{index:04d}.json"
        for index in range(1, len(chain) + 1)
    ]
    training = validate_training_chunk_summaries(output, checkpoint_paths)
    journal = validate_journal(output, logical_execution_id)
    if not journal or journal[-1]["phase"] in {"terminal", "blocked"}:
        raise ExperimentBlocked("terminal publication requires a nonterminal journal")
    if len(journal) != len(chain) + 1:
        raise ExperimentBlocked("terminal publication journal count mismatch")
    if chain:
        restored = restore_training_runtime(
            chain[-1],
            registration_sha256=registration_sha256,
            implementation_commit=implementation_commit,
            logical_execution_id=logical_execution_id,
        )
        if _model_state_bytes(restored.model) != _model_state_bytes(runtime.model):
            raise ExperimentBlocked("terminal runtime model differs from last checkpoint")
        if runtime.next_chunk_index != restored.next_chunk_index:
            raise ExperimentBlocked("terminal runtime coordinate differs from checkpoint")
    if blocked_reason is None:
        validate_prefix_replay_result(output)
    payloads, verdict = _terminal_payloads(
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
        runtime=runtime,
        training=training,
        evaluation=evaluation,
        blocked_reason=blocked_reason,
        prefix_replay_verified=prefix_replay_verified,
    )
    for name in payloads:
        if (output / name).exists():
            raise ExperimentBlocked(f"terminal artifact already exists: {name}")
    if (output / "artifact_manifest.json").exists():
        raise ExperimentBlocked("terminal manifest already exists")
    for name in sorted(payloads):
        _atomic_write_once(output / name, payloads[name])
    terminal_phase = "blocked" if verdict == "experiment_blocked" else "terminal"
    append_journal_record(
        output,
        phase=terminal_phase,
        logical_execution_id=logical_execution_id,
        details={
            "prefix_replay_verified": prefix_replay_verified,
            "verdict": verdict,
        },
    )
    manifest = {
        "artifact_inventory": _artifact_inventory(output),
        "authority": registration_authority(),
        "formal_readiness_verdict": FORMAL_READINESS_VERDICT,
        "logical_execution_id": logical_execution_id,
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": verdict,
    }
    _atomic_write_once(
        output / "artifact_manifest.json", canonical_json_bytes(manifest)
    )
    return manifest


def validate_terminal_artifact_directory(output_dir: Path | str) -> dict[str, Any]:
    """Validate terminal hash closure and no-authority result in-process."""
    output = Path(output_dir)
    manifest = load_canonical_json_bytes(
        (output / "artifact_manifest.json").read_bytes(), "artifact_manifest.json"
    )
    _require_keys(
        manifest,
        {
            "artifact_inventory",
            "authority",
            "formal_readiness_verdict",
            "logical_execution_id",
            "registration_sha256",
            "schema_version",
            "verdict",
        },
        "artifact manifest",
    )
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise ExperimentBlocked("terminal manifest schema mismatch")
    if manifest["verdict"] not in TERMINAL_VERDICTS:
        raise ExperimentBlocked("terminal manifest verdict mismatch")
    _validate_authority(manifest["authority"], registration_authority())
    if manifest["formal_readiness_verdict"] != FORMAL_READINESS_VERDICT:
        raise ExperimentBlocked("terminal formal readiness drifted")
    actual_inventory = _artifact_inventory(output)
    if manifest["artifact_inventory"] != actual_inventory:
        raise ExperimentBlocked("terminal artifact inventory mismatch")
    metrics = load_canonical_json_bytes(
        (output / "metrics.json").read_bytes(), "metrics.json"
    )
    if metrics.get("verdict") != manifest["verdict"]:
        raise ExperimentBlocked("terminal metrics verdict mismatch")
    if metrics.get("authority") != registration_authority():
        raise ExperimentBlocked("terminal metrics authority mismatch")
    model = load_canonical_json_bytes((output / "model.json").read_bytes(), "model.json")
    if model.get("verdict") != manifest["verdict"]:
        raise ExperimentBlocked("terminal model verdict mismatch")
    if (output / "evaluation.json").exists() != (
        manifest["verdict"] != "experiment_blocked"
    ):
        raise ExperimentBlocked("terminal evaluation inventory mismatch")
    return manifest


def verify_checkpoint_prefix_replay(
    primary_checkpoint_two: Mapping[str, Any],
    *,
    environment_factory: Callable[[int], Any],
    clock: Callable[[], float] = time.perf_counter,
) -> bool:
    """Replay two chunks and compare only the deterministic state payload bytes."""
    if primary_checkpoint_two.get("checkpoint_index") != 2:
        raise ExperimentBlocked("prefix replay requires primary checkpoint 2")
    state = dict(
        _mapping(primary_checkpoint_two.get("state_payload"), "primary state payload")
    )
    identity = dict(_mapping(state.get("identity"), "primary state identity"))
    registration_sha256 = _validate_sha256(
        identity.get("registration_sha256"), "registration_sha256"
    )
    implementation_commit = _validate_commit(
        identity.get("implementation_commit"), "implementation_commit"
    )
    logical_execution_id = _validate_execution_id(
        identity.get("logical_execution_id")
    )
    expected = _validate_checkpoint_state_payload(
        state,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    replay = initialize_training_runtime()
    primary_wall_seconds = primary_checkpoint_two.get("cumulative_wall_seconds")
    if (
        isinstance(primary_wall_seconds, bool)
        or not isinstance(primary_wall_seconds, Real)
        or not math.isfinite(float(primary_wall_seconds))
        or not 0.0 <= float(primary_wall_seconds) <= MAX_WALL_SECONDS
    ):
        raise ExperimentBlocked("prefix replay primary wall time is invalid")
    replay.cumulative_wall_seconds = float(primary_wall_seconds)
    run_registered_training_chunk(
        replay, environment_factory=environment_factory, clock=clock
    )
    run_registered_training_chunk(
        replay, environment_factory=environment_factory, clock=clock
    )
    actual = build_checkpoint_state_payload(
        replay,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    if canonical_json_bytes(actual) != canonical_json_bytes(expected):
        raise ExperimentBlocked("checkpoint prefix deterministic state payload mismatch")
    return True


def file_binding(repo_root: Path | str, relative_path: str) -> dict[str, Any]:
    """Bind one immutable repository-relative evidence input by bytes."""
    relative = _canonical_relative_path(relative_path, "binding")
    path = Path(repo_root).resolve() / Path(*PurePosixPath(relative).parts)
    data = path.read_bytes()
    if not data:
        raise ExperimentBlocked(f"bound file is empty: {relative}")
    return {
        "path": relative,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }
