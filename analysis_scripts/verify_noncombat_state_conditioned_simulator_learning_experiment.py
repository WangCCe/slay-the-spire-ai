"""Standard-library verifier for state-conditioned simulator evidence."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import random
import re
import statistics
import struct
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


MANIFEST_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-manifest-v2"
)
FULL_TERMINAL_ARTIFACT_NAMES = frozenset(
    {
        "authorization.json",
        "configuration.json",
        "diagnostics.json",
        "evaluation.json",
        "execution_journal.json",
        "final_model.json",
        "isolation.json",
        "metrics.json",
        "registration.json",
        "report.json",
        "training_rows.json",
    }
)
FULL_TERMINAL_ARTIFACT_CASEFOLDS = frozenset(
    name.casefold() for name in FULL_TERMINAL_ARTIFACT_NAMES
)
REGISTRATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-registration-v1"
)
AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-authorization-v1"
)
CONFIGURATION_SCHEMA_VERSION = "noncombat-state-conditioned-configuration-v1"
CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-checkpoint-v1"
)
JOURNAL_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-journal-v2"
)
EVALUATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-paired-evaluation-v1"
)
SEED_INVENTORY_SCHEMA_VERSION = (
    "noncombat-state-conditioned-seed-exclusion-inventory-v1"
)
ALGORITHM_VERSION = "state-conditioned-candidate-masked-reinforce-v1"
REWARD_VERSION = "formal-victory-primary-scalar-v1"
FEATURE_VERSION = "noncombat-state-conditioned-policy-features-v1"
ARCHITECTURE_ID = "state-conditioned-candidate-ranker-mlp-v1"
OUTPUT_ROOT_PREFIX = (
    "reports/noncombat_state_conditioned_simulator_learning_experiment_"
)
PUSHED_REMOTE_REF = "origin/master"
TARGET_CATEGORIES = ("card_reward", "event", "route", "shop")
REGISTERED_SUPPORT_BLOCKERS = {
    "unsupported_shop_courier_restock_semantics",
}
CARD_REWARD_KINDS = ("bowl", "skip", "take")
HASH_DIM = 1024
HIDDEN_DIM = 64
MODEL_SEED = 0
LEARNING_RATE = 0.001
ADAM_BETAS = [0.9, 0.999]
ADAM_EPS = 1e-8
ADAM_WEIGHT_DECAY = 0.0
ADAM_AMSGRAD = False
DISCOUNT = 1.0
ENTROPY_COEFFICIENT = 0.01
GRADIENT_NORM_CEILING = 1.0
BOOTSTRAP_CONFIDENCE = 0.95
EVALUATION_REPLAY_EPISODES_PER_SEED = 4
ASCENSION_LEVEL = 0
MAX_DECISIONS_PER_EPISODE = 500
VICTORY_WEIGHT = 2.0
MAX_FLOOR = 57
EXECUTION_SOURCE_PATH = (
    "analysis_scripts/noncombat_state_conditioned_simulator_learning_experiment.py"
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
    "promotion_authorized",
    "production_checkpoint_mutation_authorized",
    "qualification_authorized",
    "seed_access_authorized",
    "target_supported_outcome_authorized",
    "training_authorized",
)
EXECUTION_AUTHORITY_NAMES = {
    "environment_construction_authorized",
    "execution_authorized",
    "fresh_evidence_authorized",
    "model_fitting_authorized",
    "native_loading_authorized",
    "seed_access_authorized",
    "training_authorized",
}
DOWNSTREAM_AUTHORITY_NAMES = (
    "causal_claim_authorized",
    "communication_mod_authorized",
    "formal_rl_authorized",
    "gameplay_authorized",
    "live_execution_authorized",
    "ope_authorized",
    "policy_loading_authorized",
    "promotion_authorized",
    "production_checkpoint_mutation_authorized",
    "qualification_authorized",
    "target_supported_outcome_authorized",
)
TERMINAL_VERDICTS = {
    "experiment_blocked",
    "experiment_invalid",
    "experiment_stopped_at_canary",
    "experiment_valid_with_floor_only_signal",
    "experiment_valid_with_victory_signal",
    "experiment_valid_without_learning_signal",
}
REFERENCE_POLICY_NAMES = (
    "bottled",
    "current",
    "live_policy",
    "ope",
    "simple_agent",
    "simpleagent",
    "teacher",
)
IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_formal_reward_contract.py",
    "analysis_scripts/noncombat_policy_diagnostics.py",
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_rl_experiment.py",
    "analysis_scripts/noncombat_state_conditioned_policy_input.py",
    "analysis_scripts/noncombat_state_conditioned_ranker.py",
    "analysis_scripts/noncombat_state_conditioned_simulator_learning_experiment.py",
    "analysis_scripts/verify_noncombat_state_conditioned_simulator_learning_experiment.py",
)
_DTYPE_LAYOUT = {
    "bool": (1, "?"),
    "float32": (4, "f"),
    "float64": (8, "d"),
    "int32": (4, "i"),
    "int64": (8, "q"),
    "uint8": (1, "B"),
}
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_EXECUTION_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")


class VerificationError(RuntimeError):
    """Raised when terminal evidence does not reproduce exactly."""


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise VerificationError(f"non-finite JSON constant: {value}")


def _validate_json_value(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise VerificationError(f"{label} keys must be strings")
            _validate_json_value(child, f"{label}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_json_value(child, f"{label}[{index}]")
        return
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            raise VerificationError(f"{label} must be finite")
        return
    raise VerificationError(f"{label} has unsupported type {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    _validate_json_value(value, "value")
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _json_values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is bool and type(right) is bool and left is right
    if isinstance(left, Mapping) or isinstance(right, Mapping):
        return (
            isinstance(left, Mapping)
            and isinstance(right, Mapping)
            and set(left) == set(right)
            and all(_json_values_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, list) or isinstance(right, list):
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right)
            and all(
                _json_values_equal(left_item, right_item)
                for left_item, right_item in zip(left, right)
            )
        )
    return left == right


def load_canonical_json(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot parse {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"{path.name} must contain a JSON object")
    if payload != canonical_json_bytes(value):
        raise VerificationError(f"{path.name} is not canonical JSON")
    return value, payload


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationError(f"{label} must be a mapping")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise VerificationError(f"{label} must be a sequence")
    return value


def _require_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    if actual != expected:
        raise VerificationError(
            f"{label} fields mismatch: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def _strict_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VerificationError(f"{label} must be an integer")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    result = _strict_int(value, label)
    if result < 0:
        raise VerificationError(f"{label} must be a nonnegative integer")
    return result


def _positive_int(value: Any, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise VerificationError(f"{label} must be positive")
    return result


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VerificationError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise VerificationError(f"{label} must be a finite number")
    return 0.0 if result == 0.0 else result


def _float32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise VerificationError(f"{label} must be a canonical relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise VerificationError(f"{label} must be a canonical relative path")
    return value


def _canonical_windows_path(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z]:/[A-Za-z0-9_. /-]+", value)
        or ".." in PurePosixPath(value[2:]).parts
    ):
        raise VerificationError(
            f"{label} must be a canonical absolute Windows path"
        )
    return value


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise VerificationError(f"{label} must be lowercase sha256")
    return value


def _validate_commit(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _COMMIT_RE.fullmatch(value):
        raise VerificationError(f"{label} must be a lowercase git commit")
    return value


def _registration_authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def _execution_authority() -> dict[str, bool]:
    return {name: name in EXECUTION_AUTHORITY_NAMES for name in AUTHORITY_NAMES}


def _all_false_exact(value: Any, label: str) -> None:
    if not _json_values_equal(
        dict(_mapping(value, label)), _registration_authority()
    ):
        raise VerificationError(f"{label} must be the exact all-false authority")


def _all_false(value: Any, label: str) -> None:
    authority = _mapping(value, label)
    if not authority or any(item is not False for item in authority.values()):
        raise VerificationError(f"{label} must contain only false values")


def _experiment_contract() -> dict[str, Any]:
    return {
        "algorithm": {
            "algorithm_version": ALGORITHM_VERSION,
            "discount": DISCOUNT,
            "entropy_coefficient": ENTROPY_COEFFICIENT,
            "gradient_norm_ceiling": GRADIENT_NORM_CEILING,
            "learning_rate": LEARNING_RATE,
            "normalized_returns": True,
            "optimizer": "adam",
            "optimizer_amsgrad": ADAM_AMSGRAD,
            "optimizer_betas": ADAM_BETAS,
            "optimizer_eps": ADAM_EPS,
            "optimizer_weight_decay": ADAM_WEIGHT_DECAY,
        },
        "control": {
            "frozen_seeded_initialization": True,
            "model_seed": MODEL_SEED,
            "paired_same_seed_evaluation": True,
            "policy_quality_baseline": False,
        },
        "environment": {
            "ascension": ASCENSION_LEVEL,
            "character": "IRONCLAD",
            "max_decisions_per_episode": MAX_DECISIONS_PER_EPISODE,
            "registered_support_blockers": sorted(REGISTERED_SUPPORT_BLOCKERS),
        },
        "evaluation": {
            "bootstrap_confidence": BOOTSTRAP_CONFIDENCE,
            "bootstrap_seed": MODEL_SEED,
            "greedy_policy": True,
            "replay_episodes_per_seed": EVALUATION_REPLAY_EPISODES_PER_SEED,
            "update_free": True,
        },
        "input": {
            "api_version": 3,
            "candidate_order_preserved": True,
            "excluded_runtime_control_fields": ["follow_up_control"],
            "feature_version": FEATURE_VERSION,
            "hash_dim": HASH_DIM,
            "leakage_excluded": True,
        },
        "lifecycle": {
            "one_logical_attempt": True,
            "pushed_remote_ref": PUSHED_REMOTE_REF,
            "same_identity_checkpoint_resume_authorized": True,
            "source_only_controls_before_start": True,
            "terminal_artifact_reads_after_process_exit_only": True,
        },
        "model": {
            "architecture_id": ARCHITECTURE_ID,
            "candidate_input_dim": HASH_DIM,
            "channel_composition": "separate_state_and_candidate",
            "device": "cpu",
            "dtype": "float32",
            "hidden_dim": HIDDEN_DIM,
            "state_conditioned": True,
            "state_input_dim": HASH_DIM,
        },
        "output": {
            "checkpoint_directory": "checkpoints",
            "checkpoint_filename_template": "checkpoint_{index:04d}.json",
            "conditional_terminal_artifacts": {
                "evaluation.json": "present_when_evaluation_evidence_exists",
            },
            "execution_lease": ".execution.lease",
            "manifest": "artifact_manifest.json",
            "required_terminal_artifacts": sorted(
                FULL_TERMINAL_ARTIFACT_NAMES - {"evaluation.json"}
            ),
        },
        "reward": {
            "floor_progress_maximum": 1.0,
            "reward_version": REWARD_VERSION,
            "victory_primary": True,
            "victory_weight": VICTORY_WEIGHT,
        },
        "verdicts": {
            "blocked": "experiment_blocked",
            "canary_stop": "experiment_stopped_at_canary",
            "invalid": "experiment_invalid",
            "valid_floor_only": "experiment_valid_with_floor_only_signal",
            "valid_victory": "experiment_valid_with_victory_signal",
            "valid_without_learning": "experiment_valid_without_learning_signal",
        },
    }


def _verify_manifest(
    output: Path, manifest: Mapping[str, Any]
) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    manifest_kind = manifest.get("manifest_kind")
    if manifest_kind not in {"full_terminal", "generic_bundle"}:
        raise VerificationError("manifest kind is invalid")
    full_terminal = manifest_kind == "full_terminal"
    expected_manifest_fields = {
        "artifact_count",
        "artifacts",
        "authority",
        "manifest_kind",
        "schema_version",
    }
    if full_terminal:
        expected_manifest_fields.update({"logical_execution_id", "verdict"})
    _require_keys(manifest, expected_manifest_fields, "manifest")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise VerificationError("manifest schema mismatch")
    _all_false_exact(manifest.get("authority"), "manifest authority")
    if full_terminal:
        execution_id = manifest.get("logical_execution_id")
        if not isinstance(execution_id, str) or not _EXECUTION_ID_RE.fullmatch(
            execution_id
        ):
            raise VerificationError("manifest logical execution id is invalid")
        if manifest.get("verdict") not in TERMINAL_VERDICTS:
            raise VerificationError("manifest verdict is invalid")
    rows = manifest.get("artifacts")
    if not isinstance(rows, list) or not rows:
        raise VerificationError("manifest artifacts must be nonempty")
    artifact_count = _positive_int(
        manifest.get("artifact_count"), "manifest artifact_count"
    )
    if artifact_count != len(rows):
        raise VerificationError("manifest artifact_count mismatch")
    bindings: dict[str, dict[str, Any]] = {}
    payloads: dict[str, bytes] = {}
    for row in rows:
        binding = dict(_mapping(row, "manifest artifact"))
        if set(binding) != {"path", "sha256", "size_bytes"}:
            raise VerificationError("manifest artifact fields mismatch")
        name = _canonical_relative_path(binding["path"], "manifest artifact path")
        if (
            not name.endswith(".json")
            or name == "artifact_manifest.json"
            or name in bindings
            or (not full_terminal and PurePosixPath(name).name != name)
            or (
                not full_terminal
                and name.casefold() in FULL_TERMINAL_ARTIFACT_CASEFOLDS
            )
        ):
            raise VerificationError("manifest artifact path is invalid")
        if not isinstance(binding["sha256"], str) or not _SHA256_RE.fullmatch(
            binding["sha256"]
        ):
            raise VerificationError(f"manifest sha256 is invalid for {name}")
        if (
            isinstance(binding["size_bytes"], bool)
            or not isinstance(binding["size_bytes"], int)
            or binding["size_bytes"] <= 0
        ):
            raise VerificationError(f"manifest size is invalid for {name}")
        artifact_path = output / PurePosixPath(name)
        if artifact_path.is_symlink():
            raise VerificationError(f"manifest artifact is a symlink: {name}")
        _, payload = load_canonical_json(artifact_path)
        if len(payload) != binding["size_bytes"]:
            raise VerificationError(f"artifact size mismatch: {name}")
        if hashlib.sha256(payload).hexdigest() != binding["sha256"]:
            raise VerificationError(f"artifact sha256 mismatch: {name}")
        bindings[name] = binding
        payloads[name] = payload
    expected = set(bindings) | {"artifact_manifest.json"}
    actual = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
    }
    actual.discard(".execution.lease")
    if actual != expected:
        raise VerificationError(
            f"terminal artifact inventory mismatch: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )
    directories = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_dir()
    }
    allowed_directories = {"checkpoints"} if full_terminal else set()
    if directories != allowed_directories:
        raise VerificationError("terminal output contains an unregistered directory")
    return payloads, bindings


def _verify_controls(
    output: Path,
    payloads: Mapping[str, bytes],
) -> tuple[str | None, str | None]:
    required = {"registration.json", "authorization.json"}
    if not required.issubset(payloads):
        return None, None
    registration, registration_bytes = load_canonical_json(output / "registration.json")
    authorization, _ = load_canonical_json(output / "authorization.json")
    if registration.get("schema_version") != REGISTRATION_SCHEMA_VERSION:
        raise VerificationError("registration schema mismatch")
    if authorization.get("schema_version") != AUTHORIZATION_SCHEMA_VERSION:
        raise VerificationError("authorization schema mismatch")
    _all_false(registration.get("authority"), "registration authority")
    authority = _mapping(authorization.get("authority"), "authorization authority")
    for name in DOWNSTREAM_AUTHORITY_NAMES:
        if authority.get(name) is not False:
            raise VerificationError(f"downstream authority is not false: {name}")
    binding = _mapping(authorization.get("registration"), "authorization registration")
    if binding.get("sha256") != hashlib.sha256(registration_bytes).hexdigest():
        raise VerificationError("authorization registration sha256 mismatch")
    binding_size = _positive_int(
        binding.get("size_bytes"), "authorization registration size_bytes"
    )
    if binding_size != len(registration_bytes):
        raise VerificationError("authorization registration size mismatch")
    identity = _mapping(registration.get("identity"), "registration identity")
    logical_execution_id = identity.get("logical_execution_id")
    output_directory = identity.get("output_directory")
    if authorization.get("logical_execution_id") != logical_execution_id:
        raise VerificationError("authorization logical execution id mismatch")
    if authorization.get("output_directory") != output_directory:
        raise VerificationError("authorization output directory mismatch")
    return str(logical_execution_id), str(output_directory)


def _validate_binding(
    value: Any, label: str, *, relative_path: bool = False
) -> dict[str, Any]:
    binding = dict(_mapping(value, label))
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    if not isinstance(binding["path"], str) or not binding["path"]:
        raise VerificationError(f"{label}.path must be nonempty")
    if relative_path:
        _canonical_relative_path(binding["path"], f"{label}.path")
    _validate_sha256(binding["sha256"], f"{label}.sha256")
    _positive_int(binding["size_bytes"], f"{label}.size_bytes")
    return binding


def _validate_external_binding(value: Any, label: str) -> dict[str, Any]:
    binding = _validate_binding(value, label)
    _canonical_windows_path(binding["path"], f"{label}.path")
    return binding


def _validate_checkpoint_inventory(value: Any, label: str) -> dict[str, Any]:
    inventory = dict(_mapping(value, label))
    _require_keys(
        inventory,
        {"entries", "inventory_sha256", "root", "total_bytes"},
        label,
    )
    _canonical_windows_path(inventory["root"], f"{label}.root")
    entries = [
        _validate_binding(
            row, f"{label}.entries[{index}]", relative_path=True
        )
        for index, row in enumerate(_sequence(inventory["entries"], f"{label}.entries"))
    ]
    if entries != sorted(entries, key=lambda row: row["path"]):
        raise VerificationError(f"{label}.entries must be sorted")
    if len({row["path"] for row in entries}) != len(entries):
        raise VerificationError(f"{label}.entries contain duplicates")
    expected_hash = hashlib.sha256(canonical_json_bytes(entries)).hexdigest()
    if inventory["inventory_sha256"] != expected_hash:
        raise VerificationError(f"{label}.inventory_sha256 mismatch")
    total_bytes = _nonnegative_int(inventory["total_bytes"], f"{label}.total_bytes")
    if total_bytes != sum(row["size_bytes"] for row in entries):
        raise VerificationError(f"{label}.total_bytes mismatch")
    return inventory


def _validate_seed_inventory(value: Any) -> dict[str, Any]:
    inventory = dict(_mapping(value, "seed inventory"))
    _require_keys(
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
    if inventory["schema_version"] != SEED_INVENTORY_SCHEMA_VERSION:
        raise VerificationError("seed inventory schema mismatch")
    _all_false_exact(inventory["authority"], "seed inventory authority")
    _validate_commit(inventory["repository_commit"], "seed inventory commit")
    sources = dict(_mapping(inventory["sources"], "seed inventory sources"))
    if not sources:
        raise VerificationError("seed inventory sources must be nonempty")
    normalized_sources: dict[str, list[int]] = {}
    for path, raw_seeds in sorted(sources.items()):
        _canonical_relative_path(path, "seed source path")
        seeds = [
            _nonnegative_int(seed, f"seed source {path}")
            for seed in _sequence(raw_seeds, f"seed source {path}")
        ]
        if seeds != sorted(set(seeds)):
            raise VerificationError(f"seed source {path} is not canonical")
        normalized_sources[path] = seeds
    if sources != normalized_sources:
        raise VerificationError("seed inventory source order or values drifted")
    bindings = [
        _validate_binding(
            row, f"seed source binding[{index}]", relative_path=True
        )
        for index, row in enumerate(
            _sequence(inventory["source_bindings"], "seed source bindings")
        )
    ]
    if [row["path"] for row in bindings] != list(normalized_sources):
        raise VerificationError("seed source bindings do not match sources")
    excluded = sorted(
        {seed for seeds in normalized_sources.values() for seed in seeds}
    )
    registered_excluded = [
        _nonnegative_int(seed, f"seed inventory excluded_seeds[{index}]")
        for index, seed in enumerate(
            _sequence(inventory["excluded_seeds"], "seed inventory excluded seeds")
        )
    ]
    if registered_excluded != excluded:
        raise VerificationError("seed inventory excluded seeds mismatch")
    excluded_count = _nonnegative_int(
        inventory["excluded_seed_count"], "seed inventory excluded_seed_count"
    )
    if excluded_count != len(excluded):
        raise VerificationError("seed inventory excluded count mismatch")
    return inventory


def _reject_reference_policy_leakage(
    value: Any, label: str = "registration", *, allow_evidence: bool = True
) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            folded = str(key).casefold()
            if allow_evidence and folded in {
                "authority",
                "evidence",
                "historical_evidence",
                "seed_inventory",
            }:
                continue
            if any(name in folded for name in REFERENCE_POLICY_NAMES):
                raise VerificationError(
                    f"reference policy field is forbidden at {label}.{key}"
                )
            _reject_reference_policy_leakage(
                child, f"{label}.{key}", allow_evidence=allow_evidence
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_reference_policy_leakage(
                child, f"{label}[{index}]", allow_evidence=allow_evidence
            )


def _materialize_cohorts(
    inventory: Mapping[str, Any], selection: Mapping[str, Any]
) -> dict[str, list[int]]:
    expected_selection = {
        "canary_count",
        "holdout_count",
        "search_start",
        "train_count",
    }
    _require_keys(selection, expected_selection, "cohort selection")
    counts = {
        name: _positive_int(selection[name], name)
        for name in ("train_count", "canary_count", "holdout_count")
    }
    candidate = _nonnegative_int(selection["search_start"], "search_start")
    excluded = set(inventory["excluded_seeds"])
    selected: list[int] = []
    required = sum(counts.values())
    while len(selected) < required:
        if candidate not in excluded:
            selected.append(candidate)
        candidate += 1
    train_end = counts["train_count"]
    canary_end = train_end + counts["canary_count"]
    return {
        "train": selected[:train_end],
        "canary": selected[train_end:canary_end],
        "holdout": selected[canary_end:],
    }


def _validate_registration_full(value: Any, payload: bytes) -> dict[str, Any]:
    registration = dict(_mapping(value, "registration"))
    _require_keys(
        registration,
        {
            "authority",
            "behavior_gates",
            "cohorts",
            "experiment",
            "identity",
            "limits",
            "schema_version",
            "seed_inventory",
            "selection",
        },
        "registration",
    )
    if registration["schema_version"] != REGISTRATION_SCHEMA_VERSION:
        raise VerificationError("registration schema mismatch")
    _all_false_exact(registration["authority"], "registration authority")
    if not _json_values_equal(registration["experiment"], _experiment_contract()):
        raise VerificationError("registration experiment contract drift")
    _reject_reference_policy_leakage(registration)

    identity = dict(_mapping(registration["identity"], "registration identity"))
    _require_keys(
        identity,
        {
            "adapter_provenance",
            "evidence",
            "implementation",
            "isolation",
            "logical_execution_id",
            "native",
            "output_directory",
            "runtime",
            "seed_inventory_binding",
        },
        "registration identity",
    )
    execution_id = identity["logical_execution_id"]
    if not isinstance(execution_id, str) or not _EXECUTION_ID_RE.fullmatch(execution_id):
        raise VerificationError("registration logical execution id is invalid")
    output_directory = _canonical_relative_path(
        identity["output_directory"], "registration output directory"
    )
    if not output_directory.startswith(OUTPUT_ROOT_PREFIX):
        raise VerificationError("registration output directory is outside contract")
    evidence = dict(_mapping(identity["evidence"], "registration evidence"))
    if not evidence:
        raise VerificationError("registration evidence must be nonempty")
    for name, binding in evidence.items():
        _validate_binding(
            binding, f"registration evidence {name}", relative_path=True
        )
    implementation = dict(_mapping(identity["implementation"], "implementation"))
    _require_keys(
        implementation, {"commit", "source_files", "source_sha256"}, "implementation"
    )
    _validate_commit(implementation["commit"], "implementation commit")
    source_files = list(_sequence(implementation["source_files"], "source files"))
    if source_files != list(IMPLEMENTATION_SOURCE_FILES):
        raise VerificationError("implementation source file inventory mismatch")
    for path in source_files:
        _canonical_relative_path(path, "implementation source path")
    _validate_sha256(implementation["source_sha256"], "implementation source sha256")
    isolation = dict(_mapping(identity["isolation"], "isolation identity"))
    _require_keys(
        isolation,
        {"communication_mod_config", "production_checkpoints"},
        "isolation identity",
    )
    _validate_external_binding(
        isolation["communication_mod_config"], "CommunicationMod binding"
    )
    _validate_checkpoint_inventory(
        isolation["production_checkpoints"], "production checkpoint inventory"
    )
    native = dict(_mapping(identity["native"], "native identity"))
    _require_keys(native, {"dll_directories", "module", "simulator_repo"}, "native identity")
    directories = [
        _canonical_windows_path(path, "native DLL directory")
        for path in _sequence(native["dll_directories"], "native DLL directories")
    ]
    if directories != sorted(set(directories)) or not directories:
        raise VerificationError("native DLL directories are not canonical")
    _validate_external_binding(native["module"], "native module")
    _canonical_windows_path(native["simulator_repo"], "native simulator repository")
    runtime = dict(_mapping(identity["runtime"], "runtime identity"))
    _require_keys(
        runtime,
        {"executable", "platform", "python_version", "torch_version"},
        "runtime identity",
    )
    _canonical_windows_path(runtime["executable"], "runtime executable")
    if runtime["platform"] != "win32" or any(
        not isinstance(runtime[name], str) or not runtime[name]
        for name in ("python_version", "torch_version")
    ):
        raise VerificationError("runtime identity is invalid")
    provenance = dict(_mapping(identity["adapter_provenance"], "adapter provenance"))
    for name in (
        "adapter_commit",
        "adapter_source_sha256",
        "module_sha256",
        "simulator_commit",
        "simulator_source_sha256",
    ):
        if name.endswith("commit"):
            _validate_commit(provenance.get(name), f"adapter provenance {name}")
        else:
            _validate_sha256(provenance.get(name), f"adapter provenance {name}")
    if (
        provenance.get("module_sha256") != native["module"]["sha256"]
        or provenance.get("module_size_bytes") != native["module"]["size_bytes"]
    ):
        raise VerificationError("adapter provenance and native module differ")
    seed_binding = _validate_binding(
        identity["seed_inventory_binding"],
        "seed inventory binding",
        relative_path=True,
    )
    inventory = _validate_seed_inventory(registration["seed_inventory"])
    inventory_bytes = canonical_json_bytes(inventory)
    if (
        seed_binding["sha256"] != hashlib.sha256(inventory_bytes).hexdigest()
        or seed_binding["size_bytes"] != len(inventory_bytes)
    ):
        raise VerificationError("embedded seed inventory binding mismatch")
    selection = dict(_mapping(registration["selection"], "cohort selection"))
    expected_cohorts = _materialize_cohorts(inventory, selection)
    cohorts = dict(_mapping(registration["cohorts"], "cohorts"))
    _require_keys(cohorts, {"train", "canary", "holdout"}, "cohorts")
    normalized_cohorts = {
        name: [
            _nonnegative_int(seed, f"cohorts.{name}[{index}]")
            for index, seed in enumerate(
                _sequence(cohorts[name], f"cohorts.{name}")
            )
        ]
        for name in ("train", "canary", "holdout")
    }
    if normalized_cohorts != expected_cohorts:
        raise VerificationError("registered cohorts do not reproduce ascending selection")
    limits = dict(_mapping(registration["limits"], "limits"))
    _require_keys(
        limits,
        {
            "bootstrap_resamples",
            "max_checkpoint_count",
            "max_episodes",
            "max_evaluation_episodes",
            "max_total_episodes",
            "max_wall_seconds",
            "train_passes",
            "training_chunk_size",
            "unsupported_rate_ceiling",
        },
        "limits",
    )
    for name in (
        "bootstrap_resamples",
        "max_checkpoint_count",
        "max_episodes",
        "max_evaluation_episodes",
        "max_total_episodes",
        "train_passes",
        "training_chunk_size",
    ):
        _positive_int(limits[name], f"limits.{name}")
    if _finite_number(limits["max_wall_seconds"], "limits.max_wall_seconds") <= 0.0:
        raise VerificationError("max wall seconds must be positive")
    ceiling = _finite_number(
        limits["unsupported_rate_ceiling"], "limits.unsupported_rate_ceiling"
    )
    if not 0.0 <= ceiling < 1.0:
        raise VerificationError("unsupported rate ceiling is invalid")
    if limits["max_episodes"] != (
        len(normalized_cohorts["train"]) * limits["train_passes"]
    ):
        raise VerificationError("registered max episode count mismatch")
    if len(normalized_cohorts["train"]) % limits["training_chunk_size"] != 0:
        raise VerificationError("registered chunk crosses a train pass boundary")
    expected_checkpoint_count = limits["max_episodes"] // limits["training_chunk_size"]
    if limits["max_checkpoint_count"] != expected_checkpoint_count:
        raise VerificationError("registered checkpoint count mismatch")
    expected_evaluation_episodes = EVALUATION_REPLAY_EPISODES_PER_SEED * (
        len(normalized_cohorts["canary"]) + len(normalized_cohorts["holdout"])
    )
    if limits["max_evaluation_episodes"] != expected_evaluation_episodes:
        raise VerificationError("registered evaluation episode count mismatch")
    if limits["max_total_episodes"] != limits["max_episodes"] + expected_evaluation_episodes:
        raise VerificationError("registered total episode count mismatch")
    gate = dict(_mapping(registration["behavior_gates"], "behavior gates"))
    _require_keys(gate, {"category_coverage", "multi_kind", "state_effect"}, "behavior gates")
    if gate["category_coverage"] != list(TARGET_CATEGORIES):
        raise VerificationError("behavior category coverage mismatch")
    multi_gate = dict(_mapping(gate["multi_kind"], "multi-kind gate"))
    _require_keys(
        multi_gate,
        {
            "categories",
            "maximum_selected_kind_rate",
            "minimum_multi_kind_decisions",
            "minimum_selected_kinds",
        },
        "multi-kind gate",
    )
    if multi_gate["categories"] != ["card_reward", "shop"]:
        raise VerificationError("multi-kind gate categories mismatch")
    maximum_rate = _finite_number(
        multi_gate["maximum_selected_kind_rate"],
        "multi-kind maximum selected rate",
    )
    if not 0.0 < maximum_rate < 1.0:
        raise VerificationError("multi-kind maximum selected rate is invalid")
    _positive_int(
        multi_gate["minimum_multi_kind_decisions"],
        "multi-kind minimum decisions",
    )
    _positive_int(
        multi_gate["minimum_selected_kinds"], "multi-kind minimum selected kinds"
    )
    state_gate = dict(_mapping(gate["state_effect"], "state-effect gate"))
    _require_keys(
        state_gate,
        {
            "minimum_absolute_relative_score_change",
            "minimum_multi_candidate_decisions",
            "minimum_nonzero_effect_rate",
            "minimum_relative_order_change_decisions",
        },
        "state-effect gate",
    )
    if _finite_number(
        state_gate["minimum_absolute_relative_score_change"],
        "state-effect minimum magnitude",
    ) <= 0.0:
        raise VerificationError("state-effect minimum magnitude is invalid")
    _positive_int(
        state_gate["minimum_multi_candidate_decisions"],
        "state-effect minimum decisions",
    )
    _positive_int(
        state_gate["minimum_relative_order_change_decisions"],
        "state-effect minimum relative-order changes",
    )
    effect_rate = _finite_number(
        state_gate["minimum_nonzero_effect_rate"],
        "state-effect minimum nonzero rate",
    )
    if not 0.0 < effect_rate <= 1.0:
        raise VerificationError("state-effect minimum nonzero rate is invalid")
    if payload != canonical_json_bytes(registration):
        raise VerificationError("registration bytes drifted during verification")
    return registration


def _validate_full_controls(
    output: Path, payloads: Mapping[str, bytes]
) -> tuple[dict[str, Any], dict[str, Any]]:
    required = {"registration.json", "authorization.json", "configuration.json"}
    if not required.issubset(payloads):
        raise VerificationError("full terminal controls are incomplete")
    registration, registration_bytes = load_canonical_json(output / "registration.json")
    registration = _validate_registration_full(registration, registration_bytes)
    authorization, authorization_bytes = load_canonical_json(output / "authorization.json")
    _require_keys(
        authorization,
        {
            "authority",
            "execution",
            "logical_execution_id",
            "output_directory",
            "registration",
            "schema_version",
        },
        "authorization",
    )
    if authorization["schema_version"] != AUTHORIZATION_SCHEMA_VERSION:
        raise VerificationError("authorization schema mismatch")
    if not _json_values_equal(
        dict(_mapping(authorization["authority"], "authorization authority")),
        _execution_authority(),
    ):
        raise VerificationError("authorization authority mismatch")
    identity = registration["identity"]
    if authorization["logical_execution_id"] != identity["logical_execution_id"]:
        raise VerificationError("authorization logical execution id mismatch")
    if authorization["output_directory"] != identity["output_directory"]:
        raise VerificationError("authorization output directory mismatch")
    registration_binding = dict(
        _mapping(authorization["registration"], "authorization registration")
    )
    _require_keys(
        registration_binding,
        {"commit", "path", "sha256", "size_bytes"},
        "authorization registration",
    )
    _validate_commit(registration_binding["commit"], "authorization registration commit")
    registration_path = _canonical_relative_path(
        registration_binding["path"], "authorization registration path"
    )
    if (
        not registration_path.startswith(OUTPUT_ROOT_PREFIX)
        or not registration_path.endswith("_registration.json")
    ):
        raise VerificationError("authorization registration path is outside contract")
    registration_size = _positive_int(
        registration_binding["size_bytes"],
        "authorization registration size_bytes",
    )
    if (
        registration_binding["sha256"] != hashlib.sha256(registration_bytes).hexdigest()
        or registration_size != len(registration_bytes)
    ):
        raise VerificationError("authorization registration binding mismatch")
    execution = dict(
        _mapping(authorization["execution"], "authorization execution")
    )
    _require_keys(
        execution,
        {
            "authorization_path",
            "cohorts_sha256",
            "command",
            "native_module",
            "one_logical_attempt",
            "repository_root",
            "resource_limits",
            "same_identity_checkpoint_resume_authorized",
        },
        "authorization execution",
    )
    authorization_path = _canonical_relative_path(
        execution["authorization_path"], "execution authorization path"
    )
    if (
        not authorization_path.startswith(OUTPUT_ROOT_PREFIX)
        or not authorization_path.endswith("_authorization.json")
    ):
        raise VerificationError("execution authorization path is outside contract")
    root = _canonical_windows_path(
        execution["repository_root"], "execution repository root"
    )
    command = list(_sequence(execution["command"], "execution command"))
    expected_command = [
        identity["runtime"]["executable"],
        f"{root}/{EXECUTION_SOURCE_PATH}",
        "execute",
        "--repo-root",
        root,
        "--registration",
        f"{root}/{registration_path}",
        "--authorization",
        f"{root}/{authorization_path}",
        "--output",
        f"{root}/{identity['output_directory']}",
    ]
    if command != expected_command:
        raise VerificationError("authorization execution command mismatch")
    for index in (0, 1, 4, 6, 8, 10):
        _canonical_windows_path(command[index], f"execution command[{index}]")
    if execution["cohorts_sha256"] != hashlib.sha256(
        canonical_json_bytes(registration["cohorts"])
    ).hexdigest():
        raise VerificationError("authorization cohort binding mismatch")
    native_module = _validate_external_binding(
        execution["native_module"], "authorization native module"
    )
    if not _json_values_equal(native_module, identity["native"]["module"]):
        raise VerificationError("authorization native module mismatch")
    if execution["one_logical_attempt"] is not True:
        raise VerificationError("authorization logical-attempt contract drifted")
    if execution["same_identity_checkpoint_resume_authorized"] is not True:
        raise VerificationError("authorization checkpoint-resume contract drifted")
    if not _json_values_equal(execution["resource_limits"], registration["limits"]):
        raise VerificationError("authorization resource limits mismatch")
    configuration, _ = load_canonical_json(output / "configuration.json")
    expected_configuration = {
        "authority": _registration_authority(),
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "experiment": registration["experiment"],
        "identity": identity,
        "limits": registration["limits"],
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
    }
    if not _json_values_equal(configuration, expected_configuration):
        raise VerificationError("configuration does not reproduce controls")
    return registration, authorization


def _validate_tensor(value: Any, label: str) -> dict[str, Any]:
    tensor = dict(_mapping(value, label))
    _require_keys(
        tensor,
        {"byte_order", "data_base64", "data_sha256", "dtype", "shape"},
        label,
    )
    if tensor["byte_order"] != "little" or tensor["dtype"] not in _DTYPE_LAYOUT:
        raise VerificationError(f"{label} tensor metadata is invalid")
    shape = tensor["shape"]
    if not isinstance(shape, list) or any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0
        for item in shape
    ):
        raise VerificationError(f"{label} tensor shape is invalid")
    try:
        raw = base64.b64decode(tensor["data_base64"], validate=True)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"{label} tensor base64 is invalid") from exc
    _validate_sha256(tensor["data_sha256"], f"{label} tensor sha256")
    if hashlib.sha256(raw).hexdigest() != tensor["data_sha256"]:
        raise VerificationError(f"{label} tensor sha256 mismatch")
    width, format_code = _DTYPE_LAYOUT[tensor["dtype"]]
    elements = math.prod(shape) if shape else 1
    if len(raw) != elements * width:
        raise VerificationError(f"{label} tensor byte length mismatch")
    if tensor["dtype"] in {"float32", "float64"}:
        if any(
            not math.isfinite(item[0])
            for item in struct.iter_unpack(f"<{format_code}", raw)
        ):
            raise VerificationError(f"{label} tensor contains non-finite values")
    if tensor["dtype"] == "bool" and any(byte not in {0, 1} for byte in raw):
        raise VerificationError(f"{label} tensor contains invalid boolean bytes")
    return tensor


def _validate_encoded_state(value: Any, label: str) -> None:
    payload = dict(_mapping(value, label))
    kind = payload.get("kind")
    if kind == "tensor":
        _require_keys(payload, {"kind", "value"}, label)
        _validate_tensor(payload["value"], f"{label}.value")
        return
    if kind == "mapping":
        _require_keys(payload, {"items", "kind"}, label)
        items = list(_sequence(payload["items"], f"{label}.items"))
        previous: str | None = None
        for index, raw in enumerate(items):
            item = dict(_mapping(raw, f"{label}.items[{index}]"))
            _require_keys(item, {"key", "value"}, f"{label}.items[{index}]")
            key = item["key"]
            if (
                not isinstance(key, str)
                or not key
                or (previous is not None and key <= previous)
            ):
                raise VerificationError(f"{label} mapping keys are not canonical")
            previous = key
            _validate_encoded_state(item["value"], f"{label}.{key}")
        return
    if kind in {"tuple", "list"}:
        _require_keys(payload, {"items", "kind"}, label)
        for index, child in enumerate(
            _sequence(payload["items"], f"{label}.items")
        ):
            _validate_encoded_state(child, f"{label}[{index}]")
        return
    if kind == "scalar":
        _require_keys(payload, {"kind", "value"}, label)
        scalar = payload["value"]
        if isinstance(scalar, (Mapping, list)):
            raise VerificationError(f"{label} scalar is not scalar")
        _validate_json_value(scalar, label)
        return
    raise VerificationError(f"{label} encoded state kind is invalid")


def _decode_plain_encoded_state(value: Any, label: str) -> Any:
    payload = dict(_mapping(value, label))
    kind = payload.get("kind")
    if kind == "scalar":
        _require_keys(payload, {"kind", "value"}, label)
        scalar = payload["value"]
        if isinstance(scalar, (Mapping, list)):
            raise VerificationError(f"{label} scalar is not scalar")
        _validate_json_value(scalar, label)
        return scalar
    if kind == "mapping":
        _require_keys(payload, {"items", "kind"}, label)
        result: dict[str, Any] = {}
        previous: str | None = None
        for index, raw in enumerate(_sequence(payload["items"], f"{label}.items")):
            item = dict(_mapping(raw, f"{label}.items[{index}]"))
            _require_keys(item, {"key", "value"}, f"{label}.items[{index}]")
            key = item["key"]
            if (
                not isinstance(key, str)
                or not key
                or (previous is not None and key <= previous)
            ):
                raise VerificationError(f"{label} mapping keys are not canonical")
            previous = key
            result[key] = _decode_plain_encoded_state(
                item["value"], f"{label}.{key}"
            )
        return result
    if kind in {"list", "tuple"}:
        _require_keys(payload, {"items", "kind"}, label)
        items = [
            _decode_plain_encoded_state(child, f"{label}[{index}]")
            for index, child in enumerate(
                _sequence(payload["items"], f"{label}.items")
            )
        ]
        return tuple(items) if kind == "tuple" else items
    raise VerificationError(f"{label} must not contain tensors")


def _validate_optimizer(value: Any, label: str) -> None:
    optimizer = dict(_mapping(value, label))
    _require_keys(optimizer, {"param_groups", "state"}, label)
    _validate_encoded_state(optimizer["param_groups"], f"{label}.param_groups")
    param_groups = _decode_plain_encoded_state(
        optimizer["param_groups"], f"{label}.param_groups"
    )
    if not isinstance(param_groups, list) or len(param_groups) != 1:
        raise VerificationError(f"{label} must contain one parameter group")
    group = dict(_mapping(param_groups[0], f"{label}.param_groups[0]"))
    expected_controls = {
        "amsgrad": ADAM_AMSGRAD,
        "betas": tuple(ADAM_BETAS),
        "eps": ADAM_EPS,
        "lr": LEARNING_RATE,
        "weight_decay": ADAM_WEIGHT_DECAY,
    }
    for name, expected in expected_controls.items():
        if not _json_values_equal(group.get(name), expected):
            raise VerificationError(f"{label} Adam {name} mismatch")
    rows = list(_sequence(optimizer["state"], f"{label}.state"))
    previous = -1
    for index, raw in enumerate(rows):
        row = dict(_mapping(raw, f"{label}.state[{index}]"))
        _require_keys(row, {"parameter_id", "state"}, f"{label}.state[{index}]")
        parameter_id = _nonnegative_int(
            row["parameter_id"], f"{label}.state[{index}].parameter_id"
        )
        if parameter_id <= previous:
            raise VerificationError(f"{label} parameter ids are not canonical")
        previous = parameter_id
        _validate_encoded_state(row["state"], f"{label}.state[{parameter_id}]")


def _validate_model(value: Any, label: str) -> dict[str, Any]:
    model = dict(_mapping(value, label))
    if not model or list(model) != sorted(model):
        raise VerificationError(f"{label} tensor names are not canonical")
    for name, tensor in model.items():
        if not isinstance(name, str) or not name:
            raise VerificationError(f"{label} tensor name is invalid")
        _validate_tensor(tensor, f"{label}.{name}")
    return model


def _validate_ranker_model(value: Any, label: str) -> dict[str, Any]:
    model = _validate_model(value, label)
    expected = {
        "hidden.bias": [HIDDEN_DIM],
        "hidden.weight": [HIDDEN_DIM, 2 * HASH_DIM],
        "scorer.bias": [1],
        "scorer.weight": [1, HIDDEN_DIM],
    }
    if set(model) != set(expected):
        raise VerificationError(f"{label} parameter inventory mismatch")
    for name, shape in expected.items():
        if model[name]["dtype"] != "float32" or model[name]["shape"] != shape:
            raise VerificationError(f"{label}.{name} tensor metadata mismatch")
    return model


def _validate_episode_row(
    value: Any,
    *,
    expected_seed: int,
    expected_chunk: int | None,
    label: str,
) -> dict[str, Any]:
    row = dict(_mapping(value, label))
    expected = {
        "action_sequence_sha256",
        "candidate_legality",
        "categories",
        "decisions",
        "last_supported_floor",
        "outcome",
        "retained",
        "seed",
        "selected_action_ids",
        "terminal_floor",
        "total_reward",
        "unsupported_reason",
        "victory",
    }
    if expected_chunk is not None:
        expected.add("chunk_index")
    _require_keys(row, expected, label)
    seed = _nonnegative_int(row["seed"], f"{label}.seed")
    decisions = _positive_int(row["decisions"], f"{label}.decisions")
    if seed != expected_seed:
        raise VerificationError(f"{label} seed coordinate mismatch")
    if expected_chunk is not None:
        chunk_index = _nonnegative_int(
            row["chunk_index"], f"{label}.chunk_index"
        )
        if chunk_index != expected_chunk:
            raise VerificationError(f"{label} chunk coordinate mismatch")
    actions = list(_sequence(row["selected_action_ids"], f"{label}.actions"))
    if not actions or any(not isinstance(action, str) or not action for action in actions):
        raise VerificationError(f"{label} action sequence is invalid")
    if decisions != len(actions):
        raise VerificationError(f"{label} decision count mismatch")
    if decisions > MAX_DECISIONS_PER_EPISODE:
        raise VerificationError(f"{label} decision count exceeds registered limit")
    expected_action_hash = hashlib.sha256(canonical_json_bytes(actions)).hexdigest()
    if row["action_sequence_sha256"] != expected_action_hash:
        raise VerificationError(f"{label} action sequence hash mismatch")
    categories = row["categories"]
    if (
        not isinstance(categories, list)
        or categories != sorted(set(categories))
        or not categories
        or any(category not in TARGET_CATEGORIES for category in categories)
    ):
        raise VerificationError(f"{label} categories are invalid")
    if row["candidate_legality"] is not True or row["retained"] is not True:
        raise VerificationError(f"{label} legality or retention failed")
    floor = _finite_number(row["last_supported_floor"], f"{label}.last_supported_floor")
    if not 0.0 <= floor <= MAX_FLOOR:
        raise VerificationError(f"{label} floor is outside bounds")
    reward = _finite_number(row["total_reward"], f"{label}.total_reward")
    if not 0.0 <= reward <= VICTORY_WEIGHT + 1.0 + 1e-9:
        raise VerificationError(f"{label} reward is outside the formal bound")
    unsupported = row["unsupported_reason"]
    if unsupported is None:
        if row["outcome"] not in {"player_loss", "player_victory"}:
            raise VerificationError(f"{label} terminal outcome is invalid")
        terminal_floor = _finite_number(row["terminal_floor"], f"{label}.terminal_floor")
        if terminal_floor != floor:
            raise VerificationError(f"{label} terminal floor mismatch")
        if row["victory"] is not (row["outcome"] == "player_victory"):
            raise VerificationError(f"{label} victory flag mismatch")
    else:
        if (
            unsupported not in REGISTERED_SUPPORT_BLOCKERS
            or row["outcome"] is not None
            or row["terminal_floor"] is not None
            or row["victory"] is not False
        ):
            raise VerificationError(f"{label} unsupported episode is invalid")
    return row


def _validate_diagnostic_row(
    value: Any, label: str, *, require_greedy: bool = False
) -> dict[str, Any]:
    row = dict(_mapping(value, label))
    _require_keys(
        row,
        {
            "candidate_scores",
            "candidates",
            "category",
            "decision_id",
            "selected_action_id",
            "state_effect",
        },
        label,
    )
    if row["category"] not in TARGET_CATEGORIES:
        raise VerificationError(f"{label} category is invalid")
    if not isinstance(row["decision_id"], str) or not row["decision_id"]:
        raise VerificationError(f"{label} decision id is invalid")
    candidates = list(_sequence(row["candidates"], f"{label}.candidates"))
    if not candidates:
        raise VerificationError(f"{label} candidates are empty")
    ids: list[str] = []
    for index, raw in enumerate(candidates):
        candidate = dict(_mapping(raw, f"{label}.candidates[{index}]"))
        _require_keys(candidate, {"action_id", "kind"}, f"{label}.candidates[{index}]")
        if any(
            not isinstance(candidate[name], str) or not candidate[name]
            for name in ("action_id", "kind")
        ):
            raise VerificationError(f"{label} candidate is invalid")
        ids.append(candidate["action_id"])
    if len(ids) != len(set(ids)):
        raise VerificationError(f"{label} candidate ids are duplicated")
    if row["selected_action_id"] not in ids:
        raise VerificationError(f"{label} selected action is not a candidate")
    scores = dict(_mapping(row["candidate_scores"], f"{label}.candidate_scores"))
    if set(scores) != set(ids):
        raise VerificationError(f"{label} score keys differ from candidates")
    for action_id, score in scores.items():
        _finite_number(score, f"{label}.candidate_scores.{action_id}")
    effect = dict(_mapping(row["state_effect"], f"{label}.state_effect"))
    _require_keys(
        effect,
        {
            "category",
            "decision_id",
            "max_abs_relative_score_change",
            "relative_order_changed",
            "zero_state_scores",
        },
        f"{label}.state_effect",
    )
    if effect["category"] != row["category"] or effect["decision_id"] != row["decision_id"]:
        raise VerificationError(f"{label} state-effect identity mismatch")
    if _finite_number(
        effect["max_abs_relative_score_change"],
        f"{label}.state_effect.magnitude",
    ) < 0.0:
        raise VerificationError(f"{label} state-effect magnitude is negative")
    if type(effect["relative_order_changed"]) is not bool:
        raise VerificationError(f"{label} state-effect order flag is invalid")
    zero_scores = [
        _float32(_finite_number(score, f"{label}.state_effect.zero_scores"))
        for score in _sequence(
            effect["zero_state_scores"], f"{label}.state_effect.zero_scores"
        )
    ]
    if len(zero_scores) != len(candidates):
        raise VerificationError(f"{label} zero-state score count mismatch")
    actual_scores = [_float32(scores[action_id]) for action_id in ids]
    if require_greedy:
        greedy_index = max(
            range(len(actual_scores)), key=actual_scores.__getitem__
        )
        if row["selected_action_id"] != ids[greedy_index]:
            raise VerificationError(
                f"{label} selected action is not the deterministic greedy argmax"
            )
    if len(actual_scores) < 2:
        expected_magnitude = 0.0
        expected_order_change = False
    else:
        actual_relative = [
            _float32(value - actual_scores[0]) for value in actual_scores
        ]
        zero_relative = [
            _float32(value - zero_scores[0]) for value in zero_scores
        ]
        differences = [
            _float32(actual - zero)
            for actual, zero in zip(actual_relative, zero_relative)
        ]
        expected_magnitude = max(abs(value) for value in differences)
        actual_order = tuple(
            sorted(range(len(actual_scores)), key=lambda index: (-actual_scores[index], index))
        )
        zero_order = tuple(
            sorted(range(len(zero_scores)), key=lambda index: (-zero_scores[index], index))
        )
        expected_order_change = actual_order != zero_order
    if effect["max_abs_relative_score_change"] != expected_magnitude:
        raise VerificationError(f"{label} state-effect magnitude does not recompute")
    if effect["relative_order_changed"] is not expected_order_change:
        raise VerificationError(f"{label} state-effect order does not recompute")
    return row


def _distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "max": None, "mean": None, "median": None, "min": None}
    return {
        "count": len(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
    }


def _summarize_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise VerificationError("diagnostic rows must be nonempty")
    normalized = [
        _validate_diagnostic_row(row, f"diagnostic_rows[{index}]")
        for index, row in enumerate(rows)
    ]
    decision_ids = [row["decision_id"] for row in normalized]
    if len(decision_ids) != len(set(decision_ids)):
        raise VerificationError("diagnostic decision ids are not unique")
    by_category: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in normalized:
        by_category[row["category"]].append(row)
    categories: dict[str, Any] = {}
    for category, category_rows in sorted(by_category.items()):
        opportunity_counts: Counter[str] = Counter()
        occurrence_counts: Counter[str] = Counter()
        selected_counts: Counter[str] = Counter()
        multi_kind_selected_counts: Counter[str] = Counter()
        top_margins: list[float] = []
        selected_margins: list[float] = []
        single_candidate_decisions = 0
        multi_kind_decisions = 0
        for row in sorted(category_rows, key=lambda item: item["decision_id"]):
            candidate_kinds = {
                candidate["action_id"]: candidate["kind"]
                for candidate in row["candidates"]
            }
            occurrence_counts.update(candidate_kinds.values())
            opportunity_counts.update(set(candidate_kinds.values()))
            selected_counts[candidate_kinds[row["selected_action_id"]]] += 1
            if len(set(candidate_kinds.values())) > 1:
                multi_kind_decisions += 1
                multi_kind_selected_counts[
                    candidate_kinds[row["selected_action_id"]]
                ] += 1
            scores = row["candidate_scores"]
            if len(scores) == 1:
                single_candidate_decisions += 1
                continue
            ordered = sorted(scores.values(), reverse=True)
            top_margins.append(float(ordered[0]) - float(ordered[1]))
            alternatives = [
                float(score)
                for action_id, score in scores.items()
                if action_id != row["selected_action_id"]
            ]
            selected_margins.append(
                float(scores[row["selected_action_id"]]) - max(alternatives)
            )
        decision_count = len(category_rows)
        summary: dict[str, Any] = {
            "candidate_kind_occurrences": dict(sorted(occurrence_counts.items())),
            "candidate_kind_opportunities": dict(sorted(opportunity_counts.items())),
            "decision_count": decision_count,
            "distinct_candidate_kinds": sorted(occurrence_counts),
            "distinct_selected_kinds": sorted(selected_counts),
            "exact_single_kind_saturation": len(selected_counts) == 1,
            "multi_candidate_decisions": decision_count - single_candidate_decisions,
            "multi_kind_decisions": multi_kind_decisions,
            "multi_kind_selected_kinds": {
                kind: {"count": count, "rate": count / multi_kind_decisions}
                for kind, count in sorted(multi_kind_selected_counts.items())
            },
            "selected_kinds": {
                kind: {"count": count, "rate": count / decision_count}
                for kind, count in sorted(selected_counts.items())
            },
            "selected_score_margin": _distribution(selected_margins),
            "single_candidate_decisions": single_candidate_decisions,
            "top_score_margin": _distribution(top_margins),
        }
        if category == "card_reward":
            summary["card_reward"] = {
                "availability_decisions": {
                    kind: opportunity_counts.get(kind, 0)
                    for kind in CARD_REWARD_KINDS
                },
                "selections": {
                    kind: selected_counts.get(kind, 0)
                    for kind in CARD_REWARD_KINDS
                },
            }
        category_multi = [
            row for row in category_rows if len(row["candidates"]) > 1
        ]
        category_magnitudes = [
            float(row["state_effect"]["max_abs_relative_score_change"])
            for row in category_multi
        ]
        summary["state_effect"] = {
            "magnitude": _distribution(category_magnitudes),
            "multi_candidate_decisions": len(category_multi),
            "nonzero_effect_decisions": sum(
                value > 0.0 for value in category_magnitudes
            ),
            "relative_order_change_decisions": sum(
                row["state_effect"]["relative_order_changed"]
                for row in category_multi
            ),
        }
        categories[category] = summary
    multi_rows = [row for row in normalized if len(row["candidates"]) > 1]
    magnitudes = [
        float(row["state_effect"]["max_abs_relative_score_change"])
        for row in multi_rows
    ]
    return {
        "authority": _registration_authority(),
        "categories": categories,
        "decision_count": len(normalized),
        "schema_version": "noncombat-state-conditioned-experiment-diagnostics-v1",
        "state_effect": {
            "magnitude": _distribution(magnitudes),
            "multi_candidate_decisions": len(multi_rows),
            "nonzero_effect_decisions": sum(value > 0.0 for value in magnitudes),
            "relative_order_change_decisions": sum(
                row["state_effect"]["relative_order_changed"] for row in multi_rows
            ),
        },
    }


def _registered_chunk_coordinates(
    registration: Mapping[str, Any], chunk_index: int
) -> dict[str, Any]:
    chunk_index = _nonnegative_int(chunk_index, "registered chunk_index")
    train = list(registration["cohorts"]["train"])
    sequence = train * registration["limits"]["train_passes"]
    chunk_size = registration["limits"]["training_chunk_size"]
    start = chunk_index * chunk_size
    if start >= len(sequence):
        raise VerificationError("checkpoint chunk is outside registered coordinates")
    seeds = sequence[start : start + chunk_size]
    return {
        "chunk_index": chunk_index,
        "episode_end": start + len(seeds),
        "episode_start": start,
        "pass_index": start // len(train),
        "seeds": seeds,
    }


def _validate_training_chunk(
    value: Any,
    *,
    registration: Mapping[str, Any],
    chunk_index: int,
) -> dict[str, Any]:
    chunk = dict(_mapping(value, f"training chunk {chunk_index}"))
    _require_keys(
        chunk,
        {
            "categories",
            "chunk_index",
            "diagnostic_rows",
            "entropy_coefficient",
            "episode_end",
            "episode_rows",
            "episode_start",
            "episodes",
            "gradient_norm_after_clip",
            "gradient_norm_before_clip",
            "loss",
            "mean_entropy",
            "mean_episode_return",
            "optimizer_update",
            "pass_index",
            "unsupported_episodes",
            "victories",
        },
        f"training chunk {chunk_index}",
    )
    for name in ("chunk_index", "episode_end", "episode_start", "pass_index"):
        _nonnegative_int(chunk[name], f"training chunk {chunk_index} {name}")
    _positive_int(
        chunk["optimizer_update"],
        f"training chunk {chunk_index} optimizer_update",
    )
    _positive_int(chunk["episodes"], f"training chunk {chunk_index} episodes")
    for name in ("unsupported_episodes", "victories"):
        _nonnegative_int(chunk[name], f"training chunk {chunk_index} {name}")
    coordinates = _registered_chunk_coordinates(registration, chunk_index)
    for name in ("chunk_index", "episode_end", "episode_start", "pass_index"):
        if chunk[name] != coordinates[name]:
            raise VerificationError(f"training chunk {chunk_index} {name} mismatch")
    if chunk["optimizer_update"] != chunk_index + 1:
        raise VerificationError("training optimizer coordinate mismatch")
    if chunk["entropy_coefficient"] != ENTROPY_COEFFICIENT:
        raise VerificationError("training entropy coefficient mismatch")
    episode_rows = list(_sequence(chunk["episode_rows"], "training episode rows"))
    if chunk["episodes"] != len(coordinates["seeds"]) or len(episode_rows) != chunk["episodes"]:
        raise VerificationError("training chunk episode count mismatch")
    normalized_episodes = [
        _validate_episode_row(
            row,
            expected_seed=seed,
            expected_chunk=chunk_index,
            label=f"training chunk {chunk_index} episode[{index}]",
        )
        for index, (seed, row) in enumerate(zip(coordinates["seeds"], episode_rows))
    ]
    categories = sorted(
        {category for row in normalized_episodes for category in row["categories"]}
    )
    if chunk["categories"] != categories:
        raise VerificationError("training chunk category summary mismatch")
    if chunk["unsupported_episodes"] != sum(
        row["unsupported_reason"] is not None for row in normalized_episodes
    ):
        raise VerificationError("training unsupported count mismatch")
    if chunk["victories"] != sum(row["victory"] for row in normalized_episodes):
        raise VerificationError("training victory count mismatch")
    expected_mean = statistics.fmean(
        float(row["total_reward"]) for row in normalized_episodes
    )
    if chunk["mean_episode_return"] != expected_mean:
        raise VerificationError("training mean return mismatch")
    for name in (
        "gradient_norm_after_clip",
        "gradient_norm_before_clip",
        "loss",
        "mean_entropy",
        "mean_episode_return",
    ):
        _finite_number(chunk[name], f"training chunk {chunk_index} {name}")
    if not 0.0 <= chunk["gradient_norm_after_clip"] <= GRADIENT_NORM_CEILING + 1e-6:
        raise VerificationError("training clipped gradient is outside bound")
    if chunk["gradient_norm_after_clip"] > chunk["gradient_norm_before_clip"] + 1e-6:
        raise VerificationError("training gradient increased during clipping")
    if chunk["gradient_norm_before_clip"] < 0.0 or chunk["mean_entropy"] < 0.0:
        raise VerificationError("training gradient or entropy is negative")
    diagnostic_rows = list(
        _sequence(chunk["diagnostic_rows"], "training diagnostic rows")
    )
    normalized_diagnostics = [
        _validate_diagnostic_row(row, f"training diagnostic[{index}]")
        for index, row in enumerate(diagnostic_rows)
    ]
    expected_ids = [
        f"chunk-{chunk_index}:seed-{row['seed']}:decision-{decision_index}"
        for row in normalized_episodes
        for decision_index in range(row["decisions"])
    ]
    if [row["decision_id"] for row in normalized_diagnostics] != expected_ids:
        raise VerificationError("training diagnostic coordinates mismatch")
    expected_actions = [
        action_id
        for row in normalized_episodes
        for action_id in row["selected_action_ids"]
    ]
    if (
        [row["selected_action_id"] for row in normalized_diagnostics]
        != expected_actions
    ):
        raise VerificationError(
            "training diagnostic selected actions mismatch episodes"
        )
    return chunk


def _verify_checkpoints(
    output: Path,
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
) -> dict[str, Any]:
    checkpoint_dir = output / "checkpoints"
    if not checkpoint_dir.is_dir():
        raise VerificationError("checkpoint directory is missing")
    paths = sorted(checkpoint_dir.glob("checkpoint_*.json"))
    if sorted(path.name for path in checkpoint_dir.iterdir() if path.is_file()) != [
        path.name for path in paths
    ]:
        raise VerificationError("checkpoint directory contains extra files")
    previous_bytes: bytes | None = None
    checkpoint_sha256: list[str] = []
    chunks: list[dict[str, Any]] = []
    latest_runtime: dict[str, Any] | None = None
    latest_model: dict[str, Any] | None = None
    initial_model_sha256: str | None = None
    previous_wall = 0.0
    identity = registration["identity"]
    for expected_index, path in enumerate(paths, start=1):
        if path.name != f"checkpoint_{expected_index:04d}.json":
            raise VerificationError("checkpoint indices are not contiguous")
        checkpoint, payload = load_canonical_json(path)
        _require_keys(
            checkpoint,
            {
                "checkpoint_index",
                "identity",
                "initial_model_sha256",
                "previous_checkpoint_sha256",
                "runtime",
                "schema_version",
                "training_chunk",
            },
            f"checkpoint {expected_index}",
        )
        if checkpoint["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
            raise VerificationError("checkpoint schema mismatch")
        checkpoint_index = _positive_int(
            checkpoint["checkpoint_index"], f"checkpoint {expected_index} index"
        )
        if checkpoint_index != expected_index:
            raise VerificationError("checkpoint index mismatch")
        expected_identity = {
            "implementation_commit": identity["implementation"]["commit"],
            "logical_execution_id": identity["logical_execution_id"],
            "registration_sha256": registration_sha256,
        }
        if checkpoint["identity"] != expected_identity:
            raise VerificationError("checkpoint identity mismatch")
        initial_hash = _validate_sha256(
            checkpoint["initial_model_sha256"], "checkpoint initial model sha256"
        )
        if initial_model_sha256 is None:
            initial_model_sha256 = initial_hash
        elif initial_model_sha256 != initial_hash:
            raise VerificationError("checkpoint initial model identity drifted")
        expected_previous = (
            None if previous_bytes is None else hashlib.sha256(previous_bytes).hexdigest()
        )
        if checkpoint["previous_checkpoint_sha256"] != expected_previous:
            raise VerificationError("checkpoint predecessor hash mismatch")
        runtime = dict(_mapping(checkpoint["runtime"], "checkpoint runtime"))
        _require_keys(
            runtime,
            {
                "action_generator",
                "completed_episodes",
                "cumulative_wall_seconds",
                "entropy_coefficient",
                "gradient_norm_ceiling",
                "model",
                "next_chunk_index",
                "optimizer",
                "optimizer_updates",
                "python_random",
            },
            "checkpoint runtime",
        )
        next_chunk_index = _positive_int(
            runtime["next_chunk_index"], "checkpoint runtime next_chunk_index"
        )
        optimizer_updates = _positive_int(
            runtime["optimizer_updates"], "checkpoint runtime optimizer_updates"
        )
        completed_episodes = _positive_int(
            runtime["completed_episodes"], "checkpoint runtime completed_episodes"
        )
        if next_chunk_index != expected_index or optimizer_updates != expected_index:
            raise VerificationError("checkpoint runtime coordinates mismatch")
        coordinates = _registered_chunk_coordinates(registration, expected_index - 1)
        if completed_episodes != coordinates["episode_end"]:
            raise VerificationError("checkpoint completed episode coordinate mismatch")
        wall = _finite_number(runtime["cumulative_wall_seconds"], "checkpoint wall time")
        if wall < previous_wall or wall > registration["limits"]["max_wall_seconds"]:
            raise VerificationError("checkpoint wall time is outside bounds")
        previous_wall = wall
        if (
            runtime["entropy_coefficient"] != ENTROPY_COEFFICIENT
            or runtime["gradient_norm_ceiling"] != GRADIENT_NORM_CEILING
        ):
            raise VerificationError("checkpoint algorithm controls drifted")
        _validate_tensor(runtime["action_generator"], "checkpoint action generator")
        model = _validate_ranker_model(runtime["model"], "checkpoint model")
        _validate_optimizer(runtime["optimizer"], "checkpoint optimizer")
        _validate_encoded_state(runtime["python_random"], "checkpoint Python random")
        chunk = _validate_training_chunk(
            checkpoint["training_chunk"],
            registration=registration,
            chunk_index=expected_index - 1,
        )
        chunks.append(chunk)
        checkpoint_sha256.append(hashlib.sha256(payload).hexdigest())
        latest_runtime = runtime
        latest_model = model
        previous_bytes = payload
    return {
        "checkpoint_count": len(paths),
        "checkpoint_sha256": checkpoint_sha256,
        "chunks": chunks,
        "initial_model_sha256": initial_model_sha256,
        "latest_model": latest_model,
        "latest_runtime": latest_runtime,
    }


def _verify_journal(
    output: Path,
    *,
    registration: Mapping[str, Any],
    checkpoint_state: Mapping[str, Any],
) -> dict[str, Any]:
    journal, _ = load_canonical_json(output / "execution_journal.json")
    _require_keys(
        journal,
        {"logical_execution_id", "records", "schema_version", "state"},
        "execution journal",
    )
    if journal["schema_version"] != JOURNAL_SCHEMA_VERSION:
        raise VerificationError("execution journal schema mismatch")
    if journal["logical_execution_id"] != registration["identity"]["logical_execution_id"]:
        raise VerificationError("execution journal identity mismatch")
    if journal["state"] != "terminal":
        raise VerificationError("execution journal is not terminal")
    records = list(_sequence(journal["records"], "journal records"))
    if not records:
        raise VerificationError("execution journal is empty")
    previous_checkpoint = 0
    previous_completed = 0
    previous_state: str | None = None
    previous_operation: str | None = None
    checkpoint_records = 0
    evidence_names: set[str] = set()
    for sequence, raw in enumerate(records):
        record = dict(_mapping(raw, f"journal record[{sequence}]"))
        state = record.get("state")
        expected_keys = {
            "checkpoint_index",
            "completed_episodes",
            "sequence",
            "state",
        }
        if state == "checkpoint":
            expected_keys.add("checkpoint_sha256")
        elif state == "operation":
            expected_keys.add("operation")
        elif state == "evidence":
            expected_keys.update({"name", "payload", "payload_sha256"})
        elif state == "terminal":
            expected_keys.add("reason")
        _require_keys(record, expected_keys, f"journal record[{sequence}]")
        checkpoint_index = _nonnegative_int(
            record["checkpoint_index"],
            f"journal record[{sequence}].checkpoint_index",
        )
        completed = _nonnegative_int(
            record["completed_episodes"],
            f"journal record[{sequence}].completed_episodes",
        )
        if _nonnegative_int(
            record["sequence"], f"journal record[{sequence}].sequence"
        ) != sequence:
            raise VerificationError("execution journal sequence is not contiguous")
        if sequence == 0:
            if state != "started" or checkpoint_index != 0 or completed != 0:
                raise VerificationError("execution journal must start at zero")
        elif state == "started":
            raise VerificationError("execution journal repeats started state")
        elif state == "checkpoint":
            checkpoint_records += 1
            if (
                checkpoint_index != previous_checkpoint + 1
                or checkpoint_records != checkpoint_index
                or checkpoint_index > checkpoint_state["checkpoint_count"]
            ):
                raise VerificationError("execution journal checkpoint sequence mismatch")
            chunk = checkpoint_state["chunks"][checkpoint_index - 1]
            if completed != chunk["episode_end"]:
                raise VerificationError("execution journal checkpoint coordinate mismatch")
            if record["checkpoint_sha256"] != checkpoint_state[
                "checkpoint_sha256"
            ][checkpoint_index - 1]:
                raise VerificationError("execution journal checkpoint sha256 mismatch")
            if (
                previous_state != "operation"
                or previous_operation != f"training_chunk:{checkpoint_index - 1}"
            ):
                raise VerificationError("checkpoint lacks its started training operation")
        elif state in {"evidence", "operation", "terminal"}:
            if (
                checkpoint_index != previous_checkpoint
                or completed != previous_completed
            ):
                raise VerificationError(f"execution journal {state} coordinate mismatch")
            if state == "operation":
                operation = record["operation"]
                if not isinstance(operation, str) or not (
                    re.fullmatch(r"training_chunk:[0-9]+", operation)
                    or operation in {"evaluation:canary", "evaluation:holdout"}
                ):
                    raise VerificationError("execution journal operation is invalid")
                if operation.startswith("training_chunk:") and operation != (
                    f"training_chunk:{checkpoint_index}"
                ):
                    raise VerificationError("training operation coordinate mismatch")
                previous_operation = operation
            elif state == "evidence":
                name = record["name"]
                expected_operation = {
                    "canary_evaluation": "evaluation:canary",
                    "complete_evaluation": "evaluation:holdout",
                }.get(name)
                if (
                    expected_operation is None
                    or name in evidence_names
                    or previous_state != "operation"
                    or previous_operation != expected_operation
                ):
                    raise VerificationError("execution journal evidence transition mismatch")
                payload = dict(
                    _mapping(record["payload"], "execution journal evidence payload")
                )
                if record["payload_sha256"] != hashlib.sha256(
                    canonical_json_bytes(payload)
                ).hexdigest():
                    raise VerificationError("execution journal evidence sha256 mismatch")
                evidence_names.add(name)
            else:
                if sequence != len(records) - 1:
                    raise VerificationError("execution journal has records after terminal")
                if not isinstance(record["reason"], str) or not record["reason"]:
                    raise VerificationError("execution journal terminal reason is invalid")
        else:
            raise VerificationError("execution journal state is invalid")
        previous_checkpoint = checkpoint_index
        previous_completed = completed
        previous_state = state
    if previous_state != "terminal":
        raise VerificationError("execution journal lacks a terminal record")
    if checkpoint_records != checkpoint_state["checkpoint_count"]:
        raise VerificationError("execution journal checkpoint count mismatch")
    return journal


def _verify_training_rows(
    output: Path, checkpoint_state: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    training, _ = load_canonical_json(output / "training_rows.json")
    _require_keys(training, {"chunks", "episode_count", "schema_version"}, "training rows")
    if training["schema_version"] != "noncombat-state-conditioned-training-rows-v1":
        raise VerificationError("training rows schema mismatch")
    if not _json_values_equal(training["chunks"], checkpoint_state["chunks"]):
        raise VerificationError("training rows differ from checkpoint chunks")
    episodes = [
        row for chunk in checkpoint_state["chunks"] for row in chunk["episode_rows"]
    ]
    diagnostics = [
        row for chunk in checkpoint_state["chunks"] for row in chunk["diagnostic_rows"]
    ]
    episode_count = _nonnegative_int(
        training["episode_count"], "training rows episode_count"
    )
    if episode_count != len(episodes):
        raise VerificationError("training rows episode count mismatch")
    return training, episodes, diagnostics


def _verify_final_model(
    output: Path,
    *,
    checkpoint_state: Mapping[str, Any],
) -> dict[str, Any]:
    final_model, _ = load_canonical_json(output / "final_model.json")
    _require_keys(
        final_model,
        {
            "architecture",
            "authority",
            "initial_model_sha256",
            "model",
            "model_loading_authorized",
            "schema_version",
        },
        "final model",
    )
    if final_model["schema_version"] != "noncombat-state-conditioned-final-model-v1":
        raise VerificationError("final model schema mismatch")
    _all_false_exact(final_model["authority"], "final model authority")
    if final_model["model_loading_authorized"] is not False:
        raise VerificationError("final model loading authority is not false")
    expected_architecture = dict(_experiment_contract()["model"])
    expected_architecture.pop("channel_composition")
    if final_model["architecture"] != expected_architecture:
        raise VerificationError("final model architecture mismatch")
    model = _validate_ranker_model(final_model["model"], "final model")
    initial_hash = _validate_sha256(
        final_model["initial_model_sha256"], "final model initial sha256"
    )
    if checkpoint_state["checkpoint_count"]:
        if model != checkpoint_state["latest_model"]:
            raise VerificationError("final model differs from latest checkpoint")
        if initial_hash != checkpoint_state["initial_model_sha256"]:
            raise VerificationError("final model initial identity mismatch")
    elif initial_hash != hashlib.sha256(canonical_json_bytes(model)).hexdigest():
        raise VerificationError("untrained final model differs from initialization")
    return final_model


def _verify_isolation(
    output: Path, *, registration: Mapping[str, Any]
) -> dict[str, Any]:
    isolation, _ = load_canonical_json(output / "isolation.json")
    _require_keys(
        isolation,
        {"authority", "post", "pre", "schema_version", "unchanged"},
        "isolation",
    )
    if isolation["schema_version"] != "noncombat-state-conditioned-isolation-v1":
        raise VerificationError("isolation schema mismatch")
    _all_false_exact(isolation["authority"], "isolation authority")
    expected_pre = registration["identity"]["isolation"]
    if not _json_values_equal(isolation["pre"], expected_pre):
        raise VerificationError("pre-execution isolation differs from registration")
    post = dict(_mapping(isolation["post"], "post-execution isolation"))
    _require_keys(
        post,
        {"communication_mod_config", "production_checkpoints"},
        "post-execution isolation",
    )
    post_config = _validate_external_binding(
        post["communication_mod_config"], "post CommunicationMod binding"
    )
    post_checkpoints = _validate_checkpoint_inventory(
        post["production_checkpoints"], "post production checkpoint inventory"
    )
    if isolation["unchanged"] is not _json_values_equal(post, expected_pre):
        raise VerificationError("isolation unchanged flag mismatch")
    try:
        config_path = Path(post_config["path"]).resolve()
        config_payload = config_path.read_bytes()
    except OSError as exc:
        raise VerificationError(
            "live CommunicationMod configuration could not be read"
        ) from exc
    current_config = {
        "path": config_path.as_posix(),
        "sha256": hashlib.sha256(config_payload).hexdigest(),
        "size_bytes": len(config_payload),
    }
    if not _json_values_equal(current_config, post_config):
        raise VerificationError("live CommunicationMod configuration drifted")
    checkpoint_root = Path(post_checkpoints["root"]).resolve()
    try:
        if not checkpoint_root.is_dir():
            raise VerificationError("live production checkpoint root is missing")
        current_entries = []
        for path in sorted(
            (candidate for candidate in checkpoint_root.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(checkpoint_root).as_posix(),
        ):
            payload = path.read_bytes()
            current_entries.append(
                {
                    "path": path.relative_to(checkpoint_root).as_posix(),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                }
            )
    except OSError as exc:
        raise VerificationError(
            "live production checkpoint inventory could not be read"
        ) from exc
    current_checkpoints = {
        "entries": current_entries,
        "inventory_sha256": hashlib.sha256(
            canonical_json_bytes(current_entries)
        ).hexdigest(),
        "root": checkpoint_root.as_posix(),
        "total_bytes": sum(row["size_bytes"] for row in current_entries),
    }
    if not _json_values_equal(current_checkpoints, post_checkpoints):
        raise VerificationError("live production checkpoint inventory drifted")
    return isolation


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(
        sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight
    )


def _paired_bootstrap(
    differences: Sequence[float], *, resamples: int
) -> dict[str, Any]:
    generator = random.Random(MODEL_SEED)
    means = sorted(
        statistics.fmean(generator.choice(differences) for _ in differences)
        for _ in range(resamples)
    )
    return {
        "confidence": BOOTSTRAP_CONFIDENCE,
        "lower": _quantile(means, 0.025),
        "mean": statistics.fmean(differences),
        "resamples": resamples,
        "seed": MODEL_SEED,
        "upper": _quantile(means, 0.975),
    }


def _verify_evaluation_policy(
    value: Any,
    *,
    seeds: Sequence[int],
    label: str,
) -> dict[str, Any]:
    policy = dict(_mapping(value, label))
    _require_keys(
        policy,
        {
            "categories",
            "diagnostic_rows",
            "diagnostics",
            "episode_rows",
            "replay_diagnostic_rows",
            "replay_exact",
            "replay_episode_rows",
            "unsupported_episodes",
            "victories",
        },
        label,
    )
    for name in ("unsupported_episodes", "victories"):
        _nonnegative_int(policy[name], f"{label}.{name}")
    episode_rows = list(_sequence(policy["episode_rows"], f"{label}.episode_rows"))
    if len(episode_rows) != len(seeds):
        raise VerificationError(f"{label} episode count mismatch")
    normalized_episodes = [
        _validate_episode_row(
            row,
            expected_seed=seed,
            expected_chunk=None,
            label=f"{label}.episode_rows[{index}]",
        )
        for index, (seed, row) in enumerate(zip(seeds, episode_rows))
    ]
    if policy["replay_exact"] is not True:
        raise VerificationError(f"{label} replay was not exact")
    replay_episode_rows = list(
        _sequence(policy["replay_episode_rows"], f"{label}.replay_episode_rows")
    )
    if not _json_values_equal(replay_episode_rows, episode_rows):
        raise VerificationError(f"{label} replay episode rows differ")
    if policy["unsupported_episodes"] != sum(
        row["unsupported_reason"] is not None for row in normalized_episodes
    ):
        raise VerificationError(f"{label} unsupported count mismatch")
    if policy["victories"] != sum(row["victory"] for row in normalized_episodes):
        raise VerificationError(f"{label} victory count mismatch")
    categories = sorted(
        {category for row in normalized_episodes for category in row["categories"]}
    )
    if policy["categories"] != categories:
        raise VerificationError(f"{label} category summary mismatch")
    diagnostic_rows = list(
        _sequence(policy["diagnostic_rows"], f"{label}.diagnostic_rows")
    )
    normalized_diagnostics = [
        _validate_diagnostic_row(
            row,
            f"{label}.diagnostic_rows[{index}]",
            require_greedy=True,
        )
        for index, row in enumerate(diagnostic_rows)
    ]
    expected_ids = [
        f"seed-{row['seed']}:decision-{decision_index}"
        for row in normalized_episodes
        for decision_index in range(row["decisions"])
    ]
    if [row["decision_id"] for row in normalized_diagnostics] != expected_ids:
        raise VerificationError(f"{label} diagnostic coordinates mismatch")
    expected_actions = [
        action_id
        for row in normalized_episodes
        for action_id in row["selected_action_ids"]
    ]
    if (
        [row["selected_action_id"] for row in normalized_diagnostics]
        != expected_actions
    ):
        raise VerificationError(
            f"{label} diagnostic selected actions mismatch episodes"
        )
    replay_diagnostic_rows = list(
        _sequence(
            policy["replay_diagnostic_rows"],
            f"{label}.replay_diagnostic_rows",
        )
    )
    if not _json_values_equal(replay_diagnostic_rows, diagnostic_rows):
        raise VerificationError(f"{label} replay diagnostic rows differ")
    expected_diagnostics = _summarize_diagnostics(normalized_diagnostics)
    if not _json_values_equal(policy["diagnostics"], expected_diagnostics):
        raise VerificationError(f"{label} diagnostics do not recompute")
    return policy


def _verify_paired_evaluation(
    value: Any,
    *,
    registration: Mapping[str, Any],
    cohort: str,
) -> dict[str, Any]:
    evaluation = dict(_mapping(value, f"{cohort} evaluation"))
    _require_keys(
        evaluation,
        {
            "cohort",
            "floor_difference_ci",
            "initial",
            "paired_rows",
            "schema_version",
            "seeds",
            "trained",
            "unsupported_rate",
            "unsupported_rate_denominator",
        },
        f"{cohort} evaluation",
    )
    if (
        evaluation["schema_version"] != EVALUATION_SCHEMA_VERSION
        or evaluation["cohort"] != cohort
    ):
        raise VerificationError(f"{cohort} evaluation identity mismatch")
    seeds = [
        _nonnegative_int(seed, f"registered {cohort} seed[{index}]")
        for index, seed in enumerate(registration["cohorts"][cohort])
    ]
    evaluation_seeds = [
        _nonnegative_int(seed, f"{cohort} evaluation seed[{index}]")
        for index, seed in enumerate(
            _sequence(evaluation["seeds"], f"{cohort} evaluation seeds")
        )
    ]
    if evaluation_seeds != seeds:
        raise VerificationError(f"{cohort} evaluation seeds mismatch")
    initial = _verify_evaluation_policy(
        evaluation["initial"], seeds=seeds, label=f"{cohort}.initial"
    )
    trained = _verify_evaluation_policy(
        evaluation["trained"], seeds=seeds, label=f"{cohort}.trained"
    )
    expected_pairs = []
    for seed, initial_row, trained_row in zip(
        seeds, initial["episode_rows"], trained["episode_rows"]
    ):
        initial_floor = float(initial_row["last_supported_floor"])
        trained_floor = float(trained_row["last_supported_floor"])
        expected_pairs.append(
            {
                "floor_difference": trained_floor - initial_floor,
                "initial_floor": initial_floor,
                "initial_victory": bool(initial_row["victory"]),
                "seed": seed,
                "trained_floor": trained_floor,
                "trained_victory": bool(trained_row["victory"]),
                "victory_difference": int(trained_row["victory"])
                - int(initial_row["victory"]),
            }
        )
    paired_rows = list(
        _sequence(evaluation["paired_rows"], f"{cohort} paired rows")
    )
    for index, raw in enumerate(paired_rows):
        row = dict(_mapping(raw, f"{cohort} paired row[{index}]"))
        _require_keys(
            row,
            {
                "floor_difference",
                "initial_floor",
                "initial_victory",
                "seed",
                "trained_floor",
                "trained_victory",
                "victory_difference",
            },
            f"{cohort} paired row[{index}]",
        )
        _nonnegative_int(row["seed"], f"{cohort} paired row[{index}].seed")
        _strict_int(
            row["victory_difference"],
            f"{cohort} paired row[{index}].victory_difference",
        )
        for name in ("initial_victory", "trained_victory"):
            if type(row[name]) is not bool:
                raise VerificationError(
                    f"{cohort} paired row[{index}].{name} must be boolean"
                )
        for name in ("floor_difference", "initial_floor", "trained_floor"):
            _finite_number(row[name], f"{cohort} paired row[{index}].{name}")
    if not _json_values_equal(paired_rows, expected_pairs):
        raise VerificationError(f"{cohort} paired rows do not recompute")
    expected_ci = _paired_bootstrap(
        [row["floor_difference"] for row in expected_pairs],
        resamples=registration["limits"]["bootstrap_resamples"],
    )
    interval = dict(
        _mapping(evaluation["floor_difference_ci"], f"{cohort} bootstrap interval")
    )
    _require_keys(
        interval,
        {"confidence", "lower", "mean", "resamples", "seed", "upper"},
        f"{cohort} bootstrap interval",
    )
    _positive_int(interval["resamples"], f"{cohort} bootstrap resamples")
    _nonnegative_int(interval["seed"], f"{cohort} bootstrap seed")
    for name in ("confidence", "lower", "mean", "upper"):
        _finite_number(interval[name], f"{cohort} bootstrap {name}")
    if not _json_values_equal(interval, expected_ci):
        raise VerificationError(f"{cohort} bootstrap interval does not recompute")
    denominator = 2 * len(seeds)
    expected_unsupported = (
        initial["unsupported_episodes"] + trained["unsupported_episodes"]
    ) / denominator
    rate_denominator = _positive_int(
        evaluation["unsupported_rate_denominator"],
        f"{cohort} unsupported_rate_denominator",
    )
    unsupported_rate = _finite_number(
        evaluation["unsupported_rate"], f"{cohort} unsupported_rate"
    )
    if rate_denominator != denominator or unsupported_rate != expected_unsupported:
        raise VerificationError(f"{cohort} unsupported rate does not recompute")
    return evaluation


def _classify_behavior(
    diagnostics: Mapping[str, Any], contract: Mapping[str, Any]
) -> dict[str, Any]:
    categories = diagnostics["categories"]
    blockers: list[str] = []
    for category in contract["category_coverage"]:
        if category not in categories or categories[category]["decision_count"] <= 0:
            blockers.append(f"{category}_coverage")
    multi = contract["multi_kind"]
    for category in multi["categories"]:
        summary = categories.get(category)
        if not summary:
            continue
        if summary["multi_kind_decisions"] < multi["minimum_multi_kind_decisions"]:
            blockers.append(f"{category}_multi_kind_opportunities")
            continue
        selected = summary["multi_kind_selected_kinds"]
        maximum_rate = max(
            (float(row["rate"]) for row in selected.values()), default=0.0
        )
        if (
            len(selected) < multi["minimum_selected_kinds"]
            or maximum_rate > multi["maximum_selected_kind_rate"]
        ):
            blockers.append(f"{category}_selected_kind_saturation")
    state_contract = contract["state_effect"]
    for category in contract["category_coverage"]:
        summary = categories.get(category)
        if not summary:
            continue
        state = dict(_mapping(summary.get("state_effect"), f"{category} state effect"))
        multi_count = _nonnegative_int(
            state.get("multi_candidate_decisions"),
            f"{category} multi-candidate decisions",
        )
        nonzero = _nonnegative_int(
            state.get("nonzero_effect_decisions"),
            f"{category} nonzero-effect decisions",
        )
        relative_order_changes = _nonnegative_int(
            state.get("relative_order_change_decisions"),
            f"{category} relative-order-change decisions",
        )
        magnitude = dict(
            _mapping(state.get("magnitude"), f"{category} state-effect magnitude")
        )
        maximum = magnitude.get("max")
        state_passed = (
            multi_count >= state_contract["minimum_multi_candidate_decisions"]
            and nonzero / multi_count >= state_contract["minimum_nonzero_effect_rate"]
            and relative_order_changes
            >= state_contract["minimum_relative_order_change_decisions"]
            and isinstance(maximum, (int, float))
            and not isinstance(maximum, bool)
            and maximum
            >= state_contract["minimum_absolute_relative_score_change"]
        ) if multi_count else False
        if not state_passed:
            blockers.append(f"{category}_state_effect")
    return {
        "blockers": blockers,
        "passed": not blockers,
        "schema_version": "noncombat-state-conditioned-behavior-gate-v1",
    }


def _classify_canary(
    evaluation: Mapping[str, Any], registration: Mapping[str, Any]
) -> dict[str, Any]:
    blockers: list[str] = []
    for policy_name in ("initial", "trained"):
        policy = evaluation[policy_name]
        if policy["categories"] != list(TARGET_CATEGORIES):
            blockers.append(f"{policy_name}_four_category_coverage")
        if policy["replay_exact"] is not True:
            blockers.append(f"{policy_name}_replay_exact")
    if evaluation["unsupported_rate"] > registration["limits"]["unsupported_rate_ceiling"]:
        blockers.append("unsupported_rate")
    if evaluation["trained"]["victories"] < evaluation["initial"]["victories"]:
        blockers.append("trained_victory_noninferiority")
    if evaluation["floor_difference_ci"]["lower"] <= 0.0:
        blockers.append("paired_floor_lower_bound")
    behavior = _classify_behavior(
        evaluation["trained"]["diagnostics"], registration["behavior_gates"]
    )
    blockers.extend(behavior["blockers"])
    blockers = list(dict.fromkeys(blockers))
    return {
        "behavior_gate": behavior,
        "blockers": blockers,
        "floor_difference_ci": evaluation["floor_difference_ci"],
        "initial_victories": evaluation["initial"]["victories"],
        "passed": not blockers,
        "trained_victories": evaluation["trained"]["victories"],
        "unsupported_rate": evaluation["unsupported_rate"],
        "verdict": "canary_passed" if not blockers else "experiment_stopped_at_canary",
    }


def _verify_evaluation(
    output: Path, *, registration: Mapping[str, Any]
) -> dict[str, Any]:
    terminal, _ = load_canonical_json(output / "evaluation.json")
    _require_keys(terminal, {"canary", "canary_gate", "holdout", "verdict"}, "evaluation")
    canary = _verify_paired_evaluation(
        terminal["canary"], registration=registration, cohort="canary"
    )
    canary_gate = _classify_canary(canary, registration)
    if not _json_values_equal(terminal["canary_gate"], canary_gate):
        raise VerificationError("canary gate does not recompute")
    if not canary_gate["passed"]:
        holdout_wrapper = dict(_mapping(terminal["holdout"], "holdout wrapper"))
        _require_keys(holdout_wrapper, {"accessed", "episode_count"}, "holdout wrapper")
        episode_count = _nonnegative_int(
            holdout_wrapper["episode_count"], "holdout episode_count"
        )
        if holdout_wrapper["accessed"] is not False or episode_count != 0:
            raise VerificationError("failed canary accessed holdout evidence")
        expected_verdict = "experiment_stopped_at_canary"
    else:
        holdout_wrapper = dict(_mapping(terminal["holdout"], "holdout wrapper"))
        if set(holdout_wrapper) == {"accessed", "episode_count"}:
            episode_count = _nonnegative_int(
                holdout_wrapper["episode_count"], "holdout episode count"
            )
            if holdout_wrapper["accessed"] is not False or episode_count != 0:
                raise VerificationError("pending holdout wrapper is invalid")
            expected_verdict = "canary_passed_pending_holdout"
            if terminal["verdict"] != expected_verdict:
                raise VerificationError("terminal evaluation verdict does not recompute")
            return terminal
        _require_keys(
            holdout_wrapper,
            {"accessed", "behavior_gate", "episode_count", "evaluation"},
            "holdout wrapper",
        )
        if holdout_wrapper["accessed"] is not True:
            raise VerificationError("passed canary did not access holdout")
        holdout = _verify_paired_evaluation(
            holdout_wrapper["evaluation"], registration=registration, cohort="holdout"
        )
        behavior = _classify_behavior(
            holdout["trained"]["diagnostics"], registration["behavior_gates"]
        )
        if not _json_values_equal(holdout_wrapper["behavior_gate"], behavior):
            raise VerificationError("holdout behavior gate does not recompute")
        episode_count = _positive_int(
            holdout_wrapper["episode_count"], "holdout episode_count"
        )
        if episode_count != 4 * len(registration["cohorts"]["holdout"]):
            raise VerificationError("holdout episode access count mismatch")
        structural = (
            holdout["initial"]["replay_exact"] is True
            and holdout["trained"]["replay_exact"] is True
            and holdout["initial"]["categories"] == list(TARGET_CATEGORIES)
            and holdout["trained"]["categories"] == list(TARGET_CATEGORIES)
            and holdout["unsupported_rate"]
            <= registration["limits"]["unsupported_rate_ceiling"]
        )
        if not structural:
            expected_verdict = "experiment_invalid"
        elif (
            behavior["passed"]
            and holdout["trained"]["victories"]
            >= holdout["initial"]["victories"]
            and holdout["floor_difference_ci"]["lower"] > 0.0
            and holdout["trained"]["victories"] > holdout["initial"]["victories"]
        ):
            expected_verdict = "experiment_valid_with_victory_signal"
        elif (
            behavior["passed"]
            and holdout["trained"]["victories"]
            >= holdout["initial"]["victories"]
            and holdout["floor_difference_ci"]["lower"] > 0.0
        ):
            expected_verdict = "experiment_valid_with_floor_only_signal"
        else:
            expected_verdict = "experiment_valid_without_learning_signal"
    if terminal["verdict"] != expected_verdict:
        raise VerificationError("terminal evaluation verdict does not recompute")
    return terminal


def _verify_terminal_diagnostics(
    output: Path,
    *,
    training_diagnostic_rows: Sequence[Mapping[str, Any]],
    evaluation: Mapping[str, Any] | None,
) -> dict[str, Any]:
    diagnostics, _ = load_canonical_json(output / "diagnostics.json")
    _require_keys(
        diagnostics,
        {"authority", "evaluation", "schema_version", "training"},
        "terminal diagnostics",
    )
    if diagnostics["schema_version"] != "noncombat-state-conditioned-terminal-diagnostics-v1":
        raise VerificationError("terminal diagnostics schema mismatch")
    _all_false_exact(diagnostics["authority"], "terminal diagnostics authority")
    expected_training = (
        _summarize_diagnostics(training_diagnostic_rows)
        if training_diagnostic_rows
        else None
    )
    if not _json_values_equal(diagnostics["training"], expected_training):
        raise VerificationError("training diagnostics do not recompute")
    expected_evaluation = None
    if evaluation is not None:
        holdout = evaluation["holdout"]
        expected_evaluation = {
            "canary_initial": evaluation["canary"]["initial"]["diagnostics"],
            "canary_trained": evaluation["canary"]["trained"]["diagnostics"],
            "holdout_accessed": holdout["accessed"],
            "holdout_initial": (
                holdout["evaluation"]["initial"]["diagnostics"]
                if holdout["accessed"]
                else None
            ),
            "holdout_trained": (
                holdout["evaluation"]["trained"]["diagnostics"]
                if holdout["accessed"]
                else None
            ),
        }
    if not _json_values_equal(diagnostics["evaluation"], expected_evaluation):
        raise VerificationError("evaluation diagnostics do not reproduce raw rows")
    return diagnostics


def _verify_metrics_and_report(
    output: Path,
    *,
    registration: Mapping[str, Any],
    checkpoint_state: Mapping[str, Any],
    training_episode_rows: Sequence[Mapping[str, Any]],
    isolation: Mapping[str, Any],
    evaluation: Mapping[str, Any] | None,
    manifest: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    metrics, _ = load_canonical_json(output / "metrics.json")
    _require_keys(
        metrics,
        {
            "authority",
            "blocked_reason",
            "completed_training_episodes",
            "cumulative_wall_seconds",
            "formal_readiness_unchanged",
            "isolation_unchanged",
            "optimizer_updates",
            "policy_quality_baseline_established",
            "schema_version",
            "target_supported_outcomes_established",
            "training_observed_only_floor_shaping",
            "training_unsupported_episodes",
            "training_victories",
            "verdict",
        },
        "metrics",
    )
    if metrics["schema_version"] != "noncombat-state-conditioned-terminal-metrics-v1":
        raise VerificationError("metrics schema mismatch")
    _all_false_exact(metrics["authority"], "metrics authority")
    for name in (
        "completed_training_episodes",
        "optimizer_updates",
        "training_unsupported_episodes",
        "training_victories",
    ):
        _nonnegative_int(metrics[name], f"metrics.{name}")
    latest_runtime = checkpoint_state["latest_runtime"]
    completed = latest_runtime["completed_episodes"] if latest_runtime else 0
    updates = latest_runtime["optimizer_updates"] if latest_runtime else 0
    if metrics["completed_training_episodes"] != completed:
        raise VerificationError("metrics completed episode count mismatch")
    if metrics["optimizer_updates"] != updates:
        raise VerificationError("metrics optimizer update count mismatch")
    wall = _finite_number(metrics["cumulative_wall_seconds"], "metrics wall time")
    checkpoint_wall = latest_runtime["cumulative_wall_seconds"] if latest_runtime else 0.0
    if wall < checkpoint_wall or wall > registration["limits"]["max_wall_seconds"]:
        raise VerificationError("metrics wall time is outside registered bounds")
    if any(
        metrics[name] is not expected
        for name, expected in (
            ("formal_readiness_unchanged", True),
            ("policy_quality_baseline_established", False),
            ("target_supported_outcomes_established", False),
        )
    ):
        raise VerificationError("metrics readiness or quality authority drifted")
    if metrics["isolation_unchanged"] is not isolation["unchanged"]:
        raise VerificationError("metrics isolation flag mismatch")
    victories = sum(row["victory"] for row in training_episode_rows)
    unsupported = sum(
        row["unsupported_reason"] is not None for row in training_episode_rows
    )
    if metrics["training_victories"] != victories:
        raise VerificationError("metrics training victory count mismatch")
    if metrics["training_unsupported_episodes"] != unsupported:
        raise VerificationError("metrics unsupported count mismatch")
    if metrics["training_observed_only_floor_shaping"] is not (
        bool(training_episode_rows) and victories == 0
    ):
        raise VerificationError("metrics floor-only training flag mismatch")
    blocked_reason = metrics["blocked_reason"]
    if blocked_reason is not None and (
        not isinstance(blocked_reason, str) or not blocked_reason
    ):
        raise VerificationError("metrics blocked reason is invalid")
    if not isolation["unchanged"]:
        expected_verdict = "experiment_invalid"
    elif blocked_reason is not None:
        expected_verdict = "experiment_blocked"
    elif evaluation is None:
        expected_verdict = "experiment_invalid"
    else:
        expected_verdict = evaluation["verdict"]
        if completed != registration["limits"]["max_episodes"]:
            expected_verdict = "experiment_invalid"
    if metrics["verdict"] != expected_verdict:
        raise VerificationError("metrics verdict does not recompute")
    if manifest["verdict"] != expected_verdict:
        raise VerificationError("manifest verdict differs from recomputed verdict")
    report, _ = load_canonical_json(output / "report.json")
    expected_report = {
        "formal_readiness": "unchanged_not_ready",
        "logical_execution_id": registration["identity"]["logical_execution_id"],
        "policy_quality_claim": False,
        "schema_version": "noncombat-state-conditioned-terminal-report-v1",
        "target_supported_outcome_claim": False,
        "verdict": expected_verdict,
    }
    if not _json_values_equal(report, expected_report):
        raise VerificationError("terminal report does not reproduce verdict")
    return metrics, report


def _verify_full_terminal(
    output: Path,
    *,
    manifest: Mapping[str, Any],
    payloads: Mapping[str, bytes],
) -> dict[str, Any]:
    expected_common = {
        "authorization.json",
        "configuration.json",
        "diagnostics.json",
        "execution_journal.json",
        "final_model.json",
        "isolation.json",
        "metrics.json",
        "registration.json",
        "report.json",
        "training_rows.json",
    }
    if not expected_common.issubset(payloads):
        raise VerificationError("terminal artifact set is incomplete")
    registration, authorization = _validate_full_controls(output, payloads)
    execution_id = registration["identity"]["logical_execution_id"]
    if manifest["logical_execution_id"] != execution_id:
        raise VerificationError("manifest logical execution identity mismatch")
    registration_bytes = payloads["registration.json"]
    checkpoint_state = _verify_checkpoints(
        output,
        registration=registration,
        registration_sha256=hashlib.sha256(registration_bytes).hexdigest(),
    )
    journal = _verify_journal(
        output,
        registration=registration,
        checkpoint_state=checkpoint_state,
    )
    _, training_episodes, training_diagnostics = _verify_training_rows(
        output, checkpoint_state
    )
    _verify_final_model(output, checkpoint_state=checkpoint_state)
    isolation = _verify_isolation(output, registration=registration)
    evaluation = None
    if "evaluation.json" in payloads:
        evaluation = _verify_evaluation(output, registration=registration)
    journal_evidence = {
        record["name"]: record["payload"]
        for record in journal["records"]
        if record["state"] == "evidence"
    }
    if evaluation is None:
        if journal_evidence:
            raise VerificationError("journal evaluation evidence lacks terminal evaluation")
    else:
        expected_canary = {
            "canary": evaluation["canary"],
            "canary_gate": evaluation["canary_gate"],
            "holdout": {"accessed": False, "episode_count": 0},
            "verdict": (
                "canary_passed_pending_holdout"
                if evaluation["canary_gate"]["passed"]
                else "experiment_stopped_at_canary"
            ),
        }
        if not _json_values_equal(
            journal_evidence.get("canary_evaluation"), expected_canary
        ):
            raise VerificationError("journal canary evidence mismatch")
        if evaluation["holdout"]["accessed"]:
            if not _json_values_equal(
                journal_evidence.get("complete_evaluation"), evaluation
            ):
                raise VerificationError("journal complete evaluation mismatch")
        elif "complete_evaluation" in journal_evidence:
            raise VerificationError("journal contains unaccessed holdout evidence")
    _verify_terminal_diagnostics(
        output,
        training_diagnostic_rows=training_diagnostics,
        evaluation=evaluation,
    )
    metrics, _ = _verify_metrics_and_report(
        output,
        registration=registration,
        checkpoint_state=checkpoint_state,
        training_episode_rows=training_episodes,
        isolation=isolation,
        evaluation=evaluation,
        manifest=manifest,
    )
    checkpoint_paths = {
        f"checkpoints/checkpoint_{index:04d}.json"
        for index in range(1, checkpoint_state["checkpoint_count"] + 1)
    }
    expected_paths = expected_common | checkpoint_paths
    if evaluation is not None:
        expected_paths.add("evaluation.json")
    if set(payloads) != expected_paths:
        raise VerificationError("terminal artifact paths differ from fixed inventory")
    return {
        "artifact_count": int(manifest["artifact_count"]),
        "checkpoint_count": checkpoint_state["checkpoint_count"],
        "completed_training_episodes": metrics["completed_training_episodes"],
        "logical_execution_id": execution_id,
        "output_directory": authorization["output_directory"],
        "valid": True,
        "verdict": metrics["verdict"],
        "verifier": "standard-library-v1",
    }


def _classify_incomplete_consumed_output(output: Path) -> dict[str, Any]:
    """Classify a terminal journal without a manifest as consumed and invalid."""
    required = {
        "authorization.json",
        "configuration.json",
        "execution_journal.json",
        "registration.json",
    }
    if not (output / "checkpoints").is_dir() or any(
        not (output / name).is_file() for name in required
    ):
        raise VerificationError("incomplete output lacks bound controls or checkpoints")
    payloads = {
        name: load_canonical_json(output / name)[1] for name in sorted(required)
    }
    registration, authorization = _validate_full_controls(output, payloads)
    checkpoint_state = _verify_checkpoints(
        output,
        registration=registration,
        registration_sha256=hashlib.sha256(payloads["registration.json"]).hexdigest(),
    )
    journal = _verify_journal(
        output,
        registration=registration,
        checkpoint_state=checkpoint_state,
    )
    terminal = journal["records"][-1]
    return {
        "artifact_count": sum(path.is_file() for path in output.rglob("*")),
        "consumed": True,
        "logical_execution_id": registration["identity"]["logical_execution_id"],
        "output_directory": authorization["output_directory"],
        "terminal_reason": terminal["reason"],
        "valid": False,
        "verdict": "experiment_invalid",
        "verifier": "standard-library-v1",
    }


def _lock_execution_lease(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_execution_lease(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _assert_output_inactive(output: Path) -> None:
    path = output / ".execution.lease"
    try:
        handle = path.open("r+b")
    except FileNotFoundError:
        return
    locked = False
    try:
        try:
            _lock_execution_lease(handle)
            locked = True
        except OSError as exc:
            raise VerificationError("cannot inspect an active execution output") from exc
    finally:
        try:
            if locked:
                _unlock_execution_lease(handle)
        finally:
            handle.close()


def _snapshot_output(output: Path) -> tuple[tuple[str, str, int, str], ...]:
    """Hash the complete output inventory to detect transient execution races."""
    rows = []
    try:
        for path in sorted(
            output.rglob("*"),
            key=lambda candidate: candidate.relative_to(output).as_posix(),
        ):
            relative = path.relative_to(output).as_posix()
            if path.is_dir():
                rows.append(("directory", relative, 0, ""))
            elif path.is_file():
                payload = path.read_bytes()
                rows.append(
                    (
                        "file",
                        relative,
                        len(payload),
                        hashlib.sha256(payload).hexdigest(),
                    )
                )
            else:
                rows.append(("other", relative, 0, ""))
    except OSError as exc:
        raise VerificationError("output changed while taking its snapshot") from exc
    return tuple(rows)


def verify_output(
    output: Path | str, *, allow_generic_bundle: bool = False
) -> dict[str, Any]:
    directory = Path(output)
    if not directory.is_dir():
        raise VerificationError("terminal output directory does not exist")
    _assert_output_inactive(directory)
    initial_snapshot = _snapshot_output(directory)
    if not (directory / "artifact_manifest.json").is_file():
        result = _classify_incomplete_consumed_output(directory)
    else:
        manifest, _ = load_canonical_json(directory / "artifact_manifest.json")
        payloads, _ = _verify_manifest(directory, manifest)
        if manifest["manifest_kind"] == "full_terminal":
            result = _verify_full_terminal(
                directory,
                manifest=manifest,
                payloads=payloads,
            )
        else:
            if allow_generic_bundle is not True:
                raise VerificationError(
                    "full terminal verification required; generic bundle was not allowed"
                )
            result = {
                "artifact_count": int(manifest["artifact_count"]),
                "bundle_valid": True,
                "qualification_eligible": False,
                "valid": False,
                "verification_scope": "generic_bundle_only",
                "verifier": "standard-library-v1",
            }
    _assert_output_inactive(directory)
    if _snapshot_output(directory) != initial_snapshot:
        raise VerificationError("output changed during terminal verification")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-generic-bundle", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = verify_output(
            args.output, allow_generic_bundle=args.allow_generic_bundle
        )
    except VerificationError as exc:
        print(json.dumps({"error": str(exc), "valid": False}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0 if result.get("valid") is not False else 2


if __name__ == "__main__":
    raise SystemExit(main())
