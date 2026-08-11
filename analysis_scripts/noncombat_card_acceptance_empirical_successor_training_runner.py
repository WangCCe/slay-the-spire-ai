"""Source-bound launcher for the card-acceptance paired training stage."""

from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import copy
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import subprocess
import struct
import sys
import time
import types
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Any


def _bootstrap_direct_script_imports() -> None:
    if __package__:
        return
    repo_root = Path(__file__).resolve().parents[1]
    package_root = repo_root / "analysis_scripts"
    existing_package = sys.modules.get("analysis_scripts")
    if existing_package is None:
        package = types.ModuleType("analysis_scripts")
        package.__file__ = str(package_root / "__init__.py")
        package.__package__ = "analysis_scripts"
        package.__path__ = [str(package_root)]
        package.__spec__ = importlib.util.spec_from_loader(
            "analysis_scripts", loader=None, is_package=True
        )
        sys.modules["analysis_scripts"] = package
    else:
        package_paths = {
            Path(path).resolve() for path in getattr(existing_package, "__path__", ())
        }
        if package_paths != {package_root}:
            raise RuntimeError("analysis_scripts package is not repository-bound")

    repo_root_text = str(repo_root)
    while repo_root_text in sys.path:
        sys.path.remove(repo_root_text)
    sys.path.append(repo_root_text)


if __name__ == "__main__":
    _bootstrap_direct_script_imports()


LAUNCH_MANIFEST_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-launch-manifest-v1"
)
RUNNER_COMPOSITE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-command-composite-v1"
)
RUNNER_LAUNCH_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-launch-observation-v1"
)
_REGISTERED_ADAPTER_PUBLIC_SYMBOLS = (
    "ADAPTER_API_VERSION",
    "SimulatorAdapterError",
    "TARGET_CATEGORIES",
    "canonical_json_bytes",
    "validate_candidates",
    "validate_snapshot",
)
_NATIVE_DLL_DIRECTORY_HANDLES: list[Any] = []
_TRUSTED_HOST_NATIVE_IMPORTS = frozenset(
    ("kernel32.dll", "msvcrt.dll", "python310.dll")
)
_NATIVE_DEPENDENCY_MODULE_HANDLES: list[int] = []
COMMAND_ENVELOPE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-command-envelope-v1"
)
PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-source-preflight-v1"
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
PRE_ACCESS_RECEIPT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-pre-access-receipt-v1"
)
CONTINUATION_ATTEMPT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-continuation-attempt-v1"
)
REOPEN_ATTEMPT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-reopen-attempt-v1"
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
PUSHED_REF = "origin/master"
COMMAND_NAMES = ("preflight", "run-training", "terminalize-dead-owner")
STANDING_COMPOSITE_BINDING_PREFIX = (
    "standing delegation resolves exact request-subordinate runner composite "
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
EXPECTED_SOURCE_ARTIFACT_PATHS = {
    "control_source": (
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_experiment.py"
    ),
    "registration_producer_source": (
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_seed_inventory.py"
    ),
    "registration_verifier_source": (
        "analysis_scripts/verify_noncombat_card_acceptance_empirical_successor.py"
    ),
    "runner_source": (
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_training_runner.py"
    ),
    "runner_verifier_source": (
        "analysis_scripts/verify_noncombat_card_acceptance_empirical_successor_training_runner.py"
    ),
    "runtime_source": (
        "analysis_scripts/noncombat_card_acceptance_empirical_successor_runtime.py"
    ),
}
FORBIDDEN_IMPORT_PREFIXES = (
    "torch",
    "sts_lightspeed_noncombat_adapter",
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime",
    "analysis_scripts.noncombat_simulator_adapter",
)
PREFLIGHT_MAX_BYTES = 4096
AUTHORIZED_DOCUMENT_MAX_BYTES = 1024 * 1024
TERMINALIZATION_CLOSURE_FILENAME = "terminalization_closure.json"

_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_IDENTIFIER_RE = re.compile(r"[a-z0-9][a-z0-9._-]*")
_ARTIFACT_FIELDS = {"path", "sha256", "size_bytes"}
_REGISTERED_SOURCE_FIELDS = {"source_commit", "source_inventory_sha256"}
_REQUEST_CONTRACT_FIELDS = {
    "downstream_authority",
    "execution_authority",
    "output_root",
    "registration_sha256",
    "request_sha256",
    "resources",
    "source_commit",
    "source_inventory_sha256",
}
_MANIFEST_DEFINITION_FIELDS = {
    "artifacts",
    "commands",
    "denied_operations",
    "downstream_authority",
    "empirical_operations",
    "interpreter",
    "launch_id",
    "manifest_path",
    "native_identity",
    "output_root",
    "pushed_ref",
    "repository_root",
    "request_contract",
    "resources",
    "rollback_authority",
    "runner_source_commit",
    "source_inventory",
    "terminalization_guard",
    "registered_source",
}
_MANIFEST_FIELDS = _MANIFEST_DEFINITION_FIELDS | {
    "manifest_sha256",
    "schema_version",
}
_COMPOSITE_FIELDS = {
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
_RUNNER_OBSERVATION_FIELDS = {
    "authority_mode",
    "command",
    "composite_binding_text",
    "composite_sha256",
    "control_observation",
    "observation_sha256",
    "schema_version",
}
_ENVELOPE_FIELDS = {
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
_TERMINALIZATION_BINDING_FIELDS = {
    "closure_guard",
    "failure_paths",
    "lease_sha256",
    "owner",
    "prefix_sha256",
    "run_envelope_sha256",
}


class TrainingRunnerBlocked(ValueError):
    """Raised when the source-bound runner cannot prove an exact boundary."""


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
        raise TrainingRunnerBlocked("value is not canonical JSON") from exc


def canonical_json_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TrainingRunnerBlocked(f"{label} must be a mapping")
    return copy.deepcopy(dict(value))


def _fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise TrainingRunnerBlocked(f"{label} fields mismatch")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TrainingRunnerBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise TrainingRunnerBlocked(f"non-finite JSON constant: {value}")


def _parse_json_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise TrainingRunnerBlocked(f"non-finite JSON number: {value}")
    return result


def _parse_canonical_mapping(payload: bytes, label: str) -> dict[str, Any]:
    if not isinstance(payload, bytes):
        raise TrainingRunnerBlocked(f"{label} must be bytes")
    try:
        decoded = payload.decode("utf-8", errors="strict")
        parsed = json.loads(
            decoded,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
            parse_float=_parse_json_float,
        )
    except TrainingRunnerBlocked:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrainingRunnerBlocked(f"{label} is invalid strict JSON") from exc
    normalized = _mapping(parsed, label)
    if payload != canonical_json_bytes(normalized):
        raise TrainingRunnerBlocked(f"{label} is not canonical")
    return normalized


def _parse_runtime_checkpoint_mapping(payload: bytes) -> dict[str, Any]:
    if not isinstance(payload, bytes) or payload.endswith(b"\n"):
        raise TrainingRunnerBlocked("paired training checkpoint is not canonical")
    return _parse_canonical_mapping(payload + b"\n", "paired training checkpoint")


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise TrainingRunnerBlocked(f"{label} must be a SHA-256 digest")
    return value


def _commit(value: object, label: str) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise TrainingRunnerBlocked(f"{label} must be a commit")
    return value


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER_RE.fullmatch(value) is None:
        raise TrainingRunnerBlocked(f"{label} is invalid")
    return value


def _absolute_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise TrainingRunnerBlocked(f"{label} must be an absolute canonical path")
    path = Path(value)
    if not path.is_absolute() or path.resolve().as_posix() != value:
        raise TrainingRunnerBlocked(f"{label} must be an absolute canonical path")
    return value


def _relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise TrainingRunnerBlocked(f"{label} must be a repository-relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise TrainingRunnerBlocked(f"{label} must be a repository-relative path")
    return value


def _all_boolean_mapping(
    value: object,
    label: str,
    *,
    require_false: bool = False,
) -> dict[str, bool]:
    normalized = _mapping(value, label)
    if (
        not normalized
        or any(not isinstance(key, str) or not key for key in normalized)
        or any(type(item) is not bool for item in normalized.values())
    ):
        raise TrainingRunnerBlocked(f"{label} must contain booleans")
    if require_false and any(normalized.values()):
        raise TrainingRunnerBlocked(f"{label} must remain all false")
    return dict(normalized)


def _resources(value: object) -> dict[str, int | float]:
    normalized = _mapping(value, "runner resources")
    if not normalized:
        raise TrainingRunnerBlocked("runner resources cannot be empty")
    result: dict[str, int | float] = {}
    for name, item in normalized.items():
        if (
            not isinstance(name, str)
            or not name
            or isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
            or item <= 0
        ):
            raise TrainingRunnerBlocked("runner resource is invalid")
        result[name] = item
    return result


def _artifact_binding(value: object, label: str) -> dict[str, Any]:
    binding = _mapping(value, label)
    _fields(binding, _ARTIFACT_FIELDS, label)
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise TrainingRunnerBlocked(f"{label} size is invalid")
    return {
        "path": _relative_path(binding["path"], f"{label} path"),
        "sha256": _digest(binding["sha256"], f"{label} digest"),
        "size_bytes": size,
    }


def _external_binding(value: object, label: str) -> dict[str, Any]:
    binding = _mapping(value, label)
    _fields(binding, _ARTIFACT_FIELDS, label)
    size = binding["size_bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise TrainingRunnerBlocked(f"{label} size is invalid")
    return {
        "path": _absolute_path(binding["path"], f"{label} path"),
        "sha256": _digest(binding["sha256"], f"{label} digest"),
        "size_bytes": size,
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
        raise TrainingRunnerBlocked(f"{label} is invalid")
    return value


def _is_trusted_host_native_import(name: str) -> bool:
    return (
        name in _TRUSTED_HOST_NATIVE_IMPORTS
        or name.startswith("api-ms-win-")
        or name.startswith("ext-ms-win-")
    )


def _native_dependency_order_from_normalized(
    *,
    module_path: str,
    dependencies: Sequence[Mapping[str, Any]],
    imports: Sequence[Mapping[str, Any]],
) -> list[str]:
    dependencies_by_name = {
        Path(item["path"]).name.casefold(): item["path"]
        for item in dependencies
    }
    edges = {item["path"]: item["imports"] for item in imports}
    visiting = set()
    visited = set()
    order = []

    def visit(path: str) -> None:
        if path in visited:
            return
        if path in visiting:
            raise TrainingRunnerBlocked("native dependency graph is cyclic")
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
        raise TrainingRunnerBlocked("native dependency load order is incomplete")
    return order


def _native_dependency_closure(
    value: object,
    *,
    module: Mapping[str, Any],
) -> dict[str, Any]:
    closure = _mapping(value, "native dependency closure")
    _fields(
        closure,
        {"dependencies", "imports", "trusted_host_imports"},
        "native dependency closure",
    )
    dependencies_value = closure["dependencies"]
    imports_value = closure["imports"]
    host_value = closure["trusted_host_imports"]
    if (
        not isinstance(dependencies_value, list)
        or not isinstance(imports_value, list)
        or not isinstance(host_value, list)
    ):
        raise TrainingRunnerBlocked("native dependency closure sections differ")

    dependencies = [
        _external_binding(item, f"native dependency[{index}]")
        for index, item in enumerate(dependencies_value)
    ]
    dependency_paths = [item["path"] for item in dependencies]
    if (
        dependency_paths != sorted(set(dependency_paths))
        or module["path"] in dependency_paths
    ):
        raise TrainingRunnerBlocked("native dependency paths differ")
    dependencies_by_name: dict[str, dict[str, Any]] = {}
    for dependency in dependencies:
        name = Path(dependency["path"]).name.casefold()
        if name in dependencies_by_name:
            raise TrainingRunnerBlocked("native dependency basenames differ")
        dependencies_by_name[name] = dependency

    imports: list[dict[str, Any]] = []
    for index, item in enumerate(imports_value):
        row = _mapping(item, f"native imports[{index}]")
        _fields(row, {"imports", "path"}, f"native imports[{index}]")
        path = _absolute_path(row["path"], f"native imports[{index}] path")
        names_value = row["imports"]
        if not isinstance(names_value, list):
            raise TrainingRunnerBlocked("native import names differ")
        names = [
            _native_import_name(name, f"native imports[{index}] name")
            for name in names_value
        ]
        if names != sorted(set(names)):
            raise TrainingRunnerBlocked("native import names differ")
        imports.append({"imports": names, "path": path})
    import_paths = [item["path"] for item in imports]
    expected_paths = sorted([module["path"], *dependency_paths])
    if import_paths != expected_paths:
        raise TrainingRunnerBlocked("native import graph paths differ")

    trusted_host_imports = [
        _native_import_name(name, "trusted native host import")
        for name in host_value
    ]
    if (
        trusted_host_imports != sorted(set(trusted_host_imports))
        or any(
            not _is_trusted_host_native_import(name)
            for name in trusted_host_imports
        )
    ):
        raise TrainingRunnerBlocked("trusted native host imports differ")

    observed_host_imports = set()
    reachable = {module["path"]}
    edges = {item["path"]: item["imports"] for item in imports}
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
                observed_host_imports.add(name)
            else:
                raise TrainingRunnerBlocked(
                    "native dependency closure has an unresolved import"
                )
    if reachable != set(expected_paths):
        raise TrainingRunnerBlocked("native dependency closure is unreachable")
    if sorted(observed_host_imports) != trusted_host_imports:
        raise TrainingRunnerBlocked("native dependency host imports differ")
    _native_dependency_order_from_normalized(
        module_path=module["path"],
        dependencies=dependencies,
        imports=imports,
    )
    return {
        "dependencies": dependencies,
        "imports": imports,
        "trusted_host_imports": trusted_host_imports,
    }


def _native_identity(value: object) -> dict[str, Any]:
    identity = _mapping(value, "native identity")
    _fields(
        identity,
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
    adapter_api_version = identity["adapter_api_version"]
    if adapter_api_version != "sts-lightspeed-noncombat-adapter-v3":
        raise TrainingRunnerBlocked("native identity adapter API differs")
    directories = identity["dll_directories"]
    if (
        not isinstance(directories, list)
        or not directories
        or any(not isinstance(path, str) for path in directories)
        or directories != sorted(set(directories))
    ):
        raise TrainingRunnerBlocked("native identity DLL directories differ")
    normalized_directories = [
        _absolute_path(path, "native identity DLL directory")
        for path in directories
    ]
    module = _external_binding(identity["module"], "native identity module")
    dependency_closure = _native_dependency_closure(
        identity["dependency_closure"],
        module=module,
    )
    provenance = _mapping(identity["provenance"], "native identity provenance")
    if not provenance:
        raise TrainingRunnerBlocked("native identity provenance is empty")
    build = _mapping(provenance.get("build"), "native identity build")
    if (
        build.get("adapter_api_version") != adapter_api_version
        or provenance.get("module_sha256") != module["sha256"]
        or _digest(
            identity["provenance_sha256"], "native identity provenance digest"
        )
        != canonical_json_sha256(provenance)
    ):
        raise TrainingRunnerBlocked("native identity provenance differs")
    return {
        "adapter_api_version": adapter_api_version,
        "dependency_closure": dependency_closure,
        "dll_directories": normalized_directories,
        "module": module,
        "provenance": copy.deepcopy(provenance),
        "provenance_sha256": canonical_json_sha256(provenance),
    }


def _validate_rollback_authority(value: object) -> dict[str, Any]:
    authority = _mapping(value, "rollback authority")
    try:
        control = importlib.import_module(
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
        )
        normalized = control.validate_rollback_authority(authority)
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("rollback authority validation failed") from exc
    return copy.deepcopy(dict(normalized))


def _request_contract(value: object) -> dict[str, Any]:
    contract = _mapping(value, "request contract")
    _fields(contract, _REQUEST_CONTRACT_FIELDS, "request contract")
    return {
        "downstream_authority": _all_boolean_mapping(
            contract["downstream_authority"],
            "request downstream authority",
            require_false=True,
        ),
        "execution_authority": _all_boolean_mapping(
            contract["execution_authority"],
            "request execution authority",
        ),
        "output_root": _absolute_path(contract["output_root"], "request output root"),
        "registration_sha256": _digest(
            contract["registration_sha256"], "request registration identity"
        ),
        "request_sha256": _digest(contract["request_sha256"], "request identity"),
        "resources": _resources(contract["resources"]),
        "source_commit": _commit(contract["source_commit"], "request source commit"),
        "source_inventory_sha256": _digest(
            contract["source_inventory_sha256"], "request source inventory"
        ),
    }


def _command_path(
    value: object,
    *,
    command: str,
    interpreter: str,
    runner_path: str,
    manifest_path: str,
) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise TrainingRunnerBlocked(f"{command} command is invalid")
    command_value = list(value)
    expected_prefix = [interpreter, "-I", runner_path, command]
    if command_value[:4] != expected_prefix:
        raise TrainingRunnerBlocked(f"{command} command prefix differs")
    expected_flags = ["--manifest"] if command == "preflight" else [
        "--manifest",
        "--envelope",
        "--authorization",
        "--approval",
        "--launch-observation",
    ]
    tail = command_value[4:]
    if len(tail) != len(expected_flags) * 2 or tail[::2] != expected_flags:
        raise TrainingRunnerBlocked(f"{command} command arguments differ")
    if tail[1] != manifest_path:
        raise TrainingRunnerBlocked(f"{command} manifest path differs")
    for path in tail[1::2]:
        _absolute_path(path, f"{command} argument path")
    return command_value


def _normalize_launch_definition(value: object) -> dict[str, Any]:
    definition = _mapping(value, "launch manifest definition")
    _fields(definition, _MANIFEST_DEFINITION_FIELDS, "launch manifest definition")
    if definition["pushed_ref"] != PUSHED_REF:
        raise TrainingRunnerBlocked("pushed reference differs")
    repository_root = _absolute_path(definition["repository_root"], "repository root")
    manifest_path = _absolute_path(definition["manifest_path"], "manifest path")
    try:
        Path(manifest_path).relative_to(Path(repository_root))
    except ValueError as exc:
        raise TrainingRunnerBlocked("launch manifest must be inside repository") from exc
    output_root = _absolute_path(definition["output_root"], "training output root")
    guard = _absolute_path(
        definition["terminalization_guard"], "terminalization guard"
    )
    if Path(guard).parent != Path(output_root).parent or guard == output_root:
        raise TrainingRunnerBlocked("terminalization guard must be an output sibling")
    artifacts_value = _mapping(definition["artifacts"], "launch artifacts")
    _fields(artifacts_value, set(ARTIFACT_NAMES), "launch artifacts")
    artifacts = {
        name: _artifact_binding(artifacts_value[name], f"artifact {name}")
        for name in ARTIFACT_NAMES
    }
    if any(
        artifacts[name]["path"] != path
        for name, path in EXPECTED_SOURCE_ARTIFACT_PATHS.items()
    ):
        raise TrainingRunnerBlocked("launch manifest source path differs")
    artifact_paths = [binding["path"] for binding in artifacts.values()]
    if len(artifact_paths) != len(set(artifact_paths)):
        raise TrainingRunnerBlocked("launch manifest artifact paths are duplicated")
    runner_path = (Path(repository_root) / artifacts["runner_source"]["path"]).resolve().as_posix()
    interpreter = _absolute_path(definition["interpreter"], "runner interpreter")
    commands_value = _mapping(definition["commands"], "runner commands")
    _fields(
        commands_value,
        {"preflight", "run_training", "terminalize_dead_owner"},
        "runner commands",
    )
    commands = {
        "preflight": _command_path(
            commands_value["preflight"],
            command="preflight",
            interpreter=interpreter,
            runner_path=runner_path,
            manifest_path=manifest_path,
        ),
        "run_training": _command_path(
            commands_value["run_training"],
            command="run-training",
            interpreter=interpreter,
            runner_path=runner_path,
            manifest_path=manifest_path,
        ),
        "terminalize_dead_owner": _command_path(
            commands_value["terminalize_dead_owner"],
            command="terminalize-dead-owner",
            interpreter=interpreter,
            runner_path=runner_path,
            manifest_path=manifest_path,
        ),
    }
    registered_source_value = _mapping(
        definition["registered_source"], "registered source"
    )
    _fields(registered_source_value, _REGISTERED_SOURCE_FIELDS, "registered source")
    registered_source = {
        "source_commit": _commit(
            registered_source_value["source_commit"], "registered source commit"
        ),
        "source_inventory_sha256": _digest(
            registered_source_value["source_inventory_sha256"],
            "registered source inventory",
        ),
    }
    request_contract = _request_contract(definition["request_contract"])
    resources = _resources(definition["resources"])
    downstream = _all_boolean_mapping(
        definition["downstream_authority"],
        "manifest downstream authority",
        require_false=True,
    )
    if (
        request_contract["output_root"] != output_root
        or request_contract["resources"] != resources
        or request_contract["downstream_authority"] != downstream
        or request_contract["source_commit"] != registered_source["source_commit"]
        or request_contract["source_inventory_sha256"]
        != registered_source["source_inventory_sha256"]
    ):
        raise TrainingRunnerBlocked("launch manifest request binding differs")
    denied = definition["denied_operations"]
    if (
        not isinstance(denied, list)
        or not denied
        or denied != sorted(set(denied))
        or any(not isinstance(item, str) or not item for item in denied)
    ):
        raise TrainingRunnerBlocked("denied operations must be sorted and unique")
    return {
        "artifacts": artifacts,
        "commands": commands,
        "denied_operations": list(denied),
        "downstream_authority": downstream,
        "empirical_operations": _all_boolean_mapping(
            definition["empirical_operations"],
            "manifest empirical operations",
            require_false=True,
        ),
        "interpreter": interpreter,
        "launch_id": _identifier(definition["launch_id"], "launch id"),
        "manifest_path": manifest_path,
        "native_identity": _native_identity(definition["native_identity"]),
        "output_root": output_root,
        "pushed_ref": PUSHED_REF,
        "repository_root": repository_root,
        "request_contract": request_contract,
        "resources": resources,
        "rollback_authority": _validate_rollback_authority(
            definition["rollback_authority"]
        ),
        "runner_source_commit": _commit(
            definition["runner_source_commit"], "runner source commit"
        ),
        "source_inventory": _external_binding(
            definition["source_inventory"], "source inventory binding"
        ),
        "terminalization_guard": guard,
        "registered_source": registered_source,
    }


def build_launch_manifest(definition: Mapping[str, Any]) -> dict[str, Any]:
    body = {
        **_normalize_launch_definition(definition),
        "schema_version": LAUNCH_MANIFEST_SCHEMA_VERSION,
    }
    return {**body, "manifest_sha256": canonical_json_sha256(body)}


def validate_launch_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    manifest = _mapping(value, "launch manifest")
    _fields(manifest, _MANIFEST_FIELDS, "launch manifest")
    if manifest["schema_version"] != LAUNCH_MANIFEST_SCHEMA_VERSION:
        raise TrainingRunnerBlocked("launch manifest schema differs")
    expected = build_launch_manifest(
        {key: item for key, item in manifest.items() if key not in {"manifest_sha256", "schema_version"}}
    )
    if manifest != expected:
        raise TrainingRunnerBlocked("launch manifest differs from exact definition")
    return manifest


def parse_launch_manifest_bytes(payload: bytes) -> dict[str, Any]:
    return validate_launch_manifest(
        _parse_canonical_mapping(payload, "launch manifest")
    )


def build_runner_composite(
    manifest: Mapping[str, Any], command: str
) -> dict[str, Any]:
    normalized = validate_launch_manifest(manifest)
    if command not in {"run-training", "terminalize-dead-owner"}:
        raise TrainingRunnerBlocked("runner composite command is invalid")
    enabled = sorted(
        name
        for name, allowed in normalized["request_contract"][
            "execution_authority"
        ].items()
        if allowed
    )
    if command == "run-training":
        operations = enabled
    else:
        if "evidence_publication" not in enabled:
            raise TrainingRunnerBlocked(
                "terminalization is not subordinate to evidence publication"
            )
        operations = ["evidence_publication"]
    body = {
        "command": command,
        "downstream_authority": copy.deepcopy(
            normalized["downstream_authority"]
        ),
        "execution_operations": operations,
        "launch_manifest_sha256": normalized["manifest_sha256"],
        "output_root": normalized["output_root"],
        "registration_sha256": normalized["request_contract"][
            "registration_sha256"
        ],
        "request_sha256": normalized["request_contract"]["request_sha256"],
        "resources": copy.deepcopy(normalized["resources"]),
        "rollback_authority_sha256": normalized["rollback_authority"][
            "rollback_authority_sha256"
        ],
        "schema_version": RUNNER_COMPOSITE_SCHEMA_VERSION,
    }
    return {**body, "composite_sha256": canonical_json_sha256(body)}


def _validate_runner_composite(
    value: object, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    composite = _mapping(value, "runner composite")
    _fields(composite, _COMPOSITE_FIELDS, "runner composite")
    if composite["schema_version"] != RUNNER_COMPOSITE_SCHEMA_VERSION:
        raise TrainingRunnerBlocked("runner composite schema differs")
    expected = build_runner_composite(manifest, composite["command"])
    if composite != expected:
        raise TrainingRunnerBlocked("runner composite binding differs")
    return composite


def build_runner_launch_observation(
    composite: Mapping[str, Any],
    command: str,
    control_observation: Mapping[str, Any],
    *,
    authority_mode: str,
    composite_binding_text: str,
) -> dict[str, Any]:
    normalized_composite = _mapping(composite, "runner composite")
    if normalized_composite.get("command") != command:
        raise TrainingRunnerBlocked("runner observation command differs")
    composite_sha256 = _digest(
        normalized_composite.get("composite_sha256"), "runner composite"
    )
    if not isinstance(composite_binding_text, str) or not composite_binding_text:
        raise TrainingRunnerBlocked("runner composite binding text is invalid")
    if authority_mode == "standing-delegation":
        expected_text = STANDING_COMPOSITE_BINDING_PREFIX + composite_sha256
        if composite_binding_text != expected_text:
            raise TrainingRunnerBlocked("standing runner composite binding differs")
    elif authority_mode == "external-human-approval":
        if composite_binding_text.count(composite_sha256) != 1:
            raise TrainingRunnerBlocked(
                "external runner observation must name composite exactly once"
            )
    else:
        raise TrainingRunnerBlocked("runner observation authority mode differs")
    observation = _mapping(control_observation, "control launch observation")
    _digest(observation.get("observation_sha256"), "control launch observation")
    body = {
        "authority_mode": authority_mode,
        "command": command,
        "composite_binding_text": composite_binding_text,
        "composite_sha256": composite_sha256,
        "control_observation": observation,
        "schema_version": RUNNER_LAUNCH_OBSERVATION_SCHEMA_VERSION,
    }
    return {**body, "observation_sha256": canonical_json_sha256(body)}


def _validate_runner_launch_observation(
    value: object, composite: Mapping[str, Any]
) -> dict[str, Any]:
    observation = _mapping(value, "runner launch observation")
    _fields(observation, _RUNNER_OBSERVATION_FIELDS, "runner launch observation")
    if observation["schema_version"] != RUNNER_LAUNCH_OBSERVATION_SCHEMA_VERSION:
        raise TrainingRunnerBlocked("runner launch observation schema differs")
    expected = build_runner_launch_observation(
        composite,
        composite["command"],
        observation["control_observation"],
        authority_mode=observation["authority_mode"],
        composite_binding_text=observation["composite_binding_text"],
    )
    if observation != expected:
        raise TrainingRunnerBlocked("runner launch observation binding differs")
    return observation


def _terminalization_binding(value: object) -> dict[str, Any]:
    binding = _mapping(value, "terminalization binding")
    _fields(binding, _TERMINALIZATION_BINDING_FIELDS, "terminalization binding")
    failure_paths = binding["failure_paths"]
    if (
        not isinstance(failure_paths, list)
        or not failure_paths
        or failure_paths != sorted(set(failure_paths))
        or any(not isinstance(item, str) or not item for item in failure_paths)
    ):
        raise TrainingRunnerBlocked("terminalization failure paths are invalid")
    owner = _validated_lease_owner(binding["owner"], "terminalization owner")
    return {
        "closure_guard": _absolute_path(
            binding["closure_guard"], "terminalization closure guard"
        ),
        "failure_paths": list(failure_paths),
        "lease_sha256": _digest(binding["lease_sha256"], "terminalization lease"),
        "owner": owner,
        "prefix_sha256": _digest(
            binding["prefix_sha256"], "terminalization prefix"
        ),
        "run_envelope_sha256": _digest(
            binding["run_envelope_sha256"], "terminalization run envelope"
        ),
    }


def build_command_envelope(
    *,
    command: str,
    composite: Mapping[str, Any],
    stage_authorization_sha256: str,
    authority_mode: str,
    approval_sha256: str,
    runner_launch_observation: Mapping[str, Any],
    envelope_id: str,
    terminalization_binding: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_composite = _mapping(composite, "runner composite")
    if normalized_composite.get("command") != command:
        raise TrainingRunnerBlocked("command envelope composite differs")
    if authority_mode not in {"standing-delegation", "external-human-approval"}:
        raise TrainingRunnerBlocked("command envelope authority mode differs")
    observation = _validate_runner_launch_observation(
        runner_launch_observation, normalized_composite
    )
    if observation["authority_mode"] != authority_mode:
        raise TrainingRunnerBlocked("command envelope observation mode differs")
    if command == "run-training":
        if terminalization_binding is not None:
            raise TrainingRunnerBlocked("run envelope cannot bind terminalization")
        terminal = None
    elif command == "terminalize-dead-owner":
        if terminalization_binding is None:
            raise TrainingRunnerBlocked("terminalization envelope lacks prefix")
        terminal = _terminalization_binding(terminalization_binding)
    else:
        raise TrainingRunnerBlocked("command envelope command is invalid")
    body = {
        "approval_sha256": _digest(approval_sha256, "command envelope approval"),
        "authority_mode": authority_mode,
        "command": command,
        "composite": normalized_composite,
        "downstream_authority": copy.deepcopy(
            normalized_composite["downstream_authority"]
        ),
        "envelope_id": _identifier(envelope_id, "command envelope id"),
        "runner_launch_observation": observation,
        "schema_version": COMMAND_ENVELOPE_SCHEMA_VERSION,
        "stage_authorization_sha256": _digest(
            stage_authorization_sha256, "stage authorization"
        ),
        "terminalization_binding": terminal,
    }
    return {**body, "envelope_sha256": canonical_json_sha256(body)}


def validate_command_envelope(
    value: Mapping[str, Any], manifest: Mapping[str, Any]
) -> dict[str, Any]:
    envelope = _mapping(value, "command envelope")
    _fields(envelope, _ENVELOPE_FIELDS, "command envelope")
    if envelope["schema_version"] != COMMAND_ENVELOPE_SCHEMA_VERSION:
        raise TrainingRunnerBlocked("command envelope schema differs")
    composite = _validate_runner_composite(envelope["composite"], manifest)
    expected = build_command_envelope(
        command=envelope["command"],
        composite=composite,
        stage_authorization_sha256=envelope["stage_authorization_sha256"],
        authority_mode=envelope["authority_mode"],
        approval_sha256=envelope["approval_sha256"],
        runner_launch_observation=envelope["runner_launch_observation"],
        envelope_id=envelope["envelope_id"],
        terminalization_binding=envelope["terminalization_binding"],
    )
    if envelope != expected:
        raise TrainingRunnerBlocked("command envelope binding differs")
    if (
        envelope["command"] == "terminalize-dead-owner"
        and envelope["terminalization_binding"]["closure_guard"]
        != manifest["terminalization_guard"]
    ):
        raise TrainingRunnerBlocked("terminalization closure guard differs")
    return envelope


def parse_command_envelope_bytes(
    payload: bytes, manifest: Mapping[str, Any]
) -> dict[str, Any]:
    return validate_command_envelope(
        _parse_canonical_mapping(payload, "command envelope"), manifest
    )


def validate_authorized_command_envelope(
    *,
    envelope: Mapping[str, Any],
    manifest: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate existing control authority without broadening its request."""
    normalized_manifest = validate_launch_manifest(manifest)
    normalized_envelope = validate_command_envelope(envelope, normalized_manifest)
    try:
        control = importlib.import_module(
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
        )
        normalized_request = _mapping(
            control.validate_stage_request(request),
            "validated stage request",
        )
        normalized_authorization = _mapping(
            control.validate_stage_authorization(
                authorization, normalized_request
            ),
            "validated stage authorization",
        )
        contract = normalized_manifest["request_contract"]
        observed_contract = {
            "downstream_authority": normalized_request["downstream_authority"],
            "execution_authority": normalized_request["execution_authority"],
            "output_root": normalized_request["output_root"],
            "registration_sha256": normalized_request[
                "prerequisite_bindings"
            ]["registration_sha256"],
            "request_sha256": normalized_request["request_sha256"],
            "resources": normalized_request["resources"],
            "source_commit": normalized_request["source_commit"],
            "source_inventory_sha256": normalized_request[
                "source_inventory_sha256"
            ],
        }
        authorization_sha256 = normalized_authorization[
            "authorization_sha256"
        ]
        authorization_approval_sha256 = normalized_authorization[
            "approval_record_sha256"
        ]
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("stage authority validation failed") from exc
    if observed_contract != contract:
        raise TrainingRunnerBlocked("authorized request differs from runner manifest")
    if (
        authorization_sha256
        != normalized_envelope["stage_authorization_sha256"]
        or authorization_approval_sha256
        != normalized_envelope["approval_sha256"]
    ):
        raise TrainingRunnerBlocked("command envelope stage authority differs")
    runner_observation = normalized_envelope["runner_launch_observation"]
    control_observation = runner_observation["control_observation"]
    try:
        if normalized_envelope["authority_mode"] == "standing-delegation":
            normalized_approval = _mapping(
                control.validate_delegated_approval(
                    approval, normalized_request
                ),
                "validated delegated approval",
            )
            normalized_launch = _mapping(
                control.validate_delegated_stage_launch(
                    request=normalized_request,
                    authorization=normalized_authorization,
                    delegated_approval=normalized_approval,
                    launch_observation=control_observation,
                ),
                "validated delegated launch",
            )
        else:
            normalized_approval = _mapping(
                control.validate_external_human_approval(
                    approval, normalized_request
                ),
                "validated external-human approval",
            )
            approval_text = normalized_approval["approval_message"][
                "verbatim_approval_text"
            ]
            composite_sha256 = normalized_envelope["composite"][
                "composite_sha256"
            ]
            if composite_sha256 not in approval_text:
                raise TrainingRunnerBlocked(
                    "external-human approval does not name runner composite"
                )
            normalized_launch = _mapping(
                control.validate_external_human_stage_launch(
                    request=normalized_request,
                    authorization=normalized_authorization,
                    external_approval=normalized_approval,
                    launch_observation=control_observation,
                ),
                "validated external-human launch",
            )
        approval_sha256 = normalized_approval["approval_sha256"]
        if normalized_launch != control_observation:
            raise TrainingRunnerBlocked("runner launch observation differs")
        if approval_sha256 != normalized_envelope["approval_sha256"]:
            raise TrainingRunnerBlocked("runner approval identity differs")
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("runner command authority validation failed") from exc
    return {
        "authority_mode": normalized_envelope["authority_mode"],
        "command": normalized_envelope["command"],
        "composite_sha256": normalized_envelope["composite"]["composite_sha256"],
        "downstream_authority": copy.deepcopy(
            normalized_envelope["downstream_authority"]
        ),
        "envelope_sha256": normalized_envelope["envelope_sha256"],
        "runner_launch_observation_sha256": runner_observation[
            "observation_sha256"
        ],
        "stage_authorization_sha256": authorization_sha256,
        "validated": True,
    }


def _build_authorized_training_context(
    *,
    control_api: Any,
    launch_manifest: Mapping[str, Any],
    command_envelope: Mapping[str, Any],
    authority: Mapping[str, Any],
    original_registration: Mapping[str, Any],
    execution_registration: Mapping[str, Any],
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval: Mapping[str, Any],
    expected_command: str = "run-training",
    registration_identity_only: bool = False,
) -> Any:
    """Freeze the exact runner authority and rollback-bound registration."""
    required_control_operations = (
        "_build_delegated_execution_context",
        "_build_external_human_execution_context",
        "_context_identity",
        "_require_execution_context",
        "validate_stage_authorization",
        "validate_stage_request",
    )
    try:
        bound_control = importlib.import_module(
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
        )
    except Exception as exc:
        raise TrainingRunnerBlocked("bound training control is unavailable") from exc
    if control_api is not bound_control:
        raise TrainingRunnerBlocked("training context control API is not bound")
    if any(
        not callable(getattr(bound_control, name, None))
        for name in required_control_operations
    ):
        raise TrainingRunnerBlocked("training context control API is incomplete")

    manifest = validate_launch_manifest(launch_manifest)
    envelope = validate_command_envelope(command_envelope, manifest)
    normalized_authority = _mapping(authority, "runner command authority")
    _fields(
        normalized_authority,
        {
            "authority_mode",
            "command",
            "composite_sha256",
            "downstream_authority",
            "envelope_sha256",
            "runner_launch_observation_sha256",
            "stage_authorization_sha256",
            "validated",
        },
        "runner command authority",
    )
    revalidated_authority = validate_authorized_command_envelope(
        envelope=envelope,
        manifest=manifest,
        request=request,
        authorization=authorization,
        approval=approval,
    )
    if (
        normalized_authority != revalidated_authority
        or revalidated_authority["validated"] is not True
        or revalidated_authority["command"] != expected_command
    ):
        raise TrainingRunnerBlocked("training context authority differs")

    registration = _mapping(
        original_registration, "original training registration"
    )
    registration_sha256 = _digest(
        registration.get("registration_sha256"),
        "original training registration identity",
    )
    if registration_identity_only:
        if (
            expected_command != "terminalize-dead-owner"
            or set(registration) != {"registration_sha256"}
        ):
            raise TrainingRunnerBlocked(
                "identity-only registration is not terminalization-bound"
            )
    elif "rollback_authority_sha256" in registration:
        raise TrainingRunnerBlocked(
            "original training registration contains execution authority"
        )
    else:
        registration_body = {
            key: value
            for key, value in registration.items()
            if key != "registration_sha256"
        }
        if registration_sha256 != canonical_json_sha256(registration_body):
            raise TrainingRunnerBlocked("original training registration digest differs")
    rollback_sha256 = manifest["rollback_authority"][
        "rollback_authority_sha256"
    ]
    expected_execution_registration = {
        **copy.deepcopy(registration),
        "rollback_authority_sha256": rollback_sha256,
    }
    observed_execution_registration = _mapping(
        execution_registration, "execution training registration"
    )
    if observed_execution_registration != expected_execution_registration:
        raise TrainingRunnerBlocked("execution training registration differs")

    try:
        supplied_request = _mapping(request, "training context request")
        supplied_authorization = _mapping(
            authorization, "training context authorization"
        )
        normalized_request = _mapping(
            bound_control.validate_stage_request(supplied_request),
            "validated training context request",
        )
        normalized_authorization = _mapping(
            bound_control.validate_stage_authorization(
                supplied_authorization, normalized_request
            ),
            "validated training context authorization",
        )
        if (
            normalized_request != supplied_request
            or normalized_authorization != supplied_authorization
        ):
            raise TrainingRunnerBlocked("training context stage authority changed")
        request_stage = normalized_request["stage"]
        request_sha256 = normalized_request["request_sha256"]
        request_registration_sha256 = normalized_request[
            "prerequisite_bindings"
        ]["registration_sha256"]
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("training context stage authority differs") from exc
    if (
        request_stage != "training"
        or request_sha256 != manifest["request_contract"]["request_sha256"]
        or request_registration_sha256 != registration_sha256
    ):
        raise TrainingRunnerBlocked("training context request differs")

    def validate_exact_execution_registration(
        value: Mapping[str, Any],
    ) -> dict[str, Any]:
        observed = _mapping(value, "context execution registration")
        if observed != expected_execution_registration:
            raise TrainingRunnerBlocked("context execution registration differs")
        return copy.deepcopy(expected_execution_registration)

    runner_observation = envelope["runner_launch_observation"]
    if (
        runner_observation["observation_sha256"]
        != revalidated_authority["runner_launch_observation_sha256"]
    ):
        raise TrainingRunnerBlocked("training context runner observation differs")
    control_observation = runner_observation["control_observation"]
    context_arguments = {
        "registration": copy.deepcopy(expected_execution_registration),
        "request": copy.deepcopy(normalized_request),
        "authorization": copy.deepcopy(normalized_authorization),
        "launch_observation": copy.deepcopy(control_observation),
        "registration_validator": validate_exact_execution_registration,
    }
    try:
        if revalidated_authority["authority_mode"] == "standing-delegation":
            context = bound_control._build_delegated_execution_context(
                **context_arguments,
                delegated_approval=copy.deepcopy(dict(approval)),
            )
        else:
            context = bound_control._build_external_human_execution_context(
                **context_arguments,
                external_approval=copy.deepcopy(dict(approval)),
            )
        if bound_control._require_execution_context(context) is not context:
            raise TrainingRunnerBlocked("authorized training context type differs")
        context_identity = _mapping(
            bound_control._context_identity(context),
            "authorized training context identity",
        )
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked(
            "authorized training context construction failed"
        ) from exc
    expected_context_identity = {
        "authorization_sha256": normalized_authorization[
            "authorization_sha256"
        ],
        "launch_authority_sha256": control_observation["observation_sha256"],
        "registration_sha256": registration_sha256,
        "request_sha256": normalized_request["request_sha256"],
        "stage": "training",
    }
    if (
        getattr(context, "registration", None)
        != expected_execution_registration
        or getattr(context, "request", None) != normalized_request
        or getattr(context, "authorization", None) != normalized_authorization
        or getattr(context, "authority_observation", None)
        != control_observation
        or getattr(context, "stage", None) != "training"
        or context_identity != expected_context_identity
    ):
        raise TrainingRunnerBlocked("authorized training context differs")
    return context


def _checkpoint_snapshot(payload: bytes) -> dict[str, Any]:
    checkpoint = _parse_runtime_checkpoint_mapping(payload)
    _fields(
        checkpoint,
        {
            "bootstrap",
            "completed_chunk_summaries",
            "coordinates",
            "optimizers",
            "schema_version",
            "stopped_for_family_saturation",
        },
        "paired training checkpoint",
    )
    bootstrap = _mapping(checkpoint["bootstrap"], "checkpoint bootstrap")
    _fields(
        bootstrap,
        {"architecture", "generators", "models", "schema_version"},
        "checkpoint bootstrap",
    )
    models = _mapping(bootstrap["models"], "checkpoint models")
    _fields(models, {"candidate", "control"}, "checkpoint models")
    generators = _mapping(bootstrap["generators"], "checkpoint generators")
    _fields(
        generators,
        {
            "candidate_card",
            "candidate_noncard",
            "control_card",
            "control_noncard",
        },
        "checkpoint generators",
    )
    optimizers = _mapping(checkpoint["optimizers"], "checkpoint optimizers")
    _fields(optimizers, {"candidate", "control"}, "checkpoint optimizers")
    coordinates = _mapping(checkpoint["coordinates"], "checkpoint coordinates")
    coordinate_names = {
        "candidate_optimizer_updates",
        "completed_decisions",
        "completed_pairs",
        "control_optimizer_updates",
        "next_chunk_index",
        "training_environment_accesses",
        "training_optimizer_steps",
    }
    _fields(coordinates, coordinate_names, "checkpoint coordinates")
    normalized_coordinates: dict[str, int] = {}
    for name in coordinate_names:
        value = coordinates[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise TrainingRunnerBlocked("checkpoint coordinate is invalid")
        normalized_coordinates[name] = value
    index = normalized_coordinates["next_chunk_index"]
    if index > 8 or any(
        (
            normalized_coordinates["completed_pairs"] != index * 64,
            normalized_coordinates["training_environment_accesses"] != index * 128,
            normalized_coordinates["candidate_optimizer_updates"] != index,
            normalized_coordinates["control_optimizer_updates"] != index,
            normalized_coordinates["training_optimizer_steps"] != index * 2,
        )
    ):
        raise TrainingRunnerBlocked("checkpoint coordinate boundary differs")
    summaries = checkpoint["completed_chunk_summaries"]
    if not isinstance(summaries, list) or len(summaries) != index:
        raise TrainingRunnerBlocked("checkpoint chunk summaries differ")
    if type(checkpoint["stopped_for_family_saturation"]) is not bool:
        raise TrainingRunnerBlocked("checkpoint saturation flag is invalid")
    component_sha256 = {
        "candidate_card_generator": canonical_json_sha256(
            generators["candidate_card"]
        ),
        "candidate_model": canonical_json_sha256(models["candidate"]),
        "candidate_noncard_generator": canonical_json_sha256(
            generators["candidate_noncard"]
        ),
        "candidate_optimizer": canonical_json_sha256(optimizers["candidate"]),
        "control_card_generator": canonical_json_sha256(generators["control_card"]),
        "control_model": canonical_json_sha256(models["control"]),
        "control_noncard_generator": canonical_json_sha256(
            generators["control_noncard"]
        ),
        "control_optimizer": canonical_json_sha256(optimizers["control"]),
    }
    return {
        "checkpoint_sha256": hashlib.sha256(payload).hexdigest(),
        "component_sha256": component_sha256,
        "coordinates": normalized_coordinates,
        "size_bytes": len(payload),
        "stopped_for_family_saturation": checkpoint[
            "stopped_for_family_saturation"
        ],
    }


def _open_registered_training_inputs(
    *,
    authority_validator: Callable[[], Mapping[str, Any]],
    expected_envelope_sha256: str,
    expected_composite_sha256: str,
    launch_manifest: Mapping[str, Any],
    output_root: Path | str,
    process_id: int,
    pre_access_receipt_publisher: Callable[[Path, bytes], Mapping[str, Any]],
    registration_reader: Callable[[], bytes],
    registration_binding: Mapping[str, Any],
    inventory_reader: Callable[[], bytes],
    inventory_binding: Mapping[str, Any],
    inventory_parser: Callable[[bytes], Mapping[str, Any]],
    producer_validator: Callable[
        [Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]
    ],
    independent_verifier: Callable[
        [Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]
    ],
    rollback_authority_sha256: str,
    pre_input_validator: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Open the registered cohort only after one complete command authority check."""
    callbacks = (
        authority_validator,
        pre_access_receipt_publisher,
        registration_reader,
        inventory_reader,
        inventory_parser,
        producer_validator,
        independent_verifier,
    )
    if not all(callable(callback) for callback in callbacks):
        raise TrainingRunnerBlocked("registered input callback is invalid")
    if pre_input_validator is not None and not callable(pre_input_validator):
        raise TrainingRunnerBlocked("registered input pre-input validator is invalid")
    authority = _mapping(authority_validator(), "runner command authority")
    expected_envelope = _digest(expected_envelope_sha256, "expected run envelope")
    expected_composite = _digest(expected_composite_sha256, "expected runner composite")
    manifest = validate_launch_manifest(launch_manifest)
    manifest_digest = manifest["manifest_sha256"]
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0:
        raise TrainingRunnerBlocked("registered input process identity is invalid")
    output = Path(
        _absolute_path(
            Path(output_root).resolve().as_posix(), "registered input output root"
        )
    )
    if (
        authority.get("validated") is not True
        or authority.get("command") != "run-training"
        or authority.get("envelope_sha256") != expected_envelope
        or authority.get("composite_sha256") != expected_composite
    ):
        raise TrainingRunnerBlocked("run-training authority is incomplete")

    normalized_registration_binding = _artifact_binding(
        registration_binding, "registered inventory artifact"
    )
    normalized_inventory_binding = _external_binding(
        inventory_binding, "registered source inventory"
    )
    rollback_sha256 = _digest(
        rollback_authority_sha256, "registered rollback authority"
    )
    manifest_composite = build_runner_composite(manifest, "run-training")
    if (
        output.as_posix() != manifest["output_root"]
        or normalized_registration_binding != manifest["artifacts"]["registration"]
        or normalized_inventory_binding != manifest["source_inventory"]
        or rollback_sha256
        != manifest["rollback_authority"]["rollback_authority_sha256"]
        or expected_composite != manifest_composite["composite_sha256"]
    ):
        raise TrainingRunnerBlocked("registered input manifest binding differs")
    receipt_path = output.parent / f".{output.name}.pre-access-{process_id}.json"
    receipt_body = {
        "command": "run-training",
        "composite_sha256": expected_composite,
        "launch_manifest_sha256": manifest_digest,
        "output_root": output.as_posix(),
        "process_id": process_id,
        "receipt_path": receipt_path.resolve().as_posix(),
        "registration": copy.deepcopy(normalized_registration_binding),
        "rollback_authority_sha256": rollback_sha256,
        "run_envelope_sha256": expected_envelope,
        "schema_version": PRE_ACCESS_RECEIPT_SCHEMA_VERSION,
        "source_inventory": copy.deepcopy(normalized_inventory_binding),
    }
    receipt_payload = canonical_json_bytes(
        {
            **receipt_body,
            "receipt_sha256": canonical_json_sha256(receipt_body),
        }
    )
    receipt_binding = _external_binding(
        pre_access_receipt_publisher(receipt_path, receipt_payload),
        "pre-access receipt",
    )
    if (
        receipt_binding["path"] != receipt_path.resolve().as_posix()
        or not _binding_matches(receipt_payload, receipt_binding)
    ):
        raise TrainingRunnerBlocked("pre-access receipt publication differs")
    if pre_input_validator is not None:
        try:
            pre_input_validator()
        except TrainingRunnerBlocked:
            raise
        except Exception as exc:
            raise TrainingRunnerBlocked(
                "registered input pre-input validation failed"
            ) from exc

    registration_payload = registration_reader()
    if not isinstance(registration_payload, bytes) or not _binding_matches(
        registration_payload, normalized_registration_binding
    ):
        raise TrainingRunnerBlocked("registered inventory artifact differs")
    registration = _parse_canonical_mapping(
        registration_payload, "registered inventory artifact"
    )

    inventory_payload = inventory_reader()
    if not isinstance(inventory_payload, bytes) or not _binding_matches(
        inventory_payload, normalized_inventory_binding
    ):
        raise TrainingRunnerBlocked("registered source inventory differs")
    _parse_canonical_mapping(inventory_payload, "registered source inventory")
    try:
        inventory = _mapping(inventory_parser(inventory_payload), "validated source inventory")
        if canonical_json_bytes(inventory) != inventory_payload:
            raise TrainingRunnerBlocked("validated source inventory bytes differ")
        producer_result = _mapping(
            producer_validator(
                _parse_canonical_mapping(registration_payload, "producer registration"),
                _parse_canonical_mapping(inventory_payload, "producer inventory"),
            ),
            "producer registration validation",
        )
        independent_result = _mapping(
            independent_verifier(
                _parse_canonical_mapping(
                    registration_payload, "independent registration"
                ),
                _parse_canonical_mapping(inventory_payload, "independent inventory"),
            ),
            "independent registration validation",
        )
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("registration validation failed") from exc
    if producer_result != registration:
        raise TrainingRunnerBlocked("producer registration agreement differs")
    registration_sha256 = _digest(
        registration.get("registration_sha256"), "inventory registration"
    )
    expected_independent_fields = {
        "authority",
        "cohort_counts",
        "empirical_operations",
        "inventory_sha256",
        "registration_id",
        "registration_sha256",
        "verified",
    }


    if set(independent_result) != expected_independent_fields:
        raise TrainingRunnerBlocked("independent registration agreement fields differ")
    expected_cohort_counts = {"canary": 128, "holdout": 512, "training": 512}
    if (
        independent_result["verified"] is not True
        or independent_result["registration_sha256"] != registration_sha256
        or independent_result["registration_id"] != registration.get("registration_id")
        or independent_result["inventory_sha256"] != registration.get("inventory_sha256")
        or independent_result["authority"] != registration.get("authority")
        or independent_result["empirical_operations"]
        != registration.get("empirical_operations")
        or independent_result["cohort_counts"] != expected_cohort_counts
    ):
        raise TrainingRunnerBlocked("independent registration agreement differs")
    registration_body = {
        key: value
        for key, value in registration.items()
        if key != "registration_sha256"
    }
    if registration_sha256 != canonical_json_sha256(registration_body):
        raise TrainingRunnerBlocked("inventory registration self-digest differs")
    _all_boolean_mapping(
        registration.get("authority"),
        "inventory registration authority",
        require_false=True,
    )
    _all_boolean_mapping(
        registration.get("empirical_operations"),
        "inventory registration empirical operations",
        require_false=True,
    )
    cohorts = _mapping(registration.get("cohorts"), "inventory registration cohorts")
    _fields(cohorts, {"canary", "holdout", "training"}, "inventory registration cohorts")
    training_seeds = cohorts["training"]
    if (
        not isinstance(training_seeds, list)
        or len(training_seeds) != 512
        or tuple(training_seeds) != tuple(sorted(set(training_seeds)))
        or any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in training_seeds
        )
    ):
        raise TrainingRunnerBlocked("registered training cohort differs")
    authority_evidence = _mapping(
        inventory.get("authority_evidence"), "seed inventory authority evidence"
    )
    source_inventory = _mapping(
        authority_evidence.get("source_inventory"),
        "seed inventory registered source inventory",
    )
    return {
        "authority": copy.deepcopy(authority),
        "execution_registration": {
            **copy.deepcopy(registration),
            "rollback_authority_sha256": rollback_sha256,
        },
        "registration": copy.deepcopy(registration),
        "pre_access_receipt": receipt_binding,
        "source_inventory": copy.deepcopy(source_inventory),
        "training_seeds": tuple(training_seeds),
    }


def _publish_exclusive_pre_access_receipt(
    path: Path, payload: bytes
) -> dict[str, Any]:
    if (
        not isinstance(path, Path)
        or not path.is_absolute()
        or not isinstance(payload, bytes)
    ):
        raise TrainingRunnerBlocked("pre-access receipt publication input is invalid")
    publication_path = path
    if os.name == "nt":
        publication_path = path.with_name(
            f"{path.name}.{uuid.uuid4().hex}.staging"
        )
    try:
        with publication_path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name == "nt":
            try:
                _move_path_write_through(publication_path, path)
            except OSError:
                try:
                    publication_path.unlink()
                except OSError:
                    pass
                raise
        else:
            _fsync_directory(path.parent)
    except OSError as exc:
        raise TrainingRunnerBlocked("pre-access receipt publication failed") from exc
    return {
        "path": path.resolve().as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _fsync_directory(path: Path) -> None:
    if not isinstance(path, Path) or not path.is_absolute():
        raise OSError("directory sync path is invalid")
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _move_path_write_through(
    source: Path, destination: Path, *, replace: bool = False
) -> None:
    if os.name != "nt":
        if replace:
            os.replace(source, destination)
        else:
            os.rename(source, destination)
        _fsync_directory(destination.parent)
        return
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    move_file_ex = kernel32.MoveFileExW
    move_file_ex.argtypes = (wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD)
    move_file_ex.restype = wintypes.BOOL
    flags = 0x00000008 | (0x00000001 if replace else 0)
    if not move_file_ex(str(source), str(destination), flags):
        raise ctypes.WinError(ctypes.get_last_error())


def _initial_checkpoint_record(payload: bytes) -> dict[str, Any]:
    snapshot = _checkpoint_snapshot(payload)
    if snapshot["coordinates"]["next_chunk_index"] != 0 or snapshot[
        "stopped_for_family_saturation"
    ]:
        raise TrainingRunnerBlocked("initial checkpoint is not zero progress")
    body = {
        "checkpoint": snapshot,
        "schema_version": INITIAL_CHECKPOINT_SCHEMA_VERSION,
    }
    return {**body, "initial_checkpoint_sha256": canonical_json_sha256(body)}


def _checkpoint_chain_record(
    *,
    initial_payload: bytes,
    final_payload: bytes,
    chunk_index: int,
    seeds: Sequence[int],
) -> dict[str, Any]:
    if isinstance(chunk_index, bool) or not isinstance(chunk_index, int):
        raise TrainingRunnerBlocked("checkpoint chain index is invalid")
    initial = _checkpoint_snapshot(initial_payload)
    final = _checkpoint_snapshot(final_payload)
    seed_values = tuple(seeds)
    if (
        not 0 <= chunk_index < 8
        or len(seed_values) != 64
        or seed_values != tuple(sorted(set(seed_values)))
        or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seed_values)
        or initial["coordinates"]["next_chunk_index"] != chunk_index
        or final["coordinates"]["next_chunk_index"] != chunk_index + 1
    ):
        raise TrainingRunnerBlocked("checkpoint chain boundary differs")
    body = {
        "chunk_index": chunk_index,
        "final": final,
        "initial": initial,
        "schema_version": CHECKPOINT_CHAIN_SCHEMA_VERSION,
        "seeds": list(seed_values),
    }
    return {**body, "chain_sha256": canonical_json_sha256(body)}


def _checkpoint_control_binding(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    coordinates = snapshot["coordinates"]
    return {
        "checkpoint_sha256": snapshot["checkpoint_sha256"],
        "completed_pairs": coordinates["completed_pairs"],
        "component_sha256": copy.deepcopy(snapshot["component_sha256"]),
        "next_chunk_index": coordinates["next_chunk_index"],
        "training_environment_accesses": coordinates[
            "training_environment_accesses"
        ],
        "training_optimizer_steps": coordinates["training_optimizer_steps"],
    }


def _close_training_stage(
    *,
    control_api: Any,
    context: Any,
    lease: Any,
    rollback_authority: Mapping[str, Any],
    verdict: str,
    final_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish the fixed training terminal chain, rolling back saturation first."""
    operations = (
        "execute_registered_rollback",
        "publish_artifact_manifest",
        "publish_terminal_document",
        "publish_terminal_intent",
    )
    if any(not callable(getattr(control_api, name, None)) for name in operations):
        raise TrainingRunnerBlocked("training closeout control API differs")
    snapshot = _mapping(final_snapshot, "training closeout checkpoint")
    coordinates = _mapping(
        snapshot.get("coordinates"), "training closeout coordinates"
    )
    completed_chunks = coordinates.get("next_chunk_index")
    stopped = snapshot.get("stopped_for_family_saturation")
    if (
        isinstance(completed_chunks, bool)
        or not isinstance(completed_chunks, int)
        or not 1 <= completed_chunks <= 8
        or type(stopped) is not bool
    ):
        raise TrainingRunnerBlocked("training closeout checkpoint differs")
    if verdict == "training_completed_without_family_saturation":
        if completed_chunks != 8 or stopped:
            raise TrainingRunnerBlocked("completed training closeout differs")
        rollback = None
    elif verdict == "experiment_stopped_during_training_for_family_saturation":
        if not stopped:
            raise TrainingRunnerBlocked("saturated training closeout differs")
        rollback = _mapping(
            control_api.execute_registered_rollback(
                context,
                lease,
                rollback_authority=copy.deepcopy(rollback_authority),
                failure_paths=["training_family_saturation"],
            ),
            "training saturation rollback",
        )
        if (
            rollback.get("status") != "rollback_verified"
            or rollback.get("candidate_enabled") is not False
            or rollback.get("rollback_required") is not True
            or rollback.get("failure_paths") != ["training_family_saturation"]
        ):
            raise TrainingRunnerBlocked("training saturation rollback differs")
    else:
        raise TrainingRunnerBlocked("training closeout verdict differs")

    details = {
        "completed_chunks": completed_chunks,
        "final_checkpoint": _checkpoint_control_binding(snapshot),
        "stopped_for_family_saturation": stopped,
    }
    if rollback is not None:
        details["rollback_observation_sha256"] = _digest(
            rollback.get("rollback_observation_sha256"),
            "training saturation rollback observation",
        )
    intent = _mapping(
        control_api.publish_terminal_intent(
            context,
            lease,
            verdict=verdict,
            details=details,
        ),
        "training terminal intent",
    )
    terminal = _mapping(
        control_api.publish_terminal_document(
            context,
            lease,
            terminal_intent=intent,
        ),
        "training terminal document",
    )
    manifest = _mapping(
        control_api.publish_artifact_manifest(
            context,
            lease,
            terminal_document=terminal,
        ),
        "training artifact manifest",
    )
    return {
        "artifact_manifest_sha256": _digest(
            manifest.get("manifest_sha256"), "training artifact manifest"
        ),
        "rollback_observation_sha256": (
            None
            if rollback is None
            else rollback["rollback_observation_sha256"]
        ),
        "terminal_intent_sha256": _digest(
            intent.get("terminal_intent_sha256"), "training terminal intent"
        ),
        "terminal_sha256": _digest(
            terminal.get("terminal_sha256"), "training terminal document"
        ),
        "verdict": verdict,
    }


def _run_training_schedule(
    *,
    control_api: Any,
    runtime_api: Any,
    context: Any,
    lease: Any,
    runtime_state: Any,
    training_seeds: Sequence[int],
    environment_factory: Callable[[int], Any],
    deadline: float,
    clock: Callable[[], float],
    closeout: Callable[..., Any],
) -> dict[str, Any]:
    """Compose exact per-chunk runtime work under durable control-plane hooks."""
    seed_values = tuple(training_seeds)
    if (
        len(seed_values) != 512
        or seed_values != tuple(sorted(set(seed_values)))
        or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seed_values)
    ):
        raise TrainingRunnerBlocked("training seed schedule differs")
    if not callable(environment_factory) or not callable(clock) or not callable(closeout):
        raise TrainingRunnerBlocked("training schedule callback is invalid")

    predecessor = runtime_api.encode_paired_training_checkpoint(runtime_state)
    predecessor_snapshot = _checkpoint_snapshot(predecessor)
    start_index = predecessor_snapshot["coordinates"]["next_chunk_index"]
    if start_index >= 8 or predecessor_snapshot["stopped_for_family_saturation"]:
        raise TrainingRunnerBlocked("training schedule cannot start from terminal state")
    control_api.publish_managed_artifact(
        context,
        lease,
        relative_path=f"runtime_checkpoints/chunk_{start_index:04d}.json",
        payload=predecessor,
    )
    if start_index == 0:
        control_api.publish_managed_artifact(
            context,
            lease,
            relative_path="checkpoint_chains/initial.json",
            payload=canonical_json_bytes(_initial_checkpoint_record(predecessor)),
        )

    completed_chunks = start_index
    final_snapshot = predecessor_snapshot
    for chunk_index in range(start_index, 8):
        if runtime_api.encode_paired_training_checkpoint(runtime_state) != predecessor:
            raise TrainingRunnerBlocked("runtime predecessor checkpoint differs")
        chunk_seeds = seed_values[chunk_index * 64 : (chunk_index + 1) * 64]

        def before_environment(arm: str, seed: int) -> None:
            control_api.perform_journaled_environment_access(
                context,
                lease,
                seed=seed,
                arm=arm,
                purpose="training",
                access=lambda: None,
            )

        def after_environment(_arm: str, _seed: int) -> None:
            control_api.reconcile_resource_ledger(context, lease)

        try:
            completed = runtime_api.collect_and_complete_paired_training_chunk(
                runtime_state,
                environment_factory=environment_factory,
                seeds=chunk_seeds,
                chunk_index=chunk_index,
                before_environment=before_environment,
                after_environment=after_environment,
                deadline=deadline,
                clock=clock,
            )
        except Exception:
            control_api.reconcile_resource_ledger(context, lease)
            raise
        final_payload = completed.checkpoint
        if (
            not isinstance(final_payload, bytes)
            or final_payload != runtime_api.encode_paired_training_checkpoint(runtime_state)
            or tuple(completed.seeds) != chunk_seeds
        ):
            raise TrainingRunnerBlocked("runtime final checkpoint differs")
        chain = _checkpoint_chain_record(
            initial_payload=predecessor,
            final_payload=final_payload,
            chunk_index=chunk_index,
            seeds=chunk_seeds,
        )
        final_snapshot = chain["final"]
        ledger = control_api.reconcile_resource_ledger(context, lease)
        control_api.advance_resource_ledger(
            context,
            lease,
            charged_seconds=ledger["resources"]["charged_seconds"],
            environment_accesses=final_snapshot["coordinates"][
                "training_environment_accesses"
            ],
            optimizer_steps=final_snapshot["coordinates"][
                "training_optimizer_steps"
            ],
            shadow_optimizer_steps=0,
            reason=f"complete-training-chunk-{chunk_index:04d}",
        )
        control_api.publish_managed_artifact(
            context,
            lease,
            relative_path=f"runtime_checkpoints/chunk_{chunk_index + 1:04d}.json",
            payload=final_payload,
        )
        control_api.publish_managed_artifact(
            context,
            lease,
            relative_path=f"checkpoint_chains/chunk_{chunk_index + 1:04d}.json",
            payload=canonical_json_bytes(chain),
        )
        control_api.publish_complete_training_checkpoint(
            context,
            lease,
            binding=_checkpoint_control_binding(final_snapshot),
        )
        predecessor = final_payload
        completed_chunks = chunk_index + 1
        if completed.saturation["stop"] is True:
            break

    verdict = runtime_api.training_progress_verdict(runtime_state)
    if verdict not in {
        "training_completed_without_family_saturation",
        "experiment_stopped_during_training_for_family_saturation",
    }:
        raise TrainingRunnerBlocked("training schedule ended without terminal verdict")
    closeout(verdict, final_snapshot)
    return {
        "completed_chunks": completed_chunks,
        "environment_debits": final_snapshot["coordinates"][
            "training_environment_accesses"
        ],
        "final_checkpoint_sha256": final_snapshot["checkpoint_sha256"],
        "verdict": verdict,
    }


def _runner_launch_payload(
    *,
    manifest_sha256: str,
    process_id: int,
    rollback_authority_sha256: str,
    run_envelope_sha256: str,
) -> bytes:
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0:
        raise TrainingRunnerBlocked("runner launch process identity is invalid")
    body = {
        "command": "run-training",
        "launch_manifest_sha256": _digest(
            manifest_sha256, "runner launch manifest"
        ),
        "process_id": process_id,
        "rollback_authority_sha256": _digest(
            rollback_authority_sha256, "runner launch rollback authority"
        ),
        "run_envelope_sha256": _digest(
            run_envelope_sha256, "runner launch envelope"
        ),
        "schema_version": RUNNER_LAUNCH_MARKER_SCHEMA_VERSION,
    }
    return canonical_json_bytes(
        {**body, "launch_sha256": canonical_json_sha256(body)}
    )


def _validated_original_runner_launch(
    payload: bytes,
    *,
    manifest_sha256: str,
    rollback_authority_sha256: str,
    run_envelope_sha256: str,
) -> dict[str, Any]:
    if not isinstance(payload, bytes):
        raise TrainingRunnerBlocked("original runner launch is invalid")
    launch = _parse_canonical_mapping(payload, "original runner launch")
    _fields(
        launch,
        {
            "command",
            "launch_manifest_sha256",
            "launch_sha256",
            "process_id",
            "rollback_authority_sha256",
            "run_envelope_sha256",
            "schema_version",
        },
        "original runner launch",
    )
    body = {key: value for key, value in launch.items() if key != "launch_sha256"}
    if (
        launch["command"] != "run-training"
        or launch["schema_version"] != RUNNER_LAUNCH_MARKER_SCHEMA_VERSION
        or launch["launch_manifest_sha256"] != manifest_sha256
        or launch["rollback_authority_sha256"] != rollback_authority_sha256
        or launch["run_envelope_sha256"] != run_envelope_sha256
        or launch["launch_sha256"] != canonical_json_sha256(body)
        or isinstance(launch["process_id"], bool)
        or not isinstance(launch["process_id"], int)
        or launch["process_id"] <= 0
    ):
        raise TrainingRunnerBlocked("original runner launch differs")
    return launch


def _validated_artifact_inventory(value: object) -> dict[str, Any]:
    inventory = _mapping(value, "dead owner artifact inventory")
    _fields(
        inventory,
        {
            "artifact_count",
            "artifact_inventory_sha256",
            "artifacts",
            "schema_version",
            "stored_size_bytes",
            "uncompressed_size_bytes",
        },
        "dead owner artifact inventory",
    )
    artifacts = inventory["artifacts"]
    if (
        inventory["schema_version"]
        != CONTROL_ARTIFACT_INVENTORY_SCHEMA_VERSION
        or not isinstance(artifacts, list)
        or isinstance(inventory["artifact_count"], bool)
        or not isinstance(inventory["artifact_count"], int)
        or inventory["artifact_count"] != len(artifacts)
    ):
        raise TrainingRunnerBlocked("dead owner artifact inventory differs")
    normalized_rows = []
    paths = []
    stored_total = 0
    uncompressed_total = 0
    row_fields = {
        "encoding",
        "path",
        "stored_sha256",
        "stored_size_bytes",
        "uncompressed_sha256",
        "uncompressed_size_bytes",
    }
    for value in artifacts:
        row = _mapping(value, "dead owner artifact inventory row")
        _fields(row, row_fields, "dead owner artifact inventory row")
        path = _relative_path(row["path"], "managed artifact path")
        if any(
            part.startswith(".") and part.endswith(".tmp")
            for part in PurePosixPath(path).parts
        ):
            raise TrainingRunnerBlocked("managed artifact path is ambiguous")
        if row["encoding"] not in {
            "identity-bytes-v1",
            "deterministic-gzip-v1",
        }:
            raise TrainingRunnerBlocked("managed artifact encoding differs")
        _digest(row["stored_sha256"], "managed stored artifact")
        _digest(row["uncompressed_sha256"], "managed uncompressed artifact")
        for field in ("stored_size_bytes", "uncompressed_size_bytes"):
            size = row[field]
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise TrainingRunnerBlocked("managed artifact size differs")
        if row["encoding"] == "identity-bytes-v1" and (
            row["stored_sha256"] != row["uncompressed_sha256"]
            or row["stored_size_bytes"] != row["uncompressed_size_bytes"]
        ):
            raise TrainingRunnerBlocked("managed identity artifact differs")
        paths.append(path)
        stored_total += row["stored_size_bytes"]
        uncompressed_total += row["uncompressed_size_bytes"]
        normalized_rows.append(copy.deepcopy(row))
    if paths != sorted(set(paths)):
        raise TrainingRunnerBlocked("managed artifact paths differ")
    for field, total in (
        ("stored_size_bytes", stored_total),
        ("uncompressed_size_bytes", uncompressed_total),
    ):
        value = inventory[field]
        if isinstance(value, bool) or not isinstance(value, int) or value != total:
            raise TrainingRunnerBlocked("dead owner artifact inventory total differs")
    body = {
        "artifact_count": len(normalized_rows),
        "artifacts": normalized_rows,
        "schema_version": CONTROL_ARTIFACT_INVENTORY_SCHEMA_VERSION,
        "stored_size_bytes": stored_total,
        "uncompressed_size_bytes": uncompressed_total,
    }
    if inventory["artifact_inventory_sha256"] != canonical_json_sha256(body):
        raise TrainingRunnerBlocked("dead owner artifact inventory digest differs")
    return {**body, "artifact_inventory_sha256": inventory["artifact_inventory_sha256"]}


def _validated_runner_authority_identity(value: object) -> dict[str, str]:
    identity = _mapping(value, "runner authority identity")
    _fields(
        identity,
        {
            "composite_sha256",
            "launch_manifest_sha256",
            "rollback_authority_sha256",
            "run_envelope_sha256",
        },
        "runner authority identity",
    )
    return {
        name: _digest(identity[name], f"runner authority {name}")
        for name in sorted(identity)
    }


def _runner_authority_guard_payload(identity: Mapping[str, Any]) -> bytes:
    body = {
        "authority": _validated_runner_authority_identity(identity),
        "schema_version": RUNNER_AUTHORITY_GUARD_SCHEMA_VERSION,
    }
    return canonical_json_bytes(
        {**body, "guard_sha256": canonical_json_sha256(body)}
    )


def _terminalization_guard_payload(manifest: Mapping[str, Any]) -> bytes:
    normalized = validate_launch_manifest(manifest)
    body = {
        "launch_manifest_sha256": normalized["manifest_sha256"],
        "output_root": normalized["output_root"],
        "schema_version": TERMINALIZATION_GUARD_SCHEMA_VERSION,
    }
    return canonical_json_bytes(
        {**body, "guard_sha256": canonical_json_sha256(body)}
    )


def _ensure_terminalization_guard(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Create the output-sibling closure guard before managed output exists."""
    normalized = validate_launch_manifest(manifest)
    path = Path(normalized["terminalization_guard"])
    payload = _terminalization_guard_payload(normalized)
    staging = path.with_name(f".{path.name}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if staging.exists():
            raise TrainingRunnerBlocked("terminalization guard has ambiguous staging")
        if path.exists():
            if path.read_bytes() != payload:
                raise TrainingRunnerBlocked("terminalization guard differs")
        else:
            if Path(normalized["output_root"]).exists():
                raise TrainingRunnerBlocked(
                    "existing output lacks terminalization guard"
                )
            with staging.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(staging, path)
            except FileExistsError:
                if path.read_bytes() != payload:
                    raise TrainingRunnerBlocked("terminalization guard differs")
            finally:
                staging.unlink(missing_ok=True)
    except TrainingRunnerBlocked:
        raise
    except OSError as exc:
        raise TrainingRunnerBlocked("terminalization guard publication failed") from exc
    return {
        "path": path.resolve().as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


@contextmanager
def _hold_terminalization_guard(
    *, control_api: Any, manifest: Mapping[str, Any]
) -> Any:
    normalized = validate_launch_manifest(manifest)
    path = Path(normalized["terminalization_guard"])
    payload = _terminalization_guard_payload(normalized)
    staging = path.with_name(f".{path.name}.tmp")
    if staging.exists():
        raise TrainingRunnerBlocked("terminalization guard has ambiguous staging")
    try:
        handle = path.open("r+b", buffering=0)
    except OSError as exc:
        raise TrainingRunnerBlocked("terminalization guard is unavailable") from exc
    locked = False
    try:
        control_api._lock_file(handle)
        locked = True
        handle.seek(0)
        if handle.read() != payload or staging.exists():
            raise TrainingRunnerBlocked("terminalization guard changed")
        yield path
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("terminalization guard failed") from exc
    finally:
        if locked:
            try:
                control_api._unlock_file(handle)
            except OSError:
                pass
        handle.close()


@contextmanager
def _hold_exact_dead_owner_execution_lease(
    *,
    control_api: Any,
    context: Any,
    output_root: Path | str,
    expected_owner: Mapping[str, Any],
    expected_lease_sha256: str,
    process_id: int,
    process_alive: Callable[[int], bool],
    clock: Callable[[], float],
) -> Any:
    """Lock an exact stale lease without changing its registered owner bytes."""
    owner = _validated_lease_owner(expected_owner, "preserved stale lease owner")
    lease_sha256 = _digest(
        expected_lease_sha256, "preserved stale lease identity"
    )
    if not callable(process_alive) or not callable(clock):
        raise TrainingRunnerBlocked("preserved stale lease observers are invalid")
    try:
        if process_alive(process_id) is not True:
            raise TrainingRunnerBlocked(
                "preserved stale lease terminalizer is not alive"
            )
        if process_alive(owner["child_process_id"]) is not False:
            raise TrainingRunnerBlocked(
                "preserved stale lease owner is not proven dead"
            )
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked(
            "preserved stale lease liveness observation failed"
        ) from exc

    output = Path(output_root).resolve()
    lease = control_api.ExecutionLease(
        output,
        context=context,
        child_process_id=process_id,
        process_alive=process_alive,
        allow_stale_reclaim=True,
        clock=clock,
    )
    key = os.path.normcase(str(lease.path))
    if key in control_api._ACTIVE_EXECUTION_LEASES:
        raise TrainingRunnerBlocked("preserved stale execution lease is already held")
    try:
        handle = lease.path.open("r+b", buffering=0)
    except OSError as exc:
        raise TrainingRunnerBlocked(
            "preserved stale execution lease is unavailable"
        ) from exc
    locked = False
    activated = False
    try:
        try:
            control_api._lock_file(handle)
            locked = True
        except OSError as exc:
            raise TrainingRunnerBlocked(
                "preserved stale execution lease is already held"
            ) from exc
        handle.seek(0)
        payload = handle.read()
        if hashlib.sha256(payload).hexdigest() != lease_sha256:
            raise TrainingRunnerBlocked(
                "terminalization preserved stale execution lease bytes differ"
            )
        record = _parse_canonical_mapping(payload, "preserved stale execution lease")
        _fields(
            record,
            {"identity", "owner", "reclaimed_owner", "schema_version"},
            "preserved stale execution lease",
        )
        if (
            record["schema_version"] != control_api.LEASE_SCHEMA_VERSION
            or record["identity"] != control_api._context_identity(context)
            or record["owner"] != owner
        ):
            raise TrainingRunnerBlocked(
                "preserved stale execution lease identity differs"
            )
        ambiguous = sorted(
            path.name
            for path in output.iterdir()
            if path.name.startswith(".") and path.name.endswith(".tmp")
        )
        if ambiguous:
            raise TrainingRunnerBlocked(
                "preserved stale execution lease has ambiguous staging"
            )
        lease.owner = copy.deepcopy(owner)
        lease.reclaimed_owner = copy.deepcopy(owner)
        lease.started_monotonic = float(owner["acquired_monotonic"])
        lease._handle = handle
        lease.held = True
        control_api._ACTIVE_EXECUTION_LEASES.add(key)
        activated = True
        try:
            yield lease
        finally:
            handle.seek(0)
            if handle.read() != payload:
                raise TrainingRunnerBlocked(
                    "preserved stale execution lease changed while held"
                )
    finally:
        lease._handle = None
        lease.held = False
        if activated:
            control_api._ACTIVE_EXECUTION_LEASES.discard(key)
        try:
            if locked:
                control_api._unlock_file(handle)
        finally:
            handle.close()


def _terminalization_failure_prefix(
    *,
    control_api: Any,
    context: Any,
    output_root: Path | str,
    runner_authority_identity: Mapping[str, Any],
    process_alive: Callable[[int], bool],
    lease_payload_override: bytes | None = None,
    held_lease: Any | None = None,
) -> dict[str, Any]:
    """Validate and bind a nonterminal dead-owner prefix, including partial chunks."""
    output = Path(output_root).resolve()
    if not output.is_dir() or output.is_symlink():
        raise TrainingRunnerBlocked("terminalization output root is invalid")
    authority_identity = _validated_runner_authority_identity(
        runner_authority_identity
    )
    authority_guard = output.parent / f".{output.name}.execution.guard"
    try:
        if authority_guard.read_bytes() != _runner_authority_guard_payload(
            authority_identity
        ):
            raise TrainingRunnerBlocked("terminalization runner authority guard differs")
        lease_payload = (
            lease_payload_override
            if lease_payload_override is not None
            else (output / control_api.LEASE_FILENAME).read_bytes()
        )
    except TrainingRunnerBlocked:
        raise
    except OSError as exc:
        raise TrainingRunnerBlocked("terminalization prefix is unreadable") from exc
    lease_record = _parse_canonical_mapping(lease_payload, "terminalization lease")
    _fields(
        lease_record,
        {"identity", "owner", "reclaimed_owner", "schema_version"},
        "terminalization lease",
    )
    owner = _validated_lease_owner(
        lease_record["owner"], "terminalization lease owner"
    )
    if lease_record["reclaimed_owner"] is not None:
        _validated_lease_owner(
            lease_record["reclaimed_owner"], "terminalization reclaimed owner"
        )
    context_identity = _mapping(
        control_api._context_identity(context), "terminalization context identity"
    )
    if (
        lease_record["schema_version"] != control_api.LEASE_SCHEMA_VERSION
        or lease_record["identity"] != context_identity
    ):
        raise TrainingRunnerBlocked("terminalization lease identity differs")
    try:
        owner_alive = process_alive(owner["child_process_id"])
    except Exception as exc:
        raise TrainingRunnerBlocked("terminalization owner liveness failed") from exc
    if owner_alive is not False:
        raise TrainingRunnerBlocked("terminalization owner is not dead")

    terminal_names = (
        control_api.TERMINAL_INTENT_FILENAME,
        control_api.TERMINAL_FILENAME,
        control_api.MANIFEST_FILENAME,
    )
    if any((output / name).exists() for name in terminal_names):
        raise TrainingRunnerBlocked("terminalization prefix is already terminal")
    owns_probe = held_lease is None
    probe = held_lease
    if probe is None:
        probe = control_api.ExecutionLease(
            output,
            context=context,
            child_process_id=owner["child_process_id"],
            process_alive=process_alive,
        )
        probe.held = True
    try:
        journal_prefix = _mapping(
            control_api._journal_prefix_binding(context, probe),
            "terminalization journal prefix",
        )
        resource_prefix = _mapping(
            control_api._resource_prefix_binding(context, probe),
            "terminalization resource prefix",
        )
        checkpoint_markers = [
            copy.deepcopy(marker)
            for marker in control_api._load_training_checkpoint_markers(
                context, output
            )
        ]
        artifact_inventory = _validated_artifact_inventory(
            control_api._observe_artifact_inventory(output, excluded_paths=())
        )
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("terminalization prefix validation failed") from exc
    finally:
        if owns_probe:
            probe.held = False
    if any(
        row["path"]
        in {
            TERMINALIZATION_CLOSURE_FILENAME,
            control_api.ROLLBACK_OBSERVATION_FILENAME,
            *terminal_names,
        }
        for row in artifact_inventory["artifacts"]
    ):
        raise TrainingRunnerBlocked("terminalization prefix contains closure evidence")
    launch_rows = [
        row
        for row in artifact_inventory["artifacts"]
        if row["path"] == "runner_launch.json"
    ]
    if len(launch_rows) != 1:
        raise TrainingRunnerBlocked("terminalization runner launch is unavailable")
    try:
        launch_payload = (output / "runner_launch.json").read_bytes()
    except OSError as exc:
        raise TrainingRunnerBlocked("terminalization runner launch is unreadable") from exc
    if hashlib.sha256(launch_payload).hexdigest() != launch_rows[0]["stored_sha256"]:
        raise TrainingRunnerBlocked("terminalization runner launch binding differs")
    launch = _validated_original_runner_launch(
        launch_payload,
        manifest_sha256=authority_identity["launch_manifest_sha256"],
        rollback_authority_sha256=authority_identity["rollback_authority_sha256"],
        run_envelope_sha256=authority_identity["run_envelope_sha256"],
    )
    if launch["process_id"] != owner["child_process_id"]:
        raise TrainingRunnerBlocked("terminalization launch owner differs")
    body = {
        "artifact_inventory": artifact_inventory,
        "checkpoint_markers": checkpoint_markers,
        "context_identity": context_identity,
        "journal_prefix": journal_prefix,
        "lease_sha256": hashlib.sha256(lease_payload).hexdigest(),
        "owner": owner,
        "resource_prefix": resource_prefix,
        "runner_authority_identity": authority_identity,
        "runner_launch": launch,
    }
    return {**body, "prefix_sha256": canonical_json_sha256(body)}


def _validate_terminalization_failure_prefix(value: object) -> dict[str, Any]:
    prefix = _mapping(value, "terminalization failure prefix")
    _fields(
        prefix,
        {
            "artifact_inventory",
            "checkpoint_markers",
            "context_identity",
            "journal_prefix",
            "lease_sha256",
            "owner",
            "prefix_sha256",
            "resource_prefix",
            "runner_authority_identity",
            "runner_launch",
        },
        "terminalization failure prefix",
    )
    normalized = {
        "artifact_inventory": _validated_artifact_inventory(
            prefix["artifact_inventory"]
        ),
        "checkpoint_markers": copy.deepcopy(prefix["checkpoint_markers"]),
        "context_identity": _mapping(
            prefix["context_identity"], "terminalization prefix context"
        ),
        "journal_prefix": _mapping(
            prefix["journal_prefix"], "terminalization prefix journal"
        ),
        "lease_sha256": _digest(
            prefix["lease_sha256"], "terminalization prefix lease"
        ),
        "owner": _validated_lease_owner(
            prefix["owner"], "terminalization prefix owner"
        ),
        "resource_prefix": _mapping(
            prefix["resource_prefix"], "terminalization prefix resource"
        ),
        "runner_authority_identity": _validated_runner_authority_identity(
            prefix["runner_authority_identity"]
        ),
        "runner_launch": _mapping(
            prefix["runner_launch"], "terminalization prefix launch"
        ),
    }
    if not isinstance(normalized["checkpoint_markers"], list):
        raise TrainingRunnerBlocked("terminalization checkpoint prefix differs")
    expected = canonical_json_sha256(normalized)
    if _digest(prefix["prefix_sha256"], "terminalization prefix") != expected:
        raise TrainingRunnerBlocked("terminalization failure prefix digest differs")
    return {**normalized, "prefix_sha256": expected}


def _identity_observation_matches(
    value: object, expected: Mapping[str, Any], label: str
) -> dict[str, Any]:
    observation = _mapping(value, label)
    if set(observation) == {"error", "matches_registered", "observed"}:
        if observation["error"] is not None:
            raise TrainingRunnerBlocked(f"{label} differs")
        observation.pop("error")
    _fields(observation, {"matches_registered", "observed"}, label)
    if (
        observation["matches_registered"] is not True
        or observation["observed"] != expected
    ):
        raise TrainingRunnerBlocked(f"{label} differs")
    return observation


def _build_terminalization_rollback_plan(
    *,
    control_api: Any,
    context: Any,
    output_root: Path | str,
    rollback_authority: Mapping[str, Any],
    failure_paths: Sequence[str],
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None = None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
) -> dict[str, Any]:
    authority = _validate_rollback_authority(rollback_authority)
    output = Path(output_root).resolve()
    file_observer = external_binding_observer or control_api.external_file_binding
    directory_observer = (
        checkpoint_snapshot_observer or control_api.snapshot_directory_tree
    )
    classification = _mapping(
        control_api.classify_terminal_closeout(failure_paths=failure_paths),
        "terminalization rollback classification",
    )
    if classification["failure_paths"] != list(failure_paths):
        raise TrainingRunnerBlocked("terminalization failure classification differs")
    expected_control = {
        "checkpoint": authority["control_target"]["checkpoint"],
        "configuration": authority["control_target"]["configuration"],
    }
    control_before = _identity_observation_matches(
        control_api._capture_identity_observation(
            lambda: control_api._observe_control_identities(authority, file_observer),
            label="control identity observation before rollback",
        ),
        expected_control,
        "terminalization control identity before rollback",
    )
    production_before = _identity_observation_matches(
        control_api._capture_identity_observation(
            lambda: control_api._observe_production_isolation(
                authority, file_observer, directory_observer
            ),
            label="production isolation observation before rollback",
        ),
        authority["production_isolation"],
        "terminalization production isolation before rollback",
    )
    relative, target = control_api._managed_artifact_target(
        output, authority["target_relative_path"]
    )
    target_before = (
        control_api._artifact_binding(relative, target) if target.exists() else None
    )
    target_payload = canonical_json_bytes(authority["control_target"])
    target_after = {
        "path": relative,
        "sha256": hashlib.sha256(target_payload).hexdigest(),
        "size_bytes": len(target_payload),
    }
    body = {
        "classification": classification,
        "control_identities_before": control_before,
        "control_target_after": target_after,
        "control_target_before": target_before,
        "production_isolation_before": production_before,
        "rollback_authority_sha256": authority["rollback_authority_sha256"],
    }
    return {**body, "rollback_plan_sha256": canonical_json_sha256(body)}


def _validate_terminalization_rollback_plan(
    value: object, *, rollback_authority: Mapping[str, Any]
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
    authority = _validate_rollback_authority(rollback_authority)
    if plan["rollback_authority_sha256"] != authority["rollback_authority_sha256"]:
        raise TrainingRunnerBlocked("terminalization rollback authority differs")
    body = {key: item for key, item in plan.items() if key != "rollback_plan_sha256"}
    if _digest(plan["rollback_plan_sha256"], "terminalization rollback plan") != canonical_json_sha256(body):
        raise TrainingRunnerBlocked("terminalization rollback plan digest differs")
    classification = _mapping(plan["classification"], "terminalization classification")
    expected_classification = importlib.import_module(
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
    ).classify_terminal_closeout(failure_paths=classification.get("failure_paths"))
    if classification != expected_classification:
        raise TrainingRunnerBlocked("terminalization rollback classification differs")
    for name in ("control_target_before", "control_target_after"):
        binding = plan[name]
        if binding is not None:
            normalized = _artifact_binding(binding, f"terminalization {name}")
            if normalized["path"] != authority["target_relative_path"]:
                raise TrainingRunnerBlocked("terminalization rollback target differs")
    return copy.deepcopy(plan)


def _terminalization_closure_document(
    *,
    manifest_sha256: str,
    terminalization_envelope_sha256: str,
    failure_prefix: Mapping[str, Any],
    failure_paths: Sequence[str],
    rollback_plan: Mapping[str, Any],
    run_envelope_sha256: str,
) -> dict[str, Any]:
    body = {
        "command": "terminalize-dead-owner",
        "failure_paths": list(failure_paths),
        "failure_prefix": _validate_terminalization_failure_prefix(failure_prefix),
        "launch_manifest_sha256": _digest(
            manifest_sha256, "terminalization closure manifest"
        ),
        "rollback_plan": copy.deepcopy(dict(rollback_plan)),
        "run_envelope_sha256": _digest(
            run_envelope_sha256, "terminalization closure run envelope"
        ),
        "schema_version": TERMINALIZATION_CLOSURE_SCHEMA_VERSION,
        "terminalization_envelope_sha256": _digest(
            terminalization_envelope_sha256,
            "terminalization closure envelope",
        ),
    }
    return {**body, "closure_sha256": canonical_json_sha256(body)}


def _parse_terminalization_closure(
    payload: bytes,
    *,
    manifest_sha256: str,
    terminalization_envelope_sha256: str,
    rollback_authority: Mapping[str, Any],
    run_envelope_sha256: str,
) -> dict[str, Any]:
    closure = _parse_canonical_mapping(payload, "terminalization closure")
    _fields(
        closure,
        {
            "closure_sha256",
            "command",
            "failure_paths",
            "failure_prefix",
            "launch_manifest_sha256",
            "rollback_plan",
            "run_envelope_sha256",
            "schema_version",
            "terminalization_envelope_sha256",
        },
        "terminalization closure",
    )
    if (
        closure["command"] != "terminalize-dead-owner"
        or closure["schema_version"] != TERMINALIZATION_CLOSURE_SCHEMA_VERSION
        or closure["launch_manifest_sha256"] != manifest_sha256
        or closure["terminalization_envelope_sha256"]
        != terminalization_envelope_sha256
        or closure["run_envelope_sha256"] != run_envelope_sha256
    ):
        raise TrainingRunnerBlocked("terminalization closure identity differs")
    prefix = _validate_terminalization_failure_prefix(closure["failure_prefix"])
    plan = _validate_terminalization_rollback_plan(
        closure["rollback_plan"], rollback_authority=rollback_authority
    )
    expected = _terminalization_closure_document(
        manifest_sha256=manifest_sha256,
        terminalization_envelope_sha256=terminalization_envelope_sha256,
        failure_prefix=prefix,
        failure_paths=closure["failure_paths"],
        rollback_plan=plan,
        run_envelope_sha256=run_envelope_sha256,
    )
    if closure != expected:
        raise TrainingRunnerBlocked("terminalization closure differs")
    return closure


def _managed_inventory_row_from_binding(binding: Mapping[str, Any]) -> dict[str, Any]:
    normalized = _artifact_binding(binding, "terminalization artifact binding")
    return {
        "encoding": "identity-bytes-v1",
        "path": normalized["path"],
        "stored_sha256": normalized["sha256"],
        "stored_size_bytes": normalized["size_bytes"],
        "uncompressed_sha256": normalized["sha256"],
        "uncompressed_size_bytes": normalized["size_bytes"],
    }


def _terminalization_resume_state(
    *,
    control_api: Any,
    context: Any,
    output_root: Path | str,
    closure: Mapping[str, Any],
    closure_payload: bytes,
    rollback_authority: Mapping[str, Any],
) -> dict[str, Any]:
    output = Path(output_root).resolve()
    authority = _validate_rollback_authority(rollback_authority)
    prefix = _validate_terminalization_failure_prefix(closure["failure_prefix"])
    plan = _validate_terminalization_rollback_plan(
        closure["rollback_plan"], rollback_authority=authority
    )
    inventory = _validated_artifact_inventory(
        control_api._observe_artifact_inventory(output, excluded_paths=())
    )
    observed = {row["path"]: row for row in inventory["artifacts"]}
    base = {
        row["path"]: row for row in prefix["artifact_inventory"]["artifacts"]
    }
    suffix_order = (
        TERMINALIZATION_CLOSURE_FILENAME,
        control_api.ROLLBACK_OBSERVATION_FILENAME,
        control_api.TERMINAL_INTENT_FILENAME,
        control_api.TERMINAL_FILENAME,
        control_api.MANIFEST_FILENAME,
    )
    present = {name: name in observed for name in suffix_order}
    if not present[TERMINALIZATION_CLOSURE_FILENAME]:
        raise TrainingRunnerBlocked("terminalization closure marker is missing")
    try:
        stored_closure = (output / TERMINALIZATION_CLOSURE_FILENAME).read_bytes()
    except OSError as exc:
        raise TrainingRunnerBlocked("terminalization closure marker is unreadable") from exc
    if stored_closure != closure_payload:
        raise TrainingRunnerBlocked("terminalization closure marker changed")
    seen_gap = False
    for name in suffix_order:
        if not present[name]:
            seen_gap = True
        elif seen_gap:
            raise TrainingRunnerBlocked("terminalization suffix order differs")

    reconstructed = copy.deepcopy(observed)
    for name in suffix_order:
        reconstructed.pop(name, None)
    target_path = authority["target_relative_path"]
    target_row = reconstructed.get(target_path)
    base_target = base.get(target_path)
    after_target = _managed_inventory_row_from_binding(plan["control_target_after"])
    if present[control_api.MANIFEST_FILENAME] and target_row != after_target:
        raise TrainingRunnerBlocked("complete terminalization rollback target drifted")
    if target_row == after_target:
        if base_target is None:
            reconstructed.pop(target_path, None)
        else:
            reconstructed[target_path] = copy.deepcopy(base_target)
    elif target_row != base_target:
        raise TrainingRunnerBlocked("terminalization rollback target prefix differs")
    if [reconstructed[name] for name in sorted(reconstructed)] != [
        base[name] for name in sorted(base)
    ]:
        raise TrainingRunnerBlocked("terminalization failure prefix changed")
    if prefix["context_identity"] != control_api._context_identity(context):
        raise TrainingRunnerBlocked("terminalization prefix context changed")
    return {
        "complete": present[control_api.MANIFEST_FILENAME],
        "inventory": inventory,
        "plan": plan,
        "present": present,
    }


def _current_dead_terminalization_lease(
    *,
    control_api: Any,
    context: Any,
    output_root: Path | str,
    process_alive: Callable[[int], bool],
) -> dict[str, Any]:
    output = Path(output_root).resolve()
    try:
        payload = (output / control_api.LEASE_FILENAME).read_bytes()
    except OSError as exc:
        raise TrainingRunnerBlocked("terminalization lease is unreadable") from exc
    lease = _parse_canonical_mapping(payload, "current terminalization lease")
    _fields(
        lease,
        {"identity", "owner", "reclaimed_owner", "schema_version"},
        "current terminalization lease",
    )
    owner = _validated_lease_owner(lease["owner"], "current terminalization owner")
    if lease["reclaimed_owner"] is not None:
        _validated_lease_owner(
            lease["reclaimed_owner"], "current terminalization reclaimed owner"
        )
    if (
        lease["schema_version"] != control_api.LEASE_SCHEMA_VERSION
        or lease["identity"] != control_api._context_identity(context)
    ):
        raise TrainingRunnerBlocked("current terminalization lease identity differs")
    try:
        alive = process_alive(owner["child_process_id"])
    except Exception as exc:
        raise TrainingRunnerBlocked("current terminalization liveness failed") from exc
    if alive is not False:
        raise TrainingRunnerBlocked("current terminalization owner is not dead")
    return {
        "lease_sha256": hashlib.sha256(payload).hexdigest(),
        "owner": owner,
        "payload": payload,
    }


def _execute_or_resume_terminalization_rollback(
    *,
    control_api: Any,
    context: Any,
    lease: Any,
    rollback_authority: Mapping[str, Any],
    rollback_plan: Mapping[str, Any],
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None = None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
) -> dict[str, Any]:
    authority = _validate_rollback_authority(rollback_authority)
    plan = _validate_terminalization_rollback_plan(
        rollback_plan, rollback_authority=authority
    )
    output = Path(context.request["output_root"]).resolve()
    file_observer = external_binding_observer or control_api.external_file_binding
    directory_observer = (
        checkpoint_snapshot_observer or control_api.snapshot_directory_tree
    )
    relative, target = control_api._managed_artifact_target(
        output, authority["target_relative_path"]
    )
    target_payload = canonical_json_bytes(authority["control_target"])
    if target.exists():
        try:
            current_target = target.read_bytes()
        except OSError as exc:
            raise TrainingRunnerBlocked("terminalization rollback target is unreadable") from exc
    else:
        current_target = None
    before_binding = plan["control_target_before"]
    before_matches = (
        current_target is None
        if before_binding is None
        else current_target is not None
        and hashlib.sha256(current_target).hexdigest() == before_binding["sha256"]
        and len(current_target) == before_binding["size_bytes"]
    )
    if current_target != target_payload:
        if not before_matches:
            raise TrainingRunnerBlocked("terminalization rollback target changed")
        try:
            control_api._atomic_replace_rollback_target(target, target_payload)
        except Exception as exc:
            raise TrainingRunnerBlocked("terminalization rollback target failed") from exc
    control_after = _identity_observation_matches(
        control_api._capture_identity_observation(
            lambda: control_api._observe_control_identities(authority, file_observer),
            label="control identity observation after rollback",
        ),
        {
            "checkpoint": authority["control_target"]["checkpoint"],
            "configuration": authority["control_target"]["configuration"],
        },
        "terminalization control identity after rollback",
    )
    production_after = _identity_observation_matches(
        control_api._capture_identity_observation(
            lambda: control_api._observe_production_isolation(
                authority, file_observer, directory_observer
            ),
            label="production isolation observation after rollback",
        ),
        authority["production_isolation"],
        "terminalization production isolation after rollback",
    )
    after_binding = control_api._artifact_binding(relative, target)
    if after_binding != plan["control_target_after"]:
        raise TrainingRunnerBlocked("terminalization rollback target verification differs")
    classification = plan["classification"]
    body = {
        "candidate_enabled": False,
        "closeout_kind": classification["closeout_kind"],
        "control_identities_after": control_after,
        "control_identities_before": plan["control_identities_before"],
        "control_identities_verified": True,
        "control_target_after": after_binding,
        "control_target_before": before_binding,
        "control_target_verified": True,
        "downstream_authority": copy.deepcopy(
            dict(context.request["downstream_authority"])
        ),
        "failure_paths": copy.deepcopy(classification["failure_paths"]),
        "identity": control_api._context_identity(context),
        "outcome_class": classification["outcome_class"],
        "production_isolation_after": production_after,
        "production_isolation_before": plan["production_isolation_before"],
        "production_isolation_verified": True,
        "rollback_authority_sha256": authority["rollback_authority_sha256"],
        "rollback_required": classification["rollback_required"],
        "schema_version": control_api.ROLLBACK_OBSERVATION_SCHEMA_VERSION,
        "status": "rollback_verified",
        "trigger_class": classification["trigger_class"],
    }
    observation = {
        **body,
        "rollback_observation_sha256": canonical_json_sha256(body),
    }
    path = output / control_api.ROLLBACK_OBSERVATION_FILENAME
    if path.exists():
        try:
            stored = _parse_canonical_mapping(
                path.read_bytes(), "terminalization rollback observation"
            )
        except OSError as exc:
            raise TrainingRunnerBlocked("terminalization rollback is unreadable") from exc
        if stored != observation:
            raise TrainingRunnerBlocked("terminalization rollback observation differs")
    else:
        control_api.publish_managed_artifact(
            context,
            lease,
            relative_path=control_api.ROLLBACK_OBSERVATION_FILENAME,
            payload=canonical_json_bytes(observation),
        )
    return observation


def _publish_or_load_frozen_terminalization_intent(
    *,
    control_api: Any,
    context: Any,
    lease: Any,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    output = Path(context.request["output_root"]).resolve()
    path = output / control_api.TERMINAL_INTENT_FILENAME
    body = {
        "artifact_prefix": control_api._terminal_prefix_inventory(output),
        "details": copy.deepcopy(dict(details)),
        "downstream_authority": copy.deepcopy(
            dict(context.request["downstream_authority"])
        ),
        "identity": control_api._context_identity(context),
        "journal_prefix": control_api._journal_prefix_binding(context, lease),
        "resource_prefix": control_api._resource_prefix_binding(context, lease),
        "schema_version": control_api.TERMINAL_INTENT_SCHEMA_VERSION,
        "verdict": "training_process_failure_terminalized",
    }
    intent = {**body, "terminal_intent_sha256": canonical_json_sha256(body)}
    if path.exists():
        stored = _mapping(
            control_api._stored_terminal_intent(context, lease),
            "terminalization terminal intent",
        )
        if stored != intent:
            raise TrainingRunnerBlocked("terminalization terminal intent differs")
        return stored
    control_api._execution_context_for_operation(context, "terminal")
    control_api._require_terminal_publication_open(output)
    control_api._publish_bounded_artifact(
        output,
        relative_path=control_api.TERMINAL_INTENT_FILENAME,
        payload=canonical_json_bytes(intent),
    )
    return intent


def _load_expected_complete_terminalization_chain(
    *, control_api: Any, context: Any, lease: Any, intent: Mapping[str, Any]
) -> dict[str, Any]:
    output = Path(context.request["output_root"]).resolve()
    stored_intent = _mapping(
        control_api._stored_terminal_intent(context, lease, supplied=intent),
        "complete terminalization intent",
    )
    terminal = _mapping(
        control_api._stored_terminal_document(context, lease),
        "complete terminalization terminal",
    )
    try:
        manifest = _parse_canonical_mapping(
            (output / control_api.MANIFEST_FILENAME).read_bytes(),
            "complete terminalization manifest",
        )
    except OSError as exc:
        raise TrainingRunnerBlocked("complete terminalization manifest is unreadable") from exc
    expected_body = {
        "artifact_inventory": control_api._observe_artifact_inventory(
            output, excluded_paths=(control_api.MANIFEST_FILENAME,)
        ),
        "downstream_authority": copy.deepcopy(
            dict(context.request["downstream_authority"])
        ),
        "identity": control_api._context_identity(context),
        "schema_version": control_api.MANIFEST_SCHEMA_VERSION,
        "terminal_intent_sha256": terminal["terminal_intent_sha256"],
        "terminal_sha256": terminal["terminal_sha256"],
    }
    expected_manifest = {
        **expected_body,
        "manifest_sha256": canonical_json_sha256(expected_body),
    }
    if manifest != expected_manifest:
        raise TrainingRunnerBlocked("complete terminalization manifest differs")
    return {
        "artifact_manifest_sha256": manifest["manifest_sha256"],
        "terminal_intent_sha256": stored_intent["terminal_intent_sha256"],
        "terminal_sha256": terminal["terminal_sha256"],
        "verdict": terminal["verdict"],
    }


def _execute_dead_owner_terminalization(
    *,
    control_api: Any,
    context: Any,
    launch_manifest: Mapping[str, Any],
    command_envelope: Mapping[str, Any],
    authority: Mapping[str, Any],
    rollback_authority: Mapping[str, Any],
    process_id: int,
    process_alive: Callable[[int], bool],
    clock: Callable[[], float],
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None = None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
) -> dict[str, Any]:
    """Close one exact dead-owner prefix without empirical access or replay."""
    callbacks = (process_alive, clock)
    if not all(callable(callback) for callback in callbacks):
        raise TrainingRunnerBlocked("terminalization callback is invalid")
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0:
        raise TrainingRunnerBlocked("terminalization process identity is invalid")
    manifest = validate_launch_manifest(launch_manifest)
    envelope = validate_command_envelope(command_envelope, manifest)
    normalized_authority = _mapping(authority, "terminalization authority")
    if (
        envelope["command"] != "terminalize-dead-owner"
        or normalized_authority.get("validated") is not True
        or normalized_authority.get("command") != "terminalize-dead-owner"
        or normalized_authority.get("envelope_sha256")
        != envelope["envelope_sha256"]
        or normalized_authority.get("composite_sha256")
        != envelope["composite"]["composite_sha256"]
    ):
        raise TrainingRunnerBlocked("terminalization command authority differs")
    binding = envelope["terminalization_binding"]
    rollback = _validate_rollback_authority(rollback_authority)
    if rollback != manifest["rollback_authority"]:
        raise TrainingRunnerBlocked("terminalization rollback authority changed")
    try:
        normalized_failure_paths = control_api.classify_terminal_closeout(
            failure_paths=binding["failure_paths"]
        )["failure_paths"]
    except Exception as exc:
        raise TrainingRunnerBlocked("terminalization failure paths differ") from exc
    if normalized_failure_paths != binding["failure_paths"]:
        raise TrainingRunnerBlocked("terminalization failure paths are not canonical")
    output = Path(manifest["output_root"]).resolve()
    run_composite = build_runner_composite(manifest, "run-training")
    runner_authority_identity = {
        "composite_sha256": run_composite["composite_sha256"],
        "launch_manifest_sha256": manifest["manifest_sha256"],
        "rollback_authority_sha256": rollback["rollback_authority_sha256"],
        "run_envelope_sha256": binding["run_envelope_sha256"],
    }
    closure_path = output / TERMINALIZATION_CLOSURE_FILENAME

    with _hold_terminalization_guard(control_api=control_api, manifest=manifest):
        if closure_path.exists():
            try:
                closure_payload = closure_path.read_bytes()
            except OSError as exc:
                raise TrainingRunnerBlocked(
                    "terminalization closure marker is unreadable"
                ) from exc
            closure = _parse_terminalization_closure(
                closure_payload,
                manifest_sha256=manifest["manifest_sha256"],
                terminalization_envelope_sha256=envelope["envelope_sha256"],
                rollback_authority=rollback,
                run_envelope_sha256=binding["run_envelope_sha256"],
            )
            prefix = closure["failure_prefix"]
            if (
                prefix["owner"] != binding["owner"]
                or prefix["lease_sha256"] != binding["lease_sha256"]
                or prefix["prefix_sha256"] != binding["prefix_sha256"]
                or closure["failure_paths"] != binding["failure_paths"]
            ):
                raise TrainingRunnerBlocked("terminalization closure binding differs")
        else:
            prefix = _terminalization_failure_prefix(
                control_api=control_api,
                context=context,
                output_root=output,
                runner_authority_identity=runner_authority_identity,
                process_alive=process_alive,
            )
            if (
                prefix["owner"] != binding["owner"]
                or prefix["lease_sha256"] != binding["lease_sha256"]
                or prefix["prefix_sha256"] != binding["prefix_sha256"]
            ):
                raise TrainingRunnerBlocked("terminalization failure prefix differs")
            rollback_plan = _build_terminalization_rollback_plan(
                control_api=control_api,
                context=context,
                output_root=output,
                rollback_authority=rollback,
                failure_paths=binding["failure_paths"],
                external_binding_observer=external_binding_observer,
                checkpoint_snapshot_observer=checkpoint_snapshot_observer,
            )
            closure = _terminalization_closure_document(
                manifest_sha256=manifest["manifest_sha256"],
                terminalization_envelope_sha256=envelope["envelope_sha256"],
                failure_prefix=prefix,
                failure_paths=binding["failure_paths"],
                rollback_plan=rollback_plan,
                run_envelope_sha256=binding["run_envelope_sha256"],
            )
            closure_payload = canonical_json_bytes(closure)

        state = (
            _terminalization_resume_state(
                control_api=control_api,
                context=context,
                output_root=output,
                closure=closure,
                closure_payload=closure_payload,
                rollback_authority=rollback,
            )
            if closure_path.exists()
            else None
        )
        current_lease = _current_dead_terminalization_lease(
            control_api=control_api,
            context=context,
            output_root=output,
            process_alive=process_alive,
        )
        if (
            current_lease["owner"] != binding["owner"]
            or current_lease["lease_sha256"] != binding["lease_sha256"]
        ):
            raise TrainingRunnerBlocked("terminalization lease changed before reclaim")

        lease_handle = _hold_exact_dead_owner_execution_lease(
            control_api=control_api,
            context=context,
            output_root=output,
            expected_owner=current_lease["owner"],
            expected_lease_sha256=binding["lease_sha256"],
            process_id=process_id,
            process_alive=process_alive,
            clock=clock,
        )
        try:
            with lease_handle as lease:
                if lease.reclaimed_owner != current_lease["owner"]:
                    raise TrainingRunnerBlocked(
                        "terminalization lease reclamation proof differs"
                    )
                if closure_path.exists():
                    state = _terminalization_resume_state(
                        control_api=control_api,
                        context=context,
                        output_root=output,
                        closure=closure,
                        closure_payload=closure_payload,
                        rollback_authority=rollback,
                    )
                else:
                    locked_prefix = _terminalization_failure_prefix(
                        control_api=control_api,
                        context=context,
                        output_root=output,
                        runner_authority_identity=runner_authority_identity,
                        process_alive=process_alive,
                        lease_payload_override=current_lease["payload"],
                        held_lease=lease,
                    )
                    if locked_prefix != prefix:
                        raise TrainingRunnerBlocked(
                            "terminalization failure prefix changed under lease"
                        )
                    locked_plan = _build_terminalization_rollback_plan(
                        control_api=control_api,
                        context=context,
                        output_root=output,
                        rollback_authority=rollback,
                        failure_paths=binding["failure_paths"],
                        external_binding_observer=external_binding_observer,
                        checkpoint_snapshot_observer=checkpoint_snapshot_observer,
                    )
                    if locked_plan != closure["rollback_plan"]:
                        raise TrainingRunnerBlocked(
                            "terminalization rollback plan changed under lease"
                        )
                if not closure_path.exists():
                    control_api.publish_managed_artifact(
                        context,
                        lease,
                        relative_path=TERMINALIZATION_CLOSURE_FILENAME,
                        payload=closure_payload,
                    )
                rollback_observation = _execute_or_resume_terminalization_rollback(
                    control_api=control_api,
                    context=context,
                    lease=lease,
                    rollback_authority=rollback,
                    rollback_plan=closure["rollback_plan"],
                    external_binding_observer=external_binding_observer,
                    checkpoint_snapshot_observer=checkpoint_snapshot_observer,
                )
                details = {
                    "closure_sha256": closure["closure_sha256"],
                    "failure_paths": copy.deepcopy(binding["failure_paths"]),
                    "original_lease_sha256": binding["lease_sha256"],
                    "original_owner": copy.deepcopy(binding["owner"]),
                    "original_prefix_sha256": binding["prefix_sha256"],
                    "rollback_observation_sha256": rollback_observation[
                        "rollback_observation_sha256"
                    ],
                    "run_envelope_sha256": binding["run_envelope_sha256"],
                    "terminalization_envelope_sha256": envelope["envelope_sha256"],
                }
                intent = _publish_or_load_frozen_terminalization_intent(
                    control_api=control_api,
                    context=context,
                    lease=lease,
                    details=details,
                )
                if state is not None and state["complete"]:
                    return _load_expected_complete_terminalization_chain(
                        control_api=control_api,
                        context=context,
                        lease=lease,
                        intent=intent,
                    )
                terminal = _mapping(
                    control_api.publish_terminal_document(
                        context, lease, terminal_intent=intent
                    ),
                    "terminalization terminal document",
                )
                artifact_manifest = _mapping(
                    control_api.publish_artifact_manifest(
                        context, lease, terminal_document=terminal
                    ),
                    "terminalization artifact manifest",
                )
                return {
                    "artifact_manifest_sha256": artifact_manifest["manifest_sha256"],
                    "terminal_intent_sha256": intent["terminal_intent_sha256"],
                    "terminal_sha256": terminal["terminal_sha256"],
                    "verdict": terminal["verdict"],
                }
        except TrainingRunnerBlocked:
            raise
        except Exception as exc:
            raise TrainingRunnerBlocked("dead-owner terminalization failed") from exc


def _validated_reopen_observation(
    value: Mapping[str, Any],
    *,
    expected_context_identity: Mapping[str, Any],
    expected_runner_authority_identity: Mapping[str, Any],
    process_alive: Callable[[int], bool],
) -> dict[str, Any]:
    observation = _mapping(value, "read-only training reopen observation")
    _fields(
        observation,
        {"classification", "recovery", "runner_authority_identity"},
        "read-only training reopen observation",
    )
    classification = _mapping(
        observation["classification"], "read-only reopen classification"
    )
    recovery = _mapping(observation["recovery"], "read-only reopen recovery")
    context_identity = _mapping(
        expected_context_identity, "expected reopen context identity"
    )
    runner_authority_identity = _validated_runner_authority_identity(
        expected_runner_authority_identity
    )
    if observation["runner_authority_identity"] != runner_authority_identity:
        raise TrainingRunnerBlocked("read-only reopen runner authority differs")
    verdict = classification.get("verdict")
    if verdict == "pre_seed_setup_reopen":
        _fields(
            classification,
            {"debited_accesses", "identity", "verdict"},
            "read-only setup reopen classification",
        )
        if classification["debited_accesses"] != 0:
            raise TrainingRunnerBlocked("read-only setup reopen prefix differs")
    elif verdict == "complete_checkpoint_continuation":
        _fields(
            classification,
            {
                "checkpoint_sha256",
                "completed_pairs",
                "debited_accesses",
                "identity",
                "next_chunk_index",
                "verdict",
            },
            "read-only continuation classification",
        )
        _digest(
            classification["checkpoint_sha256"],
            "read-only continuation checkpoint",
        )
        index = classification["next_chunk_index"]
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or not 1 <= index < 8
            or classification["completed_pairs"] != index * 64
            or classification["debited_accesses"] != index * 128
        ):
            raise TrainingRunnerBlocked("read-only continuation index differs")
    else:
        raise TrainingRunnerBlocked("read-only training reopen verdict differs")
    if classification["identity"] != context_identity:
        raise TrainingRunnerBlocked("read-only reopen context identity differs")

    mode = recovery.get("mode")
    if mode == "fresh_output":
        _fields(recovery, {"mode"}, "fresh output recovery")
        if verdict != "pre_seed_setup_reopen":
            raise TrainingRunnerBlocked("continuation cannot use fresh output")
    elif mode == "dead_owner_reclaim":
        _fields(
            recovery,
            {
                "artifact_inventory",
                "lease_sha256",
                "mode",
                "old_owner",
                "prefix_sha256",
                "runner_launch",
            },
            "dead owner recovery",
        )
        _digest(recovery["lease_sha256"], "dead owner lease")
        prefix_sha256 = _digest(recovery["prefix_sha256"], "dead owner prefix")
        artifact_inventory = _validated_artifact_inventory(
            recovery["artifact_inventory"]
        )
        old_owner = _mapping(recovery["old_owner"], "dead lease owner")
        runner_launch = _mapping(
            recovery["runner_launch"], "dead owner runner launch"
        )
        launch_state = runner_launch.get("state")
        if launch_state == "absent":
            _fields(runner_launch, {"state"}, "absent runner launch")
            if verdict == "complete_checkpoint_continuation":
                raise TrainingRunnerBlocked(
                    "continuation lacks an original runner launch"
                )
        elif launch_state == "present":
            _fields(
                runner_launch,
                {"sha256", "state"},
                "present runner launch",
            )
            _digest(runner_launch["sha256"], "dead owner runner launch")
        else:
            raise TrainingRunnerBlocked("dead owner runner launch state differs")
        _fields(
            old_owner,
            {"acquired_monotonic", "child_process_id", "token"},
            "dead lease owner",
        )
        old_process_id = old_owner.get("child_process_id")
        acquired_monotonic = old_owner.get("acquired_monotonic")
        if (
            isinstance(old_process_id, bool)
            or not isinstance(old_process_id, int)
            or old_process_id <= 0
            or isinstance(acquired_monotonic, bool)
            or not isinstance(acquired_monotonic, (int, float))
            or not math.isfinite(float(acquired_monotonic))
            or acquired_monotonic < 0
            or not isinstance(old_owner.get("token"), str)
            or re.fullmatch(r"[0-9a-f]{32}", old_owner["token"]) is None
        ):
            raise TrainingRunnerBlocked("dead lease owner identity differs")
        expected_prefix_sha256 = canonical_json_sha256(
            {
                "artifact_inventory": artifact_inventory,
                "classification": classification,
                "context_identity": context_identity,
                "runner_authority_identity": runner_authority_identity,
            }
        )
        if prefix_sha256 != expected_prefix_sha256:
            raise TrainingRunnerBlocked("dead owner prefix identity differs")
        launch_rows = [
            row
            for row in artifact_inventory["artifacts"]
            if isinstance(row, Mapping) and row.get("path") == "runner_launch.json"
        ]
        if (
            (launch_state == "absent" and launch_rows)
            or (launch_state == "present" and len(launch_rows) != 1)
            or (
                launch_state == "present"
                and launch_rows[0].get("stored_sha256") != runner_launch["sha256"]
            )
        ):
            raise TrainingRunnerBlocked("dead owner runner launch inventory differs")
        try:
            old_owner_alive = process_alive(old_process_id)
        except Exception as exc:
            raise TrainingRunnerBlocked("dead lease owner liveness failed") from exc
        if old_owner_alive is not False:
            raise TrainingRunnerBlocked("observed lease owner is not dead")
    else:
        raise TrainingRunnerBlocked("read-only reopen recovery mode differs")
    return {
        "classification": copy.deepcopy(classification),
        "recovery": copy.deepcopy(recovery),
        "runner_authority_identity": copy.deepcopy(runner_authority_identity),
    }


def _validated_lease_owner(value: object, label: str) -> dict[str, Any]:
    owner = _mapping(value, label)
    _fields(
        owner,
        {"acquired_monotonic", "child_process_id", "token"},
        label,
    )
    acquired_monotonic = owner["acquired_monotonic"]
    process_id = owner["child_process_id"]
    if (
        isinstance(acquired_monotonic, bool)
        or not isinstance(acquired_monotonic, (int, float))
        or not math.isfinite(float(acquired_monotonic))
        or acquired_monotonic < 0
        or isinstance(process_id, bool)
        or not isinstance(process_id, int)
        or process_id <= 0
        or not isinstance(owner["token"], str)
        or re.fullmatch(r"[0-9a-f]{32}", owner["token"]) is None
    ):
        raise TrainingRunnerBlocked(f"{label} identity differs")
    return owner


def _observe_training_reopen_read_only(
    *,
    control_api: Any,
    context: Any,
    output_root: Path | str,
    runner_authority_identity: Mapping[str, Any],
    process_alive: Callable[[int], bool],
    observed_lease_payload: bytes | None = None,
) -> dict[str, Any]:
    """Classify a bounded lifecycle prefix without acquiring or changing it."""
    if not callable(process_alive):
        raise TrainingRunnerBlocked("read-only reopen liveness observer is invalid")
    output = Path(output_root).resolve()
    normalized_runner_authority = _validated_runner_authority_identity(
        runner_authority_identity
    )
    guard_path = output.parent / f".{output.name}.execution.guard"
    if guard_path.exists():
        try:
            guard_payload = guard_path.read_bytes()
        except OSError as exc:
            raise TrainingRunnerBlocked("runner authority guard is unreadable") from exc
        expected_guard_payload = _runner_authority_guard_payload(
            normalized_runner_authority
        )
        if guard_payload != expected_guard_payload:
            raise TrainingRunnerBlocked("runner authority guard differs")
    elif output.exists():
        raise TrainingRunnerBlocked("existing output lacks runner authority guard")
    try:
        context_identity = _mapping(
            control_api._context_identity(context),
            "read-only reopen context identity",
        )
    except Exception as exc:
        raise TrainingRunnerBlocked("read-only reopen context is invalid") from exc
    if not output.exists():
        if observed_lease_payload is not None:
            raise TrainingRunnerBlocked("absent output has observed lease bytes")
        return {
            "classification": {
                "debited_accesses": 0,
                "identity": copy.deepcopy(context_identity),
                "verdict": "pre_seed_setup_reopen",
            },
            "recovery": {"mode": "fresh_output"},
            "runner_authority_identity": copy.deepcopy(
                normalized_runner_authority
            ),
        }
    if not output.is_dir():
        raise TrainingRunnerBlocked("training output root is not a directory")
    lease_path = output / control_api.LEASE_FILENAME
    if observed_lease_payload is None:
        try:
            lease_payload = lease_path.read_bytes()
        except OSError as exc:
            raise TrainingRunnerBlocked("existing output lacks a readable lease") from exc
    elif isinstance(observed_lease_payload, bytes):
        lease_payload = observed_lease_payload
    else:
        raise TrainingRunnerBlocked("observed execution lease bytes are invalid")
    lease_record = _parse_canonical_mapping(lease_payload, "observed execution lease")
    _fields(
        lease_record,
        {"identity", "owner", "reclaimed_owner", "schema_version"},
        "observed execution lease",
    )
    old_owner = _validated_lease_owner(
        lease_record["owner"], "observed execution lease owner"
    )
    prior_reclaimed_owner = lease_record["reclaimed_owner"]
    if prior_reclaimed_owner is not None:
        _validated_lease_owner(
            prior_reclaimed_owner, "observed prior reclaimed lease owner"
        )
    if (
        lease_record["schema_version"] != control_api.LEASE_SCHEMA_VERSION
        or lease_record["identity"] != context_identity
    ):
        raise TrainingRunnerBlocked("observed execution lease identity differs")
    try:
        owner_alive = process_alive(old_owner["child_process_id"])
    except Exception as exc:
        raise TrainingRunnerBlocked("observed lease owner liveness failed") from exc
    if owner_alive is not False:
        raise TrainingRunnerBlocked("observed execution lease owner is not dead")

    try:
        probe = control_api.ExecutionLease(
            output,
            context=context,
            child_process_id=old_owner["child_process_id"],
            process_alive=process_alive,
        )
        probe.held = True
        try:
            classification = _mapping(
                control_api.classify_execution_reopen(context, probe),
                "read-only control reopen classification",
            )
        finally:
            probe.held = False
        artifact_inventory = _mapping(
            control_api._observe_artifact_inventory(
                output, excluded_paths=()
            ),
            "read-only managed artifact inventory",
        )
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("read-only training reopen failed") from exc
    launch_rows = [
        row
        for row in artifact_inventory.get("artifacts", ())
        if isinstance(row, Mapping) and row.get("path") == "runner_launch.json"
    ]
    if len(launch_rows) > 1:
        raise TrainingRunnerBlocked("runner launch inventory is ambiguous")
    runner_launch = (
        {"sha256": launch_rows[0]["stored_sha256"], "state": "present"}
        if launch_rows
        else {"state": "absent"}
    )
    prefix_body = {
        "artifact_inventory": artifact_inventory,
        "classification": classification,
        "context_identity": context_identity,
        "runner_authority_identity": normalized_runner_authority,
    }
    return _validated_reopen_observation(
        {
            "classification": classification,
            "recovery": {
                "artifact_inventory": artifact_inventory,
                "lease_sha256": hashlib.sha256(lease_payload).hexdigest(),
                "mode": "dead_owner_reclaim",
                "old_owner": old_owner,
                "prefix_sha256": canonical_json_sha256(prefix_body),
                "runner_launch": runner_launch,
            },
            "runner_authority_identity": normalized_runner_authority,
        },
        expected_context_identity=context_identity,
        expected_runner_authority_identity=normalized_runner_authority,
        process_alive=process_alive,
    )


class _AtomicObservedExecutionLease:
    """Commit a fully prepared lease while holding one output-sibling guard."""

    def __init__(
        self,
        *,
        control_api: Any,
        context: Any,
        output_root: Path | str,
        observation: Mapping[str, Any],
        child_process_id: int,
        process_alive: Callable[[int], bool],
        clock: Callable[[], float],
    ) -> None:
        self.control_api = control_api
        self.context = context
        self.output = Path(output_root).resolve()
        self.observation = copy.deepcopy(dict(observation))
        self.child_process_id = child_process_id
        self.process_alive = process_alive
        self.clock = clock
        self.lease: Any | None = None
        self._active_key: str | None = None
        self._committed_payload: bytes | None = None
        self._guard_handle: Any | None = None

    @property
    def guard_path(self) -> Path:
        return self.output.parent / f".{self.output.name}.execution.guard"

    @property
    def guard_lock_path(self) -> Path:
        return self.output.parent / f".{self.output.name}.execution.guard.lock"

    @staticmethod
    def _cleanup_stage(path: Path) -> None:
        try:
            if path.is_dir():
                children = list(path.iterdir())
                if len(children) == 1 and children[0].is_file():
                    children[0].unlink()
                path.rmdir()
            elif path.exists():
                path.unlink()
        except OSError:
            pass

    def __enter__(self) -> Any:
        control = self.control_api
        observation = self.observation
        runner_authority_identity = _validated_runner_authority_identity(
            observation.get("runner_authority_identity")
        )
        guard_payload = _runner_authority_guard_payload(
            runner_authority_identity
        )
        recovery = _mapping(observation.get("recovery"), "atomic lease recovery")
        mode = recovery.get("mode")
        if mode not in {"fresh_output", "dead_owner_reclaim"}:
            raise TrainingRunnerBlocked("atomic lease recovery mode differs")
        try:
            if self.process_alive(self.child_process_id) is not True:
                raise TrainingRunnerBlocked("atomic lease child is not alive")
        except TrainingRunnerBlocked:
            raise
        except Exception as exc:
            raise TrainingRunnerBlocked("atomic lease child liveness failed") from exc
        started = float(self.clock())
        if not math.isfinite(started) or started < 0.0:
            raise TrainingRunnerBlocked("atomic lease clock is invalid")
        owner = {
            "acquired_monotonic": started,
            "child_process_id": self.child_process_id,
            "token": uuid.uuid4().hex,
        }
        lease = control.ExecutionLease(
            self.output,
            context=self.context,
            child_process_id=self.child_process_id,
            process_alive=self.process_alive,
            allow_stale_reclaim=mode == "dead_owner_reclaim",
            clock=self.clock,
        )
        key = os.path.normcase(str(lease.path))
        if key in control._ACTIVE_EXECUTION_LEASES:
            raise TrainingRunnerBlocked("atomic execution lease is already held")
        guard_handle = None
        locked = False
        stage_path: Path | None = None
        state_prepared = False
        try:
            self.guard_lock_path.parent.mkdir(parents=True, exist_ok=True)
            guard_handle = self.guard_lock_path.open("a+b", buffering=0)
            guard_handle.seek(0, os.SEEK_END)
            if guard_handle.tell() == 0:
                guard_handle.write(b"\0")
                guard_handle.flush()
                os.fsync(guard_handle.fileno())
            control._lock_file(guard_handle)
            locked = True
            if self.guard_path.exists():
                try:
                    observed_guard_payload = self.guard_path.read_bytes()
                except OSError as exc:
                    raise TrainingRunnerBlocked(
                        "atomic runner authority guard is unreadable"
                    ) from exc
                if observed_guard_payload != guard_payload:
                    raise TrainingRunnerBlocked(
                        "atomic runner authority guard differs"
                    )
            else:
                if self.output.exists():
                    raise TrainingRunnerBlocked(
                        "existing output lacks atomic runner authority guard"
                    )
                guard_stage_path = self.output.parent / (
                    f".{self.output.name}.execution.guard.{uuid.uuid4().hex}.staging"
                )
                try:
                    with guard_stage_path.open("xb") as guard_stage:
                        guard_stage.write(guard_payload)
                        guard_stage.flush()
                        os.fsync(guard_stage.fileno())
                    _move_path_write_through(guard_stage_path, self.guard_path)
                except Exception:
                    self._cleanup_stage(guard_stage_path)
                    raise
            reclaimed_owner = None
            if mode == "fresh_output":
                if self.output.exists():
                    raise TrainingRunnerBlocked("fresh atomic output changed")
            else:
                if not self.output.is_dir() or not lease.path.is_file():
                    raise TrainingRunnerBlocked("stale output lease is unavailable")
                prior_payload = lease.path.read_bytes()
                if hashlib.sha256(prior_payload).hexdigest() != recovery["lease_sha256"]:
                    raise TrainingRunnerBlocked("atomic lease bytes changed")
                observed_under_lock = _observe_training_reopen_read_only(
                    control_api=control,
                    context=self.context,
                    output_root=self.output,
                    runner_authority_identity=runner_authority_identity,
                    process_alive=self.process_alive,
                    observed_lease_payload=prior_payload,
                )
                if observed_under_lock != observation:
                    raise TrainingRunnerBlocked("atomic reopen prefix changed")
                prior_lease = _parse_canonical_mapping(
                    prior_payload, "atomic prior execution lease"
                )
                reclaimed_owner = _validated_lease_owner(
                    prior_lease["owner"], "atomic prior execution lease owner"
                )
            payload = {
                "identity": control._context_identity(self.context),
                "owner": owner,
                "reclaimed_owner": reclaimed_owner,
                "schema_version": control.LEASE_SCHEMA_VERSION,
            }
            encoded_payload = canonical_json_bytes(payload)
            if mode == "fresh_output":
                stage_path = self.output.parent / (
                    f".{self.output.name}.{uuid.uuid4().hex}.staging"
                )
                stage_path.mkdir(parents=False, exist_ok=False)
                staged_lease = stage_path / control.LEASE_FILENAME
            else:
                stage_path = self.output.parent / (
                    f".{self.output.name}.lease.{uuid.uuid4().hex}.staging"
                )
                staged_lease = stage_path
            with staged_lease.open("xb") as staged_handle:
                staged_handle.write(encoded_payload)
                staged_handle.flush()
                os.fsync(staged_handle.fileno())
            lease.owner = owner
            lease.reclaimed_owner = reclaimed_owner
            lease.started_monotonic = started
            lease.held = True
            lease.acquisition_mode = mode
            lease.acquisition_observation_sha256 = canonical_json_sha256(observation)
            lease.reclaimed_lease_sha256 = recovery.get("lease_sha256")
            lease.reclaimed_prefix_sha256 = recovery.get("prefix_sha256")
            control._ACTIVE_EXECUTION_LEASES.add(key)
            self.lease = lease
            self._active_key = key
            self._committed_payload = encoded_payload
            self._guard_handle = guard_handle
            state_prepared = True
            try:
                if mode == "fresh_output":
                    _move_path_write_through(stage_path, self.output)
                else:
                    _move_path_write_through(stage_path, lease.path, replace=True)
                return lease
            except Exception:
                lease.held = False
                control._ACTIVE_EXECUTION_LEASES.discard(key)
                self.lease = None
                self._active_key = None
                self._committed_payload = None
                self._guard_handle = None
                state_prepared = False
                raise
        except Exception as exc:
            if state_prepared:
                lease.held = False
                control._ACTIVE_EXECUTION_LEASES.discard(key)
                self.lease = None
                self._active_key = None
                self._committed_payload = None
                self._guard_handle = None
            if stage_path is not None:
                self._cleanup_stage(stage_path)
            if locked and guard_handle is not None:
                try:
                    control._unlock_file(guard_handle)
                except OSError:
                    pass
            if guard_handle is not None:
                guard_handle.close()
            if isinstance(exc, TrainingRunnerBlocked):
                raise
            raise TrainingRunnerBlocked("atomic execution lease failed") from exc

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> Any:
        lease = self.lease
        guard_handle = self._guard_handle
        if lease is None or guard_handle is None:
            return False
        control = self.control_api
        drifted = False
        try:
            try:
                drifted = lease.path.read_bytes() != self._committed_payload
            except OSError:
                drifted = True
            lease.held = False
            if self._active_key is not None:
                control._ACTIVE_EXECUTION_LEASES.discard(self._active_key)
        finally:
            try:
                control._unlock_file(guard_handle)
            finally:
                guard_handle.close()
                self._guard_handle = None
        if drifted:
            raise TrainingRunnerBlocked("atomic execution lease drifted")
        return False


def _execute_training_lifecycle(
    *,
    control_api: Any,
    registered_inputs_loader: Callable[[], Mapping[str, Any]],
    context_builder: Callable[
        [Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], Any
    ],
    context_identity_observer: Callable[[Any], Mapping[str, Any]],
    reopen_observer: Callable[
        [Path, Any, Callable[[int], bool]], Mapping[str, Any]
    ],
    lease_factory: Callable[
        [
            Path,
            Any,
            Mapping[str, Any],
            int,
            Callable[[int], bool],
            Callable[[], float],
        ],
        Any,
    ],
    runtime_loader: Callable[[], Any],
    environment_factory_loader: Callable[[], Callable[[int], Any]],
    checkpoint_reader: Callable[[Path], bytes],
    launch_marker_reader: Callable[[Path], bytes],
    output_root: Path | str,
    manifest_sha256: str,
    run_envelope_sha256: str,
    rollback_authority_sha256: str,
    process_id: int,
    process_alive: Callable[[int], bool],
    deadline: float,
    clock: Callable[[], float],
    closeout: Callable[..., Any],
) -> dict[str, Any]:
    """Own one authorized lease and lazily compose setup or exact continuation."""
    callbacks = (
        registered_inputs_loader,
        context_builder,
        context_identity_observer,
        reopen_observer,
        lease_factory,
        runtime_loader,
        environment_factory_loader,
        checkpoint_reader,
        launch_marker_reader,
        process_alive,
        clock,
        closeout,
    )
    if not all(callable(callback) for callback in callbacks):
        raise TrainingRunnerBlocked("training lifecycle callback is invalid")
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0:
        raise TrainingRunnerBlocked("training lifecycle process identity is invalid")
    output = Path(
        _absolute_path(
            Path(output_root).resolve().as_posix(), "training lifecycle output"
        )
    )
    manifest_digest = _digest(manifest_sha256, "training launch manifest")
    envelope_digest = _digest(run_envelope_sha256, "training run envelope")
    rollback_digest = _digest(
        rollback_authority_sha256, "training rollback authority"
    )

    registered = _mapping(
        registered_inputs_loader(), "registered training lifecycle inputs"
    )
    authority = _mapping(registered.get("authority"), "registered runner authority")
    execution_registration = _mapping(
        registered.get("execution_registration"), "execution registration view"
    )
    original_registration = _mapping(
        registered.get("registration"), "original registration view"
    )
    training_seeds = registered.get("training_seeds")
    if (
        authority.get("validated") is not True
        or authority.get("command") != "run-training"
        or authority.get("envelope_sha256") != envelope_digest
        or execution_registration.get("rollback_authority_sha256")
        != rollback_digest
        or "rollback_authority_sha256" in original_registration
        or execution_registration
        != {
            **copy.deepcopy(original_registration),
            "rollback_authority_sha256": rollback_digest,
        }
        or not isinstance(training_seeds, tuple)
        or len(training_seeds) != 512
        or training_seeds != tuple(sorted(set(training_seeds)))
    ):
        raise TrainingRunnerBlocked("registered training lifecycle inputs differ")
    context = context_builder(
        copy.deepcopy(execution_registration),
        copy.deepcopy(original_registration),
        copy.deepcopy(authority),
    )
    expected_context_identity = _mapping(
        context_identity_observer(context), "training lifecycle context identity"
    )
    runner_authority_identity = _validated_runner_authority_identity(
        {
            "composite_sha256": authority["composite_sha256"],
            "launch_manifest_sha256": manifest_digest,
            "rollback_authority_sha256": rollback_digest,
            "run_envelope_sha256": envelope_digest,
        }
    )
    observed_reopen = _validated_reopen_observation(
        reopen_observer(output, context, process_alive),
        expected_context_identity=expected_context_identity,
        expected_runner_authority_identity=runner_authority_identity,
        process_alive=process_alive,
    )
    observed_classification = observed_reopen["classification"]
    observed_reopen_sha256 = canonical_json_sha256(observed_reopen)
    verdict = observed_classification["verdict"]
    recovery = observed_reopen["recovery"]
    observed_launch = recovery.get("runner_launch")
    if observed_launch is not None and observed_launch["state"] == "present":
        original_launch_payload = launch_marker_reader(output / "runner_launch.json")
        if (
            not isinstance(original_launch_payload, bytes)
            or hashlib.sha256(original_launch_payload).hexdigest()
            != observed_launch["sha256"]
        ):
            raise TrainingRunnerBlocked("observed runner launch binding differs")
        original_launch = _validated_original_runner_launch(
            original_launch_payload,
            manifest_sha256=manifest_digest,
            rollback_authority_sha256=rollback_digest,
            run_envelope_sha256=envelope_digest,
        )
    else:
        original_launch = None
    lease_handle = lease_factory(
        output,
        context,
        copy.deepcopy(observed_reopen),
        process_id,
        process_alive,
        clock,
    )
    with lease_handle as lease:
        if (
            getattr(lease, "acquisition_mode", None) != recovery["mode"]
            or getattr(lease, "acquisition_observation_sha256", None)
            != observed_reopen_sha256
        ):
            raise TrainingRunnerBlocked(
                "training lease compare-and-acquire proof differs"
            )
        current_owner = _validated_lease_owner(
            getattr(lease, "owner", None), "current training lease owner"
        )
        if current_owner["child_process_id"] != process_id:
            raise TrainingRunnerBlocked("current training lease owner differs")
        if recovery["mode"] == "dead_owner_reclaim":
            if (
                getattr(lease, "reclaimed_owner", None) != recovery["old_owner"]
                or getattr(lease, "reclaimed_lease_sha256", None)
                != recovery["lease_sha256"]
                or getattr(lease, "reclaimed_prefix_sha256", None)
                != recovery["prefix_sha256"]
            ):
                raise TrainingRunnerBlocked("training lease recovery proof differs")
        else:
            if any(
                getattr(lease, name, None) is not None
                for name in (
                    "reclaimed_owner",
                    "reclaimed_lease_sha256",
                    "reclaimed_prefix_sha256",
                )
            ):
                raise TrainingRunnerBlocked("fresh training lease reclaimed evidence")
            control_api.initialize_access_journal(context, lease)
            control_api.initialize_resource_ledger(context, lease)
        reopen = _mapping(
            control_api.classify_execution_reopen(context, lease),
            "training lifecycle reopen",
        )
        if reopen != observed_classification:
            raise TrainingRunnerBlocked("training lifecycle reopen changed after lease")
        if recovery["mode"] == "dead_owner_reclaim":
            control_api.initialize_access_journal(context, lease)
            control_api.initialize_resource_ledger(context, lease)
        if verdict == "complete_checkpoint_continuation":
            continuation = _mapping(
                control_api.authorize_training_continuation(context, lease),
                "training continuation authorization",
            )
            if any(
                continuation.get(name) != expected
                for name, expected in observed_classification.items()
            ):
                raise TrainingRunnerBlocked(
                    "training continuation authorization differs"
                )
        else:
            continuation = None

        if verdict == "pre_seed_setup_reopen" and original_launch is None:
            control_api.publish_managed_artifact(
                context,
                lease,
                relative_path="runner_launch.json",
                payload=_runner_launch_payload(
                    manifest_sha256=manifest_digest,
                    process_id=process_id,
                    rollback_authority_sha256=rollback_digest,
                    run_envelope_sha256=envelope_digest,
                ),
            )
        else:
            attempt_body = {
                "current_owner": copy.deepcopy(current_owner),
                "launch_manifest_sha256": manifest_digest,
                "original_launch_sha256": original_launch["launch_sha256"],
                "prior_lease_sha256": recovery["lease_sha256"],
                "prior_owner": copy.deepcopy(recovery["old_owner"]),
                "prior_prefix_sha256": recovery["prefix_sha256"],
                "rollback_authority_sha256": rollback_digest,
                "run_envelope_sha256": envelope_digest,
                "verdict": verdict,
            }
            if continuation is None:
                attempt_body["schema_version"] = REOPEN_ATTEMPT_SCHEMA_VERSION
                attempt_directory = "reopen_attempts"
            else:
                attempt_body.update(
                    {
                        "checkpoint_sha256": continuation["checkpoint_sha256"],
                        "continuation_authorization_sha256": canonical_json_sha256(
                            continuation
                        ),
                        "next_chunk_index": continuation["next_chunk_index"],
                        "schema_version": CONTINUATION_ATTEMPT_SCHEMA_VERSION,
                    }
                )
                attempt_directory = "continuation_attempts"
            attempt = {
                **attempt_body,
                "attempt_sha256": canonical_json_sha256(attempt_body),
            }
            control_api.publish_managed_artifact(
                context,
                lease,
                relative_path=(
                    f"{attempt_directory}/{attempt['attempt_sha256']}.json"
                ),
                payload=canonical_json_bytes(attempt),
            )
        runtime_api = runtime_loader()
        if verdict == "pre_seed_setup_reopen":
            runtime_state = runtime_api.initialize_paired_training_runtime()
            initial_checkpoint = runtime_api.encode_paired_training_checkpoint(
                runtime_state
            )
            initial_snapshot = _checkpoint_snapshot(initial_checkpoint)
            if initial_snapshot["coordinates"]["next_chunk_index"] != 0:
                raise TrainingRunnerBlocked("training setup is not zero progress")
            control_api.publish_write_once_marker(
                context,
                lease,
                kind="bootstrap",
                payload={
                    "checkpoint_sha256": initial_snapshot["checkpoint_sha256"],
                    "component_sha256": initial_snapshot["component_sha256"],
                },
            )
            control_api.publish_write_once_marker(
                context,
                lease,
                kind="stage",
                payload={"stage": "training", "status": "started"},
            )
        else:
            index = continuation["next_chunk_index"]
            if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index < 8:
                raise TrainingRunnerBlocked("training continuation index differs")
            checkpoint_path = output / "runtime_checkpoints" / f"chunk_{index:04d}.json"
            checkpoint = checkpoint_reader(checkpoint_path)
            if (
                not isinstance(checkpoint, bytes)
                or hashlib.sha256(checkpoint).hexdigest()
                != continuation["checkpoint_sha256"]
            ):
                raise TrainingRunnerBlocked("training continuation checkpoint differs")
            runtime_state = runtime_api.restore_paired_training_checkpoint(checkpoint)
            if runtime_api.encode_paired_training_checkpoint(runtime_state) != checkpoint:
                raise TrainingRunnerBlocked("training continuation re-encoding differs")
            restored = _checkpoint_snapshot(checkpoint)
            if restored["coordinates"]["next_chunk_index"] != index:
                raise TrainingRunnerBlocked("training continuation coordinate differs")

        environment_factory = environment_factory_loader()
        if not callable(environment_factory):
            raise TrainingRunnerBlocked("training environment factory is invalid")
        return _run_training_schedule(
            control_api=control_api,
            runtime_api=runtime_api,
            context=context,
            lease=lease,
            runtime_state=runtime_state,
            training_seeds=training_seeds,
            environment_factory=environment_factory,
            deadline=deadline,
            clock=clock,
            closeout=lambda verdict, snapshot: closeout(
                control_api=control_api,
                context=context,
                lease=lease,
                verdict=verdict,
                final_snapshot=snapshot,
            ),
        )


def _default_artifact_reader(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise TrainingRunnerBlocked(f"bound artifact cannot be read: {path.name}") from exc


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
        raise TrainingRunnerBlocked("repository observation failed") from exc
    return completed.stdout.strip()


def _git_bytes(root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TrainingRunnerBlocked("repository blob observation failed") from exc
    return completed.stdout


def _default_repo_observer(manifest: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(manifest["repository_root"])
    manifest_relative = Path(manifest["manifest_path"]).relative_to(root).as_posix()
    artifact_paths = [
        manifest["artifacts"][name]["path"] for name in ARTIFACT_NAMES
    ]
    tracked = [manifest_relative, *artifact_paths]
    observed_tracked = set(
        _git_text(root, "ls-files", "--error-unmatch", "--", *tracked).splitlines()
    )
    head = _git_text(root, "rev-parse", "HEAD")
    pushed = _git_text(root, "rev-parse", manifest["pushed_ref"])
    runner_commit = manifest["runner_source_commit"]
    _git_text(root, "merge-base", "--is-ancestor", runner_commit, head)
    source_commit_bound = all(
        _binding_matches(
            _git_bytes(root, "show", f"{runner_commit}:{binding['path']}"), binding
        )
        for binding in manifest["artifacts"].values()
    )
    return {
        "clean": _git_text(root, "status", "--porcelain=v1", "--", *tracked) == "",
        "head": head,
        "pushed": pushed,
        "runner_ancestor": True,
        "source_commit_bound": source_commit_bound,
        "tracked": (
            observed_tracked == set(tracked)
            and _git_text(root, "rev-parse", "HEAD") == head
            and _git_text(root, "rev-parse", manifest["pushed_ref"])
            == pushed
        ),
    }


def _default_authorized_source_observer(
    manifest: Mapping[str, Any],
    authority_paths: Sequence[str],
    *,
    opaque_artifact_names: Sequence[str] = (),
) -> dict[str, Any]:
    opaque_names = set(opaque_artifact_names)
    if len(opaque_names) != len(tuple(opaque_artifact_names)) or not opaque_names.issubset(
        ARTIFACT_NAMES
    ):
        raise TrainingRunnerBlocked("opaque source artifact names differ")
    root = Path(manifest["repository_root"])
    try:
        authority_relative = [
            Path(path).resolve().relative_to(root).as_posix()
            for path in authority_paths
        ]
        manifest_relative = Path(manifest["manifest_path"]).relative_to(
            root
        ).as_posix()
    except ValueError as exc:
        raise TrainingRunnerBlocked(
            "authorized command artifact is outside repository"
        ) from exc
    artifact_paths = [
        manifest["artifacts"][name]["path"] for name in ARTIFACT_NAMES
    ]
    tracked = list(
        dict.fromkeys([manifest_relative, *artifact_paths, *authority_relative])
    )
    clean_paths = list(
        dict.fromkeys(
            [
                manifest_relative,
                *(
                    manifest["artifacts"][name]["path"]
                    for name in ARTIFACT_NAMES
                    if name not in opaque_names
                ),
                *authority_relative,
            ]
        )
    )
    observed_tracked = set(
        _git_text(root, "ls-files", "--error-unmatch", "--", *tracked).splitlines()
    )
    head = _git_text(root, "rev-parse", "HEAD")
    pushed = _git_text(root, "rev-parse", manifest["pushed_ref"])
    authority_bindings = {}
    for absolute_path, relative_path in zip(
        authority_paths, authority_relative
    ):
        payload = _git_bytes(root, "show", f"{head}:{relative_path}")
        authority_bindings[absolute_path] = {
            "path": absolute_path,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    runner_commit = manifest["runner_source_commit"]
    _git_text(root, "merge-base", "--is-ancestor", runner_commit, head)
    source_commit_bound = all(
        _binding_matches(
            _git_bytes(root, "show", f"{runner_commit}:{binding['path']}"), binding
        )
        for name, binding in manifest["artifacts"].items()
        if name not in opaque_names
    )
    return {
        "authority_bindings": authority_bindings,
        "clean": _git_text(root, "status", "--porcelain=v1", "--", *clean_paths)
        == "",
        "head": head,
        "pushed": pushed,
        "runner_ancestor": True,
        "source_commit_bound": source_commit_bound,
        "tracked": (
            observed_tracked == set(tracked)
            and _git_text(root, "rev-parse", "HEAD") == head
            and _git_text(root, "rev-parse", manifest["pushed_ref"])
            == pushed
        ),
    }


def _load_authorized_command_documents(
    *,
    command: str,
    manifest_path: Path | str,
    envelope_path: Path | str,
    authorization_path: Path | str,
    approval_path: Path | str,
    launch_observation_path: Path | str,
    artifact_reader: Callable[[Path], bytes] | None = None,
    source_observer: Callable[
        [Mapping[str, Any], Sequence[str]], Mapping[str, Any]
    ]
    | None = None,
) -> dict[str, Any]:
    """Load one pushed command authority without opening empirical inputs."""
    if command not in {"run-training", "terminalize-dead-owner"}:
        raise TrainingRunnerBlocked("authorized command loader command differs")
    reader = artifact_reader or _default_artifact_reader
    if source_observer is None:
        opaque_names = ("registration",) if command == "terminalize-dead-owner" else ()

        def observer(value: Mapping[str, Any], paths: Sequence[str]) -> Mapping[str, Any]:
            return _default_authorized_source_observer(
                value, paths, opaque_artifact_names=opaque_names
            )

    else:
        observer = source_observer
    if not callable(reader) or not callable(observer):
        raise TrainingRunnerBlocked("authorized command loader callback is invalid")

    paths = {
        "--manifest": Path(manifest_path).resolve(),
        "--envelope": Path(envelope_path).resolve(),
        "--authorization": Path(authorization_path).resolve(),
        "--approval": Path(approval_path).resolve(),
        "--launch-observation": Path(launch_observation_path).resolve(),
    }

    def read_bounded(path: Path, label: str) -> bytes:
        payload = reader(path)
        if (
            not isinstance(payload, bytes)
            or not payload
            or len(payload) > AUTHORIZED_DOCUMENT_MAX_BYTES
        ):
            raise TrainingRunnerBlocked(f"{label} bytes are invalid")
        return payload

    authority_payloads = {
        "--manifest": read_bounded(paths["--manifest"], "launch manifest")
    }
    manifest = parse_launch_manifest_bytes(authority_payloads["--manifest"])
    if paths["--manifest"].as_posix() != manifest["manifest_path"]:
        raise TrainingRunnerBlocked("authorized command manifest path differs")
    command_key = (
        "run_training" if command == "run-training" else "terminalize_dead_owner"
    )
    command_value = manifest["commands"][command_key]
    expected_paths = dict(zip(command_value[4::2], command_value[5::2]))
    observed_paths = {name: path.as_posix() for name, path in paths.items()}
    if observed_paths != expected_paths:
        raise TrainingRunnerBlocked("authorized command path differs")

    root = Path(manifest["repository_root"])
    request_path = root / PurePosixPath(
        manifest["artifacts"]["training_request"]["path"]
    )
    request_payload = read_bounded(request_path, "training request")
    if not _binding_matches(
        request_payload, manifest["artifacts"]["training_request"]
    ):
        raise TrainingRunnerBlocked("authorized training request binding differs")
    request = _parse_canonical_mapping(request_payload, "training request")
    authority_payloads["--envelope"] = read_bounded(
        paths["--envelope"], f"{command} envelope"
    )
    envelope = parse_command_envelope_bytes(
        authority_payloads["--envelope"], manifest
    )
    if envelope["command"] != command:
        raise TrainingRunnerBlocked("authorized command envelope differs")
    authority_payloads["--authorization"] = read_bounded(
        paths["--authorization"], "stage authorization"
    )
    authorization = _parse_canonical_mapping(
        authority_payloads["--authorization"],
        "stage authorization",
    )
    authority_payloads["--approval"] = read_bounded(
        paths["--approval"], "stage approval"
    )
    approval = _parse_canonical_mapping(
        authority_payloads["--approval"],
        "stage approval",
    )
    authority_payloads["--launch-observation"] = read_bounded(
        paths["--launch-observation"], "runner launch observation"
    )
    launch_observation = _parse_canonical_mapping(
        authority_payloads["--launch-observation"],
        "runner launch observation",
    )
    if launch_observation != envelope["runner_launch_observation"]:
        raise TrainingRunnerBlocked("bound runner launch observation differs")

    authority_path_values = [
        paths[name].as_posix()
        for name in (
            "--manifest",
            "--envelope",
            "--authorization",
            "--approval",
            "--launch-observation",
        )
    ]
    try:
        source = _mapping(
            observer(manifest, authority_path_values),
            "authorized command source observation",
        )
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked(
            "authorized command source observation failed"
        ) from exc
    _fields(
        source,
        {
            "authority_bindings",
            "clean",
            "head",
            "pushed",
            "runner_ancestor",
            "source_commit_bound",
            "tracked",
        },
        "authorized command source observation",
    )
    observed_authority_bindings = _mapping(
        source["authority_bindings"], "pushed authority bindings"
    )
    if set(observed_authority_bindings) != set(authority_path_values):
        raise TrainingRunnerBlocked("pushed authority binding paths differ")
    for name, payload in authority_payloads.items():
        path = paths[name].as_posix()
        binding = _external_binding(
            observed_authority_bindings[path], "pushed authority artifact"
        )
        if binding["path"] != path or not _binding_matches(payload, binding):
            raise TrainingRunnerBlocked("pushed authority bytes differ")
    if (
        source["clean"] is not True
        or source["tracked"] is not True
        or source["runner_ancestor"] is not True
        or source["source_commit_bound"] is not True
        or _commit(source["head"], "authorized source head")
        != _commit(source["pushed"], "authorized pushed head")
    ):
        raise TrainingRunnerBlocked("authorized command pushed source differs")
    authority = validate_authorized_command_envelope(
        envelope=envelope,
        manifest=manifest,
        request=request,
        authorization=authorization,
        approval=approval,
    )
    return {
        "approval": copy.deepcopy(approval),
        "authority": authority,
        "authorization": copy.deepcopy(authorization),
        "envelope": copy.deepcopy(envelope),
        "launch_observation": copy.deepcopy(launch_observation),
        "manifest": copy.deepcopy(manifest),
        "request": copy.deepcopy(request),
        "source_observation": source,
    }


def _load_registration_validation_dependencies(
    *,
    launch_manifest: Mapping[str, Any],
    artifact_reader: Callable[[Path], bytes] | None = None,
) -> dict[str, Any]:
    """Load both registration validators from their manifest-bound sources."""
    manifest = validate_launch_manifest(launch_manifest)
    reader = artifact_reader or _default_artifact_reader
    if not callable(reader):
        raise TrainingRunnerBlocked(
            "registration validation dependency callback is invalid"
        )
    definitions = {
        "producer": (
            "registration_producer_source",
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_seed_inventory",
        ),
        "independent": (
            "registration_verifier_source",
            "analysis_scripts.verify_noncombat_card_acceptance_empirical_successor",
        ),
    }
    root = Path(manifest["repository_root"])
    loaded = {}
    source_bindings = {}
    for role, (artifact_name, module_name) in definitions.items():
        binding = manifest["artifacts"][artifact_name]
        path = (root / PurePosixPath(binding["path"])).resolve()
        before = reader(path)
        if not isinstance(before, bytes) or not _binding_matches(before, binding):
            raise TrainingRunnerBlocked(
                f"registration {role} dependency source differs"
            )
        try:
            code = compile(before, str(path), "exec", dont_inherit=True)
            module = types.ModuleType(module_name)
            module.__file__ = str(path)
            module.__package__ = module_name.rpartition(".")[0]
            exec(code, module.__dict__)
        except Exception as exc:
            raise TrainingRunnerBlocked(
                f"registration {role} dependency execution failed"
            ) from exc
        after = reader(path)
        if (
            not isinstance(after, bytes)
            or after != before
            or not _binding_matches(after, binding)
        ):
            raise TrainingRunnerBlocked(
                f"registration {role} dependency execution source differs"
            )
        loaded[role] = module
        source_bindings[role] = copy.deepcopy(binding)

    producer = loaded["producer"]
    independent = loaded["independent"]
    required = (
        getattr(producer, "parse_canonical_mapping_bytes", None),
        getattr(producer, "validate_inventory", None),
        getattr(producer, "validate_inventory_registration", None),
        getattr(independent, "verify_inventory_registration", None),
    )
    if not all(callable(operation) for operation in required):
        raise TrainingRunnerBlocked(
            "registration validation dependency API is incomplete"
        )

    def parse_inventory(payload: bytes) -> Mapping[str, Any]:
        return producer.validate_inventory(
            producer.parse_canonical_mapping_bytes(payload, "source inventory")
        )

    return {
        "independent_verifier": independent.verify_inventory_registration,
        "inventory_parser": parse_inventory,
        "producer_validator": producer.validate_inventory_registration,
        "source_bindings": source_bindings,
    }


def _source_inventory_execution_bindings(
    *,
    launch_manifest: Mapping[str, Any],
    source_inventory: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    manifest = validate_launch_manifest(launch_manifest)
    inventory = _mapping(source_inventory, "registered source inventory")
    if (
        _digest(
            inventory.get("inventory_sha256"),
            "registered source inventory digest",
        )
        != manifest["registered_source"]["source_inventory_sha256"]
    ):
        raise TrainingRunnerBlocked("registered source inventory identity differs")
    modules = inventory.get("modules")
    dependencies = inventory.get("public_dependencies")
    if not isinstance(modules, list) or not isinstance(dependencies, list):
        raise TrainingRunnerBlocked("registered source inventory sections differ")

    root = Path(manifest["repository_root"])
    rows: dict[str, dict[str, Any]] = {}
    overrides = {
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_seed_inventory": (
            "seed_inventory",
            "registration_producer_source",
        ),
        "analysis_scripts.verify_noncombat_card_acceptance_empirical_successor": (
            "independent_verifier",
            "registration_verifier_source",
        ),
    }
    seen_overrides = set()
    for section_name, values in (
        ("modules", modules),
        ("public_dependencies", dependencies),
    ):
        for index, value in enumerate(values):
            row = _mapping(value, f"registered source {section_name}[{index}]")
            expected_fields = (
                {"name", "path", "role", "sha256", "size_bytes"}
                if section_name == "modules"
                else {
                    "name",
                    "path",
                    "public_symbols",
                    "sha256",
                    "size_bytes",
                }
            )
            _fields(
                row,
                expected_fields,
                f"registered source {section_name}[{index}]",
            )
            binding = _artifact_binding(
                {
                    "path": row.get("path"),
                    "sha256": row.get("sha256"),
                    "size_bytes": row.get("size_bytes"),
                },
                f"registered source {section_name}[{index}]",
            )
            if section_name == "modules":
                module_name = row.get("name")
                if not isinstance(module_name, str) or not module_name:
                    raise TrainingRunnerBlocked(
                        "registered source module name differs"
                    )
            else:
                public_symbols = row["public_symbols"]
                if (
                    not isinstance(public_symbols, list)
                    or not public_symbols
                    or any(
                        not isinstance(symbol, str) or not symbol
                        for symbol in public_symbols
                    )
                    or public_symbols != sorted(set(public_symbols))
                ):
                    raise TrainingRunnerBlocked(
                        "registered public dependency symbols differ"
                    )
                path = PurePosixPath(binding["path"])
                if path.suffix != ".py" or path.parts[:1] != ("analysis_scripts",):
                    raise TrainingRunnerBlocked(
                        "registered public dependency path differs"
                    )
                module_name = ".".join(path.with_suffix("").parts)
                if module_name.endswith(".__init__"):
                    module_name = module_name.removesuffix(".__init__")
                if (
                    module_name == "analysis_scripts.noncombat_simulator_adapter"
                    and public_symbols
                    != list(_REGISTERED_ADAPTER_PUBLIC_SYMBOLS)
                ):
                    raise TrainingRunnerBlocked(
                        "registered simulator adapter public API differs"
                    )
            if module_name in overrides:
                if section_name != "modules":
                    raise TrainingRunnerBlocked(
                        "registered additive override section differs"
                    )
                expected_role, artifact_name = overrides[module_name]
                if (
                    row["role"] != expected_role
                    or binding["path"]
                    != manifest["artifacts"][artifact_name]["path"]
                ):
                    raise TrainingRunnerBlocked(
                        "registered additive override identity differs"
                    )
                seen_overrides.add(module_name)
                continue
            if module_name in rows or any(
                item["path"] == binding["path"] for item in rows.values()
            ):
                raise TrainingRunnerBlocked("registered execution source is duplicated")
            rows[module_name] = {
                **binding,
                "absolute_path": str((root / PurePosixPath(binding["path"])).resolve()),
                "module_name": module_name,
            }

    if seen_overrides != set(overrides):
        raise TrainingRunnerBlocked("registered additive override is incomplete")

    required = {
        "control": "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment",
        "runtime": "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime",
        "adapter": "analysis_scripts.noncombat_simulator_adapter",
    }
    if any(name not in rows for name in required.values()):
        raise TrainingRunnerBlocked("registered execution source is incomplete")
    if (
        {
            field: rows[required["control"]][field]
            for field in _ARTIFACT_FIELDS
        }
        != manifest["artifacts"]["control_source"]
        or {
            field: rows[required["runtime"]][field]
            for field in _ARTIFACT_FIELDS
        }
        != manifest["artifacts"]["runtime_source"]
    ):
        raise TrainingRunnerBlocked("registered execution manifest source differs")
    return rows


def _default_external_binding_observer(path: Path | str) -> dict[str, Any]:
    target = Path(path).resolve()
    digest = hashlib.sha256()
    size = 0
    try:
        with target.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise TrainingRunnerBlocked("bound external artifact cannot be read") from exc
    return {
        "path": target.as_posix(),
        "sha256": digest.hexdigest(),
        "size_bytes": size,
    }


def _pe_import_names(payload: bytes) -> list[str]:
    """Read normal and delay-load DLL names from one PE image."""
    if not isinstance(payload, bytes) or len(payload) < 64 or payload[:2] != b"MZ":
        raise TrainingRunnerBlocked("native dependency is not a PE image")

    def unpack(format_string: str, offset: int, label: str) -> tuple[Any, ...]:
        try:
            return struct.unpack_from(format_string, payload, offset)
        except (struct.error, TypeError) as exc:
            raise TrainingRunnerBlocked(f"native PE {label} is truncated") from exc

    pe_offset = unpack("<I", 0x3C, "DOS header")[0]
    if pe_offset < 64 or payload[pe_offset : pe_offset + 4] != b"PE\x00\x00":
        raise TrainingRunnerBlocked("native dependency PE signature differs")
    file_header = pe_offset + 4
    section_count = unpack("<H", file_header + 2, "file header")[0]
    optional_size = unpack("<H", file_header + 16, "file header")[0]
    if section_count <= 0 or section_count > 96:
        raise TrainingRunnerBlocked("native PE section count differs")
    optional = file_header + 20
    magic = unpack("<H", optional, "optional header")[0]
    if magic == 0x20B:
        directory_count_offset = optional + 108
        directories_offset = optional + 112
    elif magic == 0x10B:
        directory_count_offset = optional + 92
        directories_offset = optional + 96
    else:
        raise TrainingRunnerBlocked("native PE optional-header magic differs")
    if optional_size < directories_offset - optional:
        raise TrainingRunnerBlocked("native PE optional header differs")
    directory_count = unpack(
        "<I", directory_count_offset, "data-directory count"
    )[0]
    section_offset = optional + optional_size
    sections = []
    for index in range(section_count):
        offset = section_offset + index * 40
        virtual_size, virtual_address, raw_size, raw_offset = unpack(
            "<IIII", offset + 8, f"section[{index}]"
        )
        sections.append(
            (virtual_address, max(virtual_size, raw_size), raw_offset, raw_size)
        )

    def rva_offset(rva: int, label: str) -> int:
        if rva == 0:
            raise TrainingRunnerBlocked(f"native PE {label} RVA is absent")
        for virtual_address, span, raw_offset, raw_size in sections:
            if virtual_address <= rva < virtual_address + span:
                relative = rva - virtual_address
                if relative >= raw_size:
                    break
                result = raw_offset + relative
                if result >= len(payload):
                    break
                return result
        if rva < section_offset and rva < len(payload):
            return rva
        raise TrainingRunnerBlocked(f"native PE {label} RVA differs")

    def c_string(rva: int, label: str) -> str:
        offset = rva_offset(rva, label)
        end = payload.find(b"\x00", offset, min(len(payload), offset + 512))
        if end < 0:
            raise TrainingRunnerBlocked(f"native PE {label} is unterminated")
        try:
            name = payload[offset:end].decode("ascii").casefold()
        except UnicodeDecodeError as exc:
            raise TrainingRunnerBlocked(f"native PE {label} is not ASCII") from exc
        return _native_import_name(name, f"native PE {label}")

    names = set()

    def directory(index: int) -> tuple[int, int]:
        if directory_count <= index:
            return 0, 0
        return unpack(
            "<II", directories_offset + index * 8, f"directory[{index}]"
        )

    import_rva, import_size = directory(1)
    if import_rva:
        descriptor = rva_offset(import_rva, "import directory")
        limit = min(4096, max(1, import_size // 20 + 1))
        for index in range(limit):
            values = unpack("<IIIII", descriptor + index * 20, "import descriptor")
            if values == (0, 0, 0, 0, 0):
                break
            names.add(c_string(values[3], "import name"))
        else:
            raise TrainingRunnerBlocked("native PE import directory is unterminated")

    delay_rva, delay_size = directory(13)
    if delay_rva:
        descriptor = rva_offset(delay_rva, "delay-import directory")
        limit = min(4096, max(1, delay_size // 32 + 1))
        for index in range(limit):
            values = unpack(
                "<IIIIIIII", descriptor + index * 32, "delay-import descriptor"
            )
            if values == (0, 0, 0, 0, 0, 0, 0, 0):
                break
            raise TrainingRunnerBlocked("native PE delay imports are unsupported")
        else:
            raise TrainingRunnerBlocked(
                "native PE delay-import directory is unterminated"
            )
    return sorted(names)


def build_native_dependency_closure(
    *,
    module_path: Path | str,
    dll_directories: Sequence[Path | str],
    interpreter_path: Path | str,
    artifact_reader: Callable[[Path], bytes] | None = None,
) -> dict[str, Any]:
    """Resolve recursive non-host PE dependencies without loading them."""
    reader = artifact_reader or _default_artifact_reader
    if not callable(reader) or isinstance(dll_directories, (str, bytes)):
        raise TrainingRunnerBlocked("native dependency discovery input differs")
    module = Path(module_path).resolve()
    interpreter = Path(interpreter_path).resolve()
    directories = []
    for value in (module.parent, *(Path(path).resolve() for path in dll_directories), interpreter.parent):
        if value not in directories:
            directories.append(value)
    if not module.is_file() or not interpreter.is_file() or any(
        not path.is_dir() for path in directories
    ):
        raise TrainingRunnerBlocked("native dependency discovery path is unavailable")

    indexes: list[dict[str, Path]] = []
    try:
        for directory in directories:
            index: dict[str, Path] = {}
            for child in directory.iterdir():
                if not child.is_file():
                    continue
                name = child.name.casefold()
                if name in index:
                    raise TrainingRunnerBlocked(
                        "native dependency directory has ambiguous names"
                    )
                index[name] = child.resolve()
            indexes.append(index)
    except OSError as exc:
        raise TrainingRunnerBlocked(
            "native dependency directory cannot be enumerated"
        ) from exc

    payloads: dict[str, bytes] = {}
    imports: dict[str, list[str]] = {}
    pending = [module]
    dependencies: dict[str, Path] = {}
    trusted_host_imports = set()
    while pending:
        source = pending.pop()
        path = source.resolve().as_posix()
        if path in imports:
            continue
        payload = reader(source)
        if not isinstance(payload, bytes):
            raise TrainingRunnerBlocked("native dependency reader returned non-bytes")
        payloads[path] = payload
        names = _pe_import_names(payload)
        imports[path] = names
        for name in names:
            if _is_trusted_host_native_import(name):
                trusted_host_imports.add(name)
                continue
            resolved = next((index[name] for index in indexes if name in index), None)
            if resolved is None:
                raise TrainingRunnerBlocked(
                    f"native dependency import is unresolved: {name}"
                )
            resolved_path = resolved.as_posix()
            if resolved_path == module.as_posix():
                raise TrainingRunnerBlocked("native dependency imports the module")
            existing = dependencies.get(name)
            if existing is not None and existing != resolved:
                raise TrainingRunnerBlocked("native dependency resolution differs")
            dependencies[name] = resolved
            if resolved_path not in imports:
                pending.append(resolved)
        if len(imports) + len(pending) > 256:
            raise TrainingRunnerBlocked("native dependency closure is too large")

    dependency_bindings = sorted(
        (
            {
                "path": path.as_posix(),
                "sha256": hashlib.sha256(payloads[path.as_posix()]).hexdigest(),
                "size_bytes": len(payloads[path.as_posix()]),
            }
            for path in set(dependencies.values())
        ),
        key=lambda item: item["path"],
    )
    return {
        "dependencies": dependency_bindings,
        "imports": [
            {"imports": imports[path], "path": path}
            for path in sorted(imports)
        ],
        "trusted_host_imports": sorted(trusted_host_imports),
    }


@contextmanager
def _default_locked_external_binding(
    path: Path | str,
) -> Any:
    """Hold a Windows read/share lock while observing and loading a native file."""
    if os.name != "nt":
        raise TrainingRunnerBlocked(
            "locked native loading requires the registered Windows platform"
        )
    try:
        import ctypes
        from ctypes import wintypes
        import msvcrt
    except ImportError as exc:
        raise TrainingRunnerBlocked("Windows native locking is unavailable") from exc

    target = Path(path).resolve()
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = (
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )
    create_file.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    handle = create_file(
        str(target),
        0x80000000,  # GENERIC_READ
        0x00000001,  # FILE_SHARE_READ; deny concurrent write and delete
        None,
        3,  # OPEN_EXISTING
        0x00000080,  # FILE_ATTRIBUTE_NORMAL
        None,
    )
    if handle == wintypes.HANDLE(-1).value:
        raise TrainingRunnerBlocked(
            "bound native artifact cannot be locked"
        ) from OSError(ctypes.get_last_error(), "CreateFileW failed", str(target))
    try:
        file_descriptor = msvcrt.open_osfhandle(
            int(handle),
            os.O_RDONLY | getattr(os, "O_BINARY", 0),
        )
    except OSError as exc:
        close_handle(handle)
        raise TrainingRunnerBlocked(
            "bound native artifact lock cannot be adopted"
        ) from exc

    try:
        with os.fdopen(file_descriptor, "rb", closefd=True) as stream:
            def observe() -> dict[str, Any]:
                digest = hashlib.sha256()
                size = 0
                try:
                    stream.seek(0)
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                        size += len(chunk)
                except OSError as exc:
                    raise TrainingRunnerBlocked(
                        "locked native artifact cannot be read"
                    ) from exc
                return {
                    "path": target.as_posix(),
                    "sha256": digest.hexdigest(),
                    "size_bytes": size,
                }

            yield observe
    except OSError as exc:
        raise TrainingRunnerBlocked("bound native artifact lock failed") from exc


def _load_registered_native_module(
    module_path: Path | str,
    *,
    dll_directories: Sequence[Path | str],
) -> Any:
    module_file = Path(module_path).resolve()
    if not hasattr(os, "add_dll_directory"):
        raise TrainingRunnerBlocked("registered DLL loading is unavailable")
    try:
        for directory in dll_directories:
            _NATIVE_DLL_DIRECTORY_HANDLES.append(
                os.add_dll_directory(str(Path(directory).resolve()))
            )
        existing = sys.modules.get("sts_lightspeed_noncombat_adapter")
        if existing is not None:
            if Path(getattr(existing, "__file__", "")).resolve() != module_file:
                raise TrainingRunnerBlocked(
                    "registered native module was loaded from another path"
                )
            return existing
        spec = importlib.util.spec_from_file_location(
            "sts_lightspeed_noncombat_adapter",
            module_file,
        )
        if spec is None or spec.loader is None:
            raise TrainingRunnerBlocked(
                "registered native module import specification is unavailable"
            )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules["sts_lightspeed_noncombat_adapter"] = module
        return module
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked(
            "registered native module could not be loaded"
        ) from exc


class _TrainingNativeEnvironment:
    def __init__(self, *, adapter: Any, native: Any, provenance: Mapping[str, Any]):
        self._adapter = adapter
        self._native = native
        self._provenance = copy.deepcopy(dict(provenance))

    def snapshot(self) -> dict[str, Any]:
        return self._adapter.validate_snapshot(
            json.loads(self._native.snapshot_json())
        )

    def legal_actions(self) -> list[dict[str, Any]]:
        snapshot = self.snapshot()
        return self._adapter.validate_candidates(
            json.loads(self._native.legal_actions_json()),
            category=snapshot["category"],
        )

    def clone(self) -> "_TrainingNativeEnvironment":
        return _TrainingNativeEnvironment(
            adapter=self._adapter,
            native=self._native.clone(),
            provenance=self._provenance,
        )

    def step(self, action_id: str) -> dict[str, Any]:
        before = self.snapshot()
        candidates = self.legal_actions()
        if [item["action_id"] for item in candidates].count(action_id) != 1:
            raise TrainingRunnerBlocked(
                "training action must select one registered candidate"
            )
        self._native.step(action_id)
        after = self.snapshot()
        return {
            "baseline_control": after["baseline_control"],
            "candidate_actions": candidates,
            "category": before["category"],
            "evidence_class": "simulator_transition",
            "live_evidence": {
                "known_propensity": False,
                "live_outcome_join": False,
                "ope_overlap": False,
                "target_supported_victory": False,
            },
            "provenance": copy.deepcopy(self._provenance),
            "schema_version": "noncombat-simulator-transition-v1",
            "selected_action_id": action_id,
            "source_state": before["state"],
            "source_type": "sts_lightspeed_simulation",
            "successor": {
                "category": after["category"],
                "state": after["state"],
                "terminal": after["terminal"],
            },
            "training_authority": {
                "formal_noncombat_rl": False,
                "live_policy_loading": False,
                "live_study_launch": False,
                "ope_reinterpretation": False,
                "policy_promotion": False,
            },
        }


class _BoundSourceLoader(importlib.abc.Loader):
    def __init__(self, *, module_name: str, path: str, payload: bytes) -> None:
        self._module_name = module_name
        self._path = path
        self._payload = payload

    def exec_module(self, module: types.ModuleType) -> None:
        module.__file__ = self._path
        code = compile(
            self._payload,
            self._path,
            "exec",
            dont_inherit=True,
        )
        exec(code, module.__dict__)


class _BoundSourceFinder(importlib.abc.MetaPathFinder):
    def __init__(
        self,
        *,
        sources: Mapping[str, tuple[str, bytes]],
        allowed_preloaded: Sequence[str],
    ) -> None:
        self._sources = dict(sources)
        self._allowed_preloaded = frozenset(allowed_preloaded)

    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None = None,
        target: types.ModuleType | None = None,
    ) -> Any:
        del path, target
        source = self._sources.get(fullname)
        if source is not None:
            source_path, payload = source
            return importlib.util.spec_from_loader(
                fullname,
                _BoundSourceLoader(
                    module_name=fullname,
                    path=source_path,
                    payload=payload,
                ),
                origin=source_path,
            )
        if (
            fullname.startswith("analysis_scripts.")
            and fullname not in self._allowed_preloaded
        ):
            raise ImportError(f"unregistered local execution import: {fullname}")
        return None


def _observe_native_dependency_closure(
    native_identity: Mapping[str, Any],
) -> dict[str, Any]:
    native = _mapping(native_identity, "native identity for dependency observation")
    module = _external_binding(native.get("module"), "observed native module")
    expected = _native_dependency_closure(
        native.get("dependency_closure"),
        module=module,
    )
    dependencies_by_name = {
        Path(item["path"]).name.casefold(): item
        for item in expected["dependencies"]
    }
    imports = []
    trusted_host_imports = set()
    for binding in [module, *expected["dependencies"]]:
        try:
            payload = Path(binding["path"]).read_bytes()
        except OSError as exc:
            raise TrainingRunnerBlocked(
                "locked native dependency cannot be parsed"
            ) from exc
        names = _pe_import_names(payload)
        for name in names:
            if name in dependencies_by_name:
                continue
            if not _is_trusted_host_native_import(name):
                raise TrainingRunnerBlocked(
                    "observed native dependency import is unresolved"
                )
            trusted_host_imports.add(name)
        imports.append({"imports": names, "path": binding["path"]})
    return _native_dependency_closure(
        {
            "dependencies": copy.deepcopy(expected["dependencies"]),
            "imports": sorted(imports, key=lambda item: item["path"]),
            "trusted_host_imports": sorted(trusted_host_imports),
        },
        module=module,
    )


def _validate_native_dependency_resolution(
    native_identity: Mapping[str, Any],
    *,
    interpreter_path: Path | str,
) -> dict[str, Any]:
    native = _mapping(native_identity, "native identity for resolution")
    module = _external_binding(native.get("module"), "resolved native module")
    closure = _native_dependency_closure(
        native.get("dependency_closure"),
        module=module,
    )
    interpreter = Path(interpreter_path).resolve()
    directories = []
    for directory in (
        Path(module["path"]).parent,
        *(Path(path).resolve() for path in native.get("dll_directories", ())),
        interpreter.parent,
    ):
        if directory not in directories:
            directories.append(directory)
    if not interpreter.is_file() or any(not directory.is_dir() for directory in directories):
        raise TrainingRunnerBlocked("native dependency resolution path is unavailable")

    try:
        entries = {
            directory: [
                child.resolve()
                for child in directory.iterdir()
                if child.is_file()
            ]
            for directory in directories
        }
    except OSError as exc:
        raise TrainingRunnerBlocked(
            "native dependency resolution directory cannot be enumerated"
        ) from exc

    resolved = []
    for dependency in closure["dependencies"]:
        name = Path(dependency["path"]).name.casefold()
        matches = sorted(
            {
                child.as_posix()
                for directory in directories
                for child in entries[directory]
                if child.name.casefold() == name
            }
        )
        if matches != [dependency["path"]]:
            raise TrainingRunnerBlocked(
                "native dependency resolution is shadowed or unavailable"
            )
        resolved.append({"name": name, "path": dependency["path"]})
    return {
        "directories": [directory.as_posix() for directory in directories],
        "dependencies": resolved,
    }


def _preload_registered_native_dependencies(
    native_identity: Mapping[str, Any],
) -> dict[str, Any]:
    native = _mapping(native_identity, "native identity for dependency preload")
    module = _external_binding(native.get("module"), "preloaded native module")
    closure = _native_dependency_closure(
        native.get("dependency_closure"),
        module=module,
    )
    order = _native_dependency_order_from_normalized(
        module_path=module["path"],
        dependencies=closure["dependencies"],
        imports=closure["imports"],
    )
    if os.name != "nt":
        raise TrainingRunnerBlocked(
            "native dependency preload requires the registered Windows platform"
        )
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError as exc:
        raise TrainingRunnerBlocked(
            "Windows native dependency preload is unavailable"
        ) from exc

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_module_handle = kernel32.GetModuleHandleW
    get_module_handle.argtypes = (wintypes.LPCWSTR,)
    get_module_handle.restype = wintypes.HMODULE
    load_library = kernel32.LoadLibraryExW
    load_library.argtypes = (wintypes.LPCWSTR, wintypes.HANDLE, wintypes.DWORD)
    load_library.restype = wintypes.HMODULE
    get_module_filename = kernel32.GetModuleFileNameW
    get_module_filename.argtypes = (
        wintypes.HMODULE,
        wintypes.LPWSTR,
        wintypes.DWORD,
    )
    get_module_filename.restype = wintypes.DWORD
    loaded = []
    for path in order:
        name = Path(path).name
        if get_module_handle(name):
            raise TrainingRunnerBlocked(
                "registered native dependency was preloaded"
            )
        handle = load_library(
            str(Path(path).resolve()),
            None,
            0x00000100 | 0x00000400,
        )
        if not handle:
            raise TrainingRunnerBlocked(
                "registered native dependency could not be preloaded"
            ) from OSError(
                ctypes.get_last_error(),
                "LoadLibraryExW failed",
                path,
            )
        buffer = ctypes.create_unicode_buffer(32768)
        length = get_module_filename(handle, buffer, len(buffer))
        if not length or length >= len(buffer):
            raise TrainingRunnerBlocked(
                "preloaded native dependency path is unavailable"
            )
        observed_path = Path(buffer.value).resolve().as_posix()
        if observed_path.casefold() != path.casefold():
            raise TrainingRunnerBlocked(
                "preloaded native dependency path differs"
            )
        _NATIVE_DEPENDENCY_MODULE_HANDLES.append(int(handle))
        loaded.append({"name": name.casefold(), "path": path})
    return {"dependencies": loaded}


def _load_source_bound_training_dependencies(
    *,
    control_api: Any,
    launch_manifest: Mapping[str, Any],
    source_inventory: Mapping[str, Any],
    artifact_reader: Callable[[Path], bytes] | None = None,
    module_importer: Callable[[str], Any] | None = None,
    module_registry: Mapping[str, Any] | None = None,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None = None,
    native_import_observer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    native_module_loader: Callable[..., Any] | None = None,
    native_dependency_preloader: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    native_resolution_validator: Callable[..., Mapping[str, Any] | None] | None = None,
    directory_observer: Callable[[Path], bool] | None = None,
    python_version: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Load the registered adapter, native module and runtime after source checks."""
    manifest = validate_launch_manifest(launch_manifest)
    reader = artifact_reader or _default_artifact_reader
    importer = module_importer or importlib.import_module
    registry = module_registry if module_registry is not None else sys.modules
    load_native = native_module_loader or _load_registered_native_module
    observe_native_imports = (
        native_import_observer or _observe_native_dependency_closure
    )
    validate_native_resolution = (
        native_resolution_validator or _validate_native_dependency_resolution
    )
    preload_native_dependencies = (
        native_dependency_preloader or _preload_registered_native_dependencies
    )
    is_directory = directory_observer or (lambda path: path.is_dir())
    version = python_version or platform.python_version
    callbacks = (
        reader,
        importer,
        load_native,
        observe_native_imports,
        preload_native_dependencies,
        validate_native_resolution,
        is_directory,
        version,
    )
    if not all(callable(callback) for callback in callbacks):
        raise TrainingRunnerBlocked("training dependency callback is invalid")
    if external_binding_observer is not None and not callable(
        external_binding_observer
    ):
        raise TrainingRunnerBlocked("training native observer is invalid")

    if external_binding_observer is None:
        native_binding_guard = _default_locked_external_binding
    else:
        @contextmanager
        def native_binding_guard(path: Path | str) -> Any:
            yield lambda: external_binding_observer(path)

    if any(
        name == prefix or name.startswith(prefix + ".")
        for name in registry
        for prefix in (
            "torch",
            "sts_lightspeed_noncombat_adapter",
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime",
            "analysis_scripts.noncombat_simulator_adapter",
        )
    ):
        raise TrainingRunnerBlocked("training execution dependency is preloaded")

    sources = _source_inventory_execution_bindings(
        launch_manifest=manifest,
        source_inventory=source_inventory,
    )
    before: dict[str, bytes] = {}
    for name in sorted(sources):
        binding = sources[name]
        payload = reader(Path(binding["absolute_path"]))
        if not isinstance(payload, bytes) or not _binding_matches(payload, binding):
            raise TrainingRunnerBlocked(f"registered execution source differs: {name}")
        before[name] = payload

    finder = None
    if module_importer is None:
        allowed_preloaded = {
            "analysis_scripts",
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment",
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_training_runner",
        }
        unexpectedly_preloaded = sorted(
            name
            for name in sources
            if name in registry and name not in allowed_preloaded
        )
        if unexpectedly_preloaded:
            raise TrainingRunnerBlocked(
                "registered execution source is preloaded: "
                + ", ".join(unexpectedly_preloaded)
            )
        finder = _BoundSourceFinder(
            sources={
                name: (binding["absolute_path"], before[name])
                for name, binding in sources.items()
                if name not in allowed_preloaded
            },
            allowed_preloaded=tuple(allowed_preloaded),
        )
        sys.meta_path.insert(0, finder)

    adapter_name = "analysis_scripts.noncombat_simulator_adapter"
    runtime_name = (
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime"
    )
    try:
        try:
            adapter = importer(adapter_name)
        except Exception as exc:
            raise TrainingRunnerBlocked(
                "source-bound simulator adapter is unavailable"
            ) from exc
        if Path(getattr(adapter, "__file__", "")).resolve() != Path(
            sources[adapter_name]["absolute_path"]
        ):
            raise TrainingRunnerBlocked("source-bound simulator adapter path differs")
        adapter_operations = (
            "canonical_json_bytes",
            "validate_candidates",
            "validate_snapshot",
        )
        if (
            getattr(adapter, "ADAPTER_API_VERSION", None)
            != manifest["native_identity"]["adapter_api_version"]
            or getattr(adapter, "TARGET_CATEGORIES", None)
            != ("card_reward", "event", "route", "shop")
            or not isinstance(getattr(adapter, "SimulatorAdapterError", None), type)
            or any(
                not callable(getattr(adapter, name, None))
                for name in adapter_operations
            )
        ):
            raise TrainingRunnerBlocked("source-bound simulator adapter API differs")
        if any(
            name == prefix or name.startswith(prefix + ".")
            for name in registry
            for prefix in ("torch", "sts_lightspeed_noncombat_adapter")
        ):
            raise TrainingRunnerBlocked(
                "simulator adapter loaded execution dependency early"
            )

        native = manifest["native_identity"]
        if not all(is_directory(Path(path)) for path in native["dll_directories"]):
            raise TrainingRunnerBlocked("registered native DLL directory is unavailable")
        native_bindings = [
            native["module"],
            *native["dependency_closure"]["dependencies"],
        ]
        with ExitStack() as native_locks:
            native_observers = {
                binding["path"]: native_locks.enter_context(
                    native_binding_guard(binding["path"])
                )
                for binding in native_bindings
            }
            for binding in native_bindings:
                observed = _external_binding(
                    native_observers[binding["path"]](),
                    "native dependency before load",
                )
                if observed != binding:
                    raise TrainingRunnerBlocked(
                        "native dependency bytes differ before load"
                    )
            observed_closure = _native_dependency_closure(
                observe_native_imports(copy.deepcopy(native)),
                module=native["module"],
            )
            if observed_closure != native["dependency_closure"]:
                raise TrainingRunnerBlocked("native dependency import graph differs")
            validate_native_resolution(
                copy.deepcopy(native),
                interpreter_path=manifest["interpreter"],
            )
            preload_native_dependencies(copy.deepcopy(native))
            native_module = load_native(
                native["module"]["path"],
                dll_directories=[Path(path) for path in native["dll_directories"]],
            )
            if any(name == "torch" or name.startswith("torch.") for name in registry):
                raise TrainingRunnerBlocked("native loading imported Torch out of order")
            for binding in native_bindings:
                observed = _external_binding(
                    native_observers[binding["path"]](),
                    "native dependency after load",
                )
                if observed != binding:
                    raise TrainingRunnerBlocked(
                        "native dependency bytes differ after load"
                    )
        try:
            if (
                Path(getattr(native_module, "__file__", "")).resolve()
                != Path(native["module"]["path"])
                or any(
                    not callable(getattr(native_module, name, None))
                    for name in ("Environment", "adapter_api_version", "build_info_json")
                )
                or native_module.adapter_api_version()
                != native["adapter_api_version"]
            ):
                raise TrainingRunnerBlocked("loaded native adapter API differs")
            provenance = copy.deepcopy(native["provenance"])
            build = json.loads(
                native_module.build_info_json(),
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
            )
            build = _mapping(build, "loaded native build")
        except TrainingRunnerBlocked:
            raise
        except Exception as exc:
            raise TrainingRunnerBlocked("loaded native provenance is invalid") from exc
        build["python"] = version()
        if (
            provenance != native["provenance"]
            or provenance.get("build") != build
            or provenance.get("module_sha256") != native["module"]["sha256"]
            or (
                "module_size_bytes" in provenance
                and provenance["module_size_bytes"] != native["module"]["size_bytes"]
            )
            or canonical_json_sha256(provenance) != native["provenance_sha256"]
        ):
            raise TrainingRunnerBlocked("loaded native provenance differs")

        try:
            runtime = importer(runtime_name)
        except Exception as exc:
            raise TrainingRunnerBlocked(
                "source-bound training runtime is unavailable"
            ) from exc
        if Path(getattr(runtime, "__file__", "")).resolve() != Path(
            sources[runtime_name]["absolute_path"]
        ):
            raise TrainingRunnerBlocked("source-bound training runtime path differs")
        try:
            expected_metadata = _mapping(
                control_api.expected_runtime_metadata(), "expected runtime metadata"
            )
            observed_metadata = _mapping(runtime.runtime_metadata(), "runtime metadata")
        except TrainingRunnerBlocked:
            raise
        except Exception as exc:
            raise TrainingRunnerBlocked("training runtime metadata is invalid") from exc
        if observed_metadata != expected_metadata:
            raise TrainingRunnerBlocked("training runtime metadata differs")
        runtime_operations = (
            "collect_and_complete_paired_training_chunk",
            "encode_paired_training_checkpoint",
            "initialize_paired_training_runtime",
            "restore_paired_training_checkpoint",
            "runtime_metadata",
            "training_progress_verdict",
        )
        if any(
            not callable(getattr(runtime, name, None))
            for name in runtime_operations
        ):
            raise TrainingRunnerBlocked("training runtime API differs")
    finally:
        if finder is not None:
            try:
                sys.meta_path.remove(finder)
            except ValueError:
                pass

    for name in sorted(sources):
        binding = sources[name]
        after = reader(Path(binding["absolute_path"]))
        if (
            not isinstance(after, bytes)
            or after != before[name]
            or not _binding_matches(after, binding)
        ):
            raise TrainingRunnerBlocked(
                f"registered execution source changed during load: {name}"
            )

    native_environment = getattr(native_module, "Environment", None)
    if not callable(native_environment):
        raise TrainingRunnerBlocked("loaded environment constructors are unavailable")
    try:
        contract = _mapping(control_api.experiment_contract(), "training contract")
        environment = _mapping(contract.get("environment"), "training environment")
        ascension = environment["ascension"]
    except (KeyError, TypeError, TrainingRunnerBlocked) as exc:
        raise TrainingRunnerBlocked("training environment contract is invalid") from exc
    if environment != {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "ascension": 0,
        "device": "cpu",
    }:
        raise TrainingRunnerBlocked("training environment ascension differs")

    def environment_factory(seed: int) -> Any:
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise TrainingRunnerBlocked("training environment seed differs")
        return _TrainingNativeEnvironment(
            adapter=adapter,
            native=native_environment(seed, ascension),
            provenance=copy.deepcopy(provenance),
        )

    return {
        "adapter": adapter,
        "environment_factory": environment_factory,
        "native_module": native_module,
        "provenance": copy.deepcopy(provenance),
        "runtime": runtime,
        "source_bindings": copy.deepcopy(sources),
    }


def _compose_authorized_training_command_for_qualification(
    *,
    manifest_path: Path | str,
    envelope_path: Path | str,
    authorization_path: Path | str,
    approval_path: Path | str,
    launch_observation_path: Path | str,
    process_id: int,
    process_alive: Callable[[int], bool],
    clock: Callable[[], float],
    interpreter_path: Path | str | None = None,
    artifact_reader: Callable[[Path], bytes] | None = None,
    source_observer: Callable[
        [Mapping[str, Any], Sequence[str]], Mapping[str, Any]
    ]
    | None = None,
    pre_access_receipt_publisher: Callable[[Path, bytes], Mapping[str, Any]]
    | None = None,
) -> dict[str, Any]:
    """Exercise exact pre-runtime composition while the production CLI is closed."""
    reader = artifact_reader or _default_artifact_reader
    receipt_publisher = (
        pre_access_receipt_publisher or _publish_exclusive_pre_access_receipt
    )
    callbacks = (
        process_alive,
        clock,
        reader,
        receipt_publisher,
    )
    if not all(callable(callback) for callback in callbacks):
        raise TrainingRunnerBlocked("authorized training command callback is invalid")
    if _forbidden_imports_loaded():
        raise TrainingRunnerBlocked(
            "training command composition started after runtime dependency load"
        )
    documents = _load_authorized_command_documents(
        command="run-training",
        manifest_path=manifest_path,
        envelope_path=envelope_path,
        authorization_path=authorization_path,
        approval_path=approval_path,
        launch_observation_path=launch_observation_path,
        artifact_reader=reader,
        source_observer=source_observer,
    )
    manifest = documents["manifest"]
    observed_interpreter = Path(interpreter_path or sys.executable).resolve().as_posix()
    if observed_interpreter.casefold() != manifest["interpreter"].casefold():
        raise TrainingRunnerBlocked("authorized training interpreter differs")
    started = float(clock())
    max_seconds = manifest["resources"].get("max_charged_seconds")
    if (
        not math.isfinite(started)
        or isinstance(max_seconds, bool)
        or not isinstance(max_seconds, (int, float))
        or not math.isfinite(float(max_seconds))
        or max_seconds <= 0
    ):
        raise TrainingRunnerBlocked("authorized training deadline differs")
    deadline = started + float(max_seconds)
    try:
        control = importlib.import_module(
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
        )
    except Exception as exc:
        raise TrainingRunnerBlocked("bound training control is unavailable") from exc
    root = Path(manifest["repository_root"])
    registration_path = (
        root / PurePosixPath(manifest["artifacts"]["registration"]["path"])
    ).resolve()
    inventory_path = Path(manifest["source_inventory"]["path"]).resolve()
    dependency_state: dict[str, Any] = {}
    registered_state: dict[str, Any] = {}
    training_dependency_state: dict[str, Any] = {}

    def load_dependencies() -> None:
        dependencies = _mapping(
            _load_registration_validation_dependencies(
                launch_manifest=manifest,
                artifact_reader=reader,
            ),
            "registration validation dependencies",
        )
        _fields(
            dependencies,
            {
                "independent_verifier",
                "inventory_parser",
                "producer_validator",
                "source_bindings",
            },
            "registration validation dependencies",
        )
        if not all(
            callable(dependencies[name])
            for name in (
                "independent_verifier",
                "inventory_parser",
                "producer_validator",
            )
        ):
            raise TrainingRunnerBlocked(
                "registration validation dependency operation is invalid"
            )
        expected_bindings = {
            "independent": manifest["artifacts"]["registration_verifier_source"],
            "producer": manifest["artifacts"]["registration_producer_source"],
        }
        if dependencies["source_bindings"] != expected_bindings:
            raise TrainingRunnerBlocked(
                "registration validation dependency binding differs"
            )
        dependency_state.update(dependencies)
        if _forbidden_imports_loaded():
            raise TrainingRunnerBlocked(
                "registration validation loaded runtime dependencies"
            )

    def dependency_operation(name: str) -> Callable[..., Any]:
        def invoke(*args: Any) -> Any:
            operation = dependency_state.get(name)
            if not callable(operation):
                raise TrainingRunnerBlocked(
                    "registration validation dependency was not loaded"
                )
            return operation(*args)

        return invoke

    def validate_current_authority() -> Mapping[str, Any]:
        return validate_authorized_command_envelope(
            envelope=documents["envelope"],
            manifest=manifest,
            request=documents["request"],
            authorization=documents["authorization"],
            approval=documents["approval"],
        )

    def open_registered_inputs() -> Mapping[str, Any]:
        registered = _open_registered_training_inputs(
            authority_validator=validate_current_authority,
            expected_envelope_sha256=documents["authority"]["envelope_sha256"],
            expected_composite_sha256=documents["authority"]["composite_sha256"],
            launch_manifest=manifest,
            output_root=Path(manifest["output_root"]),
            process_id=process_id,
            pre_access_receipt_publisher=receipt_publisher,
            registration_reader=lambda: reader(registration_path),
            registration_binding=manifest["artifacts"]["registration"],
            inventory_reader=lambda: reader(inventory_path),
            inventory_binding=manifest["source_inventory"],
            inventory_parser=dependency_operation("inventory_parser"),
            producer_validator=dependency_operation("producer_validator"),
            independent_verifier=dependency_operation("independent_verifier"),
            rollback_authority_sha256=manifest["rollback_authority"][
                "rollback_authority_sha256"
            ],
            pre_input_validator=load_dependencies,
        )
        registered_state.update(copy.deepcopy(registered))
        return registered

    def load_training_dependencies() -> Mapping[str, Any]:
        if training_dependency_state:
            return training_dependency_state
        source_inventory = registered_state.get("source_inventory")
        if not isinstance(source_inventory, Mapping):
            raise TrainingRunnerBlocked(
                "validated source inventory is unavailable to runtime loader"
            )
        loaded = _mapping(
            _load_source_bound_training_dependencies(
                control_api=control,
                launch_manifest=manifest,
                source_inventory=copy.deepcopy(source_inventory),
            ),
            "source-bound training dependencies",
        )
        _fields(
            loaded,
            {
                "adapter",
                "environment_factory",
                "native_module",
                "provenance",
                "runtime",
                "source_bindings",
            },
            "source-bound training dependencies",
        )
        if not callable(loaded["environment_factory"]):
            raise TrainingRunnerBlocked(
                "source-bound training environment factory is invalid"
            )
        training_dependency_state.update(loaded)
        return training_dependency_state

    def resolved_runtime_loader() -> Any:
        return load_training_dependencies()["runtime"]

    def resolved_environment_factory_loader() -> Callable[[int], Any]:
        return load_training_dependencies()["environment_factory"]

    def build_context(
        execution_registration: Mapping[str, Any],
        original_registration: Mapping[str, Any],
        authority: Mapping[str, Any],
    ) -> Any:
        return _build_authorized_training_context(
            control_api=control,
            launch_manifest=manifest,
            command_envelope=documents["envelope"],
            authority=authority,
            original_registration=original_registration,
            execution_registration=execution_registration,
            request=documents["request"],
            authorization=documents["authorization"],
            approval=documents["approval"],
        )

    runner_authority_identity = {
        "composite_sha256": documents["authority"]["composite_sha256"],
        "launch_manifest_sha256": manifest["manifest_sha256"],
        "rollback_authority_sha256": manifest["rollback_authority"][
            "rollback_authority_sha256"
        ],
        "run_envelope_sha256": documents["authority"]["envelope_sha256"],
    }
    if _forbidden_imports_loaded():
        raise TrainingRunnerBlocked(
            "training command composition reached lifecycle after runtime dependency load"
        )
    _ensure_terminalization_guard(manifest)
    return _execute_training_lifecycle(
        control_api=control,
        registered_inputs_loader=open_registered_inputs,
        context_builder=build_context,
        context_identity_observer=control._context_identity,
        reopen_observer=lambda output, context, alive: (
            _observe_training_reopen_read_only(
                control_api=control,
                context=context,
                output_root=output,
                runner_authority_identity=runner_authority_identity,
                process_alive=alive,
            )
        ),
        lease_factory=lambda output, context, observation, child, alive, now: (
            _AtomicObservedExecutionLease(
                control_api=control,
                context=context,
                output_root=output,
                observation=observation,
                child_process_id=child,
                process_alive=alive,
                clock=now,
            )
        ),
        runtime_loader=resolved_runtime_loader,
        environment_factory_loader=resolved_environment_factory_loader,
        checkpoint_reader=reader,
        launch_marker_reader=reader,
        output_root=Path(manifest["output_root"]),
        manifest_sha256=manifest["manifest_sha256"],
        run_envelope_sha256=documents["authority"]["envelope_sha256"],
        rollback_authority_sha256=manifest["rollback_authority"][
            "rollback_authority_sha256"
        ],
        process_id=process_id,
        process_alive=process_alive,
        deadline=deadline,
        clock=clock,
        closeout=lambda **kwargs: _close_training_stage(
            rollback_authority=manifest["rollback_authority"],
            **kwargs,
        ),
    )


def _windows_process_alive(process_id: int) -> bool:
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0:
        return False
    if process_id == os.getpid():
        return True
    if os.name != "nt":
        return False
    try:
        import ctypes
        from ctypes import wintypes
    except ImportError:
        return False
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
        return ctypes.get_last_error() == 5
    try:
        return wait_for_single_object(handle, 0) == 0x00000102
    finally:
        close_handle(handle)


def _execute_authorized_training_command(
    *,
    manifest_path: Path | str,
    envelope_path: Path | str,
    authorization_path: Path | str,
    approval_path: Path | str,
    launch_observation_path: Path | str,
) -> dict[str, Any]:
    """Run the fixed production composition after CLI qualification opens it."""
    return _compose_authorized_training_command_for_qualification(
        manifest_path=manifest_path,
        envelope_path=envelope_path,
        authorization_path=authorization_path,
        approval_path=approval_path,
        launch_observation_path=launch_observation_path,
        process_id=os.getpid(),
        process_alive=_windows_process_alive,
        clock=time.monotonic,
    )


def _compose_authorized_dead_owner_terminalization_for_qualification(
    *,
    manifest_path: Path | str,
    envelope_path: Path | str,
    authorization_path: Path | str,
    approval_path: Path | str,
    launch_observation_path: Path | str,
    process_id: int,
    process_alive: Callable[[int], bool],
    clock: Callable[[], float],
    interpreter_path: Path | str | None = None,
    artifact_reader: Callable[[Path], bytes] | None = None,
    source_observer: Callable[
        [Mapping[str, Any], Sequence[str]], Mapping[str, Any]
    ]
    | None = None,
    external_binding_observer: Callable[[Path | str], Mapping[str, Any]] | None = None,
    checkpoint_snapshot_observer: Callable[[Path | str], Mapping[str, Any]]
    | None = None,
) -> dict[str, Any]:
    """Compose closure-only authority without opening inventory or runtime inputs."""
    reader = artifact_reader or _default_artifact_reader
    if not all(callable(callback) for callback in (reader, process_alive, clock)):
        raise TrainingRunnerBlocked("terminalization composition callback is invalid")
    if _forbidden_imports_loaded():
        raise TrainingRunnerBlocked(
            "terminalization composition started after runtime dependency load"
        )
    documents = _load_authorized_command_documents(
        command="terminalize-dead-owner",
        manifest_path=manifest_path,
        envelope_path=envelope_path,
        authorization_path=authorization_path,
        approval_path=approval_path,
        launch_observation_path=launch_observation_path,
        artifact_reader=reader,
        source_observer=source_observer,
    )
    manifest = documents["manifest"]
    observed_interpreter = Path(interpreter_path or sys.executable).resolve().as_posix()
    if observed_interpreter.casefold() != manifest["interpreter"].casefold():
        raise TrainingRunnerBlocked("terminalization interpreter differs")
    try:
        control = importlib.import_module(
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
        )
    except Exception as exc:
        raise TrainingRunnerBlocked("bound terminalization control is unavailable") from exc
    registration = {
        "registration_sha256": manifest["request_contract"]["registration_sha256"]
    }
    execution_registration = {
        **copy.deepcopy(registration),
        "rollback_authority_sha256": manifest["rollback_authority"][
            "rollback_authority_sha256"
        ],
    }
    context = _build_authorized_training_context(
        control_api=control,
        launch_manifest=manifest,
        command_envelope=documents["envelope"],
        authority=documents["authority"],
        original_registration=registration,
        execution_registration=execution_registration,
        request=documents["request"],
        authorization=documents["authorization"],
        approval=documents["approval"],
        expected_command="terminalize-dead-owner",
        registration_identity_only=True,
    )
    if _forbidden_imports_loaded():
        raise TrainingRunnerBlocked(
            "terminalization composition loaded runtime dependencies"
        )
    return _execute_dead_owner_terminalization(
        control_api=control,
        context=context,
        launch_manifest=manifest,
        command_envelope=documents["envelope"],
        authority=documents["authority"],
        rollback_authority=manifest["rollback_authority"],
        process_id=process_id,
        process_alive=process_alive,
        clock=clock,
        external_binding_observer=external_binding_observer,
        checkpoint_snapshot_observer=checkpoint_snapshot_observer,
    )


def _execute_authorized_dead_owner_terminalization_command(
    *,
    manifest_path: Path | str,
    envelope_path: Path | str,
    authorization_path: Path | str,
    approval_path: Path | str,
    launch_observation_path: Path | str,
) -> dict[str, Any]:
    return _compose_authorized_dead_owner_terminalization_for_qualification(
        manifest_path=manifest_path,
        envelope_path=envelope_path,
        authorization_path=authorization_path,
        approval_path=approval_path,
        launch_observation_path=launch_observation_path,
        process_id=os.getpid(),
        process_alive=_windows_process_alive,
        clock=time.monotonic,
    )


def _binding_matches(payload: bytes, binding: Mapping[str, Any]) -> bool:
    return (
        len(payload) == binding["size_bytes"]
        and hashlib.sha256(payload).hexdigest() == binding["sha256"]
    )


def _forbidden_imports_loaded() -> list[str]:
    return sorted(
        name
        for name in sys.modules
        if any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in FORBIDDEN_IMPORT_PREFIXES
        )
    )


def source_only_preflight(
    manifest_path: Path | str,
    *,
    repo_observer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    artifact_reader: Callable[[Path], bytes] | None = None,
    output_exists: Callable[[Path], bool] | None = None,
    interpreter_path: Path | str | None = None,
) -> dict[str, Any]:
    reader = artifact_reader or _default_artifact_reader
    path = Path(manifest_path).resolve()
    manifest = parse_launch_manifest_bytes(reader(path))
    if path.as_posix() != manifest["manifest_path"]:
        raise TrainingRunnerBlocked("preflight manifest path differs")
    if _forbidden_imports_loaded():
        raise TrainingRunnerBlocked("preflight started after forbidden import")
    output = Path(manifest["output_root"])
    exists = output_exists or (lambda target: target.exists())
    if exists(output):
        raise TrainingRunnerBlocked("source-only preflight requires absent output root")
    actual_interpreter = Path(interpreter_path or sys.executable).resolve().as_posix()
    if actual_interpreter.casefold() != manifest["interpreter"].casefold():
        raise TrainingRunnerBlocked("preflight interpreter differs")
    observation = dict((repo_observer or _default_repo_observer)(manifest))
    expected_observation_fields = {
        "clean",
        "head",
        "pushed",
        "runner_ancestor",
        "source_commit_bound",
        "tracked",
    }
    if (
        set(observation) != expected_observation_fields
        or observation["clean"] is not True
        or observation["tracked"] is not True
        or observation["runner_ancestor"] is not True
        or observation["source_commit_bound"] is not True
        or _commit(observation["head"], "observed repository head")
        != _commit(observation["pushed"], "observed pushed head")
    ):
        raise TrainingRunnerBlocked("preflight pushed source boundary differs")
    root = Path(manifest["repository_root"])
    payloads: dict[str, bytes] = {}
    for name in ARTIFACT_NAMES:
        binding = manifest["artifacts"][name]
        payload = reader(root / PurePosixPath(binding["path"]))
        if not _binding_matches(payload, binding):
            raise TrainingRunnerBlocked(f"preflight artifact binding differs: {name}")
        payloads[name] = payload

    training_request = _parse_canonical_mapping(
        payloads["training_request"], "training request"
    )
    try:
        control = importlib.import_module(
            "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
        )
        normalized_request = control.validate_stage_request(training_request)
    except Exception as exc:
        raise TrainingRunnerBlocked("training request validation failed") from exc
    contract = manifest["request_contract"]
    observed_contract = {
        "downstream_authority": normalized_request["downstream_authority"],
        "execution_authority": normalized_request["execution_authority"],
        "output_root": normalized_request["output_root"],
        "registration_sha256": normalized_request["prerequisite_bindings"][
            "registration_sha256"
        ],
        "request_sha256": normalized_request["request_sha256"],
        "resources": normalized_request["resources"],
        "source_commit": normalized_request["source_commit"],
        "source_inventory_sha256": normalized_request[
            "source_inventory_sha256"
        ],
    }
    if observed_contract != contract:
        raise TrainingRunnerBlocked("preflight training request contract differs")
    registration_request = _parse_canonical_mapping(
        payloads["registration_request"], "registration request"
    )
    try:
        inventory_binding = registration_request["input_bindings"]["inventory"]
    except (KeyError, TypeError) as exc:
        raise TrainingRunnerBlocked(
            "registration request inventory binding is missing"
        ) from exc
    if inventory_binding != {
        "content_kind": "canonical_json",
        **manifest["source_inventory"],
    }:
        raise TrainingRunnerBlocked("source inventory binding differs")
    _validate_rollback_authority(manifest["rollback_authority"])
    if _forbidden_imports_loaded():
        raise TrainingRunnerBlocked("source-only preflight imported runtime dependencies")
    result = {
        "authority": copy.deepcopy(manifest["downstream_authority"]),
        "checks": {
            "authorization_accessed": False,
            "checkpoint_accessed": False,
            "environment_constructed": False,
            "native_loaded": False,
            "output_absent": True,
            "output_child_accessed": False,
            "rollback_target_accessed": False,
            "runtime_loaded": False,
            "seed_inventory_accessed": False,
            "source_only_preflight_passed": True,
            "training_started": False,
        },
        "empirical_operations": copy.deepcopy(manifest["empirical_operations"]),
        "launch_manifest_sha256": manifest["manifest_sha256"],
        "schema_version": PREFLIGHT_SCHEMA_VERSION,
    }
    if len(canonical_json_bytes(result)) > PREFLIGHT_MAX_BYTES:
        raise TrainingRunnerBlocked("preflight completion exceeds byte ceiling")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight")
    preflight.add_argument("--manifest", type=Path, required=True)
    for name in ("run-training", "terminalize-dead-owner"):
        command = commands.add_parser(name)
        command.add_argument("--manifest", type=Path, required=True)
        command.add_argument("--envelope", type=Path, required=True)
        command.add_argument("--authorization", type=Path, required=True)
        command.add_argument("--approval", type=Path, required=True)
        command.add_argument("--launch-observation", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "preflight":
        sys.stdout.buffer.write(canonical_json_bytes(source_only_preflight(args.manifest)))
        return 0
    arguments = {
        "manifest_path": args.manifest,
        "envelope_path": args.envelope,
        "authorization_path": args.authorization,
        "approval_path": args.approval,
        "launch_observation_path": args.launch_observation,
    }
    if args.command == "run-training":
        result = _execute_authorized_training_command(**arguments)
    else:
        result = _execute_authorized_dead_owner_terminalization_command(
            **arguments
        )
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
