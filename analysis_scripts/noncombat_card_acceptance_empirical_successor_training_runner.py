"""Source-bound launcher for the card-acceptance paired training stage."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
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
