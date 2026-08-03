"""Independently verify bounded non-combat simulator RL artifacts."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import random
import re
import struct
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


EXPERIMENT_SCHEMA_VERSION = "noncombat-simulator-rl-experiment-registration-v1"
AUTHORIZATION_SCHEMA_VERSION = "noncombat-simulator-rl-experiment-authorization-v1"
CONFIGURATION_SCHEMA_VERSION = "noncombat-simulator-rl-configuration-v1"
CHECKPOINT_SCHEMA_VERSION = "noncombat-simulator-rl-checkpoint-v1"
CHECKPOINT_STATE_SCHEMA_VERSION = "noncombat-simulator-rl-checkpoint-state-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-simulator-rl-journal-v1"
LEASE_SCHEMA_VERSION = "noncombat-simulator-rl-lease-v1"
TRAINING_CHUNK_SCHEMA_VERSION = "noncombat-simulator-rl-training-chunk-v1"
EVALUATION_SCHEMA_VERSION = "noncombat-simulator-rl-paired-evaluation-v1"
TERMINAL_EVALUATION_SCHEMA_VERSION = "noncombat-simulator-rl-evaluation-v1"
PREFIX_REPLAY_SCHEMA_VERSION = "noncombat-simulator-rl-prefix-replay-v1"
METRICS_SCHEMA_VERSION = "noncombat-simulator-rl-metrics-v1"
FINAL_MODEL_SCHEMA_VERSION = "noncombat-simulator-rl-final-model-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-simulator-rl-manifest-v1"
FORMAL_READINESS_VERDICT = "not_ready_for_bounded_training_proposal"
ADAPTER_API_VERSION = "sts-lightspeed-noncombat-adapter-v3"
FEATURE_VERSION = "noncombat-simulator-policy-features-v2"
ALGORITHM_VERSION = "candidate-masked-reinforce-experiment-v1"
REWARD_VERSION = "formal-victory-primary-scalar-v1"
NATIVE_TARGET_POLICY_ID = "sts_lightspeed_simple_agent_target_v1"
SIMULATOR_BASELINE_POLICY_ID = "sts_lightspeed_simple_agent_no_potions_v1"

TRAIN_SEEDS = tuple(range(50000, 51024))
CANARY_SEEDS = tuple(range(51024, 51152))
HOLDOUT_SEEDS = tuple(range(51152, 51664))
TARGET_CATEGORIES = ("card_reward", "event", "route", "shop")
REGISTERED_SUPPORT_BLOCKERS = ("unsupported_shop_courier_restock_semantics",)
CHECKPOINT_INTERVAL_EPISODES = 64
TRAINING_CHUNKS = 64
TRAINING_EPISODES = 4096
MAX_WALL_SECONDS = 28_800.0
BOOTSTRAP_SEED = 0
BOOTSTRAP_RESAMPLES = 10_000
CONFIDENCE_LEVEL = 0.95
UNSUPPORTED_RATE_CEILING = 0.10
MAX_DECISIONS_PER_EPISODE = 500
HASH_DIM = 1024
LEARNING_RATE = 0.001
MODEL_SEED = 0
DISCOUNT = 1.0
MAX_FLOOR = 57
VICTORY_WEIGHT = 2.0
TRAIN_PASSES = 4
IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_formal_reward_contract.py",
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_rl_experiment.py",
    "analysis_scripts/verify_noncombat_simulator_rl_experiment.py",
    "scripts/run_noncombat_simulator_rl_experiment.py",
)
EVIDENCE_BINDING_NAMES = (
    "formal_readiness_manifest",
    "formal_reward_manifest",
    "simulator_smoke_manifest",
    "simulator_smoke_registration",
)
AUTHORITY_NAMES = (
    "experiment_execution",
    "formal_noncombat_rl",
    "live_gameplay",
    "live_policy_loading",
    "live_study_launch",
    "ope_estimation",
    "ope_reinterpretation",
    "policy_promotion",
    "qualification",
)
TERMINAL_VERDICTS = {
    "experiment_blocked",
    "experiment_stopped_at_canary",
    "experiment_valid_without_learning_signal",
    "experiment_valid_with_learning_signal",
}
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
_EXECUTION_ID_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")


class VerificationError(ValueError):
    """Raised when terminal artifacts cannot support their claimed verdict."""


class Checks:
    def __init__(self) -> None:
        self.count = 0

    def require(self, condition: bool, message: str) -> None:
        self.count += 1
        if not condition:
            raise VerificationError(message)


def canonical_json_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"value is not canonical JSON: {exc}") from exc


def _duplicate_free(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise VerificationError(f"non-finite JSON constant: {value}")


def load_canonical(path: Path) -> tuple[dict[str, Any], bytes]:
    payload = path.read_bytes()
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_duplicate_free,
            parse_constant=_reject_constant,
        )
    except VerificationError:
        raise
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid JSON: {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"JSON root must be an object: {path.name}")
    if canonical_json_bytes(value) != payload:
        raise VerificationError(f"noncanonical JSON bytes: {path.name}")
    return value, payload


def _require_keys(
    checks: Checks, value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    checks.require(set(value) == expected, f"{label} fields mismatch")


def _all_false_authority(checks: Checks, value: object, label: str) -> None:
    checks.require(isinstance(value, Mapping), f"{label} authority missing")
    checks.require(
        dict(value) == {name: False for name in AUTHORITY_NAMES},
        f"{label} authority is not all false",
    )


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _experiment_contract() -> dict[str, Any]:
    return {
        "algorithm": {
            "discount": DISCOUNT,
            "feature_version": FEATURE_VERSION,
            "hash_dim": HASH_DIM,
            "learning_rate": LEARNING_RATE,
            "model_seed": MODEL_SEED,
            "optimizer": "adam",
            "passes": TRAIN_PASSES,
            "standardize_returns": True,
            "version": ALGORITHM_VERSION,
        },
        "ascension": 0,
        "cohorts": {
            "canary_seeds": list(CANARY_SEEDS),
            "holdout_seeds": list(HOLDOUT_SEEDS),
            "train_seeds": list(TRAIN_SEEDS),
        },
        "evaluation": {
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "confidence_level": CONFIDENCE_LEVEL,
            "holdout_access": "only_after_canary_pass",
            "policy": "greedy",
            "trained_victories_must_exceed_initial": True,
            "unsupported_rate_denominator": "policy_episodes",
        },
        "execution": {
            "allow_parameter_retry": False,
            "logical_execution_count": 1,
            "prefix_replay_chunks": 2,
        },
        "limits": {
            "checkpoint_interval_episodes": CHECKPOINT_INTERVAL_EPISODES,
            "max_decisions_per_episode": MAX_DECISIONS_PER_EPISODE,
            "max_train_episodes": TRAINING_EPISODES,
            "max_wall_seconds": MAX_WALL_SECONDS,
            "unsupported_rate_ceiling": UNSUPPORTED_RATE_CEILING,
        },
        "reward": {
            "discount": DISCOUNT,
            "max_floor": MAX_FLOOR,
            "maximum_episode_floor_progress": 1.0,
            "progress_divisor": float(MAX_FLOOR),
            "strict_primary_dominance": True,
            "version": REWARD_VERSION,
            "victory_weight": VICTORY_WEIGHT,
        },
        "support": {
            "registered_blockers": list(REGISTERED_SUPPORT_BLOCKERS),
            "retain_in_denominator": True,
            "unsupported_disposition": "non_victory_at_last_supported_floor",
        },
    }


def _canonical_relative_path(checks: Checks, value: object, label: str) -> str:
    checks.require(isinstance(value, str) and bool(value), f"{label} path invalid")
    checks.require(
        "\\" not in value and ":" not in value and not value.startswith("/"),
        f"{label} path is not repository-relative POSIX",
    )
    path = PurePosixPath(value)
    checks.require(
        all(part not in {"", ".", ".."} for part in path.parts)
        and path.as_posix() == value,
        f"{label} path is not canonical",
    )
    return value


def _validate_binding(checks: Checks, value: object, label: str) -> dict[str, Any]:
    checks.require(isinstance(value, Mapping), f"{label} binding missing")
    binding = dict(value)
    _require_keys(checks, binding, {"path", "sha256", "size_bytes"}, label)
    _canonical_relative_path(checks, binding["path"], label)
    checks.require(
        isinstance(binding["sha256"], str)
        and _SHA256_RE.fullmatch(binding["sha256"]) is not None,
        f"{label} sha256 invalid",
    )
    checks.require(
        type(binding["size_bytes"]) is int and binding["size_bytes"] > 0,
        f"{label} size invalid",
    )
    return binding


def _validate_registration_identity(
    checks: Checks, value: object
) -> tuple[dict[str, Any], str]:
    checks.require(isinstance(value, Mapping), "registration identity missing")
    identity = dict(value)
    _require_keys(
        checks,
        identity,
        {"adapter_provenance", "evidence", "implementation", "runtime", "seed_inventory"},
        "registration identity",
    )

    implementation = identity["implementation"]
    checks.require(isinstance(implementation, Mapping), "implementation identity missing")
    implementation = dict(implementation)
    _require_keys(
        checks,
        implementation,
        {"commit", "source_files", "source_sha256"},
        "implementation identity",
    )
    commit = implementation["commit"]
    checks.require(
        isinstance(commit, str) and _COMMIT_RE.fullmatch(commit) is not None,
        "implementation commit invalid",
    )
    checks.require(
        implementation["source_files"] == list(IMPLEMENTATION_SOURCE_FILES),
        "implementation source inventory mismatch",
    )
    checks.require(
        isinstance(implementation["source_sha256"], str)
        and _SHA256_RE.fullmatch(implementation["source_sha256"]) is not None,
        "implementation source hash invalid",
    )

    runtime = identity["runtime"]
    checks.require(isinstance(runtime, Mapping), "runtime identity missing")
    runtime = dict(runtime)
    _require_keys(
        checks,
        runtime,
        {"executable", "platform", "python_version", "torch_version"},
        "runtime identity",
    )
    checks.require(
        isinstance(runtime["executable"], str)
        and re.fullmatch(r"[A-Za-z]:/[A-Za-z0-9_./-]+", runtime["executable"])
        is not None,
        "runtime executable invalid",
    )
    checks.require(runtime["platform"] == "win32", "runtime platform mismatch")
    for field in ("python_version", "torch_version"):
        checks.require(
            isinstance(runtime[field], str) and bool(runtime[field]),
            f"runtime {field} invalid",
        )

    provenance = identity["adapter_provenance"]
    checks.require(isinstance(provenance, Mapping), "adapter provenance missing")
    provenance = dict(provenance)
    _require_keys(
        checks,
        provenance,
        {
            "adapter_commit",
            "adapter_source_sha256",
            "build",
            "module_sha256",
            "module_size_bytes",
            "simulator_commit",
            "simulator_dirty",
            "simulator_source_file_count",
            "simulator_source_sha256",
            "submodules",
        },
        "adapter provenance",
    )
    for field in ("adapter_commit", "simulator_commit"):
        checks.require(
            isinstance(provenance[field], str)
            and _COMMIT_RE.fullmatch(provenance[field]) is not None,
            f"adapter provenance {field} invalid",
        )
    for field in ("adapter_source_sha256", "module_sha256", "simulator_source_sha256"):
        checks.require(
            isinstance(provenance[field], str)
            and _SHA256_RE.fullmatch(provenance[field]) is not None,
            f"adapter provenance {field} invalid",
        )
    for field in ("module_size_bytes", "simulator_source_file_count"):
        checks.require(
            type(provenance[field]) is int and provenance[field] > 0,
            f"adapter provenance {field} invalid",
        )
    checks.require(
        type(provenance["simulator_dirty"]) is bool,
        "adapter simulator_dirty invalid",
    )
    submodules = provenance["submodules"]
    checks.require(isinstance(submodules, Mapping), "adapter submodules missing")
    _require_keys(checks, submodules, {"json", "pybind11"}, "adapter submodules")
    for name, submodule_commit in submodules.items():
        checks.require(
            isinstance(submodule_commit, str)
            and _COMMIT_RE.fullmatch(submodule_commit) is not None,
            f"adapter submodule {name} invalid",
        )
    build = provenance["build"]
    checks.require(isinstance(build, Mapping), "adapter build missing")
    _require_keys(
        checks,
        build,
        {
            "adapter_api_version",
            "baseline_policy_id",
            "compiler",
            "cpp_standard",
            "native_target_policy_id",
            "pybind11_version",
            "python",
        },
        "adapter build",
    )
    checks.require(build["adapter_api_version"] == ADAPTER_API_VERSION, "adapter API mismatch")
    checks.require(build["baseline_policy_id"] == SIMULATOR_BASELINE_POLICY_ID, "baseline identity mismatch")
    checks.require(build["native_target_policy_id"] == NATIVE_TARGET_POLICY_ID, "native target identity mismatch")
    for field in ("compiler", "pybind11_version", "python"):
        checks.require(isinstance(build[field], str) and bool(build[field]), f"adapter build {field} invalid")
    checks.require(type(build["cpp_standard"]) is int and build["cpp_standard"] >= 201703, "adapter C++ standard invalid")
    checks.require(build["python"] == runtime["python_version"], "adapter/runtime Python mismatch")

    evidence = identity["evidence"]
    checks.require(isinstance(evidence, Mapping), "registration evidence missing")
    _require_keys(checks, evidence, set(EVIDENCE_BINDING_NAMES), "registration evidence")
    for name in EVIDENCE_BINDING_NAMES:
        _validate_binding(checks, evidence[name], f"evidence.{name}")
    _validate_binding(checks, identity["seed_inventory"], "seed inventory")
    return identity, commit


def _inventory(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_dir():
            continue
        relative = path.relative_to(root).as_posix()
        if relative in {".execution.lease", "artifact_manifest.json"}:
            continue
        if path.is_symlink() or relative.endswith(".tmp"):
            raise VerificationError(f"noncanonical inventory entry: {relative}")
        payload = path.read_bytes()
        rows.append(
            {"path": relative, "sha256": _sha256(payload), "size_bytes": len(payload)}
        )
    return rows


def _validate_tensor(checks: Checks, value: object, label: str) -> None:
    checks.require(isinstance(value, Mapping), f"{label} tensor missing")
    payload = dict(value)
    _require_keys(
        checks,
        payload,
        {"byte_order", "data_base64", "data_sha256", "dtype", "shape"},
        label,
    )
    checks.require(payload["byte_order"] == "little", f"{label} byte order mismatch")
    checks.require(payload["dtype"] in _DTYPE_LAYOUT, f"{label} dtype mismatch")
    shape = payload["shape"]
    checks.require(
        isinstance(shape, list)
        and all(type(item) is int and item >= 0 for item in shape),
        f"{label} shape invalid",
    )
    try:
        raw = base64.b64decode(payload["data_base64"], validate=True)
    except (TypeError, ValueError) as exc:
        raise VerificationError(f"{label} base64 invalid") from exc
    checks.require(_sha256(raw) == payload["data_sha256"], f"{label} hash mismatch")
    size, format_code = _DTYPE_LAYOUT[payload["dtype"]]
    elements = math.prod(shape) if shape else 1
    checks.require(len(raw) == elements * size, f"{label} byte length mismatch")
    if payload["dtype"] in {"float32", "float64"}:
        values = struct.iter_unpack("<" + format_code, raw)
        checks.require(
            all(math.isfinite(item[0]) for item in values),
            f"{label} contains non-finite values",
        )


def _validate_encoded_state(checks: Checks, value: object, label: str) -> None:
    checks.require(isinstance(value, Mapping), f"{label} state node missing")
    node = dict(value)
    kind = node.get("kind")
    if kind == "tensor":
        _require_keys(checks, node, {"kind", "value"}, label)
        _validate_tensor(checks, node["value"], label + ".value")
        return
    if kind == "mapping":
        _require_keys(checks, node, {"items", "kind"}, label)
        checks.require(isinstance(node["items"], list), f"{label} items invalid")
        keys = []
        for index, item in enumerate(node["items"]):
            checks.require(isinstance(item, Mapping), f"{label} item invalid")
            _require_keys(checks, item, {"key", "value"}, f"{label}[{index}]")
            checks.require(isinstance(item["key"], str), f"{label} key invalid")
            keys.append(item["key"])
            _validate_encoded_state(checks, item["value"], f"{label}.{item['key']}")
        checks.require(keys == sorted(set(keys)), f"{label} key order mismatch")
        return
    if kind in {"tuple", "list"}:
        _require_keys(checks, node, {"items", "kind"}, label)
        checks.require(isinstance(node["items"], list), f"{label} items invalid")
        for index, item in enumerate(node["items"]):
            _validate_encoded_state(checks, item, f"{label}[{index}]")
        return
    if kind == "scalar":
        _require_keys(checks, node, {"kind", "value"}, label)
        checks.require(
            node["value"] is None
            or isinstance(node["value"], (bool, int, float, str)),
            f"{label} scalar invalid",
        )
        if isinstance(node["value"], float):
            checks.require(math.isfinite(node["value"]), f"{label} scalar non-finite")
        return
    raise VerificationError(f"{label} state kind invalid")


def _expected_next(chunk_index: int) -> dict[str, Any]:
    if chunk_index == TRAINING_CHUNKS:
        return {"phase": "canary"}
    chunks_per_pass = len(TRAIN_SEEDS) // CHECKPOINT_INTERVAL_EPISODES
    pass_index = chunk_index // chunks_per_pass
    chunk_in_pass = chunk_index % chunks_per_pass
    start = chunk_in_pass * CHECKPOINT_INTERVAL_EPISODES
    seeds = TRAIN_SEEDS[start : start + CHECKPOINT_INTERVAL_EPISODES]
    return {
        "chunk_index": chunk_index,
        "episode_start": chunk_index * CHECKPOINT_INTERVAL_EPISODES,
        "pass_index": pass_index,
        "phase": "training",
        "seed_end": seeds[-1],
        "seed_start": seeds[0],
    }


def _validate_state_payload(
    checks: Checks,
    state: object,
    *,
    index: int,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> dict[str, Any]:
    checks.require(isinstance(state, Mapping), "checkpoint state missing")
    state = dict(state)
    _require_keys(
        checks,
        state,
        {"coordinate", "identity", "model", "optimizer", "random", "schema_version"},
        "checkpoint state",
    )
    checks.require(
        state["schema_version"] == CHECKPOINT_STATE_SCHEMA_VERSION,
        "checkpoint state schema mismatch",
    )
    identity = state["identity"]
    checks.require(
        identity
        == {
            "implementation_commit": implementation_commit,
            "logical_execution_id": logical_execution_id,
            "registration_sha256": registration_sha256,
        },
        "checkpoint state identity mismatch",
    )
    coordinate = state["coordinate"]
    checks.require(isinstance(coordinate, Mapping), "checkpoint coordinate missing")
    _require_keys(
        checks,
        coordinate,
        {"completed_episodes", "next", "next_chunk_index", "optimizer_updates"},
        "checkpoint coordinate",
    )
    checks.require(coordinate.get("next_chunk_index") == index, "checkpoint next index mismatch")
    checks.require(coordinate.get("optimizer_updates") == index, "optimizer update mismatch")
    checks.require(
        coordinate.get("completed_episodes") == index * CHECKPOINT_INTERVAL_EPISODES,
        "checkpoint episode coordinate mismatch",
    )
    checks.require(coordinate.get("next") == _expected_next(index), "next coordinate mismatch")
    model = state["model"]
    checks.require(isinstance(model, Mapping), "checkpoint model missing")
    _require_keys(
        checks,
        model,
        {"architecture", "input_dim", "state_dict"},
        "checkpoint model",
    )
    checks.require(model.get("architecture") == "candidate-ranker-linear-v1", "model architecture mismatch")
    checks.require(model.get("input_dim") == 1024, "model input dimension mismatch")
    state_dict = model.get("state_dict")
    checks.require(
        isinstance(state_dict, Mapping)
        and set(state_dict) == {"scorer.bias", "scorer.weight"},
        "model state fields mismatch",
    )
    checks.require(
        all(isinstance(tensor, Mapping) for tensor in state_dict.values()),
        "model tensor payload missing",
    )
    checks.require(
        state_dict["scorer.bias"].get("shape") == [1]
        and state_dict["scorer.weight"].get("shape") == [1, HASH_DIM],
        "model tensor shapes mismatch",
    )
    for name, tensor in state_dict.items():
        _validate_tensor(checks, tensor, f"model.{name}")
    optimizer = state["optimizer"]
    checks.require(isinstance(optimizer, Mapping), "optimizer state missing")
    _require_keys(checks, optimizer, {"param_groups", "state"}, "optimizer")
    _validate_encoded_state(checks, optimizer["param_groups"], "optimizer.param_groups")
    checks.require(isinstance(optimizer["state"], list), "optimizer state list invalid")
    previous_parameter = -1
    for row in optimizer["state"]:
        checks.require(isinstance(row, Mapping), "optimizer row invalid")
        _require_keys(checks, row, {"parameter_id", "state"}, "optimizer row")
        parameter_id = row.get("parameter_id")
        checks.require(
            type(parameter_id) is int and parameter_id > previous_parameter,
            "optimizer parameter order mismatch",
        )
        previous_parameter = parameter_id
        _validate_encoded_state(checks, row.get("state"), "optimizer parameter state")
    random_state = state["random"]
    checks.require(isinstance(random_state, Mapping), "random state missing")
    _require_keys(
        checks,
        random_state,
        {"action_generator", "python", "torch_global"},
        "random state",
    )
    _validate_tensor(checks, random_state["action_generator"], "action generator")
    _validate_encoded_state(checks, random_state["python"], "Python random")
    _validate_tensor(checks, random_state["torch_global"], "torch global RNG")
    return state


def _verify_checkpoints(
    checks: Checks,
    root: Path,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
    require_complete: bool,
) -> tuple[list[dict[str, Any]], list[bytes]]:
    directory = root / "checkpoints"
    checks.require(directory.is_dir(), "checkpoint directory missing")
    paths = sorted(directory.iterdir())
    checks.require(all(path.is_file() for path in paths), "checkpoint inventory invalid")
    if require_complete:
        checks.require(len(paths) == TRAINING_CHUNKS, "complete checkpoint count mismatch")
    else:
        checks.require(0 <= len(paths) <= TRAINING_CHUNKS, "blocked checkpoint count invalid")
    values = []
    payloads = []
    previous_payload = None
    previous_elapsed = 0.0
    for index, path in enumerate(paths, start=1):
        checks.require(path.name == f"checkpoint_{index:04d}.json", "checkpoint filename gap")
        checkpoint, payload = load_canonical(path)
        _require_keys(
            checks,
            checkpoint,
            {
                "checkpoint_index",
                "cumulative_wall_seconds",
                "logical_execution_id",
                "previous_checkpoint_sha256",
                "schema_version",
                "state_payload",
                "state_payload_sha256",
            },
            "checkpoint",
        )
        checks.require(checkpoint["schema_version"] == CHECKPOINT_SCHEMA_VERSION, "checkpoint schema mismatch")
        checks.require(checkpoint["checkpoint_index"] == index, "checkpoint index mismatch")
        checks.require(checkpoint["logical_execution_id"] == logical_execution_id, "checkpoint execution id mismatch")
        expected_previous = None if previous_payload is None else _sha256(previous_payload)
        checks.require(
            checkpoint["previous_checkpoint_sha256"] == expected_previous,
            "checkpoint chain mismatch",
        )
        elapsed = checkpoint["cumulative_wall_seconds"]
        checks.require(
            isinstance(elapsed, (int, float))
            and not isinstance(elapsed, bool)
            and math.isfinite(float(elapsed))
            and previous_elapsed <= float(elapsed) <= MAX_WALL_SECONDS,
            "checkpoint wall time mismatch",
        )
        previous_elapsed = float(elapsed)
        state = _validate_state_payload(
            checks,
            checkpoint["state_payload"],
            index=index,
            registration_sha256=registration_sha256,
            implementation_commit=implementation_commit,
            logical_execution_id=logical_execution_id,
        )
        checks.require(
            checkpoint["state_payload_sha256"] == _sha256(canonical_json_bytes(state)),
            "checkpoint state payload hash mismatch",
        )
        values.append(checkpoint)
        payloads.append(payload)
        previous_payload = payload
    return values, payloads


def _chunk_seeds(chunk_index: int) -> tuple[int, ...]:
    chunk_in_pass = chunk_index % (len(TRAIN_SEEDS) // CHECKPOINT_INTERVAL_EPISODES)
    start = chunk_in_pass * CHECKPOINT_INTERVAL_EPISODES
    return TRAIN_SEEDS[start : start + CHECKPOINT_INTERVAL_EPISODES]


def _verify_training(
    checks: Checks, root: Path, checkpoint_payloads: Sequence[bytes]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    directory = root / "training"
    checks.require(directory.is_dir(), "training directory missing")
    paths = sorted(directory.iterdir())
    checks.require(len(paths) == len(checkpoint_payloads), "training count mismatch")
    artifacts = []
    categories = set()
    unsupported = 0
    victories = 0
    episodes = 0
    for chunk_index, (path, checkpoint_payload) in enumerate(zip(paths, checkpoint_payloads)):
        checks.require(path.name == f"chunk_{chunk_index:04d}.json", "training filename gap")
        artifact, _ = load_canonical(path)
        _require_keys(
            checks,
            artifact,
            {"checkpoint_index", "checkpoint_sha256", "schema_version", "summary"},
            "training artifact",
        )
        checks.require(artifact["schema_version"] == TRAINING_CHUNK_SCHEMA_VERSION, "training schema mismatch")
        checks.require(artifact["checkpoint_index"] == chunk_index + 1, "training checkpoint index mismatch")
        checks.require(artifact["checkpoint_sha256"] == _sha256(checkpoint_payload), "training checkpoint hash mismatch")
        summary = artifact["summary"]
        checks.require(isinstance(summary, Mapping), "training summary missing")
        _require_keys(
            checks,
            summary,
            {
                "candidate_legality",
                "categories",
                "chunk_index",
                "episode_rows",
                "episodes",
                "loss",
                "mean_episode_return",
                "optimizer_update",
                "pass_index",
                "unsupported_episodes",
                "victories",
            },
            "training summary",
        )
        checks.require(summary.get("chunk_index") == chunk_index, "training chunk index mismatch")
        checks.require(summary.get("episodes") == CHECKPOINT_INTERVAL_EPISODES, "training denominator mismatch")
        checks.require(summary.get("pass_index") == chunk_index // 16, "training pass mismatch")
        checks.require(summary.get("optimizer_update") == chunk_index + 1, "training optimizer coordinate mismatch")
        checks.require(summary.get("candidate_legality") is True, "training legality summary mismatch")
        checks.require(
            isinstance(summary.get("loss"), (int, float))
            and not isinstance(summary.get("loss"), bool)
            and math.isfinite(float(summary["loss"])),
            "training loss invalid",
        )
        checks.require(
            isinstance(summary.get("mean_episode_return"), (int, float))
            and not isinstance(summary.get("mean_episode_return"), bool)
            and math.isfinite(float(summary["mean_episode_return"])),
            "training mean return invalid",
        )
        rows = summary.get("episode_rows")
        checks.require(isinstance(rows, list) and len(rows) == 64, "training rows mismatch")
        expected_seeds = _chunk_seeds(chunk_index)
        chunk_categories = set()
        chunk_unsupported = 0
        chunk_victories = 0
        chunk_returns = []
        for row_index, (row, seed) in enumerate(zip(rows, expected_seeds)):
            checks.require(isinstance(row, Mapping), "training row invalid")
            _require_keys(
                checks,
                row,
                {
                    "action_sequence_sha256",
                    "candidate_legality",
                    "categories",
                    "chunk_index",
                    "decisions",
                    "last_supported_floor",
                    "outcome",
                    "pass_index",
                    "policy_input_sha256s",
                    "retained",
                    "seed",
                    "selected_action_ids",
                    "terminal_floor",
                    "total_reward",
                    "unsupported_reason",
                    "victory",
                },
                "training row",
            )
            checks.require(row.get("chunk_index") == chunk_index, "training row chunk mismatch")
            checks.require(row.get("pass_index") == chunk_index // 16, "training row pass mismatch")
            checks.require(row.get("seed") == seed, "training row seed mismatch")
            checks.require(
                row.get("candidate_legality") is True and row.get("retained") is True,
                "training row was dropped or illegal",
            )
            decisions = row.get("decisions")
            checks.require(
                type(decisions) is int and 1 <= decisions <= MAX_DECISIONS_PER_EPISODE,
                "training row decision count invalid",
            )
            action_ids = row.get("selected_action_ids")
            policy_hashes = row.get("policy_input_sha256s")
            checks.require(
                isinstance(action_ids, list)
                and len(action_ids) == decisions
                and all(isinstance(value, str) and value for value in action_ids),
                "training row action sequence invalid",
            )
            checks.require(
                isinstance(policy_hashes, list)
                and len(policy_hashes) == decisions
                and all(
                    isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None
                    for value in policy_hashes
                ),
                "training row policy hashes invalid",
            )
            checks.require(
                isinstance(row.get("action_sequence_sha256"), str)
                and _SHA256_RE.fullmatch(row["action_sequence_sha256"]) is not None,
                "training row action hash invalid",
            )
            row_categories = row.get("categories")
            checks.require(
                isinstance(row_categories, list)
                and row_categories == sorted(set(row_categories))
                and bool(row_categories)
                and all(category in TARGET_CATEGORIES for category in row_categories),
                "training row categories invalid",
            )
            reason = row.get("unsupported_reason")
            checks.require(
                reason is None or reason in REGISTERED_SUPPORT_BLOCKERS,
                "training row support reason mismatch",
            )
            last_floor = row.get("last_supported_floor")
            checks.require(
                isinstance(last_floor, (int, float))
                and not isinstance(last_floor, bool)
                and math.isfinite(float(last_floor))
                and 0.0 <= float(last_floor) <= MAX_FLOOR,
                "training row floor invalid",
            )
            reward = row.get("total_reward")
            checks.require(
                isinstance(reward, (int, float))
                and not isinstance(reward, bool)
                and math.isfinite(float(reward))
                and 0.0 <= float(reward) <= VICTORY_WEIGHT + 1.0,
                "training row reward invalid",
            )
            victory = row.get("victory")
            checks.require(type(victory) is bool, "training row victory invalid")
            if reason is None:
                checks.require(
                    row.get("outcome") in {"player_loss", "player_victory"}
                    and isinstance(row.get("terminal_floor"), (int, float))
                    and not isinstance(row.get("terminal_floor"), bool)
                    and float(row["terminal_floor"]) == float(last_floor)
                    and victory == (row["outcome"] == "player_victory"),
                    "training terminal disposition mismatch",
                )
            else:
                checks.require(
                    row.get("outcome") is None
                    and row.get("terminal_floor") is None
                    and victory is False,
                    "training blocker disposition mismatch",
                )
            chunk_unsupported += reason is not None
            chunk_victories += int(victory)
            chunk_returns.append(float(reward))
            chunk_categories.update(row_categories)
            episodes += 1
        checks.require(
            summary.get("categories") == sorted(chunk_categories),
            "training category aggregate mismatch",
        )
        checks.require(
            summary.get("unsupported_episodes") == chunk_unsupported,
            "training unsupported aggregate mismatch",
        )
        checks.require(
            summary.get("victories") == chunk_victories,
            "training victory aggregate mismatch",
        )
        checks.require(
            float(summary["mean_episode_return"])
            == sum(chunk_returns) / len(chunk_returns),
            "training return aggregate mismatch",
        )
        unsupported += chunk_unsupported
        victories += chunk_victories
        categories.update(chunk_categories)
        artifacts.append(artifact)
    return artifacts, {
        "categories": sorted(categories),
        "episodes": episodes,
        "optimizer_updates": len(artifacts),
        "unsupported_episodes": unsupported,
        "victories": victories,
    }


def _verify_journal(
    checks: Checks,
    root: Path,
    *,
    logical_execution_id: str,
    registration_sha256: str,
    checkpoint_payloads: Sequence[bytes],
    training_paths: Sequence[Path],
    verdict: str,
    prefix_replay_verified: bool,
) -> None:
    directory = root / "journal"
    checks.require(directory.is_dir(), "journal directory missing")
    paths = sorted(directory.iterdir())
    checks.require(len(paths) == len(checkpoint_payloads) + 2, "journal count mismatch")
    previous = None
    for index, path in enumerate(paths):
        checks.require(path.name == f"record_{index:06d}.json", "journal filename gap")
        record, payload = load_canonical(path)
        _require_keys(
            checks,
            record,
            {"details", "index", "logical_execution_id", "phase", "previous_record_sha256", "schema_version"},
            "journal record",
        )
        checks.require(record["schema_version"] == JOURNAL_SCHEMA_VERSION, "journal schema mismatch")
        checks.require(record["index"] == index, "journal index mismatch")
        checks.require(record["logical_execution_id"] == logical_execution_id, "journal execution id mismatch")
        checks.require(record["previous_record_sha256"] == (None if previous is None else _sha256(previous)), "journal chain mismatch")
        if index == 0:
            checks.require(record["phase"] == "started", "journal does not start")
            checks.require(record["details"] == {"registration_sha256": registration_sha256}, "started journal identity mismatch")
        elif index <= len(checkpoint_payloads):
            checks.require(record["phase"] == "continued", "journal continuation mismatch")
            checkpoint_index = index
            expected = {
                "checkpoint_index": checkpoint_index,
                "checkpoint_sha256": _sha256(checkpoint_payloads[index - 1]),
                "training_summary_sha256": _sha256(training_paths[index - 1].read_bytes()),
            }
            checks.require(record["details"] == expected, "journal checkpoint binding mismatch")
        else:
            expected_phase = "blocked" if verdict == "experiment_blocked" else "terminal"
            checks.require(record["phase"] == expected_phase, "journal terminal phase mismatch")
            checks.require(
                record["details"]
                == {"prefix_replay_verified": prefix_replay_verified, "verdict": verdict},
                "journal terminal details mismatch",
            )
        previous = payload


def _quantile(values: Sequence[float], probability: float) -> float:
    position = probability * (len(values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(values[lower])
    weight = position - lower
    return float(values[lower] * (1.0 - weight) + values[upper] * weight)


def _bootstrap(differences: Sequence[float]) -> dict[str, Any]:
    values = [float(value) for value in differences]
    if not values or any(not math.isfinite(value) for value in values):
        raise VerificationError("paired differences invalid")
    if all(value == values[0] for value in values[1:]):
        lower = upper = values[0]
    else:
        generator = random.Random(BOOTSTRAP_SEED)
        means = [
            sum(values[generator.randrange(len(values))] for _ in values) / len(values)
            for _ in range(BOOTSTRAP_RESAMPLES)
        ]
        means.sort()
        tail = (1.0 - CONFIDENCE_LEVEL) / 2.0
        lower = _quantile(means, tail)
        upper = _quantile(means, 1.0 - tail)
    return {
        "confidence_level": CONFIDENCE_LEVEL,
        "lower": lower,
        "mean": sum(values) / len(values),
        "resamples": BOOTSTRAP_RESAMPLES,
        "upper": upper,
    }


def _rebuild_paired_evaluation(
    checks: Checks, evaluation: object, cohort: str
) -> dict[str, Any]:
    checks.require(isinstance(evaluation, Mapping), f"{cohort} evaluation missing")
    evaluation = dict(evaluation)
    seeds = CANARY_SEEDS if cohort == "canary" else HOLDOUT_SEEDS
    initial_block = evaluation.get("initial")
    trained_block = evaluation.get("trained")
    checks.require(isinstance(initial_block, Mapping), f"{cohort} initial missing")
    checks.require(isinstance(trained_block, Mapping), f"{cohort} trained missing")
    initial_rows = initial_block.get("rows")
    trained_rows = trained_block.get("rows")
    checks.require(isinstance(initial_rows, list) and len(initial_rows) == len(seeds), f"{cohort} initial count mismatch")
    checks.require(isinstance(trained_rows, list) and len(trained_rows) == len(seeds), f"{cohort} trained count mismatch")
    initial_categories = set()
    trained_categories = set()
    paired = []
    initial_unsupported = 0
    trained_unsupported = 0
    initial_victories = 0
    trained_victories = 0
    for index, seed in enumerate(seeds):
        initial = initial_rows[index]
        trained = trained_rows[index]
        for label, row in (("initial", initial), ("trained", trained)):
            checks.require(isinstance(row, Mapping), f"{cohort} {label} row invalid")
            _require_keys(
                checks,
                row,
                {
                    "action_sequence_sha256",
                    "candidate_legality",
                    "categories",
                    "decisions",
                    "last_supported_floor",
                    "outcome",
                    "policy_input_sha256s",
                    "retained",
                    "seed",
                    "selected_action_ids",
                    "terminal_floor",
                    "total_reward",
                    "unsupported_reason",
                    "victory",
                },
                f"{cohort} {label} row",
            )
            checks.require(row.get("seed") == seed, f"{cohort} {label} seed mismatch")
            checks.require(row.get("candidate_legality") is True and row.get("retained") is True, f"{cohort} {label} row not legal")
            decisions = row.get("decisions")
            checks.require(
                type(decisions) is int and 1 <= decisions <= MAX_DECISIONS_PER_EPISODE,
                f"{cohort} {label} decisions invalid",
            )
            action_ids = row.get("selected_action_ids")
            policy_hashes = row.get("policy_input_sha256s")
            checks.require(
                isinstance(action_ids, list)
                and len(action_ids) == decisions
                and all(isinstance(value, str) and value for value in action_ids),
                f"{cohort} {label} actions invalid",
            )
            checks.require(
                isinstance(policy_hashes, list)
                and len(policy_hashes) == decisions
                and all(
                    isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None
                    for value in policy_hashes
                ),
                f"{cohort} {label} policy hashes invalid",
            )
            checks.require(
                isinstance(row.get("action_sequence_sha256"), str)
                and _SHA256_RE.fullmatch(row["action_sequence_sha256"]) is not None,
                f"{cohort} {label} action hash invalid",
            )
            categories = row.get("categories")
            checks.require(
                isinstance(categories, list)
                and categories == sorted(set(categories))
                and bool(categories),
                f"{cohort} {label} categories missing",
            )
            checks.require(all(category in TARGET_CATEGORIES for category in categories), f"{cohort} {label} category invalid")
            reason = row.get("unsupported_reason")
            checks.require(reason is None or reason in REGISTERED_SUPPORT_BLOCKERS, f"{cohort} {label} blocker invalid")
            floor = row.get("last_supported_floor")
            checks.require(
                isinstance(floor, (int, float))
                and not isinstance(floor, bool)
                and math.isfinite(float(floor))
                and 0.0 <= float(floor) <= MAX_FLOOR,
                f"{cohort} {label} floor invalid",
            )
            total_reward = row.get("total_reward")
            checks.require(
                isinstance(total_reward, (int, float))
                and not isinstance(total_reward, bool)
                and math.isfinite(float(total_reward))
                and 0.0 <= float(total_reward) <= VICTORY_WEIGHT + 1.0,
                f"{cohort} {label} reward invalid",
            )
            checks.require(type(row.get("victory")) is bool, f"{cohort} {label} victory invalid")
            if reason is None:
                checks.require(row.get("outcome") in {"player_loss", "player_victory"}, f"{cohort} {label} outcome invalid")
                checks.require(row.get("terminal_floor") == floor, f"{cohort} {label} terminal floor mismatch")
                checks.require(row.get("victory") is (row.get("outcome") == "player_victory"), f"{cohort} {label} victory mismatch")
            else:
                checks.require(row.get("outcome") is None and row.get("terminal_floor") is None and row.get("victory") is False, f"{cohort} {label} unsupported disposition mismatch")
        initial_categories.update(initial["categories"])
        trained_categories.update(trained["categories"])
        initial_unsupported += initial["unsupported_reason"] is not None
        trained_unsupported += trained["unsupported_reason"] is not None
        initial_victories += bool(initial["victory"])
        trained_victories += bool(trained["victory"])
        initial_floor = float(initial["last_supported_floor"])
        trained_floor = float(trained["last_supported_floor"])
        paired.append(
            {
                "floor_difference": trained_floor - initial_floor,
                "initial_floor": initial_floor,
                "initial_outcome": initial["outcome"],
                "initial_unsupported_reason": initial["unsupported_reason"],
                "initial_victory": bool(initial["victory"]),
                "seed": seed,
                "trained_floor": trained_floor,
                "trained_outcome": trained["outcome"],
                "trained_unsupported_reason": trained["unsupported_reason"],
                "trained_victory": bool(trained["victory"]),
                "victory_difference": int(trained["victory"]) - int(initial["victory"]),
            }
        )
    denominator = 2 * len(seeds)
    rebuilt = {
        "cohort": cohort,
        "floor_difference_ci": _bootstrap([row["floor_difference"] for row in paired]),
        "initial": {
            "categories": sorted(initial_categories),
            "rows": initial_rows,
            "unsupported_episodes": initial_unsupported,
            "victories": initial_victories,
        },
        "paired_rows": paired,
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "trained": {
            "categories": sorted(trained_categories),
            "rows": trained_rows,
            "unsupported_episodes": trained_unsupported,
            "victories": trained_victories,
        },
        "unsupported_rate": (initial_unsupported + trained_unsupported) / denominator,
        "unsupported_rate_denominator": denominator,
    }
    checks.require(canonical_json_bytes(evaluation) == canonical_json_bytes(rebuilt), f"{cohort} evaluation recomputation mismatch")
    return rebuilt


def _canary_gate(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    blockers = []
    required_categories = list(TARGET_CATEGORIES)
    if evaluation["initial"]["categories"] != required_categories:
        blockers.append("initial_four_category_coverage")
    if evaluation["trained"]["categories"] != required_categories:
        blockers.append("trained_four_category_coverage")
    if evaluation["unsupported_rate"] > UNSUPPORTED_RATE_CEILING:
        blockers.append("unsupported_rate")
    if evaluation["trained"]["victories"] < evaluation["initial"]["victories"]:
        blockers.append("trained_victory_noninferiority")
    if evaluation["floor_difference_ci"]["lower"] <= 0.0:
        blockers.append("paired_floor_lower_bound")
    return {
        "blockers": blockers,
        "floor_difference_ci": evaluation["floor_difference_ci"],
        "initial_victories": evaluation["initial"]["victories"],
        "passed": not blockers,
        "trained_victories": evaluation["trained"]["victories"],
        "unsupported_rate": evaluation["unsupported_rate"],
        "unsupported_rate_denominator": evaluation["unsupported_rate_denominator"],
        "verdict": "canary_passed" if not blockers else "experiment_stopped_at_canary",
    }


def _holdout_classification(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    victory_signal = evaluation["trained"]["victories"] > evaluation["initial"]["victories"]
    floor_signal = evaluation["floor_difference_ci"]["lower"] > 0.0
    return {
        "floor_difference_ci": evaluation["floor_difference_ci"],
        "floor_signal": floor_signal,
        "initial_victories": evaluation["initial"]["victories"],
        "trained_victories": evaluation["trained"]["victories"],
        "unsupported_rate": evaluation["unsupported_rate"],
        "verdict": (
            "experiment_valid_with_learning_signal"
            if victory_signal and floor_signal
            else "experiment_valid_without_learning_signal"
        ),
        "victory_signal": victory_signal,
    }


def _render_terminal_report(metrics: Mapping[str, Any]) -> bytes:
    lines = [
        "# Bounded Non-Combat Simulator RL Experiment",
        "",
        f"- Verdict: `{metrics['verdict']}`",
        f"- Formal readiness: `{FORMAL_READINESS_VERDICT}`",
        f"- Training episodes: {metrics['training']['episodes']}",
        f"- Training optimizer updates: {metrics['training']['optimizer_updates']}",
    ]
    if "canary" in metrics:
        lines.extend(
            [
                f"- Canary initial victories: {metrics['canary']['initial_victories']}",
                f"- Canary trained victories: {metrics['canary']['trained_victories']}",
                f"- Canary paired floor CI lower: {metrics['canary']['floor_difference_ci']['lower']}",
            ]
        )
    if "holdout" in metrics:
        lines.extend(
            [
                f"- Holdout initial victories: {metrics['holdout']['initial_victories']}",
                f"- Holdout trained victories: {metrics['holdout']['trained_victories']}",
                f"- Holdout paired floor CI lower: {metrics['holdout']['floor_difference_ci']['lower']}",
            ]
        )
    if metrics.get("blocked_reason"):
        lines.append(f"- Blocked reason: `{metrics['blocked_reason']}`")
    lines.extend(
        [
            "",
            "This result is simulator-only. It grants no Current, live, OPE, causal,",
            "qualification, loading, formal-RL, or promotion authority.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def verify_artifact_directory(output_dir: Path | str) -> dict[str, Any]:
    """Recompute one terminal result without importing native code or PyTorch."""
    forbidden = [
        name
        for name in sys.modules
        if name == "torch"
        or name.startswith("torch.")
        or name == "sts_lightspeed_noncombat_adapter"
    ]
    if forbidden:
        raise VerificationError(f"forbidden modules already loaded: {forbidden[:3]}")
    checks = Checks()
    root = Path(output_dir)
    checks.require(root.is_dir(), "artifact directory missing")
    manifest, _ = load_canonical(root / "artifact_manifest.json")
    _require_keys(
        checks,
        manifest,
        {"artifact_inventory", "authority", "formal_readiness_verdict", "logical_execution_id", "registration_sha256", "schema_version", "verdict"},
        "manifest",
    )
    checks.require(manifest["schema_version"] == MANIFEST_SCHEMA_VERSION, "manifest schema mismatch")
    checks.require(manifest["verdict"] in TERMINAL_VERDICTS, "manifest verdict invalid")
    checks.require(manifest["formal_readiness_verdict"] == FORMAL_READINESS_VERDICT, "formal readiness drifted")
    _all_false_authority(checks, manifest["authority"], "manifest")
    checks.require(manifest["artifact_inventory"] == _inventory(root), "manifest inventory mismatch")

    verdict = manifest["verdict"]
    require_complete = verdict != "experiment_blocked"
    expected_root = {
        "artifact_manifest.json",
        "authorization.json",
        "checkpoints",
        "configuration.json",
        "journal",
        "metrics.json",
        "model.json",
        "registration.json",
        "report.md",
        "training",
    }
    if require_complete:
        expected_root.add("evaluation.json")
        expected_root.add("prefix_replay.json")
    elif (root / "prefix_replay.json").exists():
        expected_root.add("prefix_replay.json")
    if (root / ".execution.lease").exists():
        expected_root.add(".execution.lease")
    checks.require({path.name for path in root.iterdir()} == expected_root, "root inventory mismatch")

    registration, registration_bytes = load_canonical(root / "registration.json")
    _require_keys(
        checks,
        registration,
        {"authority", "experiment", "identity", "schema_version"},
        "registration",
    )
    checks.require(
        registration["schema_version"] == EXPERIMENT_SCHEMA_VERSION,
        "registration schema mismatch",
    )
    _all_false_authority(checks, registration["authority"], "registration")
    registration_sha256 = _sha256(registration_bytes)
    checks.require(registration_sha256 == manifest["registration_sha256"], "registration hash mismatch")
    experiment = registration["experiment"]
    checks.require(experiment == _experiment_contract(), "experiment contract drift")
    identity, implementation_commit = _validate_registration_identity(
        checks, registration["identity"]
    )

    authorization, authorization_bytes = load_canonical(root / "authorization.json")
    _require_keys(
        checks,
        authorization,
        {
            "authority",
            "logical_execution_id",
            "output_directory",
            "registration",
            "schema_version",
        },
        "authorization",
    )
    checks.require(authorization["schema_version"] == AUTHORIZATION_SCHEMA_VERSION, "authorization schema mismatch")
    expected_execution_authority = {name: False for name in AUTHORITY_NAMES}
    expected_execution_authority["experiment_execution"] = True
    checks.require(authorization["authority"] == expected_execution_authority, "authorization authority mismatch")
    execution_id = authorization["logical_execution_id"]
    checks.require(
        isinstance(execution_id, str)
        and _EXECUTION_ID_RE.fullmatch(execution_id) is not None,
        "authorization execution id invalid",
    )
    checks.require(execution_id == manifest["logical_execution_id"], "authorization execution id mismatch")
    output_relative = _canonical_relative_path(
        checks, authorization["output_directory"], "authorization output"
    )
    checks.require(
        output_relative.startswith("reports/noncombat_simulator_rl_experiment_")
        and "checkpoints" not in PurePosixPath(output_relative).parts,
        "authorization output is outside the contract",
    )
    checks.require(
        root.name == PurePosixPath(output_relative).name,
        "authorization output mismatch",
    )
    binding = authorization["registration"]
    checks.require(isinstance(binding, Mapping), "authorization registration binding missing")
    _require_keys(
        checks,
        binding,
        {"commit", "path", "sha256", "size_bytes"},
        "authorization registration binding",
    )
    checks.require(
        isinstance(binding["commit"], str)
        and _COMMIT_RE.fullmatch(binding["commit"]) is not None,
        "authorization registration commit invalid",
    )
    registration_path = _canonical_relative_path(
        checks, binding["path"], "authorization registration"
    )
    checks.require(
        registration_path.startswith("reports/noncombat_simulator_rl_experiment_")
        and registration_path.endswith("_registration.json"),
        "authorization registration path mismatch",
    )
    checks.require(
        binding["sha256"] == registration_sha256
        and binding["size_bytes"] == len(registration_bytes),
        "authorization registration binding mismatch",
    )
    if (root / ".execution.lease").exists():
        lease, _ = load_canonical(root / ".execution.lease")
        checks.require(
            lease
            == {
                "logical_execution_id": execution_id,
                "schema_version": LEASE_SCHEMA_VERSION,
            },
            "execution lease mismatch",
        )

    configuration, _ = load_canonical(root / "configuration.json")
    expected_configuration = {
        "authority": {name: False for name in AUTHORITY_NAMES},
        "authorization_sha256": _sha256(authorization_bytes),
        "experiment": experiment,
        "formal_readiness_verdict": FORMAL_READINESS_VERDICT,
        "identity": identity,
        "logical_execution_id": execution_id,
        "registration_sha256": registration_sha256,
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
    }
    checks.require(configuration == expected_configuration, "configuration mismatch")

    checkpoints, checkpoint_payloads = _verify_checkpoints(
        checks,
        root,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=manifest["logical_execution_id"],
        require_complete=require_complete,
    )
    prefix_cumulative_wall = None
    if require_complete or (root / "prefix_replay.json").exists():
        checks.require(len(checkpoints) >= 2, "prefix replay lacks checkpoint 2")
        prefix, _ = load_canonical(root / "prefix_replay.json")
        _require_keys(
            checks,
            prefix,
            {
                "checkpoint_index",
                "checkpoint_sha256",
                "cumulative_wall_seconds",
                "replay_wall_seconds",
                "schema_version",
                "state_payload_sha256",
                "verified",
            },
            "prefix replay",
        )
        checks.require(prefix["schema_version"] == PREFIX_REPLAY_SCHEMA_VERSION, "prefix replay schema mismatch")
        checks.require(prefix["checkpoint_index"] == 2 and prefix["verified"] is True, "prefix replay verdict mismatch")
        checks.require(prefix["checkpoint_sha256"] == _sha256(checkpoint_payloads[1]), "prefix replay checkpoint hash mismatch")
        checks.require(
            prefix["state_payload_sha256"]
            == checkpoints[1]["state_payload_sha256"],
            "prefix replay state hash mismatch",
        )
        replay_wall = prefix["replay_wall_seconds"]
        prefix_cumulative_wall = prefix["cumulative_wall_seconds"]
        checks.require(
            isinstance(replay_wall, (int, float))
            and not isinstance(replay_wall, bool)
            and math.isfinite(float(replay_wall))
            and float(replay_wall) >= 0.0,
            "prefix replay wall time invalid",
        )
        checks.require(
            isinstance(prefix_cumulative_wall, (int, float))
            and not isinstance(prefix_cumulative_wall, bool)
            and math.isfinite(float(prefix_cumulative_wall))
            and 0.0 <= float(prefix_cumulative_wall) <= MAX_WALL_SECONDS,
            "prefix replay cumulative wall time invalid",
        )
        checks.require(
            float(prefix_cumulative_wall)
            == float(checkpoints[1]["cumulative_wall_seconds"]) + float(replay_wall),
            "prefix replay cumulative wall time mismatch",
        )
        if len(checkpoints) > 2:
            checks.require(
                float(checkpoints[2]["cumulative_wall_seconds"])
                >= float(prefix_cumulative_wall),
                "checkpoint wall time precedes prefix replay",
            )
    training_paths = sorted((root / "training").iterdir())
    _, training_aggregates = _verify_training(checks, root, checkpoint_payloads)

    metrics, _ = load_canonical(root / "metrics.json")
    common_metric_fields = {
        "authority",
        "blocked_reason",
        "cumulative_wall_seconds",
        "formal_readiness_verdict",
        "logical_execution_id",
        "prefix_replay_verified",
        "registration_sha256",
        "schema_version",
        "training",
        "verdict",
    }
    allowed_metric_fields = (
        common_metric_fields | {"canary", "holdout"}
        if require_complete
        else common_metric_fields
    )
    checks.require(
        common_metric_fields <= set(metrics) <= allowed_metric_fields,
        "metrics fields mismatch",
    )
    checks.require(metrics.get("schema_version") == METRICS_SCHEMA_VERSION, "metrics schema mismatch")
    checks.require(metrics.get("verdict") == verdict, "metrics verdict mismatch")
    checks.require(metrics.get("registration_sha256") == registration_sha256, "metrics registration mismatch")
    checks.require(metrics.get("logical_execution_id") == manifest["logical_execution_id"], "metrics execution id mismatch")
    checks.require(metrics.get("formal_readiness_verdict") == FORMAL_READINESS_VERDICT, "metrics readiness mismatch")
    _all_false_authority(checks, metrics.get("authority"), "metrics")
    checks.require(metrics.get("training") == training_aggregates, "metrics training aggregates mismatch")
    prefix_replay_verified = metrics.get("prefix_replay_verified")
    checks.require(type(prefix_replay_verified) is bool, "prefix replay flag invalid")
    cumulative_wall = metrics.get("cumulative_wall_seconds")
    checks.require(
        isinstance(cumulative_wall, (int, float))
        and not isinstance(cumulative_wall, bool)
        and math.isfinite(float(cumulative_wall))
        and 0.0 <= float(cumulative_wall) <= MAX_WALL_SECONDS,
        "metrics cumulative wall time invalid",
    )
    if checkpoints:
        checks.require(
            float(cumulative_wall)
            >= float(checkpoints[-1]["cumulative_wall_seconds"]),
            "metrics cumulative wall time precedes checkpoint",
        )
    if prefix_cumulative_wall is not None:
        checks.require(
            float(cumulative_wall) >= float(prefix_cumulative_wall),
            "metrics cumulative wall time precedes prefix replay",
        )
    if require_complete:
        checks.require(metrics.get("blocked_reason") is None, "complete result has blocked reason")
        checks.require(prefix_replay_verified is True, "complete result lacks prefix replay")
        evaluation_artifact, _ = load_canonical(root / "evaluation.json")
        _require_keys(
            checks,
            evaluation_artifact,
            {
                "authority",
                "formal_readiness_verdict",
                "registration_sha256",
                "result",
                "schema_version",
            },
            "evaluation artifact",
        )
        checks.require(evaluation_artifact.get("schema_version") == TERMINAL_EVALUATION_SCHEMA_VERSION, "evaluation artifact schema mismatch")
        _all_false_authority(checks, evaluation_artifact.get("authority"), "evaluation")
        checks.require(
            evaluation_artifact.get("formal_readiness_verdict")
            == FORMAL_READINESS_VERDICT,
            "evaluation readiness mismatch",
        )
        checks.require(evaluation_artifact.get("registration_sha256") == registration_sha256, "evaluation registration mismatch")
        result = evaluation_artifact.get("result")
        checks.require(isinstance(result, Mapping), "terminal evaluation result missing")
        _require_keys(
            checks,
            result,
            {"canary", "canary_gate", "holdout", "verdict"},
            "terminal evaluation result",
        )
        canary = _rebuild_paired_evaluation(checks, result.get("canary"), "canary")
        canary_gate = _canary_gate(canary)
        checks.require(result.get("canary_gate") == canary_gate, "canary gate mismatch")
        checks.require(metrics.get("canary") == canary_gate, "metrics canary mismatch")
        if not canary_gate["passed"]:
            _require_keys(checks, metrics, common_metric_fields | {"canary"}, "metrics")
            checks.require(verdict == "experiment_stopped_at_canary", "stopped canary verdict mismatch")
            checks.require(result.get("holdout") == {"accessed": False, "episode_count": 0}, "holdout was not untouched")
            checks.require("holdout" not in metrics, "stopped canary published holdout metrics")
        else:
            _require_keys(
                checks,
                metrics,
                common_metric_fields | {"canary", "holdout"},
                "metrics",
            )
            holdout_block = result.get("holdout")
            checks.require(isinstance(holdout_block, Mapping) and holdout_block.get("accessed") is True, "holdout access missing")
            _require_keys(
                checks,
                holdout_block,
                {"accessed", "classification", "episode_count", "evaluation"},
                "terminal holdout",
            )
            checks.require(holdout_block.get("episode_count") == 2 * len(HOLDOUT_SEEDS), "holdout denominator mismatch")
            holdout = _rebuild_paired_evaluation(checks, holdout_block.get("evaluation"), "holdout")
            classification = _holdout_classification(holdout)
            checks.require(holdout_block.get("classification") == classification, "holdout classification mismatch")
            checks.require(metrics.get("holdout") == classification, "metrics holdout mismatch")
            checks.require(verdict == classification["verdict"] == result.get("verdict"), "learning verdict mismatch")
    else:
        _require_keys(checks, metrics, common_metric_fields, "metrics")
        checks.require(not (root / "evaluation.json").exists(), "blocked result published evaluation")
        checks.require(isinstance(metrics.get("blocked_reason"), str) and metrics["blocked_reason"], "blocked reason missing")

    checks.require(
        (root / "report.md").read_bytes() == _render_terminal_report(metrics),
        "terminal report mismatch",
    )

    model, _ = load_canonical(root / "model.json")
    _require_keys(
        checks,
        model,
        {
            "architecture",
            "authority",
            "input_dim",
            "registration_sha256",
            "schema_version",
            "state_dict",
            "verdict",
        },
        "final model",
    )
    checks.require(model.get("schema_version") == FINAL_MODEL_SCHEMA_VERSION, "final model schema mismatch")
    checks.require(model.get("verdict") == verdict, "final model verdict mismatch")
    checks.require(model.get("registration_sha256") == registration_sha256, "final model registration mismatch")
    _all_false_authority(checks, model.get("authority"), "final model")
    checks.require(model.get("architecture") == "candidate-ranker-linear-v1" and model.get("input_dim") == 1024, "final model architecture mismatch")
    state_dict = model["state_dict"]
    checks.require(
        isinstance(state_dict, Mapping)
        and set(state_dict) == {"scorer.bias", "scorer.weight"},
        "final model state fields mismatch",
    )
    checks.require(
        all(isinstance(tensor, Mapping) for tensor in state_dict.values()),
        "final model tensor payload missing",
    )
    checks.require(
        state_dict["scorer.bias"].get("shape") == [1]
        and state_dict["scorer.weight"].get("shape") == [1, HASH_DIM],
        "final model tensor shapes mismatch",
    )
    for name, tensor in state_dict.items():
        _validate_tensor(checks, tensor, f"final model.{name}")
    if checkpoints:
        checkpoint_model = checkpoints[-1]["state_payload"]["model"]
        checks.require(model.get("state_dict") == checkpoint_model.get("state_dict"), "final model differs from checkpoint")

    _verify_journal(
        checks,
        root,
        logical_execution_id=manifest["logical_execution_id"],
        registration_sha256=registration_sha256,
        checkpoint_payloads=checkpoint_payloads,
        training_paths=training_paths,
        verdict=verdict,
        prefix_replay_verified=prefix_replay_verified,
    )
    forbidden_after = [
        name
        for name in sys.modules
        if name == "torch"
        or name.startswith("torch.")
        or name == "sts_lightspeed_noncombat_adapter"
    ]
    checks.require(not forbidden_after, "verifier loaded a forbidden module")
    return {
        "artifact_count": len(manifest["artifact_inventory"]),
        "checks": checks.count,
        "formal_readiness_verdict": FORMAL_READINESS_VERDICT,
        "verdict": verdict,
        "verification": "verified",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = verify_artifact_directory(args.output_dir)
    except (OSError, VerificationError) as exc:
        print(json.dumps({"error": str(exc), "verification": "failed"}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
