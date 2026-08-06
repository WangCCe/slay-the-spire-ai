"""Independent verifier for the hierarchical simulator-learning successor.

The verifier intentionally uses only the Python standard library. It does not
import the control plane, Torch runtime, native adapter, or an environment.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import platform
import random
import re
import subprocess
import struct
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import contextmanager
from importlib import metadata as importlib_metadata
from pathlib import Path, PurePosixPath
from typing import Any


REGISTRATION_SCHEMA = "noncombat-hierarchical-simulator-learning-registration-v1"
AUTHORIZATION_SCHEMA = "noncombat-hierarchical-simulator-learning-authorization-v1"
JOURNAL_SCHEMA = "noncombat-hierarchical-simulator-learning-journal-v1"
EVIDENCE_START_SCHEMA = (
    "noncombat-hierarchical-simulator-learning-evidence-start-v1"
)
CHECKPOINT_SCHEMA = "noncombat-hierarchical-simulator-learning-checkpoint-envelope-v1"
RUNTIME_CHECKPOINT_SCHEMA = (
    "noncombat-hierarchical-simulator-learning-runtime-checkpoint-v1"
)
CHUNK_SCHEMA = "noncombat-hierarchical-simulator-learning-chunk-summary-v1"
TRAINING_ROWS_SCHEMA = "noncombat-hierarchical-simulator-learning-training-rows-v1"
EVALUATION_ARTIFACT_SCHEMA = (
    "noncombat-hierarchical-simulator-learning-evaluation-artifact-v1"
)
FINAL_MODEL_SCHEMA = "noncombat-hierarchical-simulator-learning-final-model-v1"
ISOLATION_SCHEMA = "noncombat-hierarchical-simulator-learning-isolation-v1"
METRICS_SCHEMA = "noncombat-hierarchical-simulator-learning-terminal-metrics-v1"
REPORT_SCHEMA = "noncombat-hierarchical-simulator-learning-terminal-report-v1"
TERMINAL_SCHEMA = "noncombat-hierarchical-simulator-learning-terminal-v1"
TERMINAL_INTENT_SCHEMA = (
    "noncombat-hierarchical-simulator-learning-terminal-intent-v1"
)
RESOURCE_LEDGER_SCHEMA = (
    "noncombat-hierarchical-simulator-learning-resource-ledger-v1"
)
BOOTSTRAP_RUNTIME_SCHEMA = (
    "noncombat-hierarchical-simulator-learning-bootstrap-runtime-v1"
)
MANIFEST_SCHEMA = "noncombat-hierarchical-simulator-learning-artifact-manifest-v1"
SAMPLING_VERSION = "family-first-then-conditional-v1"
EVALUATION_SELECTION = "unique-raw-score-maximum-v1"
EVALUATION_SCHEMA = "noncombat-hierarchical-simulator-learning-evaluation-v1"
TRAINING_ROW_SCHEMA = "noncombat-hierarchical-simulator-learning-training-row-v1"
BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_CONFIDENCE = 0.95
BOOTSTRAP_SEED = 0
INITIAL_RUNTIME_SHA256 = (
    "f6e79c86e442ad059fb8ec867fb261175ff3d5563b0b679999ef0d13ac4d9c9b"
)

AUTHORITY_NAMES = (
    "causal_claim_authorized",
    "cohort_materialization_authorized",
    "communication_mod_authorized",
    "environment_construction_authorized",
    "execution_authorized",
    "formal_rl_authorized",
    "fresh_evidence_authorized",
    "gameplay_authorized",
    "live_execution_authorized",
    "model_fitting_authorized",
    "native_loading_authorized",
    "ope_authorized",
    "policy_loading_authorized",
    "production_checkpoint_mutation_authorized",
    "promotion_authorized",
    "qualification_authorized",
    "seed_access_authorized",
    "target_supported_outcome_authorized",
    "training_authorized",
)
EXECUTION_ENABLED = {
    "environment_construction_authorized",
    "execution_authorized",
    "fresh_evidence_authorized",
    "model_fitting_authorized",
    "native_loading_authorized",
    "seed_access_authorized",
    "training_authorized",
}
PLANNED_SOURCE_FILES = (
    "analysis_scripts/noncombat_hierarchical_simulator_learning_experiment.py",
    "analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py",
    "analysis_scripts/verify_noncombat_hierarchical_simulator_learning_experiment.py",
    "tests/test_noncombat_hierarchical_simulator_learning_experiment.py",
    "tests/test_noncombat_hierarchical_simulator_learning_runtime.py",
)
DEFAULT_PREIMPLEMENTATION_PATH = (
    "reports/noncombat_hierarchical_simulator_learning_successor_"
    "20260806_preimplementation.json"
)
DEFAULT_STEM = "noncombat_hierarchical_simulator_learning_successor_20260806"
DEFAULT_INVENTORY_PATH = f"reports/{DEFAULT_STEM}_seed_inventory.json"
DEFAULT_PREFLIGHT_PATH = f"reports/{DEFAULT_STEM}_preflight.json"
DEFAULT_REGISTRATION_PATH = f"reports/{DEFAULT_STEM}_registration.json"
DEFAULT_AUTHORIZATION_PATH = f"reports/{DEFAULT_STEM}_authorization.json"
DEFAULT_OUTPUT_DIRECTORY = f"reports/{DEFAULT_STEM}"
RESERVED_PREVIOUS_HOLDOUT_NAME = (
    "reserved:consumed_state_conditioned_unvisited_holdout"
)
RESERVED_PREVIOUS_HOLDOUT = tuple(range(71152, 71664))
OUTPUT_INVENTORY = {
    "bootstrap_runtime": "bootstrap_runtime.json",
    "checkpoint_pattern": "checkpoints/checkpoint_{index:04d}.json",
    "compressed_training_rows": "training_rows.json.gz",
    "required_terminal_files": [
        "artifact_manifest.json",
        "authorization.json",
        "bootstrap_runtime.json",
        "evaluation.json",
        "evidence_start.json",
        "execution_journal.json",
        "final_model.json",
        "isolation.json",
        "metrics.json",
        "registration.json",
        "resource_use.json",
        "report.json",
        "terminal.json",
        "terminal_intent.json",
        "training_rows.json.gz",
    ],
}
LIMITS = {
    "episodes_per_update": 64,
    "max_decisions_per_episode": 500,
    "max_evaluation_episodes": 2560,
    "max_optimizer_updates": 64,
    "max_total_episodes": 6656,
    "max_training_episodes": 4096,
    "max_wall_seconds": 28800.0,
}
MODEL_ARCHITECTURE = {
    "architecture_id": "state-conditioned-candidate-ranker-mlp-v1",
    "candidate_input_dim": 1024,
    "device": "cpu",
    "dtype": "float32",
    "hidden_dim": 64,
    "state_conditioned": True,
    "state_input_dim": 1024,
}
TARGET_CATEGORIES = ("card_reward", "event", "route", "shop")
SATURATION_CATEGORIES = ("card_reward", "shop")
STATE_EFFECT_MINIMUM_ABSOLUTE_CHANGE = 1e-8
REGISTERED_SUPPORT_BLOCKERS = {
    "unsupported_shop_courier_restock_semantics",
}
TERMINAL_VERDICTS = {
    "experiment_blocked",
    "experiment_invalid",
    "experiment_stopped_at_canary",
    "experiment_stopped_during_training_for_family_saturation",
    "experiment_valid_with_floor_only_signal",
    "experiment_valid_with_victory_signal",
    "experiment_valid_without_learning_signal",
}
JOURNAL_TRANSITIONS = {
    "prestart_owned": {"evidence_started"},
    "evidence_started": {
        "infrastructure_interrupted",
        "invalid",
        "training_chunk_completed",
        "training_completed",
        "training_stopped_family_saturation",
    },
    "evidence_resumed": {
        "infrastructure_interrupted",
        "invalid",
        "training_chunk_completed",
        "training_completed",
        "training_stopped_family_saturation",
    },
    "training_chunk_completed": {
        "infrastructure_interrupted",
        "invalid",
        "training_chunk_completed",
        "training_completed",
        "training_stopped_family_saturation",
    },
    "training_completed": {"canary_started", "infrastructure_interrupted", "invalid"},
    "canary_started": {"canary_completed", "infrastructure_interrupted", "invalid"},
    "canary_completed": {"holdout_started", "infrastructure_interrupted", "invalid", "terminal"},
    "holdout_started": {"holdout_completed", "infrastructure_interrupted", "invalid"},
    "holdout_completed": {"invalid", "terminal"},
    "infrastructure_interrupted": {"evidence_resumed", "invalid", "terminal"},
    "training_stopped_family_saturation": {"invalid", "terminal"},
    "invalid": {"terminal"},
    "terminal": set(),
}

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_EXECUTION_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")


class VerificationError(RuntimeError):
    """Raised when terminal evidence cannot be independently trusted."""


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise VerificationError(f"non-finite JSON constant: {value}")


def canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"value is not canonical JSON: {exc}") from exc
    return (text + "\n").encode("utf-8")


def load_canonical_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{path.name} is invalid JSON") from exc
    if not isinstance(value, dict) or canonical_json_bytes(value) != payload:
        raise VerificationError(f"{path.name} is not a canonical JSON object")
    return value, payload


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationError(f"{label} must be an object")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise VerificationError(f"{label} must be a sequence")
    return value


def _exact_keys(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise VerificationError(f"{label} fields mismatch")


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VerificationError(f"{label} must be a non-negative integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise VerificationError(f"{label} must be positive")
    return result


def _finite(value: Any, label: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VerificationError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise VerificationError(f"{label} must be finite")
    return result


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise VerificationError(f"{label} must be lowercase sha256")
    return value


def _commit(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _COMMIT_RE.fullmatch(value):
        raise VerificationError(f"{label} must be a commit")
    return value


def _execution_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _EXECUTION_ID_RE.fullmatch(value):
        raise VerificationError(f"{label} is invalid")
    return value


def _canonical_relative(value: Any, label: str) -> str:
    if not isinstance(value, str) or "\\" in value:
        raise VerificationError(f"{label} path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        raise VerificationError(f"{label} path is invalid")
    return value


def _windows_path(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z]:/[^\r\n]*", value)
        or "\\" in value
    ):
        raise VerificationError(f"{label} path is invalid")
    return value


def _registration_authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def _execution_authority() -> dict[str, bool]:
    return {name: name in EXECUTION_ENABLED for name in AUTHORITY_NAMES}


def _require_all_false(value: Any, label: str) -> None:
    if value != _registration_authority():
        raise VerificationError(f"{label} authority mismatch")


def _contract() -> dict[str, Any]:
    return {
        "algorithm": {
            "conditional_entropy_coefficient": 0.01,
            "discount": 1.0,
            "family_entropy_coefficient": 0.01,
            "gradient_norm_ceiling": 1.0,
            "learning_rate": 0.001,
            "normalized_returns": True,
            "optimizer": "adam",
            "optimizer_amsgrad": False,
            "optimizer_betas": [0.9, 0.999],
            "optimizer_capturable": False,
            "optimizer_differentiable": False,
            "optimizer_eps": 1e-8,
            "optimizer_foreach": None,
            "optimizer_fused": None,
            "optimizer_maximize": False,
            "optimizer_weight_decay": 0.0,
            "sampling": SAMPLING_VERSION,
        },
        "authority": _registration_authority(),
        "canary_family_gate": {
            "categories": ["card_reward", "shop"],
            "maximum_selected_family_rate": 0.95,
            "minimum_multi_family_decisions": 32,
            "minimum_selected_families": 2,
        },
        "cohorts": {
            "canary_count": 128,
            "holdout_count": 512,
            "selection": "tracked-fixed-tree-ascending-v1",
            "train_count": 1024,
            "train_passes": 4,
        },
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
        },
        "evaluation": {
            "bootstrap_confidence": 0.95,
            "bootstrap_resamples": 10000,
            "bootstrap_seed": 0,
            "replay_each_episode_once": True,
            "selection": EVALUATION_SELECTION,
            "tie_handling": "fail-closed",
            "unsupported_rate_ceiling": 0.10,
        },
        "identity": {
            "algorithm_version": "hierarchical-family-first-reinforce-v1",
            "device": "cpu",
            "registration_schema_version": REGISTRATION_SCHEMA,
        },
        "limits": LIMITS,
        "model": {
            "architecture": "state-conditioned-candidate-ranker-mlp-v1",
            "model_seed": 0,
        },
        "reward": {
            "floor_progress_maximum": 1.0,
            "terminal_victory_weight": 2.0,
            "version": "formal-victory-primary-scalar-v1",
        },
        "state_effect_gate": {
            "minimum_absolute_relative_score_change": 1e-8,
            "minimum_multi_candidate_decisions": 4,
            "minimum_nonzero_effect_rate": 0.25,
            "minimum_relative_order_change_decisions": 1,
        },
        "training_collapse_gate": {
            "categories": ["card_reward", "shop"],
            "minimum_multi_family_decisions": 64,
            "required_singleton_max_family_rate": 1.0,
            "window_chunks": 4,
        },
    }


def _validate_binding(value: Any, label: str, *, external: bool = False) -> dict[str, Any]:
    binding = dict(_mapping(value, label))
    _exact_keys(binding, {"path", "sha256", "size_bytes"}, label)
    if external:
        _windows_path(binding["path"], label)
    else:
        _canonical_relative(binding["path"], label)
    _sha256(binding["sha256"], label)
    _positive_int(binding["size_bytes"], label)
    return binding


def _validate_isolation_identity(value: Any, label: str) -> dict[str, Any]:
    identity = dict(_mapping(value, label))
    _exact_keys(identity, {"communication_mod_config", "production_checkpoints"}, label)
    identity["communication_mod_config"] = _validate_binding(
        identity["communication_mod_config"], f"{label}.communication_mod_config", external=True
    )
    checkpoints = dict(_mapping(identity["production_checkpoints"], f"{label}.production_checkpoints"))
    _exact_keys(checkpoints, {"file_count", "root", "sha256", "size_bytes"}, f"{label}.production_checkpoints")
    _nonnegative_int(checkpoints["file_count"], f"{label}.file_count")
    _windows_path(checkpoints["root"], f"{label}.root")
    _sha256(checkpoints["sha256"], f"{label}.sha256")
    _nonnegative_int(checkpoints["size_bytes"], f"{label}.size_bytes")
    identity["production_checkpoints"] = checkpoints
    return identity


def _validate_seed_inventory(value: Any, commit: str) -> dict[str, Any]:
    inventory = dict(_mapping(value, "seed inventory"))
    _exact_keys(
        inventory,
        {
            "authority",
            "excluded_seed_count",
            "excluded_seeds",
            "repository_commit",
            "schema_version",
            "source_bindings",
            "sources",
        },
        "seed inventory",
    )
    _require_all_false(inventory["authority"], "seed inventory")
    if inventory["schema_version"] != "noncombat-hierarchical-simulator-learning-seed-inventory-v1":
        raise VerificationError("seed inventory schema mismatch")
    if inventory["repository_commit"] != commit:
        raise VerificationError("seed inventory commit mismatch")
    sources = dict(_mapping(inventory["sources"], "seed inventory sources"))
    normalized_sources: dict[str, list[int]] = {}
    for name, raw in sources.items():
        if not isinstance(name, str) or not name:
            raise VerificationError("seed source name is invalid")
        seeds = [_nonnegative_int(seed, f"seed source {name}") for seed in _sequence(raw, f"seed source {name}")]
        if seeds != sorted(set(seeds)):
            raise VerificationError("seed source values are not unique ascending")
        normalized_sources[name] = seeds
    reserved = normalized_sources.get(RESERVED_PREVIOUS_HOLDOUT_NAME)
    if reserved != list(RESERVED_PREVIOUS_HOLDOUT):
        raise VerificationError("prior untouched holdout reservation mismatch")
    excluded = [_nonnegative_int(seed, "excluded seed") for seed in _sequence(inventory["excluded_seeds"], "excluded seeds")]
    expected_excluded = sorted({seed for seeds in normalized_sources.values() for seed in seeds})
    if excluded != expected_excluded:
        raise VerificationError("excluded seed union mismatch")
    if inventory["excluded_seed_count"] != len(excluded):
        raise VerificationError("seed inventory counts mismatch")
    source_bindings = dict(_mapping(inventory["source_bindings"], "seed source bindings"))
    if set(source_bindings) != set(normalized_sources):
        raise VerificationError("seed source bindings mismatch")
    for name, binding in source_bindings.items():
        values = dict(_mapping(binding, f"seed source binding {name}"))
        if set(values) != {"sha256", "size_bytes"}:
            raise VerificationError("seed source binding fields mismatch")
        _sha256(values["sha256"], f"seed source binding {name}")
        _positive_int(values["size_bytes"], f"seed source binding {name}")
    inventory["sources"] = normalized_sources
    inventory["excluded_seeds"] = excluded
    return inventory


def _materialize_cohorts(excluded: Sequence[int]) -> dict[str, list[int]]:
    blocked = set(excluded)
    selected: list[int] = []
    candidate = 0
    while len(selected) < 1664:
        if candidate not in blocked:
            selected.append(candidate)
        candidate += 1
    return {
        "train": selected[:1024],
        "canary": selected[1024:1152],
        "holdout": selected[1152:],
    }


def _validate_registration(value: Any, payload: bytes) -> dict[str, Any]:
    registration = dict(_mapping(value, "registration"))
    _exact_keys(
        registration,
        {
            "authority",
            "cohorts",
            "contract",
            "implementation",
            "isolation_identity",
            "limits",
            "logical_experiment_id",
            "native_identity",
            "output_directory",
            "output_inventory",
            "preimplementation_binding",
            "pushed_remote_ref",
            "repository_commit",
            "runtime_identity",
            "schema_version",
            "seed_inventory",
            "seed_inventory_binding",
        },
        "registration",
    )
    if registration["schema_version"] != REGISTRATION_SCHEMA:
        raise VerificationError("registration schema mismatch")
    _require_all_false(registration["authority"], "registration")
    commit = _commit(registration["repository_commit"], "registration commit")
    _execution_id(registration["logical_experiment_id"], "logical experiment id")
    if registration["contract"] != _contract() or registration["limits"] != LIMITS:
        raise VerificationError("registration contract mismatch")
    if registration["output_directory"] != DEFAULT_OUTPUT_DIRECTORY or registration["output_inventory"] != OUTPUT_INVENTORY:
        raise VerificationError("registration output contract mismatch")
    if registration["pushed_remote_ref"] != "origin/master":
        raise VerificationError("registration pushed ref mismatch")
    implementation = dict(_mapping(registration["implementation"], "implementation"))
    _exact_keys(implementation, {"source_files", "source_sha256"}, "implementation")
    files = [_validate_binding(item, "implementation source") for item in _sequence(implementation["source_files"], "implementation sources")]
    if tuple(item["path"] for item in files) != PLANNED_SOURCE_FILES:
        raise VerificationError("implementation source allowlist mismatch")
    _sha256(implementation["source_sha256"], "implementation aggregate")
    inventory = _validate_seed_inventory(registration["seed_inventory"], commit)
    cohorts = dict(_mapping(registration["cohorts"], "registration cohorts"))
    _exact_keys(cohorts, {"train", "canary", "holdout", "selection"}, "registration cohorts")
    if cohorts["selection"] != {
        "canary_count": 128,
        "holdout_count": 512,
        "train_count": 1024,
        "train_passes": 4,
    }:
        raise VerificationError("cohort selection contract mismatch")
    normalized_cohorts = {
        name: [_nonnegative_int(seed, f"{name} seed") for seed in _sequence(cohorts[name], f"{name} seeds")]
        for name in ("train", "canary", "holdout")
    }
    if normalized_cohorts != _materialize_cohorts(inventory["excluded_seeds"]):
        raise VerificationError("registered cohorts differ from fixed ascending selection")
    native = dict(_mapping(registration["native_identity"], "native identity"))
    _exact_keys(native, {"dll_directories", "module", "provenance", "provenance_sha256"}, "native identity")
    directories = [_windows_path(path, "native DLL directory") for path in _sequence(native["dll_directories"], "native DLL directories")]
    if not directories or len(directories) != len(set(directories)):
        raise VerificationError("native DLL directories are invalid")
    _validate_binding(native["module"], "native module", external=True)
    provenance = dict(_mapping(native["provenance"], "native provenance"))
    if not provenance:
        raise VerificationError("native provenance is empty")
    provenance_sha256 = _sha256(native["provenance_sha256"], "native provenance")
    if provenance_sha256 != hashlib.sha256(canonical_json_bytes(provenance)).hexdigest():
        raise VerificationError("native provenance binding mismatch")
    runtime = dict(_mapping(registration["runtime_identity"], "runtime identity"))
    _exact_keys(runtime, {"device", "executable", "platform", "python_version", "torch_version"}, "runtime identity")
    if runtime["device"] != "cpu" or any(not isinstance(item, str) or not item for item in runtime.values()):
        raise VerificationError("runtime identity is invalid")
    _windows_path(runtime["executable"], "runtime executable")
    registration["isolation_identity"] = _validate_isolation_identity(registration["isolation_identity"], "pre isolation")
    preimplementation = _validate_binding(registration["preimplementation_binding"], "preimplementation binding")
    seed_binding = _validate_binding(registration["seed_inventory_binding"], "seed inventory binding")
    if preimplementation["path"] != DEFAULT_PREIMPLEMENTATION_PATH or seed_binding["path"] != DEFAULT_INVENTORY_PATH:
        raise VerificationError("registration input binding path mismatch")
    registration["implementation"] = {"source_files": files, "source_sha256": implementation["source_sha256"]}
    registration["seed_inventory"] = inventory
    registration["cohorts"] = {**normalized_cohorts, "selection": cohorts["selection"]}
    if canonical_json_bytes(registration) != payload:
        raise VerificationError("normalized registration differs from canonical bytes")
    return registration


def _validate_authorization(value: Any, payload: bytes, registration: Mapping[str, Any], registration_payload: bytes) -> dict[str, Any]:
    authorization = dict(_mapping(value, "authorization"))
    _exact_keys(
        authorization,
        {
            "authority",
            "authorization_id",
            "command",
            "implementation_commit",
            "logical_experiment_id",
            "registration_binding",
            "registration_commit",
            "schema_version",
        },
        "authorization",
    )
    if authorization["schema_version"] != AUTHORIZATION_SCHEMA or authorization["authority"] != _execution_authority():
        raise VerificationError("authorization schema or authority mismatch")
    logical_id = registration["logical_experiment_id"]
    if (
        authorization["logical_experiment_id"] != logical_id
        or authorization["authorization_id"] != logical_id + ":authorization-v1"
        or authorization["implementation_commit"] != registration["repository_commit"]
    ):
        raise VerificationError("authorization identity mismatch")
    _commit(authorization["registration_commit"], "authorization registration commit")
    command = list(_sequence(authorization["command"], "authorization command"))
    if not command or any(not isinstance(part, str) or not part for part in command):
        raise VerificationError("authorization command is invalid")
    binding = _validate_binding(authorization["registration_binding"], "authorization registration binding")
    if (
        binding["path"] != DEFAULT_REGISTRATION_PATH
        or binding["sha256"] != hashlib.sha256(registration_payload).hexdigest()
        or binding["size_bytes"] != len(registration_payload)
    ):
        raise VerificationError("authorization registration binding mismatch")
    if canonical_json_bytes(authorization) != payload:
        raise VerificationError("normalized authorization differs from bytes")
    return authorization


def _validate_identity(value: Any) -> dict[str, str]:
    identity = dict(_mapping(value, "execution identity"))
    _exact_keys(identity, {"authorization_sha256", "logical_execution_id", "registration_sha256"}, "execution identity")
    _sha256(identity["authorization_sha256"], "authorization identity")
    _sha256(identity["registration_sha256"], "registration identity")
    _execution_id(identity["logical_execution_id"], "logical execution identity")
    return identity


def _validate_manifest(output: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    temporaries = sorted(
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file() and path.name.endswith(".tmp")
    )
    if temporaries:
        raise VerificationError(
            "terminal output contains an unreconciled temporary: "
            + ", ".join(temporaries)
        )
    manifest, _ = load_canonical_json(output / "artifact_manifest.json")
    _exact_keys(manifest, {"artifact_count", "artifacts", "authority", "identity", "manifest_kind", "schema_version", "verdict"}, "manifest")
    if manifest["schema_version"] != MANIFEST_SCHEMA or manifest["manifest_kind"] != "full_terminal":
        raise VerificationError("manifest schema or kind mismatch")
    _require_all_false(manifest["authority"], "manifest")
    _validate_identity(manifest["identity"])
    if manifest["verdict"] not in TERMINAL_VERDICTS:
        raise VerificationError("manifest verdict is invalid")
    artifacts = list(_sequence(manifest["artifacts"], "manifest artifacts"))
    if manifest["artifact_count"] != len(artifacts):
        raise VerificationError("manifest artifact count mismatch")
    bindings: dict[str, dict[str, Any]] = {}
    paths = []
    for raw in artifacts:
        binding = dict(_mapping(raw, "manifest artifact"))
        path = _canonical_relative(binding.get("path"), "manifest artifact")
        if path in bindings:
            raise VerificationError("manifest contains duplicate paths")
        regular = {"path", "sha256", "size_bytes"}
        compressed = regular | {"canonical_sha256", "canonical_size_bytes", "compression"}
        if set(binding) != regular and set(binding) != compressed:
            raise VerificationError("manifest artifact binding fields mismatch")
        _sha256(binding["sha256"], "manifest artifact")
        _positive_int(binding["size_bytes"], "manifest artifact")
        if set(binding) == compressed:
            if path != "training_rows.json.gz" or binding["compression"] != "gzip-mtime-zero-v1":
                raise VerificationError("compressed artifact identity mismatch")
            _sha256(binding["canonical_sha256"], "canonical training rows")
            _positive_int(binding["canonical_size_bytes"], "canonical training rows")
        payload_path = output / path
        if not payload_path.is_file():
            raise VerificationError(f"manifest artifact is missing: {path}")
        payload = payload_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != binding["sha256"] or len(payload) != binding["size_bytes"]:
            raise VerificationError(f"manifest artifact binding mismatch: {path}")
        bindings[path] = binding
        paths.append(path)
    if paths != sorted(paths):
        raise VerificationError("manifest artifacts are not sorted")
    observed = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
        and path.name not in {".execution.lease", "artifact_manifest.json"}
    }
    if observed != set(bindings):
        raise VerificationError("manifest inventory differs from output files")
    if not (set(OUTPUT_INVENTORY["required_terminal_files"]) - {"artifact_manifest.json"}).issubset(observed):
        raise VerificationError("required terminal inventory is incomplete")
    return manifest, bindings


def _validate_resource_ledger(
    value: Any, *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    ledger = dict(_mapping(value, "resource ledger"))
    _exact_keys(
        ledger,
        {
            "identity",
            "last_event",
            "resource_use",
            "revision",
            "schema_version",
        },
        "resource ledger",
    )
    if ledger["schema_version"] != RESOURCE_LEDGER_SCHEMA:
        raise VerificationError("resource ledger schema mismatch")
    if _validate_identity(ledger["identity"]) != identity:
        raise VerificationError("resource ledger identity mismatch")
    revision = _nonnegative_int(ledger["revision"], "resource ledger revision")
    resources = dict(_mapping(ledger["resource_use"], "resource ledger use"))
    _exact_keys(
        resources,
        {
            "charged_seconds",
            "evaluation_episodes",
            "total_episodes",
            "training_episodes",
        },
        "resource ledger use",
    )
    charged = _finite(
        resources["charged_seconds"], "resource ledger charged seconds", minimum=0.0
    )
    for name in set(resources) - {"charged_seconds"}:
        _nonnegative_int(resources[name], f"resource ledger {name}")
    if (
        resources["total_episodes"]
        != resources["training_episodes"] + resources["evaluation_episodes"]
        or revision < resources["total_episodes"]
        or resources["training_episodes"] > LIMITS["max_training_episodes"]
        or resources["evaluation_episodes"] > LIMITS["max_evaluation_episodes"]
        or resources["total_episodes"] > LIMITS["max_total_episodes"]
        or charged > LIMITS["max_wall_seconds"]
    ):
        raise VerificationError("resource ledger accounting mismatch")
    event = ledger["last_event"]
    if revision == 0:
        if event is not None or any(resources.values()):
            raise VerificationError("initial resource ledger is not empty")
    else:
        event = dict(_mapping(event, "resource ledger event"))
        _exact_keys(event, {"kind", "phase", "seed"}, "resource ledger event")
        if event["kind"] not in {
            "checkpoint_reconciled",
            "episode_debited",
            "terminal_reconciled",
            "wall_charged",
        }:
            raise VerificationError("resource ledger event kind mismatch")
        if not isinstance(event["phase"], str) or not event["phase"]:
            raise VerificationError("resource ledger event phase mismatch")
        if event["kind"] == "episode_debited":
            _nonnegative_int(event["seed"], "resource ledger event seed")
        elif event["seed"] is not None:
            raise VerificationError("non-episode resource event has a seed")
    ledger["last_event"] = event
    ledger["resource_use"] = {
        "charged_seconds": charged,
        "evaluation_episodes": resources["evaluation_episodes"],
        "total_episodes": resources["total_episodes"],
        "training_episodes": resources["training_episodes"],
    }
    ledger["revision"] = revision
    return ledger


def _close(actual: Any, expected: float, label: str) -> float:
    value = _finite(actual, label)
    if not math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise VerificationError(f"{label} differs from recomputation")
    return value


def _softmax(values: Sequence[float]) -> list[float]:
    maximum = max(values)
    weights = [math.exp(value - maximum) for value in values]
    denominator = sum(weights)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise VerificationError("diagnostic softmax is invalid")
    return [weight / denominator for weight in weights]


def _entropy(probabilities: Sequence[float]) -> float:
    return -sum(
        probability * math.log(probability)
        for probability in probabilities
        if probability > 0.0
    )


def _margin(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    ordered = sorted(values, reverse=True)
    return ordered[0] - ordered[1]


def _sign(value: float) -> int:
    return 1 if value > 0.0 else (-1 if value < 0.0 else 0)


def _validate_optional_margin(value: Any, expected: float | None, label: str) -> None:
    if expected is None:
        if value is not None:
            raise VerificationError(f"{label} must be null")
        return
    _close(value, expected, label)


def _validate_diagnostic_row(
    value: Any,
    *,
    training: bool,
    expected_chunk: int | None,
    label: str,
) -> dict[str, Any]:
    row = dict(_mapping(value, label))
    required = {
        "candidate_scores",
        "candidates",
        "category",
        "chunk_index",
        "conditional_probabilities",
        "decision_id",
        "decision_index",
        "entropies",
        "family_order",
        "family_probabilities",
        "family_score_margin",
        "formal_reward",
        "joint_probabilities",
        "joint_probability_max_action_ids",
        "legal_action_ids",
        "multi_family",
        "raw_score_max_action_ids",
        "raw_score_max_family_ids",
        "schema_version",
        "score_greedy_action_ids",
        "score_greedy_family_ids",
        "score_margin",
        "seed",
        "selected_action_id",
        "selected_family",
        "selected_terms",
        "selection_mode",
        "state_effect",
    }
    if training:
        required.add("action_generator_state_sha256")
    allowed = required | {"unsupported_reason"}
    actual_fields = set(row)
    if actual_fields != required and actual_fields != allowed:
        raise VerificationError(f"{label} fields mismatch")
    if row["schema_version"] != TRAINING_ROW_SCHEMA:
        raise VerificationError(f"{label} schema mismatch")
    selection = SAMPLING_VERSION if training else EVALUATION_SELECTION
    if row["selection_mode"] != selection:
        raise VerificationError(f"{label} selection mode mismatch")
    if row["chunk_index"] != expected_chunk:
        raise VerificationError(f"{label} chunk coordinate mismatch")
    seed = _nonnegative_int(row["seed"], f"{label} seed")
    decision_index = _nonnegative_int(
        row["decision_index"], f"{label} decision index"
    )
    if row["decision_id"] != f"seed-{seed}:decision-{decision_index}":
        raise VerificationError(f"{label} decision identity mismatch")
    if row["category"] not in TARGET_CATEGORIES:
        raise VerificationError(f"{label} category mismatch")

    candidates = []
    action_ids = []
    candidate_families = []
    for candidate_index, raw in enumerate(
        _sequence(row["candidates"], f"{label} candidates")
    ):
        candidate = dict(_mapping(raw, f"{label} candidate[{candidate_index}]"))
        _exact_keys(
            candidate,
            {"action_id", "kind"},
            f"{label} candidate[{candidate_index}]",
        )
        action_id = candidate["action_id"]
        family = candidate["kind"]
        if not isinstance(action_id, str) or not action_id:
            raise VerificationError(f"{label} candidate action ID mismatch")
        if not isinstance(family, str) or not family:
            raise VerificationError(f"{label} candidate family mismatch")
        candidates.append(candidate)
        action_ids.append(action_id)
        candidate_families.append(family)
    if not candidates or len(set(action_ids)) != len(action_ids):
        raise VerificationError(f"{label} candidate identity mismatch")
    legal_action_ids = list(
        _sequence(row["legal_action_ids"], f"{label} legal action IDs")
    )
    if legal_action_ids != action_ids:
        raise VerificationError(f"{label} legal candidate order mismatch")
    family_order = list(_sequence(row["family_order"], f"{label} family order"))
    expected_family_order = sorted(set(candidate_families))
    if family_order != expected_family_order:
        raise VerificationError(f"{label} family order mismatch")
    if row["multi_family"] is not (len(family_order) > 1):
        raise VerificationError(f"{label} multi-family claim mismatch")

    score_mapping = dict(_mapping(row["candidate_scores"], f"{label} scores"))
    _exact_keys(score_mapping, set(action_ids), f"{label} scores")
    scores = [
        _finite(score_mapping[action_id], f"{label} score {action_id}")
        for action_id in action_ids
    ]
    family_logits = [
        max(
            score
            for score, candidate_family in zip(
                scores, candidate_families, strict=True
            )
            if candidate_family == family
        )
        for family in family_order
    ]
    expected_family_probabilities = _softmax(family_logits)
    family_probability_mapping = dict(
        _mapping(row["family_probabilities"], f"{label} family probabilities")
    )
    _exact_keys(
        family_probability_mapping,
        set(family_order),
        f"{label} family probabilities",
    )
    family_probabilities = []
    for family, expected in zip(
        family_order, expected_family_probabilities, strict=True
    ):
        family_probabilities.append(
            _close(
                family_probability_mapping[family],
                expected,
                f"{label} family probability {family}",
            )
        )

    conditional_mapping = dict(
        _mapping(
            row["conditional_probabilities"],
            f"{label} conditional probabilities",
        )
    )
    joint_mapping = dict(
        _mapping(row["joint_probabilities"], f"{label} joint probabilities")
    )
    _exact_keys(conditional_mapping, set(action_ids), f"{label} conditional probabilities")
    _exact_keys(joint_mapping, set(action_ids), f"{label} joint probabilities")
    expected_conditionals: dict[str, float] = {}
    expected_joint: dict[str, float] = {}
    conditional_entropies = []
    for family_index, family in enumerate(family_order):
        indices = [
            index
            for index, candidate_family in enumerate(candidate_families)
            if candidate_family == family
        ]
        family_conditionals = _softmax([scores[index] for index in indices])
        conditional_entropies.append(_entropy(family_conditionals))
        for index, probability in zip(indices, family_conditionals, strict=True):
            action_id = action_ids[index]
            expected_conditionals[action_id] = probability
            expected_joint[action_id] = (
                expected_family_probabilities[family_index] * probability
            )
    for action_id in action_ids:
        _close(
            conditional_mapping[action_id],
            expected_conditionals[action_id],
            f"{label} conditional probability {action_id}",
        )
        _close(
            joint_mapping[action_id],
            expected_joint[action_id],
            f"{label} joint probability {action_id}",
        )

    maximum_score = max(scores)
    raw_max_action_ids = [
        action_id
        for action_id, score in zip(action_ids, scores, strict=True)
        if score == maximum_score
    ]
    family_by_action = dict(zip(action_ids, candidate_families, strict=True))
    raw_max_family_ids = sorted(
        {family_by_action[action_id] for action_id in raw_max_action_ids}
    )
    if row["raw_score_max_action_ids"] != raw_max_action_ids:
        raise VerificationError(f"{label} raw-score maximum actions mismatch")
    if row["score_greedy_action_ids"] != raw_max_action_ids:
        raise VerificationError(f"{label} score-greedy actions mismatch")
    if row["raw_score_max_family_ids"] != raw_max_family_ids:
        raise VerificationError(f"{label} raw-score maximum families mismatch")
    if row["score_greedy_family_ids"] != raw_max_family_ids:
        raise VerificationError(f"{label} score-greedy families mismatch")
    maximum_joint = max(expected_joint.values())
    joint_max_action_ids = sorted(
        action_id
        for action_id, probability in expected_joint.items()
        if probability == maximum_joint
    )
    if row["joint_probability_max_action_ids"] != joint_max_action_ids:
        raise VerificationError(f"{label} joint maximum actions mismatch")
    _validate_optional_margin(row["score_margin"], _margin(scores), f"{label} score margin")
    _validate_optional_margin(
        row["family_score_margin"],
        _margin(family_logits),
        f"{label} family score margin",
    )

    selected_action_id = row["selected_action_id"]
    if selected_action_id not in action_ids:
        raise VerificationError(f"{label} selected action is illegal")
    selected_index = action_ids.index(selected_action_id)
    selected_family = candidate_families[selected_index]
    if row["selected_family"] != selected_family:
        raise VerificationError(f"{label} selected family mismatch")
    if not training:
        if len(raw_max_action_ids) != 1 or selected_action_id != raw_max_action_ids[0]:
            raise VerificationError(f"{label} evaluation is not raw-score greedy")
    selected_terms = dict(
        _mapping(row["selected_terms"], f"{label} selected terms")
    )
    _exact_keys(
        selected_terms,
        {
            "conditional_log_probability",
            "family_log_probability",
            "joint_log_probability",
        },
        f"{label} selected terms",
    )
    family_index = family_order.index(selected_family)
    expected_family_log = math.log(expected_family_probabilities[family_index])
    expected_conditional_log = math.log(expected_conditionals[selected_action_id])
    expected_joint_log = expected_family_log + expected_conditional_log
    _close(
        selected_terms["family_log_probability"],
        expected_family_log,
        f"{label} selected family log probability",
    )
    _close(
        selected_terms["conditional_log_probability"],
        expected_conditional_log,
        f"{label} selected conditional log probability",
    )
    _close(
        selected_terms["joint_log_probability"],
        expected_joint_log,
        f"{label} selected joint log probability",
    )

    family_entropy = _entropy(expected_family_probabilities)
    expected_conditional_entropy = sum(
        probability * entropy
        for probability, entropy in zip(
            expected_family_probabilities, conditional_entropies, strict=True
        )
    )
    joint_entropy = _entropy(list(expected_joint.values()))
    entropies = dict(_mapping(row["entropies"], f"{label} entropies"))
    _exact_keys(
        entropies,
        {"expected_conditional", "family", "joint"},
        f"{label} entropies",
    )
    _close(entropies["family"], family_entropy, f"{label} family entropy")
    _close(
        entropies["expected_conditional"],
        expected_conditional_entropy,
        f"{label} expected conditional entropy",
    )
    _close(entropies["joint"], joint_entropy, f"{label} joint entropy")
    _close(
        entropies["joint"],
        family_entropy + expected_conditional_entropy,
        f"{label} entropy identity",
    )

    state_effect = dict(_mapping(row["state_effect"], f"{label} state effect"))
    _exact_keys(
        state_effect,
        {
            "actual_scores",
            "max_abs_relative_score_change",
            "nonzero",
            "relative_order_changed",
            "zero_state_scores",
        },
        f"{label} state effect",
    )
    actual_scores = [
        _finite(item, f"{label} actual state score")
        for item in _sequence(
            state_effect["actual_scores"], f"{label} actual state scores"
        )
    ]
    zero_scores = [
        _finite(item, f"{label} zero-state score")
        for item in _sequence(
            state_effect["zero_state_scores"], f"{label} zero-state scores"
        )
    ]
    if actual_scores != scores or len(zero_scores) != len(scores):
        raise VerificationError(f"{label} state-effect score alignment mismatch")
    actual_mean = sum(actual_scores) / len(actual_scores)
    zero_mean = sum(zero_scores) / len(zero_scores)
    maximum_change = max(
        abs((actual - actual_mean) - (zero - zero_mean))
        for actual, zero in zip(actual_scores, zero_scores, strict=True)
    )
    order_changed = any(
        _sign(actual_scores[left] - actual_scores[right])
        != _sign(zero_scores[left] - zero_scores[right])
        for left in range(len(scores))
        for right in range(left + 1, len(scores))
    )
    _close(
        state_effect["max_abs_relative_score_change"],
        maximum_change,
        f"{label} state-effect maximum change",
    )
    if state_effect["nonzero"] is not (
        maximum_change >= STATE_EFFECT_MINIMUM_ABSOLUTE_CHANGE
    ):
        raise VerificationError(f"{label} state-effect nonzero claim mismatch")
    if state_effect["relative_order_changed"] is not order_changed:
        raise VerificationError(f"{label} state-effect order claim mismatch")

    reward = dict(_mapping(row["formal_reward"], f"{label} formal reward"))
    _exact_keys(
        reward,
        {"floor_progress", "scalar_reward", "terminal_victory"},
        f"{label} formal reward",
    )
    floor_progress = _finite(
        reward["floor_progress"], f"{label} floor progress", minimum=0.0
    )
    victory = reward["terminal_victory"]
    if type(victory) is not int or victory not in {0, 1}:
        raise VerificationError(f"{label} terminal victory mismatch")
    _close(
        reward["scalar_reward"],
        2.0 * victory + floor_progress,
        f"{label} scalar reward",
    )
    reason = row.get("unsupported_reason")
    if reason is not None:
        if reason not in REGISTERED_SUPPORT_BLOCKERS or reward != {
            "floor_progress": 0.0,
            "scalar_reward": 0.0,
            "terminal_victory": 0,
        }:
            raise VerificationError(f"{label} unsupported evidence mismatch")
    return row


def _validate_generator_hashes(row: Mapping[str, Any], previous_after: str | None) -> tuple[str, str]:
    if row.get("selection_mode") != SAMPLING_VERSION:
        raise VerificationError("training selection mode mismatch")
    hashes = dict(_mapping(row.get("action_generator_state_sha256"), "generator hashes"))
    _exact_keys(hashes, {"after_conditional", "after_family", "before_family"}, "generator hashes")
    for digest in hashes.values():
        _sha256(digest, "generator hash")
    if len(set(hashes.values())) != 3:
        raise VerificationError("training generator stages did not advance")
    if previous_after is not None and hashes["before_family"] != previous_after:
        raise VerificationError("training generator hash chain mismatch")
    legal = list(_sequence(row.get("legal_action_ids"), "legal action ids"))
    if not legal or row.get("selected_action_id") not in legal:
        raise VerificationError("training selected action is illegal")
    return hashes["before_family"], hashes["after_conditional"]


def _recompute_family_diagnostics(
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    categories: dict[str, Any] = {}
    for category in TARGET_CATEGORIES:
        category_rows = [row for row in rows if row["category"] == category]
        multi_family_rows = [row for row in category_rows if row["multi_family"]]
        selected_counts = Counter(
            row["selected_family"] for row in multi_family_rows
        )
        opportunity_counts: Counter[str] = Counter()
        for row in category_rows:
            for family in set(row["family_order"]):
                opportunity_counts[family] += 1
        maximum_set_counts = Counter(
            "|".join(row["raw_score_max_family_ids"])
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


def _recompute_training_objective(
    rows: Sequence[Mapping[str, Any]], episode_seeds: Sequence[int]
) -> dict[str, float]:
    ordered_rows = []
    returns = []
    for seed in episode_seeds:
        episode_rows = sorted(
            (row for row in rows if row["seed"] == seed),
            key=lambda row: row["decision_index"],
        )
        ordered_rows.extend(episode_rows)
        running = 0.0
        episode_returns = []
        for row in reversed(episode_rows):
            running = row["formal_reward"]["scalar_reward"] + running
            episode_returns.append(running)
        returns.extend(reversed(episode_returns))
    if ordered_rows != list(rows) or not returns or len(returns) != len(rows):
        raise VerificationError("training objective row order mismatch")
    float32_returns = [_float32(value) for value in returns]
    mean_return = _float32_mean(float32_returns)
    standard_deviation = _float32_population_std(
        float32_returns,
        mean=mean_return,
    )
    if abs(standard_deviation - 1e-12) <= 1e-15:
        raise VerificationError("return normalization is ambiguous at epsilon")
    normalized = (
        [
            _float32(
                _float32(value - mean_return)
                / _float32(standard_deviation + _float32(1e-8))
            )
            for value in float32_returns
        ]
        if standard_deviation > 1e-12
        else [0.0 for _ in returns]
    )
    policy_loss = -sum(
        row["selected_terms"]["joint_log_probability"] * weight
        for row, weight in zip(rows, normalized, strict=True)
    ) / len(rows)
    mean_family_entropy = sum(
        row["entropies"]["family"] for row in rows
    ) / len(rows)
    mean_conditional_entropy = sum(
        row["entropies"]["expected_conditional"] for row in rows
    ) / len(rows)
    return {
        "loss": (
            policy_loss
            - 0.01 * mean_family_entropy
            - 0.01 * mean_conditional_entropy
        ),
        "mean_expected_conditional_entropy": mean_conditional_entropy,
        "mean_family_entropy": mean_family_entropy,
        "normalized_return_mean": _float32_mean(normalized),
        "normalized_return_std": _float32_population_std(
            normalized,
            mean=_float32_mean(normalized),
        ),
        "policy_loss": policy_loss,
    }


def _close_training_summary(actual: Any, expected: float, label: str) -> None:
    value = _finite(actual, label)
    if not math.isclose(value, expected, rel_tol=2e-5, abs_tol=2e-6):
        raise VerificationError(f"{label} differs from diagnostic evidence")


def _float32(value: float) -> float:
    try:
        return struct.unpack("<f", struct.pack("<f", float(value)))[0]
    except (OverflowError, struct.error) as exc:
        raise VerificationError("float32 normalization overflowed") from exc


def _float32_sum(values: Sequence[float]) -> float:
    total = _float32(0.0)
    for value in values:
        total = _float32(total + _float32(value))
    return total


def _float32_mean(values: Sequence[float]) -> float:
    if not values:
        raise VerificationError("float32 reduction is empty")
    return _float32(_float32_sum(values) / len(values))


def _float32_population_std(
    values: Sequence[float], *, mean: float
) -> float:
    squared = [
        _float32(_float32(value - mean) * _float32(value - mean))
        for value in values
    ]
    variance = _float32(_float32_sum(squared) / len(values))
    return _float32(math.sqrt(variance))


def _validate_chunk(
    value: Any,
    index: int,
    previous_after: str | None,
    *,
    expected_seeds: Sequence[int] | None = None,
) -> tuple[dict[str, Any], str | None]:
    chunk = dict(_mapping(value, f"chunk {index}"))
    required = {
        "categories",
        "chunk_index",
        "complete",
        "conditional_entropy_coefficient",
        "decisions",
        "diagnostic_rows",
        "episode_seeds",
        "episodes",
        "family_diagnostics",
        "family_entropy_coefficient",
        "gradient_norm_after_clip",
        "gradient_norm_before_clip",
        "loss",
        "mean_expected_conditional_entropy",
        "mean_family_entropy",
        "normalized_return_mean",
        "normalized_return_std",
        "optimizer_update",
        "policy_loss",
        "resource_use",
        "schema_version",
    }
    _exact_keys(chunk, required, f"chunk {index}")
    if chunk["schema_version"] != CHUNK_SCHEMA or chunk["chunk_index"] != index or chunk["complete"] is not True:
        raise VerificationError("training chunk schema or coordinate mismatch")
    if chunk["family_entropy_coefficient"] != 0.01 or chunk["conditional_entropy_coefficient"] != 0.01:
        raise VerificationError("training chunk coefficient mismatch")
    episodes = _positive_int(chunk["episodes"], "training chunk episodes")
    if episodes != LIMITS["episodes_per_update"]:
        raise VerificationError("training chunk must contain exactly 64 episodes")
    episode_seeds = [
        _nonnegative_int(seed, f"training chunk seed[{seed_index}]")
        for seed_index, seed in enumerate(
            _sequence(chunk["episode_seeds"], "training chunk episode seeds")
        )
    ]
    if len(episode_seeds) != episodes or len(set(episode_seeds)) != episodes:
        raise VerificationError("training chunk episode seeds are invalid")
    if expected_seeds is not None and episode_seeds != list(expected_seeds):
        raise VerificationError("training chunk seed order differs from registration")
    decisions = _positive_int(chunk["decisions"], "training chunk decisions")
    rows = list(_sequence(chunk["diagnostic_rows"], "training diagnostic rows"))
    if len(rows) != decisions:
        raise VerificationError("training diagnostic count mismatch")
    current_after = previous_after
    normalized_rows = []
    decision_indexes: dict[int, list[int]] = {seed: [] for seed in episode_seeds}
    for row_index, raw in enumerate(rows):
        row = _validate_diagnostic_row(
            raw,
            training=True,
            expected_chunk=index,
            label=f"training diagnostic row[{row_index}]",
        )
        seed = row["seed"]
        if seed not in decision_indexes:
            raise VerificationError("training diagnostic contains an unregistered seed")
        decision_indexes[seed].append(row["decision_index"])
        _, current_after = _validate_generator_hashes(row, current_after)
        normalized_rows.append(row)
    if any(
        indexes != list(range(len(indexes)))
        for indexes in decision_indexes.values()
    ):
        raise VerificationError("training diagnostic decision coordinates mismatch")
    resources = dict(_mapping(chunk["resource_use"], "chunk resource use"))
    _exact_keys(resources, {"charged_seconds", "completed_decisions", "evaluation_episodes", "optimizer_updates", "total_episodes", "training_episodes"}, "chunk resource use")
    _finite(resources["charged_seconds"], "chunk charged seconds", minimum=0.0)
    for name in set(resources) - {"charged_seconds"}:
        _nonnegative_int(resources[name], f"chunk resource {name}")
    if (
        resources["evaluation_episodes"] != 0
        or resources["optimizer_updates"] != index + 1
        or resources["training_episodes"] < (index + 1) * episodes
        or resources["total_episodes"]
        != resources["training_episodes"] + resources["evaluation_episodes"]
        or resources["completed_decisions"] < decisions
    ):
        raise VerificationError("training chunk resource accounting mismatch")
    expected_categories = sorted({row["category"] for row in normalized_rows})
    if chunk["categories"] != expected_categories:
        raise VerificationError("training chunk category summary mismatch")
    expected_family_diagnostics = _recompute_family_diagnostics(normalized_rows)
    if chunk["family_diagnostics"] != expected_family_diagnostics:
        raise VerificationError("training chunk family diagnostics mismatch")
    objective = _recompute_training_objective(normalized_rows, episode_seeds)
    for name, expected in objective.items():
        _close_training_summary(
            chunk[name], expected, f"training chunk {name}"
        )
    gradient_before = _finite(
        chunk["gradient_norm_before_clip"],
        "training chunk gradient norm before clip",
        minimum=0.0,
    )
    gradient_after = _finite(
        chunk["gradient_norm_after_clip"],
        "training chunk gradient norm after clip",
        minimum=0.0,
    )
    if gradient_after > 1.0 + 1e-6 or gradient_after > gradient_before + 1e-6:
        raise VerificationError("training chunk gradient clipping mismatch")
    if chunk["optimizer_update"] != index + 1:
        raise VerificationError("training chunk optimizer coordinate mismatch")
    chunk["diagnostic_rows"] = normalized_rows
    chunk["episode_seeds"] = episode_seeds
    return chunk, current_after


def _runtime_generator_sha256(runtime: Mapping[str, Any]) -> str:
    states = _mapping(runtime["states"], "runtime states")
    tensor = dict(_mapping(states.get("action_generator"), "action generator state"))
    _exact_keys(tensor, {"dtype", "shape", "values"}, "action generator state")
    if tensor["dtype"] != "uint8":
        raise VerificationError("action generator state dtype mismatch")
    shape = [_nonnegative_int(item, "action generator shape") for item in _sequence(tensor["shape"], "action generator shape")]
    values = [_nonnegative_int(item, "action generator byte") for item in _sequence(tensor["values"], "action generator values")]
    if any(item > 255 for item in values) or len(values) != math.prod(shape):
        raise VerificationError("action generator encoded tensor is invalid")
    return hashlib.sha256(bytes(values)).hexdigest()


def _validate_encoded_tensor(value: Any, label: str) -> tuple[Any, ...]:
    tensor = dict(_mapping(value, label))
    _exact_keys(tensor, {"dtype", "shape", "values"}, label)
    if tensor["dtype"] not in {
        "bool",
        "float32",
        "float64",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
    }:
        raise VerificationError(f"{label} dtype mismatch")
    shape = tuple(
        _nonnegative_int(item, f"{label} shape")
        for item in _sequence(tensor["shape"], f"{label} shape")
    )
    values = tuple(_sequence(tensor["values"], f"{label} values"))
    if len(values) != (math.prod(shape) if shape else 1):
        raise VerificationError(f"{label} value count mismatch")
    for item in values:
        if isinstance(item, bool):
            if tensor["dtype"] != "bool":
                raise VerificationError(f"{label} value type mismatch")
        elif isinstance(item, int):
            if tensor["dtype"] == "bool":
                raise VerificationError(f"{label} value type mismatch")
        elif isinstance(item, float):
            if not tensor["dtype"].startswith("float") or not math.isfinite(item):
                raise VerificationError(f"{label} value type mismatch")
        else:
            raise VerificationError(f"{label} value type mismatch")
    return ("tensor", tensor["dtype"], shape, values)


def _decode_state_value(value: Any, label: str) -> Any:
    encoded = dict(_mapping(value, label))
    state_type = encoded.get("type")
    if state_type == "tensor":
        _exact_keys(encoded, {"type", "value"}, label)
        return _validate_encoded_tensor(encoded["value"], f"{label} tensor")
    if state_type in {"tuple", "list"}:
        _exact_keys(encoded, {"items", "type"}, label)
        items = [
            _decode_state_value(item, f"{label}[{index}]")
            for index, item in enumerate(
                _sequence(encoded["items"], f"{label} items")
            )
        ]
        return tuple(items) if state_type == "tuple" else items
    if state_type == "mapping":
        _exact_keys(encoded, {"items", "type"}, label)
        raw_items = list(_sequence(encoded["items"], f"{label} items"))
        key_bytes = []
        decoded_items = []
        for index, raw in enumerate(raw_items):
            item = dict(_mapping(raw, f"{label} item[{index}]"))
            _exact_keys(item, {"key", "value"}, f"{label} item[{index}]")
            key_bytes.append(canonical_json_bytes(item["key"]))
            decoded_items.append(
                (
                    _decode_state_value(item["key"], f"{label} key[{index}]"),
                    _decode_state_value(item["value"], f"{label} value[{index}]"),
                )
            )
        if key_bytes != sorted(key_bytes) or len(set(key_bytes)) != len(key_bytes):
            raise VerificationError(f"{label} mapping order or keys mismatch")
        result = {}
        for key, item in decoded_items:
            try:
                if key in result:
                    raise VerificationError(f"{label} contains a duplicate key")
                result[key] = item
            except TypeError as exc:
                raise VerificationError(f"{label} contains an unhashable key") from exc
        return result
    if state_type == "scalar":
        _exact_keys(encoded, {"type", "value"}, label)
        scalar = encoded["value"]
        if scalar is not None and not isinstance(scalar, (bool, int, float, str)):
            raise VerificationError(f"{label} scalar type mismatch")
        if isinstance(scalar, float) and not math.isfinite(scalar):
            raise VerificationError(f"{label} scalar is non-finite")
        return scalar
    raise VerificationError(f"{label} encoded state type mismatch")


def _validate_optimizer_state(
    value: Any,
    *,
    expected_parameter_shapes: Sequence[tuple[int, ...]] | None = None,
) -> None:
    optimizer = _decode_state_value(value, "optimizer state")
    if not isinstance(optimizer, dict) or set(optimizer) != {"param_groups", "state"}:
        raise VerificationError("optimizer state fields mismatch")
    groups = optimizer["param_groups"]
    if not isinstance(groups, list) or len(groups) != 1 or not isinstance(groups[0], dict):
        raise VerificationError("optimizer parameter groups mismatch")
    group = groups[0]
    expected_fields = {
        "amsgrad",
        "betas",
        "capturable",
        "differentiable",
        "eps",
        "foreach",
        "fused",
        "lr",
        "maximize",
        "params",
        "weight_decay",
    }
    if set(group) != expected_fields:
        raise VerificationError("optimizer parameter-group fields mismatch")
    expected_values = {
        "amsgrad": False,
        "betas": (0.9, 0.999),
        "capturable": False,
        "differentiable": False,
        "eps": 1e-8,
        "foreach": None,
        "fused": None,
        "lr": 0.001,
        "maximize": False,
        "weight_decay": 0.0,
    }
    if any(group[name] != expected for name, expected in expected_values.items()):
        raise VerificationError("optimizer semantics differ from registration")
    params = group["params"]
    if (
        not isinstance(params, list)
        or not params
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in params
        )
        or len(set(params)) != len(params)
    ):
        raise VerificationError("optimizer parameter identities mismatch")
    state = optimizer["state"]
    if not isinstance(state, dict) or any(
        isinstance(key, bool) or not isinstance(key, int) or key not in params
        for key in state
    ):
        raise VerificationError("optimizer state parameter identities mismatch")
    if expected_parameter_shapes is not None:
        expected_params = list(range(len(expected_parameter_shapes)))
        if params != expected_params or set(state) != set(expected_params):
            raise VerificationError("updated optimizer state is incomplete")
        for parameter_id, expected_shape in enumerate(expected_parameter_shapes):
            parameter_state = state[parameter_id]
            if not isinstance(parameter_state, dict) or set(parameter_state) != {
                "exp_avg",
                "exp_avg_sq",
                "step",
            }:
                raise VerificationError("Adam parameter state fields mismatch")
            step = parameter_state["step"]
            exp_avg = parameter_state["exp_avg"]
            exp_avg_sq = parameter_state["exp_avg_sq"]
            if (
                not isinstance(step, tuple)
                or step[:3] != ("tensor", "float32", ())
                or not isinstance(exp_avg, tuple)
                or exp_avg[:3] != ("tensor", "float32", expected_shape)
                or not isinstance(exp_avg_sq, tuple)
                or exp_avg_sq[:3] != ("tensor", "float32", expected_shape)
            ):
                raise VerificationError("Adam parameter tensor shape mismatch")


def _validate_python_rng_state(value: Any) -> None:
    state = _decode_state_value(value, "Python RNG state")
    if (
        not isinstance(state, tuple)
        or len(state) != 3
        or state[0] != 3
        or not isinstance(state[1], tuple)
        or len(state[1]) != 625
        or any(
            isinstance(item, bool) or not isinstance(item, int) for item in state[1]
        )
        or (state[2] is not None and not isinstance(state[2], float))
        or (isinstance(state[2], float) and not math.isfinite(state[2]))
    ):
        raise VerificationError("Python RNG state is invalid")


def _validate_runtime_checkpoint(
    value: Any,
    index: int,
    *,
    strict_model_state: bool = False,
) -> dict[str, Any]:
    runtime = dict(_mapping(value, "runtime checkpoint"))
    _exact_keys(runtime, {"algorithm", "coordinates", "model_architecture", "resource_use", "schema_version", "states"}, "runtime checkpoint")
    if runtime["schema_version"] != RUNTIME_CHECKPOINT_SCHEMA:
        raise VerificationError("runtime checkpoint schema mismatch")
    if runtime["algorithm"] != {"conditional_entropy_coefficient": 0.01, "family_entropy_coefficient": 0.01, "sampling": SAMPLING_VERSION}:
        raise VerificationError("runtime checkpoint algorithm mismatch")
    if runtime["model_architecture"] != MODEL_ARCHITECTURE:
        raise VerificationError("runtime checkpoint architecture mismatch")
    coordinates = dict(_mapping(runtime["coordinates"], "runtime coordinates"))
    _exact_keys(coordinates, {"completed_decisions", "completed_episodes", "next_chunk_index", "optimizer_updates"}, "runtime coordinates")
    for name in coordinates:
        _nonnegative_int(coordinates[name], f"runtime coordinate {name}")
    if coordinates["next_chunk_index"] != index or coordinates["optimizer_updates"] != index:
        raise VerificationError("runtime update coordinate mismatch")
    if coordinates["completed_episodes"] != index * LIMITS["episodes_per_update"]:
        raise VerificationError("runtime completed episode coordinate mismatch")
    resources = dict(_mapping(runtime["resource_use"], "runtime resources"))
    _exact_keys(resources, {"charged_seconds", "evaluation_episodes", "optimizer_updates", "total_episodes", "training_episodes"}, "runtime resources")
    charged = _finite(resources["charged_seconds"], "runtime charged seconds", minimum=0.0)
    for name in set(resources) - {"charged_seconds"}:
        _nonnegative_int(resources[name], f"runtime resource {name}")
    if (
        resources["optimizer_updates"] != index
        or resources["training_episodes"] < coordinates["completed_episodes"]
        or resources["total_episodes"] != resources["training_episodes"] + resources["evaluation_episodes"]
        or resources["training_episodes"] > LIMITS["max_training_episodes"]
        or resources["evaluation_episodes"] > LIMITS["max_evaluation_episodes"]
        or resources["total_episodes"] > LIMITS["max_total_episodes"]
        or charged > LIMITS["max_wall_seconds"]
    ):
        raise VerificationError("runtime resource accounting mismatch")
    states = dict(_mapping(runtime["states"], "runtime states"))
    _exact_keys(states, {"action_generator", "model", "optimizer", "python_rng"}, "runtime states")
    if not isinstance(states["model"], Mapping) or not states["model"]:
        raise VerificationError("runtime model state is invalid")
    expected_model_shapes = {
        "hidden.bias": (64,),
        "hidden.weight": (64, 2048),
        "scorer.bias": (1,),
        "scorer.weight": (1, 64),
    }
    if strict_model_state and set(states["model"]) != set(expected_model_shapes):
        raise VerificationError("runtime model parameter inventory mismatch")
    for name, tensor in states["model"].items():
        if not isinstance(name, str) or not name:
            raise VerificationError("runtime model parameter name is invalid")
        decoded = _validate_encoded_tensor(tensor, f"runtime model state {name}")
        if strict_model_state and decoded[:3] != (
            "tensor",
            "float32",
            expected_model_shapes[name],
        ):
            raise VerificationError("runtime model parameter shape mismatch")
    _validate_optimizer_state(
        states["optimizer"],
        expected_parameter_shapes=(
            (
                expected_model_shapes["hidden.weight"],
                expected_model_shapes["hidden.bias"],
                expected_model_shapes["scorer.weight"],
                expected_model_shapes["scorer.bias"],
            )
            if strict_model_state and index > 0
            else None
        ),
    )
    _validate_python_rng_state(states["python_rng"])
    _runtime_generator_sha256(runtime)
    return runtime


def _verify_bootstrap_runtime(
    output: Path,
    identity: Mapping[str, Any],
    *,
    strict_model_state: bool,
) -> dict[str, Any]:
    path = output / OUTPUT_INVENTORY["bootstrap_runtime"]
    if not path.is_file():
        raise VerificationError("terminal output lacks a bootstrap runtime")
    bootstrap, _ = load_canonical_json(path)
    bootstrap = dict(_mapping(bootstrap, "bootstrap runtime"))
    _exact_keys(
        bootstrap,
        {"authority", "identity", "runtime", "schema_version"},
        "bootstrap runtime",
    )
    if bootstrap["schema_version"] != BOOTSTRAP_RUNTIME_SCHEMA:
        raise VerificationError("bootstrap runtime schema mismatch")
    _require_all_false(bootstrap["authority"], "bootstrap runtime")
    if _validate_identity(bootstrap["identity"]) != identity:
        raise VerificationError("bootstrap runtime identity mismatch")
    runtime = _validate_runtime_checkpoint(
        bootstrap["runtime"],
        0,
        strict_model_state=strict_model_state,
    )
    if runtime["coordinates"] != {
        "completed_decisions": 0,
        "completed_episodes": 0,
        "next_chunk_index": 0,
        "optimizer_updates": 0,
    } or runtime["resource_use"] != {
        "charged_seconds": 0.0,
        "evaluation_episodes": 0,
        "optimizer_updates": 0,
        "total_episodes": 0,
        "training_episodes": 0,
    }:
        raise VerificationError("bootstrap runtime is not at coordinate zero")
    if (
        hashlib.sha256(canonical_json_bytes(runtime)).hexdigest()
        != INITIAL_RUNTIME_SHA256
    ):
        raise VerificationError("bootstrap runtime differs from seeded initialization")
    bootstrap["runtime"] = runtime
    return bootstrap


def _validate_terminal_resource_use(
    value: Any,
    *,
    checkpoint_resource_use: Mapping[str, Any] | None,
) -> dict[str, Any]:
    resources = dict(_mapping(value, "terminal resource use"))
    _exact_keys(
        resources,
        {
            "charged_seconds",
            "evaluation_episodes",
            "optimizer_updates",
            "total_episodes",
            "training_episodes",
        },
        "terminal resource use",
    )
    normalized = {
        "charged_seconds": _finite(
            resources["charged_seconds"], "terminal charged seconds", minimum=0.0
        ),
        **{
            name: _nonnegative_int(resources[name], f"terminal resource {name}")
            for name in (
                "evaluation_episodes",
                "optimizer_updates",
                "total_episodes",
                "training_episodes",
            )
        },
    }
    baseline = (
        dict(checkpoint_resource_use)
        if checkpoint_resource_use is not None
        else {
            "charged_seconds": 0.0,
            "evaluation_episodes": 0,
            "optimizer_updates": 0,
            "total_episodes": 0,
            "training_episodes": 0,
        }
    )
    if (
        normalized["optimizer_updates"] != baseline["optimizer_updates"]
        or normalized["training_episodes"] < baseline["training_episodes"]
        or normalized["evaluation_episodes"] < baseline["evaluation_episodes"]
        or normalized["charged_seconds"] < baseline["charged_seconds"]
        or normalized["total_episodes"]
        != normalized["training_episodes"] + normalized["evaluation_episodes"]
        or normalized["optimizer_updates"] > LIMITS["max_optimizer_updates"]
        or normalized["training_episodes"] > LIMITS["max_training_episodes"]
        or normalized["evaluation_episodes"] > LIMITS["max_evaluation_episodes"]
        or normalized["total_episodes"] > LIMITS["max_total_episodes"]
        or normalized["charged_seconds"] > LIMITS["max_wall_seconds"]
    ):
        raise VerificationError("terminal resource accounting mismatch")
    return normalized


def _verify_checkpoints(
    output: Path,
    identity: Mapping[str, Any],
    registration: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
    *,
    strict_model_state: bool,
) -> list[dict[str, Any]]:
    paths = sorted((output / "checkpoints").glob("checkpoint_*.json"))
    checkpoints = []
    previous_sha: str | None = None
    previous_generator_after: str | None = _runtime_generator_sha256(
        bootstrap["runtime"]
    )
    previous_completed_decisions = 0
    previous_training_episodes = 0
    previous_charged_seconds = 0.0
    train_sequence = (
        list(registration["cohorts"]["train"])
        * registration["contract"]["cohorts"]["train_passes"]
    )
    for index, path in enumerate(paths, start=1):
        if path.name != f"checkpoint_{index:04d}.json":
            raise VerificationError("checkpoint filenames are not contiguous")
        checkpoint, payload = load_canonical_json(path)
        _exact_keys(checkpoint, {"authority", "checkpoint_index", "complete", "identity", "previous_checkpoint_sha256", "runtime", "schema_version", "training_chunk"}, "checkpoint envelope")
        if checkpoint["schema_version"] != CHECKPOINT_SCHEMA or checkpoint["checkpoint_index"] != index or checkpoint["complete"] is not True:
            raise VerificationError("checkpoint envelope schema or coordinate mismatch")
        _require_all_false(checkpoint["authority"], "checkpoint")
        if _validate_identity(checkpoint["identity"]) != identity or checkpoint["previous_checkpoint_sha256"] != previous_sha:
            raise VerificationError("checkpoint identity or predecessor mismatch")
        runtime = _validate_runtime_checkpoint(
            checkpoint["runtime"],
            index,
            strict_model_state=strict_model_state,
        )
        start = (index - 1) * LIMITS["episodes_per_update"]
        chunk, previous_generator_after = _validate_chunk(
            checkpoint["training_chunk"],
            index - 1,
            previous_generator_after,
            expected_seeds=train_sequence[
                start : start + LIMITS["episodes_per_update"]
            ],
        )
        expected_resources = {
            "charged_seconds": runtime["resource_use"]["charged_seconds"],
            "completed_decisions": runtime["coordinates"]["completed_decisions"],
            "evaluation_episodes": runtime["resource_use"]["evaluation_episodes"],
            "optimizer_updates": runtime["resource_use"]["optimizer_updates"],
            "total_episodes": runtime["resource_use"]["total_episodes"],
            "training_episodes": runtime["resource_use"]["training_episodes"],
        }
        if chunk["resource_use"] != expected_resources:
            raise VerificationError("checkpoint chunk resource coordinate mismatch")
        if (
            runtime["coordinates"]["completed_decisions"]
            != previous_completed_decisions + chunk["decisions"]
            or runtime["resource_use"]["training_episodes"]
            < previous_training_episodes + LIMITS["episodes_per_update"]
            or runtime["resource_use"]["charged_seconds"]
            < previous_charged_seconds
        ):
            raise VerificationError("checkpoint cumulative coordinate mismatch")
        if previous_generator_after != _runtime_generator_sha256(runtime):
            raise VerificationError("checkpoint generator state does not close chunk chain")
        checkpoints.append(checkpoint)
        previous_completed_decisions = runtime["coordinates"]["completed_decisions"]
        previous_training_episodes = runtime["resource_use"]["training_episodes"]
        previous_charged_seconds = runtime["resource_use"]["charged_seconds"]
        previous_sha = hashlib.sha256(payload).hexdigest()
    return checkpoints


def _verify_training_rows(
    output: Path,
    binding: Mapping[str, Any],
    checkpoints: Sequence[Mapping[str, Any]],
    bootstrap: Mapping[str, Any],
) -> dict[str, Any]:
    required = {"path", "sha256", "size_bytes", "canonical_sha256", "canonical_size_bytes", "compression"}
    if set(binding) != required or binding["path"] != "training_rows.json.gz" or binding["compression"] != "gzip-mtime-zero-v1":
        raise VerificationError("training rows manifest binding mismatch")
    stored = (output / "training_rows.json.gz").read_bytes()
    try:
        canonical = gzip.decompress(stored)
        value = json.loads(canonical, object_pairs_hook=_reject_duplicate_pairs, parse_constant=_reject_constant)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("training rows gzip is invalid") from exc
    if not isinstance(value, dict) or canonical_json_bytes(value) != canonical:
        raise VerificationError("training rows canonical payload mismatch")
    if hashlib.sha256(canonical).hexdigest() != binding["canonical_sha256"] or len(canonical) != binding["canonical_size_bytes"]:
        raise VerificationError("training rows canonical binding mismatch")
    _exact_keys(value, {"authority", "chunk_count", "chunks", "schema_version"}, "training rows")
    if value["schema_version"] != TRAINING_ROWS_SCHEMA:
        raise VerificationError("training rows schema mismatch")
    _require_all_false(value["authority"], "training rows")
    chunks = list(_sequence(value["chunks"], "training chunks"))
    if value["chunk_count"] != len(chunks) or len(chunks) != len(checkpoints):
        raise VerificationError("training row/checkpoint count mismatch")
    previous_after: str | None = _runtime_generator_sha256(bootstrap["runtime"])
    normalized = []
    for index, raw in enumerate(chunks):
        chunk, previous_after = _validate_chunk(raw, index, previous_after)
        if chunk != checkpoints[index]["training_chunk"]:
            raise VerificationError("training row differs from checkpoint chunk")
        if previous_after != _runtime_generator_sha256(checkpoints[index]["runtime"]):
            raise VerificationError("training generator/checkpoint chain mismatch")
        normalized.append(chunk)
    value["chunks"] = normalized
    return value


def _verify_journal(
    output: Path,
    identity: Mapping[str, Any],
    checkpoints: Sequence[Mapping[str, Any]],
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    journal, _ = load_canonical_json(output / "execution_journal.json")
    _exact_keys(journal, {"identity", "records", "schema_version"}, "execution journal")
    if journal["schema_version"] != JOURNAL_SCHEMA or _validate_identity(journal["identity"]) != identity:
        raise VerificationError("execution journal identity mismatch")
    records = list(_sequence(journal["records"], "journal records"))
    if not records:
        raise VerificationError("execution journal is empty")
    previous: str | None = None
    normalized = []
    for index, raw in enumerate(records):
        record = dict(_mapping(raw, "journal record"))
        _exact_keys(record, {"details", "sequence", "state"}, "journal record")
        if record["sequence"] != index or record["state"] not in JOURNAL_TRANSITIONS or not isinstance(record["details"], Mapping):
            raise VerificationError("journal record is invalid")
        if index == 0 and record["state"] != "prestart_owned":
            raise VerificationError("journal initial state mismatch")
        if index > 0 and record["state"] not in JOURNAL_TRANSITIONS[previous]:
            raise VerificationError("journal transition mismatch")
        previous = record["state"]
        normalized.append(record)
    if normalized[-1]["state"] != "terminal":
        raise VerificationError("journal lacks terminal record")
    checkpoint_records = [record for record in normalized if record["state"] == "training_chunk_completed"]
    if [record["details"].get("checkpoint_index") for record in checkpoint_records] != list(range(1, len(checkpoints) + 1)):
        raise VerificationError("journal checkpoint coordinates mismatch")
    marker, _ = load_canonical_json(output / "evidence_start.json")
    _exact_keys(
        marker,
        {
            "authorization_sha256",
            "first_seed",
            "logical_execution_id",
            "registration_sha256",
            "schema_version",
            "state",
        },
        "evidence start",
    )
    expected_first_seed = registration["cohorts"]["train"][0]
    if (
        any(marker.get(name) != value for name, value in identity.items())
        or marker.get("state") != "evidence_started"
        or marker.get("schema_version") != EVIDENCE_START_SCHEMA
        or marker.get("first_seed") != expected_first_seed
    ):
        raise VerificationError("evidence-start identity mismatch")
    evidence_records = [record for record in normalized if record["state"] == "evidence_started"]
    if (
        len(evidence_records) != 1
        or evidence_records[0]["details"] != {"first_seed": expected_first_seed}
    ):
        raise VerificationError("evidence-start journal mismatch")
    journal["records"] = normalized
    return journal


def _family_gate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    blockers = []
    categories = {}
    for category in SATURATION_CATEGORIES:
        eligible = [row for row in rows if row.get("category") == category and row.get("multi_family") is True]
        counts: Counter[str] = Counter()
        ties = 0
        alignment = 0
        for row in eligible:
            maxima = tuple(row.get("raw_score_max_family_ids", ()))
            if len(maxima) != 1:
                ties += 1
                continue
            selected = str(row.get("selected_family"))
            if selected != maxima[0]:
                alignment += 1
                continue
            counts[selected] += 1
        largest = max(counts.values()) / len(eligible) if eligible and counts else 0.0
        if len(eligible) < 32:
            blockers.append(f"{category}_multi_family_decisions")
        if len(counts) < 2:
            blockers.append(f"{category}_selected_families")
        if largest > 0.95:
            blockers.append(f"{category}_selected_family_rate")
        if ties:
            blockers.append(f"{category}_raw_score_ties")
        if alignment:
            blockers.append(f"{category}_raw_score_alignment")
        categories[category] = {
            "alignment_failures": alignment,
            "largest_selected_family_rate": largest,
            "multi_family_decisions": len(eligible),
            "raw_score_ties": ties,
            "selected_families": dict(sorted(counts.items())),
        }
    return {"blockers": sorted(set(blockers)), "categories": categories, "passed": not blockers}


def _state_effect_gate(rows: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    summaries = {}
    blockers = []
    for category in TARGET_CATEGORIES:
        eligible = [row for row in rows if row.get("category") == category and len(row.get("candidates", ())) > 1]
        nonzero = 0
        order_changes = 0
        for row in eligible:
            effect = _mapping(row.get("state_effect"), "state effect")
            if _finite(effect.get("max_abs_relative_score_change"), "state effect", minimum=0.0) >= 1e-8:
                nonzero += 1
            order_changes += effect.get("relative_order_changed") is True
        rate = nonzero / len(eligible) if eligible else 0.0
        if len(eligible) < 4 or rate < 0.25 or order_changes < 1:
            blockers.append(f"{category}_state_effect")
        summaries[category] = {"decisions": len(eligible), "nonzero_rate": rate, "relative_order_changes": order_changes}
    return summaries, blockers


def _paired_bootstrap_interval(differences: Sequence[Any]) -> dict[str, Any]:
    values = [
        _finite(value, f"paired difference[{index}]")
        for index, value in enumerate(differences)
    ]
    if not values:
        raise VerificationError("paired differences must be nonempty")
    rng = random.Random(BOOTSTRAP_SEED)
    count = len(values)
    means = sorted(
        sum(values[rng.randrange(count)] for _ in range(count)) / count
        for _ in range(BOOTSTRAP_RESAMPLES)
    )

    def quantile(probability: float) -> float:
        position = (len(means) - 1) * probability
        lower_index = math.floor(position)
        upper_index = math.ceil(position)
        if lower_index == upper_index:
            return means[lower_index]
        weight = position - lower_index
        return means[lower_index] * (1.0 - weight) + means[upper_index] * weight

    alpha = (1.0 - BOOTSTRAP_CONFIDENCE) / 2.0
    return {
        "confidence": BOOTSTRAP_CONFIDENCE,
        "lower": quantile(alpha),
        "mean": sum(values) / count,
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "upper": quantile(1.0 - alpha),
    }


def _validate_evaluation_diagnostics(
    rows: Any,
    *,
    expected_seeds: Sequence[int],
    label: str,
) -> list[dict[str, Any]]:
    seed_set = set(expected_seeds)
    normalized = []
    decision_indexes: dict[int, list[int]] = {seed: [] for seed in expected_seeds}
    for index, raw in enumerate(_sequence(rows, label)):
        row = _validate_diagnostic_row(
            raw,
            training=False,
            expected_chunk=None,
            label=f"{label}[{index}]",
        )
        seed = row["seed"]
        if seed not in seed_set:
            raise VerificationError(f"{label} contains an unregistered seed")
        decision_index = row["decision_index"]
        decision_indexes[seed].append(decision_index)
        normalized.append(row)
    if any(indexes != list(range(len(indexes))) for indexes in decision_indexes.values()):
        raise VerificationError(f"{label} decision coordinates mismatch")
    return normalized


def _validate_episode_rows(
    rows: Any,
    *,
    diagnostics: Sequence[Mapping[str, Any]],
    expected_seeds: Sequence[int],
    label: str,
) -> list[dict[str, Any]]:
    values = [dict(_mapping(row, label)) for row in _sequence(rows, label)]
    if len(values) != len(expected_seeds):
        raise VerificationError(f"{label} count mismatch")
    normalized = []
    for index, (row, expected_seed) in enumerate(zip(values, expected_seeds, strict=True)):
        _exact_keys(
            row,
            {
                "categories",
                "decisions",
                "floor_progress",
                "formal_return",
                "seed",
                "terminal_victory",
                "unsupported_reason",
            },
            f"{label}[{index}]",
        )
        if _nonnegative_int(row["seed"], f"{label}[{index}] seed") != expected_seed:
            raise VerificationError(f"{label} seed order mismatch")
        seed_diagnostics = [item for item in diagnostics if item["seed"] == expected_seed]
        if _nonnegative_int(row["decisions"], f"{label}[{index}] decisions") != len(
            seed_diagnostics
        ):
            raise VerificationError(f"{label} decision count mismatch")
        categories = sorted({item["category"] for item in seed_diagnostics})
        if row["categories"] != categories:
            raise VerificationError(f"{label} category summary mismatch")
        expected_return = sum(
            _finite(item["formal_reward"]["scalar_reward"], "diagnostic scalar reward")
            for item in seed_diagnostics
        )
        if _finite(row["formal_return"], f"{label}[{index}] formal return") != expected_return:
            raise VerificationError(f"{label} formal return mismatch")
        expected_victory = max(
            (item["formal_reward"]["terminal_victory"] for item in seed_diagnostics),
            default=0,
        )
        if row["terminal_victory"] != expected_victory:
            raise VerificationError(f"{label} victory summary mismatch")
        _finite(row["floor_progress"], f"{label}[{index}] floor progress", minimum=0.0)
        reason = row["unsupported_reason"]
        if reason is not None and (not isinstance(reason, str) or not reason):
            raise VerificationError(f"{label} unsupported reason mismatch")
        diagnostic_reasons = [
            item.get("unsupported_reason")
            for item in seed_diagnostics
            if item.get("unsupported_reason") is not None
        ]
        if diagnostic_reasons != ([] if reason is None else [reason]):
            raise VerificationError(f"{label} unsupported evidence mismatch")
        normalized.append(row)
    return normalized


def _validate_policy_evaluation(
    value: Any,
    *,
    expected_cohort: str,
    expected_seeds: Sequence[int],
    label: str,
) -> dict[str, Any]:
    policy = dict(_mapping(value, label))
    _exact_keys(
        policy,
        {
            "categories",
            "cohort",
            "diagnostic_rows",
            "episode_rows",
            "episodes",
            "floor_progress",
            "replay_diagnostic_rows",
            "replay_episode_rows",
            "replay_exact",
            "schema_version",
            "unsupported_episodes",
            "victories",
        },
        label,
    )
    if policy["schema_version"] != EVALUATION_SCHEMA or policy["cohort"] != expected_cohort:
        raise VerificationError(f"{label} schema or cohort mismatch")
    diagnostics = _validate_evaluation_diagnostics(
        policy["diagnostic_rows"], expected_seeds=expected_seeds, label=f"{label} diagnostics"
    )
    replay_diagnostics = _validate_evaluation_diagnostics(
        policy["replay_diagnostic_rows"],
        expected_seeds=expected_seeds,
        label=f"{label} replay diagnostics",
    )
    episodes = _validate_episode_rows(
        policy["episode_rows"],
        diagnostics=diagnostics,
        expected_seeds=expected_seeds,
        label=f"{label} episodes",
    )
    replay_episodes = _validate_episode_rows(
        policy["replay_episode_rows"],
        diagnostics=replay_diagnostics,
        expected_seeds=expected_seeds,
        label=f"{label} replay episodes",
    )
    if _nonnegative_int(policy["episodes"], f"{label} episode count") != len(episodes):
        raise VerificationError(f"{label} episode count mismatch")
    expected_categories = sorted({row["category"] for row in diagnostics})
    if policy["categories"] != expected_categories:
        raise VerificationError(f"{label} categories differ from diagnostics")
    expected_floor = float(sum(row["floor_progress"] for row in episodes))
    if _finite(policy["floor_progress"], f"{label} floor progress") != expected_floor:
        raise VerificationError(f"{label} floor progress summary mismatch")
    unsupported = sum(row["unsupported_reason"] is not None for row in episodes)
    victories = sum(row["terminal_victory"] for row in episodes)
    if _nonnegative_int(policy["unsupported_episodes"], f"{label} unsupported episodes") != unsupported:
        raise VerificationError(f"{label} unsupported summary mismatch")
    if _nonnegative_int(policy["victories"], f"{label} victories") != victories:
        raise VerificationError(f"{label} victory summary mismatch")
    replay_exact = (
        canonical_json_bytes(diagnostics) == canonical_json_bytes(replay_diagnostics)
        and canonical_json_bytes(episodes) == canonical_json_bytes(replay_episodes)
    )
    if policy["replay_exact"] is not replay_exact:
        raise VerificationError(f"{label} replay claim mismatch")
    policy["diagnostic_rows"] = diagnostics
    policy["episode_rows"] = episodes
    policy["replay_diagnostic_rows"] = replay_diagnostics
    policy["replay_episode_rows"] = replay_episodes
    return policy


def _canary_gate(
    evaluation: Mapping[str, Any],
    *,
    expected_cohort: str,
    expected_seeds: Sequence[int],
) -> dict[str, Any]:
    value = dict(_mapping(evaluation, f"{expected_cohort} evaluation"))
    _exact_keys(
        value,
        {
            "cohort",
            "evaluation_episodes",
            "floor_difference_ci",
            "initial",
            "paired_rows",
            "schema_version",
            "trained",
            "unsupported_rate",
            "unsupported_rate_denominator",
        },
        f"{expected_cohort} evaluation",
    )
    if value["schema_version"] != EVALUATION_SCHEMA or value["cohort"] != expected_cohort:
        raise VerificationError(f"{expected_cohort} evaluation schema mismatch")
    seeds = [
        _nonnegative_int(seed, f"{expected_cohort} seed") for seed in expected_seeds
    ]
    initial = _validate_policy_evaluation(
        value["initial"],
        expected_cohort=expected_cohort,
        expected_seeds=seeds,
        label=f"{expected_cohort} initial",
    )
    trained = _validate_policy_evaluation(
        value["trained"],
        expected_cohort=expected_cohort,
        expected_seeds=seeds,
        label=f"{expected_cohort} trained",
    )
    if _nonnegative_int(value["evaluation_episodes"], "evaluation episode count") != 4 * len(seeds):
        raise VerificationError("evaluation episode count mismatch")
    paired_rows = [
        dict(_mapping(row, f"{expected_cohort} paired row"))
        for row in _sequence(value["paired_rows"], f"{expected_cohort} paired rows")
    ]
    if len(paired_rows) != len(seeds):
        raise VerificationError("paired row count mismatch")
    initial_by_seed = {row["seed"]: row for row in initial["episode_rows"]}
    trained_by_seed = {row["seed"]: row for row in trained["episode_rows"]}
    differences = []
    for index, (row, seed) in enumerate(zip(paired_rows, seeds, strict=True)):
        _exact_keys(
            row,
            {
                "floor_difference",
                "initial_floor_progress",
                "seed",
                "trained_floor_progress",
            },
            f"{expected_cohort} paired row[{index}]",
        )
        initial_floor = _finite(
            row["initial_floor_progress"], f"{expected_cohort} initial floor", minimum=0.0
        )
        trained_floor = _finite(
            row["trained_floor_progress"], f"{expected_cohort} trained floor", minimum=0.0
        )
        difference = _finite(row["floor_difference"], f"{expected_cohort} floor difference")
        if (
            row["seed"] != seed
            or initial_floor != initial_by_seed[seed]["floor_progress"]
            or trained_floor != trained_by_seed[seed]["floor_progress"]
            or difference != trained_floor - initial_floor
        ):
            raise VerificationError("paired floor evidence mismatch")
        differences.append(difference)
    if dict(_mapping(value["floor_difference_ci"], "floor interval")) != _paired_bootstrap_interval(differences):
        raise VerificationError("bootstrap evidence differs from registered controls")
    denominator = _positive_int(
        value["unsupported_rate_denominator"], "unsupported rate denominator"
    )
    if denominator != 2 * len(seeds):
        raise VerificationError("unsupported rate denominator mismatch")
    unsupported = initial["unsupported_episodes"] + trained["unsupported_episodes"]
    unsupported_rate = _finite(value["unsupported_rate"], "unsupported rate", minimum=0.0)
    if unsupported_rate != unsupported / denominator:
        raise VerificationError("unsupported rate evidence mismatch")
    blockers = []
    if initial.get("replay_exact") is not True or trained.get("replay_exact") is not True:
        blockers.append("exact_replay")
    if set(initial.get("categories", ())) != set(TARGET_CATEGORIES):
        blockers.append("initial_category_coverage")
    if set(trained.get("categories", ())) != set(TARGET_CATEGORIES):
        blockers.append("trained_category_coverage")
    if unsupported_rate > 0.10:
        blockers.append("unsupported_rate")
    rows = [dict(_mapping(row, "trained diagnostic row")) for row in _sequence(trained.get("diagnostic_rows"), "trained diagnostic rows")]
    if any(row.get("selected_action_id") not in row.get("legal_action_ids", ()) for row in rows):
        blockers.append("legality")
    family = _family_gate(rows)
    blockers.extend(family["blockers"])
    state_effects, state_blockers = _state_effect_gate(rows)
    blockers.extend(state_blockers)
    initial_victories = _nonnegative_int(initial.get("victories"), "initial victories")
    trained_victories = _nonnegative_int(trained.get("victories"), "trained victories")
    if trained_victories < initial_victories:
        blockers.append("victory_noninferiority")
    interval = _mapping(value["floor_difference_ci"], "floor interval")
    if _finite(interval.get("lower"), "floor lower bound") <= 0.0:
        blockers.append("paired_floor_lower_bound")
    unique = sorted(set(blockers))
    return {"blockers": unique, "family_gate": family, "passed": not unique, "state_effects": state_effects}


def _saturation(chunks: Sequence[Mapping[str, Any]]) -> bool:
    if len(chunks) < 4:
        return False
    rows = [row for chunk in chunks[-4:] for row in chunk["diagnostic_rows"]]
    for category in SATURATION_CATEGORIES:
        eligible = [row for row in rows if row.get("category") == category and row.get("multi_family") is True]
        maxima = [tuple(row.get("raw_score_max_family_ids", ())) for row in eligible]
        if len(eligible) >= 64 and all(len(item) == 1 for item in maxima) and len({item[0] for item in maxima}) == 1:
            return True
    return False


def _expected_evaluation_verdict(
    evaluation: Mapping[str, Any], registration: Mapping[str, Any]
) -> str:
    canary = _mapping(evaluation.get("canary"), "canary evaluation")
    calculated_canary = _canary_gate(
        canary,
        expected_cohort="canary",
        expected_seeds=registration["cohorts"]["canary"],
    )
    if evaluation.get("canary_gate") != calculated_canary:
        raise VerificationError("recorded canary gate differs from evidence")
    holdout = _mapping(evaluation.get("holdout"), "holdout result")
    if not calculated_canary["passed"]:
        if holdout != {"accessed": False, "episode_count": 0}:
            raise VerificationError("failed canary accessed holdout")
        return "experiment_stopped_at_canary"
    if holdout.get("accessed") is not True:
        raise VerificationError("passed canary lacks holdout")
    holdout_evaluation = _mapping(holdout.get("evaluation"), "holdout evaluation")
    calculated_holdout = _canary_gate(
        holdout_evaluation,
        expected_cohort="holdout",
        expected_seeds=registration["cohorts"]["holdout"],
    )
    if holdout.get("episode_count") != holdout_evaluation.get("evaluation_episodes"):
        raise VerificationError("holdout episode count mismatch")
    if holdout.get("gate") != calculated_holdout or holdout.get("family_gate") != calculated_holdout["family_gate"]:
        raise VerificationError("recorded holdout gates differ from evidence")
    blockers = set(calculated_holdout["blockers"])
    structural = {"exact_replay", "initial_category_coverage", "trained_category_coverage", "legality"}
    if blockers.intersection(structural):
        return "experiment_invalid"
    behavior_valid = not (blockers - structural - {"paired_floor_lower_bound"})
    lower = _finite(_mapping(holdout_evaluation.get("floor_difference_ci"), "holdout floor interval").get("lower"), "holdout floor lower")
    initial_victories = _nonnegative_int(_mapping(holdout_evaluation.get("initial"), "holdout initial").get("victories"), "holdout initial victories")
    trained_victories = _nonnegative_int(_mapping(holdout_evaluation.get("trained"), "holdout trained").get("victories"), "holdout trained victories")
    if not behavior_valid or lower <= 0.0 or trained_victories < initial_victories:
        return "experiment_valid_without_learning_signal"
    if trained_victories > initial_victories:
        return "experiment_valid_with_victory_signal"
    return "experiment_valid_with_floor_only_signal"


def _verify_terminal_artifacts(
    output: Path,
    manifest: Mapping[str, Any],
    bindings: Mapping[str, Mapping[str, Any]],
    identity: Mapping[str, Any],
    registration: Mapping[str, Any],
    bootstrap: Mapping[str, Any] | None,
    checkpoints: Sequence[Mapping[str, Any]],
    training_rows: Mapping[str, Any],
    journal: Mapping[str, Any],
    resource_ledger: Mapping[str, Any],
) -> str:
    evaluation_wrapper, _ = load_canonical_json(output / "evaluation.json")
    final_model, _ = load_canonical_json(output / "final_model.json")
    isolation, _ = load_canonical_json(output / "isolation.json")
    metrics, _ = load_canonical_json(output / "metrics.json")
    report, _ = load_canonical_json(output / "report.json")
    terminal, _ = load_canonical_json(output / "terminal.json")
    terminal_intent, _ = load_canonical_json(output / "terminal_intent.json")
    _exact_keys(evaluation_wrapper, {"authority", "evaluation", "schema_version"}, "evaluation artifact")
    if evaluation_wrapper["schema_version"] != EVALUATION_ARTIFACT_SCHEMA:
        raise VerificationError("evaluation artifact schema mismatch")
    _require_all_false(evaluation_wrapper["authority"], "evaluation artifact")
    _exact_keys(final_model, {"authority", "model", "model_loading_authorized", "schema_version"}, "final model")
    if final_model["schema_version"] != FINAL_MODEL_SCHEMA or final_model["model_loading_authorized"] is not False or not isinstance(final_model["model"], Mapping) or not final_model["model"]:
        raise VerificationError("final model artifact mismatch")
    _require_all_false(final_model["authority"], "final model")
    _exact_keys(isolation, {"authority", "post", "pre", "schema_version", "unchanged"}, "isolation")
    if isolation["schema_version"] != ISOLATION_SCHEMA:
        raise VerificationError("isolation schema mismatch")
    _require_all_false(isolation["authority"], "isolation")
    pre = _validate_isolation_identity(isolation["pre"], "terminal pre isolation")
    post = _validate_isolation_identity(isolation["post"], "terminal post isolation")
    unchanged = pre == post == registration["isolation_identity"]
    if isolation["unchanged"] is not unchanged:
        raise VerificationError("isolation unchanged claim mismatch")
    _exact_keys(metrics, {"authority", "checkpoint_count", "formal_rl_readiness_established", "isolation_unchanged", "policy_quality_established", "resource_use", "schema_version", "target_supported_outcomes_established", "training_chunk_count", "verdict"}, "metrics")
    if metrics["schema_version"] != METRICS_SCHEMA:
        raise VerificationError("metrics schema mismatch")
    _require_all_false(metrics["authority"], "metrics")
    if any(metrics[name] is not False for name in ("formal_rl_readiness_established", "policy_quality_established", "target_supported_outcomes_established")):
        raise VerificationError("metrics grants downstream authority")
    _exact_keys(report, {"authority", "formal_rl_readiness", "logical_execution_id", "policy_quality_claim", "schema_version", "target_supported_outcome_claim", "verdict"}, "report")
    if report["schema_version"] != REPORT_SCHEMA or report["formal_rl_readiness"] != "unchanged_not_ready" or report["policy_quality_claim"] is not False or report["target_supported_outcome_claim"] is not False:
        raise VerificationError("report claim boundary mismatch")
    _require_all_false(report["authority"], "report")
    _exact_keys(terminal, {"authority", "checkpoint_count", "holdout_accessed", "identity", "reason", "schema_version", "training_rows_binding", "verdict"}, "terminal")
    if terminal["schema_version"] != TERMINAL_SCHEMA or _validate_identity(terminal["identity"]) != identity:
        raise VerificationError("terminal schema or identity mismatch")
    _require_all_false(terminal["authority"], "terminal")
    _exact_keys(
        terminal_intent,
        {
            "algorithm_verdict",
            "authority",
            "evaluation",
            "final_model",
            "holdout_accessed",
            "identity",
            "isolation_post",
            "reason",
            "resource_use",
            "schema_version",
        },
        "terminal intent",
    )
    if (
        terminal_intent["schema_version"] != TERMINAL_INTENT_SCHEMA
        or _validate_identity(terminal_intent["identity"]) != identity
        or terminal_intent["algorithm_verdict"] not in TERMINAL_VERDICTS
        or not isinstance(terminal_intent["reason"], str)
        or not terminal_intent["reason"]
        or type(terminal_intent["holdout_accessed"]) is not bool
    ):
        raise VerificationError("terminal intent schema or identity mismatch")
    _require_all_false(terminal_intent["authority"], "terminal intent")
    verdict = terminal["verdict"]
    if verdict not in TERMINAL_VERDICTS:
        raise VerificationError("terminal verdict is invalid")
    if not isinstance(terminal["reason"], str) or not terminal["reason"]:
        raise VerificationError("terminal reason is invalid")
    if terminal["training_rows_binding"] != bindings["training_rows.json.gz"]:
        raise VerificationError("terminal training rows binding mismatch")
    if checkpoints:
        durable_model = checkpoints[-1]["runtime"]["states"]["model"]
        model_label = "latest checkpoint"
    else:
        if bootstrap is None:
            raise VerificationError("zero-checkpoint output lacks a bootstrap runtime")
        durable_model = bootstrap["runtime"]["states"]["model"]
        model_label = "bootstrap runtime"
    if final_model["model"] != durable_model:
        raise VerificationError(f"final model differs from the {model_label}")
    if terminal["checkpoint_count"] != len(checkpoints) or metrics["checkpoint_count"] != len(checkpoints) or metrics["training_chunk_count"] != training_rows["chunk_count"]:
        raise VerificationError("terminal checkpoint coordinates mismatch")
    expected_resources = _validate_terminal_resource_use(
        metrics["resource_use"],
        checkpoint_resource_use=(
            checkpoints[-1]["runtime"]["resource_use"] if checkpoints else None
        ),
    )
    if metrics["resource_use"] != expected_resources:
        raise VerificationError("terminal resource normalization mismatch")
    ledger_resources = resource_ledger["resource_use"]
    if ledger_resources != {
        "charged_seconds": expected_resources["charged_seconds"],
        "evaluation_episodes": expected_resources["evaluation_episodes"],
        "total_episodes": expected_resources["total_episodes"],
        "training_episodes": expected_resources["training_episodes"],
    }:
        raise VerificationError("terminal resources differ from the resource ledger")
    if (
        terminal_intent["evaluation"] != evaluation_wrapper["evaluation"]
        or terminal_intent["final_model"] != final_model["model"]
        or terminal_intent["resource_use"] != metrics["resource_use"]
        or _validate_isolation_identity(
            terminal_intent["isolation_post"], "terminal intent isolation"
        )
        != post
        or terminal_intent["holdout_accessed"]
        is not terminal["holdout_accessed"]
    ):
        raise VerificationError("terminal intent differs from terminal artifacts")
    if metrics["isolation_unchanged"] is not unchanged:
        raise VerificationError("metrics isolation claim mismatch")
    if report["logical_execution_id"] != identity["logical_execution_id"]:
        raise VerificationError("report logical identity mismatch")
    if not (
        manifest["verdict"]
        == metrics["verdict"]
        == report["verdict"]
        == verdict
        == journal["records"][-1]["details"].get("verdict")
    ):
        raise VerificationError("terminal verdict surfaces disagree")
    evaluation = evaluation_wrapper["evaluation"]
    previous_state = journal["records"][-2]["state"]
    journal_holdout_accessed = any(
        record["state"] in {"holdout_started", "holdout_completed"}
        for record in journal["records"]
    )
    if not unchanged:
        if (
            terminal["reason"]
            != terminal_intent["reason"] + "; production isolation changed"
        ):
            raise VerificationError("isolation-invalid terminal reason mismatch")
        if verdict != "experiment_invalid" or previous_state != "invalid":
            raise VerificationError("changed production isolation is not invalid")
        if evaluation is None:
            observed_holdout_access = journal_holdout_accessed
        else:
            evaluation_value = dict(_mapping(evaluation, "terminal evaluation"))
            expected_evaluation_verdict = _expected_evaluation_verdict(
                evaluation_value, registration
            )
            if evaluation_value.get("verdict") != expected_evaluation_verdict:
                raise VerificationError("isolation-invalid evaluation evidence drifted")
            observed_holdout_access = (
                _mapping(
                    evaluation_value.get("holdout"), "evaluation holdout"
                ).get("accessed")
                is True
            )
        if (
            terminal["holdout_accessed"] is not observed_holdout_access
            or observed_holdout_access is not journal_holdout_accessed
        ):
            raise VerificationError("isolation-invalid holdout access mismatch")
    elif verdict == "experiment_blocked":
        if terminal_intent["algorithm_verdict"] != verdict or terminal_intent["reason"] != terminal["reason"]:
            raise VerificationError("blocked terminal intent mismatch")
        if (
            evaluation is not None
            or previous_state != "infrastructure_interrupted"
            or terminal["holdout_accessed"] is not journal_holdout_accessed
        ):
            raise VerificationError("blocked terminal evidence mismatch")
    elif verdict == "experiment_stopped_during_training_for_family_saturation":
        if terminal_intent["algorithm_verdict"] != verdict or terminal_intent["reason"] != terminal["reason"]:
            raise VerificationError("training saturation terminal intent mismatch")
        if evaluation is not None or previous_state != "training_stopped_family_saturation" or terminal["holdout_accessed"] is not False or journal_holdout_accessed or not _saturation(training_rows["chunks"]):
            raise VerificationError("training saturation terminal mismatch")
    elif verdict == "experiment_invalid" and evaluation is None:
        if terminal_intent["algorithm_verdict"] != verdict or terminal_intent["reason"] != terminal["reason"]:
            raise VerificationError("invalid terminal intent mismatch")
        if previous_state != "invalid" or terminal["holdout_accessed"] is not journal_holdout_accessed:
            raise VerificationError("invalid terminal evidence mismatch")
    else:
        if terminal_intent["algorithm_verdict"] != verdict or terminal_intent["reason"] != terminal["reason"]:
            raise VerificationError("evaluated terminal intent mismatch")
        evaluation_value = dict(_mapping(evaluation, "terminal evaluation"))
        expected_verdict = _expected_evaluation_verdict(
            evaluation_value, registration
        )
        if evaluation_value.get("verdict") != expected_verdict or verdict != expected_verdict:
            raise VerificationError("evaluation verdict mismatch")
        holdout_accessed = _mapping(evaluation_value.get("holdout"), "evaluation holdout").get("accessed") is True
        if (
            terminal["holdout_accessed"] is not holdout_accessed
            or holdout_accessed is not journal_holdout_accessed
        ):
            raise VerificationError("terminal holdout access mismatch")
    return verdict


def _lock_lease(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_lease(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _hold_output_inactive(output: Path):
    lease = output / ".execution.lease"
    if not lease.is_file():
        raise VerificationError("execution lease file is missing")
    with lease.open("r+b", buffering=0) as handle:
        try:
            _lock_lease(handle)
        except OSError as exc:
            raise VerificationError("output is owned by an active execution") from exc
        try:
            yield
        finally:
            _unlock_lease(handle)


def _snapshot(output: Path) -> tuple[tuple[str, int, str], ...]:
    return tuple(
        (
            path.relative_to(output).as_posix(),
            len(payload := path.read_bytes()),
            hashlib.sha256(payload).hexdigest(),
        )
        for path in sorted(
            (
                candidate
                for candidate in output.rglob("*")
                if candidate.is_file()
                and candidate.name != ".execution.lease"
            ),
            key=lambda candidate: candidate.relative_to(output).as_posix(),
        )
    )


def _git_text(root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(f"Git identity command failed: {' '.join(args)}") from exc
    return completed.stdout.strip()


def _git_bytes(root: Path, commit: str, path: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(f"Git artifact is missing: {commit}:{path}") from exc


def _hash_named_bytes(rows: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in rows:
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _seed_scalars(value: Any) -> list[int]:
    result: list[int] = []

    def visit(node: Any, seed_context: bool) -> None:
        if isinstance(node, Mapping):
            for key in sorted(node):
                if not isinstance(key, str):
                    continue
                folded = key.casefold()
                visit(
                    node[key],
                    seed_context or "seed" in folded or folded == "cohorts",
                )
            return
        if isinstance(node, list):
            for child in node:
                visit(child, seed_context)
            return
        if not seed_context or isinstance(node, bool):
            return
        if isinstance(node, int) and node >= 0:
            result.append(node)
        elif isinstance(node, str) and node.isascii() and node.isdigit():
            result.append(int(node))

    visit(value, False)
    return result


def _recompute_tracked_seed_inventory(
    root: Path, *, repository_commit: str
) -> dict[str, Any]:
    ignored = {
        DEFAULT_AUTHORIZATION_PATH,
        DEFAULT_INVENTORY_PATH,
        DEFAULT_PREFLIGHT_PATH,
        DEFAULT_REGISTRATION_PATH,
    }
    candidates = []
    for raw_path in _git_text(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        repository_commit,
        "--",
        "reports",
    ).splitlines():
        path = raw_path.replace("\\", "/")
        if (
            not path.endswith(".json")
            or path in ignored
            or path.startswith(f"{DEFAULT_OUTPUT_DIRECTORY}/")
        ):
            continue
        candidates.append(_canonical_relative(path, "tracked seed source"))

    sources: dict[str, list[int]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    for path in sorted(set(candidates)):
        payload = _git_bytes(root, repository_commit, path)
        try:
            value = json.loads(
                payload,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VerificationError(
                f"tracked seed source is invalid JSON: {path}"
            ) from exc
        seeds = sorted(set(_seed_scalars(value)))
        if not seeds:
            continue
        sources[path] = seeds
        bindings[path] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }

    reserved = list(RESERVED_PREVIOUS_HOLDOUT)
    sources[RESERVED_PREVIOUS_HOLDOUT_NAME] = reserved
    reserved_payload = canonical_json_bytes(reserved)
    bindings[RESERVED_PREVIOUS_HOLDOUT_NAME] = {
        "sha256": hashlib.sha256(reserved_payload).hexdigest(),
        "size_bytes": len(reserved_payload),
    }
    sources = dict(sorted(sources.items()))
    bindings = {name: bindings[name] for name in sources}
    excluded = sorted({seed for seeds in sources.values() for seed in seeds})
    return {
        "authority": _registration_authority(),
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": repository_commit,
        "schema_version": (
            "noncombat-hierarchical-simulator-learning-seed-inventory-v1"
        ),
        "source_bindings": bindings,
        "sources": sources,
    }


def _verify_repository_identity(
    repo_root: Path | str,
    *,
    registration: Mapping[str, Any],
    registration_payload: bytes,
    authorization: Mapping[str, Any],
    authorization_payload: bytes,
) -> None:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise VerificationError("repository root is missing")
    head = _git_text(root, "rev-parse", "HEAD")
    pushed = _git_text(root, "rev-parse", "origin/master")
    if head != pushed or _git_text(
        root, "status", "--porcelain", "--untracked-files=no"
    ):
        raise VerificationError("repository is not at a clean pushed identity")
    implementation_commit = registration["repository_commit"]
    registration_commit = authorization["registration_commit"]
    _git_text(
        root,
        "merge-base",
        "--is-ancestor",
        implementation_commit,
        registration_commit,
    )
    _git_text(
        root,
        "merge-base",
        "--is-ancestor",
        registration_commit,
        pushed,
    )
    if (
        _git_bytes(root, registration_commit, DEFAULT_REGISTRATION_PATH)
        != registration_payload
        or _git_bytes(root, pushed, DEFAULT_AUTHORIZATION_PATH)
        != authorization_payload
    ):
        raise VerificationError("pushed control artifact bytes differ")
    source_rows = [
        (path, _git_bytes(root, implementation_commit, path))
        for path in PLANNED_SOURCE_FILES
    ]
    expected_files = registration["implementation"]["source_files"]
    actual_files = [
        {
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
        for path, payload in source_rows
    ]
    if (
        actual_files != expected_files
        or _hash_named_bytes(source_rows)
        != registration["implementation"]["source_sha256"]
    ):
        raise VerificationError("implementation Git tree differs from registration")
    preimplementation = registration["preimplementation_binding"]
    seed_inventory = registration["seed_inventory_binding"]
    bound_payloads = {}
    for binding, commit in (
        (preimplementation, implementation_commit),
        (seed_inventory, registration_commit),
    ):
        payload = _git_bytes(root, commit, binding["path"])
        if (
            hashlib.sha256(payload).hexdigest() != binding["sha256"]
            or len(payload) != binding["size_bytes"]
        ):
            raise VerificationError("registered source artifact binding differs")
        bound_payloads[binding["path"]] = payload
    inventory_payload = bound_payloads[seed_inventory["path"]]
    try:
        inventory_value = json.loads(
            inventory_payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("seed inventory artifact is invalid JSON") from exc
    if (
        not isinstance(inventory_value, Mapping)
        or canonical_json_bytes(inventory_value) != inventory_payload
    ):
        raise VerificationError("seed inventory artifact is not canonical")
    normalized_inventory = _validate_seed_inventory(
        inventory_value,
        implementation_commit,
    )
    if normalized_inventory != registration["seed_inventory"]:
        raise VerificationError("seed inventory artifact differs from registration")
    recomputed_inventory = _recompute_tracked_seed_inventory(
        root,
        repository_commit=implementation_commit,
    )
    if recomputed_inventory != normalized_inventory:
        raise VerificationError("seed inventory differs from fixed Git tree")
    native = registration["native_identity"]["module"]
    native_path = Path(native["path"])
    try:
        native_payload = native_path.read_bytes()
    except OSError as exc:
        raise VerificationError("registered native module is unreadable") from exc
    if (
        hashlib.sha256(native_payload).hexdigest() != native["sha256"]
        or len(native_payload) != native["size_bytes"]
    ):
        raise VerificationError("registered native module bytes differ")
    runtime = registration["runtime_identity"]
    expected_command = [
        runtime["executable"],
        (root / PLANNED_SOURCE_FILES[0]).resolve().as_posix(),
        "execute",
        "--repo-root",
        root.as_posix(),
        "--registration",
        (root / DEFAULT_REGISTRATION_PATH).resolve().as_posix(),
        "--authorization",
        (root / DEFAULT_AUTHORIZATION_PATH).resolve().as_posix(),
        "--output-dir",
        (root / DEFAULT_OUTPUT_DIRECTORY).resolve().as_posix(),
    ]
    if authorization["command"] != expected_command:
        raise VerificationError("authorization command differs from canonical argv")
    try:
        torch_version = importlib_metadata.version("torch")
    except (importlib_metadata.PackageNotFoundError, OSError) as exc:
        raise VerificationError("verification Torch package metadata is unavailable") from exc
    if (
        Path(sys.executable).resolve().as_posix().casefold()
        != runtime["executable"].casefold()
        or sys.platform != runtime["platform"]
        or platform.python_version() != runtime["python_version"]
        or torch_version != runtime["torch_version"]
    ):
        raise VerificationError("verification runtime differs from registration")


def _verify_output(
    output_path: Path | str,
    *,
    repo_root: Path | str | None,
    verification: str,
) -> dict[str, Any]:
    output = Path(output_path).resolve()
    if not output.is_dir():
        raise VerificationError("terminal output directory is missing")
    with _hold_output_inactive(output):
        before = _snapshot(output)
        manifest, bindings = _validate_manifest(output)
        registration, registration_payload = load_canonical_json(
            output / "registration.json"
        )
        registration = _validate_registration(registration, registration_payload)
        authorization, authorization_payload = load_canonical_json(
            output / "authorization.json"
        )
        authorization = _validate_authorization(
            authorization,
            authorization_payload,
            registration=registration,
            registration_payload=registration_payload,
        )
        if repo_root is not None:
            _verify_repository_identity(
                repo_root,
                registration=registration,
                registration_payload=registration_payload,
                authorization=authorization,
                authorization_payload=authorization_payload,
            )
        identity = {
            "authorization_sha256": hashlib.sha256(
                authorization_payload
            ).hexdigest(),
            "logical_execution_id": registration["logical_experiment_id"],
            "registration_sha256": hashlib.sha256(
                registration_payload
            ).hexdigest(),
        }
        if _validate_identity(manifest["identity"]) != identity:
            raise VerificationError("manifest execution identity mismatch")
        resource_ledger_value, _ = load_canonical_json(
            output / "resource_use.json"
        )
        resource_ledger = _validate_resource_ledger(
            resource_ledger_value,
            identity=identity,
        )
        bootstrap = _verify_bootstrap_runtime(
            output,
            identity,
            strict_model_state=repo_root is not None,
        )
        checkpoints = _verify_checkpoints(
            output,
            identity,
            registration,
            bootstrap,
            strict_model_state=repo_root is not None,
        )
        training_rows = _verify_training_rows(
            output,
            bindings["training_rows.json.gz"],
            checkpoints,
            bootstrap,
        )
        journal = _verify_journal(output, identity, checkpoints, registration)
        verdict = _verify_terminal_artifacts(
            output,
            manifest,
            bindings,
            identity,
            registration,
            bootstrap,
            checkpoints,
            training_rows,
            journal,
            resource_ledger,
        )
        if _snapshot(output) != before:
            raise VerificationError("terminal output changed during verification")
    return {
        "artifact_count": manifest["artifact_count"],
        "checkpoint_count": len(checkpoints),
        "logical_execution_id": identity["logical_execution_id"],
        "repository_identity_verified": repo_root is not None,
        "training_chunk_count": training_rows["chunk_count"],
        "verdict": verdict,
        "verification": verification,
    }


def verify_artifact_output(output_path: Path | str) -> dict[str, Any]:
    """Verify artifact internals without claiming repository identity."""
    return _verify_output(
        output_path,
        repo_root=None,
        verification="artifact_verified",
    )


def verify_output(
    output_path: Path | str, *, repo_root: Path | str
) -> dict[str, Any]:
    """Fully verify one inactive terminal output and its repository identity."""
    if repo_root is None:
        raise VerificationError("full verification requires a repository root")
    return _verify_output(
        output_path,
        repo_root=repo_root,
        verification="verified",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--repo-root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(json.dumps(verify_output(args.output, repo_root=args.repo_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
