"""Source-only controls for the card-acceptance empirical successor."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


CONTRACT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-contract-v1"
)
RUNTIME_METADATA_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-runtime-metadata-v1"
)
DEPENDENCY_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-module-inventory-v1"
)
SOURCE_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-source-inventory-v1"
)
CONFIG_IDENTITY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-config-identity-v1"
)
STAGE_REQUEST_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-stage-request-v1"
)
STAGE_AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-stage-authorization-v1"
)
RUNTIME_MODULE_NAME = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime"
)

_AUTHORITY_NAMES = (
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
_MODULE_SPECS = (
    (
        "control_plane",
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment",
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_experiment.py",
    ),
    (
        "torch_runtime",
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime",
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py",
    ),
    (
        "seed_inventory",
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_seed_inventory",
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_seed_inventory.py",
    ),
    (
        "independent_verifier",
        "analysis_scripts.verify_noncombat_card_acceptance_empirical_successor",
        "analysis_scripts/verify_noncombat_card_acceptance_empirical_successor.py",
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
        (
            "FEATURE_FIELDS",
            "FEATURE_SCHEMA_VERSION",
            "AdvantageAttributionError",
            "AdvantageBatch",
            "build_advantage_batch",
        ),
    ),
    (
        "card_acceptance_objective",
        "analysis_scripts/noncombat_card_acceptance_objective.py",
        (
            "CardAcceptanceObjectiveError",
            "CardAcceptancePolicyTerms",
            "build_card_acceptance_policy_terms",
        ),
    ),
    (
        "card_acceptance_policy",
        "analysis_scripts/noncombat_card_acceptance_policy.py",
        (
            "CardAcceptancePolicy",
            "CardAcceptancePolicyError",
            "CardAcceptancePolicyOutput",
            "build_family_features",
        ),
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
        "policy_input",
        "analysis_scripts/noncombat_state_conditioned_policy_input.py",
        (
            "HASH_DIM",
            "PolicyInputError",
            "project_state_conditioned_policy_input",
        ),
    ),
    (
        "simulator_adapter",
        "analysis_scripts/noncombat_simulator_adapter.py",
        (
            "ADAPTER_API_VERSION",
            "SimulatorAdapterError",
            "TARGET_CATEGORIES",
            "canonical_json_bytes",
            "validate_candidates",
            "validate_snapshot",
        ),
    ),
    (
        "simulator_rl_policy_projection",
        "analysis_scripts/noncombat_simulator_rl_experiment.py",
        ("canonical_json_bytes", "project_policy_view_v2"),
    ),
    (
        "state_conditioned_ranker",
        "analysis_scripts/noncombat_state_conditioned_ranker.py",
        ("DEFAULT_HIDDEN_DIM", "StateConditionedCandidateRanker"),
    ),
)
_STAGES = ("inventory", "training", "canary", "holdout")
_EXECUTION_CONTEXT_OPERATIONS = (
    "journal",
    "resource",
    "checkpoint",
    "stage",
    "rollback",
    "terminal",
)
_EXECUTION_OPERATION_NAMES = (
    "checkpoint_publication",
    "cohort_materialization",
    "environment_construction",
    "evaluation",
    "evidence_publication",
    "experiment_model_loading",
    "model_fitting",
    "native_loading",
    "repository_evidence_read",
    "seed_access",
    "seed_discovery",
    "shadow_optimizer_step",
    "training",
)
_STAGE_ENABLED_OPERATIONS = {
    "inventory": frozenset(
        {
            "cohort_materialization",
            "repository_evidence_read",
            "seed_discovery",
        }
    ),
    "training": frozenset(
        {
            "checkpoint_publication",
            "environment_construction",
            "evidence_publication",
            "experiment_model_loading",
            "model_fitting",
            "native_loading",
            "seed_access",
            "training",
        }
    ),
    "canary": frozenset(
        {
            "environment_construction",
            "evaluation",
            "evidence_publication",
            "experiment_model_loading",
            "native_loading",
            "seed_access",
            "shadow_optimizer_step",
        }
    ),
    "holdout": frozenset(
        {
            "environment_construction",
            "evaluation",
            "evidence_publication",
            "experiment_model_loading",
            "native_loading",
            "seed_access",
        }
    ),
}
_STAGE_PREREQUISITE_FIELDS = {
    "inventory": (),
    "training": ("registration_sha256",),
    "canary": (
        "frozen_seal_sha256",
        "registration_sha256",
        "training_terminal_sha256",
    ),
    "holdout": (
        "canary_terminal_sha256",
        "frozen_seal_sha256",
        "registration_sha256",
    ),
}
_STAGE_RESOURCES: dict[str, dict[str, int | float]] = {
    "inventory": {"max_materialized_seeds": 1_152},
    "training": {
        "max_charged_seconds": 28_800.0,
        "max_environment_accesses": 1_024,
        "max_optimizer_steps": 16,
        "max_pairs": 512,
    },
    "canary": {
        "max_environment_accesses": 512,
        "max_pairs": 128,
        "max_shadow_optimizer_steps": 1,
    },
    "holdout": {
        "bootstrap_resamples": 10_000,
        "max_environment_accesses": 1_024,
        "max_pairs": 512,
    },
}
_STAGE_EXCLUSIONS = (
    "causal_claim",
    "communication_mod",
    "formal_rl",
    "gameplay",
    "ope",
    "production_model_loading",
    "promotion",
    "qualification",
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_IDENTIFIER_RE = re.compile(r"[a-z0-9][a-z0-9._:-]{2,191}")


class SuccessorControlError(ValueError):
    """Raised when a source-only control value cannot be encoded safely."""


def canonical_json_bytes(value: object) -> bytes:
    """Encode deterministic ASCII JSON with exactly one trailing newline."""
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SuccessorControlError("value is not canonical JSON") from exc
    return rendered.encode("ascii") + b"\n"


def canonical_json_sha256(value: object) -> str:
    """Digest the exact canonical JSON representation."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _copy_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SuccessorControlError(f"{label} must be a mapping")
    return copy.deepcopy(dict(value))


def _require_fields(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise SuccessorControlError(f"{label} fields mismatch")


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise SuccessorControlError(f"{label} must be a SHA-256 digest")
    return value


def _commit(value: object, label: str) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise SuccessorControlError(f"{label} must be a full Git commit")
    return value


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER_RE.fullmatch(value) is None:
        raise SuccessorControlError(f"{label} is invalid")
    return value


def _canonical_absolute_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise SuccessorControlError(f"{label} must be a canonical absolute path")
    windows_absolute = re.fullmatch(r"[A-Za-z]:/[^\x00]+", value) is not None
    posix_absolute = value.startswith("/")
    pure = PurePosixPath(value[3:] if windows_absolute else value)
    if (
        not (windows_absolute or posix_absolute)
        or value.endswith("/")
        or "." in pure.parts
        or ".." in pure.parts
    ):
        raise SuccessorControlError(f"{label} must be a canonical absolute path")
    return value


def _stage(value: object) -> str:
    if value not in _STAGES:
        raise SuccessorControlError("empirical stage is invalid")
    return str(value)


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SuccessorControlError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise SuccessorControlError(f"non-finite JSON constant: {value}")


def _read_json_mapping(path: Path | str, label: str) -> dict[str, Any]:
    candidate = Path(path).resolve()
    try:
        payload = candidate.read_bytes()
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except SuccessorControlError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SuccessorControlError(f"{label} cannot be read") from exc
    return _copy_mapping(value, label)


def _authority() -> dict[str, bool]:
    return {name: False for name in _AUTHORITY_NAMES}


def _algorithm() -> dict[str, Any]:
    return {
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
    }


def _cohorts() -> dict[str, int]:
    return {
        "canary_pairs": 128,
        "holdout_pairs": 512,
        "training_chunks": 8,
        "training_pairs": 512,
        "training_pairs_per_chunk": 64,
    }


def _limits() -> dict[str, int | float]:
    return {
        "max_artifact_bytes": 64 * 1024 * 1024,
        "max_canary_environment_accesses": 512,
        "max_charged_seconds": 28_800.0,
        "max_decisions_per_episode": 500,
        "max_environment_accesses": 2_560,
        "max_holdout_environment_accesses": 1_024,
        "max_shadow_optimizer_steps": 1,
        "max_stored_bytes": 256 * 1024 * 1024,
        "max_training_environment_accesses": 1_024,
        "max_training_optimizer_steps": 16,
        "max_training_updates_per_arm": 8,
        "max_uncompressed_bytes": 512 * 1024 * 1024,
    }


def expected_runtime_metadata() -> dict[str, Any]:
    """Return fresh expected metadata without importing the runtime."""
    algorithm = _algorithm()
    return {
        "algorithm": algorithm,
        "architecture": {
            "candidate": "disjoint-family-and-conditional-heads",
            "control": "shared-card-ranker",
            "frozen_noncard_rankers": 2,
            "matched_rankers": 5,
        },
        "authority": _authority(),
        "baseline": {
            "feature_dim": 128,
            "fit_trajectories_per_fold": 48,
            "fold_count": 4,
            "held_out_trajectories_per_fold": 16,
            "prediction_bounds": [0.0, 3.0],
            "ridge_coefficient": 0.001,
            "ridge_residual_atol": 1e-9,
            "ridge_residual_rtol": 1e-9,
            "scale": 1.0,
            "solver": "cpu-float64-cholesky-v1",
            "source_dim": 1024,
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
            "amsgrad": algorithm["optimizer_amsgrad"],
            "betas": list(algorithm["optimizer_betas"]),
            "eps": algorithm["optimizer_eps"],
            "learning_rate": algorithm["learning_rate"],
            "name": algorithm["optimizer"],
            "weight_decay": algorithm["optimizer_weight_decay"],
        },
        "schema_version": RUNTIME_METADATA_SCHEMA_VERSION,
    }


def module_dependency_inventory() -> dict[str, Any]:
    """Declare the closed successor modules and local behavioral dependencies."""
    return {
        "modules": [
            {"name": name, "path": path, "role": role}
            for role, name, path in _MODULE_SPECS
        ],
        "public_dependencies": [
            {
                "name": name,
                "path": path,
                "public_symbols": list(public_symbols),
            }
            for name, path, public_symbols in _PUBLIC_DEPENDENCY_SPECS
        ],
        "schema_version": DEPENDENCY_INVENTORY_SCHEMA_VERSION,
    }


def _source_binding(path: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def build_source_inventory(repo_root: Path | str) -> dict[str, Any]:
    """Hash the closed source declaration without importing any source module."""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise SuccessorControlError("source repository root is missing")
    declaration = module_dependency_inventory()
    observed: dict[str, list[dict[str, Any]]] = {
        "modules": [],
        "public_dependencies": [],
    }
    try:
        for section in observed:
            for row in declaration[section]:
                path = str(row["path"])
                payload = (root / PurePosixPath(path)).read_bytes()
                observed[section].append({**row, **_source_binding(path, payload)})
    except OSError as exc:
        raise SuccessorControlError(
            f"source inventory cannot be observed: {exc}"
        ) from exc
    body = {
        **observed,
        "schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
    }
    return {**body, "inventory_sha256": canonical_json_sha256(body)}


def external_file_binding(path: Path | str) -> dict[str, Any]:
    """Hash one external file as inert bytes without importing or loading it."""
    candidate = Path(path).resolve()
    if not candidate.is_file():
        raise SuccessorControlError(f"external file is missing: {candidate}")
    try:
        payload = candidate.read_bytes()
    except OSError as exc:
        raise SuccessorControlError(
            f"external file cannot be read: {candidate}"
        ) from exc
    if not payload:
        raise SuccessorControlError(f"external file is empty: {candidate}")
    return {
        "path": candidate.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _hash_named_bytes(rows: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in rows:
        encoded_name = name.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def snapshot_directory_tree(root: Path | str) -> dict[str, Any]:
    """Hash a complete directory tree in canonical relative-path order."""
    directory = Path(root).resolve()
    if not directory.is_dir():
        raise SuccessorControlError(f"directory root is missing: {directory}")
    try:
        files = sorted(
            (path for path in directory.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(directory).as_posix(),
        )
        rows = [
            (path.relative_to(directory).as_posix(), path.read_bytes())
            for path in files
        ]
    except OSError as exc:
        raise SuccessorControlError(
            f"directory tree cannot be read: {directory}"
        ) from exc
    return {
        "file_count": len(rows),
        "root": directory.as_posix(),
        "sha256": _hash_named_bytes(rows),
        "size_bytes": sum(len(payload) for _, payload in rows),
    }


def build_native_identity(
    *,
    module_path: Path | str,
    dll_directories: Sequence[Path | str],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind native bytes and declared provenance without loading the module."""
    if isinstance(dll_directories, (str, bytes)):
        raise SuccessorControlError("native DLL directories must be a sequence")
    normalized_directories = sorted(
        {Path(path).resolve().as_posix() for path in dll_directories}
    )
    if not normalized_directories or any(
        not Path(path).is_dir() for path in normalized_directories
    ):
        raise SuccessorControlError("native DLL directory is missing")
    module = external_file_binding(module_path)
    if not isinstance(provenance, Mapping) or not provenance:
        raise SuccessorControlError("native provenance must be a nonempty mapping")
    normalized_provenance = copy.deepcopy(dict(provenance))
    build = normalized_provenance.get("build")
    if not isinstance(build, Mapping) or build.get("adapter_api_version") != (
        "sts-lightspeed-noncombat-adapter-v3"
    ):
        raise SuccessorControlError("native provenance adapter API mismatch")
    if normalized_provenance.get("module_sha256") != module["sha256"]:
        raise SuccessorControlError("native provenance module digest mismatch")
    return {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "dll_directories": normalized_directories,
        "module": module,
        "provenance": normalized_provenance,
        "provenance_sha256": canonical_json_sha256(normalized_provenance),
    }


def build_isolation_identity(
    *,
    communication_mod_config: Path | str,
    production_checkpoint_root: Path | str,
) -> dict[str, Any]:
    """Bind production configuration and checkpoint bytes without loading them."""
    return {
        "communication_mod_config": external_file_binding(
            communication_mod_config
        ),
        "production_checkpoints": snapshot_directory_tree(
            production_checkpoint_root
        ),
    }


def _load_runtime_module(
    *, module_importer: Callable[[str], Any] | None = None
) -> Any:
    """Import the Torch runtime only when a later validated preflight calls here."""
    importer = module_importer or importlib.import_module
    return importer(RUNTIME_MODULE_NAME)


def experiment_contract() -> dict[str, Any]:
    """Return the fixed source-only experiment contract."""
    return {
        "algorithm": _algorithm(),
        "authority": _authority(),
        "cohorts": _cohorts(),
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "limits": _limits(),
        "runtime_metadata": expected_runtime_metadata(),
        "schema_version": CONTRACT_SCHEMA_VERSION,
    }


def experiment_configuration_identity() -> dict[str, Any]:
    """Bind the fixed source-only experiment configuration canonically."""
    payload = canonical_json_bytes(experiment_contract())
    return {
        "canonical_size_bytes": len(payload),
        "contract_sha256": hashlib.sha256(payload).hexdigest(),
        "schema_version": CONFIG_IDENTITY_SCHEMA_VERSION,
    }


def stage_execution_authority(stage: str) -> dict[str, bool]:
    """Return the exact operation map for one empirical stage."""
    normalized_stage = _stage(stage)
    enabled = _STAGE_ENABLED_OPERATIONS[normalized_stage]
    return {name: name in enabled for name in _EXECUTION_OPERATION_NAMES}


def stage_resources(stage: str) -> dict[str, int | float]:
    """Return fresh fixed ceilings for one empirical stage."""
    return copy.deepcopy(_STAGE_RESOURCES[_stage(stage)])


def _normalize_configuration_identity(value: object) -> dict[str, Any]:
    identity = _copy_mapping(value, "configuration identity")
    if identity != experiment_configuration_identity():
        raise SuccessorControlError("configuration identity mismatch")
    return identity


def _normalize_prerequisites(
    value: object, *, stage: str
) -> dict[str, str]:
    prerequisites = _copy_mapping(value, "stage prerequisite bindings")
    expected_fields = _STAGE_PREREQUISITE_FIELDS[stage]
    if tuple(sorted(prerequisites)) != expected_fields:
        raise SuccessorControlError("stage prerequisite bindings mismatch")
    return {
        name: _digest(prerequisites[name], f"{name} prerequisite")
        for name in expected_fields
    }


def _stage_request_body(
    *,
    stage: str,
    request_id: str,
    source_commit: str,
    source_inventory_sha256: str,
    configuration_identity: Mapping[str, Any],
    prerequisite_bindings: Mapping[str, Any],
    output_root: str,
) -> dict[str, Any]:
    normalized_stage = _stage(stage)
    normalized_request_id = _identifier(request_id, "stage request id")
    if not normalized_request_id.endswith(f"-{normalized_stage}-request-v1"):
        raise SuccessorControlError("stage request id does not bind its stage")
    return {
        "configuration_identity": _normalize_configuration_identity(
            configuration_identity
        ),
        "downstream_authority": _authority(),
        "execution_authority": stage_execution_authority(normalized_stage),
        "exclusions": list(_STAGE_EXCLUSIONS),
        "output_root": _canonical_absolute_path(output_root, "stage output root"),
        "prerequisite_bindings": _normalize_prerequisites(
            prerequisite_bindings,
            stage=normalized_stage,
        ),
        "request_id": normalized_request_id,
        "resources": stage_resources(normalized_stage),
        "schema_version": STAGE_REQUEST_SCHEMA_VERSION,
        "source_commit": _commit(source_commit, "stage source commit"),
        "source_inventory_sha256": _digest(
            source_inventory_sha256,
            "stage source inventory identity",
        ),
        "stage": normalized_stage,
    }


def build_stage_request(
    *,
    stage: str,
    request_id: str,
    source_commit: str,
    source_inventory_sha256: str,
    configuration_identity: Mapping[str, Any],
    prerequisite_bindings: Mapping[str, Any],
    output_root: str,
) -> dict[str, Any]:
    """Render one exact stage request without publishing or granting authority."""
    body = _stage_request_body(
        stage=stage,
        request_id=request_id,
        source_commit=source_commit,
        source_inventory_sha256=source_inventory_sha256,
        configuration_identity=configuration_identity,
        prerequisite_bindings=prerequisite_bindings,
        output_root=output_root,
    )
    return {**body, "request_sha256": canonical_json_sha256(body)}


def validate_stage_request(value: Mapping[str, Any]) -> dict[str, Any]:
    """Reconstruct a stage request and reject every caller-supplied drift."""
    request = _copy_mapping(value, "stage request")
    _require_fields(
        request,
        {
            "configuration_identity",
            "downstream_authority",
            "execution_authority",
            "exclusions",
            "output_root",
            "prerequisite_bindings",
            "request_id",
            "request_sha256",
            "resources",
            "schema_version",
            "source_commit",
            "source_inventory_sha256",
            "stage",
        },
        "stage request",
    )
    if request["schema_version"] != STAGE_REQUEST_SCHEMA_VERSION:
        raise SuccessorControlError("stage request schema mismatch")
    expected = build_stage_request(
        stage=request["stage"],
        request_id=request["request_id"],
        source_commit=request["source_commit"],
        source_inventory_sha256=request["source_inventory_sha256"],
        configuration_identity=request["configuration_identity"],
        prerequisite_bindings=request["prerequisite_bindings"],
        output_root=request["output_root"],
    )
    if request != expected:
        raise SuccessorControlError("stage request differs from exact terms")
    return request


def _stage_authorization_body(
    *,
    request: Mapping[str, Any],
    authorization_id: str,
    request_review_sha256: str,
    approval_record_sha256: str,
) -> dict[str, Any]:
    normalized_request = validate_stage_request(request)
    stage = normalized_request["stage"]
    normalized_id = _identifier(authorization_id, "stage authorization id")
    if not normalized_id.endswith(f"-{stage}-authorization-v1"):
        raise SuccessorControlError(
            "stage authorization id does not bind its stage"
        )
    return {
        "approval_record_sha256": _digest(
            approval_record_sha256,
            "approval record identity",
        ),
        "authorization_id": normalized_id,
        "downstream_authority": _authority(),
        "execution_authority": copy.deepcopy(
            normalized_request["execution_authority"]
        ),
        "request_id": normalized_request["request_id"],
        "request_review_sha256": _digest(
            request_review_sha256,
            "request review identity",
        ),
        "request_sha256": normalized_request["request_sha256"],
        "schema_version": STAGE_AUTHORIZATION_SCHEMA_VERSION,
        "stage": stage,
    }


def build_stage_authorization(
    *,
    request: Mapping[str, Any],
    authorization_id: str,
    request_review_sha256: str,
    approval_record_sha256: str,
) -> dict[str, Any]:
    """Bind one reviewed request to an externally validated approval record."""
    body = _stage_authorization_body(
        request=request,
        authorization_id=authorization_id,
        request_review_sha256=request_review_sha256,
        approval_record_sha256=approval_record_sha256,
    )
    return {**body, "authorization_sha256": canonical_json_sha256(body)}


def validate_stage_authorization(
    value: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    """Require exact request, review, approval-record, and authority bindings."""
    authorization = _copy_mapping(value, "stage authorization")
    _require_fields(
        authorization,
        {
            "approval_record_sha256",
            "authorization_id",
            "authorization_sha256",
            "downstream_authority",
            "execution_authority",
            "request_id",
            "request_review_sha256",
            "request_sha256",
            "schema_version",
            "stage",
        },
        "stage authorization",
    )
    if authorization["schema_version"] != STAGE_AUTHORIZATION_SCHEMA_VERSION:
        raise SuccessorControlError("stage authorization schema mismatch")
    expected = build_stage_authorization(
        request=request,
        authorization_id=authorization["authorization_id"],
        request_review_sha256=authorization["request_review_sha256"],
        approval_record_sha256=authorization["approval_record_sha256"],
    )
    if authorization != expected:
        raise SuccessorControlError(
            "stage authorization differs from exact request binding"
        )
    return authorization


class _FrozenExecutionDict(dict[str, Any]):
    """JSON-compatible mapping owned by one process-local execution context."""

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("validated execution context is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


class _FrozenExecutionList(list[Any]):
    """JSON-compatible sequence owned by one process-local execution context."""

    @staticmethod
    def _immutable(*_args: Any, **_kwargs: Any) -> None:
        raise TypeError("validated execution context is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable


def _freeze_execution_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _FrozenExecutionDict(
            {key: _freeze_execution_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return _FrozenExecutionList(_freeze_execution_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_execution_value(item) for item in value)
    return value


class _ValidatedExecutionContext:
    """Own one validated registration/request/authorization tuple exactly once."""

    __slots__ = (
        "_authorization",
        "_registration",
        "_request",
        "_sealed",
        "_stage",
    )

    def __init__(
        self,
        *,
        registration: _FrozenExecutionDict,
        request: _FrozenExecutionDict,
        authorization: _FrozenExecutionDict,
        stage: str,
    ) -> None:
        object.__setattr__(self, "_registration", registration)
        object.__setattr__(self, "_request", request)
        object.__setattr__(self, "_authorization", authorization)
        object.__setattr__(self, "_stage", stage)
        object.__setattr__(self, "_sealed", True)

    def __setattr__(self, _name: str, _value: Any) -> None:
        if getattr(self, "_sealed", False):
            raise TypeError("validated execution context is immutable")
        object.__setattr__(self, _name, _value)

    def __delattr__(self, _name: str) -> None:
        raise TypeError("validated execution context is immutable")

    def __copy__(self):
        raise TypeError("validated execution context cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]):
        raise TypeError("validated execution context cannot be copied")

    @property
    def registration(self) -> Mapping[str, Any]:
        return self._registration

    @property
    def request(self) -> Mapping[str, Any]:
        return self._request

    @property
    def authorization(self) -> Mapping[str, Any]:
        return self._authorization

    @property
    def stage(self) -> str:
        return self._stage


def _build_validated_execution_context(
    *,
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    registration_validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> _ValidatedExecutionContext:
    """Validate raw stage bindings once, then retain recursively frozen values."""
    if type(registration) is _ValidatedExecutionContext:
        raise SuccessorControlError(
            "execution context must be built from raw registration"
        )
    if not callable(registration_validator):
        raise SuccessorControlError("registration validator must be callable")
    normalized_request = validate_stage_request(request)
    if normalized_request["stage"] == "inventory":
        raise SuccessorControlError(
            "inventory does not use an empirical registration context"
        )
    normalized_authorization = validate_stage_authorization(
        authorization,
        normalized_request,
    )
    try:
        normalized_registration = _copy_mapping(
            registration_validator(registration),
            "validated registration",
        )
    except SuccessorControlError:
        raise
    except Exception as exc:
        raise SuccessorControlError("registration validation failed") from exc
    registration_sha256 = _digest(
        normalized_registration.get("registration_sha256"),
        "registration identity",
    )
    if registration_sha256 != normalized_request["prerequisite_bindings"].get(
        "registration_sha256"
    ):
        raise SuccessorControlError("execution registration binding mismatch")
    frozen_registration = _freeze_execution_value(normalized_registration)
    frozen_request = _freeze_execution_value(normalized_request)
    frozen_authorization = _freeze_execution_value(normalized_authorization)
    if not all(
        type(value) is _FrozenExecutionDict
        for value in (frozen_registration, frozen_request, frozen_authorization)
    ):
        raise SuccessorControlError("execution context ownership failed")
    return _ValidatedExecutionContext(
        registration=frozen_registration,
        request=frozen_request,
        authorization=frozen_authorization,
        stage=normalized_request["stage"],
    )


def _require_execution_context(value: object) -> _ValidatedExecutionContext:
    """Reject raw mappings so all lifecycle operations share the exact context."""
    if type(value) is not _ValidatedExecutionContext:
        raise SuccessorControlError("validated execution context is required")
    return value


def _execution_context_for_operation(
    value: object, operation: str
) -> _ValidatedExecutionContext:
    """Route every lifecycle operation through the same process-owned context."""
    context = _require_execution_context(value)
    if operation not in _EXECUTION_CONTEXT_OPERATIONS:
        raise SuccessorControlError("execution context operation is invalid")
    return context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Card-acceptance empirical successor source controls"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("contract", help="print the immutable source contract")
    render_request = subparsers.add_parser(
        "render-request", help="render one exact stage request"
    )
    render_request.add_argument("--definition", required=True)
    validate_request = subparsers.add_parser(
        "validate-request", help="validate one exact stage request"
    )
    validate_request.add_argument("--request", required=True)
    render_authorization = subparsers.add_parser(
        "render-authorization", help="render one exact stage authorization"
    )
    render_authorization.add_argument("--request", required=True)
    render_authorization.add_argument("--definition", required=True)
    validate_authorization = subparsers.add_parser(
        "validate-authorization", help="validate one exact stage authorization"
    )
    validate_authorization.add_argument("--request", required=True)
    validate_authorization.add_argument("--authorization", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "contract":
        output = experiment_contract()
    elif args.command == "render-request":
        definition = _read_json_mapping(args.definition, "request definition")
        output = build_stage_request(**definition)
    elif args.command == "validate-request":
        output = validate_stage_request(
            _read_json_mapping(args.request, "stage request")
        )
    elif args.command == "render-authorization":
        request = validate_stage_request(
            _read_json_mapping(args.request, "stage request")
        )
        definition = _read_json_mapping(
            args.definition,
            "authorization definition",
        )
        output = build_stage_authorization(request=request, **definition)
    elif args.command == "validate-authorization":
        request = validate_stage_request(
            _read_json_mapping(args.request, "stage request")
        )
        output = validate_stage_authorization(
            _read_json_mapping(args.authorization, "stage authorization"),
            request,
        )
    else:
        raise SuccessorControlError("unknown source-only command")
    sys.stdout.buffer.write(canonical_json_bytes(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
