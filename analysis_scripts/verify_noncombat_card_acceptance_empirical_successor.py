"""Independent standard-library verifier for the empirical successor."""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
import math
import random
import re
import struct
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


VERIFIER_CONTRACT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-verifier-contract-v1"
)
LEASE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-execution-lease-v1"
)
ACCESS_JOURNAL_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-access-journal-v1"
)
RESOURCE_LEDGER_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-resource-ledger-v1"
)
ARTIFACT_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-artifact-inventory-v1"
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
BOOTSTRAP_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-bootstrap-v1"
)
TRAINING_CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-training-checkpoint-v1"
)
CANARY_COMMITMENT_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-canary-commitment-v1"
)
CANARY_REPLAY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-canary-replay-v1"
)
OPTIMIZER_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-optimizer-evidence-v1"
)
CROSS_FITTED_BASELINE_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-"
    "cross-fitted-baseline-evidence-v1"
)
BASELINE_FEATURE_SCHEMA_VERSION = "cross-fitted-baseline-state-features-v1"
ROLLBACK_AUTHORITY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-rollback-authority-v1"
)
EXPERIMENT_TARGET_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-experiment-target-v1"
)
ROLLBACK_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-rollback-observation-v1"
)
SOURCE_REGISTRY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-seed-source-registry-v1"
)
SEED_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-seed-inventory-v1"
)
OUTPUT_ROOT_POLICY_VERSION = (
    "noncombat-card-acceptance-empirical-successor-output-root-policy-v1"
)

LEASE_FILENAME = ".execution.lease"
ACCESS_JOURNAL_FILENAME = "access_journal.jsonl"
RESOURCE_LEDGER_FILENAME = "resource_ledger.jsonl"
TERMINAL_INTENT_FILENAME = "terminal_intent.json"
TERMINAL_FILENAME = "terminal.json"
MANIFEST_FILENAME = "artifact_manifest.json"
ROLLBACK_OBSERVATION_FILENAME = "rollback.json"
_TERMINAL_FILENAMES = (
    TERMINAL_INTENT_FILENAME,
    TERMINAL_FILENAME,
    MANIFEST_FILENAME,
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_TOKEN_RE = re.compile(r"[0-9a-f]{32}")
_IDENTIFIER_RE = re.compile(r"[a-z0-9][a-z0-9._:-]{2,191}")
_TRAJECTORY_RE = re.compile(r"(candidate|control):seed-(0|[1-9][0-9]*)")
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
_MAX_STORED_BYTES = 256 * 1024 * 1024
_MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024

# These tuples are intentionally local: the verifier must not import its producer.
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
_RESOURCE_LIMITS = {
    "training": {
        "charged_seconds": 28_800.0,
        "environment_accesses": 1_024,
        "optimizer_steps": 16,
        "shadow_optimizer_steps": 0,
    },
    "canary": {
        "charged_seconds": 28_800.0,
        "environment_accesses": 512,
        "optimizer_steps": 0,
        "shadow_optimizer_steps": 1,
    },
    "holdout": {
        "charged_seconds": 28_800.0,
        "environment_accesses": 1_024,
        "optimizer_steps": 0,
        "shadow_optimizer_steps": 0,
    },
}
_RESOURCE_FIELDS = (
    "charged_seconds",
    "environment_accesses",
    "optimizer_steps",
    "shadow_optimizer_steps",
)
_ROLLBACK_TRIGGER_CLASSES = (
    "authority",
    "identity",
    "legality",
    "preflight",
    "canary",
    "holdout",
    "publication",
)
_INVENTORY_ROLE_COUNTS = {"training": 512, "canary": 128, "holdout": 512}
_INVENTORY_ROLE_ORDER = ("training", "canary", "holdout")
_INVENTORY_ROW_ROLES = {
    "canary",
    "consumed",
    "diagnostic",
    "evaluation",
    "failed_access",
    "holdout",
    "qualification",
    "reserved",
    "seed",
    "selected",
    "smoke",
    "training",
    "used",
}
_INVENTORY_GENERATED_ROOT_KINDS = (
    "attempt",
    "candidate",
    "scratch",
    "sealed",
    "staging",
    "temporary",
)


class VerificationError(ValueError):
    """Raised when independently observed evidence fails closed."""


def verifier_contract() -> dict[str, Any]:
    """Return a fresh verifier contract without importing successor modules."""
    return {
        "authority": {name: False for name in _AUTHORITY_NAMES},
        "producer_imported": False,
        "runtime_imported": False,
        "schema_version": VERIFIER_CONTRACT_SCHEMA_VERSION,
        "seed_inventory_imported": False,
        "standard_library_only": True,
    }


def canonical_json_bytes(value: object) -> bytes:
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise VerificationError("value is not canonical JSON") from exc
    return rendered.encode("ascii") + b"\n"


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise VerificationError("canonical JSON contains a duplicate key")
        value[key] = item
    return value


def _reject_json_constant(value: str) -> None:
    raise VerificationError(f"canonical JSON contains invalid constant: {value}")


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationError(f"{label} must be a mapping")
    return copy.deepcopy(dict(value))


def _fields(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise VerificationError(f"{label} fields mismatch")


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise VerificationError(f"{label} must be a SHA-256 digest")
    return value


def _parse_canonical_mapping(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except VerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} is invalid") from exc
    normalized = _mapping(value, label)
    if payload != canonical_json_bytes(normalized):
        raise VerificationError(f"{label} is not canonical")
    return normalized


def _runtime_canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise VerificationError("runtime value is not canonical JSON") from exc


def _parse_runtime_mapping(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except VerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} is invalid") from exc
    normalized = _mapping(value, label)
    if payload != _runtime_canonical_json_bytes(normalized):
        raise VerificationError(f"{label} is not canonical")
    return normalized


def _verify_tensor(
    value: object,
    label: str,
    *,
    expected_dtype: str | None = None,
    expected_shape: Sequence[int] | None = None,
) -> dict[str, Any]:
    tensor = _mapping(value, f"{label} tensor")
    _fields(tensor, {"dtype", "shape", "values"}, f"{label} tensor")
    dtype = tensor["dtype"]
    if dtype not in {"float32", "float64", "int64", "uint8"}:
        raise VerificationError(f"{label} tensor dtype is unsupported")
    if expected_dtype is not None and dtype != expected_dtype:
        raise VerificationError(f"{label} tensor dtype differs")
    raw_shape = tensor["shape"]
    if isinstance(raw_shape, (str, bytes)) or not isinstance(raw_shape, Sequence):
        raise VerificationError(f"{label} tensor shape is invalid")
    shape: list[int] = []
    for dimension in raw_shape:
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension < 0:
            raise VerificationError(f"{label} tensor shape is invalid")
        shape.append(dimension)
    if expected_shape is not None and shape != list(expected_shape):
        raise VerificationError(f"{label} tensor shape differs")
    values = tensor["values"]
    if isinstance(values, (str, bytes)) or not isinstance(values, list):
        raise VerificationError(f"{label} tensor values are invalid")
    expected_count = math.prod(shape) if shape else 1
    if len(values) != expected_count:
        raise VerificationError(f"{label} tensor value count differs")
    for item in values:
        if dtype.startswith("float"):
            if (
                isinstance(item, bool)
                or not isinstance(item, (int, float))
                or not math.isfinite(float(item))
            ):
                raise VerificationError(f"{label} tensor value is not finite")
        elif isinstance(item, bool) or not isinstance(item, int):
            raise VerificationError(f"{label} tensor integer value is invalid")
        elif dtype == "uint8" and not 0 <= item <= 255:
            raise VerificationError(f"{label} tensor uint8 value is invalid")
    return {"dtype": dtype, "shape": shape, "values": list(values)}


def _verify_ranker_state(value: object, label: str) -> dict[str, Any]:
    state = _mapping(value, f"{label} state")
    expected_shapes = {
        "hidden.bias": [64],
        "hidden.weight": [64, 2_048],
        "scorer.bias": [1],
        "scorer.weight": [1, 64],
    }
    _fields(state, set(expected_shapes), f"{label} state")
    return {
        name: _verify_tensor(
            state[name],
            f"{label}.{name}",
            expected_dtype="float32",
            expected_shape=shape,
        )
        for name, shape in sorted(expected_shapes.items())
    }


def verify_paired_bootstrap_bytes(value: bytes) -> dict[str, Any]:
    """Reconstruct fixed five-copy initialization without importing Torch."""
    if not isinstance(value, bytes) or not value or len(value) > _MAX_ARTIFACT_BYTES:
        raise VerificationError("paired bootstrap bytes are invalid")
    bootstrap = _parse_runtime_mapping(value, "paired bootstrap")
    _fields(
        bootstrap,
        {"architecture", "generators", "models", "schema_version"},
        "paired bootstrap",
    )
    architecture = {
        "hidden_dim": 64,
        "input_dim": 1_024,
        "model_seed": 0,
    }
    if (
        bootstrap["schema_version"] != BOOTSTRAP_SCHEMA_VERSION
        or bootstrap["architecture"] != architecture
    ):
        raise VerificationError("paired bootstrap architecture differs")
    models = _mapping(bootstrap["models"], "paired bootstrap models")
    _fields(models, {"candidate", "control"}, "paired bootstrap models")
    candidate = _mapping(models["candidate"], "candidate bootstrap models")
    control = _mapping(models["control"], "control bootstrap models")
    _fields(
        candidate,
        {"conditional_ranker", "family_head", "frozen_noncard_ranker"},
        "candidate bootstrap models",
    )
    _fields(
        control,
        {"frozen_noncard_ranker", "shared_card_ranker"},
        "control bootstrap models",
    )
    states = [
        _verify_ranker_state(candidate["family_head"], "candidate family head"),
        _verify_ranker_state(
            candidate["conditional_ranker"],
            "candidate conditional ranker",
        ),
        _verify_ranker_state(
            candidate["frozen_noncard_ranker"],
            "candidate frozen noncard ranker",
        ),
        _verify_ranker_state(control["shared_card_ranker"], "control shared ranker"),
        _verify_ranker_state(
            control["frozen_noncard_ranker"],
            "control frozen noncard ranker",
        ),
    ]
    state_bytes = [_runtime_canonical_json_bytes(state) for state in states]
    if any(encoded != state_bytes[0] for encoded in state_bytes[1:]):
        raise VerificationError("paired bootstrap model state mapping differs")
    generators = _mapping(bootstrap["generators"], "paired bootstrap generators")
    generator_names = {
        "candidate_card",
        "candidate_noncard",
        "control_card",
        "control_noncard",
    }
    _fields(generators, generator_names, "paired bootstrap generators")
    normalized_generators = {
        name: _verify_tensor(
            generators[name],
            f"paired bootstrap generator {name}",
            expected_dtype="uint8",
        )
        for name in sorted(generator_names)
    }
    if (
        normalized_generators["candidate_card"]
        != normalized_generators["control_card"]
        or normalized_generators["candidate_noncard"]
        != normalized_generators["control_noncard"]
        or normalized_generators["candidate_card"]
        == normalized_generators["candidate_noncard"]
    ):
        raise VerificationError("paired bootstrap generator mapping differs")
    return {
        "architecture": architecture,
        "generator_pairs_exact": True,
        "model_copy_count": len(states),
        "model_state_sha256": hashlib.sha256(state_bytes[0]).hexdigest(),
        "verified": True,
    }


def _checkpoint_bootstrap(value: object, label: str) -> dict[str, Any]:
    bootstrap = _mapping(value, label)
    _fields(
        bootstrap,
        {"architecture", "generators", "models", "schema_version"},
        label,
    )
    if bootstrap["schema_version"] != BOOTSTRAP_SCHEMA_VERSION or bootstrap[
        "architecture"
    ] != {"hidden_dim": 64, "input_dim": 1_024, "model_seed": 0}:
        raise VerificationError(f"{label} architecture differs")
    models = _mapping(bootstrap["models"], f"{label} models")
    _fields(models, {"candidate", "control"}, f"{label} models")
    candidate = _mapping(models["candidate"], f"{label} candidate models")
    control = _mapping(models["control"], f"{label} control models")
    _fields(
        candidate,
        {"conditional_ranker", "family_head", "frozen_noncard_ranker"},
        f"{label} candidate models",
    )
    _fields(
        control,
        {"frozen_noncard_ranker", "shared_card_ranker"},
        f"{label} control models",
    )
    normalized_models = {
        "candidate": {
            name: _verify_ranker_state(state, f"{label} candidate {name}")
            for name, state in candidate.items()
        },
        "control": {
            name: _verify_ranker_state(state, f"{label} control {name}")
            for name, state in control.items()
        },
    }
    generators = _mapping(bootstrap["generators"], f"{label} generators")
    generator_names = {
        "candidate_card",
        "candidate_noncard",
        "control_card",
        "control_noncard",
    }
    _fields(generators, generator_names, f"{label} generators")
    normalized_generators: dict[str, dict[str, Any]] = {}
    for name in sorted(generator_names):
        tensor = _verify_tensor(
            generators[name],
            f"{label} generator {name}",
            expected_dtype="uint8",
        )
        if len(tensor["shape"]) != 1:
            raise VerificationError(f"{label} generator {name} shape differs")
        normalized_generators[name] = tensor
    return {
        "architecture": copy.deepcopy(bootstrap["architecture"]),
        "generators": normalized_generators,
        "models": normalized_models,
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
    }


def _decode_optimizer_state_node(value: object, label: str) -> Any:
    node = _mapping(value, label)
    node_type = node.get("type")
    if node_type == "scalar":
        _fields(node, {"type", "value"}, label)
        scalar = node["value"]
        if scalar is not None and not isinstance(scalar, (bool, int, float, str)):
            raise VerificationError(f"{label} scalar differs")
        if isinstance(scalar, float) and not math.isfinite(scalar):
            raise VerificationError(f"{label} scalar is not finite")
        return scalar
    if node_type == "tensor":
        _fields(node, {"type", "value"}, label)
        return _verify_tensor(node["value"], label)
    if node_type in {"list", "tuple"}:
        _fields(node, {"items", "type"}, label)
        items = node["items"]
        if not isinstance(items, list):
            raise VerificationError(f"{label} items differ")
        decoded = [
            _decode_optimizer_state_node(item, f"{label}[{index}]")
            for index, item in enumerate(items)
        ]
        return tuple(decoded) if node_type == "tuple" else decoded
    if node_type == "mapping":
        _fields(node, {"items", "type"}, label)
        items = node["items"]
        if not isinstance(items, list):
            raise VerificationError(f"{label} mapping items differ")
        if items != sorted(
            items,
            key=lambda item: _runtime_canonical_json_bytes(
                _mapping(item, f"{label} mapping item").get("key")
            ),
        ):
            raise VerificationError(f"{label} mapping order differs")
        decoded_mapping: dict[Any, Any] = {}
        for index, raw_item in enumerate(items):
            item = _mapping(raw_item, f"{label} mapping item {index}")
            _fields(item, {"key", "value"}, f"{label} mapping item {index}")
            key = _decode_optimizer_state_node(
                item["key"],
                f"{label} mapping key {index}",
            )
            if isinstance(key, (dict, list, tuple)) or key in decoded_mapping:
                raise VerificationError(f"{label} mapping key differs")
            decoded_mapping[key] = _decode_optimizer_state_node(
                item["value"],
                f"{label} mapping value {index}",
            )
        return decoded_mapping
    raise VerificationError(f"{label} state node differs")


def _verify_checkpoint_optimizer(
    value: object,
    *,
    arm: str,
    expected_steps: int,
) -> None:
    decoded = _decode_optimizer_state_node(value, f"{arm} checkpoint optimizer")
    if not isinstance(decoded, dict) or set(decoded) != {"param_groups", "state"}:
        raise VerificationError(f"{arm} checkpoint optimizer fields differ")
    parameter_count = 8 if arm == "candidate" else 4
    groups = decoded["param_groups"]
    if not isinstance(groups, list) or len(groups) != 1:
        raise VerificationError(f"{arm} checkpoint optimizer group differs")
    group = groups[0]
    expected_group = {
        "amsgrad": False,
        "betas": (0.9, 0.999),
        "capturable": False,
        "differentiable": False,
        "eps": 1e-8,
        "foreach": False,
        "fused": False,
        "lr": 0.001,
        "maximize": False,
        "params": list(range(parameter_count)),
        "weight_decay": 0.0,
    }
    if group != expected_group:
        raise VerificationError(f"{arm} checkpoint optimizer ownership differs")
    state = decoded["state"]
    if not isinstance(state, dict):
        raise VerificationError(f"{arm} checkpoint Adam state differs")
    expected_indexes = set(range(parameter_count)) if expected_steps else set()
    if set(state) != expected_indexes:
        raise VerificationError(f"{arm} checkpoint Adam coverage differs")
    ranker_shapes = ([64, 2_048], [64], [1, 64], [1])
    expected_shapes = (
        list(ranker_shapes) * 2 if arm == "candidate" else list(ranker_shapes)
    )
    for index, shape in enumerate(expected_shapes):
        if not expected_steps:
            continue
        entry = state[index]
        if not isinstance(entry, dict) or set(entry) != {
            "step",
            "exp_avg",
            "exp_avg_sq",
        }:
            raise VerificationError(f"{arm} checkpoint Adam fields differ")
        step = entry["step"]
        if (
            not isinstance(step, dict)
            or step["dtype"] != "float32"
            or step["shape"] != []
            or step["values"] != [float(expected_steps)]
        ):
            raise VerificationError(f"{arm} checkpoint Adam step differs")
        for name in ("exp_avg", "exp_avg_sq"):
            moment = entry[name]
            if (
                not isinstance(moment, dict)
                or moment["dtype"] != "float32"
                or moment["shape"] != shape
            ):
                raise VerificationError(f"{arm} checkpoint Adam moment differs")


def _checkpoint_saturation(summaries: Sequence[Mapping[str, Any]]) -> bool:
    normalized: list[dict[str, Any]] = []
    for index, raw_summary in enumerate(summaries):
        summary = _mapping(raw_summary, "checkpoint chunk summary")
        _fields(
            summary,
            {"candidate_card_decisions", "chunk_index"},
            "checkpoint chunk summary",
        )
        if summary["chunk_index"] != index:
            raise VerificationError("checkpoint chunk indices differ")
        raw_decisions = summary["candidate_card_decisions"]
        if not isinstance(raw_decisions, list) or not raw_decisions:
            raise VerificationError("checkpoint family diagnostics differ")
        decisions: list[dict[str, Any]] = []
        for raw_decision in raw_decisions:
            decision = _mapping(raw_decision, "checkpoint family diagnostic")
            _fields(
                decision,
                {"multi_family", "unique_greedy_family_id"},
                "checkpoint family diagnostic",
            )
            family = decision["unique_greedy_family_id"]
            if not isinstance(decision["multi_family"], bool) or (
                family is not None and (not isinstance(family, str) or not family)
            ):
                raise VerificationError("checkpoint family diagnostic differs")
            decisions.append(decision)
        normalized.append(
            {"candidate_card_decisions": decisions, "chunk_index": index}
        )
    window = normalized[-4:]
    if len(window) < 4:
        return False
    rows = [
        row
        for chunk in window
        for row in chunk["candidate_card_decisions"]
        if row["multi_family"] is True
    ]
    families = [row["unique_greedy_family_id"] for row in rows]
    return (
        len(rows) >= 64
        and all(isinstance(family, str) and family for family in families)
        and len(set(families)) == 1
    )


def verify_paired_training_checkpoint_bytes(
    value: bytes,
    *,
    initial_bootstrap_bytes: bytes,
) -> dict[str, Any]:
    """Verify complete-boundary coordinates, Adam state, and frozen bytes."""
    verify_paired_bootstrap_bytes(initial_bootstrap_bytes)
    initial = _checkpoint_bootstrap(
        _parse_runtime_mapping(initial_bootstrap_bytes, "initial bootstrap"),
        "initial bootstrap",
    )
    if not isinstance(value, bytes) or not value or len(value) > _MAX_ARTIFACT_BYTES:
        raise VerificationError("paired training checkpoint bytes are invalid")
    checkpoint = _parse_runtime_mapping(value, "paired training checkpoint")
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
    if checkpoint["schema_version"] != TRAINING_CHECKPOINT_SCHEMA_VERSION:
        raise VerificationError("paired training checkpoint schema differs")
    current = _checkpoint_bootstrap(checkpoint["bootstrap"], "checkpoint bootstrap")
    initial_frozen = initial["models"]["candidate"]["frozen_noncard_ranker"]
    candidate_frozen = current["models"]["candidate"]["frozen_noncard_ranker"]
    control_frozen = current["models"]["control"]["frozen_noncard_ranker"]
    if candidate_frozen != initial_frozen or control_frozen != initial_frozen:
        raise VerificationError("checkpoint frozen non-card bytes differ")
    coordinates = _mapping(checkpoint["coordinates"], "checkpoint coordinates")
    coordinate_fields = {
        "candidate_optimizer_updates",
        "completed_decisions",
        "completed_pairs",
        "control_optimizer_updates",
        "next_chunk_index",
        "training_environment_accesses",
        "training_optimizer_steps",
    }
    _fields(coordinates, coordinate_fields, "checkpoint coordinates")
    for name in coordinate_fields:
        coordinates[name] = _inventory_nonnegative(
            coordinates[name],
            f"checkpoint coordinate {name}",
        )
    chunk_count = coordinates["next_chunk_index"]
    if chunk_count > 8 or (
        coordinates["completed_pairs"] != 64 * chunk_count
        or coordinates["training_environment_accesses"] != 128 * chunk_count
        or coordinates["candidate_optimizer_updates"] != chunk_count
        or coordinates["control_optimizer_updates"] != chunk_count
        or coordinates["training_optimizer_steps"] != 2 * chunk_count
        or coordinates["completed_decisions"]
        < coordinates["training_environment_accesses"]
        or coordinates["completed_decisions"]
        > coordinates["training_environment_accesses"] * 500
    ):
        raise VerificationError("checkpoint resource coordinates differ")
    summaries = checkpoint["completed_chunk_summaries"]
    if not isinstance(summaries, list) or len(summaries) != chunk_count:
        raise VerificationError("checkpoint chunk summaries differ")
    saturation = _checkpoint_saturation(summaries)
    if checkpoint["stopped_for_family_saturation"] is not saturation:
        raise VerificationError("checkpoint family saturation differs")
    optimizers = _mapping(checkpoint["optimizers"], "checkpoint optimizers")
    _fields(optimizers, {"candidate", "control"}, "checkpoint optimizers")
    _verify_checkpoint_optimizer(
        optimizers["candidate"],
        arm="candidate",
        expected_steps=chunk_count,
    )
    _verify_checkpoint_optimizer(
        optimizers["control"],
        arm="control",
        expected_steps=chunk_count,
    )
    return {
        "candidate_optimizer_updates": chunk_count,
        "completed_pairs": coordinates["completed_pairs"],
        "control_optimizer_updates": chunk_count,
        "frozen_noncard_verified": True,
        "next_chunk_index": chunk_count,
        "stopped_for_family_saturation": saturation,
        "verified": True,
    }


def _finite_scalar_tensor(value: object, label: str) -> float:
    tensor = _verify_tensor(
        value,
        label,
        expected_dtype="float64",
        expected_shape=(),
    )
    return float(tensor["values"][0])


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-12)


def _verify_canary_card_terms(
    value: object,
    *,
    selected_action_id: str,
    candidates: Sequence[Mapping[str, Any]],
    label: str,
) -> tuple[str, str | None] | None:
    terms = _mapping(value, f"{label} card terms")
    _fields(
        terms,
        {
            "action_ids",
            "candidate_families",
            "conditional_log_probabilities",
            "conditional_probabilities",
            "family_entropy",
            "family_log_probabilities",
            "family_order",
            "family_probabilities",
            "selected_action_id",
            "selected_conditional_log_probability",
            "selected_family",
            "selected_family_log_probability",
            "two_stage_greedy_action_ids",
            "unique_greedy_family_id",
            "unique_two_stage_greedy_action_id",
        },
        f"{label} card terms",
    )
    action_ids = terms["action_ids"]
    candidate_families = terms["candidate_families"]
    family_order = terms["family_order"]
    if (
        not isinstance(action_ids, list)
        or not action_ids
        or len(set(action_ids)) != len(action_ids)
        or any(not isinstance(item, str) or not item for item in action_ids)
        or not isinstance(candidate_families, list)
        or len(candidate_families) != len(action_ids)
        or any(not isinstance(item, str) or not item for item in candidate_families)
        or not isinstance(family_order, list)
        or family_order != sorted(set(family_order))
        or set(candidate_families) != set(family_order)
    ):
        raise VerificationError(f"{label} card family mapping is invalid")
    candidate_action_ids = [candidate.get("action_id") for candidate in candidates]
    if candidate_action_ids != action_ids:
        raise VerificationError(f"{label} candidate action mapping differs")
    if terms["selected_action_id"] != selected_action_id or selected_action_id not in action_ids:
        raise VerificationError(f"{label} selected action differs")
    family_count = len(family_order)
    action_count = len(action_ids)
    family_probabilities = _verify_tensor(
        terms["family_probabilities"],
        f"{label} family probabilities",
        expected_dtype="float64",
        expected_shape=(family_count,),
    )["values"]
    family_logs = _verify_tensor(
        terms["family_log_probabilities"],
        f"{label} family log probabilities",
        expected_dtype="float64",
        expected_shape=(family_count,),
    )["values"]
    conditional_probabilities = _verify_tensor(
        terms["conditional_probabilities"],
        f"{label} conditional probabilities",
        expected_dtype="float64",
        expected_shape=(action_count,),
    )["values"]
    conditional_logs = _verify_tensor(
        terms["conditional_log_probabilities"],
        f"{label} conditional log probabilities",
        expected_dtype="float64",
        expected_shape=(action_count,),
    )["values"]
    if (
        any(probability <= 0.0 for probability in family_probabilities)
        or not _close(sum(family_probabilities), 1.0)
        or any(
            not _close(math.log(probability), float(log_probability))
            for probability, log_probability in zip(
                family_probabilities,
                family_logs,
                strict=True,
            )
        )
    ):
        raise VerificationError(f"{label} family probabilities differ")
    for family in family_order:
        indexes = [
            index
            for index, candidate_family in enumerate(candidate_families)
            if candidate_family == family
        ]
        if (
            any(conditional_probabilities[index] <= 0.0 for index in indexes)
            or not _close(sum(conditional_probabilities[index] for index in indexes), 1.0)
            or any(
                not _close(
                    math.log(conditional_probabilities[index]),
                    float(conditional_logs[index]),
                )
                for index in indexes
            )
        ):
            raise VerificationError(f"{label} conditional probabilities differ")
    expected_entropy = -sum(
        probability * math.log(probability)
        for probability in family_probabilities
    )
    if not _close(
        _finite_scalar_tensor(terms["family_entropy"], f"{label} family entropy"),
        expected_entropy,
    ):
        raise VerificationError(f"{label} family entropy differs")
    selected_index = action_ids.index(selected_action_id)
    selected_family = terms["selected_family"]
    if selected_family != candidate_families[selected_index]:
        raise VerificationError(f"{label} selected family differs")
    selected_family_index = family_order.index(selected_family)
    if not _close(
        _finite_scalar_tensor(
            terms["selected_family_log_probability"],
            f"{label} selected family log probability",
        ),
        float(family_logs[selected_family_index]),
    ) or not _close(
        _finite_scalar_tensor(
            terms["selected_conditional_log_probability"],
            f"{label} selected conditional log probability",
        ),
        float(conditional_logs[selected_index]),
    ):
        raise VerificationError(f"{label} selected probability term differs")
    maximum_family_probability = max(family_probabilities)
    greedy_families = [
        family_order[index]
        for index, probability in enumerate(family_probabilities)
        if probability == maximum_family_probability
    ]
    expected_unique_family = greedy_families[0] if len(greedy_families) == 1 else None
    if terms["unique_greedy_family_id"] != expected_unique_family:
        raise VerificationError(f"{label} unique greedy family differs")
    if family_count < 2:
        return None
    return selected_family, expected_unique_family


def _verify_canary_output(
    output: Mapping[str, Any],
    *,
    arm: str,
    seed: int,
) -> tuple[list[str], list[str]]:
    _fields(output, {"arm", "decisions", "seed", "terminal"}, "canary output")
    if output["arm"] != arm or output["seed"] != seed:
        raise VerificationError("canary output coordinate differs")
    decisions = output["decisions"]
    if not isinstance(decisions, list) or not 1 <= len(decisions) <= 500:
        raise VerificationError("canary output decision count is invalid")
    selected_families: list[str] = []
    greedy_families: list[str] = []
    for index, raw_decision in enumerate(decisions):
        decision = _mapping(raw_decision, "canary decision")
        _fields(
            decision,
            {
                "candidate_features",
                "candidates",
                "card_terms",
                "category",
                "decision_id",
                "decision_index",
                "diagnostic",
                "selected_action_id",
                "state_features",
            },
            "canary decision",
        )
        if (
            decision["decision_index"] != index
            or decision["decision_id"] != f"{arm}:seed-{seed}:decision-{index}"
            or not isinstance(decision["selected_action_id"], str)
            or not isinstance(decision["diagnostic"], Mapping)
        ):
            raise VerificationError("canary decision coordinate differs")
        _verify_tensor(decision["state_features"], "canary state features")
        candidates = decision["candidates"]
        if not isinstance(candidates, list) or any(
            not isinstance(candidate, Mapping) for candidate in candidates
        ):
            raise VerificationError("canary decision candidates are invalid")
        if decision["category"] == "card_reward":
            if decision["candidate_features"] is None:
                raise VerificationError("canary card candidate features are absent")
            _verify_tensor(
                decision["candidate_features"],
                "canary candidate features",
            )
            observation = _verify_canary_card_terms(
                decision["card_terms"],
                selected_action_id=decision["selected_action_id"],
                candidates=candidates,
                label=f"canary decision {index}",
            )
            if arm == "candidate" and observation is not None:
                selected, greedy = observation
                selected_families.append(selected)
                if greedy is not None:
                    greedy_families.append(greedy)
        elif decision["card_terms"] is not None:
            raise VerificationError("canary non-card decision has card terms")
    terminal = _mapping(output["terminal"], "canary terminal")
    _fields(
        terminal,
        {
            "final_snapshot",
            "floor_progress",
            "rewards",
            "terminal_victory",
            "trajectory_id",
            "transitions",
            "unsupported_reason",
        },
        "canary terminal",
    )
    if (
        terminal["trajectory_id"] != f"{arm}:seed-{seed}"
        or terminal["unsupported_reason"] is not None
        or isinstance(terminal["terminal_victory"], bool)
        or not isinstance(terminal["terminal_victory"], int)
        or terminal["terminal_victory"] not in {0, 1}
        or not isinstance(terminal["final_snapshot"], Mapping)
        or terminal["final_snapshot"].get("terminal") is not True
    ):
        raise VerificationError("canary terminal differs")
    return selected_families, greedy_families


def _family_concentration(values: Sequence[str]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    denominator = len(values)
    maximum_count = max(counts.values(), default=0)
    maximum_rate = 0.0 if denominator == 0 else maximum_count / denominator
    return {
        "counts": {key: counts[key] for key in sorted(counts)},
        "denominator": denominator,
        "family_count": len(counts),
        "maximum_count": maximum_count,
        "maximum_rate": maximum_rate,
        "passed": (
            denominator >= 64
            and len(counts) >= 2
            and maximum_rate <= 0.95
        ),
    }


def verify_canary_evidence(
    *,
    artifact_root: Path | str,
    seeds: Sequence[int],
    arm_bindings: Mapping[str, Mapping[str, str]],
    commitments: Sequence[Mapping[str, Any]],
    replays: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify first-output artifacts, hash chain, replay receipts, and gates."""
    root = Path(artifact_root).resolve()
    normalized_seeds = tuple(seeds)
    if (
        len(normalized_seeds) != 128
        or normalized_seeds != tuple(sorted(set(normalized_seeds)))
        or any(
            isinstance(seed, bool) or not isinstance(seed, int) or seed < 0
            for seed in normalized_seeds
        )
    ):
        raise VerificationError("canary seeds differ from the fixed schedule")
    bindings = _mapping(arm_bindings, "canary arm bindings")
    _fields(bindings, {"candidate", "control"}, "canary arm bindings")
    for arm in ("candidate", "control"):
        binding = _mapping(bindings[arm], f"{arm} canary arm binding")
        _fields(
            binding,
            {"checkpoint_sha256", "configuration_sha256", "source_sha256"},
            f"{arm} canary arm binding",
        )
        for name, digest in binding.items():
            _digest(digest, f"{arm} {name}")
        bindings[arm] = binding
    if len(commitments) != 256 or len(replays) != 256:
        raise VerificationError("canary commitment or replay count differs")
    previous = "0" * 64
    selected_families: list[str] = []
    greedy_families: list[str] = []
    normalized_commitments: list[dict[str, Any]] = []
    for sequence_index, raw_commitment in enumerate(commitments):
        commitment = _mapping(raw_commitment, "canary commitment")
        _fields(
            commitment,
            {
                "arm",
                "arm_binding",
                "commitment_sha256",
                "output_artifact",
                "output_sha256",
                "previous_commitment_sha256",
                "schema_version",
                "seed",
                "seed_index",
                "sequence_index",
            },
            "canary commitment",
        )
        seed_index = sequence_index // 2
        arm = "candidate" if sequence_index % 2 == 0 else "control"
        seed = normalized_seeds[seed_index]
        body = {
            key: value
            for key, value in commitment.items()
            if key != "commitment_sha256"
        }
        if (
            commitment["schema_version"] != CANARY_COMMITMENT_SCHEMA_VERSION
            or commitment["sequence_index"] != sequence_index
            or commitment["seed_index"] != seed_index
            or commitment["seed"] != seed
            or commitment["arm"] != arm
            or commitment["arm_binding"] != bindings[arm]
            or commitment["previous_commitment_sha256"] != previous
            or commitment["commitment_sha256"]
            != hashlib.sha256(_runtime_canonical_json_bytes(body)).hexdigest()
        ):
            raise VerificationError("canary commitment chain differs")
        artifact = _mapping(commitment["output_artifact"], "canary output artifact")
        expected_path = f"canary/outputs/{sequence_index:04d}-{arm}.json.gz"
        if artifact.get("path") != expected_path:
            raise VerificationError("canary output artifact path differs")
        observed_artifact = _artifact_binding(root, expected_path)
        if artifact != observed_artifact or artifact.get("encoding") != "deterministic-gzip-v1":
            raise VerificationError("canary output artifact binding differs")
        try:
            stored = root.joinpath(*PurePosixPath(expected_path).parts).read_bytes()
        except OSError as exc:
            raise VerificationError("canary output artifact cannot be read") from exc
        output_bytes = _bounded_gzip_payload(stored)
        if commitment["output_sha256"] != hashlib.sha256(output_bytes).hexdigest():
            raise VerificationError("canary output digest differs")
        output = _parse_runtime_mapping(output_bytes, "canary output")
        selected, greedy = _verify_canary_output(output, arm=arm, seed=seed)
        selected_families.extend(selected)
        greedy_families.extend(greedy)
        normalized_commitments.append(commitment)
        previous = commitment["commitment_sha256"]
    for sequence_index, raw_replay in enumerate(replays):
        replay = _mapping(raw_replay, "canary replay")
        _fields(
            replay,
            {
                "arm",
                "first_commitment_sha256",
                "output_sha256",
                "replay_sha256",
                "schema_version",
                "seed",
                "seed_index",
                "sequence_index",
            },
            "canary replay",
        )
        commitment = normalized_commitments[sequence_index]
        body = {key: value for key, value in replay.items() if key != "replay_sha256"}
        if (
            replay["schema_version"] != CANARY_REPLAY_SCHEMA_VERSION
            or replay["sequence_index"] != sequence_index
            or replay["seed_index"] != commitment["seed_index"]
            or replay["seed"] != commitment["seed"]
            or replay["arm"] != commitment["arm"]
            or replay["first_commitment_sha256"] != commitment["commitment_sha256"]
            or replay["output_sha256"] != commitment["output_sha256"]
            or replay["replay_sha256"]
            != hashlib.sha256(_runtime_canonical_json_bytes(body)).hexdigest()
        ):
            raise VerificationError("canary replay receipt differs")
    selected_gate = _family_concentration(selected_families)
    greedy_gate = _family_concentration(greedy_families)
    concentration = {
        "passed": selected_gate["passed"] and greedy_gate["passed"],
        "selected_family": selected_gate,
        "unique_greedy_family": greedy_gate,
    }
    return {
        "commitment_count": len(normalized_commitments),
        "concentration": concentration,
        "replay_count": len(replays),
        "verified": True,
    }


def _paired_floor_bootstrap(differences: Sequence[float]) -> dict[str, Any]:
    if len(differences) != 512:
        raise VerificationError("holdout bootstrap requires 512 pairs")
    generator = random.Random(0)
    means: list[float] = []
    for _ in range(10_000):
        total = 0.0
        for _ in range(512):
            total += differences[generator.randrange(512)]
        means.append(total / 512)
    means.sort()

    def quantile(probability: float) -> float:
        position = (10_000 - 1) * probability
        lower = math.floor(position)
        upper = math.ceil(position)
        fraction = position - lower
        return means[lower] + fraction * (means[upper] - means[lower])

    return {
        "bootstrap_seed": 0,
        "lower": quantile(0.025),
        "pair_count": 512,
        "quantile_method": "linear-position-(n-1)-p-v1",
        "resample_count": 10_000,
        "upper": quantile(0.975),
    }


def _holdout_outcome(
    candidate_victories: int,
    control_victories: int,
    paired_floor_lower: float,
) -> tuple[str, str, bool]:
    if candidate_victories > control_victories:
        comparison = "greater"
    elif candidate_victories == control_victories:
        comparison = "equal"
    else:
        comparison = "fewer"
    floor_signal = paired_floor_lower > 0.0
    truth_table = {
        ("greater", True): "victory_and_floor_signal",
        ("equal", True): "floor_only_signal",
        ("greater", False): "inconclusive_signal",
        ("fewer", True): "inconclusive_signal",
        ("equal", False): "no_learning_signal",
        ("fewer", False): "no_learning_signal",
    }
    return truth_table[(comparison, floor_signal)], comparison, floor_signal


def verify_holdout_evidence(value: object) -> dict[str, Any]:
    """Reconstruct untouched pairs, concentration, bootstrap, and six cells."""
    evidence = _mapping(value, "holdout evidence")
    _fields(
        evidence,
        {
            "arm_bindings",
            "bootstrap",
            "concentration",
            "family_observations",
            "outcome_class",
            "pairs",
            "resource_use",
            "seeds",
            "verdict",
            "verified_canary",
            "victory_counts",
        },
        "holdout evidence",
    )
    seeds = evidence["seeds"]
    if (
        not isinstance(seeds, (list, tuple))
        or len(seeds) != 512
        or tuple(seeds) != tuple(sorted(set(seeds)))
        or any(isinstance(seed, bool) or not isinstance(seed, int) or seed < 0 for seed in seeds)
    ):
        raise VerificationError("holdout seeds differ from the fixed schedule")
    normalized_seeds = tuple(seeds)
    bindings = _mapping(evidence["arm_bindings"], "holdout arm bindings")
    _fields(bindings, {"candidate", "control"}, "holdout arm bindings")
    for arm in ("candidate", "control"):
        binding = _mapping(bindings[arm], f"{arm} holdout arm binding")
        _fields(
            binding,
            {"checkpoint_sha256", "configuration_sha256", "source_sha256"},
            f"{arm} holdout arm binding",
        )
        for name, digest in binding.items():
            _digest(digest, f"{arm} holdout {name}")
    canary = _mapping(evidence["verified_canary"], "verified canary")
    _fields(canary, {"terminal_sha256", "verdict", "verified"}, "verified canary")
    if (
        _digest(canary["terminal_sha256"], "verified canary terminal")
        != canary["terminal_sha256"]
        or canary["verdict"] != "canary_passed"
        or canary["verified"] is not True
    ):
        raise VerificationError("verified canary prerequisite differs")
    resource_use = _mapping(evidence["resource_use"], "holdout resource use")
    if resource_use != {"holdout_environment_accesses": 1_024}:
        raise VerificationError("holdout resource use differs")
    raw_pairs = evidence["pairs"]
    if not isinstance(raw_pairs, (list, tuple)) or len(raw_pairs) != 512:
        raise VerificationError("holdout pair count differs")
    pair_fields = {
        "candidate_floor_progress",
        "candidate_output_sha256",
        "candidate_victory",
        "control_floor_progress",
        "control_output_sha256",
        "control_victory",
        "floor_progress_difference",
        "seed",
        "seed_index",
    }
    differences: list[float] = []
    candidate_victories = 0
    control_victories = 0
    for seed_index, raw_pair in enumerate(raw_pairs):
        pair = _mapping(raw_pair, "holdout pair")
        _fields(pair, pair_fields, "holdout pair")
        if pair["seed_index"] != seed_index or pair["seed"] != normalized_seeds[seed_index]:
            raise VerificationError("holdout pair coordinate differs")
        _digest(pair["candidate_output_sha256"], "candidate holdout output")
        _digest(pair["control_output_sha256"], "control holdout output")
        values: list[float] = []
        for name in (
            "candidate_floor_progress",
            "control_floor_progress",
            "floor_progress_difference",
        ):
            raw = pair[name]
            if (
                isinstance(raw, bool)
                or not isinstance(raw, (int, float))
                or not math.isfinite(float(raw))
            ):
                raise VerificationError("holdout pair floor value is invalid")
            values.append(float(raw))
        expected_difference = values[0] - values[1]
        if not _close(values[2], expected_difference):
            raise VerificationError("holdout pair floor difference differs")
        for name in ("candidate_victory", "control_victory"):
            if (
                isinstance(pair[name], bool)
                or not isinstance(pair[name], int)
                or pair[name] not in {0, 1}
            ):
                raise VerificationError("holdout pair victory is invalid")
        candidate_victories += pair["candidate_victory"]
        control_victories += pair["control_victory"]
        differences.append(values[2])
    observations = evidence["family_observations"]
    if not isinstance(observations, (list, tuple)):
        raise VerificationError("holdout family observations are invalid")
    normalized_observations: list[dict[str, Any]] = []
    selected_families: list[str] = []
    greedy_families: list[str] = []
    observation_fields = {
        "decision_id",
        "decision_index",
        "family_order",
        "seed",
        "selected_family",
        "unique_greedy_family_id",
    }
    for raw_observation in observations:
        observation = _mapping(raw_observation, "holdout family observation")
        _fields(observation, observation_fields, "holdout family observation")
        seed = observation["seed"]
        decision_index = observation["decision_index"]
        family_order = observation["family_order"]
        if (
            seed not in normalized_seeds
            or isinstance(decision_index, bool)
            or not isinstance(decision_index, int)
            or not 0 <= decision_index < 500
            or observation["decision_id"]
            != f"candidate:seed-{seed}:decision-{decision_index}"
            or not isinstance(family_order, list)
            or len(family_order) < 2
            or family_order != sorted(set(family_order))
            or observation["selected_family"] not in family_order
            or (
                observation["unique_greedy_family_id"] is not None
                and observation["unique_greedy_family_id"] not in family_order
            )
        ):
            raise VerificationError("holdout family observation differs")
        selected_families.append(observation["selected_family"])
        if observation["unique_greedy_family_id"] is not None:
            greedy_families.append(observation["unique_greedy_family_id"])
        normalized_observations.append(observation)
    expected_order = sorted(
        normalized_observations,
        key=lambda row: (row["seed"], row["decision_index"], row["decision_id"]),
    )
    if normalized_observations != expected_order:
        raise VerificationError("holdout family observations are not canonical")
    selected_gate = _family_concentration(selected_families)
    greedy_gate = _family_concentration(greedy_families)
    concentration = {
        "passed": selected_gate["passed"] and greedy_gate["passed"],
        "selected_family": selected_gate,
        "unique_greedy_family": greedy_gate,
    }
    if evidence["concentration"] != concentration:
        raise VerificationError("holdout concentration differs")
    expected_counts = {
        "candidate": candidate_victories,
        "control": control_victories,
    }
    if evidence["victory_counts"] != expected_counts:
        raise VerificationError("holdout victory counts differ")
    if not concentration["passed"]:
        if (
            evidence["verdict"] != "holdout_failed_concentration"
            or evidence["bootstrap"] is not None
            or evidence["outcome_class"] is not None
        ):
            raise VerificationError("holdout concentration failure differs")
        return {
            "bootstrap": None,
            "outcome_class": None,
            "pair_count": 512,
            "truth_table": {},
            "verified": True,
        }
    bootstrap = _paired_floor_bootstrap(differences)
    if evidence["bootstrap"] != bootstrap:
        raise VerificationError("holdout bootstrap differs")
    outcome, _comparison, _floor_signal = _holdout_outcome(
        candidate_victories,
        control_victories,
        float(bootstrap["lower"]),
    )
    if (
        evidence["verdict"] != "holdout_completed"
        or evidence["outcome_class"] != outcome
    ):
        raise VerificationError("holdout outcome class differs")
    truth_table = {
        f"{comparison}:{str(signal).lower()}": _holdout_outcome(
            2 if comparison == "greater" else (1 if comparison == "equal" else 0),
            1,
            1.0 if signal else 0.0,
        )[0]
        for comparison in ("equal", "fewer", "greater")
        for signal in (False, True)
    }
    return {
        "bootstrap": bootstrap,
        "outcome_class": outcome,
        "pair_count": 512,
        "truth_table": truth_table,
        "verified": True,
    }


def _finite_number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise VerificationError(f"{label} must be finite")
    return float(value)


def _numeric_vector(
    value: object,
    *,
    count: int,
    label: str,
) -> list[float]:
    if not isinstance(value, list) or len(value) != count:
        raise VerificationError(f"{label} shape differs")
    return [_finite_number(item, f"{label} value") for item in value]


def _verify_adam_state(
    value: object,
    *,
    count: int,
    label: str,
) -> dict[str, Any]:
    state = _mapping(value, label)
    _fields(state, {"exp_avg", "exp_avg_sq", "step"}, label)
    step = state["step"]
    if isinstance(step, bool) or not isinstance(step, int) or step < 0:
        raise VerificationError(f"{label} step is invalid")
    return {
        "exp_avg": _numeric_vector(state["exp_avg"], count=count, label=f"{label} exp_avg"),
        "exp_avg_sq": _numeric_vector(
            state["exp_avg_sq"],
            count=count,
            label=f"{label} exp_avg_sq",
        ),
        "step": step,
    }


def verify_objective_and_adam_evidence(value: object) -> dict[str, Any]:
    """Recompute four losses, gradient ownership/clipping, and fixed Adam."""
    evidence = _mapping(value, "optimizer evidence")
    _fields(
        evidence,
        {
            "arm",
            "card_decisions",
            "component_order",
            "gradient_norm_ceiling",
            "optimizer",
            "parameters",
            "postclip_global_norm",
            "preclip_global_norm",
            "reported_components",
            "reported_total_loss",
            "schema_version",
        },
        "optimizer evidence",
    )
    if evidence["schema_version"] != OPTIMIZER_EVIDENCE_SCHEMA_VERSION:
        raise VerificationError("optimizer evidence schema differs")
    arm = evidence["arm"]
    if arm not in {"candidate", "control"}:
        raise VerificationError("optimizer evidence arm differs")
    component_order = [
        "family_policy",
        "conditional_policy",
        "family_entropy",
        "conditional_entropy",
    ]
    if evidence["component_order"] != component_order:
        raise VerificationError("optimizer component order differs")
    decisions = evidence["card_decisions"]
    if not isinstance(decisions, list) or not decisions:
        raise VerificationError("optimizer evidence has no card decisions")
    family_policy_values: list[float] = []
    conditional_policy_values: list[float] = []
    family_entropies: list[float] = []
    conditional_entropies: list[float] = []
    decision_fields = {
        "advantage",
        "family_entropy",
        "per_family_conditional_entropies",
        "selected_conditional_log_probability",
        "selected_family_log_probability",
    }
    for raw_decision in decisions:
        decision = _mapping(raw_decision, "optimizer card decision")
        _fields(decision, decision_fields, "optimizer card decision")
        advantage = _finite_number(decision["advantage"], "card advantage")
        family_log = _finite_number(
            decision["selected_family_log_probability"],
            "selected family log probability",
        )
        conditional_log = _finite_number(
            decision["selected_conditional_log_probability"],
            "selected conditional log probability",
        )
        family_entropy = _finite_number(
            decision["family_entropy"],
            "family entropy",
        )
        per_family = decision["per_family_conditional_entropies"]
        if not isinstance(per_family, list) or not per_family:
            raise VerificationError("per-family conditional entropies are invalid")
        normalized_per_family = [
            _finite_number(item, "per-family conditional entropy")
            for item in per_family
        ]
        family_policy_values.append(-advantage * family_log)
        conditional_policy_values.append(-advantage * conditional_log)
        family_entropies.append(family_entropy)
        conditional_entropies.append(
            sum(normalized_per_family) / len(normalized_per_family)
        )
    count = len(decisions)
    components = {
        "family_policy": sum(family_policy_values) / count,
        "conditional_policy": sum(conditional_policy_values) / count,
        "family_entropy": -0.01 * sum(family_entropies) / count,
        "conditional_entropy": -0.01 * sum(conditional_entropies) / count,
    }
    reported_components = _mapping(
        evidence["reported_components"],
        "reported optimizer components",
    )
    _fields(reported_components, set(component_order), "reported optimizer components")
    for name in component_order:
        if not _close(
            _finite_number(reported_components[name], f"reported {name}"),
            components[name],
        ):
            raise VerificationError("reported optimizer loss component differs")
    total_loss = sum(components[name] for name in component_order)
    if not _close(
        _finite_number(evidence["reported_total_loss"], "reported total loss"),
        total_loss,
    ):
        raise VerificationError("reported optimizer total loss differs")
    optimizer = _mapping(evidence["optimizer"], "optimizer controls")
    expected_optimizer = {
        "betas": [0.9, 0.999],
        "eps": 1e-8,
        "learning_rate": 0.001,
        "name": "adam",
        "weight_decay": 0.0,
    }
    if optimizer != expected_optimizer or evidence["gradient_norm_ceiling"] != 1.0:
        raise VerificationError("optimizer controls differ")
    parameters = evidence["parameters"]
    if not isinstance(parameters, list) or not parameters:
        raise VerificationError("optimizer parameter evidence is invalid")
    parameter_fields = {
        "adam_after",
        "adam_before",
        "applied_gradient",
        "combined_gradient",
        "component_gradients",
        "name",
        "owner",
        "post_parameter",
        "pre_parameter",
        "shape",
    }
    names: list[str] = []
    prepared: list[dict[str, Any]] = []
    all_combined: list[float] = []
    for raw_parameter in parameters:
        parameter = _mapping(raw_parameter, "optimizer parameter")
        _fields(parameter, parameter_fields, "optimizer parameter")
        name = parameter["name"]
        owner = parameter["owner"]
        if not isinstance(name, str) or not name or owner not in {
            "family",
            "conditional",
            "shared",
        }:
            raise VerificationError("optimizer parameter ownership differs")
        if (arm == "candidate" and owner == "shared") or (
            arm == "control" and owner != "shared"
        ):
            raise VerificationError("optimizer arm parameter ownership differs")
        shape = parameter["shape"]
        if (
            not isinstance(shape, list)
            or any(
                isinstance(dimension, bool)
                or not isinstance(dimension, int)
                or dimension < 0
                for dimension in shape
            )
        ):
            raise VerificationError("optimizer parameter shape differs")
        element_count = math.prod(shape) if shape else 1
        if element_count <= 0:
            raise VerificationError("optimizer parameter is empty")
        pre_parameter = _numeric_vector(
            parameter["pre_parameter"],
            count=element_count,
            label=f"{name} pre parameter",
        )
        post_parameter = _numeric_vector(
            parameter["post_parameter"],
            count=element_count,
            label=f"{name} post parameter",
        )
        component_gradients = _mapping(
            parameter["component_gradients"],
            f"{name} component gradients",
        )
        _fields(
            component_gradients,
            set(component_order),
            f"{name} component gradients",
        )
        forbidden = (
            {"conditional_policy", "conditional_entropy"}
            if owner == "family"
            else (
                {"family_policy", "family_entropy"}
                if owner == "conditional"
                else set()
            )
        )
        normalized_components: dict[str, list[float] | None] = {}
        for component in component_order:
            raw_gradient = component_gradients[component]
            if component in forbidden and raw_gradient is not None:
                raise VerificationError("optimizer gradient ownership differs")
            normalized_components[component] = (
                None
                if raw_gradient is None
                else _numeric_vector(
                    raw_gradient,
                    count=element_count,
                    label=f"{name} {component} gradient",
                )
            )
        reconstructed = [0.0] * element_count
        for gradient in normalized_components.values():
            if gradient is not None:
                reconstructed = [
                    left + right
                    for left, right in zip(reconstructed, gradient, strict=True)
                ]
        combined = _numeric_vector(
            parameter["combined_gradient"],
            count=element_count,
            label=f"{name} combined gradient",
        )
        if any(
            not _close(left, right)
            for left, right in zip(reconstructed, combined, strict=True)
        ):
            raise VerificationError("optimizer combined gradient differs")
        applied = _numeric_vector(
            parameter["applied_gradient"],
            count=element_count,
            label=f"{name} applied gradient",
        )
        before = _verify_adam_state(
            parameter["adam_before"],
            count=element_count,
            label=f"{name} Adam before",
        )
        after = _verify_adam_state(
            parameter["adam_after"],
            count=element_count,
            label=f"{name} Adam after",
        )
        names.append(name)
        all_combined.extend(combined)
        prepared.append(
            {
                "after": after,
                "applied": applied,
                "before": before,
                "name": name,
                "post": post_parameter,
                "pre": pre_parameter,
            }
        )
    if len(set(names)) != len(names):
        raise VerificationError("optimizer parameter names are not unique")
    preclip_norm = math.sqrt(sum(value * value for value in all_combined))
    if not _close(
        _finite_number(evidence["preclip_global_norm"], "preclip global norm"),
        preclip_norm,
    ):
        raise VerificationError("optimizer preclip global norm differs")
    clip_coefficient = min(1.0, 1.0 / (preclip_norm + 1e-6))
    all_applied: list[float] = []
    offset = 0
    for row in prepared:
        expected_applied = [
            gradient * clip_coefficient
            for gradient in all_combined[offset : offset + len(row["applied"])]
        ]
        offset += len(row["applied"])
        if any(
            not _close(left, right)
            for left, right in zip(row["applied"], expected_applied, strict=True)
        ):
            raise VerificationError("optimizer applied gradient differs")
        all_applied.extend(row["applied"])
    postclip_norm = math.sqrt(sum(value * value for value in all_applied))
    if (
        postclip_norm > 1.0 + 1e-6
        or not _close(
            _finite_number(evidence["postclip_global_norm"], "postclip global norm"),
            postclip_norm,
        )
    ):
        raise VerificationError("optimizer postclip global norm differs")
    beta1, beta2 = expected_optimizer["betas"]
    learning_rate = expected_optimizer["learning_rate"]
    epsilon = expected_optimizer["eps"]
    for row in prepared:
        before = row["before"]
        after = row["after"]
        expected_step = before["step"] + 1
        if after["step"] != expected_step:
            raise VerificationError("Adam step differs")
        for index, gradient in enumerate(row["applied"]):
            expected_m = beta1 * before["exp_avg"][index] + (1.0 - beta1) * gradient
            expected_v = (
                beta2 * before["exp_avg_sq"][index]
                + (1.0 - beta2) * gradient * gradient
            )
            denominator = (
                math.sqrt(expected_v) / math.sqrt(1.0 - beta2**expected_step)
            ) + epsilon
            step_size = learning_rate / (1.0 - beta1**expected_step)
            expected_post = row["pre"][index] - step_size * expected_m / denominator
            if (
                not _close(after["exp_avg"][index], expected_m)
                or not _close(after["exp_avg_sq"][index], expected_v)
                or not _close(row["post"][index], expected_post)
            ):
                raise VerificationError("Adam parameter transition differs")
    return {
        "card_decision_count": count,
        "components": components,
        "parameter_count": len(prepared),
        "total_loss": total_loss,
        "verified": True,
    }


def _baseline_trajectory_order(value: object, *, arm: str) -> list[str]:
    if not isinstance(value, list) or len(value) != 64:
        raise VerificationError("cross-fitted trajectory count differs")
    seeds: list[int] = []
    trajectories: list[str] = []
    for trajectory_id in value:
        if not isinstance(trajectory_id, str):
            raise VerificationError("cross-fitted trajectory identity differs")
        match = _TRAJECTORY_RE.fullmatch(trajectory_id)
        if match is None or match.group(1) != arm:
            raise VerificationError("cross-fitted trajectory identity differs")
        trajectories.append(trajectory_id)
        seeds.append(int(match.group(2)))
    if seeds != sorted(set(seeds)):
        raise VerificationError("cross-fitted trajectory order differs")
    return trajectories


def _baseline_fold_manifest(
    value: object,
    *,
    trajectories: Sequence[str],
) -> dict[str, list[str]]:
    folds = _mapping(value, "cross-fitted fold trajectories")
    expected_keys = {f"fold-{index}" for index in range(4)}
    _fields(folds, expected_keys, "cross-fitted fold trajectories")
    expected = {
        f"fold-{fold_index}": sorted(
            trajectory_id
            for position, trajectory_id in enumerate(trajectories)
            if position % 4 == fold_index
        )
        for fold_index in range(4)
    }
    if folds != expected or any(len(rows) != 16 for rows in expected.values()):
        raise VerificationError("cross-fitted fold assignment differs")
    return expected


def _baseline_models(
    value: object,
    *,
    trajectories: Sequence[str],
    folds: Mapping[str, list[str]],
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list) or len(value) != 4:
        raise VerificationError("cross-fitted model count differs")
    model_fields = {
        "absolute_product_sums",
        "coefficients",
        "fit_trajectory_ids",
        "fold_id",
        "held_out_trajectory_ids",
        "kkt_residuals",
        "rhs",
    }
    models_by_fold: dict[str, dict[str, Any]] = {}
    for fold_index, raw_model in enumerate(value):
        model = _mapping(raw_model, "cross-fitted fold model")
        _fields(model, model_fields, "cross-fitted fold model")
        fold_id = f"fold-{fold_index}"
        held_out = folds[fold_id]
        fit_ids = sorted(set(trajectories).difference(held_out))
        if (
            model["fold_id"] != fold_id
            or model["held_out_trajectory_ids"] != held_out
            or model["fit_trajectory_ids"] != fit_ids
            or len(fit_ids) != 48
        ):
            raise VerificationError("cross-fitted model fold membership differs")
        coefficients = _numeric_vector(
            model["coefficients"],
            count=129,
            label=f"{fold_id} coefficients",
        )
        residuals = _numeric_vector(
            model["kkt_residuals"],
            count=129,
            label=f"{fold_id} KKT residuals",
        )
        rhs = _numeric_vector(
            model["rhs"],
            count=129,
            label=f"{fold_id} right-hand side",
        )
        product_sums = _numeric_vector(
            model["absolute_product_sums"],
            count=129,
            label=f"{fold_id} absolute product sums",
        )
        for residual, right_hand_side, product_sum in zip(
            residuals,
            rhs,
            product_sums,
            strict=True,
        ):
            if product_sum < 0.0:
                raise VerificationError("cross-fitted absolute product sum is negative")
            scale = max(abs(right_hand_side), product_sum)
            if abs(residual) > 1e-9 + 1e-9 * scale:
                raise VerificationError("cross-fitted KKT residual exceeds its bound")
        models_by_fold[fold_id] = {
            "absolute_product_sums": product_sums,
            "coefficients": coefficients,
            "fit_trajectory_ids": fit_ids,
            "kkt_residuals": residuals,
            "rhs": rhs,
        }
    return models_by_fold


def _baseline_feature_identity(values: Sequence[float]) -> dict[str, Any]:
    entries: list[list[int | float]] = []
    for index, item in enumerate(values):
        try:
            float32_value = struct.unpack("<f", struct.pack("<f", item))[0]
        except (OverflowError, struct.error) as exc:
            raise VerificationError("cross-fitted feature is not float32") from exc
        if float32_value != item:
            raise VerificationError("cross-fitted feature is not exact float32")
        if item != 0.0:
            entries.append([index, item])
    return {
        "dense_dim": 128,
        "dtype": "float32",
        "entries": entries,
        "folding": "ascending-source-index-modulo-128-float32-add-v1",
        "schema_version": BASELINE_FEATURE_SCHEMA_VERSION,
        "source_dim": 1_024,
    }


def _verify_cross_fitted_normal_equations(
    models: Mapping[str, Mapping[str, Any]],
    decisions_by_trajectory: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    for fold_id, model in models.items():
        coefficients = model["coefficients"]
        rhs_terms: list[list[float]] = [[] for _ in range(129)]
        product_terms: list[list[float]] = [[] for _ in range(129)]
        absolute_bounds: list[list[float]] = [[] for _ in range(129)]
        for trajectory_id in model["fit_trajectory_ids"]:
            trajectory = decisions_by_trajectory[trajectory_id]
            weight = 1.0 / (48 * len(trajectory))
            for decision in trajectory:
                sparse = [(0, 1.0)] + [
                    (index + 1, feature)
                    for index, feature in enumerate(decision["features"])
                    if feature != 0.0
                ]
                dot = math.fsum(
                    coefficients[index] * feature for index, feature in sparse
                )
                absolute_dot_bound = math.fsum(
                    abs(coefficients[index] * feature)
                    for index, feature in sparse
                )
                for index, feature in sparse:
                    rhs_terms[index].append(weight * decision["raw_return"] * feature)
                    product_terms[index].append(weight * feature * dot)
                    absolute_bounds[index].append(
                        weight * abs(feature) * absolute_dot_bound
                    )
        for index in range(1, 129):
            product_terms[index].append(0.001 * coefficients[index])
            absolute_bounds[index].append(0.001 * abs(coefficients[index]))
        reconstructed_rhs = [math.fsum(terms) for terms in rhs_terms]
        reconstructed_product = [math.fsum(terms) for terms in product_terms]
        reconstructed_bound = [math.fsum(terms) for terms in absolute_bounds]
        for index in range(129):
            expected_residual = reconstructed_product[index] - reconstructed_rhs[index]
            scale = max(
                1.0,
                abs(reconstructed_rhs[index]),
                reconstructed_bound[index],
            )
            tolerance = 1e-9 + 1e-9 * scale
            reported_product_sum = model["absolute_product_sums"][index]
            if (
                abs(model["rhs"][index] - reconstructed_rhs[index]) > tolerance
                or abs(model["kkt_residuals"][index] - expected_residual)
                > tolerance
                or reported_product_sum + tolerance
                < abs(reconstructed_product[index])
                or reported_product_sum > reconstructed_bound[index] + tolerance
            ):
                raise VerificationError(
                    f"cross-fitted {fold_id} normal equation differs"
                )


def verify_cross_fitted_baseline_evidence(value: object) -> dict[str, Any]:
    """Reconstruct arm-local folds, KKT bounds, and held-out advantages."""
    evidence = _mapping(value, "cross-fitted baseline evidence")
    _fields(
        evidence,
        {
            "arm",
            "decisions",
            "fold_trajectories",
            "models",
            "schema_version",
            "trajectory_ids",
        },
        "cross-fitted baseline evidence",
    )
    if evidence["schema_version"] != CROSS_FITTED_BASELINE_EVIDENCE_SCHEMA_VERSION:
        raise VerificationError("cross-fitted baseline schema differs")
    arm = evidence["arm"]
    if arm not in {"candidate", "control"}:
        raise VerificationError("cross-fitted baseline arm differs")
    trajectories = _baseline_trajectory_order(evidence["trajectory_ids"], arm=arm)
    folds = _baseline_fold_manifest(
        evidence["fold_trajectories"],
        trajectories=trajectories,
    )
    models = _baseline_models(
        evidence["models"],
        trajectories=trajectories,
        folds=folds,
    )
    fold_by_trajectory = {
        trajectory_id: fold_id
        for fold_id, held_out in folds.items()
        for trajectory_id in held_out
    }
    decisions = evidence["decisions"]
    if not isinstance(decisions, list) or not decisions:
        raise VerificationError("cross-fitted decisions are empty")
    decision_fields = {
        "advantage",
        "baseline_prediction",
        "decision_id",
        "decision_index",
        "feature_sha256",
        "feature_values",
        "fold_id",
        "preclip_little_endian_hex",
        "raw_return",
        "trajectory_id",
        "unclipped_prediction",
        "was_clipped",
    }
    expected_order: list[tuple[int, int]] = []
    counts = {trajectory_id: 0 for trajectory_id in trajectories}
    decisions_by_trajectory: dict[str, list[dict[str, Any]]] = {
        trajectory_id: [] for trajectory_id in trajectories
    }
    position_by_trajectory = {
        trajectory_id: position
        for position, trajectory_id in enumerate(trajectories)
    }
    for raw_decision in decisions:
        decision = _mapping(raw_decision, "cross-fitted decision")
        _fields(decision, decision_fields, "cross-fitted decision")
        trajectory_id = decision["trajectory_id"]
        decision_index = decision["decision_index"]
        if trajectory_id not in counts or (
            isinstance(decision_index, bool)
            or not isinstance(decision_index, int)
            or decision_index != counts[trajectory_id]
        ):
            raise VerificationError("cross-fitted decision order differs")
        expected_id = f"{trajectory_id}:decision-{decision_index}"
        fold_id = fold_by_trajectory[trajectory_id]
        if decision["decision_id"] != expected_id or decision["fold_id"] != fold_id:
            raise VerificationError("cross-fitted decision fold identity differs")
        features = _numeric_vector(
            decision["feature_values"],
            count=128,
            label="cross-fitted baseline features",
        )
        feature_identity = _baseline_feature_identity(features)
        feature_sha256 = hashlib.sha256(
            _runtime_canonical_json_bytes(feature_identity) + b"\n"
        ).hexdigest()
        if decision["feature_sha256"] != feature_sha256:
            raise VerificationError("cross-fitted feature identity differs")
        values = [1.0, *features]
        unclipped = math.fsum(
            coefficient * feature
            for coefficient, feature in zip(
                models[fold_id]["coefficients"],
                values,
                strict=True,
            )
        )
        clipped = min(3.0, max(0.0, unclipped))
        raw_return = _finite_number(decision["raw_return"], "cross-fitted return")
        if not 0.0 <= raw_return <= 3.0:
            raise VerificationError("cross-fitted return is outside [0, 3]")
        if not isinstance(decision["was_clipped"], bool):
            raise VerificationError("cross-fitted clipping flag differs")
        reported_unclipped = _finite_number(
            decision["unclipped_prediction"],
            "cross-fitted unclipped prediction",
        )
        reported_clipped = _finite_number(
            decision["baseline_prediction"],
            "cross-fitted baseline prediction",
        )
        reported_advantage = _finite_number(
            decision["advantage"],
            "cross-fitted advantage",
        )
        if (
            not _close(reported_unclipped, unclipped)
            or not _close(reported_clipped, clipped)
            or not _close(reported_advantage, raw_return - clipped)
            or decision["was_clipped"] != (clipped != unclipped)
            or decision["preclip_little_endian_hex"]
            != struct.pack("<d", unclipped).hex()
        ):
            raise VerificationError("cross-fitted advantage or prediction differs")
        expected_order.append((position_by_trajectory[trajectory_id], decision_index))
        decisions_by_trajectory[trajectory_id].append(
            {"features": features, "raw_return": raw_return}
        )
        counts[trajectory_id] += 1
    if any(count == 0 for count in counts.values()) or expected_order != sorted(
        expected_order
    ):
        raise VerificationError("cross-fitted decision coverage differs")
    _verify_cross_fitted_normal_equations(models, decisions_by_trajectory)
    return {
        "advantage_count": len(decisions),
        "arm": arm,
        "fold_count": len(folds),
        "trajectory_count": len(trajectories),
        "verified": True,
    }


def _inventory_nonnegative(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VerificationError(f"{label} must be a nonnegative integer")
    return value


def _inventory_report_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise VerificationError(f"{label} is not a canonical report path")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or pure.as_posix() != value
        or ".." in pure.parts
        or len(pure.parts) < 2
        or pure.parts[0] != "reports"
        or "\n" in value
        or "\r" in value
    ):
        raise VerificationError(f"{label} is not a canonical report path")
    return value


def _inventory_format(path: str) -> str | None:
    for suffix, name in (
        (".jsonl.gz", "jsonl.gz"),
        (".json.gz", "json.gz"),
        (".jsonl", "jsonl"),
        (".json", "json"),
    ):
        if path.endswith(suffix):
            return name
    return None


def _inventory_root_match(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _verify_seed_source_registry(value: object) -> dict[str, Any]:
    registry = _mapping(value, "seed source registry")
    _fields(
        registry,
        {
            "excluded_roots",
            "output_root_policy",
            "registry_sha256",
            "repository_commit",
            "schema_version",
            "source_count",
            "sources",
        },
        "seed source registry",
    )
    if (
        registry["schema_version"] != SOURCE_REGISTRY_SCHEMA_VERSION
        or not isinstance(registry["repository_commit"], str)
        or _COMMIT_RE.fullmatch(registry["repository_commit"]) is None
    ):
        raise VerificationError("seed source registry identity differs")
    policy = _mapping(registry["output_root_policy"], "inventory output policy")
    _fields(
        policy,
        {
            "candidate_output_root",
            "excluded_kinds",
            "registered_source_root",
            "schema_version",
        },
        "inventory output policy",
    )
    candidate_root = policy["candidate_output_root"]
    if candidate_root is not None:
        candidate_root = _inventory_report_path(
            candidate_root,
            "inventory candidate output root",
        )
    policy = {**policy, "candidate_output_root": candidate_root}
    if (
        policy["schema_version"] != OUTPUT_ROOT_POLICY_VERSION
        or policy["registered_source_root"] != "reports"
        or policy["excluded_kinds"] != list(_INVENTORY_GENERATED_ROOT_KINDS)
    ):
        raise VerificationError("inventory output policy differs")
    raw_roots = registry["excluded_roots"]
    if not isinstance(raw_roots, list):
        raise VerificationError("inventory excluded roots differ")
    roots: list[dict[str, str]] = []
    for raw_root in raw_roots:
        root = _mapping(raw_root, "inventory excluded root")
        _fields(root, {"kind", "path"}, "inventory excluded root")
        if root["kind"] not in _INVENTORY_GENERATED_ROOT_KINDS:
            raise VerificationError("inventory excluded-root kind differs")
        root["path"] = _inventory_report_path(
            root["path"],
            "inventory excluded-root path",
        )
        roots.append(root)
    if roots != sorted(roots, key=lambda row: row["path"]) or len(
        {row["path"] for row in roots}
    ) != len(roots):
        raise VerificationError("inventory excluded roots are not canonical")
    raw_sources = registry["sources"]
    if not isinstance(raw_sources, list):
        raise VerificationError("inventory sources differ")
    sources: list[dict[str, Any]] = []
    for raw_source in raw_sources:
        source = _mapping(raw_source, "inventory source")
        _fields(
            source,
            {
                "document_count",
                "format",
                "path",
                "row_count",
                "sha256",
                "size_bytes",
            },
            "inventory source",
        )
        source["path"] = _inventory_report_path(
            source["path"],
            "inventory source path",
        )
        if source["format"] != _inventory_format(source["path"]):
            raise VerificationError("inventory source format differs")
        _digest(source["sha256"], "inventory source digest")
        if _inventory_nonnegative(source["size_bytes"], "inventory source size") == 0:
            raise VerificationError("inventory source is empty")
        if (
            _inventory_nonnegative(
                source["document_count"],
                "inventory source document count",
            )
            == 0
        ):
            raise VerificationError("inventory source has no documents")
        _inventory_nonnegative(source["row_count"], "inventory source row count")
        if any(
            _inventory_root_match(source["path"], root["path"])
            for root in roots
        ):
            raise VerificationError("generated root entered inventory sources")
        sources.append(source)
    if sources != sorted(sources, key=lambda row: row["path"]) or len(
        {row["path"] for row in sources}
    ) != len(sources):
        raise VerificationError("inventory sources are not canonical")
    if _inventory_nonnegative(registry["source_count"], "inventory source count") != (
        len(sources)
    ):
        raise VerificationError("inventory source count differs")
    normalized = {
        **registry,
        "excluded_roots": roots,
        "output_root_policy": policy,
        "sources": sources,
    }
    body = {key: item for key, item in normalized.items() if key != "registry_sha256"}
    if _digest(normalized["registry_sha256"], "source registry digest") != (
        _canonical_sha256(body)
    ):
        raise VerificationError("seed source registry digest differs")
    return normalized


def verify_seed_inventory_evidence(value: object) -> dict[str, Any]:
    """Reconstruct one fixed fresh-cohort inventory from its canonical claims."""
    inventory = _mapping(value, "seed inventory")
    _fields(
        inventory,
        {
            "authorization_sha256",
            "cohort_counts",
            "cohorts",
            "excluded_seed_count",
            "excluded_seeds",
            "excluded_seeds_sha256",
            "inventory_sha256",
            "request_sha256",
            "repository_commit",
            "role_sha256",
            "row_count",
            "rows",
            "schema_version",
            "source_registry",
        },
        "seed inventory",
    )
    if (
        inventory["schema_version"] != SEED_INVENTORY_SCHEMA_VERSION
        or not isinstance(inventory["repository_commit"], str)
        or _COMMIT_RE.fullmatch(inventory["repository_commit"]) is None
    ):
        raise VerificationError("seed inventory identity differs")
    _digest(inventory["request_sha256"], "inventory request digest")
    _digest(inventory["authorization_sha256"], "inventory authorization digest")
    registry = _verify_seed_source_registry(inventory["source_registry"])
    if registry["repository_commit"] != inventory["repository_commit"]:
        raise VerificationError("inventory repository binding differs")
    raw_rows = inventory["rows"]
    if not isinstance(raw_rows, list):
        raise VerificationError("inventory rows differ")
    rows: list[dict[str, Any]] = []
    for raw_row in raw_rows:
        row = _mapping(raw_row, "inventory row")
        _fields(
            row,
            {"document_index", "json_path", "role", "seed", "source_path"},
            "inventory row",
        )
        row["document_index"] = _inventory_nonnegative(
            row["document_index"],
            "inventory row document index",
        )
        if not isinstance(row["json_path"], str) or not row["json_path"].startswith(
            "/"
        ):
            raise VerificationError("inventory row JSON path differs")
        if row["role"] not in _INVENTORY_ROW_ROLES:
            raise VerificationError("inventory row role differs")
        row["seed"] = _inventory_nonnegative(row["seed"], "inventory row seed")
        row["source_path"] = _inventory_report_path(
            row["source_path"],
            "inventory row source path",
        )
        rows.append(row)
    row_key = lambda row: (
        row["seed"],
        row["source_path"],
        row["document_index"],
        row["json_path"],
        row["role"],
    )
    if rows != sorted(rows, key=row_key) or len(
        {
            (
                row["document_index"],
                row["json_path"],
                row["role"],
                row["seed"],
                row["source_path"],
            )
            for row in rows
        }
    ) != len(rows):
        raise VerificationError("inventory rows are not canonical")
    sources = {source["path"]: source for source in registry["sources"]}
    rows_by_source: dict[str, list[dict[str, Any]]] = {
        path: [] for path in sources
    }
    for row in rows:
        if row["source_path"] not in rows_by_source:
            raise VerificationError("inventory row source is not registered")
        rows_by_source[row["source_path"]].append(row)
    for path, source in sources.items():
        if source["row_count"] != len(rows_by_source[path]) or any(
            row["document_index"] >= source["document_count"]
            for row in rows_by_source[path]
        ):
            raise VerificationError("inventory source row counts differ")
    if _inventory_nonnegative(inventory["row_count"], "inventory row count") != len(
        rows
    ):
        raise VerificationError("inventory row count differs")
    excluded = sorted({row["seed"] for row in rows})
    if inventory["excluded_seeds"] != excluded:
        raise VerificationError("inventory exclusion union differs")
    if _inventory_nonnegative(
        inventory["excluded_seed_count"],
        "inventory excluded-seed count",
    ) != len(excluded):
        raise VerificationError("inventory excluded-seed count differs")
    if _digest(
        inventory["excluded_seeds_sha256"],
        "inventory excluded-seed digest",
    ) != _canonical_sha256(excluded):
        raise VerificationError("inventory excluded-seed digest differs")
    if inventory["cohort_counts"] != _INVENTORY_ROLE_COUNTS:
        raise VerificationError("inventory cohort counts differ")
    cohorts = _mapping(inventory["cohorts"], "inventory cohorts")
    _fields(cohorts, set(_INVENTORY_ROLE_ORDER), "inventory cohorts")
    selected: list[int] = []
    candidate = 0
    excluded_set = set(excluded)
    while len(selected) < sum(_INVENTORY_ROLE_COUNTS.values()):
        if candidate not in excluded_set:
            selected.append(candidate)
        candidate += 1
    offset = 0
    normalized_cohorts: dict[str, list[int]] = {}
    for role in _INVENTORY_ROLE_ORDER:
        raw_cohort = cohorts[role]
        count = _INVENTORY_ROLE_COUNTS[role]
        if not isinstance(raw_cohort, list):
            raise VerificationError(f"inventory {role} cohort differs")
        cohort = [
            _inventory_nonnegative(seed, f"inventory {role} seed")
            for seed in raw_cohort
        ]
        expected = selected[offset : offset + count]
        offset += count
        if cohort != expected:
            raise VerificationError("inventory cohorts differ from fixed selection")
        normalized_cohorts[role] = cohort
    role_sha256 = _mapping(inventory["role_sha256"], "inventory role digests")
    _fields(role_sha256, set(_INVENTORY_ROLE_ORDER), "inventory role digests")
    expected_role_sha256 = {
        role: _canonical_sha256(normalized_cohorts[role])
        for role in _INVENTORY_ROLE_ORDER
    }
    if role_sha256 != expected_role_sha256:
        raise VerificationError("inventory role digests differ")
    normalized = {
        **inventory,
        "cohorts": normalized_cohorts,
        "excluded_seeds": excluded,
        "role_sha256": role_sha256,
        "rows": rows,
        "source_registry": registry,
    }
    body = {key: item for key, item in normalized.items() if key != "inventory_sha256"}
    if _digest(normalized["inventory_sha256"], "seed inventory digest") != (
        _canonical_sha256(body)
    ):
        raise VerificationError("seed inventory digest differs")
    return {
        "cohort_counts": copy.deepcopy(_INVENTORY_ROLE_COUNTS),
        "excluded_seed_count": len(excluded),
        "inventory_sha256": normalized["inventory_sha256"],
        "source_count": len(sources),
        "verified": True,
    }


def _external_file_binding(value: object, label: str) -> dict[str, Any]:
    binding = _mapping(value, label)
    _fields(binding, {"path", "sha256", "size_bytes"}, label)
    path = binding["path"]
    size = binding["size_bytes"]
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise VerificationError(f"{label} path is not absolute")
    _digest(binding["sha256"], f"{label} digest")
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise VerificationError(f"{label} size differs")
    return binding


def _external_tree_binding(value: object, label: str) -> dict[str, Any]:
    binding = _mapping(value, label)
    _fields(binding, {"file_count", "root", "sha256", "size_bytes"}, label)
    root = binding["root"]
    if not isinstance(root, str) or not Path(root).is_absolute():
        raise VerificationError(f"{label} root is not absolute")
    _digest(binding["sha256"], f"{label} digest")
    for name in ("file_count", "size_bytes"):
        item = binding[name]
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise VerificationError(f"{label} {name} differs")
    return binding


def _observe_external_file(binding: Mapping[str, Any], label: str) -> dict[str, Any]:
    path = Path(binding["path"])
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"{label} cannot be observed") from exc
    if not payload:
        raise VerificationError(f"{label} is empty")
    return {
        "path": path.resolve().as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _named_byte_sha256(rows: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in rows:
        encoded_name = name.encode("utf-8")
        digest.update(len(encoded_name).to_bytes(4, "big"))
        digest.update(encoded_name)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _observe_external_tree(binding: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(binding["root"])
    if not root.is_dir() or root.is_symlink():
        raise VerificationError("production checkpoint root cannot be observed")
    try:
        observed_paths = list(root.rglob("*"))
        if any(path.is_symlink() for path in observed_paths):
            raise VerificationError("production checkpoint tree contains a symlink")
        paths = sorted(
            (path for path in observed_paths if path.is_file()),
            key=lambda path: path.relative_to(root).as_posix(),
        )
        rows = [
            (path.relative_to(root).as_posix(), path.read_bytes())
            for path in paths
        ]
    except OSError as exc:
        raise VerificationError("production checkpoint tree cannot be observed") from exc
    return {
        "file_count": len(rows),
        "root": root.resolve().as_posix(),
        "sha256": _named_byte_sha256(rows),
        "size_bytes": sum(len(payload) for _, payload in rows),
    }


def _rollback_authority(value: object) -> dict[str, Any]:
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
    if (
        authority["schema_version"] != ROLLBACK_AUTHORITY_SCHEMA_VERSION
        or authority["candidate_disabled_value"] is not False
        or authority["trigger_classes"] != list(_ROLLBACK_TRIGGER_CLASSES)
    ):
        raise VerificationError("rollback authority contract differs")
    target = _mapping(authority["control_target"], "rollback control target")
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
        "rollback control target",
    )
    if (
        target["candidate_enabled"] is not False
        or target["selected_arm"] != "control"
        or target["schema_version"] != EXPERIMENT_TARGET_SCHEMA_VERSION
    ):
        raise VerificationError("rollback control target contract differs")
    target["checkpoint"] = _external_file_binding(
        target["checkpoint"],
        "rollback control checkpoint",
    )
    target["configuration"] = _external_file_binding(
        target["configuration"],
        "rollback control configuration",
    )
    target_body = {key: item for key, item in target.items() if key != "target_sha256"}
    if _digest(target["target_sha256"], "rollback target digest") != (
        _canonical_sha256(target_body)
    ):
        raise VerificationError("rollback control target digest differs")
    isolation = _mapping(authority["production_isolation"], "production isolation")
    _fields(
        isolation,
        {"communication_mod_config", "production_checkpoints"},
        "production isolation",
    )
    isolation = {
        "communication_mod_config": _external_file_binding(
            isolation["communication_mod_config"],
            "production CommunicationMod configuration",
        ),
        "production_checkpoints": _external_tree_binding(
            isolation["production_checkpoints"],
            "production checkpoint inventory",
        ),
    }
    relative = _relative_path(authority["target_relative_path"])
    if relative == ROLLBACK_OBSERVATION_FILENAME:
        raise VerificationError("rollback target conflicts with its observation")
    normalized_body = {
        "candidate_disabled_value": False,
        "control_target": target,
        "production_isolation": isolation,
        "schema_version": ROLLBACK_AUTHORITY_SCHEMA_VERSION,
        "target_relative_path": relative,
        "trigger_classes": list(_ROLLBACK_TRIGGER_CLASSES),
    }
    if _digest(
        authority["rollback_authority_sha256"],
        "rollback authority digest",
    ) != _canonical_sha256(normalized_body):
        raise VerificationError("rollback authority digest differs")
    return {
        **normalized_body,
        "rollback_authority_sha256": authority["rollback_authority_sha256"],
    }


def _rollback_identity_observation(
    value: object,
    *,
    expected: Mapping[str, Any],
    label: str,
) -> bool:
    observation = _mapping(value, label)
    if observation.get("observed") is None:
        _fields(observation, {"error", "matches_registered", "observed"}, label)
        if (
            not isinstance(observation["error"], str)
            or not observation["error"]
            or observation["matches_registered"] is not False
        ):
            raise VerificationError(f"{label} error claim differs")
        return False
    _fields(observation, {"matches_registered", "observed"}, label)
    observed = _mapping(observation["observed"], f"{label} observed identity")
    matches = observed == expected
    if observation["matches_registered"] is not matches:
        raise VerificationError(f"{label} match claim differs")
    return matches


def verify_rollback_evidence(
    output_path: Path | str,
    *,
    rollback_authority: Mapping[str, Any],
    expected_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Reobserve a rollback target, control bytes, and production isolation."""
    root = Path(output_path).resolve()
    if not root.is_dir() or root.is_symlink():
        raise VerificationError("rollback output root is invalid")
    authority = _rollback_authority(rollback_authority)
    identity = _normalize_identity(expected_identity)
    observation = _read_canonical_mapping(
        root / ROLLBACK_OBSERVATION_FILENAME,
        "rollback observation",
    )
    observation_fields = {
        "candidate_enabled",
        "control_identities_after",
        "control_identities_before",
        "control_identities_verified",
        "control_target_after",
        "control_target_before",
        "control_target_verified",
        "downstream_authority",
        "identity",
        "production_isolation_after",
        "production_isolation_before",
        "production_isolation_verified",
        "rollback_authority_sha256",
        "rollback_observation_sha256",
        "schema_version",
        "status",
        "trigger_class",
    }
    _fields(observation, observation_fields, "rollback observation")
    body = {
        key: item
        for key, item in observation.items()
        if key != "rollback_observation_sha256"
    }
    if (
        observation["schema_version"] != ROLLBACK_OBSERVATION_SCHEMA_VERSION
        or observation["candidate_enabled"] is not False
        or observation["identity"] != identity
        or observation["rollback_authority_sha256"]
        != authority["rollback_authority_sha256"]
        or observation["trigger_class"] not in _ROLLBACK_TRIGGER_CLASSES
        or _digest(
            observation["rollback_observation_sha256"],
            "rollback observation digest",
        )
        != _canonical_sha256(body)
    ):
        raise VerificationError("rollback observation identity differs")
    if observation["downstream_authority"] != {
        name: False for name in _AUTHORITY_NAMES
    }:
        raise VerificationError("rollback downstream authority differs")
    expected_control = {
        "checkpoint": authority["control_target"]["checkpoint"],
        "configuration": authority["control_target"]["configuration"],
    }
    control_before = _rollback_identity_observation(
        observation["control_identities_before"],
        expected=expected_control,
        label="control identity before rollback",
    )
    control_after = _rollback_identity_observation(
        observation["control_identities_after"],
        expected=expected_control,
        label="control identity after rollback",
    )
    isolation_before = _rollback_identity_observation(
        observation["production_isolation_before"],
        expected=authority["production_isolation"],
        label="production isolation before rollback",
    )
    isolation_after = _rollback_identity_observation(
        observation["production_isolation_after"],
        expected=authority["production_isolation"],
        label="production isolation after rollback",
    )
    control_verified = control_before and control_after
    isolation_verified = isolation_before and isolation_after
    expected_status = (
        "rollback_control_identity_failure"
        if not control_verified
        else (
            "rollback_isolation_failure"
            if not isolation_verified
            else "rollback_verified"
        )
    )
    if (
        observation["control_identities_verified"] is not control_verified
        or observation["production_isolation_verified"] is not isolation_verified
        or observation["control_target_verified"] is not True
        or observation["status"] != expected_status
    ):
        raise VerificationError("rollback status or verification claim differs")
    target_path = root.joinpath(
        *PurePosixPath(authority["target_relative_path"]).parts
    )
    cursor = root
    for part in PurePosixPath(authority["target_relative_path"]).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise VerificationError("rollback control target contains a symlink")
    try:
        target_bytes = target_path.read_bytes()
    except OSError as exc:
        raise VerificationError("rollback control target cannot be read") from exc
    expected_target_bytes = canonical_json_bytes(authority["control_target"])
    expected_target_binding = {
        "path": authority["target_relative_path"],
        "sha256": hashlib.sha256(target_bytes).hexdigest(),
        "size_bytes": len(target_bytes),
    }
    if (
        target_bytes != expected_target_bytes
        or observation["control_target_after"] != expected_target_binding
    ):
        raise VerificationError("rollback control target bytes differ")
    before_binding = observation["control_target_before"]
    if before_binding is not None:
        normalized_before = _mapping(before_binding, "rollback target before")
        _fields(
            normalized_before,
            {"path", "sha256", "size_bytes"},
            "rollback target before",
        )
        if normalized_before["path"] != authority["target_relative_path"]:
            raise VerificationError("rollback target-before path differs")
        _digest(normalized_before["sha256"], "rollback target-before digest")
        size = normalized_before["size_bytes"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise VerificationError("rollback target-before size differs")
    current_control = {
        "checkpoint": _observe_external_file(
            authority["control_target"]["checkpoint"],
            "control checkpoint",
        ),
        "configuration": _observe_external_file(
            authority["control_target"]["configuration"],
            "control configuration",
        ),
    }
    current_isolation = {
        "communication_mod_config": _observe_external_file(
            authority["production_isolation"]["communication_mod_config"],
            "production CommunicationMod configuration",
        ),
        "production_checkpoints": _observe_external_tree(
            authority["production_isolation"]["production_checkpoints"]
        ),
    }
    after_control_observed = observation["control_identities_after"].get("observed")
    after_isolation_observed = observation["production_isolation_after"].get(
        "observed"
    )
    if after_control_observed != current_control:
        raise VerificationError("rollback control identity changed after observation")
    if after_isolation_observed != current_isolation:
        raise VerificationError("rollback production isolation changed after observation")
    return {
        "candidate_enabled": False,
        "control_target_sha256": authority["control_target"]["target_sha256"],
        "production_isolation_verified": isolation_verified,
        "status": expected_status,
        "trigger_class": observation["trigger_class"],
        "verified": True,
    }


def _read_canonical_mapping(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"{label} cannot be read") from exc
    return _parse_canonical_mapping(payload, label)


def _canonical_json_lines(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"{label} cannot be read") from exc
    if not payload or not payload.endswith(b"\n"):
        raise VerificationError(f"{label} is incomplete")
    return [
        _parse_canonical_mapping(line, f"{label} line {index}")
        for index, line in enumerate(payload.splitlines(keepends=True), start=1)
    ]


def _relative_path(value: object) -> str:
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise VerificationError("artifact path is invalid")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or pure.as_posix() != value
        or value.endswith("/")
        or any(part in {"", ".", ".."} for part in pure.parts)
        or any(part.startswith(".") and part.endswith(".tmp") for part in pure.parts)
    ):
        raise VerificationError("artifact path is invalid")
    return value


def _deterministic_gzip_bytes(payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        fileobj=buffer,
        mode="wb",
        filename="",
        mtime=0,
    ) as handle:
        handle.write(payload)
    return buffer.getvalue()


def _bounded_gzip_payload(stored: bytes) -> bytes:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as stream:
            uncompressed = stream.read(_MAX_ARTIFACT_BYTES + 1)
            trailing_output = (
                b""
                if len(uncompressed) > _MAX_ARTIFACT_BYTES
                else stream.read(1)
            )
    except (EOFError, gzip.BadGzipFile, OSError) as exc:
        raise VerificationError("managed gzip artifact is invalid") from exc
    if len(uncompressed) > _MAX_ARTIFACT_BYTES or trailing_output:
        raise VerificationError("managed artifact exceeds its byte ceiling")
    if _deterministic_gzip_bytes(uncompressed) != stored:
        raise VerificationError("managed gzip artifact is not deterministic")
    return uncompressed


def _artifact_binding(root: Path, relative: str) -> dict[str, Any]:
    normalized = _relative_path(relative)
    path = root.joinpath(*PurePosixPath(normalized).parts)
    if path.is_symlink() or not path.is_file():
        raise VerificationError(f"managed artifact is not regular: {normalized}")
    try:
        if path.stat().st_size > _MAX_ARTIFACT_BYTES:
            raise VerificationError("managed artifact exceeds its byte ceiling")
        stored = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"managed artifact cannot be read: {normalized}") from exc
    if normalized.endswith(".gz"):
        uncompressed = _bounded_gzip_payload(stored)
        encoding = "deterministic-gzip-v1"
    else:
        uncompressed = stored
        encoding = "identity-bytes-v1"
    return {
        "encoding": encoding,
        "path": normalized,
        "stored_sha256": hashlib.sha256(stored).hexdigest(),
        "stored_size_bytes": len(stored),
        "uncompressed_sha256": hashlib.sha256(uncompressed).hexdigest(),
        "uncompressed_size_bytes": len(uncompressed),
    }


def _observe_inventory(
    root: Path,
    *,
    excluded_paths: Sequence[str],
) -> dict[str, Any]:
    excluded = set(excluded_paths)
    rows: list[dict[str, Any]] = []
    try:
        paths = sorted(
            root.rglob("*"),
            key=lambda path: path.relative_to(root).as_posix(),
        )
    except OSError as exc:
        raise VerificationError("managed artifact inventory cannot be listed") from exc
    for path in paths:
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise VerificationError(f"managed artifact is a symlink: {relative}")
        if path.is_dir():
            continue
        if relative == LEASE_FILENAME or relative in excluded:
            continue
        if path.name.startswith(".") and path.name.endswith(".tmp"):
            raise VerificationError(f"managed artifact staging is ambiguous: {relative}")
        rows.append(_artifact_binding(root, relative))
    stored_total = sum(row["stored_size_bytes"] for row in rows)
    uncompressed_total = sum(row["uncompressed_size_bytes"] for row in rows)
    if stored_total > _MAX_STORED_BYTES:
        raise VerificationError("managed stored-byte ceiling exceeded")
    if uncompressed_total > _MAX_UNCOMPRESSED_BYTES:
        raise VerificationError("managed uncompressed-byte ceiling exceeded")
    body = {
        "artifact_count": len(rows),
        "artifacts": rows,
        "schema_version": ARTIFACT_INVENTORY_SCHEMA_VERSION,
        "stored_size_bytes": stored_total,
        "uncompressed_size_bytes": uncompressed_total,
    }
    return {**body, "artifact_inventory_sha256": _canonical_sha256(body)}


def _normalize_identity(value: object) -> dict[str, str]:
    identity = _mapping(value, "execution identity")
    expected = {
        "authorization_sha256",
        "registration_sha256",
        "request_sha256",
        "stage",
    }
    if "launch_authority_sha256" in identity:
        expected.add("launch_authority_sha256")
    _fields(identity, expected, "execution identity")
    for name in expected - {"stage"}:
        _digest(identity[name], f"execution identity {name}")
    if identity["stage"] not in _RESOURCE_LIMITS:
        raise VerificationError("execution identity stage is invalid")
    return identity


def _verify_lease(
    root: Path,
    *,
    identity: Mapping[str, Any],
    expected_child_process_id: int,
    owner_alive: Callable[[int], bool],
) -> dict[str, Any]:
    lease = _read_canonical_mapping(root / LEASE_FILENAME, "execution lease")
    _fields(
        lease,
        {"identity", "owner", "reclaimed_owner", "schema_version"},
        "execution lease",
    )
    if lease["schema_version"] != LEASE_SCHEMA_VERSION or lease["identity"] != identity:
        raise VerificationError("execution lease identity mismatch")
    owner = _mapping(lease["owner"], "execution lease owner")
    _fields(
        owner,
        {"acquired_monotonic", "child_process_id", "token"},
        "execution lease owner",
    )
    process_id = owner["child_process_id"]
    if (
        isinstance(expected_child_process_id, bool)
        or not isinstance(expected_child_process_id, int)
        or expected_child_process_id <= 0
        or process_id != expected_child_process_id
    ):
        raise VerificationError("execution lease owner process differs")
    acquired = owner["acquired_monotonic"]
    if (
        isinstance(acquired, bool)
        or not isinstance(acquired, (int, float))
        or not math.isfinite(float(acquired))
        or acquired < 0.0
        or not isinstance(owner["token"], str)
        or _TOKEN_RE.fullmatch(owner["token"]) is None
    ):
        raise VerificationError("execution lease owner is invalid")
    try:
        alive = owner_alive(process_id)
    except Exception as exc:
        raise VerificationError("execution lease owner liveness failed") from exc
    if alive is not False:
        raise VerificationError("execution lease owner is still alive")
    reclaimed = lease["reclaimed_owner"]
    if reclaimed is not None:
        prior = _mapping(reclaimed, "reclaimed execution lease owner")
        _fields(
            prior,
            {"acquired_monotonic", "child_process_id", "token"},
            "reclaimed execution lease owner",
        )
    return lease


def _verify_access_journal(
    root: Path,
    *,
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    events = _canonical_json_lines(root / ACCESS_JOURNAL_FILENAME, "access journal")
    expected_header = {
        "event_index": 0,
        "identity": identity,
        "kind": "journal_opened",
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
    }
    if events[0] != expected_header:
        raise VerificationError("access journal header mismatch")
    previous = events[0]
    for index, event in enumerate(events[1:], start=1):
        _fields(
            event,
            {
                "arm",
                "event_index",
                "kind",
                "previous_event_sha256",
                "schema_version",
                "seed",
                "stage",
            },
            "access journal event",
        )
        seed = event["seed"]
        if (
            event["schema_version"] != ACCESS_JOURNAL_SCHEMA_VERSION
            or event["kind"] != "environment_access_debited"
            or event["event_index"] != index
            or event["previous_event_sha256"] != _canonical_sha256(previous)
            or event["stage"] != identity["stage"]
            or event["arm"] not in {"candidate", "control"}
            or isinstance(seed, bool)
            or not isinstance(seed, int)
            or seed < 0
        ):
            raise VerificationError("access journal event mismatch")
        previous = event
    return {
        "debited_accesses": len(events) - 1,
        "event_count": len(events),
        "events": events,
        "last_event_sha256": _canonical_sha256(events[-1]),
    }


def _verify_resource_ledger(
    root: Path,
    *,
    identity: Mapping[str, Any],
    debited_accesses: int,
) -> dict[str, Any]:
    events = _canonical_json_lines(root / RESOURCE_LEDGER_FILENAME, "resource ledger")
    limits = copy.deepcopy(_RESOURCE_LIMITS[identity["stage"]])
    zero = {
        "charged_seconds": 0.0,
        "environment_accesses": 0,
        "optimizer_steps": 0,
        "shadow_optimizer_steps": 0,
    }
    expected_header = {
        "identity": identity,
        "kind": "resource_ledger_opened",
        "limits": limits,
        "resources": zero,
        "revision": 0,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }
    if events[0] != expected_header:
        raise VerificationError("resource ledger header mismatch")
    previous_event = events[0]
    previous_resources: dict[str, int | float] = zero
    for revision, event in enumerate(events[1:], start=1):
        _fields(
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
        resources = _mapping(event["resources"], "resource prefix")
        if (
            event["schema_version"] != RESOURCE_LEDGER_SCHEMA_VERSION
            or event["kind"] != "resource_prefix_advanced"
            or event["revision"] != revision
            or event["previous_event_sha256"] != _canonical_sha256(previous_event)
            or not isinstance(event["reason"], str)
            or not event["reason"]
            or set(resources) != set(_RESOURCE_FIELDS)
        ):
            raise VerificationError("resource ledger event mismatch")
        for name in _RESOURCE_FIELDS:
            value = resources[name]
            valid_type = (
                isinstance(value, (int, float))
                if name == "charged_seconds"
                else isinstance(value, int)
            )
            if (
                isinstance(value, bool)
                or not valid_type
                or not math.isfinite(float(value))
                or value < previous_resources[name]
                or value > limits[name]
            ):
                raise VerificationError("resource prefix exceeds its bound")
        previous_event = event
        previous_resources = resources
    if previous_resources["environment_accesses"] != debited_accesses:
        raise VerificationError("resource and access journal prefixes differ")
    return {
        "events": events,
        "last_event_sha256": _canonical_sha256(events[-1]),
        "resources": previous_resources,
        "revision": len(events) - 1,
    }


def _verify_terminal_intent(
    root: Path,
    *,
    identity: Mapping[str, Any],
    journal: Mapping[str, Any],
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    intent = _read_canonical_mapping(root / TERMINAL_INTENT_FILENAME, "terminal intent")
    _fields(
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
    authority = {name: False for name in _AUTHORITY_NAMES}
    if (
        intent["schema_version"] != TERMINAL_INTENT_SCHEMA_VERSION
        or intent["identity"] != identity
        or intent["downstream_authority"] != authority
        or not isinstance(intent["verdict"], str)
        or _IDENTIFIER_RE.fullmatch(intent["verdict"]) is None
        or not isinstance(intent["details"], Mapping)
    ):
        raise VerificationError("terminal intent identity or authority mismatch")
    body = {key: value for key, value in intent.items() if key != "terminal_intent_sha256"}
    if _digest(intent["terminal_intent_sha256"], "terminal intent digest") != (
        _canonical_sha256(body)
    ):
        raise VerificationError("terminal intent digest mismatch")
    expected_journal = {
        "debited_accesses": journal["debited_accesses"],
        "event_count": journal["event_count"],
        "last_event_sha256": journal["last_event_sha256"],
    }
    expected_resource = {
        "last_event_sha256": ledger["last_event_sha256"],
        "resources": ledger["resources"],
        "revision": ledger["revision"],
    }
    if intent["journal_prefix"] != expected_journal:
        raise VerificationError("terminal intent journal prefix mismatch")
    if intent["resource_prefix"] != expected_resource:
        raise VerificationError("terminal intent resource prefix mismatch")
    expected_inventory = _observe_inventory(
        root,
        excluded_paths=_TERMINAL_FILENAMES,
    )
    if intent["artifact_prefix"] != expected_inventory:
        raise VerificationError("terminal intent artifact inventory mismatch")
    return intent


def _verify_terminal(root: Path, intent: Mapping[str, Any]) -> dict[str, Any]:
    terminal = _read_canonical_mapping(root / TERMINAL_FILENAME, "terminal")
    _fields(
        terminal,
        {
            "artifact_prefix_sha256",
            "details",
            "downstream_authority",
            "identity",
            "journal_prefix",
            "resource_prefix",
            "schema_version",
            "terminal_intent_sha256",
            "terminal_sha256",
            "verdict",
        },
        "terminal",
    )
    expected_body = {
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
    expected = {
        **expected_body,
        "terminal_sha256": _canonical_sha256(expected_body),
    }
    if terminal != expected:
        raise VerificationError("terminal differs from its intent")
    return terminal


def _verify_manifest(
    root: Path,
    *,
    terminal: Mapping[str, Any],
) -> dict[str, Any]:
    manifest = _read_canonical_mapping(root / MANIFEST_FILENAME, "artifact manifest")
    _fields(
        manifest,
        {
            "artifact_inventory",
            "downstream_authority",
            "identity",
            "manifest_sha256",
            "schema_version",
            "terminal_intent_sha256",
            "terminal_sha256",
        },
        "artifact manifest",
    )
    expected_inventory = _observe_inventory(root, excluded_paths=(MANIFEST_FILENAME,))
    if manifest["artifact_inventory"] != expected_inventory:
        raise VerificationError("artifact manifest inventory mismatch")
    if (
        manifest["schema_version"] != MANIFEST_SCHEMA_VERSION
        or manifest["identity"] != terminal["identity"]
        or manifest["downstream_authority"] != terminal["downstream_authority"]
        or manifest["terminal_intent_sha256"]
        != terminal["terminal_intent_sha256"]
        or manifest["terminal_sha256"] != terminal["terminal_sha256"]
    ):
        raise VerificationError("artifact manifest terminal binding mismatch")
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if _digest(manifest["manifest_sha256"], "manifest digest") != _canonical_sha256(body):
        raise VerificationError("artifact manifest digest mismatch")
    return manifest


def verify_terminal_bundle(
    output_path: Path | str,
    *,
    expected_identity: Mapping[str, Any],
    expected_child_process_id: int,
    owner_alive: Callable[[int], bool],
) -> dict[str, Any]:
    """Independently reconstruct a closed lifecycle bundle from raw bytes."""
    root = Path(output_path).resolve()
    if not root.is_dir() or root.is_symlink():
        raise VerificationError("terminal bundle root is invalid")
    if not callable(owner_alive):
        raise VerificationError("lease owner observer must be callable")
    identity = _normalize_identity(expected_identity)
    _verify_lease(
        root,
        identity=identity,
        expected_child_process_id=expected_child_process_id,
        owner_alive=owner_alive,
    )
    journal = _verify_access_journal(root, identity=identity)
    ledger = _verify_resource_ledger(
        root,
        identity=identity,
        debited_accesses=journal["debited_accesses"],
    )
    intent = _verify_terminal_intent(
        root,
        identity=identity,
        journal=journal,
        ledger=ledger,
    )
    terminal = _verify_terminal(root, intent)
    manifest = _verify_manifest(root, terminal=terminal)
    return {
        "authority": {name: False for name in _AUTHORITY_NAMES},
        "debited_accesses": journal["debited_accesses"],
        "identity": identity,
        "manifest_sha256": manifest["manifest_sha256"],
        "resources": copy.deepcopy(ledger["resources"]),
        "verdict": terminal["verdict"],
        "verified": True,
    }
