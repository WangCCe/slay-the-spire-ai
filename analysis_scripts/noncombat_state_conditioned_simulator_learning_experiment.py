"""State-conditioned, simulator-only non-combat learning experiment.

The module keeps source-only control validation free of Torch and native module
loading. Torch-backed model and rollout components are imported only when an
authorized execution path explicitly initializes a runtime.
"""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
from importlib import metadata as importlib_metadata
import json
import math
import os
import platform
import random
import re
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Integral, Real
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


EXPERIMENT_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-registration-v1"
)
AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-authorization-v1"
)
MANIFEST_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-manifest-v2"
)
FULL_TERMINAL_ARTIFACT_NAMES = frozenset(
    {
        "authorization.json",
        "configuration.json",
        "diagnostics.json",
        "evaluation.json",
        "execution_journal.json",
        "final_model.json",
        "isolation.json",
        "metrics.json",
        "registration.json",
        "report.json",
        "training_rows.json",
    }
)
FULL_TERMINAL_ARTIFACT_CASEFOLDS = frozenset(
    name.casefold() for name in FULL_TERMINAL_ARTIFACT_NAMES
)
CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-checkpoint-v1"
)
EVALUATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-paired-evaluation-v1"
)
ALGORITHM_VERSION = "state-conditioned-candidate-masked-reinforce-v1"
REWARD_VERSION = "formal-victory-primary-scalar-v1"
FEATURE_VERSION = "noncombat-state-conditioned-policy-features-v1"
ARCHITECTURE_ID = "state-conditioned-candidate-ranker-mlp-v1"
HASH_DIM = 1024
HIDDEN_DIM = 64
MODEL_SEED = 0
LEARNING_RATE = 0.001
ADAM_BETAS = (0.9, 0.999)
ADAM_EPS = 1e-8
ADAM_WEIGHT_DECAY = 0.0
ADAM_AMSGRAD = False
DISCOUNT = 1.0
ENTROPY_COEFFICIENT = 0.01
GRADIENT_NORM_CEILING = 1.0
ASCENSION_LEVEL = 0
MAX_DECISIONS_PER_EPISODE = 500
VICTORY_WEIGHT = 2.0
MAX_FLOOR = 57
REGISTERED_SUPPORT_BLOCKERS = (
    "unsupported_shop_courier_restock_semantics",
)
TARGET_CATEGORIES = ("card_reward", "event", "route", "shop")
OUTPUT_ROOT_PREFIX = (
    "reports/noncombat_state_conditioned_simulator_learning_experiment_"
)
PUSHED_REMOTE_REF = "origin/master"
DEFAULT_EXPERIMENT_STEM = (
    "noncombat_state_conditioned_simulator_learning_experiment_20260805"
)
DEFAULT_SEED_INVENTORY_PATH = f"reports/{DEFAULT_EXPERIMENT_STEM}_seed_inventory.json"
DEFAULT_REGISTRATION_PATH = f"reports/{DEFAULT_EXPERIMENT_STEM}_registration.json"
DEFAULT_PREFLIGHT_PATH = f"reports/{DEFAULT_EXPERIMENT_STEM}_preflight.json"
DEFAULT_AUTHORIZATION_PATH = f"reports/{DEFAULT_EXPERIMENT_STEM}_authorization.json"
DEFAULT_OUTPUT_DIRECTORY = f"reports/{DEFAULT_EXPERIMENT_STEM}"
EXECUTION_SOURCE_PATH = (
    "analysis_scripts/noncombat_state_conditioned_simulator_learning_experiment.py"
)
PREIMPLEMENTATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-preimplementation-v1"
)
IMPLEMENTATION_VERIFICATION_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-implementation-verification-v1"
)
DEFAULT_PREIMPLEMENTATION_PATH = (
    f"reports/{DEFAULT_EXPERIMENT_STEM}_preimplementation.json"
)
DEFAULT_IMPLEMENTATION_VERIFICATION_PATH = (
    f"reports/{DEFAULT_EXPERIMENT_STEM}_implementation_verification.json"
)
R2_PREFLIGHT_PATH = "reports/noncombat_simulator_rl_experiment_20260804_r2_preflight.json"
R2_VERIFIER_PATH = "analysis_scripts/verify_noncombat_simulator_rl_experiment.py"
DEFAULT_PRODUCTION_CHECKPOINT_ROOT = (
    "D:/SteamLibrary/steamapps/common/SlayTheSpire/checkpoints"
)
PREIMPLEMENTATION_EVIDENCE_NAMES = (
    "baseline_strategy_audit",
    "current_baseline_readiness",
    "formal_readiness",
    "formal_reward",
    "outcome_feasibility",
    "r2_manifest",
    "r2_metrics",
    "r2_postmortem",
    "r2_source",
    "state_action_teacher_result",
    "state_conditioned_input_source",
    "state_conditioned_input_tests",
    "state_conditioned_ranker_source",
    "state_conditioned_ranker_tests",
)
PLANNED_SUCCESSOR_SOURCE_FILES = (
    "analysis_scripts/noncombat_state_conditioned_simulator_learning_experiment.py",
    "analysis_scripts/verify_noncombat_state_conditioned_simulator_learning_experiment.py",
    "tests/test_noncombat_state_conditioned_simulator_learning_experiment.py",
)
IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_formal_reward_contract.py",
    "analysis_scripts/noncombat_policy_diagnostics.py",
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_rl_experiment.py",
    "analysis_scripts/noncombat_state_conditioned_policy_input.py",
    "analysis_scripts/noncombat_state_conditioned_ranker.py",
    "analysis_scripts/noncombat_state_conditioned_simulator_learning_experiment.py",
    "analysis_scripts/verify_noncombat_state_conditioned_simulator_learning_experiment.py",
)
ADAPTER_SOURCE_FILES = (
    "analysis_scripts/noncombat_simulator_adapter.py",
    "simulator_adapters/sts_lightspeed/noncombat_adapter.cpp",
)

REFERENCE_POLICY_NAMES = (
    "bottled",
    "current",
    "live_policy",
    "ope",
    "simple_agent",
    "simpleagent",
    "teacher",
)
SUCCESSOR_POLICY_EXCLUDED_FIELDS = frozenset({"follow_up_control"})

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
    "promotion_authorized",
    "production_checkpoint_mutation_authorized",
    "qualification_authorized",
    "seed_access_authorized",
    "target_supported_outcome_authorized",
    "training_authorized",
)
DOWNSTREAM_AUTHORITY_NAMES = (
    "causal_claim_authorized",
    "communication_mod_authorized",
    "formal_rl_authorized",
    "gameplay_authorized",
    "live_execution_authorized",
    "ope_authorized",
    "policy_loading_authorized",
    "promotion_authorized",
    "production_checkpoint_mutation_authorized",
    "qualification_authorized",
    "target_supported_outcome_authorized",
)

_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_EXECUTION_ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")


class ExperimentBlocked(RuntimeError):
    """Raised when a registered experiment boundary fails closed."""


def canonical_json_bytes(value: Any) -> bytes:
    """Encode one JSON-compatible value with deterministic canonical bytes."""
    _validate_json_value(value, "value")
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _validate_json_value(value: Any, label: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ExperimentBlocked(f"{label} keys must be strings")
            _validate_json_value(child, f"{label}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_json_value(child, f"{label}[{index}]")
        return
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, Real):
        try:
            finite = math.isfinite(float(value))
        except (OverflowError, ValueError):
            finite = False
        if not finite:
            raise ExperimentBlocked(f"{label} numeric values must be finite")
        return
    raise ExperimentBlocked(f"{label} contains unsupported {type(value).__name__}")


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExperimentBlocked(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ExperimentBlocked(f"{label} must be a sequence")
    return value


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ExperimentBlocked(
            f"{label} fields mismatch: missing={missing}, extra={extra}"
        )


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise ExperimentBlocked(f"{label} must be a nonnegative integer")
    return int(value)


def _positive_int(value: object, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise ExperimentBlocked(f"{label} must be positive")
    return result


def _positive_float(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ExperimentBlocked(f"{label} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ExperimentBlocked(f"{label} must be a positive finite number")
    return result


def _canonical_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ExperimentBlocked(f"{label} must be a canonical relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ExperimentBlocked(f"{label} must be a canonical relative path")
    return value


def _canonical_windows_path(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[A-Za-z]:/[A-Za-z0-9_. /-]+", value)
        or ".." in PurePosixPath(value[2:]).parts
    ):
        raise ExperimentBlocked(f"{label} must be a canonical absolute Windows path")
    return value


def _validate_binding(value: object, label: str) -> dict[str, Any]:
    binding = dict(_mapping(value, label))
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    binding["path"] = _canonical_relative_path(binding["path"], f"{label}.path")
    binding["sha256"] = _validate_sha256(binding["sha256"], f"{label}.sha256")
    binding["size_bytes"] = _positive_int(
        binding["size_bytes"], f"{label}.size_bytes"
    )
    return binding


def _validate_external_binding(value: object, label: str) -> dict[str, Any]:
    binding = dict(_mapping(value, label))
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    binding["path"] = _canonical_windows_path(binding["path"], f"{label}.path")
    binding["sha256"] = _validate_sha256(binding["sha256"], f"{label}.sha256")
    binding["size_bytes"] = _positive_int(
        binding["size_bytes"], f"{label}.size_bytes"
    )
    return binding


def registration_authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def execution_authority() -> dict[str, bool]:
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


def experiment_contract() -> dict[str, Any]:
    """Return the fixed source-level learning contract without importing Torch."""
    return {
        "algorithm": {
            "algorithm_version": ALGORITHM_VERSION,
            "discount": DISCOUNT,
            "entropy_coefficient": ENTROPY_COEFFICIENT,
            "gradient_norm_ceiling": GRADIENT_NORM_CEILING,
            "learning_rate": LEARNING_RATE,
            "normalized_returns": True,
            "optimizer": "adam",
            "optimizer_amsgrad": ADAM_AMSGRAD,
            "optimizer_betas": list(ADAM_BETAS),
            "optimizer_eps": ADAM_EPS,
            "optimizer_weight_decay": ADAM_WEIGHT_DECAY,
        },
        "control": {
            "frozen_seeded_initialization": True,
            "model_seed": MODEL_SEED,
            "paired_same_seed_evaluation": True,
            "policy_quality_baseline": False,
        },
        "environment": {
            "ascension": ASCENSION_LEVEL,
            "character": "IRONCLAD",
            "max_decisions_per_episode": MAX_DECISIONS_PER_EPISODE,
            "registered_support_blockers": list(REGISTERED_SUPPORT_BLOCKERS),
        },
        "input": {
            "api_version": 3,
            "candidate_order_preserved": True,
            "excluded_runtime_control_fields": sorted(
                SUCCESSOR_POLICY_EXCLUDED_FIELDS
            ),
            "feature_version": FEATURE_VERSION,
            "hash_dim": HASH_DIM,
            "leakage_excluded": True,
        },
        "lifecycle": {
            "one_logical_attempt": True,
            "pushed_remote_ref": PUSHED_REMOTE_REF,
            "same_identity_checkpoint_resume_authorized": True,
            "source_only_controls_before_start": True,
            "terminal_artifact_reads_after_process_exit_only": True,
        },
        "model": {
            "architecture_id": ARCHITECTURE_ID,
            "candidate_input_dim": HASH_DIM,
            "channel_composition": "separate_state_and_candidate",
            "device": "cpu",
            "dtype": "float32",
            "hidden_dim": HIDDEN_DIM,
            "state_conditioned": True,
            "state_input_dim": HASH_DIM,
        },
        "reward": {
            "floor_progress_maximum": 1.0,
            "reward_version": REWARD_VERSION,
            "victory_primary": True,
            "victory_weight": VICTORY_WEIGHT,
        },
    }


def default_behavior_gate_contract() -> dict[str, Any]:
    """Return source defaults that must later be frozen in registration."""
    return {
        "category_coverage": list(TARGET_CATEGORIES),
        "multi_kind": {
            "categories": ["card_reward", "shop"],
            "maximum_selected_kind_rate": 0.95,
            "minimum_multi_kind_decisions": 2,
            "minimum_selected_kinds": 2,
        },
        "state_effect": {
            "minimum_absolute_relative_score_change": 1e-8,
            "minimum_multi_candidate_decisions": 4,
            "minimum_nonzero_effect_rate": 0.25,
            "minimum_relative_order_change_decisions": 1,
        },
    }


def _torch_components():
    import torch

    from analysis_scripts.noncombat_state_conditioned_ranker import (
        StateConditionedCandidateRanker,
    )

    return torch, StateConditionedCandidateRanker


@dataclass
class TrainingRuntime:
    """Mutable state for one bounded logical training execution."""

    model: Any
    optimizer: Any
    action_generator: Any
    python_random: random.Random
    initial_model_state: dict[str, Any]
    entropy_coefficient: float = ENTROPY_COEFFICIENT
    gradient_norm_ceiling: float = GRADIENT_NORM_CEILING
    next_chunk_index: int = 0
    completed_episodes: int = 0
    optimizer_updates: int = 0
    cumulative_wall_seconds: float = 0.0


@dataclass(frozen=True)
class EpisodeRollout:
    summary: dict[str, Any]
    log_probabilities: tuple[Any, ...]
    entropies: tuple[Any, ...]
    rewards: tuple[float, ...]
    diagnostic_rows: tuple[dict[str, Any], ...]


def initialize_training_runtime() -> TrainingRuntime:
    """Construct the deterministic CPU model, optimizer, and generators."""
    torch, ranker_type = _torch_components()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    previous_state = torch.get_rng_state()
    try:
        torch.manual_seed(MODEL_SEED)
        model = ranker_type(input_dim=HASH_DIM, hidden_dim=HIDDEN_DIM)
    finally:
        torch.set_rng_state(previous_state)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
        betas=ADAM_BETAS,
        eps=ADAM_EPS,
        weight_decay=ADAM_WEIGHT_DECAY,
        amsgrad=ADAM_AMSGRAD,
    )
    action_generator = torch.Generator(device="cpu")
    action_generator.manual_seed(MODEL_SEED)
    runtime = TrainingRuntime(
        model=model,
        optimizer=optimizer,
        action_generator=action_generator,
        python_random=random.Random(MODEL_SEED),
        initial_model_state=copy.deepcopy(model.state_dict()),
    )
    _validate_runtime(runtime)
    return runtime


def _finite_tensor(value: Any, label: str) -> None:
    torch, _ = _torch_components()
    if not torch.is_tensor(value) or not torch.isfinite(value).all().item():
        raise ExperimentBlocked(f"{label} must be a finite tensor")
    if value.device.type != "cpu":
        raise ExperimentBlocked(f"{label} must remain on CPU")


def _finite_tree(value: Any, label: str) -> None:
    torch, _ = _torch_components()
    if torch.is_tensor(value):
        _finite_tensor(value, label)
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            _finite_tree(child, f"{label}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _finite_tree(child, f"{label}[{index}]")
        return
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, Real) and not math.isfinite(float(value)):
        raise ExperimentBlocked(f"{label} must be finite")


def _validate_runtime(runtime: TrainingRuntime) -> None:
    torch, ranker_type = _torch_components()
    if not isinstance(runtime.model, ranker_type):
        raise ExperimentBlocked("runtime model type mismatch")
    metadata = runtime.model.architecture_metadata()
    expected_model = dict(experiment_contract()["model"])
    expected_model.pop("channel_composition")
    if metadata != expected_model:
        raise ExperimentBlocked("runtime model metadata mismatch")
    if runtime.model.training is not True:
        raise ExperimentBlocked("training runtime model must remain in training mode")
    for name, parameter in runtime.model.named_parameters():
        _finite_tensor(parameter, f"model parameter {name}")
        if parameter.grad is not None:
            raise ExperimentBlocked("durable runtime gradients must be cleared")
    if not isinstance(runtime.optimizer, torch.optim.Adam):
        raise ExperimentBlocked("runtime optimizer must remain Adam")
    if len(runtime.optimizer.param_groups) != 1:
        raise ExperimentBlocked("runtime optimizer must have one parameter group")
    optimizer_group = runtime.optimizer.param_groups[0]
    expected_optimizer = {
        "amsgrad": ADAM_AMSGRAD,
        "betas": ADAM_BETAS,
        "eps": ADAM_EPS,
        "lr": LEARNING_RATE,
        "weight_decay": ADAM_WEIGHT_DECAY,
    }
    for name, expected in expected_optimizer.items():
        if optimizer_group.get(name) != expected:
            raise ExperimentBlocked(f"runtime optimizer {name} mismatch")
    _finite_tree(runtime.optimizer.state_dict(), "optimizer state")
    if str(runtime.action_generator.device) != "cpu":
        raise ExperimentBlocked("action generator must remain on CPU")
    if runtime.entropy_coefficient != ENTROPY_COEFFICIENT:
        raise ExperimentBlocked("runtime entropy coefficient mismatch")
    if runtime.gradient_norm_ceiling != GRADIENT_NORM_CEILING:
        raise ExperimentBlocked("runtime gradient ceiling mismatch")
    for label in ("next_chunk_index", "completed_episodes", "optimizer_updates"):
        _nonnegative_int(getattr(runtime, label), f"runtime {label}")
    if runtime.next_chunk_index != runtime.optimizer_updates:
        raise ExperimentBlocked("runtime chunk and optimizer coordinates differ")
    if not math.isfinite(runtime.cumulative_wall_seconds) or runtime.cumulative_wall_seconds < 0:
        raise ExperimentBlocked("runtime cumulative wall time is invalid")


def _encode_tensor(value: Any) -> dict[str, Any]:
    torch, _ = _torch_components()
    if not torch.is_tensor(value):
        raise ExperimentBlocked("tensor encoding requires a tensor")
    tensor = value.detach().cpu().contiguous()
    if tensor.is_floating_point() and not torch.isfinite(tensor).all().item():
        raise ExperimentBlocked("encoded tensor must be finite")
    raw = tensor.numpy().tobytes(order="C")
    return {
        "byte_order": "little",
        "data_base64": base64.b64encode(raw).decode("ascii"),
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "dtype": str(tensor.dtype).removeprefix("torch."),
        "shape": list(tensor.shape),
    }


_TORCH_DTYPE_SIZES = {
    "bool": 1,
    "float32": 4,
    "float64": 8,
    "int32": 4,
    "int64": 8,
    "uint8": 1,
}


def decode_tensor(value: object, label: str) -> Any:
    torch, _ = _torch_components()
    payload = dict(_mapping(value, label))
    _require_keys(
        payload,
        {"byte_order", "data_base64", "data_sha256", "dtype", "shape"},
        label,
    )
    if payload["byte_order"] != "little":
        raise ExperimentBlocked(f"{label} byte order must be little")
    dtype_name = payload["dtype"]
    if dtype_name not in _TORCH_DTYPE_SIZES:
        raise ExperimentBlocked(f"{label} dtype is unsupported")
    shape = payload["shape"]
    if not isinstance(shape, list) or any(
        isinstance(item, bool) or not isinstance(item, int) or item < 0
        for item in shape
    ):
        raise ExperimentBlocked(f"{label} shape is invalid")
    try:
        raw = base64.b64decode(payload["data_base64"], validate=True)
    except (TypeError, ValueError) as exc:
        raise ExperimentBlocked(f"{label} data is invalid base64") from exc
    digest = payload["data_sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise ExperimentBlocked(f"{label} sha256 is invalid")
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ExperimentBlocked(f"{label} sha256 mismatch")
    elements = math.prod(shape) if shape else 1
    if len(raw) != elements * _TORCH_DTYPE_SIZES[dtype_name]:
        raise ExperimentBlocked(f"{label} byte length mismatch")
    try:
        tensor = torch.frombuffer(
            bytearray(raw), dtype=getattr(torch, dtype_name)
        ).clone().reshape(shape)
    except (RuntimeError, ValueError) as exc:
        raise ExperimentBlocked(f"{label} tensor decode failed: {exc}") from exc
    if tensor.is_floating_point():
        _finite_tensor(tensor, label)
    return tensor


def _encode_state_value(value: Any) -> dict[str, Any]:
    torch, _ = _torch_components()
    if torch.is_tensor(value):
        return {"kind": "tensor", "value": _encode_tensor(value)}
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ExperimentBlocked("checkpoint mapping keys must be strings")
        return {
            "items": [
                {"key": key, "value": _encode_state_value(value[key])}
                for key in sorted(value)
            ],
            "kind": "mapping",
        }
    if isinstance(value, tuple):
        return {
            "items": [_encode_state_value(child) for child in value],
            "kind": "tuple",
        }
    if isinstance(value, list):
        return {
            "items": [_encode_state_value(child) for child in value],
            "kind": "list",
        }
    if value is None or isinstance(value, (bool, int, str)):
        _validate_json_value(value, "optimizer state")
        return {"kind": "scalar", "value": value}
    if isinstance(value, Real):
        number = float(value)
        if not math.isfinite(number):
            raise ExperimentBlocked("checkpoint scalar must be finite")
        return {"kind": "scalar", "value": number}
    raise ExperimentBlocked(
        f"checkpoint state contains unsupported {type(value).__name__}"
    )


def _decode_state_value(value: object, label: str) -> Any:
    payload = dict(_mapping(value, label))
    kind = payload.get("kind")
    if kind == "tensor":
        _require_keys(payload, {"kind", "value"}, label)
        return decode_tensor(payload["value"], f"{label}.value")
    if kind == "mapping":
        _require_keys(payload, {"items", "kind"}, label)
        items = payload["items"]
        if not isinstance(items, list):
            raise ExperimentBlocked(f"{label}.items must be a list")
        result: dict[str, Any] = {}
        previous: str | None = None
        for index, raw in enumerate(items):
            item = dict(_mapping(raw, f"{label}.items[{index}]"))
            _require_keys(item, {"key", "value"}, f"{label}.items[{index}]")
            key = item["key"]
            if (
                not isinstance(key, str)
                or not key
                or (previous is not None and key <= previous)
            ):
                raise ExperimentBlocked(f"{label} mapping keys are not canonical")
            previous = key
            result[key] = _decode_state_value(item["value"], f"{label}.{key}")
        return result
    if kind in {"tuple", "list"}:
        _require_keys(payload, {"items", "kind"}, label)
        if not isinstance(payload["items"], list):
            raise ExperimentBlocked(f"{label}.items must be a list")
        items = [
            _decode_state_value(item, f"{label}[{index}]")
            for index, item in enumerate(payload["items"])
        ]
        return tuple(items) if kind == "tuple" else items
    if kind == "scalar":
        _require_keys(payload, {"kind", "value"}, label)
        scalar = payload["value"]
        _validate_json_value(scalar, label)
        if isinstance(scalar, (Mapping, list, tuple)):
            raise ExperimentBlocked(f"{label} scalar is not scalar")
        return scalar
    raise ExperimentBlocked(f"{label} kind is unsupported")


def encode_optimizer_state(optimizer: Any) -> dict[str, Any]:
    """Return a deterministic JSON representation used by rollback evidence."""
    state = optimizer.state_dict()
    rows = []
    for parameter_id in sorted(state["state"]):
        if isinstance(parameter_id, bool) or not isinstance(parameter_id, int):
            raise ExperimentBlocked("optimizer parameter id must be an integer")
        rows.append(
            {
                "parameter_id": parameter_id,
                "state": _encode_state_value(state["state"][parameter_id]),
            }
        )
    return {
        "param_groups": _encode_state_value(state["param_groups"]),
        "state": rows,
    }


def decode_optimizer_state(value: object) -> dict[str, Any]:
    payload = dict(_mapping(value, "optimizer"))
    _require_keys(payload, {"param_groups", "state"}, "optimizer")
    state_rows = payload["state"]
    if not isinstance(state_rows, list):
        raise ExperimentBlocked("optimizer state must be a list")
    state: dict[int, Any] = {}
    previous = -1
    for index, raw in enumerate(state_rows):
        row = dict(_mapping(raw, f"optimizer state[{index}]"))
        _require_keys(row, {"parameter_id", "state"}, f"optimizer state[{index}]")
        parameter_id = row["parameter_id"]
        if (
            isinstance(parameter_id, bool)
            or not isinstance(parameter_id, int)
            or parameter_id <= previous
        ):
            raise ExperimentBlocked("optimizer parameter ids are not canonical")
        previous = parameter_id
        state[parameter_id] = _decode_state_value(
            row["state"], f"optimizer state[{parameter_id}]"
        )
    param_groups = _decode_state_value(payload["param_groups"], "optimizer param_groups")
    if not isinstance(param_groups, list):
        raise ExperimentBlocked("optimizer param_groups must decode to a list")
    return {"param_groups": param_groups, "state": state}


def _model_state_bytes(model: Any) -> bytes:
    return canonical_json_bytes(
        {
            name: _encode_tensor(tensor)
            for name, tensor in sorted(model.state_dict().items())
        }
    )


def _relative_state_effect(
    *,
    decision_id: str,
    category: str,
    actual_scores: Any,
    zero_state_scores: Any,
) -> dict[str, Any]:
    torch, _ = _torch_components()
    _finite_tensor(actual_scores, "actual scores")
    _finite_tensor(zero_state_scores, "zero-state scores")
    if actual_scores.shape != zero_state_scores.shape or actual_scores.ndim != 1:
        raise ExperimentBlocked("state-effect score shapes mismatch")
    if actual_scores.shape[0] < 2:
        return {
            "decision_id": decision_id,
            "category": category,
            "max_abs_relative_score_change": 0.0,
            "relative_order_changed": False,
            "zero_state_scores": [
                float(value) for value in zero_state_scores.detach().tolist()
            ],
        }
    actual_relative = actual_scores - actual_scores[0]
    zero_relative = zero_state_scores - zero_state_scores[0]
    difference = actual_relative - zero_relative
    maximum = float(torch.max(torch.abs(difference)).detach().item())
    actual_order = tuple(
        sorted(
            range(actual_scores.shape[0]),
            key=lambda index: (-float(actual_scores[index].detach().item()), index),
        )
    )
    zero_order = tuple(
        sorted(
            range(zero_state_scores.shape[0]),
            key=lambda index: (-float(zero_state_scores[index].detach().item()), index),
        )
    )
    return {
        "category": category,
        "decision_id": decision_id,
        "max_abs_relative_score_change": 0.0 if maximum == 0.0 else maximum,
        "relative_order_changed": actual_order != zero_order,
        "zero_state_scores": [
            float(value) for value in zero_state_scores.detach().tolist()
        ],
    }


def _strip_successor_runtime_control(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _strip_successor_runtime_control(child)
            for key, child in value.items()
            if str(key).casefold() not in SUCCESSOR_POLICY_EXCLUDED_FIELDS
        }
    if isinstance(value, (list, tuple)):
        return [_strip_successor_runtime_control(child) for child in value]
    return copy.deepcopy(value)


def _successor_policy_inputs(
    snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    policy_snapshot = copy.deepcopy(dict(snapshot))
    if "state" in policy_snapshot:
        policy_snapshot["state"] = _strip_successor_runtime_control(
            policy_snapshot["state"]
        )
    policy_candidates = _strip_successor_runtime_control(list(candidates))
    return policy_snapshot, policy_candidates


def _project_and_score(model: Any, snapshot: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]):
    torch, _ = _torch_components()
    from analysis_scripts.noncombat_state_conditioned_policy_input import (
        project_state_conditioned_policy_input,
    )

    try:
        policy_snapshot, policy_candidates = _successor_policy_inputs(
            snapshot, candidates
        )
        policy_input = project_state_conditioned_policy_input(
            policy_snapshot, policy_candidates
        )
        scores = model(policy_input.state_features, policy_input.candidate_features)
        zero_scores = model(
            torch.zeros_like(policy_input.state_features),
            policy_input.candidate_features,
        )
    except Exception as exc:
        if isinstance(exc, ExperimentBlocked):
            raise
        raise ExperimentBlocked(str(exc)) from exc
    _finite_tensor(scores, "policy scores")
    _finite_tensor(zero_scores, "zero-state policy scores")
    return policy_input, scores, zero_scores, policy_snapshot, policy_candidates


def score_decision(
    model: Any,
    *,
    decision_id: str,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Greedily score one decision and emit its state-effect diagnostic."""
    from analysis_scripts.noncombat_state_conditioned_policy_input import (
        build_policy_diagnostic_row,
    )

    was_training = bool(model.training)
    model.eval()
    try:
        _, scores, zero_scores, policy_snapshot, policy_candidates = (
            _project_and_score(model, snapshot, candidates)
        )
        selected_index = int(scores.detach().argmax().item())
        row = build_policy_diagnostic_row(
            decision_id=decision_id,
            snapshot=policy_snapshot,
            candidates=policy_candidates,
            scores=scores.detach(),
            selected_index=selected_index,
        )
        state_effect = _relative_state_effect(
            decision_id=decision_id,
            category=str(snapshot["category"]),
            actual_scores=scores.detach(),
            zero_state_scores=zero_scores.detach(),
        )
    finally:
        model.train(was_training)
    return {
        "diagnostic_row": row,
        "scores": scores.detach().clone(),
        "state_effect": state_effect,
    }


def _exact_snapshot(value: object, label: str) -> dict[str, Any]:
    from analysis_scripts.noncombat_simulator_adapter import (
        ADAPTER_API_VERSION,
        SimulatorAdapterError,
        validate_snapshot,
    )

    try:
        snapshot = validate_snapshot(copy.deepcopy(value))
    except SimulatorAdapterError as exc:
        raise ExperimentBlocked(f"{label} invalid: {exc}") from exc
    if snapshot["adapter_api_version"] != ADAPTER_API_VERSION:
        raise ExperimentBlocked(f"{label} must use exact API v3")
    return snapshot


def _validated_candidates(value: object, category: str) -> list[dict[str, Any]]:
    from analysis_scripts.noncombat_simulator_adapter import (
        SimulatorAdapterError,
        validate_candidates,
    )

    try:
        return validate_candidates(copy.deepcopy(list(_sequence(value, "candidates"))), category=category)
    except SimulatorAdapterError as exc:
        raise ExperimentBlocked(str(exc)) from exc


def _formal_reward(transition: Mapping[str, Any]) -> float:
    from analysis_scripts.noncombat_simulator_rl_experiment import (
        simulator_experiment_reward,
    )

    try:
        result = float(simulator_experiment_reward(transition))
    except Exception as exc:
        raise ExperimentBlocked(str(exc)) from exc
    if not math.isfinite(result):
        raise ExperimentBlocked("training reward must be finite")
    return result


def _check_deadline(deadline: float, clock: Callable[[], float]) -> None:
    now = float(clock())
    if not math.isfinite(now) or now > deadline:
        raise ExperimentBlocked("wall-time bound exceeded")


def _returns_to_go(rewards: Sequence[float]) -> tuple[float, ...]:
    running = 0.0
    result = [0.0] * len(rewards)
    for index in range(len(rewards) - 1, -1, -1):
        reward = float(rewards[index])
        if not math.isfinite(reward):
            raise ExperimentBlocked("training reward must be finite")
        running = reward + DISCOUNT * running
        result[index] = running
    return tuple(result)


def rollout_episode(
    model: Any,
    *,
    environment_factory: Callable[[int], Any],
    seed: int,
    training: bool,
    action_generator: Any | None,
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
) -> EpisodeRollout:
    """Run one exact API v3 episode without mutating an unselected source branch."""
    torch, _ = _torch_components()
    from analysis_scripts.noncombat_state_conditioned_policy_input import (
        build_policy_diagnostic_row,
    )

    _check_deadline(deadline, clock)
    try:
        environment = environment_factory(seed)
    except Exception as exc:
        raise ExperimentBlocked(f"seed {seed} environment construction failed: {exc}") from exc
    categories: set[str] = set()
    action_ids: list[str] = []
    rewards: list[float] = []
    log_probabilities: list[Any] = []
    entropies: list[Any] = []
    diagnostic_rows: list[dict[str, Any]] = []
    unsupported_reason: str | None = None
    terminal_snapshot: dict[str, Any] | None = None
    last_supported_floor = 0.0

    while True:
        _check_deadline(deadline, clock)
        snapshot = _exact_snapshot(environment.snapshot(), "environment snapshot")
        if snapshot["terminal"] is True:
            terminal_snapshot = snapshot
            break
        if len(action_ids) >= MAX_DECISIONS_PER_EPISODE:
            raise ExperimentBlocked("episode exceeded decision bound")
        category = str(snapshot["category"])
        if category not in TARGET_CATEGORIES:
            raise ExperimentBlocked("episode stopped outside a target category")
        categories.add(category)
        source_floor = snapshot["state"].get("floor")
        if (
            isinstance(source_floor, bool)
            or not isinstance(source_floor, Real)
            or not math.isfinite(float(source_floor))
        ):
            raise ExperimentBlocked("source floor must be finite")
        last_supported_floor = float(source_floor)
        raw_candidates = environment.legal_actions()
        candidates = _validated_candidates(raw_candidates, category)
        snapshot_bytes = canonical_json_bytes(snapshot)
        candidates_bytes = canonical_json_bytes(candidates)
        try:
            branch = environment.clone()
            branch_snapshot = _exact_snapshot(branch.snapshot(), "cloned snapshot")
            branch_candidates = _validated_candidates(branch.legal_actions(), category)
        except Exception as exc:
            raise ExperimentBlocked(f"seed {seed} clone validation failed: {exc}") from exc
        if canonical_json_bytes(branch_snapshot) != snapshot_bytes:
            raise ExperimentBlocked("clone snapshot differs before action")
        if canonical_json_bytes(branch_candidates) != candidates_bytes:
            raise ExperimentBlocked("clone candidate set differs before action")

        _, scores, zero_scores, policy_snapshot, policy_candidates = (
            _project_and_score(model, snapshot, candidates)
        )
        probabilities = torch.softmax(scores, dim=0)
        log_probabilities_all = torch.log_softmax(scores, dim=0)
        entropy = -(probabilities * log_probabilities_all).sum()
        _finite_tensor(entropy, "policy entropy")
        if training:
            if action_generator is None:
                raise ExperimentBlocked("training action generator is required")
            selected_index = int(
                torch.multinomial(
                    probabilities.detach(), 1, generator=action_generator
                ).item()
            )
            selected_log_probability = log_probabilities_all[selected_index]
            _finite_tensor(selected_log_probability, "selected log probability")
            log_probabilities.append(selected_log_probability)
            entropies.append(entropy)
        else:
            selected_index = int(scores.detach().argmax().item())
        action_id = str(candidates[selected_index]["action_id"])
        decision_id = f"seed-{seed}:decision-{len(action_ids)}"
        diagnostic_row = build_policy_diagnostic_row(
            decision_id=decision_id,
            snapshot=policy_snapshot,
            candidates=policy_candidates,
            scores=scores.detach(),
            selected_index=selected_index,
        )
        state_effect = _relative_state_effect(
            decision_id=decision_id,
            category=category,
            actual_scores=scores.detach(),
            zero_state_scores=zero_scores.detach(),
        )
        diagnostic_rows.append({**diagnostic_row, "state_effect": state_effect})
        action_ids.append(action_id)
        try:
            transition = branch.step(action_id)
        except RuntimeError as exc:
            reason = str(exc)
            if reason not in REGISTERED_SUPPORT_BLOCKERS:
                raise ExperimentBlocked(
                    f"seed {seed} reached unregistered blocker: {reason}"
                ) from exc
            unsupported_reason = reason
            rewards.append(0.0)
            if canonical_json_bytes(_exact_snapshot(environment.snapshot(), "source snapshot")) != snapshot_bytes:
                raise ExperimentBlocked("selected clone action mutated the source branch")
            break
        except Exception as exc:
            raise ExperimentBlocked(
                f"seed {seed} rejected candidate {action_id}: {exc}"
            ) from exc
        if canonical_json_bytes(_exact_snapshot(environment.snapshot(), "source snapshot")) != snapshot_bytes:
            raise ExperimentBlocked("selected clone action mutated the source branch")
        rewards.append(_formal_reward(_mapping(transition, "transition")))
        environment = branch

    if not action_ids:
        raise ExperimentBlocked(f"seed {seed} produced no policy decisions")
    if unsupported_reason is None:
        if terminal_snapshot is None:
            raise ExperimentBlocked("terminal snapshot missing")
        state = _mapping(terminal_snapshot["state"], "terminal state")
        outcome = state.get("outcome")
        if outcome not in {"player_loss", "player_victory"}:
            raise ExperimentBlocked("episode terminal outcome is invalid")
        terminal_floor = float(state.get("floor"))
        if not math.isfinite(terminal_floor):
            raise ExperimentBlocked("episode terminal floor must be finite")
        last_supported_floor = terminal_floor
    else:
        outcome = None
        terminal_floor = None
    summary = {
        "action_sequence_sha256": hashlib.sha256(
            canonical_json_bytes(action_ids)
        ).hexdigest(),
        "candidate_legality": True,
        "categories": sorted(categories),
        "decisions": len(action_ids),
        "last_supported_floor": last_supported_floor,
        "outcome": outcome,
        "retained": True,
        "seed": int(seed),
        "selected_action_ids": action_ids,
        "terminal_floor": terminal_floor,
        "total_reward": sum(rewards),
        "unsupported_reason": unsupported_reason,
        "victory": outcome == "player_victory",
    }
    return EpisodeRollout(
        summary=summary,
        log_probabilities=tuple(log_probabilities),
        entropies=tuple(entropies),
        rewards=tuple(rewards),
        diagnostic_rows=tuple(diagnostic_rows),
    )


def _runtime_snapshot(runtime: TrainingRuntime) -> dict[str, Any]:
    return {
        "action_generator": runtime.action_generator.get_state().clone(),
        "completed_episodes": runtime.completed_episodes,
        "cumulative_wall_seconds": runtime.cumulative_wall_seconds,
        "model": copy.deepcopy(runtime.model.state_dict()),
        "next_chunk_index": runtime.next_chunk_index,
        "optimizer": copy.deepcopy(runtime.optimizer.state_dict()),
        "optimizer_updates": runtime.optimizer_updates,
        "python_random": runtime.python_random.getstate(),
    }


def _restore_runtime(runtime: TrainingRuntime, snapshot: Mapping[str, Any]) -> None:
    runtime.model.load_state_dict(snapshot["model"])
    runtime.optimizer.load_state_dict(snapshot["optimizer"])
    runtime.optimizer.zero_grad(set_to_none=True)
    runtime.model.train()
    runtime.action_generator.set_state(snapshot["action_generator"])
    runtime.python_random.setstate(snapshot["python_random"])
    runtime.next_chunk_index = int(snapshot["next_chunk_index"])
    runtime.completed_episodes = int(snapshot["completed_episodes"])
    runtime.optimizer_updates = int(snapshot["optimizer_updates"])
    runtime.cumulative_wall_seconds = float(snapshot["cumulative_wall_seconds"])


def _gradient_norm(model: Any) -> float:
    total = 0.0
    for parameter in model.parameters():
        if parameter.grad is None:
            raise ExperimentBlocked("model parameter gradient is missing")
        _finite_tensor(parameter.grad, "model gradient")
        total += float(parameter.grad.detach().pow(2).sum().item())
    result = math.sqrt(total)
    if not math.isfinite(result):
        raise ExperimentBlocked("gradient norm must be finite")
    return result


def run_training_chunk(
    runtime: TrainingRuntime,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    chunk_index: int,
    max_wall_seconds: float,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Apply exactly one atomic normalized-return REINFORCE update."""
    _validate_runtime(runtime)
    if chunk_index != runtime.next_chunk_index:
        raise ExperimentBlocked("chunk_index is not the unique next chunk")
    seed_values = tuple(_nonnegative_int(seed, "training seed") for seed in _sequence(seeds, "seeds"))
    if not seed_values or len(set(seed_values)) != len(seed_values):
        raise ExperimentBlocked("training seeds must be nonempty and unique")
    wall_limit = _positive_float(max_wall_seconds, "max_wall_seconds")
    remaining = wall_limit - runtime.cumulative_wall_seconds
    if remaining <= 0.0:
        raise ExperimentBlocked("wall-time bound exceeded")
    started = float(clock())
    if not math.isfinite(started):
        raise ExperimentBlocked("wall clock must be finite")
    deadline = started + remaining
    rollback = _runtime_snapshot(runtime)
    torch, _ = _torch_components()

    try:
        runtime.model.train()
        runtime.optimizer.zero_grad(set_to_none=True)
        episode_rows: list[dict[str, Any]] = []
        diagnostic_rows: list[dict[str, Any]] = []
        log_probabilities: list[Any] = []
        entropies: list[Any] = []
        returns: list[float] = []
        for seed in seed_values:
            rollout = rollout_episode(
                runtime.model,
                environment_factory=environment_factory,
                seed=seed,
                training=True,
                action_generator=runtime.action_generator,
                deadline=deadline,
                clock=clock,
            )
            episode_rows.append({**rollout.summary, "chunk_index": chunk_index})
            for raw_diagnostic in rollout.diagnostic_rows:
                diagnostic = copy.deepcopy(raw_diagnostic)
                scoped_id = f"chunk-{chunk_index}:{diagnostic['decision_id']}"
                diagnostic["decision_id"] = scoped_id
                diagnostic["state_effect"]["decision_id"] = scoped_id
                diagnostic_rows.append(diagnostic)
            log_probabilities.extend(rollout.log_probabilities)
            entropies.extend(rollout.entropies)
            returns.extend(_returns_to_go(rollout.rewards))
        if not log_probabilities or len(log_probabilities) != len(returns):
            raise ExperimentBlocked("training decisions and returns are not aligned")
        if len(entropies) != len(log_probabilities):
            raise ExperimentBlocked("training entropy rows are not aligned")
        return_tensor = torch.tensor(returns, dtype=torch.float32, device="cpu")
        _finite_tensor(return_tensor, "returns")
        standard_deviation = return_tensor.std(unbiased=False)
        if float(standard_deviation.item()) > 1e-12:
            normalized_returns = (
                return_tensor - return_tensor.mean()
            ) / (standard_deviation + 1e-8)
        else:
            normalized_returns = torch.zeros_like(return_tensor)
        stacked_log_probabilities = torch.stack(log_probabilities)
        stacked_entropies = torch.stack(entropies)
        policy_loss = -(
            stacked_log_probabilities * normalized_returns.detach()
        ).mean()
        mean_entropy = stacked_entropies.mean()
        loss = policy_loss - runtime.entropy_coefficient * mean_entropy
        _finite_tensor(loss, "training loss")
        loss.backward()
        gradient_before = _gradient_norm(runtime.model)
        torch.nn.utils.clip_grad_norm_(
            runtime.model.parameters(), runtime.gradient_norm_ceiling
        )
        gradient_after = _gradient_norm(runtime.model)
        if gradient_after > runtime.gradient_norm_ceiling + 1e-6:
            raise ExperimentBlocked("gradient norm exceeds registered ceiling")
        _check_deadline(deadline, clock)
        runtime.optimizer.step()
        for name, parameter in runtime.model.named_parameters():
            _finite_tensor(parameter, f"model parameter {name}")
        _finite_tree(runtime.optimizer.state_dict(), "optimizer state")
        runtime.optimizer.zero_grad(set_to_none=True)
        finished = float(clock())
        if not math.isfinite(finished) or finished < started:
            raise ExperimentBlocked("wall clock moved backwards")
        elapsed = finished - started
        if runtime.cumulative_wall_seconds + elapsed > wall_limit:
            raise ExperimentBlocked("wall-time bound exceeded")
        runtime.next_chunk_index += 1
        runtime.completed_episodes += len(seed_values)
        runtime.optimizer_updates += 1
        runtime.cumulative_wall_seconds += elapsed
        _validate_runtime(runtime)
        summary = {
            "categories": sorted(
                {
                    category
                    for row in episode_rows
                    for category in row["categories"]
                }
            ),
            "chunk_index": chunk_index,
            "diagnostic_rows": diagnostic_rows,
            "entropy_coefficient": runtime.entropy_coefficient,
            "episode_rows": episode_rows,
            "episodes": len(episode_rows),
            "gradient_norm_after_clip": gradient_after,
            "gradient_norm_before_clip": gradient_before,
            "loss": float(loss.detach().item()),
            "mean_entropy": float(mean_entropy.detach().item()),
            "mean_episode_return": statistics.fmean(
                float(row["total_reward"]) for row in episode_rows
            ),
            "optimizer_update": runtime.optimizer_updates,
            "unsupported_episodes": sum(
                row["unsupported_reason"] is not None for row in episode_rows
            ),
            "victories": sum(bool(row["victory"]) for row in episode_rows),
        }
    except BaseException:
        _restore_runtime(runtime, rollback)
        raise
    return summary


def _distribution(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "max": None, "mean": None, "median": None, "min": None}
    return {
        "count": len(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "min": min(values),
    }


def summarize_experiment_diagnostics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Combine canonical policy-family and actual-versus-zero-state evidence."""
    from analysis_scripts.noncombat_policy_diagnostics import (
        PolicyDiagnosticError,
        summarize_policy_diagnostics,
    )

    values = list(_sequence(rows, "diagnostic rows"))
    if not values:
        raise ExperimentBlocked("diagnostic rows must be nonempty")
    policy_rows = []
    effects = []
    multi_kind_by_category = {category: 0 for category in TARGET_CATEGORIES}
    multi_kind_selected_by_category: dict[str, dict[str, int]] = {
        category: {} for category in TARGET_CATEGORIES
    }
    for raw in values:
        row = dict(_mapping(raw, "diagnostic row"))
        effect = dict(_mapping(row.pop("state_effect", None), "state_effect"))
        if "zero_state_scores" in effect:
            _require_keys(
                effect,
                {
                    "category",
                    "decision_id",
                    "max_abs_relative_score_change",
                    "relative_order_changed",
                    "zero_state_scores",
                },
                "state_effect",
            )
            zero_scores = list(
                _sequence(effect["zero_state_scores"], "zero-state scores")
            )
            if not zero_scores or any(
                isinstance(score, bool)
                or not isinstance(score, Real)
                or not math.isfinite(float(score))
                for score in zero_scores
            ):
                raise ExperimentBlocked("zero-state scores must be finite")
        elif "decision_id" in effect or "category" in effect:
            _require_keys(
                effect,
                {
                    "category",
                    "decision_id",
                    "max_abs_relative_score_change",
                    "relative_order_changed",
                },
                "state_effect",
            )
        else:
            _require_keys(
                effect,
                {"max_abs_relative_score_change", "relative_order_changed"},
                "state_effect",
            )
        magnitude = effect["max_abs_relative_score_change"]
        if isinstance(magnitude, bool) or not isinstance(magnitude, Real) or not math.isfinite(float(magnitude)) or float(magnitude) < 0.0:
            raise ExperimentBlocked("state-effect magnitude must be finite and nonnegative")
        if type(effect["relative_order_changed"]) is not bool:
            raise ExperimentBlocked("state-effect relative_order_changed must be boolean")
        candidates = list(_sequence(row.get("candidates"), "candidates"))
        category = str(row.get("category"))
        candidate_kinds = {
            str(_mapping(candidate, "candidate").get("action_id")): str(
                _mapping(candidate, "candidate").get("kind")
            )
            for candidate in candidates
        }
        if len(set(candidate_kinds.values())) > 1:
            multi_kind_by_category[category] = multi_kind_by_category.get(category, 0) + 1
            selected_kind = candidate_kinds[str(row.get("selected_action_id"))]
            selected_counts = multi_kind_selected_by_category.setdefault(category, {})
            selected_counts[selected_kind] = selected_counts.get(selected_kind, 0) + 1
        effects.append(
            {
                "category": category,
                "decision_id": str(row.get("decision_id")),
                "magnitude": float(magnitude),
                "multi_candidate": len(candidates) > 1,
                "relative_order_changed": bool(effect["relative_order_changed"]),
            }
        )
        policy_rows.append(row)
    try:
        policy = summarize_policy_diagnostics(policy_rows)
    except PolicyDiagnosticError as exc:
        raise ExperimentBlocked(str(exc)) from exc
    for category, summary in policy["categories"].items():
        summary["distinct_candidate_kinds"] = sorted(
            summary["candidate_kind_occurrences"]
        )
        summary["multi_candidate_decisions"] = (
            summary["decision_count"] - summary["single_candidate_decisions"]
        )
        summary["multi_kind_decisions"] = multi_kind_by_category.get(category, 0)
        multi_kind_count = summary["multi_kind_decisions"]
        summary["multi_kind_selected_kinds"] = {
            kind: {"count": count, "rate": count / multi_kind_count}
            for kind, count in sorted(
                multi_kind_selected_by_category.get(category, {}).items()
            )
        }
        category_multi = [
            row
            for row in effects
            if row["category"] == category and row["multi_candidate"]
        ]
        category_magnitudes = [row["magnitude"] for row in category_multi]
        summary["state_effect"] = {
            "magnitude": _distribution(category_magnitudes),
            "multi_candidate_decisions": len(category_multi),
            "nonzero_effect_decisions": sum(
                value > 0.0 for value in category_magnitudes
            ),
            "relative_order_change_decisions": sum(
                row["relative_order_changed"] for row in category_multi
            ),
        }
    multi = [row for row in effects if row["multi_candidate"]]
    magnitudes = [row["magnitude"] for row in multi]
    state_effect = {
        "magnitude": _distribution(magnitudes),
        "multi_candidate_decisions": len(multi),
        "nonzero_effect_decisions": sum(value > 0.0 for value in magnitudes),
        "relative_order_change_decisions": sum(
            row["relative_order_changed"] for row in multi
        ),
    }
    return {
        "authority": registration_authority(),
        "categories": policy["categories"],
        "decision_count": policy["decision_count"],
        "schema_version": "noncombat-state-conditioned-experiment-diagnostics-v1",
        "state_effect": state_effect,
    }


def _validate_behavior_gate_contract(value: object) -> dict[str, Any]:
    gate = copy.deepcopy(dict(_mapping(value, "behavior gate contract")))
    _require_keys(gate, {"category_coverage", "multi_kind", "state_effect"}, "behavior gate contract")
    if gate["category_coverage"] != list(TARGET_CATEGORIES):
        raise ExperimentBlocked("behavior category coverage mismatch")
    multi = dict(_mapping(gate["multi_kind"], "multi_kind gate"))
    _require_keys(
        multi,
        {
            "categories",
            "maximum_selected_kind_rate",
            "minimum_multi_kind_decisions",
            "minimum_selected_kinds",
        },
        "multi_kind gate",
    )
    if multi["categories"] != ["card_reward", "shop"]:
        raise ExperimentBlocked("multi_kind categories mismatch")
    raw_rate = multi["maximum_selected_kind_rate"]
    if isinstance(raw_rate, bool) or not isinstance(raw_rate, Real):
        raise ExperimentBlocked("maximum selected-kind rate must be a finite number")
    rate = float(raw_rate)
    if not 0.0 < rate < 1.0:
        raise ExperimentBlocked("maximum selected-kind rate must be between zero and one")
    _positive_int(multi["minimum_multi_kind_decisions"], "minimum multi-kind decisions")
    _positive_int(multi["minimum_selected_kinds"], "minimum selected kinds")
    state = dict(_mapping(gate["state_effect"], "state-effect gate"))
    _require_keys(
        state,
        {
            "minimum_absolute_relative_score_change",
            "minimum_multi_candidate_decisions",
            "minimum_nonzero_effect_rate",
            "minimum_relative_order_change_decisions",
        },
        "state-effect gate",
    )
    _positive_float(
        state["minimum_absolute_relative_score_change"],
        "minimum absolute relative-score change",
    )
    _positive_int(
        state["minimum_multi_candidate_decisions"],
        "minimum multi-candidate decisions",
    )
    _positive_int(
        state["minimum_relative_order_change_decisions"],
        "minimum relative-order-change decisions",
    )
    raw_effect_rate = state["minimum_nonzero_effect_rate"]
    if isinstance(raw_effect_rate, bool) or not isinstance(raw_effect_rate, Real):
        raise ExperimentBlocked("minimum nonzero-effect rate must be a finite number")
    effect_rate = float(raw_effect_rate)
    if not 0.0 < effect_rate <= 1.0:
        raise ExperimentBlocked("minimum nonzero-effect rate must be in (0, 1]")
    return gate


def classify_behavior_gates(
    diagnostics: Mapping[str, Any], gate_contract: Mapping[str, Any]
) -> dict[str, Any]:
    """Classify coverage, category-aware anti-collapse, and state-effect gates."""
    gate = _validate_behavior_gate_contract(gate_contract)
    value = dict(_mapping(diagnostics, "diagnostics"))
    categories = dict(_mapping(value.get("categories"), "diagnostic categories"))
    blockers: list[str] = []
    for category in gate["category_coverage"]:
        if category not in categories or categories[category].get("decision_count", 0) <= 0:
            blockers.append(f"{category}_coverage")
    multi_gate = gate["multi_kind"]
    for category in multi_gate["categories"]:
        summary = categories.get(category)
        if not summary:
            continue
        if summary.get("multi_kind_decisions", 0) < multi_gate["minimum_multi_kind_decisions"]:
            blockers.append(f"{category}_multi_kind_opportunities")
            continue
        selected = summary.get("multi_kind_selected_kinds", {})
        maximum_rate = max(
            (float(row["rate"]) for row in selected.values()), default=0.0
        )
        if (
            len(selected) < multi_gate["minimum_selected_kinds"]
            or maximum_rate > multi_gate["maximum_selected_kind_rate"]
        ):
            blockers.append(f"{category}_selected_kind_saturation")
    state_gate = gate["state_effect"]
    for category in gate["category_coverage"]:
        summary = categories.get(category)
        if not summary:
            continue
        state = dict(
            _mapping(summary.get("state_effect"), f"{category} state effect")
        )
        multi_count = _nonnegative_int(
            state.get("multi_candidate_decisions"),
            f"{category} multi-candidate decisions",
        )
        nonzero = _nonnegative_int(
            state.get("nonzero_effect_decisions"),
            f"{category} nonzero-effect decisions",
        )
        relative_order_changes = _nonnegative_int(
            state.get("relative_order_change_decisions"),
            f"{category} relative-order-change decisions",
        )
        distribution = dict(
            _mapping(state.get("magnitude"), f"{category} state-effect magnitude")
        )
        maximum = distribution.get("max")
        state_passed = (
            multi_count >= state_gate["minimum_multi_candidate_decisions"]
            and nonzero / multi_count >= state_gate["minimum_nonzero_effect_rate"]
            and relative_order_changes
            >= state_gate["minimum_relative_order_change_decisions"]
            and isinstance(maximum, Real)
            and not isinstance(maximum, bool)
            and float(maximum)
            >= state_gate["minimum_absolute_relative_score_change"]
        ) if multi_count else False
        if not state_passed:
            blockers.append(f"{category}_state_effect")
    return {
        "blockers": blockers,
        "passed": not blockers,
        "schema_version": "noncombat-state-conditioned-behavior-gate-v1",
    }


def classify_terminal_verdict(
    *,
    complete: bool,
    structural_valid: bool,
    behavior_valid: bool,
    floor_signal: bool,
    initial_victories: int,
    trained_victories: int,
    blocked: bool = False,
) -> dict[str, Any]:
    """Apply invalid, blocked, negative, floor-only, then victory precedence."""
    for label, value in (
        ("complete", complete),
        ("structural_valid", structural_valid),
        ("behavior_valid", behavior_valid),
        ("floor_signal", floor_signal),
        ("blocked", blocked),
    ):
        if type(value) is not bool:
            raise ExperimentBlocked(f"{label} must be boolean")
    initial = _nonnegative_int(initial_victories, "initial victories")
    trained = _nonnegative_int(trained_victories, "trained victories")
    if not structural_valid:
        verdict = "experiment_invalid"
    elif blocked or not complete:
        verdict = "experiment_blocked"
    elif behavior_valid and floor_signal and trained > initial:
        verdict = "experiment_valid_with_victory_signal"
    elif behavior_valid and floor_signal:
        verdict = "experiment_valid_with_floor_only_signal"
    else:
        verdict = "experiment_valid_without_learning_signal"
    return {
        "behavior_valid": behavior_valid,
        "floor_signal": floor_signal,
        "initial_victories": initial,
        "trained_victories": trained,
        "verdict": verdict,
        "victory_signal": trained > initial,
    }


def build_seed_exclusion_inventory(
    sources: Mapping[str, Sequence[int]],
    *,
    repository_commit: str = "0" * 40,
    source_payloads: Mapping[str, bytes] | None = None,
) -> dict[str, Any]:
    """Build one canonical source-only union of tracked seed exclusions."""
    normalized_sources: dict[str, list[int]] = {}
    for name, raw in sorted(_mapping(sources, "seed sources").items()):
        if not isinstance(name, str) or not name:
            raise ExperimentBlocked("seed source names must be nonempty strings")
        values = sorted(
            {
                _nonnegative_int(seed, f"seed source {name}")
                for seed in _sequence(raw, f"seed source {name}")
            }
        )
        normalized_sources[name] = values
    excluded = sorted({seed for values in normalized_sources.values() for seed in values})
    if not isinstance(repository_commit, str) or not _COMMIT_RE.fullmatch(
        repository_commit
    ):
        raise ExperimentBlocked("seed inventory repository commit is invalid")
    payload_values = dict(source_payloads or {})
    if payload_values and set(payload_values) != set(normalized_sources):
        raise ExperimentBlocked("seed source payload paths mismatch")
    source_bindings = []
    for path, seeds in normalized_sources.items():
        canonical_path = _canonical_relative_path(path, "seed source path")
        payload = payload_values.get(path, canonical_json_bytes(seeds))
        if not isinstance(payload, bytes) or not payload:
            raise ExperimentBlocked("seed source payload must be nonempty bytes")
        source_bindings.append(
            {
                "path": canonical_path,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    return {
        "authority": registration_authority(),
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": repository_commit,
        "schema_version": "noncombat-state-conditioned-seed-exclusion-inventory-v1",
        "source_bindings": source_bindings,
        "sources": normalized_sources,
    }


def _validate_inventory(value: object) -> dict[str, Any]:
    inventory = copy.deepcopy(dict(_mapping(value, "seed inventory")))
    _require_keys(
        inventory,
        {
            "authority",
            "excluded_seed_count",
            "excluded_seeds",
            "repository_commit",
            "schema_version",
            "source_bindings",
            "sources",
        },
        "seed inventory",
    )
    if inventory["schema_version"] != "noncombat-state-conditioned-seed-exclusion-inventory-v1":
        raise ExperimentBlocked("seed inventory schema mismatch")
    if inventory["authority"] != registration_authority():
        raise ExperimentBlocked("seed inventory authority mismatch")
    if not isinstance(inventory["repository_commit"], str) or not _COMMIT_RE.fullmatch(
        inventory["repository_commit"]
    ):
        raise ExperimentBlocked("seed inventory repository commit is invalid")
    sources = dict(_mapping(inventory["sources"], "seed inventory sources"))
    normalized_sources = {
        path: sorted(
            {
                _nonnegative_int(seed, f"seed source {path}")
                for seed in _sequence(values, f"seed source {path}")
            }
        )
        for path, values in sorted(sources.items())
    }
    bindings = [
        _validate_binding(row, f"seed source binding[{index}]")
        for index, row in enumerate(
            _sequence(inventory["source_bindings"], "seed source bindings")
        )
    ]
    if bindings != sorted(bindings, key=lambda row: row["path"]):
        raise ExperimentBlocked("seed source bindings are not sorted")
    if [row["path"] for row in bindings] != list(normalized_sources):
        raise ExperimentBlocked("seed source bindings do not match sources")
    excluded = sorted(
        {seed for values in normalized_sources.values() for seed in values}
    )
    if (
        inventory["excluded_seeds"] != excluded
        or inventory["excluded_seed_count"] != len(excluded)
    ):
        raise ExperimentBlocked("seed inventory counts mismatch")
    inventory["sources"] = normalized_sources
    inventory["source_bindings"] = bindings
    return inventory


def _git_bytes(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise ExperimentBlocked(
            f"git {' '.join(args)} failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout


def _git_text(repo_root: Path, *args: str) -> str:
    return _git_bytes(repo_root, *args).decode("utf-8").strip()


def _git_blob_batch(
    repo_root: Path, *, repository_commit: str, paths: Sequence[str]
) -> dict[str, bytes]:
    ordered = list(paths)
    if not ordered:
        return {}
    request = "".join(f"{repository_commit}:{path}\n" for path in ordered).encode(
        "utf-8"
    )
    completed = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=repo_root,
        input=request,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        raise ExperimentBlocked(
            "git cat-file --batch failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    output = completed.stdout
    offset = 0
    result: dict[str, bytes] = {}
    for path in ordered:
        line_end = output.find(b"\n", offset)
        if line_end < 0:
            raise ExperimentBlocked("git batch response ended before blob header")
        header = output[offset:line_end].decode("ascii", errors="strict").split()
        offset = line_end + 1
        if len(header) != 3 or header[1] != "blob" or not header[2].isdigit():
            raise ExperimentBlocked(f"git batch blob header is invalid for {path}")
        size = int(header[2])
        payload = output[offset : offset + size]
        offset += size
        if len(payload) != size or output[offset : offset + 1] != b"\n":
            raise ExperimentBlocked(f"git batch blob payload is truncated for {path}")
        offset += 1
        result[path] = payload
    if offset != len(output):
        raise ExperimentBlocked("git batch response has trailing bytes")
    return result


def _seed_scalars(value: object) -> list[int]:
    result: list[int] = []

    def visit(node: object, seed_context: bool) -> None:
        if isinstance(node, Mapping):
            for key in sorted(node):
                if isinstance(key, str):
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
            return
        if isinstance(node, str) and node.isascii() and node.isdigit():
            result.append(int(node))

    visit(value, False)
    return result


def discover_tracked_seed_source_payloads(
    repo_root: Path | str, *, repository_commit: str
) -> dict[str, bytes]:
    """Read only tracked JSON evidence from one fixed Git tree."""
    root = Path(repo_root).resolve()
    commit = _validate_commit(repository_commit, "seed inventory commit")
    paths = _git_text(
        root, "ls-tree", "-r", "--name-only", commit, "--", "reports"
    ).splitlines()
    ignored = {
        DEFAULT_AUTHORIZATION_PATH,
        DEFAULT_PREFLIGHT_PATH,
        DEFAULT_REGISTRATION_PATH,
        DEFAULT_SEED_INVENTORY_PATH,
    }
    candidates = []
    for raw_path in paths:
        path = raw_path.replace("\\", "/")
        if (
            not path.endswith(".json")
            or path in ignored
            or path.startswith(f"{DEFAULT_OUTPUT_DIRECTORY}/")
        ):
            continue
        candidates.append(path)
    blobs = _git_blob_batch(
        root, repository_commit=commit, paths=sorted(candidates)
    )
    payloads: dict[str, bytes] = {}
    for path, payload in blobs.items():
        try:
            value = json.loads(
                payload,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExperimentBlocked(f"tracked seed source is invalid JSON: {path}: {exc}") from exc
        if _seed_scalars(value):
            payloads[path] = payload
    return payloads


def build_tracked_seed_exclusion_inventory(
    repo_root: Path | str, *, repository_commit: str | None = None
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = repository_commit or _git_text(root, "rev-parse", "HEAD")
    payloads = discover_tracked_seed_source_payloads(
        root, repository_commit=commit
    )
    sources = {
        path: sorted(set(_seed_scalars(json.loads(payload))))
        for path, payload in sorted(payloads.items())
    }
    return build_seed_exclusion_inventory(
        sources,
        repository_commit=commit,
        source_payloads=payloads,
    )


def verify_tracked_seed_exclusion_inventory(
    inventory: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Any]:
    normalized = _validate_inventory(inventory)
    recomputed = build_tracked_seed_exclusion_inventory(
        repo_root, repository_commit=normalized["repository_commit"]
    )
    if canonical_json_bytes(recomputed) != canonical_json_bytes(normalized):
        raise ExperimentBlocked("tracked seed inventory recomputation mismatch")
    return recomputed


def _hash_named_bytes(rows: Sequence[tuple[str, bytes]]) -> str:
    digest = hashlib.sha256()
    for name, payload in sorted(rows):
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def git_source_hash(
    repo_root: Path | str, *, commit: str, source_files: Sequence[str]
) -> str:
    root = Path(repo_root).resolve()
    paths = [
        _canonical_relative_path(path, "implementation source path")
        for path in source_files
    ]
    blobs = _git_blob_batch(
        root, repository_commit=_validate_commit(commit, "source commit"), paths=paths
    )
    return _hash_named_bytes(list(blobs.items()))


def working_source_hash(
    repo_root: Path | str, *, source_files: Sequence[str]
) -> str:
    root = Path(repo_root).resolve()
    rows = []
    for raw_path in source_files:
        path = _canonical_relative_path(raw_path, "implementation source path")
        source = root / PurePosixPath(path)
        if not source.is_file():
            raise ExperimentBlocked(f"implementation source is missing: {path}")
        rows.append((path, source.read_bytes()))
    return _hash_named_bytes(rows)


def file_binding(repo_root: Path | str, relative_path: str) -> dict[str, Any]:
    path = _canonical_relative_path(relative_path, "binding path")
    payload = (Path(repo_root).resolve() / PurePosixPath(path)).read_bytes()
    return {
        "path": path,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def external_file_binding(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    payload = source.read_bytes()
    return {
        "path": source.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def snapshot_production_checkpoints(root: Path | str) -> dict[str, Any]:
    """Hash every production checkpoint without loading model contents."""
    directory = Path(root).resolve()
    if not directory.is_dir():
        raise ExperimentBlocked("production checkpoint root is missing")
    entries = []
    for path in sorted(
        (candidate for candidate in directory.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(directory).as_posix(),
    ):
        payload = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(directory).as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    return _validate_checkpoint_inventory(
        {
            "entries": entries,
            "inventory_sha256": hashlib.sha256(
                canonical_json_bytes(entries)
            ).hexdigest(),
            "root": directory.as_posix(),
            "total_bytes": sum(row["size_bytes"] for row in entries),
        }
    )


def _verify_bound_payload(
    repo_root: Path, binding: Mapping[str, Any], label: str
) -> bytes:
    normalized = _validate_binding(binding, label)
    source = repo_root / PurePosixPath(normalized["path"])
    if not source.is_file():
        raise ExperimentBlocked(f"{label} file is missing")
    payload = source.read_bytes()
    if (
        len(payload) != normalized["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != normalized["sha256"]
    ):
        raise ExperimentBlocked(f"{label} binding mismatch")
    return payload


def _validate_preimplementation_record(
    repo_root: Path, path: Path
) -> tuple[dict[str, Any], bytes, dict[str, bytes], dict[str, bytes]]:
    payload = path.read_bytes()
    record = load_canonical_json_bytes(payload, "preimplementation record")
    _require_keys(
        record,
        {
            "authority",
            "contract",
            "evidence",
            "planned_source_files",
            "planning",
            "schema_version",
        },
        "preimplementation record",
    )
    if record["schema_version"] != PREIMPLEMENTATION_SCHEMA_VERSION:
        raise ExperimentBlocked("preimplementation schema mismatch")
    if record["authority"] != registration_authority():
        raise ExperimentBlocked("preimplementation authority mismatch")
    contract = _mapping(record["contract"], "preimplementation contract")
    required_contract = {
        "cohorts_materialized": False,
        "output_root_materialized": False,
        "source_only": True,
    }
    if any(contract.get(name) is not expected for name, expected in required_contract.items()):
        raise ExperimentBlocked("preimplementation source-only contract mismatch")

    evidence = dict(_mapping(record["evidence"], "preimplementation evidence"))
    if set(evidence) != set(PREIMPLEMENTATION_EVIDENCE_NAMES):
        raise ExperimentBlocked("preimplementation evidence names mismatch")
    evidence_payloads = {
        name: _verify_bound_payload(
            repo_root,
            _mapping(evidence[name], f"preimplementation evidence.{name}"),
            f"preimplementation evidence.{name}",
        )
        for name in sorted(evidence)
    }

    planned = list(
        _sequence(record["planned_source_files"], "planned successor source files")
    )
    if planned != list(PLANNED_SUCCESSOR_SOURCE_FILES):
        raise ExperimentBlocked("planned successor source files mismatch")

    planning = dict(_mapping(record["planning"], "preimplementation planning"))
    _require_keys(planning, {"commit", "files"}, "preimplementation planning")
    commit = _validate_commit(planning["commit"], "planning commit")
    planning_files = dict(_mapping(planning["files"], "planning files"))
    if set(planning_files) != {"design", "proposal", "spec", "tasks"}:
        raise ExperimentBlocked("planning file names mismatch")
    normalized_planning = {
        name: _validate_binding(binding, f"planning.{name}")
        for name, binding in sorted(planning_files.items())
    }
    planning_blobs = _git_blob_batch(
        repo_root,
        repository_commit=commit,
        paths=[binding["path"] for binding in normalized_planning.values()],
    )
    for name, binding in normalized_planning.items():
        blob = planning_blobs[binding["path"]]
        if (
            len(blob) != binding["size_bytes"]
            or hashlib.sha256(blob).hexdigest() != binding["sha256"]
        ):
            raise ExperimentBlocked(f"planning.{name} binding mismatch")
    return record, payload, evidence_payloads, planning_blobs


def _legacy_r2_isolation_baseline(
    preflight: Mapping[str, Any], checkpoint_root: Path | str
) -> dict[str, Any]:
    isolation = dict(_mapping(preflight.get("isolation"), "r2 isolation"))
    config = _validate_external_binding(
        isolation.get("communication_mod_config"), "r2 CommunicationMod config"
    )
    entries = [
        _validate_binding(row, f"r2 checkpoint[{index}]")
        for index, row in enumerate(
            _sequence(isolation.get("checkpoint_inventory"), "r2 checkpoint inventory")
        )
    ]
    if entries != sorted(entries, key=lambda row: row["path"]):
        raise ExperimentBlocked("r2 checkpoint inventory is not sorted")
    expected_count = _positive_int(
        isolation.get("production_checkpoint_count"), "r2 checkpoint count"
    )
    expected_total = _positive_int(
        isolation.get("checkpoint_total_bytes"), "r2 checkpoint total bytes"
    )
    expected_sha = _validate_sha256(
        isolation.get("checkpoint_inventory_sha256"), "r2 checkpoint inventory sha256"
    )
    if (
        len(entries) != expected_count
        or sum(row["size_bytes"] for row in entries) != expected_total
        or hashlib.sha256(canonical_json_bytes(entries)).hexdigest() != expected_sha
    ):
        raise ExperimentBlocked("r2 checkpoint inventory summary mismatch")
    if isolation.get("pre_snapshot_sha256") != isolation.get("post_snapshot_sha256"):
        raise ExperimentBlocked("r2 isolation snapshots differ")
    checks = _mapping(preflight.get("checks"), "r2 preflight checks")
    if checks.get("communication_mod_config_unchanged") is not True:
        raise ExperimentBlocked("r2 CommunicationMod isolation was not verified")
    if checks.get("production_checkpoint_inventory_unchanged") is not True:
        raise ExperimentBlocked("r2 checkpoint isolation was not verified")
    return {
        "communication_mod_config": config,
        "production_checkpoints": {
            "entries": entries,
            "inventory_sha256": expected_sha,
            "root": Path(checkpoint_root).resolve().as_posix(),
            "total_bytes": expected_total,
        },
    }


def _run_json_process(command: Sequence[str], *, cwd: Path, label: str) -> dict[str, Any]:
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ExperimentBlocked(f"{label} failed: {detail}")
    try:
        result = json.loads(
            completed.stdout,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise ExperimentBlocked(f"{label} returned invalid JSON: {exc}") from exc
    if not isinstance(result, dict):
        raise ExperimentBlocked(f"{label} must return a JSON object")
    return result


def _source_only_import_probe(source: Path, *, repo_root: Path) -> dict[str, bool]:
    probe_code = f"""
import importlib.util
import json
import os
import sys

opened = []

def audit(event, args):
    if event != "open" or not args:
        return
    value = args[0]
    if isinstance(value, (str, bytes, os.PathLike)):
        opened.append(os.fsdecode(value).replace("\\\\", "/").casefold())

sys.addaudithook(audit)
spec = importlib.util.spec_from_file_location("source_only_import_probe", {str(source)!r})
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
patterns = (
    "/runs/",
    "/ai_games.txt",
    "ai_decision_trace",
    "sim_divergence_trace",
    "_seed_inventory.json",
)
print(json.dumps({{
    "empirical_seed_file_accessed": any(
        any(pattern in path for pattern in patterns) for path in opened
    ),
    "native_module_imported": any(
        name == "sts_lightspeed_noncombat_adapter" for name in sys.modules
    ),
    "torch_imported": any(name == "torch" or name.startswith("torch.") for name in sys.modules),
}}, sort_keys=True))
"""
    result = _run_json_process(
        [sys.executable, "-c", probe_code],
        cwd=repo_root,
        label=f"source-only import probe for {source.name}",
    )
    expected = {
        "empirical_seed_file_accessed": False,
        "native_module_imported": False,
        "torch_imported": False,
    }
    if result != expected:
        raise ExperimentBlocked(f"source-only import probe failed for {source.name}")
    return expected


def _checkpoint_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    inventory = _validate_checkpoint_inventory(value)
    return {
        "entry_count": len(inventory["entries"]),
        "inventory_sha256": inventory["inventory_sha256"],
        "root": inventory["root"],
        "total_bytes": inventory["total_bytes"],
    }


def _validate_checkpoint_summary(value: object, label: str) -> dict[str, Any]:
    summary = dict(_mapping(value, label))
    _require_keys(
        summary,
        {"entry_count", "inventory_sha256", "root", "total_bytes"},
        label,
    )
    summary["entry_count"] = _positive_int(summary["entry_count"], f"{label}.entry_count")
    summary["inventory_sha256"] = _validate_sha256(
        summary["inventory_sha256"], f"{label}.inventory_sha256"
    )
    summary["root"] = _canonical_windows_path(summary["root"], f"{label}.root")
    summary["total_bytes"] = _positive_int(
        summary["total_bytes"], f"{label}.total_bytes"
    )
    return summary


def build_source_only_implementation_verification(
    *,
    repo_root: Path | str,
    preimplementation_path: Path | str,
    r2_preflight_path: Path | str,
    production_checkpoint_root: Path | str,
) -> dict[str, Any]:
    """Recheck frozen evidence and external isolation without runtime loading."""
    forbidden_before = [
        name
        for name in sys.modules
        if name == "torch"
        or name.startswith("torch.")
        or name == "sts_lightspeed_noncombat_adapter"
    ]
    if forbidden_before:
        raise ExperimentBlocked("implementation verification imported a runtime module")
    root = Path(repo_root).resolve()
    preimplementation_file = Path(preimplementation_path).resolve()
    r2_preflight_file = Path(r2_preflight_path).resolve()
    record, preimplementation_bytes, evidence_payloads, planning_blobs = (
        _validate_preimplementation_record(root, preimplementation_file)
    )
    r2_preflight_bytes = r2_preflight_file.read_bytes()
    r2_preflight = load_canonical_json_bytes(r2_preflight_bytes, "r2 preflight")
    baseline = _legacy_r2_isolation_baseline(
        r2_preflight, production_checkpoint_root
    )
    current_config = external_file_binding(
        baseline["communication_mod_config"]["path"]
    )
    if current_config != baseline["communication_mod_config"]:
        raise ExperimentBlocked("CommunicationMod configuration changed since r2")
    current_checkpoints = snapshot_production_checkpoints(production_checkpoint_root)
    if current_checkpoints != baseline["production_checkpoints"]:
        raise ExperimentBlocked("production checkpoints changed since r2")

    evidence = dict(_mapping(record["evidence"], "preimplementation evidence"))
    r2_manifest = _validate_binding(evidence["r2_manifest"], "r2 manifest")
    r2_output_relative = PurePosixPath(r2_manifest["path"]).parent.as_posix()
    r2_output = root / PurePosixPath(r2_output_relative)
    r2_verifier = root / PurePosixPath(R2_VERIFIER_PATH)
    r2_verification = _run_json_process(
        [sys.executable, str(r2_verifier), str(r2_output)],
        cwd=root,
        label="independent r2 terminal verification",
    )
    if (
        r2_verification.get("verification") != "verified"
        or r2_verification.get("verdict")
        != "experiment_valid_without_learning_signal"
        or r2_verification.get("formal_readiness_verdict")
        != "not_ready_for_bounded_training_proposal"
    ):
        raise ExperimentBlocked("r2 terminal verification verdict mismatch")

    probe_sources = {
        "r2_terminal_verifier": r2_verifier,
        "successor_runner": root
        / "analysis_scripts/noncombat_state_conditioned_simulator_learning_experiment.py",
        "successor_terminal_verifier": root
        / "analysis_scripts/verify_noncombat_state_conditioned_simulator_learning_experiment.py",
    }
    probes = {
        name: _source_only_import_probe(path, repo_root=root)
        for name, path in sorted(probe_sources.items())
    }
    source_bindings = [
        file_binding(root, path) for path in record["planned_source_files"]
    ]
    planning = _mapping(record["planning"], "preimplementation planning")
    report = {
        "authority": registration_authority(),
        "checks": {
            "communication_mod_config_unchanged": True,
            "empirical_seed_consumed": False,
            "environment_constructed": False,
            "frozen_evidence_unchanged": True,
            "native_module_imported": False,
            "planning_evidence_unchanged": True,
            "production_checkpoint_inventory_unchanged": True,
            "r2_terminal_artifacts_verified": True,
            "torch_imported": False,
            "training_started": False,
        },
        "external_isolation": {
            "communication_mod_config": {
                "current": current_config,
                "historical": baseline["communication_mod_config"],
                "unchanged": True,
            },
            "production_checkpoints": {
                "current": _checkpoint_summary(current_checkpoints),
                "historical": _checkpoint_summary(
                    baseline["production_checkpoints"]
                ),
                "unchanged": True,
            },
            "r2_preflight": file_binding(
                root, r2_preflight_file.relative_to(root).as_posix()
            ),
        },
        "frozen_evidence": {
            "binding_count": len(evidence_payloads),
            "bindings": evidence,
            "combined_sha256": _hash_named_bytes(list(evidence_payloads.items())),
            "preimplementation": {
                "path": preimplementation_file.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(preimplementation_bytes).hexdigest(),
                "size_bytes": len(preimplementation_bytes),
            },
        },
        "implementation": {
            "source_files": source_bindings,
            "working_source_sha256": _hash_named_bytes(
                [
                    (binding["path"], (root / binding["path"]).read_bytes())
                    for binding in source_bindings
                ]
            ),
        },
        "import_probes": probes,
        "planning": {
            "commit": planning["commit"],
            "file_count": len(planning_blobs),
            "files": planning["files"],
        },
        "r2_terminal": {
            "output_directory": r2_output_relative,
            "verification": r2_verification,
            "verifier": file_binding(root, R2_VERIFIER_PATH),
        },
        "schema_version": IMPLEMENTATION_VERIFICATION_SCHEMA_VERSION,
        "verdict": "source_only_implementation_verified",
    }
    forbidden_after = [
        name
        for name in sys.modules
        if name == "torch"
        or name.startswith("torch.")
        or name == "sts_lightspeed_noncombat_adapter"
    ]
    if forbidden_after:
        raise ExperimentBlocked("implementation verification imported a runtime module")
    return validate_implementation_verification_report(report, root)


def validate_implementation_verification_report(
    value: object, repo_root: Path | str
) -> dict[str, Any]:
    report = copy.deepcopy(dict(_mapping(value, "implementation verification")))
    _require_keys(
        report,
        {
            "authority",
            "checks",
            "external_isolation",
            "frozen_evidence",
            "implementation",
            "import_probes",
            "planning",
            "r2_terminal",
            "schema_version",
            "verdict",
        },
        "implementation verification",
    )
    if report["schema_version"] != IMPLEMENTATION_VERIFICATION_SCHEMA_VERSION:
        raise ExperimentBlocked("implementation verification schema mismatch")
    if report["authority"] != registration_authority():
        raise ExperimentBlocked("implementation verification authority mismatch")
    expected_checks = {
        "communication_mod_config_unchanged": True,
        "empirical_seed_consumed": False,
        "environment_constructed": False,
        "frozen_evidence_unchanged": True,
        "native_module_imported": False,
        "planning_evidence_unchanged": True,
        "production_checkpoint_inventory_unchanged": True,
        "r2_terminal_artifacts_verified": True,
        "torch_imported": False,
        "training_started": False,
    }
    if report["checks"] != expected_checks:
        raise ExperimentBlocked("implementation verification checks mismatch")
    if report["verdict"] != "source_only_implementation_verified":
        raise ExperimentBlocked("implementation verification verdict mismatch")

    root = Path(repo_root).resolve()
    frozen = dict(_mapping(report["frozen_evidence"], "frozen evidence"))
    _require_keys(
        frozen,
        {"binding_count", "bindings", "combined_sha256", "preimplementation"},
        "frozen evidence",
    )
    bindings = dict(_mapping(frozen["bindings"], "frozen evidence bindings"))
    if set(bindings) != set(PREIMPLEMENTATION_EVIDENCE_NAMES):
        raise ExperimentBlocked("frozen evidence names mismatch")
    payloads = {
        name: _verify_bound_payload(root, binding, f"frozen evidence.{name}")
        for name, binding in sorted(bindings.items())
    }
    if frozen["binding_count"] != len(payloads):
        raise ExperimentBlocked("frozen evidence binding count mismatch")
    if frozen["combined_sha256"] != _hash_named_bytes(list(payloads.items())):
        raise ExperimentBlocked("frozen evidence combined sha256 mismatch")
    _verify_bound_payload(root, frozen["preimplementation"], "preimplementation")

    implementation = dict(_mapping(report["implementation"], "implementation"))
    _require_keys(
        implementation, {"source_files", "working_source_sha256"}, "implementation"
    )
    source_bindings = [
        _validate_binding(binding, f"implementation source[{index}]")
        for index, binding in enumerate(
            _sequence(implementation["source_files"], "implementation source files")
        )
    ]
    if [binding["path"] for binding in source_bindings] != list(
        PLANNED_SUCCESSOR_SOURCE_FILES
    ):
        raise ExperimentBlocked("implementation source paths mismatch")
    source_payloads = [
        (
            binding["path"],
            _verify_bound_payload(root, binding, f"implementation source[{index}]"),
        )
        for index, binding in enumerate(source_bindings)
    ]
    if implementation["working_source_sha256"] != _hash_named_bytes(source_payloads):
        raise ExperimentBlocked("implementation source sha256 mismatch")

    planning = dict(_mapping(report["planning"], "planning verification"))
    _require_keys(planning, {"commit", "file_count", "files"}, "planning verification")
    commit = _validate_commit(planning["commit"], "planning verification commit")
    planning_files = dict(_mapping(planning["files"], "planning verification files"))
    if set(planning_files) != {"design", "proposal", "spec", "tasks"}:
        raise ExperimentBlocked("planning verification file names mismatch")
    normalized_planning = {
        name: _validate_binding(binding, f"planning verification.{name}")
        for name, binding in sorted(planning_files.items())
    }
    if planning["file_count"] != len(normalized_planning):
        raise ExperimentBlocked("planning verification file count mismatch")
    blobs = _git_blob_batch(
        root,
        repository_commit=commit,
        paths=[binding["path"] for binding in normalized_planning.values()],
    )
    for name, binding in normalized_planning.items():
        payload = blobs[binding["path"]]
        if (
            len(payload) != binding["size_bytes"]
            or hashlib.sha256(payload).hexdigest() != binding["sha256"]
        ):
            raise ExperimentBlocked(f"planning verification.{name} mismatch")

    external = dict(_mapping(report["external_isolation"], "external isolation"))
    _require_keys(
        external,
        {"communication_mod_config", "production_checkpoints", "r2_preflight"},
        "external isolation",
    )
    config = dict(_mapping(external["communication_mod_config"], "config isolation"))
    _require_keys(config, {"current", "historical", "unchanged"}, "config isolation")
    if config["unchanged"] is not True:
        raise ExperimentBlocked("CommunicationMod config is not unchanged")
    current_config = _validate_external_binding(config["current"], "current config")
    historical_config = _validate_external_binding(
        config["historical"], "historical config"
    )
    if current_config != historical_config:
        raise ExperimentBlocked("CommunicationMod config bindings differ")
    if external_file_binding(current_config["path"]) != current_config:
        raise ExperimentBlocked("CommunicationMod config live binding mismatch")
    checkpoints = dict(
        _mapping(external["production_checkpoints"], "checkpoint isolation")
    )
    _require_keys(
        checkpoints,
        {"current", "historical", "unchanged"},
        "checkpoint isolation",
    )
    if checkpoints["unchanged"] is not True:
        raise ExperimentBlocked("production checkpoint inventory is not unchanged")
    current_checkpoints = _validate_checkpoint_summary(
        checkpoints["current"], "current checkpoint summary"
    )
    historical_checkpoints = _validate_checkpoint_summary(
        checkpoints["historical"], "historical checkpoint summary"
    )
    if current_checkpoints != historical_checkpoints:
        raise ExperimentBlocked("production checkpoint summaries differ")
    live_checkpoints = _checkpoint_summary(
        snapshot_production_checkpoints(current_checkpoints["root"])
    )
    if live_checkpoints != current_checkpoints:
        raise ExperimentBlocked("production checkpoint live inventory mismatch")
    _verify_bound_payload(root, external["r2_preflight"], "r2 preflight")

    probes = dict(_mapping(report["import_probes"], "import probes"))
    if set(probes) != {
        "r2_terminal_verifier",
        "successor_runner",
        "successor_terminal_verifier",
    }:
        raise ExperimentBlocked("source-only import probe names mismatch")
    expected_probe = {
        "empirical_seed_file_accessed": False,
        "native_module_imported": False,
        "torch_imported": False,
    }
    if any(probe != expected_probe for probe in probes.values()):
        raise ExperimentBlocked("source-only import probe result mismatch")
    probe_sources = {
        "r2_terminal_verifier": root / PurePosixPath(R2_VERIFIER_PATH),
        "successor_runner": root / PurePosixPath(EXECUTION_SOURCE_PATH),
        "successor_terminal_verifier": root
        / "analysis_scripts/verify_noncombat_state_conditioned_simulator_learning_experiment.py",
    }
    live_probes = {
        name: _source_only_import_probe(path, repo_root=root)
        for name, path in sorted(probe_sources.items())
    }
    if live_probes != probes:
        raise ExperimentBlocked("source-only import probe live replay mismatch")

    terminal = dict(_mapping(report["r2_terminal"], "r2 terminal"))
    _require_keys(
        terminal, {"output_directory", "verification", "verifier"}, "r2 terminal"
    )
    r2_output_relative = _canonical_relative_path(
        terminal["output_directory"], "r2 output directory"
    )
    _verify_bound_payload(root, terminal["verifier"], "r2 verifier")
    verification = dict(_mapping(terminal["verification"], "r2 verification"))
    _require_keys(
        verification,
        {"artifact_count", "checks", "formal_readiness_verdict", "verdict", "verification"},
        "r2 verification",
    )
    if (
        _positive_int(verification["artifact_count"], "r2 artifact count") != 202
        or _positive_int(verification["checks"], "r2 verification checks") != 225389
        or verification["formal_readiness_verdict"]
        != "not_ready_for_bounded_training_proposal"
        or verification["verdict"] != "experiment_valid_without_learning_signal"
        or verification["verification"] != "verified"
    ):
        raise ExperimentBlocked("r2 terminal verification mismatch")
    live_verification = _run_json_process(
        [
            sys.executable,
            str(root / PurePosixPath(R2_VERIFIER_PATH)),
            str(root / PurePosixPath(r2_output_relative)),
        ],
        cwd=root,
        label="independent r2 terminal verification replay",
    )
    if live_verification != verification:
        raise ExperimentBlocked("r2 terminal verification live replay mismatch")
    return report


def _verify_repo_binding(
    repo_root: Path, binding: Mapping[str, Any], label: str
) -> None:
    normalized = _validate_binding(binding, label)
    if file_binding(repo_root, normalized["path"]) != normalized:
        raise ExperimentBlocked(f"{label} binding mismatch")


def _verify_external_binding(binding: Mapping[str, Any], label: str) -> None:
    normalized = _validate_external_binding(binding, label)
    if external_file_binding(normalized["path"]) != normalized:
        raise ExperimentBlocked(f"{label} binding mismatch")


def _installed_torch_version() -> str:
    try:
        return importlib_metadata.version("torch")
    except importlib_metadata.PackageNotFoundError as exc:
        raise ExperimentBlocked("runtime PyTorch distribution is missing") from exc


def find_relevant_processes() -> list[dict[str, Any]]:
    """Return live gameplay/CommunicationMod Python or Java processes."""
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -in @('java.exe','javaw.exe','python.exe','pythonw.exe','SlayTheSpire.exe') } | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise ExperimentBlocked(
            f"process inventory failed: {completed.stderr.strip()}"
        )
    raw = completed.stdout.strip()
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExperimentBlocked(f"process inventory JSON is invalid: {exc}") from exc
    rows = value if isinstance(value, list) else [value]
    relevant = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        process_id = row.get("ProcessId")
        line = str(row.get("CommandLine") or "")
        folded = line.casefold().replace("\\", "/")
        name = str(row.get("Name") or "")
        if process_id == os.getpid():
            continue
        if (
            name.casefold() == "slaythespire.exe"
            or "modthespire" in folded
            or "communicationmod" in folded
            or "slay-the-spire-ai/main.py" in folded
        ):
            relevant.append(
                {
                    "command_line": line,
                    "name": name,
                    "process_id": int(process_id),
                }
            )
    return relevant


def _load_control_files(
    registration_path: Path | str, authorization_path: Path | str
) -> tuple[dict[str, Any], bytes, dict[str, Any], bytes]:
    registration_bytes = Path(registration_path).read_bytes()
    authorization_bytes = Path(authorization_path).read_bytes()
    registration = validate_registration(
        load_canonical_json_bytes(registration_bytes, "registration")
    )
    authorization = validate_execution_authorization(
        load_canonical_json_bytes(authorization_bytes, "authorization"),
        registration=registration,
        registration_bytes=registration_bytes,
    )
    return registration, registration_bytes, authorization, authorization_bytes


def _lock_execution_lease(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_execution_lease(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def recover_stale_execution_lease(
    output: Path | str, logical_execution_id: str
) -> bool:
    """Confirm an existing persistent lease has no live OS-lock owner."""
    _validate_execution_id(logical_execution_id)
    path = Path(output) / ".execution.lease"
    try:
        handle = path.open("r+b")
    except FileNotFoundError:
        return False
    locked = False
    try:
        try:
            _lock_execution_lease(handle)
            locked = True
        except OSError as exc:
            raise ExperimentBlocked("execution lease is already held") from exc
    finally:
        try:
            if locked:
                _unlock_execution_lease(handle)
        finally:
            handle.close()
    return True


def validate_nonterminal_output_inventory(output: Path | str) -> list[str]:
    """Reject partial terminal publication before native loading on resume."""
    directory = Path(output)
    checkpoint_dir = directory / "checkpoints"
    if not checkpoint_dir.is_dir():
        raise ExperimentBlocked("resume checkpoint directory is missing")
    root_files = {
        path.name for path in directory.iterdir() if path.is_file()
    }
    expected_root_files = {
        "authorization.json",
        "configuration.json",
        "execution_journal.json",
        "registration.json",
    }
    if root_files not in (
        expected_root_files,
        expected_root_files | {".execution.lease"},
    ):
        raise ExperimentBlocked("resume output contains partial or extra artifacts")
    directories = {path.name for path in directory.iterdir() if path.is_dir()}
    if directories != {"checkpoints"}:
        raise ExperimentBlocked("resume output contains an extra directory")
    checkpoint_names = sorted(
        path.name for path in checkpoint_dir.iterdir() if path.is_file()
    )
    if any(
        name != f"checkpoint_{index:04d}.json"
        for index, name in enumerate(checkpoint_names, start=1)
    ):
        raise ExperimentBlocked("resume checkpoint files are not contiguous")
    if any(path.is_dir() for path in checkpoint_dir.iterdir()):
        raise ExperimentBlocked("resume checkpoint directory contains a directory")
    return checkpoint_names


def _initial_configuration(
    registration: Mapping[str, Any],
    *,
    registration_bytes: bytes,
    authorization_bytes: bytes,
) -> dict[str, Any]:
    return {
        "authority": registration_authority(),
        "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
        "experiment": registration["experiment"],
        "identity": registration["identity"],
        "limits": registration["limits"],
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "schema_version": "noncombat-state-conditioned-configuration-v1",
    }


def _started_journal(logical_execution_id: str) -> dict[str, Any]:
    return {
        "logical_execution_id": _validate_execution_id(logical_execution_id),
        "records": [
            {
                "checkpoint_index": 0,
                "completed_episodes": 0,
                "sequence": 0,
                "state": "started",
            }
        ],
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "state": "started",
    }


def validate_abandoned_prestart_output(
    output: Path | str,
    *,
    registration: Mapping[str, Any],
    registration_bytes: bytes,
    authorization_bytes: bytes,
) -> dict[str, Any]:
    """Validate only the exact initialization prefix preceding started."""
    directory = Path(output)
    if not directory.is_dir() or directory.is_symlink():
        raise ExperimentBlocked("abandoned pre-start output must be a directory")
    if (directory / "execution_journal.json").exists():
        raise ExperimentBlocked("abandoned pre-start output already has a journal")
    entries = list(directory.iterdir())
    if any(path.is_symlink() for path in entries):
        raise ExperimentBlocked("abandoned pre-start output contains a symlink")

    configuration_bytes = canonical_json_bytes(
        _initial_configuration(
            registration,
            registration_bytes=registration_bytes,
            authorization_bytes=authorization_bytes,
        )
    )
    stages: list[tuple[str, str, bytes | None]] = [
        ("registration.json", "file", registration_bytes),
        ("authorization.json", "file", authorization_bytes),
        ("configuration.json", "file", configuration_bytes),
        ("checkpoints", "directory", None),
        ("execution_journal.json", "file", None),
    ]
    first_missing = len(stages)
    for index, (name, kind, expected_bytes) in enumerate(stages):
        path = directory / name
        exists = path.exists()
        if not exists:
            first_missing = min(first_missing, index)
            continue
        if index > first_missing:
            raise ExperimentBlocked("abandoned pre-start artifacts are not a prefix")
        if kind == "directory":
            if not path.is_dir() or any(path.iterdir()):
                raise ExperimentBlocked("abandoned checkpoint directory must be empty")
        else:
            if not path.is_file() or expected_bytes is None:
                raise ExperimentBlocked("abandoned pre-start artifact is invalid")
            if path.read_bytes() != expected_bytes:
                raise ExperimentBlocked(f"abandoned pre-start {name} bytes mismatch")

    temporary_targets = {
        ".registration.json.tmp": 0,
        ".authorization.json.tmp": 1,
        ".configuration.json.tmp": 2,
        ".execution_journal.json.tmp": 4,
    }
    temporary_names = sorted(
        path.name for path in entries if path.name in temporary_targets
    )
    if len(temporary_names) > 1:
        raise ExperimentBlocked("abandoned pre-start has multiple temporary artifacts")
    if temporary_names:
        temporary_name = temporary_names[0]
        if temporary_targets[temporary_name] != first_missing:
            raise ExperimentBlocked("abandoned pre-start temporary artifact is out of order")

    allowed_files = {
        ".execution.lease",
        "authorization.json",
        "configuration.json",
        "registration.json",
        *temporary_targets,
    }
    root_files = {path.name for path in entries if path.is_file()}
    if not root_files.issubset(allowed_files):
        raise ExperimentBlocked("abandoned pre-start contains an extra file")
    root_directories = {path.name for path in entries if path.is_dir()}
    if not root_directories.issubset({"checkpoints"}):
        raise ExperimentBlocked("abandoned pre-start contains an extra directory")
    if len(root_files) + len(root_directories) != len(entries):
        raise ExperimentBlocked("abandoned pre-start contains an unsupported entry")
    return {
        "first_missing_stage": first_missing,
        "temporary_artifacts": temporary_names,
    }


def complete_abandoned_prestart_output(
    output: Path | str,
    *,
    registration: Mapping[str, Any],
    registration_bytes: bytes,
    authorization: Mapping[str, Any],
    authorization_bytes: bytes,
    execution_lease: "ExecutionLease",
) -> dict[str, Any]:
    """Complete a validated pre-start prefix while retaining its OS lease."""
    directory = Path(output)
    execution_id = _validate_execution_id(authorization["logical_execution_id"])
    if (
        execution_lease.released
        or execution_lease.logical_execution_id != execution_id
        or execution_lease.path.resolve() != (directory / ".execution.lease").resolve()
    ):
        raise ExperimentBlocked("abandoned pre-start recovery lacks lease ownership")
    state = validate_abandoned_prestart_output(
        directory,
        registration=registration,
        registration_bytes=registration_bytes,
        authorization_bytes=authorization_bytes,
    )
    for name in state["temporary_artifacts"]:
        (directory / name).unlink()

    expected_files = (
        ("registration.json", registration_bytes),
        ("authorization.json", authorization_bytes),
        (
            "configuration.json",
            canonical_json_bytes(
                _initial_configuration(
                    registration,
                    registration_bytes=registration_bytes,
                    authorization_bytes=authorization_bytes,
                )
            ),
        ),
    )
    for name, payload in expected_files:
        path = directory / name
        if not path.exists():
            _atomic_write_once(path, payload)
    checkpoint_directory = directory / "checkpoints"
    if not checkpoint_directory.exists():
        checkpoint_directory.mkdir()
    journal = _started_journal(execution_id)
    _atomic_write_once(
        directory / "execution_journal.json", canonical_json_bytes(journal)
    )
    return journal


def source_only_preflight(
    *,
    repo_root: Path | str,
    registration_path: Path | str,
    authorization_path: Path | str,
    output_dir: Path | str,
    relevant_processes: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate all identities available before native or Torch loading."""
    native_module_name = "sts_lightspeed_noncombat_adapter"
    root = Path(repo_root).resolve()
    registration_file = Path(registration_path).resolve()
    authorization_file = Path(authorization_path).resolve()
    output = Path(output_dir).resolve()
    registration, registration_bytes, authorization, authorization_bytes = _load_control_files(
        registration_file, authorization_file
    )
    identity = registration["identity"]
    expected_output = root / PurePosixPath(identity["output_directory"])
    if output != expected_output.resolve():
        raise ExperimentBlocked("authorized output path mismatch")
    stale_lease_recovered = False
    consumed_operation_reason: str | None = None
    if output.exists():
        if (
            authorization["execution"][
                "same_identity_checkpoint_resume_authorized"
            ]
            is not True
        ):
            raise ExperimentBlocked("same-identity checkpoint resume is not authorized")
        stale_lease_recovered = recover_stale_execution_lease(
            output, identity["logical_execution_id"]
        )
        journal_path = output / "execution_journal.json"
        if not journal_path.exists():
            validate_abandoned_prestart_output(
                output,
                registration=registration,
                registration_bytes=registration_bytes,
                authorization_bytes=authorization_bytes,
            )
            output_state = "abandoned_prestart"
        else:
            if (
                (output / "registration.json").read_bytes() != registration_bytes
                or (output / "authorization.json").read_bytes()
                != authorization_bytes
            ):
                raise ExperimentBlocked("resume control bytes mismatch")
            journal = validate_journal(
                load_canonical_json_bytes(
                    journal_path.read_bytes(),
                    "execution journal",
                ),
                logical_execution_id=identity["logical_execution_id"],
            )
            if journal["state"] == "terminal":
                raise ExperimentBlocked("terminal logical execution cannot resume")
            checkpoint_names = validate_nonterminal_output_inventory(output)
            try:
                validate_nonterminal_resume_coordinates(
                    output,
                    journal=journal,
                    checkpoint_names=checkpoint_names,
                    registration=registration,
                )
            except ExperimentBlocked as exc:
                if str(exc) != "started operation consumed the logical execution":
                    raise
                last = journal["records"][-1]
                marker = str(
                    last.get("operation") or last.get("name") or last.get("state")
                )
                consumed_operation_reason = (
                    f"interrupted_without_durable_checkpoint:{marker}"
                )
            output_state = "resume"
    else:
        output_state = "absent"

    registration_binding = authorization["registration"]
    try:
        registration_relative = registration_file.relative_to(root).as_posix()
        authorization_relative = authorization_file.relative_to(root).as_posix()
    except ValueError as exc:
        raise ExperimentBlocked("control files must be inside the authorized repository") from exc
    if registration_relative != registration_binding["path"]:
        raise ExperimentBlocked("authorization registration path mismatch")
    expected_execution = _build_execution_binding(
        registration,
        repo_root=root,
        registration_path=registration_relative,
        authorization_path=authorization_relative,
    )
    if authorization["execution"] != expected_execution:
        raise ExperimentBlocked("authorization execution command or repository mismatch")
    committed_registration = _git_bytes(
        root,
        "show",
        f"{registration_binding['commit']}:{registration_relative}",
    )
    if committed_registration != registration_bytes:
        raise ExperimentBlocked("pushed registration bytes mismatch")
    committed_authorization = _git_bytes(
        root, "show", f"{PUSHED_REMOTE_REF}:{authorization_relative}"
    )
    if committed_authorization != authorization_bytes:
        raise ExperimentBlocked("pushed authorization bytes mismatch")
    _git_text(
        root,
        "merge-base",
        "--is-ancestor",
        registration_binding["commit"],
        PUSHED_REMOTE_REF,
    )
    if consumed_operation_reason is not None:
        consume_started_journal(
            output,
            logical_execution_id=identity["logical_execution_id"],
            reason=consumed_operation_reason,
        )
        raise ExperimentBlocked(
            "interrupted operation was terminalized as a consumed execution"
        )
    if "torch" in sys.modules:
        raise ExperimentBlocked("source-only preflight must run before Torch import")
    if native_module_name in sys.modules:
        raise ExperimentBlocked("source-only preflight must run before native import")
    processes = (
        list(relevant_processes)
        if relevant_processes is not None
        else find_relevant_processes()
    )
    if processes:
        raise ExperimentBlocked("gameplay or CommunicationMod process is active")

    implementation = identity["implementation"]
    source_commit = implementation["commit"]
    _git_text(
        root, "merge-base", "--is-ancestor", source_commit, PUSHED_REMOTE_REF
    )
    git_hash = git_source_hash(
        root, commit=source_commit, source_files=implementation["source_files"]
    )
    working_hash = working_source_hash(
        root, source_files=implementation["source_files"]
    )
    if git_hash != implementation["source_sha256"] or working_hash != git_hash:
        raise ExperimentBlocked("implementation source identity mismatch")
    for name, binding in identity["evidence"].items():
        _verify_repo_binding(root, binding, f"evidence.{name}")
    _verify_repo_binding(
        root, identity["seed_inventory_binding"], "seed inventory"
    )
    inventory = load_canonical_json_bytes(
        (root / PurePosixPath(identity["seed_inventory_binding"]["path"])).read_bytes(),
        "seed inventory",
    )
    verify_tracked_seed_exclusion_inventory(inventory, root)
    if canonical_json_bytes(inventory) != canonical_json_bytes(registration["seed_inventory"]):
        raise ExperimentBlocked("registration and tracked seed inventory differ")

    runtime = identity["runtime"]
    if Path(sys.executable).resolve().as_posix().casefold() != runtime["executable"].casefold():
        raise ExperimentBlocked("runtime executable mismatch")
    if sys.platform != runtime["platform"]:
        raise ExperimentBlocked("runtime platform mismatch")
    if platform.python_version() != runtime["python_version"]:
        raise ExperimentBlocked("runtime Python version mismatch")
    if _installed_torch_version() != runtime["torch_version"]:
        raise ExperimentBlocked("runtime PyTorch version mismatch")

    _verify_external_binding(identity["native"]["module"], "native module")
    provenance = identity["adapter_provenance"]
    adapter_commit = provenance["adapter_commit"]
    _git_text(
        root, "merge-base", "--is-ancestor", adapter_commit, PUSHED_REMOTE_REF
    )
    if git_source_hash(
        root,
        commit=adapter_commit,
        source_files=ADAPTER_SOURCE_FILES,
    ) != provenance["adapter_source_sha256"]:
        raise ExperimentBlocked("adapter source identity mismatch")
    simulator_repo = Path(identity["native"]["simulator_repo"])
    from analysis_scripts.noncombat_simulator_adapter import (
        hash_compiled_simulator_sources,
    )

    source_sha, source_count = hash_compiled_simulator_sources(simulator_repo)
    if (
        source_sha != provenance["simulator_source_sha256"]
        or source_count != provenance["simulator_source_file_count"]
        or _git_text(simulator_repo, "rev-parse", "HEAD") != provenance["simulator_commit"]
        or bool(_git_text(simulator_repo, "status", "--porcelain=v1"))
        is not provenance["simulator_dirty"]
    ):
        raise ExperimentBlocked("simulator source identity mismatch")
    for name, commit in provenance["submodules"].items():
        if _git_text(simulator_repo / name, "rev-parse", "HEAD") != commit:
            raise ExperimentBlocked(f"simulator submodule identity mismatch: {name}")

    isolation = identity["isolation"]
    _verify_external_binding(
        isolation["communication_mod_config"], "CommunicationMod config"
    )
    checkpoint_snapshot = snapshot_production_checkpoints(
        isolation["production_checkpoints"]["root"]
    )
    if checkpoint_snapshot != isolation["production_checkpoints"]:
        raise ExperimentBlocked("production checkpoint inventory mismatch")
    if "torch" in sys.modules or native_module_name in sys.modules:
        raise ExperimentBlocked("source-only preflight imported runtime modules")
    return {
        "authority": execution_authority(),
        "checks": {
            "authorization_pushed_exact": True,
            "communication_mod_config_unchanged": True,
            "environment_constructed": False,
            "native_module_imported": False,
            "output_absent": output_state == "absent",
            "production_checkpoint_inventory_unchanged": True,
            "registered_seed_consumed": False,
            "relevant_process_count": 0,
            "source_only_preflight_passed": True,
            "stale_execution_lease_recovered": stale_lease_recovered,
            "torch_imported": False,
            "training_started": False,
        },
        "logical_execution_id": identity["logical_execution_id"],
        "output_state": output_state,
        "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
        "schema_version": "noncombat-state-conditioned-source-only-preflight-v1",
        "source_commit": source_commit,
    }


def _validate_selection(value: object) -> dict[str, int]:
    selection = dict(_mapping(value, "cohort selection"))
    _require_keys(
        selection,
        {"canary_count", "holdout_count", "search_start", "train_count"},
        "cohort selection",
    )
    return {
        "canary_count": _positive_int(selection["canary_count"], "canary_count"),
        "holdout_count": _positive_int(selection["holdout_count"], "holdout_count"),
        "search_start": _nonnegative_int(selection["search_start"], "search_start"),
        "train_count": _positive_int(selection["train_count"], "train_count"),
    }


def materialize_fresh_cohorts(
    inventory: Mapping[str, Any], selection: Mapping[str, Any]
) -> dict[str, list[int]]:
    """Select the fixed ascending fresh train, canary, then holdout cohorts."""
    normalized_inventory = _validate_inventory(inventory)
    normalized_selection = _validate_selection(selection)
    excluded = set(normalized_inventory["excluded_seeds"])
    required = sum(
        normalized_selection[name]
        for name in ("train_count", "canary_count", "holdout_count")
    )
    selected: list[int] = []
    candidate = normalized_selection["search_start"]
    while len(selected) < required:
        if candidate not in excluded:
            selected.append(candidate)
        candidate += 1
    train_end = normalized_selection["train_count"]
    canary_end = train_end + normalized_selection["canary_count"]
    return {
        "train": selected[:train_end],
        "canary": selected[train_end:canary_end],
        "holdout": selected[canary_end:],
    }


def validate_fresh_cohorts(
    inventory: Mapping[str, Any],
    selection: Mapping[str, Any],
    cohorts: Mapping[str, Sequence[int]],
) -> dict[str, list[int]]:
    value = dict(_mapping(cohorts, "cohorts"))
    _require_keys(value, {"canary", "holdout", "train"}, "cohorts")
    normalized = {
        name: [
            _nonnegative_int(seed, f"{name} seed")
            for seed in _sequence(value[name], f"{name} seeds")
        ]
        for name in ("train", "canary", "holdout")
    }
    flattened = [seed for name in ("train", "canary", "holdout") for seed in normalized[name]]
    if len(flattened) != len(set(flattened)):
        raise ExperimentBlocked("cohort overlap is forbidden")
    expected = materialize_fresh_cohorts(inventory, selection)
    if normalized != expected:
        raise ExperimentBlocked("cohorts do not reproduce exact ascending selection")
    return normalized


def _reject_reference_policy_leakage(
    value: Any, label: str = "registration", *, allow_evidence: bool = True
) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            folded = str(key).casefold()
            if allow_evidence and folded in {
                "authority",
                "evidence",
                "historical_evidence",
            }:
                continue
            if any(name in folded for name in REFERENCE_POLICY_NAMES):
                raise ExperimentBlocked(f"reference policy field is forbidden at {label}.{key}")
            _reject_reference_policy_leakage(
                child, f"{label}.{key}", allow_evidence=allow_evidence
            )
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_reference_policy_leakage(
                child, f"{label}[{index}]", allow_evidence=allow_evidence
            )


def _validate_implementation(value: object) -> dict[str, Any]:
    implementation = dict(_mapping(value, "implementation"))
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "implementation",
    )
    implementation["commit"] = _validate_commit(
        implementation["commit"], "implementation commit"
    )
    if implementation["source_files"] != list(IMPLEMENTATION_SOURCE_FILES):
        raise ExperimentBlocked("implementation source file inventory mismatch")
    implementation["source_sha256"] = _validate_sha256(
        implementation["source_sha256"], "implementation source sha256"
    )
    return implementation


def _validate_runtime_identity(value: object) -> dict[str, str]:
    runtime = dict(_mapping(value, "runtime identity"))
    _require_keys(
        runtime,
        {"executable", "platform", "python_version", "torch_version"},
        "runtime identity",
    )
    runtime["executable"] = _canonical_windows_path(
        runtime["executable"], "runtime executable"
    )
    if runtime["platform"] != "win32":
        raise ExperimentBlocked("runtime platform must be win32")
    for name in ("python_version", "torch_version"):
        if not isinstance(runtime[name], str) or not runtime[name]:
            raise ExperimentBlocked(f"runtime {name} must be nonempty")
    return runtime


def _validate_native_identity(value: object) -> dict[str, Any]:
    native = dict(_mapping(value, "native identity"))
    _require_keys(
        native,
        {"dll_directories", "module", "simulator_repo"},
        "native identity",
    )
    directories = [
        _canonical_windows_path(path, "native DLL directory")
        for path in _sequence(native["dll_directories"], "native DLL directories")
    ]
    if directories != sorted(set(directories)):
        raise ExperimentBlocked("native DLL directories must be sorted and unique")
    native["dll_directories"] = directories
    native["module"] = _validate_external_binding(native["module"], "native module")
    native["simulator_repo"] = _canonical_windows_path(
        native["simulator_repo"], "simulator repository"
    )
    return native


def _validate_checkpoint_inventory(value: object) -> dict[str, Any]:
    inventory = dict(_mapping(value, "production checkpoint inventory"))
    _require_keys(
        inventory,
        {"entries", "inventory_sha256", "root", "total_bytes"},
        "production checkpoint inventory",
    )
    inventory["root"] = _canonical_windows_path(
        inventory["root"], "production checkpoint root"
    )
    entries = [
        _validate_binding(entry, f"production checkpoint[{index}]")
        for index, entry in enumerate(
            _sequence(inventory["entries"], "production checkpoint entries")
        )
    ]
    if entries != sorted(entries, key=lambda row: row["path"]) or len(
        {row["path"] for row in entries}
    ) != len(entries):
        raise ExperimentBlocked("production checkpoint entries are not canonical")
    expected_hash = hashlib.sha256(canonical_json_bytes(entries)).hexdigest()
    if inventory["inventory_sha256"] != expected_hash:
        raise ExperimentBlocked("production checkpoint inventory sha256 mismatch")
    total_bytes = sum(row["size_bytes"] for row in entries)
    if inventory["total_bytes"] != total_bytes:
        raise ExperimentBlocked("production checkpoint total bytes mismatch")
    inventory["entries"] = entries
    return inventory


def _validate_isolation_identity(value: object) -> dict[str, Any]:
    isolation = dict(_mapping(value, "isolation identity"))
    _require_keys(
        isolation,
        {"communication_mod_config", "production_checkpoints"},
        "isolation identity",
    )
    isolation["communication_mod_config"] = _validate_external_binding(
        isolation["communication_mod_config"], "CommunicationMod config"
    )
    isolation["production_checkpoints"] = _validate_checkpoint_inventory(
        isolation["production_checkpoints"]
    )
    return isolation


def _validate_identity(value: object) -> dict[str, Any]:
    identity = dict(_mapping(value, "registration identity"))
    _require_keys(
        identity,
        {
            "adapter_provenance",
            "evidence",
            "implementation",
            "isolation",
            "logical_execution_id",
            "native",
            "output_directory",
            "runtime",
            "seed_inventory_binding",
        },
        "registration identity",
    )
    execution_id = identity["logical_execution_id"]
    if not isinstance(execution_id, str) or not _EXECUTION_ID_RE.fullmatch(execution_id):
        raise ExperimentBlocked("logical execution id is invalid")
    output = _canonical_relative_path(identity["output_directory"], "output directory")
    if not output.startswith(OUTPUT_ROOT_PREFIX):
        raise ExperimentBlocked("output directory is outside the experiment root")
    try:
        from analysis_scripts.noncombat_simulator_adapter import validate_provenance

        identity["adapter_provenance"] = validate_provenance(
            identity["adapter_provenance"]
        )
    except Exception as exc:
        raise ExperimentBlocked(f"adapter provenance is invalid: {exc}") from exc
    evidence = dict(_mapping(identity["evidence"], "evidence bindings"))
    if not evidence:
        raise ExperimentBlocked("evidence bindings must be nonempty")
    identity["evidence"] = {
        name: _validate_binding(evidence[name], f"evidence.{name}")
        for name in sorted(evidence)
    }
    identity["implementation"] = _validate_implementation(
        identity["implementation"]
    )
    identity["isolation"] = _validate_isolation_identity(identity["isolation"])
    identity["native"] = _validate_native_identity(identity["native"])
    identity["runtime"] = _validate_runtime_identity(identity["runtime"])
    identity["seed_inventory_binding"] = _validate_binding(
        identity["seed_inventory_binding"], "seed inventory binding"
    )
    provenance = identity["adapter_provenance"]
    module = identity["native"]["module"]
    if (
        provenance["module_sha256"] != module["sha256"]
        or provenance["module_size_bytes"] != module["size_bytes"]
    ):
        raise ExperimentBlocked("native module and adapter provenance differ")
    if provenance["build"]["python"] != identity["runtime"]["python_version"]:
        raise ExperimentBlocked("adapter and runtime Python versions differ")
    _reject_reference_policy_leakage(identity, "registration.identity")
    identity["logical_execution_id"] = execution_id
    identity["output_directory"] = output
    return identity


def _validate_limits(value: object) -> dict[str, Any]:
    limits = dict(_mapping(value, "limits"))
    _require_keys(
        limits,
        {
            "bootstrap_resamples",
            "max_episodes",
            "max_wall_seconds",
            "train_passes",
            "training_chunk_size",
            "unsupported_rate_ceiling",
        },
        "limits",
    )
    ceiling = limits["unsupported_rate_ceiling"]
    if (
        isinstance(ceiling, bool)
        or not isinstance(ceiling, Real)
        or not math.isfinite(float(ceiling))
        or not 0.0 <= float(ceiling) < 1.0
    ):
        raise ExperimentBlocked("unsupported rate ceiling must be in [0, 1)")
    return {
        "bootstrap_resamples": _positive_int(
            limits["bootstrap_resamples"], "bootstrap resamples"
        ),
        "max_episodes": _positive_int(limits["max_episodes"], "max episodes"),
        "max_wall_seconds": _positive_float(limits["max_wall_seconds"], "max wall seconds"),
        "train_passes": _positive_int(limits["train_passes"], "train passes"),
        "training_chunk_size": _positive_int(limits["training_chunk_size"], "training chunk size"),
        "unsupported_rate_ceiling": float(ceiling),
    }


def build_source_only_registration(
    *,
    identity: Mapping[str, Any],
    inventory: Mapping[str, Any],
    selection: Mapping[str, Any],
    cohorts: Mapping[str, Sequence[int]],
    limits: Mapping[str, Any],
    behavior_gates: Mapping[str, Any],
) -> dict[str, Any]:
    value = {
        "authority": registration_authority(),
        "behavior_gates": copy.deepcopy(dict(behavior_gates)),
        "cohorts": copy.deepcopy(dict(cohorts)),
        "experiment": experiment_contract(),
        "identity": copy.deepcopy(dict(identity)),
        "limits": copy.deepcopy(dict(limits)),
        "schema_version": EXPERIMENT_SCHEMA_VERSION,
        "seed_inventory": copy.deepcopy(dict(inventory)),
        "selection": copy.deepcopy(dict(selection)),
    }
    return validate_registration(value)


def validate_registration(value: object) -> dict[str, Any]:
    registration = copy.deepcopy(dict(_mapping(value, "registration")))
    _reject_reference_policy_leakage(registration)
    _require_keys(
        registration,
        {
            "authority",
            "behavior_gates",
            "cohorts",
            "experiment",
            "identity",
            "limits",
            "schema_version",
            "seed_inventory",
            "selection",
        },
        "registration",
    )
    if registration["schema_version"] != EXPERIMENT_SCHEMA_VERSION:
        raise ExperimentBlocked("registration schema mismatch")
    if registration["authority"] != registration_authority():
        raise ExperimentBlocked("registration authority mismatch")
    if registration["experiment"] != experiment_contract():
        raise ExperimentBlocked("registration experiment contract drift")
    registration["identity"] = _validate_identity(registration["identity"])
    registration["seed_inventory"] = _validate_inventory(registration["seed_inventory"])
    registration["selection"] = _validate_selection(registration["selection"])
    registration["cohorts"] = validate_fresh_cohorts(
        registration["seed_inventory"],
        registration["selection"],
        registration["cohorts"],
    )
    registration["limits"] = _validate_limits(registration["limits"])
    registration["behavior_gates"] = _validate_behavior_gate_contract(
        registration["behavior_gates"]
    )
    inventory_bytes = canonical_json_bytes(registration["seed_inventory"])
    inventory_binding = registration["identity"]["seed_inventory_binding"]
    if (
        inventory_binding["sha256"] != hashlib.sha256(inventory_bytes).hexdigest()
        or inventory_binding["size_bytes"] != len(inventory_bytes)
    ):
        raise ExperimentBlocked("embedded seed inventory binding mismatch")
    expected_episodes = (
        len(registration["cohorts"]["train"])
        * registration["limits"]["train_passes"]
    )
    if registration["limits"]["max_episodes"] != expected_episodes:
        raise ExperimentBlocked("registered training episode count mismatch")
    if (
        registration["limits"]["training_chunk_size"]
        > len(registration["cohorts"]["train"])
    ):
        raise ExperimentBlocked("training chunk exceeds train cohort size")
    if (
        len(registration["cohorts"]["train"])
        % registration["limits"]["training_chunk_size"]
        != 0
    ):
        raise ExperimentBlocked("training chunk crosses a train pass boundary")
    return registration


def build_execution_authorization(
    *,
    registration_path: str,
    registration_bytes: bytes,
    registration_commit: str,
    logical_execution_id: str,
    output_directory: str,
    authorization_path: str | None = None,
    repo_root: Path | str = REPO_ROOT,
) -> dict[str, Any]:
    if not isinstance(registration_bytes, bytes) or not registration_bytes:
        raise ExperimentBlocked("registration bytes must be nonempty")
    registration = validate_registration(
        load_canonical_json_bytes(registration_bytes, "registration")
    )
    registration_relative = _canonical_relative_path(
        registration_path, "authorization registration path"
    )
    if authorization_path is None:
        if not registration_relative.endswith("_registration.json"):
            raise ExperimentBlocked("authorization registration path is outside the contract")
        authorization_path = (
            registration_relative.removesuffix("_registration.json")
            + "_authorization.json"
        )
    authorization_relative = _canonical_relative_path(
        authorization_path, "authorization artifact path"
    )
    if logical_execution_id != registration["identity"]["logical_execution_id"]:
        raise ExperimentBlocked("authorization logical execution id mismatch")
    if output_directory != registration["identity"]["output_directory"]:
        raise ExperimentBlocked("authorization output directory mismatch")
    value = {
        "authority": execution_authority(),
        "execution": _build_execution_binding(
            registration,
            repo_root=repo_root,
            registration_path=registration_relative,
            authorization_path=authorization_relative,
        ),
        "logical_execution_id": logical_execution_id,
        "output_directory": output_directory,
        "registration": {
            "commit": _validate_commit(
                registration_commit, "authorization registration commit"
            ),
            "path": registration_relative,
            "sha256": hashlib.sha256(registration_bytes).hexdigest(),
            "size_bytes": len(registration_bytes),
        },
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
    }
    return _validate_authorization_shape(value)


def _resolved_windows_path(path: Path | str, label: str) -> str:
    return _canonical_windows_path(Path(path).resolve().as_posix(), label)


def _build_execution_binding(
    registration: Mapping[str, Any],
    *,
    repo_root: Path | str,
    registration_path: str,
    authorization_path: str,
) -> dict[str, Any]:
    normalized = validate_registration(registration)
    root = Path(repo_root).resolve()
    root_text = _resolved_windows_path(root, "execution repository root")
    registration_relative = _canonical_relative_path(
        registration_path, "execution registration path"
    )
    authorization_relative = _canonical_relative_path(
        authorization_path, "execution authorization path"
    )
    identity = normalized["identity"]
    command = [
        identity["runtime"]["executable"],
        _resolved_windows_path(
            root / PurePosixPath(EXECUTION_SOURCE_PATH),
            "execution source path",
        ),
        "execute",
        "--repo-root",
        root_text,
        "--registration",
        _resolved_windows_path(
            root / PurePosixPath(registration_relative),
            "execution registration file",
        ),
        "--authorization",
        _resolved_windows_path(
            root / PurePosixPath(authorization_relative),
            "execution authorization file",
        ),
        "--output",
        _resolved_windows_path(
            root / PurePosixPath(identity["output_directory"]),
            "execution output directory",
        ),
    ]
    return {
        "authorization_path": authorization_relative,
        "cohorts_sha256": hashlib.sha256(
            canonical_json_bytes(normalized["cohorts"])
        ).hexdigest(),
        "command": command,
        "native_module": copy.deepcopy(identity["native"]["module"]),
        "one_logical_attempt": True,
        "repository_root": root_text,
        "resource_limits": copy.deepcopy(normalized["limits"]),
        "same_identity_checkpoint_resume_authorized": normalized["experiment"][
            "lifecycle"
        ]["same_identity_checkpoint_resume_authorized"],
    }


def _validate_authorization_shape(value: object) -> dict[str, Any]:
    authorization = copy.deepcopy(dict(_mapping(value, "authorization")))
    _require_keys(
        authorization,
        {
            "authority",
            "execution",
            "logical_execution_id",
            "output_directory",
            "registration",
            "schema_version",
        },
        "authorization",
    )
    if authorization["schema_version"] != AUTHORIZATION_SCHEMA_VERSION:
        raise ExperimentBlocked("authorization schema mismatch")
    if authorization["authority"] != execution_authority():
        raise ExperimentBlocked("authorization authority mismatch")
    execution = dict(_mapping(authorization["execution"], "authorization execution"))
    _require_keys(
        execution,
        {
            "authorization_path",
            "cohorts_sha256",
            "command",
            "native_module",
            "one_logical_attempt",
            "repository_root",
            "resource_limits",
            "same_identity_checkpoint_resume_authorized",
        },
        "authorization execution",
    )
    execution["authorization_path"] = _canonical_relative_path(
        execution["authorization_path"], "execution authorization path"
    )
    if not execution["authorization_path"].startswith(OUTPUT_ROOT_PREFIX) or not execution[
        "authorization_path"
    ].endswith("_authorization.json"):
        raise ExperimentBlocked("execution authorization path is outside the contract")
    execution["cohorts_sha256"] = _validate_sha256(
        execution["cohorts_sha256"], "execution cohorts sha256"
    )
    command = list(_sequence(execution["command"], "execution command"))
    if len(command) != 11 or any(not isinstance(item, str) or not item for item in command):
        raise ExperimentBlocked("execution command shape mismatch")
    for index in (0, 1, 4, 6, 8, 10):
        _canonical_windows_path(command[index], f"execution command[{index}]")
    execution["repository_root"] = _canonical_windows_path(
        execution["repository_root"], "execution repository root"
    )
    expected_command = [
        command[0],
        f"{execution['repository_root']}/{EXECUTION_SOURCE_PATH}",
        "execute",
        "--repo-root",
        execution["repository_root"],
        "--registration",
        f"{execution['repository_root']}/{authorization['registration']['path']}",
        "--authorization",
        f"{execution['repository_root']}/{execution['authorization_path']}",
        "--output",
        f"{execution['repository_root']}/{authorization['output_directory']}",
    ]
    if command != expected_command:
        raise ExperimentBlocked("execution command mismatch")
    execution["command"] = command
    execution["native_module"] = _validate_external_binding(
        execution["native_module"], "execution native module"
    )
    if execution["one_logical_attempt"] is not True:
        raise ExperimentBlocked("execution must authorize one logical attempt")
    execution["resource_limits"] = _validate_limits(execution["resource_limits"])
    if execution["same_identity_checkpoint_resume_authorized"] is not True:
        raise ExperimentBlocked("same-identity checkpoint resume is not authorized")
    authorization["execution"] = execution
    execution_id = authorization["logical_execution_id"]
    if not isinstance(execution_id, str) or not _EXECUTION_ID_RE.fullmatch(execution_id):
        raise ExperimentBlocked("authorization logical execution id is invalid")
    output = _canonical_relative_path(authorization["output_directory"], "authorization output")
    if not output.startswith(OUTPUT_ROOT_PREFIX):
        raise ExperimentBlocked("authorization output is outside the experiment root")
    binding = dict(_mapping(authorization["registration"], "authorization registration"))
    _require_keys(binding, {"commit", "path", "sha256", "size_bytes"}, "authorization registration")
    if not isinstance(binding["commit"], str) or not _COMMIT_RE.fullmatch(binding["commit"]):
        raise ExperimentBlocked("authorization registration commit is invalid")
    path = _canonical_relative_path(binding["path"], "authorization registration path")
    if not path.startswith(OUTPUT_ROOT_PREFIX) or not path.endswith("_registration.json"):
        raise ExperimentBlocked("authorization registration path is outside the contract")
    if not isinstance(binding["sha256"], str) or not _SHA256_RE.fullmatch(binding["sha256"]):
        raise ExperimentBlocked("authorization registration sha256 is invalid")
    binding["size_bytes"] = _positive_int(binding["size_bytes"], "authorization registration size")
    authorization["registration"] = binding
    return authorization


def validate_execution_authorization(
    value: object,
    *,
    registration: Mapping[str, Any],
    registration_bytes: bytes,
) -> dict[str, Any]:
    normalized_registration = validate_registration(registration)
    if canonical_json_bytes(normalized_registration) != registration_bytes:
        raise ExperimentBlocked("registration bytes are not canonical or exact")
    authorization = _validate_authorization_shape(value)
    binding = authorization["registration"]
    if binding["sha256"] != hashlib.sha256(registration_bytes).hexdigest():
        raise ExperimentBlocked("authorization registration sha256 mismatch")
    if binding["size_bytes"] != len(registration_bytes):
        raise ExperimentBlocked("authorization registration size mismatch")
    identity = normalized_registration["identity"]
    if authorization["logical_execution_id"] != identity["logical_execution_id"]:
        raise ExperimentBlocked("authorization logical execution id mismatch")
    if authorization["output_directory"] != identity["output_directory"]:
        raise ExperimentBlocked("authorization output directory mismatch")
    execution = authorization["execution"]
    if execution["cohorts_sha256"] != hashlib.sha256(
        canonical_json_bytes(normalized_registration["cohorts"])
    ).hexdigest():
        raise ExperimentBlocked("authorization cohort binding mismatch")
    if execution["native_module"] != identity["native"]["module"]:
        raise ExperimentBlocked("authorization native module mismatch")
    if execution["resource_limits"] != normalized_registration["limits"]:
        raise ExperimentBlocked("authorization resource limits mismatch")
    expected_execution = _build_execution_binding(
        normalized_registration,
        repo_root=execution["repository_root"],
        registration_path=binding["path"],
        authorization_path=execution["authorization_path"],
    )
    if execution != expected_execution:
        raise ExperimentBlocked("authorization execution binding mismatch")
    return authorization


def _normalize_actual_execution_command(
    actual_command: Sequence[str],
) -> list[str]:
    command = list(_sequence(actual_command, "actual execution command"))
    if len(command) != 11 or any(
        not isinstance(item, str) or not item for item in command
    ):
        raise ExperimentBlocked("actual execution command shape mismatch")
    if command[2] != "execute" or [command[index] for index in (3, 5, 7, 9)] != [
        "--repo-root",
        "--registration",
        "--authorization",
        "--output",
    ]:
        raise ExperimentBlocked("actual execution command flags mismatch")
    for index in (0, 1, 4, 6, 8, 10):
        command[index] = _resolved_windows_path(
            command[index], f"actual execution command[{index}]"
        )
    return command


def validate_actual_execution_command(
    authorization: Mapping[str, Any], actual_command: Sequence[str]
) -> list[str]:
    """Bind the running interpreter, module file, and argv to authorization."""
    normalized = _normalize_actual_execution_command(actual_command)
    execution = _mapping(
        _mapping(authorization, "authorization").get("execution"),
        "authorization execution",
    )
    expected = list(
        _sequence(execution.get("command"), "authorized execution command")
    )
    if len(expected) != 11:
        raise ExperimentBlocked("authorized execution command shape mismatch")
    for index in (0, 1, 4, 6, 8, 10):
        expected[index] = _resolved_windows_path(
            expected[index], f"authorized execution command[{index}]"
        )
    current_executable = _resolved_windows_path(
        sys.executable, "current runtime executable"
    )
    current_source = _resolved_windows_path(
        Path(__file__).resolve(), "current execution source"
    )
    if normalized[0] != current_executable:
        raise ExperimentBlocked("actual runtime executable mismatch")
    if normalized[1] != current_source or expected[1] != current_source:
        raise ExperimentBlocked("actual execution source mismatch")
    if normalized != expected:
        raise ExperimentBlocked("actual execution command differs from authorization")
    return normalized


def current_process_execution_command() -> list[str]:
    """Return the interpreter, real process entry point, and process argv."""
    if not sys.argv or not isinstance(sys.argv[0], str) or not sys.argv[0]:
        raise ExperimentBlocked("process entry point is unavailable")
    return [
        sys.executable,
        str(Path(sys.argv[0]).resolve()),
        *sys.argv[1:],
    ]


def consume_after_lease_acquisition_failure(
    output: Path | str,
    *,
    logical_execution_id: str,
    acquisition_error: BaseException,
) -> None:
    """Consume only while holding the lease after a failed initial acquire."""
    try:
        recover_stale_execution_lease(output, logical_execution_id)
    except ExperimentBlocked as active_exc:
        raise ExperimentBlocked(
            "execution lease is held by the active logical execution owner"
        ) from active_exc
    try:
        cleanup_lease = ExecutionLease.acquire(output, logical_execution_id)
    except BaseException as takeover_exc:
        raise ExperimentBlocked(
            "execution lease owner appeared before failed-start cleanup"
        ) from takeover_exc
    with cleanup_lease:
        consume_started_journal(
            output,
            logical_execution_id=logical_execution_id,
            reason=(
                "lease_acquisition_failed:"
                f"{type(acquisition_error).__name__}: {acquisition_error}"
            ),
        )
    raise ExperimentBlocked(
        "execution lease acquisition failed after identity consumption"
    ) from acquisition_error


def assert_output_read_allowed(output: Path | str, *, process_alive: bool) -> None:
    """Fail closed before any caller reads an active Windows output root."""
    Path(output)
    if type(process_alive) is not bool:
        raise ExperimentBlocked("process_alive must be boolean")
    if process_alive:
        raise ExperimentBlocked("active output root must not be read")


def _atomic_write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        raise ExperimentBlocked(f"artifact already exists: {path.name}")
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


def publish_terminal_bundle(
    output: Path | str, artifacts: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Atomically publish canonical JSON artifacts and a hash manifest."""
    directory = Path(output)
    if directory.exists() and any(directory.iterdir()):
        raise ExperimentBlocked("terminal output directory must be empty")
    directory.mkdir(parents=True, exist_ok=True)
    values = dict(_mapping(artifacts, "terminal artifacts"))
    if not values or "artifact_manifest.json" in values:
        raise ExperimentBlocked("terminal artifacts must be nonempty and exclude manifest")
    inventory = []
    for name in sorted(values):
        if PurePosixPath(name).name != name or not name.endswith(".json"):
            raise ExperimentBlocked("terminal artifact names must be flat JSON files")
        if name.casefold() in FULL_TERMINAL_ARTIFACT_CASEFOLDS:
            raise ExperimentBlocked(
                "generic terminal bundle cannot use a full-terminal artifact name"
            )
        payload = canonical_json_bytes(values[name])
        _atomic_write_once(directory / name, payload)
        inventory.append(
            {
                "path": name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    manifest = {
        "artifact_count": len(inventory),
        "artifacts": inventory,
        "authority": registration_authority(),
        "manifest_kind": "generic_bundle",
        "schema_version": MANIFEST_SCHEMA_VERSION,
    }
    _atomic_write_once(directory / "artifact_manifest.json", canonical_json_bytes(manifest))
    return manifest


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ExperimentBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ExperimentBlocked(f"non-finite JSON constant: {value}")


def load_canonical_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExperimentBlocked(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ExperimentBlocked(f"{label} must contain a JSON object")
    if canonical_json_bytes(value) != payload:
        raise ExperimentBlocked(f"{label} is not canonical JSON")
    return value


def _validate_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ExperimentBlocked(f"{label} must be lowercase sha256")
    return value


def _validate_commit(value: object, label: str) -> str:
    if not isinstance(value, str) or not _COMMIT_RE.fullmatch(value):
        raise ExperimentBlocked(f"{label} must be lowercase git commit hex")
    return value


def _validate_execution_id(value: object) -> str:
    if not isinstance(value, str) or not _EXECUTION_ID_RE.fullmatch(value):
        raise ExperimentBlocked("logical execution id is invalid")
    return value


def _encode_model_state(state: Mapping[str, Any]) -> dict[str, Any]:
    if not state:
        raise ExperimentBlocked("model state must be nonempty")
    return {name: _encode_tensor(state[name]) for name in sorted(state)}


def _decode_model_state(value: object, label: str) -> dict[str, Any]:
    state = dict(_mapping(value, label))
    if not state or any(not isinstance(name, str) or not name for name in state):
        raise ExperimentBlocked(f"{label} must be a nonempty named tensor mapping")
    return {
        name: decode_tensor(state[name], f"{label}.{name}") for name in sorted(state)
    }


def build_checkpoint_payload(
    runtime: TrainingRuntime,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
    previous_checkpoint_bytes: bytes | None,
    training_chunk: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one exact resumable checkpoint after a completed optimizer update."""
    _validate_runtime(runtime)
    registration_hash = _validate_sha256(
        registration_sha256, "registration sha256"
    )
    commit = _validate_commit(implementation_commit, "implementation commit")
    execution_id = _validate_execution_id(logical_execution_id)
    checkpoint_index = runtime.next_chunk_index
    if checkpoint_index <= 0:
        raise ExperimentBlocked("checkpoint requires a completed optimizer update")
    if previous_checkpoint_bytes is None:
        previous_hash = None
        if checkpoint_index != 1:
            raise ExperimentBlocked("noninitial checkpoint requires previous bytes")
    else:
        if not isinstance(previous_checkpoint_bytes, bytes) or not previous_checkpoint_bytes:
            raise ExperimentBlocked("previous checkpoint bytes must be nonempty")
        previous_hash = hashlib.sha256(previous_checkpoint_bytes).hexdigest()
        if checkpoint_index == 1:
            raise ExperimentBlocked("initial checkpoint cannot have a predecessor")
    initial_model = _encode_model_state(runtime.initial_model_state)
    value = {
        "checkpoint_index": checkpoint_index,
        "identity": {
            "implementation_commit": commit,
            "logical_execution_id": execution_id,
            "registration_sha256": registration_hash,
        },
        "initial_model_sha256": hashlib.sha256(
            canonical_json_bytes(initial_model)
        ).hexdigest(),
        "previous_checkpoint_sha256": previous_hash,
        "runtime": {
            "action_generator": _encode_tensor(runtime.action_generator.get_state()),
            "completed_episodes": runtime.completed_episodes,
            "cumulative_wall_seconds": runtime.cumulative_wall_seconds,
            "entropy_coefficient": runtime.entropy_coefficient,
            "gradient_norm_ceiling": runtime.gradient_norm_ceiling,
            "model": _encode_model_state(runtime.model.state_dict()),
            "next_chunk_index": runtime.next_chunk_index,
            "optimizer": encode_optimizer_state(runtime.optimizer),
            "optimizer_updates": runtime.optimizer_updates,
            "python_random": _encode_state_value(runtime.python_random.getstate()),
        },
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "training_chunk": copy.deepcopy(dict(training_chunk))
        if training_chunk is not None
        else None,
    }
    return validate_checkpoint_payload(
        value,
        registration_sha256=registration_hash,
        implementation_commit=commit,
        logical_execution_id=execution_id,
    )


def validate_checkpoint_payload(
    value: object,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> dict[str, Any]:
    checkpoint = copy.deepcopy(dict(_mapping(value, "checkpoint")))
    _require_keys(
        checkpoint,
        {
            "checkpoint_index",
            "identity",
            "initial_model_sha256",
            "previous_checkpoint_sha256",
            "runtime",
            "schema_version",
            "training_chunk",
        },
        "checkpoint",
    )
    if checkpoint["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
        raise ExperimentBlocked("checkpoint schema mismatch")
    checkpoint_index = _positive_int(
        checkpoint["checkpoint_index"], "checkpoint index"
    )
    identity = dict(_mapping(checkpoint["identity"], "checkpoint identity"))
    _require_keys(
        identity,
        {"implementation_commit", "logical_execution_id", "registration_sha256"},
        "checkpoint identity",
    )
    if identity != {
        "implementation_commit": _validate_commit(
            implementation_commit, "implementation commit"
        ),
        "logical_execution_id": _validate_execution_id(logical_execution_id),
        "registration_sha256": _validate_sha256(
            registration_sha256, "registration sha256"
        ),
    }:
        raise ExperimentBlocked("checkpoint identity mismatch")
    _validate_sha256(checkpoint["initial_model_sha256"], "initial model sha256")
    previous = checkpoint["previous_checkpoint_sha256"]
    if checkpoint_index == 1:
        if previous is not None:
            raise ExperimentBlocked("initial checkpoint predecessor must be null")
    else:
        _validate_sha256(previous, "previous checkpoint sha256")
    state = dict(_mapping(checkpoint["runtime"], "checkpoint runtime"))
    _require_keys(
        state,
        {
            "action_generator",
            "completed_episodes",
            "cumulative_wall_seconds",
            "entropy_coefficient",
            "gradient_norm_ceiling",
            "model",
            "next_chunk_index",
            "optimizer",
            "optimizer_updates",
            "python_random",
        },
        "checkpoint runtime",
    )
    if _positive_int(state["next_chunk_index"], "checkpoint next chunk") != checkpoint_index:
        raise ExperimentBlocked("checkpoint next chunk coordinate mismatch")
    if _positive_int(state["optimizer_updates"], "checkpoint optimizer updates") != checkpoint_index:
        raise ExperimentBlocked("checkpoint optimizer coordinate mismatch")
    _positive_int(state["completed_episodes"], "checkpoint completed episodes")
    elapsed = state["cumulative_wall_seconds"]
    if isinstance(elapsed, bool) or not isinstance(elapsed, Real) or not math.isfinite(float(elapsed)) or float(elapsed) < 0.0:
        raise ExperimentBlocked("checkpoint cumulative wall time is invalid")
    if state["entropy_coefficient"] != ENTROPY_COEFFICIENT:
        raise ExperimentBlocked("checkpoint entropy coefficient mismatch")
    if state["gradient_norm_ceiling"] != GRADIENT_NORM_CEILING:
        raise ExperimentBlocked("checkpoint gradient ceiling mismatch")
    _decode_model_state(state["model"], "checkpoint model")
    decode_optimizer_state(state["optimizer"])
    decode_tensor(state["action_generator"], "checkpoint action generator")
    _decode_state_value(state["python_random"], "checkpoint python random")
    training_chunk = checkpoint["training_chunk"]
    if training_chunk is not None:
        chunk = dict(_mapping(training_chunk, "checkpoint training chunk"))
        if chunk.get("chunk_index") != checkpoint_index - 1:
            raise ExperimentBlocked("checkpoint training chunk coordinate mismatch")
        if chunk.get("optimizer_update") != checkpoint_index:
            raise ExperimentBlocked("checkpoint optimizer update mismatch")
        _validate_json_value(chunk, "checkpoint training chunk")
    return checkpoint


def restore_training_runtime_from_checkpoint(
    checkpoint: Mapping[str, Any],
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> TrainingRuntime:
    normalized = validate_checkpoint_payload(
        checkpoint,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    runtime = initialize_training_runtime()
    initial_sha = hashlib.sha256(
        canonical_json_bytes(_encode_model_state(runtime.initial_model_state))
    ).hexdigest()
    if initial_sha != normalized["initial_model_sha256"]:
        raise ExperimentBlocked("checkpoint initial model identity mismatch")
    state = normalized["runtime"]
    decoded_model = _decode_model_state(state["model"], "checkpoint model")
    try:
        runtime.model.load_state_dict(decoded_model, strict=True)
        runtime.optimizer.load_state_dict(decode_optimizer_state(state["optimizer"]))
        runtime.action_generator.set_state(
            decode_tensor(state["action_generator"], "checkpoint action generator")
        )
        runtime.python_random.setstate(
            _decode_state_value(state["python_random"], "checkpoint python random")
        )
    except (KeyError, RuntimeError, TypeError, ValueError) as exc:
        raise ExperimentBlocked(f"checkpoint restore failed: {exc}") from exc
    runtime.next_chunk_index = int(state["next_chunk_index"])
    runtime.completed_episodes = int(state["completed_episodes"])
    runtime.optimizer_updates = int(state["optimizer_updates"])
    runtime.cumulative_wall_seconds = float(state["cumulative_wall_seconds"])
    _validate_runtime(runtime)
    return runtime


def publish_checkpoint(
    output: Path | str, checkpoint: Mapping[str, Any]
) -> Path:
    value = dict(_mapping(checkpoint, "checkpoint"))
    index = _positive_int(value.get("checkpoint_index"), "checkpoint index")
    directory = Path(output) / "checkpoints"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"checkpoint_{index:04d}.json"
    _atomic_write_once(path, canonical_json_bytes(value))
    return path


def validate_checkpoint_chain(
    output: Path | str,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> list[dict[str, Any]]:
    directory = Path(output) / "checkpoints"
    if not directory.is_dir():
        raise ExperimentBlocked("checkpoint directory is missing")
    paths = sorted(directory.glob("checkpoint_*.json"))
    actual_files = sorted(path.name for path in directory.iterdir() if path.is_file())
    if actual_files != [path.name for path in paths] or not paths:
        raise ExperimentBlocked("checkpoint directory contains partial or extra files")
    result = []
    previous_bytes: bytes | None = None
    for expected_index, path in enumerate(paths, start=1):
        if path.name != f"checkpoint_{expected_index:04d}.json":
            raise ExperimentBlocked("checkpoint indices are not contiguous")
        payload = path.read_bytes()
        value = load_canonical_json_bytes(payload, path.name)
        normalized = validate_checkpoint_payload(
            value,
            registration_sha256=registration_sha256,
            implementation_commit=implementation_commit,
            logical_execution_id=logical_execution_id,
        )
        expected_previous = (
            None
            if previous_bytes is None
            else hashlib.sha256(previous_bytes).hexdigest()
        )
        if normalized["previous_checkpoint_sha256"] != expected_previous:
            raise ExperimentBlocked("checkpoint predecessor hash mismatch")
        result.append(
            {
                "checkpoint_index": expected_index,
                "path": path.name,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
        previous_bytes = payload
    return result


def evaluate_frozen_policy(
    model: Any,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    deadline: float,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Greedily evaluate one frozen model with exact per-seed replay."""
    torch, _ = _torch_components()
    seed_values = tuple(
        _nonnegative_int(seed, "evaluation seed")
        for seed in _sequence(seeds, "evaluation seeds")
    )
    if not seed_values or len(set(seed_values)) != len(seed_values):
        raise ExperimentBlocked("evaluation seeds must be nonempty and unique")
    before = _model_state_bytes(model)
    was_training = bool(model.training)
    rows = []
    diagnostics = []
    replay_rows = []
    replay_diagnostics = []
    try:
        model.eval()
        with torch.no_grad():
            for seed in seed_values:
                first = rollout_episode(
                    model,
                    environment_factory=environment_factory,
                    seed=seed,
                    training=False,
                    action_generator=None,
                    deadline=deadline,
                    clock=clock,
                )
                replay = rollout_episode(
                    model,
                    environment_factory=environment_factory,
                    seed=seed,
                    training=False,
                    action_generator=None,
                    deadline=deadline,
                    clock=clock,
                )
                if canonical_json_bytes(first.summary) != canonical_json_bytes(replay.summary):
                    raise ExperimentBlocked(f"seed {seed} episode replay mismatch")
                if canonical_json_bytes(list(first.diagnostic_rows)) != canonical_json_bytes(list(replay.diagnostic_rows)):
                    raise ExperimentBlocked(f"seed {seed} diagnostic replay mismatch")
                rows.append(first.summary)
                diagnostics.extend(first.diagnostic_rows)
                replay_rows.append(replay.summary)
                replay_diagnostics.extend(replay.diagnostic_rows)
    finally:
        model.train(was_training)
    if _model_state_bytes(model) != before:
        raise ExperimentBlocked("frozen evaluation mutated model parameters")
    summary = summarize_experiment_diagnostics(diagnostics)
    return {
        "categories": sorted(
            {category for row in rows for category in row["categories"]}
        ),
        "diagnostic_rows": diagnostics,
        "diagnostics": summary,
        "episode_rows": rows,
        "replay_diagnostic_rows": replay_diagnostics,
        "replay_exact": True,
        "replay_episode_rows": replay_rows,
        "unsupported_episodes": sum(
            row["unsupported_reason"] is not None for row in rows
        ),
        "victories": sum(bool(row["victory"]) for row in rows),
    }


def _quantile(sorted_values: Sequence[float], probability: float) -> float:
    if not sorted_values:
        raise ExperimentBlocked("quantile values must be nonempty")
    position = (len(sorted_values) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(sorted_values[lower])
    weight = position - lower
    return float(sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight)


def paired_bootstrap_interval(
    differences: Sequence[float],
    *,
    seed: int,
    resamples: int,
    confidence: float = 0.95,
) -> dict[str, Any]:
    values = [float(value) for value in _sequence(differences, "differences")]
    if not values or any(not math.isfinite(value) for value in values):
        raise ExperimentBlocked("paired differences must be nonempty and finite")
    bootstrap_seed = _nonnegative_int(seed, "bootstrap seed")
    count = _positive_int(resamples, "bootstrap resamples")
    if not 0.0 < confidence < 1.0:
        raise ExperimentBlocked("bootstrap confidence must be between zero and one")
    generator = random.Random(bootstrap_seed)
    means = sorted(
        statistics.fmean(generator.choice(values) for _ in values)
        for _ in range(count)
    )
    alpha = (1.0 - confidence) / 2.0
    return {
        "confidence": confidence,
        "lower": _quantile(means, alpha),
        "mean": statistics.fmean(values),
        "resamples": count,
        "seed": bootstrap_seed,
        "upper": _quantile(means, 1.0 - alpha),
    }


def paired_policy_evaluation(
    initial_model: Any,
    trained_model: Any,
    *,
    environment_factory: Callable[[int], Any],
    seeds: Sequence[int],
    cohort: str,
    bootstrap_resamples: int,
    bootstrap_seed: int = MODEL_SEED,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    if cohort not in {"canary", "holdout"}:
        raise ExperimentBlocked("evaluation cohort must be canary or holdout")
    seed_values = tuple(
        _nonnegative_int(seed, "evaluation seed")
        for seed in _sequence(seeds, "evaluation seeds")
    )
    if not seed_values or len(set(seed_values)) != len(seed_values):
        raise ExperimentBlocked("evaluation seeds must be nonempty and unique")
    if deadline is None:
        started = float(clock())
        if not math.isfinite(started):
            raise ExperimentBlocked("evaluation wall clock must be finite")
        deadline = started + 28_800.0
    initial = evaluate_frozen_policy(
        initial_model,
        environment_factory=environment_factory,
        seeds=seed_values,
        deadline=deadline,
        clock=clock,
    )
    trained = evaluate_frozen_policy(
        trained_model,
        environment_factory=environment_factory,
        seeds=seed_values,
        deadline=deadline,
        clock=clock,
    )
    paired_rows = []
    for seed, initial_row, trained_row in zip(
        seed_values, initial["episode_rows"], trained["episode_rows"]
    ):
        initial_floor = float(initial_row["last_supported_floor"])
        trained_floor = float(trained_row["last_supported_floor"])
        paired_rows.append(
            {
                "floor_difference": trained_floor - initial_floor,
                "initial_floor": initial_floor,
                "initial_victory": bool(initial_row["victory"]),
                "seed": seed,
                "trained_floor": trained_floor,
                "trained_victory": bool(trained_row["victory"]),
                "victory_difference": int(trained_row["victory"])
                - int(initial_row["victory"]),
            }
        )
    denominator = 2 * len(seed_values)
    return {
        "cohort": cohort,
        "floor_difference_ci": paired_bootstrap_interval(
            [row["floor_difference"] for row in paired_rows],
            seed=bootstrap_seed,
            resamples=bootstrap_resamples,
        ),
        "initial": initial,
        "paired_rows": paired_rows,
        "schema_version": EVALUATION_SCHEMA_VERSION,
        "seeds": list(seed_values),
        "trained": trained,
        "unsupported_rate": (
            initial["unsupported_episodes"] + trained["unsupported_episodes"]
        )
        / denominator,
        "unsupported_rate_denominator": denominator,
    }


def classify_canary_evaluation(
    evaluation: Mapping[str, Any],
    *,
    gate_contract: Mapping[str, Any],
    unsupported_rate_ceiling: float,
) -> dict[str, Any]:
    value = dict(_mapping(evaluation, "canary evaluation"))
    if value.get("schema_version") != EVALUATION_SCHEMA_VERSION or value.get("cohort") != "canary":
        raise ExperimentBlocked("canary evaluation identity mismatch")
    ceiling = float(unsupported_rate_ceiling)
    if not 0.0 <= ceiling < 1.0:
        raise ExperimentBlocked("unsupported-rate ceiling must be in [0, 1)")
    blockers = []
    required = list(TARGET_CATEGORIES)
    for policy in ("initial", "trained"):
        policy_value = dict(_mapping(value.get(policy), f"{policy} evaluation"))
        if policy_value.get("categories") != required:
            blockers.append(f"{policy}_four_category_coverage")
        if policy_value.get("replay_exact") is not True:
            blockers.append(f"{policy}_replay_exact")
    if float(value.get("unsupported_rate")) > ceiling:
        blockers.append("unsupported_rate")
    if int(value["trained"]["victories"]) < int(value["initial"]["victories"]):
        blockers.append("trained_victory_noninferiority")
    if float(value["floor_difference_ci"]["lower"]) <= 0.0:
        blockers.append("paired_floor_lower_bound")
    behavior = classify_behavior_gates(
        value["trained"]["diagnostics"], gate_contract
    )
    blockers.extend(behavior["blockers"])
    blockers = list(dict.fromkeys(blockers))
    return {
        "behavior_gate": behavior,
        "blockers": blockers,
        "floor_difference_ci": value["floor_difference_ci"],
        "initial_victories": value["initial"]["victories"],
        "passed": not blockers,
        "trained_victories": value["trained"]["victories"],
        "unsupported_rate": value["unsupported_rate"],
        "verdict": "canary_passed" if not blockers else "experiment_stopped_at_canary",
    }


def run_conditional_evaluation(
    initial_model: Any,
    trained_model: Any,
    *,
    environment_factory: Callable[[int], Any],
    canary_seeds: Sequence[int],
    holdout_seeds: Sequence[int],
    gate_contract: Mapping[str, Any],
    unsupported_rate_ceiling: float,
    bootstrap_resamples: int,
    bootstrap_seed: int = MODEL_SEED,
    deadline: float | None = None,
    clock: Callable[[], float] = time.monotonic,
    on_canary_complete: Callable[[Mapping[str, Any]], None] | None = None,
    on_holdout_start: Callable[[], None] | None = None,
    on_holdout_complete: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if deadline is None:
        started = float(clock())
        if not math.isfinite(started):
            raise ExperimentBlocked("evaluation wall clock must be finite")
        deadline = started + 28_800.0
    canary = paired_policy_evaluation(
        initial_model,
        trained_model,
        environment_factory=environment_factory,
        seeds=canary_seeds,
        cohort="canary",
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        deadline=deadline,
        clock=clock,
    )
    canary_gate = classify_canary_evaluation(
        canary,
        gate_contract=gate_contract,
        unsupported_rate_ceiling=unsupported_rate_ceiling,
    )
    canary_result = {
        "canary": canary,
        "canary_gate": canary_gate,
        "holdout": {"accessed": False, "episode_count": 0},
        "verdict": (
            "canary_passed_pending_holdout"
            if canary_gate["passed"]
            else "experiment_stopped_at_canary"
        ),
    }
    if on_canary_complete is not None:
        on_canary_complete(canary_result)
    if not canary_gate["passed"]:
        return canary_result
    _check_deadline(deadline, clock)
    if on_holdout_start is not None:
        on_holdout_start()
    holdout_seed_values = tuple(
        _nonnegative_int(seed, "holdout seed")
        for seed in _sequence(holdout_seeds, "holdout seeds")
    )
    holdout = paired_policy_evaluation(
        initial_model,
        trained_model,
        environment_factory=environment_factory,
        seeds=holdout_seed_values,
        cohort="holdout",
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        deadline=deadline,
        clock=clock,
    )
    behavior = classify_behavior_gates(
        holdout["trained"]["diagnostics"], gate_contract
    )
    terminal = classify_terminal_verdict(
        complete=True,
        structural_valid=(
            holdout["initial"]["replay_exact"] is True
            and holdout["trained"]["replay_exact"] is True
            and holdout["initial"]["categories"] == list(TARGET_CATEGORIES)
            and holdout["trained"]["categories"] == list(TARGET_CATEGORIES)
            and holdout["unsupported_rate"] <= unsupported_rate_ceiling
        ),
        behavior_valid=(
            behavior["passed"]
            and holdout["trained"]["victories"]
            >= holdout["initial"]["victories"]
        ),
        floor_signal=holdout["floor_difference_ci"]["lower"] > 0.0,
        initial_victories=holdout["initial"]["victories"],
        trained_victories=holdout["trained"]["victories"],
    )
    result = {
        "canary": canary,
        "canary_gate": canary_gate,
        "holdout": {
            "accessed": True,
            "behavior_gate": behavior,
            "episode_count": 4 * len(holdout_seed_values),
            "evaluation": holdout,
        },
        "verdict": terminal["verdict"],
    }
    if on_holdout_complete is not None:
        on_holdout_complete(result)
    return result


JOURNAL_SCHEMA_VERSION = (
    "noncombat-state-conditioned-simulator-learning-journal-v2"
)
LEASE_SCHEMA_VERSION = "noncombat-state-conditioned-simulator-learning-lease-v1"


def _atomic_replace(path: Path, payload: bytes) -> None:
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


def initialize_experiment_output(
    output: Path | str,
    *,
    registration_bytes: bytes,
    authorization_bytes: bytes,
    repo_root: Path | str = REPO_ROOT,
    acquire_execution_lease: bool = False,
) -> Any:
    """Create controls and the durable started journal before seed access."""
    if type(acquire_execution_lease) is not bool:
        raise ExperimentBlocked("acquire_execution_lease must be boolean")
    directory = Path(output)
    if directory.exists():
        raise ExperimentBlocked("experiment output already exists")
    registration = validate_registration(
        load_canonical_json_bytes(registration_bytes, "registration")
    )
    authorization = validate_execution_authorization(
        load_canonical_json_bytes(authorization_bytes, "authorization"),
        registration=registration,
        registration_bytes=registration_bytes,
    )
    expected = Path(repo_root).resolve() / PurePosixPath(
        authorization["output_directory"]
    )
    if directory.resolve() != expected.resolve():
        raise ExperimentBlocked("experiment output path differs from authorization")
    directory.mkdir(parents=True)
    journal_path = directory / "execution_journal.json"
    execution_lease: ExecutionLease | None = None
    try:
        if acquire_execution_lease:
            execution_lease = ExecutionLease.acquire(
                directory, authorization["logical_execution_id"]
            )
        _atomic_write_once(directory / "registration.json", registration_bytes)
        _atomic_write_once(directory / "authorization.json", authorization_bytes)
        configuration = _initial_configuration(
            registration,
            registration_bytes=registration_bytes,
            authorization_bytes=authorization_bytes,
        )
        _atomic_write_once(
            directory / "configuration.json", canonical_json_bytes(configuration)
        )
        (directory / "checkpoints").mkdir()
        journal = _started_journal(authorization["logical_execution_id"])
        _atomic_write_once(
            journal_path, canonical_json_bytes(journal)
        )
    except BaseException:
        if execution_lease is not None:
            try:
                execution_lease.release()
            except BaseException:
                pass
        if not acquire_execution_lease and not journal_path.exists():
            for name in (
                "authorization.json",
                "configuration.json",
                "registration.json",
            ):
                try:
                    (directory / name).unlink(missing_ok=True)
                except OSError:
                    pass
            try:
                (directory / "checkpoints").rmdir()
            except OSError:
                pass
            try:
                directory.rmdir()
            except OSError:
                pass
        elif acquire_execution_lease and execution_lease is None:
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    if execution_lease is not None:
        return journal, execution_lease
    return journal


def validate_journal(
    value: object, *, logical_execution_id: str
) -> dict[str, Any]:
    journal = copy.deepcopy(dict(_mapping(value, "execution journal")))
    _require_keys(
        journal,
        {"logical_execution_id", "records", "schema_version", "state"},
        "execution journal",
    )
    if journal["schema_version"] != JOURNAL_SCHEMA_VERSION:
        raise ExperimentBlocked("execution journal schema mismatch")
    if journal["logical_execution_id"] != _validate_execution_id(
        logical_execution_id
    ):
        raise ExperimentBlocked("execution journal identity mismatch")
    records = list(_sequence(journal["records"], "journal records"))
    if not records:
        raise ExperimentBlocked("execution journal records must be nonempty")
    previous_checkpoint = 0
    previous_episodes = 0
    previous_state: str | None = None
    terminal_seen = False
    normalized = []
    for index, raw in enumerate(records):
        record = dict(_mapping(raw, f"journal record[{index}]"))
        state = record.get("state")
        expected_keys = {
            "checkpoint_index",
            "completed_episodes",
            "sequence",
            "state",
        }
        if state == "checkpoint":
            expected_keys.add("checkpoint_sha256")
        elif state == "operation":
            expected_keys.add("operation")
        elif state == "evidence":
            expected_keys.update({"name", "payload", "payload_sha256"})
        elif state == "terminal":
            expected_keys.add("reason")
        _require_keys(record, expected_keys, f"journal record[{index}]")
        if record["sequence"] != index:
            raise ExperimentBlocked("journal sequence is not contiguous")
        checkpoint_index = _nonnegative_int(
            record["checkpoint_index"], "journal checkpoint index"
        )
        completed = _nonnegative_int(
            record["completed_episodes"], "journal completed episodes"
        )
        if state not in {"checkpoint", "evidence", "operation", "started", "terminal"}:
            raise ExperimentBlocked("journal state is invalid")
        if index == 0:
            if state != "started" or checkpoint_index != 0 or completed != 0:
                raise ExperimentBlocked("journal must start at the zero coordinate")
        elif state == "started":
            raise ExperimentBlocked("journal has a noninitial started record")
        elif state == "checkpoint":
            if (
                checkpoint_index != previous_checkpoint + 1
                or completed <= previous_episodes
            ):
                raise ExperimentBlocked("journal checkpoint sequence is not exact")
            record["checkpoint_sha256"] = _validate_sha256(
                record["checkpoint_sha256"], "journal checkpoint sha256"
            )
        else:
            if (
                checkpoint_index != previous_checkpoint
                or completed != previous_episodes
            ):
                raise ExperimentBlocked(f"journal {state} coordinate mismatch")
            if state == "operation":
                operation = record["operation"]
                if not isinstance(operation, str) or not (
                    re.fullmatch(r"training_chunk:[0-9]+", operation)
                    or operation in {"evaluation:canary", "evaluation:holdout"}
                ):
                    raise ExperimentBlocked("journal operation is invalid")
            elif state == "evidence":
                name = record["name"]
                if name not in {"canary_evaluation", "complete_evaluation"}:
                    raise ExperimentBlocked("journal evidence name is invalid")
                payload = dict(_mapping(record["payload"], "journal evidence payload"))
                payload_sha256 = _validate_sha256(
                    record["payload_sha256"], "journal evidence sha256"
                )
                if hashlib.sha256(canonical_json_bytes(payload)).hexdigest() != payload_sha256:
                    raise ExperimentBlocked("journal evidence sha256 mismatch")
                if previous_state != "operation":
                    raise ExperimentBlocked("journal evidence lacks a preceding operation")
                record["payload"] = payload
            elif state == "terminal":
                reason = record["reason"]
                if not isinstance(reason, str) or not reason:
                    raise ExperimentBlocked("journal terminal reason is invalid")
        if terminal_seen:
            raise ExperimentBlocked("journal has records after terminal")
        terminal_seen = state == "terminal"
        previous_checkpoint = checkpoint_index
        previous_episodes = completed
        previous_state = state
        normalized.append(record)
    expected_state = "terminal" if terminal_seen else "started"
    if journal["state"] != expected_state:
        raise ExperimentBlocked("journal terminal state mismatch")
    journal["records"] = normalized
    return journal


def validate_nonterminal_resume_coordinates(
    output: Path | str,
    *,
    journal: Mapping[str, Any],
    checkpoint_names: Sequence[str],
    registration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Allow only the one atomic checkpoint-before-journal crash boundary."""
    normalized_journal = validate_journal(
        journal,
        logical_execution_id=str(journal.get("logical_execution_id")),
    )
    if normalized_journal["state"] != "started":
        raise ExperimentBlocked("resume journal must be nonterminal")
    names = list(_sequence(checkpoint_names, "resume checkpoint names"))
    if names != [f"checkpoint_{index:04d}.json" for index in range(1, len(names) + 1)]:
        raise ExperimentBlocked("resume checkpoint names are not contiguous")
    normalized_registration = (
        validate_registration(registration) if registration is not None else None
    )
    coordinates = []
    checkpoint_dir = Path(output) / "checkpoints"
    previous_completed = 0
    previous_checkpoint_bytes: bytes | None = None
    initial_model_sha256: str | None = None
    registration_sha256 = (
        hashlib.sha256(canonical_json_bytes(normalized_registration)).hexdigest()
        if normalized_registration is not None
        else None
    )
    for index, name in enumerate(names, start=1):
        checkpoint_bytes = (checkpoint_dir / name).read_bytes()
        checkpoint = load_canonical_json_bytes(checkpoint_bytes, name)
        if normalized_registration is not None:
            _require_keys(
                checkpoint,
                {
                    "checkpoint_index",
                    "identity",
                    "initial_model_sha256",
                    "previous_checkpoint_sha256",
                    "runtime",
                    "schema_version",
                    "training_chunk",
                },
                f"resume checkpoint[{index}]",
            )
            if checkpoint["schema_version"] != CHECKPOINT_SCHEMA_VERSION:
                raise ExperimentBlocked("resume checkpoint schema mismatch")
            expected_identity = {
                "implementation_commit": normalized_registration["identity"][
                    "implementation"
                ]["commit"],
                "logical_execution_id": normalized_registration["identity"][
                    "logical_execution_id"
                ],
                "registration_sha256": registration_sha256,
            }
            if checkpoint["identity"] != expected_identity:
                raise ExperimentBlocked("resume checkpoint identity mismatch")
            current_initial_sha256 = _validate_sha256(
                checkpoint["initial_model_sha256"],
                "resume checkpoint initial model sha256",
            )
            if initial_model_sha256 is None:
                initial_model_sha256 = current_initial_sha256
            elif initial_model_sha256 != current_initial_sha256:
                raise ExperimentBlocked("resume checkpoint initial model drifted")
            expected_previous_sha256 = (
                None
                if previous_checkpoint_bytes is None
                else hashlib.sha256(previous_checkpoint_bytes).hexdigest()
            )
            if checkpoint["previous_checkpoint_sha256"] != expected_previous_sha256:
                raise ExperimentBlocked("resume checkpoint predecessor hash mismatch")
        runtime = dict(
            _mapping(checkpoint.get("runtime"), f"resume checkpoint[{index}].runtime")
        )
        if normalized_registration is not None:
            _require_keys(
                runtime,
                {
                    "action_generator",
                    "completed_episodes",
                    "cumulative_wall_seconds",
                    "entropy_coefficient",
                    "gradient_norm_ceiling",
                    "model",
                    "next_chunk_index",
                    "optimizer",
                    "optimizer_updates",
                    "python_random",
                },
                f"resume checkpoint[{index}].runtime",
            )
            if (
                _positive_int(
                    runtime["optimizer_updates"],
                    f"resume checkpoint[{index}].optimizer_updates",
                )
                != index
                or runtime["entropy_coefficient"] != ENTROPY_COEFFICIENT
                or runtime["gradient_norm_ceiling"] != GRADIENT_NORM_CEILING
            ):
                raise ExperimentBlocked("resume checkpoint runtime controls drifted")
        completed = _positive_int(
            runtime.get("completed_episodes"),
            f"resume checkpoint[{index}].completed_episodes",
        )
        if (
            _positive_int(checkpoint.get("checkpoint_index"), "resume checkpoint index")
            != index
            or _positive_int(
                runtime.get("next_chunk_index"),
                f"resume checkpoint[{index}].next_chunk_index",
            )
            != index
            or completed <= previous_completed
        ):
            raise ExperimentBlocked("resume checkpoint coordinates are not exact")
        if normalized_registration is not None:
            expected = registered_training_coordinates(
                normalized_registration, index - 1
            )
            chunk = dict(
                _mapping(
                    checkpoint.get("training_chunk"),
                    f"resume checkpoint[{index}].training_chunk",
                )
            )
            if (
                completed != expected["episode_end"]
                or chunk.get("chunk_index") != expected["chunk_index"]
                or chunk.get("episode_start") != expected["episode_start"]
                or chunk.get("episode_end") != expected["episode_end"]
                or chunk.get("pass_index") != expected["pass_index"]
            ):
                raise ExperimentBlocked(
                    "resume checkpoint differs from registered training coordinates"
                )
        coordinates.append(
            {
                "checkpoint_index": index,
                "completed_episodes": completed,
                "sha256": hashlib.sha256(checkpoint_bytes).hexdigest(),
            }
        )
        previous_completed = completed
        previous_checkpoint_bytes = checkpoint_bytes

    journal_records = normalized_journal["records"]
    checkpoint_records = [
        record for record in journal_records if record["state"] == "checkpoint"
    ]
    journal_checkpoint_count = len(checkpoint_records)
    if len(names) - journal_checkpoint_count not in {0, 1}:
        raise ExperimentBlocked("resume journal/checkpoint gap is not recoverable")
    for index, record in enumerate(checkpoint_records, start=1):
        coordinate = coordinates[index - 1]
        if (
            record["checkpoint_index"] != coordinate["checkpoint_index"]
            or record["completed_episodes"] != coordinate["completed_episodes"]
            or record["checkpoint_sha256"] != coordinate["sha256"]
        ):
            raise ExperimentBlocked("resume journal/checkpoint coordinates differ")
    pending = len(names) == journal_checkpoint_count + 1
    last_record = journal_records[-1]
    if pending:
        expected_operation = f"training_chunk:{journal_checkpoint_count}"
        if (
            last_record["state"] != "operation"
            or last_record["operation"] != expected_operation
        ):
            raise ExperimentBlocked("pending checkpoint lacks its started operation")
    elif last_record["state"] in {"evidence", "operation"}:
        raise ExperimentBlocked("started operation consumed the logical execution")
    return {
        "checkpoint_count": len(names),
        "journal_checkpoint_count": journal_checkpoint_count,
        "pending_completed_episodes": (
            coordinates[-1]["completed_episodes"] if pending else None
        ),
        "pending_checkpoint_sha256": coordinates[-1]["sha256"] if pending else None,
        "pending_journal_append": pending,
    }


def append_journal_record(
    output: Path | str,
    *,
    logical_execution_id: str,
    state: str,
    checkpoint_index: int,
    completed_episodes: int,
    checkpoint_sha256: str | None = None,
    operation: str | None = None,
    evidence_name: str | None = None,
    evidence: Mapping[str, Any] | None = None,
    terminal_reason: str | None = None,
) -> dict[str, Any]:
    path = Path(output) / "execution_journal.json"
    journal = validate_journal(
        load_canonical_json_bytes(path.read_bytes(), "execution journal"),
        logical_execution_id=logical_execution_id,
    )
    if journal["state"] == "terminal":
        raise ExperimentBlocked("cannot append after terminal journal state")
    if state not in {"checkpoint", "evidence", "operation", "terminal"}:
        raise ExperimentBlocked("journal append state is invalid")
    record = {
        "checkpoint_index": _nonnegative_int(
            checkpoint_index, "journal checkpoint index"
        ),
        "completed_episodes": _nonnegative_int(
            completed_episodes, "journal completed episodes"
        ),
        "sequence": len(journal["records"]),
        "state": state,
    }
    if state == "checkpoint":
        if checkpoint_sha256 is None:
            checkpoint_path = (
                Path(output)
                / "checkpoints"
                / f"checkpoint_{record['checkpoint_index']:04d}.json"
            )
            checkpoint_sha256 = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
        record["checkpoint_sha256"] = _validate_sha256(
            checkpoint_sha256, "journal checkpoint sha256"
        )
    elif state == "operation":
        record["operation"] = operation
    elif state == "evidence":
        payload = copy.deepcopy(dict(_mapping(evidence, "journal evidence")))
        record.update(
            {
                "name": evidence_name,
                "payload": payload,
                "payload_sha256": hashlib.sha256(
                    canonical_json_bytes(payload)
                ).hexdigest(),
            }
        )
    else:
        record["reason"] = terminal_reason or "completed"
    journal["records"].append(record)
    if state == "terminal":
        journal["state"] = "terminal"
    normalized = validate_journal(
        journal, logical_execution_id=logical_execution_id
    )
    _atomic_replace(path, canonical_json_bytes(normalized))
    return normalized


def consume_started_journal(
    output: Path | str, *, logical_execution_id: str, reason: str
) -> dict[str, Any]:
    """Durably consume a started identity when no full terminal can be built."""
    path = Path(output) / "execution_journal.json"
    journal = validate_journal(
        load_canonical_json_bytes(path.read_bytes(), "execution journal"),
        logical_execution_id=logical_execution_id,
    )
    if journal["state"] == "terminal":
        return journal
    last = journal["records"][-1]
    return append_journal_record(
        output,
        logical_execution_id=logical_execution_id,
        state="terminal",
        checkpoint_index=last["checkpoint_index"],
        completed_episodes=last["completed_episodes"],
        terminal_reason=reason,
    )


def reconcile_pending_checkpoint_journal(
    output: Path | str,
    *,
    registration: Mapping[str, Any],
    logical_execution_id: str,
) -> bool:
    """Finish only the checkpoint-before-journal atomic crash boundary."""
    directory = Path(output)
    journal = validate_journal(
        load_canonical_json_bytes(
            (directory / "execution_journal.json").read_bytes(),
            "execution journal",
        ),
        logical_execution_id=logical_execution_id,
    )
    checkpoint_names = sorted(
        path.name for path in (directory / "checkpoints").glob("checkpoint_*.json")
    )
    coordinates = validate_nonterminal_resume_coordinates(
        directory,
        journal=journal,
        checkpoint_names=checkpoint_names,
        registration=registration,
    )
    if not coordinates["pending_journal_append"]:
        return False
    append_journal_record(
        directory,
        logical_execution_id=logical_execution_id,
        state="checkpoint",
        checkpoint_index=coordinates["checkpoint_count"],
        completed_episodes=coordinates["pending_completed_episodes"],
        checkpoint_sha256=coordinates["pending_checkpoint_sha256"],
    )
    return True


@dataclass
class ExecutionLease:
    path: Path
    logical_execution_id: str
    handle: Any
    released: bool = False

    @classmethod
    def acquire(
        cls, output: Path | str, logical_execution_id: str
    ) -> "ExecutionLease":
        execution_id = _validate_execution_id(logical_execution_id)
        path = Path(output) / ".execution.lease"
        payload = canonical_json_bytes(
            {
                "logical_execution_id": execution_id,
                "process_id": os.getpid(),
                "schema_version": LEASE_SCHEMA_VERSION,
            }
        )
        handle = path.open("a+b")
        try:
            _lock_execution_lease(handle)
            handle.seek(0)
            handle.truncate()
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException as exc:
            handle.close()
            raise ExperimentBlocked("execution lease is already held") from exc
        return cls(
            path=path,
            logical_execution_id=execution_id,
            handle=handle,
        )

    def __enter__(self) -> "ExecutionLease":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.release()

    def release(self) -> None:
        if self.released:
            return
        try:
            self.handle.seek(0)
            payload = load_canonical_json_bytes(
                self.handle.read(), "execution lease"
            )
            if (
                payload.get("schema_version") != LEASE_SCHEMA_VERSION
                or payload.get("logical_execution_id") != self.logical_execution_id
                or payload.get("process_id") != os.getpid()
            ):
                raise ExperimentBlocked("execution lease identity drifted")
        finally:
            try:
                _unlock_execution_lease(self.handle)
            finally:
                self.handle.close()
                self.released = True


def registered_training_coordinates(
    registration: Mapping[str, Any], chunk_index: int
) -> dict[str, Any]:
    value = validate_registration(registration)
    index = _nonnegative_int(chunk_index, "chunk index")
    train = list(value["cohorts"]["train"])
    passes = value["limits"]["train_passes"]
    sequence = train * passes
    chunk_size = value["limits"]["training_chunk_size"]
    start = index * chunk_size
    if start >= len(sequence):
        raise ExperimentBlocked("chunk index is outside registered training coordinates")
    seeds = sequence[start : start + chunk_size]
    return {
        "chunk_index": index,
        "episode_end": start + len(seeds),
        "episode_start": start,
        "pass_index": start // len(train),
        "seeds": tuple(seeds),
    }


def registered_training_chunk_count(registration: Mapping[str, Any]) -> int:
    value = validate_registration(registration)
    episodes = value["limits"]["max_episodes"]
    chunk_size = value["limits"]["training_chunk_size"]
    return math.ceil(episodes / chunk_size)


def resume_training_runtime_from_output(
    output: Path | str,
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> tuple[TrainingRuntime, bytes]:
    checkpoint_names = sorted(
        path.name
        for path in (Path(output) / "checkpoints").glob("checkpoint_*.json")
    )
    journal = validate_journal(
        load_canonical_json_bytes(
            (Path(output) / "execution_journal.json").read_bytes(),
            "execution journal",
        ),
        logical_execution_id=logical_execution_id,
    )
    resume_coordinates = validate_nonterminal_resume_coordinates(
        output,
        journal=journal,
        checkpoint_names=checkpoint_names,
        registration=registration,
    )
    chain = validate_checkpoint_chain(
        output,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    latest_path = Path(output) / "checkpoints" / chain[-1]["path"]
    payload = latest_path.read_bytes()
    runtime = restore_training_runtime_from_checkpoint(
        load_canonical_json_bytes(payload, latest_path.name),
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    if resume_coordinates["pending_journal_append"]:
        append_journal_record(
            output,
            logical_execution_id=logical_execution_id,
            state="checkpoint",
            checkpoint_index=runtime.next_chunk_index,
            completed_episodes=runtime.completed_episodes,
            checkpoint_sha256=resume_coordinates["pending_checkpoint_sha256"],
        )
    return runtime, payload


def _checkpoint_values_for_terminal(
    output: Path,
    *,
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> list[dict[str, Any]]:
    checkpoint_dir = output / "checkpoints"
    if not checkpoint_dir.is_dir():
        raise ExperimentBlocked("checkpoint directory is missing")
    files = sorted(checkpoint_dir.glob("checkpoint_*.json"))
    if not files:
        return []
    validate_checkpoint_chain(
        output,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )
    return [
        load_canonical_json_bytes(path.read_bytes(), path.name) for path in files
    ]


def _terminal_inventory(output: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(
        (
            candidate
            for candidate in output.rglob("*")
            if candidate.is_file()
            and candidate.name not in {".execution.lease", "artifact_manifest.json"}
            and not candidate.name.endswith(".tmp")
        ),
        key=lambda candidate: candidate.relative_to(output).as_posix(),
    ):
        payload = path.read_bytes()
        rows.append(
            {
                "path": path.relative_to(output).as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    return rows


def publish_experiment_terminal(
    output: Path | str,
    *,
    runtime: TrainingRuntime,
    evaluation: Mapping[str, Any] | None = None,
    blocked_reason: str | None = None,
    isolation_post: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Publish the terminal evidence for one consumed logical identity."""
    directory = Path(output)
    registration, registration_bytes, authorization, _ = _load_control_files(
        directory / "registration.json", directory / "authorization.json"
    )
    identity = registration["identity"]
    execution_id = identity["logical_execution_id"]
    registration_sha256 = hashlib.sha256(registration_bytes).hexdigest()
    implementation_commit = identity["implementation"]["commit"]
    _validate_runtime(runtime)
    checkpoints = _checkpoint_values_for_terminal(
        directory,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=execution_id,
    )
    if checkpoints:
        latest_runtime = checkpoints[-1]["runtime"]
        if (
            latest_runtime["next_chunk_index"] != runtime.next_chunk_index
            or latest_runtime["completed_episodes"] != runtime.completed_episodes
        ):
            raise ExperimentBlocked("terminal runtime is ahead of durable checkpoint")
    elif runtime.next_chunk_index != 0 or runtime.completed_episodes != 0:
        raise ExperimentBlocked("terminal runtime has uncheckpointed training")
    training_chunks = [
        checkpoint["training_chunk"]
        for checkpoint in checkpoints
        if checkpoint["training_chunk"] is not None
    ]
    training_episode_rows = [
        row for chunk in training_chunks for row in chunk["episode_rows"]
    ]
    training_diagnostic_rows = [
        row for chunk in training_chunks for row in chunk["diagnostic_rows"]
    ]
    training_diagnostics = (
        summarize_experiment_diagnostics(training_diagnostic_rows)
        if training_diagnostic_rows
        else None
    )
    normalized_evaluation = copy.deepcopy(dict(evaluation)) if evaluation is not None else None
    if blocked_reason is not None and (
        not isinstance(blocked_reason, str) or not blocked_reason
    ):
        raise ExperimentBlocked("blocked reason must be a nonempty string")

    if isolation_post is None:
        post = {
            "communication_mod_config": external_file_binding(
                identity["isolation"]["communication_mod_config"]["path"]
            ),
            "production_checkpoints": snapshot_production_checkpoints(
                identity["isolation"]["production_checkpoints"]["root"]
            ),
        }
    else:
        post = copy.deepcopy(dict(_mapping(isolation_post, "post isolation")))
        _require_keys(
            post,
            {"communication_mod_config", "production_checkpoints"},
            "post isolation",
        )
        post["communication_mod_config"] = _validate_external_binding(
            post["communication_mod_config"], "post CommunicationMod config"
        )
        post["production_checkpoints"] = _validate_checkpoint_inventory(
            post["production_checkpoints"]
        )
    isolation_unchanged = post == identity["isolation"]
    if not isolation_unchanged:
        verdict = "experiment_invalid"
    elif blocked_reason is not None:
        verdict = "experiment_blocked"
    elif normalized_evaluation is None:
        verdict = "experiment_invalid"
    else:
        verdict = str(normalized_evaluation.get("verdict"))
        if verdict not in {
            "experiment_stopped_at_canary",
            "experiment_valid_with_floor_only_signal",
            "experiment_valid_with_victory_signal",
            "experiment_valid_without_learning_signal",
        }:
            verdict = "experiment_invalid"
    trained_only_floor = (
        bool(training_episode_rows)
        and not any(bool(row["victory"]) for row in training_episode_rows)
    )
    diagnostics = {
        "authority": registration_authority(),
        "evaluation": (
            {
                "canary_initial": normalized_evaluation["canary"]["initial"]["diagnostics"],
                "canary_trained": normalized_evaluation["canary"]["trained"]["diagnostics"],
                "holdout_accessed": normalized_evaluation["holdout"]["accessed"],
                "holdout_initial": (
                    normalized_evaluation["holdout"]["evaluation"]["initial"]["diagnostics"]
                    if normalized_evaluation["holdout"]["accessed"]
                    else None
                ),
                "holdout_trained": (
                    normalized_evaluation["holdout"]["evaluation"]["trained"]["diagnostics"]
                    if normalized_evaluation["holdout"]["accessed"]
                    else None
                ),
            }
            if normalized_evaluation is not None
            else None
        ),
        "schema_version": "noncombat-state-conditioned-terminal-diagnostics-v1",
        "training": training_diagnostics,
    }
    metrics = {
        "authority": registration_authority(),
        "blocked_reason": blocked_reason,
        "completed_training_episodes": runtime.completed_episodes,
        "cumulative_wall_seconds": runtime.cumulative_wall_seconds,
        "formal_readiness_unchanged": True,
        "isolation_unchanged": isolation_unchanged,
        "optimizer_updates": runtime.optimizer_updates,
        "policy_quality_baseline_established": False,
        "schema_version": "noncombat-state-conditioned-terminal-metrics-v1",
        "target_supported_outcomes_established": False,
        "training_observed_only_floor_shaping": trained_only_floor,
        "training_unsupported_episodes": sum(
            row["unsupported_reason"] is not None for row in training_episode_rows
        ),
        "training_victories": sum(bool(row["victory"]) for row in training_episode_rows),
        "verdict": verdict,
    }
    final_model = {
        "architecture": runtime.model.architecture_metadata(),
        "authority": registration_authority(),
        "initial_model_sha256": hashlib.sha256(
            canonical_json_bytes(_encode_model_state(runtime.initial_model_state))
        ).hexdigest(),
        "model": _encode_model_state(runtime.model.state_dict()),
        "model_loading_authorized": False,
        "schema_version": "noncombat-state-conditioned-final-model-v1",
    }
    training_rows = {
        "chunks": training_chunks,
        "episode_count": len(training_episode_rows),
        "schema_version": "noncombat-state-conditioned-training-rows-v1",
    }
    isolation = {
        "authority": registration_authority(),
        "post": post,
        "pre": identity["isolation"],
        "schema_version": "noncombat-state-conditioned-isolation-v1",
        "unchanged": isolation_unchanged,
    }
    report = {
        "formal_readiness": "unchanged_not_ready",
        "logical_execution_id": execution_id,
        "policy_quality_claim": False,
        "schema_version": "noncombat-state-conditioned-terminal-report-v1",
        "target_supported_outcome_claim": False,
        "verdict": verdict,
    }
    payloads: dict[str, Any] = {
        "diagnostics.json": diagnostics,
        "final_model.json": final_model,
        "isolation.json": isolation,
        "metrics.json": metrics,
        "report.json": report,
        "training_rows.json": training_rows,
    }
    if normalized_evaluation is not None:
        payloads["evaluation.json"] = normalized_evaluation
    append_journal_record(
        directory,
        logical_execution_id=execution_id,
        state="terminal",
        checkpoint_index=runtime.next_chunk_index,
        completed_episodes=runtime.completed_episodes,
        terminal_reason=(
            f"blocked:{blocked_reason}" if blocked_reason is not None else verdict
        ),
    )
    for name, value in sorted(payloads.items()):
        _atomic_write_once(directory / name, canonical_json_bytes(value))
    inventory = _terminal_inventory(directory)
    manifest = {
        "artifact_count": len(inventory),
        "artifacts": inventory,
        "authority": registration_authority(),
        "logical_execution_id": authorization["logical_execution_id"],
        "manifest_kind": "full_terminal",
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": verdict,
    }
    _atomic_write_once(
        directory / "artifact_manifest.json", canonical_json_bytes(manifest)
    )
    return manifest


def _load_registered_native(
    registration: Mapping[str, Any]
) -> tuple[Any, Any, dict[str, Any]]:
    if "torch" in sys.modules:
        raise ExperimentBlocked("native module must load before Torch")
    from analysis_scripts.noncombat_simulator_adapter import (
        NativeSimulatorEnvironment,
        load_native_module,
        validate_provenance,
    )

    identity = registration["identity"]
    native = identity["native"]
    module = load_native_module(
        native["module"]["path"],
        dll_directories=[Path(path) for path in native["dll_directories"]],
    )
    if external_file_binding(native["module"]["path"]) != native["module"]:
        raise ExperimentBlocked("loaded native module file identity mismatch")
    if "torch" in sys.modules:
        raise ExperimentBlocked("native loading imported Torch out of order")
    expected = identity["adapter_provenance"]
    try:
        build = json.loads(module.build_info_json())
    except (AttributeError, json.JSONDecodeError) as exc:
        raise ExperimentBlocked(f"native build identity is invalid: {exc}") from exc
    build["python"] = platform.python_version()
    actual = copy.deepcopy(expected)
    actual["build"] = build
    try:
        actual = validate_provenance(actual)
    except Exception as exc:
        raise ExperimentBlocked(f"loaded native provenance is invalid: {exc}") from exc
    if actual != expected:
        raise ExperimentBlocked("loaded native build identity mismatch")
    return module, NativeSimulatorEnvironment, actual


def _last_durable_runtime(
    output: Path,
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    implementation_commit: str,
    logical_execution_id: str,
) -> tuple[TrainingRuntime, bytes | None]:
    checkpoint_files = sorted((output / "checkpoints").glob("checkpoint_*.json"))
    if not checkpoint_files:
        journal = validate_journal(
            load_canonical_json_bytes(
                (output / "execution_journal.json").read_bytes(),
                "execution journal",
            ),
            logical_execution_id=logical_execution_id,
        )
        validate_nonterminal_resume_coordinates(
            output,
            journal=journal,
            checkpoint_names=[],
            registration=registration,
        )
        return initialize_training_runtime(), None
    return resume_training_runtime_from_output(
        output,
        registration=registration,
        registration_sha256=registration_sha256,
        implementation_commit=implementation_commit,
        logical_execution_id=logical_execution_id,
    )


def _verify_terminal_with_fresh_process(output: Path) -> dict[str, Any]:
    verifier = REPO_ROOT / "analysis_scripts" / (
        "verify_noncombat_state_conditioned_simulator_learning_experiment.py"
    )
    completed = subprocess.run(
        [sys.executable, str(verifier), "--output", str(output)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
    )
    if completed.returncode != 0:
        raise ExperimentBlocked(
            f"standalone terminal verification failed: {completed.stderr.strip()}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ExperimentBlocked("standalone verifier returned invalid JSON") from exc


def execute_authorized_experiment(
    *,
    repo_root: Path | str,
    registration_path: Path | str,
    authorization_path: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    """Execute or resume the one registered logical simulator experiment."""
    root = Path(repo_root).resolve()
    output = Path(output_dir).resolve()
    registration, registration_bytes, authorization, authorization_bytes = _load_control_files(
        registration_path, authorization_path
    )
    actual_command = current_process_execution_command()
    validate_actual_execution_command(authorization, actual_command)
    preflight = source_only_preflight(
        repo_root=root,
        registration_path=registration_path,
        authorization_path=authorization_path,
        output_dir=output,
    )
    post_registration, post_registration_bytes, post_authorization, post_authorization_bytes = _load_control_files(
        registration_path, authorization_path
    )
    if (
        post_registration_bytes != registration_bytes
        or post_authorization_bytes != authorization_bytes
    ):
        raise ExperimentBlocked("control files changed during source-only preflight")
    registration = post_registration
    registration_bytes = post_registration_bytes
    authorization = post_authorization
    authorization_bytes = post_authorization_bytes
    validate_actual_execution_command(authorization, actual_command)
    identity = registration["identity"]
    registration_sha256 = hashlib.sha256(registration_bytes).hexdigest()
    implementation_commit = identity["implementation"]["commit"]
    execution_id = identity["logical_execution_id"]
    output_state = preflight["output_state"]
    fresh_start = output_state in {"absent", "abandoned_prestart"}
    runtime: TrainingRuntime | None = None
    module = None
    environment_type = None
    actual_provenance = None
    execution_lease: ExecutionLease | None = None
    if fresh_start:
        if output_state == "absent":
            _, execution_lease = initialize_experiment_output(
                output,
                registration_bytes=registration_bytes,
                authorization_bytes=authorization_bytes,
                repo_root=root,
                acquire_execution_lease=True,
            )
        else:
            try:
                execution_lease = ExecutionLease.acquire(output, execution_id)
            except BaseException as exc:
                raise ExperimentBlocked(
                    "abandoned pre-start lease acquisition failed"
                ) from exc
            try:
                complete_abandoned_prestart_output(
                    output,
                    registration=registration,
                    registration_bytes=registration_bytes,
                    authorization=authorization,
                    authorization_bytes=authorization_bytes,
                    execution_lease=execution_lease,
                )
            except BaseException:
                execution_lease.release()
                raise
        previous_checkpoint_bytes: bytes | None = None

    if execution_lease is None:
        try:
            execution_lease = ExecutionLease.acquire(output, execution_id)
        except BaseException as exc:
            consume_after_lease_acquisition_failure(
                output,
                logical_execution_id=execution_id,
                acquisition_error=exc,
            )
            raise AssertionError("lease failure cleanup must raise")

    with execution_lease:
        evaluation: dict[str, Any] | None = None
        active_started: float | None = None
        active_wall_before = 0.0
        active_runtime_snapshot: dict[str, Any] | None = None
        try:
            if fresh_start:
                module, environment_type, actual_provenance = _load_registered_native(
                    registration
                )
                runtime = initialize_training_runtime()
            else:
                module, environment_type, actual_provenance = _load_registered_native(
                    registration
                )
                runtime, previous_checkpoint_bytes = _last_durable_runtime(
                    output,
                    registration=registration,
                    registration_sha256=registration_sha256,
                    implementation_commit=implementation_commit,
                    logical_execution_id=execution_id,
                )
            if runtime is None or module is None or environment_type is None:
                raise ExperimentBlocked("execution runtime was not initialized")

            def environment_factory(seed: int):
                return environment_type(
                    module.Environment(seed, ASCENSION_LEVEL), actual_provenance
                )

            total_chunks = registered_training_chunk_count(registration)
            while runtime.next_chunk_index < total_chunks:
                coordinates = registered_training_coordinates(
                    registration, runtime.next_chunk_index
                )
                active_started = time.monotonic()
                active_wall_before = runtime.cumulative_wall_seconds
                active_runtime_snapshot = _runtime_snapshot(runtime)
                append_journal_record(
                    output,
                    logical_execution_id=execution_id,
                    state="operation",
                    checkpoint_index=runtime.next_chunk_index,
                    completed_episodes=runtime.completed_episodes,
                    operation=f"training_chunk:{runtime.next_chunk_index}",
                )
                summary = run_training_chunk(
                    runtime,
                    environment_factory=environment_factory,
                    seeds=coordinates["seeds"],
                    chunk_index=coordinates["chunk_index"],
                    max_wall_seconds=registration["limits"]["max_wall_seconds"],
                )
                summary["episode_end"] = coordinates["episode_end"]
                summary["episode_start"] = coordinates["episode_start"]
                summary["pass_index"] = coordinates["pass_index"]
                elapsed = time.monotonic() - active_started
                charged = runtime.cumulative_wall_seconds - active_wall_before
                runtime.cumulative_wall_seconds += max(0.0, elapsed - charged)
                if runtime.cumulative_wall_seconds > registration["limits"]["max_wall_seconds"]:
                    raise ExperimentBlocked("cumulative wall-time bound exceeded")
                checkpoint = build_checkpoint_payload(
                    runtime,
                    registration_sha256=registration_sha256,
                    implementation_commit=implementation_commit,
                    logical_execution_id=execution_id,
                    previous_checkpoint_bytes=previous_checkpoint_bytes,
                    training_chunk=summary,
                )
                checkpoint_path = publish_checkpoint(output, checkpoint)
                previous_checkpoint_bytes = checkpoint_path.read_bytes()
                append_journal_record(
                    output,
                    logical_execution_id=execution_id,
                    state="checkpoint",
                    checkpoint_index=runtime.next_chunk_index,
                    completed_episodes=runtime.completed_episodes,
                    checkpoint_sha256=hashlib.sha256(
                        previous_checkpoint_bytes
                    ).hexdigest(),
                )
                active_runtime_snapshot = None
                active_started = None
            if runtime.completed_episodes != registration["limits"]["max_episodes"]:
                raise ExperimentBlocked("registered training episode count was not completed")
            remaining = (
                registration["limits"]["max_wall_seconds"]
                - runtime.cumulative_wall_seconds
            )
            if remaining <= 0.0:
                raise ExperimentBlocked("wall-time bound exhausted before evaluation")
            initial_model = initialize_training_runtime().model
            active_started = time.monotonic()
            active_wall_before = runtime.cumulative_wall_seconds
            active_runtime_snapshot = _runtime_snapshot(runtime)
            append_journal_record(
                output,
                logical_execution_id=execution_id,
                state="operation",
                checkpoint_index=runtime.next_chunk_index,
                completed_episodes=runtime.completed_episodes,
                operation="evaluation:canary",
            )

            def preserve_canary(result: Mapping[str, Any]) -> None:
                nonlocal evaluation
                evaluation = copy.deepcopy(dict(result))
                append_journal_record(
                    output,
                    logical_execution_id=execution_id,
                    state="evidence",
                    checkpoint_index=runtime.next_chunk_index,
                    completed_episodes=runtime.completed_episodes,
                    evidence_name="canary_evaluation",
                    evidence=evaluation,
                )

            def begin_holdout() -> None:
                append_journal_record(
                    output,
                    logical_execution_id=execution_id,
                    state="operation",
                    checkpoint_index=runtime.next_chunk_index,
                    completed_episodes=runtime.completed_episodes,
                    operation="evaluation:holdout",
                )

            def preserve_complete_evaluation(result: Mapping[str, Any]) -> None:
                nonlocal evaluation
                evaluation = copy.deepcopy(dict(result))
                append_journal_record(
                    output,
                    logical_execution_id=execution_id,
                    state="evidence",
                    checkpoint_index=runtime.next_chunk_index,
                    completed_episodes=runtime.completed_episodes,
                    evidence_name="complete_evaluation",
                    evidence=evaluation,
                )

            evaluation = run_conditional_evaluation(
                initial_model,
                runtime.model,
                environment_factory=environment_factory,
                canary_seeds=registration["cohorts"]["canary"],
                holdout_seeds=registration["cohorts"]["holdout"],
                gate_contract=registration["behavior_gates"],
                unsupported_rate_ceiling=registration["limits"]["unsupported_rate_ceiling"],
                bootstrap_resamples=registration["limits"]["bootstrap_resamples"],
                deadline=active_started + remaining,
                on_canary_complete=preserve_canary,
                on_holdout_start=begin_holdout,
                on_holdout_complete=preserve_complete_evaluation,
            )
            runtime.cumulative_wall_seconds += time.monotonic() - active_started
            if runtime.cumulative_wall_seconds > registration["limits"]["max_wall_seconds"]:
                raise ExperimentBlocked("cumulative wall-time bound exceeded during evaluation")
            active_runtime_snapshot = None
            active_started = None
            manifest = publish_experiment_terminal(
                output,
                runtime=runtime,
                evaluation=evaluation,
            )
        except BaseException as exc:
            reason = f"{type(exc).__name__}: {exc}"
            journal = validate_journal(
                load_canonical_json_bytes(
                    (output / "execution_journal.json").read_bytes(),
                    "execution journal",
                ),
                logical_execution_id=execution_id,
            )
            if journal["state"] == "terminal":
                raise ExperimentBlocked(
                    f"terminal publication failed after identity consumption: {reason}"
                ) from exc
            checkpoint_names = sorted(
                path.name
                for path in (output / "checkpoints").glob("checkpoint_*.json")
            )
            checkpoint_records = [
                record
                for record in journal["records"]
                if record["state"] == "checkpoint"
            ]
            latest_record = journal["records"][-1]
            active_checkpoint_durable = (
                runtime is not None
                and latest_record["state"] == "checkpoint"
                and latest_record["checkpoint_index"] == runtime.next_chunk_index
                and latest_record["completed_episodes"] == runtime.completed_episodes
            )
            if len(checkpoint_names) > len(checkpoint_records):
                try:
                    reconcile_pending_checkpoint_journal(
                        output,
                        registration=registration,
                        logical_execution_id=execution_id,
                    )
                except BaseException as reconcile_exc:
                    consume_started_journal(
                        output,
                        logical_execution_id=execution_id,
                        reason=f"checkpoint_reconciliation_failed:{type(reconcile_exc).__name__}: {reconcile_exc}",
                    )
                    raise ExperimentBlocked(
                        "checkpoint reconciliation failed after identity consumption"
                    ) from reconcile_exc
            if runtime is None:
                phase = (
                    "runtime_initialization_failed"
                    if fresh_start
                    else "runtime_restore_failed"
                )
                consume_started_journal(
                    output,
                    logical_execution_id=execution_id,
                    reason=f"{phase}:{reason}",
                )
                raise ExperimentBlocked(
                    f"{phase} after identity consumption: {reason}"
                ) from exc
            if active_runtime_snapshot is not None and not (
                len(checkpoint_names) > len(checkpoint_records)
                or active_checkpoint_durable
            ):
                _restore_runtime(runtime, active_runtime_snapshot)
            if active_started is not None:
                elapsed = max(0.0, time.monotonic() - active_started)
                runtime.cumulative_wall_seconds = min(
                    registration["limits"]["max_wall_seconds"],
                    max(
                        runtime.cumulative_wall_seconds,
                        active_wall_before + elapsed,
                    ),
                )
            try:
                manifest = publish_experiment_terminal(
                    output,
                    runtime=runtime,
                    evaluation=evaluation,
                    blocked_reason=reason,
                )
            except BaseException as publication_exc:
                consume_started_journal(
                    output,
                    logical_execution_id=execution_id,
                    reason=f"terminal_publication_failed:{type(publication_exc).__name__}: {publication_exc}",
                )
                raise ExperimentBlocked(
                    "terminal publication failed after identity consumption"
                ) from publication_exc
    return {
        "manifest": manifest,
        "preflight": preflight,
        "verification": {
            "required_after_process_exit": True,
            "status": "pending_process_exit",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    implementation = commands.add_parser("verify-implementation")
    implementation.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    implementation.add_argument(
        "--preimplementation",
        type=Path,
        default=REPO_ROOT / DEFAULT_PREIMPLEMENTATION_PATH,
    )
    implementation.add_argument(
        "--r2-preflight",
        type=Path,
        default=REPO_ROOT / R2_PREFLIGHT_PATH,
    )
    implementation.add_argument(
        "--production-checkpoint-root",
        type=Path,
        default=Path(DEFAULT_PRODUCTION_CHECKPOINT_ROOT),
    )
    implementation.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate-controls")
    preflight = commands.add_parser("preflight")
    execute = commands.add_parser("execute")
    for command in (validate, preflight, execute):
        command.add_argument("--repo-root", type=Path, default=REPO_ROOT)
        command.add_argument("--registration", type=Path, required=True)
        command.add_argument("--authorization", type=Path, required=True)
    for command in (preflight, execute):
        command.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(raw_argv)
    try:
        if args.command == "verify-implementation":
            report = build_source_only_implementation_verification(
                repo_root=args.repo_root,
                preimplementation_path=args.preimplementation,
                r2_preflight_path=args.r2_preflight,
                production_checkpoint_root=args.production_checkpoint_root,
            )
            report_bytes = canonical_json_bytes(report)
            _atomic_write_once(args.output.resolve(), report_bytes)
            result = {
                "frozen_evidence_count": report["frozen_evidence"]["binding_count"],
                "output": args.output.resolve().as_posix(),
                "report_sha256": hashlib.sha256(report_bytes).hexdigest(),
                "verdict": report["verdict"],
            }
        elif args.command == "validate-controls":
            registration, registration_bytes, authorization, authorization_bytes = _load_control_files(
                args.registration, args.authorization
            )
            result = {
                "authorization_sha256": hashlib.sha256(authorization_bytes).hexdigest(),
                "execution_authorized": authorization["authority"]["execution_authorized"],
                "logical_execution_id": authorization["logical_execution_id"],
                "registration_sha256": hashlib.sha256(registration_bytes).hexdigest(),
                "source_commit": registration["identity"]["implementation"]["commit"],
                "validated": True,
            }
        elif args.command == "preflight":
            result = source_only_preflight(
                repo_root=args.repo_root,
                registration_path=args.registration,
                authorization_path=args.authorization,
                output_dir=args.output,
            )
        elif args.command == "execute":
            if argv is not None:
                raise ExperimentBlocked(
                    "execute must use the real process argv"
                )
            result = execute_authorized_experiment(
                repo_root=args.repo_root,
                registration_path=args.registration,
                authorization_path=args.authorization,
                output_dir=args.output,
            )
        else:
            result = _verify_terminal_with_fresh_process(args.output)
    except (OSError, ValueError, ExperimentBlocked) as exc:
        print(
            json.dumps({"error": str(exc), "status": "blocked"}, sort_keys=True),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, sort_keys=True))
    if (
        args.command == "execute"
        and result.get("manifest", {}).get("verdict") == "experiment_blocked"
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
