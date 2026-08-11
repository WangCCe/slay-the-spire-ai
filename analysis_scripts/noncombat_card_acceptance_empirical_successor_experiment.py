"""Source-only controls for the card-acceptance empirical successor."""

from __future__ import annotations

import argparse
import ast
import copy
import gzip
import hashlib
import importlib
import io
import json
import math
import os
import re
import struct
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
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
    "noncombat-card-acceptance-empirical-successor-source-inventory-v2"
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
STANDING_DELEGATION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-standing-delegation-v1"
)
DELEGATED_APPROVAL_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-delegated-approval-v1"
)
REVOCATION_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-revocation-observation-v1"
)
EXTERNAL_APPROVAL_MESSAGE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-external-approval-message-v1"
)
EXTERNAL_HUMAN_APPROVAL_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-external-human-approval-v1"
)
EXTERNAL_REVOCATION_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-external-revocation-observation-v1"
)
RUNTIME_MODULE_NAME = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime"
)
CONSUMED_EVIDENCE_PRESERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-consumed-evidence-preservation-v1"
)
CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_ID = (
    "noncombat-card-acceptance-empirical-successor-preservation-20260809"
)
CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_PATH = (
    "reports/noncombat_card_acceptance_empirical_successor_preservation_20260809.json"
)
CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_SHA256 = (
    "6d5ec05d51a53a73c053e1591b3fb85d746c06efdc5c1b96f82a176e3de4e992"
)
CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_COMMIT = (
    "df706481140f62fd5b08aaa370d27b27360430f2"
)
CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_TREE = (
    "a04b20e870bad125d090f4e1b2ad90b438536e60"
)
CONSUMED_EVIDENCE_DIRECTORY_INVENTORY_SCHEMA = (
    "sorted-relative-path-type-rows-v1"
)
CONSUMED_EVIDENCE_PRESERVATION_BASELINE = {
    "remote_commit": "6f620434ba962216fb4cab11bd4bb0a8aefc4674",
    "remote_ref": "origin/master",
    "source_commit": "6f620434ba962216fb4cab11bd4bb0a8aefc4674",
    "source_tree": "ad7c1c4f18af90966577c01a2851444ff66c66e1",
    "tracked_worktree_clean": True,
}
CONSUMED_EVIDENCE_PRESERVATION_SOURCE_PATHS = (
    "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py",
    "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_runtime.py",
    "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py",
    "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_inventory.py",
    "openspec/specs/noncombat-cross-fitted-hierarchical-learning-successor/spec.md",
)
CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_FILE_PATHS = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_registration.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_registration_review.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_request.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_request_review.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_standing_delegation_20260808.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_delegated_approval.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_delegated_approval_review.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_authorization.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_authorization_review.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_preflight.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_postmortem.json",
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_postmortem.md",
    "reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r5_closeout.json",
)
CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_ROOT_PATHS = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2",
    "reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r5",
    "reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/ffd9acc444258483d172529eccfe8ccb05c9bb9b",
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
_STAGES = (
    "inventory",
    "inventory-verification",
    "training",
    "canary",
    "holdout",
)
DELEGATED_REGISTRATION_ID_PREFIX = (
    "noncombat-card-acceptance-empirical-successor-"
)
DELEGATED_REQUEST_CLASS = STAGE_REQUEST_SCHEMA_VERSION
DELEGATED_APPROVAL_RESOLVER = "codex-agent-under-standing-delegation-v1"
REPOSITORY_ID = "WangCCe/slay-the-spire-ai"
STANDING_DELEGATION_REVOCATION = (
    "future-explicit-human-revocation-before-approval-publication-v1"
)
STANDING_DELEGATION_EXCLUSIONS = (
    "bypass-codex-host-or-operating-system-approval",
    "change-request-bound-source-path-cohort-resource-retry-or-authority-terms",
    "destructive-unrelated-repository-or-filesystem-operation",
    "substitute-another-request-digest",
)
STANDING_DELEGATION_GRANT_SOURCE = {
    "delegation_sha256": (
        "9720eede9ca1eb41d65277ec9e1fcff024931c06720d2d322bc4f29c55ae97ff"
    ),
    "file_sha256": (
        "6dac765272edc2a730f9d03075c97ebccc373a704fcc6d1bf4674dbc29a699dc"
    ),
    "path": (
        "reports/noncombat_cross_fitted_hierarchical_learning_"
        "standing_delegation_20260808.json"
    ),
}
STANDING_DELEGATION_GRANT = {
    "granted_at": "2026-08-08T09:46:47Z",
    "provenance": {
        "message_id": "item-22027",
        "source": "external-human-message",
        "task_id": "019eb771-30f7-7ed2-9af2-ea4b22fadc11",
    },
    "verbatim_text": (
        "\u540e\u9762\u80fd\u4e0d\u80fd\u6539\u6210\u4e0d\u9700\u8981"
        "\u8fd9\u6837\u7cbe\u786e\u7684\u6388\u6743\uff0c\u8fd9\u4e2a"
        "\u4ed3\u5e93\u53ea\u6709\u6211\u81ea\u5df1\uff0c\u4f60\u53ef"
        "\u4ee5\u5168\u6743\u4ee3\u8868\u6211\u3002"
    ),
}
_EXECUTION_CONTEXT_OPERATIONS = (
    "artifact",
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
    "inventory-verification": frozenset(
        {
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
    "inventory-verification": (
        "inventory_authorization_sha256",
        "inventory_file_sha256",
        "inventory_launch_observation_sha256",
        "inventory_receipt_sha256",
        "inventory_request_sha256",
        "inventory_sha256",
    ),
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
    "inventory-verification": {
        "max_cli_completion_bytes": 2_048,
        "max_inventory_bytes": 64 * 1024 * 1024,
    },
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
LEASE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-execution-lease-v1"
)
ACCESS_JOURNAL_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-access-journal-v1"
)
RESOURCE_LEDGER_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-resource-ledger-v1"
)
MARKER_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-marker-v1"
)
TRAINING_CHECKPOINT_BINDING_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-training-checkpoint-binding-v1"
)
TRAINING_CONTINUATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-training-continuation-v1"
)
ARTIFACT_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-artifact-inventory-v1"
)
FLOAT64_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-float64-evidence-v1"
)
TERMINAL_INTENT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-terminal-intent-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-terminal-v1"
)
MANIFEST_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-artifact-manifest-v1"
)
ROLLBACK_AUTHORITY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-rollback-authority-v1"
)
EXPERIMENT_TARGET_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-experiment-target-v1"
)
ROLLBACK_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-rollback-observation-v2"
)
LEASE_FILENAME = ".execution.lease"
ACCESS_JOURNAL_FILENAME = "access_journal.jsonl"
RESOURCE_LEDGER_FILENAME = "resource_ledger.jsonl"
TERMINAL_INTENT_FILENAME = "terminal_intent.json"
TERMINAL_FILENAME = "terminal.json"
MANIFEST_FILENAME = "artifact_manifest.json"
ROLLBACK_OBSERVATION_FILENAME = "rollback.json"
ROLLBACK_TARGET_STAGING_SUFFIX = ".rollback.tmp"
ROLLBACK_TRIGGER_CLASSES = (
    "authority",
    "identity",
    "legality",
    "preflight",
    "canary",
    "holdout",
    "publication",
)
ROLLBACK_FAILURE_PATHS = (
    ("grant_failure", "authority"),
    ("revocation_failure", "authority"),
    ("approval_failure", "authority"),
    ("authorization_failure", "authority"),
    ("stage_authority_failure", "authority"),
    ("source_identity_failure", "identity"),
    ("checkpoint_identity_failure", "identity"),
    ("config_identity_failure", "identity"),
    ("cohort_identity_failure", "identity"),
    ("target_identity_failure", "identity"),
    ("production_identity_failure", "identity"),
    ("child_identity_failure", "identity"),
    ("process_identity_failure", "identity"),
    ("lease_identity_failure", "identity"),
    ("candidate_legality_failure", "legality"),
    ("action_legality_failure", "legality"),
    ("schema_failure", "legality"),
    ("finiteness_failure", "legality"),
    ("objective_support_failure", "legality"),
    ("zero_card_reward_chunk", "legality"),
    ("interpreter_preflight_failure", "preflight"),
    ("native_preflight_failure", "preflight"),
    ("isolation_preflight_failure", "preflight"),
    ("output_preflight_failure", "preflight"),
    ("dependency_preflight_failure", "preflight"),
    ("setup_preflight_failure", "preflight"),
    ("training_family_saturation", "canary"),
    ("canary_gate_failure", "canary"),
    ("canary_failure", "canary"),
    ("holdout_gate_failure", "holdout"),
    ("holdout_access_failure", "holdout"),
    ("holdout_evaluation_failure", "holdout"),
    ("holdout_classification_failure", "holdout"),
    ("resource_accounting_failure", "publication"),
    ("time_accounting_failure", "publication"),
    ("access_accounting_failure", "publication"),
    ("partial_chunk_failure", "publication"),
    ("journal_failure", "publication"),
    ("evidence_failure", "publication"),
    ("byte_bound_failure", "publication"),
    ("staging_failure", "publication"),
    ("checkpoint_publication_failure", "publication"),
    ("terminal_publication_failure", "publication"),
    ("manifest_publication_failure", "publication"),
)
HOLDOUT_OUTCOME_CLASSES = (
    "victory_and_floor_signal",
    "floor_only_signal",
    "victory_only_signal",
    "no_learning_signal",
)
_TERMINAL_PUBLICATION_FILENAMES = (
    TERMINAL_INTENT_FILENAME,
    TERMINAL_FILENAME,
    MANIFEST_FILENAME,
)
_ACTIVE_EXECUTION_LEASES: set[str] = set()
_CHECKPOINT_COMPONENT_NAMES = (
    "candidate_card_generator",
    "candidate_model",
    "candidate_noncard_generator",
    "candidate_optimizer",
    "control_card_generator",
    "control_model",
    "control_noncard_generator",
    "control_optimizer",
)


class SuccessorControlError(ValueError):
    """Raised when a source-only control value cannot be encoded safely."""


def classify_terminal_closeout(
    *,
    failure_paths: Sequence[str] | None = None,
    outcome_class: str | None = None,
) -> dict[str, Any]:
    """Map closed failure paths by precedence or admit one normal outcome."""
    if outcome_class is not None:
        if failure_paths is not None:
            raise SuccessorControlError(
                "terminal closeout cannot combine failure paths and an outcome"
            )
        if outcome_class not in HOLDOUT_OUTCOME_CLASSES:
            raise SuccessorControlError("terminal closeout outcome is not registered")
        return {
            "closeout_kind": "normal_holdout",
            "failure_paths": [],
            "outcome_class": outcome_class,
            "rollback_required": False,
            "trigger_class": None,
        }
    if (
        failure_paths is None
        or isinstance(failure_paths, (str, bytes))
        or not isinstance(failure_paths, Sequence)
        or not failure_paths
    ):
        raise SuccessorControlError("rollback failure paths must be nonempty")
    paths = tuple(failure_paths)
    if any(not isinstance(path, str) for path in paths):
        raise SuccessorControlError("rollback failure path is invalid")
    if len(set(paths)) != len(paths):
        raise SuccessorControlError("rollback failure paths contain a duplicate")
    trigger_by_path = dict(ROLLBACK_FAILURE_PATHS)
    if any(path not in trigger_by_path for path in paths):
        raise SuccessorControlError("rollback failure path is not registered")
    path_order = {
        path: index for index, (path, _trigger) in enumerate(ROLLBACK_FAILURE_PATHS)
    }
    normalized_paths = sorted(paths, key=path_order.__getitem__)
    trigger_class = min(
        (trigger_by_path[path] for path in normalized_paths),
        key=ROLLBACK_TRIGGER_CLASSES.index,
    )
    return {
        "closeout_kind": "rollback_failure",
        "failure_paths": normalized_paths,
        "outcome_class": None,
        "rollback_required": True,
        "trigger_class": trigger_class,
    }


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


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise SuccessorControlError(f"{label} must be a nonempty string")
    return value


def _timestamp(value: object, label: str) -> datetime:
    text = _nonempty_string(value, label)
    normalized = f"{text[:-1]}+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SuccessorControlError(f"{label} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise SuccessorControlError(f"{label} must include a timezone")
    return parsed


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
        "consumed_evidence_preservation": verify_consumed_evidence_preservation(
            root
        ),
        "schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
    }
    return {**body, "inventory_sha256": canonical_json_sha256(body)}


def _preservation_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise SuccessorControlError(f"{label} path is invalid")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or pure.as_posix() != value
        or value.endswith("/")
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise SuccessorControlError(f"{label} path is invalid")
    return value


def _read_preserved_file(root: Path, relative_path: object, label: str) -> bytes:
    relative = _preservation_relative_path(relative_path, label)
    path = root.joinpath(*PurePosixPath(relative).parts)
    cursor = root
    for part in PurePosixPath(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise SuccessorControlError(f"{label} path contains a symlink: {relative}")
    if not path.is_file():
        raise SuccessorControlError(f"{label} is missing: {relative}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SuccessorControlError(f"{label} cannot be read: {relative}") from exc


def _preservation_file_binding(relative_path: str, payload: bytes) -> dict[str, Any]:
    git_blob = b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    return {
        "git_blob_oid": hashlib.sha1(git_blob).hexdigest(),
        "path": relative_path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _static_import_string(
    value: ast.expr, constants: Mapping[str, str]
) -> str | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.Name):
        return constants.get(value.id)
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
        left = _static_import_string(value.left, constants)
        right = _static_import_string(value.right, constants)
        if left is not None and right is not None:
            return left + right
    return None


def _is_dynamic_import_callable(
    value: ast.expr,
    *,
    getattr_aliases: set[str],
    importlib_aliases: set[str],
    import_module_aliases: set[str],
) -> bool:
    if isinstance(value, ast.Name):
        return value.id == "__import__" or value.id in import_module_aliases
    if isinstance(value, ast.Attribute):
        return (
            value.attr == "import_module"
            and isinstance(value.value, ast.Name)
            and value.value.id in importlib_aliases
        )
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id in getattr_aliases
        and len(value.args) >= 2
        and isinstance(value.args[0], ast.Name)
        and value.args[0].id in importlib_aliases
        and isinstance(value.args[1], ast.Constant)
        and value.args[1].value == "import_module"
    )


def _reject_successor_import(relative_path: str, payload: bytes) -> None:
    if not relative_path.endswith(".py"):
        return
    try:
        tree = ast.parse(payload.decode("utf-8"), filename=relative_path)
    except (SyntaxError, UnicodeDecodeError) as exc:
        raise SuccessorControlError(
            f"consumed source is not valid UTF-8 Python: {relative_path}"
        ) from exc
    imported_names: list[str] = []
    getattr_aliases = {"getattr"}
    importlib_aliases: set[str] = set()
    import_module_aliases: set[str] = set()
    string_constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                value = _static_import_string(node.value, string_constants)
                if value is not None:
                    string_constants[target.id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                value = _static_import_string(node.value, string_constants)
                if value is not None:
                    string_constants[node.target.id] = value
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    importlib_aliases.add(alias.asname or "importlib")
        elif isinstance(node, ast.ImportFrom) and node.module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    import_module_aliases.add(alias.asname or alias.name)
    alias_assignments = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
    ]
    changed = True
    while changed:
        changed = False
        for node in alias_assignments:
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if value is None:
                continue
            if isinstance(value, ast.Name) and value.id in getattr_aliases:
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in getattr_aliases:
                        getattr_aliases.add(target.id)
                        changed = True
            if isinstance(value, ast.Name) and value.id in importlib_aliases:
                for target in targets:
                    if isinstance(target, ast.Name) and target.id not in importlib_aliases:
                        importlib_aliases.add(target.id)
                        changed = True
            is_import_callable = _is_dynamic_import_callable(
                value,
                getattr_aliases=getattr_aliases,
                importlib_aliases=importlib_aliases,
                import_module_aliases=import_module_aliases,
            )
            if not is_import_callable:
                continue
            for target in targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id not in import_module_aliases
                ):
                    import_module_aliases.add(target.id)
                    changed = True
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.append(node.module)
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Call):
            dynamic_import = _is_dynamic_import_callable(
                node.func,
                getattr_aliases=getattr_aliases,
                importlib_aliases=importlib_aliases,
                import_module_aliases=import_module_aliases,
            )
            if dynamic_import:
                if not node.args:
                    raise SuccessorControlError(
                        f"consumed source dynamic import is unresolved: {relative_path}"
                    )
                target = _static_import_string(node.args[0], string_constants)
                if target is None:
                    raise SuccessorControlError(
                        f"consumed source dynamic import is unresolved: {relative_path}"
                    )
                imported_names.append(target)
    if any("card_acceptance_empirical_successor" in name for name in imported_names):
        raise SuccessorControlError(
            f"consumed source imports successor: {relative_path}"
        )


def _observe_preserved_directory(root: Path, relative_path: object) -> dict[str, Any]:
    relative = _preservation_relative_path(relative_path, "artifact root")
    directory = root.joinpath(*PurePosixPath(relative).parts)
    cursor = root
    for part in PurePosixPath(relative).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise SuccessorControlError(
                f"artifact root path contains a symlink: {relative}"
            )
    if not directory.is_dir():
        raise SuccessorControlError(f"artifact root is missing: {relative}")
    try:
        candidates = sorted(
            directory.rglob("*"),
            key=lambda path: path.relative_to(directory).as_posix(),
        )
        entries: list[dict[str, Any]] = []
        total_file_bytes = 0
        directory_count = 0
        file_count = 0
        for path in candidates:
            entry_path = path.relative_to(directory).as_posix()
            if path.is_symlink():
                raise SuccessorControlError(
                    f"artifact root contains a symlink: {relative}/{entry_path}"
                )
            if path.is_dir():
                directory_count += 1
                entries.append({"path": entry_path, "type": "directory"})
            elif path.is_file():
                payload = path.read_bytes()
                file_count += 1
                total_file_bytes += len(payload)
                entries.append(
                    {
                        "path": entry_path,
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "size_bytes": len(payload),
                        "type": "file",
                    }
                )
            else:
                raise SuccessorControlError(
                    f"artifact root contains a non-file entry: {relative}/{entry_path}"
                )
    except OSError as exc:
        raise SuccessorControlError(
            f"artifact root cannot be observed: {relative}"
        ) from exc
    inventory_payload = canonical_json_bytes(entries)[:-1]
    return {
        "directory_count": directory_count,
        "directory_inventory_sha256": hashlib.sha256(inventory_payload).hexdigest(),
        "entries": entries,
        "file_count": file_count,
        "root": relative,
        "total_file_bytes": total_file_bytes,
    }


def _preservation_git_command(root: Path, args: Sequence[str]) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SuccessorControlError(
            f"preservation Git {' '.join(args)} failed: {stderr}"
        )
    return completed.stdout


def _verify_preservation_git_boundary(root: Path, manifest_payload: bytes) -> None:
    try:
        top_level = Path(
            _preservation_git_command(root, ["rev-parse", "--show-toplevel"])
            .decode("utf-8", errors="strict")
            .strip()
        ).resolve()
        baseline_commit = CONSUMED_EVIDENCE_PRESERVATION_BASELINE[
            "source_commit"
        ]
        baseline_tree = (
            _preservation_git_command(
                root,
                ["rev-parse", f"{baseline_commit}^{{tree}}"],
            )
            .decode("ascii", errors="strict")
            .strip()
        )
        publication_commit = CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_COMMIT
        publication_tree = (
            _preservation_git_command(
                root,
                ["rev-parse", f"{publication_commit}^{{tree}}"],
            )
            .decode("ascii", errors="strict")
            .strip()
        )
        parents = (
            _preservation_git_command(
                root,
                ["show", "-s", "--format=%P", publication_commit],
            )
            .decode("ascii", errors="strict")
            .strip()
            .split()
        )
    except UnicodeDecodeError as exc:
        raise SuccessorControlError("preservation Git identity is not decodable") from exc
    if top_level != root:
        raise SuccessorControlError("preservation root is not the Git top level")
    if baseline_tree != CONSUMED_EVIDENCE_PRESERVATION_BASELINE["source_tree"]:
        raise SuccessorControlError("preservation baseline Git tree mismatch")
    if publication_tree != CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_TREE:
        raise SuccessorControlError("preservation publication Git tree mismatch")
    if parents != [baseline_commit]:
        raise SuccessorControlError("preservation publication parent mismatch")
    committed_manifest = _preservation_git_command(
        root,
        [
            "show",
            f"{publication_commit}:{CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_PATH}",
        ],
    )
    if committed_manifest != manifest_payload:
        raise SuccessorControlError("preservation publication manifest mismatch")
    _preservation_git_command(
        root,
        [
            "merge-base",
            "--is-ancestor",
            publication_commit,
            CONSUMED_EVIDENCE_PRESERVATION_BASELINE["remote_ref"],
        ],
    )


def verify_consumed_evidence_preservation(
    repo_root: Path | str,
) -> dict[str, Any]:
    """Reobserve the fixed consumed evidence without importing its modules."""
    root = Path(repo_root).resolve()
    if not root.is_dir():
        raise SuccessorControlError("preservation repository root is missing")
    manifest_payload = _read_preserved_file(
        root,
        CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_PATH,
        "preservation manifest",
    )
    _verify_preservation_git_boundary(root, manifest_payload)
    try:
        manifest = json.loads(
            manifest_payload.decode("ascii"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SuccessorControlError("preservation manifest is not canonical JSON") from exc
    if not isinstance(manifest, Mapping):
        raise SuccessorControlError("preservation manifest must be a mapping")
    manifest = dict(manifest)
    if manifest_payload != canonical_json_bytes(manifest):
        raise SuccessorControlError("preservation manifest is not canonical JSON")
    _require_fields(
        manifest,
        {
            "artifact_files",
            "artifact_roots",
            "baseline",
            "closed_artifact_file_paths",
            "closed_artifact_root_paths",
            "closed_source_paths",
            "created_at_utc",
            "directory_inventory_schema",
            "manifest_id",
            "manifest_sha256",
            "schema_version",
            "source_files",
        },
        "preservation manifest",
    )
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    observed_manifest_sha256 = hashlib.sha256(
        canonical_json_bytes(body)[:-1]
    ).hexdigest()
    if manifest.get("manifest_sha256") != observed_manifest_sha256:
        raise SuccessorControlError("preservation manifest self digest mismatch")
    if observed_manifest_sha256 != CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_SHA256:
        raise SuccessorControlError("reviewed preservation manifest digest mismatch")
    if manifest.get("schema_version") != CONSUMED_EVIDENCE_PRESERVATION_SCHEMA_VERSION:
        raise SuccessorControlError("preservation manifest schema mismatch")
    if manifest.get("manifest_id") != CONSUMED_EVIDENCE_PRESERVATION_MANIFEST_ID:
        raise SuccessorControlError("preservation manifest identity mismatch")
    if manifest.get("directory_inventory_schema") != (
        CONSUMED_EVIDENCE_DIRECTORY_INVENTORY_SCHEMA
    ):
        raise SuccessorControlError("preservation directory schema mismatch")
    if manifest.get("baseline") != CONSUMED_EVIDENCE_PRESERVATION_BASELINE:
        raise SuccessorControlError("preservation baseline mismatch")
    _timestamp(manifest.get("created_at_utc"), "preservation creation timestamp")

    expected_path_sections = (
        (
            "closed_source_paths",
            CONSUMED_EVIDENCE_PRESERVATION_SOURCE_PATHS,
            "closed source",
        ),
        (
            "closed_artifact_file_paths",
            CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_FILE_PATHS,
            "closed artifact file",
        ),
        (
            "closed_artifact_root_paths",
            CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_ROOT_PATHS,
            "closed artifact root",
        ),
    )
    for key, expected, label in expected_path_sections:
        if manifest.get(key) != list(expected):
            raise SuccessorControlError(f"{label} path array mismatch")

    file_sections = (
        (
            "source_files",
            CONSUMED_EVIDENCE_PRESERVATION_SOURCE_PATHS,
            "consumed source",
            True,
        ),
        (
            "artifact_files",
            CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_FILE_PATHS,
            "consumed artifact file",
            False,
        ),
    )
    for key, paths, label, reject_import in file_sections:
        rows = manifest.get(key)
        if not isinstance(rows, list) or len(rows) != len(paths):
            raise SuccessorControlError(f"{label} row count mismatch")
        if any(not isinstance(row, Mapping) for row in rows):
            raise SuccessorControlError(f"{label} row is invalid")
        if [row.get("path") for row in rows] != list(paths):
            raise SuccessorControlError(f"{label} row order mismatch")
        for expected_row, relative_path in zip(rows, paths, strict=True):
            payload = _read_preserved_file(root, relative_path, label)
            observed_row = _preservation_file_binding(relative_path, payload)
            if dict(expected_row) != observed_row:
                raise SuccessorControlError(f"{label} bytes mismatch: {relative_path}")
            if reject_import:
                _reject_successor_import(relative_path, payload)

    root_rows = manifest.get("artifact_roots")
    root_paths = CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_ROOT_PATHS
    if not isinstance(root_rows, list) or len(root_rows) != len(root_paths):
        raise SuccessorControlError("artifact root row count mismatch")
    if any(not isinstance(row, Mapping) for row in root_rows):
        raise SuccessorControlError("artifact root row is invalid")
    if [row.get("root") for row in root_rows] != list(root_paths):
        raise SuccessorControlError("artifact root row order mismatch")
    for expected_row, relative_path in zip(root_rows, root_paths, strict=True):
        observed_row = _observe_preserved_directory(root, relative_path)
        if dict(expected_row) != observed_row:
            raise SuccessorControlError(f"artifact root inventory mismatch: {relative_path}")

    return {
        "artifact_file_count": len(
            CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_FILE_PATHS
        ),
        "artifact_root_count": len(
            CONSUMED_EVIDENCE_PRESERVATION_ARTIFACT_ROOT_PATHS
        ),
        "baseline_source_commit": CONSUMED_EVIDENCE_PRESERVATION_BASELINE[
            "source_commit"
        ],
        "baseline_source_tree": CONSUMED_EVIDENCE_PRESERVATION_BASELINE[
            "source_tree"
        ],
        "manifest_sha256": observed_manifest_sha256,
        "publication_commit": CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_COMMIT,
        "publication_tree": CONSUMED_EVIDENCE_PRESERVATION_PUBLICATION_TREE,
        "pushed_remote_ref": CONSUMED_EVIDENCE_PRESERVATION_BASELINE["remote_ref"],
        "source_file_count": len(CONSUMED_EVIDENCE_PRESERVATION_SOURCE_PATHS),
        "verified": True,
    }


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


def _normalize_file_binding(value: object, label: str) -> dict[str, Any]:
    binding = _copy_mapping(value, label)
    _require_fields(binding, {"path", "sha256", "size_bytes"}, label)
    binding["path"] = _canonical_absolute_path(binding["path"], f"{label} path")
    binding["sha256"] = _digest(binding["sha256"], f"{label} identity")
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise SuccessorControlError(f"{label} size is invalid")
    return binding


def _normalize_directory_tree_binding(value: object, label: str) -> dict[str, Any]:
    binding = _copy_mapping(value, label)
    _require_fields(
        binding,
        {"file_count", "root", "sha256", "size_bytes"},
        label,
    )
    binding["root"] = _canonical_absolute_path(binding["root"], f"{label} root")
    binding["sha256"] = _digest(binding["sha256"], f"{label} identity")
    for name in ("file_count", "size_bytes"):
        item = binding[name]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise SuccessorControlError(f"{label} {name} is invalid")
    return binding


def _normalize_isolation_identity(value: object) -> dict[str, Any]:
    identity = _copy_mapping(value, "production isolation identity")
    _require_fields(
        identity,
        {"communication_mod_config", "production_checkpoints"},
        "production isolation identity",
    )
    return {
        "communication_mod_config": _normalize_file_binding(
            identity["communication_mod_config"],
            "CommunicationMod configuration",
        ),
        "production_checkpoints": _normalize_directory_tree_binding(
            identity["production_checkpoints"],
            "production checkpoint inventory",
        ),
    }


def _control_target_document(
    *,
    checkpoint: Mapping[str, Any],
    configuration: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "candidate_enabled": False,
        "checkpoint": _normalize_file_binding(
            checkpoint,
            "control checkpoint",
        ),
        "configuration": _normalize_file_binding(
            configuration,
            "control configuration",
        ),
        "schema_version": EXPERIMENT_TARGET_SCHEMA_VERSION,
        "selected_arm": "control",
    }
    return {**body, "target_sha256": canonical_json_sha256(body)}


def build_rollback_authority(
    *,
    target_relative_path: str,
    control_checkpoint: Mapping[str, Any],
    control_configuration: Mapping[str, Any],
    production_isolation: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind the sole local control target and read-only production identities."""
    relative = _managed_relative_path(target_relative_path)
    if relative == ROLLBACK_OBSERVATION_FILENAME:
        raise SuccessorControlError("rollback target conflicts with evidence path")
    body = {
        "candidate_disabled_value": False,
        "control_target": _control_target_document(
            checkpoint=control_checkpoint,
            configuration=control_configuration,
        ),
        "production_isolation": _normalize_isolation_identity(
            production_isolation
        ),
        "schema_version": ROLLBACK_AUTHORITY_SCHEMA_VERSION,
        "target_relative_path": relative,
        "trigger_classes": list(ROLLBACK_TRIGGER_CLASSES),
    }
    return {**body, "rollback_authority_sha256": canonical_json_sha256(body)}


def validate_rollback_authority(value: Mapping[str, Any]) -> dict[str, Any]:
    authority = _copy_mapping(value, "rollback authority")
    _require_fields(
        authority,
        {
            "candidate_disabled_value",
            "control_target",
            "production_isolation",
            "rollback_authority_sha256",
            "schema_version",
            "target_relative_path",
            "trigger_classes",
        },
        "rollback authority",
    )
    if (
        authority["schema_version"] != ROLLBACK_AUTHORITY_SCHEMA_VERSION
        or authority["candidate_disabled_value"] is not False
        or authority["trigger_classes"] != list(ROLLBACK_TRIGGER_CLASSES)
    ):
        raise SuccessorControlError("rollback authority contract mismatch")
    target = _copy_mapping(authority["control_target"], "control target")
    _require_fields(
        target,
        {
            "candidate_enabled",
            "checkpoint",
            "configuration",
            "schema_version",
            "selected_arm",
            "target_sha256",
        },
        "control target",
    )
    normalized_target = _control_target_document(
        checkpoint=target["checkpoint"],
        configuration=target["configuration"],
    )
    if target != normalized_target:
        raise SuccessorControlError("rollback control target mismatch")
    normalized = {
        "candidate_disabled_value": False,
        "control_target": normalized_target,
        "production_isolation": _normalize_isolation_identity(
            authority["production_isolation"]
        ),
        "schema_version": ROLLBACK_AUTHORITY_SCHEMA_VERSION,
        "target_relative_path": _managed_relative_path(
            authority["target_relative_path"]
        ),
        "trigger_classes": list(ROLLBACK_TRIGGER_CLASSES),
    }
    if normalized["target_relative_path"] == ROLLBACK_OBSERVATION_FILENAME:
        raise SuccessorControlError("rollback target conflicts with evidence path")
    digest = _digest(
        authority["rollback_authority_sha256"],
        "rollback authority identity",
    )
    if digest != canonical_json_sha256(normalized):
        raise SuccessorControlError("rollback authority identity mismatch")
    return {**normalized, "rollback_authority_sha256": digest}


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


def _normalize_external_human_provenance(value: object) -> dict[str, str]:
    provenance = _copy_mapping(value, "external-human grant provenance")
    _require_fields(
        provenance,
        {"message_id", "source", "task_id"},
        "external-human grant provenance",
    )
    if provenance["source"] != "external-human-message":
        raise SuccessorControlError("grant provenance is not external human input")
    return {
        "message_id": _nonempty_string(
            provenance["message_id"],
            "grant provenance message id",
        ),
        "source": "external-human-message",
        "task_id": _nonempty_string(
            provenance["task_id"],
            "grant provenance task id",
        ),
    }


def validate_standing_delegation(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate, but never create or amend, one external-human standing grant."""
    delegation = _copy_mapping(value, "standing delegation")
    _require_fields(
        delegation,
        {
            "delegation_sha256",
            "exclusions",
            "grant",
            "revocation",
            "schema_version",
            "scope",
        },
        "standing delegation",
    )
    if delegation["schema_version"] != STANDING_DELEGATION_SCHEMA_VERSION:
        raise SuccessorControlError("standing delegation schema mismatch")
    if delegation["exclusions"] != list(STANDING_DELEGATION_EXCLUSIONS):
        raise SuccessorControlError("standing delegation exclusions mismatch")
    if delegation["revocation"] != STANDING_DELEGATION_REVOCATION:
        raise SuccessorControlError("standing delegation revocation mismatch")
    grant = _copy_mapping(delegation["grant"], "standing delegation grant")
    _require_fields(
        grant,
        {"granted_at", "provenance", "verbatim_text"},
        "standing delegation grant",
    )
    _timestamp(grant["granted_at"], "standing delegation grant timestamp")
    normalized_grant = {
        "granted_at": grant["granted_at"],
        "provenance": _normalize_external_human_provenance(grant["provenance"]),
        "verbatim_text": _nonempty_string(
            grant["verbatim_text"],
            "standing delegation verbatim grant text",
        ),
    }
    if normalized_grant != STANDING_DELEGATION_GRANT:
        raise SuccessorControlError(
            "standing delegation grant differs from immutable external-human grant"
        )
    scope = _copy_mapping(delegation["scope"], "standing delegation scope")
    _require_fields(
        scope,
        {"pushed_remote_ref", "registration_id_prefix", "request_class"},
        "standing delegation scope",
    )
    expected_scope = {
        "pushed_remote_ref": "origin/master",
        "registration_id_prefix": DELEGATED_REGISTRATION_ID_PREFIX,
        "request_class": DELEGATED_REQUEST_CLASS,
    }
    if scope != expected_scope:
        raise SuccessorControlError("standing delegation scope mismatch")
    normalized = {
        "exclusions": list(STANDING_DELEGATION_EXCLUSIONS),
        "grant": normalized_grant,
        "revocation": STANDING_DELEGATION_REVOCATION,
        "schema_version": STANDING_DELEGATION_SCHEMA_VERSION,
        "scope": expected_scope,
    }
    digest = _digest(
        delegation["delegation_sha256"],
        "standing delegation identity",
    )
    if digest != canonical_json_sha256(normalized):
        raise SuccessorControlError("standing delegation identity mismatch")
    return {**normalized, "delegation_sha256": digest}


def _normalize_message_watermark(value: object, label: str) -> dict[str, str]:
    watermark = _copy_mapping(value, label)
    _require_fields(
        watermark,
        {"message_id", "message_timestamp", "task_id"},
        label,
    )
    _timestamp(watermark["message_timestamp"], f"{label} timestamp")
    return {
        "message_id": _nonempty_string(
            watermark["message_id"],
            f"{label} message id",
        ),
        "message_timestamp": watermark["message_timestamp"],
        "task_id": _nonempty_string(
            watermark["task_id"],
            f"{label} task id",
        ),
    }


def validate_revocation_observation(
    value: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    delegation: Mapping[str, Any],
    phase: str,
) -> dict[str, Any]:
    """Validate one externally supplied current-conversation trust observation."""
    if phase not in {"approval", "launch"}:
        raise SuccessorControlError("revocation observation phase is invalid")
    normalized_request = validate_stage_request(request)
    normalized_delegation = validate_standing_delegation(delegation)
    observation = _copy_mapping(value, "revocation observation")
    _require_fields(
        observation,
        {
            "authoritative_state_available",
            "authority_mode",
            "checked_at",
            "delegation_sha256",
            "latest_human_message_watermark",
            "observation_sha256",
            "phase",
            "request_sha256",
            "revocation_message_watermark",
            "revocation_observed",
            "schema_version",
            "stage",
        },
        "revocation observation",
    )
    if (
        observation["schema_version"] != REVOCATION_OBSERVATION_SCHEMA_VERSION
        or observation["authority_mode"] != "standing-delegation"
        or observation["phase"] != phase
        or observation["stage"] != normalized_request["stage"]
        or observation["request_sha256"] != normalized_request["request_sha256"]
        or observation["delegation_sha256"]
        != normalized_delegation["delegation_sha256"]
    ):
        raise SuccessorControlError("revocation observation binding mismatch")
    if type(observation["authoritative_state_available"]) is not bool or type(
        observation["revocation_observed"]
    ) is not bool:
        raise SuccessorControlError("revocation observation booleans are invalid")
    checked_at = _timestamp(
        observation["checked_at"],
        "revocation observation checked-at timestamp",
    )
    latest = _normalize_message_watermark(
        observation["latest_human_message_watermark"],
        "latest human-message watermark",
    )
    grant = normalized_delegation["grant"]
    grant_time = _timestamp(grant["granted_at"], "standing grant timestamp")
    latest_time = _timestamp(
        latest["message_timestamp"],
        "latest human-message timestamp",
    )
    if latest["task_id"] != grant["provenance"]["task_id"]:
        raise SuccessorControlError(
            "revocation observation task provenance mismatch"
        )
    if checked_at < latest_time or latest_time < grant_time or checked_at <= grant_time:
        raise SuccessorControlError("revocation observation watermark is stale")
    revocation_watermark = observation["revocation_message_watermark"]
    if observation["revocation_observed"]:
        normalized_revocation = _normalize_message_watermark(
            revocation_watermark,
            "revocation message watermark",
        )
        if normalized_revocation["task_id"] != grant["provenance"]["task_id"]:
            raise SuccessorControlError("revocation task provenance mismatch")
    elif revocation_watermark is not None:
        raise SuccessorControlError("non-revoked observation names a revocation")
    else:
        normalized_revocation = None
    normalized = {
        "authoritative_state_available": observation[
            "authoritative_state_available"
        ],
        "authority_mode": "standing-delegation",
        "checked_at": observation["checked_at"],
        "delegation_sha256": normalized_delegation["delegation_sha256"],
        "latest_human_message_watermark": latest,
        "phase": phase,
        "request_sha256": normalized_request["request_sha256"],
        "revocation_message_watermark": normalized_revocation,
        "revocation_observed": observation["revocation_observed"],
        "schema_version": REVOCATION_OBSERVATION_SCHEMA_VERSION,
        "stage": normalized_request["stage"],
    }
    digest = _digest(
        observation["observation_sha256"],
        "revocation observation identity",
    )
    if digest != canonical_json_sha256(normalized):
        raise SuccessorControlError("revocation observation identity mismatch")
    if observation["authoritative_state_available"] is not True:
        raise SuccessorControlError(
            "authoritative current-conversation state is unavailable"
        )
    if observation["revocation_observed"] is not False:
        raise SuccessorControlError("explicit human revocation was observed")
    return {**normalized, "observation_sha256": digest}


def bind_delegated_approval(
    *,
    request: Mapping[str, Any],
    request_review_sha256: str,
    delegation: Mapping[str, Any],
    approval_observation: Mapping[str, Any],
    resolved_at: str,
) -> dict[str, Any]:
    """Resolve one immutable standing grant to one exact reviewed request."""
    normalized_request = validate_stage_request(request)
    normalized_delegation = validate_standing_delegation(delegation)
    normalized_observation = validate_revocation_observation(
        approval_observation,
        request=normalized_request,
        delegation=normalized_delegation,
        phase="approval",
    )
    _timestamp(resolved_at, "delegated approval resolution timestamp")
    if resolved_at != normalized_observation["checked_at"]:
        raise SuccessorControlError(
            "delegated approval resolution lacks a fresh approval observation"
        )
    review_digest = _digest(
        request_review_sha256,
        "delegated request review identity",
    )
    resolution = {
        "approval_observation_sha256": normalized_observation[
            "observation_sha256"
        ],
        "delegation_sha256": normalized_delegation["delegation_sha256"],
        "request_review_sha256": review_digest,
        "request_sha256": normalized_request["request_sha256"],
        "resolved_at": resolved_at,
        "resolver": DELEGATED_APPROVAL_RESOLVER,
    }
    body = {
        "approval_mode": "standing-delegation",
        "approval_observation": normalized_observation,
        "approved_request_sha256": normalized_request["request_sha256"],
        "delegation": normalized_delegation,
        "request_review_sha256": review_digest,
        "resolution": resolution,
        "schema_version": DELEGATED_APPROVAL_SCHEMA_VERSION,
        "stage": normalized_request["stage"],
    }
    return {**body, "approval_sha256": canonical_json_sha256(body)}


def validate_delegated_approval(
    value: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    approval = _copy_mapping(value, "delegated approval")
    _require_fields(
        approval,
        {
            "approval_mode",
            "approval_observation",
            "approval_sha256",
            "approved_request_sha256",
            "delegation",
            "request_review_sha256",
            "resolution",
            "schema_version",
            "stage",
        },
        "delegated approval",
    )
    if (
        approval["schema_version"] != DELEGATED_APPROVAL_SCHEMA_VERSION
        or approval["approval_mode"] != "standing-delegation"
    ):
        raise SuccessorControlError("delegated approval schema or mode mismatch")
    resolution = _copy_mapping(
        approval["resolution"],
        "delegated approval resolution",
    )
    _require_fields(
        resolution,
        {
            "approval_observation_sha256",
            "delegation_sha256",
            "request_review_sha256",
            "request_sha256",
            "resolved_at",
            "resolver",
        },
        "delegated approval resolution",
    )
    expected = bind_delegated_approval(
        request=request,
        request_review_sha256=approval["request_review_sha256"],
        delegation=approval["delegation"],
        approval_observation=approval["approval_observation"],
        resolved_at=resolution["resolved_at"],
    )
    if approval != expected:
        raise SuccessorControlError("delegated approval binding mismatch")
    return approval


def _external_approval_message_record(
    *,
    approval_text: str,
    approved_at: str,
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    _timestamp(approved_at, "external approval timestamp")
    body = {
        "approved_at": approved_at,
        "provenance": _normalize_external_human_provenance(provenance),
        "schema_version": EXTERNAL_APPROVAL_MESSAGE_SCHEMA_VERSION,
        "verbatim_approval_text": _nonempty_string(
            approval_text,
            "verbatim external approval text",
        ),
    }
    return {**body, "approval_message_sha256": canonical_json_sha256(body)}


def _validate_external_approval_message(value: object) -> dict[str, Any]:
    message = _copy_mapping(value, "external approval message")
    _require_fields(
        message,
        {
            "approval_message_sha256",
            "approved_at",
            "provenance",
            "schema_version",
            "verbatim_approval_text",
        },
        "external approval message",
    )
    if message["schema_version"] != EXTERNAL_APPROVAL_MESSAGE_SCHEMA_VERSION:
        raise SuccessorControlError("external approval message schema mismatch")
    expected = _external_approval_message_record(
        approval_text=message["verbatim_approval_text"],
        approved_at=message["approved_at"],
        provenance=message["provenance"],
    )
    if message != expected:
        raise SuccessorControlError("external approval message identity mismatch")
    return message


def validate_external_revocation_observation(
    value: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    approval_message: Mapping[str, Any],
    phase: str,
) -> dict[str, Any]:
    """Validate current conversation state anchored to one human approval message."""
    if phase not in {"approval", "launch"}:
        raise SuccessorControlError("external revocation observation phase is invalid")
    normalized_request = validate_stage_request(request)
    normalized_message = _validate_external_approval_message(approval_message)
    observation = _copy_mapping(value, "external revocation observation")
    _require_fields(
        observation,
        {
            "approval_message_sha256",
            "authoritative_state_available",
            "authority_mode",
            "checked_at",
            "latest_human_message_watermark",
            "observation_sha256",
            "phase",
            "request_sha256",
            "revocation_message_watermark",
            "revocation_observed",
            "schema_version",
            "stage",
        },
        "external revocation observation",
    )
    if (
        observation["schema_version"]
        != EXTERNAL_REVOCATION_OBSERVATION_SCHEMA_VERSION
        or observation["authority_mode"] != "external-human-approval"
        or observation["phase"] != phase
        or observation["stage"] != normalized_request["stage"]
        or observation["request_sha256"] != normalized_request["request_sha256"]
        or observation["approval_message_sha256"]
        != normalized_message["approval_message_sha256"]
    ):
        raise SuccessorControlError("external revocation observation binding mismatch")
    if type(observation["authoritative_state_available"]) is not bool or type(
        observation["revocation_observed"]
    ) is not bool:
        raise SuccessorControlError(
            "external revocation observation booleans are invalid"
        )
    checked_at = _timestamp(
        observation["checked_at"],
        "external revocation checked-at timestamp",
    )
    latest = _normalize_message_watermark(
        observation["latest_human_message_watermark"],
        "external latest human-message watermark",
    )
    approved_at = _timestamp(
        normalized_message["approved_at"],
        "external approval message timestamp",
    )
    latest_at = _timestamp(
        latest["message_timestamp"],
        "external latest human-message timestamp",
    )
    expected_task = normalized_message["provenance"]["task_id"]
    if latest["task_id"] != expected_task:
        raise SuccessorControlError("external approval task provenance mismatch")
    if checked_at < latest_at or latest_at < approved_at:
        raise SuccessorControlError("external revocation observation watermark is stale")
    revocation_watermark = observation["revocation_message_watermark"]
    if observation["revocation_observed"]:
        normalized_revocation = _normalize_message_watermark(
            revocation_watermark,
            "external revocation message watermark",
        )
        if normalized_revocation["task_id"] != expected_task:
            raise SuccessorControlError("external revocation task provenance mismatch")
    elif revocation_watermark is not None:
        raise SuccessorControlError(
            "non-revoked external observation names a revocation"
        )
    else:
        normalized_revocation = None
    normalized = {
        "approval_message_sha256": normalized_message[
            "approval_message_sha256"
        ],
        "authoritative_state_available": observation[
            "authoritative_state_available"
        ],
        "authority_mode": "external-human-approval",
        "checked_at": observation["checked_at"],
        "latest_human_message_watermark": latest,
        "phase": phase,
        "request_sha256": normalized_request["request_sha256"],
        "revocation_message_watermark": normalized_revocation,
        "revocation_observed": observation["revocation_observed"],
        "schema_version": EXTERNAL_REVOCATION_OBSERVATION_SCHEMA_VERSION,
        "stage": normalized_request["stage"],
    }
    digest = _digest(
        observation["observation_sha256"],
        "external revocation observation identity",
    )
    if digest != canonical_json_sha256(normalized):
        raise SuccessorControlError(
            "external revocation observation identity mismatch"
        )
    if observation["authoritative_state_available"] is not True:
        raise SuccessorControlError(
            "authoritative current-conversation state is unavailable"
        )
    if observation["revocation_observed"] is not False:
        raise SuccessorControlError("explicit human revocation was observed")
    return {**normalized, "observation_sha256": digest}


def _external_bound_request_terms(request: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_stage_request(request)
    return {
        "configuration_identity": copy.deepcopy(
            normalized["configuration_identity"]
        ),
        "downstream_authority": copy.deepcopy(
            normalized["downstream_authority"]
        ),
        "execution_authority": copy.deepcopy(normalized["execution_authority"]),
        "exclusions": copy.deepcopy(normalized["exclusions"]),
        "output_root": normalized["output_root"],
        "prerequisite_bindings": copy.deepcopy(
            normalized["prerequisite_bindings"]
        ),
        "pushed_remote_ref": "origin/master",
        "repository_id": REPOSITORY_ID,
        "request_class": STAGE_REQUEST_SCHEMA_VERSION,
        "request_id": normalized["request_id"],
        "request_sha256": normalized["request_sha256"],
        "resources": copy.deepcopy(normalized["resources"]),
        "source_commit": normalized["source_commit"],
        "source_inventory_sha256": normalized["source_inventory_sha256"],
        "stage": normalized["stage"],
    }


def bind_external_human_approval(
    *,
    request: Mapping[str, Any],
    request_review_sha256: str,
    request_published_at: str,
    approval_text: str,
    approved_at: str,
    provenance: Mapping[str, Any],
    approval_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one post-request external-human message to exactly one request."""
    normalized_request = validate_stage_request(request)
    published_at = _timestamp(
        request_published_at,
        "stage request publication timestamp",
    )
    approved_time = _timestamp(approved_at, "external approval timestamp")
    if approved_time <= published_at:
        raise SuccessorControlError(
            "external approval must postdate the published request"
        )
    text = _nonempty_string(approval_text, "verbatim external approval text")
    if text.count(normalized_request["request_sha256"]) != 1:
        raise SuccessorControlError(
            "external approval text must name the exact request digest once"
        )
    message = _external_approval_message_record(
        approval_text=text,
        approved_at=approved_at,
        provenance=provenance,
    )
    observation = validate_external_revocation_observation(
        approval_observation,
        request=normalized_request,
        approval_message=message,
        phase="approval",
    )
    review_digest = _digest(
        request_review_sha256,
        "external approval request review identity",
    )
    body = {
        "approval_message": message,
        "approval_mode": "external-human-approval",
        "approval_observation": observation,
        "approved_request_sha256": normalized_request["request_sha256"],
        "bound_request_terms": _external_bound_request_terms(normalized_request),
        "request_published_at": request_published_at,
        "request_review_sha256": review_digest,
        "schema_version": EXTERNAL_HUMAN_APPROVAL_SCHEMA_VERSION,
        "stage": normalized_request["stage"],
    }
    return {**body, "approval_sha256": canonical_json_sha256(body)}


def validate_external_human_approval(
    value: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    approval = _copy_mapping(value, "external-human approval")
    _require_fields(
        approval,
        {
            "approval_message",
            "approval_mode",
            "approval_observation",
            "approval_sha256",
            "approved_request_sha256",
            "bound_request_terms",
            "request_published_at",
            "request_review_sha256",
            "schema_version",
            "stage",
        },
        "external-human approval",
    )
    if (
        approval["schema_version"] != EXTERNAL_HUMAN_APPROVAL_SCHEMA_VERSION
        or approval["approval_mode"] != "external-human-approval"
    ):
        raise SuccessorControlError("external-human approval schema or mode mismatch")
    message = _validate_external_approval_message(approval["approval_message"])
    expected = bind_external_human_approval(
        request=request,
        request_review_sha256=approval["request_review_sha256"],
        request_published_at=approval["request_published_at"],
        approval_text=message["verbatim_approval_text"],
        approved_at=message["approved_at"],
        provenance=message["provenance"],
        approval_observation=approval["approval_observation"],
    )
    if approval != expected:
        raise SuccessorControlError("external-human approval binding mismatch")
    return approval


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


def validate_delegated_stage_launch(
    *,
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    delegated_approval: Mapping[str, Any],
    launch_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Require a fresh non-revoked observation before any delegated stage launch."""
    normalized_request = validate_stage_request(request)
    normalized_approval = validate_delegated_approval(
        delegated_approval,
        normalized_request,
    )
    normalized_authorization = validate_stage_authorization(
        authorization,
        normalized_request,
    )
    if (
        normalized_authorization["approval_record_sha256"]
        != normalized_approval["approval_sha256"]
        or normalized_authorization["request_review_sha256"]
        != normalized_approval["request_review_sha256"]
    ):
        raise SuccessorControlError(
            "delegated stage authorization approval binding mismatch"
        )
    normalized_launch = validate_revocation_observation(
        launch_observation,
        request=normalized_request,
        delegation=normalized_approval["delegation"],
        phase="launch",
    )
    approval_observation = normalized_approval["approval_observation"]
    launch_checked = _timestamp(
        normalized_launch["checked_at"],
        "launch revocation checked-at timestamp",
    )
    approval_checked = _timestamp(
        approval_observation["checked_at"],
        "approval revocation checked-at timestamp",
    )
    launch_watermark = _timestamp(
        normalized_launch["latest_human_message_watermark"][
            "message_timestamp"
        ],
        "launch human-message watermark timestamp",
    )
    approval_watermark = _timestamp(
        approval_observation["latest_human_message_watermark"][
            "message_timestamp"
        ],
        "approval human-message watermark timestamp",
    )
    if launch_checked < approval_checked or launch_watermark < approval_watermark:
        raise SuccessorControlError("delegated launch watermark is stale")
    return normalized_launch


def validate_external_human_stage_launch(
    *,
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    external_approval: Mapping[str, Any],
    launch_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Recheck an exact external-human authority after authorization publication."""
    normalized_request = validate_stage_request(request)
    normalized_approval = validate_external_human_approval(
        external_approval,
        normalized_request,
    )
    normalized_authorization = validate_stage_authorization(
        authorization,
        normalized_request,
    )
    if (
        normalized_authorization["approval_record_sha256"]
        != normalized_approval["approval_sha256"]
        or normalized_authorization["request_review_sha256"]
        != normalized_approval["request_review_sha256"]
    ):
        raise SuccessorControlError(
            "external-human stage authorization approval binding mismatch"
        )
    normalized_launch = validate_external_revocation_observation(
        launch_observation,
        request=normalized_request,
        approval_message=normalized_approval["approval_message"],
        phase="launch",
    )
    approval_observation = normalized_approval["approval_observation"]
    launch_checked = _timestamp(
        normalized_launch["checked_at"],
        "external launch checked-at timestamp",
    )
    approval_checked = _timestamp(
        approval_observation["checked_at"],
        "external approval checked-at timestamp",
    )
    launch_watermark = _timestamp(
        normalized_launch["latest_human_message_watermark"][
            "message_timestamp"
        ],
        "external launch human-message watermark timestamp",
    )
    approval_watermark = _timestamp(
        approval_observation["latest_human_message_watermark"][
            "message_timestamp"
        ],
        "external approval human-message watermark timestamp",
    )
    if launch_checked < approval_checked or launch_watermark < approval_watermark:
        raise SuccessorControlError("external-human launch watermark is stale")
    return normalized_launch


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
    """Own one validated stage tuple and optional launch authority exactly once."""

    __slots__ = (
        "_authority_observation",
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
        authority_observation: _FrozenExecutionDict | None,
        stage: str,
    ) -> None:
        object.__setattr__(self, "_registration", registration)
        object.__setattr__(self, "_request", request)
        object.__setattr__(self, "_authorization", authorization)
        object.__setattr__(self, "_authority_observation", authority_observation)
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
    def authority_observation(self) -> Mapping[str, Any] | None:
        return self._authority_observation

    @property
    def stage(self) -> str:
        return self._stage


def _build_validated_execution_context(
    *,
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    registration_validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    authority_observation: Mapping[str, Any] | None = None,
    authority_observation_validator: Callable[
        [Mapping[str, Any]], Mapping[str, Any]
    ]
    | None = None,
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
    if (authority_observation is None) != (authority_observation_validator is None):
        raise SuccessorControlError(
            "execution authority observation and validator must be paired"
        )
    normalized_authority_observation: dict[str, Any] | None = None
    if authority_observation is not None:
        if not callable(authority_observation_validator):
            raise SuccessorControlError(
                "execution authority observation validator is invalid"
            )
        try:
            normalized_authority_observation = _copy_mapping(
                authority_observation_validator(authority_observation),
                "validated execution authority observation",
            )
        except SuccessorControlError:
            raise
        except Exception as exc:
            raise SuccessorControlError(
                "execution authority observation validation failed"
            ) from exc
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
    frozen_authority_observation = (
        _freeze_execution_value(normalized_authority_observation)
        if normalized_authority_observation is not None
        else None
    )
    if not all(
        type(value) is _FrozenExecutionDict
        for value in (frozen_registration, frozen_request, frozen_authorization)
    ) or (
        frozen_authority_observation is not None
        and type(frozen_authority_observation) is not _FrozenExecutionDict
    ):
        raise SuccessorControlError("execution context ownership failed")
    return _ValidatedExecutionContext(
        registration=frozen_registration,
        request=frozen_request,
        authorization=frozen_authorization,
        authority_observation=frozen_authority_observation,
        stage=normalized_request["stage"],
    )


def _build_delegated_execution_context(
    *,
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    delegated_approval: Mapping[str, Any],
    launch_observation: Mapping[str, Any],
    registration_validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> _ValidatedExecutionContext:
    """Freeze a validated launch observation into every delegated lifecycle ID."""
    return _build_validated_execution_context(
        registration=registration,
        request=request,
        authorization=authorization,
        registration_validator=registration_validator,
        authority_observation=launch_observation,
        authority_observation_validator=lambda value: (
            validate_delegated_stage_launch(
                request=request,
                authorization=authorization,
                delegated_approval=delegated_approval,
                launch_observation=value,
            )
        ),
    )


def _build_external_human_execution_context(
    *,
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    external_approval: Mapping[str, Any],
    launch_observation: Mapping[str, Any],
    registration_validator: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> _ValidatedExecutionContext:
    """Freeze exact external-human launch authority into the lifecycle identity."""
    return _build_validated_execution_context(
        registration=registration,
        request=request,
        authorization=authorization,
        registration_validator=registration_validator,
        authority_observation=launch_observation,
        authority_observation_validator=lambda value: (
            validate_external_human_stage_launch(
                request=request,
                authorization=authorization,
                external_approval=external_approval,
                launch_observation=value,
            )
        ),
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


def _context_identity(context: _ValidatedExecutionContext) -> dict[str, str]:
    identity = {
        "authorization_sha256": _digest(
            context.authorization["authorization_sha256"],
            "context authorization identity",
        ),
        "registration_sha256": _digest(
            context.registration["registration_sha256"],
            "context registration identity",
        ),
        "request_sha256": _digest(
            context.request["request_sha256"],
            "context request identity",
        ),
        "stage": context.stage,
    }
    if context.authority_observation is not None:
        identity["launch_authority_sha256"] = _digest(
            context.authority_observation["observation_sha256"],
            "context launch authority identity",
        )
    return identity


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


def _parse_canonical_mapping(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except SuccessorControlError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SuccessorControlError(f"{label} is invalid") from exc
    normalized = _copy_mapping(value, label)
    if payload != canonical_json_bytes(normalized):
        raise SuccessorControlError(f"{label} is not canonical")
    return normalized


def _positive_process_id(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SuccessorControlError(f"{label} must be a positive integer")
    return value


class ExecutionLease:
    """Exclusive child-process ownership with explicit dead-owner recovery."""

    def __init__(
        self,
        output_path: Path | str,
        *,
        context: _ValidatedExecutionContext,
        child_process_id: int,
        process_alive: Callable[[int], bool],
        allow_stale_reclaim: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.output_path = Path(output_path).resolve()
        self.context = _require_execution_context(context)
        self.child_process_id = _positive_process_id(
            child_process_id,
            "lease child process id",
        )
        if not callable(process_alive) or not callable(clock):
            raise SuccessorControlError("lease observers must be callable")
        if type(allow_stale_reclaim) is not bool:
            raise SuccessorControlError("allow_stale_reclaim must be boolean")
        self.process_alive = process_alive
        self.allow_stale_reclaim = allow_stale_reclaim
        self.clock = clock
        self.path = self.output_path / LEASE_FILENAME
        self.owner: dict[str, Any] | None = None
        self.reclaimed_owner: dict[str, Any] | None = None
        self.started_monotonic: float | None = None
        self._handle: Any | None = None
        self.held = False

    def __enter__(self) -> "ExecutionLease":
        if self.held:
            return self
        key = os.path.normcase(str(self.path))
        if key in _ACTIVE_EXECUTION_LEASES:
            raise SuccessorControlError("execution lease is already held")
        try:
            child_alive = self.process_alive(self.child_process_id)
        except Exception as exc:
            raise SuccessorControlError("execution lease child liveness failed") from exc
        if child_alive is not True:
            raise SuccessorControlError(
                "execution lease child process is not alive"
            )
        if self.output_path.exists() and not self.path.exists():
            raise SuccessorControlError(
                "preexisting output root lacks an execution lease"
            )
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
                raise SuccessorControlError(
                    "execution lease is already held"
                ) from exc
            handle.seek(0)
            raw = handle.read()
            existing: dict[str, Any] | None = None
            if raw not in {b"", b"\0"}:
                existing = _parse_canonical_mapping(raw, "execution lease")
                if existing.get("schema_version") != LEASE_SCHEMA_VERSION:
                    raise SuccessorControlError("execution lease schema mismatch")
                if existing.get("identity") != _context_identity(self.context):
                    raise SuccessorControlError("execution lease identity mismatch")
                if not self.allow_stale_reclaim:
                    raise SuccessorControlError(
                        "preexisting execution lease requires recovery"
                    )
                old_owner = _copy_mapping(
                    existing.get("owner"),
                    "execution lease owner",
                )
                old_pid = _positive_process_id(
                    old_owner.get("child_process_id"),
                    "lease owner child process id",
                )
                try:
                    old_alive = self.process_alive(old_pid)
                except Exception as exc:
                    raise SuccessorControlError(
                        "execution lease owner liveness failed"
                    ) from exc
                if old_alive is not False:
                    raise SuccessorControlError(
                        "execution lease child owner is still alive"
                    )
                ambiguous = sorted(
                    path.name
                    for path in self.output_path.iterdir()
                    if path.name.startswith(".") and path.name.endswith(".tmp")
                )
                if ambiguous:
                    raise SuccessorControlError(
                        "stale execution lease has ambiguous temporary output"
                    )
                self.reclaimed_owner = old_owner
            started = float(self.clock())
            if not math.isfinite(started) or started < 0.0:
                raise SuccessorControlError("lease monotonic clock is invalid")
            self.started_monotonic = started
            self.owner = {
                "acquired_monotonic": started,
                "child_process_id": self.child_process_id,
                "token": uuid.uuid4().hex,
            }
            payload = {
                "identity": _context_identity(self.context),
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

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        handle = self._handle
        key = os.path.normcase(str(self.path))
        self._handle = None
        self.held = False
        _ACTIVE_EXECUTION_LEASES.discard(key)
        if handle is None:
            return
        try:
            handle.seek(0)
            payload = _parse_canonical_mapping(handle.read(), "execution lease")
            if (
                payload.get("identity") != _context_identity(self.context)
                or payload.get("owner") != self.owner
            ):
                raise SuccessorControlError("execution lease identity drifted")
        finally:
            try:
                _unlock_file(handle)
            finally:
                handle.close()


def _require_execution_lease(
    context: _ValidatedExecutionContext, lease: ExecutionLease
) -> tuple[_ValidatedExecutionContext, Path]:
    normalized_context = _require_execution_context(context)
    if (
        not isinstance(lease, ExecutionLease)
        or not lease.held
        or lease.context is not normalized_context
    ):
        raise SuccessorControlError("matching execution lease is not held")
    return normalized_context, lease.output_path


def _atomic_write_once_or_identical(path: Path, payload: bytes) -> bytes:
    if not isinstance(payload, bytes):
        raise SuccessorControlError("write-once artifact payload must be bytes")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SuccessorControlError(
            f"write-once artifact parent cannot be created: {path.name}"
        ) from exc
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise SuccessorControlError(
            f"write-once artifact has ambiguous staging: {path.name}"
        )
    if path.exists():
        try:
            existing = path.read_bytes()
        except OSError as exc:
            raise SuccessorControlError(
                f"write-once artifact cannot be read: {path.name}"
            ) from exc
        if existing != payload:
            raise SuccessorControlError(
                f"write-once artifact drifted: {path.name}"
            )
        return existing
    created_temporary = False
    try:
        with temporary.open("xb") as handle:
            created_temporary = True
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        temporary.unlink()
        created_temporary = False
    except BaseException as exc:
        try:
            if created_temporary:
                temporary.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, SuccessorControlError):
            raise
        raise SuccessorControlError(
            f"write-once artifact publication failed: {path.name}"
        ) from exc
    return payload


def _require_terminal_publication_open(output: Path) -> None:
    for name in _TERMINAL_PUBLICATION_FILENAMES:
        path = output / name
        if path.with_name(f".{path.name}.tmp").exists():
            raise SuccessorControlError(
                f"terminal publication has ambiguous staging: {name}"
            )
        if path.exists():
            raise SuccessorControlError("terminal publication is closed")


def deterministic_gzip_bytes(payload: bytes) -> bytes:
    """Return one gzip member with fixed filename and timestamp metadata."""
    if not isinstance(payload, bytes):
        raise SuccessorControlError("gzip payload must be bytes")
    buffer = io.BytesIO()
    with gzip.GzipFile(
        fileobj=buffer,
        mode="wb",
        filename="",
        mtime=0,
    ) as handle:
        handle.write(payload)
    return buffer.getvalue()


def _publication_byte_limits() -> dict[str, int]:
    limits = _limits()
    return {
        "max_artifact_bytes": int(limits["max_artifact_bytes"]),
        "max_stored_bytes": int(limits["max_stored_bytes"]),
        "max_uncompressed_bytes": int(limits["max_uncompressed_bytes"]),
    }


def _artifact_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise SuccessorControlError("artifact path is invalid")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or pure.as_posix() != value
        or value.endswith("/")
        or any(part in {"", ".", ".."} for part in pure.parts)
        or any(part.startswith(".") and part.endswith(".tmp") for part in pure.parts)
    ):
        raise SuccessorControlError("artifact path is invalid")
    return value


def _managed_relative_path(value: object) -> str:
    relative = _artifact_relative_path(value)
    if relative in {LEASE_FILENAME, *_TERMINAL_PUBLICATION_FILENAMES}:
        raise SuccessorControlError("managed artifact path is invalid")
    return relative


def _managed_artifact_target(output: Path, relative_path: object) -> tuple[str, Path]:
    relative = _managed_relative_path(relative_path)
    pure = PurePosixPath(relative)
    target = output.joinpath(*pure.parts)
    cursor = output
    for part in pure.parts:
        cursor = cursor / part
        if cursor.exists() and cursor.is_symlink():
            raise SuccessorControlError("managed artifact path contains a symlink")
    return relative, target


def _artifact_binding(relative_path: str, path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SuccessorControlError(
            f"managed artifact is not a regular file: {relative_path}"
        )
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise SuccessorControlError(
            f"managed artifact cannot be read: {relative_path}"
        ) from exc
    return {
        "path": relative_path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _bounded_deterministic_gzip_payload(
    stored: bytes,
    *,
    max_uncompressed_bytes: int,
) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as stream:
            uncompressed = stream.read(max_uncompressed_bytes + 1)
            trailing_output = b"" if len(uncompressed) > max_uncompressed_bytes else stream.read(1)
    except (EOFError, gzip.BadGzipFile, OSError) as exc:
        raise SuccessorControlError("managed gzip artifact is invalid") from exc
    if len(uncompressed) > max_uncompressed_bytes or trailing_output:
        raise SuccessorControlError(
            "managed artifact exceeds its uncompressed byte ceiling"
        )
    if deterministic_gzip_bytes(uncompressed) != stored:
        raise SuccessorControlError("managed gzip artifact is not deterministic")
    return uncompressed


def _managed_binding_from_bytes(
    relative_path: str,
    stored: bytes,
    *,
    limits: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    relative = _artifact_relative_path(relative_path)
    if not isinstance(stored, bytes):
        raise SuccessorControlError("managed artifact payload must be bytes")
    active_limits = dict(_publication_byte_limits() if limits is None else limits)
    max_artifact = active_limits["max_artifact_bytes"]
    if len(stored) > max_artifact:
        raise SuccessorControlError("managed artifact exceeds its byte ceiling")
    if relative.endswith(".gz"):
        uncompressed = _bounded_deterministic_gzip_payload(
            stored,
            max_uncompressed_bytes=max_artifact,
        )
        encoding = "deterministic-gzip-v1"
    else:
        uncompressed = stored
        encoding = "identity-bytes-v1"
    if len(uncompressed) > max_artifact:
        raise SuccessorControlError("managed artifact exceeds its byte ceiling")
    return {
        "encoding": encoding,
        "path": relative,
        "stored_sha256": hashlib.sha256(stored).hexdigest(),
        "stored_size_bytes": len(stored),
        "uncompressed_sha256": hashlib.sha256(uncompressed).hexdigest(),
        "uncompressed_size_bytes": len(uncompressed),
    }


def _managed_artifact_binding(relative_path: str, path: Path) -> dict[str, Any]:
    relative = _artifact_relative_path(relative_path)
    if path.is_symlink() or not path.is_file():
        raise SuccessorControlError(
            f"managed artifact is not a regular file: {relative}"
        )
    limits = _publication_byte_limits()
    try:
        if path.stat().st_size > limits["max_artifact_bytes"]:
            raise SuccessorControlError(
                "managed artifact exceeds its byte ceiling"
            )
        stored = path.read_bytes()
    except OSError as exc:
        raise SuccessorControlError(
            f"managed artifact cannot be read: {relative}"
        ) from exc
    return _managed_binding_from_bytes(relative, stored, limits=limits)


def _validate_artifact_budget_rows(
    artifacts: Sequence[Mapping[str, Any]],
    *,
    limits: Mapping[str, int] | None = None,
) -> tuple[list[dict[str, Any]], int, int]:
    active_limits = dict(_publication_byte_limits() if limits is None else limits)
    normalized: list[dict[str, Any]] = []
    paths: list[str] = []
    stored_total = 0
    uncompressed_total = 0
    fields = {
        "encoding",
        "path",
        "stored_sha256",
        "stored_size_bytes",
        "uncompressed_sha256",
        "uncompressed_size_bytes",
    }
    for value in artifacts:
        row = _copy_mapping(value, "artifact budget row")
        _require_fields(row, fields, "artifact budget row")
        row["path"] = _artifact_relative_path(row["path"])
        if row["encoding"] not in {
            "identity-bytes-v1",
            "deterministic-gzip-v1",
        }:
            raise SuccessorControlError("artifact encoding is invalid")
        _digest(row["stored_sha256"], "artifact stored digest")
        _digest(row["uncompressed_sha256"], "artifact uncompressed digest")
        for field in ("stored_size_bytes", "uncompressed_size_bytes"):
            size = row[field]
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise SuccessorControlError(f"artifact {field} is invalid")
        if max(row["stored_size_bytes"], row["uncompressed_size_bytes"]) > active_limits[
            "max_artifact_bytes"
        ]:
            raise SuccessorControlError("managed artifact exceeds its byte ceiling")
        if row["encoding"] == "identity-bytes-v1" and (
            row["stored_sha256"] != row["uncompressed_sha256"]
            or row["stored_size_bytes"] != row["uncompressed_size_bytes"]
        ):
            raise SuccessorControlError("identity artifact binding differs")
        paths.append(row["path"])
        stored_total += row["stored_size_bytes"]
        uncompressed_total += row["uncompressed_size_bytes"]
        normalized.append(row)
    if paths != sorted(set(paths)):
        raise SuccessorControlError("artifact paths must be unique and sorted")
    if stored_total > active_limits["max_stored_bytes"]:
        raise SuccessorControlError("managed stored-byte ceiling exceeded")
    if uncompressed_total > active_limits["max_uncompressed_bytes"]:
        raise SuccessorControlError("managed uncompressed-byte ceiling exceeded")
    return normalized, stored_total, uncompressed_total


def _observe_artifact_inventory(
    output: Path, *, excluded_paths: Sequence[str]
) -> dict[str, Any]:
    excluded = set(excluded_paths)
    rows: list[dict[str, Any]] = []
    try:
        candidates = sorted(
            output.rglob("*"),
            key=lambda path: path.relative_to(output).as_posix(),
        )
    except OSError as exc:
        raise SuccessorControlError("managed artifacts cannot be listed") from exc
    for path in candidates:
        relative = path.relative_to(output).as_posix()
        if path.is_symlink():
            raise SuccessorControlError(
                f"managed artifact path contains a symlink: {relative}"
            )
        if path.is_dir():
            continue
        if relative == LEASE_FILENAME or relative in excluded:
            continue
        if path.name.startswith(".") and path.name.endswith(".tmp"):
            raise SuccessorControlError(
                f"managed artifact has ambiguous staging: {relative}"
            )
        rows.append(_managed_artifact_binding(relative, path))
    normalized_rows, stored_total, uncompressed_total = (
        _validate_artifact_budget_rows(rows)
    )
    body = {
        "artifact_count": len(normalized_rows),
        "artifacts": normalized_rows,
        "schema_version": ARTIFACT_INVENTORY_SCHEMA_VERSION,
        "stored_size_bytes": stored_total,
        "uncompressed_size_bytes": uncompressed_total,
    }
    return {**body, "artifact_inventory_sha256": canonical_json_sha256(body)}


def _require_prospective_artifact_budget(
    output: Path,
    *,
    relative_path: str,
    payload: bytes,
) -> dict[str, Any]:
    relative = _artifact_relative_path(relative_path)
    candidate = _managed_binding_from_bytes(relative, payload)
    inventory = _observe_artifact_inventory(output, excluded_paths=(relative,))
    rows = [*inventory["artifacts"], candidate]
    rows.sort(key=lambda row: row["path"])
    _validate_artifact_budget_rows(rows)
    return candidate


def _publish_bounded_artifact(
    output: Path,
    *,
    relative_path: str,
    payload: bytes,
) -> dict[str, Any]:
    binding = _require_prospective_artifact_budget(
        output,
        relative_path=relative_path,
        payload=payload,
    )
    path = output.joinpath(*PurePosixPath(binding["path"]).parts)
    _atomic_write_once_or_identical(path, payload)
    observed = _managed_artifact_binding(binding["path"], path)
    if observed != binding:
        raise SuccessorControlError("managed artifact binding drifted")
    return binding


def publish_managed_artifact(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    relative_path: str,
    payload: bytes,
) -> dict[str, Any]:
    """Atomically publish exact evidence bytes while terminalization is open."""
    context, output = _require_execution_lease(context, lease)
    _execution_context_for_operation(context, "artifact")
    _require_terminal_publication_open(output)
    relative, path = _managed_artifact_target(output, relative_path)
    del path
    return _publish_bounded_artifact(
        output,
        relative_path=relative,
        payload=payload,
    )


def encode_float64_evidence_artifact(
    *,
    relative_path: str,
    rows: Sequence[Sequence[int | float]],
) -> tuple[dict[str, Any], bytes]:
    """Encode bounded rectangular float evidence without inline JSON values."""
    relative = _managed_relative_path(relative_path)
    if not relative.endswith(".gz"):
        raise SuccessorControlError("float64 evidence path must end in .gz")
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise SuccessorControlError("float64 evidence rows are invalid")
    normalized_rows: list[tuple[float, ...]] = []
    column_count: int | None = None
    for row in rows:
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise SuccessorControlError("float64 evidence row is invalid")
        if column_count is None:
            column_count = len(row)
            if column_count == 0:
                raise SuccessorControlError(
                    "float64 evidence column count must be positive"
                )
        elif len(row) != column_count:
            raise SuccessorControlError("float64 evidence must be rectangular")
        values: list[float] = []
        for value in row:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SuccessorControlError("float64 evidence value is invalid")
            normalized = float(value)
            if not math.isfinite(normalized):
                raise SuccessorControlError("float64 evidence values must be finite")
            values.append(normalized)
        normalized_rows.append(tuple(values))
    assert column_count is not None
    element_count = len(normalized_rows) * column_count
    canonical_size = element_count * 8
    if canonical_size > _publication_byte_limits()["max_artifact_bytes"]:
        raise SuccessorControlError("managed artifact exceeds its byte ceiling")
    canonical_buffer = bytearray(canonical_size)
    offset = 0
    for row in normalized_rows:
        for value in row:
            struct.pack_into("<d", canonical_buffer, offset, value)
            offset += 8
    canonical = bytes(canonical_buffer)
    stored = deterministic_gzip_bytes(canonical)
    artifact = _managed_binding_from_bytes(relative, stored)
    metadata = {
        "artifact": artifact,
        "dtype": "float64",
        "element_count": element_count,
        "endian": "little",
        "row_order": "row-major",
        "schema_version": FLOAT64_EVIDENCE_SCHEMA_VERSION,
        "shape": [len(normalized_rows), column_count],
    }
    canonical_json_bytes(metadata)
    return metadata, stored


def validate_resource_and_evidence_budget(
    *,
    artifacts: Sequence[Mapping[str, Any]],
    decisions_per_episode: Sequence[int],
    training_environment_accesses: int,
    canary_environment_accesses: int,
    holdout_environment_accesses: int,
    candidate_optimizer_updates: int,
    control_optimizer_updates: int,
    shadow_optimizer_steps: int,
    charged_seconds: float,
) -> dict[str, Any]:
    """Validate one complete or terminal-prefix resource/evidence budget."""
    if isinstance(artifacts, (str, bytes)) or not isinstance(artifacts, Sequence):
        raise SuccessorControlError("artifact budget rows are invalid")
    normalized_rows, stored_total, uncompressed_total = (
        _validate_artifact_budget_rows(artifacts)
    )
    limits = _limits()
    resource_values = {
        "training_environment_accesses": training_environment_accesses,
        "canary_environment_accesses": canary_environment_accesses,
        "holdout_environment_accesses": holdout_environment_accesses,
        "candidate_optimizer_updates": candidate_optimizer_updates,
        "control_optimizer_updates": control_optimizer_updates,
        "shadow_optimizer_steps": shadow_optimizer_steps,
    }
    resource_ceilings = {
        "training_environment_accesses": limits[
            "max_training_environment_accesses"
        ],
        "canary_environment_accesses": limits["max_canary_environment_accesses"],
        "holdout_environment_accesses": limits[
            "max_holdout_environment_accesses"
        ],
        "candidate_optimizer_updates": limits["max_training_updates_per_arm"],
        "control_optimizer_updates": limits["max_training_updates_per_arm"],
        "shadow_optimizer_steps": limits["max_shadow_optimizer_steps"],
    }
    for name, value in resource_values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SuccessorControlError(
                f"{name.replace('_', ' ')} must be a nonnegative integer"
            )
        if value > resource_ceilings[name]:
            raise SuccessorControlError(
                f"{name.replace('_', ' ')} exceeds its ceiling"
            )
    training_optimizer_steps = (
        candidate_optimizer_updates + control_optimizer_updates
    )
    if training_optimizer_steps > limits["max_training_optimizer_steps"]:
        raise SuccessorControlError("training optimizer steps exceed their ceiling")
    total_environment_accesses = (
        training_environment_accesses
        + canary_environment_accesses
        + holdout_environment_accesses
    )
    if total_environment_accesses > limits["max_environment_accesses"]:
        raise SuccessorControlError("total environment accesses exceed their ceiling")
    if (
        isinstance(charged_seconds, bool)
        or not isinstance(charged_seconds, (int, float))
        or not math.isfinite(float(charged_seconds))
        or charged_seconds < 0.0
    ):
        raise SuccessorControlError("charged seconds are invalid")
    if charged_seconds > limits["max_charged_seconds"]:
        raise SuccessorControlError("charged seconds exceed their ceiling")
    if (
        isinstance(decisions_per_episode, (str, bytes))
        or not isinstance(decisions_per_episode, Sequence)
    ):
        raise SuccessorControlError("decisions per episode are invalid")
    normalized_decisions: list[int] = []
    for value in decisions_per_episode:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise SuccessorControlError("decision count is invalid")
        if value > limits["max_decisions_per_episode"]:
            raise SuccessorControlError("decision count exceeds its ceiling")
        normalized_decisions.append(value)
    if len(normalized_decisions) != total_environment_accesses:
        raise SuccessorControlError(
            "episode count differs from environment accesses"
        )
    return {
        "artifact_count": len(normalized_rows),
        "artifacts": normalized_rows,
        "candidate_optimizer_updates": candidate_optimizer_updates,
        "canary_environment_accesses": canary_environment_accesses,
        "charged_seconds": float(charged_seconds),
        "control_optimizer_updates": control_optimizer_updates,
        "decisions_per_episode": normalized_decisions,
        "episode_count": len(normalized_decisions),
        "holdout_environment_accesses": holdout_environment_accesses,
        "shadow_optimizer_steps": shadow_optimizer_steps,
        "stored_size_bytes": stored_total,
        "total_environment_accesses": total_environment_accesses,
        "training_environment_accesses": training_environment_accesses,
        "training_optimizer_steps": training_optimizer_steps,
        "uncompressed_size_bytes": uncompressed_total,
    }


def _append_durable(output: Path, path: Path, payload: bytes) -> None:
    if not path.is_file() or not payload or not payload.endswith(b"\n"):
        raise SuccessorControlError(f"append target is invalid: {path.name}")
    try:
        relative = path.relative_to(output).as_posix()
        prospective = path.read_bytes() + payload
    except (OSError, ValueError) as exc:
        raise SuccessorControlError(
            f"append target cannot be budgeted: {path.name}"
        ) from exc
    _require_prospective_artifact_budget(
        output,
        relative_path=relative,
        payload=prospective,
    )
    with path.open("ab", buffering=0) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _journal_header(context: _ValidatedExecutionContext) -> dict[str, Any]:
    return {
        "event_index": 0,
        "identity": _context_identity(context),
        "kind": "journal_opened",
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
    }


def initialize_access_journal(
    context: _ValidatedExecutionContext, lease: ExecutionLease
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    _execution_context_for_operation(context, "journal")
    _require_terminal_publication_open(output)
    _publish_bounded_artifact(
        output,
        relative_path=ACCESS_JOURNAL_FILENAME,
        payload=canonical_json_bytes(_journal_header(context)),
    )
    return load_access_journal(context, lease)


def _canonical_json_lines(payload: bytes, label: str) -> list[dict[str, Any]]:
    if not payload or not payload.endswith(b"\n"):
        raise SuccessorControlError(f"{label} is incomplete")
    return [
        _parse_canonical_mapping(line, f"{label} line {index}")
        for index, line in enumerate(payload.splitlines(keepends=True), start=1)
    ]


def load_access_journal(
    context: _ValidatedExecutionContext, lease: ExecutionLease
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    try:
        events = _canonical_json_lines(
            (output / ACCESS_JOURNAL_FILENAME).read_bytes(),
            "access journal",
        )
    except OSError as exc:
        raise SuccessorControlError("access journal cannot be read") from exc
    if events[0] != _journal_header(context):
        raise SuccessorControlError("access journal header mismatch")
    previous = events[0]
    for index, event in enumerate(events[1:], start=1):
        if (
            event.get("schema_version") != ACCESS_JOURNAL_SCHEMA_VERSION
            or event.get("kind") != "environment_access_debited"
            or event.get("event_index") != index
            or event.get("previous_event_sha256")
            != canonical_json_sha256(previous)
            or event.get("stage") != context.stage
        ):
            raise SuccessorControlError("access journal event mismatch")
        seed = event.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise SuccessorControlError("access journal seed is invalid")
        if event.get("arm") not in {"candidate", "control"}:
            raise SuccessorControlError("access journal arm is invalid")
        previous = event
    return {"debited_accesses": len(events) - 1, "events": events}


def perform_journaled_environment_access(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    seed: int,
    arm: str,
    purpose: str,
    access: Callable[[], Any],
) -> Any:
    context, output = _require_execution_lease(context, lease)
    _require_terminal_publication_open(output)
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise SuccessorControlError("environment seed is invalid")
    if arm not in {"candidate", "control"}:
        raise SuccessorControlError("environment arm is invalid")
    if purpose != context.stage or not callable(access):
        raise SuccessorControlError("environment access purpose is invalid")
    journal = load_access_journal(context, lease)
    if journal["debited_accesses"] >= _resource_limits(context)[
        "environment_accesses"
    ]:
        raise SuccessorControlError(
            "environment access would exceed the stage ceiling"
        )
    event = {
        "arm": arm,
        "event_index": journal["debited_accesses"] + 1,
        "kind": "environment_access_debited",
        "previous_event_sha256": canonical_json_sha256(journal["events"][-1]),
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
        "seed": seed,
        "stage": context.stage,
    }
    _append_durable(
        output,
        output / ACCESS_JOURNAL_FILENAME,
        canonical_json_bytes(event),
    )
    return access()


def _zero_resources() -> dict[str, int | float]:
    return {
        "charged_seconds": 0.0,
        "environment_accesses": 0,
        "optimizer_steps": 0,
        "shadow_optimizer_steps": 0,
    }


def _resource_limits(context: _ValidatedExecutionContext) -> dict[str, int | float]:
    resources = context.request["resources"]
    return {
        "charged_seconds": float(resources.get("max_charged_seconds", 28_800.0)),
        "environment_accesses": int(resources.get("max_environment_accesses", 0)),
        "optimizer_steps": int(resources.get("max_optimizer_steps", 0)),
        "shadow_optimizer_steps": int(
            resources.get("max_shadow_optimizer_steps", 0)
        ),
    }


def _resource_header(context: _ValidatedExecutionContext) -> dict[str, Any]:
    return {
        "identity": _context_identity(context),
        "kind": "resource_ledger_opened",
        "limits": _resource_limits(context),
        "resources": _zero_resources(),
        "revision": 0,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }


def initialize_resource_ledger(
    context: _ValidatedExecutionContext, lease: ExecutionLease
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    _execution_context_for_operation(context, "resource")
    _require_terminal_publication_open(output)
    _publish_bounded_artifact(
        output,
        relative_path=RESOURCE_LEDGER_FILENAME,
        payload=canonical_json_bytes(_resource_header(context)),
    )
    return load_resource_ledger(context, lease)


def load_resource_ledger(
    context: _ValidatedExecutionContext, lease: ExecutionLease
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    try:
        events = _canonical_json_lines(
            (output / RESOURCE_LEDGER_FILENAME).read_bytes(),
            "resource ledger",
        )
    except OSError as exc:
        raise SuccessorControlError("resource ledger cannot be read") from exc
    if events[0] != _resource_header(context):
        raise SuccessorControlError("resource ledger header mismatch")
    previous = events[0]
    previous_resources = _zero_resources()
    limits = _resource_limits(context)
    for revision, event in enumerate(events[1:], start=1):
        if (
            event.get("schema_version") != RESOURCE_LEDGER_SCHEMA_VERSION
            or event.get("kind") != "resource_prefix_advanced"
            or event.get("revision") != revision
            or event.get("previous_event_sha256")
            != canonical_json_sha256(previous)
        ):
            raise SuccessorControlError("resource ledger event mismatch")
        resources = _copy_mapping(event.get("resources"), "resource prefix")
        for name, old_value in previous_resources.items():
            value = resources.get(name)
            valid_type = (
                isinstance(value, (int, float))
                if name == "charged_seconds"
                else isinstance(value, int)
            )
            if isinstance(value, bool) or not valid_type:
                raise SuccessorControlError("resource prefix value is invalid")
            if not math.isfinite(float(value)) or value < old_value:
                raise SuccessorControlError("resource prefix is not monotonic")
            if value > limits[name]:
                raise SuccessorControlError("resource prefix exceeds stage limit")
        if set(resources) != set(previous_resources):
            raise SuccessorControlError("resource prefix fields mismatch")
        previous_resources = resources
        previous = event
    return {
        "events": events,
        "limits": limits,
        "resources": previous_resources,
        "revision": len(events) - 1,
    }


def advance_resource_ledger(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    charged_seconds: float,
    environment_accesses: int,
    optimizer_steps: int,
    shadow_optimizer_steps: int,
    reason: str,
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    _require_terminal_publication_open(output)
    ledger = load_resource_ledger(context, lease)
    resources: dict[str, int | float] = {
        "charged_seconds": charged_seconds,
        "environment_accesses": environment_accesses,
        "optimizer_steps": optimizer_steps,
        "shadow_optimizer_steps": shadow_optimizer_steps,
    }
    previous = ledger["resources"]
    for name, value in resources.items():
        valid_type = (
            isinstance(value, (int, float))
            if name == "charged_seconds"
            else isinstance(value, int)
        )
        if isinstance(value, bool) or not valid_type:
            raise SuccessorControlError("resource prefix value is invalid")
        if not math.isfinite(float(value)) or value < previous[name]:
            raise SuccessorControlError("resource prefix is not monotonic")
        if value > ledger["limits"][name]:
            raise SuccessorControlError("resource prefix exceeds stage limit")
    journal = load_access_journal(context, lease)
    if environment_accesses > journal["debited_accesses"]:
        raise SuccessorControlError(
            "resource accesses exceed durable journal debits"
        )
    if resources == previous:
        return ledger
    if not isinstance(reason, str) or not reason:
        raise SuccessorControlError("resource advance reason is invalid")
    event = {
        "kind": "resource_prefix_advanced",
        "previous_event_sha256": canonical_json_sha256(ledger["events"][-1]),
        "reason": reason,
        "resources": resources,
        "revision": ledger["revision"] + 1,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }
    _append_durable(
        output,
        output / RESOURCE_LEDGER_FILENAME,
        canonical_json_bytes(event),
    )
    return load_resource_ledger(context, lease)


def reconcile_resource_ledger(
    context: _ValidatedExecutionContext, lease: ExecutionLease
) -> dict[str, Any]:
    context, _ = _require_execution_lease(context, lease)
    ledger = load_resource_ledger(context, lease)
    journal = load_access_journal(context, lease)
    if lease.started_monotonic is None:
        raise SuccessorControlError("execution lease clock is unavailable")
    try:
        now = float(lease.clock())
    except Exception as exc:
        raise SuccessorControlError("resource monotonic clock failed") from exc
    elapsed = now - lease.started_monotonic
    if not math.isfinite(elapsed) or elapsed < 0.0:
        raise SuccessorControlError("resource elapsed time is not monotonic")
    resources = ledger["resources"]
    return advance_resource_ledger(
        context,
        lease,
        charged_seconds=max(float(resources["charged_seconds"]), elapsed),
        environment_accesses=journal["debited_accesses"],
        optimizer_steps=int(resources["optimizer_steps"]),
        shadow_optimizer_steps=int(resources["shadow_optimizer_steps"]),
        reason="journal-and-elapsed-reconciliation",
    )


def publish_write_once_marker(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    kind: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    _require_terminal_publication_open(output)
    if kind == "bootstrap":
        _execution_context_for_operation(context, "checkpoint")
        path = output / "bootstrap.json"
    elif kind == "stage":
        _execution_context_for_operation(context, "stage")
        path = output / "stages" / f"{context.stage}.json"
    else:
        raise SuccessorControlError("write-once marker kind is invalid")
    marker = {
        "identity": _context_identity(context),
        "kind": kind,
        "payload": _copy_mapping(payload, "write-once marker payload"),
        "schema_version": MARKER_SCHEMA_VERSION,
    }
    encoded = canonical_json_bytes(marker)
    _publish_bounded_artifact(
        output,
        relative_path=path.relative_to(output).as_posix(),
        payload=encoded,
    )
    return marker


def _normalize_complete_checkpoint_binding(value: object) -> dict[str, Any]:
    binding = _copy_mapping(value, "complete training checkpoint binding")
    _require_fields(
        binding,
        {
            "checkpoint_sha256",
            "completed_pairs",
            "component_sha256",
            "next_chunk_index",
            "training_environment_accesses",
            "training_optimizer_steps",
        },
        "complete training checkpoint binding",
    )
    index = binding["next_chunk_index"]
    if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index <= 8:
        raise SuccessorControlError("checkpoint chunk index is invalid")
    expected_coordinates = {
        "completed_pairs": index * 64,
        "training_environment_accesses": index * 128,
        "training_optimizer_steps": index * 2,
    }
    for name, expected in expected_coordinates.items():
        value_at_coordinate = binding[name]
        if (
            isinstance(value_at_coordinate, bool)
            or not isinstance(value_at_coordinate, int)
            or value_at_coordinate != expected
        ):
            raise SuccessorControlError(
                "complete training checkpoint coordinate mismatch"
            )
    binding["checkpoint_sha256"] = _digest(
        binding["checkpoint_sha256"],
        "complete training checkpoint identity",
    )
    components = _copy_mapping(
        binding["component_sha256"],
        "complete training checkpoint components",
    )
    if tuple(sorted(components)) != _CHECKPOINT_COMPONENT_NAMES:
        raise SuccessorControlError(
            "complete training checkpoint component fields mismatch"
        )
    binding["component_sha256"] = {
        name: _digest(components[name], f"checkpoint {name} identity")
        for name in _CHECKPOINT_COMPONENT_NAMES
    }
    return binding


def _validate_complete_paired_access_prefix(
    journal: Mapping[str, Any], *, expected_accesses: int
) -> None:
    if journal["debited_accesses"] != expected_accesses or expected_accesses % 128:
        raise SuccessorControlError(
            "partial training chunk cannot be replayed"
        )
    events = journal["events"][1:]
    previous_seed: int | None = None
    for index in range(0, len(events), 2):
        candidate = events[index]
        control = events[index + 1]
        seed = candidate["seed"]
        if (
            candidate["arm"] != "candidate"
            or control["arm"] != "control"
            or control["seed"] != seed
            or (previous_seed is not None and seed <= previous_seed)
        ):
            raise SuccessorControlError(
                "training access prefix differs from paired seed order"
            )
        previous_seed = seed


def _checkpoint_marker(
    context: _ValidatedExecutionContext,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "binding": _normalize_complete_checkpoint_binding(binding),
        "identity": _context_identity(context),
        "schema_version": TRAINING_CHECKPOINT_BINDING_SCHEMA_VERSION,
    }


def publish_complete_training_checkpoint(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish one complete-boundary checkpoint binding or exact same bytes."""
    context, output = _require_execution_lease(context, lease)
    _execution_context_for_operation(context, "checkpoint")
    _require_terminal_publication_open(output)
    if context.stage != "training":
        raise SuccessorControlError("training checkpoint requires training stage")
    marker = _checkpoint_marker(context, binding)
    coordinates = marker["binding"]
    journal = load_access_journal(context, lease)
    _validate_complete_paired_access_prefix(
        journal,
        expected_accesses=coordinates["training_environment_accesses"],
    )
    ledger = load_resource_ledger(context, lease)
    resources = ledger["resources"]
    if (
        resources["environment_accesses"]
        != coordinates["training_environment_accesses"]
        or resources["optimizer_steps"]
        != coordinates["training_optimizer_steps"]
        or resources["shadow_optimizer_steps"] != 0
    ):
        raise SuccessorControlError(
            "training checkpoint resource prefix mismatch"
        )
    index = coordinates["next_chunk_index"]
    existing = _load_training_checkpoint_markers(context, output)
    if len(existing) not in {index - 1, index}:
        raise SuccessorControlError("training checkpoint sequence has a gap")
    if len(existing) == index and existing[-1] != marker:
        raise SuccessorControlError("training checkpoint replacement is forbidden")
    path = output / "checkpoints" / f"chunk_{index:04d}.json"
    _publish_bounded_artifact(
        output,
        relative_path=path.relative_to(output).as_posix(),
        payload=canonical_json_bytes(marker),
    )
    return marker


def _load_training_checkpoint_markers(
    context: _ValidatedExecutionContext,
    output: Path,
) -> list[dict[str, Any]]:
    directory = output / "checkpoints"
    if not directory.exists():
        return []
    try:
        paths = sorted(directory.glob("chunk_*.json"))
    except OSError as exc:
        raise SuccessorControlError("training checkpoints cannot be listed") from exc
    markers: list[dict[str, Any]] = []
    for expected_index, path in enumerate(paths, start=1):
        if path.name != f"chunk_{expected_index:04d}.json":
            raise SuccessorControlError("training checkpoint sequence mismatch")
        try:
            marker = _parse_canonical_mapping(
                path.read_bytes(),
                "training checkpoint marker",
            )
        except OSError as exc:
            raise SuccessorControlError(
                "training checkpoint marker cannot be read"
            ) from exc
        _require_fields(
            marker,
            {"binding", "identity", "schema_version"},
            "training checkpoint marker",
        )
        if (
            marker["schema_version"]
            != TRAINING_CHECKPOINT_BINDING_SCHEMA_VERSION
            or marker["identity"] != _context_identity(context)
        ):
            raise SuccessorControlError("training checkpoint marker mismatch")
        normalized = _checkpoint_marker(context, marker["binding"])
        if marker != normalized or normalized["binding"]["next_chunk_index"] != (
            expected_index
        ):
            raise SuccessorControlError("training checkpoint binding mismatch")
        markers.append(marker)
    return markers


def classify_execution_reopen(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Classify only repeated pre-seed setup or the sole complete continuation."""
    context, output = _require_execution_lease(context, lease)
    _require_terminal_publication_open(output)
    if context.stage != "training":
        raise SuccessorControlError("only training setup may reopen")
    for forbidden_stage in ("canary", "holdout"):
        if (output / "stages" / f"{forbidden_stage}.json").exists():
            raise SuccessorControlError(
                "post-canary continuation, retry, or replacement is forbidden"
            )
    continuation_path = output / "training_continuation.json"
    if continuation_path.exists():
        raise SuccessorControlError("training continuation was already used")
    journal = load_access_journal(context, lease)
    if journal["debited_accesses"] == 0:
        return {
            "debited_accesses": 0,
            "identity": _context_identity(context),
            "verdict": "pre_seed_setup_reopen",
        }
    checkpoints = _load_training_checkpoint_markers(context, output)
    if not checkpoints:
        raise SuccessorControlError(
            "partial uncheckpointed training chunk cannot be replayed"
        )
    latest = checkpoints[-1]
    binding = latest["binding"]
    if binding["next_chunk_index"] >= 8:
        raise SuccessorControlError(
            "completed training cannot consume a continuation"
        )
    _validate_complete_paired_access_prefix(
        journal,
        expected_accesses=binding["training_environment_accesses"],
    )
    ledger = load_resource_ledger(context, lease)
    resources = ledger["resources"]
    if (
        resources["environment_accesses"]
        != binding["training_environment_accesses"]
        or resources["optimizer_steps"] != binding["training_optimizer_steps"]
        or resources["shadow_optimizer_steps"] != 0
    ):
        raise SuccessorControlError(
            "complete checkpoint resource prefix mismatch"
        )
    return {
        "checkpoint_sha256": binding["checkpoint_sha256"],
        "completed_pairs": binding["completed_pairs"],
        "debited_accesses": journal["debited_accesses"],
        "identity": _context_identity(context),
        "next_chunk_index": binding["next_chunk_index"],
        "verdict": "complete_checkpoint_continuation",
    }


def authorize_training_continuation(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Consume the one manual continuation identity at a complete boundary."""
    context, output = _require_execution_lease(context, lease)
    eligibility = classify_execution_reopen(context, lease)
    if eligibility["verdict"] != "complete_checkpoint_continuation":
        raise SuccessorControlError(
            "pre-seed setup reopen does not consume training continuation"
        )
    marker = {
        **eligibility,
        "schema_version": TRAINING_CONTINUATION_SCHEMA_VERSION,
    }
    path = output / "training_continuation.json"
    if path.exists():
        raise SuccessorControlError("training continuation was already used")
    _publish_bounded_artifact(
        output,
        relative_path=path.relative_to(output).as_posix(),
        payload=canonical_json_bytes(marker),
    )
    return marker


def _read_canonical_document(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise SuccessorControlError(f"{label} publication order is incomplete") from exc
    return _parse_canonical_mapping(payload, label)


def _journal_prefix_binding(
    context: _ValidatedExecutionContext, lease: ExecutionLease
) -> dict[str, Any]:
    journal = load_access_journal(context, lease)
    return {
        "debited_accesses": journal["debited_accesses"],
        "event_count": len(journal["events"]),
        "last_event_sha256": canonical_json_sha256(journal["events"][-1]),
    }


def _resource_prefix_binding(
    context: _ValidatedExecutionContext, lease: ExecutionLease
) -> dict[str, Any]:
    ledger = load_resource_ledger(context, lease)
    return {
        "last_event_sha256": canonical_json_sha256(ledger["events"][-1]),
        "resources": copy.deepcopy(ledger["resources"]),
        "revision": ledger["revision"],
    }


def _terminal_prefix_inventory(output: Path) -> dict[str, Any]:
    return _observe_artifact_inventory(
        output,
        excluded_paths=_TERMINAL_PUBLICATION_FILENAMES,
    )


def _validate_terminal_intent_document(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    intent = _copy_mapping(value, "terminal intent")
    _require_fields(
        intent,
        {
            "artifact_prefix",
            "details",
            "downstream_authority",
            "identity",
            "journal_prefix",
            "resource_prefix",
            "schema_version",
            "terminal_intent_sha256",
            "verdict",
        },
        "terminal intent",
    )
    if intent["schema_version"] != TERMINAL_INTENT_SCHEMA_VERSION:
        raise SuccessorControlError("terminal intent schema mismatch")
    if (
        intent["identity"] != _context_identity(context)
        or intent["downstream_authority"]
        != context.request["downstream_authority"]
    ):
        raise SuccessorControlError("terminal intent identity drifted")
    _identifier(intent["verdict"], "terminal verdict")
    _copy_mapping(intent["details"], "terminal details")
    _copy_mapping(intent["artifact_prefix"], "terminal artifact prefix")
    _copy_mapping(intent["journal_prefix"], "terminal journal prefix")
    _copy_mapping(intent["resource_prefix"], "terminal resource prefix")
    digest = _digest(
        intent["terminal_intent_sha256"],
        "terminal intent identity",
    )
    body = {
        key: item
        for key, item in intent.items()
        if key != "terminal_intent_sha256"
    }
    if digest != canonical_json_sha256(body):
        raise SuccessorControlError("terminal intent identity drifted")
    if intent["artifact_prefix"] != _terminal_prefix_inventory(output):
        raise SuccessorControlError("terminal intent artifact prefix drifted")
    if intent["journal_prefix"] != _journal_prefix_binding(context, lease):
        raise SuccessorControlError("terminal intent journal prefix drifted")
    if intent["resource_prefix"] != _resource_prefix_binding(context, lease):
        raise SuccessorControlError("terminal intent resource prefix drifted")
    return intent


def _stored_terminal_intent(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    supplied: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    path = output / TERMINAL_INTENT_FILENAME
    stored = _read_canonical_document(path, "terminal intent")
    if supplied is not None:
        normalized_supplied = _copy_mapping(supplied, "terminal intent")
        if canonical_json_bytes(normalized_supplied) != canonical_json_bytes(stored):
            raise SuccessorControlError(
                "supplied terminal intent differs from published bytes"
            )
    return _validate_terminal_intent_document(context, lease, stored)


def publish_terminal_intent(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    verdict: str,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    """Reconcile final resources and freeze the complete pre-terminal prefix."""
    context, output = _require_execution_lease(context, lease)
    _execution_context_for_operation(context, "terminal")
    _require_terminal_publication_open(output)
    normalized_verdict = _identifier(verdict, "terminal verdict")
    normalized_details = _copy_mapping(details, "terminal details")
    reconcile_resource_ledger(context, lease)
    body = {
        "artifact_prefix": _terminal_prefix_inventory(output),
        "details": normalized_details,
        "downstream_authority": _copy_mapping(
            context.request["downstream_authority"],
            "terminal downstream authority",
        ),
        "identity": _context_identity(context),
        "journal_prefix": _journal_prefix_binding(context, lease),
        "resource_prefix": _resource_prefix_binding(context, lease),
        "schema_version": TERMINAL_INTENT_SCHEMA_VERSION,
        "verdict": normalized_verdict,
    }
    intent = {
        **body,
        "terminal_intent_sha256": canonical_json_sha256(body),
    }
    _publish_bounded_artifact(
        output,
        relative_path=TERMINAL_INTENT_FILENAME,
        payload=canonical_json_bytes(intent),
    )
    return intent


def _expected_terminal_document(intent: Mapping[str, Any]) -> dict[str, Any]:
    body = {
        "artifact_prefix_sha256": intent["artifact_prefix"][
            "artifact_inventory_sha256"
        ],
        "details": copy.deepcopy(intent["details"]),
        "downstream_authority": copy.deepcopy(intent["downstream_authority"]),
        "identity": copy.deepcopy(intent["identity"]),
        "journal_prefix": copy.deepcopy(intent["journal_prefix"]),
        "resource_prefix": copy.deepcopy(intent["resource_prefix"]),
        "schema_version": TERMINAL_SCHEMA_VERSION,
        "terminal_intent_sha256": intent["terminal_intent_sha256"],
        "verdict": intent["verdict"],
    }
    return {**body, "terminal_sha256": canonical_json_sha256(body)}


def publish_terminal_document(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    terminal_intent: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish the terminal document only from the exact durable intent."""
    context, output = _require_execution_lease(context, lease)
    _execution_context_for_operation(context, "terminal")
    manifest = output / MANIFEST_FILENAME
    if manifest.exists() or manifest.with_name(f".{manifest.name}.tmp").exists():
        raise SuccessorControlError("terminal publication order is closed")
    intent = _stored_terminal_intent(context, lease, terminal_intent)
    terminal = _expected_terminal_document(intent)
    _publish_bounded_artifact(
        output,
        relative_path=TERMINAL_FILENAME,
        payload=canonical_json_bytes(terminal),
    )
    return terminal


def _stored_terminal_document(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    supplied: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context, output = _require_execution_lease(context, lease)
    stored = _read_canonical_document(output / TERMINAL_FILENAME, "terminal")
    if supplied is not None:
        normalized_supplied = _copy_mapping(supplied, "terminal")
        if canonical_json_bytes(normalized_supplied) != canonical_json_bytes(stored):
            raise SuccessorControlError(
                "supplied terminal differs from published bytes"
            )
    intent = _stored_terminal_intent(context, lease)
    expected = _expected_terminal_document(intent)
    if stored != expected:
        raise SuccessorControlError("terminal document drifted")
    return stored


def publish_artifact_manifest(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    terminal_document: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Close managed evidence by publishing the artifact manifest last."""
    context, output = _require_execution_lease(context, lease)
    _execution_context_for_operation(context, "terminal")
    terminal = _stored_terminal_document(context, lease, terminal_document)
    inventory = _observe_artifact_inventory(
        output,
        excluded_paths=(MANIFEST_FILENAME,),
    )
    body = {
        "artifact_inventory": inventory,
        "downstream_authority": _copy_mapping(
            context.request["downstream_authority"],
            "manifest downstream authority",
        ),
        "identity": _context_identity(context),
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "terminal_intent_sha256": terminal["terminal_intent_sha256"],
        "terminal_sha256": terminal["terminal_sha256"],
    }
    manifest = {**body, "manifest_sha256": canonical_json_sha256(body)}
    _publish_bounded_artifact(
        output,
        relative_path=MANIFEST_FILENAME,
        payload=canonical_json_bytes(manifest),
    )
    return manifest


def _observe_control_identities(
    authority: Mapping[str, Any],
    observer: Callable[[Path | str], Mapping[str, Any]],
) -> dict[str, Any]:
    expected = authority["control_target"]
    observed = {
        "checkpoint": _normalize_file_binding(
            observer(expected["checkpoint"]["path"]),
            "observed control checkpoint",
        ),
        "configuration": _normalize_file_binding(
            observer(expected["configuration"]["path"]),
            "observed control configuration",
        ),
    }
    return {
        "matches_registered": observed
        == {
            "checkpoint": expected["checkpoint"],
            "configuration": expected["configuration"],
        },
        "observed": observed,
    }


def _observe_production_isolation(
    authority: Mapping[str, Any],
    file_observer: Callable[[Path | str], Mapping[str, Any]],
    directory_observer: Callable[[Path | str], Mapping[str, Any]],
) -> dict[str, Any]:
    expected = authority["production_isolation"]
    observed = {
        "communication_mod_config": _normalize_file_binding(
            file_observer(expected["communication_mod_config"]["path"]),
            "observed CommunicationMod configuration",
        ),
        "production_checkpoints": _normalize_directory_tree_binding(
            directory_observer(expected["production_checkpoints"]["root"]),
            "observed production checkpoint inventory",
        ),
    }
    return {
        "matches_registered": observed == expected,
        "observed": observed,
    }


def _capture_identity_observation(
    operation: Callable[[], dict[str, Any]], *, label: str
) -> dict[str, Any]:
    try:
        return operation()
    except Exception as exc:
        return {
            "error": f"{label}: {type(exc).__name__}: {exc}",
            "matches_registered": False,
            "observed": None,
        }


def _atomic_replace_rollback_target(path: Path, payload: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SuccessorControlError("rollback target parent cannot be created") from exc
    staging = path.with_name(f".{path.name}{ROLLBACK_TARGET_STAGING_SUFFIX}")
    if staging.exists():
        raise SuccessorControlError("rollback target has ambiguous staging")
    if path.exists():
        try:
            if path.read_bytes() == payload:
                return
        except OSError as exc:
            raise SuccessorControlError("rollback target cannot be read") from exc
    created_staging = False
    try:
        with staging.open("xb") as handle:
            created_staging = True
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staging, path)
        created_staging = False
        if path.read_bytes() != payload:
            raise SuccessorControlError("rollback target verification failed")
    except BaseException as exc:
        try:
            if created_staging:
                staging.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, SuccessorControlError):
            raise
        raise SuccessorControlError("rollback target replacement failed") from exc


def _execute_registered_closeout(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    rollback_authority: Mapping[str, Any],
    classification: Mapping[str, Any],
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
    checkpoint_snapshot_observer: Callable[
        [Path | str], Mapping[str, Any]
    ]
    | None = None,
) -> dict[str, Any]:
    """Restore the registered control target for one classified closeout."""
    context, output = _require_execution_lease(context, lease)
    _execution_context_for_operation(context, "rollback")
    _require_terminal_publication_open(output)
    authority = validate_rollback_authority(rollback_authority)
    if context.registration.get("rollback_authority_sha256") != authority[
        "rollback_authority_sha256"
    ]:
        raise SuccessorControlError("rollback authority is not registered")
    normalized_classification = _copy_mapping(
        classification,
        "terminal closeout classification",
    )
    _require_fields(
        normalized_classification,
        {
            "closeout_kind",
            "failure_paths",
            "outcome_class",
            "rollback_required",
            "trigger_class",
        },
        "terminal closeout classification",
    )
    if normalized_classification["closeout_kind"] == "rollback_failure":
        expected_classification = classify_terminal_closeout(
            failure_paths=normalized_classification["failure_paths"]
        )
    elif normalized_classification["closeout_kind"] == "normal_holdout":
        expected_classification = classify_terminal_closeout(
            outcome_class=normalized_classification["outcome_class"]
        )
        if context.stage != "holdout":
            raise SuccessorControlError(
                "normal closeout requires the holdout stage"
            )
    else:
        raise SuccessorControlError("terminal closeout kind is not registered")
    if normalized_classification != expected_classification:
        raise SuccessorControlError("terminal closeout classification differs")

    relative, target = _managed_artifact_target(
        output,
        authority["target_relative_path"],
    )
    before_target = (
        _artifact_binding(relative, target) if target.exists() else None
    )
    file_observer = external_binding_observer or external_file_binding
    directory_observer = (
        checkpoint_snapshot_observer or snapshot_directory_tree
    )
    control_before = _capture_identity_observation(
        lambda: _observe_control_identities(authority, file_observer),
        label="control identity observation before rollback",
    )
    production_before = _capture_identity_observation(
        lambda: _observe_production_isolation(
            authority,
            file_observer,
            directory_observer,
        ),
        label="production isolation observation before rollback",
    )

    target_bytes = canonical_json_bytes(authority["control_target"])
    _require_prospective_artifact_budget(
        output,
        relative_path=relative,
        payload=target_bytes,
    )
    _atomic_replace_rollback_target(target, target_bytes)
    try:
        restored_target = _parse_canonical_mapping(
            target.read_bytes(),
            "restored control target",
        )
    except OSError as exc:
        raise SuccessorControlError("restored control target cannot be read") from exc
    control_target_verified = restored_target == authority["control_target"]
    if not control_target_verified or restored_target["candidate_enabled"] is not False:
        raise SuccessorControlError("rollback control target verification failed")

    control_after = _capture_identity_observation(
        lambda: _observe_control_identities(authority, file_observer),
        label="control identity observation after rollback",
    )
    production_after = _capture_identity_observation(
        lambda: _observe_production_isolation(
            authority,
            file_observer,
            directory_observer,
        ),
        label="production isolation observation after rollback",
    )
    control_identities_verified = (
        control_before["matches_registered"] is True
        and control_after["matches_registered"] is True
    )
    production_isolation_verified = (
        production_before["matches_registered"] is True
        and production_after["matches_registered"] is True
    )
    is_rollback = normalized_classification["rollback_required"] is True
    if not control_identities_verified:
        status = (
            "rollback_control_identity_failure"
            if is_rollback
            else "normal_closeout_control_identity_failure"
        )
    elif not production_isolation_verified:
        status = (
            "rollback_isolation_failure"
            if is_rollback
            else "normal_closeout_isolation_failure"
        )
    else:
        status = "rollback_verified" if is_rollback else "normal_closeout_verified"
    body = {
        "candidate_enabled": False,
        "closeout_kind": normalized_classification["closeout_kind"],
        "control_identities_after": control_after,
        "control_identities_before": control_before,
        "control_identities_verified": control_identities_verified,
        "control_target_after": _artifact_binding(relative, target),
        "control_target_before": before_target,
        "control_target_verified": control_target_verified,
        "downstream_authority": _copy_mapping(
            context.request["downstream_authority"],
            "rollback downstream authority",
        ),
        "failure_paths": copy.deepcopy(normalized_classification["failure_paths"]),
        "identity": _context_identity(context),
        "outcome_class": normalized_classification["outcome_class"],
        "production_isolation_after": production_after,
        "production_isolation_before": production_before,
        "production_isolation_verified": production_isolation_verified,
        "rollback_authority_sha256": authority["rollback_authority_sha256"],
        "rollback_required": normalized_classification["rollback_required"],
        "schema_version": ROLLBACK_OBSERVATION_SCHEMA_VERSION,
        "status": status,
        "trigger_class": normalized_classification["trigger_class"],
    }
    observation = {
        **body,
        "rollback_observation_sha256": canonical_json_sha256(body),
    }
    publish_managed_artifact(
        context,
        lease,
        relative_path=ROLLBACK_OBSERVATION_FILENAME,
        payload=canonical_json_bytes(observation),
    )
    return observation


def execute_registered_rollback(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    rollback_authority: Mapping[str, Any],
    failure_paths: Sequence[str],
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
    checkpoint_snapshot_observer: Callable[
        [Path | str], Mapping[str, Any]
    ]
    | None = None,
) -> dict[str, Any]:
    """Classify one failure and restore the registered control target."""
    return _execute_registered_closeout(
        context,
        lease,
        rollback_authority=rollback_authority,
        classification=classify_terminal_closeout(failure_paths=failure_paths),
        external_binding_observer=external_binding_observer,
        checkpoint_snapshot_observer=checkpoint_snapshot_observer,
    )


def execute_registered_normal_closeout(
    context: _ValidatedExecutionContext,
    lease: ExecutionLease,
    *,
    rollback_authority: Mapping[str, Any],
    outcome_class: str,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
    checkpoint_snapshot_observer: Callable[
        [Path | str], Mapping[str, Any]
    ]
    | None = None,
) -> dict[str, Any]:
    """Restore the control target after one complete holdout outcome."""
    return _execute_registered_closeout(
        context,
        lease,
        rollback_authority=rollback_authority,
        classification=classify_terminal_closeout(outcome_class=outcome_class),
        external_binding_observer=external_binding_observer,
        checkpoint_snapshot_observer=checkpoint_snapshot_observer,
    )


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
