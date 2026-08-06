"""Source-only controls for the hierarchical simulator-learning successor.

Torch and the native simulator are intentionally absent from this module's
import graph. Execution loads them only after the exact authorization gate.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib
from importlib import metadata as importlib_metadata
import io
import json
import os
import platform
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PLANNING_COMMIT = "9cdeb85066d5ceff8a3ec3fbbb5c2bd4de7fc081"
PREIMPLEMENTATION_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-preimplementation-v1"
)
SEED_INVENTORY_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-seed-inventory-v1"
)
PRESTART_ATTEMPTS_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-prestart-attempts-v1"
)
EVIDENCE_START_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-evidence-start-v1"
)
LEASE_SCHEMA_VERSION = "noncombat-hierarchical-simulator-learning-lease-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-hierarchical-simulator-learning-journal-v1"
AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-authorization-v1"
)
PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-preflight-v1"
)
REGISTRATION_PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-registration-preflight-v1"
)
CHECKPOINT_ENVELOPE_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-checkpoint-envelope-v1"
)
TRAINING_ROWS_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-training-rows-v1"
)
EVALUATION_ARTIFACT_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-evaluation-artifact-v1"
)
FINAL_MODEL_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-final-model-v1"
)
ISOLATION_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-isolation-v1"
)
METRICS_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-terminal-metrics-v1"
)
REPORT_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-terminal-report-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-terminal-v1"
)
TERMINAL_INTENT_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-terminal-intent-v1"
)
RESOURCE_LEDGER_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-resource-ledger-v1"
)
BOOTSTRAP_RUNTIME_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-bootstrap-runtime-v1"
)
MANIFEST_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-artifact-manifest-v1"
)
EXPERIMENT_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-registration-v1"
)
ALGORITHM_VERSION = "hierarchical-family-first-reinforce-v1"
INITIAL_RUNTIME_SHA256 = (
    "f6e79c86e442ad059fb8ec867fb261175ff3d5563b0b679999ef0d13ac4d9c9b"
)
DEFAULT_PREIMPLEMENTATION_PATH = (
    "reports/noncombat_hierarchical_simulator_learning_successor_"
    "20260806_preimplementation.json"
)
DEFAULT_EXPERIMENT_STEM = (
    "noncombat_hierarchical_simulator_learning_successor_20260806"
)
DEFAULT_SEED_INVENTORY_PATH = f"reports/{DEFAULT_EXPERIMENT_STEM}_seed_inventory.json"
DEFAULT_REGISTRATION_PATH = f"reports/{DEFAULT_EXPERIMENT_STEM}_registration.json"
DEFAULT_PREFLIGHT_PATH = f"reports/{DEFAULT_EXPERIMENT_STEM}_preflight.json"
DEFAULT_AUTHORIZATION_PATH = f"reports/{DEFAULT_EXPERIMENT_STEM}_authorization.json"
DEFAULT_OUTPUT_DIRECTORY = f"reports/{DEFAULT_EXPERIMENT_STEM}"

_REGISTERED_OUTPUT_INVENTORY = {
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

PLANNED_SOURCE_FILES = (
    "analysis_scripts/noncombat_hierarchical_simulator_learning_experiment.py",
    "analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py",
    "analysis_scripts/verify_noncombat_hierarchical_simulator_learning_experiment.py",
    "tests/test_noncombat_hierarchical_simulator_learning_experiment.py",
    "tests/test_noncombat_hierarchical_simulator_learning_runtime.py",
)

PLANNING_FILES = {
    "design": (
        "openspec/changes/add-hierarchical-noncombat-simulator-learning-"
        "successor/design.md"
    ),
    "proposal": (
        "openspec/changes/add-hierarchical-noncombat-simulator-learning-"
        "successor/proposal.md"
    ),
    "spec": (
        "openspec/changes/add-hierarchical-noncombat-simulator-learning-"
        "successor/specs/noncombat-hierarchical-simulator-learning-successor/"
        "spec.md"
    ),
    "tasks": (
        "openspec/changes/add-hierarchical-noncombat-simulator-learning-"
        "successor/tasks.md"
    ),
}

EVIDENCE_FILES = {
    "action_family_counterfactual_report": (
        "reports/noncombat_action_family_counterfactual_audit_20260806.json"
    ),
    "action_family_counterfactual_source": (
        "analysis_scripts/noncombat_action_family_counterfactual_audit.py"
    ),
    "action_family_counterfactual_spec": (
        "openspec/specs/noncombat-action-family-counterfactual-audit/spec.md"
    ),
    "action_family_counterfactual_tests": (
        "tests/test_noncombat_action_family_counterfactual_audit.py"
    ),
    "action_family_distribution_report": (
        "reports/noncombat_action_family_distribution_design_20260805.md"
    ),
    "action_family_distribution_source": (
        "analysis_scripts/noncombat_action_family_distribution.py"
    ),
    "action_family_distribution_spec": (
        "openspec/specs/noncombat-action-family-distribution/spec.md"
    ),
    "action_family_distribution_tests": (
        "tests/test_noncombat_action_family_distribution.py"
    ),
    "collapse_audit_report": (
        "reports/noncombat_state_conditioned_card_reward_collapse_audit_20260805.json"
    ),
    "collapse_audit_source": (
        "analysis_scripts/noncombat_state_conditioned_collapse_audit.py"
    ),
    "collapse_audit_spec": (
        "openspec/specs/noncombat-state-conditioned-collapse-audit/spec.md"
    ),
    "consumed_manifest": (
        "reports/noncombat_state_conditioned_simulator_learning_experiment_"
        "20260805/artifact_manifest.json"
    ),
    "consumed_postmortem": (
        "reports/noncombat_state_conditioned_simulator_learning_experiment_"
        "20260805_postmortem.json"
    ),
    "consumed_registration": (
        "reports/noncombat_state_conditioned_simulator_learning_experiment_"
        "20260805_registration.json"
    ),
    "consumed_runner": (
        "analysis_scripts/noncombat_state_conditioned_simulator_learning_"
        "experiment.py"
    ),
    "consumed_spec": (
        "openspec/specs/noncombat-state-conditioned-simulator-learning-"
        "experiment/spec.md"
    ),
    "consumed_tests": (
        "tests/test_noncombat_state_conditioned_simulator_learning_experiment.py"
    ),
    "consumed_verifier": (
        "analysis_scripts/verify_noncombat_state_conditioned_simulator_"
        "learning_experiment.py"
    ),
    "formal_reward_contract": (
        "reports/noncombat_formal_reward_contract_20260802/contract.json"
    ),
    "formal_reward_source": (
        "analysis_scripts/noncombat_formal_reward_contract.py"
    ),
    "formal_reward_spec": (
        "openspec/specs/noncombat-formal-reward-contract/spec.md"
    ),
    "hierarchical_objective_report": (
        "reports/noncombat_hierarchical_policy_objective_contract_20260806.md"
    ),
    "hierarchical_objective_source": (
        "analysis_scripts/noncombat_hierarchical_policy_objective.py"
    ),
    "hierarchical_objective_spec": (
        "openspec/specs/noncombat-hierarchical-policy-objective-contract/spec.md"
    ),
    "hierarchical_objective_tests": (
        "tests/test_noncombat_hierarchical_policy_objective.py"
    ),
    "policy_input_source": (
        "analysis_scripts/noncombat_state_conditioned_policy_input.py"
    ),
    "policy_input_spec": (
        "openspec/specs/noncombat-state-conditioned-policy-input/spec.md"
    ),
    "policy_input_tests": (
        "tests/test_noncombat_state_conditioned_policy_input.py"
    ),
    "project_direction": "docs/project_direction.md",
    "ranker_source": "analysis_scripts/noncombat_state_conditioned_ranker.py",
    "ranker_spec": "openspec/specs/noncombat-state-conditioned-ranker/spec.md",
    "ranker_tests": "tests/test_noncombat_state_conditioned_ranker.py",
    "simulator_adapter_source": "analysis_scripts/noncombat_simulator_adapter.py",
    "simulator_adapter_spec": (
        "openspec/specs/noncombat-simulator-adapter/spec.md"
    ),
    "simulator_adapter_tests": "tests/test_noncombat_simulator_adapter.py",
}

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

_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_EXECUTION_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
_RESERVED_PREVIOUS_HOLDOUT_NAME = (
    "reserved:consumed_state_conditioned_unvisited_holdout"
)
_RESERVED_PREVIOUS_HOLDOUT = tuple(range(71152, 71664))
_ACTIVE_EXECUTION_LEASES: set[str] = set()
_RUNTIME_CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-runtime-checkpoint-v1"
)
_CHUNK_SUMMARY_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-chunk-summary-v1"
)
_TRAINING_SELECTION_MODE = "family-first-then-conditional-v1"
_TERMINAL_VERDICTS = {
    "experiment_blocked",
    "experiment_invalid",
    "experiment_stopped_at_canary",
    "experiment_stopped_during_training_for_family_saturation",
    "experiment_valid_with_floor_only_signal",
    "experiment_valid_with_victory_signal",
    "experiment_valid_without_learning_signal",
}
_JOURNAL_TRANSITIONS = {
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


class ExperimentBlocked(RuntimeError):
    """Raised when a successor control boundary cannot be trusted."""


def canonical_json_bytes(value: Any) -> bytes:
    """Encode deterministic, finite JSON bytes."""
    try:
        text = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ExperimentBlocked(f"value is not canonical JSON: {exc}") from exc
    return (text + "\n").encode("utf-8")


def registration_authority() -> dict[str, bool]:
    """Return the all-false authority used before exact execution approval."""
    return {name: False for name in AUTHORITY_NAMES}


def execution_authority() -> dict[str, bool]:
    """Enable only the separately authorized simulator experiment surface."""
    enabled = {
        "environment_construction_authorized",
        "execution_authorized",
        "fresh_evidence_authorized",
        "model_fitting_authorized",
        "native_loading_authorized",
        "seed_access_authorized",
        "training_authorized",
    }
    return {name: name in enabled for name in AUTHORITY_NAMES}


def registered_output_inventory() -> dict[str, Any]:
    """Return the exact additive artifact inventory frozen at registration."""
    return copy.deepcopy(_REGISTERED_OUTPUT_INVENTORY)


def experiment_contract() -> dict[str, Any]:
    """Return the immutable source-level successor proposal contract."""
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
            "sampling": "family-first-then-conditional-v1",
        },
        "authority": registration_authority(),
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
            "bootstrap_resamples": 10_000,
            "bootstrap_seed": 0,
            "replay_each_episode_once": True,
            "selection": "unique-raw-score-maximum-v1",
            "tie_handling": "fail-closed",
            "unsupported_rate_ceiling": 0.10,
        },
        "identity": {
            "algorithm_version": ALGORITHM_VERSION,
            "device": "cpu",
            "registration_schema_version": EXPERIMENT_SCHEMA_VERSION,
        },
        "limits": {
            "episodes_per_update": 64,
            "max_decisions_per_episode": 500,
            "max_evaluation_episodes": 2560,
            "max_optimizer_updates": 64,
            "max_total_episodes": 6656,
            "max_training_episodes": 4096,
            "max_wall_seconds": 28_800.0,
        },
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


def _canonical_relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ExperimentBlocked("binding path must be a canonical relative path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != value:
        raise ExperimentBlocked("binding path must be a canonical relative path")
    return value


def _git_blob(repo_root: Path, commit: str, path: str) -> bytes:
    if not _COMMIT_RE.fullmatch(commit):
        raise ExperimentBlocked("planning commit is invalid")
    relative = _canonical_relative_path(path)
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExperimentBlocked(f"git binding read failed for {relative}: {message}")
    return completed.stdout


def _git_text(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExperimentBlocked(f"git {' '.join(args)} failed: {message}")
    return completed.stdout.decode("utf-8").strip()


def _git_blob_batch(
    repo_root: Path,
    *,
    repository_commit: str,
    paths: Sequence[str],
) -> dict[str, bytes]:
    ordered = [_canonical_relative_path(path) for path in paths]
    if not ordered:
        return {}
    if not _COMMIT_RE.fullmatch(repository_commit):
        raise ExperimentBlocked("repository commit is invalid")
    request = "".join(
        f"{repository_commit}:{path}\n" for path in ordered
    ).encode("utf-8")
    completed = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo_root,
        input=request,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExperimentBlocked(f"git cat-file --batch failed: {message}")
    output = completed.stdout
    offset = 0
    result: dict[str, bytes] = {}
    for path in ordered:
        line_end = output.find(b"\n", offset)
        if line_end < 0:
            raise ExperimentBlocked("git batch response is truncated")
        header = output[offset:line_end].decode("ascii", errors="strict").split()
        offset = line_end + 1
        if len(header) != 3 or header[1] != "blob" or not header[2].isdigit():
            raise ExperimentBlocked(f"git batch blob header is invalid for {path}")
        size = int(header[2])
        payload = output[offset : offset + size]
        offset += size
        if len(payload) != size or output[offset : offset + 1] != b"\n":
            raise ExperimentBlocked(f"git batch blob is truncated for {path}")
        offset += 1
        result[path] = payload
    if offset != len(output):
        raise ExperimentBlocked("git batch response has trailing bytes")
    return result


def _git_binding(repo_root: Path, commit: str, path: str) -> dict[str, Any]:
    relative = _canonical_relative_path(path)
    payload = _git_blob(repo_root, commit, relative)
    return {
        "path": relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def build_preimplementation_record(
    repo_root: Path | str,
    *,
    planning_commit: str = PLANNING_COMMIT,
) -> dict[str, Any]:
    """Bind planning and prior evidence from one immutable Git tree."""
    root = Path(repo_root).resolve()
    if not _COMMIT_RE.fullmatch(planning_commit):
        raise ExperimentBlocked("planning commit is invalid")
    evidence = {
        name: _git_binding(root, planning_commit, path)
        for name, path in sorted(EVIDENCE_FILES.items())
    }
    planning = {
        name: _git_binding(root, planning_commit, path)
        for name, path in sorted(PLANNING_FILES.items())
    }
    return {
        "authority": registration_authority(),
        "contract": {
            "cohorts_materialized": False,
            "consumed_experiment_immutable": True,
            "environment_constructed": False,
            "native_loaded": False,
            "output_root_materialized": False,
            "seed_accessed": False,
            "source_only": True,
            "training_started": False,
        },
        "evidence": evidence,
        "experiment_contract": experiment_contract(),
        "planned_source_files": list(PLANNED_SOURCE_FILES),
        "planning": {
            "commit": planning_commit,
            "files": planning,
        },
        "schema_version": PREIMPLEMENTATION_SCHEMA_VERSION,
    }


def validate_preimplementation_record(
    value: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Any]:
    """Recompute a preimplementation record from its fixed planning commit."""
    record = copy.deepcopy(dict(value))
    planning = record.get("planning")
    if not isinstance(planning, Mapping):
        raise ExperimentBlocked("preimplementation planning is invalid")
    commit = planning.get("commit")
    if not isinstance(commit, str):
        raise ExperimentBlocked("preimplementation planning commit is invalid")
    expected = build_preimplementation_record(repo_root, planning_commit=commit)
    if record.get("evidence") != expected["evidence"]:
        raise ExperimentBlocked("preimplementation evidence mismatch")
    if record.get("planning") != expected["planning"]:
        raise ExperimentBlocked("preimplementation planning mismatch")
    if canonical_json_bytes(record) != canonical_json_bytes(expected):
        raise ExperimentBlocked("preimplementation record mismatch")
    return record


def publish_preimplementation_record(
    value: Mapping[str, Any], output_path: Path | str
) -> Path:
    """Publish canonical preimplementation bytes exactly once."""
    output = Path(output_path)
    payload = canonical_json_bytes(dict(value))
    _atomic_write_once(output, payload)
    return output


def _nonnegative_seed(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ExperimentBlocked(f"{label} must be a nonnegative integer")
    return value


def _validate_commit(value: object, label: str) -> str:
    if not isinstance(value, str) or not _COMMIT_RE.fullmatch(value):
        raise ExperimentBlocked(f"{label} must be a lowercase Git commit")
    return value


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExperimentBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ExperimentBlocked(f"non-finite JSON constant: {value}")


def _seed_scalars(value: object) -> list[int]:
    result: list[int] = []

    def visit(node: object, seed_context: bool) -> None:
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


def discover_tracked_seed_source_payloads(
    repo_root: Path | str, *, repository_commit: str
) -> dict[str, bytes]:
    """Read seed-bearing tracked JSON only from one fixed Git tree."""
    root = Path(repo_root).resolve()
    if not _COMMIT_RE.fullmatch(repository_commit):
        raise ExperimentBlocked("seed inventory repository commit is invalid")
    ignored = {
        DEFAULT_AUTHORIZATION_PATH,
        DEFAULT_PREFLIGHT_PATH,
        DEFAULT_REGISTRATION_PATH,
        DEFAULT_SEED_INVENTORY_PATH,
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
        candidates.append(_canonical_relative_path(path))
    blobs = _git_blob_batch(
        root,
        repository_commit=repository_commit,
        paths=sorted(candidates),
    )
    result = {}
    for path, payload in blobs.items():
        try:
            value = json.loads(
                payload,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExperimentBlocked(
                f"tracked seed source is invalid JSON: {path}: {exc}"
            ) from exc
        if _seed_scalars(value):
            result[path] = payload
    return result


def build_tracked_seed_exclusion_inventory(
    repo_root: Path | str, *, repository_commit: str
) -> dict[str, Any]:
    payloads = discover_tracked_seed_source_payloads(
        repo_root,
        repository_commit=repository_commit,
    )
    sources = {}
    for path, payload in sorted(payloads.items()):
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
        sources[path] = sorted(set(_seed_scalars(value)))
    return build_seed_exclusion_inventory(
        sources,
        repository_commit=repository_commit,
        source_payloads=payloads,
    )


def verify_tracked_seed_exclusion_inventory(
    inventory: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Any]:
    normalized = _validate_seed_inventory(inventory)
    recomputed = build_tracked_seed_exclusion_inventory(
        repo_root,
        repository_commit=normalized["repository_commit"],
    )
    if canonical_json_bytes(normalized) != canonical_json_bytes(recomputed):
        raise ExperimentBlocked("seed inventory recomputation mismatch")
    return normalized


def build_seed_exclusion_inventory(
    sources: Mapping[str, Sequence[int]],
    *,
    repository_commit: str,
    source_payloads: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Build the fixed exclusion union and always reserve the old holdout."""
    if not _COMMIT_RE.fullmatch(repository_commit):
        raise ExperimentBlocked("seed inventory repository commit is invalid")
    normalized: dict[str, list[int]] = {}
    for name, values in sorted(dict(sources).items()):
        if not isinstance(name, str) or not name:
            raise ExperimentBlocked("seed source names must be nonempty strings")
        if name == _RESERVED_PREVIOUS_HOLDOUT_NAME:
            raise ExperimentBlocked("reserved holdout source is control-owned")
        normalized[name] = sorted(
            {
                _nonnegative_seed(seed, f"seed source {name}")
                for seed in values
            }
        )
    normalized[_RESERVED_PREVIOUS_HOLDOUT_NAME] = list(
        _RESERVED_PREVIOUS_HOLDOUT
    )
    normalized = dict(sorted(normalized.items()))
    payloads = dict(source_payloads or {})
    if set(payloads) - (set(normalized) - {_RESERVED_PREVIOUS_HOLDOUT_NAME}):
        raise ExperimentBlocked("seed source payload names mismatch")
    bindings = {}
    for name, seeds in normalized.items():
        payload = payloads.get(name, canonical_json_bytes(seeds))
        if not isinstance(payload, bytes) or not payload:
            raise ExperimentBlocked("seed source payload must be nonempty bytes")
        bindings[name] = {
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    excluded = sorted({seed for values in normalized.values() for seed in values})
    return {
        "authority": registration_authority(),
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": repository_commit,
        "schema_version": SEED_INVENTORY_SCHEMA_VERSION,
        "source_bindings": bindings,
        "sources": normalized,
    }


def _validate_seed_inventory(value: Mapping[str, Any]) -> dict[str, Any]:
    inventory = copy.deepcopy(dict(value))
    if inventory.get("schema_version") != SEED_INVENTORY_SCHEMA_VERSION:
        raise ExperimentBlocked("seed inventory schema mismatch")
    commit = inventory.get("repository_commit")
    if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
        raise ExperimentBlocked("seed inventory repository commit is invalid")
    if inventory.get("authority") != registration_authority():
        raise ExperimentBlocked("seed inventory authority mismatch")
    raw_sources = inventory.get("sources")
    if not isinstance(raw_sources, Mapping):
        raise ExperimentBlocked("seed inventory sources are invalid")
    sources: dict[str, list[int]] = {}
    for name, values in sorted(raw_sources.items()):
        if not isinstance(name, str) or not isinstance(values, list):
            raise ExperimentBlocked("seed inventory sources are invalid")
        seeds = [_nonnegative_seed(seed, f"seed source {name}") for seed in values]
        if seeds != sorted(set(seeds)):
            raise ExperimentBlocked("seed inventory source values are not canonical")
        sources[name] = seeds
    if sources.get(_RESERVED_PREVIOUS_HOLDOUT_NAME) != list(
        _RESERVED_PREVIOUS_HOLDOUT
    ):
        raise ExperimentBlocked("seed inventory omitted the consumed holdout")
    excluded = sorted({seed for values in sources.values() for seed in values})
    if (
        inventory.get("excluded_seeds") != excluded
        or inventory.get("excluded_seed_count") != len(excluded)
    ):
        raise ExperimentBlocked("seed inventory counts mismatch")
    bindings = inventory.get("source_bindings")
    if not isinstance(bindings, Mapping) or set(bindings) != set(sources):
        raise ExperimentBlocked("seed inventory source bindings mismatch")
    for name, binding in bindings.items():
        if not isinstance(binding, Mapping):
            raise ExperimentBlocked("seed inventory source binding is invalid")
        digest = binding.get("sha256")
        size = binding.get("size_bytes")
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ExperimentBlocked("seed inventory source binding is invalid")
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise ExperimentBlocked("seed inventory source binding is invalid")
    inventory["sources"] = sources
    inventory["excluded_seeds"] = excluded
    return inventory


def _validate_binding(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    binding = copy.deepcopy(dict(value))
    if set(binding) != {"path", "sha256", "size_bytes"}:
        raise ExperimentBlocked(f"{label} fields mismatch")
    binding["path"] = _canonical_relative_path(binding["path"])
    digest = binding["sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ExperimentBlocked(f"{label} digest is invalid")
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ExperimentBlocked(f"{label} size is invalid")
    return binding


def _validate_external_binding(
    value: Mapping[str, Any], label: str
) -> dict[str, Any]:
    binding = copy.deepcopy(dict(value))
    if set(binding) != {"path", "sha256", "size_bytes"}:
        raise ExperimentBlocked(f"{label} fields mismatch")
    path = binding["path"]
    if (
        not isinstance(path, str)
        or not re.fullmatch(r"[A-Za-z]:/[^\r\n]+", path)
        or "\\" in path
    ):
        raise ExperimentBlocked(f"{label} path is invalid")
    digest = binding["sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ExperimentBlocked(f"{label} digest is invalid")
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise ExperimentBlocked(f"{label} size is invalid")
    return binding


def _canonical_windows_path(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z]:/[^\r\n]*", value)
        or "\\" in value
    ):
        raise ExperimentBlocked(f"{label} path is invalid")
    return value


def external_file_binding(path: Path | str) -> dict[str, Any]:
    """Hash one external file without importing or executing it."""
    candidate = Path(path).resolve()
    if not candidate.is_file():
        raise ExperimentBlocked(f"external file is missing: {candidate}")
    payload = candidate.read_bytes()
    if not payload:
        raise ExperimentBlocked(f"external file is empty: {candidate}")
    return {
        "path": candidate.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def snapshot_production_checkpoints(root: Path | str) -> dict[str, Any]:
    """Hash the complete production-checkpoint tree as inert bytes."""
    directory = Path(root).resolve()
    if not directory.is_dir():
        raise ExperimentBlocked(f"production checkpoint root is missing: {directory}")
    rows = [
        (path.relative_to(directory).as_posix(), path.read_bytes())
        for path in sorted(
            (candidate for candidate in directory.rglob("*") if candidate.is_file()),
            key=lambda candidate: candidate.relative_to(directory).as_posix(),
        )
    ]
    return {
        "file_count": len(rows),
        "root": directory.as_posix(),
        "sha256": _hash_named_bytes(rows),
        "size_bytes": sum(len(payload) for _, payload in rows),
    }


def _validate_implementation(value: Mapping[str, Any]) -> dict[str, Any]:
    implementation = copy.deepcopy(dict(value))
    if set(implementation) != {"source_files", "source_sha256"}:
        raise ExperimentBlocked("implementation fields mismatch")
    raw_files = implementation["source_files"]
    if not isinstance(raw_files, list):
        raise ExperimentBlocked("implementation source files are invalid")
    source_files = [
        _validate_binding(binding, f"implementation source file[{index}]")
        for index, binding in enumerate(raw_files)
    ]
    if [binding["path"] for binding in source_files] != list(
        PLANNED_SOURCE_FILES
    ):
        raise ExperimentBlocked("implementation source file paths mismatch")
    digest = implementation["source_sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ExperimentBlocked("implementation source digest is invalid")
    implementation["source_files"] = source_files
    return implementation


def _hash_named_bytes(rows: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in rows:
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def build_git_implementation_binding(
    repo_root: Path | str, *, repository_commit: str
) -> dict[str, Any]:
    """Bind exactly the planned implementation files from one Git tree."""
    root = Path(repo_root).resolve()
    blobs = _git_blob_batch(
        root,
        repository_commit=repository_commit,
        paths=PLANNED_SOURCE_FILES,
    )
    rows = [(path, blobs[path]) for path in PLANNED_SOURCE_FILES]
    return {
        "source_files": [
            {
                "path": path,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
            for path, payload in rows
        ],
        "source_sha256": _hash_named_bytes(rows),
    }


def validate_implementation_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_implementation(value)


def current_runtime_identity() -> dict[str, str]:
    """Read runtime package metadata without importing Torch."""
    return {
        "device": "cpu",
        "executable": Path(sys.executable).resolve().as_posix(),
        "platform": sys.platform,
        "python_version": platform.python_version(),
        "torch_version": importlib_metadata.version("torch"),
    }


def _validate_runtime_identity(value: Mapping[str, Any]) -> dict[str, str]:
    runtime = copy.deepcopy(dict(value))
    if set(runtime) != {
        "device",
        "executable",
        "platform",
        "python_version",
        "torch_version",
    }:
        raise ExperimentBlocked("runtime identity fields mismatch")
    if runtime["device"] != "cpu":
        raise ExperimentBlocked("runtime device must be cpu")
    _canonical_windows_path(runtime["executable"], "runtime executable")
    if any(not isinstance(value, str) or not value for value in runtime.values()):
        raise ExperimentBlocked("runtime identity values are invalid")
    return runtime


def _validate_native_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    native = copy.deepcopy(dict(value))
    if set(native) != {
        "dll_directories",
        "module",
        "provenance",
        "provenance_sha256",
    }:
        raise ExperimentBlocked("native identity fields mismatch")
    directories = native["dll_directories"]
    if not isinstance(directories, list) or not directories:
        raise ExperimentBlocked("native DLL directories are invalid")
    native["dll_directories"] = [
        _canonical_windows_path(path, f"native DLL directory[{index}]")
        for index, path in enumerate(directories)
    ]
    if len(set(native["dll_directories"])) != len(native["dll_directories"]):
        raise ExperimentBlocked("native DLL directories contain duplicates")
    native["module"] = _validate_external_binding(
        native["module"], "native module"
    )
    provenance = native["provenance"]
    if not isinstance(provenance, Mapping) or not provenance:
        raise ExperimentBlocked("native provenance is invalid")
    native["provenance"] = copy.deepcopy(dict(provenance))
    provenance_bytes = canonical_json_bytes(native["provenance"])
    digest = native["provenance_sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ExperimentBlocked("native provenance digest is invalid")
    if digest != hashlib.sha256(provenance_bytes).hexdigest():
        raise ExperimentBlocked("native provenance digest mismatch")
    return native


def _validate_isolation_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    isolation = copy.deepcopy(dict(value))
    if set(isolation) != {
        "communication_mod_config",
        "production_checkpoints",
    }:
        raise ExperimentBlocked("isolation identity fields mismatch")
    isolation["communication_mod_config"] = _validate_external_binding(
        isolation["communication_mod_config"],
        "CommunicationMod configuration",
    )
    checkpoints = copy.deepcopy(dict(isolation["production_checkpoints"]))
    if set(checkpoints) != {"file_count", "root", "sha256", "size_bytes"}:
        raise ExperimentBlocked("production checkpoint identity fields mismatch")
    checkpoints["root"] = _canonical_windows_path(
        checkpoints["root"], "production checkpoint root"
    )
    for field in ("file_count", "size_bytes"):
        value = checkpoints[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ExperimentBlocked("production checkpoint count is invalid")
    digest = checkpoints["sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ExperimentBlocked("production checkpoint digest is invalid")
    isolation["production_checkpoints"] = checkpoints
    return isolation


def build_source_only_registration(
    *,
    repository_commit: str,
    logical_experiment_id: str,
    preimplementation_binding: Mapping[str, Any],
    seed_inventory: Mapping[str, Any],
    seed_inventory_binding: Mapping[str, Any],
    cohorts: Mapping[str, Any],
    implementation: Mapping[str, Any],
    runtime_identity: Mapping[str, Any],
    native_identity: Mapping[str, Any],
    isolation_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Build one immutable all-false registration without loading runtime code."""
    if not _COMMIT_RE.fullmatch(repository_commit):
        raise ExperimentBlocked("registration repository commit is invalid")
    if not _EXECUTION_ID_RE.fullmatch(logical_experiment_id):
        raise ExperimentBlocked("registration logical identity is invalid")
    inventory = _validate_seed_inventory(seed_inventory)
    if inventory["repository_commit"] != repository_commit:
        raise ExperimentBlocked("registration seed inventory commit mismatch")
    cohort_values = validate_fresh_cohorts(inventory, cohorts)
    registration = {
        "authority": registration_authority(),
        "cohorts": {
            **cohort_values,
            "selection": {
                "canary_count": 128,
                "holdout_count": 512,
                "train_count": 1024,
                "train_passes": 4,
            },
        },
        "contract": experiment_contract(),
        "implementation": _validate_implementation(implementation),
        "isolation_identity": _validate_isolation_identity(isolation_identity),
        "limits": copy.deepcopy(experiment_contract()["limits"]),
        "logical_experiment_id": logical_experiment_id,
        "native_identity": _validate_native_identity(native_identity),
        "output_directory": DEFAULT_OUTPUT_DIRECTORY,
        "output_inventory": registered_output_inventory(),
        "preimplementation_binding": _validate_binding(
            preimplementation_binding,
            "preimplementation binding",
        ),
        "pushed_remote_ref": "origin/master",
        "repository_commit": repository_commit,
        "runtime_identity": _validate_runtime_identity(runtime_identity),
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
        "seed_inventory": inventory,
        "seed_inventory_binding": _validate_binding(
            seed_inventory_binding,
            "seed inventory binding",
        ),
    }
    return validate_registration(registration)


def validate_registration(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact source-only registration shape and fixed controls."""
    registration = copy.deepcopy(dict(value))
    expected_keys = {
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
    }
    if set(registration) != expected_keys:
        raise ExperimentBlocked("registration fields mismatch")
    if registration["schema_version"] != EXPERIMENT_SCHEMA_VERSION:
        raise ExperimentBlocked("registration schema mismatch")
    commit = registration["repository_commit"]
    if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
        raise ExperimentBlocked("registration repository commit is invalid")
    logical_id = registration["logical_experiment_id"]
    if not isinstance(logical_id, str) or not _EXECUTION_ID_RE.fullmatch(logical_id):
        raise ExperimentBlocked("registration logical identity is invalid")
    if registration["authority"] != registration_authority():
        raise ExperimentBlocked("registration authority mismatch")
    if registration["contract"] != experiment_contract():
        raise ExperimentBlocked("registration contract mismatch")
    if registration["limits"] != experiment_contract()["limits"]:
        raise ExperimentBlocked("registration limits mismatch")
    if registration["output_directory"] != DEFAULT_OUTPUT_DIRECTORY:
        raise ExperimentBlocked("registration output directory mismatch")
    if registration["output_inventory"] != registered_output_inventory():
        raise ExperimentBlocked("registration output inventory mismatch")
    if registration["pushed_remote_ref"] != "origin/master":
        raise ExperimentBlocked("registration remote ref mismatch")
    inventory = _validate_seed_inventory(registration["seed_inventory"])
    if inventory["repository_commit"] != commit:
        raise ExperimentBlocked("registration seed inventory commit mismatch")
    cohorts = copy.deepcopy(dict(registration["cohorts"]))
    selection = cohorts.pop("selection", None)
    if selection != {
        "canary_count": 128,
        "holdout_count": 512,
        "train_count": 1024,
        "train_passes": 4,
    }:
        raise ExperimentBlocked("registration cohort selection mismatch")
    validate_fresh_cohorts(inventory, cohorts)
    registration["implementation"] = _validate_implementation(
        registration["implementation"]
    )
    registration["runtime_identity"] = _validate_runtime_identity(
        registration["runtime_identity"]
    )
    registration["native_identity"] = _validate_native_identity(
        registration["native_identity"]
    )
    registration["isolation_identity"] = _validate_isolation_identity(
        registration["isolation_identity"]
    )
    registration["preimplementation_binding"] = _validate_binding(
        registration["preimplementation_binding"],
        "preimplementation binding",
    )
    registration["seed_inventory_binding"] = _validate_binding(
        registration["seed_inventory_binding"],
        "seed inventory binding",
    )
    if (
        registration["preimplementation_binding"]["path"]
        != DEFAULT_PREIMPLEMENTATION_PATH
    ):
        raise ExperimentBlocked("preimplementation binding path mismatch")
    if (
        registration["seed_inventory_binding"]["path"]
        != DEFAULT_SEED_INVENTORY_PATH
    ):
        raise ExperimentBlocked("seed inventory binding path mismatch")
    registration["seed_inventory"] = inventory
    return registration


def build_execution_authorization(
    registration: Mapping[str, Any],
    *,
    registration_binding: Mapping[str, Any],
    registration_commit: str,
    command: Sequence[str],
) -> dict[str, Any]:
    """Bind one exact execution command without invoking it."""
    normalized_registration = validate_registration(registration)
    binding = _validate_binding(registration_binding, "registration binding")
    registration_bytes = canonical_json_bytes(normalized_registration)
    if (
        binding["path"] != DEFAULT_REGISTRATION_PATH
        or binding["sha256"] != hashlib.sha256(registration_bytes).hexdigest()
        or binding["size_bytes"] != len(registration_bytes)
    ):
        raise ExperimentBlocked("registration binding mismatch")
    command_values = list(command)
    if not command_values or any(
        not isinstance(part, str) or not part for part in command_values
    ):
        raise ExperimentBlocked("authorization command is invalid")
    return {
        "authority": execution_authority(),
        "authorization_id": (
            normalized_registration["logical_experiment_id"] + ":authorization-v1"
        ),
        "command": command_values,
        "implementation_commit": normalized_registration["repository_commit"],
        "logical_experiment_id": normalized_registration[
            "logical_experiment_id"
        ],
        "registration_commit": _validate_commit(
            registration_commit, "authorization registration commit"
        ),
        "registration_binding": binding,
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
    }


def validate_execution_authorization(
    value: Mapping[str, Any],
    registration: Mapping[str, Any],
    *,
    expected_command: Sequence[str],
) -> dict[str, Any]:
    authorization = copy.deepcopy(dict(value))
    if set(authorization) != {
        "authority",
        "authorization_id",
        "command",
        "implementation_commit",
        "logical_experiment_id",
        "registration_commit",
        "registration_binding",
        "schema_version",
    }:
        raise ExperimentBlocked("authorization fields mismatch")
    if authorization["schema_version"] != AUTHORIZATION_SCHEMA_VERSION:
        raise ExperimentBlocked("authorization schema mismatch")
    normalized_registration = validate_registration(registration)
    if authorization["authority"] != execution_authority():
        raise ExperimentBlocked("authorization authority mismatch")
    if authorization["command"] != list(expected_command):
        raise ExperimentBlocked("authorization command mismatch")
    if (
        authorization["logical_experiment_id"]
        != normalized_registration["logical_experiment_id"]
        or authorization["implementation_commit"]
        != normalized_registration["repository_commit"]
        or authorization["authorization_id"]
        != normalized_registration["logical_experiment_id"] + ":authorization-v1"
    ):
        raise ExperimentBlocked("authorization identity mismatch")
    _validate_commit(
        authorization["registration_commit"],
        "authorization registration commit",
    )
    binding = _validate_binding(
        authorization["registration_binding"],
        "registration binding",
    )
    registration_bytes = canonical_json_bytes(normalized_registration)
    if (
        binding["path"] != DEFAULT_REGISTRATION_PATH
        or binding["sha256"] != hashlib.sha256(registration_bytes).hexdigest()
        or binding["size_bytes"] != len(registration_bytes)
    ):
        raise ExperimentBlocked("registration binding mismatch")
    authorization["registration_binding"] = binding
    return authorization


def source_only_registration_preflight(
    repo_root: Path | str, registration: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate a not-yet-committed registration on its pushed implementation."""
    root = Path(repo_root).resolve()
    normalized = validate_registration(registration)
    implementation_commit = normalized["repository_commit"]
    if _git_text(root, "rev-parse", "HEAD") != implementation_commit:
        raise ExperimentBlocked("registration preflight HEAD differs from implementation")
    if _git_text(root, "rev-parse", "origin/master") != implementation_commit:
        raise ExperimentBlocked("registration preflight implementation is not pushed")
    if _git_text(root, "status", "--porcelain", "--untracked-files=no"):
        raise ExperimentBlocked("registration preflight tracked worktree is not clean")
    if (
        build_git_implementation_binding(
            root, repository_commit=implementation_commit
        )
        != normalized["implementation"]
    ):
        raise ExperimentBlocked("registration preflight implementation mismatch")
    verify_tracked_seed_exclusion_inventory(normalized["seed_inventory"], root)
    if current_runtime_identity() != normalized["runtime_identity"]:
        raise ExperimentBlocked("registration preflight runtime identity mismatch")
    native = normalized["native_identity"]
    if external_file_binding(native["module"]["path"]) != native["module"]:
        raise ExperimentBlocked("registration preflight native identity mismatch")
    isolation = normalized["isolation_identity"]
    if (
        external_file_binding(isolation["communication_mod_config"]["path"])
        != isolation["communication_mod_config"]
        or snapshot_production_checkpoints(
            isolation["production_checkpoints"]["root"]
        )
        != isolation["production_checkpoints"]
    ):
        raise ExperimentBlocked("registration preflight isolation mismatch")
    registration_bytes = canonical_json_bytes(normalized)
    return {
        "authority": registration_authority(),
        "checks": {
            "communication_mod_unchanged": True,
            "implementation_exact": True,
            "implementation_pushed": True,
            "native_module_unchanged": True,
            "production_checkpoints_unchanged": True,
            "runtime_identity_exact": True,
            "seed_inventory_replayed": True,
            "tracked_worktree_clean": True,
        },
        "logical_experiment_id": normalized["logical_experiment_id"],
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "repository_commit": implementation_commit,
        "schema_version": REGISTRATION_PREFLIGHT_SCHEMA_VERSION,
    }


def source_only_preflight(
    repo_root: Path | str,
    registration: Mapping[str, Any],
    authorization: Mapping[str, Any],
    *,
    expected_command: Sequence[str],
) -> dict[str, Any]:
    """Recheck a clean pushed identity before any runtime or native import."""
    root = Path(repo_root).resolve()
    normalized_registration = validate_registration(registration)
    normalized_authorization = validate_execution_authorization(
        authorization,
        normalized_registration,
        expected_command=expected_command,
    )
    implementation_commit = normalized_registration["repository_commit"]
    head_commit = _git_text(root, "rev-parse", "HEAD")
    pushed_commit = _git_text(root, "rev-parse", "origin/master")
    if head_commit != pushed_commit:
        raise ExperimentBlocked("preflight HEAD differs from pushed authorization")
    if _git_text(root, "status", "--porcelain", "--untracked-files=no"):
        raise ExperimentBlocked("preflight tracked worktree is not clean")
    registration_commit = normalized_authorization["registration_commit"]
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
        pushed_commit,
    )
    registration_bytes = canonical_json_bytes(normalized_registration)
    authorization_bytes = canonical_json_bytes(normalized_authorization)
    committed_registration = _git_blob_batch(
        root,
        repository_commit=registration_commit,
        paths=(DEFAULT_REGISTRATION_PATH,),
    )[DEFAULT_REGISTRATION_PATH]
    pushed_authorization = _git_blob_batch(
        root,
        repository_commit=pushed_commit,
        paths=(DEFAULT_AUTHORIZATION_PATH,),
    )[DEFAULT_AUTHORIZATION_PATH]
    if committed_registration != registration_bytes:
        raise ExperimentBlocked("preflight pushed registration bytes mismatch")
    if pushed_authorization != authorization_bytes:
        raise ExperimentBlocked("preflight pushed authorization bytes mismatch")
    implementation = build_git_implementation_binding(
        root,
        repository_commit=implementation_commit,
    )
    if implementation != normalized_registration["implementation"]:
        raise ExperimentBlocked("preflight implementation binding mismatch")
    if (
        build_git_implementation_binding(root, repository_commit=pushed_commit)
        != implementation
    ):
        raise ExperimentBlocked("preflight pushed implementation bytes drifted")
    inventory = verify_tracked_seed_exclusion_inventory(
        normalized_registration["seed_inventory"], root
    )
    if inventory != normalized_registration["seed_inventory"]:
        raise ExperimentBlocked("preflight seed inventory mismatch")
    runtime_identity = current_runtime_identity()
    if runtime_identity != normalized_registration["runtime_identity"]:
        raise ExperimentBlocked("preflight runtime identity mismatch")
    native = normalized_registration["native_identity"]
    if external_file_binding(native["module"]["path"]) != native["module"]:
        raise ExperimentBlocked("preflight native module identity mismatch")
    isolation = normalized_registration["isolation_identity"]
    config = isolation["communication_mod_config"]
    if external_file_binding(config["path"]) != config:
        raise ExperimentBlocked("preflight CommunicationMod identity mismatch")
    checkpoints = isolation["production_checkpoints"]
    if snapshot_production_checkpoints(checkpoints["root"]) != checkpoints:
        raise ExperimentBlocked("preflight production checkpoint identity mismatch")
    return {
        "authority": registration_authority(),
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "checks": {
            "authorization_exact": True,
            "authorization_pushed_exact": True,
            "communication_mod_unchanged": True,
            "implementation_ancestor": True,
            "implementation_exact": True,
            "native_module_unchanged": True,
            "origin_master_exact": True,
            "production_checkpoints_unchanged": True,
            "registration_bytes_exact": True,
            "registration_commit_ancestor": True,
            "runtime_identity_exact": True,
            "seed_inventory_replayed": True,
            "tracked_worktree_clean": True,
        },
        "logical_experiment_id": normalized_registration[
            "logical_experiment_id"
        ],
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "pushed_commit": pushed_commit,
        "repository_commit": implementation_commit,
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
    }


def materialize_fresh_cohorts(inventory: Mapping[str, Any]) -> dict[str, list[int]]:
    """Select only the proposal's fixed ascending 1024/128/512 cohorts."""
    normalized = _validate_seed_inventory(inventory)
    excluded = set(normalized["excluded_seeds"])
    selected: list[int] = []
    candidate = 0
    required = 1024 + 128 + 512
    while len(selected) < required:
        if candidate not in excluded:
            selected.append(candidate)
        candidate += 1
    return {
        "train": selected[:1024],
        "canary": selected[1024:1152],
        "holdout": selected[1152:],
    }


def validate_fresh_cohorts(
    inventory: Mapping[str, Any], cohorts: Mapping[str, Any]
) -> dict[str, list[int]]:
    """Require exact reproduction of the sole fixed selection algorithm."""
    expected = materialize_fresh_cohorts(inventory)
    normalized = copy.deepcopy(dict(cohorts))
    if normalized != expected:
        raise ExperimentBlocked("fresh cohorts differ from the exact selection or overlap")
    return expected


def _validate_execution_identity(value: Mapping[str, Any]) -> dict[str, str]:
    identity = copy.deepcopy(dict(value))
    if set(identity) != {
        "authorization_sha256",
        "logical_execution_id",
        "registration_sha256",
    }:
        raise ExperimentBlocked("execution identity fields mismatch")
    for field in ("authorization_sha256", "registration_sha256"):
        digest = identity[field]
        if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
            raise ExperimentBlocked("execution identity digest is invalid")
    logical_id = identity["logical_execution_id"]
    if not isinstance(logical_id, str) or not _EXECUTION_ID_RE.fullmatch(logical_id):
        raise ExperimentBlocked("logical execution identity is invalid")
    return identity


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExperimentBlocked(f"{label} is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise ExperimentBlocked(f"{label} is invalid")
    if payload != canonical_json_bytes(value):
        raise ExperimentBlocked(f"{label} is not canonical")
    return value


def _atomic_replace(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o644,
        )
    except FileExistsError as exc:
        raise ExperimentBlocked(f"atomic temporary already exists: {temporary}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _atomic_write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        raise ExperimentBlocked(f"artifact already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise ExperimentBlocked(f"partial artifact exists: {temporary.name}")
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


def _atomic_write_once_or_same(path: Path, payload: bytes) -> None:
    """Write once, while allowing crash recovery with identical bytes."""
    if path.exists():
        try:
            observed = path.read_bytes()
        except OSError as exc:
            raise ExperimentBlocked(
                f"existing artifact cannot be read: {path.name}"
            ) from exc
        if observed != payload:
            raise ExperimentBlocked(f"existing artifact bytes differ: {path.name}")
        return
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        try:
            partial = temporary.read_bytes()
            if partial == payload:
                os.replace(temporary, path)
                return
            temporary.unlink()
        except OSError as exc:
            raise ExperimentBlocked(
                f"partial artifact cannot be reconciled: {temporary.name}"
            ) from exc
    _atomic_write_once(path, payload)


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


class ExecutionLease:
    """Exclusive identity-bound ownership of one future output root."""

    def __init__(
        self, output_path: Path | str, *, identity: Mapping[str, Any]
    ) -> None:
        self.output_path = Path(output_path).resolve()
        self.identity = _validate_execution_identity(identity)
        self.path = self.output_path / ".execution.lease"
        self._handle: Any | None = None
        self.held = False

    def __enter__(self) -> "ExecutionLease":
        key = os.path.normcase(str(self.path))
        if key in _ACTIVE_EXECUTION_LEASES:
            raise ExperimentBlocked("execution lease is already held")
        self.output_path.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b", buffering=0)
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                _lock_file(handle)
            except OSError as exc:
                raise ExperimentBlocked("execution lease is already held") from exc
            handle.seek(0)
            raw = handle.read()
            if raw not in {b"", b"\0"}:
                try:
                    existing = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ExperimentBlocked("execution lease payload is invalid") from exc
                if raw != canonical_json_bytes(existing):
                    raise ExperimentBlocked("execution lease payload is not canonical")
                if existing != {
                    "identity": self.identity,
                    "schema_version": LEASE_SCHEMA_VERSION,
                }:
                    raise ExperimentBlocked("execution lease identity mismatch")
            payload = canonical_json_bytes(
                {
                    "identity": self.identity,
                    "schema_version": LEASE_SCHEMA_VERSION,
                }
            )
            handle.seek(0)
            handle.truncate()
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
            self._handle = handle
            self.held = True
            _ACTIVE_EXECUTION_LEASES.add(key)
            return self
        except BaseException:
            try:
                if handle is not None:
                    _unlock_file(handle)
            except OSError:
                pass
            handle.close()
            raise

    def __exit__(self, exc_type, exc, traceback) -> None:
        handle = self._handle
        key = os.path.normcase(str(self.path))
        self._handle = None
        self.held = False
        _ACTIVE_EXECUTION_LEASES.discard(key)
        if handle is not None:
            try:
                _unlock_file(handle)
            finally:
                handle.close()


def _require_execution_lease(
    lease: ExecutionLease,
    output_path: Path | str,
    identity: Mapping[str, Any],
) -> None:
    normalized_identity = _validate_execution_identity(identity)
    if not isinstance(lease, ExecutionLease) or not lease.held:
        raise ExperimentBlocked("execution lease is not held")
    if lease.output_path != Path(output_path).resolve():
        raise ExperimentBlocked("execution lease output mismatch")
    if lease.identity != normalized_identity:
        raise ExperimentBlocked("execution lease identity mismatch")


def record_prestart_failure(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    reason: str,
) -> dict[str, Any]:
    """Append a deterministic setup failure before evidence can start."""
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    if not isinstance(reason, str) or not reason.strip():
        raise ExperimentBlocked("prestart failure reason is invalid")
    if (output / "evidence_start.json").exists():
        raise ExperimentBlocked("evidence already started")
    attempts_path = output / "prestart_attempts.json"
    if attempts_path.exists():
        payload = _load_json(attempts_path, "prestart attempts")
        if payload.get("identity") != normalized_identity:
            raise ExperimentBlocked("prestart identity mismatch")
        attempts = payload.get("attempts")
        if not isinstance(attempts, list):
            raise ExperimentBlocked("prestart attempts are invalid")
    else:
        attempts = []
    attempt = {
        "attempt_index": len(attempts) + 1,
        "reason": reason.strip(),
        "state": "prestart_failed",
    }
    attempts.append(attempt)
    payload = {
        "attempts": attempts,
        "identity": normalized_identity,
        "schema_version": PRESTART_ATTEMPTS_SCHEMA_VERSION,
    }
    _atomic_replace(attempts_path, canonical_json_bytes(payload))
    return copy.deepcopy(attempt)


def preseed_retry_allowed(
    output_path: Path | str, *, identity: Mapping[str, Any]
) -> bool:
    """Return true only for an unchanged identity without start marker."""
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    attempts_path = output / "prestart_attempts.json"
    if attempts_path.exists():
        attempts = _load_json(attempts_path, "prestart attempts")
        if attempts.get("identity") != normalized_identity:
            raise ExperimentBlocked("prestart identity mismatch")
    marker_path = output / "evidence_start.json"
    if not marker_path.exists():
        return not _resource_artifact_has_evidence(
            output,
            identity=normalized_identity,
        )
    _load_evidence_start(output, identity=normalized_identity)
    return False


def _load_evidence_start(
    output_path: Path | str, *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    normalized_identity = _validate_execution_identity(identity)
    marker = _load_json(Path(output_path) / "evidence_start.json", "evidence start")
    if set(marker) != {
        "authorization_sha256",
        "first_seed",
        "logical_execution_id",
        "registration_sha256",
        "schema_version",
        "state",
    }:
        raise ExperimentBlocked("evidence start fields mismatch")
    if (
        marker["schema_version"] != EVIDENCE_START_SCHEMA_VERSION
        or marker["state"] != "evidence_started"
    ):
        raise ExperimentBlocked("evidence start marker is invalid")
    if any(marker.get(name) != value for name, value in normalized_identity.items()):
        raise ExperimentBlocked("evidence start identity mismatch")
    marker["first_seed"] = _nonnegative_seed(marker["first_seed"], "first seed")
    return marker


def mark_evidence_start(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    first_seed: int,
    lease: ExecutionLease,
) -> dict[str, Any]:
    """Durably consume the empirical identity before environment construction."""
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    seed = _nonnegative_seed(first_seed, "first seed")
    attempts_path = output / "prestart_attempts.json"
    if attempts_path.exists():
        attempts = _load_json(attempts_path, "prestart attempts")
        if attempts.get("identity") != normalized_identity:
            raise ExperimentBlocked("prestart identity mismatch")
    marker = {
        **normalized_identity,
        "first_seed": seed,
        "schema_version": EVIDENCE_START_SCHEMA_VERSION,
        "state": "evidence_started",
    }
    marker_path = output / "evidence_start.json"
    if marker_path.exists():
        raise ExperimentBlocked("evidence already started")
    _atomic_write_once_or_same(marker_path, canonical_json_bytes(marker))
    return marker


def validate_same_identity_resume(
    marker: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    *,
    identity: Mapping[str, Any],
    interruption_class: str,
) -> dict[str, Any]:
    """Validate the only post-seed resume path."""
    normalized_identity = _validate_execution_identity(identity)
    marker_value = copy.deepcopy(dict(marker))
    if (
        marker_value.get("schema_version") != EVIDENCE_START_SCHEMA_VERSION
        or marker_value.get("state") != "evidence_started"
    ):
        raise ExperimentBlocked("evidence start marker is invalid")
    if any(marker_value.get(name) != value for name, value in normalized_identity.items()):
        raise ExperimentBlocked("evidence start identity mismatch")
    if interruption_class != "infrastructure":
        raise ExperimentBlocked("interruption class is not resumable")
    checkpoint_value = copy.deepcopy(dict(checkpoint))
    if checkpoint_value.get("identity") != normalized_identity:
        raise ExperimentBlocked("checkpoint identity mismatch")
    if checkpoint_value.get("complete") is not True:
        raise ExperimentBlocked("checkpoint must be complete")
    runtime = checkpoint_value.get("runtime")
    if not isinstance(runtime, Mapping):
        raise ExperimentBlocked("checkpoint runtime is invalid")
    coordinates = runtime.get("coordinates")
    if not isinstance(coordinates, Mapping):
        raise ExperimentBlocked("checkpoint runtime coordinates are invalid")
    next_chunk = coordinates.get("next_chunk_index")
    if isinstance(next_chunk, bool) or not isinstance(next_chunk, int) or next_chunk < 0:
        raise ExperimentBlocked("checkpoint coordinate is invalid")
    return checkpoint_value


def assert_output_read_allowed(*, process_alive: bool) -> None:
    """Forbid active-output inspection on Windows."""
    if process_alive:
        raise ExperimentBlocked("active output root cannot be read")


def validate_execution_journal(
    value: Mapping[str, Any], *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    journal = copy.deepcopy(dict(value))
    if set(journal) != {"identity", "records", "schema_version"}:
        raise ExperimentBlocked("execution journal fields mismatch")
    if journal["schema_version"] != JOURNAL_SCHEMA_VERSION:
        raise ExperimentBlocked("execution journal schema mismatch")
    normalized_identity = _validate_execution_identity(identity)
    if journal["identity"] != normalized_identity:
        raise ExperimentBlocked("execution journal identity mismatch")
    records = journal["records"]
    if not isinstance(records, list) or not records:
        raise ExperimentBlocked("execution journal records are invalid")
    previous_state: str | None = None
    normalized_records = []
    for index, raw in enumerate(records):
        if not isinstance(raw, Mapping):
            raise ExperimentBlocked("execution journal record is invalid")
        record = copy.deepcopy(dict(raw))
        if set(record) != {"details", "sequence", "state"}:
            raise ExperimentBlocked("execution journal record fields mismatch")
        if record["sequence"] != index:
            raise ExperimentBlocked("execution journal sequence mismatch")
        state = record["state"]
        if not isinstance(state, str) or state not in _JOURNAL_TRANSITIONS:
            raise ExperimentBlocked("execution journal state is invalid")
        if not isinstance(record["details"], Mapping):
            raise ExperimentBlocked("execution journal details are invalid")
        canonical_json_bytes(dict(record["details"]))
        if index == 0:
            if state != "prestart_owned":
                raise ExperimentBlocked("execution journal initial state mismatch")
        elif state not in _JOURNAL_TRANSITIONS[previous_state]:
            raise ExperimentBlocked("execution journal transition is invalid")
        record["details"] = copy.deepcopy(dict(record["details"]))
        normalized_records.append(record)
        previous_state = state
    journal["records"] = normalized_records
    return journal


def _reconcile_execution_journal(
    output: Path,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    path = output / "execution_journal.json"
    temporary = output / ".execution_journal.json.tmp"
    current = (
        validate_execution_journal(
            _load_json(path, "execution journal"),
            identity=normalized_identity,
        )
        if path.is_file()
        else None
    )
    if not temporary.exists():
        if current is None:
            raise ExperimentBlocked("execution journal does not exist")
        return current
    candidate = validate_execution_journal(
        _load_json(temporary, "partial execution journal"),
        identity=normalized_identity,
    )
    if current is None:
        if candidate["records"] != [
            {"details": {}, "sequence": 0, "state": "prestart_owned"}
        ]:
            raise ExperimentBlocked("partial execution journal lacks its predecessor")
        os.replace(temporary, path)
        return candidate
    current_records = current["records"]
    candidate_records = candidate["records"]
    if candidate == current or (
        len(candidate_records) <= len(current_records)
        and candidate_records == current_records[: len(candidate_records)]
    ):
        temporary.unlink()
        return current
    if (
        len(candidate_records) != len(current_records) + 1
        or candidate_records[:-1] != current_records
    ):
        raise ExperimentBlocked(
            "partial execution journal is not the next durable record"
        )
    os.replace(temporary, path)
    return candidate


def load_execution_journal(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease | None = None,
) -> dict[str, Any]:
    output = Path(output_path)
    if (output / ".execution_journal.json.tmp").exists():
        if lease is None:
            raise ExperimentBlocked(
                "partial execution journal requires the execution lease"
            )
        return _reconcile_execution_journal(
            output,
            identity=identity,
            lease=lease,
        )
    path = output / "execution_journal.json"
    if not path.is_file():
        raise ExperimentBlocked("execution journal does not exist")
    return validate_execution_journal(
        _load_json(path, "execution journal"),
        identity=identity,
    )


def initialize_execution_journal(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    journal = {
        "identity": normalized_identity,
        "records": [
            {"details": {}, "sequence": 0, "state": "prestart_owned"}
        ],
        "schema_version": JOURNAL_SCHEMA_VERSION,
    }
    validate_execution_journal(journal, identity=normalized_identity)
    _atomic_write_once_or_same(
        output / "execution_journal.json",
        canonical_json_bytes(journal),
    )
    return journal


def append_execution_journal(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    expected_previous_state: str,
    state: str,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    path = output / "execution_journal.json"
    if not path.exists():
        raise ExperimentBlocked("execution journal does not exist")
    journal = load_execution_journal(
        output,
        identity=normalized_identity,
        lease=lease,
    )
    previous_state = journal["records"][-1]["state"]
    if previous_state != expected_previous_state:
        raise ExperimentBlocked("execution journal previous state mismatch")
    if state not in _JOURNAL_TRANSITIONS.get(previous_state, set()):
        raise ExperimentBlocked("execution journal transition is invalid")
    record = {
        "details": copy.deepcopy(dict(details)),
        "sequence": len(journal["records"]),
        "state": state,
    }
    canonical_json_bytes(record["details"])
    journal["records"].append(record)
    validate_execution_journal(journal, identity=normalized_identity)
    _atomic_replace(path, canonical_json_bytes(journal))
    return journal


def stage_execution_controls(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    authorization: Mapping[str, Any],
    expected_command: Sequence[str],
    lease: ExecutionLease,
    identity: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Publish immutable controls under the leased output identity."""
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    normalized_registration = validate_registration(registration)
    normalized_authorization = validate_execution_authorization(
        authorization,
        normalized_registration,
        expected_command=expected_command,
    )
    registration_bytes = canonical_json_bytes(normalized_registration)
    authorization_bytes = canonical_json_bytes(normalized_authorization)
    expected_identity = {
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "logical_execution_id": normalized_registration["logical_experiment_id"],
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
    }
    if normalized_identity != expected_identity:
        raise ExperimentBlocked("staged control identity mismatch")
    _atomic_write_once_or_same(output / "registration.json", registration_bytes)
    _atomic_write_once_or_same(output / "authorization.json", authorization_bytes)
    initialize_resource_ledger(
        output,
        identity=normalized_identity,
        lease=lease,
    )
    return {
        "authorization": normalized_authorization,
        "registration": normalized_registration,
    }


def _nonnegative_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExperimentBlocked(f"{label} must be a non-negative finite number")
    normalized = float(value)
    if not normalized >= 0.0 or normalized == float("inf"):
        raise ExperimentBlocked(f"{label} must be a non-negative finite number")
    return normalized


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExperimentBlocked(f"{label} must be a finite number")
    normalized = float(value)
    if normalized != normalized or normalized in {float("inf"), float("-inf")}:
        raise ExperimentBlocked(f"{label} must be a finite number")
    return normalized


def _normalize_resource_prefix(value: Mapping[str, Any]) -> dict[str, Any]:
    resources = copy.deepcopy(dict(value))
    allowed = {
        "charged_seconds",
        "evaluation_episodes",
        "total_episodes",
        "training_episodes",
    }
    if set(resources) == allowed | {"optimizer_updates"}:
        _nonnegative_seed(
            resources.pop("optimizer_updates"), "resource optimizer updates"
        )
    elif set(resources) != allowed:
        raise ExperimentBlocked("resource prefix fields mismatch")
    normalized = {
        "charged_seconds": _nonnegative_number(
            resources["charged_seconds"], "resource charged seconds"
        ),
        **{
            name: _nonnegative_seed(resources[name], f"resource {name}")
            for name in (
                "evaluation_episodes",
                "total_episodes",
                "training_episodes",
            )
        },
    }
    if normalized["total_episodes"] != (
        normalized["training_episodes"] + normalized["evaluation_episodes"]
    ):
        raise ExperimentBlocked("resource prefix total episode mismatch")
    limits = experiment_contract()["limits"]
    if (
        normalized["training_episodes"] > limits["max_training_episodes"]
        or normalized["evaluation_episodes"] > limits["max_evaluation_episodes"]
        or normalized["total_episodes"] > limits["max_total_episodes"]
        or normalized["charged_seconds"] > limits["max_wall_seconds"]
    ):
        raise ExperimentBlocked("resource prefix limit exceeded")
    return normalized


def _validate_resource_event(value: Mapping[str, Any]) -> dict[str, Any]:
    event = copy.deepcopy(dict(value))
    if set(event) != {"kind", "phase", "seed"}:
        raise ExperimentBlocked("resource event fields mismatch")
    if event["kind"] not in {
        "checkpoint_reconciled",
        "episode_debited",
        "terminal_reconciled",
        "wall_charged",
    }:
        raise ExperimentBlocked("resource event kind is invalid")
    if not isinstance(event["phase"], str) or not event["phase"]:
        raise ExperimentBlocked("resource event phase is invalid")
    if event["kind"] == "episode_debited":
        event["seed"] = _nonnegative_seed(event["seed"], "resource event seed")
    elif event["seed"] is not None:
        raise ExperimentBlocked("non-episode resource event has a seed")
    return event


def _validate_resource_ledger(
    value: Mapping[str, Any], *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    ledger = copy.deepcopy(dict(value))
    if set(ledger) != {
        "identity",
        "last_event",
        "resource_use",
        "revision",
        "schema_version",
    }:
        raise ExperimentBlocked("resource ledger fields mismatch")
    if ledger["schema_version"] != RESOURCE_LEDGER_SCHEMA_VERSION:
        raise ExperimentBlocked("resource ledger schema mismatch")
    normalized_identity = _validate_execution_identity(identity)
    if ledger["identity"] != normalized_identity:
        raise ExperimentBlocked("resource ledger identity mismatch")
    revision = _nonnegative_seed(ledger["revision"], "resource ledger revision")
    event = ledger["last_event"]
    if revision == 0:
        if event is not None:
            raise ExperimentBlocked("initial resource ledger has an event")
    else:
        if not isinstance(event, Mapping):
            raise ExperimentBlocked("resource ledger event is missing")
        event = _validate_resource_event(event)
    resources = _normalize_resource_prefix(ledger["resource_use"])
    if revision < resources["total_episodes"]:
        raise ExperimentBlocked("resource ledger revision lags episode evidence")
    if revision == 0 and resources != {
        "charged_seconds": 0.0,
        "evaluation_episodes": 0,
        "total_episodes": 0,
        "training_episodes": 0,
    }:
        raise ExperimentBlocked("initial resource ledger is nonzero")
    ledger["identity"] = normalized_identity
    ledger["last_event"] = event
    ledger["resource_use"] = resources
    ledger["revision"] = revision
    canonical_json_bytes(ledger)
    return ledger


def _resource_prefix_is_zero(value: Mapping[str, Any]) -> bool:
    resources = _normalize_resource_prefix(value)
    return resources == {
        "charged_seconds": 0.0,
        "evaluation_episodes": 0,
        "total_episodes": 0,
        "training_episodes": 0,
    }


def _resource_artifact_has_evidence(
    output_path: Path | str, *, identity: Mapping[str, Any]
) -> bool:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    paths = (
        output / "resource_use.json",
        output / ".resource_use.json.tmp",
    )
    observed = []
    for path in paths:
        if path.exists():
            observed.append(
                _validate_resource_ledger(
                    _load_json(path, f"resource ledger {path.name}"),
                    identity=normalized_identity,
                )
            )
    return any(
        ledger["revision"] > 0
        or not _resource_prefix_is_zero(ledger["resource_use"])
        for ledger in observed
    )


def _require_resource_evidence_marker(
    output: Path,
    *,
    identity: Mapping[str, Any],
    previous: Mapping[str, Any],
    resources: Mapping[str, Any],
    event: Mapping[str, Any],
) -> None:
    if _resource_prefix_is_zero(resources):
        return
    marker_path = output / "evidence_start.json"
    if not marker_path.is_file():
        raise ExperimentBlocked("resource evidence lacks an evidence marker")
    marker = _load_evidence_start(output, identity=identity)
    if (
        _resource_prefix_is_zero(previous)
        and event["kind"] == "episode_debited"
        and event["phase"] == "training"
        and event["seed"] != marker["first_seed"]
    ):
        raise ExperimentBlocked("first resource seed differs from evidence marker")


def _resource_revision_increment(
    previous: Mapping[str, Any], resources: Mapping[str, Any]
) -> int:
    episode_delta = resources["total_episodes"] - previous["total_episodes"]
    if episode_delta > 0:
        return episode_delta
    if resources["charged_seconds"] > previous["charged_seconds"]:
        return 1
    raise ExperimentBlocked("resource successor does not advance evidence")


def _reconcile_resource_ledger(
    output: Path,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    path = output / "resource_use.json"
    temporary = output / ".resource_use.json.tmp"
    current = (
        _validate_resource_ledger(
            _load_json(path, "resource ledger"),
            identity=normalized_identity,
        )
        if path.is_file()
        else None
    )
    if not temporary.exists():
        if current is None:
            raise ExperimentBlocked("resource ledger does not exist")
        return current
    candidate = _validate_resource_ledger(
        _load_json(temporary, "partial resource ledger"),
        identity=normalized_identity,
    )
    if current is None:
        if candidate["revision"] != 0 or not _resource_prefix_is_zero(
            candidate["resource_use"]
        ):
            raise ExperimentBlocked("partial resource ledger lacks its predecessor")
        os.replace(temporary, path)
        return candidate
    if candidate == current or (
        candidate["revision"] <= current["revision"]
        and all(
            candidate["resource_use"][name] <= current["resource_use"][name]
            for name in current["resource_use"]
        )
    ):
        temporary.unlink()
        return current
    if any(
        candidate["resource_use"][name] < current["resource_use"][name]
        for name in current["resource_use"]
    ):
        raise ExperimentBlocked("partial resource ledger is not a durable successor")
    revision_increment = _resource_revision_increment(
        current["resource_use"],
        candidate["resource_use"],
    )
    if candidate["revision"] != current["revision"] + revision_increment:
        raise ExperimentBlocked("partial resource ledger is not a durable successor")
    _require_resource_evidence_marker(
        output,
        identity=normalized_identity,
        previous=current["resource_use"],
        resources=candidate["resource_use"],
        event=candidate["last_event"],
    )
    os.replace(temporary, path)
    return candidate


def initialize_resource_ledger(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    path = output / "resource_use.json"
    if path.exists() or (output / ".resource_use.json.tmp").exists():
        return load_resource_ledger(
            output,
            identity=normalized_identity,
            lease=lease,
        )
    ledger = {
        "identity": normalized_identity,
        "last_event": None,
        "resource_use": {
            "charged_seconds": 0.0,
            "evaluation_episodes": 0,
            "total_episodes": 0,
            "training_episodes": 0,
        },
        "revision": 0,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }
    _atomic_write_once_or_same(path, canonical_json_bytes(ledger))
    return ledger


def load_resource_ledger(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease | None = None,
) -> dict[str, Any]:
    output = Path(output_path)
    path = output / "resource_use.json"
    if (output / ".resource_use.json.tmp").exists():
        if lease is None:
            raise ExperimentBlocked(
                "partial resource ledger requires the execution lease"
            )
        return _reconcile_resource_ledger(
            output,
            identity=identity,
            lease=lease,
        )
    if not path.is_file():
        raise ExperimentBlocked("resource ledger does not exist")
    return _validate_resource_ledger(
        _load_json(path, "resource ledger"), identity=identity
    )


def publish_resource_prefix(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    resource_use: Mapping[str, Any],
    event: Mapping[str, Any],
) -> dict[str, Any]:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    current = load_resource_ledger(
        output,
        identity=normalized_identity,
        lease=lease,
    )
    resources = _normalize_resource_prefix(resource_use)
    normalized_event = _validate_resource_event(event)
    previous = current["resource_use"]
    if any(
        resources[name] < previous[name]
        for name in (
            "charged_seconds",
            "evaluation_episodes",
            "total_episodes",
            "training_episodes",
        )
    ):
        raise ExperimentBlocked("resource prefix is not monotonic")
    if resources == previous:
        if not _resource_prefix_is_zero(resources):
            _require_resource_evidence_marker(
                output,
                identity=normalized_identity,
                previous=previous,
                resources=resources,
                event=normalized_event,
            )
        return current
    _require_resource_evidence_marker(
        output,
        identity=normalized_identity,
        previous=previous,
        resources=resources,
        event=normalized_event,
    )
    ledger = {
        "identity": normalized_identity,
        "last_event": normalized_event,
        "resource_use": resources,
        "revision": current["revision"]
        + _resource_revision_increment(previous, resources),
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }
    normalized = _validate_resource_ledger(ledger, identity=normalized_identity)
    _atomic_replace(output / "resource_use.json", canonical_json_bytes(normalized))
    return normalized


def _validate_runtime_checkpoint_control(value: Mapping[str, Any]) -> dict[str, Any]:
    checkpoint = copy.deepcopy(dict(value))
    if set(checkpoint) != {
        "algorithm",
        "coordinates",
        "model_architecture",
        "resource_use",
        "schema_version",
        "states",
    }:
        raise ExperimentBlocked("runtime checkpoint fields mismatch")
    if checkpoint["schema_version"] != _RUNTIME_CHECKPOINT_SCHEMA_VERSION:
        raise ExperimentBlocked("runtime checkpoint schema mismatch")
    if checkpoint["algorithm"] != {
        "conditional_entropy_coefficient": 0.01,
        "family_entropy_coefficient": 0.01,
        "sampling": _TRAINING_SELECTION_MODE,
    }:
        raise ExperimentBlocked("runtime checkpoint algorithm mismatch")
    coordinates = checkpoint["coordinates"]
    if not isinstance(coordinates, Mapping) or set(coordinates) != {
        "completed_decisions",
        "completed_episodes",
        "next_chunk_index",
        "optimizer_updates",
    }:
        raise ExperimentBlocked("runtime checkpoint coordinates mismatch")
    normalized_coordinates = {
        name: _nonnegative_seed(coordinates[name], f"runtime coordinate {name}")
        for name in coordinates
    }
    if normalized_coordinates["next_chunk_index"] != normalized_coordinates[
        "optimizer_updates"
    ]:
        raise ExperimentBlocked("runtime checkpoint update coordinates mismatch")
    if normalized_coordinates["completed_episodes"] != (
        normalized_coordinates["optimizer_updates"]
        * experiment_contract()["limits"]["episodes_per_update"]
    ):
        raise ExperimentBlocked("runtime checkpoint episode coordinates mismatch")
    if checkpoint["model_architecture"] != {
        "architecture_id": "state-conditioned-candidate-ranker-mlp-v1",
        "candidate_input_dim": 1024,
        "device": "cpu",
        "dtype": "float32",
        "hidden_dim": 64,
        "state_conditioned": True,
        "state_input_dim": 1024,
    }:
        raise ExperimentBlocked("runtime checkpoint architecture is invalid")
    resources = checkpoint["resource_use"]
    if not isinstance(resources, Mapping) or set(resources) != {
        "charged_seconds",
        "evaluation_episodes",
        "optimizer_updates",
        "total_episodes",
        "training_episodes",
    }:
        raise ExperimentBlocked("runtime checkpoint resource fields mismatch")
    normalized_resources = {
        "charged_seconds": _nonnegative_number(
            resources["charged_seconds"], "runtime charged seconds"
        ),
        **{
            name: _nonnegative_seed(resources[name], f"runtime resource {name}")
            for name in (
                "evaluation_episodes",
                "optimizer_updates",
                "total_episodes",
                "training_episodes",
            )
        },
    }
    if (
        normalized_resources["optimizer_updates"]
        != normalized_coordinates["optimizer_updates"]
        or normalized_resources["training_episodes"]
        < normalized_coordinates["completed_episodes"]
        or normalized_resources["total_episodes"]
        != normalized_resources["training_episodes"]
        + normalized_resources["evaluation_episodes"]
    ):
        raise ExperimentBlocked("runtime checkpoint resource coordinates mismatch")
    limits = experiment_contract()["limits"]
    if (
        normalized_resources["training_episodes"] > limits["max_training_episodes"]
        or normalized_resources["evaluation_episodes"]
        > limits["max_evaluation_episodes"]
        or normalized_resources["total_episodes"] > limits["max_total_episodes"]
        or normalized_resources["optimizer_updates"]
        > limits["max_optimizer_updates"]
        or normalized_resources["charged_seconds"] > limits["max_wall_seconds"]
    ):
        raise ExperimentBlocked("runtime checkpoint resource limit exceeded")
    states = checkpoint["states"]
    if not isinstance(states, Mapping) or set(states) != {
        "action_generator",
        "model",
        "optimizer",
        "python_rng",
    }:
        raise ExperimentBlocked("runtime checkpoint state fields mismatch")
    canonical_json_bytes(checkpoint)
    checkpoint["coordinates"] = normalized_coordinates
    checkpoint["model_architecture"] = copy.deepcopy(
        dict(checkpoint["model_architecture"])
    )
    checkpoint["resource_use"] = normalized_resources
    checkpoint["states"] = copy.deepcopy(dict(states))
    return checkpoint


def _validate_bootstrap_runtime(
    value: Mapping[str, Any], *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    bootstrap = copy.deepcopy(dict(value))
    if set(bootstrap) != {
        "authority",
        "identity",
        "runtime",
        "schema_version",
    }:
        raise ExperimentBlocked("bootstrap runtime fields mismatch")
    if bootstrap["schema_version"] != BOOTSTRAP_RUNTIME_SCHEMA_VERSION:
        raise ExperimentBlocked("bootstrap runtime schema mismatch")
    if bootstrap["authority"] != registration_authority():
        raise ExperimentBlocked("bootstrap runtime authority mismatch")
    normalized_identity = _validate_execution_identity(identity)
    if bootstrap["identity"] != normalized_identity:
        raise ExperimentBlocked("bootstrap runtime identity mismatch")
    runtime = _validate_runtime_checkpoint_control(bootstrap["runtime"])
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
        raise ExperimentBlocked("bootstrap runtime is not at coordinate zero")
    if (
        hashlib.sha256(canonical_json_bytes(runtime)).hexdigest()
        != INITIAL_RUNTIME_SHA256
    ):
        raise ExperimentBlocked("bootstrap runtime differs from seeded initialization")
    bootstrap["identity"] = normalized_identity
    bootstrap["runtime"] = runtime
    canonical_json_bytes(bootstrap)
    return bootstrap


def publish_bootstrap_runtime(
    output_path: Path | str,
    runtime: Mapping[str, Any],
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    bootstrap = _validate_bootstrap_runtime(
        {
            "authority": registration_authority(),
            "identity": normalized_identity,
            "runtime": copy.deepcopy(dict(runtime)),
            "schema_version": BOOTSTRAP_RUNTIME_SCHEMA_VERSION,
        },
        identity=normalized_identity,
    )
    _atomic_write_once_or_same(
        output / _REGISTERED_OUTPUT_INVENTORY["bootstrap_runtime"],
        canonical_json_bytes(bootstrap),
    )
    return bootstrap


def load_bootstrap_runtime(
    output_path: Path | str, *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    output = Path(output_path)
    path = output / _REGISTERED_OUTPUT_INVENTORY["bootstrap_runtime"]
    if not path.is_file():
        raise ExperimentBlocked("bootstrap runtime does not exist")
    return _validate_bootstrap_runtime(
        _load_json(path, "bootstrap runtime"),
        identity=identity,
    )


def _validate_terminal_resource_use(
    value: Mapping[str, Any],
    *,
    checkpoint_resource_use: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if set(value) != {
        "charged_seconds",
        "evaluation_episodes",
        "optimizer_updates",
        "total_episodes",
        "training_episodes",
    }:
        raise ExperimentBlocked("terminal resource fields mismatch")
    normalized = {
        "charged_seconds": _nonnegative_number(
            value["charged_seconds"], "terminal charged seconds"
        ),
        **{
            name: _nonnegative_seed(value[name], f"terminal resource {name}")
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
    ):
        raise ExperimentBlocked("terminal resource coordinates mismatch")
    limits = experiment_contract()["limits"]
    if (
        normalized["optimizer_updates"] > limits["max_optimizer_updates"]
        or normalized["training_episodes"] > limits["max_training_episodes"]
        or normalized["evaluation_episodes"] > limits["max_evaluation_episodes"]
        or normalized["total_episodes"] > limits["max_total_episodes"]
        or normalized["charged_seconds"] > limits["max_wall_seconds"]
    ):
        raise ExperimentBlocked("terminal resource limit exceeded")
    return normalized


def _validate_training_chunk(
    value: Mapping[str, Any], *, expected_index: int
) -> tuple[dict[str, Any], str | None, str | None]:
    chunk = copy.deepcopy(dict(value))
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
    if set(chunk) != required:
        raise ExperimentBlocked("training chunk fields mismatch")
    if chunk["schema_version"] != _CHUNK_SUMMARY_SCHEMA_VERSION:
        raise ExperimentBlocked("training chunk schema mismatch")
    if chunk["complete"] is not True or chunk["chunk_index"] != expected_index:
        raise ExperimentBlocked("training chunk coordinate mismatch")
    if (
        chunk["family_entropy_coefficient"] != 0.01
        or chunk["conditional_entropy_coefficient"] != 0.01
    ):
        raise ExperimentBlocked("training chunk coefficient mismatch")
    episodes = _nonnegative_seed(chunk["episodes"], "training chunk episodes")
    decisions = _nonnegative_seed(chunk["decisions"], "training chunk decisions")
    if episodes != experiment_contract()["limits"]["episodes_per_update"]:
        raise ExperimentBlocked("training chunk must contain exactly 64 episodes")
    raw_episode_seeds = chunk["episode_seeds"]
    if not isinstance(raw_episode_seeds, list):
        raise ExperimentBlocked("training chunk episode seeds must be a list")
    episode_seeds = [
        _nonnegative_seed(seed, f"training chunk seed[{seed_index}]")
        for seed_index, seed in enumerate(raw_episode_seeds)
    ]
    if len(episode_seeds) != episodes or len(set(episode_seeds)) != episodes:
        raise ExperimentBlocked("training chunk episode seeds are invalid")
    if decisions <= 0:
        raise ExperimentBlocked("training chunk decision count is invalid")
    if chunk["optimizer_update"] != expected_index + 1:
        raise ExperimentBlocked("training chunk optimizer coordinate mismatch")
    for name in (
        "gradient_norm_after_clip",
        "gradient_norm_before_clip",
        "loss",
        "mean_expected_conditional_entropy",
        "mean_family_entropy",
        "normalized_return_mean",
        "normalized_return_std",
        "policy_loss",
    ):
        _finite_number(chunk[name], f"training chunk {name}")
    if (
        chunk["gradient_norm_after_clip"] < 0.0
        or chunk["gradient_norm_before_clip"] < 0.0
        or chunk["gradient_norm_after_clip"] > 1.0 + 1e-6
    ):
        raise ExperimentBlocked("training chunk gradient norm mismatch")
    rows = chunk["diagnostic_rows"]
    if not isinstance(rows, list) or len(rows) != decisions:
        raise ExperimentBlocked("training chunk diagnostic count mismatch")
    first_before: str | None = None
    previous_after: str | None = None
    normalized_rows = []
    for row_index, raw in enumerate(rows):
        if not isinstance(raw, Mapping):
            raise ExperimentBlocked("training diagnostic row is invalid")
        row = copy.deepcopy(dict(raw))
        if row.get("selection_mode") != _TRAINING_SELECTION_MODE:
            raise ExperimentBlocked("training diagnostic selection mode mismatch")
        hashes = row.get("action_generator_state_sha256")
        if not isinstance(hashes, Mapping) or set(hashes) != {
            "after_conditional",
            "after_family",
            "before_family",
        }:
            raise ExperimentBlocked("training diagnostic generator hashes mismatch")
        normalized_hashes = dict(hashes)
        if any(
            not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest)
            for digest in normalized_hashes.values()
        ):
            raise ExperimentBlocked("training diagnostic generator hash is invalid")
        if len(set(normalized_hashes.values())) != 3:
            raise ExperimentBlocked("training diagnostic generator stages did not advance")
        if previous_after is not None and normalized_hashes["before_family"] != previous_after:
            raise ExperimentBlocked("training generator hash chain mismatch")
        if row_index == 0:
            first_before = normalized_hashes["before_family"]
        previous_after = normalized_hashes["after_conditional"]
        legal_ids = row.get("legal_action_ids")
        if (
            not isinstance(legal_ids, list)
            or not legal_ids
            or row.get("selected_action_id") not in legal_ids
        ):
            raise ExperimentBlocked("training diagnostic selected action is illegal")
        row["action_generator_state_sha256"] = normalized_hashes
        normalized_rows.append(row)
    resource_use = chunk["resource_use"]
    if not isinstance(resource_use, Mapping) or set(resource_use) != {
        "charged_seconds",
        "completed_decisions",
        "evaluation_episodes",
        "optimizer_updates",
        "total_episodes",
        "training_episodes",
    }:
        raise ExperimentBlocked("training chunk resource use is invalid")
    normalized_resource_use = {
        "charged_seconds": _nonnegative_number(
            resource_use["charged_seconds"], "chunk charged seconds"
        ),
        **{
            name: _nonnegative_seed(resource_use[name], f"chunk resource {name}")
            for name in (
                "completed_decisions",
                "evaluation_episodes",
                "optimizer_updates",
                "total_episodes",
                "training_episodes",
            )
        },
    }
    chunk["diagnostic_rows"] = normalized_rows
    chunk["episode_seeds"] = episode_seeds
    chunk["resource_use"] = normalized_resource_use
    return chunk, first_before, previous_after


def _chunk_resource_from_runtime(runtime: Mapping[str, Any]) -> dict[str, Any]:
    coordinates = runtime["coordinates"]
    resources = runtime["resource_use"]
    return {
        "charged_seconds": resources["charged_seconds"],
        "completed_decisions": coordinates["completed_decisions"],
        "evaluation_episodes": resources["evaluation_episodes"],
        "optimizer_updates": resources["optimizer_updates"],
        "total_episodes": resources["total_episodes"],
        "training_episodes": resources["training_episodes"],
    }


def _runtime_action_generator_sha256(runtime: Mapping[str, Any]) -> str:
    states = runtime["states"]
    if not isinstance(states, Mapping):
        raise ExperimentBlocked("runtime checkpoint states are invalid")
    generator = states.get("action_generator")
    if not isinstance(generator, Mapping) or set(generator) != {
        "dtype",
        "shape",
        "values",
    }:
        raise ExperimentBlocked("runtime action generator state is invalid")
    if generator["dtype"] != "uint8" or not isinstance(generator["shape"], list):
        raise ExperimentBlocked("runtime action generator state is invalid")
    shape = [
        _nonnegative_seed(value, "runtime action generator shape")
        for value in generator["shape"]
    ]
    values = generator["values"]
    if not isinstance(values, list):
        raise ExperimentBlocked("runtime action generator state is invalid")
    normalized_values = [
        _nonnegative_seed(value, "runtime action generator byte")
        for value in values
    ]
    expected_size = 1
    for dimension in shape:
        expected_size *= dimension
    if (
        any(value > 255 for value in normalized_values)
        or len(normalized_values) != expected_size
    ):
        raise ExperimentBlocked("runtime action generator state is invalid")
    return hashlib.sha256(bytes(normalized_values)).hexdigest()


def build_checkpoint_envelope(
    runtime_checkpoint: Mapping[str, Any],
    *,
    identity: Mapping[str, Any],
    checkpoint_index: int,
    previous_checkpoint_bytes: bytes | None,
    training_chunk: Mapping[str, Any],
) -> dict[str, Any]:
    """Wrap one complete runtime checkpoint in a standard-library identity chain."""
    normalized_identity = _validate_execution_identity(identity)
    index = _nonnegative_seed(checkpoint_index, "checkpoint index")
    if index <= 0:
        raise ExperimentBlocked("checkpoint index must be positive")
    runtime = _validate_runtime_checkpoint_control(runtime_checkpoint)
    if runtime["coordinates"]["next_chunk_index"] != index:
        raise ExperimentBlocked("checkpoint runtime coordinate mismatch")
    chunk, _, _ = _validate_training_chunk(
        training_chunk, expected_index=index - 1
    )
    if chunk["resource_use"] != _chunk_resource_from_runtime(runtime):
        raise ExperimentBlocked("checkpoint chunk resource use mismatch")
    if previous_checkpoint_bytes is None:
        if index != 1:
            raise ExperimentBlocked("noninitial checkpoint lacks predecessor")
        predecessor = None
    else:
        if not isinstance(previous_checkpoint_bytes, bytes) or not previous_checkpoint_bytes:
            raise ExperimentBlocked("previous checkpoint bytes are invalid")
        if index == 1:
            raise ExperimentBlocked("initial checkpoint cannot have predecessor")
        predecessor = hashlib.sha256(previous_checkpoint_bytes).hexdigest()
    return {
        "authority": registration_authority(),
        "checkpoint_index": index,
        "complete": True,
        "identity": normalized_identity,
        "previous_checkpoint_sha256": predecessor,
        "runtime": runtime,
        "schema_version": CHECKPOINT_ENVELOPE_SCHEMA_VERSION,
        "training_chunk": chunk,
    }


def _validate_checkpoint_envelope(
    value: Mapping[str, Any],
    *,
    identity: Mapping[str, Any],
    expected_index: int,
    previous_checkpoint_sha256: str | None,
) -> dict[str, Any]:
    checkpoint = copy.deepcopy(dict(value))
    if set(checkpoint) != {
        "authority",
        "checkpoint_index",
        "complete",
        "identity",
        "previous_checkpoint_sha256",
        "runtime",
        "schema_version",
        "training_chunk",
    }:
        raise ExperimentBlocked("checkpoint envelope fields mismatch")
    if checkpoint["schema_version"] != CHECKPOINT_ENVELOPE_SCHEMA_VERSION:
        raise ExperimentBlocked("checkpoint envelope schema mismatch")
    if checkpoint["authority"] != registration_authority():
        raise ExperimentBlocked("checkpoint authority mismatch")
    if checkpoint["complete"] is not True:
        raise ExperimentBlocked("checkpoint is incomplete")
    normalized_identity = _validate_execution_identity(identity)
    if checkpoint["identity"] != normalized_identity:
        raise ExperimentBlocked("checkpoint identity mismatch")
    if checkpoint["checkpoint_index"] != expected_index:
        raise ExperimentBlocked("checkpoint index mismatch")
    if checkpoint["previous_checkpoint_sha256"] != previous_checkpoint_sha256:
        raise ExperimentBlocked("checkpoint predecessor mismatch")
    runtime = _validate_runtime_checkpoint_control(checkpoint["runtime"])
    if runtime["coordinates"]["next_chunk_index"] != expected_index:
        raise ExperimentBlocked("checkpoint runtime coordinate mismatch")
    chunk, _, _ = _validate_training_chunk(
        checkpoint["training_chunk"], expected_index=expected_index - 1
    )
    if chunk["resource_use"] != _chunk_resource_from_runtime(runtime):
        raise ExperimentBlocked("checkpoint chunk resource use mismatch")
    checkpoint["identity"] = normalized_identity
    checkpoint["runtime"] = runtime
    checkpoint["training_chunk"] = chunk
    return checkpoint


def publish_checkpoint(
    output_path: Path | str,
    checkpoint: Mapping[str, Any],
    *,
    lease: ExecutionLease,
    identity: Mapping[str, Any],
) -> Path:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    index = checkpoint.get("checkpoint_index")
    if isinstance(index, bool) or not isinstance(index, int) or index <= 0:
        raise ExperimentBlocked("checkpoint index is invalid")
    checkpoint_dir = output / "checkpoints"
    previous_path = checkpoint_dir / f"checkpoint_{index - 1:04d}.json"
    predecessor = (
        hashlib.sha256(previous_path.read_bytes()).hexdigest()
        if index > 1 and previous_path.is_file()
        else None
    )
    normalized = _validate_checkpoint_envelope(
        checkpoint,
        identity=normalized_identity,
        expected_index=index,
        previous_checkpoint_sha256=predecessor,
    )
    if index == 1:
        predecessor_runtime = load_bootstrap_runtime(
            output,
            identity=normalized_identity,
        )["runtime"]
    else:
        if not previous_path.is_file():
            raise ExperimentBlocked("checkpoint predecessor is missing")
        previous_checkpoint = _load_json(previous_path, previous_path.name)
        if not isinstance(previous_checkpoint, Mapping) or not isinstance(
            previous_checkpoint.get("runtime"), Mapping
        ):
            raise ExperimentBlocked("checkpoint predecessor runtime is invalid")
        predecessor_runtime = _validate_runtime_checkpoint_control(
            previous_checkpoint["runtime"]
        )
    first_hashes = normalized["training_chunk"]["diagnostic_rows"][0][
        "action_generator_state_sha256"
    ]
    last_hashes = normalized["training_chunk"]["diagnostic_rows"][-1][
        "action_generator_state_sha256"
    ]
    if first_hashes["before_family"] != _runtime_action_generator_sha256(
        predecessor_runtime
    ):
        raise ExperimentBlocked("checkpoint generator does not start at predecessor")
    if last_hashes["after_conditional"] != _runtime_action_generator_sha256(
        normalized["runtime"]
    ):
        raise ExperimentBlocked("checkpoint generator does not close its chunk")
    initialize_resource_ledger(
        output,
        identity=normalized_identity,
        lease=lease,
    )
    publish_resource_prefix(
        output,
        identity=normalized_identity,
        lease=lease,
        resource_use=normalized["runtime"]["resource_use"],
        event={
            "kind": "checkpoint_reconciled",
            "phase": "training",
            "seed": None,
        },
    )
    path = checkpoint_dir / f"checkpoint_{index:04d}.json"
    _atomic_write_once_or_same(path, canonical_json_bytes(normalized))
    return path


def validate_checkpoint_chain(
    output_path: Path | str,
    *,
    identity: Mapping[str, Any],
    registration: Mapping[str, Any],
) -> list[dict[str, Any]]:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    normalized_registration = validate_registration(registration)
    train_sequence = (
        normalized_registration["cohorts"]["train"]
        * normalized_registration["contract"]["cohorts"]["train_passes"]
    )
    episodes_per_update = normalized_registration["limits"]["episodes_per_update"]
    checkpoint_dir = output / "checkpoints"
    if not checkpoint_dir.is_dir():
        return []
    paths = sorted(checkpoint_dir.glob("checkpoint_*.json"))
    bootstrap = load_bootstrap_runtime(output, identity=normalized_identity)
    chain = []
    previous_sha256: str | None = None
    previous_generator_sha256 = _runtime_action_generator_sha256(
        bootstrap["runtime"]
    )
    for index, path in enumerate(paths, start=1):
        if path.name != f"checkpoint_{index:04d}.json":
            raise ExperimentBlocked("checkpoint filenames are not contiguous")
        payload = path.read_bytes()
        checkpoint = _validate_checkpoint_envelope(
            _load_json(path, path.name),
            identity=normalized_identity,
            expected_index=index,
            previous_checkpoint_sha256=previous_sha256,
        )
        start = (index - 1) * episodes_per_update
        expected_seeds = train_sequence[start : start + episodes_per_update]
        if checkpoint["training_chunk"]["episode_seeds"] != expected_seeds:
            raise ExperimentBlocked("checkpoint seed order differs from registration")
        first_hashes = checkpoint["training_chunk"]["diagnostic_rows"][0][
            "action_generator_state_sha256"
        ]
        last_hashes = checkpoint["training_chunk"]["diagnostic_rows"][-1][
            "action_generator_state_sha256"
        ]
        if first_hashes["before_family"] != previous_generator_sha256:
            raise ExperimentBlocked("checkpoint generator chain lacks bootstrap anchor")
        runtime_generator_sha256 = _runtime_action_generator_sha256(
            checkpoint["runtime"]
        )
        if last_hashes["after_conditional"] != runtime_generator_sha256:
            raise ExperimentBlocked("checkpoint generator state does not close chunk")
        chain.append(checkpoint)
        previous_generator_sha256 = runtime_generator_sha256
        previous_sha256 = hashlib.sha256(payload).hexdigest()
    return chain


def _deterministic_gzip(payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="",
        mode="wb",
        compresslevel=9,
        fileobj=buffer,
        mtime=0,
    ) as handle:
        handle.write(payload)
    return buffer.getvalue()


def build_training_rows_artifact(
    chunk_summaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    chunks = []
    previous_after: str | None = None
    for index, raw in enumerate(chunk_summaries):
        chunk, first_before, last_after = _validate_training_chunk(
            raw, expected_index=index
        )
        if previous_after is not None and first_before != previous_after:
            raise ExperimentBlocked("training generator hash chain mismatch")
        previous_after = last_after
        chunks.append(chunk)
    value = {
        "authority": registration_authority(),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "schema_version": TRAINING_ROWS_SCHEMA_VERSION,
    }
    canonical = canonical_json_bytes(value)
    stored = _deterministic_gzip(canonical)
    return {
        "binding": {
            "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
            "canonical_size_bytes": len(canonical),
            "compression": "gzip-mtime-zero-v1",
            "path": "training_rows.json.gz",
            "sha256": hashlib.sha256(stored).hexdigest(),
            "size_bytes": len(stored),
        },
        "canonical_bytes": canonical,
        "stored_bytes": stored,
        "value": value,
    }


def _validate_training_rows_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    binding = copy.deepcopy(dict(value))
    if set(binding) != {
        "canonical_sha256",
        "canonical_size_bytes",
        "compression",
        "path",
        "sha256",
        "size_bytes",
    }:
        raise ExperimentBlocked("training rows binding fields mismatch")
    if (
        binding["path"] != "training_rows.json.gz"
        or binding["compression"] != "gzip-mtime-zero-v1"
    ):
        raise ExperimentBlocked("training rows binding identity mismatch")
    for field in ("canonical_sha256", "sha256"):
        if not isinstance(binding[field], str) or not _SHA256_RE.fullmatch(
            binding[field]
        ):
            raise ExperimentBlocked("training rows binding digest is invalid")
    for field in ("canonical_size_bytes", "size_bytes"):
        if (
            isinstance(binding[field], bool)
            or not isinstance(binding[field], int)
            or binding[field] <= 0
        ):
            raise ExperimentBlocked("training rows binding size is invalid")
    return binding


def publish_training_rows(
    output_path: Path | str,
    chunk_summaries: Sequence[Mapping[str, Any]],
    *,
    lease: ExecutionLease,
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    artifact = build_training_rows_artifact(chunk_summaries)
    _atomic_write_once_or_same(
        output / "training_rows.json.gz", artifact["stored_bytes"]
    )
    return copy.deepcopy(artifact["binding"])


def _terminal_artifact_inventory(
    output: Path, *, training_rows_binding: Mapping[str, Any]
) -> list[dict[str, Any]]:
    special = _validate_training_rows_binding(training_rows_binding)
    temporaries = sorted(
        candidate.relative_to(output).as_posix()
        for candidate in output.rglob("*")
        if candidate.is_file() and candidate.name.endswith(".tmp")
    )
    if temporaries:
        raise ExperimentBlocked(
            "terminal output contains an unreconciled temporary: "
            + ", ".join(temporaries)
        )
    rows = []
    for path in sorted(
        (
            candidate
            for candidate in output.rglob("*")
            if candidate.is_file()
            and candidate.name not in {".execution.lease", "artifact_manifest.json"}
        ),
        key=lambda candidate: candidate.relative_to(output).as_posix(),
    ):
        relative = path.relative_to(output).as_posix()
        payload = path.read_bytes()
        binding = {
            "path": relative,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
        if relative == special["path"]:
            if (
                binding["sha256"] != special["sha256"]
                or binding["size_bytes"] != special["size_bytes"]
            ):
                raise ExperimentBlocked("stored training rows binding mismatch")
            binding.update(
                {
                    "canonical_sha256": special["canonical_sha256"],
                    "canonical_size_bytes": special["canonical_size_bytes"],
                    "compression": special["compression"],
                }
            )
        rows.append(binding)
    return rows


def _build_terminal_intent(
    *,
    identity: Mapping[str, Any],
    evaluation: Mapping[str, Any] | None,
    final_model: Mapping[str, Any],
    resource_use: Mapping[str, Any],
    isolation_post: Mapping[str, Any],
    algorithm_verdict: str,
    reason: str,
    holdout_accessed: bool,
) -> dict[str, Any]:
    intent = {
        "algorithm_verdict": algorithm_verdict,
        "authority": registration_authority(),
        "evaluation": (
            None if evaluation is None else copy.deepcopy(dict(evaluation))
        ),
        "final_model": copy.deepcopy(dict(final_model)),
        "holdout_accessed": holdout_accessed,
        "identity": _validate_execution_identity(identity),
        "isolation_post": copy.deepcopy(dict(isolation_post)),
        "reason": reason.strip(),
        "resource_use": copy.deepcopy(dict(resource_use)),
        "schema_version": TERMINAL_INTENT_SCHEMA_VERSION,
    }
    canonical_json_bytes(intent)
    return intent


def _validate_terminal_intent(
    value: Mapping[str, Any], *, identity: Mapping[str, Any]
) -> dict[str, Any]:
    intent = copy.deepcopy(dict(value))
    if set(intent) != {
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
    }:
        raise ExperimentBlocked("terminal intent fields mismatch")
    if intent["schema_version"] != TERMINAL_INTENT_SCHEMA_VERSION:
        raise ExperimentBlocked("terminal intent schema mismatch")
    if intent["authority"] != registration_authority():
        raise ExperimentBlocked("terminal intent authority mismatch")
    if intent["identity"] != _validate_execution_identity(identity):
        raise ExperimentBlocked("terminal intent identity mismatch")
    if intent["algorithm_verdict"] not in _TERMINAL_VERDICTS:
        raise ExperimentBlocked("terminal intent verdict is invalid")
    if not isinstance(intent["reason"], str) or not intent["reason"].strip():
        raise ExperimentBlocked("terminal intent reason is invalid")
    if type(intent["holdout_accessed"]) is not bool:
        raise ExperimentBlocked("terminal intent holdout access is invalid")
    if not isinstance(intent["final_model"], Mapping) or not intent["final_model"]:
        raise ExperimentBlocked("terminal intent model is invalid")
    if not isinstance(intent["resource_use"], Mapping):
        raise ExperimentBlocked("terminal intent resources are invalid")
    _validate_isolation_identity(intent["isolation_post"])
    if intent["evaluation"] is not None and not isinstance(
        intent["evaluation"], Mapping
    ):
        raise ExperimentBlocked("terminal intent evaluation is invalid")
    canonical_json_bytes(intent)
    return intent


def publish_experiment_terminal(
    output_path: Path | str,
    *,
    registration: Mapping[str, Any],
    authorization: Mapping[str, Any],
    expected_command: Sequence[str],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    training_rows_binding: Mapping[str, Any],
    evaluation: Mapping[str, Any] | None,
    final_model: Mapping[str, Any],
    resource_use: Mapping[str, Any],
    isolation_post: Mapping[str, Any],
    verdict: str,
    terminal_reason: str,
    holdout_accessed: bool | None = None,
) -> dict[str, Any]:
    """Publish a complete terminal bundle and write the manifest last."""
    output = Path(output_path)
    normalized_identity = _validate_execution_identity(identity)
    _require_execution_lease(lease, output, normalized_identity)
    normalized_registration = validate_registration(registration)
    normalized_authorization = validate_execution_authorization(
        authorization,
        normalized_registration,
        expected_command=expected_command,
    )
    if not isinstance(verdict, str) or verdict not in _TERMINAL_VERDICTS:
        raise ExperimentBlocked("terminal verdict is invalid")
    if not isinstance(terminal_reason, str) or not terminal_reason.strip():
        raise ExperimentBlocked("terminal reason is invalid")
    algorithm_verdict = verdict
    algorithm_reason = terminal_reason.strip()
    if not isinstance(final_model, Mapping) or not final_model:
        raise ExperimentBlocked("terminal final model is invalid")
    canonical_json_bytes(dict(final_model))
    if not isinstance(resource_use, Mapping):
        raise ExperimentBlocked("terminal resource use is invalid")
    if holdout_accessed is not None and type(holdout_accessed) is not bool:
        raise ExperimentBlocked("terminal holdout access is invalid")
    normalized_post = _validate_isolation_identity(isolation_post)
    isolation_pre = normalized_registration["isolation_identity"]
    isolation_unchanged = normalized_post == isolation_pre
    if not isolation_unchanged:
        verdict = "experiment_invalid"
        terminal_reason = (
            f"{terminal_reason.strip()}; production isolation changed"
        )

    staged_registration = _load_json(output / "registration.json", "registration")
    staged_authorization = _load_json(output / "authorization.json", "authorization")
    if (
        staged_registration != normalized_registration
        or staged_authorization != normalized_authorization
    ):
        raise ExperimentBlocked("staged controls drifted")
    expected_identity = {
        "authorization_sha256": hashlib.sha256(
            canonical_json_bytes(normalized_authorization)
        ).hexdigest(),
        "logical_execution_id": normalized_registration["logical_experiment_id"],
        "registration_sha256": hashlib.sha256(
            canonical_json_bytes(normalized_registration)
        ).hexdigest(),
    }
    if normalized_identity != expected_identity:
        raise ExperimentBlocked("terminal identity mismatch")

    chain = validate_checkpoint_chain(
        output,
        identity=normalized_identity,
        registration=normalized_registration,
    )
    bootstrap = load_bootstrap_runtime(
        output,
        identity=normalized_identity,
    )
    binding = _validate_training_rows_binding(training_rows_binding)
    training_path = output / binding["path"]
    if not training_path.is_file():
        raise ExperimentBlocked("training rows artifact is missing")
    stored = training_path.read_bytes()
    try:
        canonical_training = gzip.decompress(stored)
        training_value = json.loads(
            canonical_training,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExperimentBlocked("training rows artifact is invalid") from exc
    if (
        canonical_json_bytes(training_value) != canonical_training
        or hashlib.sha256(canonical_training).hexdigest()
        != binding["canonical_sha256"]
        or len(canonical_training) != binding["canonical_size_bytes"]
        or hashlib.sha256(stored).hexdigest() != binding["sha256"]
        or len(stored) != binding["size_bytes"]
    ):
        raise ExperimentBlocked("training rows artifact binding mismatch")
    rebuilt_training = build_training_rows_artifact(training_value.get("chunks", []))
    if rebuilt_training["value"] != training_value or rebuilt_training["binding"] != binding:
        raise ExperimentBlocked("training rows artifact does not replay")
    if len(chain) != training_value["chunk_count"] or any(
        checkpoint["training_chunk"] != chunk
        for checkpoint, chunk in zip(chain, training_value["chunks"], strict=True)
    ):
        raise ExperimentBlocked("checkpoint and training-row coordinates differ")
    normalized_resource_use = _validate_terminal_resource_use(
        resource_use,
        checkpoint_resource_use=(
            chain[-1]["runtime"]["resource_use"] if chain else None
        ),
    )
    ledger = publish_resource_prefix(
        output,
        identity=normalized_identity,
        lease=lease,
        resource_use=normalized_resource_use,
        event={
            "kind": "terminal_reconciled",
            "phase": "terminal",
            "seed": None,
        },
    )
    if ledger["resource_use"] != _normalize_resource_prefix(
        normalized_resource_use
    ):
        raise ExperimentBlocked("terminal resources differ from the ledger")
    if chain:
        durable_model = chain[-1]["runtime"]["states"]["model"]
        model_label = "latest checkpoint"
    else:
        durable_model = bootstrap["runtime"]["states"]["model"]
        model_label = "bootstrap runtime"
    if durable_model != dict(final_model):
        raise ExperimentBlocked(f"terminal model differs from the {model_label}")

    journal = validate_execution_journal(
        _load_json(output / "execution_journal.json", "execution journal"),
        identity=normalized_identity,
    )
    previous_state = journal["records"][-1]["state"]
    terminal_already_committed = previous_state == "terminal"
    requires_invalid_transition = (
        not isolation_unchanged
        and previous_state not in {"invalid", "terminal"}
    )
    if requires_invalid_transition:
        if "invalid" not in _JOURNAL_TRANSITIONS.get(previous_state, set()):
            raise ExperimentBlocked(
                "changed production isolation cannot transition to invalid"
            )
    if terminal_already_committed:
        expected_terminal_details = {
            "reason": terminal_reason.strip(),
            "verdict": verdict,
        }
        if journal["records"][-1]["details"] != expected_terminal_details:
            raise ExperimentBlocked("committed terminal journal differs")
    elif not requires_invalid_transition:
        valid_previous = {
            "experiment_blocked": {"infrastructure_interrupted"},
            "experiment_invalid": {
                "canary_completed",
                "holdout_completed",
                "invalid",
            },
            "experiment_stopped_at_canary": {"canary_completed"},
            "experiment_stopped_during_training_for_family_saturation": {
                "training_stopped_family_saturation"
            },
            "experiment_valid_with_floor_only_signal": {"holdout_completed"},
            "experiment_valid_with_victory_signal": {"holdout_completed"},
            "experiment_valid_without_learning_signal": {"holdout_completed"},
        }[verdict]
        if previous_state not in valid_previous:
            raise ExperimentBlocked("terminal verdict does not match journal state")
    if evaluation is None:
        if verdict not in {
            "experiment_blocked",
            "experiment_invalid",
            "experiment_stopped_during_training_for_family_saturation",
        }:
            raise ExperimentBlocked("terminal verdict requires evaluation evidence")
        evaluation_value = None
        observed_holdout_access = (
            False if holdout_accessed is None else holdout_accessed
        )
    else:
        evaluation_value = copy.deepcopy(dict(evaluation))
        canonical_json_bytes(evaluation_value)
        if (
            isolation_unchanged
            and evaluation_value.get("verdict") != verdict
        ):
            raise ExperimentBlocked("evaluation and terminal verdict differ")
        holdout = evaluation_value.get("holdout")
        if not isinstance(holdout, Mapping) or type(holdout.get("accessed")) is not bool:
            raise ExperimentBlocked("evaluation holdout access is invalid")
        observed_holdout_access = holdout["accessed"]
        if (
            holdout_accessed is not None
            and holdout_accessed is not observed_holdout_access
        ):
            raise ExperimentBlocked("declared and evaluated holdout access differ")
        if verdict == "experiment_stopped_at_canary" and observed_holdout_access:
            raise ExperimentBlocked("canary stop accessed holdout")
        if verdict.startswith("experiment_valid_") and not observed_holdout_access:
            raise ExperimentBlocked("complete verdict lacks holdout access")
    if (
        verdict
        in {
            "experiment_stopped_at_canary",
            "experiment_stopped_during_training_for_family_saturation",
        }
        and observed_holdout_access
    ):
        raise ExperimentBlocked("pre-holdout verdict accessed holdout")

    intent = _build_terminal_intent(
        identity=normalized_identity,
        evaluation=evaluation_value,
        final_model=final_model,
        resource_use=normalized_resource_use,
        isolation_post=normalized_post,
        algorithm_verdict=algorithm_verdict,
        reason=algorithm_reason,
        holdout_accessed=observed_holdout_access,
    )
    _atomic_write_once_or_same(
        output / "terminal_intent.json", canonical_json_bytes(intent)
    )
    authority = registration_authority()
    payloads = {
        "evaluation.json": {
            "authority": authority,
            "evaluation": evaluation_value,
            "schema_version": EVALUATION_ARTIFACT_SCHEMA_VERSION,
        },
        "final_model.json": {
            "authority": authority,
            "model": copy.deepcopy(dict(final_model)),
            "model_loading_authorized": False,
            "schema_version": FINAL_MODEL_SCHEMA_VERSION,
        },
        "isolation.json": {
            "authority": authority,
            "post": normalized_post,
            "pre": isolation_pre,
            "schema_version": ISOLATION_SCHEMA_VERSION,
            "unchanged": isolation_unchanged,
        },
        "metrics.json": {
            "authority": authority,
            "checkpoint_count": len(chain),
            "formal_rl_readiness_established": False,
            "isolation_unchanged": isolation_unchanged,
            "policy_quality_established": False,
            "resource_use": normalized_resource_use,
            "schema_version": METRICS_SCHEMA_VERSION,
            "target_supported_outcomes_established": False,
            "training_chunk_count": training_value["chunk_count"],
            "verdict": verdict,
        },
        "report.json": {
            "authority": authority,
            "formal_rl_readiness": "unchanged_not_ready",
            "logical_execution_id": normalized_identity["logical_execution_id"],
            "policy_quality_claim": False,
            "schema_version": REPORT_SCHEMA_VERSION,
            "target_supported_outcome_claim": False,
            "verdict": verdict,
        },
        "terminal.json": {
            "authority": authority,
            "checkpoint_count": len(chain),
            "holdout_accessed": observed_holdout_access,
            "identity": normalized_identity,
            "reason": terminal_reason.strip(),
            "schema_version": TERMINAL_SCHEMA_VERSION,
            "training_rows_binding": binding,
            "verdict": verdict,
        },
    }
    for name, value in sorted(payloads.items()):
        _atomic_write_once_or_same(output / name, canonical_json_bytes(value))
    if not terminal_already_committed:
        if requires_invalid_transition:
            append_execution_journal(
                output,
                identity=normalized_identity,
                lease=lease,
                expected_previous_state=previous_state,
                state="invalid",
                details={"reason": "production isolation changed"},
            )
            previous_state = "invalid"
        append_execution_journal(
            output,
            identity=normalized_identity,
            lease=lease,
            expected_previous_state=previous_state,
            state="terminal",
            details={"reason": terminal_reason.strip(), "verdict": verdict},
        )
    inventory = _terminal_artifact_inventory(
        output, training_rows_binding=binding
    )
    required = set(registered_output_inventory()["required_terminal_files"])
    observed = {row["path"] for row in inventory}
    if required - {"artifact_manifest.json"} - observed:
        raise ExperimentBlocked("terminal output inventory is incomplete")
    manifest = {
        "artifact_count": len(inventory),
        "artifacts": inventory,
        "authority": authority,
        "identity": normalized_identity,
        "manifest_kind": "full_terminal",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": verdict,
    }
    _atomic_write_once_or_same(
        output / "artifact_manifest.json", canonical_json_bytes(manifest)
    )
    return manifest


def _execution_identity(
    registration: Mapping[str, Any], authorization: Mapping[str, Any]
) -> dict[str, str]:
    registration_bytes = canonical_json_bytes(dict(registration))
    authorization_bytes = canonical_json_bytes(dict(authorization))
    return {
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "logical_execution_id": registration["logical_experiment_id"],
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
    }


def _load_execution_dependencies(
    registration: Mapping[str, Any], *, repo_root: Path | str = REPO_ROOT
) -> dict[str, Any]:
    """Load registered native code before importing the Torch runtime."""
    normalized = validate_registration(registration)
    root = Path(repo_root).resolve()
    root_text = str(root)
    if not any(
        Path(entry or os.curdir).resolve() == root
        for entry in sys.path
    ):
        sys.path.insert(0, root_text)
    if "torch" in sys.modules:
        raise ExperimentBlocked("Torch was imported before registered native loading")
    native_name = "sts_lightspeed_noncombat_adapter"
    if native_name in sys.modules:
        raise ExperimentBlocked("native module was imported before the execution gate")
    adapter = importlib.import_module("analysis_scripts.noncombat_simulator_adapter")
    expected_adapter = (root / "analysis_scripts/noncombat_simulator_adapter.py").resolve()
    if Path(getattr(adapter, "__file__", "")).resolve() != expected_adapter:
        raise ExperimentBlocked("simulator adapter resolved outside the registered repo")
    native = normalized["native_identity"]
    module = adapter.load_native_module(
        native["module"]["path"],
        dll_directories=[Path(path) for path in native["dll_directories"]],
    )
    if external_file_binding(native["module"]["path"]) != native["module"]:
        raise ExperimentBlocked("loaded native module bytes differ from registration")
    if "torch" in sys.modules:
        raise ExperimentBlocked("native loading imported Torch out of order")
    try:
        provenance = adapter.validate_provenance(native["provenance"])
        build = json.loads(
            module.build_info_json(),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ExperimentBlocked("loaded native provenance is invalid") from exc
    build["python"] = platform.python_version()
    if provenance.get("build") != build:
        raise ExperimentBlocked("loaded native build differs from registration")
    if (
        hashlib.sha256(canonical_json_bytes(provenance)).hexdigest()
        != native["provenance_sha256"]
    ):
        raise ExperimentBlocked("loaded native provenance digest mismatch")
    runtime = importlib.import_module(
        "analysis_scripts.noncombat_hierarchical_simulator_learning_runtime"
    )
    expected_runtime = (
        root
        / "analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py"
    ).resolve()
    if Path(getattr(runtime, "__file__", "")).resolve() != expected_runtime:
        raise ExperimentBlocked("hierarchical runtime resolved outside the registered repo")
    metadata = runtime.runtime_metadata()
    contract = normalized["contract"]
    if (
        metadata["algorithm"] != contract["algorithm"]
        or metadata["adapter_api_version"]
        != contract["environment"]["adapter_api_version"]
        or metadata["device"] != contract["identity"]["device"]
        or metadata["evaluation_selection"] != contract["evaluation"]["selection"]
    ):
        raise ExperimentBlocked("loaded runtime metadata differs from registration")
    return {
        "environment_type": adapter.NativeSimulatorEnvironment,
        "module": module,
        "provenance": provenance,
        "runtime": runtime,
    }


def _is_infrastructure_failure(error: BaseException) -> bool:
    current: BaseException | None = error
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (KeyboardInterrupt, SystemExit, OSError, TimeoutError)):
            return True
        current = current.__cause__ or current.__context__
    return False


def _complete_terminal_intent(
    output: Path,
    *,
    registration: Mapping[str, Any],
    authorization: Mapping[str, Any],
    expected_command: Sequence[str],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
) -> dict[str, Any]:
    intent = _validate_terminal_intent(
        _load_json(output / "terminal_intent.json", "terminal intent"),
        identity=identity,
    )
    chain = validate_checkpoint_chain(
        output,
        identity=identity,
        registration=registration,
    )
    training_binding = publish_training_rows(
        output,
        [checkpoint["training_chunk"] for checkpoint in chain],
        lease=lease,
        identity=identity,
    )
    return publish_experiment_terminal(
        output,
        registration=registration,
        authorization=authorization,
        expected_command=expected_command,
        identity=identity,
        lease=lease,
        training_rows_binding=training_binding,
        evaluation=intent["evaluation"],
        final_model=intent["final_model"],
        resource_use=intent["resource_use"],
        isolation_post=intent["isolation_post"],
        verdict=intent["algorithm_verdict"],
        terminal_reason=intent["reason"],
        holdout_accessed=intent["holdout_accessed"],
    )


def _terminalize_execution(
    output: Path,
    *,
    registration: Mapping[str, Any],
    authorization: Mapping[str, Any],
    expected_command: Sequence[str],
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    runtime_module: Any,
    runtime_state: Any,
    evaluation: Mapping[str, Any] | None,
    verdict: str,
    reason: str,
    holdout_accessed: bool | None = None,
) -> dict[str, Any]:
    isolation = registration["isolation_identity"]
    isolation_post = {
        "communication_mod_config": external_file_binding(
            isolation["communication_mod_config"]["path"]
        ),
        "production_checkpoints": snapshot_production_checkpoints(
            isolation["production_checkpoints"]["root"]
        ),
    }
    if evaluation is None:
        observed_holdout_access = (
            False if holdout_accessed is None else holdout_accessed
        )
    else:
        holdout = evaluation.get("holdout")
        if not isinstance(holdout, Mapping) or type(holdout.get("accessed")) is not bool:
            raise ExperimentBlocked("terminal evaluation holdout access is invalid")
        observed_holdout_access = holdout["accessed"]
        if (
            holdout_accessed is not None
            and holdout_accessed is not observed_holdout_access
        ):
            raise ExperimentBlocked("terminal holdout access differs from evaluation")
    intent = _build_terminal_intent(
        identity=identity,
        evaluation=evaluation,
        final_model=runtime_module.encode_model_state(runtime_state.model),
        resource_use=runtime_module.runtime_resource_use(runtime_state),
        isolation_post=isolation_post,
        algorithm_verdict=verdict,
        reason=reason,
        holdout_accessed=observed_holdout_access,
    )
    _atomic_write_once_or_same(
        output / "terminal_intent.json", canonical_json_bytes(intent)
    )
    return _complete_terminal_intent(
        output,
        registration=registration,
        authorization=authorization,
        expected_command=expected_command,
        identity=identity,
        lease=lease,
    )


def _journal_state(output: Path, identity: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    journal = validate_execution_journal(
        _load_json(output / "execution_journal.json", "execution journal"),
        identity=identity,
    )
    return journal["records"][-1]["state"], journal


def _append_journal(
    output: Path,
    *,
    identity: Mapping[str, Any],
    lease: ExecutionLease,
    previous: str,
    state: str,
    details: Mapping[str, Any],
) -> str:
    append_execution_journal(
        output,
        identity=identity,
        lease=lease,
        expected_previous_state=previous,
        state=state,
        details=details,
    )
    return state


def _recover_durable_runtime(
    output: Path,
    *,
    identity: Mapping[str, Any],
    registration: Mapping[str, Any],
    lease: ExecutionLease,
    runtime_module: Any,
) -> tuple[Any, list[dict[str, Any]], bytes | None]:
    """Restore logical state from checkpoints and merge the resource ledger."""
    chain = validate_checkpoint_chain(
        output,
        identity=identity,
        registration=registration,
    )
    if chain:
        runtime_state = runtime_module.restore_training_runtime_from_checkpoint(
            chain[-1]["runtime"]
        )
        previous_checkpoint_bytes = (
            output / "checkpoints" / f"checkpoint_{len(chain):04d}.json"
        ).read_bytes()
    else:
        bootstrap_path = (
            output / _REGISTERED_OUTPUT_INVENTORY["bootstrap_runtime"]
        )
        if bootstrap_path.is_file():
            bootstrap = load_bootstrap_runtime(output, identity=identity)
            runtime_state = runtime_module.restore_training_runtime_from_checkpoint(
                bootstrap["runtime"]
            )
        else:
            if (output / "evidence_start.json").exists():
                raise ExperimentBlocked(
                    "post-seed output lacks a bootstrap runtime"
                )
            runtime_state = runtime_module.initialize_training_runtime()
            bootstrap = publish_bootstrap_runtime(
                output,
                runtime_module.encode_checkpoint_state(runtime_state),
                identity=identity,
                lease=lease,
            )
            if bootstrap["runtime"] != runtime_module.encode_checkpoint_state(
                runtime_state
            ):
                raise ExperimentBlocked("bootstrap runtime publication drifted")
        previous_checkpoint_bytes = None
    if runtime_state.next_chunk_index != len(chain):
        raise ExperimentBlocked("runtime and checkpoint coordinates differ")
    ledger = load_resource_ledger(
        output,
        identity=identity,
        lease=lease,
    )
    resources = {
        **ledger["resource_use"],
        "optimizer_updates": runtime_state.next_chunk_index,
    }
    restore = getattr(runtime_module, "restore_consumed_resource_prefix", None)
    if not callable(restore):
        if ledger["revision"] != 0:
            raise ExperimentBlocked(
                "runtime cannot restore the durable resource prefix"
            )
    else:
        restored = restore(runtime_state, resources)
        if not isinstance(restored, Mapping) or (
            _normalize_resource_prefix(restored) != ledger["resource_use"]
        ):
            raise ExperimentBlocked("runtime resource restoration mismatch")
    return runtime_state, chain, previous_checkpoint_bytes


def execute_authorized_experiment(
    *,
    repo_root: Path | str,
    registration: Mapping[str, Any],
    authorization: Mapping[str, Any],
    expected_command: Sequence[str],
    output_dir: Path | str,
    dependency_loader: Any | None = None,
    clock: Any = time.monotonic,
) -> dict[str, Any]:
    """Execute or resume the sole immutable hierarchical experiment identity."""
    root = Path(repo_root).resolve()
    output = Path(output_dir).resolve()
    normalized_registration = validate_registration(registration)
    normalized_authorization = validate_execution_authorization(
        authorization,
        normalized_registration,
        expected_command=expected_command,
    )
    preflight = source_only_preflight(
        root,
        normalized_registration,
        normalized_authorization,
        expected_command=expected_command,
    )
    identity = _execution_identity(
        normalized_registration, normalized_authorization
    )
    loader = dependency_loader or (
        lambda value: _load_execution_dependencies(value, repo_root=root)
    )
    phase = "prestart"

    with ExecutionLease(output, identity=identity) as lease:
        marker_path = output / "evidence_start.json"
        try:
            stage_execution_controls(
                output,
                registration=normalized_registration,
                authorization=normalized_authorization,
                expected_command=expected_command,
                lease=lease,
                identity=identity,
            )
            journal_path = output / "execution_journal.json"
            if journal_path.exists():
                load_execution_journal(
                    output,
                    identity=identity,
                    lease=lease,
                )
            else:
                if marker_path.exists():
                    raise ExperimentBlocked(
                        "evidence marker exists without an execution journal"
                    )
                initialize_execution_journal(
                    output, identity=identity, lease=lease
                )
            if (
                not marker_path.exists()
                and _resource_artifact_has_evidence(output, identity=identity)
            ):
                raise ExperimentBlocked(
                    "resource evidence exists without an evidence marker"
                )
        except BaseException as exc:
            if not marker_path.exists():
                record_prestart_failure(
                    output,
                    identity=identity,
                    lease=lease,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            raise

        if (output / "terminal_intent.json").exists():
            manifest = _complete_terminal_intent(
                output,
                registration=normalized_registration,
                authorization=normalized_authorization,
                expected_command=expected_command,
                identity=identity,
                lease=lease,
            )
            return {
                "manifest": manifest,
                "preflight": preflight,
                "status": "terminal",
            }

        marker_existed = marker_path.exists()
        try:
            dependencies = loader(normalized_registration)
        except BaseException as exc:
            if not marker_existed:
                record_prestart_failure(
                    output,
                    identity=identity,
                    lease=lease,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            raise

        try:
            runtime_module = dependencies["runtime"]
            runtime_state, chain, previous_checkpoint_bytes = (
                _recover_durable_runtime(
                    output,
                    identity=identity,
                    registration=normalized_registration,
                    lease=lease,
                    runtime_module=runtime_module,
                )
            )
        except BaseException as exc:
            if not marker_path.exists():
                record_prestart_failure(
                    output,
                    identity=identity,
                    lease=lease,
                    reason=f"{type(exc).__name__}: {exc}",
                )
            raise

        state, journal = _journal_state(output, identity)
        checkpoint_records = [
            record
            for record in journal["records"]
            if record["state"] == "training_chunk_completed"
        ]
        checkpoint_journal_delta = len(chain) - len(checkpoint_records)
        if checkpoint_journal_delta not in {0, 1}:
            raise ExperimentBlocked("checkpoint and journal durable prefixes differ")
        checkpoint_ahead = checkpoint_journal_delta == 1

        if not marker_existed:
            if chain or state != "prestart_owned":
                raise ExperimentBlocked("prestart output contains empirical evidence")
        else:
            marker = _load_evidence_start(output, identity=identity)
            if chain:
                validate_same_identity_resume(
                    marker,
                    chain[-1],
                    identity=identity,
                    interruption_class="infrastructure",
                )
            elif state == "prestart_owned":
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="evidence_started",
                    details={"first_seed": marker["first_seed"]},
                )
            else:
                if state not in {
                    "evidence_started",
                    "infrastructure_interrupted",
                    "invalid",
                    "terminal",
                    "training_stopped_family_saturation",
                }:
                    raise ExperimentBlocked("post-seed output lacks a complete checkpoint")

            if state == "terminal":
                raise ExperimentBlocked("terminal execution cannot resume")
            if state == "invalid":
                details = journal["records"][-1]["details"]
                if isinstance(details.get("phase"), str) and isinstance(
                    details.get("reason"), str
                ):
                    invalid_reason = (
                        f"algorithm failure during {details['phase']}: "
                        f"{details['reason']}"
                    )
                else:
                    invalid_reason = (
                        "post-seed interruption lacks a complete checkpoint"
                    )
                manifest = _terminalize_execution(
                    output,
                    registration=normalized_registration,
                    authorization=normalized_authorization,
                    expected_command=expected_command,
                    identity=identity,
                    lease=lease,
                    runtime_module=runtime_module,
                    runtime_state=runtime_state,
                    evaluation=None,
                    verdict="experiment_invalid",
                    reason=invalid_reason,
                )
                return {
                    "manifest": manifest,
                    "preflight": preflight,
                    "status": "terminal",
                }
            if state == "training_stopped_family_saturation":
                manifest = _terminalize_execution(
                    output,
                    registration=normalized_registration,
                    authorization=normalized_authorization,
                    expected_command=expected_command,
                    identity=identity,
                    lease=lease,
                    runtime_module=runtime_module,
                    runtime_state=runtime_state,
                    evaluation=None,
                    verdict=(
                        "experiment_stopped_during_training_for_family_saturation"
                    ),
                    reason="registered family saturation gate fired",
                )
                return {
                    "manifest": manifest,
                    "preflight": preflight,
                    "status": "terminal",
                }
            if state in {"canary_started", "holdout_started"}:
                interrupted_phase = (
                    "holdout" if state == "holdout_started" else "canary"
                )
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="infrastructure_interrupted",
                    details={
                        "phase": interrupted_phase,
                        "reason": f"interrupted during {state}",
                    },
                )
                manifest = _terminalize_execution(
                    output,
                    registration=normalized_registration,
                    authorization=normalized_authorization,
                    expected_command=expected_command,
                    identity=identity,
                    lease=lease,
                    runtime_module=runtime_module,
                    runtime_state=runtime_state,
                    evaluation=None,
                    verdict="experiment_blocked",
                    reason="evaluation infrastructure interruption",
                    holdout_accessed=interrupted_phase == "holdout",
                )
                return {"manifest": manifest, "preflight": preflight, "status": "terminal"}
            if state == "canary_completed":
                details = journal["records"][-1]["details"]
                resource_use = details.get("resource_use")
                evaluation = details.get("evaluation")
                if not isinstance(resource_use, Mapping) or not isinstance(
                    evaluation, Mapping
                ):
                    raise ExperimentBlocked("durable canary evidence is invalid")
                runtime_module.restore_evaluation_resource_prefix(
                    runtime_state, resource_use
                )
                if evaluation.get("verdict") == "experiment_stopped_at_canary":
                    manifest = _terminalize_execution(
                        output,
                        registration=normalized_registration,
                        authorization=normalized_authorization,
                        expected_command=expected_command,
                        identity=identity,
                        lease=lease,
                        runtime_module=runtime_module,
                        runtime_state=runtime_state,
                        evaluation=evaluation,
                        verdict="experiment_stopped_at_canary",
                        reason="registered canary gate failed",
                    )
                    return {"manifest": manifest, "preflight": preflight, "status": "terminal"}
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="infrastructure_interrupted",
                    details={"reason": "interrupted after canary completion"},
                )
                manifest = _terminalize_execution(
                    output,
                    registration=normalized_registration,
                    authorization=normalized_authorization,
                    expected_command=expected_command,
                    identity=identity,
                    lease=lease,
                    runtime_module=runtime_module,
                    runtime_state=runtime_state,
                    evaluation=None,
                    verdict="experiment_blocked",
                    reason="interrupted before holdout start",
                )
                return {"manifest": manifest, "preflight": preflight, "status": "terminal"}
            if state == "holdout_completed":
                details = journal["records"][-1]["details"]
                evaluation = details.get("evaluation")
                resource_use = details.get("resource_use")
                if not isinstance(evaluation, Mapping) or not isinstance(
                    resource_use, Mapping
                ):
                    raise ExperimentBlocked("durable holdout evidence is invalid")
                runtime_module.restore_evaluation_resource_prefix(
                    runtime_state, resource_use
                )
                manifest = _terminalize_execution(
                    output,
                    registration=normalized_registration,
                    authorization=normalized_authorization,
                    expected_command=expected_command,
                    identity=identity,
                    lease=lease,
                    runtime_module=runtime_module,
                    runtime_state=runtime_state,
                    evaluation=evaluation,
                    verdict=evaluation["verdict"],
                    reason="registered holdout completed",
                )
                return {"manifest": manifest, "preflight": preflight, "status": "terminal"}
            if state in {
                "evidence_started",
                "evidence_resumed",
                "training_chunk_completed",
            }:
                if not chain:
                    state = _append_journal(
                        output,
                        identity=identity,
                        lease=lease,
                        previous=state,
                        state="invalid",
                        details={"reason": "post-seed interruption lacks a checkpoint"},
                    )
                    manifest = _terminalize_execution(
                        output,
                        registration=normalized_registration,
                        authorization=normalized_authorization,
                        expected_command=expected_command,
                        identity=identity,
                        lease=lease,
                        runtime_module=runtime_module,
                        runtime_state=runtime_state,
                        evaluation=None,
                        verdict="experiment_invalid",
                        reason="post-seed interruption lacks a complete checkpoint",
                    )
                    return {"manifest": manifest, "preflight": preflight, "status": "terminal"}
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="infrastructure_interrupted",
                    details={"checkpoint_index": len(chain)},
                )
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="evidence_resumed",
                    details={"checkpoint_index": len(chain)},
                )
                if checkpoint_ahead:
                    state = _append_journal(
                        output,
                        identity=identity,
                        lease=lease,
                        previous=state,
                        state="training_chunk_completed",
                        details={"checkpoint_index": len(chain)},
                    )
            elif state == "infrastructure_interrupted":
                if not chain:
                    details = journal["records"][-1]["details"]
                    interrupted_phase = details.get("phase", "training")
                    manifest = _terminalize_execution(
                        output,
                        registration=normalized_registration,
                        authorization=normalized_authorization,
                        expected_command=expected_command,
                        identity=identity,
                        lease=lease,
                        runtime_module=runtime_module,
                        runtime_state=runtime_state,
                        evaluation=None,
                        verdict="experiment_blocked",
                        reason=(
                            "infrastructure interruption during "
                            f"{interrupted_phase}"
                        ),
                        holdout_accessed=interrupted_phase == "holdout",
                    )
                    return {
                        "manifest": manifest,
                        "preflight": preflight,
                        "status": "terminal",
                    }
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="evidence_resumed",
                    details={"checkpoint_index": len(chain)},
                )
                if checkpoint_ahead:
                    state = _append_journal(
                        output,
                        identity=identity,
                        lease=lease,
                        previous=state,
                        state="training_chunk_completed",
                        details={"checkpoint_index": len(chain)},
                    )
            elif state not in {"training_completed"}:
                raise ExperimentBlocked(f"execution cannot resume from {state}")
            elif checkpoint_ahead:
                raise ExperimentBlocked(
                    "completed training journal omits a durable checkpoint"
                )

        environment_type = dependencies["environment_type"]
        module = dependencies["module"]
        provenance = dependencies["provenance"]
        ascension = normalized_registration["contract"]["environment"]["ascension"]

        def environment_factory(seed: int):
            nonlocal marker_existed, state
            if not marker_existed:
                first_seed = normalized_registration["cohorts"]["train"][0]
                if seed != first_seed:
                    raise ExperimentBlocked(
                        "first environment seed differs from registration"
                    )
                mark_evidence_start(
                    output,
                    identity=identity,
                    first_seed=first_seed,
                    lease=lease,
                )
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="evidence_started",
                    details={"first_seed": first_seed},
                )
                marker_existed = True
            return environment_type(module.Environment(seed, ascension), provenance)

        def persist_resource_prefix(
            resources: Mapping[str, Any], event: Mapping[str, Any]
        ) -> None:
            nonlocal marker_existed, state
            if not marker_existed and (
                event.get("kind") == "episode_debited"
                and event.get("phase") == "training"
            ):
                first_seed = normalized_registration["cohorts"]["train"][0]
                if event.get("seed") != first_seed:
                    raise ExperimentBlocked(
                        "first resource seed differs from registration"
                    )
                mark_evidence_start(
                    output,
                    identity=identity,
                    first_seed=first_seed,
                    lease=lease,
                )
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="evidence_started",
                    details={"first_seed": first_seed},
                )
                marker_existed = True
            publish_resource_prefix(
                output,
                identity=identity,
                lease=lease,
                resource_use=resources,
                event=event,
            )

        phase = "training"
        chunks = [checkpoint["training_chunk"] for checkpoint in chain]
        try:
            saturation = runtime_module.classify_training_family_saturation(chunks)
            if saturation["saturated"]:
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="training_stopped_family_saturation",
                    details={"classification": saturation},
                )
                manifest = _terminalize_execution(
                    output,
                    registration=normalized_registration,
                    authorization=normalized_authorization,
                    expected_command=expected_command,
                    identity=identity,
                    lease=lease,
                    runtime_module=runtime_module,
                    runtime_state=runtime_state,
                    evaluation=None,
                    verdict="experiment_stopped_during_training_for_family_saturation",
                    reason="registered family saturation gate fired",
                )
                return {"manifest": manifest, "preflight": preflight, "status": "terminal"}

            contract = normalized_registration["contract"]
            limits = normalized_registration["limits"]
            episodes_per_update = limits["episodes_per_update"]
            train_sequence = (
                normalized_registration["cohorts"]["train"]
                * contract["cohorts"]["train_passes"]
            )
            while runtime_state.next_chunk_index < limits["max_optimizer_updates"]:
                start = runtime_state.next_chunk_index * episodes_per_update
                seeds = train_sequence[start : start + episodes_per_update]
                summary = runtime_module.run_training_chunk(
                    runtime_state,
                    environment_factory=environment_factory,
                    seeds=seeds,
                    chunk_index=runtime_state.next_chunk_index,
                    max_wall_seconds=(
                        normalized_registration["limits"]["max_wall_seconds"]
                        - runtime_state.charged_seconds
                    ),
                    clock=clock,
                    on_resource_change=persist_resource_prefix,
                )
                if summary.get("episode_seeds") != list(seeds):
                    raise ExperimentBlocked(
                        "training summary seed order differs from registration"
                    )
                checkpoint = build_checkpoint_envelope(
                    runtime_module.encode_checkpoint_state(runtime_state),
                    identity=identity,
                    checkpoint_index=runtime_state.next_chunk_index,
                    previous_checkpoint_bytes=previous_checkpoint_bytes,
                    training_chunk=summary,
                )
                checkpoint_path = publish_checkpoint(
                    output, checkpoint, lease=lease, identity=identity
                )
                previous_checkpoint_bytes = checkpoint_path.read_bytes()
                chunks.append(summary)
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="training_chunk_completed",
                    details={"checkpoint_index": runtime_state.next_chunk_index},
                )
                saturation = runtime_module.classify_training_family_saturation(chunks)
                if saturation["saturated"]:
                    state = _append_journal(
                        output,
                        identity=identity,
                        lease=lease,
                        previous=state,
                        state="training_stopped_family_saturation",
                        details={"classification": saturation},
                    )
                    manifest = _terminalize_execution(
                        output,
                        registration=normalized_registration,
                        authorization=normalized_authorization,
                        expected_command=expected_command,
                        identity=identity,
                        lease=lease,
                        runtime_module=runtime_module,
                        runtime_state=runtime_state,
                        evaluation=None,
                        verdict="experiment_stopped_during_training_for_family_saturation",
                        reason="registered family saturation gate fired",
                    )
                    return {"manifest": manifest, "preflight": preflight, "status": "terminal"}

            if state != "training_completed":
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="training_completed",
                    details={"checkpoint_count": len(chunks)},
                )
            phase = "canary"
            state = _append_journal(
                output,
                identity=identity,
                lease=lease,
                previous=state,
                state="canary_started",
                details={},
            )
            initial_model = runtime_module.initialize_training_runtime().model
            evaluation_value: dict[str, Any] | None = None

            def preserve_canary(result: Mapping[str, Any]) -> None:
                nonlocal evaluation_value, state
                evaluation_value = copy.deepcopy(dict(result))
                resources = runtime_module.runtime_resource_use(runtime_state)
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="canary_completed",
                    details={"evaluation": evaluation_value, "resource_use": resources},
                )

            def begin_holdout() -> None:
                nonlocal phase, state
                phase = "holdout"
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="holdout_started",
                    details={},
                )

            def preserve_holdout(result: Mapping[str, Any]) -> None:
                nonlocal evaluation_value, state
                evaluation_value = copy.deepcopy(dict(result))
                resources = runtime_module.runtime_resource_use(runtime_state)
                state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=state,
                    state="holdout_completed",
                    details={"evaluation": evaluation_value, "resource_use": resources},
                )

            evaluation_value = runtime_module.run_conditional_evaluation(
                initial_model,
                runtime_state.model,
                environment_factory=environment_factory,
                canary_seeds=normalized_registration["cohorts"]["canary"],
                holdout_seeds=normalized_registration["cohorts"]["holdout"],
                deadline=(
                    clock()
                    + normalized_registration["limits"]["max_wall_seconds"]
                    - runtime_state.charged_seconds
                ),
                clock=clock,
                on_canary_complete=preserve_canary,
                on_holdout_start=begin_holdout,
                on_holdout_complete=preserve_holdout,
                resource_runtime=runtime_state,
                on_resource_change=persist_resource_prefix,
            )
            phase = "terminal"
            manifest = _terminalize_execution(
                output,
                registration=normalized_registration,
                authorization=normalized_authorization,
                expected_command=expected_command,
                identity=identity,
                lease=lease,
                runtime_module=runtime_module,
                runtime_state=runtime_state,
                evaluation=evaluation_value,
                verdict=evaluation_value["verdict"],
                reason="registered conditional evaluation completed",
            )
            return {"manifest": manifest, "preflight": preflight, "status": "terminal"}
        except BaseException as exc:
            if phase == "terminal":
                raise
            if not marker_path.exists():
                record_prestart_failure(
                    output,
                    identity=identity,
                    lease=lease,
                    reason=f"{type(exc).__name__}: {exc}",
                )
                raise
            current_state, current_journal = _journal_state(output, identity)
            holdout_was_accessed = any(
                record["state"] in {"holdout_started", "holdout_completed"}
                for record in current_journal["records"]
            )
            infrastructure = _is_infrastructure_failure(exc)
            if infrastructure and current_state in _JOURNAL_TRANSITIONS and (
                "infrastructure_interrupted" in _JOURNAL_TRANSITIONS[current_state]
            ):
                current_state = _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=current_state,
                    state="infrastructure_interrupted",
                    details={"phase": phase, "reason": f"{type(exc).__name__}: {exc}"},
                )
                durable = validate_checkpoint_chain(
                    output,
                    identity=identity,
                    registration=normalized_registration,
                )
                if phase == "training" and durable:
                    return {
                        "preflight": preflight,
                        "reason": f"{type(exc).__name__}: {exc}",
                        "status": "same_identity_resume_required",
                    }
                runtime_state, _, _ = _recover_durable_runtime(
                    output,
                    identity=identity,
                    registration=normalized_registration,
                    lease=lease,
                    runtime_module=runtime_module,
                )
                manifest = _terminalize_execution(
                    output,
                    registration=normalized_registration,
                    authorization=normalized_authorization,
                    expected_command=expected_command,
                    identity=identity,
                    lease=lease,
                    runtime_module=runtime_module,
                    runtime_state=runtime_state,
                    evaluation=None,
                    verdict="experiment_blocked",
                    reason=f"infrastructure interruption during {phase}",
                    holdout_accessed=holdout_was_accessed,
                )
                return {"manifest": manifest, "preflight": preflight, "status": "terminal"}
            if current_state in _JOURNAL_TRANSITIONS and "invalid" in _JOURNAL_TRANSITIONS[current_state]:
                _append_journal(
                    output,
                    identity=identity,
                    lease=lease,
                    previous=current_state,
                    state="invalid",
                    details={"phase": phase, "reason": f"{type(exc).__name__}: {exc}"},
                )
                runtime_state, _, _ = _recover_durable_runtime(
                    output,
                    identity=identity,
                    registration=normalized_registration,
                    lease=lease,
                    runtime_module=runtime_module,
                )
                manifest = _terminalize_execution(
                    output,
                    registration=normalized_registration,
                    authorization=normalized_authorization,
                    expected_command=expected_command,
                    identity=identity,
                    lease=lease,
                    runtime_module=runtime_module,
                    runtime_state=runtime_state,
                    evaluation=None,
                    verdict="experiment_invalid",
                    reason=f"algorithm failure during {phase}: {type(exc).__name__}: {exc}",
                    holdout_accessed=holdout_was_accessed,
                )
                return {"manifest": manifest, "preflight": preflight, "status": "terminal"}
            raise


def _repo_artifact_binding(
    path: Path | str,
    *,
    repo_root: Path | str,
    expected_relative: str,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(repo_root).resolve()
    artifact = Path(path).resolve()
    expected = (root / PurePosixPath(expected_relative)).resolve()
    if artifact != expected:
        raise ExperimentBlocked(f"{label} path differs from the registered path")
    value = _load_json(artifact, label)
    payload = artifact.read_bytes()
    return value, {
        "path": expected_relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def registered_execution_command(
    registration: Mapping[str, Any],
    *,
    repo_root: Path | str,
    registration_path: Path | str,
    authorization_path: Path | str,
    output_dir: Path | str,
) -> list[str]:
    """Build the sole command that an authorization may enable."""
    normalized = validate_registration(registration)
    root = Path(repo_root).resolve()
    registration_file = Path(registration_path).resolve()
    authorization_file = Path(authorization_path).resolve()
    output = Path(output_dir).resolve()
    if registration_file != (root / PurePosixPath(DEFAULT_REGISTRATION_PATH)).resolve():
        raise ExperimentBlocked("execution registration path mismatch")
    if authorization_file != (root / PurePosixPath(DEFAULT_AUTHORIZATION_PATH)).resolve():
        raise ExperimentBlocked("execution authorization path mismatch")
    if output != (root / PurePosixPath(normalized["output_directory"])).resolve():
        raise ExperimentBlocked("execution output path mismatch")
    return [
        normalized["runtime_identity"]["executable"],
        (root / PurePosixPath(PLANNED_SOURCE_FILES[0])).resolve().as_posix(),
        "execute",
        "--repo-root",
        root.as_posix(),
        "--registration",
        registration_file.as_posix(),
        "--authorization",
        authorization_file.as_posix(),
        "--output-dir",
        output.as_posix(),
    ]


def _require_clean_pushed_head(repo_root: Path | str) -> str:
    root = Path(repo_root).resolve()
    head = _git_text(root, "rev-parse", "HEAD")
    if _git_text(root, "rev-parse", "origin/master") != head:
        raise ExperimentBlocked("HEAD is not pushed to origin/master")
    if _git_text(root, "status", "--porcelain", "--untracked-files=no"):
        raise ExperimentBlocked("tracked worktree is not clean")
    return _validate_commit(head, "pushed HEAD")


def _publish_cli_artifact(path: Path | str, value: Mapping[str, Any]) -> Path:
    output = Path(path).resolve()
    _atomic_write_once(output, canonical_json_bytes(dict(value)))
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preimplementation = subparsers.add_parser("preimplementation")
    preimplementation.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    preimplementation.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / DEFAULT_PREIMPLEMENTATION_PATH,
    )
    preimplementation.add_argument(
        "--planning-commit",
        default=PLANNING_COMMIT,
    )
    inventory = subparsers.add_parser("inventory")
    inventory.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    inventory.add_argument("--repository-commit")
    inventory.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / DEFAULT_SEED_INVENTORY_PATH,
    )
    register = subparsers.add_parser("register")
    register.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    register.add_argument("--logical-experiment-id", required=True)
    register.add_argument(
        "--preimplementation",
        type=Path,
        default=REPO_ROOT / DEFAULT_PREIMPLEMENTATION_PATH,
    )
    register.add_argument(
        "--seed-inventory",
        type=Path,
        default=REPO_ROOT / DEFAULT_SEED_INVENTORY_PATH,
    )
    register.add_argument("--native-module", type=Path, required=True)
    register.add_argument(
        "--native-dll-directory", type=Path, action="append", required=True
    )
    register.add_argument("--native-provenance", type=Path, required=True)
    register.add_argument("--communication-mod-config", type=Path, required=True)
    register.add_argument("--production-checkpoints", type=Path, required=True)
    register.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / DEFAULT_REGISTRATION_PATH,
    )
    registration_preflight = subparsers.add_parser("registration-preflight")
    registration_preflight.add_argument(
        "--repo-root", type=Path, default=REPO_ROOT
    )
    registration_preflight.add_argument(
        "--registration",
        type=Path,
        default=REPO_ROOT / DEFAULT_REGISTRATION_PATH,
    )
    registration_preflight.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / DEFAULT_PREFLIGHT_PATH,
    )
    authorize = subparsers.add_parser("authorize")
    authorize.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    authorize.add_argument(
        "--registration",
        type=Path,
        default=REPO_ROOT / DEFAULT_REGISTRATION_PATH,
    )
    authorize.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / DEFAULT_OUTPUT_DIRECTORY,
    )
    authorize.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / DEFAULT_AUTHORIZATION_PATH,
    )
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    preflight.add_argument(
        "--registration",
        type=Path,
        default=REPO_ROOT / DEFAULT_REGISTRATION_PATH,
    )
    preflight.add_argument(
        "--authorization",
        type=Path,
        default=REPO_ROOT / DEFAULT_AUTHORIZATION_PATH,
    )
    preflight.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / DEFAULT_OUTPUT_DIRECTORY,
    )
    preflight.add_argument(
        "--output",
        type=Path,
    )
    execute = subparsers.add_parser("execute")
    execute.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    execute.add_argument(
        "--registration",
        type=Path,
        default=REPO_ROOT / DEFAULT_REGISTRATION_PATH,
    )
    execute.add_argument(
        "--authorization",
        type=Path,
        default=REPO_ROOT / DEFAULT_AUTHORIZATION_PATH,
    )
    execute.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / DEFAULT_OUTPUT_DIRECTORY,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preimplementation":
        record = build_preimplementation_record(
            args.repo_root,
            planning_commit=args.planning_commit,
        )
        validate_preimplementation_record(record, args.repo_root)
        output = publish_preimplementation_record(record, args.output)
        print(output)
        return 0
    if args.command == "inventory":
        commit = args.repository_commit or _require_clean_pushed_head(args.repo_root)
        inventory = build_tracked_seed_exclusion_inventory(
            args.repo_root,
            repository_commit=_validate_commit(commit, "inventory commit"),
        )
        verify_tracked_seed_exclusion_inventory(inventory, args.repo_root)
        print(_publish_cli_artifact(args.output, inventory))
        return 0
    if args.command == "register":
        root = args.repo_root.resolve()
        commit = _require_clean_pushed_head(root)
        preimplementation, preimplementation_binding = _repo_artifact_binding(
            args.preimplementation,
            repo_root=root,
            expected_relative=DEFAULT_PREIMPLEMENTATION_PATH,
            label="preimplementation",
        )
        validate_preimplementation_record(preimplementation, root)
        inventory, inventory_binding = _repo_artifact_binding(
            args.seed_inventory,
            repo_root=root,
            expected_relative=DEFAULT_SEED_INVENTORY_PATH,
            label="seed inventory",
        )
        verify_tracked_seed_exclusion_inventory(inventory, root)
        if inventory["repository_commit"] != commit:
            raise ExperimentBlocked("seed inventory is not bound to the pushed implementation")
        native_provenance = _load_json(
            args.native_provenance.resolve(), "native provenance"
        )
        registration = build_source_only_registration(
            repository_commit=commit,
            logical_experiment_id=args.logical_experiment_id,
            preimplementation_binding=preimplementation_binding,
            seed_inventory=inventory,
            seed_inventory_binding=inventory_binding,
            cohorts=materialize_fresh_cohorts(inventory),
            implementation=build_git_implementation_binding(
                root, repository_commit=commit
            ),
            runtime_identity=current_runtime_identity(),
            native_identity={
                "dll_directories": [
                    path.resolve().as_posix() for path in args.native_dll_directory
                ],
                "module": external_file_binding(args.native_module),
                "provenance": native_provenance,
                "provenance_sha256": hashlib.sha256(
                    canonical_json_bytes(native_provenance)
                ).hexdigest(),
            },
            isolation_identity={
                "communication_mod_config": external_file_binding(
                    args.communication_mod_config
                ),
                "production_checkpoints": snapshot_production_checkpoints(
                    args.production_checkpoints
                ),
            },
        )
        print(_publish_cli_artifact(args.output, registration))
        return 0
    if args.command == "registration-preflight":
        registration, _ = _repo_artifact_binding(
            args.registration,
            repo_root=args.repo_root,
            expected_relative=DEFAULT_REGISTRATION_PATH,
            label="registration",
        )
        report = source_only_registration_preflight(
            args.repo_root, registration
        )
        print(_publish_cli_artifact(args.output, report))
        return 0
    if args.command == "authorize":
        root = args.repo_root.resolve()
        registration_commit = _require_clean_pushed_head(root)
        registration, registration_binding = _repo_artifact_binding(
            args.registration,
            repo_root=root,
            expected_relative=DEFAULT_REGISTRATION_PATH,
            label="registration",
        )
        validate_registration(registration)
        committed = _git_blob_batch(
            root,
            repository_commit=registration_commit,
            paths=(DEFAULT_REGISTRATION_PATH,),
        )[DEFAULT_REGISTRATION_PATH]
        if committed != canonical_json_bytes(registration):
            raise ExperimentBlocked("pushed registration bytes mismatch")
        command = registered_execution_command(
            registration,
            repo_root=root,
            registration_path=args.registration,
            authorization_path=args.output,
            output_dir=args.output_dir,
        )
        authorization = build_execution_authorization(
            registration,
            registration_binding=registration_binding,
            registration_commit=registration_commit,
            command=command,
        )
        print(_publish_cli_artifact(args.output, authorization))
        return 0
    if args.command in {"preflight", "execute"}:
        root = args.repo_root.resolve()
        registration = _load_json(args.registration.resolve(), "registration")
        authorization = _load_json(args.authorization.resolve(), "authorization")
        command = registered_execution_command(
            registration,
            repo_root=root,
            registration_path=args.registration,
            authorization_path=args.authorization,
            output_dir=args.output_dir,
        )
        if args.command == "preflight":
            report = source_only_preflight(
                root,
                registration,
                authorization,
                expected_command=command,
            )
            if args.output is None:
                print(json.dumps(report, allow_nan=False, sort_keys=True))
            else:
                print(_publish_cli_artifact(args.output, report))
            return 0
        result = execute_authorized_experiment(
            repo_root=root,
            registration=registration,
            authorization=authorization,
            expected_command=command,
            output_dir=args.output_dir,
        )
        print(json.dumps(result, allow_nan=False, sort_keys=True))
        return 0
    raise ExperimentBlocked("unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
