"""Standard-library controls for the cross-fitted hierarchical successor.

Torch and the native simulator are intentionally absent from this module's
import graph.  Source inspection, registration, request rendering, approval
binding, and durable lifecycle bookkeeping all complete before the runtime can
be imported.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib
import io
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from importlib import metadata as importlib_metadata
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


CONTRACT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-contract-v1"
)
SOURCE_INVENTORY_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-source-inventory-v1"
)
REGISTRATION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-registration-v1"
)
EXECUTION_REQUEST_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-execution-request-v1"
)
EXTERNAL_APPROVAL_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-external-approval-v1"
)
AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-authorization-v1"
)
SOURCE_PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-source-preflight-v1"
)
ISOLATION_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-isolation-observation-v1"
)
FAILURE_WITNESS_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-failure-witness-v1"
)
LEASE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-lease-v1"
)
ACCESS_JOURNAL_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-access-journal-v2"
)
RESOURCE_LEDGER_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-resource-ledger-v1"
)
BOOTSTRAP_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-bootstrap-v1"
)
CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-checkpoint-v1"
)
CHUNK_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-chunk-evidence-v2"
)
TERMINAL_INTENT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-terminal-intent-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-terminal-v1"
)
MANIFEST_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-manifest-v1"
)

BASELINE_FEATURE_DIM = 128
FOLD_COUNT = 4
EPISODES_PER_CHUNK = 64
CHUNK_COUNT = 8
SCHEDULED_TRAJECTORIES = EPISODES_PER_CHUNK * CHUNK_COUNT

CONTROL_MODULE_PATH = (
    "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py"
)
RUNTIME_MODULE_PATH = (
    "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_runtime.py"
)
VERIFIER_MODULE_PATH = (
    "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_"
    "experiment.py"
)
RUNTIME_MODULE_NAME = (
    "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime"
)
ADAPTER_MODULE_NAME = "analysis_scripts.noncombat_simulator_adapter"
NATIVE_MODULE_NAME = "sts_lightspeed_noncombat_adapter"
SEED_INVENTORY_MODULE_NAME = (
    "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_seed_inventory"
)

LEASE_FILENAME = ".execution.lease"
ACCESS_JOURNAL_FILENAME = "access_journal.jsonl"
RESOURCE_LEDGER_FILENAME = "resource_ledger.jsonl"
BOOTSTRAP_FILENAME = "bootstrap.json"
TERMINAL_INTENT_FILENAME = "terminal_intent.json"
TERMINAL_FILENAME = "terminal.json"
MANIFEST_FILENAME = "artifact_manifest.json"
REGISTRATION_FILENAME = "registration.json"
EXECUTION_REQUEST_FILENAME = "execution_request.json"
EXTERNAL_APPROVAL_FILENAME = "external_approval.json"
AUTHORIZATION_FILENAME = "authorization.json"
SOURCE_PREFLIGHT_FILENAME = "source_preflight.json"
PRE_ISOLATION_FILENAME = "pre_isolation.json"
POST_ISOLATION_FILENAME = "post_isolation.json"
FAILURE_FILENAME = "failure.json"

_MODULE_SPECS = (
    (
        "control_plane",
        CONTROL_MODULE_PATH,
        "standard-library immutable controls and lifecycle ownership",
    ),
    (
        "torch_runtime",
        RUNTIME_MODULE_PATH,
        "authorized rollout, fitting, gradient, and optimizer runtime",
    ),
    (
        "independent_verifier",
        VERIFIER_MODULE_PATH,
        "standard-library independent terminal verification",
    ),
)

_PUBLIC_DEPENDENCY_SPECS = (
    (
        "analysis_scripts_package",
        "analysis_scripts/__init__.py",
        (),
    ),
    (
        "action_family_distribution",
        "analysis_scripts/noncombat_action_family_distribution.py",
        (
            "ActionFamilyDistribution",
            "build_action_family_distribution",
            "distribution_metadata",
        ),
    ),
    (
        "advantage_attribution",
        "analysis_scripts/noncombat_hierarchical_advantage_attribution.py",
        ("build_advantage_batch", "build_gradient_ledger"),
    ),
    (
        "candidate_feature_projection",
        "analysis_scripts/noncombat_policy_model.py",
        ("FeatureConfig", "candidate_feature_vector"),
    ),
    (
        "formal_reward",
        "analysis_scripts/noncombat_formal_reward_contract.py",
        ("reward_channels", "validate_scalarization"),
    ),
    (
        "hierarchical_objective",
        "analysis_scripts/noncombat_hierarchical_policy_objective.py",
        ("build_hierarchical_policy_terms",),
    ),
    (
        "legacy_objective_diagnostic",
        "analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py",
        ("build_reinforce_loss", "normalize_returns"),
    ),
    (
        "policy_input",
        "analysis_scripts/noncombat_state_conditioned_policy_input.py",
        ("project_state_conditioned_policy_input",),
    ),
    (
        "simulator_adapter",
        "analysis_scripts/noncombat_simulator_adapter.py",
        ("validate_candidates", "validate_snapshot"),
    ),
    (
        "simulator_rl_policy_projection",
        "analysis_scripts/noncombat_simulator_rl_experiment.py",
        ("canonical_json_bytes", "project_policy_view_v2"),
    ),
    (
        "seed_inventory",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_inventory.py",
        (
            "materialize_fresh_schedule",
            "validate_fresh_schedule",
            "validate_seed_inventory",
            "verify_seed_inventory",
        ),
    ),
    (
        "state_conditioned_ranker",
        "analysis_scripts/noncombat_state_conditioned_ranker.py",
        ("StateConditionedCandidateRanker",),
    ),
)

AUTHORITY_NAMES = (
    "communication_mod",
    "environment_construction",
    "evaluation",
    "execution",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "model_loading",
    "native_loading",
    "policy_promotion",
    "qualification",
    "seed_access",
    "training",
)
_EXECUTION_AUTHORITY_NAMES = frozenset(
    {
        "environment_construction",
        "execution",
        "model_fitting",
        "native_loading",
        "seed_access",
        "training",
    }
)

_RESOURCE_FIELDS = (
    "charged_seconds",
    "environment_accesses",
    "optimizer_updates",
    "retained_decisions",
    "stored_bytes",
    "uncompressed_bytes",
)
_INTEGER_RESOURCE_FIELDS = frozenset(set(_RESOURCE_FIELDS) - {"charged_seconds"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_IDENTITY_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
_OWNER_TOKEN_RE = re.compile(r"[0-9a-f]{32}")
_ACTIVE_EXECUTION_LEASES: set[str] = set()
_TERMINAL_VERDICTS = (
    "experiment_blocked_before_seed_access",
    "experiment_completed_with_cross_fitted_mechanism_evidence",
    "experiment_failed_after_seed_access",
    "experiment_stopped_during_training_for_family_saturation",
)


class ExperimentBlocked(ValueError):
    """Raised when a source-only experiment boundary cannot be trusted."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return deterministic ASCII JSON with one trailing newline."""
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ExperimentBlocked("value is not canonical JSON") from exc
    return rendered.encode("ascii") + b"\n"


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _copy_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ExperimentBlocked(f"{label} must be a mapping")
    return copy.deepcopy(dict(value))


def _require_fields(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise ExperimentBlocked(f"{label} fields mismatch")


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExperimentBlocked(f"{label} must be a nonempty string")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExperimentBlocked(f"{label} must be a nonnegative integer")
    return value


def _positive_integer(value: object, label: str) -> int:
    normalized = _nonnegative_integer(value, label)
    if normalized == 0:
        raise ExperimentBlocked(f"{label} must be positive")
    return normalized


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ExperimentBlocked(f"{label} must be a SHA-256 digest")
    return value


def _commit(value: object, label: str) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise ExperimentBlocked(f"{label} must be a full Git commit")
    return value


def _logical_identity(value: object, label: str) -> str:
    if not isinstance(value, str) or _IDENTITY_RE.fullmatch(value) is None:
        raise ExperimentBlocked(f"{label} is invalid")
    return value


def _relative_source_path(value: object, label: str) -> str:
    path = _nonempty_string(value, label)
    if "\\" in path:
        raise ExperimentBlocked(f"{label} must use forward slashes")
    pure = PurePosixPath(path)
    if pure.is_absolute() or path != pure.as_posix() or ".." in pure.parts:
        raise ExperimentBlocked(f"{label} must be a canonical relative path")
    return path


def _absolute_external_path(value: object, label: str) -> str:
    path = _nonempty_string(value, label)
    if "\\" in path or path.endswith("/"):
        raise ExperimentBlocked(f"{label} must be a canonical absolute path")
    windows_absolute = re.fullmatch(r"[A-Za-z]:/[^\x00]+", path) is not None
    posix_absolute = path.startswith("/")
    pure = PurePosixPath(path[3:] if windows_absolute else path)
    if (
        not (windows_absolute or posix_absolute)
        or "." in pure.parts
        or ".." in pure.parts
    ):
        raise ExperimentBlocked(f"{label} must be a canonical absolute path")
    return path


def registration_authority() -> dict[str, bool]:
    """Return the immutable all-false registration authority."""
    return {name: False for name in AUTHORITY_NAMES}


def execution_authority() -> dict[str, bool]:
    """Return only the operations an exact authorization may enable."""
    return {name: name in _EXECUTION_AUTHORITY_NAMES for name in AUTHORITY_NAMES}


def registered_output_inventory() -> dict[str, Any]:
    """Return the additive lifecycle artifact names frozen by registration."""
    return {
        "access_journal": ACCESS_JOURNAL_FILENAME,
        "artifact_manifest": MANIFEST_FILENAME,
        "authorization": AUTHORIZATION_FILENAME,
        "bootstrap": BOOTSTRAP_FILENAME,
        "chunk_evidence_pattern": (
            "checkpoints/chunk_{index:04d}_evidence.json.gz"
        ),
        "checkpoint_pattern": "checkpoints/checkpoint_{index:04d}.json",
        "execution_lease": LEASE_FILENAME,
        "execution_request": EXECUTION_REQUEST_FILENAME,
        "external_approval": EXTERNAL_APPROVAL_FILENAME,
        "failure": FAILURE_FILENAME,
        "post_isolation": POST_ISOLATION_FILENAME,
        "pre_isolation": PRE_ISOLATION_FILENAME,
        "registration": REGISTRATION_FILENAME,
        "resource_ledger": RESOURCE_LEDGER_FILENAME,
        "source_preflight": SOURCE_PREFLIGHT_FILENAME,
        "terminal": TERMINAL_FILENAME,
        "terminal_intent": TERMINAL_INTENT_FILENAME,
    }


def module_dependency_inventory() -> dict[str, Any]:
    """Return the declared additive modules and bound public dependencies."""
    return {
        "modules": [
            {"name": name, "path": path, "role": role}
            for name, path, role in _MODULE_SPECS
        ],
        "public_dependencies": [
            {
                "name": name,
                "path": path,
                "public_symbols": list(public_symbols),
            }
            for name, path, public_symbols in _PUBLIC_DEPENDENCY_SPECS
        ],
    }


def _algorithm_controls() -> dict[str, Any]:
    return {
        "architecture": "state-conditioned-candidate-ranker-mlp-v1",
        "conditional_entropy_coefficient": 0.01,
        "discount": 1.0,
        "family_entropy_coefficient": 0.01,
        "gradient_norm_ceiling": 1.0,
        "learning_rate": 0.001,
        "model_seed": 0,
        "optimizer": "adam",
        "optimizer_amsgrad": False,
        "optimizer_betas": [0.9, 0.999],
        "optimizer_eps": 1e-8,
        "optimizer_weight_decay": 0.0,
        "sampling": "family-first-then-conditional-v1",
    }


def _baseline_controls() -> dict[str, Any]:
    return {
        "feature_dim": BASELINE_FEATURE_DIM,
        "fit_trajectories_per_fold": 48,
        "fold_count": FOLD_COUNT,
        "held_out_trajectories_per_fold": 16,
        "prediction_bounds": [0.0, 3.0],
        "ridge_coefficient": 0.001,
        "ridge_residual_atol": 1e-9,
        "ridge_residual_rtol": 1e-9,
        "scale": 1.0,
        "solver": "cpu-float64-cholesky-v1",
        "trajectory_weighting": "equal-trajectory-mean-squared-error-v1",
    }


def expected_runtime_metadata() -> dict[str, Any]:
    """Return the complete metadata expected from the bound Torch runtime."""
    return {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "algorithm": _algorithm_controls(),
        "authority": registration_authority(),
        "baseline": _baseline_controls(),
        "baseline_feature_dim": BASELINE_FEATURE_DIM,
        "baseline_feature_schema_version": (
            "cross-fitted-baseline-state-features-v1"
        ),
        "device": "cpu",
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "fold_count": FOLD_COUNT,
        "rng": {"action_generator_seed": 0, "python_rng_seed": 0},
        "ridge_coefficient": 0.001,
        "schema_version": (
            "noncombat-cross-fitted-hierarchical-learning-runtime-v1"
        ),
    }


def experiment_contract() -> dict[str, Any]:
    """Return immutable successor terms without importing runtime code."""
    return {
        "algorithm": _algorithm_controls(),
        "authority": registration_authority(),
        "baseline": _baseline_controls(),
        "cohort": {
            "chunk_count": CHUNK_COUNT,
            "episodes_per_chunk": EPISODES_PER_CHUNK,
            "evaluation_cohorts": [],
            "scheduled_trajectories": SCHEDULED_TRAJECTORIES,
            "selection": "tracked-fixed-tree-ascending-v1",
        },
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "evaluation": {"authorized": False},
        "limits": {
            "max_artifact_bytes": 64 * 1024 * 1024,
            "max_charged_seconds": 14_400.0,
            "max_decisions_per_episode": 500,
            "max_environment_accesses": 576,
            "max_optimizer_updates": 8,
            "max_retained_decisions": 32_768,
            "max_stored_bytes": 192 * 1024 * 1024,
            "max_uncompressed_bytes": 256 * 1024 * 1024,
        },
        "lifecycle": {
            "maximum_post_start_resumes": 1,
            "resume_scope": "same-identity-chunk-or-checkpoint-boundary-v2",
            "seed_journal": "append-only-write-ahead-per-access-v1",
        },
        "runtime_metadata": expected_runtime_metadata(),
        "schema_version": CONTRACT_SCHEMA_VERSION,
    }


def _source_binding(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def external_file_binding(path: Path | str) -> dict[str, Any]:
    """Hash one external file as inert bytes without importing it."""
    candidate = Path(path).resolve()
    if not candidate.is_file():
        raise ExperimentBlocked(f"external file is missing: {candidate}")
    try:
        payload = candidate.read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"external file cannot be read: {candidate}") from exc
    if not payload:
        raise ExperimentBlocked(f"external file is empty: {candidate}")
    return {
        "path": candidate.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _hash_named_bytes(rows: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in rows:
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def snapshot_production_checkpoints(root: Path | str) -> dict[str, Any]:
    """Hash the complete production-checkpoint tree without loading artifacts."""
    directory = Path(root).resolve()
    if not directory.is_dir():
        raise ExperimentBlocked(
            f"production checkpoint root is missing: {directory}"
        )
    try:
        files = sorted(
            (candidate for candidate in directory.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(directory).as_posix(),
        )
        rows = [
            (candidate.relative_to(directory).as_posix(), candidate.read_bytes())
            for candidate in files
        ]
    except OSError as exc:
        raise ExperimentBlocked(
            f"production checkpoint tree cannot be read: {directory}"
        ) from exc
    return {
        "file_count": len(rows),
        "root": directory.as_posix(),
        "sha256": _hash_named_bytes(rows),
        "size_bytes": sum(len(payload) for _, payload in rows),
    }


def build_source_inventory(repo_root: Path | str) -> dict[str, Any]:
    """Hash the declared modules and public dependencies without importing them."""
    root = Path(repo_root).resolve()
    definition = module_dependency_inventory()
    modules: list[dict[str, Any]] = []
    dependencies: list[dict[str, Any]] = []
    try:
        for row in definition["modules"]:
            binding = _source_binding(
                row["path"], (root / PurePosixPath(row["path"])).read_bytes()
            )
            modules.append({**row, **binding})
        for row in definition["public_dependencies"]:
            binding = _source_binding(
                row["path"], (root / PurePosixPath(row["path"])).read_bytes()
            )
            dependencies.append({**row, **binding})
    except OSError as exc:
        raise ExperimentBlocked(f"source inventory cannot be observed: {exc}") from exc
    body = {
        "modules": modules,
        "public_dependencies": dependencies,
        "schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
    }
    return {**body, "inventory_sha256": _canonical_digest(body)}


def _validate_source_rows(
    rows: object,
    definitions: Sequence[Mapping[str, Any]],
    *,
    dependency: bool,
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or len(rows) != len(definitions):
        raise ExperimentBlocked("source inventory rows mismatch")
    normalized: list[dict[str, Any]] = []
    for row, expected in zip(rows, definitions, strict=True):
        value = _copy_mapping(row, "source inventory row")
        fields = {"name", "path", "sha256", "size_bytes"}
        fields.add("public_symbols" if dependency else "role")
        _require_fields(value, fields, "source inventory row")
        if value["name"] != expected["name"] or value["path"] != expected["path"]:
            raise ExperimentBlocked("source inventory declaration mismatch")
        _relative_source_path(value["path"], "source inventory path")
        if dependency:
            if value["public_symbols"] != expected["public_symbols"]:
                raise ExperimentBlocked("public dependency symbols mismatch")
        elif value["role"] != expected["role"]:
            raise ExperimentBlocked("module role mismatch")
        _digest(value["sha256"], "source inventory digest")
        _nonnegative_integer(value["size_bytes"], "source inventory byte size")
        normalized.append(value)
    return normalized


def validate_source_inventory(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate declaration, binding shape, and the inventory's own digest."""
    inventory = _copy_mapping(value, "source inventory")
    _require_fields(
        inventory,
        {
            "inventory_sha256",
            "modules",
            "public_dependencies",
            "schema_version",
        },
        "source inventory",
    )
    if inventory["schema_version"] != SOURCE_INVENTORY_SCHEMA_VERSION:
        raise ExperimentBlocked("source inventory schema mismatch")
    definition = module_dependency_inventory()
    inventory["modules"] = _validate_source_rows(
        inventory["modules"], definition["modules"], dependency=False
    )
    inventory["public_dependencies"] = _validate_source_rows(
        inventory["public_dependencies"],
        definition["public_dependencies"],
        dependency=True,
    )
    digest = _digest(inventory["inventory_sha256"], "source inventory identity")
    body = {key: item for key, item in inventory.items() if key != "inventory_sha256"}
    if digest != _canonical_digest(body):
        raise ExperimentBlocked("source inventory identity mismatch")
    return inventory


def verify_source_inventory(
    value: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Any]:
    """Reobserve every declared source byte and fail closed on drift."""
    inventory = validate_source_inventory(value)
    if inventory != build_source_inventory(repo_root):
        raise ExperimentBlocked("source inventory bytes mismatch")
    return inventory


def _validate_file_binding(value: object, label: str) -> dict[str, Any]:
    binding = _copy_mapping(value, label)
    _require_fields(binding, {"path", "sha256", "size_bytes"}, label)
    binding["path"] = _absolute_external_path(binding["path"], f"{label} path")
    _digest(binding["sha256"], f"{label} digest")
    _nonnegative_integer(binding["size_bytes"], f"{label} byte size")
    return binding


def current_runtime_identity(
    *, package_version: Callable[[str], str] | None = None
) -> dict[str, str]:
    """Observe Python and installed Torch package metadata without importing Torch."""
    version_observer = package_version or importlib_metadata.version
    try:
        torch_version = version_observer("torch")
    except Exception as exc:
        raise ExperimentBlocked("Torch package version cannot be observed") from exc
    return {
        "device": "cpu",
        "python_executable": Path(sys.executable).resolve().as_posix(),
        "python_version": platform.python_version(),
        "torch_version": _nonempty_string(torch_version, "Torch package version"),
    }


def _validate_runtime_identity(value: object) -> dict[str, Any]:
    identity = _copy_mapping(value, "runtime identity")
    _require_fields(
        identity,
        {"device", "python_executable", "python_version", "torch_version"},
        "runtime identity",
    )
    if identity["device"] != "cpu":
        raise ExperimentBlocked("runtime device must be cpu")
    identity["python_executable"] = _absolute_external_path(
        identity["python_executable"], "Python executable"
    )
    _nonempty_string(identity["python_version"], "Python version")
    _nonempty_string(identity["torch_version"], "Torch version")
    return identity


def _validate_native_identity(value: object) -> dict[str, Any]:
    identity = _copy_mapping(value, "native identity")
    _require_fields(
        identity,
        {
            "adapter_api_version",
            "dll_directories",
            "module",
            "provenance",
            "provenance_sha256",
        },
        "native identity",
    )
    if identity["adapter_api_version"] != "sts-lightspeed-noncombat-adapter-v3":
        raise ExperimentBlocked("native adapter API mismatch")
    directories = identity["dll_directories"]
    if not isinstance(directories, list):
        raise ExperimentBlocked("native DLL directories must be a list")
    normalized_directories = [
        _absolute_external_path(item, "native DLL directory") for item in directories
    ]
    if normalized_directories != sorted(set(normalized_directories)):
        raise ExperimentBlocked("native DLL directories must be unique and sorted")
    identity["dll_directories"] = normalized_directories
    identity["module"] = _validate_file_binding(identity["module"], "native module")
    provenance = _copy_mapping(identity["provenance"], "native provenance")
    if not provenance:
        raise ExperimentBlocked("native provenance must not be empty")
    build = _copy_mapping(provenance.get("build"), "native provenance build")
    if build.get("adapter_api_version") != identity["adapter_api_version"]:
        raise ExperimentBlocked("native provenance adapter API mismatch")
    if provenance.get("module_sha256") != identity["module"]["sha256"]:
        raise ExperimentBlocked("native provenance module digest mismatch")
    identity["provenance"] = provenance
    identity["provenance_sha256"] = _digest(
        identity["provenance_sha256"], "native provenance digest"
    )
    if identity["provenance_sha256"] != _canonical_digest(provenance):
        raise ExperimentBlocked("native provenance digest mismatch")
    return identity


def _validate_checkpoint_tree_identity(value: object) -> dict[str, Any]:
    identity = _copy_mapping(value, "production checkpoint identity")
    _require_fields(
        identity,
        {"file_count", "root", "sha256", "size_bytes"},
        "production checkpoint identity",
    )
    identity["root"] = _absolute_external_path(
        identity["root"], "production checkpoint root"
    )
    identity["file_count"] = _nonnegative_integer(
        identity["file_count"], "production checkpoint file count"
    )
    identity["sha256"] = _digest(
        identity["sha256"], "production checkpoint digest"
    )
    identity["size_bytes"] = _nonnegative_integer(
        identity["size_bytes"], "production checkpoint byte size"
    )
    return identity


def _validate_isolation_identity(value: object) -> dict[str, Any]:
    identity = _copy_mapping(value, "isolation identity")
    _require_fields(
        identity,
        {"communication_mod_config", "production_checkpoints"},
        "isolation identity",
    )
    identity["communication_mod_config"] = _validate_file_binding(
        identity["communication_mod_config"], "CommunicationMod configuration"
    )
    identity["production_checkpoints"] = _validate_checkpoint_tree_identity(
        identity["production_checkpoints"]
    )
    return identity


def _validated_seed_inventory(value: object) -> tuple[Any, dict[str, Any]]:
    try:
        module = importlib.import_module(SEED_INVENTORY_MODULE_NAME)
        inventory = module.validate_seed_inventory(value)
    except Exception as exc:
        if isinstance(exc, ExperimentBlocked):
            raise
        raise ExperimentBlocked("seed inventory is invalid") from exc
    return module, inventory


def _validate_schedule(
    value: object, *, seed_inventory: Mapping[str, Any]
) -> dict[str, Any]:
    schedule = _copy_mapping(value, "schedule")
    _require_fields(
        schedule,
        {
            "canonical_search_start",
            "chunk_count",
            "chunks",
            "episodes_per_chunk",
            "inventory_sha256",
            "seeds",
            "seeds_sha256",
            "selection_schema_version",
        },
        "schedule",
    )
    module, inventory = _validated_seed_inventory(seed_inventory)
    try:
        fresh = module.validate_fresh_schedule(
            inventory,
            {
                "canonical_search_start": schedule["canonical_search_start"],
                "inventory_sha256": schedule["inventory_sha256"],
                "schema_version": schedule["selection_schema_version"],
                "seed_count": len(schedule["seeds"])
                if isinstance(schedule["seeds"], list)
                else -1,
                "seeds": copy.deepcopy(schedule["seeds"]),
            },
        )
    except Exception as exc:
        raise ExperimentBlocked("schedule differs from the fixed seed inventory") from exc
    seeds = schedule["seeds"]
    if not isinstance(seeds, list):
        raise ExperimentBlocked("scheduled seeds must be a list")
    normalized_seeds = [
        _nonnegative_integer(seed, "scheduled seed") for seed in seeds
    ]
    if (
        len(normalized_seeds) != SCHEDULED_TRAJECTORIES
        or normalized_seeds != sorted(set(normalized_seeds))
    ):
        raise ExperimentBlocked("scheduled seeds must be 512 unique ascending integers")
    chunks = [
        normalized_seeds[index : index + EPISODES_PER_CHUNK]
        for index in range(0, len(normalized_seeds), EPISODES_PER_CHUNK)
    ]
    expected = {
        "canonical_search_start": fresh["canonical_search_start"],
        "chunk_count": CHUNK_COUNT,
        "chunks": chunks,
        "episodes_per_chunk": EPISODES_PER_CHUNK,
        "inventory_sha256": fresh["inventory_sha256"],
        "seeds": normalized_seeds,
        "seeds_sha256": _canonical_digest(normalized_seeds),
        "selection_schema_version": fresh["schema_version"],
    }
    if schedule != expected:
        raise ExperimentBlocked("schedule differs from canonical chunks or identity")
    return schedule


def build_source_only_registration(
    *,
    registration_id: str,
    repository_commit: str,
    source_inventory: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
    native_identity: Mapping[str, Any],
    isolation_identity: Mapping[str, Any],
    seed_inventory: Mapping[str, Any],
    output_root: str,
) -> dict[str, Any]:
    """Build one immutable registration that grants no execution authority."""
    identity = _logical_identity(registration_id, "registration identity")
    commit = _commit(repository_commit, "registration repository commit")
    normalized_source_inventory = validate_source_inventory(source_inventory)
    runtime = _validate_runtime_identity(runtime_identity)
    native = _validate_native_identity(native_identity)
    isolation = _validate_isolation_identity(isolation_identity)
    seed_module, normalized_seed_inventory = _validated_seed_inventory(seed_inventory)
    if normalized_seed_inventory["repository_commit"] != commit:
        raise ExperimentBlocked("seed inventory commit differs from registration")
    try:
        fresh = seed_module.materialize_fresh_schedule(normalized_seed_inventory)
    except Exception as exc:
        raise ExperimentBlocked("fresh schedule cannot be materialized") from exc
    seeds = list(fresh["seeds"])
    chunks = [
        seeds[index : index + EPISODES_PER_CHUNK]
        for index in range(0, len(seeds), EPISODES_PER_CHUNK)
    ]
    schedule = _validate_schedule(
        {
            "canonical_search_start": fresh["canonical_search_start"],
            "chunk_count": CHUNK_COUNT,
            "chunks": chunks,
            "episodes_per_chunk": EPISODES_PER_CHUNK,
            "inventory_sha256": fresh["inventory_sha256"],
            "seeds": seeds,
            "seeds_sha256": _canonical_digest(seeds),
            "selection_schema_version": fresh["schema_version"],
        },
        seed_inventory=normalized_seed_inventory,
    )
    registration = {
        "authority": registration_authority(),
        "contract": experiment_contract(),
        "isolation_identity": isolation,
        "native_identity": native,
        "output_inventory": registered_output_inventory(),
        "output_root": _absolute_external_path(output_root, "output root"),
        "pushed_remote_ref": "origin/master",
        "registration_id": identity,
        "repository_commit": commit,
        "runtime_identity": runtime,
        "schedule": schedule,
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "seed_inventory": normalized_seed_inventory,
        "source_inventory": normalized_source_inventory,
    }
    return validate_registration(registration)


def validate_registration(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the complete all-false source registration."""
    registration = _copy_mapping(value, "registration")
    _require_fields(
        registration,
        {
            "authority",
            "contract",
            "isolation_identity",
            "native_identity",
            "output_inventory",
            "output_root",
            "pushed_remote_ref",
            "registration_id",
            "repository_commit",
            "runtime_identity",
            "schedule",
            "schema_version",
            "seed_inventory",
            "source_inventory",
        },
        "registration",
    )
    if registration["schema_version"] != REGISTRATION_SCHEMA_VERSION:
        raise ExperimentBlocked("registration schema mismatch")
    if registration["authority"] != registration_authority():
        raise ExperimentBlocked("registration authority must remain all false")
    if registration["contract"] != experiment_contract():
        raise ExperimentBlocked("registration contract mismatch")
    if registration["pushed_remote_ref"] != "origin/master":
        raise ExperimentBlocked("registration pushed remote must be origin/master")
    if registration["output_inventory"] != registered_output_inventory():
        raise ExperimentBlocked("registration output inventory mismatch")
    registration["registration_id"] = _logical_identity(
        registration["registration_id"], "registration identity"
    )
    registration["repository_commit"] = _commit(
        registration["repository_commit"], "registration repository commit"
    )
    registration["output_root"] = _absolute_external_path(
        registration["output_root"], "output root"
    )
    registration["source_inventory"] = validate_source_inventory(
        registration["source_inventory"]
    )
    _seed_module, normalized_seed_inventory = _validated_seed_inventory(
        registration["seed_inventory"]
    )
    if normalized_seed_inventory["repository_commit"] != registration[
        "repository_commit"
    ]:
        raise ExperimentBlocked("seed inventory commit differs from registration")
    registration["seed_inventory"] = normalized_seed_inventory
    registration["runtime_identity"] = _validate_runtime_identity(
        registration["runtime_identity"]
    )
    registration["native_identity"] = _validate_native_identity(
        registration["native_identity"]
    )
    registration["isolation_identity"] = _validate_isolation_identity(
        registration["isolation_identity"]
    )
    registration["schedule"] = _validate_schedule(
        registration["schedule"],
        seed_inventory=registration["seed_inventory"],
    )
    return registration


def registration_sha256(value: Mapping[str, Any]) -> str:
    return _canonical_digest(validate_registration(value))


def _execution_request_body(registration: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_registration(registration)
    contract = normalized["contract"]
    return {
        "authority": registration_authority(),
        "native_identity": copy.deepcopy(normalized["native_identity"]),
        "operations": {
            "baseline_fitting": "four-fold-cross-fitted-ridge-v1",
            "environment_construction": True,
            "native_loading": True,
            "optimizer_updates_maximum": contract["limits"][
                "max_optimizer_updates"
            ],
            "policy_training": True,
        },
        "output_root": normalized["output_root"],
        "registration_id": normalized["registration_id"],
        "registration_sha256": registration_sha256(normalized),
        "repository_commit": normalized["repository_commit"],
        "request_id": normalized["registration_id"] + ":execution-request-v1",
        "requested_execution_authority": execution_authority(),
        "resources": copy.deepcopy(contract["limits"]),
        "resume": copy.deepcopy(contract["lifecycle"]),
        "runtime_identity": copy.deepcopy(normalized["runtime_identity"]),
        "schedule": copy.deepcopy(normalized["schedule"]),
        "schema_version": EXECUTION_REQUEST_SCHEMA_VERSION,
        "source_inventory_sha256": normalized["source_inventory"][
            "inventory_sha256"
        ],
    }


def build_exact_execution_request(
    registration: Mapping[str, Any]
) -> dict[str, Any]:
    """Render the exact request in memory; this function never publishes it."""
    body = _execution_request_body(registration)
    return {**body, "request_sha256": _canonical_digest(body)}


def validate_exact_execution_request(
    value: Mapping[str, Any], registration: Mapping[str, Any]
) -> dict[str, Any]:
    """Require byte-equivalent request terms derived from one registration."""
    request = _copy_mapping(value, "execution request")
    expected = build_exact_execution_request(registration)
    if request != expected:
        raise ExperimentBlocked("execution request differs from exact registration")
    return request


def _validate_approval_provenance(value: object) -> dict[str, str]:
    provenance = _copy_mapping(value, "approval provenance")
    _require_fields(
        provenance,
        {"message_id", "source", "task_id"},
        "approval provenance",
    )
    if provenance["source"] != "external-human-message":
        raise ExperimentBlocked("approval must come from an external human message")
    for name in ("message_id", "task_id"):
        _nonempty_string(provenance[name], f"approval provenance {name}")
    return provenance


def bind_external_approval(
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    approved_request_sha256: str,
    approval_text: str,
    approved_at: str,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a separately supplied human message to exactly one request digest."""
    normalized_request = validate_exact_execution_request(request, registration)
    digest = _digest(approved_request_sha256, "approved request digest")
    if digest != normalized_request["request_sha256"]:
        raise ExperimentBlocked("external approval request digest mismatch")
    text = _nonempty_string(approval_text, "verbatim approval text")
    if digest not in text:
        raise ExperimentBlocked("external approval text does not name the request digest")
    timestamp = _nonempty_string(approved_at, "approval timestamp")
    normalized_provenance = _validate_approval_provenance(provenance)
    body = {
        "approved_at": timestamp,
        "approved_request_sha256": digest,
        "provenance": normalized_provenance,
        "schema_version": EXTERNAL_APPROVAL_SCHEMA_VERSION,
        "verbatim_approval_text": text,
    }
    return {**body, "approval_sha256": _canonical_digest(body)}


def validate_external_approval(
    value: Mapping[str, Any],
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
) -> dict[str, Any]:
    approval = _copy_mapping(value, "external approval")
    _require_fields(
        approval,
        {
            "approval_sha256",
            "approved_at",
            "approved_request_sha256",
            "provenance",
            "schema_version",
            "verbatim_approval_text",
        },
        "external approval",
    )
    if approval["schema_version"] != EXTERNAL_APPROVAL_SCHEMA_VERSION:
        raise ExperimentBlocked("external approval schema mismatch")
    expected = bind_external_approval(
        registration,
        request,
        approved_request_sha256=approval["approved_request_sha256"],
        approval_text=approval["verbatim_approval_text"],
        approved_at=approval["approved_at"],
        provenance=approval["provenance"],
    )
    if approval != expected:
        raise ExperimentBlocked("external approval binding mismatch")
    return approval


def _authorization_body(
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_registration = validate_registration(registration)
    normalized_request = validate_exact_execution_request(
        request, normalized_registration
    )
    normalized_approval = validate_external_approval(
        approval, normalized_registration, normalized_request
    )
    return {
        "approval": normalized_approval,
        "authorization_id": (
            normalized_registration["registration_id"] + ":authorization-v1"
        ),
        "authority": execution_authority(),
        "registration_id": normalized_registration["registration_id"],
        "registration_sha256": normalized_request["registration_sha256"],
        "request_id": normalized_request["request_id"],
        "request_sha256": normalized_request["request_sha256"],
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
    }


def build_execution_authorization(
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the narrow authorization only after exact external approval."""
    body = _authorization_body(registration, request, approval)
    return {**body, "authorization_sha256": _canonical_digest(body)}


def validate_execution_authorization(
    value: Mapping[str, Any],
    registration: Mapping[str, Any],
    request: Mapping[str, Any] | None = None,
    approval: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail closed unless registration, request, approval, and authority all match."""
    if request is None:
        raise ExperimentBlocked("exact execution request is required")
    if approval is None:
        raise ExperimentBlocked("external approval is required")
    authorization = _copy_mapping(value, "execution authorization")
    expected = build_execution_authorization(registration, request, approval)
    if authorization != expected:
        raise ExperimentBlocked("execution authorization binding mismatch")
    return authorization


def execution_identity(
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, str]:
    normalized = validate_execution_authorization(
        authorization, registration, request, approval
    )
    return {
        "authorization_sha256": normalized["authorization_sha256"],
        "logical_execution_id": validate_registration(registration)[
            "registration_id"
        ],
        "registration_sha256": normalized["registration_sha256"],
        "request_sha256": normalized["request_sha256"],
    }


def _git_text(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ExperimentBlocked(f"Git preflight failed for {' '.join(args)}") from exc
    return completed.stdout.strip()


def _call_git_observer(
    observer: Callable[..., str], root: Path, *args: str
) -> str:
    value = observer(root, *args)
    if not isinstance(value, str):
        raise ExperimentBlocked("Git preflight observer returned invalid output")
    return value.strip()


def source_only_preflight(
    repo_root: Path | str,
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
    *,
    git_text: Callable[..., str] | None = None,
    source_inventory_observer: Callable[[Path], Mapping[str, Any]] | None = None,
    runtime_identity_observer: Callable[[], Mapping[str, Any]] | None = None,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None = None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
) -> dict[str, Any]:
    """Reobserve pushed source and inert identities before dependency loading."""
    normalized = validate_registration(registration)
    validate_execution_authorization(
        authorization, normalized, request, approval
    )
    root = Path(repo_root).resolve()
    git_observer = git_text or _git_text
    commit = normalized["repository_commit"]
    if _call_git_observer(git_observer, root, "rev-parse", "HEAD") != commit:
        raise ExperimentBlocked("source preflight HEAD differs from registration")
    remote_ref = normalized["pushed_remote_ref"]
    if _call_git_observer(git_observer, root, "rev-parse", remote_ref) != commit:
        raise ExperimentBlocked(
            "source preflight origin/master differs from registration"
        )
    if _call_git_observer(
        git_observer,
        root,
        "status",
        "--porcelain",
        "--untracked-files=no",
    ):
        raise ExperimentBlocked("source preflight tracked worktree is not clean")

    source_observer = source_inventory_observer or build_source_inventory
    try:
        observed_source = validate_source_inventory(source_observer(root))
    except (OSError, TypeError, ValueError) as exc:
        if isinstance(exc, ExperimentBlocked):
            raise
        raise ExperimentBlocked("source preflight inventory cannot be observed") from exc
    if observed_source != normalized["source_inventory"]:
        raise ExperimentBlocked("source preflight source inventory bytes mismatch")

    runtime_observer = runtime_identity_observer or current_runtime_identity
    observed_runtime = _validate_runtime_identity(runtime_observer())
    if observed_runtime != normalized["runtime_identity"]:
        raise ExperimentBlocked("source preflight runtime identity mismatch")

    binding_observer = external_binding_observer or external_file_binding
    native = normalized["native_identity"]
    observed_native = _validate_file_binding(
        binding_observer(native["module"]["path"]), "observed native module"
    )
    if observed_native != native["module"]:
        raise ExperimentBlocked("source preflight native module bytes mismatch")

    isolation = normalized["isolation_identity"]
    observed_config = _validate_file_binding(
        binding_observer(isolation["communication_mod_config"]["path"]),
        "observed CommunicationMod configuration",
    )
    if observed_config != isolation["communication_mod_config"]:
        raise ExperimentBlocked("source preflight CommunicationMod bytes mismatch")
    checkpoint_observer = (
        checkpoint_snapshot_observer or snapshot_production_checkpoints
    )
    observed_checkpoints = _validate_checkpoint_tree_identity(
        checkpoint_observer(isolation["production_checkpoints"]["root"])
    )
    if observed_checkpoints != isolation["production_checkpoints"]:
        raise ExperimentBlocked(
            "source preflight production checkpoint isolation mismatch"
        )

    return {
        "checks": {
            "communication_mod_unchanged": True,
            "native_module_unchanged": True,
            "production_checkpoints_unchanged": True,
            "pushed_source_exact": True,
            "runtime_identity_exact": True,
            "source_inventory_exact": True,
            "tracked_worktree_clean": True,
        },
        "registration_sha256": registration_sha256(normalized),
        "repository_commit": commit,
        "schema_version": SOURCE_PREFLIGHT_SCHEMA_VERSION,
    }


def _source_inventory_path(
    registration: Mapping[str, Any], source_name: str
) -> str:
    inventory = registration["source_inventory"]
    for section in (inventory["modules"], inventory["public_dependencies"]):
        for row in section:
            if row["name"] == source_name:
                return row["path"]
    raise ExperimentBlocked(f"registered source is missing: {source_name}")


def _verify_import_path(
    module: Any, *, root: Path, relative_path: str, label: str
) -> None:
    expected = (root / PurePosixPath(relative_path)).resolve()
    observed = Path(getattr(module, "__file__", "")).resolve()
    if observed != expected:
        raise ExperimentBlocked(f"{label} resolved outside the registered source")


def _module_preloaded(registry: Mapping[str, Any], name: str) -> bool:
    return any(key == name or key.startswith(name + ".") for key in registry)


def _load_registered_dependencies(
    registration: Mapping[str, Any],
    *,
    repo_root: Path,
    module_importer: Callable[[str], Any] | None,
    module_registry: Mapping[str, Any] | None,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None,
) -> dict[str, Any]:
    normalized = validate_registration(registration)
    registry = module_registry if module_registry is not None else sys.modules
    if _module_preloaded(registry, "torch"):
        raise ExperimentBlocked("pre-imported Torch is forbidden")
    if _module_preloaded(registry, NATIVE_MODULE_NAME):
        raise ExperimentBlocked("pre-imported native module is forbidden")

    root_text = str(repo_root)
    if not any(Path(entry or os.curdir).resolve() == repo_root for entry in sys.path):
        sys.path.insert(0, root_text)
    importer = module_importer or importlib.import_module
    adapter = importer(ADAPTER_MODULE_NAME)
    _verify_import_path(
        adapter,
        root=repo_root,
        relative_path=_source_inventory_path(normalized, "simulator_adapter"),
        label="simulator adapter",
    )
    if _module_preloaded(registry, "torch"):
        raise ExperimentBlocked("simulator adapter imported Torch before native loading")
    if _module_preloaded(registry, NATIVE_MODULE_NAME):
        raise ExperimentBlocked("simulator adapter pre-imported the native module")

    native = normalized["native_identity"]
    try:
        native_module = adapter.load_native_module(
            native["module"]["path"],
            dll_directories=[Path(path) for path in native["dll_directories"]],
        )
    except Exception as exc:
        raise ExperimentBlocked("registered native module could not be loaded") from exc
    if _module_preloaded(registry, "torch"):
        raise ExperimentBlocked("native loading imported Torch out of order")
    binding_observer = external_binding_observer or external_file_binding
    observed_native = _validate_file_binding(
        binding_observer(native["module"]["path"]), "loaded native module"
    )
    if observed_native != native["module"]:
        raise ExperimentBlocked("loaded native module bytes differ from registration")

    try:
        if native_module.adapter_api_version() != native["adapter_api_version"]:
            raise ExperimentBlocked("loaded native adapter API mismatch")
        provenance = _copy_mapping(
            adapter.validate_provenance(native["provenance"]),
            "loaded native provenance",
        )
        build = json.loads(
            native_module.build_info_json(),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
        build = _copy_mapping(build, "loaded native build")
    except ExperimentBlocked:
        raise
    except (AttributeError, TypeError, ValueError, UnicodeDecodeError) as exc:
        raise ExperimentBlocked("loaded native build provenance is invalid") from exc
    build["python"] = platform.python_version()
    if provenance.get("build") != build:
        raise ExperimentBlocked("loaded native build provenance differs from registration")
    if provenance != native["provenance"]:
        raise ExperimentBlocked("loaded native provenance differs from registration")
    if _canonical_digest(provenance) != native["provenance_sha256"]:
        raise ExperimentBlocked("loaded native provenance digest mismatch")

    runtime = importer(RUNTIME_MODULE_NAME)
    _verify_import_path(
        runtime,
        root=repo_root,
        relative_path=_source_inventory_path(normalized, "torch_runtime"),
        label="Torch runtime",
    )
    try:
        metadata = _copy_mapping(runtime.runtime_metadata(), "runtime metadata")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ExperimentBlocked("loaded runtime metadata is invalid") from exc
    if metadata != normalized["contract"]["runtime_metadata"]:
        raise ExperimentBlocked("loaded runtime metadata differs from registration")
    return {
        "adapter": adapter,
        "native_module": native_module,
        "provenance": provenance,
        "runtime": runtime,
    }


def _load_registered_runtime(
    registration: Mapping[str, Any],
    *,
    repo_root: Path,
    module_importer: Callable[[str], Any] | None,
    module_registry: Mapping[str, Any] | None,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None,
) -> Any:
    dependencies = _load_registered_dependencies(
        registration,
        repo_root=repo_root,
        module_importer=module_importer,
        module_registry=module_registry,
        external_binding_observer=external_binding_observer,
    )
    return dependencies["runtime"]


def load_authorized_runtime(
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval: Mapping[str, Any] | None = None,
    *,
    repo_root: Path | str | None = None,
    git_text: Callable[..., str] | None = None,
    source_inventory_observer: Callable[[Path], Mapping[str, Any]] | None = None,
    runtime_identity_observer: Callable[[], Mapping[str, Any]] | None = None,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None = None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
    module_importer: Callable[[str], Any] | None = None,
    module_registry: Mapping[str, Any] | None = None,
) -> Any:
    """Preflight all inert bytes, then load native before the bound Torch runtime."""
    validate_execution_authorization(
        authorization, registration, request, approval
    )
    root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
    source_only_preflight(
        root,
        registration,
        request,
        authorization,
        approval,
        git_text=git_text,
        source_inventory_observer=source_inventory_observer,
        runtime_identity_observer=runtime_identity_observer,
        external_binding_observer=external_binding_observer,
        checkpoint_snapshot_observer=checkpoint_snapshot_observer,
    )
    return _load_registered_runtime(
        registration,
        repo_root=root,
        module_importer=module_importer,
        module_registry=module_registry,
        external_binding_observer=external_binding_observer,
    )


def _validate_execution_identity(value: object) -> dict[str, str]:
    identity = _copy_mapping(value, "execution identity")
    _require_fields(
        identity,
        {
            "authorization_sha256",
            "logical_execution_id",
            "registration_sha256",
            "request_sha256",
        },
        "execution identity",
    )
    for name in (
        "authorization_sha256",
        "registration_sha256",
        "request_sha256",
    ):
        identity[name] = _digest(identity[name], f"execution identity {name}")
    identity["logical_execution_id"] = _logical_identity(
        identity["logical_execution_id"], "logical execution identity"
    )
    return identity


def _load_json_lines(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"{label} cannot be read: {exc}") from exc
    if not payload or not payload.endswith(b"\n"):
        raise ExperimentBlocked(f"{label} is incomplete")
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(keepends=True), start=1):
        try:
            value = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExperimentBlocked(
                f"{label} line {line_number} is invalid"
            ) from exc
        if not isinstance(value, dict) or line != canonical_json_bytes(value):
            raise ExperimentBlocked(f"{label} line {line_number} is not canonical")
        values.append(value)
    return values


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ExperimentBlocked("duplicate JSON object key")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise ExperimentBlocked(f"nonfinite JSON constant is invalid: {value}")


def _atomic_write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if path.exists() or temporary.exists():
        raise ExperimentBlocked(f"artifact already exists or is ambiguous: {path.name}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _append_durable(path: Path, payload: bytes) -> None:
    if not path.exists() or not payload or not payload.endswith(b"\n"):
        raise ExperimentBlocked(f"append target is invalid: {path.name}")
    with path.open("ab", buffering=0) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _lock_file(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _process_is_alive(process_id: int) -> bool:
    if process_id == os.getpid():
        return True
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _validate_owner(value: object) -> dict[str, Any]:
    owner = _copy_mapping(value, "lease owner")
    _require_fields(owner, {"acquired_at_ns", "process_id", "token"}, "lease owner")
    owner["process_id"] = _positive_integer(owner["process_id"], "lease owner PID")
    owner["acquired_at_ns"] = _positive_integer(
        owner["acquired_at_ns"], "lease acquisition coordinate"
    )
    if (
        not isinstance(owner["token"], str)
        or _OWNER_TOKEN_RE.fullmatch(owner["token"]) is None
    ):
        raise ExperimentBlocked("lease owner token is invalid")
    return owner


def _validate_lease_payload(value: object) -> dict[str, Any]:
    payload = _copy_mapping(value, "execution lease")
    _require_fields(
        payload,
        {"identity", "owner", "reclaimed_owner", "schema_version"},
        "execution lease",
    )
    if payload["schema_version"] != LEASE_SCHEMA_VERSION:
        raise ExperimentBlocked("execution lease schema mismatch")
    payload["identity"] = _validate_execution_identity(payload["identity"])
    payload["owner"] = _validate_owner(payload["owner"])
    if payload["reclaimed_owner"] is not None:
        payload["reclaimed_owner"] = _validate_owner(payload["reclaimed_owner"])
    return payload


class ExecutionLease:
    """Exclusive identity-bound ownership with explicit dead-owner reclamation."""

    def __init__(
        self,
        output_path: Path | str,
        *,
        identity: Mapping[str, Any],
        allow_stale_reclaim: bool = False,
        owner_alive: Callable[[int], bool] | None = None,
    ) -> None:
        if type(allow_stale_reclaim) is not bool:
            raise ExperimentBlocked("allow_stale_reclaim must be boolean")
        self.output_path = Path(output_path).resolve()
        self.identity = _validate_execution_identity(identity)
        self.path = self.output_path / LEASE_FILENAME
        self.allow_stale_reclaim = allow_stale_reclaim
        self._owner_alive = owner_alive or _process_is_alive
        self._handle: Any | None = None
        self.owner: dict[str, Any] | None = None
        self.reclaimed_owner: dict[str, Any] | None = None
        self.held = False

    def __enter__(self) -> "ExecutionLease":
        if self.held:
            return self
        key = os.path.normcase(str(self.path))
        if key in _ACTIVE_EXECUTION_LEASES:
            raise ExperimentBlocked("execution lease is already held")
        if self.output_path.exists() and not self.path.exists():
            raise ExperimentBlocked("preexisting output root lacks an execution lease")
        self.output_path.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b", buffering=0)
        locked = False
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                _lock_file(handle)
                locked = True
            except OSError as exc:
                raise ExperimentBlocked("execution lease is already held") from exc
            handle.seek(0)
            raw = handle.read()
            existing: dict[str, Any] | None = None
            if raw not in {b"", b"\0"}:
                try:
                    parsed = json.loads(
                        raw,
                        object_pairs_hook=_reject_duplicate_pairs,
                        parse_constant=_reject_json_constant,
                    )
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ExperimentBlocked("execution lease payload is invalid") from exc
                if raw != canonical_json_bytes(parsed):
                    raise ExperimentBlocked("execution lease payload is not canonical")
                existing = _validate_lease_payload(parsed)
                if existing["identity"] != self.identity:
                    raise ExperimentBlocked("execution lease identity mismatch")
                if not self.allow_stale_reclaim:
                    raise ExperimentBlocked("preexisting execution lease requires recovery")
                owner = existing["owner"]
                if self._owner_alive(owner["process_id"]):
                    raise ExperimentBlocked("execution lease owner is still alive")
                ambiguous = sorted(
                    path.name
                    for path in self.output_path.iterdir()
                    if path.name.startswith(".")
                    and path.name.endswith(".tmp")
                )
                if ambiguous:
                    raise ExperimentBlocked("stale lease has ambiguous temporary output")
                self.reclaimed_owner = owner
            self.owner = {
                "acquired_at_ns": time.time_ns(),
                "process_id": os.getpid(),
                "token": uuid.uuid4().hex,
            }
            payload = {
                "identity": self.identity,
                "owner": self.owner,
                "reclaimed_owner": self.reclaimed_owner,
                "schema_version": LEASE_SCHEMA_VERSION,
            }
            handle.seek(0)
            handle.truncate()
            handle.write(canonical_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
            self._handle = handle
            self.held = True
            _ACTIVE_EXECUTION_LEASES.add(key)
            return self
        except BaseException:
            if locked:
                try:
                    _unlock_file(handle)
                except OSError:
                    pass
            handle.close()
            raise

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        handle = self._handle
        key = os.path.normcase(str(self.path))
        self._handle = None
        self.held = False
        _ACTIVE_EXECUTION_LEASES.discard(key)
        if handle is not None:
            try:
                handle.seek(0)
                raw = handle.read()
                try:
                    payload = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise ExperimentBlocked("execution lease identity drifted") from error
                normalized = _validate_lease_payload(payload)
                if normalized["identity"] != self.identity or normalized["owner"] != self.owner:
                    raise ExperimentBlocked("execution lease identity drifted")
            finally:
                try:
                    _unlock_file(handle)
                finally:
                    handle.close()


def _require_execution_lease(
    lease: ExecutionLease,
    output_path: Path | str,
    identity: Mapping[str, Any],
) -> None:
    normalized = _validate_execution_identity(identity)
    if not isinstance(lease, ExecutionLease) or not lease.held:
        raise ExperimentBlocked("execution lease is not held")
    if lease.output_path != Path(output_path).resolve():
        raise ExperimentBlocked("execution lease output mismatch")
    if lease.identity != normalized:
        raise ExperimentBlocked("execution lease identity mismatch")


def _registration_for_identity(
    registration: Mapping[str, Any], identity: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    normalized_registration = validate_registration(registration)
    normalized_identity = _validate_execution_identity(identity)
    if (
        registration_sha256(normalized_registration)
        != normalized_identity["registration_sha256"]
    ):
        raise ExperimentBlocked("execution identity registration mismatch")
    if (
        normalized_registration["registration_id"]
        != normalized_identity["logical_execution_id"]
    ):
        raise ExperimentBlocked("logical execution registration mismatch")
    return normalized_registration, normalized_identity


def _registration_for_output(
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    output_path: Path | str,
) -> tuple[dict[str, Any], dict[str, str], Path]:
    normalized_registration, normalized_identity = _registration_for_identity(
        registration, identity
    )
    output = Path(output_path).resolve()
    registered_output = Path(normalized_registration["output_root"]).resolve()
    if os.path.normcase(str(output)) != os.path.normcase(str(registered_output)):
        raise ExperimentBlocked("output root differs from exact registration")
    return normalized_registration, normalized_identity, output


def _access_journal_header(
    registration: Mapping[str, Any], identity: Mapping[str, Any]
) -> dict[str, Any]:
    normalized_registration, normalized_identity = _registration_for_identity(
        registration, identity
    )
    return {
        "event_index": 0,
        "identity": normalized_identity,
        "kind": "journal_opened",
        "registration_sha256": registration_sha256(normalized_registration),
        "schedule_sha256": normalized_registration["schedule"]["seeds_sha256"],
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
    }


def initialize_access_journal(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Create a write-once journal bound to the exact registered schedule."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    header = _access_journal_header(normalized_registration, normalized_identity)
    _atomic_write_once(output / ACCESS_JOURNAL_FILENAME, canonical_json_bytes(header))
    return load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )


def _validate_access_coordinate(value: Mapping[str, Any]) -> dict[str, Any]:
    coordinate = {
        "access_ordinal": _positive_integer(
            value["access_ordinal"], "access ordinal"
        ),
        "attempt_ordinal": _nonnegative_integer(
            value["attempt_ordinal"], "attempt ordinal"
        ),
        "chunk_index": _nonnegative_integer(value["chunk_index"], "chunk index"),
        "seed": _nonnegative_integer(value["seed"], "scheduled seed"),
    }
    if coordinate["attempt_ordinal"] not in {0, 1}:
        raise ExperimentBlocked("attempt ordinal must be primary or one resume")
    if coordinate["chunk_index"] >= CHUNK_COUNT:
        raise ExperimentBlocked("chunk index exceeds the registered schedule")
    return coordinate


def validate_access_journal_bytes(
    payload: bytes,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Replay the exact primary schedule and at most one incomplete-chunk resume."""
    normalized_registration, normalized_identity = _registration_for_identity(
        registration, identity
    )
    if not payload or not payload.endswith(b"\n"):
        raise ExperimentBlocked("access journal is incomplete")
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(keepends=True), start=1):
        try:
            value = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExperimentBlocked(
                f"access journal line {line_number} is invalid"
            ) from exc
        if not isinstance(value, dict) or line != canonical_json_bytes(value):
            raise ExperimentBlocked(
                f"access journal line {line_number} is not canonical"
            )
        values.append(value)
    header = values[0]
    if header != _access_journal_header(normalized_registration, normalized_identity):
        raise ExperimentBlocked("access journal header mismatch")
    schedule = normalized_registration["schedule"]
    pending: dict[str, Any] | None = None
    debited = 0
    completed = 0
    terminal_records = 0
    primary_position = 0
    primary_completed = [0 for _ in range(CHUNK_COUNT)]
    completed_chunks: set[int] = set()
    primary_interrupted_chunk: int | None = None
    resume_used = False
    resume_chunk: int | None = None
    resume_mode: str | None = None
    resume_position = 0
    resume_completed = 0
    resume_complete = False
    resume_failed = False
    terminal_access_failure = False
    last_access_status: str | None = None
    for event_index, event in enumerate(values[1:], start=1):
        if event.get("event_index") != event_index:
            raise ExperimentBlocked("access journal event sequence mismatch")
        if event.get("schema_version") != ACCESS_JOURNAL_SCHEMA_VERSION:
            raise ExperimentBlocked("access journal schema mismatch")
        kind = event.get("kind")
        if kind == "access_debited":
            _require_fields(
                event,
                {
                    "access_ordinal",
                    "attempt_ordinal",
                    "chunk_index",
                    "event_index",
                    "kind",
                    "schema_version",
                    "seed",
                    "status",
                },
                "access debit event",
            )
            if pending is not None:
                raise ExperimentBlocked("access journal has overlapping accesses")
            if terminal_access_failure or resume_failed:
                raise ExperimentBlocked("access journal continues after terminal failure")
            coordinate = _validate_access_coordinate(event)
            if coordinate["access_ordinal"] != debited + 1:
                raise ExperimentBlocked("access journal ordinal is not monotonic")
            if event["status"] != "debited":
                raise ExperimentBlocked("access debit status mismatch")
            attempt = coordinate["attempt_ordinal"]
            if attempt == 0:
                if primary_interrupted_chunk is not None:
                    raise ExperimentBlocked(
                        "primary schedule continues after an incomplete chunk"
                    )
                if resume_used and not resume_complete:
                    raise ExperimentBlocked("primary schedule overlaps its replay")
                if primary_position >= SCHEDULED_TRAJECTORIES:
                    raise ExperimentBlocked("primary schedule exceeds registration")
                expected_chunk = primary_position // EPISODES_PER_CHUNK
                expected_seed = schedule["seeds"][primary_position]
                if (
                    coordinate["chunk_index"] != expected_chunk
                    or coordinate["seed"] != expected_seed
                ):
                    raise ExperimentBlocked(
                        "primary access differs from exact chunk/seed order"
                    )
                primary_position += 1
            else:
                if not resume_used or resume_chunk is None:
                    raise ExperimentBlocked("resume access lacks a durable resume marker")
                if resume_mode != "replay_uncheckpointed_chunk":
                    raise ExperimentBlocked("checkpoint continuation cannot replay seeds")
                if resume_complete or resume_failed:
                    raise ExperimentBlocked("resume chunk cannot be replayed again")
                if resume_position >= EPISODES_PER_CHUNK:
                    raise ExperimentBlocked("resume exceeds one complete chunk")
                expected_seed = schedule["chunks"][resume_chunk][resume_position]
                if (
                    coordinate["chunk_index"] != resume_chunk
                    or coordinate["seed"] != expected_seed
                ):
                    raise ExperimentBlocked(
                        "resume access substitutes its registered chunk or seed"
                    )
                resume_position += 1
            pending = coordinate
            debited += 1
        elif kind == "access_terminal":
            _require_fields(
                event,
                {
                    "access_ordinal",
                    "attempt_ordinal",
                    "chunk_index",
                    "event_index",
                    "kind",
                    "schema_version",
                    "seed",
                    "status",
                },
                "access terminal event",
            )
            coordinate = _validate_access_coordinate(event)
            if pending is None or coordinate != {
                key: pending[key]
                for key in (
                    "access_ordinal",
                    "attempt_ordinal",
                    "chunk_index",
                    "seed",
                )
            }:
                raise ExperimentBlocked("access terminal does not match its debit")
            if event["status"] not in {
                "completed",
                "failed",
                "infrastructure_interrupted",
            }:
                raise ExperimentBlocked("access terminal status is invalid")
            status = event["status"]
            attempt = pending["attempt_ordinal"]
            chunk_index = pending["chunk_index"]
            if status == "completed":
                completed += 1
                if attempt == 0:
                    primary_completed[chunk_index] += 1
                    if primary_completed[chunk_index] == EPISODES_PER_CHUNK:
                        completed_chunks.add(chunk_index)
                else:
                    resume_completed += 1
                    if resume_completed == EPISODES_PER_CHUNK:
                        resume_complete = True
                        completed_chunks.add(chunk_index)
                        primary_position = max(
                            primary_position,
                            (chunk_index + 1) * EPISODES_PER_CHUNK,
                        )
            elif status == "infrastructure_interrupted":
                if attempt == 0:
                    primary_interrupted_chunk = chunk_index
                else:
                    resume_failed = True
            else:
                terminal_access_failure = True
            terminal_records += 1
            last_access_status = status
            pending = None
        elif kind == "resume_started":
            _require_fields(
                event,
                {
                    "attempt_ordinal",
                    "chunk_index",
                    "event_index",
                    "kind",
                    "mode",
                    "schema_version",
                    "status",
                },
                "resume marker event",
            )
            if pending is not None:
                raise ExperimentBlocked("resume marker cannot bypass an open access")
            if resume_used:
                raise ExperimentBlocked("a second resume is forbidden")
            if terminal_access_failure:
                raise ExperimentBlocked("algorithm failure cannot trigger a resume")
            chunk_index = _nonnegative_integer(
                event["chunk_index"], "resume chunk index"
            )
            mode = event["mode"]
            if mode not in {
                "continue_after_checkpoint",
                "replay_uncheckpointed_chunk",
            }:
                raise ExperimentBlocked("resume mode is invalid")
            if event["attempt_ordinal"] != 1 or event["status"] != "resume_used":
                raise ExperimentBlocked("resume marker coordinates mismatch")
            if mode == "replay_uncheckpointed_chunk":
                inferred_partial = (
                    primary_position > 0
                    and primary_position % EPISODES_PER_CHUNK != 0
                    and chunk_index == primary_position // EPISODES_PER_CHUNK
                )
                inferred_complete = (
                    chunk_index in completed_chunks
                    and primary_position == (chunk_index + 1) * EPISODES_PER_CHUNK
                )
                if primary_interrupted_chunk is not None:
                    if chunk_index != primary_interrupted_chunk:
                        raise ExperimentBlocked("resume marker coordinates mismatch")
                elif not (inferred_partial or inferred_complete):
                    raise ExperimentBlocked(
                        "resume lacks one uncheckpointed primary chunk"
                    )
                if any(index not in completed_chunks for index in range(chunk_index)):
                    raise ExperimentBlocked("resume skips an earlier incomplete chunk")
                resume_complete = False
            else:
                expected_chunk = primary_position // EPISODES_PER_CHUNK
                if (
                    primary_interrupted_chunk is not None
                    or debited == 0
                    or primary_position % EPISODES_PER_CHUNK != 0
                    or chunk_index != expected_chunk
                    or chunk_index >= CHUNK_COUNT
                    or chunk_index in completed_chunks
                    or any(
                        index not in completed_chunks for index in range(chunk_index)
                    )
                ):
                    raise ExperimentBlocked(
                        "checkpoint-boundary resume coordinates mismatch"
                    )
                resume_complete = True
            resume_used = True
            resume_chunk = chunk_index
            resume_mode = mode
            primary_interrupted_chunk = None
        else:
            raise ExperimentBlocked("access journal event kind is invalid")
    resume_candidate: int | None = primary_interrupted_chunk
    if pending is not None:
        if pending["attempt_ordinal"] == 0:
            resume_candidate = pending["chunk_index"]
        else:
            resume_failed = True
    return {
        "completed_accesses": completed,
        "completed_chunk_indices": sorted(completed_chunks),
        "debited_accesses": debited,
        "events": values,
        "pending_access": pending,
        "primary_next_position": primary_position,
        "resume_candidate_chunk_index": resume_candidate,
        "resume_chunk_index": resume_chunk,
        "resume_complete": resume_complete,
        "resume_failed": resume_failed,
        "resume_mode": resume_mode,
        "resume_used": resume_used,
        "terminal_access_failure": terminal_access_failure,
        "terminal_records": terminal_records,
        "last_access_status": last_access_status,
    }


def load_access_journal(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    path = output / ACCESS_JOURNAL_FILENAME
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"access journal cannot be read: {exc}") from exc
    return validate_access_journal_bytes(
        payload,
        registration=normalized_registration,
        identity=normalized_identity,
    )


def _append_validated_access_event(
    path: Path,
    event: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> None:
    try:
        current = path.read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"access journal cannot be read: {exc}") from exc
    candidate = current + canonical_json_bytes(dict(event))
    validate_access_journal_bytes(
        candidate,
        registration=registration,
        identity=identity,
    )
    _append_durable(path, canonical_json_bytes(dict(event)))


def append_access_debit(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    chunk_index: int,
    seed: int,
    attempt_ordinal: int,
) -> dict[str, Any]:
    """Flush one debit before its registered seed may reach an environment."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    journal = load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if journal["pending_access"] is not None:
        raise ExperimentBlocked("previous environment access is still open")
    coordinate = _validate_access_coordinate(
        {
            "access_ordinal": journal["debited_accesses"] + 1,
            "attempt_ordinal": attempt_ordinal,
            "chunk_index": chunk_index,
            "seed": seed,
        }
    )
    if coordinate["access_ordinal"] > experiment_contract()["limits"][
        "max_environment_accesses"
    ]:
        raise ExperimentBlocked("environment access ceiling would be exceeded")
    event = {
        **coordinate,
        "event_index": len(journal["events"]),
        "kind": "access_debited",
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
        "status": "debited",
    }
    path = output / ACCESS_JOURNAL_FILENAME
    _append_validated_access_event(
        path,
        event,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    return event


def append_access_terminal(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    status: str,
) -> dict[str, Any]:
    """Append a terminal status without rewriting its durable debit prefix."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    journal = load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    pending = journal["pending_access"]
    if pending is None:
        raise ExperimentBlocked("access terminal lacks a pending debit")
    if status not in {"completed", "failed", "infrastructure_interrupted"}:
        raise ExperimentBlocked("access terminal status is invalid")
    event = {
        **pending,
        "event_index": len(journal["events"]),
        "kind": "access_terminal",
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
        "status": status,
    }
    _append_validated_access_event(
        output / ACCESS_JOURNAL_FILENAME,
        event,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    return event


def start_incomplete_chunk_resume(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Persist the sole resume marker for a chunk or checkpoint boundary."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    journal = load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if journal["pending_access"] is not None:
        append_access_terminal(
            output,
            registration=normalized_registration,
            identity=normalized_identity,
            lease=lease,
            status="infrastructure_interrupted",
        )
        journal = load_access_journal(
            output,
            registration=normalized_registration,
            identity=normalized_identity,
        )
    reconcile_resource_ledger_from_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
        lease=lease,
    )
    if journal["resume_used"]:
        raise ExperimentBlocked("a second resume is forbidden")
    if journal["debited_accesses"] == 0:
        raise ExperimentBlocked("post-start resume requires a durable seed debit")
    if journal["terminal_access_failure"]:
        raise ExperimentBlocked("algorithm failure cannot trigger a resume")
    chain = load_checkpoint_chain(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    checkpoint_count = len(chain)
    primary_position = journal["primary_next_position"]
    candidate = journal["resume_candidate_chunk_index"]
    if checkpoint_count > CHUNK_COUNT or checkpoint_count * EPISODES_PER_CHUNK > primary_position:
        raise ExperimentBlocked("resume checkpoint and journal prefixes are ambiguous")
    if candidate is not None:
        chunk_index = candidate
        mode = "replay_uncheckpointed_chunk"
    elif primary_position > checkpoint_count * EPISODES_PER_CHUNK:
        chunk_index = checkpoint_count
        mode = "replay_uncheckpointed_chunk"
    elif (
        primary_position == checkpoint_count * EPISODES_PER_CHUNK
        and checkpoint_count < CHUNK_COUNT
    ):
        chunk_index = checkpoint_count
        mode = "continue_after_checkpoint"
    else:
        raise ExperimentBlocked("resume lacks a recoverable execution boundary")
    if chunk_index != checkpoint_count:
        raise ExperimentBlocked("resume anchor differs from the checkpoint prefix")
    event = {
        "attempt_ordinal": 1,
        "chunk_index": chunk_index,
        "event_index": len(journal["events"]),
        "kind": "resume_started",
        "mode": mode,
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
        "status": "resume_used",
    }
    _append_validated_access_event(
        output / ACCESS_JOURNAL_FILENAME,
        event,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    return event


def _resource_limits() -> dict[str, int | float]:
    limits = experiment_contract()["limits"]
    return {
        "charged_seconds": limits["max_charged_seconds"],
        "environment_accesses": limits["max_environment_accesses"],
        "optimizer_updates": limits["max_optimizer_updates"],
        "retained_decisions": limits["max_retained_decisions"],
        "stored_bytes": limits["max_stored_bytes"],
        "uncompressed_bytes": limits["max_uncompressed_bytes"],
    }


def _zero_resources() -> dict[str, int | float]:
    return {
        "charged_seconds": 0.0,
        "environment_accesses": 0,
        "optimizer_updates": 0,
        "retained_decisions": 0,
        "stored_bytes": 0,
        "uncompressed_bytes": 0,
    }


def _normalize_resources(value: object) -> dict[str, int | float]:
    resources = _copy_mapping(value, "resource prefix")
    _require_fields(resources, set(_RESOURCE_FIELDS), "resource prefix")
    normalized: dict[str, int | float] = {}
    limits = _resource_limits()
    for name in _RESOURCE_FIELDS:
        item = resources[name]
        if name in _INTEGER_RESOURCE_FIELDS:
            normalized[name] = _nonnegative_integer(item, f"resource {name}")
        else:
            if isinstance(item, bool):
                raise ExperimentBlocked("charged seconds must be finite and nonnegative")
            try:
                numeric = float(item)
            except (TypeError, ValueError) as exc:
                raise ExperimentBlocked(
                    "charged seconds must be finite and nonnegative"
                ) from exc
            if not math.isfinite(numeric) or numeric < 0.0:
                raise ExperimentBlocked("charged seconds must be finite and nonnegative")
            normalized[name] = numeric
        if normalized[name] > limits[name]:
            raise ExperimentBlocked(f"resource {name} exceeds its registered limit")
    return normalized


def _resource_header(identity: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "identity": _validate_execution_identity(identity),
        "kind": "resource_ledger_opened",
        "limits": _resource_limits(),
        "resources": _zero_resources(),
        "revision": 0,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }


def initialize_resource_ledger(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Create the immutable zero-resource ledger prefix."""
    _, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    header = _resource_header(normalized_identity)
    _atomic_write_once(output / RESOURCE_LEDGER_FILENAME, canonical_json_bytes(header))
    return load_resource_ledger(output, identity=normalized_identity)


def validate_resource_ledger_bytes(
    payload: bytes, *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    normalized_identity = _validate_execution_identity(identity)
    if not payload or not payload.endswith(b"\n"):
        raise ExperimentBlocked("resource ledger is incomplete")
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(keepends=True), start=1):
        try:
            event = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExperimentBlocked(
                f"resource ledger line {line_number} is invalid"
            ) from exc
        if not isinstance(event, dict) or line != canonical_json_bytes(event):
            raise ExperimentBlocked(
                f"resource ledger line {line_number} is not canonical"
            )
        events.append(event)
    header = events[0]
    if header != _resource_header(normalized_identity):
        raise ExperimentBlocked("resource ledger header mismatch")
    previous = header
    previous_resources = _zero_resources()
    for revision, event in enumerate(events[1:], start=1):
        _require_fields(
            event,
            {
                "kind",
                "previous_event_sha256",
                "reason",
                "resources",
                "revision",
                "schema_version",
            },
            "resource ledger event",
        )
        if (
            event["schema_version"] != RESOURCE_LEDGER_SCHEMA_VERSION
            or event["kind"] != "resource_prefix_advanced"
            or event["revision"] != revision
        ):
            raise ExperimentBlocked("resource ledger revision mismatch")
        if event["previous_event_sha256"] != _canonical_digest(previous):
            raise ExperimentBlocked("resource ledger hash chain mismatch")
        _nonempty_string(event["reason"], "resource advance reason")
        resources = _normalize_resources(event["resources"])
        if any(resources[name] < previous_resources[name] for name in _RESOURCE_FIELDS):
            raise ExperimentBlocked("resource prefix is not monotonic")
        if resources == previous_resources:
            raise ExperimentBlocked("resource prefix did not advance")
        event["resources"] = resources
        previous = event
        previous_resources = resources
    return {
        "events": events,
        "limits": _resource_limits(),
        "resources": previous_resources,
        "revision": len(events) - 1,
    }


def load_resource_ledger(
    output_path: Path | str, *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    path = Path(output_path).resolve() / RESOURCE_LEDGER_FILENAME
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"resource ledger cannot be read: {exc}") from exc
    return validate_resource_ledger_bytes(payload, identity=identity)


def advance_resource_ledger(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    resources: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    """Append one bounded resource prefix; no coordinate may move backward."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    ledger = load_resource_ledger(output, identity=normalized_identity)
    normalized_resources = _normalize_resources(resources)
    previous_resources = ledger["resources"]
    if any(
        normalized_resources[name] < previous_resources[name]
        for name in _RESOURCE_FIELDS
    ):
        raise ExperimentBlocked("resource prefix is not monotonic")
    if normalized_resources == previous_resources:
        raise ExperimentBlocked("resource prefix did not advance")
    if (output / ACCESS_JOURNAL_FILENAME).exists():
        journal = load_access_journal(
            output,
            registration=normalized_registration,
            identity=normalized_identity,
        )
        if normalized_resources["environment_accesses"] > journal["debited_accesses"]:
            raise ExperimentBlocked("resource access count exceeds durable journal")
    event = {
        "kind": "resource_prefix_advanced",
        "previous_event_sha256": _canonical_digest(ledger["events"][-1]),
        "reason": _nonempty_string(reason, "resource advance reason"),
        "resources": normalized_resources,
        "revision": ledger["revision"] + 1,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }
    _append_durable(output / RESOURCE_LEDGER_FILENAME, canonical_json_bytes(event))
    return load_resource_ledger(output, identity=normalized_identity)


def reconcile_resource_ledger_from_journal(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Advance access resources to the durable write-ahead journal prefix."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    journal = load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    ledger = load_resource_ledger(output, identity=normalized_identity)
    debited = journal["debited_accesses"]
    observed = ledger["resources"]["environment_accesses"]
    if observed > debited:
        raise ExperimentBlocked("resource ledger is ahead of the access journal")
    if observed == debited:
        return ledger
    resources = dict(ledger["resources"])
    resources["environment_accesses"] = debited
    return advance_resource_ledger(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
        lease=lease,
        resources=resources,
        reason="access-journal-reconcile",
    )


def begin_environment_access(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    chunk_index: int,
    seed: int,
    attempt_ordinal: int,
) -> dict[str, Any]:
    """Write the debit first, then advance the monotonic resource ledger."""
    event = append_access_debit(
        output_path,
        registration=registration,
        identity=identity,
        lease=lease,
        chunk_index=chunk_index,
        seed=seed,
        attempt_ordinal=attempt_ordinal,
    )
    reconcile_resource_ledger_from_journal(
        output_path,
        registration=registration,
        identity=identity,
        lease=lease,
    )
    return event


def complete_environment_access(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    status: str = "completed",
) -> dict[str, Any]:
    return append_access_terminal(
        output_path,
        registration=registration,
        identity=identity,
        lease=lease,
        status=status,
    )


def _opaque_payload_binding(value: object, label: str) -> dict[str, Any]:
    payload = _copy_mapping(value, label)
    payload_bytes = canonical_json_bytes(payload)
    return {
        "payload": payload,
        "sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "size_bytes": len(payload_bytes),
    }


def _validate_opaque_payload_binding(
    value: object, label: str
) -> dict[str, Any]:
    binding = _copy_mapping(value, label)
    _require_fields(binding, {"payload", "sha256", "size_bytes"}, label)
    expected = _opaque_payload_binding(binding["payload"], f"{label} payload")
    if binding != expected:
        raise ExperimentBlocked(f"{label} bytes mismatch")
    return binding


def build_bootstrap_envelope(
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    runtime_checkpoint_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one opaque seeded runtime state without importing its implementation."""
    normalized_registration, normalized_identity = _registration_for_identity(
        registration, identity
    )
    body = {
        "authority": registration_authority(),
        "identity": normalized_identity,
        "registration_sha256": registration_sha256(normalized_registration),
        "resource_use": _zero_resources(),
        "runtime_checkpoint": _opaque_payload_binding(
            runtime_checkpoint_payload, "bootstrap runtime checkpoint"
        ),
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
    }
    return {**body, "bootstrap_sha256": _canonical_digest(body)}


def validate_bootstrap_envelope(
    value: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    bootstrap = _copy_mapping(value, "bootstrap")
    _require_fields(
        bootstrap,
        {
            "authority",
            "bootstrap_sha256",
            "identity",
            "registration_sha256",
            "resource_use",
            "runtime_checkpoint",
            "schema_version",
        },
        "bootstrap",
    )
    if bootstrap["schema_version"] != BOOTSTRAP_SCHEMA_VERSION:
        raise ExperimentBlocked("bootstrap schema mismatch")
    normalized_registration, normalized_identity = _registration_for_identity(
        registration, identity
    )
    if bootstrap["identity"] != normalized_identity:
        raise ExperimentBlocked("bootstrap execution identity mismatch")
    if bootstrap["registration_sha256"] != registration_sha256(
        normalized_registration
    ):
        raise ExperimentBlocked("bootstrap registration mismatch")
    if bootstrap["authority"] != registration_authority():
        raise ExperimentBlocked("bootstrap authority must remain all false")
    if _normalize_resources(bootstrap["resource_use"]) != _zero_resources():
        raise ExperimentBlocked("bootstrap resources must be zero")
    bootstrap["resource_use"] = _zero_resources()
    bootstrap["runtime_checkpoint"] = _validate_opaque_payload_binding(
        bootstrap["runtime_checkpoint"], "bootstrap runtime checkpoint"
    )
    digest = _digest(bootstrap["bootstrap_sha256"], "bootstrap identity")
    body = {key: item for key, item in bootstrap.items() if key != "bootstrap_sha256"}
    if digest != _canonical_digest(body):
        raise ExperimentBlocked("bootstrap identity mismatch")
    return bootstrap


def publish_bootstrap(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    runtime_checkpoint_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish the write-once runtime bootstrap before any environment access."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    journal = load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    ledger = load_resource_ledger(output, identity=normalized_identity)
    if journal["debited_accesses"] != 0 or ledger["resources"] != _zero_resources():
        raise ExperimentBlocked("bootstrap must precede every resource access")
    bootstrap = build_bootstrap_envelope(
        normalized_registration,
        normalized_identity,
        runtime_checkpoint_payload,
    )
    payload = canonical_json_bytes(bootstrap)
    if len(payload) > experiment_contract()["limits"]["max_artifact_bytes"]:
        raise ExperimentBlocked("bootstrap exceeds the artifact byte ceiling")
    _atomic_write_once(output / BOOTSTRAP_FILENAME, payload)
    return bootstrap


def load_bootstrap(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    value = _load_canonical_json_file(
        output / BOOTSTRAP_FILENAME,
        "bootstrap",
    )
    return validate_bootstrap_envelope(
        value,
        registration=normalized_registration,
        identity=normalized_identity,
    )


def deterministic_gzip_bytes(payload: bytes) -> bytes:
    """Return gzip bytes with fixed filename and timestamp metadata."""
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=0) as handle:
        handle.write(payload)
    return buffer.getvalue()


def _checkpoint_relative_paths(chunk_index: int) -> tuple[str, str]:
    index = _nonnegative_integer(chunk_index, "checkpoint chunk index")
    if index >= CHUNK_COUNT:
        raise ExperimentBlocked("checkpoint chunk index exceeds registration")
    number = index + 1
    return (
        f"checkpoints/checkpoint_{number:04d}.json",
        f"checkpoints/chunk_{number:04d}_evidence.json.gz",
    )


def _chunk_evidence_artifact(
    chunk_index: int,
    evidence: Mapping[str, Any],
    runtime_checkpoint_payload: Mapping[str, Any],
) -> tuple[dict[str, Any], bytes]:
    checkpoint_path, evidence_path = _checkpoint_relative_paths(chunk_index)
    del checkpoint_path
    document = {
        "chunk_index": chunk_index,
        "evidence": _copy_mapping(evidence, "chunk evidence"),
        "runtime_checkpoint": _opaque_payload_binding(
            runtime_checkpoint_payload, "chunk evidence runtime checkpoint"
        ),
        "schema_version": CHUNK_EVIDENCE_SCHEMA_VERSION,
    }
    uncompressed = canonical_json_bytes(document)
    stored = deterministic_gzip_bytes(uncompressed)
    binding = {
        "encoding": "deterministic-gzip-canonical-json-v1",
        "path": evidence_path,
        "stored_sha256": hashlib.sha256(stored).hexdigest(),
        "stored_size_bytes": len(stored),
        "uncompressed_sha256": hashlib.sha256(uncompressed).hexdigest(),
        "uncompressed_size_bytes": len(uncompressed),
    }
    return binding, stored


def _decode_chunk_evidence_artifact(
    stored: bytes, *, chunk_index: int
) -> tuple[dict[str, Any], bytes]:
    try:
        uncompressed = gzip.decompress(stored)
        document = json.loads(
            uncompressed,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (
        EOFError,
        gzip.BadGzipFile,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise ExperimentBlocked("chunk evidence bytes or JSON are invalid") from exc
    document = _copy_mapping(document, "chunk evidence document")
    _require_fields(
        document,
        {"chunk_index", "evidence", "runtime_checkpoint", "schema_version"},
        "chunk evidence document",
    )
    if (
        document["schema_version"] != CHUNK_EVIDENCE_SCHEMA_VERSION
        or document["chunk_index"] != chunk_index
        or uncompressed != canonical_json_bytes(document)
    ):
        raise ExperimentBlocked("chunk evidence document mismatch")
    document["evidence"] = _copy_mapping(
        document["evidence"], "chunk evidence"
    )
    document["runtime_checkpoint"] = _validate_opaque_payload_binding(
        document["runtime_checkpoint"], "chunk evidence runtime checkpoint"
    )
    return document, uncompressed


def _validate_chunk_evidence_binding(
    value: object,
    *,
    output: Path,
    chunk_index: int,
    expected_runtime_checkpoint: Mapping[str, Any],
) -> dict[str, Any]:
    binding = _copy_mapping(value, "chunk evidence binding")
    _require_fields(
        binding,
        {
            "encoding",
            "path",
            "stored_sha256",
            "stored_size_bytes",
            "uncompressed_sha256",
            "uncompressed_size_bytes",
        },
        "chunk evidence binding",
    )
    _, expected_path = _checkpoint_relative_paths(chunk_index)
    if (
        binding["encoding"] != "deterministic-gzip-canonical-json-v1"
        or binding["path"] != expected_path
    ):
        raise ExperimentBlocked("chunk evidence encoding or path mismatch")
    for field in ("stored_sha256", "uncompressed_sha256"):
        _digest(binding[field], f"chunk evidence {field}")
    for field in ("stored_size_bytes", "uncompressed_size_bytes"):
        _nonnegative_integer(binding[field], f"chunk evidence {field}")
    path = output / PurePosixPath(expected_path)
    try:
        stored = path.read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"chunk evidence bytes mismatch: {exc}") from exc
    document, uncompressed = _decode_chunk_evidence_artifact(
        stored, chunk_index=chunk_index
    )
    if document["runtime_checkpoint"] != _validate_opaque_payload_binding(
        expected_runtime_checkpoint, "checkpoint runtime checkpoint"
    ):
        raise ExperimentBlocked("chunk evidence runtime checkpoint mismatch")
    observed = {
        "encoding": "deterministic-gzip-canonical-json-v1",
        "path": expected_path,
        "stored_sha256": hashlib.sha256(stored).hexdigest(),
        "stored_size_bytes": len(stored),
        "uncompressed_sha256": hashlib.sha256(uncompressed).hexdigest(),
        "uncompressed_size_bytes": len(uncompressed),
    }
    if binding != observed or stored != deterministic_gzip_bytes(uncompressed):
        raise ExperimentBlocked("chunk evidence bytes mismatch")
    return binding


def _journal_prefix_binding(output: Path) -> dict[str, Any]:
    try:
        payload = (output / ACCESS_JOURNAL_FILENAME).read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"access journal cannot be read: {exc}") from exc
    return {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _validate_journal_prefix_binding(value: object, output: Path) -> dict[str, Any]:
    binding = _copy_mapping(value, "access journal prefix")
    _require_fields(binding, {"sha256", "size_bytes"}, "access journal prefix")
    digest = _digest(binding["sha256"], "access journal prefix digest")
    size = _nonnegative_integer(binding["size_bytes"], "access journal prefix size")
    try:
        current = (output / ACCESS_JOURNAL_FILENAME).read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"access journal cannot be read: {exc}") from exc
    if size > len(current) or hashlib.sha256(current[:size]).hexdigest() != digest:
        raise ExperimentBlocked("access journal checkpoint prefix mismatch")
    return binding


def _checkpoint_body(
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    chunk_index: int,
    previous_checkpoint_sha256: str,
    resource_revision: int,
    resource_use: Mapping[str, Any],
    runtime_checkpoint_payload: Mapping[str, Any],
    chunk_evidence_binding: Mapping[str, Any],
    journal_prefix: Mapping[str, Any],
    resume_used: bool,
) -> dict[str, Any]:
    normalized_registration, normalized_identity = _registration_for_identity(
        registration, identity
    )
    if type(resume_used) is not bool:
        raise ExperimentBlocked("checkpoint resume-used flag is invalid")
    return {
        "access_journal_prefix": copy.deepcopy(dict(journal_prefix)),
        "checkpoint_index": chunk_index + 1,
        "chunk_evidence": copy.deepcopy(dict(chunk_evidence_binding)),
        "chunk_index": chunk_index,
        "identity": normalized_identity,
        "previous_checkpoint_sha256": _digest(
            previous_checkpoint_sha256, "previous checkpoint identity"
        ),
        "registration_sha256": registration_sha256(normalized_registration),
        "resource_revision": _positive_integer(
            resource_revision, "checkpoint resource revision"
        ),
        "resource_use": _normalize_resources(resource_use),
        "resume_used": resume_used,
        "runtime_checkpoint": _opaque_payload_binding(
            runtime_checkpoint_payload, "runtime checkpoint"
        ),
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
    }


def _load_checkpoint_envelope(path: Path) -> dict[str, Any]:
    return _load_canonical_json_file(path, f"checkpoint {path.name}")


def _validate_checkpoint_envelope(
    value: Mapping[str, Any],
    *,
    output: Path,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    expected_chunk_index: int,
    previous_checkpoint_sha256: str,
    ledger: Mapping[str, Any],
    journal: Mapping[str, Any],
) -> dict[str, Any]:
    checkpoint = _copy_mapping(value, "checkpoint")
    _require_fields(
        checkpoint,
        {
            "access_journal_prefix",
            "checkpoint_index",
            "checkpoint_sha256",
            "chunk_evidence",
            "chunk_index",
            "identity",
            "previous_checkpoint_sha256",
            "registration_sha256",
            "resource_revision",
            "resource_use",
            "resume_used",
            "runtime_checkpoint",
            "schema_version",
        },
        "checkpoint",
    )
    if checkpoint["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise ExperimentBlocked("checkpoint schema mismatch")
    if (
        checkpoint["chunk_index"] != expected_chunk_index
        or checkpoint["checkpoint_index"] != expected_chunk_index + 1
    ):
        raise ExperimentBlocked("checkpoint coordinate mismatch")
    normalized_registration, normalized_identity = _registration_for_identity(
        registration, identity
    )
    if checkpoint["identity"] != normalized_identity:
        raise ExperimentBlocked("checkpoint execution identity mismatch")
    if checkpoint["registration_sha256"] != registration_sha256(
        normalized_registration
    ):
        raise ExperimentBlocked("checkpoint registration mismatch")
    if checkpoint["previous_checkpoint_sha256"] != previous_checkpoint_sha256:
        raise ExperimentBlocked("checkpoint chain predecessor mismatch")
    if type(checkpoint["resume_used"]) is not bool:
        raise ExperimentBlocked("checkpoint resume-used flag is invalid")
    revision = _positive_integer(
        checkpoint["resource_revision"], "checkpoint resource revision"
    )
    if revision > ledger["revision"]:
        raise ExperimentBlocked("checkpoint resource revision is unavailable")
    resource_event = ledger["events"][revision]
    resources = _normalize_resources(checkpoint["resource_use"])
    if resource_event["resources"] != resources:
        raise ExperimentBlocked("checkpoint resource prefix mismatch")
    if resource_event["reason"] != (
        f"complete-chunk-checkpoint-{expected_chunk_index + 1}"
    ):
        raise ExperimentBlocked("checkpoint resource event reason mismatch")
    if resources["optimizer_updates"] != expected_chunk_index + 1:
        raise ExperimentBlocked("checkpoint optimizer coordinate mismatch")
    if resources["environment_accesses"] < (
        expected_chunk_index + 1
    ) * EPISODES_PER_CHUNK:
        raise ExperimentBlocked("checkpoint episode resources are incomplete")
    if expected_chunk_index not in journal["completed_chunk_indices"]:
        raise ExperimentBlocked("checkpoint lacks a complete journal chunk")
    checkpoint["resource_use"] = resources
    checkpoint["runtime_checkpoint"] = _validate_opaque_payload_binding(
        checkpoint["runtime_checkpoint"], "runtime checkpoint"
    )
    checkpoint["access_journal_prefix"] = _validate_journal_prefix_binding(
        checkpoint["access_journal_prefix"], output
    )
    try:
        journal_bytes = (output / ACCESS_JOURNAL_FILENAME).read_bytes()
    except OSError as exc:
        raise ExperimentBlocked(f"access journal cannot be read: {exc}") from exc
    prefix_size = checkpoint["access_journal_prefix"]["size_bytes"]
    checkpoint_journal = validate_access_journal_bytes(
        journal_bytes[:prefix_size],
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if (
        checkpoint_journal["pending_access"] is not None
        or expected_chunk_index not in checkpoint_journal["completed_chunk_indices"]
        or checkpoint["resume_used"] != checkpoint_journal["resume_used"]
    ):
        raise ExperimentBlocked("checkpoint access journal prefix is not complete")
    if (
        checkpoint_journal["primary_next_position"]
        != (expected_chunk_index + 1) * EPISODES_PER_CHUNK
        or checkpoint_journal["completed_chunk_indices"]
        != list(range(expected_chunk_index + 1))
        or resources["environment_accesses"]
        != checkpoint_journal["debited_accesses"]
    ):
        raise ExperimentBlocked("checkpoint journal/resource coordinate mismatch")
    if (
        checkpoint_journal["resume_failed"]
        or checkpoint_journal["terminal_access_failure"]
        or (
            checkpoint_journal["resume_mode"] == "replay_uncheckpointed_chunk"
            and not checkpoint_journal["resume_complete"]
        )
    ):
        raise ExperimentBlocked("checkpoint access journal prefix is terminal")
    checkpoint["chunk_evidence"] = _validate_chunk_evidence_binding(
        checkpoint["chunk_evidence"],
        output=output,
        chunk_index=expected_chunk_index,
        expected_runtime_checkpoint=checkpoint["runtime_checkpoint"],
    )
    digest = _digest(checkpoint["checkpoint_sha256"], "checkpoint identity")
    body = {
        key: item for key, item in checkpoint.items() if key != "checkpoint_sha256"
    }
    if digest != _canonical_digest(body):
        raise ExperimentBlocked("checkpoint identity mismatch")
    return checkpoint


def _checkpoint_inventory(output: Path) -> dict[str, Any]:
    directory = output / "checkpoints"
    if not directory.exists():
        return {
            "checkpoint_numbers": [],
            "directory": directory,
            "evidence_numbers": [],
            "names": [],
        }
    if not directory.is_dir() or directory.is_symlink():
        raise ExperimentBlocked("checkpoint directory is invalid")
    paths = list(directory.iterdir())
    names = sorted(path.name for path in paths)
    if any(path.is_dir() or path.is_symlink() for path in paths):
        raise ExperimentBlocked("checkpoint inventory contains a non-file")
    checkpoint_numbers = sorted(
        int(match.group(1))
        for name in names
        if (match := re.fullmatch(r"checkpoint_([0-9]{4})\.json", name))
    )
    evidence_numbers = sorted(
        int(match.group(1))
        for name in names
        if (match := re.fullmatch(r"chunk_([0-9]{4})_evidence\.json\.gz", name))
    )
    return {
        "checkpoint_numbers": checkpoint_numbers,
        "directory": directory,
        "evidence_numbers": evidence_numbers,
        "names": names,
    }


def _load_checkpoint_chain_prefix(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    checkpoint_count: int,
) -> list[dict[str, Any]]:
    count = _nonnegative_integer(checkpoint_count, "checkpoint prefix count")
    if count > CHUNK_COUNT:
        raise ExperimentBlocked("checkpoint prefix exceeds registration")
    bootstrap = load_bootstrap(
        output, registration=registration, identity=identity
    )
    ledger = load_resource_ledger(output, identity=identity)
    journal = load_access_journal(
        output, registration=registration, identity=identity
    )
    previous = bootstrap["bootstrap_sha256"]
    chain: list[dict[str, Any]] = []
    directory = output / "checkpoints"
    for chunk_index in range(count):
        number = chunk_index + 1
        checkpoint = _validate_checkpoint_envelope(
            _load_checkpoint_envelope(
                directory / f"checkpoint_{number:04d}.json"
            ),
            output=output,
            registration=registration,
            identity=identity,
            expected_chunk_index=chunk_index,
            previous_checkpoint_sha256=previous,
            ledger=ledger,
            journal=journal,
        )
        chain.append(checkpoint)
        previous = checkpoint["checkpoint_sha256"]
    return chain


def load_checkpoint_chain(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Validate every contiguous envelope, gzip payload, and resource prefix."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    inventory = _checkpoint_inventory(output)
    checkpoint_numbers = inventory["checkpoint_numbers"]
    evidence_numbers = inventory["evidence_numbers"]
    names = inventory["names"]
    expected_numbers = list(range(1, len(checkpoint_numbers) + 1))
    expected_names = sorted(
        name
        for number in expected_numbers
        for name in (
            f"checkpoint_{number:04d}.json",
            f"chunk_{number:04d}_evidence.json.gz",
        )
    )
    if (
        checkpoint_numbers != expected_numbers
        or evidence_numbers != expected_numbers
        or names != expected_names
        or len(expected_numbers) > CHUNK_COUNT
    ):
        raise ExperimentBlocked("checkpoint inventory is noncontiguous or ambiguous")
    return _load_checkpoint_chain_prefix(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
        checkpoint_count=len(expected_numbers),
    )


def _checkpoint_publication_recovery_state(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    inventory = _checkpoint_inventory(output)
    checkpoint_numbers = inventory["checkpoint_numbers"]
    evidence_numbers = inventory["evidence_numbers"]
    expected_checkpoint_numbers = list(range(1, len(checkpoint_numbers) + 1))
    orphan_number = len(checkpoint_numbers) + 1
    expected_evidence_numbers = list(range(1, orphan_number + 1))
    expected_names = sorted(
        [
            name
            for number in expected_checkpoint_numbers
            for name in (
                f"checkpoint_{number:04d}.json",
                f"chunk_{number:04d}_evidence.json.gz",
            )
        ]
        + [f"chunk_{orphan_number:04d}_evidence.json.gz"]
    )
    if (
        checkpoint_numbers != expected_checkpoint_numbers
        or evidence_numbers != expected_evidence_numbers
        or inventory["names"] != expected_names
        or orphan_number > CHUNK_COUNT
    ):
        raise ExperimentBlocked("checkpoint recovery inventory is ambiguous")
    chain = _load_checkpoint_chain_prefix(
        output,
        registration=registration,
        identity=identity,
        checkpoint_count=len(checkpoint_numbers),
    )
    chunk_index = len(chain)
    journal = load_access_journal(
        output, registration=registration, identity=identity
    )
    if (
        journal["pending_access"] is not None
        or journal["resume_failed"]
        or journal["terminal_access_failure"]
        or journal["primary_next_position"]
        != (chunk_index + 1) * EPISODES_PER_CHUNK
        or journal["completed_chunk_indices"] != list(range(chunk_index + 1))
        or (
            journal["resume_mode"] == "replay_uncheckpointed_chunk"
            and not journal["resume_complete"]
        )
    ):
        raise ExperimentBlocked("checkpoint recovery journal is not complete")
    evidence_path = (
        inventory["directory"]
        / f"chunk_{orphan_number:04d}_evidence.json.gz"
    )
    try:
        stored = evidence_path.read_bytes()
    except OSError as exc:
        raise ExperimentBlocked("checkpoint recovery evidence cannot be read") from exc
    document, uncompressed = _decode_chunk_evidence_artifact(
        stored, chunk_index=chunk_index
    )
    evidence_binding, expected_stored = _chunk_evidence_artifact(
        chunk_index,
        document["evidence"],
        document["runtime_checkpoint"]["payload"],
    )
    if stored != expected_stored:
        raise ExperimentBlocked("checkpoint recovery evidence bytes mismatch")
    ledger = load_resource_ledger(output, identity=identity)
    reason = f"complete-chunk-checkpoint-{orphan_number}"
    matches = [
        event
        for event in ledger["events"][1:]
        if event["reason"] == reason
    ]
    if len(matches) != 1:
        raise ExperimentBlocked("checkpoint recovery resource event is ambiguous")
    resource_event = matches[0]
    revision = resource_event["revision"]
    previous_revision = chain[-1]["resource_revision"] if chain else 0
    if revision <= previous_revision:
        raise ExperimentBlocked("checkpoint recovery resource revision is stale")
    for later in ledger["events"][revision + 1 :]:
        if later["reason"] != "infrastructure-interruption-charge":
            raise ExperimentBlocked("checkpoint recovery has later resource activity")
        before = ledger["events"][later["revision"] - 1]["resources"]
        if any(
            later["resources"][name] != before[name]
            for name in _RESOURCE_FIELDS
            if name != "charged_seconds"
        ):
            raise ExperimentBlocked("checkpoint recovery charge changed other resources")
    resources = resource_event["resources"]
    if (
        resources["optimizer_updates"] != orphan_number
        or resources["environment_accesses"] != journal["debited_accesses"]
    ):
        raise ExperimentBlocked("checkpoint recovery resource coordinate mismatch")
    bootstrap = load_bootstrap(
        output, registration=registration, identity=identity
    )
    previous = (
        chain[-1]["checkpoint_sha256"]
        if chain
        else bootstrap["bootstrap_sha256"]
    )
    body = _checkpoint_body(
        registration=registration,
        identity=identity,
        chunk_index=chunk_index,
        previous_checkpoint_sha256=previous,
        resource_revision=revision,
        resource_use=resources,
        runtime_checkpoint_payload=document["runtime_checkpoint"]["payload"],
        chunk_evidence_binding=evidence_binding,
        journal_prefix=_journal_prefix_binding(output),
        resume_used=journal["resume_used"],
    )
    checkpoint = {**body, "checkpoint_sha256": _canonical_digest(body)}
    checkpoint_bytes = canonical_json_bytes(checkpoint)
    prior_resources = ledger["events"][revision - 1]["resources"]
    if (
        resources["stored_bytes"] - prior_resources["stored_bytes"]
        < len(stored) + len(checkpoint_bytes)
        or resources["uncompressed_bytes"]
        - prior_resources["uncompressed_bytes"]
        < len(uncompressed) + len(checkpoint_bytes)
    ):
        raise ExperimentBlocked("checkpoint recovery byte resources are insufficient")
    if max(len(stored), len(checkpoint_bytes)) > experiment_contract()["limits"][
        "max_artifact_bytes"
    ]:
        raise ExperimentBlocked("checkpoint recovery artifact exceeds its byte ceiling")
    return {
        "checkpoint": checkpoint,
        "checkpoint_bytes": checkpoint_bytes,
        "chunk_index": chunk_index,
    }


def recover_checkpoint_publication(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Complete one uniquely reconstructable evidence-first publication."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    state = _checkpoint_publication_recovery_state(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    checkpoint_relative, _evidence_relative = _checkpoint_relative_paths(
        state["chunk_index"]
    )
    _atomic_write_once(
        output / PurePosixPath(checkpoint_relative), state["checkpoint_bytes"]
    )
    return load_checkpoint_chain(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )[-1]


def publish_complete_chunk_checkpoint(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    chunk_index: int,
    resources: Mapping[str, Any],
    runtime_checkpoint_payload: Mapping[str, Any],
    chunk_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Advance resources first, then publish one complete contiguous checkpoint."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    index = _nonnegative_integer(chunk_index, "checkpoint chunk index")
    chain = load_checkpoint_chain(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if index != len(chain) or index >= CHUNK_COUNT:
        raise ExperimentBlocked("checkpoint is not the next complete chunk")
    journal = load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if index not in journal["completed_chunk_indices"]:
        raise ExperimentBlocked("checkpoint chunk is not complete")
    if (
        journal["resume_mode"] == "replay_uncheckpointed_chunk"
        and journal["resume_chunk_index"] == index
        and not journal["resume_complete"]
    ):
        raise ExperimentBlocked("checkpoint replay is incomplete")
    if (
        journal["pending_access"] is not None
        or journal["resume_failed"]
        or journal["terminal_access_failure"]
        or journal["primary_next_position"]
        != (index + 1) * EPISODES_PER_CHUNK
        or journal["completed_chunk_indices"] != list(range(index + 1))
    ):
        raise ExperimentBlocked("checkpoint journal coordinate is not complete")
    ledger = load_resource_ledger(output, identity=normalized_identity)
    normalized_resources = _normalize_resources(resources)
    if normalized_resources["optimizer_updates"] != index + 1:
        raise ExperimentBlocked("checkpoint optimizer coordinate mismatch")
    if any(
        normalized_resources[name] < ledger["resources"][name]
        for name in _RESOURCE_FIELDS
    ):
        raise ExperimentBlocked("checkpoint resources cannot roll back")
    evidence_binding, evidence_bytes = _chunk_evidence_artifact(
        index, chunk_evidence, runtime_checkpoint_payload
    )
    bootstrap = load_bootstrap(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    previous = (
        chain[-1]["checkpoint_sha256"]
        if chain
        else bootstrap["bootstrap_sha256"]
    )
    body = _checkpoint_body(
        registration=normalized_registration,
        identity=normalized_identity,
        chunk_index=index,
        previous_checkpoint_sha256=previous,
        resource_revision=ledger["revision"] + 1,
        resource_use=normalized_resources,
        runtime_checkpoint_payload=runtime_checkpoint_payload,
        chunk_evidence_binding=evidence_binding,
        journal_prefix=_journal_prefix_binding(output),
        resume_used=journal["resume_used"],
    )
    checkpoint = {**body, "checkpoint_sha256": _canonical_digest(body)}
    checkpoint_bytes = canonical_json_bytes(checkpoint)
    limits = experiment_contract()["limits"]
    if max(len(evidence_bytes), len(checkpoint_bytes)) > limits[
        "max_artifact_bytes"
    ]:
        raise ExperimentBlocked("checkpoint artifact exceeds its byte ceiling")
    if normalized_resources["stored_bytes"] - ledger["resources"][
        "stored_bytes"
    ] < len(evidence_bytes) + len(checkpoint_bytes):
        raise ExperimentBlocked("checkpoint stored-byte resource is insufficient")
    if normalized_resources["uncompressed_bytes"] - ledger["resources"][
        "uncompressed_bytes"
    ] < evidence_binding["uncompressed_size_bytes"] + len(checkpoint_bytes):
        raise ExperimentBlocked("checkpoint uncompressed-byte resource is insufficient")
    advanced = advance_resource_ledger(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
        lease=lease,
        resources=normalized_resources,
        reason=f"complete-chunk-checkpoint-{index + 1}",
    )
    if advanced["revision"] != body["resource_revision"]:
        raise ExperimentBlocked("checkpoint resource revision changed unexpectedly")
    checkpoint_relative, evidence_relative = _checkpoint_relative_paths(index)
    _atomic_write_once(output / PurePosixPath(evidence_relative), evidence_bytes)
    _atomic_write_once(output / PurePosixPath(checkpoint_relative), checkpoint_bytes)
    return load_checkpoint_chain(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )[-1]


def load_incomplete_chunk_resume_state(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Select only the latest complete checkpoint, or bootstrap for chunk zero."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    journal = load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if not journal["resume_used"] or journal["resume_chunk_index"] is None:
        raise ExperimentBlocked("resume state lacks a durable resume-used marker")
    mode = journal["resume_mode"]
    if mode not in {
        "continue_after_checkpoint",
        "replay_uncheckpointed_chunk",
    }:
        raise ExperimentBlocked("resume state mode is invalid")
    if journal["resume_failed"]:
        raise ExperimentBlocked("resume state is terminal")
    if mode == "replay_uncheckpointed_chunk" and journal["resume_complete"]:
        raise ExperimentBlocked("replay resume state is already complete")
    if mode == "continue_after_checkpoint" and not journal["resume_complete"]:
        raise ExperimentBlocked("checkpoint continuation marker is incomplete")
    resume_chunk = journal["resume_chunk_index"]
    chain = load_checkpoint_chain(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if len(chain) != resume_chunk:
        raise ExperimentBlocked("resume anchor is not the latest complete checkpoint")
    ledger = load_resource_ledger(output, identity=normalized_identity)
    if chain:
        anchor = chain[-1]
        source = "latest_complete_checkpoint"
        runtime_checkpoint = anchor["runtime_checkpoint"]
        checkpoint_resources = anchor["resource_use"]
        restored_chunk_index: int | None = anchor["chunk_index"]
    else:
        bootstrap = load_bootstrap(
            output,
            registration=normalized_registration,
            identity=normalized_identity,
        )
        source = "bootstrap"
        runtime_checkpoint = bootstrap["runtime_checkpoint"]
        checkpoint_resources = bootstrap["resource_use"]
        restored_chunk_index = None
    if any(
        ledger["resources"][name] < checkpoint_resources[name]
        for name in _RESOURCE_FIELDS
    ):
        raise ExperimentBlocked("resume resources roll back below their checkpoint")
    return {
        "checkpoint_resource_use": copy.deepcopy(checkpoint_resources),
        "resource_use": copy.deepcopy(ledger["resources"]),
        "restore_source": source,
        "restored_chunk_index": restored_chunk_index,
        "resume_chunk_index": resume_chunk,
        "resume_mode": mode,
        "resume_used": True,
        "runtime_checkpoint": copy.deepcopy(runtime_checkpoint),
    }


def _output_relative_files(output: Path) -> list[str]:
    files: list[str] = []
    try:
        candidates = sorted(output.rglob("*"))
    except OSError as exc:
        raise ExperimentBlocked(f"output inventory cannot be read: {exc}") from exc
    for path in candidates:
        if path.is_symlink():
            raise ExperimentBlocked("output inventory contains a symbolic link")
        if path.is_dir():
            continue
        relative = path.relative_to(output).as_posix()
        if path.name.startswith(".") and path.name.endswith(".tmp"):
            raise ExperimentBlocked("output inventory contains temporary publication")
        files.append(relative)
    return files


def _read_lease_payload(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExperimentBlocked(f"execution lease cannot be inspected: {exc}") from exc
    if not isinstance(value, dict) or raw != canonical_json_bytes(value):
        raise ExperimentBlocked("execution lease payload is not canonical")
    return _validate_lease_payload(value)


def classify_output_root(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    owner_alive: Callable[[int], bool] | None = None,
    expected_documents: Sequence[tuple[str, Mapping[str, Any]]] = (),
) -> dict[str, Any]:
    """Classify only exact initial, prestart, resume, or closeout roots."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    if not output.exists():
        return {
            "classification": "absent_root_initial",
            "owner_dead": None,
            "relative_files": [],
        }
    if not output.is_dir() or output.is_symlink():
        raise ExperimentBlocked("preexisting output root is not a plain directory")
    lease_path = output / LEASE_FILENAME
    if not lease_path.is_file() or lease_path.is_symlink():
        raise ExperimentBlocked("preexisting output root lacks an execution lease")
    lease_payload = _read_lease_payload(lease_path)
    if lease_payload["identity"] != normalized_identity:
        raise ExperimentBlocked("execution lease identity mismatch")
    liveness = owner_alive or _process_is_alive
    if liveness(lease_payload["owner"]["process_id"]):
        raise ExperimentBlocked("execution lease owner is still alive")
    files = _output_relative_files(output)
    static_names: set[str] = set()
    for filename, value in expected_documents:
        normalized_filename = _relative_source_path(
            filename, "static execution artifact path"
        )
        if "/" in normalized_filename or normalized_filename in static_names:
            raise ExperimentBlocked("static execution artifact inventory is invalid")
        static_names.add(normalized_filename)
        _publish_or_validate_document(
            output,
            normalized_filename,
            value,
            allow_existing=True,
        )
    setup_inventory = static_names | {LEASE_FILENAME}
    if static_names and set(files) == setup_inventory:
        return {
            "classification": "setup_before_bootstrap",
            "owner": lease_payload["owner"],
            "owner_dead": True,
            "relative_files": files,
        }
    base = {
        ACCESS_JOURNAL_FILENAME,
        BOOTSTRAP_FILENAME,
        LEASE_FILENAME,
        RESOURCE_LEDGER_FILENAME,
    } | static_names
    if not base.issubset(files):
        raise ExperimentBlocked("resume output inventory lacks required controls")
    if TERMINAL_INTENT_FILENAME in files:
        intent = load_terminal_intent(
            output,
            registration=normalized_registration,
            identity=normalized_identity,
        )
        terminal_present = TERMINAL_FILENAME in files
        manifest_present = MANIFEST_FILENAME in files
        if manifest_present:
            if not terminal_present:
                raise ExperimentBlocked("terminal manifest exists without terminal")
            validate_terminal_bundle(
                output,
                registration=normalized_registration,
                identity=normalized_identity,
            )
            return {
                "classification": "existing_terminal",
                "owner": lease_payload["owner"],
                "owner_dead": True,
                "relative_files": files,
            }
        if terminal_present:
            expected_terminal = _expected_terminal_document(
                output,
                registration=normalized_registration,
                identity=normalized_identity,
            )
            _publish_or_validate_document(
                output,
                TERMINAL_FILENAME,
                expected_terminal,
                allow_existing=True,
            )
        prefix_paths = {
            row["path"]
            for row in intent["artifact_prefix_inventory"]["artifacts"]
        }
        expected = prefix_paths | {LEASE_FILENAME, TERMINAL_INTENT_FILENAME}
        if terminal_present:
            expected.add(TERMINAL_FILENAME)
        if set(files) != expected:
            raise ExperimentBlocked("terminal recovery output inventory mismatch")
        return {
            "classification": "terminal_publication_recovery",
            "owner": lease_payload["owner"],
            "owner_dead": True,
            "relative_files": files,
        }
    if TERMINAL_FILENAME in files or MANIFEST_FILENAME in files:
        raise ExperimentBlocked("terminal output lacks its durable intent")
    journal = load_access_journal(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    checkpoint_inventory = _checkpoint_inventory(output)
    if len(checkpoint_inventory["evidence_numbers"]) == (
        len(checkpoint_inventory["checkpoint_numbers"]) + 1
    ):
        recovery = _checkpoint_publication_recovery_state(
            output,
            registration=normalized_registration,
            identity=normalized_identity,
        )
        expected = set(base)
        for chunk_index in range(recovery["chunk_index"]):
            checkpoint_path, evidence_path = _checkpoint_relative_paths(chunk_index)
            expected.update({checkpoint_path, evidence_path})
        _checkpoint_path, orphan_evidence_path = _checkpoint_relative_paths(
            recovery["chunk_index"]
        )
        expected.add(orphan_evidence_path)
        if set(files) != expected:
            raise ExperimentBlocked("checkpoint recovery output inventory mismatch")
        return {
            "classification": "checkpoint_publication_recovery",
            "owner": lease_payload["owner"],
            "owner_dead": True,
            "relative_files": files,
            "recovery_chunk_index": recovery["chunk_index"],
        }
    chain = load_checkpoint_chain(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    expected = set(base)
    for chunk_index in range(len(chain)):
        checkpoint_path, evidence_path = _checkpoint_relative_paths(chunk_index)
        expected.update({checkpoint_path, evidence_path})
    if set(files) != expected:
        raise ExperimentBlocked("resume output inventory mismatch")
    if journal["debited_accesses"] == 0:
        if chain or journal["resume_used"]:
            raise ExperimentBlocked("zero-access output contains empirical state")
        return {
            "classification": "initialized_before_seed",
            "owner": lease_payload["owner"],
            "owner_dead": True,
            "relative_files": files,
        }
    if journal["resume_used"]:
        raise ExperimentBlocked("output root has already consumed its one resume")
    checkpoint_count = len(chain)
    if (
        checkpoint_count == CHUNK_COUNT
        and journal["completed_chunk_indices"] == list(range(CHUNK_COUNT))
        and journal["pending_access"] is None
    ):
        return {
            "classification": "complete_checkpoint_prefix",
            "owner": lease_payload["owner"],
            "owner_dead": True,
            "relative_files": files,
        }
    primary_position = journal["primary_next_position"]
    resume_chunk = journal["resume_candidate_chunk_index"]
    if resume_chunk is None:
        if primary_position < checkpoint_count * EPISODES_PER_CHUNK:
            raise ExperimentBlocked("resume journal precedes its checkpoint prefix")
        if checkpoint_count >= CHUNK_COUNT:
            raise ExperimentBlocked("resume exceeds the registered chunk schedule")
        resume_chunk = checkpoint_count
    if checkpoint_count != resume_chunk:
        raise ExperimentBlocked("resume output lacks its latest complete checkpoint")
    return {
        "classification": "incomplete_chunk_resume",
        "owner": lease_payload["owner"],
        "owner_dead": True,
        "relative_files": files,
        "resume_chunk_index": resume_chunk,
    }


def classified_execution_lease(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    owner_alive: Callable[[int], bool] | None = None,
    expected_documents: Sequence[tuple[str, Mapping[str, Any]]] = (),
) -> ExecutionLease:
    """Return a lease configured only after the output root classifies exactly."""
    classification = classify_output_root(
        output_path,
        registration=registration,
        identity=identity,
        owner_alive=owner_alive,
        expected_documents=expected_documents,
    )
    lease = ExecutionLease(
        output_path,
        identity=identity,
        allow_stale_reclaim=(
            classification["classification"] != "absent_root_initial"
        ),
        owner_alive=owner_alive,
    )
    lease.root_classification = classification
    return lease


def terminal_verdicts() -> tuple[str, ...]:
    """Return the only terminal classifications this mechanism identity may use."""
    return _TERMINAL_VERDICTS


def _terminal_verdict(value: object) -> str:
    verdict = _nonempty_string(value, "terminal verdict")
    if verdict not in _TERMINAL_VERDICTS:
        raise ExperimentBlocked("terminal verdict is not registered")
    return verdict


def validate_artifact_inventory(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate canonical artifact rows and immutable per-file/aggregate ceilings."""
    inventory = _copy_mapping(value, "artifact inventory")
    _require_fields(
        inventory,
        {"artifacts", "stored_size_bytes", "uncompressed_size_bytes"},
        "artifact inventory",
    )
    rows = inventory["artifacts"]
    if not isinstance(rows, list):
        raise ExperimentBlocked("artifact inventory rows must be a list")
    normalized_rows: list[dict[str, Any]] = []
    paths: list[str] = []
    stored_total = 0
    uncompressed_total = 0
    limits = experiment_contract()["limits"]
    for row in rows:
        artifact = _copy_mapping(row, "artifact inventory row")
        _require_fields(
            artifact,
            {
                "encoding",
                "path",
                "stored_sha256",
                "stored_size_bytes",
                "uncompressed_sha256",
                "uncompressed_size_bytes",
            },
            "artifact inventory row",
        )
        artifact["path"] = _relative_source_path(
            artifact["path"], "artifact inventory path"
        )
        if artifact["encoding"] not in {
            "identity-bytes-v1",
            "deterministic-gzip-v1",
        }:
            raise ExperimentBlocked("artifact inventory encoding is invalid")
        for field in ("stored_sha256", "uncompressed_sha256"):
            _digest(artifact[field], f"artifact {field}")
        for field in ("stored_size_bytes", "uncompressed_size_bytes"):
            artifact[field] = _nonnegative_integer(
                artifact[field], f"artifact {field}"
            )
        if max(
            artifact["stored_size_bytes"], artifact["uncompressed_size_bytes"]
        ) > limits["max_artifact_bytes"]:
            raise ExperimentBlocked("managed artifact exceeds its byte ceiling")
        paths.append(artifact["path"])
        stored_total += artifact["stored_size_bytes"]
        uncompressed_total += artifact["uncompressed_size_bytes"]
        normalized_rows.append(artifact)
    if paths != sorted(set(paths)):
        raise ExperimentBlocked("artifact inventory paths must be unique and sorted")
    if (
        inventory["stored_size_bytes"] != stored_total
        or inventory["uncompressed_size_bytes"] != uncompressed_total
    ):
        raise ExperimentBlocked("artifact inventory totals mismatch")
    if stored_total > limits["max_stored_bytes"]:
        raise ExperimentBlocked("managed stored-byte ceiling exceeded")
    if uncompressed_total > limits["max_uncompressed_bytes"]:
        raise ExperimentBlocked("managed uncompressed-byte ceiling exceeded")
    inventory["artifacts"] = normalized_rows
    return inventory


def build_managed_artifact_inventory(
    output_path: Path | str,
    *,
    excluded_paths: Sequence[str] = (),
) -> dict[str, Any]:
    """Observe bounded managed bytes without treating the persistent lease as evidence."""
    output = Path(output_path).resolve()
    excluded = {
        _relative_source_path(path, "excluded artifact path")
        for path in excluded_paths
    }
    excluded.add(LEASE_FILENAME)
    rows: list[dict[str, Any]] = []
    for relative in _output_relative_files(output):
        if relative in excluded:
            continue
        path = output / PurePosixPath(relative)
        try:
            stored = path.read_bytes()
            if relative.endswith(".gz"):
                uncompressed = gzip.decompress(stored)
                encoding = "deterministic-gzip-v1"
            else:
                uncompressed = stored
                encoding = "identity-bytes-v1"
        except (OSError, EOFError, gzip.BadGzipFile) as exc:
            raise ExperimentBlocked(f"managed artifact cannot be read: {relative}") from exc
        rows.append(
            {
                "encoding": encoding,
                "path": relative,
                "stored_sha256": hashlib.sha256(stored).hexdigest(),
                "stored_size_bytes": len(stored),
                "uncompressed_sha256": hashlib.sha256(uncompressed).hexdigest(),
                "uncompressed_size_bytes": len(uncompressed),
            }
        )
    rows.sort(key=lambda row: row["path"])
    return validate_artifact_inventory(
        {
            "artifacts": rows,
            "stored_size_bytes": sum(row["stored_size_bytes"] for row in rows),
            "uncompressed_size_bytes": sum(
                row["uncompressed_size_bytes"] for row in rows
            ),
        }
    )


def _terminal_state(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    journal = load_access_journal(
        output,
        registration=registration,
        identity=identity,
    )
    ledger = load_resource_ledger(output, identity=identity)
    chain = load_checkpoint_chain(
        output,
        registration=registration,
        identity=identity,
    )
    return journal, ledger, chain


def _validate_terminal_state(
    verdict: str,
    *,
    journal: Mapping[str, Any],
    ledger: Mapping[str, Any],
    chain: Sequence[Mapping[str, Any]],
) -> None:
    normalized_verdict = _terminal_verdict(verdict)
    completed_chunks = journal["completed_chunk_indices"]
    pending = journal["pending_access"]
    if normalized_verdict == "experiment_blocked_before_seed_access":
        if (
            journal["debited_accesses"] != 0
            or pending is not None
            or chain
            or ledger["resources"] != _zero_resources()
        ):
            raise ExperimentBlocked("prestart verdict contains empirical evidence")
        return
    if normalized_verdict == (
        "experiment_completed_with_cross_fitted_mechanism_evidence"
    ):
        if (
            completed_chunks != list(range(CHUNK_COUNT))
            or len(chain) != CHUNK_COUNT
            or journal["primary_next_position"]
            != len(chain) * EPISODES_PER_CHUNK
            or journal["resume_candidate_chunk_index"] is not None
            or pending is not None
            or journal["resume_failed"]
            or journal["terminal_access_failure"]
            or (journal["resume_used"] and not journal["resume_complete"])
        ):
            raise ExperimentBlocked("completion verdict lacks eight complete chunks")
        return
    if normalized_verdict == (
        "experiment_stopped_during_training_for_family_saturation"
    ):
        if (
            len(chain) < 4
            or completed_chunks[: len(chain)] != list(range(len(chain)))
            or journal["primary_next_position"]
            != len(chain) * EPISODES_PER_CHUNK
            or journal["resume_candidate_chunk_index"] is not None
            or pending is not None
            or journal["resume_failed"]
            or journal["terminal_access_failure"]
            or (journal["resume_used"] and not journal["resume_complete"])
        ):
            raise ExperimentBlocked(
                "family-saturation verdict is not at its checkpoint boundary"
            )
        return
    if journal["debited_accesses"] == 0:
        raise ExperimentBlocked("post-start failure lacks a durable access debit")


def _terminal_prefix_inventory(output: Path) -> dict[str, Any]:
    return build_managed_artifact_inventory(
        output,
        excluded_paths=(
            MANIFEST_FILENAME,
            TERMINAL_FILENAME,
            TERMINAL_INTENT_FILENAME,
        ),
    )


def publish_terminal_intent(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    verdict: str,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    """Freeze one terminal classification and all durable prefixes before closeout."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    for name in (TERMINAL_INTENT_FILENAME, TERMINAL_FILENAME, MANIFEST_FILENAME):
        if (output / name).exists():
            raise ExperimentBlocked("terminal publication already started")
    journal, ledger, chain = _terminal_state(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    normalized_verdict = _terminal_verdict(verdict)
    _validate_terminal_state(
        normalized_verdict,
        journal=journal,
        ledger=ledger,
        chain=chain,
    )
    prefix_inventory = _terminal_prefix_inventory(output)
    body = {
        "artifact_prefix_inventory": prefix_inventory,
        "authority": registration_authority(),
        "checkpoint_sha256s": [
            checkpoint["checkpoint_sha256"] for checkpoint in chain
        ],
        "details": _copy_mapping(details, "terminal details"),
        "identity": normalized_identity,
        "journal_prefix": _journal_prefix_binding(output),
        "registration_sha256": registration_sha256(normalized_registration),
        "resource_revision": ledger["revision"],
        "resource_use": copy.deepcopy(ledger["resources"]),
        "schema_version": TERMINAL_INTENT_SCHEMA_VERSION,
        "verdict": normalized_verdict,
    }
    intent = {**body, "terminal_intent_sha256": _canonical_digest(body)}
    _atomic_write_once(
        output / TERMINAL_INTENT_FILENAME,
        canonical_json_bytes(intent),
    )
    return intent


def load_terminal_intent(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    intent = _load_canonical_json_file(
        output / TERMINAL_INTENT_FILENAME,
        "terminal intent",
    )
    _require_fields(
        intent,
        {
            "artifact_prefix_inventory",
            "authority",
            "checkpoint_sha256s",
            "details",
            "identity",
            "journal_prefix",
            "registration_sha256",
            "resource_revision",
            "resource_use",
            "schema_version",
            "terminal_intent_sha256",
            "verdict",
        },
        "terminal intent",
    )
    if intent["schema_version"] != TERMINAL_INTENT_SCHEMA_VERSION:
        raise ExperimentBlocked("terminal intent schema mismatch")
    if (
        intent["identity"] != normalized_identity
        or intent["registration_sha256"]
        != registration_sha256(normalized_registration)
        or intent["authority"] != registration_authority()
    ):
        raise ExperimentBlocked("terminal intent identity or authority mismatch")
    _copy_mapping(intent["details"], "terminal details")
    _validate_journal_prefix_binding(intent["journal_prefix"], output)
    journal, ledger, chain = _terminal_state(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if (
        intent["resource_revision"] != ledger["revision"]
        or intent["resource_use"] != ledger["resources"]
        or intent["checkpoint_sha256s"]
        != [checkpoint["checkpoint_sha256"] for checkpoint in chain]
        or intent["artifact_prefix_inventory"] != _terminal_prefix_inventory(output)
    ):
        raise ExperimentBlocked("terminal intent durable prefix mismatch")
    _validate_terminal_state(
        intent["verdict"],
        journal=journal,
        ledger=ledger,
        chain=chain,
    )
    digest = _digest(intent["terminal_intent_sha256"], "terminal intent identity")
    body = {
        key: item
        for key, item in intent.items()
        if key != "terminal_intent_sha256"
    }
    if digest != _canonical_digest(body):
        raise ExperimentBlocked("terminal intent identity mismatch")
    return intent


def _expected_terminal_document(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    intent = load_terminal_intent(
        output,
        registration=registration,
        identity=identity,
    )
    journal, ledger, chain = _terminal_state(
        output,
        registration=registration,
        identity=identity,
    )
    body = {
        "authority": registration_authority(),
        "checkpoint_count": len(chain),
        "completed_chunk_indices": journal["completed_chunk_indices"],
        "details": copy.deepcopy(intent["details"]),
        "identity": _validate_execution_identity(identity),
        "registration_sha256": registration_sha256(registration),
        "resource_use": copy.deepcopy(ledger["resources"]),
        "resume_used": journal["resume_used"],
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "terminal_intent_sha256": intent["terminal_intent_sha256"],
        "verdict": intent["verdict"],
    }
    return {**body, "terminal_sha256": _canonical_digest(body)}


def publish_terminal_bundle(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Publish terminal bytes and write the closed artifact manifest last."""
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    _require_execution_lease(lease, output, normalized_identity)
    if (output / MANIFEST_FILENAME).exists() and not (
        output / TERMINAL_FILENAME
    ).exists():
        raise ExperimentBlocked("terminal manifest exists without terminal")
    terminal = _expected_terminal_document(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    terminal_bytes = canonical_json_bytes(terminal)
    if len(terminal_bytes) > experiment_contract()["limits"]["max_artifact_bytes"]:
        raise ExperimentBlocked("terminal exceeds the artifact byte ceiling")
    _publish_or_validate_document(
        output,
        TERMINAL_FILENAME,
        terminal,
        allow_existing=(output / TERMINAL_FILENAME).exists(),
    )
    inventory = build_managed_artifact_inventory(
        output,
        excluded_paths=(MANIFEST_FILENAME,),
    )
    manifest_body = {
        "artifact_inventory": inventory,
        "authority": registration_authority(),
        "identity": normalized_identity,
        "registration_sha256": registration_sha256(normalized_registration),
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "terminal_sha256": terminal["terminal_sha256"],
    }
    manifest = {**manifest_body, "manifest_sha256": _canonical_digest(manifest_body)}
    manifest_bytes = canonical_json_bytes(manifest)
    limits = experiment_contract()["limits"]
    if len(manifest_bytes) > limits["max_artifact_bytes"]:
        raise ExperimentBlocked("manifest exceeds the artifact byte ceiling")
    if inventory["stored_size_bytes"] + len(manifest_bytes) > limits[
        "max_stored_bytes"
    ]:
        raise ExperimentBlocked("manifest would exceed the stored-byte ceiling")
    if inventory["uncompressed_size_bytes"] + len(manifest_bytes) > limits[
        "max_uncompressed_bytes"
    ]:
        raise ExperimentBlocked("manifest would exceed the uncompressed-byte ceiling")
    _publish_or_validate_document(
        output,
        MANIFEST_FILENAME,
        manifest,
        allow_existing=(output / MANIFEST_FILENAME).exists(),
    )
    return {"manifest": manifest, "terminal": terminal}


def validate_terminal_bundle(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_registration, normalized_identity, output = _registration_for_output(
        registration, identity, output_path
    )
    terminal = _load_canonical_json_file(output / TERMINAL_FILENAME, "terminal")
    manifest = _load_canonical_json_file(output / MANIFEST_FILENAME, "manifest")
    _require_fields(
        terminal,
        {
            "authority",
            "checkpoint_count",
            "completed_chunk_indices",
            "details",
            "identity",
            "registration_sha256",
            "resource_use",
            "resume_used",
            "schema_version",
            "terminal_intent_sha256",
            "terminal_sha256",
            "verdict",
        },
        "terminal",
    )
    _require_fields(
        manifest,
        {
            "artifact_inventory",
            "authority",
            "identity",
            "manifest_sha256",
            "registration_sha256",
            "schema_version",
            "terminal_sha256",
        },
        "manifest",
    )
    if (
        terminal["schema_version"] != TERMINAL_SCHEMA_VERSION
        or manifest["schema_version"] != MANIFEST_SCHEMA_VERSION
        or terminal["identity"] != normalized_identity
        or manifest["identity"] != normalized_identity
        or terminal["authority"] != registration_authority()
        or manifest["authority"] != registration_authority()
        or terminal["registration_sha256"]
        != registration_sha256(normalized_registration)
        or manifest["registration_sha256"]
        != registration_sha256(normalized_registration)
    ):
        raise ExperimentBlocked("terminal bundle identity or authority mismatch")
    terminal_digest = _digest(terminal["terminal_sha256"], "terminal identity")
    terminal_body = {
        key: item for key, item in terminal.items() if key != "terminal_sha256"
    }
    if terminal_digest != _canonical_digest(terminal_body):
        raise ExperimentBlocked("terminal identity mismatch")
    manifest_digest = _digest(manifest["manifest_sha256"], "manifest identity")
    manifest_body = {
        key: item for key, item in manifest.items() if key != "manifest_sha256"
    }
    if manifest_digest != _canonical_digest(manifest_body):
        raise ExperimentBlocked("manifest identity mismatch")
    observed_inventory = build_managed_artifact_inventory(
        output,
        excluded_paths=(MANIFEST_FILENAME,),
    )
    if (
        manifest["artifact_inventory"] != observed_inventory
        or manifest["terminal_sha256"] != terminal_digest
    ):
        raise ExperimentBlocked("terminal manifest inventory mismatch")
    intent = load_terminal_intent(
        output,
        registration=normalized_registration,
        identity=normalized_identity,
    )
    if (
        terminal["terminal_intent_sha256"] != intent["terminal_intent_sha256"]
        or terminal["verdict"] != intent["verdict"]
    ):
        raise ExperimentBlocked("terminal differs from its intent")
    return {"manifest": manifest, "terminal": terminal}


def _validate_source_preflight_report(
    value: object, registration: Mapping[str, Any]
) -> dict[str, Any]:
    report = _copy_mapping(value, "source preflight report")
    _require_fields(
        report,
        {"checks", "registration_sha256", "repository_commit", "schema_version"},
        "source preflight report",
    )
    normalized = validate_registration(registration)
    if (
        report["schema_version"] != SOURCE_PREFLIGHT_SCHEMA_VERSION
        or report["registration_sha256"] != registration_sha256(normalized)
        or report["repository_commit"] != normalized["repository_commit"]
    ):
        raise ExperimentBlocked("source preflight report identity mismatch")
    checks = _copy_mapping(report["checks"], "source preflight checks")
    expected_checks = {
        "communication_mod_unchanged",
        "native_module_unchanged",
        "production_checkpoints_unchanged",
        "pushed_source_exact",
        "runtime_identity_exact",
        "source_inventory_exact",
        "tracked_worktree_clean",
    }
    _require_fields(checks, expected_checks, "source preflight checks")
    if any(value is not True for value in checks.values()):
        raise ExperimentBlocked("source preflight report contains a failed check")
    report["checks"] = checks
    return report


def _observe_isolation(
    registration: Mapping[str, Any],
    *,
    phase: str,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None,
) -> dict[str, Any]:
    normalized = validate_registration(registration)
    if phase not in {"post", "pre"}:
        raise ExperimentBlocked("isolation observation phase is invalid")
    expected = normalized["isolation_identity"]
    binding_observer = external_binding_observer or external_file_binding
    checkpoint_observer = (
        checkpoint_snapshot_observer or snapshot_production_checkpoints
    )
    observed = {
        "communication_mod_config": _validate_file_binding(
            binding_observer(expected["communication_mod_config"]["path"]),
            f"{phase} CommunicationMod configuration",
        ),
        "production_checkpoints": _validate_checkpoint_tree_identity(
            checkpoint_observer(expected["production_checkpoints"]["root"])
        ),
    }
    return {
        "isolation_identity": observed,
        "matches_registration": observed == expected,
        "phase": phase,
        "registration_sha256": registration_sha256(normalized),
        "schema_version": ISOLATION_OBSERVATION_SCHEMA_VERSION,
    }


def _publish_or_validate_document(
    output: Path,
    filename: str,
    value: Mapping[str, Any],
    *,
    allow_existing: bool,
) -> None:
    payload = canonical_json_bytes(dict(value))
    path = output / filename
    if path.exists():
        if not allow_existing:
            raise ExperimentBlocked(f"execution artifact already exists: {filename}")
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise ExperimentBlocked(
                f"execution artifact cannot be read: {filename}"
            ) from exc
        if existing != payload:
            raise ExperimentBlocked(f"execution artifact identity mismatch: {filename}")
        return
    if allow_existing:
        raise ExperimentBlocked(f"execution artifact is missing: {filename}")
    _atomic_write_once(path, payload)


def _static_execution_documents(
    *,
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    approval: Mapping[str, Any],
    authorization: Mapping[str, Any],
    preflight: Mapping[str, Any],
    pre_isolation: Mapping[str, Any],
) -> tuple[tuple[str, dict[str, Any]], ...]:
    return (
        (REGISTRATION_FILENAME, copy.deepcopy(dict(registration))),
        (EXECUTION_REQUEST_FILENAME, copy.deepcopy(dict(request))),
        (EXTERNAL_APPROVAL_FILENAME, copy.deepcopy(dict(approval))),
        (AUTHORIZATION_FILENAME, copy.deepcopy(dict(authorization))),
        (SOURCE_PREFLIGHT_FILENAME, copy.deepcopy(dict(preflight))),
        (PRE_ISOLATION_FILENAME, copy.deepcopy(dict(pre_isolation))),
    )


def _load_completed_chunk_evidence(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> list[dict[str, Any]]:
    chain = load_checkpoint_chain(
        output, registration=registration, identity=identity
    )
    chunks: list[dict[str, Any]] = []
    for checkpoint in chain:
        path = output / PurePosixPath(checkpoint["chunk_evidence"]["path"])
        try:
            stored = path.read_bytes()
        except OSError as exc:
            raise ExperimentBlocked("completed chunk evidence cannot be loaded") from exc
        document, _uncompressed = _decode_chunk_evidence_artifact(
            stored, chunk_index=checkpoint["chunk_index"]
        )
        if document["runtime_checkpoint"] != checkpoint["runtime_checkpoint"]:
            raise ExperimentBlocked("completed chunk runtime checkpoint mismatch")
        chunks.append(_copy_mapping(document["evidence"], "completed chunk evidence"))
    return chunks


def _exact_checkpoint_resources(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    runtime_state: Any,
    runtime_checkpoint_payload: Mapping[str, Any],
    chunk_evidence: Mapping[str, Any],
    chunk_index: int,
    charged_seconds: float,
) -> dict[str, int | float]:
    ledger = load_resource_ledger(output, identity=identity)
    journal = load_access_journal(
        output, registration=registration, identity=identity
    )
    chain = load_checkpoint_chain(
        output, registration=registration, identity=identity
    )
    if len(chain) != chunk_index:
        raise ExperimentBlocked("checkpoint resource calculation is out of sequence")
    bootstrap = load_bootstrap(
        output, registration=registration, identity=identity
    )
    previous = (
        chain[-1]["checkpoint_sha256"]
        if chain
        else bootstrap["bootstrap_sha256"]
    )
    evidence_binding, evidence_bytes = _chunk_evidence_artifact(
        chunk_index, chunk_evidence, runtime_checkpoint_payload
    )
    try:
        optimizer_updates = int(runtime_state.optimizer_updates)
        retained_decisions = int(runtime_state.completed_decisions)
        next_chunk_index = int(runtime_state.next_chunk_index)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ExperimentBlocked("runtime resource coordinates are invalid") from exc
    if (
        optimizer_updates != chunk_index + 1
        or next_chunk_index != chunk_index + 1
        or retained_decisions < 0
    ):
        raise ExperimentBlocked("runtime checkpoint coordinates differ from chunk")
    resources = copy.deepcopy(ledger["resources"])
    resources["charged_seconds"] = max(
        float(resources["charged_seconds"]), float(charged_seconds)
    )
    resources["environment_accesses"] = journal["debited_accesses"]
    resources["optimizer_updates"] = optimizer_updates
    resources["retained_decisions"] = retained_decisions
    checkpoint_size = 0
    for _iteration in range(16):
        resources["stored_bytes"] = (
            ledger["resources"]["stored_bytes"]
            + len(evidence_bytes)
            + checkpoint_size
        )
        resources["uncompressed_bytes"] = (
            ledger["resources"]["uncompressed_bytes"]
            + evidence_binding["uncompressed_size_bytes"]
            + checkpoint_size
        )
        resources = _normalize_resources(resources)
        body = _checkpoint_body(
            registration=registration,
            identity=identity,
            chunk_index=chunk_index,
            previous_checkpoint_sha256=previous,
            resource_revision=ledger["revision"] + 1,
            resource_use=resources,
            runtime_checkpoint_payload=runtime_checkpoint_payload,
            chunk_evidence_binding=evidence_binding,
            journal_prefix=_journal_prefix_binding(output),
            resume_used=journal["resume_used"],
        )
        encoded = canonical_json_bytes(
            {**body, "checkpoint_sha256": _canonical_digest(body)}
        )
        if len(encoded) == checkpoint_size:
            return resources
        checkpoint_size = len(encoded)
    raise ExperimentBlocked("checkpoint byte accounting did not converge")


def _is_infrastructure_interruption(exc: BaseException) -> bool:
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, (KeyboardInterrupt, OSError, SystemExit, TimeoutError)):
            return True
        cause = current.__cause__ or current.__context__
        current = cause if isinstance(cause, BaseException) else None
    return False


def _charge_infrastructure_interruption(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    attempt_started: float,
    charged_origin: float,
    clock: Callable[[], float],
) -> dict[str, Any]:
    observed_at = float(clock())
    elapsed = observed_at - attempt_started
    if not math.isfinite(observed_at) or not math.isfinite(elapsed) or elapsed < 0.0:
        raise ExperimentBlocked("execution clock moved backwards")
    journal = load_access_journal(
        output, registration=registration, identity=identity
    )
    ledger = load_resource_ledger(output, identity=identity)
    resources = copy.deepcopy(ledger["resources"])
    resources["charged_seconds"] = min(
        float(experiment_contract()["limits"]["max_charged_seconds"]),
        max(
            float(resources["charged_seconds"]),
            float(charged_origin) + elapsed,
        ),
    )
    resources["environment_accesses"] = max(
        int(resources["environment_accesses"]),
        int(journal["debited_accesses"]),
    )
    if resources == ledger["resources"]:
        return ledger
    return advance_resource_ledger(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
        resources=resources,
        reason="infrastructure-interruption-charge",
    )


def _failure_witness(
    exc: BaseException, *, phase: str, infrastructure: bool
) -> dict[str, Any]:
    if phase not in {"bootstrap", "terminal", "training"}:
        raise ExperimentBlocked("failure phase is invalid")
    body = {
        "exception_type": type(exc).__name__,
        "infrastructure": infrastructure,
        "message": str(exc),
        "phase": phase,
        "schema_version": FAILURE_WITNESS_SCHEMA_VERSION,
    }
    return {**body, "failure_sha256": _canonical_digest(body)}


def _publish_post_isolation(
    output: Path,
    *,
    registration: Mapping[str, Any],
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None,
) -> dict[str, Any]:
    observation = _observe_isolation(
        registration,
        phase="post",
        external_binding_observer=external_binding_observer,
        checkpoint_snapshot_observer=checkpoint_snapshot_observer,
    )
    _publish_or_validate_document(
        output,
        POST_ISOLATION_FILENAME,
        observation,
        allow_existing=(output / POST_ISOLATION_FILENAME).exists(),
    )
    return observation


def _close_runner_terminal(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    verdict: str,
    saturation: Mapping[str, Any],
    failure: Mapping[str, Any] | None,
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    details = {
        "evaluation": None,
        "failure": copy.deepcopy(dict(failure)) if failure is not None else None,
        "saturation": copy.deepcopy(dict(saturation)),
    }
    publish_terminal_intent(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
        verdict=verdict,
        details=details,
    )
    bundle = publish_terminal_bundle(
        output,
        registration=registration,
        identity=identity,
        lease=lease,
    )
    return {
        "identity": copy.deepcopy(dict(identity)),
        "manifest": bundle["manifest"],
        "preflight": copy.deepcopy(dict(preflight)),
        "status": "terminal",
        "terminal": bundle["terminal"],
    }


def _post_isolation_mismatch_result(
    *,
    identity: Mapping[str, Any],
    observation: Mapping[str, Any],
    preflight: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "identity": copy.deepcopy(dict(identity)),
        "post_isolation": copy.deepcopy(dict(observation)),
        "preflight": copy.deepcopy(dict(preflight)),
        "status": "post_isolation_mismatch",
    }


def execute_authorized_experiment(
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval: Mapping[str, Any] | None,
    *,
    repo_root: Path | str | None = None,
    git_text: Callable[..., str] | None = None,
    source_inventory_observer: Callable[[Path], Mapping[str, Any]] | None = None,
    runtime_identity_observer: Callable[[], Mapping[str, Any]] | None = None,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None = None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
    module_importer: Callable[[str], Any] | None = None,
    module_registry: Mapping[str, Any] | None = None,
    clock: Callable[[], float] = time.monotonic,
    owner_alive: Callable[[int], bool] | None = None,
) -> dict[str, Any]:
    """Execute only the exact approved training schedule and close its bundle."""
    normalized_registration = validate_registration(registration)
    normalized_request = validate_exact_execution_request(
        request, normalized_registration
    )
    if approval is None:
        raise ExperimentBlocked("exact external approval is required")
    normalized_approval = validate_external_approval(
        approval, normalized_registration, normalized_request
    )
    normalized_authorization = validate_execution_authorization(
        authorization,
        normalized_registration,
        normalized_request,
        normalized_approval,
    )
    identity = execution_identity(
        normalized_registration,
        normalized_request,
        normalized_authorization,
        normalized_approval,
    )
    output = Path(normalized_registration["output_root"]).resolve()
    if (output / TERMINAL_FILENAME).is_file() and (output / MANIFEST_FILENAME).is_file():
        bundle = validate_terminal_bundle(
            output, registration=normalized_registration, identity=identity
        )
        return {
            "identity": identity,
            "manifest": bundle["manifest"],
            "preflight": None,
            "status": "existing_terminal",
            "terminal": bundle["terminal"],
        }

    root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
    preflight = _validate_source_preflight_report(
        source_only_preflight(
            root,
            normalized_registration,
            normalized_request,
            normalized_authorization,
            normalized_approval,
            git_text=git_text,
            source_inventory_observer=source_inventory_observer,
            runtime_identity_observer=runtime_identity_observer,
            external_binding_observer=external_binding_observer,
            checkpoint_snapshot_observer=checkpoint_snapshot_observer,
        ),
        normalized_registration,
    )
    pre_isolation = _observe_isolation(
        normalized_registration,
        phase="pre",
        external_binding_observer=external_binding_observer,
        checkpoint_snapshot_observer=checkpoint_snapshot_observer,
    )
    if pre_isolation["matches_registration"] is not True:
        raise ExperimentBlocked("pre-execution isolation differs from registration")
    documents = _static_execution_documents(
        registration=normalized_registration,
        request=normalized_request,
        approval=normalized_approval,
        authorization=normalized_authorization,
        preflight=preflight,
        pre_isolation=pre_isolation,
    )
    if (output / POST_ISOLATION_FILENAME).exists():
        existing_post_isolation = _observe_isolation(
            normalized_registration,
            phase="post",
            external_binding_observer=external_binding_observer,
            checkpoint_snapshot_observer=checkpoint_snapshot_observer,
        )
        if existing_post_isolation["matches_registration"] is not True:
            raise ExperimentBlocked("post-execution isolation differs from registration")
        documents = (
            *documents,
            (POST_ISOLATION_FILENAME, existing_post_isolation),
        )
    lease_context = classified_execution_lease(
        output,
        registration=normalized_registration,
        identity=identity,
        owner_alive=owner_alive,
        expected_documents=documents,
    )
    if lease_context.root_classification["classification"] == (
        "terminal_publication_recovery"
    ):
        with lease_context as lease:
            bundle = publish_terminal_bundle(
                output,
                registration=normalized_registration,
                identity=identity,
                lease=lease,
            )
        return {
            "identity": identity,
            "manifest": bundle["manifest"],
            "preflight": preflight,
            "status": "terminal",
            "terminal": bundle["terminal"],
        }
    lease_context.__enter__()
    try:
        classification = lease_context.root_classification["classification"]
        fresh = classification == "absent_root_initial"
        existing_names = set(_output_relative_files(output)) - {LEASE_FILENAME}
        static_names = {filename for filename, _value in documents}
        if fresh and existing_names - static_names:
            raise ExperimentBlocked("prestart output inventory is ambiguous")
        for filename, value in documents:
            _publish_or_validate_document(
                output,
                filename,
                value,
                allow_existing=filename in existing_names,
            )
        dependencies = _load_registered_dependencies(
            normalized_registration,
            repo_root=root,
            module_importer=module_importer,
            module_registry=module_registry,
            external_binding_observer=external_binding_observer,
        )
        runtime = dependencies["runtime"]
        adapter = dependencies["adapter"]
        native_module = dependencies["native_module"]
        provenance = dependencies["provenance"]
        environment_type = getattr(adapter, "NativeSimulatorEnvironment", None)
        native_environment = getattr(native_module, "Environment", None)
        if not callable(environment_type) or not callable(native_environment):
            raise ExperimentBlocked("loaded environment constructors are unavailable")
        ascension = normalized_registration["contract"]["environment"]["ascension"]

        def environment_factory(seed: int) -> Any:
            return environment_type(native_environment(seed, ascension), provenance)

        attempt_started = float(clock())
        if not math.isfinite(attempt_started):
            raise ExperimentBlocked("execution clock is non-finite")
        limits = normalized_registration["contract"]["limits"]
    except BaseException as exc:
        lease_context.__exit__(type(exc), exc, exc.__traceback__)
        raise
    with lease_context as lease:
        classification = lease.root_classification["classification"]
        if classification == "checkpoint_publication_recovery":
            recovered = recover_checkpoint_publication(
                output,
                registration=normalized_registration,
                identity=identity,
                lease=lease,
            )
            classification = (
                "complete_checkpoint_prefix"
                if recovered["chunk_index"] == CHUNK_COUNT - 1
                else "incomplete_chunk_resume"
            )

        if classification in {"absent_root_initial", "setup_before_bootstrap"}:
            phase = "bootstrap"
            runtime_state = runtime.initialize_training_runtime()
            initial_checkpoint = runtime.encode_runtime_checkpoint(runtime_state)
            initialize_access_journal(
                output,
                registration=normalized_registration,
                identity=identity,
                lease=lease,
            )
            initialize_resource_ledger(
                output,
                registration=normalized_registration,
                identity=identity,
                lease=lease,
            )
            publish_bootstrap(
                output,
                registration=normalized_registration,
                identity=identity,
                lease=lease,
                runtime_checkpoint_payload=initial_checkpoint,
            )
            attempt_ordinal = 0
        elif classification == "initialized_before_seed":
            phase = "bootstrap"
            bootstrap = load_bootstrap(
                output,
                registration=normalized_registration,
                identity=identity,
            )
            runtime_state = runtime.restore_training_runtime_from_checkpoint(
                bootstrap["runtime_checkpoint"]["payload"]
            )
            attempt_ordinal = 0
        elif classification == "complete_checkpoint_prefix":
            phase = "terminal"
            chain = load_checkpoint_chain(
                output,
                registration=normalized_registration,
                identity=identity,
            )
            runtime_state = runtime.restore_training_runtime_from_checkpoint(
                chain[-1]["runtime_checkpoint"]["payload"]
            )
            attempt_ordinal = 0
        else:
            phase = "bootstrap"
            for required in (
                ACCESS_JOURNAL_FILENAME,
                BOOTSTRAP_FILENAME,
                RESOURCE_LEDGER_FILENAME,
            ):
                if not (output / required).is_file():
                    raise ExperimentBlocked("resume output inventory is incomplete")
            start_incomplete_chunk_resume(
                output,
                registration=normalized_registration,
                identity=identity,
                lease=lease,
            )
            resume = load_incomplete_chunk_resume_state(
                output,
                registration=normalized_registration,
                identity=identity,
            )
            runtime_state = runtime.restore_training_runtime_from_checkpoint(
                resume["runtime_checkpoint"]["payload"]
            )
            attempt_ordinal = (
                1
                if resume["resume_mode"] == "replay_uncheckpointed_chunk"
                else 0
            )

        initial_resources = load_resource_ledger(output, identity=identity)["resources"]
        charged_origin = float(initial_resources["charged_seconds"])
        deadline = attempt_started + max(
            0.0, limits["max_charged_seconds"] - charged_origin
        )
        completed_chunks = _load_completed_chunk_evidence(
            output,
            registration=normalized_registration,
            identity=identity,
        )
        saturation = runtime.classify_family_saturation(completed_chunks)
        phase = "training"
        try:
            while (
                runtime_state.next_chunk_index < CHUNK_COUNT
                and saturation.get("stop") is not True
            ):
                chunk_index = int(runtime_state.next_chunk_index)
                seeds = normalized_registration["schedule"]["chunks"][chunk_index]

                def before_environment(seed: int) -> None:
                    begin_environment_access(
                        output,
                        registration=normalized_registration,
                        identity=identity,
                        lease=lease,
                        chunk_index=chunk_index,
                        seed=seed,
                        attempt_ordinal=attempt_ordinal,
                    )

                def after_environment(_seed: int) -> None:
                    complete_environment_access(
                        output,
                        registration=normalized_registration,
                        identity=identity,
                        lease=lease,
                    )

                collected = runtime.collect_and_update_training_chunk(
                    runtime_state,
                    environment_factory=environment_factory,
                    seeds=seeds,
                    chunk_index=chunk_index,
                    before_environment=before_environment,
                    after_environment=after_environment,
                    deadline=deadline,
                    clock=clock,
                )
                evidence = runtime.build_chunk_evidence(collected.update)
                runtime_checkpoint = runtime.encode_runtime_checkpoint(runtime_state)
                elapsed = float(clock()) - attempt_started
                if not math.isfinite(elapsed) or elapsed < 0.0:
                    raise ExperimentBlocked("execution clock moved backwards")
                resources = _exact_checkpoint_resources(
                    output,
                    registration=normalized_registration,
                    identity=identity,
                    runtime_state=runtime_state,
                    runtime_checkpoint_payload=runtime_checkpoint,
                    chunk_evidence=evidence,
                    chunk_index=chunk_index,
                    charged_seconds=charged_origin + elapsed,
                )
                publish_complete_chunk_checkpoint(
                    output,
                    registration=normalized_registration,
                    identity=identity,
                    lease=lease,
                    chunk_index=chunk_index,
                    resources=resources,
                    runtime_checkpoint_payload=runtime_checkpoint,
                    chunk_evidence=evidence,
                )
                completed_chunks.append(evidence)
                saturation = runtime.classify_family_saturation(completed_chunks)
                attempt_ordinal = 0
        except BaseException as exc:
            infrastructure = _is_infrastructure_interruption(exc)
            journal = load_access_journal(
                output,
                registration=normalized_registration,
                identity=identity,
            )
            if journal["pending_access"] is not None:
                append_access_terminal(
                    output,
                    registration=normalized_registration,
                    identity=identity,
                    lease=lease,
                    status=(
                        "infrastructure_interrupted" if infrastructure else "failed"
                    ),
                )
            if infrastructure:
                _charge_infrastructure_interruption(
                    output,
                    registration=normalized_registration,
                    identity=identity,
                    lease=lease,
                    attempt_started=attempt_started,
                    charged_origin=charged_origin,
                    clock=clock,
                )
                charged_journal = load_access_journal(
                    output,
                    registration=normalized_registration,
                    identity=identity,
                )
                if charged_journal["resume_used"]:
                    failure = _failure_witness(
                        exc, phase=phase, infrastructure=True
                    )
                    _publish_or_validate_document(
                        output,
                        FAILURE_FILENAME,
                        failure,
                        allow_existing=(output / FAILURE_FILENAME).exists(),
                    )
                    post = _publish_post_isolation(
                        output,
                        registration=normalized_registration,
                        external_binding_observer=external_binding_observer,
                        checkpoint_snapshot_observer=(
                            checkpoint_snapshot_observer
                        ),
                    )
                    if post["matches_registration"] is not True:
                        return _post_isolation_mismatch_result(
                            identity=identity,
                            observation=post,
                            preflight=preflight,
                        )
                    return _close_runner_terminal(
                        output,
                        registration=normalized_registration,
                        identity=identity,
                        lease=lease,
                        verdict="experiment_failed_after_seed_access",
                        saturation=saturation,
                        failure=failure,
                        preflight=preflight,
                    )
                return {
                    "identity": identity,
                    "preflight": preflight,
                    "status": "infrastructure_interrupted",
                }
            failure = _failure_witness(
                exc, phase=phase, infrastructure=False
            )
            _publish_or_validate_document(
                output,
                FAILURE_FILENAME,
                failure,
                allow_existing=(output / FAILURE_FILENAME).exists(),
            )
            post = _publish_post_isolation(
                output,
                registration=normalized_registration,
                external_binding_observer=external_binding_observer,
                checkpoint_snapshot_observer=checkpoint_snapshot_observer,
            )
            if post["matches_registration"] is not True:
                return _post_isolation_mismatch_result(
                    identity=identity,
                    observation=post,
                    preflight=preflight,
                )
            verdict = (
                "experiment_blocked_before_seed_access"
                if load_access_journal(
                    output,
                    registration=normalized_registration,
                    identity=identity,
                )["debited_accesses"]
                == 0
                else "experiment_failed_after_seed_access"
            )
            return _close_runner_terminal(
                output,
                registration=normalized_registration,
                identity=identity,
                lease=lease,
                verdict=verdict,
                saturation=saturation,
                failure=failure,
                preflight=preflight,
            )

        post = _publish_post_isolation(
            output,
            registration=normalized_registration,
            external_binding_observer=external_binding_observer,
            checkpoint_snapshot_observer=checkpoint_snapshot_observer,
        )
        if post["matches_registration"] is not True:
            failure = _failure_witness(
                ExperimentBlocked("post-execution isolation differs"),
                phase="terminal",
                infrastructure=False,
            )
            _publish_or_validate_document(
                output,
                FAILURE_FILENAME,
                failure,
                allow_existing=(output / FAILURE_FILENAME).exists(),
            )
            return _post_isolation_mismatch_result(
                identity=identity,
                observation=post,
                preflight=preflight,
            )
        verdict = (
            "experiment_stopped_during_training_for_family_saturation"
            if saturation.get("stop") is True
            else "experiment_completed_with_cross_fitted_mechanism_evidence"
        )
        return _close_runner_terminal(
            output,
            registration=normalized_registration,
            identity=identity,
            lease=lease,
            verdict=verdict,
            saturation=saturation,
            failure=None,
            preflight=preflight,
        )


def _load_canonical_json_file(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExperimentBlocked(f"{label} is invalid: {exc}") from exc
    if not isinstance(value, dict) or payload != canonical_json_bytes(value):
        raise ExperimentBlocked(f"{label} is not canonical")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Cross-fitted hierarchical successor controls"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("contract", help="print the immutable source contract")
    inventory = subparsers.add_parser(
        "source-inventory", help="observe source modules without importing them"
    )
    inventory.add_argument("--repo-root", type=Path, default=Path(__file__).parents[1])
    inspect_registration = subparsers.add_parser(
        "inspect-registration", help="validate one all-false registration"
    )
    inspect_registration.add_argument("--registration", type=Path, required=True)
    request = subparsers.add_parser(
        "render-request", help="render an exact request to stdout without publishing"
    )
    request.add_argument("--registration", type=Path, required=True)
    execute = subparsers.add_parser(
        "execute", help="run the one exactly authorized registered mechanism"
    )
    execute.add_argument("--repo-root", type=Path, default=Path(__file__).parents[1])
    execute.add_argument("--registration", type=Path, required=True)
    execute.add_argument("--request", type=Path, required=True)
    execute.add_argument("--approval", type=Path, required=True)
    execute.add_argument("--authorization", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "contract":
        value = experiment_contract()
    elif args.command == "source-inventory":
        value = build_source_inventory(args.repo_root)
    elif args.command == "inspect-registration":
        value = validate_registration(
            _load_canonical_json_file(args.registration, "registration")
        )
    elif args.command == "render-request":
        registration = validate_registration(
            _load_canonical_json_file(args.registration, "registration")
        )
        value = build_exact_execution_request(registration)
    elif args.command == "execute":
        if argv is not None:
            raise ExperimentBlocked("execute must use the real process argv")
        value = execute_authorized_experiment(
            _load_canonical_json_file(args.registration, "registration"),
            _load_canonical_json_file(args.request, "execution request"),
            _load_canonical_json_file(args.authorization, "authorization"),
            _load_canonical_json_file(args.approval, "external approval"),
            repo_root=args.repo_root.resolve(),
        )
    else:  # pragma: no cover - argparse owns command selection.
        raise ExperimentBlocked("unknown source-only command")
    sys.stdout.buffer.write(canonical_json_bytes(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
