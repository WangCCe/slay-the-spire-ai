"""Source-bound launcher for the card-acceptance paired training stage."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping, Sequence
from typing import Any


LAUNCH_MANIFEST_SCHEMA_VERSION = (
    "noncombat-card-acceptance-training-runner-launch-manifest-v1"
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
    "registration_request",
    "registration_verifier_source",
    "runner_source",
    "runner_verifier_source",
    "runtime_source",
    "training_request",
    "training_request_review",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "torch",
    "sts_lightspeed_noncombat_adapter",
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime",
    "analysis_scripts.noncombat_simulator_adapter",
)
PREFLIGHT_MAX_BYTES = 4096

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
    owner = _mapping(binding["owner"], "terminalization owner")
    if not owner:
        raise TrainingRunnerBlocked("terminalization owner is empty")
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
        normalized_request = control.validate_stage_request(request)
        normalized_authorization = control.validate_stage_authorization(
            authorization, normalized_request
        )
    except Exception as exc:
        raise TrainingRunnerBlocked("stage authority validation failed") from exc
    contract = normalized_manifest["request_contract"]
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
        raise TrainingRunnerBlocked("authorized request differs from runner manifest")
    if (
        normalized_authorization["authorization_sha256"]
        != normalized_envelope["stage_authorization_sha256"]
        or normalized_authorization["approval_record_sha256"]
        != normalized_envelope["approval_sha256"]
    ):
        raise TrainingRunnerBlocked("command envelope stage authority differs")
    runner_observation = normalized_envelope["runner_launch_observation"]
    control_observation = runner_observation["control_observation"]
    try:
        if normalized_envelope["authority_mode"] == "standing-delegation":
            normalized_approval = control.validate_delegated_approval(
                approval, normalized_request
            )
            normalized_launch = control.validate_delegated_stage_launch(
                request=normalized_request,
                authorization=normalized_authorization,
                delegated_approval=normalized_approval,
                launch_observation=control_observation,
            )
        else:
            normalized_approval = control.validate_external_human_approval(
                approval, normalized_request
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
            normalized_launch = control.validate_external_human_stage_launch(
                request=normalized_request,
                authorization=normalized_authorization,
                external_approval=normalized_approval,
                launch_observation=control_observation,
            )
    except TrainingRunnerBlocked:
        raise
    except Exception as exc:
        raise TrainingRunnerBlocked("runner command authority validation failed") from exc
    if normalized_launch != control_observation:
        raise TrainingRunnerBlocked("runner launch observation differs")
    if normalized_approval["approval_sha256"] != normalized_envelope[
        "approval_sha256"
    ]:
        raise TrainingRunnerBlocked("runner approval identity differs")
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
        "stage_authorization_sha256": normalized_authorization[
            "authorization_sha256"
        ],
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
) -> Any:
    """Freeze the exact runner authority and rollback-bound registration."""
    required_control_operations = (
        "_build_delegated_execution_context",
        "_build_external_human_execution_context",
        "_context_identity",
        "validate_stage_authorization",
        "validate_stage_request",
    )
    if any(
        not callable(getattr(control_api, name, None))
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
        or revalidated_authority["command"] != "run-training"
    ):
        raise TrainingRunnerBlocked("training context authority differs")

    registration = _mapping(
        original_registration, "original training registration"
    )
    registration_sha256 = _digest(
        registration.get("registration_sha256"),
        "original training registration identity",
    )
    if "rollback_authority_sha256" in registration:
        raise TrainingRunnerBlocked(
            "original training registration contains execution authority"
        )
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
        normalized_request = control_api.validate_stage_request(request)
        normalized_authorization = control_api.validate_stage_authorization(
            authorization, normalized_request
        )
    except Exception as exc:
        raise TrainingRunnerBlocked("training context stage authority differs") from exc
    if (
        normalized_request["stage"] != "training"
        or normalized_request["request_sha256"]
        != manifest["request_contract"]["request_sha256"]
        or normalized_request["prerequisite_bindings"]["registration_sha256"]
        != registration_sha256
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
            context = control_api._build_delegated_execution_context(
                **context_arguments,
                delegated_approval=copy.deepcopy(dict(approval)),
            )
        else:
            context = control_api._build_external_human_execution_context(
                **context_arguments,
                external_approval=copy.deepcopy(dict(approval)),
            )
        context_identity = _mapping(
            control_api._context_identity(context),
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
    checkpoint = _parse_canonical_mapping(payload, "paired training checkpoint")
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
    return {
        "authority": copy.deepcopy(authority),
        "execution_registration": {
            **copy.deepcopy(registration),
            "rollback_authority_sha256": rollback_sha256,
        },
        "registration": copy.deepcopy(registration),
        "pre_access_receipt": receipt_binding,
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
    closeout: Callable[[str, Mapping[str, Any]], Any],
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


def _validated_reopen_observation(
    value: Mapping[str, Any],
    *,
    expected_context_identity: Mapping[str, Any],
    process_alive: Callable[[int], bool],
) -> dict[str, Any]:
    observation = _mapping(value, "read-only training reopen observation")
    _fields(
        observation,
        {"classification", "recovery"},
        "read-only training reopen observation",
    )
    classification = _mapping(
        observation["classification"], "read-only reopen classification"
    )
    recovery = _mapping(observation["recovery"], "read-only reopen recovery")
    context_identity = _mapping(
        expected_context_identity, "expected reopen context identity"
    )
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
    process_alive: Callable[[int], bool],
    observed_lease_payload: bytes | None = None,
) -> dict[str, Any]:
    """Classify a bounded lifecycle prefix without acquiring or changing it."""
    if not callable(process_alive):
        raise TrainingRunnerBlocked("read-only reopen liveness observer is invalid")
    output = Path(output_root).resolve()
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
        },
        expected_context_identity=context_identity,
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
            self.guard_path.parent.mkdir(parents=True, exist_ok=True)
            guard_handle = self.guard_path.open("a+b", buffering=0)
            guard_handle.seek(0, os.SEEK_END)
            if guard_handle.tell() == 0:
                guard_handle.write(b"\0")
                guard_handle.flush()
                os.fsync(guard_handle.fileno())
            control._lock_file(guard_handle)
            locked = True
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
    context_builder: Callable[[Mapping[str, Any]], Any],
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
    closeout: Callable[[str, Mapping[str, Any]], Any],
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
    training_seeds = registered.get("training_seeds")
    if (
        authority.get("validated") is not True
        or authority.get("command") != "run-training"
        or authority.get("envelope_sha256") != envelope_digest
        or execution_registration.get("rollback_authority_sha256")
        != rollback_digest
        or not isinstance(training_seeds, tuple)
        or len(training_seeds) != 512
        or training_seeds != tuple(sorted(set(training_seeds)))
    ):
        raise TrainingRunnerBlocked("registered training lifecycle inputs differ")
    context = context_builder(copy.deepcopy(execution_registration))
    expected_context_identity = _mapping(
        context_identity_observer(context), "training lifecycle context identity"
    )
    observed_reopen = _validated_reopen_observation(
        reopen_observer(output, context, process_alive),
        expected_context_identity=expected_context_identity,
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
            closeout=closeout,
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
    runner_commit = manifest["runner_source_commit"]
    _git_text(root, "merge-base", "--is-ancestor", runner_commit, "HEAD")
    source_commit_bound = all(
        _binding_matches(
            _git_bytes(root, "show", f"{runner_commit}:{binding['path']}"), binding
        )
        for binding in manifest["artifacts"].values()
    )
    return {
        "clean": _git_text(root, "status", "--porcelain=v1", "--", *tracked) == "",
        "head": _git_text(root, "rev-parse", "HEAD"),
        "pushed": _git_text(root, "rev-parse", manifest["pushed_ref"]),
        "runner_ancestor": True,
        "source_commit_bound": source_commit_bound,
        "tracked": observed_tracked == set(tracked),
    }


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
    raise TrainingRunnerBlocked(
        f"{args.command} is unavailable until lifecycle qualification completes"
    )


if __name__ == "__main__":
    raise SystemExit(main())
