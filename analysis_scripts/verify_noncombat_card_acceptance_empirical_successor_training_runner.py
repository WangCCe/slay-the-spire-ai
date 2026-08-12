"""Independent verifier for a terminalized card-acceptance training runner."""

from __future__ import annotations

import argparse
import copy
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import types
from collections.abc import Callable, Mapping, Sequence
from typing import Any


LAUNCH_MANIFEST_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-launch-manifest-v1"
)
RECOVERY_REVIEW_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-r6-"
    "terminalization-recovery-boundary-review-v2"
)
RECOVERY_REVIEW_RELATIVE_PATH = (
    "reports/noncombat_card_acceptance_empirical_successor_20260811_r6_"
    "training_terminalization_recovery_boundary_review.json"
)
RUNNER_COMPOSITE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-command-composite-v1"
)
RUNNER_LAUNCH_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-launch-observation-v1"
)
COMMAND_ENVELOPE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-command-envelope-v1"
)
INITIAL_CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-initial-checkpoint-v1"
)
CHECKPOINT_CHAIN_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-checkpoint-chain-v1"
)
RUNNER_LAUNCH_MARKER_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-launch-marker-v1"
)
RUNNER_AUTHORITY_GUARD_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-authority-guard-v1"
)
TERMINALIZATION_GUARD_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-terminalization-guard-v1"
)
TERMINALIZATION_CLOSURE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-terminalization-closure-v1"
)
CONTROL_ARTIFACT_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-artifact-inventory-v1"
)
STAGE_REQUEST_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-stage-request-v1"
)
STAGE_AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-stage-authorization-v1"
)
DELEGATED_APPROVAL_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-delegated-approval-v1"
)
EXTERNAL_HUMAN_APPROVAL_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-external-human-approval-v1"
)
EXTERNAL_APPROVAL_MESSAGE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-external-approval-message-v1"
)
REVOCATION_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-revocation-observation-v1"
)
EXTERNAL_REVOCATION_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-external-revocation-observation-v1"
)
LEASE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-execution-lease-v1"
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
STANDING_DELEGATION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-standing-delegation-v1"
)
CONFIG_IDENTITY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-config-identity-v1"
)
INVENTORY_REGISTRATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-registration-v1"
)
INVENTORY_REGISTRATION_ID = (
    "noncombat-card-acceptance-empirical-successor-20260811-r6-registration-v1"
)

PUSHED_REF = "origin/master"
TERMINALIZATION_CLOSURE_FILENAME = "terminalization_closure.json"
BASE_VERIFIER_RELATIVE_PATH = (
    "analysis_scripts/verify_noncombat_card_acceptance_empirical_successor.py"
)
RUNNER_RELATIVE_PATH = (
    "analysis_scripts/noncombat_card_acceptance_empirical_successor_training_runner.py"
)
RUNNER_VERIFIER_RELATIVE_PATH = (
    "analysis_scripts/verify_noncombat_card_acceptance_empirical_successor_training_runner.py"
)
ARTIFACT_NAMES = (
    "control_source",
    "registration",
    "registration_producer_source",
    "registration_request",
    "registration_verifier_source",
    "runner_source",
    "runner_verifier_source",
    "runtime_source",
    "training_request",
    "training_request_review",
)
AUTHORITY_NAMES = (
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
EMPIRICAL_OPERATION_NAMES = {
    "communication_mod",
    "environment_construction",
    "evaluation",
    "model_fitting",
    "model_loading",
    "native_loading",
    "ope",
    "runtime_fitting",
    "seed_access",
    "training",
}
EXECUTION_AUTHORITY_NAMES = {
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
}
RESOURCE_NAMES = {
    "max_charged_seconds",
    "max_environment_accesses",
    "max_optimizer_steps",
    "max_pairs",
}
DENIED_OPERATIONS = [
    "communication_mod",
    "gameplay",
    "ope",
    "production_model_loading",
    "promotion",
    "qualification",
]
STAGE_EXCLUSIONS = [
    "causal_claim",
    "communication_mod",
    "formal_rl",
    "gameplay",
    "ope",
    "production_model_loading",
    "promotion",
    "qualification",
]
TRAINING_EXECUTION_AUTHORITY = {
    "checkpoint_publication": True,
    "cohort_materialization": False,
    "environment_construction": True,
    "evaluation": False,
    "evidence_publication": True,
    "experiment_model_loading": True,
    "model_fitting": True,
    "native_loading": True,
    "repository_evidence_read": False,
    "seed_access": True,
    "seed_discovery": False,
    "shadow_optimizer_step": False,
    "training": True,
}
TRAINING_RESOURCES = {
    "max_charged_seconds": 28_800.0,
    "max_environment_accesses": 1_024,
    "max_optimizer_steps": 16,
    "max_pairs": 512,
}
EXPECTED_CONFIGURATION_IDENTITY = {
    "canonical_size_bytes": 2_824,
    "contract_sha256": (
        "69efdcb18fc16e65715ff38f2a4985f49cade47bdfa734e299874031007605a2"
    ),
    "schema_version": CONFIG_IDENTITY_SCHEMA_VERSION,
}
STANDING_DELEGATION_EXCLUSIONS = [
    "bypass-codex-host-or-operating-system-approval",
    "change-request-bound-source-path-cohort-resource-retry-or-authority-terms",
    "destructive-unrelated-repository-or-filesystem-operation",
    "substitute-another-request-digest",
]
STANDING_DELEGATION_REVOCATION = (
    "future-explicit-human-revocation-before-approval-publication-v1"
)
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
STANDING_DELEGATION_SCOPE = {
    "pushed_remote_ref": PUSHED_REF,
    "registration_id_prefix": "noncombat-card-acceptance-empirical-successor-",
    "request_class": STAGE_REQUEST_SCHEMA_VERSION,
}
DELEGATED_APPROVAL_RESOLVER = "codex-agent-under-standing-delegation-v1"
REPOSITORY_ID = "WangCCe/slay-the-spire-ai"
TRUSTED_HOST_NATIVE_IMPORTS = frozenset(
    ("kernel32.dll", "msvcrt.dll", "python310.dll")
)
INVENTORY_ROLE_COUNTS = {"training": 512, "canary": 128, "holdout": 512}
INVENTORY_ROLE_ORDER = ("training", "canary", "holdout")
INVENTORY_REGISTRATION_FIELDS = {
    "approval_sha256",
    "authority",
    "authorization_sha256",
    "cohorts",
    "empirical_operations",
    "inventory_sha256",
    "launch_observation_sha256",
    "output_root",
    "receipt_sha256",
    "registration_id",
    "registration_sha256",
    "request_sha256",
    "role_sha256",
    "schema_version",
    "source_commit",
    "source_inventory_sha256",
}
MANIFEST_FIELDS = {
    "artifacts",
    "commands",
    "denied_operations",
    "downstream_authority",
    "empirical_operations",
    "interpreter",
    "launch_id",
    "manifest_path",
    "manifest_sha256",
    "native_identity",
    "output_root",
    "pushed_ref",
    "registered_source",
    "repository_root",
    "request_contract",
    "resources",
    "rollback_authority",
    "runner_source_commit",
    "schema_version",
    "source_inventory",
    "terminalization_guard",
}
REQUEST_FIELDS = {
    "configuration_identity",
    "downstream_authority",
    "exclusions",
    "execution_authority",
    "output_root",
    "prerequisite_bindings",
    "request_id",
    "request_sha256",
    "resources",
    "schema_version",
    "source_commit",
    "source_inventory_sha256",
    "stage",
}
AUTHORIZATION_FIELDS = {
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
}
COMPOSITE_FIELDS = {
    "command",
    "composite_sha256",
    "downstream_authority",
    "execution_operations",
    "launch_manifest_sha256",
    "output_root",
    "registration_sha256",
    "request_sha256",
    "resources",
    "rollback_authority_sha256",
    "schema_version",
}
ENVELOPE_FIELDS = {
    "approval_sha256",
    "authority_mode",
    "command",
    "composite",
    "downstream_authority",
    "envelope_id",
    "envelope_sha256",
    "runner_launch_observation",
    "schema_version",
    "stage_authorization_sha256",
    "terminalization_binding",
}
LAUNCH_OBSERVATION_FIELDS = {
    "authority_mode",
    "command",
    "composite_binding_text",
    "composite_sha256",
    "control_observation",
    "observation_sha256",
    "schema_version",
}
TERMINALIZATION_BINDING_FIELDS = {
    "closure_guard",
    "failure_paths",
    "lease_sha256",
    "owner",
    "prefix_sha256",
    "run_envelope_sha256",
}

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_TOKEN_RE = re.compile(r"[0-9a-f]{32}")
_IDENTIFIER_RE = re.compile(r"[a-z0-9][a-z0-9._:-]{2,191}")
_RUNTIME_CHECKPOINT_RE = re.compile(r"runtime_checkpoints/chunk_(\d{4})\.json")
_CHAIN_RE = re.compile(r"checkpoint_chains/chunk_(\d{4})\.json")
_CHECKPOINT_MARKER_RE = re.compile(r"checkpoints/chunk_(\d{4})\.json")
_ATTEMPT_RE = re.compile(r"(reopen|continuation)_attempts/[0-9a-f]{64}\.json")
class VerificationError(ValueError):
    """Raised when a runner terminalization bundle cannot be reconstructed."""


def canonical_json_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("ascii")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise VerificationError("value is not canonical JSON") from exc


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise VerificationError(f"{label} digest is invalid")
    return value


def _commit(value: object, label: str) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise VerificationError(f"{label} commit is invalid")
    return value


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationError(f"{label} must be a mapping")
    return copy.deepcopy(dict(value))


def _fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise VerificationError(f"{label} fields mismatch")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise VerificationError(f"non-finite JSON constant: {value}")


def _parse_canonical(payload: bytes, label: str) -> dict[str, Any]:
    if not isinstance(payload, bytes):
        raise VerificationError(f"{label} must be bytes")
    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except VerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} is invalid JSON") from exc
    normalized = _mapping(value, label)
    if payload != canonical_json_bytes(normalized):
        raise VerificationError(f"{label} is not canonical")
    return normalized


def _read_canonical_payload(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"{label} cannot be read") from exc
    return _parse_canonical(payload, label), payload


def _read_canonical(path: Path, label: str) -> dict[str, Any]:
    return _read_canonical_payload(path, label)[0]


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _self_digest(value: Mapping[str, Any], field: str, label: str) -> dict[str, Any]:
    normalized = _mapping(value, label)
    digest = _sha(normalized.get(field), label)
    body = {key: item for key, item in normalized.items() if key != field}
    if digest != _canonical_digest(body):
        raise VerificationError(f"{label} self-digest mismatch")
    return normalized


def _absolute_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise VerificationError(f"{label} is not an absolute canonical path")
    path = Path(value)
    if not path.is_absolute() or path.resolve().as_posix() != value:
        raise VerificationError(f"{label} is not an absolute canonical path")
    return value


def _relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise VerificationError(f"{label} is not a relative canonical path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise VerificationError(f"{label} is not a relative canonical path")
    return value


def _all_false(value: object, label: str) -> dict[str, bool]:
    result = _mapping(value, label)
    if (
        not result
        or any(not isinstance(key, str) or not key for key in result)
        or any(type(item) is not bool for item in result.values())
        or any(result.values())
    ):
        raise VerificationError(f"{label} must remain all false")
    return dict(result)


def _resources(value: object, label: str) -> dict[str, int | float]:
    result = _mapping(value, label)
    if not result:
        raise VerificationError(f"{label} is empty")
    for name, item in result.items():
        if (
            not isinstance(name, str)
            or not name
            or isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
            or item <= 0
        ):
            raise VerificationError(f"{label} is invalid")
    return result


def _binding(value: object, label: str, *, external: bool) -> dict[str, Any]:
    result = _mapping(value, label)
    _fields(result, {"path", "sha256", "size_bytes"}, label)
    size = result["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise VerificationError(f"{label} size is invalid")
    path = (
        _absolute_path(result["path"], f"{label} path")
        if external
        else _relative_path(result["path"], f"{label} path")
    )
    return {"path": path, "sha256": _sha(result["sha256"], label), "size_bytes": size}


def _owner(value: object, label: str) -> dict[str, Any]:
    result = _mapping(value, label)
    _fields(result, {"acquired_monotonic", "child_process_id", "token"}, label)
    acquired = result["acquired_monotonic"]
    process_id = result["child_process_id"]
    if (
        isinstance(acquired, bool)
        or not isinstance(acquired, (int, float))
        or not math.isfinite(float(acquired))
        or acquired < 0
        or isinstance(process_id, bool)
        or not isinstance(process_id, int)
        or process_id <= 0
        or not isinstance(result["token"], str)
        or _TOKEN_RE.fullmatch(result["token"]) is None
    ):
        raise VerificationError(f"{label} is invalid")
    return result


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise VerificationError(f"{label} is invalid")
    return value


def _timestamp(value: object, label: str) -> datetime:
    text = _nonempty_string(value, label)
    normalized = f"{text[:-1]}+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise VerificationError(f"{label} is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise VerificationError(f"{label} lacks a timezone")
    return parsed


def _message_watermark(value: object, label: str) -> dict[str, str]:
    watermark = _mapping(value, label)
    _fields(watermark, {"message_id", "message_timestamp", "task_id"}, label)
    _timestamp(watermark["message_timestamp"], f"{label} timestamp")
    return {
        "message_id": _nonempty_string(watermark["message_id"], f"{label} id"),
        "message_timestamp": watermark["message_timestamp"],
        "task_id": _nonempty_string(watermark["task_id"], f"{label} task"),
    }


def _native_import_name(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.casefold()
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or not value.endswith(".dll")
    ):
        raise VerificationError(f"{label} is invalid")
    return value


def _is_trusted_host_native_import(name: str) -> bool:
    return (
        name in TRUSTED_HOST_NATIVE_IMPORTS
        or name.startswith("api-ms-win-")
        or name.startswith("ext-ms-win-")
    )


def _native_dependency_order(
    *,
    module_path: str,
    dependencies: Sequence[Mapping[str, Any]],
    imports: Sequence[Mapping[str, Any]],
) -> list[str]:
    dependencies_by_name = {
        Path(item["path"]).name.casefold(): item["path"] for item in dependencies
    }
    edges = {item["path"]: item["imports"] for item in imports}
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(path: str) -> None:
        if path in visited:
            return
        if path in visiting:
            raise VerificationError("native dependency graph is cyclic")
        visiting.add(path)
        for name in edges[path]:
            dependency_path = dependencies_by_name.get(name)
            if dependency_path is not None:
                visit(dependency_path)
        visiting.remove(path)
        visited.add(path)
        if path != module_path:
            order.append(path)

    visit(module_path)
    if set(order) != {item["path"] for item in dependencies}:
        raise VerificationError("native dependency load order is incomplete")
    return order


def _validate_native_identity(
    value: object,
    *,
    interpreter_path: Path | str,
) -> dict[str, Any]:
    native = _mapping(value, "native identity")
    _fields(
        native,
        {
            "adapter_api_version",
            "dependency_closure",
            "dll_directories",
            "module",
            "provenance",
            "provenance_sha256",
        },
        "native identity",
    )
    if native["adapter_api_version"] != "sts-lightspeed-noncombat-adapter-v3":
        raise VerificationError("native identity adapter API differs")
    module = _binding(native["module"], "native module", external=True)

    directories_value = native["dll_directories"]
    if not isinstance(directories_value, list) or not directories_value:
        raise VerificationError("native DLL directories differ")
    directories = [
        _absolute_path(path, "native DLL directory") for path in directories_value
    ]
    if directories != sorted(set(directories)):
        raise VerificationError("native DLL directory closure differs")

    closure_value = _mapping(native["dependency_closure"], "native dependency closure")
    _fields(
        closure_value,
        {"dependencies", "imports", "trusted_host_imports"},
        "native dependency closure",
    )
    if not isinstance(closure_value["dependencies"], list):
        raise VerificationError("native dependencies differ")
    dependencies = [
        _binding(item, f"native dependency {index}", external=True)
        for index, item in enumerate(closure_value["dependencies"])
    ]
    dependency_paths = [item["path"] for item in dependencies]
    if dependency_paths != sorted(set(dependency_paths)) or module["path"] in dependency_paths:
        raise VerificationError("native dependency paths differ")
    dependency_names = [Path(path).name.casefold() for path in dependency_paths]
    if len(dependency_names) != len(set(dependency_names)):
        raise VerificationError("native dependency basenames differ")
    dependencies_by_name = dict(zip(dependency_names, dependencies))

    imports_value = closure_value["imports"]
    if not isinstance(imports_value, list):
        raise VerificationError("native dependency graph differs")
    imports: list[dict[str, Any]] = []
    for index, item in enumerate(imports_value):
        row = _mapping(item, f"native imports {index}")
        _fields(row, {"imports", "path"}, f"native imports {index}")
        names_value = row["imports"]
        if not isinstance(names_value, list):
            raise VerificationError("native import names differ")
        names = [
            _native_import_name(name, f"native imports {index} name")
            for name in names_value
        ]
        if names != sorted(set(names)):
            raise VerificationError("native import names differ")
        imports.append(
            {
                "imports": names,
                "path": _absolute_path(row["path"], f"native imports {index} path"),
            }
        )
    expected_paths = sorted([module["path"], *dependency_paths])
    if [item["path"] for item in imports] != expected_paths:
        raise VerificationError("native import graph paths differ")

    host_value = closure_value["trusted_host_imports"]
    if not isinstance(host_value, list):
        raise VerificationError("trusted native host imports differ")
    trusted_host_imports = [
        _native_import_name(name, "trusted native host import") for name in host_value
    ]
    if (
        trusted_host_imports != sorted(set(trusted_host_imports))
        or any(not _is_trusted_host_native_import(name) for name in trusted_host_imports)
    ):
        raise VerificationError("trusted native host imports differ")

    edges = {item["path"]: item["imports"] for item in imports}
    reachable = {module["path"]}
    observed_hosts: set[str] = set()
    pending = [module["path"]]
    while pending:
        source = pending.pop()
        for name in edges[source]:
            dependency = dependencies_by_name.get(name)
            if dependency is not None:
                if dependency["path"] not in reachable:
                    reachable.add(dependency["path"])
                    pending.append(dependency["path"])
            elif _is_trusted_host_native_import(name):
                observed_hosts.add(name)
            else:
                raise VerificationError("native dependency closure has an unresolved import")
    if reachable != set(expected_paths):
        raise VerificationError("native dependency closure is unreachable")
    if sorted(observed_hosts) != trusted_host_imports:
        raise VerificationError("native dependency host imports differ")
    _native_dependency_order(
        module_path=module["path"], dependencies=dependencies, imports=imports
    )

    provenance = _mapping(native["provenance"], "native provenance")
    if not provenance:
        raise VerificationError("native provenance is empty")
    build = _mapping(provenance.get("build"), "native provenance build")
    if (
        build.get("adapter_api_version") != native["adapter_api_version"]
        or provenance.get("module_sha256") != module["sha256"]
        or provenance.get("module_size_bytes") != module["size_bytes"]
        or _sha(native["provenance_sha256"], "native provenance")
        != _canonical_digest(provenance)
    ):
        raise VerificationError("native provenance differs")

    interpreter = Path(interpreter_path).resolve()
    search_directories: list[Path] = []
    for directory in (
        Path(module["path"]).parent,
        *(Path(path).resolve() for path in directories),
        interpreter.parent,
    ):
        if directory not in search_directories:
            search_directories.append(directory)
    if not interpreter.is_file() or any(
        not directory.is_dir() for directory in search_directories
    ):
        raise VerificationError("native dependency resolution path is unavailable")
    try:
        entries = {
            directory: [child.resolve() for child in directory.iterdir() if child.is_file()]
            for directory in search_directories
        }
    except OSError as exc:
        raise VerificationError("native dependency resolution cannot be enumerated") from exc
    for dependency in dependencies:
        name = Path(dependency["path"]).name.casefold()
        matches = sorted(
            {
                child.as_posix()
                for directory in search_directories
                for child in entries[directory]
                if child.name.casefold() == name
            }
        )
        if matches != [dependency["path"]]:
            raise VerificationError("native dependency resolution is shadowed or unavailable")

    return {
        "adapter_api_version": native["adapter_api_version"],
        "dependency_closure": {
            "dependencies": dependencies,
            "imports": imports,
            "trusted_host_imports": trusted_host_imports,
        },
        "dll_directories": directories,
        "module": module,
        "provenance": provenance,
        "provenance_sha256": native["provenance_sha256"],
    }


def _validate_rollback_authority(value: object) -> dict[str, Any]:
    authority = _mapping(value, "rollback authority")
    _fields(
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
    target = _mapping(authority["control_target"], "rollback target")
    _fields(
        target,
        {
            "candidate_enabled",
            "checkpoint",
            "configuration",
            "schema_version",
            "selected_arm",
            "target_sha256",
        },
        "rollback target",
    )
    target["checkpoint"] = _binding(target["checkpoint"], "control checkpoint", external=True)
    target["configuration"] = _binding(
        target["configuration"], "control configuration", external=True
    )
    target_body = {key: item for key, item in target.items() if key != "target_sha256"}
    if (
        target["candidate_enabled"] is not False
        or target["selected_arm"] != "control"
        or _sha(target["target_sha256"], "rollback target")
        != _canonical_digest(target_body)
    ):
        raise VerificationError("rollback target differs")
    isolation = _mapping(authority["production_isolation"], "production isolation")
    _fields(isolation, {"communication_mod_config", "production_checkpoints"}, "production isolation")
    isolation["communication_mod_config"] = _binding(
        isolation["communication_mod_config"], "CommunicationMod config", external=True
    )
    tree = _mapping(isolation["production_checkpoints"], "production checkpoints")
    _fields(tree, {"file_count", "root", "sha256", "size_bytes"}, "production checkpoints")
    _absolute_path(tree["root"], "production checkpoint root")
    _sha(tree["sha256"], "production checkpoints")
    for name in ("file_count", "size_bytes"):
        if isinstance(tree[name], bool) or not isinstance(tree[name], int) or tree[name] < 0:
            raise VerificationError("production checkpoint inventory differs")
    relative = _relative_path(authority["target_relative_path"], "rollback target path")
    body = {
        "candidate_disabled_value": authority["candidate_disabled_value"],
        "control_target": target,
        "production_isolation": isolation,
        "schema_version": authority["schema_version"],
        "target_relative_path": relative,
        "trigger_classes": copy.deepcopy(authority["trigger_classes"]),
    }
    if (
        authority["candidate_disabled_value"] is not False
        or not isinstance(authority["trigger_classes"], list)
        or not authority["trigger_classes"]
        or _sha(authority["rollback_authority_sha256"], "rollback authority")
        != _canonical_digest(body)
    ):
        raise VerificationError("rollback authority differs")
    return {**body, "rollback_authority_sha256": authority["rollback_authority_sha256"]}


def _validate_manifest(value: object, manifest_path: Path) -> dict[str, Any]:
    manifest = _mapping(value, "launch manifest")
    _fields(manifest, MANIFEST_FIELDS, "launch manifest")
    if manifest["schema_version"] != LAUNCH_MANIFEST_SCHEMA_VERSION:
        raise VerificationError("launch manifest schema differs")
    _self_digest(manifest, "manifest_sha256", "launch manifest")
    root = _absolute_path(manifest["repository_root"], "repository root")
    if manifest_path.resolve().as_posix() != _absolute_path(
        manifest["manifest_path"], "manifest path"
    ):
        raise VerificationError("launch manifest path differs")
    try:
        manifest_path.resolve().relative_to(Path(root))
    except ValueError as exc:
        raise VerificationError("launch manifest is outside repository") from exc
    output = _absolute_path(manifest["output_root"], "output root")
    guard = _absolute_path(manifest["terminalization_guard"], "terminalization guard")
    if Path(guard).parent != Path(output).parent or guard == output:
        raise VerificationError("terminalization guard path differs")
    if manifest["pushed_ref"] != PUSHED_REF:
        raise VerificationError("manifest pushed reference differs")
    _commit(manifest["runner_source_commit"], "runner source")

    artifacts = _mapping(manifest["artifacts"], "manifest artifacts")
    _fields(artifacts, set(ARTIFACT_NAMES), "manifest artifacts")
    manifest["artifacts"] = {
        name: _binding(artifacts[name], f"artifact {name}", external=False)
        for name in ARTIFACT_NAMES
    }
    expected_paths = {
        "control_source": (
            "analysis_scripts/noncombat_card_acceptance_empirical_successor_experiment.py"
        ),
        "registration_producer_source": (
            "analysis_scripts/noncombat_card_acceptance_empirical_successor_seed_inventory.py"
        ),
        "registration_verifier_source": BASE_VERIFIER_RELATIVE_PATH,
        "runner_source": RUNNER_RELATIVE_PATH,
        "runner_verifier_source": RUNNER_VERIFIER_RELATIVE_PATH,
        "runtime_source": (
            "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py"
        ),
    }
    if any(manifest["artifacts"][name]["path"] != path for name, path in expected_paths.items()):
        raise VerificationError("manifest source path differs")
    artifact_paths = [item["path"] for item in manifest["artifacts"].values()]
    if len(artifact_paths) != len(set(artifact_paths)):
        raise VerificationError("manifest source paths are duplicated")

    manifest["downstream_authority"] = _all_false(
        manifest["downstream_authority"], "manifest downstream authority"
    )
    if set(manifest["downstream_authority"]) != set(AUTHORITY_NAMES):
        raise VerificationError("manifest downstream authority fields differ")
    manifest["empirical_operations"] = _all_false(
        manifest["empirical_operations"], "manifest empirical operations"
    )
    if set(manifest["empirical_operations"]) != EMPIRICAL_OPERATION_NAMES:
        raise VerificationError("manifest empirical operation fields differ")
    manifest["resources"] = _resources(manifest["resources"], "manifest resources")
    if (
        set(manifest["resources"]) != RESOURCE_NAMES
        or manifest["resources"] != TRAINING_RESOURCES
    ):
        raise VerificationError("manifest resource fields differ")
    contract = _mapping(manifest["request_contract"], "request contract")
    _fields(
        contract,
        {
            "downstream_authority",
            "execution_authority",
            "output_root",
            "registration_sha256",
            "request_sha256",
            "resources",
            "source_commit",
            "source_inventory_sha256",
        },
        "request contract",
    )
    contract["downstream_authority"] = _all_false(
        contract["downstream_authority"], "request downstream authority"
    )
    execution = _mapping(contract["execution_authority"], "request execution authority")
    if (
        set(execution) != EXECUTION_AUTHORITY_NAMES
        or any(type(item) is not bool for item in execution.values())
        or execution != TRAINING_EXECUTION_AUTHORITY
    ):
        raise VerificationError("request execution authority differs")
    contract["execution_authority"] = execution
    contract["resources"] = _resources(contract["resources"], "request resources")
    _absolute_path(contract["output_root"], "request output root")
    _sha(contract["registration_sha256"], "request registration")
    _sha(contract["request_sha256"], "request")
    _commit(contract["source_commit"], "registered source")
    _sha(contract["source_inventory_sha256"], "registered inventory")
    registered = _mapping(manifest["registered_source"], "registered source")
    _fields(registered, {"source_commit", "source_inventory_sha256"}, "registered source")
    _commit(registered["source_commit"], "registered source")
    _sha(registered["source_inventory_sha256"], "registered inventory")
    if (
        contract["output_root"] != output
        or contract["resources"] != manifest["resources"]
        or contract["downstream_authority"] != manifest["downstream_authority"]
        or contract["source_commit"] != registered["source_commit"]
        or contract["source_inventory_sha256"] != registered["source_inventory_sha256"]
        or contract["resources"] != TRAINING_RESOURCES
    ):
        raise VerificationError("launch manifest request binding differs")
    manifest["request_contract"] = contract
    manifest["registered_source"] = registered
    manifest["source_inventory"] = _binding(
        manifest["source_inventory"], "source inventory", external=True
    )
    manifest["rollback_authority"] = _validate_rollback_authority(
        manifest["rollback_authority"]
    )

    manifest["native_identity"] = _validate_native_identity(
        manifest["native_identity"], interpreter_path=manifest["interpreter"]
    )

    denied = manifest["denied_operations"]
    if denied != DENIED_OPERATIONS:
        raise VerificationError("manifest denied operations differ")
    commands = _mapping(manifest["commands"], "manifest commands")
    _fields(commands, {"preflight", "run_training", "terminalize_dead_owner"}, "manifest commands")
    runner_path = (Path(root) / RUNNER_RELATIVE_PATH).resolve().as_posix()
    interpreter = _absolute_path(manifest["interpreter"], "runner interpreter")
    for key, command in (
        ("preflight", "preflight"),
        ("run_training", "run-training"),
        ("terminalize_dead_owner", "terminalize-dead-owner"),
    ):
        value_at_command = commands[key]
        if not isinstance(value_at_command, list) or value_at_command[:4] != [
            interpreter,
            "-I",
            runner_path,
            command,
        ]:
            raise VerificationError(f"{command} command prefix differs")
        flags = ["--manifest"] if command == "preflight" else [
            "--manifest",
            "--envelope",
            "--authorization",
            "--approval",
            "--launch-observation",
        ]
        tail = value_at_command[4:]
        if len(tail) != len(flags) * 2 or tail[::2] != flags or tail[1] != manifest["manifest_path"]:
            raise VerificationError(f"{command} command arguments differ")
        for path in tail[1::2]:
            _absolute_path(path, f"{command} command path")
    return manifest


def _expected_composite(manifest: Mapping[str, Any], command: str) -> dict[str, Any]:
    enabled = sorted(
        name
        for name, allowed in manifest["request_contract"]["execution_authority"].items()
        if allowed
    )
    if command != "terminalize-dead-owner" or "evidence_publication" not in enabled:
        raise VerificationError("terminalization composite is not subordinate")
    body = {
        "command": command,
        "downstream_authority": copy.deepcopy(manifest["downstream_authority"]),
        "execution_operations": ["evidence_publication"],
        "launch_manifest_sha256": manifest["manifest_sha256"],
        "output_root": manifest["output_root"],
        "registration_sha256": manifest["request_contract"]["registration_sha256"],
        "request_sha256": manifest["request_contract"]["request_sha256"],
        "resources": copy.deepcopy(manifest["resources"]),
        "rollback_authority_sha256": manifest["rollback_authority"]["rollback_authority_sha256"],
        "schema_version": RUNNER_COMPOSITE_SCHEMA_VERSION,
    }
    return {**body, "composite_sha256": _canonical_digest(body)}


def _validate_standing_delegation(value: object) -> dict[str, Any]:
    delegation = _self_digest(
        _mapping(value, "standing delegation"),
        "delegation_sha256",
        "standing delegation",
    )
    _fields(
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
    grant = _mapping(delegation["grant"], "standing delegation grant")
    _fields(grant, {"granted_at", "provenance", "verbatim_text"}, "standing delegation grant")
    provenance = _mapping(grant["provenance"], "standing delegation provenance")
    _fields(provenance, {"message_id", "source", "task_id"}, "standing delegation provenance")
    _timestamp(grant["granted_at"], "standing delegation grant timestamp")
    scope = _mapping(delegation["scope"], "standing delegation scope")
    _fields(
        scope,
        {"pushed_remote_ref", "registration_id_prefix", "request_class"},
        "standing delegation scope",
    )
    if (
        delegation["schema_version"] != STANDING_DELEGATION_SCHEMA_VERSION
        or delegation["exclusions"] != STANDING_DELEGATION_EXCLUSIONS
        or delegation["revocation"] != STANDING_DELEGATION_REVOCATION
        or grant != STANDING_DELEGATION_GRANT
        or scope != STANDING_DELEGATION_SCOPE
    ):
        raise VerificationError("standing delegation immutable grant or scope differs")
    return delegation


def _external_bound_request_terms(request: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "configuration_identity": copy.deepcopy(request["configuration_identity"]),
        "downstream_authority": copy.deepcopy(request["downstream_authority"]),
        "execution_authority": copy.deepcopy(request["execution_authority"]),
        "exclusions": copy.deepcopy(request["exclusions"]),
        "output_root": request["output_root"],
        "prerequisite_bindings": copy.deepcopy(request["prerequisite_bindings"]),
        "pushed_remote_ref": PUSHED_REF,
        "repository_id": REPOSITORY_ID,
        "request_class": STAGE_REQUEST_SCHEMA_VERSION,
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "resources": copy.deepcopy(request["resources"]),
        "source_commit": request["source_commit"],
        "source_inventory_sha256": request["source_inventory_sha256"],
        "stage": request["stage"],
    }


def _validate_external_approval(
    value: object,
    request: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    approval = _self_digest(
        _mapping(value, "external-human approval"),
        "approval_sha256",
        "external-human approval",
    )
    _fields(
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
    message = _self_digest(
        _mapping(approval["approval_message"], "external approval message"),
        "approval_message_sha256",
        "external approval message",
    )
    _fields(
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
    provenance = _mapping(message["provenance"], "external approval provenance")
    _fields(provenance, {"message_id", "source", "task_id"}, "external approval provenance")
    for name in ("message_id", "task_id"):
        _nonempty_string(provenance[name], f"external approval provenance {name}")
    approved_at = _timestamp(message["approved_at"], "external approval timestamp")
    published_at = _timestamp(
        approval["request_published_at"], "request publication timestamp"
    )
    text = _nonempty_string(
        message["verbatim_approval_text"], "external approval text"
    )
    if (
        approval["schema_version"] != EXTERNAL_HUMAN_APPROVAL_SCHEMA_VERSION
        or approval["approval_mode"] != "external-human-approval"
        or approval["stage"] != "training"
        or approval["approved_request_sha256"] != request["request_sha256"]
        or message["schema_version"] != EXTERNAL_APPROVAL_MESSAGE_SCHEMA_VERSION
        or provenance["source"] != "external-human-message"
        or approved_at <= published_at
        or text.count(request["request_sha256"]) != 1
        or approval["bound_request_terms"] != _external_bound_request_terms(request)
    ):
        raise VerificationError("external approval bound terms, time, or request digest differ")
    observation = _validate_control_observation(
        approval["approval_observation"],
        mode="external-human-approval",
        request_sha256=request["request_sha256"],
        phase="approval",
        mode_binding=message["approval_message_sha256"],
        authority_time=approved_at,
        authority_task_id=provenance["task_id"],
    )
    return approval, message, observation


def _validate_control_observation(
    value: object,
    *,
    mode: str,
    request_sha256: str,
    phase: str,
    mode_binding: str | None = None,
    authority_time: datetime | None = None,
    authority_task_id: str | None = None,
) -> dict[str, Any]:
    observation = _self_digest(_mapping(value, "control observation"), "observation_sha256", "control observation")
    expected_schema = (
        REVOCATION_OBSERVATION_SCHEMA_VERSION
        if mode == "standing-delegation"
        else EXTERNAL_REVOCATION_OBSERVATION_SCHEMA_VERSION
    )
    mode_binding_field = (
        "delegation_sha256"
        if mode == "standing-delegation"
        else "approval_message_sha256"
    )
    _fields(
        observation,
        {
            "authoritative_state_available",
            "authority_mode",
            "checked_at",
            "latest_human_message_watermark",
            mode_binding_field,
            "observation_sha256",
            "phase",
            "request_sha256",
            "revocation_message_watermark",
            "revocation_observed",
            "schema_version",
            "stage",
        },
        "control observation",
    )
    watermark = _message_watermark(
        observation["latest_human_message_watermark"],
        "latest human message watermark",
    )
    if (
        observation.get("schema_version") != expected_schema
        or observation.get("authority_mode") != mode
        or observation.get("phase") != phase
        or observation.get("request_sha256") != request_sha256
        or observation.get("stage") != "training"
        or observation.get("authoritative_state_available") is not True
        or observation.get("revocation_observed") is not False
        or observation.get("revocation_message_watermark") is not None
        or (mode_binding is not None and observation.get(mode_binding_field) != mode_binding)
    ):
        raise VerificationError("control launch observation authority differs")
    checked_at = _timestamp(observation["checked_at"], "control observation timestamp")
    watermark_time = _timestamp(
        watermark["message_timestamp"], "control observation watermark timestamp"
    )
    if (
        checked_at < watermark_time
        or (authority_time is not None and watermark_time < authority_time)
        or (
            mode == "standing-delegation"
            and authority_time is not None
            and checked_at <= authority_time
        )
        or (
            authority_task_id is not None
            and watermark["task_id"] != authority_task_id
        )
    ):
        raise VerificationError("control launch observation watermark is stale")
    return observation


def _validate_request(manifest: Mapping[str, Any], payload: bytes) -> dict[str, Any]:
    request = _parse_canonical(payload, "training request")
    _fields(request, REQUEST_FIELDS, "training request")
    _self_digest(request, "request_sha256", "training request")
    prerequisites = _mapping(request["prerequisite_bindings"], "request prerequisites")
    _fields(prerequisites, {"registration_sha256"}, "request prerequisites")
    registration_sha256 = _sha(
        prerequisites["registration_sha256"], "request registration"
    )
    request_id = request["request_id"]
    if (
        not isinstance(request_id, str)
        or _IDENTIFIER_RE.fullmatch(request_id) is None
        or not request_id.endswith("-training-request-v1")
        or request["configuration_identity"] != EXPECTED_CONFIGURATION_IDENTITY
        or request["exclusions"] != STAGE_EXCLUSIONS
        or request["downstream_authority"]
        != {name: False for name in AUTHORITY_NAMES}
        or request["execution_authority"] != TRAINING_EXECUTION_AUTHORITY
        or request["resources"] != TRAINING_RESOURCES
    ):
        raise VerificationError("training request exact terms differ")
    _absolute_path(request["output_root"], "training request output root")
    _commit(request["source_commit"], "training request source")
    _sha(request["source_inventory_sha256"], "training request inventory")
    contract = manifest["request_contract"]
    observed = {
        "downstream_authority": _all_false(request["downstream_authority"], "request downstream authority"),
        "execution_authority": _mapping(request["execution_authority"], "request execution authority"),
        "output_root": request["output_root"],
        "registration_sha256": registration_sha256,
        "request_sha256": request["request_sha256"],
        "resources": request["resources"],
        "source_commit": request["source_commit"],
        "source_inventory_sha256": request["source_inventory_sha256"],
    }
    if request["schema_version"] != STAGE_REQUEST_SCHEMA_VERSION or request["stage"] != "training" or observed != contract:
        raise VerificationError("training request differs from launch manifest")
    return request


def _validate_registration_sources(
    manifest: Mapping[str, Any],
    registration_payload: bytes,
    registration_request_payload: bytes,
) -> list[int]:
    registration = _parse_canonical(registration_payload, "inventory registration")
    _fields(
        registration,
        INVENTORY_REGISTRATION_FIELDS,
        "inventory registration",
    )
    _self_digest(
        registration,
        "registration_sha256",
        "inventory registration",
    )
    if (
        registration["schema_version"] != INVENTORY_REGISTRATION_SCHEMA_VERSION
        or registration["registration_id"] != INVENTORY_REGISTRATION_ID
        or registration["registration_sha256"]
        != manifest["request_contract"]["registration_sha256"]
        or registration["source_commit"]
        != manifest["registered_source"]["source_commit"]
        or registration["source_inventory_sha256"]
        != manifest["registered_source"]["source_inventory_sha256"]
    ):
        raise VerificationError("inventory registration contract differs")
    _absolute_path(registration["output_root"], "inventory registration output root")
    for name in (
        "approval_sha256",
        "authorization_sha256",
        "inventory_sha256",
        "launch_observation_sha256",
        "receipt_sha256",
        "request_sha256",
    ):
        _sha(registration[name], f"inventory registration {name}")
    if (
        _all_false(registration["authority"], "inventory registration authority")
        != {name: False for name in AUTHORITY_NAMES}
        or _all_false(
            registration["empirical_operations"],
            "inventory registration empirical operations",
        )
        != {name: False for name in sorted(EMPIRICAL_OPERATION_NAMES)}
    ):
        raise VerificationError("inventory registration authority differs")

    cohorts = _mapping(registration["cohorts"], "inventory registration cohorts")
    _fields(cohorts, set(INVENTORY_ROLE_ORDER), "inventory registration cohorts")
    normalized_cohorts: dict[str, list[int]] = {}
    observed_seeds: set[int] = set()
    for role in INVENTORY_ROLE_ORDER:
        seeds = cohorts[role]
        if (
            not isinstance(seeds, list)
            or len(seeds) != INVENTORY_ROLE_COUNTS[role]
            or seeds != sorted(set(seeds))
            or any(
                isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
                for seed in seeds
            )
            or observed_seeds.intersection(seeds)
        ):
            raise VerificationError(f"inventory registration {role} cohort differs")
        observed_seeds.update(seeds)
        normalized_cohorts[role] = list(seeds)
    role_sha256 = _mapping(
        registration["role_sha256"], "inventory registration role digests"
    )
    expected_role_sha256 = {
        role: _canonical_digest(normalized_cohorts[role])
        for role in INVENTORY_ROLE_ORDER
    }
    if role_sha256 != expected_role_sha256:
        raise VerificationError("inventory registration cohort digest differs")

    registration_request = _parse_canonical(
        registration_request_payload, "registration request"
    )
    input_bindings = _mapping(
        registration_request.get("input_bindings"),
        "registration request input bindings",
    )
    inventory_binding = _mapping(
        input_bindings.get("inventory"), "registration request inventory binding"
    )
    expected_inventory_binding = {
        "content_kind": "canonical_json",
        **copy.deepcopy(manifest["source_inventory"]),
    }
    if inventory_binding != expected_inventory_binding:
        raise VerificationError("registration request inventory binding differs")
    return normalized_cohorts["training"]


def _validate_training_seed_prefix(
    observed_seeds: object,
    training_cohort: object,
) -> list[int]:
    if not isinstance(observed_seeds, list) or not isinstance(training_cohort, list):
        raise VerificationError("checkpoint seed cohort prefix differs")
    if (
        any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in observed_seeds
        )
        or observed_seeds != training_cohort[: len(observed_seeds)]
    ):
        raise VerificationError("checkpoint seeds are not the registered training cohort prefix")
    return list(observed_seeds)


def _validate_authority_documents(
    *,
    manifest: Mapping[str, Any],
    envelope: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval: Mapping[str, Any],
    launch_observation: Mapping[str, Any],
    request: Mapping[str, Any],
) -> None:
    _fields(authorization, AUTHORIZATION_FIELDS, "stage authorization")
    _self_digest(authorization, "authorization_sha256", "stage authorization")
    authorization_id = authorization["authorization_id"]
    if (
        authorization["schema_version"] != STAGE_AUTHORIZATION_SCHEMA_VERSION
        or authorization["stage"] != "training"
        or not isinstance(authorization_id, str)
        or _IDENTIFIER_RE.fullmatch(authorization_id) is None
        or not authorization_id.endswith("-training-authorization-v1")
        or authorization["request_id"] != request["request_id"]
        or authorization["request_sha256"] != request["request_sha256"]
        or authorization["downstream_authority"] != request["downstream_authority"]
        or authorization["execution_authority"] != request["execution_authority"]
        or authorization["request_review_sha256"]
        != manifest["artifacts"]["training_request_review"]["sha256"]
        or authorization["authorization_sha256"] != envelope["stage_authorization_sha256"]
    ):
        raise VerificationError("stage authorization differs")

    approval = _self_digest(approval, "approval_sha256", "stage approval")
    mode = envelope["authority_mode"]
    expected_schema = (
        DELEGATED_APPROVAL_SCHEMA_VERSION
        if mode == "standing-delegation"
        else EXTERNAL_HUMAN_APPROVAL_SCHEMA_VERSION
    )
    expected_approval_fields = (
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
        }
        if mode == "standing-delegation"
        else {
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
        }
    )
    _fields(approval, expected_approval_fields, "stage approval")
    if (
        approval.get("schema_version") != expected_schema
        or approval.get("approval_mode") != mode
        or approval.get("stage") != "training"
        or approval.get("approved_request_sha256") != request["request_sha256"]
        or approval.get("request_review_sha256")
        != manifest["artifacts"]["training_request_review"]["sha256"]
        or approval["approval_sha256"] != envelope["approval_sha256"]
        or approval["approval_sha256"] != authorization["approval_record_sha256"]
    ):
        raise VerificationError("stage approval differs")
    if mode == "standing-delegation":
        delegation = _validate_standing_delegation(approval.get("delegation"))
        grant = delegation["grant"]
        grant_time = _timestamp(grant["granted_at"], "standing delegation grant")
        approval_observation = _validate_control_observation(
            approval.get("approval_observation"),
            mode=mode,
            request_sha256=request["request_sha256"],
            phase="approval",
            mode_binding=delegation["delegation_sha256"],
            authority_time=grant_time,
            authority_task_id=grant["provenance"]["task_id"],
        )
        resolution = _mapping(approval.get("resolution"), "delegated approval resolution")
        _fields(
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
        expected_resolution = {
            "approval_observation_sha256": approval_observation["observation_sha256"],
            "delegation_sha256": delegation["delegation_sha256"],
            "request_review_sha256": approval["request_review_sha256"],
            "request_sha256": request["request_sha256"],
            "resolved_at": approval_observation["checked_at"],
            "resolver": DELEGATED_APPROVAL_RESOLVER,
        }
        if resolution != expected_resolution:
            raise VerificationError("delegated approval resolution differs")
        mode_binding = delegation["delegation_sha256"]
        authority_time = grant_time
        authority_task_id = grant["provenance"]["task_id"]
    else:
        approval, message, approval_observation = _validate_external_approval(
            approval, request
        )
        if message["verbatim_approval_text"].count(
            envelope["composite"]["composite_sha256"]
        ) != 1:
            raise VerificationError("external approval does not bind composite")
        mode_binding = message["approval_message_sha256"]
        authority_time = _timestamp(message["approved_at"], "external approval time")
        authority_task_id = message["provenance"]["task_id"]

    observed_launch = _validate_control_observation(
        launch_observation["control_observation"],
        mode=mode,
        request_sha256=request["request_sha256"],
        phase="launch",
        mode_binding=mode_binding,
        authority_time=authority_time,
        authority_task_id=authority_task_id,
    )
    approval_time = _timestamp(
        approval_observation["checked_at"], "approval observation time"
    )
    launch_time = _timestamp(observed_launch["checked_at"], "launch observation time")
    if launch_time < approval_time:
        raise VerificationError("launch observation predates approval")


def _validate_envelope(manifest: Mapping[str, Any], value: object) -> dict[str, Any]:
    envelope = _mapping(value, "terminalization envelope")
    _fields(envelope, ENVELOPE_FIELDS, "terminalization envelope")
    if envelope["schema_version"] != COMMAND_ENVELOPE_SCHEMA_VERSION or envelope["command"] != "terminalize-dead-owner":
        raise VerificationError("terminalization envelope command differs")
    expected_composite = _expected_composite(manifest, "terminalize-dead-owner")
    composite = _mapping(envelope["composite"], "runner composite")
    _fields(composite, COMPOSITE_FIELDS, "runner composite")
    if composite != expected_composite:
        raise VerificationError("terminalization command composite differs")
    launch = _mapping(envelope["runner_launch_observation"], "runner launch observation")
    _fields(launch, LAUNCH_OBSERVATION_FIELDS, "runner launch observation")
    if (
        launch["schema_version"] != RUNNER_LAUNCH_OBSERVATION_SCHEMA_VERSION
        or launch["command"] != "terminalize-dead-owner"
        or launch["composite_sha256"] != composite["composite_sha256"]
        or launch["authority_mode"] != envelope["authority_mode"]
    ):
        raise VerificationError("runner launch observation differs")
    _self_digest(launch, "observation_sha256", "runner launch observation")
    text = launch["composite_binding_text"]
    if not isinstance(text, str) or text.count(composite["composite_sha256"]) != 1:
        raise VerificationError("runner launch observation composite differs")
    terminal = _mapping(envelope["terminalization_binding"], "terminalization binding")
    _fields(terminal, TERMINALIZATION_BINDING_FIELDS, "terminalization binding")
    terminal["owner"] = _owner(terminal["owner"], "terminalization owner")
    for name in ("lease_sha256", "prefix_sha256", "run_envelope_sha256"):
        _sha(terminal[name], f"terminalization {name}")
    if (
        terminal["closure_guard"] != manifest["terminalization_guard"]
        or terminal["failure_paths"] != ["process_identity_failure"]
        or envelope["downstream_authority"] != manifest["downstream_authority"]
        or envelope["authority_mode"] not in {"standing-delegation", "external-human-approval"}
    ):
        raise VerificationError("terminalization envelope binding differs")
    _self_digest(envelope, "envelope_sha256", "terminalization envelope")
    envelope["terminalization_binding"] = terminal
    return envelope


def _validate_recovery_review(
    value: object,
    *,
    manifest: Mapping[str, Any],
    envelope: Mapping[str, Any],
    envelope_payload: bytes,
    launch_payload: bytes,
) -> dict[str, Any]:
    review = _mapping(value, "terminalization recovery review")
    _fields(
        review,
        {
            "failed_v1_attempt",
            "failure_prefix",
            "recovery_source",
            "recovery_verifier",
            "recovery_v2",
            "review_sha256",
            "reviewed_at",
            "schema_version",
        },
        "terminalization recovery review",
    )
    if review["schema_version"] != RECOVERY_REVIEW_SCHEMA_VERSION:
        raise VerificationError("terminalization recovery review schema differs")
    _self_digest(
        review,
        "review_sha256",
        "terminalization recovery review",
    )
    source = _mapping(review["recovery_source"], "terminalization recovery source")
    _fields(
        source,
        {"runner_path", "runner_sha256", "runner_size_bytes"},
        "terminalization recovery source",
    )
    _sha(source["runner_sha256"], "terminalization recovery runner")
    if (
        source["runner_path"]
        != manifest["artifacts"]["runner_source"]["path"]
        or isinstance(source["runner_size_bytes"], bool)
        or not isinstance(source["runner_size_bytes"], int)
        or source["runner_size_bytes"] <= 0
    ):
        raise VerificationError("terminalization recovery source differs")
    verifier_source = _mapping(
        review["recovery_verifier"], "terminalization recovery verifier"
    )
    _fields(
        verifier_source,
        {"verifier_path", "verifier_sha256", "verifier_size_bytes"},
        "terminalization recovery verifier",
    )
    _sha(verifier_source["verifier_sha256"], "terminalization recovery verifier")
    if (
        verifier_source["verifier_path"]
        != manifest["artifacts"]["runner_verifier_source"]["path"]
        or isinstance(verifier_source["verifier_size_bytes"], bool)
        or not isinstance(verifier_source["verifier_size_bytes"], int)
        or verifier_source["verifier_size_bytes"] <= 0
    ):
        raise VerificationError("terminalization recovery verifier differs")
    recovery = _mapping(review["recovery_v2"], "terminalization recovery v2")
    _fields(
        recovery,
        {
            "command_execution_operations",
            "downstream_authority_all_false",
            "envelope_file_sha256",
            "envelope_id",
            "envelope_sha256",
            "launch_file_sha256",
            "launch_observation_sha256",
            "pushed_source_validation_pending",
            "terminalization_invoked",
        },
        "terminalization recovery v2",
    )
    if (
        recovery["command_execution_operations"] != ["evidence_publication"]
        or recovery["downstream_authority_all_false"] is not True
        or recovery["envelope_id"] != envelope["envelope_id"]
        or recovery["envelope_sha256"] != envelope["envelope_sha256"]
        or recovery["envelope_file_sha256"]
        != hashlib.sha256(envelope_payload).hexdigest()
        or recovery["launch_file_sha256"]
        != hashlib.sha256(launch_payload).hexdigest()
        or recovery["launch_observation_sha256"]
        != envelope["runner_launch_observation"]["observation_sha256"]
        or recovery["pushed_source_validation_pending"] is not True
        or recovery["terminalization_invoked"] is not False
    ):
        raise VerificationError("terminalization recovery v2 differs")
    failed = _mapping(review["failed_v1_attempt"], "failed v1 attempt")
    _fields(
        failed,
        {
            "closure_artifacts_written",
            "envelope_sha256",
            "environment_accesses",
            "error",
            "failure_phase",
            "invoked_once",
            "retry_same_envelope",
        },
        "failed v1 attempt",
    )
    if (
        failed["closure_artifacts_written"] is not False
        or failed["environment_accesses"] != 0
        or failed["failure_phase"] != "pre-start-validation"
        or failed["invoked_once"] is not True
        or failed["retry_same_envelope"] is not False
        or failed["envelope_sha256"] == envelope["envelope_sha256"]
    ):
        raise VerificationError("failed v1 recovery boundary differs")
    prefix = _mapping(review["failure_prefix"], "terminalization recovery prefix")
    binding = envelope["terminalization_binding"]
    if (
        prefix.get("failure_paths") != binding["failure_paths"]
        or prefix.get("lease_sha256") != binding["lease_sha256"]
        or prefix.get("prefix_sha256") != binding["prefix_sha256"]
        or prefix.get("run_envelope_sha256") != binding["run_envelope_sha256"]
        or prefix.get("owner_child_process_id")
        != binding["owner"]["child_process_id"]
    ):
        raise VerificationError("terminalization recovery prefix differs")
    return copy.deepcopy(dict(review))


def _observe_bound_sources(
    manifest: Mapping[str, Any],
    authority_payloads: Mapping[str, bytes],
    source_observer: Callable[
        [Mapping[str, Any], Sequence[str], Mapping[str, Mapping[str, Any]]],
        Mapping[str, Any],
    ],
    recovery_review: Mapping[str, Any] | None = None,
) -> dict[str, bytes]:
    root = Path(manifest["repository_root"])
    payloads: dict[str, bytes] = {}
    repository_payloads = dict(authority_payloads)
    for name in ARTIFACT_NAMES:
        binding = manifest["artifacts"][name]
        path = (root / PurePosixPath(binding["path"])).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise VerificationError(
                f"bound repository artifact escapes repository: {name}"
            ) from exc
        if path.is_symlink():
            raise VerificationError(f"bound repository artifact is a symlink: {name}")
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise VerificationError(f"bound source artifact cannot be read: {name}") from exc
        recovery_binding = None
        recovery_path_field = None
        recovery_size_field = None
        recovery_sha_field = None
        if recovery_review is not None and name == "runner_source":
            recovery_binding = _mapping(
                recovery_review.get("recovery_source"),
                "terminalization recovery source",
            )
            recovery_path_field = "runner_path"
            recovery_size_field = "runner_size_bytes"
            recovery_sha_field = "runner_sha256"
        elif recovery_review is not None and name == "runner_verifier_source":
            recovery_binding = _mapping(
                recovery_review.get("recovery_verifier"),
                "terminalization recovery verifier",
            )
            recovery_path_field = "verifier_path"
            recovery_size_field = "verifier_size_bytes"
            recovery_sha_field = "verifier_sha256"
        if recovery_binding is not None:
            if (
                recovery_binding[recovery_path_field] != binding["path"]
                or recovery_binding[recovery_size_field] != len(payload)
                or recovery_binding[recovery_sha_field]
                != hashlib.sha256(payload).hexdigest()
            ):
                raise VerificationError(f"recovery source artifact differs: {name}")
        elif (
            len(payload) != binding["size_bytes"]
            or hashlib.sha256(payload).hexdigest() != binding["sha256"]
        ):
            raise VerificationError(f"bound source artifact differs: {name}")
        payloads[name] = payload
        absolute = path.as_posix()
        if absolute in repository_payloads and repository_payloads[absolute] != payload:
            raise VerificationError(f"bound repository bytes disagree: {name}")
        repository_payloads[absolute] = payload
    native_bindings = [manifest["native_identity"]["module"], *manifest["native_identity"]["dependency_closure"]["dependencies"]]
    for index, binding in enumerate(native_bindings):
        path = Path(binding["path"])
        if path.is_symlink():
            raise VerificationError(f"bound native source artifact is a symlink: {index}")
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise VerificationError("bound native source artifact cannot be read") from exc
        if len(payload) != binding["size_bytes"] or hashlib.sha256(payload).hexdigest() != binding["sha256"]:
            raise VerificationError(f"bound native source artifact differs: {index}")
    for path in repository_payloads:
        resolved = Path(path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise VerificationError("authority source path escapes repository") from exc
        if resolved.as_posix() != path:
            raise VerificationError("authority source path is not canonical")
    repository_paths = tuple(repository_payloads)
    observed_bindings = {
        path: {
            "path": path,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
        for path, payload in repository_payloads.items()
    }
    try:
        observation = _mapping(
            source_observer(
                manifest,
                repository_paths,
                copy.deepcopy(observed_bindings),
            ),
            "source observation",
        )
    except VerificationError:
        raise
    except Exception as exc:
        raise VerificationError("source observation failed") from exc
    _fields(
        observation,
        {
            "clean",
            "head",
            "head_bindings",
            "pushed",
            "pushed_bindings",
            "runner_ancestor",
            "source_commit_bound",
            "tracked",
        },
        "source observation",
    )
    for field in ("head_bindings", "pushed_bindings"):
        bindings = _mapping(observation[field], f"source observation {field}")
        if set(bindings) != set(observed_bindings):
            raise VerificationError(f"source observation {field} paths differ")
        normalized = {
            path: _binding(item, f"source observation {field} {path}", external=True)
            for path, item in bindings.items()
        }
        if normalized != observed_bindings:
            raise VerificationError(f"source observation {field} bytes differ")
    if (
        observation["clean"] is not True
        or observation["tracked"] is not True
        or observation["runner_ancestor"] is not True
        or observation["source_commit_bound"] is not True
        or _commit(observation["head"], "observed source HEAD")
        != _commit(observation["pushed"], "observed pushed HEAD")
    ):
        raise VerificationError("pushed source boundary differs")
    return payloads


def _default_source_observer(
    manifest: Mapping[str, Any],
    paths: Sequence[str],
    observed_bindings: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    root = Path(manifest["repository_root"])
    try:
        relative_paths = [
            Path(path).resolve().relative_to(root).as_posix() for path in paths
        ]
    except ValueError as exc:
        raise VerificationError(
            "repository source observer received an external path"
        ) from exc

    if len(relative_paths) != len(set(relative_paths)) or set(paths) != set(
        observed_bindings
    ):
        raise VerificationError("repository source binding paths differ")

    def git(*arguments: str) -> subprocess.CompletedProcess[bytes]:
        try:
            completed = subprocess.run(
                ["git", "-C", str(root), *arguments],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except OSError as exc:
            raise VerificationError("repository source observation failed") from exc
        return completed

    def git_text(*arguments: str) -> str:
        completed = git(*arguments)
        if completed.returncode != 0:
            raise VerificationError("repository source observation failed")
        return completed.stdout.decode("ascii", errors="strict").strip()

    def git_blob(reference: str, relative_path: str) -> bytes:
        completed = git("show", f"{reference}:{relative_path}")
        if completed.returncode != 0:
            raise VerificationError("repository source blob is unavailable")
        return completed.stdout

    head = _commit(git_text("rev-parse", "HEAD"), "repository HEAD")
    pushed = _commit(
        git_text("rev-parse", manifest["pushed_ref"]), "repository pushed HEAD"
    )
    head_bindings: dict[str, dict[str, Any]] = {}
    pushed_bindings: dict[str, dict[str, Any]] = {}
    for absolute, relative in zip(paths, relative_paths):
        for reference, target in (
            (head, head_bindings),
            (pushed, pushed_bindings),
        ):
            payload = git_blob(reference, relative)
            target[absolute] = {
                "path": absolute,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
    normalized_observed = {
        path: _binding(item, f"observed repository binding {path}", external=True)
        for path, item in observed_bindings.items()
    }
    if head_bindings != normalized_observed or pushed_bindings != normalized_observed:
        raise VerificationError("repository HEAD or pushed blob bytes differ")
    return {
        "clean": True,
        "head": head,
        "head_bindings": head_bindings,
        "pushed": pushed,
        "pushed_bindings": pushed_bindings,
        "runner_ancestor": git(
            "merge-base", "--is-ancestor", manifest["runner_source_commit"], head
        ).returncode
        == 0,
        "source_commit_bound": git(
            "merge-base",
            "--is-ancestor",
            manifest["registered_source"]["source_commit"],
            head,
        ).returncode
        == 0,
        "tracked": True,
    }


def _load_bound_base_verifier(manifest: Mapping[str, Any], payload: bytes) -> Any:
    binding = manifest["artifacts"]["registration_verifier_source"]
    if binding["path"] != BASE_VERIFIER_RELATIVE_PATH or len(payload) != binding["size_bytes"] or hashlib.sha256(payload).hexdigest() != binding["sha256"]:
        raise VerificationError("base verifier source binding differs")
    path = (Path(manifest["repository_root"]) / BASE_VERIFIER_RELATIVE_PATH).resolve()
    name = f"_bound_card_acceptance_verifier_{binding['sha256'][:16]}"
    module = types.ModuleType(name)
    module.__file__ = path.as_posix()
    module.__package__ = ""
    module.__loader__ = None
    module.__spec__ = None
    try:
        code = compile(
            payload,
            path.as_posix(),
            "exec",
            dont_inherit=True,
        )
        exec(code, module.__dict__)
    except Exception as exc:
        raise VerificationError("bound base verifier bytes cannot be executed") from exc
    for operation in ("verify_terminal_bundle", "verify_rollback_evidence"):
        if not callable(getattr(module, operation, None)):
            raise VerificationError("bound base verifier API differs")
    return module


def _artifact_inventory(value: object, label: str) -> dict[str, Any]:
    inventory = _mapping(value, label)
    _fields(
        inventory,
        {"artifact_count", "artifact_inventory_sha256", "artifacts", "schema_version", "stored_size_bytes", "uncompressed_size_bytes"},
        label,
    )
    rows = inventory["artifacts"]
    if not isinstance(rows, list):
        raise VerificationError(f"{label} rows differ")
    paths: list[str] = []
    stored = 0
    uncompressed = 0
    for row in rows:
        normalized = _mapping(row, f"{label} row")
        _fields(normalized, {"encoding", "path", "stored_sha256", "stored_size_bytes", "uncompressed_sha256", "uncompressed_size_bytes"}, f"{label} row")
        path = _relative_path(normalized["path"], f"{label} path")
        _sha(normalized["stored_sha256"], f"{label} stored")
        _sha(normalized["uncompressed_sha256"], f"{label} uncompressed")
        if normalized["encoding"] not in {"identity-bytes-v1", "deterministic-gzip-v1"}:
            raise VerificationError(f"{label} encoding differs")
        for name in ("stored_size_bytes", "uncompressed_size_bytes"):
            if isinstance(normalized[name], bool) or not isinstance(normalized[name], int) or normalized[name] < 0:
                raise VerificationError(f"{label} size differs")
        paths.append(path)
        stored += normalized["stored_size_bytes"]
        uncompressed += normalized["uncompressed_size_bytes"]
    if paths != sorted(set(paths)) or inventory["artifact_count"] != len(rows) or inventory["stored_size_bytes"] != stored or inventory["uncompressed_size_bytes"] != uncompressed:
        raise VerificationError(f"{label} totals differ")
    body = {
        "artifact_count": len(rows),
        "artifacts": rows,
        "schema_version": CONTROL_ARTIFACT_INVENTORY_SCHEMA_VERSION,
        "stored_size_bytes": stored,
        "uncompressed_size_bytes": uncompressed,
    }
    if inventory["schema_version"] != CONTROL_ARTIFACT_INVENTORY_SCHEMA_VERSION or inventory["artifact_inventory_sha256"] != _canonical_digest(body):
        raise VerificationError(f"{label} digest differs")
    return inventory


def _read_lines(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"{label} cannot be read") from exc
    if not payload or not payload.endswith(b"\n"):
        raise VerificationError(f"{label} is incomplete")
    return [_parse_canonical(line, f"{label} line") for line in payload.splitlines(keepends=True)]


def _validate_guards(manifest: Mapping[str, Any], run_identity: Mapping[str, Any]) -> None:
    guard = _read_canonical(Path(manifest["terminalization_guard"]), "terminalization guard")
    expected_body = {
        "launch_manifest_sha256": manifest["manifest_sha256"],
        "output_root": manifest["output_root"],
        "schema_version": TERMINALIZATION_GUARD_SCHEMA_VERSION,
    }
    if guard != {**expected_body, "guard_sha256": _canonical_digest(expected_body)}:
        raise VerificationError("terminalization guard differs")
    output = Path(manifest["output_root"])
    authority_path = output.parent / f".{output.name}.execution.guard"
    authority_guard = _read_canonical(authority_path, "runner authority guard")
    expected_body = {
        "authority": copy.deepcopy(dict(run_identity)),
        "schema_version": RUNNER_AUTHORITY_GUARD_SCHEMA_VERSION,
    }
    if authority_guard != {**expected_body, "guard_sha256": _canonical_digest(expected_body)}:
        raise VerificationError("runner authority guard differs")


def _validate_path_closure(output: Path, rollback_target: str) -> list[str]:
    required = {
        ".execution.lease",
        "access_journal.jsonl",
        "artifact_manifest.json",
        "resource_ledger.jsonl",
        "rollback.json",
        "runner_launch.json",
        TERMINALIZATION_CLOSURE_FILENAME,
        "terminal.json",
        "terminal_intent.json",
        rollback_target,
    }
    try:
        entries = sorted(output.rglob("*"), key=lambda path: path.relative_to(output).as_posix())
    except OSError as exc:
        raise VerificationError("output artifact closure cannot be listed") from exc
    files: list[str] = []
    for path in entries:
        relative = path.relative_to(output).as_posix()
        lowered = relative.casefold()
        if path.is_symlink():
            raise VerificationError(f"output artifact path is a symlink: {relative}")
        if path.is_dir():
            continue
        files.append(relative)
        if "canary" in lowered:
            raise VerificationError(f"prohibited canary artifact: {relative}")
        if "holdout" in lowered:
            raise VerificationError(f"prohibited holdout artifact: {relative}")
        if "staging" in lowered or (path.name.startswith(".") and path.name.endswith(".tmp")):
            raise VerificationError(f"ambiguous staging artifact: {relative}")
        allowed = (
            relative in required
            or relative in {"bootstrap.json", "checkpoint_chains/initial.json", "stages/training.json", "training_continuation.json"}
            or _RUNTIME_CHECKPOINT_RE.fullmatch(relative) is not None
            or _CHAIN_RE.fullmatch(relative) is not None
            or _CHECKPOINT_MARKER_RE.fullmatch(relative) is not None
            or _ATTEMPT_RE.fullmatch(relative) is not None
        )
        if not allowed:
            raise VerificationError(f"unknown output artifact path: {relative}")
    missing = required - set(files)
    if missing:
        raise VerificationError(f"terminal publication order is incomplete: {sorted(missing)}")
    return files


def _checkpoint_snapshot(payload: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(payload, object_pairs_hook=_reject_duplicate_pairs, parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError("runtime checkpoint is invalid JSON") from exc
    checkpoint = _mapping(parsed, "runtime checkpoint")
    runtime_bytes = json.dumps(checkpoint, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")
    if payload != runtime_bytes:
        raise VerificationError("runtime checkpoint is not canonical")
    _fields(checkpoint, {"bootstrap", "completed_chunk_summaries", "coordinates", "optimizers", "schema_version", "stopped_for_family_saturation"}, "runtime checkpoint")
    bootstrap = _mapping(checkpoint["bootstrap"], "checkpoint bootstrap")
    _fields(bootstrap, {"architecture", "generators", "models", "schema_version"}, "checkpoint bootstrap")
    generators = _mapping(bootstrap["generators"], "checkpoint generators")
    _fields(generators, {"candidate_card", "candidate_noncard", "control_card", "control_noncard"}, "checkpoint generators")
    models = _mapping(bootstrap["models"], "checkpoint models")
    _fields(models, {"candidate", "control"}, "checkpoint models")
    optimizers = _mapping(checkpoint["optimizers"], "checkpoint optimizers")
    _fields(optimizers, {"candidate", "control"}, "checkpoint optimizers")
    coordinates = _mapping(checkpoint["coordinates"], "checkpoint coordinates")
    coordinate_fields = {"candidate_optimizer_updates", "completed_decisions", "completed_pairs", "control_optimizer_updates", "next_chunk_index", "training_environment_accesses", "training_optimizer_steps"}
    _fields(coordinates, coordinate_fields, "checkpoint coordinates")
    index = coordinates["next_chunk_index"]
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index <= 8:
        raise VerificationError("checkpoint index differs")
    expected = {
        "candidate_optimizer_updates": index,
        "completed_pairs": index * 64,
        "control_optimizer_updates": index,
        "training_environment_accesses": index * 128,
        "training_optimizer_steps": index * 2,
    }
    if any(coordinates[name] != value for name, value in expected.items()):
        raise VerificationError("checkpoint coordinates differ")
    summaries = checkpoint["completed_chunk_summaries"]
    if not isinstance(summaries, list) or len(summaries) != index or type(checkpoint["stopped_for_family_saturation"]) is not bool:
        raise VerificationError("checkpoint summaries differ")
    component_sha256 = {
        "candidate_card_generator": _canonical_digest(generators["candidate_card"]),
        "candidate_model": _canonical_digest(models["candidate"]),
        "candidate_noncard_generator": _canonical_digest(generators["candidate_noncard"]),
        "candidate_optimizer": _canonical_digest(optimizers["candidate"]),
        "control_card_generator": _canonical_digest(generators["control_card"]),
        "control_model": _canonical_digest(models["control"]),
        "control_noncard_generator": _canonical_digest(generators["control_noncard"]),
        "control_optimizer": _canonical_digest(optimizers["control"]),
    }
    return {
        "checkpoint_sha256": hashlib.sha256(payload).hexdigest(),
        "component_sha256": component_sha256,
        "coordinates": coordinates,
        "size_bytes": len(payload),
        "stopped_for_family_saturation": checkpoint["stopped_for_family_saturation"],
    }


def _validate_partial_checkpoint_journal(
    events: Sequence[Mapping[str, Any]],
    *,
    completed_seeds: Sequence[int],
    training_cohort: list[int],
) -> list[int]:
    partial = list(events)
    if len(partial) > 128:
        raise VerificationError("complete journal chunk lacks a checkpoint")
    partial_seeds: list[int] = []
    paired_length = len(partial) - (len(partial) % 2)
    for index in range(0, paired_length, 2):
        candidate = partial[index]
        control = partial[index + 1]
        seed = candidate.get("seed")
        if (
            candidate.get("arm") != "candidate"
            or control.get("arm") != "control"
            or control.get("seed") != seed
            or isinstance(seed, bool)
            or not isinstance(seed, int)
            or seed < 0
        ):
            raise VerificationError("partial checkpoint journal pair ordering differs")
        partial_seeds.append(seed)
    if paired_length != len(partial):
        candidate = partial[-1]
        seed = candidate.get("seed")
        if (
            candidate.get("arm") != "candidate"
            or isinstance(seed, bool)
            or not isinstance(seed, int)
            or seed < 0
        ):
            raise VerificationError(
                "partial checkpoint journal has an invalid write-ahead candidate"
            )
        partial_seeds.append(seed)
    _validate_training_seed_prefix(
        [*completed_seeds, *partial_seeds],
        training_cohort,
    )
    return partial_seeds


def _verify_checkpoint_chain(
    output: Path,
    identity: Mapping[str, Any],
    journal_events: Sequence[Mapping[str, Any]],
    resources: Mapping[str, Any],
    expected_markers: object,
    base_verifier: Any,
    training_cohort: list[int],
) -> int:
    runtime_paths = sorted(output.glob("runtime_checkpoints/chunk_*.json"))
    chain_paths = sorted(output.glob("checkpoint_chains/chunk_*.json"))
    marker_paths = sorted(output.glob("checkpoints/chunk_*.json"))
    initial_path = output / "checkpoint_chains" / "initial.json"
    if not runtime_paths and not chain_paths and not marker_paths and not initial_path.exists():
        if (
            resources["environment_accesses"] != 0
            or resources["optimizer_steps"] != 0
            or resources["shadow_optimizer_steps"] != 0
            or expected_markers != []
            or len(journal_events) != 1
        ):
            raise VerificationError(
                "training progress exists before bootstrap checkpoint"
            )
        return 0
    if not runtime_paths:
        raise VerificationError("checkpoint path closure differs")
    runtime_count = len(runtime_paths) - 1
    chain_count = len(chain_paths)
    marker_count = len(marker_paths)
    expected_runtime = [
        f"chunk_{index:04d}.json" for index in range(runtime_count + 1)
    ]
    expected_chains = [
        f"chunk_{index:04d}.json" for index in range(1, chain_count + 1)
    ]
    expected_marker_paths = [
        f"chunk_{index:04d}.json" for index in range(1, marker_count + 1)
    ]
    if (
        [path.name for path in runtime_paths] != expected_runtime
        or [path.name for path in chain_paths] != expected_chains
        or [path.name for path in marker_paths] != expected_marker_paths
        or not 0 <= marker_count <= chain_count <= runtime_count <= marker_count + 1
    ):
        raise VerificationError("checkpoint path closure differs")
    runtime_payloads = [path.read_bytes() for path in runtime_paths]
    snapshots = [_checkpoint_snapshot(payload) for payload in runtime_payloads]
    initial_checkpoint = json.loads(runtime_payloads[0])
    initial_bootstrap_bytes = json.dumps(
        initial_checkpoint["bootstrap"],
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    try:
        for payload in runtime_payloads:
            result = base_verifier.verify_paired_training_checkpoint_bytes(
                payload.rstrip(b"\n"),
                initial_bootstrap_bytes=initial_bootstrap_bytes,
            )
            if result.get("verified") is not True:
                raise VerificationError("base checkpoint verification was incomplete")
    except VerificationError:
        raise
    except Exception as exc:
        raise VerificationError(
            f"bound checkpoint semantics differ: {exc}"
        ) from exc
    if any(
        snapshot["coordinates"]["next_chunk_index"] != position
        for position, snapshot in enumerate(snapshots)
    ):
        raise VerificationError("runtime checkpoint sequence differs")
    if not initial_path.exists():
        if (
            runtime_count != 0
            or chain_count != 0
            or marker_count != 0
            or resources["environment_accesses"] != 0
            or resources["optimizer_steps"] != 0
            or resources["shadow_optimizer_steps"] != 0
            or expected_markers != []
            or len(journal_events) != 1
        ):
            raise VerificationError("bootstrap checkpoint publication prefix differs")
        return 0
    if not initial_path.is_file():
        raise VerificationError("initial checkpoint chain path differs")
    initial = _read_canonical(initial_path, "initial checkpoint chain")
    _fields(initial, {"checkpoint", "initial_checkpoint_sha256", "schema_version"}, "initial checkpoint chain")
    _self_digest(initial, "initial_checkpoint_sha256", "initial checkpoint chain")
    if initial["schema_version"] != INITIAL_CHECKPOINT_SCHEMA_VERSION or initial["checkpoint"] != snapshots[0] or snapshots[0]["coordinates"]["next_chunk_index"] != 0:
        raise VerificationError("initial checkpoint chain differs")
    all_seeds: list[int] = []
    for position, chain_path in enumerate(chain_paths, start=1):
        chain = _read_canonical(chain_path, f"checkpoint chain {position}")
        _fields(chain, {"chain_sha256", "chunk_index", "final", "initial", "schema_version", "seeds"}, "checkpoint chain")
        _self_digest(chain, "chain_sha256", "checkpoint chain")
        seeds = chain["seeds"]
        if (
            chain["schema_version"] != CHECKPOINT_CHAIN_SCHEMA_VERSION
            or chain["chunk_index"] != position - 1
            or chain["initial"] != snapshots[position - 1]
            or chain["final"] != snapshots[position]
            or not isinstance(seeds, list)
            or len(seeds) != 64
            or seeds != sorted(set(seeds))
            or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds)
        ):
            raise VerificationError("checkpoint predecessor chain differs")
        all_seeds.extend(seeds)
    observed_markers: list[dict[str, Any]] = []
    for position, marker_path in enumerate(marker_paths, start=1):
        marker = _read_canonical(marker_path, f"checkpoint marker {position}")
        _fields(marker, {"binding", "identity", "schema_version"}, "checkpoint marker")
        final = snapshots[position]
        expected_binding = {
            "checkpoint_sha256": final["checkpoint_sha256"],
            "completed_pairs": position * 64,
            "component_sha256": final["component_sha256"],
            "next_chunk_index": position,
            "training_environment_accesses": position * 128,
            "training_optimizer_steps": position * 2,
        }
        if marker != {"binding": expected_binding, "identity": identity, "schema_version": TRAINING_CHECKPOINT_BINDING_SCHEMA_VERSION}:
            raise VerificationError("checkpoint control marker differs")
        observed_markers.append(marker)
    _validate_training_seed_prefix(all_seeds, training_cohort)
    optimizer_steps = resources["optimizer_steps"]
    if (
        isinstance(optimizer_steps, bool)
        or not isinstance(optimizer_steps, int)
        or optimizer_steps < 0
        or optimizer_steps % 2
    ):
        raise VerificationError("checkpoint optimizer resource prefix differs")
    durable_count = optimizer_steps // 2
    if (
        durable_count > 8
        or durable_count not in {marker_count, marker_count + 1}
        or runtime_count > durable_count
        or chain_count > durable_count
    ):
        raise VerificationError("checkpoint publication prefix differs")
    durable_seeds = training_cohort[: durable_count * 64]
    if (
        len(durable_seeds) != durable_count * 64
        or all_seeds != durable_seeds[: len(all_seeds)]
    ):
        raise VerificationError("checkpoint training seed prefix differs")
    expected_events = [
        (seed, arm)
        for seed in durable_seeds
        for arm in ("candidate", "control")
    ]
    observed_events = [(event.get("seed"), event.get("arm")) for event in journal_events[1 : 1 + len(expected_events)]]
    tail = list(journal_events[1 + len(expected_events) :])
    if durable_count > marker_count:
        if tail:
            raise VerificationError(
                "unpublished checkpoint has a later journal prefix"
            )
    else:
        _validate_partial_checkpoint_journal(
            tail,
            completed_seeds=durable_seeds,
            training_cohort=training_cohort,
        )
    if (
        observed_events != expected_events
        or resources["environment_accesses"] != len(journal_events) - 1
        or expected_markers != observed_markers
    ):
        raise VerificationError("checkpoint journal/resource prefix mismatch")
    return marker_count


def _validate_rollback_plan(
    value: object, rollback_authority: Mapping[str, Any]
) -> dict[str, Any]:
    plan = _mapping(value, "terminalization rollback plan")
    _fields(
        plan,
        {
            "classification",
            "control_identities_before",
            "control_target_after",
            "control_target_before",
            "production_isolation_before",
            "rollback_authority_sha256",
            "rollback_plan_sha256",
        },
        "terminalization rollback plan",
    )
    _self_digest(plan, "rollback_plan_sha256", "terminalization rollback plan")
    classification = _mapping(plan["classification"], "terminalization classification")
    expected_classification = {
        "closeout_kind": "rollback_failure",
        "failure_paths": ["process_identity_failure"],
        "outcome_class": None,
        "rollback_required": True,
        "trigger_class": "identity",
    }
    expected_control = {
        "checkpoint": rollback_authority["control_target"]["checkpoint"],
        "configuration": rollback_authority["control_target"]["configuration"],
    }
    expected_isolation = rollback_authority["production_isolation"]
    if (
        classification != expected_classification
        or plan["rollback_authority_sha256"]
        != rollback_authority["rollback_authority_sha256"]
        or plan["control_identities_before"]
        != {"matches_registered": True, "observed": expected_control}
        or plan["production_isolation_before"]
        != {"matches_registered": True, "observed": expected_isolation}
    ):
        raise VerificationError("terminalization rollback plan identity differs")
    expected_target_payload = canonical_json_bytes(
        rollback_authority["control_target"]
    )
    expected_after = {
        "path": rollback_authority["target_relative_path"],
        "sha256": hashlib.sha256(expected_target_payload).hexdigest(),
        "size_bytes": len(expected_target_payload),
    }
    if plan["control_target_after"] != expected_after:
        raise VerificationError("terminalization rollback target plan differs")
    if plan["control_target_before"] is not None:
        before = _binding(
            plan["control_target_before"],
            "terminalization rollback target before",
            external=False,
        )
        if before["path"] != rollback_authority["target_relative_path"]:
            raise VerificationError("terminalization rollback target-before path differs")
    return plan


def _verify_closure(
    *,
    manifest: Mapping[str, Any],
    envelope: Mapping[str, Any],
    owner_alive: Callable[[int], bool],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    output = Path(manifest["output_root"])
    binding = envelope["terminalization_binding"]
    closure = _read_canonical(output / TERMINALIZATION_CLOSURE_FILENAME, "terminalization closure")
    _fields(closure, {"closure_sha256", "command", "failure_paths", "failure_prefix", "launch_manifest_sha256", "rollback_plan", "run_envelope_sha256", "schema_version", "terminalization_envelope_sha256"}, "terminalization closure")
    _self_digest(closure, "closure_sha256", "terminalization closure")
    if (
        closure["schema_version"] != TERMINALIZATION_CLOSURE_SCHEMA_VERSION
        or closure["command"] != "terminalize-dead-owner"
        or closure["failure_paths"] != binding["failure_paths"]
        or closure["launch_manifest_sha256"] != manifest["manifest_sha256"]
        or closure["terminalization_envelope_sha256"] != envelope["envelope_sha256"]
        or closure["run_envelope_sha256"] != binding["run_envelope_sha256"]
    ):
        raise VerificationError("terminalization closure identity differs")
    closure["rollback_plan"] = _validate_rollback_plan(
        closure["rollback_plan"], manifest["rollback_authority"]
    )
    prefix = _mapping(closure["failure_prefix"], "terminalization failure prefix")
    _fields(prefix, {"artifact_inventory", "checkpoint_markers", "context_identity", "journal_prefix", "lease_sha256", "owner", "prefix_sha256", "resource_prefix", "runner_authority_identity", "runner_launch"}, "terminalization failure prefix")
    _self_digest(prefix, "prefix_sha256", "terminalization failure prefix")
    prefix["owner"] = _owner(prefix["owner"], "dead runner owner")
    if owner_alive(prefix["owner"]["child_process_id"]) is not False:
        raise VerificationError("dead runner lease owner is still active")
    if prefix["owner"] != binding["owner"] or prefix["lease_sha256"] != binding["lease_sha256"] or prefix["prefix_sha256"] != binding["prefix_sha256"]:
        raise VerificationError("terminalization dead lease binding differs")
    inventory = _artifact_inventory(prefix["artifact_inventory"], "failure prefix inventory")
    forbidden_prefix = {TERMINALIZATION_CLOSURE_FILENAME, "rollback.json", "terminal_intent.json", "terminal.json", "artifact_manifest.json"}
    for row in inventory["artifacts"]:
        if row["path"] in forbidden_prefix:
            raise VerificationError("failure prefix contains terminal evidence")
        path = output.joinpath(*PurePosixPath(row["path"]).parts)
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise VerificationError("failure prefix artifact cannot be read") from exc
        if len(payload) != row["stored_size_bytes"] or hashlib.sha256(payload).hexdigest() != row["stored_sha256"]:
            raise VerificationError("failure prefix artifact binding differs")
    launch = _mapping(prefix["runner_launch"], "runner launch marker")
    _fields(launch, {"command", "launch_manifest_sha256", "launch_sha256", "process_id", "rollback_authority_sha256", "run_envelope_sha256", "schema_version"}, "runner launch marker")
    _self_digest(launch, "launch_sha256", "runner launch marker")
    run_identity = _mapping(prefix["runner_authority_identity"], "runner authority identity")
    _fields(run_identity, {"composite_sha256", "launch_manifest_sha256", "rollback_authority_sha256", "run_envelope_sha256"}, "runner authority identity")
    expected_run = {
        "composite_sha256": _run_composite_sha256(manifest),
        "launch_manifest_sha256": manifest["manifest_sha256"],
        "rollback_authority_sha256": manifest["rollback_authority"]["rollback_authority_sha256"],
        "run_envelope_sha256": binding["run_envelope_sha256"],
    }
    if run_identity != expected_run or launch != _expected_runner_launch(expected_run, prefix["owner"]["child_process_id"]):
        raise VerificationError("original runner launch differs")
    if (output / "runner_launch.json").read_bytes() != canonical_json_bytes(launch):
        raise VerificationError("runner launch bytes differ")

    lease, lease_payload = _read_canonical_payload(
        output / ".execution.lease", "terminal execution lease"
    )
    _fields(lease, {"identity", "owner", "reclaimed_owner", "schema_version"}, "terminal execution lease")
    current_owner = _owner(lease["owner"], "terminal lease owner")
    reclaimed = (
        None
        if lease["reclaimed_owner"] is None
        else _owner(lease["reclaimed_owner"], "reclaimed runner owner")
    )
    if (
        lease["schema_version"] != LEASE_SCHEMA_VERSION
        or lease["identity"] != prefix["context_identity"]
        or hashlib.sha256(lease_payload).hexdigest() != prefix["lease_sha256"]
        or current_owner != prefix["owner"]
        or (reclaimed is not None and reclaimed != prefix["owner"])
        or owner_alive(current_owner["child_process_id"]) is not False
    ):
        raise VerificationError("inactive terminal lease differs")
    journal_events = _read_lines(output / "access_journal.jsonl", "access journal")
    resource_events = _read_lines(output / "resource_ledger.jsonl", "resource ledger")
    return closure, prefix, current_owner, journal_events, resource_events


def _run_composite_sha256(manifest: Mapping[str, Any]) -> str:
    enabled = sorted(name for name, allowed in manifest["request_contract"]["execution_authority"].items() if allowed)
    body = {
        "command": "run-training",
        "downstream_authority": copy.deepcopy(manifest["downstream_authority"]),
        "execution_operations": enabled,
        "launch_manifest_sha256": manifest["manifest_sha256"],
        "output_root": manifest["output_root"],
        "registration_sha256": manifest["request_contract"]["registration_sha256"],
        "request_sha256": manifest["request_contract"]["request_sha256"],
        "resources": copy.deepcopy(manifest["resources"]),
        "rollback_authority_sha256": manifest["rollback_authority"]["rollback_authority_sha256"],
        "schema_version": RUNNER_COMPOSITE_SCHEMA_VERSION,
    }
    return _canonical_digest(body)


def _expected_runner_launch(identity: Mapping[str, Any], process_id: int) -> dict[str, Any]:
    body = {
        "command": "run-training",
        "launch_manifest_sha256": identity["launch_manifest_sha256"],
        "process_id": process_id,
        "rollback_authority_sha256": identity["rollback_authority_sha256"],
        "run_envelope_sha256": identity["run_envelope_sha256"],
        "schema_version": RUNNER_LAUNCH_MARKER_SCHEMA_VERSION,
    }
    return {**body, "launch_sha256": _canonical_digest(body)}


def _verify_terminal_details(output: Path, closure: Mapping[str, Any], prefix: Mapping[str, Any], envelope: Mapping[str, Any]) -> None:
    intent = _read_canonical(output / "terminal_intent.json", "terminal intent")
    if intent.get("downstream_authority") != {name: False for name in AUTHORITY_NAMES}:
        raise VerificationError("terminal downstream authority differs")
    rollback = _read_canonical(output / "rollback.json", "rollback observation")
    plan = closure["rollback_plan"]
    if any(
        rollback.get(name) != plan[name]
        for name in (
            "control_identities_before",
            "control_target_after",
            "control_target_before",
            "production_isolation_before",
        )
    ):
        raise VerificationError("rollback observation differs from closure plan")
    classification = plan["classification"]
    if any(rollback.get(name) != classification[name] for name in classification):
        raise VerificationError("rollback classification differs from closure plan")
    expected_details = {
        "closure_sha256": closure["closure_sha256"],
        "failure_paths": envelope["terminalization_binding"]["failure_paths"],
        "original_lease_sha256": prefix["lease_sha256"],
        "original_owner": prefix["owner"],
        "original_prefix_sha256": prefix["prefix_sha256"],
        "rollback_observation_sha256": rollback["rollback_observation_sha256"],
        "run_envelope_sha256": envelope["terminalization_binding"]["run_envelope_sha256"],
        "terminalization_envelope_sha256": envelope["envelope_sha256"],
    }
    if (
        intent.get("verdict") != "training_process_failure_terminalized"
        or intent.get("details") != expected_details
        or intent.get("journal_prefix") != prefix["journal_prefix"]
        or intent.get("resource_prefix") != prefix["resource_prefix"]
    ):
        raise VerificationError("terminal ordering or closure details differ")
    paths = {row["path"] for row in _artifact_inventory(intent["artifact_prefix"], "terminal intent inventory")["artifacts"]}
    required = {TERMINALIZATION_CLOSURE_FILENAME, "rollback.json", "runner_launch.json"}
    if not required.issubset(paths):
        raise VerificationError("terminal publication ordering differs")


def verify_terminalized_runner_bundle(
    *,
    manifest_path: Path | str,
    envelope_path: Path | str,
    authorization_path: Path | str,
    approval_path: Path | str,
    launch_observation_path: Path | str,
    recovery_review_path: Path | str | None = None,
    source_observer: Callable[
        [Mapping[str, Any], Sequence[str], Mapping[str, Mapping[str, Any]]],
        Mapping[str, Any],
    ]
    | None = None,
    owner_alive: Callable[[int], bool] | None = None,
) -> dict[str, Any]:
    """Reconstruct one exact dead-owner terminalization from immutable bytes."""
    paths = {
        "--manifest": Path(manifest_path).resolve(),
        "--envelope": Path(envelope_path).resolve(),
        "--authorization": Path(authorization_path).resolve(),
        "--approval": Path(approval_path).resolve(),
        "--launch-observation": Path(launch_observation_path).resolve(),
    }
    manifest_document, manifest_payload = _read_canonical_payload(
        paths["--manifest"], "launch manifest"
    )
    manifest = _validate_manifest(manifest_document, paths["--manifest"])
    command = manifest["commands"]["terminalize_dead_owner"]
    expected_paths = dict(zip(command[4::2], command[5::2]))
    if {name: path.as_posix() for name, path in paths.items()} != expected_paths:
        raise VerificationError("terminalization command path closure differs")
    envelope_document, envelope_payload = _read_canonical_payload(
        paths["--envelope"], "terminalization envelope"
    )
    envelope = _validate_envelope(manifest, envelope_document)
    authorization, authorization_payload = _read_canonical_payload(
        paths["--authorization"], "stage authorization"
    )
    approval, approval_payload = _read_canonical_payload(
        paths["--approval"], "stage approval"
    )
    launch, launch_payload = _read_canonical_payload(
        paths["--launch-observation"], "runner launch observation"
    )
    if launch != envelope["runner_launch_observation"]:
        raise VerificationError("standalone launch observation differs from envelope")
    recovery_review = None
    recovery_payload = None
    if recovery_review_path is not None:
        recovery_path = Path(recovery_review_path).resolve()
        expected_recovery_path = (
            Path(manifest["repository_root"]) / RECOVERY_REVIEW_RELATIVE_PATH
        ).resolve()
        if recovery_path != expected_recovery_path:
            raise VerificationError("terminalization recovery review path differs")
        recovery_document, recovery_payload = _read_canonical_payload(
            recovery_path, "terminalization recovery review"
        )
        recovery_review = _validate_recovery_review(
            recovery_document,
            manifest=manifest,
            envelope=envelope,
            envelope_payload=envelope_payload,
            launch_payload=launch_payload,
        )
    authority_payloads = {
        paths["--manifest"].as_posix(): manifest_payload,
        paths["--envelope"].as_posix(): envelope_payload,
        paths["--authorization"].as_posix(): authorization_payload,
        paths["--approval"].as_posix(): approval_payload,
        paths["--launch-observation"].as_posix(): launch_payload,
    }
    if recovery_payload is not None:
        authority_payloads[Path(recovery_review_path).resolve().as_posix()] = (
            recovery_payload
        )
    source_payloads = _observe_bound_sources(
        manifest,
        authority_payloads,
        source_observer or _default_source_observer,
        recovery_review=recovery_review,
    )
    request = _validate_request(manifest, source_payloads["training_request"])
    training_cohort = _validate_registration_sources(
        manifest,
        source_payloads["registration"],
        source_payloads["registration_request"],
    )
    _validate_authority_documents(
        manifest=manifest,
        envelope=envelope,
        authorization=authorization,
        approval=approval,
        launch_observation=launch,
        request=request,
    )

    base = _load_bound_base_verifier(
        manifest, source_payloads["registration_verifier_source"]
    )
    observer = owner_alive or _default_process_alive
    if not callable(observer):
        raise VerificationError("process liveness observer is invalid")
    output = Path(manifest["output_root"])
    if not output.is_dir() or output.is_symlink():
        raise VerificationError("runner output root is invalid")
    _validate_path_closure(
        output, manifest["rollback_authority"]["target_relative_path"]
    )
    closure, prefix, current_owner, journal_events, _resource_events = _verify_closure(
        manifest=manifest,
        envelope=envelope,
        owner_alive=observer,
    )
    _validate_guards(manifest, prefix["runner_authority_identity"])
    try:
        terminal_result = base.verify_terminal_bundle(
            output,
            expected_identity=prefix["context_identity"],
            expected_child_process_id=current_owner["child_process_id"],
            owner_alive=observer,
        )
        rollback_result = base.verify_rollback_evidence(
            output,
            rollback_authority=manifest["rollback_authority"],
            expected_identity=prefix["context_identity"],
        )
    except Exception as exc:
        raise VerificationError(f"journal/resource/terminal/rollback verification failed: {exc}") from exc
    _verify_terminal_details(output, closure, prefix, envelope)
    checkpoint_count = _verify_checkpoint_chain(
        output,
        prefix["context_identity"],
        journal_events,
        terminal_result["resources"],
        prefix["checkpoint_markers"],
        base,
        training_cohort,
    )
    if (
        terminal_result.get("verified") is not True
        or terminal_result.get("verdict") != "training_process_failure_terminalized"
        or rollback_result.get("verified") is not True
        or rollback_result.get("candidate_enabled") is not False
        or terminal_result.get("authority") != {name: False for name in AUTHORITY_NAMES}
    ):
        raise VerificationError("terminalized runner authority or rollback differs")
    result = {
        "authority": {name: False for name in AUTHORITY_NAMES},
        "checkpoint_count": checkpoint_count,
        "closure_sha256": closure["closure_sha256"],
        "command": "terminalize-dead-owner",
        "manifest_sha256": terminal_result["manifest_sha256"],
        "resources": copy.deepcopy(terminal_result["resources"]),
        "rollback_status": rollback_result["status"],
        "terminalization_envelope_sha256": envelope["envelope_sha256"],
        "verdict": terminal_result["verdict"],
        "verified": True,
    }
    if recovery_review is not None:
        result["recovery_review_sha256"] = recovery_review["review_sha256"]
    return result


def _default_process_alive(process_id: int) -> bool:
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0:
        raise VerificationError("process identity is invalid")
    if process_id == os.getpid():
        return True
    if os.name != "nt":
        try:
            os.kill(process_id, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError as exc:
        raise VerificationError("Windows process observer is unavailable") from exc
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    open_process.restype = wintypes.HANDLE
    wait_for_single_object = kernel32.WaitForSingleObject
    wait_for_single_object.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    wait_for_single_object.restype = wintypes.DWORD
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    handle = open_process(0x00100000, False, process_id)
    if not handle:
        error = ctypes.get_last_error()
        if error == 87:
            return False
        return True
    try:
        result = wait_for_single_object(handle, 0)
        if result == 0x00000000:
            return False
        if result == 0x00000102:
            return True
        return True
    finally:
        close_handle(handle)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--envelope", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--launch-observation", type=Path, required=True)
    parser.add_argument("--recovery-review", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = verify_terminalized_runner_bundle(
        manifest_path=args.manifest,
        envelope_path=args.envelope,
        authorization_path=args.authorization,
        approval_path=args.approval,
        launch_observation_path=args.launch_observation,
        recovery_review_path=args.recovery_review,
    )
    print(canonical_json_bytes(result).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
