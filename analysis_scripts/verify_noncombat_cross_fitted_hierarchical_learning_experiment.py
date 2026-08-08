"""Independent standard-library verifier for the cross-fitted successor."""

from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import gzip
import hashlib
import hmac
import io
import json
import math
import os
import re
import stat as stat_module
import struct
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


VERIFIER_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-verifier-v1"
)
RIDGE_RESIDUAL_ATOL = 1e-9
RIDGE_RESIDUAL_RTOL = 1e-9
ADAM_ATOL = 5e-7
ADAM_RTOL = 5e-6
ADAM_LEARNING_RATE = 0.001
ADAM_BETA1 = 0.9
ADAM_BETA2 = 0.999
ADAM_EPSILON = 1e-8
MAX_BINARY_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_GZIP_STORED_BYTES = 64 * 1024 * 1024
MAX_GZIP_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_RIDGE_WIDTH = 129
GZIP_COMPRESSION_IDENTITY = "gzip-mtime-zero-v1"
CHUNK_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-chunk-evidence-v1"
)
CHUNK_EVIDENCE_DOCUMENT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-chunk-evidence-v2"
)
BASELINE_FEATURE_SCHEMA_VERSION = "cross-fitted-baseline-state-features-v1"
BASELINE_FEATURE_FOLDING = (
    "ascending-source-index-modulo-128-float32-add-v1"
)
BASELINE_FEATURE_DIM = 128
BASELINE_SOURCE_DIM = 1024
FOLD_COUNT = 4
TRAJECTORIES_PER_CHUNK = 64
HELD_OUT_TRAJECTORIES_PER_FOLD = 16
FIT_TRAJECTORIES_PER_FOLD = 48
RIDGE_COEFFICIENT = 0.001
PREDICTION_MIN = 0.0
PREDICTION_MAX = 3.0
FAMILY_ENTROPY_COEFFICIENT = 0.01
CONDITIONAL_ENTROPY_COEFFICIENT = 0.01
GRADIENT_NORM_CEILING = 1.0
GRADIENT_CLIP_EPSILON = 1e-6
GRADIENT_ATOL = 1e-7
GRADIENT_RTOL = 1e-5
LOSS_ATOL = 1e-8
LOSS_RTOL = 1e-6
MAX_CHUNK_DECISIONS = 32_768
MAX_DECISIONS_PER_TRAJECTORY = 500
COMPONENT_NAMES = (
    "card_reward_family_policy",
    "card_reward_conditional_policy",
    "other_policy",
    "family_entropy_regularizer",
    "conditional_entropy_regularizer",
)

_FLOAT_LAYOUT = {
    "float32": ("f", 4),
    "float64": ("d", 8),
}
_FLOAT_PAYLOAD_FIELDS = {
    "byte_order",
    "data_base64",
    "data_sha256",
    "dtype",
    "shape",
}
_GZIP_BINDING_FIELDS = {
    "canonical_sha256",
    "canonical_size_bytes",
    "compression",
    "sha256",
    "size_bytes",
}
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_FLOAT64_HEX_RE = re.compile(r"[0-9a-f]{16}\Z")
_CHUNK_FIELDS = {
    "adam",
    "baseline",
    "chunk_index",
    "content_sha256",
    "decisions",
    "gradients",
    "schema_version",
    "torch_version",
}
_DECISION_FIELDS = {
    "advantage",
    "baseline_fit_trajectory_ids",
    "baseline_prediction",
    "category",
    "decision_id",
    "decision_index",
    "diagnostic",
    "feature",
    "fold_id",
    "policy_terms",
    "prediction",
    "raw_return",
    "reward",
    "scale",
    "scale_mode",
    "seed",
    "trajectory_id",
}
_POLICY_TERM_FIELDS = {
    "conditional_entropy",
    "family_entropy",
    "selected_action_id",
    "selected_conditional_log_probability",
    "selected_family",
    "selected_family_log_probability",
    "selected_joint_log_probability",
}
_DIAGNOSTIC_REQUIRED_FIELDS = {
    "action_generator_state_sha256",
    "candidate_scores",
    "candidates",
    "category",
    "chunk_index",
    "conditional_probabilities",
    "decision_id",
    "decision_index",
    "family_order",
    "family_probabilities",
    "formal_reward",
    "joint_probabilities",
    "multi_family",
    "raw_score_max_action_ids",
    "raw_score_max_family_ids",
    "selected_action_id",
    "selected_family",
    "selection_mode",
}
_DIAGNOSTIC_OPTIONAL_FIELDS = {"unsupported_reason"}
_GENERATOR_STATE_FIELDS = {
    "after_conditional",
    "after_family",
    "before_family",
}
_CANDIDATE_FIELDS = {"action_id", "kind"}
_FORMAL_REWARD_FIELDS = {
    "floor_progress",
    "scalar_reward",
    "terminal_victory",
}
_FEATURE_FIELDS = {
    "dense_dim",
    "dtype",
    "entries",
    "folding",
    "schema_version",
    "sha256",
    "source_dim",
}
_MODEL_FIELDS = {
    "absolute_product_sums",
    "coefficients",
    "fit_trajectory_ids",
    "fold_id",
    "held_out_trajectory_ids",
    "kkt_residuals",
    "rhs",
}
_GRADIENT_FIELDS = {
    "clip_comparison",
    "clip_factor",
    "clipped_full",
    "component_order",
    "component_vectors",
    "consumed_torch_clipped",
    "full",
    "gradient_comparison",
    "installed",
    "legacy",
    "legacy_loss_value",
    "legacy_normalized_returns",
    "parameter_names",
    "parameter_shapes",
    "pre_parameter_sha256",
    "scalar_components",
    "scalar_full_loss",
}
_ADAM_PARAMETER_FIELDS = {
    "installed_gradient",
    "name",
    "post_exp_avg",
    "post_exp_avg_sq",
    "post_parameter",
    "post_step",
    "pre_exp_avg",
    "pre_exp_avg_sq",
    "pre_parameter",
    "pre_step",
    "shape",
}

_AUTHORITY = {
    "communication_mod": False,
    "environment_construction": False,
    "evaluation": False,
    "execution": False,
    "formal_rl": False,
    "gameplay": False,
    "model_fitting": False,
    "model_loading": False,
    "native_loading": False,
    "policy_promotion": False,
    "qualification": False,
    "seed_access": False,
    "training": False,
}
READINESS_AUTHORITY_NAMES = (
    "causal_claim",
    "communication_mod",
    "empirical_registration",
    "evaluation",
    "execution_authorization",
    "execution_request",
    "external_approval",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "model_loading",
    "native_loading",
    "ope",
    "policy_quality",
    "promotion",
    "qualification",
    "seed_access",
    "training",
)
_EXECUTION_AUTHORITY = {
    name: name
    in {
        "environment_construction",
        "execution",
        "model_fitting",
        "native_loading",
        "seed_access",
        "training",
    }
    for name in _AUTHORITY
}

CONTRACT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-contract-v1"
)
SOURCE_INVENTORY_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-source-inventory-v1"
)
REGISTRATION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-registration-v1"
)
REGISTRATION_V2_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-registration-v2"
)
READINESS_REPORT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-report-v1"
)
READINESS_CANDIDATE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-candidate-v1"
)
READINESS_CANDIDATE_ENCODING = "gzip-mtime-zero-v1"
READINESS_VERIFICATION_RECEIPT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-attempt-verified-v1"
)
EXECUTION_REQUEST_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-execution-request-v1"
)
EXTERNAL_APPROVAL_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-external-approval-v1"
)
AUTHORIZATION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-authorization-v1"
)
LEASE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-lease-v1"
)
SOURCE_PREFLIGHT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-source-preflight-v2"
)
ISOLATION_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-isolation-observation-v1"
)
FAILURE_WITNESS_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-failure-witness-v1"
)
ACCESS_JOURNAL_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-access-journal-v2"
)
RESOURCE_LEDGER_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-resource-ledger-v1"
)
BOOTSTRAP_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-bootstrap-v1"
)
CHECKPOINT_ENVELOPE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-checkpoint-v1"
)
RUNTIME_CHECKPOINT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-runtime-checkpoint-v1"
)
TERMINAL_INTENT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-terminal-intent-v1"
)
TERMINAL_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-terminal-v1"
)
MANIFEST_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-manifest-v1"
)
SEED_INVENTORY_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-seed-inventory-v1"
)
FRESH_SCHEDULE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1"
)

ACCESS_JOURNAL_FILENAME = "access_journal.jsonl"
RESOURCE_LEDGER_FILENAME = "resource_ledger.jsonl"
BOOTSTRAP_FILENAME = "bootstrap.json"
TERMINAL_INTENT_FILENAME = "terminal_intent.json"
TERMINAL_FILENAME = "terminal.json"
MANIFEST_FILENAME = "artifact_manifest.json"
REGISTRATION_FILENAME = "registration.json"
EXECUTION_REQUEST_FILENAME = "execution_request.json"
EXTERNAL_APPROVAL_FILENAME = "external_approval.json"
AUTHORIZATION_FILENAME = "authorization.json"
SOURCE_PREFLIGHT_FILENAME = "source_preflight.json"
PRE_ISOLATION_FILENAME = "pre_isolation.json"
POST_ISOLATION_FILENAME = "post_isolation.json"
FAILURE_FILENAME = "failure.json"
LEASE_FILENAME = ".execution.lease"

CHUNK_COUNT = 8
SCHEDULED_TRAJECTORIES = CHUNK_COUNT * TRAJECTORIES_PER_CHUNK
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_READINESS_CANDIDATE_STORED_BYTES = 64 * 1024 * 1024
MAX_READINESS_CANDIDATE_CANONICAL_BYTES = 512 * 1024 * 1024
MAX_STORED_BYTES = 192 * 1024 * 1024
MAX_UNCOMPRESSED_BUNDLE_BYTES = 256 * 1024 * 1024
MAX_ENVIRONMENT_ACCESSES = 576
MAX_OPTIMIZER_UPDATES = 8
MAX_RETAINED_DECISIONS = 32_768
MAX_CHARGED_SECONDS = 14_400.0
PREVIOUS_UNTOUCHED_HOLDOUT_START = 71_152
PREVIOUS_UNTOUCHED_HOLDOUT_END = 71_663
SEED_INVENTORY_MODULE_PATH = (
    "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_inventory.py"
)
SUCCESSOR_CONTRACT_PATH = (
    "openspec/specs/noncombat-cross-fitted-hierarchical-learning-successor/spec.md"
)
READINESS_CANDIDATE_FILENAME = "candidate_seed_inventory.json.gz"
READINESS_REPORT_FILENAME = "readiness_report.json"
READINESS_REPORT_MARKDOWN_FILENAME = "readiness_report.md"
READINESS_VERIFICATION_RECEIPT_FILENAME = "attempt_verified.json"
READINESS_ATTEMPT_ROOT_PATH = (
    "reports/noncombat_cross_fitted_empirical_successor_readiness_attempts"
)

_COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
_IDENTITY_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}\Z")
_OWNER_TOKEN_RE = re.compile(r"[0-9a-f]{32}\Z")
_TERMINAL_VERDICTS = {
    "experiment_blocked_before_seed_access",
    "experiment_completed_with_cross_fitted_mechanism_evidence",
    "experiment_failed_after_seed_access",
    "experiment_stopped_during_training_for_family_saturation",
}
_RESOURCE_FIELDS = (
    "charged_seconds",
    "environment_accesses",
    "optimizer_updates",
    "retained_decisions",
    "stored_bytes",
    "uncompressed_bytes",
)
_INTEGER_RESOURCE_FIELDS = frozenset(
    set(_RESOURCE_FIELDS) - {"charged_seconds"}
)

_MODULE_SPECS = (
    (
        "control_plane",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py",
        "standard-library immutable controls and lifecycle ownership",
    ),
    (
        "torch_runtime",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_runtime.py",
        "authorized rollout, fitting, gradient, and optimizer runtime",
    ),
    (
        "independent_verifier",
        "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py",
        "standard-library independent terminal verification",
    ),
)
_PUBLIC_DEPENDENCY_SPECS = (
    ("analysis_scripts_package", "analysis_scripts/__init__.py", ()),
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
        ("build_advantage_batch", "build_gradient_ledger"),
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
        "legacy_objective_diagnostic",
        "analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py",
        ("build_reinforce_loss", "normalize_returns"),
    ),
    (
        "policy_input",
        "analysis_scripts/noncombat_state_conditioned_policy_input.py",
        ("project_state_conditioned_policy_input",),
    ),
    (
        "simulator_adapter",
        "analysis_scripts/noncombat_simulator_adapter.py",
        ("validate_candidates", "validate_snapshot"),
    ),
    (
        "simulator_rl_policy_projection",
        "analysis_scripts/noncombat_simulator_rl_experiment.py",
        ("canonical_json_bytes", "project_policy_view_v2"),
    ),
    (
        "seed_inventory",
        "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_inventory.py",
        (
            "materialize_fresh_schedule",
            "validate_fresh_schedule",
            "validate_seed_inventory",
            "verify_seed_inventory",
        ),
    ),
    (
        "state_conditioned_ranker",
        "analysis_scripts/noncombat_state_conditioned_ranker.py",
        ("StateConditionedCandidateRanker",),
    ),
)
_V2_SEED_INVENTORY_PUBLIC_SYMBOLS = (
    "decode_readiness_candidate_artifact",
    "materialize_fresh_schedule",
    "validate_fresh_schedule",
    "validate_readiness_candidate_artifact",
    "validate_seed_inventory",
    "verify_seed_inventory",
)


class VerifierError(ValueError):
    """Raised when independently verified evidence is invalid."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return independently encoded canonical JSON bytes."""
    try:
        rendered = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise VerifierError("value is not canonical JSON") from exc
    return rendered.encode("ascii") + b"\n"


def verifier_contract() -> dict[str, Any]:
    """Return verifier identity without importing producer or Torch code."""
    return {
        "adam_replay": {
            "atol": ADAM_ATOL,
            "betas": [ADAM_BETA1, ADAM_BETA2],
            "epsilon": ADAM_EPSILON,
            "learning_rate": ADAM_LEARNING_RATE,
            "rtol": ADAM_RTOL,
        },
        "authority": dict(_AUTHORITY),
        "binary_payload": {
            "byte_order": "little",
            "dtypes": sorted(_FLOAT_LAYOUT),
            "max_bytes": MAX_BINARY_PAYLOAD_BYTES,
        },
        "chunk_evidence": {
            "component_order": list(COMPONENT_NAMES),
            "fold_count": FOLD_COUNT,
            "schema_version": CHUNK_EVIDENCE_SCHEMA_VERSION,
            "trajectories_per_chunk": TRAJECTORIES_PER_CHUNK,
        },
        "gzip": {
            "compression": GZIP_COMPRESSION_IDENTITY,
            "max_stored_bytes": MAX_GZIP_STORED_BYTES,
            "max_uncompressed_bytes": MAX_GZIP_UNCOMPRESSED_BYTES,
        },
        "ridge_residual": {
            "atol": RIDGE_RESIDUAL_ATOL,
            "rtol": RIDGE_RESIDUAL_RTOL,
            "scale": "max(abs(rhs),absolute_product_sum)",
        },
        "schema_version": VERIFIER_SCHEMA_VERSION,
    }


def _bounded_limit(value: Any, label: str, ceiling: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > ceiling
    ):
        raise VerifierError(f"{label} must be a positive integer at most {ceiling}")
    return value


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VerifierError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise VerifierError(f"{label} must be a finite number")
    return result


def _finite_vector(value: Any, label: str) -> tuple[float, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        raise VerifierError(f"{label} must be a sequence")
    return tuple(
        _finite_number(item, f"{label}[{index}]")
        for index, item in enumerate(value)
    )


def _shape_and_size(
    value: Any,
    *,
    item_size: int,
    max_bytes: int,
    canonical: bool,
) -> tuple[list[int], int, int]:
    if canonical:
        valid_sequence = isinstance(value, list)
    else:
        valid_sequence = isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        )
    if not valid_sequence:
        raise VerifierError("binary payload shape is invalid")
    shape = list(value)
    if any(
        isinstance(dimension, bool)
        or not isinstance(dimension, int)
        or dimension < 0
        for dimension in shape
    ):
        raise VerifierError("binary payload shape is invalid")

    element_count = 1
    for dimension in shape:
        element_count *= dimension
        if element_count * item_size > max_bytes:
            raise VerifierError("binary payload exceeds the byte bound")
    byte_count = element_count * item_size
    if byte_count > max_bytes:
        raise VerifierError("binary payload exceeds the byte bound")
    return shape, element_count, byte_count


def encode_float_payload(
    values: Sequence[float],
    *,
    dtype: str,
    shape: Sequence[int],
    max_bytes: int = MAX_BINARY_PAYLOAD_BYTES,
) -> dict[str, Any]:
    """Encode finite values as one canonical little-endian float payload."""
    limit = _bounded_limit(
        max_bytes, "binary payload byte bound", MAX_BINARY_PAYLOAD_BYTES
    )
    if dtype not in _FLOAT_LAYOUT:
        raise VerifierError("binary payload dtype must be float32 or float64")
    format_code, item_size = _FLOAT_LAYOUT[dtype]
    normalized_shape, element_count, _byte_count = _shape_and_size(
        shape,
        item_size=item_size,
        max_bytes=limit,
        canonical=False,
    )
    source = _finite_vector(values, "binary payload values")
    if len(source) != element_count:
        raise VerifierError("binary payload value count does not match shape")

    raw = bytearray()
    for index, item in enumerate(source):
        try:
            encoded = struct.pack("<" + format_code, item)
        except (OverflowError, struct.error) as exc:
            raise VerifierError(
                f"binary payload values[{index}] cannot be represented as {dtype}"
            ) from exc
        decoded = struct.unpack("<" + format_code, encoded)[0]
        if not math.isfinite(decoded):
            raise VerifierError(
                f"binary payload values[{index}] is non-finite after {dtype} cast"
            )
        raw.extend(encoded)
    raw_bytes = bytes(raw)
    return {
        "byte_order": "little",
        "data_base64": base64.b64encode(raw_bytes).decode("ascii"),
        "data_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "dtype": dtype,
        "shape": normalized_shape,
    }


def _decode_float_payload_details(
    value: Any,
    label: str,
    *,
    max_bytes: int,
) -> tuple[tuple[float, ...], bytes, str, tuple[int, ...]]:
    limit = _bounded_limit(
        max_bytes, f"{label} byte bound", MAX_BINARY_PAYLOAD_BYTES
    )
    if not isinstance(value, Mapping):
        raise VerifierError(f"{label} must be a mapping")
    payload = dict(value)
    if set(payload) != _FLOAT_PAYLOAD_FIELDS:
        raise VerifierError(f"{label} fields mismatch")
    if payload["byte_order"] != "little":
        raise VerifierError(f"{label} byte order must be little")
    dtype = payload["dtype"]
    if dtype not in _FLOAT_LAYOUT:
        raise VerifierError(f"{label} dtype must be float32 or float64")
    format_code, item_size = _FLOAT_LAYOUT[dtype]
    shape, _element_count, expected_bytes = _shape_and_size(
        payload["shape"],
        item_size=item_size,
        max_bytes=limit,
        canonical=True,
    )

    encoded = payload["data_base64"]
    if not isinstance(encoded, str):
        raise VerifierError(f"{label} base64 is invalid")
    expected_base64_length = 4 * ((expected_bytes + 2) // 3)
    if len(encoded) != expected_base64_length:
        raise VerifierError(f"{label} base64 length does not match shape")
    try:
        encoded_ascii = encoded.encode("ascii")
        raw = base64.b64decode(encoded_ascii, validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise VerifierError(f"{label} base64 is invalid") from exc
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise VerifierError(f"{label} base64 is not canonical")
    if len(raw) != expected_bytes:
        raise VerifierError(f"{label} byte length does not match shape")

    digest = payload["data_sha256"]
    if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
        raise VerifierError(f"{label} hash is invalid")
    actual_digest = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual_digest, digest):
        raise VerifierError(f"{label} hash mismatch")

    decoded = tuple(item[0] for item in struct.iter_unpack("<" + format_code, raw))
    if not all(math.isfinite(item) for item in decoded):
        raise VerifierError(f"{label} contains non-finite values")
    return decoded, raw, dtype, tuple(shape)


def decode_float_payload(
    value: Any,
    label: str = "binary payload",
    *,
    max_bytes: int = MAX_BINARY_PAYLOAD_BYTES,
) -> tuple[float, ...]:
    """Strictly verify and decode one canonical float32/float64 payload."""
    decoded, _raw, _dtype, _shape = _decode_float_payload_details(
        value, label, max_bytes=max_bytes
    )
    return decoded


def _deterministic_gzip(payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        filename="",
        mode="wb",
        compresslevel=9,
        fileobj=buffer,
        mtime=0,
    ) as stream:
        stream.write(payload)
    return buffer.getvalue()


def encode_deterministic_gzip(
    payload: bytes,
    *,
    max_stored_bytes: int = MAX_GZIP_STORED_BYTES,
    max_uncompressed_bytes: int = MAX_GZIP_UNCOMPRESSED_BYTES,
) -> tuple[bytes, dict[str, Any]]:
    """Compress bytes deterministically and bind stored and canonical identity."""
    stored_limit = _bounded_limit(
        max_stored_bytes, "gzip stored byte bound", MAX_GZIP_STORED_BYTES
    )
    uncompressed_limit = _bounded_limit(
        max_uncompressed_bytes,
        "gzip uncompressed byte bound",
        MAX_GZIP_UNCOMPRESSED_BYTES,
    )
    if not isinstance(payload, bytes):
        raise VerifierError("gzip canonical payload must be bytes")
    if len(payload) > uncompressed_limit:
        raise VerifierError("gzip canonical payload exceeds the byte bound")
    stored = _deterministic_gzip(payload)
    if len(stored) > stored_limit:
        raise VerifierError("gzip stored payload exceeds the byte bound")
    binding = {
        "canonical_sha256": hashlib.sha256(payload).hexdigest(),
        "canonical_size_bytes": len(payload),
        "compression": GZIP_COMPRESSION_IDENTITY,
        "sha256": hashlib.sha256(stored).hexdigest(),
        "size_bytes": len(stored),
    }
    return stored, binding


def _binding_size(value: Any, label: str, *, allow_zero: bool) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise VerifierError(f"{label} is invalid")
    if value < 0 or (value == 0 and not allow_zero):
        raise VerifierError(f"{label} is invalid")
    return value


def _binding_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise VerifierError(f"{label} is invalid")
    return value


def verify_deterministic_gzip(
    stored: bytes,
    binding: Mapping[str, Any],
    *,
    max_stored_bytes: int = MAX_GZIP_STORED_BYTES,
    max_uncompressed_bytes: int = MAX_GZIP_UNCOMPRESSED_BYTES,
) -> bytes:
    """Boundedly decompress and exactly reconstruct deterministic gzip bytes."""
    stored_limit = _bounded_limit(
        max_stored_bytes, "gzip stored byte bound", MAX_GZIP_STORED_BYTES
    )
    uncompressed_limit = _bounded_limit(
        max_uncompressed_bytes,
        "gzip uncompressed byte bound",
        MAX_GZIP_UNCOMPRESSED_BYTES,
    )
    if not isinstance(stored, bytes):
        raise VerifierError("gzip stored payload must be bytes")
    if not isinstance(binding, Mapping):
        raise VerifierError("gzip binding must be a mapping")
    normalized = dict(binding)
    if set(normalized) != _GZIP_BINDING_FIELDS:
        raise VerifierError("gzip binding fields mismatch")
    if normalized["compression"] != GZIP_COMPRESSION_IDENTITY:
        raise VerifierError("gzip compression identity mismatch")

    canonical_size = _binding_size(
        normalized["canonical_size_bytes"],
        "gzip canonical size",
        allow_zero=True,
    )
    stored_size = _binding_size(
        normalized["size_bytes"], "gzip stored size", allow_zero=False
    )
    canonical_digest = _binding_sha256(
        normalized["canonical_sha256"], "gzip canonical hash"
    )
    stored_digest = _binding_sha256(normalized["sha256"], "gzip stored hash")
    if canonical_size > uncompressed_limit:
        raise VerifierError("gzip canonical payload exceeds the byte bound")
    if stored_size > stored_limit or len(stored) > stored_limit:
        raise VerifierError("gzip stored payload exceeds the byte bound")
    if len(stored) != stored_size:
        raise VerifierError("gzip stored size mismatch")
    if not hmac.compare_digest(hashlib.sha256(stored).hexdigest(), stored_digest):
        raise VerifierError("gzip stored hash mismatch")
    if (
        len(stored) < 10
        or stored[:4] != b"\x1f\x8b\x08\x00"
        or stored[4:8] != b"\x00\x00\x00\x00"
    ):
        raise VerifierError("gzip deterministic header mismatch")

    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as stream:
            canonical = stream.read(canonical_size + 1)
            trailing = stream.read(1) if len(canonical) == canonical_size else b""
    except (EOFError, OSError) as exc:
        raise VerifierError("gzip payload is invalid") from exc
    if len(canonical) != canonical_size or trailing:
        raise VerifierError("gzip canonical size mismatch")
    if not hmac.compare_digest(
        hashlib.sha256(canonical).hexdigest(), canonical_digest
    ):
        raise VerifierError("gzip canonical hash mismatch")
    reconstructed = _deterministic_gzip(canonical)
    if not hmac.compare_digest(reconstructed, stored):
        raise VerifierError("gzip bytes do not match deterministic reconstruction")
    return canonical


def ridge_residual_within_tolerance(
    *, residual: float, rhs: float, absolute_product_sum: float
) -> bool:
    """Apply the fixed per-coordinate KKT residual boundary."""
    residual_value = _finite_number(residual, "ridge residual")
    rhs_value = _finite_number(rhs, "ridge rhs")
    product_sum = _finite_number(
        absolute_product_sum, "ridge absolute product sum"
    )
    if product_sum < 0.0:
        raise VerifierError("absolute product sum must be nonnegative")
    scale = max(abs(rhs_value), product_sum)
    limit = RIDGE_RESIDUAL_ATOL + RIDGE_RESIDUAL_RTOL * scale
    return abs(residual_value) <= limit


def verify_ridge_residuals(
    *,
    normal_matrix: Sequence[Sequence[float]],
    coefficients: Sequence[float],
    rhs: Sequence[float],
) -> tuple[float, ...]:
    """Replay all ridge KKT residuals in canonical coordinate order."""
    beta = _finite_vector(coefficients, "ridge coefficients")
    right_hand_side = _finite_vector(rhs, "ridge rhs")
    width = len(beta)
    if not 0 < width <= MAX_RIDGE_WIDTH or len(right_hand_side) != width:
        raise VerifierError("ridge dimensions mismatch")
    if isinstance(normal_matrix, (str, bytes, bytearray)) or not isinstance(
        normal_matrix, Sequence
    ):
        raise VerifierError("ridge normal matrix must be a sequence")
    if len(normal_matrix) != width:
        raise VerifierError("ridge dimensions mismatch")

    residuals: list[float] = []
    for coordinate, raw_row in enumerate(normal_matrix):
        row = _finite_vector(raw_row, f"ridge normal matrix[{coordinate}]")
        if len(row) != width:
            raise VerifierError("ridge dimensions mismatch")
        products = tuple(row[index] * beta[index] for index in range(width))
        if not all(math.isfinite(product) for product in products):
            raise VerifierError("ridge matrix product is non-finite")
        try:
            residual = math.fsum(products) - right_hand_side[coordinate]
            absolute_product_sum = math.fsum(
                abs(product) for product in products
            )
        except OverflowError as exc:
            raise VerifierError(
                "ridge residual reconstruction overflowed"
            ) from exc
        if not math.isfinite(residual) or not math.isfinite(absolute_product_sum):
            raise VerifierError("ridge residual reconstruction is non-finite")
        if not ridge_residual_within_tolerance(
            residual=residual,
            rhs=right_hand_side[coordinate],
            absolute_product_sum=absolute_product_sum,
        ):
            raise VerifierError(
                f"ridge residual coordinate {coordinate} exceeds fixed tolerance"
            )
        residuals.append(residual)
    return tuple(residuals)


def replay_preclip_prediction(
    *,
    coefficients: Sequence[float],
    augmented_features: Sequence[float],
    stored_prediction: float,
    stored_little_endian_hex: str,
) -> float:
    """Replay a prediction and require exact canonical float64 evidence bytes."""
    beta = _finite_vector(coefficients, "prediction coefficients")
    features = _finite_vector(augmented_features, "prediction features")
    if not beta or len(beta) != len(features):
        raise VerifierError("prediction dimensions mismatch")
    products = tuple(beta[index] * features[index] for index in range(len(beta)))
    if not all(math.isfinite(product) for product in products):
        raise VerifierError("prediction product is non-finite")
    try:
        replayed = math.fsum(products)
    except OverflowError as exc:
        raise VerifierError("prediction reconstruction overflowed") from exc
    if not math.isfinite(replayed):
        raise VerifierError("prediction reconstruction is non-finite")
    stored_value = _finite_number(stored_prediction, "stored prediction")
    if (
        not isinstance(stored_little_endian_hex, str)
        or not _FLOAT64_HEX_RE.fullmatch(stored_little_endian_hex)
    ):
        raise VerifierError("stored prediction float64 bytes are invalid")
    replayed_bytes = struct.pack("<d", replayed)
    if not hmac.compare_digest(replayed_bytes, struct.pack("<d", stored_value)):
        raise VerifierError("stored prediction value does not replay exactly")
    if not hmac.compare_digest(replayed_bytes.hex(), stored_little_endian_hex):
        raise VerifierError("stored prediction float64 bytes do not replay exactly")
    return replayed


def _float32(value: float, label: str) -> float:
    try:
        encoded = struct.pack("<f", _finite_number(value, label))
    except (OverflowError, struct.error) as exc:
        raise VerifierError(f"{label} cannot be represented as float32") from exc
    result = struct.unpack("<f", encoded)[0]
    if not math.isfinite(result):
        raise VerifierError(f"{label} is non-finite after float32 cast")
    return result


def _float32_vector(value: Any, label: str) -> tuple[float, ...]:
    source = _finite_vector(value, label)
    return tuple(
        _float32(item, f"{label}[{index}]")
        for index, item in enumerate(source)
    )


def _adam_step(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VerifierError(f"{label} must be a nonnegative integer")
    return value


def _require_adam_close(actual: float, expected: float, label: str) -> None:
    limit = ADAM_ATOL + ADAM_RTOL * abs(expected)
    if abs(actual - expected) > limit:
        raise VerifierError(f"Adam {label} transition mismatch")


def replay_adam_transition(
    *,
    pre_parameters: Sequence[float],
    installed_gradient: Sequence[float],
    pre_exp_avg: Sequence[float],
    pre_exp_avg_sq: Sequence[float],
    pre_step: int,
    post_parameters: Sequence[float],
    post_exp_avg: Sequence[float],
    post_exp_avg_sq: Sequence[float],
    post_step: int,
) -> dict[str, Any]:
    """Independently verify one fixed-control CPU float32 Adam transition."""
    before = _float32_vector(pre_parameters, "Adam pre parameters")
    gradient = _float32_vector(installed_gradient, "Adam installed gradient")
    first_before = _float32_vector(pre_exp_avg, "Adam pre first moment")
    second_before = _float32_vector(pre_exp_avg_sq, "Adam pre second moment")
    after = _float32_vector(post_parameters, "Adam post parameters")
    first_after = _float32_vector(post_exp_avg, "Adam post first moment")
    second_after = _float32_vector(post_exp_avg_sq, "Adam post second moment")
    width = len(before)
    if width == 0 or any(
        len(vector) != width
        for vector in (
            gradient,
            first_before,
            second_before,
            after,
            first_after,
            second_after,
        )
    ):
        raise VerifierError("Adam vector dimensions mismatch")
    if any(value < 0.0 for value in second_before + second_after):
        raise VerifierError("Adam second moments must be nonnegative")

    step_before = _adam_step(pre_step, "Adam pre step")
    step_after = _adam_step(post_step, "Adam post step")
    expected_step = step_before + 1
    if step_after != expected_step:
        raise VerifierError("Adam step transition mismatch")
    bias_correction1 = 1.0 - ADAM_BETA1**expected_step
    bias_correction2 = 1.0 - ADAM_BETA2**expected_step
    step_size = ADAM_LEARNING_RATE / bias_correction1
    bias_correction2_sqrt = math.sqrt(bias_correction2)

    expected_first: list[float] = []
    expected_second: list[float] = []
    expected_parameters: list[float] = []
    for index in range(width):
        first = _float32(
            ADAM_BETA1 * first_before[index]
            + (1.0 - ADAM_BETA1) * gradient[index],
            f"Adam expected first moment[{index}]",
        )
        second = _float32(
            ADAM_BETA2 * second_before[index]
            + (1.0 - ADAM_BETA2) * gradient[index] * gradient[index],
            f"Adam expected second moment[{index}]",
        )
        if second < 0.0:
            raise VerifierError("Adam expected second moment is negative")
        denominator = math.sqrt(second) / bias_correction2_sqrt + ADAM_EPSILON
        parameter = _float32(
            before[index] - step_size * first / denominator,
            f"Adam expected parameter[{index}]",
        )
        _require_adam_close(
            first_after[index], first, f"first moment[{index}]"
        )
        _require_adam_close(
            second_after[index], second, f"second moment[{index}]"
        )
        _require_adam_close(after[index], parameter, f"parameter[{index}]")
        expected_first.append(first)
        expected_second.append(second)
        expected_parameters.append(parameter)

    return {
        "post_exp_avg": tuple(expected_first),
        "post_exp_avg_sq": tuple(expected_second),
        "post_parameters": tuple(expected_parameters),
        "post_step": expected_step,
    }


def _exact_mapping(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise VerifierError(f"{label} must be a mapping")
    result = dict(value)
    if set(result) != fields:
        raise VerifierError(f"{label} fields mismatch")
    return result


def _exact_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise VerifierError(f"{label} must be a list")
    return value


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VerifierError(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: Any, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise VerifierError(f"{label} must be positive")
    return result


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerifierError(f"{label} must be a nonempty string")
    return value


def _id_list(
    value: Any,
    label: str,
    *,
    expected_size: int | None = None,
) -> tuple[str, ...]:
    source = _exact_list(value, label)
    result = tuple(
        _nonempty_string(item, f"{label}[{index}]")
        for index, item in enumerate(source)
    )
    if len(set(result)) != len(result):
        raise VerifierError(f"{label} contains duplicate identities")
    if expected_size is not None and len(result) != expected_size:
        raise VerifierError(f"{label} must contain exactly {expected_size} items")
    return result


def _require_close(
    actual: Any,
    expected: float,
    label: str,
    *,
    atol: float,
    rtol: float,
) -> float:
    value = _finite_number(actual, label)
    if abs(value - expected) > atol + rtol * abs(expected):
        raise VerifierError(f"{label} mismatch")
    return value


def _require_vector_close(
    actual: Sequence[float],
    expected: Sequence[float],
    label: str,
    *,
    atol: float,
    rtol: float,
) -> None:
    if len(actual) != len(expected):
        raise VerifierError(f"{label} dimensions mismatch")
    for index, (actual_value, expected_value) in enumerate(
        zip(actual, expected, strict=True)
    ):
        _require_close(
            actual_value,
            expected_value,
            f"{label}[{index}]",
            atol=atol,
            rtol=rtol,
        )


def _require_exact_float64_vector(
    actual: Sequence[float], expected: Sequence[float], label: str
) -> None:
    if len(actual) != len(expected):
        raise VerifierError(f"{label} dimensions mismatch")
    for index, (actual_value, expected_value) in enumerate(
        zip(actual, expected, strict=True)
    ):
        if struct.pack("<d", actual_value) != struct.pack("<d", expected_value):
            raise VerifierError(f"{label}[{index}] differs from canonical replay")


def _require_exact_float32_vector(
    actual: Sequence[float], expected: Sequence[float], label: str
) -> None:
    if len(actual) != len(expected):
        raise VerifierError(f"{label} dimensions mismatch")
    for index, (actual_value, expected_value) in enumerate(
        zip(actual, expected, strict=True)
    ):
        if struct.pack("<f", actual_value) != struct.pack("<f", expected_value):
            raise VerifierError(f"{label}[{index}] differs from canonical replay")


def _typed_float_payload(
    value: Any,
    label: str,
    *,
    dtype: str,
    shape: Sequence[int],
) -> tuple[tuple[float, ...], bytes]:
    decoded, raw, actual_dtype, actual_shape = _decode_float_payload_details(
        value,
        label,
        max_bytes=MAX_BINARY_PAYLOAD_BYTES,
    )
    if actual_dtype != dtype or actual_shape != tuple(shape):
        raise VerifierError(f"{label} dtype or shape mismatch")
    return decoded, raw


def _validate_sparse_feature(
    value: Any, label: str
) -> tuple[tuple[float, ...], tuple[tuple[int, float], ...]]:
    feature = _exact_mapping(value, _FEATURE_FIELDS, label)
    if (
        feature["dense_dim"] != BASELINE_FEATURE_DIM
        or feature["source_dim"] != BASELINE_SOURCE_DIM
        or feature["dtype"] != "float32"
        or feature["folding"] != BASELINE_FEATURE_FOLDING
        or feature["schema_version"] != BASELINE_FEATURE_SCHEMA_VERSION
    ):
        raise VerifierError(f"{label} identity mismatch")
    entries = _exact_list(feature["entries"], f"{label}.entries")
    dense = [0.0] * BASELINE_FEATURE_DIM
    sparse: list[tuple[int, float]] = [(0, 1.0)]
    previous_index = -1
    for position, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, list) or len(raw_entry) != 2:
            raise VerifierError(f"{label}.entries[{position}] is invalid")
        feature_index = _nonnegative_int(
            raw_entry[0], f"{label}.entries[{position}].index"
        )
        if feature_index >= BASELINE_FEATURE_DIM or feature_index <= previous_index:
            raise VerifierError(f"{label}.entries are not strictly increasing")
        raw_value = _finite_number(
            raw_entry[1], f"{label}.entries[{position}].value"
        )
        float32_value = _float32(
            raw_value, f"{label}.entries[{position}].value"
        )
        if raw_value != float32_value or float32_value == 0.0:
            raise VerifierError(
                f"{label}.entries[{position}] is not canonical nonzero float32"
            )
        dense[feature_index] = float32_value
        sparse.append((feature_index + 1, float(float32_value)))
        previous_index = feature_index

    identity = {
        "dense_dim": feature["dense_dim"],
        "dtype": feature["dtype"],
        "entries": feature["entries"],
        "folding": feature["folding"],
        "schema_version": feature["schema_version"],
        "source_dim": feature["source_dim"],
    }
    digest = _binding_sha256(feature["sha256"], f"{label}.sha256")
    expected_digest = hashlib.sha256(canonical_json_bytes(identity)).hexdigest()
    if not hmac.compare_digest(digest, expected_digest):
        raise VerifierError(f"{label} digest mismatch")
    return (1.0, *dense), tuple(sparse)


def _validate_policy_terms(value: Any, label: str) -> dict[str, Any]:
    terms = _exact_mapping(value, _POLICY_TERM_FIELDS, label)
    result = {
        "conditional_entropy": _finite_number(
            terms["conditional_entropy"], f"{label}.conditional_entropy"
        ),
        "family_entropy": _finite_number(
            terms["family_entropy"], f"{label}.family_entropy"
        ),
        "selected_action_id": _nonempty_string(
            terms["selected_action_id"], f"{label}.selected_action_id"
        ),
        "selected_conditional_log_probability": _finite_number(
            terms["selected_conditional_log_probability"],
            f"{label}.selected_conditional_log_probability",
        ),
        "selected_family": _nonempty_string(
            terms["selected_family"], f"{label}.selected_family"
        ),
        "selected_family_log_probability": _finite_number(
            terms["selected_family_log_probability"],
            f"{label}.selected_family_log_probability",
        ),
        "selected_joint_log_probability": _finite_number(
            terms["selected_joint_log_probability"],
            f"{label}.selected_joint_log_probability",
        ),
    }
    if result["conditional_entropy"] < 0.0 or result["family_entropy"] < 0.0:
        raise VerifierError(f"{label} entropy must be nonnegative")
    return result


def _probability_mapping(
    value: Any,
    identities: Sequence[str],
    label: str,
) -> dict[str, float]:
    expected = set(identities)
    result = _exact_mapping(value, expected, label)
    probabilities: dict[str, float] = {}
    for identity in identities:
        probability = _finite_number(result[identity], f"{label}.{identity}")
        if not 0.0 <= probability <= 1.0:
            raise VerifierError(f"{label}.{identity} is outside [0, 1]")
        probabilities[identity] = probability
    return probabilities


def _log_softmax(values: Sequence[float], label: str) -> tuple[float, ...]:
    if not values:
        raise VerifierError(f"{label} must be nonempty")
    maximum = max(values)
    denominator = math.fsum(math.exp(value - maximum) for value in values)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise VerifierError(f"{label} normalization failed")
    normalization = maximum + math.log(denominator)
    result = tuple(value - normalization for value in values)
    if any(not math.isfinite(value) for value in result):
        raise VerifierError(f"{label} log probabilities are non-finite")
    return result


def _require_probability_close(
    actual: float, expected: float, label: str
) -> None:
    _require_close(
        actual,
        expected,
        label,
        atol=1e-12,
        rtol=1e-10,
    )


def _validate_decision_diagnostic(
    value: Any,
    *,
    category: str,
    chunk_index: int,
    decision_id: str,
    decision_index: int,
    policy_terms: Mapping[str, Any],
    reward: float,
    label: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise VerifierError(f"{label} must be a mapping")
    diagnostic = dict(value)
    fields = set(diagnostic)
    if not _DIAGNOSTIC_REQUIRED_FIELDS <= fields or not fields <= (
        _DIAGNOSTIC_REQUIRED_FIELDS | _DIAGNOSTIC_OPTIONAL_FIELDS
    ):
        raise VerifierError(f"{label} diagnostic fields mismatch")
    if diagnostic["category"] != category:
        raise VerifierError(f"{label} diagnostic category mismatch")
    if diagnostic["chunk_index"] != chunk_index:
        raise VerifierError(f"{label} diagnostic chunk index mismatch")
    if diagnostic["decision_id"] != decision_id:
        raise VerifierError(f"{label} diagnostic decision identity mismatch")
    if diagnostic["decision_index"] != decision_index:
        raise VerifierError(f"{label} diagnostic decision index mismatch")
    if diagnostic["selection_mode"] != "family-first-then-conditional-v1":
        raise VerifierError(f"{label} diagnostic selection mode mismatch")

    generator_states = _exact_mapping(
        diagnostic["action_generator_state_sha256"],
        _GENERATOR_STATE_FIELDS,
        f"{label}.action_generator_state_sha256",
    )
    for stage in sorted(_GENERATOR_STATE_FIELDS):
        _binding_sha256(generator_states[stage], f"{label} generator state {stage}")

    raw_candidates = _exact_list(diagnostic["candidates"], f"{label}.candidates")
    if not raw_candidates:
        raise VerifierError(f"{label} candidates must be nonempty")
    action_ids: list[str] = []
    families: list[str] = []
    for candidate_index, raw_candidate in enumerate(raw_candidates):
        candidate_label = f"{label}.candidates[{candidate_index}]"
        candidate = _exact_mapping(
            raw_candidate, _CANDIDATE_FIELDS, candidate_label
        )
        action_ids.append(
            _nonempty_string(candidate["action_id"], f"{candidate_label}.action_id")
        )
        families.append(
            _nonempty_string(candidate["kind"], f"{candidate_label}.kind")
        )
    if len(set(action_ids)) != len(action_ids):
        raise VerifierError(f"{label} candidate action identities must be unique")
    expected_family_order = tuple(sorted(set(families)))
    family_order = _id_list(diagnostic["family_order"], f"{label}.family_order")
    if family_order != expected_family_order:
        raise VerifierError(f"{label} family order mismatch")
    multi_family = diagnostic["multi_family"]
    if type(multi_family) is not bool or multi_family != (len(family_order) > 1):
        raise VerifierError(f"{label} multi-family diagnostic mismatch")

    raw_scores = _exact_mapping(
        diagnostic["candidate_scores"], set(action_ids), f"{label}.candidate_scores"
    )
    scores: dict[str, float] = {}
    for action_id in action_ids:
        score = _finite_number(
            raw_scores[action_id], f"{label}.candidate_scores.{action_id}"
        )
        if _float32(score, f"{label}.candidate_scores.{action_id}") != score:
            raise VerifierError(f"{label} candidate score is not canonical float32")
        scores[action_id] = score

    family_logits = tuple(
        max(
            scores[action_id]
            for action_id, family in zip(action_ids, families, strict=True)
            if family == expected_family
        )
        for expected_family in family_order
    )
    family_logs = _log_softmax(family_logits, f"{label} family")
    expected_family_probabilities = {
        family: math.exp(family_logs[index])
        for index, family in enumerate(family_order)
    }
    family_probabilities = _probability_mapping(
        diagnostic["family_probabilities"], family_order, f"{label}.family_probabilities"
    )
    for family in family_order:
        _require_probability_close(
            family_probabilities[family],
            expected_family_probabilities[family],
            f"{label} family probability {family}",
        )

    conditional_logs: dict[str, float] = {}
    for family in family_order:
        members = [
            action_id
            for action_id, candidate_family in zip(action_ids, families, strict=True)
            if candidate_family == family
        ]
        member_logs = _log_softmax(
            tuple(scores[action_id] for action_id in members),
            f"{label} conditional family {family}",
        )
        conditional_logs.update(zip(members, member_logs, strict=True))
    expected_conditional_probabilities = {
        action_id: math.exp(conditional_logs[action_id]) for action_id in action_ids
    }
    conditional_probabilities = _probability_mapping(
        diagnostic["conditional_probabilities"],
        action_ids,
        f"{label}.conditional_probabilities",
    )
    joint_probabilities = _probability_mapping(
        diagnostic["joint_probabilities"], action_ids, f"{label}.joint_probabilities"
    )
    family_log_by_id = dict(zip(family_order, family_logs, strict=True))
    for action_id, family in zip(action_ids, families, strict=True):
        _require_probability_close(
            conditional_probabilities[action_id],
            expected_conditional_probabilities[action_id],
            f"{label} conditional probability {action_id}",
        )
        expected_joint = math.exp(
            family_log_by_id[family] + conditional_logs[action_id]
        )
        _require_probability_close(
            joint_probabilities[action_id],
            expected_joint,
            f"{label} joint probability {action_id}",
        )

    maximum_score = max(scores.values())
    expected_max_actions = tuple(
        sorted(action_id for action_id in action_ids if scores[action_id] == maximum_score)
    )
    maximum_actions = _id_list(
        diagnostic["raw_score_max_action_ids"],
        f"{label}.raw_score_max_action_ids",
    )
    if maximum_actions != expected_max_actions:
        raise VerifierError(f"{label} raw-score maximum action mismatch")
    family_by_action = dict(zip(action_ids, families, strict=True))
    expected_max_families = tuple(
        sorted({family_by_action[action_id] for action_id in expected_max_actions})
    )
    maximum_families = _id_list(
        diagnostic["raw_score_max_family_ids"],
        f"{label}.raw_score_max_family_ids",
    )
    if maximum_families != expected_max_families:
        raise VerifierError(f"{label} raw-score maximum family mismatch")

    selected_action_id = _nonempty_string(
        diagnostic["selected_action_id"], f"{label}.selected_action_id"
    )
    selected_family = _nonempty_string(
        diagnostic["selected_family"], f"{label}.selected_family"
    )
    if selected_action_id not in family_by_action:
        raise VerifierError(f"{label} selected action is not a candidate")
    if family_by_action[selected_action_id] != selected_family:
        raise VerifierError(f"{label} selected action family mismatch")
    if (
        policy_terms["selected_action_id"] != selected_action_id
        or policy_terms["selected_family"] != selected_family
    ):
        raise VerifierError(f"{label} selected action or family differs from policy terms")

    selected_family_log = family_log_by_id[selected_family]
    selected_conditional_log = conditional_logs[selected_action_id]
    selected_joint_log = selected_family_log + selected_conditional_log
    log_checks = (
        (
            policy_terms["selected_family_log_probability"],
            selected_family_log,
            "selected family log probability",
        ),
        (
            policy_terms["selected_conditional_log_probability"],
            selected_conditional_log,
            "selected conditional log probability",
        ),
        (
            policy_terms["selected_joint_log_probability"],
            selected_joint_log,
            "selected joint log probability",
        ),
    )
    for actual, expected, description in log_checks:
        _require_close(
            actual,
            expected,
            f"{label} {description}",
            atol=LOSS_ATOL,
            rtol=LOSS_RTOL,
        )
    expected_family_entropy = -math.fsum(
        math.exp(log_probability) * log_probability
        for log_probability in family_logs
    )
    expected_conditional_entropy = math.fsum(
        expected_family_probabilities[family]
        * -math.fsum(
            math.exp(conditional_logs[action_id]) * conditional_logs[action_id]
            for action_id, candidate_family in zip(action_ids, families, strict=True)
            if candidate_family == family
        )
        for family in family_order
    )
    _require_close(
        policy_terms["family_entropy"],
        expected_family_entropy,
        f"{label} family entropy",
        atol=LOSS_ATOL,
        rtol=LOSS_RTOL,
    )
    _require_close(
        policy_terms["conditional_entropy"],
        expected_conditional_entropy,
        f"{label} conditional entropy",
        atol=LOSS_ATOL,
        rtol=LOSS_RTOL,
    )

    formal_reward = _exact_mapping(
        diagnostic["formal_reward"], _FORMAL_REWARD_FIELDS, f"{label}.formal_reward"
    )
    floor_progress = _finite_number(
        formal_reward["floor_progress"], f"{label}.formal_reward.floor_progress"
    )
    terminal_victory = formal_reward["terminal_victory"]
    if not 0.0 <= floor_progress <= 1.0:
        raise VerifierError(f"{label} formal reward floor progress is outside [0, 1]")
    if type(terminal_victory) is not int or terminal_victory not in {0, 1}:
        raise VerifierError(f"{label} formal reward terminal victory is invalid")
    expected_reward = 2.0 * terminal_victory + floor_progress
    scalar_reward = _finite_number(
        formal_reward["scalar_reward"], f"{label}.formal_reward.scalar_reward"
    )
    if struct.pack("<d", scalar_reward) != struct.pack("<d", expected_reward):
        raise VerifierError(f"{label} formal reward scalar mismatch")
    if struct.pack("<d", reward) != struct.pack("<d", scalar_reward):
        raise VerifierError(f"{label} decision reward differs from formal reward scalar")
    if "unsupported_reason" in diagnostic:
        _nonempty_string(
            diagnostic["unsupported_reason"], f"{label}.unsupported_reason"
        )
        if terminal_victory != 0 or floor_progress != 0.0 or scalar_reward != 0.0:
            raise VerifierError(f"{label} unsupported decision reward must be zero")
    return diagnostic


def _validate_chunk_decisions(
    value: Any,
    *,
    chunk_index: int,
) -> tuple[
    list[dict[str, Any]],
    tuple[str, ...],
    dict[str, list[dict[str, Any]]],
    dict[str, tuple[str, ...]],
]:
    rows = _exact_list(value, "chunk decisions")
    if not rows or len(rows) > MAX_CHUNK_DECISIONS:
        raise VerifierError("chunk decision count is invalid")
    decisions: list[dict[str, Any]] = []
    by_trajectory: dict[str, list[dict[str, Any]]] = {}
    seed_by_trajectory: dict[str, int] = {}
    seen_decision_ids: set[str] = set()
    for row_index, raw_row in enumerate(rows):
        label = f"chunk decisions[{row_index}]"
        row = _exact_mapping(raw_row, _DECISION_FIELDS, label)
        decision_id = _nonempty_string(row["decision_id"], f"{label}.decision_id")
        if decision_id in seen_decision_ids:
            raise VerifierError("chunk decision identities must be unique")
        seen_decision_ids.add(decision_id)
        trajectory_id = _nonempty_string(
            row["trajectory_id"], f"{label}.trajectory_id"
        )
        seed = _nonnegative_int(row["seed"], f"{label}.seed")
        if trajectory_id in seed_by_trajectory:
            if seed_by_trajectory[trajectory_id] != seed:
                raise VerifierError("one trajectory cannot contain multiple seeds")
        else:
            seed_by_trajectory[trajectory_id] = seed
        decision_index = _nonnegative_int(
            row["decision_index"], f"{label}.decision_index"
        )
        raw_return = _finite_number(row["raw_return"], f"{label}.raw_return")
        if not PREDICTION_MIN <= raw_return <= PREDICTION_MAX:
            raise VerifierError(f"{label}.raw_return is outside [0, 3]")
        reward = _finite_number(row["reward"], f"{label}.reward")
        if not PREDICTION_MIN <= reward <= PREDICTION_MAX:
            raise VerifierError(f"{label}.reward is outside [0, 3]")
        scale = _finite_number(row["scale"], f"{label}.scale")
        if scale != 1.0 or row["scale_mode"] != "fixed_unit":
            raise VerifierError(f"{label} advantage scale identity mismatch")
        category = _nonempty_string(row["category"], f"{label}.category")
        fold_id = _nonempty_string(row["fold_id"], f"{label}.fold_id")
        fit_ids = _id_list(
            row["baseline_fit_trajectory_ids"],
            f"{label}.baseline_fit_trajectory_ids",
            expected_size=FIT_TRAJECTORIES_PER_FOLD,
        )
        augmented_dense, augmented_sparse = _validate_sparse_feature(
            row["feature"], f"{label}.feature"
        )
        policy_terms = _validate_policy_terms(
            row["policy_terms"], f"{label}.policy_terms"
        )
        diagnostic = _validate_decision_diagnostic(
            row["diagnostic"],
            category=category,
            chunk_index=chunk_index,
            decision_id=decision_id,
            decision_index=decision_index,
            policy_terms=policy_terms,
            reward=reward,
            label=label,
        )
        decision = {
            "augmented_dense": augmented_dense,
            "augmented_sparse": augmented_sparse,
            "category": category,
            "decision_id": decision_id,
            "decision_index": decision_index,
            "diagnostic": diagnostic,
            "fit_ids": fit_ids,
            "fold_id": fold_id,
            "policy_terms": policy_terms,
            "raw": row,
            "raw_return": raw_return,
            "reward": reward,
            "seed": seed,
            "trajectory_id": trajectory_id,
        }
        decisions.append(decision)
        by_trajectory.setdefault(trajectory_id, []).append(decision)

    if len(by_trajectory) != TRAJECTORIES_PER_CHUNK:
        raise VerifierError("chunk must contain exactly 64 complete trajectories")
    if len(set(seed_by_trajectory.values())) != TRAJECTORIES_PER_CHUNK:
        raise VerifierError("chunk trajectory seeds must be unique")
    trajectory_order = tuple(
        sorted(seed_by_trajectory, key=lambda item: seed_by_trajectory[item])
    )
    canonical_decisions: list[dict[str, Any]] = []
    for trajectory_id in trajectory_order:
        trajectory = by_trajectory[trajectory_id]
        if len(trajectory) > MAX_DECISIONS_PER_TRAJECTORY:
            raise VerifierError(
                f"trajectory {trajectory_id} exceeds 500 decisions"
            )
        indices = [item["decision_index"] for item in trajectory]
        if indices != list(range(len(trajectory))):
            raise VerifierError(
                f"trajectory {trajectory_id} decisions are not contiguous"
            )
        running = 0.0
        for decision in reversed(trajectory):
            running = float(decision["reward"]) + float(running)
            if not math.isfinite(running) or not PREDICTION_MIN <= running <= PREDICTION_MAX:
                raise VerifierError(
                    f"trajectory {trajectory_id} return-to-go is outside [0, 3]"
                )
            if struct.pack("<d", running) != struct.pack(
                "<d", decision["raw_return"]
            ):
                raise VerifierError(
                    f"trajectory {trajectory_id} return-to-go mismatch"
                )
        canonical_decisions.extend(trajectory)
    if [item["decision_id"] for item in decisions] != [
        item["decision_id"] for item in canonical_decisions
    ]:
        raise VerifierError("chunk decisions are not in canonical trajectory order")

    fold_trajectories = {
        f"fold-{fold_index}": tuple(
            sorted(
                trajectory_id
                for position, trajectory_id in enumerate(trajectory_order)
                if position % FOLD_COUNT == fold_index
            )
        )
        for fold_index in range(FOLD_COUNT)
    }
    if any(
        len(identities) != HELD_OUT_TRAJECTORIES_PER_FOLD
        for identities in fold_trajectories.values()
    ):
        raise VerifierError("every fold must contain exactly 16 trajectories")
    return decisions, trajectory_order, by_trajectory, fold_trajectories


def _reconstruct_normal_equations(
    *,
    held_out: set[str],
    trajectory_order: Sequence[str],
    by_trajectory: Mapping[str, Sequence[dict[str, Any]]],
) -> tuple[list[list[float]], list[float]]:
    width = BASELINE_FEATURE_DIM + 1
    matrix = [[0.0] * width for _ in range(width)]
    rhs = [0.0] * width
    for trajectory_id in trajectory_order:
        if trajectory_id in held_out:
            continue
        trajectory = by_trajectory[trajectory_id]
        weight = float(1.0 / (FIT_TRAJECTORIES_PER_FOLD * len(trajectory)))
        for decision in trajectory:
            target = float(decision["raw_return"])
            sparse = decision["augmented_sparse"]
            for row_index, row_value in sparse:
                rhs[row_index] = float(rhs[row_index]) + (
                    (weight * target) * float(row_value)
                )
                for column_index, column_value in sparse:
                    matrix[row_index][column_index] = float(
                        matrix[row_index][column_index]
                    ) + ((weight * float(row_value)) * float(column_value))
    for coordinate in range(1, width):
        matrix[coordinate][coordinate] = (
            float(matrix[coordinate][coordinate]) + RIDGE_COEFFICIENT
        )
    return matrix, rhs


def _ridge_products(
    matrix: Sequence[Sequence[float]], coefficients: Sequence[float]
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    residual_products: list[float] = []
    absolute_products: list[float] = []
    for row in matrix:
        products = tuple(
            float(row[index]) * float(coefficients[index])
            for index in range(len(coefficients))
        )
        try:
            residual_products.append(math.fsum(products))
            absolute_products.append(math.fsum(abs(value) for value in products))
        except OverflowError as exc:
            raise VerifierError("ridge product reconstruction overflowed") from exc
    return tuple(residual_products), tuple(absolute_products)


def _verify_chunk_baseline(
    value: Any,
    *,
    decisions: Sequence[dict[str, Any]],
    trajectory_order: Sequence[str],
    by_trajectory: Mapping[str, Sequence[dict[str, Any]]],
    expected_folds: Mapping[str, tuple[str, ...]],
) -> None:
    baseline = _exact_mapping(
        value, {"fold_trajectories", "models"}, "chunk baseline"
    )
    fold_rows = _exact_mapping(
        baseline["fold_trajectories"], set(expected_folds), "fold trajectories"
    )
    if tuple(fold_rows) != tuple(expected_folds):
        raise VerifierError("fold trajectory order mismatch")
    for fold_id, expected in expected_folds.items():
        actual = _id_list(
            fold_rows[fold_id],
            f"fold trajectories.{fold_id}",
            expected_size=HELD_OUT_TRAJECTORIES_PER_FOLD,
        )
        if actual != expected:
            raise VerifierError(f"{fold_id} seed-position membership mismatch")

    model_rows = _exact_list(baseline["models"], "baseline models")
    if len(model_rows) != FOLD_COUNT:
        raise VerifierError("baseline must contain exactly four models")
    coefficients_by_fold: dict[str, tuple[float, ...]] = {}
    for fold_index, raw_model in enumerate(model_rows):
        label = f"baseline models[{fold_index}]"
        model = _exact_mapping(raw_model, _MODEL_FIELDS, label)
        expected_fold_id = f"fold-{fold_index}"
        if model["fold_id"] != expected_fold_id:
            raise VerifierError("baseline model fold order mismatch")
        expected_held_out = expected_folds[expected_fold_id]
        held_out = _id_list(
            model["held_out_trajectory_ids"],
            f"{label}.held_out_trajectory_ids",
            expected_size=HELD_OUT_TRAJECTORIES_PER_FOLD,
        )
        if held_out != expected_held_out:
            raise VerifierError(f"{label} held-out identities mismatch")
        expected_fit = tuple(
            sorted(set(trajectory_order).difference(expected_held_out))
        )
        fit = _id_list(
            model["fit_trajectory_ids"],
            f"{label}.fit_trajectory_ids",
            expected_size=FIT_TRAJECTORIES_PER_FOLD,
        )
        if fit != expected_fit:
            raise VerifierError(f"{label} fit identities mismatch")

        width = BASELINE_FEATURE_DIM + 1
        coefficients, _coefficient_bytes = _typed_float_payload(
            model["coefficients"],
            f"{label}.coefficients",
            dtype="float64",
            shape=[width],
        )
        stored_rhs, _rhs_bytes = _typed_float_payload(
            model["rhs"], f"{label}.rhs", dtype="float64", shape=[width]
        )
        stored_residuals, _residual_bytes = _typed_float_payload(
            model["kkt_residuals"],
            f"{label}.kkt_residuals",
            dtype="float64",
            shape=[width],
        )
        stored_product_sums, _product_bytes = _typed_float_payload(
            model["absolute_product_sums"],
            f"{label}.absolute_product_sums",
            dtype="float64",
            shape=[width],
        )
        matrix, reconstructed_rhs = _reconstruct_normal_equations(
            held_out=set(expected_held_out),
            trajectory_order=trajectory_order,
            by_trajectory=by_trajectory,
        )
        _require_exact_float64_vector(
            stored_rhs, reconstructed_rhs, f"{label}.rhs"
        )
        reconstructed_residuals = verify_ridge_residuals(
            normal_matrix=matrix,
            coefficients=coefficients,
            rhs=reconstructed_rhs,
        )
        matrix_products, reconstructed_product_sums = _ridge_products(
            matrix, coefficients
        )
        expected_residuals = tuple(
            matrix_products[index] - reconstructed_rhs[index]
            for index in range(width)
        )
        _require_exact_float64_vector(
            reconstructed_residuals,
            expected_residuals,
            f"{label} internal residual",
        )
        _require_exact_float64_vector(
            stored_residuals,
            reconstructed_residuals,
            f"{label}.kkt_residuals",
        )
        _require_exact_float64_vector(
            stored_product_sums,
            reconstructed_product_sums,
            f"{label}.absolute_product_sums",
        )
        coefficients_by_fold[expected_fold_id] = coefficients

    for decision_index, decision in enumerate(decisions):
        label = f"chunk decisions[{decision_index}]"
        fold_id = decision["fold_id"]
        if fold_id not in coefficients_by_fold:
            raise VerifierError(f"{label}.fold_id is invalid")
        expected_held_out = expected_folds[fold_id]
        if decision["trajectory_id"] not in expected_held_out:
            raise VerifierError(f"{label} trajectory is not held out by its fold")
        expected_fit = tuple(
            sorted(set(trajectory_order).difference(expected_held_out))
        )
        if decision["fit_ids"] != expected_fit:
            raise VerifierError(f"{label} fit provenance mismatch")
        prediction = _exact_mapping(
            decision["raw"]["prediction"],
            {
                "clipped",
                "preclip_little_endian_hex",
                "unclipped",
                "was_clipped",
            },
            f"{label}.prediction",
        )
        replayed = replay_preclip_prediction(
            coefficients=coefficients_by_fold[fold_id],
            augmented_features=decision["augmented_dense"],
            stored_prediction=prediction["unclipped"],
            stored_little_endian_hex=prediction["preclip_little_endian_hex"],
        )
        clipped = min(PREDICTION_MAX, max(PREDICTION_MIN, replayed))
        stored_clipped = _finite_number(
            prediction["clipped"], f"{label}.prediction.clipped"
        )
        if struct.pack("<d", stored_clipped) != struct.pack("<d", clipped):
            raise VerifierError(f"{label} clipped prediction mismatch")
        if not isinstance(prediction["was_clipped"], bool) or prediction[
            "was_clipped"
        ] != (clipped != replayed):
            raise VerifierError(f"{label} prediction clipping diagnostic mismatch")
        baseline_prediction = _finite_number(
            decision["raw"]["baseline_prediction"],
            f"{label}.baseline_prediction",
        )
        if struct.pack("<d", baseline_prediction) != struct.pack("<d", clipped):
            raise VerifierError(f"{label} baseline prediction mismatch")
        advantage = _finite_number(
            decision["raw"]["advantage"], f"{label}.advantage"
        )
        expected_advantage = decision["raw_return"] - clipped
        if struct.pack("<d", advantage) != struct.pack(
            "<d", expected_advantage
        ):
            raise VerifierError(f"{label} advantage mismatch")
        decision["advantage"] = advantage


def _reconstruct_scalar_components(
    decisions: Sequence[dict[str, Any]],
) -> dict[str, float]:
    denominator = float(len(decisions))
    card_family_terms: list[float] = []
    card_conditional_terms: list[float] = []
    other_terms: list[float] = []
    family_entropies: list[float] = []
    conditional_entropies: list[float] = []
    for decision in decisions:
        terms = decision["policy_terms"]
        advantage = float(decision["advantage"])
        if decision["category"] == "card_reward":
            card_family_terms.append(
                terms["selected_family_log_probability"] * advantage
            )
            card_conditional_terms.append(
                terms["selected_conditional_log_probability"] * advantage
            )
        else:
            other_terms.append(
                terms["selected_joint_log_probability"] * advantage
            )
        family_entropies.append(terms["family_entropy"])
        conditional_entropies.append(terms["conditional_entropy"])
    return {
        "card_reward_family_policy": -math.fsum(card_family_terms)
        / denominator,
        "card_reward_conditional_policy": -math.fsum(
            card_conditional_terms
        )
        / denominator,
        "other_policy": -math.fsum(other_terms) / denominator,
        "family_entropy_regularizer": -FAMILY_ENTROPY_COEFFICIENT
        * math.fsum(family_entropies)
        / denominator,
        "conditional_entropy_regularizer": -CONDITIONAL_ENTROPY_COEFFICIENT
        * math.fsum(conditional_entropies)
        / denominator,
    }


def _parameter_layout(
    gradients: Mapping[str, Any],
) -> tuple[tuple[str, ...], tuple[tuple[int, ...], ...], tuple[int, ...]]:
    names = _id_list(gradients["parameter_names"], "gradient parameter names")
    raw_shapes = _exact_list(
        gradients["parameter_shapes"], "gradient parameter shapes"
    )
    if not names or len(raw_shapes) != len(names):
        raise VerifierError("gradient parameter layout mismatch")
    shapes: list[tuple[int, ...]] = []
    counts: list[int] = []
    for index, raw_shape in enumerate(raw_shapes):
        shape_values = _exact_list(
            raw_shape, f"gradient parameter shapes[{index}]"
        )
        shape: list[int] = []
        for dimension_index, dimension in enumerate(shape_values):
            shape.append(
                _nonnegative_int(
                    dimension,
                    "gradient parameter shapes"
                    f"[{index}][{dimension_index}]",
                )
            )
        count = math.prod(shape) if shape else 1
        if count <= 0:
            raise VerifierError("gradient parameters must contain values")
        shapes.append(tuple(shape))
        counts.append(count)
    if sum(counts) * 8 > MAX_BINARY_PAYLOAD_BYTES:
        raise VerifierError("gradient parameter layout exceeds the byte bound")
    return names, tuple(shapes), tuple(counts)


def _independent_vector_norm(value: Sequence[float], label: str) -> float:
    try:
        squared = math.fsum(float(item) * float(item) for item in value)
        result = math.sqrt(squared)
    except (OverflowError, ValueError) as exc:
        raise VerifierError(f"{label} norm reconstruction failed") from exc
    if not math.isfinite(result):
        raise VerifierError(f"{label} norm is non-finite")
    return result


def _independent_dot(
    left: Sequence[float], right: Sequence[float], label: str
) -> float:
    try:
        result = math.fsum(
            float(left_value) * float(right_value)
            for left_value, right_value in zip(left, right, strict=True)
        )
    except OverflowError as exc:
        raise VerifierError(f"{label} dot reconstruction overflowed") from exc
    if not math.isfinite(result):
        raise VerifierError(f"{label} dot is non-finite")
    return result


def _verify_gradient_comparison(
    value: Any,
    *,
    full: Sequence[float],
    legacy: Sequence[float],
) -> None:
    comparison = _exact_mapping(
        value,
        {
            "cosine",
            "cross_fitted_norm",
            "difference_norm",
            "dot",
            "legacy_norm",
        },
        "gradient comparison",
    )
    cross_norm = _independent_vector_norm(full, "cross-fitted gradient")
    legacy_norm = _independent_vector_norm(legacy, "legacy gradient")
    differences = tuple(
        full[index] - legacy[index] for index in range(len(full))
    )
    difference_norm = _independent_vector_norm(
        differences, "objective gradient difference"
    )
    dot = _independent_dot(full, legacy, "objective gradient")
    _require_close(
        comparison["cross_fitted_norm"],
        cross_norm,
        "gradient comparison.cross_fitted_norm",
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    )
    _require_close(
        comparison["legacy_norm"],
        legacy_norm,
        "gradient comparison.legacy_norm",
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    )
    _require_close(
        comparison["difference_norm"],
        difference_norm,
        "gradient comparison.difference_norm",
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    )
    _require_close(
        comparison["dot"],
        dot,
        "gradient comparison.dot",
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    )
    if cross_norm == 0.0 or legacy_norm == 0.0:
        if comparison["cosine"] is not None:
            raise VerifierError(
                "gradient comparison cosine must be undefined for a zero norm"
            )
    else:
        expected_cosine = dot / (cross_norm * legacy_norm)
        if comparison["cosine"] is None:
            raise VerifierError(
                "gradient comparison cosine cannot be undefined for nonzero norms"
            )
        _require_close(
            comparison["cosine"],
            expected_cosine,
            "gradient comparison.cosine",
            atol=GRADIENT_ATOL,
            rtol=GRADIENT_RTOL,
        )


def _verify_clip_comparison(
    value: Any,
    *,
    installed: Sequence[float],
    consumed: Sequence[float],
) -> None:
    comparison = _exact_mapping(
        value,
        {"max_abs_difference", "max_relative_difference"},
        "clip comparison",
    )
    differences = [
        abs(float(left) - float(right))
        for left, right in zip(installed, consumed, strict=True)
    ]
    relatives = []
    for index, difference in enumerate(differences):
        denominator = max(abs(installed[index]), abs(consumed[index]))
        relatives.append(0.0 if denominator == 0.0 else difference / denominator)
    expected_absolute = max(differences)
    expected_relative = max(relatives)
    _require_close(
        comparison["max_abs_difference"],
        expected_absolute,
        "clip comparison.max_abs_difference",
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    )
    _require_close(
        comparison["max_relative_difference"],
        expected_relative,
        "clip comparison.max_relative_difference",
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    )


def _verify_chunk_gradients(
    value: Any,
    *,
    decisions: Sequence[dict[str, Any]],
) -> tuple[
    tuple[str, ...],
    tuple[tuple[int, ...], ...],
    tuple[int, ...],
    tuple[float, ...],
    str,
]:
    gradients = _exact_mapping(value, _GRADIENT_FIELDS, "chunk gradients")
    names, shapes, counts = _parameter_layout(gradients)
    width = sum(counts)
    component_order = _exact_list(
        gradients["component_order"], "gradient component order"
    )
    if component_order != list(COMPONENT_NAMES):
        raise VerifierError("gradient component order mismatch")
    raw_components = _exact_mapping(
        gradients["component_vectors"],
        set(COMPONENT_NAMES),
        "gradient component vectors",
    )
    components: dict[str, tuple[float, ...]] = {}
    for name in COMPONENT_NAMES:
        components[name], _raw = _typed_float_payload(
            raw_components[name],
            f"gradient component vectors.{name}",
            dtype="float64",
            shape=[width],
        )
    full, _full_raw = _typed_float_payload(
        gradients["full"], "gradient full", dtype="float64", shape=[width]
    )
    clipped_full, _clipped_raw = _typed_float_payload(
        gradients["clipped_full"],
        "gradient clipped full",
        dtype="float64",
        shape=[width],
    )
    installed, _installed_raw = _typed_float_payload(
        gradients["installed"],
        "gradient installed",
        dtype="float32",
        shape=[width],
    )
    legacy, _legacy_raw = _typed_float_payload(
        gradients["legacy"],
        "gradient legacy",
        dtype="float64",
        shape=[width],
    )
    consumed, _consumed_raw = _typed_float_payload(
        gradients["consumed_torch_clipped"],
        "gradient consumed Torch clipped",
        dtype="float32",
        shape=[width],
    )
    _legacy_returns, _legacy_returns_raw = _typed_float_payload(
        gradients["legacy_normalized_returns"],
        "legacy normalized returns",
        dtype="float32",
        shape=[len(decisions)],
    )
    _finite_number(gradients["legacy_loss_value"], "legacy loss value")

    component_sum = []
    for coordinate in range(width):
        total = 0.0
        for name in COMPONENT_NAMES:
            total = float(total) + float(components[name][coordinate])
        component_sum.append(total)
    _require_vector_close(
        full,
        component_sum,
        "gradient component sum",
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    )
    full_norm = _independent_vector_norm(full, "full gradient")
    expected_clip_factor = (
        1.0
        if full_norm <= GRADIENT_NORM_CEILING
        else GRADIENT_NORM_CEILING
        / (full_norm + GRADIENT_CLIP_EPSILON)
    )
    clip_factor = _require_close(
        gradients["clip_factor"],
        expected_clip_factor,
        "gradient clip factor",
        atol=LOSS_ATOL,
        rtol=LOSS_RTOL,
    )
    expected_clipped = tuple(value * clip_factor for value in full)
    _require_vector_close(
        clipped_full,
        expected_clipped,
        "gradient clipped full",
        atol=GRADIENT_ATOL,
        rtol=GRADIENT_RTOL,
    )
    expected_installed = tuple(
        _float32(value, f"gradient installed replay[{index}]")
        for index, value in enumerate(expected_clipped)
    )
    _require_exact_float32_vector(
        installed, expected_installed, "gradient installed"
    )
    _verify_clip_comparison(
        gradients["clip_comparison"],
        installed=installed,
        consumed=consumed,
    )
    _verify_gradient_comparison(
        gradients["gradient_comparison"], full=full, legacy=legacy
    )

    scalar_components = _exact_mapping(
        gradients["scalar_components"],
        set(COMPONENT_NAMES),
        "scalar components",
    )
    reconstructed_components = _reconstruct_scalar_components(decisions)
    stored_components: dict[str, float] = {}
    for name in COMPONENT_NAMES:
        stored_components[name] = _require_close(
            scalar_components[name],
            reconstructed_components[name],
            f"scalar components.{name}",
            atol=LOSS_ATOL,
            rtol=LOSS_RTOL,
        )
    reconstructed_full = 0.0
    stored_full_sum = 0.0
    for name in COMPONENT_NAMES:
        reconstructed_full = float(reconstructed_full) + float(
            reconstructed_components[name]
        )
        stored_full_sum = float(stored_full_sum) + float(
            stored_components[name]
        )
    scalar_full = _require_close(
        gradients["scalar_full_loss"],
        reconstructed_full,
        "scalar full loss",
        atol=LOSS_ATOL,
        rtol=LOSS_RTOL,
    )
    _require_close(
        scalar_full,
        stored_full_sum,
        "scalar full loss component reconstruction",
        atol=LOSS_ATOL,
        rtol=LOSS_RTOL,
    )
    pre_parameter_sha256 = _binding_sha256(
        gradients["pre_parameter_sha256"], "pre-parameter hash"
    )
    return names, shapes, counts, installed, pre_parameter_sha256


def _verify_chunk_adam(
    value: Any,
    *,
    names: Sequence[str],
    shapes: Sequence[tuple[int, ...]],
    counts: Sequence[int],
    installed: Sequence[float],
    pre_parameter_sha256: str,
) -> None:
    adam = _exact_mapping(
        value,
        {"betas", "epsilon", "learning_rate", "parameters", "weight_decay"},
        "chunk Adam",
    )
    if adam["betas"] != [ADAM_BETA1, ADAM_BETA2]:
        raise VerifierError("Adam betas mismatch")
    controls = (
        (adam["epsilon"], ADAM_EPSILON, "Adam epsilon"),
        (adam["learning_rate"], ADAM_LEARNING_RATE, "Adam learning rate"),
        (adam["weight_decay"], 0.0, "Adam weight decay"),
    )
    for actual, expected, label in controls:
        if _finite_number(actual, label) != expected:
            raise VerifierError(f"{label} mismatch")
    parameters = _exact_list(adam["parameters"], "Adam parameters")
    if len(parameters) != len(names):
        raise VerifierError("Adam parameter layout length mismatch")

    pre_parameter_bytes = bytearray()
    offset = 0
    for index, raw_parameter in enumerate(parameters):
        label = f"Adam parameters[{index}]"
        parameter = _exact_mapping(
            raw_parameter, _ADAM_PARAMETER_FIELDS, label
        )
        if parameter["name"] != names[index]:
            raise VerifierError(f"{label} name or order mismatch")
        if parameter["shape"] != list(shapes[index]):
            raise VerifierError(f"{label} shape mismatch")
        shape = shapes[index]
        count = counts[index]
        parameter_installed, _parameter_installed_raw = _typed_float_payload(
            parameter["installed_gradient"],
            f"{label}.installed_gradient",
            dtype="float32",
            shape=shape,
        )
        expected_segment = tuple(installed[offset : offset + count])
        _require_exact_float32_vector(
            parameter_installed,
            expected_segment,
            f"{label}.installed_gradient",
        )
        pre_parameters, pre_raw = _typed_float_payload(
            parameter["pre_parameter"],
            f"{label}.pre_parameter",
            dtype="float32",
            shape=shape,
        )
        post_parameters, _post_raw = _typed_float_payload(
            parameter["post_parameter"],
            f"{label}.post_parameter",
            dtype="float32",
            shape=shape,
        )
        pre_exp_avg, _pre_avg_raw = _typed_float_payload(
            parameter["pre_exp_avg"],
            f"{label}.pre_exp_avg",
            dtype="float32",
            shape=shape,
        )
        pre_exp_avg_sq, _pre_avg_sq_raw = _typed_float_payload(
            parameter["pre_exp_avg_sq"],
            f"{label}.pre_exp_avg_sq",
            dtype="float32",
            shape=shape,
        )
        post_exp_avg, _post_avg_raw = _typed_float_payload(
            parameter["post_exp_avg"],
            f"{label}.post_exp_avg",
            dtype="float32",
            shape=shape,
        )
        post_exp_avg_sq, _post_avg_sq_raw = _typed_float_payload(
            parameter["post_exp_avg_sq"],
            f"{label}.post_exp_avg_sq",
            dtype="float32",
            shape=shape,
        )
        replay_adam_transition(
            pre_parameters=pre_parameters,
            installed_gradient=parameter_installed,
            pre_exp_avg=pre_exp_avg,
            pre_exp_avg_sq=pre_exp_avg_sq,
            pre_step=parameter["pre_step"],
            post_parameters=post_parameters,
            post_exp_avg=post_exp_avg,
            post_exp_avg_sq=post_exp_avg_sq,
            post_step=parameter["post_step"],
        )
        pre_parameter_bytes.extend(pre_raw)
        offset += count
    if offset != len(installed):
        raise VerifierError("Adam parameter layout does not consume the gradient")
    actual_pre_parameter_sha256 = hashlib.sha256(pre_parameter_bytes).hexdigest()
    if not hmac.compare_digest(
        actual_pre_parameter_sha256, pre_parameter_sha256
    ):
        raise VerifierError("pre-parameter hash mismatch")


def verify_chunk_evidence(value: Any) -> dict[str, Any]:
    """Independently verify one complete producer-compatible chunk payload."""
    chunk = _exact_mapping(value, _CHUNK_FIELDS, "chunk evidence")
    content_sha256 = _binding_sha256(
        chunk["content_sha256"], "chunk content hash"
    )
    content = {
        key: item for key, item in chunk.items() if key != "content_sha256"
    }
    expected_content_sha256 = hashlib.sha256(
        canonical_json_bytes(content)
    ).hexdigest()
    if not hmac.compare_digest(content_sha256, expected_content_sha256):
        raise VerifierError("chunk content hash mismatch")
    if chunk["schema_version"] != CHUNK_EVIDENCE_SCHEMA_VERSION:
        raise VerifierError("chunk evidence schema version mismatch")
    chunk_index = _nonnegative_int(chunk["chunk_index"], "chunk index")
    _nonempty_string(chunk["torch_version"], "chunk Torch version")

    decisions, trajectory_order, by_trajectory, expected_folds = (
        _validate_chunk_decisions(chunk["decisions"], chunk_index=chunk_index)
    )
    _verify_chunk_baseline(
        chunk["baseline"],
        decisions=decisions,
        trajectory_order=trajectory_order,
        by_trajectory=by_trajectory,
        expected_folds=expected_folds,
    )
    names, shapes, counts, installed, pre_parameter_sha256 = (
        _verify_chunk_gradients(chunk["gradients"], decisions=decisions)
    )
    _verify_chunk_adam(
        chunk["adam"],
        names=names,
        shapes=shapes,
        counts=counts,
        installed=installed,
        pre_parameter_sha256=pre_parameter_sha256,
    )
    return {
        "chunk_index": chunk_index,
        "content_sha256": content_sha256,
        "decision_count": len(decisions),
        "fold_count": FOLD_COUNT,
        "parameter_count": len(installed),
        "schema_version": CHUNK_EVIDENCE_SCHEMA_VERSION,
        "trajectory_count": len(trajectory_order),
    }


def _canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _canonical_digest_streaming(value: Any) -> str:
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    try:
        for fragment in encoder.iterencode(value):
            digest.update(fragment.encode("ascii"))
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise VerifierError("value is not canonical JSON") from exc
    digest.update(b"\n")
    return digest.hexdigest()


def _reject_json_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerifierError("canonical JSON contains a duplicate key")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise VerifierError(f"canonical JSON contains {value}")


def _read_bounded_file(path: Path, *, label: str, limit: int) -> bytes:
    try:
        stat = path.lstat()
    except OSError as exc:
        raise VerifierError(f"{label} is missing or unreadable") from exc
    if path.is_symlink() or not path.is_file():
        raise VerifierError(f"{label} must be a regular non-symlink file")
    if stat.st_size > limit:
        raise VerifierError(f"{label} exceeds the byte bound")
    try:
        with path.open("rb") as handle:
            payload = handle.read(limit + 1)
    except OSError as exc:
        raise VerifierError(f"{label} is unreadable") from exc
    if len(payload) > limit or len(payload) != stat.st_size:
        raise VerifierError(f"{label} exceeds the byte bound or changed while read")
    return payload


def _parse_canonical_json(payload: bytes, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload,
            object_pairs_hook=_reject_json_pairs,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerifierError(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict) or payload != canonical_json_bytes(value):
        raise VerifierError(f"{label} is not canonical JSON")
    return value


def _process_is_alive(process_id: int) -> bool:
    if process_id == os.getpid():
        return True
    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _validate_lease_owner(value: Any, label: str) -> dict[str, Any]:
    owner = _exact_mapping(
        value,
        {"acquired_at_ns", "process_id", "token"},
        label,
    )
    process_id = _nonnegative_int(owner["process_id"], f"{label} process ID")
    acquired_at_ns = _nonnegative_int(
        owner["acquired_at_ns"], f"{label} acquisition coordinate"
    )
    if process_id == 0 or acquired_at_ns == 0:
        raise VerifierError(f"{label} coordinates must be positive")
    if (
        not isinstance(owner["token"], str)
        or _OWNER_TOKEN_RE.fullmatch(owner["token"]) is None
    ):
        raise VerifierError(f"{label} token is invalid")
    return owner


def _validate_unbound_execution_identity(value: Any) -> dict[str, str]:
    identity = _exact_mapping(
        value,
        {
            "authorization_sha256",
            "logical_execution_id",
            "registration_sha256",
            "request_sha256",
        },
        "lease execution identity",
    )
    for name in ("authorization_sha256", "registration_sha256", "request_sha256"):
        _binding_sha256(identity[name], f"lease execution identity {name}")
    logical_id = identity["logical_execution_id"]
    if not isinstance(logical_id, str) or _IDENTITY_RE.fullmatch(logical_id) is None:
        raise VerifierError("lease logical execution identity is invalid")
    return identity


@contextlib.contextmanager
def _hold_inactive_execution_lease(path: Path):
    def checked_stat() -> os.stat_result:
        try:
            observed = path.lstat()
        except OSError as exc:
            raise VerifierError("execution lease is missing or unreadable") from exc
        reparse_flag = getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if (
            stat_module.S_ISLNK(observed.st_mode)
            or not stat_module.S_ISREG(observed.st_mode)
            or bool(getattr(observed, "st_file_attributes", 0) & reparse_flag)
            or observed.st_size > 64 * 1024
        ):
            raise VerifierError("execution lease is not a bounded regular file")
        return observed

    initial_stat = checked_stat()
    descriptor = None
    handle = None
    locked = False
    try:
        flags = os.O_RDWR | getattr(os, "O_BINARY", 0)
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        handle = os.fdopen(descriptor, "r+b", buffering=0)
        descriptor = None
        opened_stat = os.fstat(handle.fileno())
        if not os.path.samestat(initial_stat, opened_stat):
            raise VerifierError("execution lease changed before lock acquisition")
        current_stat = checked_stat()
        if not os.path.samestat(opened_stat, current_stat):
            raise VerifierError("execution lease path changed before lock acquisition")
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
        except OSError as exc:
            raise VerifierError("execution lease is still locked") from exc
        handle.seek(0)
        payload = handle.read(64 * 1024 + 1)
        locked_stat = os.fstat(handle.fileno())
        if (
            not os.path.samestat(opened_stat, locked_stat)
            or len(payload) > 64 * 1024
            or len(payload) != locked_stat.st_size
        ):
            raise VerifierError("execution lease changed while read")
        lease = _parse_canonical_json(payload, label="execution lease")
        lease = _exact_mapping(
            lease,
            {"identity", "owner", "reclaimed_owner", "schema_version"},
            "execution lease",
        )
        if lease["schema_version"] != LEASE_SCHEMA_VERSION:
            raise VerifierError("execution lease schema mismatch")
        identity = _validate_unbound_execution_identity(lease["identity"])
        owner = _validate_lease_owner(lease["owner"], "execution lease owner")
        if lease["reclaimed_owner"] is not None:
            _validate_lease_owner(
                lease["reclaimed_owner"], "reclaimed execution lease owner"
            )
        try:
            owner_alive = _process_is_alive(owner["process_id"])
        except BaseException as exc:
            raise VerifierError("execution lease owner liveness is ambiguous") from exc
        if owner_alive is not False:
            raise VerifierError("execution lease owner is still alive")
        yield identity
        final_stat = checked_stat()
        if not os.path.samestat(opened_stat, final_stat):
            raise VerifierError("execution lease path changed during verification")
    except VerifierError:
        raise
    except OSError as exc:
        raise VerifierError("execution lease is unreadable") from exc
    finally:
        if locked and handle is not None:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        if handle is not None:
            handle.close()
        elif descriptor is not None:
            os.close(descriptor)


def _load_canonical_document(
    output: Path, filename: str, *, label: str | None = None
) -> dict[str, Any]:
    return _parse_canonical_json(
        _read_bounded_file(
            output / PurePosixPath(filename),
            label=label or filename,
            limit=MAX_ARTIFACT_BYTES,
        ),
        label=label or filename,
    )


def _canonical_relative_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise VerifierError(f"{label} is not a canonical relative path")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or "." in pure.parts
        or ".." in pure.parts
        or str(pure) != value
        or "\n" in value
        or "\r" in value
    ):
        raise VerifierError(f"{label} is not a canonical relative path")
    return value


def _absolute_path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\n" in value or "\r" in value:
        raise VerifierError(f"{label} is not an absolute path")
    candidate = Path(value)
    if not candidate.is_absolute() or candidate.as_posix() != value:
        raise VerifierError(f"{label} is not a canonical absolute path")
    return value


def _expected_output_inventory() -> dict[str, Any]:
    return {
        "access_journal": ACCESS_JOURNAL_FILENAME,
        "artifact_manifest": MANIFEST_FILENAME,
        "authorization": AUTHORIZATION_FILENAME,
        "bootstrap": BOOTSTRAP_FILENAME,
        "chunk_evidence_pattern": "checkpoints/chunk_{index:04d}_evidence.json.gz",
        "checkpoint_pattern": "checkpoints/checkpoint_{index:04d}.json",
        "execution_lease": LEASE_FILENAME,
        "execution_request": EXECUTION_REQUEST_FILENAME,
        "external_approval": EXTERNAL_APPROVAL_FILENAME,
        "failure": FAILURE_FILENAME,
        "post_isolation": POST_ISOLATION_FILENAME,
        "pre_isolation": PRE_ISOLATION_FILENAME,
        "registration": REGISTRATION_FILENAME,
        "resource_ledger": RESOURCE_LEDGER_FILENAME,
        "source_preflight": SOURCE_PREFLIGHT_FILENAME,
        "terminal": TERMINAL_FILENAME,
        "terminal_intent": TERMINAL_INTENT_FILENAME,
    }


def _algorithm_controls() -> dict[str, Any]:
    return {
        "architecture": "state-conditioned-candidate-ranker-mlp-v1",
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
        "sampling": "family-first-then-conditional-v1",
    }


def _baseline_controls() -> dict[str, Any]:
    return {
        "feature_dim": BASELINE_FEATURE_DIM,
        "fit_trajectories_per_fold": FIT_TRAJECTORIES_PER_FOLD,
        "fold_count": FOLD_COUNT,
        "held_out_trajectories_per_fold": HELD_OUT_TRAJECTORIES_PER_FOLD,
        "prediction_bounds": [PREDICTION_MIN, PREDICTION_MAX],
        "ridge_coefficient": RIDGE_COEFFICIENT,
        "ridge_residual_atol": RIDGE_RESIDUAL_ATOL,
        "ridge_residual_rtol": RIDGE_RESIDUAL_RTOL,
        "scale": 1.0,
        "solver": "cpu-float64-cholesky-v1",
        "trajectory_weighting": "equal-trajectory-mean-squared-error-v1",
    }


def _expected_runtime_metadata() -> dict[str, Any]:
    return {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
        "algorithm": _algorithm_controls(),
        "authority": dict(_AUTHORITY),
        "baseline": _baseline_controls(),
        "baseline_feature_dim": BASELINE_FEATURE_DIM,
        "baseline_feature_schema_version": BASELINE_FEATURE_SCHEMA_VERSION,
        "device": "cpu",
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "fold_count": FOLD_COUNT,
        "rng": {"action_generator_seed": 0, "python_rng_seed": 0},
        "ridge_coefficient": RIDGE_COEFFICIENT,
        "schema_version": (
            "noncombat-cross-fitted-hierarchical-learning-runtime-v1"
        ),
    }


def _resource_limits() -> dict[str, int | float]:
    return {
        "charged_seconds": MAX_CHARGED_SECONDS,
        "environment_accesses": MAX_ENVIRONMENT_ACCESSES,
        "optimizer_updates": MAX_OPTIMIZER_UPDATES,
        "retained_decisions": MAX_RETAINED_DECISIONS,
        "stored_bytes": MAX_STORED_BYTES,
        "uncompressed_bytes": MAX_UNCOMPRESSED_BUNDLE_BYTES,
    }


def _zero_resources() -> dict[str, int | float]:
    return {
        "charged_seconds": 0.0,
        "environment_accesses": 0,
        "optimizer_updates": 0,
        "retained_decisions": 0,
        "stored_bytes": 0,
        "uncompressed_bytes": 0,
    }


def _expected_contract() -> dict[str, Any]:
    return {
        "algorithm": _algorithm_controls(),
        "authority": dict(_AUTHORITY),
        "baseline": _baseline_controls(),
        "cohort": {
            "chunk_count": CHUNK_COUNT,
            "episodes_per_chunk": TRAJECTORIES_PER_CHUNK,
            "evaluation_cohorts": [],
            "scheduled_trajectories": SCHEDULED_TRAJECTORIES,
            "selection": "tracked-fixed-tree-ascending-v1",
        },
        "environment": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v3",
            "ascension": 0,
            "device": "cpu",
        },
        "evaluation": {"authorized": False},
        "limits": {
            "max_artifact_bytes": MAX_ARTIFACT_BYTES,
            "max_charged_seconds": MAX_CHARGED_SECONDS,
            "max_decisions_per_episode": MAX_DECISIONS_PER_TRAJECTORY,
            "max_environment_accesses": MAX_ENVIRONMENT_ACCESSES,
            "max_optimizer_updates": MAX_OPTIMIZER_UPDATES,
            "max_retained_decisions": MAX_RETAINED_DECISIONS,
            "max_stored_bytes": MAX_STORED_BYTES,
            "max_uncompressed_bytes": MAX_UNCOMPRESSED_BUNDLE_BYTES,
        },
        "lifecycle": {
            "maximum_post_start_resumes": 1,
            "resume_scope": "same-identity-chunk-or-checkpoint-boundary-v2",
            "seed_journal": "append-only-write-ahead-per-access-v1",
        },
        "runtime_metadata": _expected_runtime_metadata(),
        "schema_version": CONTRACT_SCHEMA_VERSION,
    }


def _validate_file_binding(value: Any, label: str) -> dict[str, Any]:
    binding = _exact_mapping(value, {"path", "sha256", "size_bytes"}, label)
    _absolute_path(binding["path"], f"{label}.path")
    _binding_sha256(binding["sha256"], f"{label}.sha256")
    _nonnegative_int(binding["size_bytes"], f"{label}.size_bytes")
    return binding


def _validate_checkpoint_tree_identity(value: Any) -> dict[str, Any]:
    identity = _exact_mapping(
        value,
        {"file_count", "root", "sha256", "size_bytes"},
        "production checkpoint identity",
    )
    _absolute_path(identity["root"], "production checkpoint root")
    _nonnegative_int(identity["file_count"], "production checkpoint file count")
    _binding_sha256(identity["sha256"], "production checkpoint sha256")
    _nonnegative_int(identity["size_bytes"], "production checkpoint size")
    return identity


def _validate_isolation_identity(value: Any) -> dict[str, Any]:
    identity = _exact_mapping(
        value,
        {"communication_mod_config", "production_checkpoints"},
        "isolation identity",
    )
    identity["communication_mod_config"] = _validate_file_binding(
        identity["communication_mod_config"], "CommunicationMod configuration"
    )
    identity["production_checkpoints"] = _validate_checkpoint_tree_identity(
        identity["production_checkpoints"]
    )
    return identity


def _validate_native_identity(value: Any) -> dict[str, Any]:
    identity = _exact_mapping(
        value,
        {
            "adapter_api_version",
            "dll_directories",
            "module",
            "provenance",
            "provenance_sha256",
        },
        "native identity",
    )
    if identity["adapter_api_version"] != "sts-lightspeed-noncombat-adapter-v3":
        raise VerifierError("native adapter API mismatch")
    directories = _exact_list(identity["dll_directories"], "native DLL directories")
    normalized_directories = [
        _absolute_path(item, "native DLL directory") for item in directories
    ]
    if normalized_directories != sorted(set(normalized_directories)):
        raise VerifierError("native DLL directories are not unique and sorted")
    identity["dll_directories"] = normalized_directories
    identity["module"] = _validate_file_binding(identity["module"], "native module")
    if not isinstance(identity["provenance"], Mapping) or not identity["provenance"]:
        raise VerifierError("native provenance must be a nonempty mapping")
    provenance = dict(identity["provenance"])
    build = provenance.get("build")
    if (
        not isinstance(build, Mapping)
        or build.get("adapter_api_version") != identity["adapter_api_version"]
        or provenance.get("module_sha256") != identity["module"]["sha256"]
    ):
        raise VerifierError("native provenance binding mismatch")
    if identity["provenance_sha256"] != _canonical_digest(provenance):
        raise VerifierError("native provenance digest mismatch")
    return identity


def _validate_seed_inventory(
    value: Any,
    repository_commit: str,
    *,
    max_rows: int = 1_000_000,
) -> dict[str, Any]:
    fields = {
        "canonical_search_start",
        "excluded_seed_count",
        "excluded_seeds",
        "repository_commit",
        "reserved_seed_ranges",
        "row_count",
        "rows",
        "schema_version",
        "source_bindings",
        "source_count",
    }
    inventory = _exact_mapping(value, fields, "seed inventory")
    if (
        inventory["schema_version"] != SEED_INVENTORY_SCHEMA_VERSION
        or inventory["repository_commit"] != repository_commit
        or inventory["canonical_search_start"] != 0
        or type(inventory["canonical_search_start"]) is not int
    ):
        raise VerifierError("seed inventory identity mismatch")
    reserved_ranges = [
        {
            "end_inclusive": PREVIOUS_UNTOUCHED_HOLDOUT_END,
            "name": "previous_untouched_holdout",
            "start_inclusive": PREVIOUS_UNTOUCHED_HOLDOUT_START,
        }
    ]
    if inventory["reserved_seed_ranges"] != reserved_ranges:
        raise VerifierError("seed inventory reserved range mismatch")
    roles = {
        "canary",
        "consumed",
        "diagnostic",
        "holdout",
        "qualification",
        "reserved",
        "seed",
        "selected",
        "smoke",
        "training",
        "used",
    }
    rows = _exact_list(inventory["rows"], "seed inventory rows")
    if len(rows) > max_rows:
        raise VerifierError("seed inventory rows exceed the verifier bound")
    normalized_rows: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        row = _exact_mapping(
            raw,
            {"document_index", "json_path", "role", "seed", "source_path"},
            f"seed inventory rows[{index}]",
        )
        _nonnegative_int(row["document_index"], "seed document index")
        _nonnegative_int(row["seed"], "historical seed")
        if (
            not isinstance(row["json_path"], str)
            or not row["json_path"].startswith("/")
            or row["role"] not in roles
        ):
            raise VerifierError("seed inventory row identity mismatch")
        source_path = _canonical_relative_path(
            row["source_path"], "seed inventory source path"
        )
        if not source_path.startswith("reports/") or not source_path.endswith(
            (".json", ".jsonl", ".json.gz", ".jsonl.gz")
        ):
            raise VerifierError("seed inventory source format mismatch")
        normalized_rows.append(row)
    row_sort = lambda row: (
        row["seed"],
        row["source_path"],
        row["document_index"],
        row["json_path"],
        row["role"],
    )
    if normalized_rows != sorted(normalized_rows, key=row_sort):
        raise VerifierError("seed inventory rows are not canonical")
    if len({_canonical_digest(row) for row in normalized_rows}) != len(normalized_rows):
        raise VerifierError("seed inventory rows contain duplicates")

    bindings = _exact_list(
        inventory["source_bindings"], "seed inventory source bindings"
    )
    normalized_bindings: list[dict[str, Any]] = []
    for index, raw in enumerate(bindings):
        binding = _exact_mapping(
            raw,
            {
                "document_count",
                "format",
                "path",
                "row_count",
                "sha256",
                "size_bytes",
            },
            f"seed source binding[{index}]",
        )
        path = _canonical_relative_path(binding["path"], "seed source path")
        expected_format = next(
            (
                suffix
                for suffix in ("jsonl.gz", "json.gz", "jsonl", "json")
                if path.endswith("." + suffix)
            ),
            None,
        )
        if (
            not path.startswith("reports/")
            or binding["format"] != expected_format
            or _nonnegative_int(binding["document_count"], "seed document count") == 0
            or _nonnegative_int(binding["row_count"], "seed binding row count") == 0
            or _nonnegative_int(binding["size_bytes"], "seed binding size") == 0
        ):
            raise VerifierError("seed source binding mismatch")
        _binding_sha256(binding["sha256"], "seed source digest")
        normalized_bindings.append(binding)
    if [row["path"] for row in normalized_bindings] != sorted(
        {row["path"] for row in normalized_bindings}
    ):
        raise VerifierError("seed source bindings are not canonical")
    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in normalized_rows:
        rows_by_source.setdefault(row["source_path"], []).append(row)
    if set(rows_by_source) != {row["path"] for row in normalized_bindings}:
        raise VerifierError("seed rows and bindings differ")
    for binding in normalized_bindings:
        source_rows = rows_by_source[binding["path"]]
        if binding["row_count"] != len(source_rows) or any(
            row["document_index"] >= binding["document_count"]
            for row in source_rows
        ):
            raise VerifierError("seed source binding counts mismatch")

    excluded = sorted(
        {row["seed"] for row in normalized_rows}
        | set(
            range(
                PREVIOUS_UNTOUCHED_HOLDOUT_START,
                PREVIOUS_UNTOUCHED_HOLDOUT_END + 1,
            )
        )
    )
    if (
        inventory["excluded_seeds"] != excluded
        or inventory["excluded_seed_count"] != len(excluded)
        or inventory["row_count"] != len(normalized_rows)
        or inventory["source_count"] != len(normalized_bindings)
    ):
        raise VerifierError("seed inventory aggregate mismatch")
    return inventory


def _validate_schedule(value: Any, seed_inventory: Mapping[str, Any]) -> dict[str, Any]:
    schedule = _exact_mapping(
        value,
        {
            "canonical_search_start",
            "chunk_count",
            "chunks",
            "episodes_per_chunk",
            "inventory_sha256",
            "seeds",
            "seeds_sha256",
            "selection_schema_version",
        },
        "schedule",
    )
    seeds = _exact_list(schedule["seeds"], "scheduled seeds")
    normalized_seeds = [
        _nonnegative_int(seed, "scheduled seed") for seed in seeds
    ]
    if (
        len(normalized_seeds) != SCHEDULED_TRAJECTORIES
        or normalized_seeds != sorted(set(normalized_seeds))
        or normalized_seeds[-1] > 10_000_000
    ):
        raise VerifierError("schedule must contain 512 bounded ascending seeds")
    excluded = set(seed_inventory["excluded_seeds"])
    expected: list[int] = []
    candidate = 0
    while len(expected) < SCHEDULED_TRAJECTORIES:
        if candidate not in excluded:
            expected.append(candidate)
        candidate += 1
        if candidate > 10_000_001:
            raise VerifierError("fixed seed selection exceeds the verifier bound")
    chunks = [
        expected[index : index + TRAJECTORIES_PER_CHUNK]
        for index in range(0, SCHEDULED_TRAJECTORIES, TRAJECTORIES_PER_CHUNK)
    ]
    expected_schedule = {
        "canonical_search_start": 0,
        "chunk_count": CHUNK_COUNT,
        "chunks": chunks,
        "episodes_per_chunk": TRAJECTORIES_PER_CHUNK,
        "inventory_sha256": _canonical_digest(seed_inventory),
        "seeds": expected,
        "seeds_sha256": _canonical_digest(expected),
        "selection_schema_version": FRESH_SCHEDULE_SCHEMA_VERSION,
    }
    if schedule != expected_schedule:
        raise VerifierError("schedule differs from fixed 8x64 selection")
    return schedule


def _declared_source_rows(
    registration_schema_version: str = REGISTRATION_SCHEMA_VERSION,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if registration_schema_version not in {
        REGISTRATION_SCHEMA_VERSION,
        REGISTRATION_V2_SCHEMA_VERSION,
    }:
        raise VerifierError("registration schema mismatch")
    modules = [
        {"name": name, "path": path, "role": role}
        for name, path, role in _MODULE_SPECS
    ]
    dependencies = []
    for name, path, symbols in _PUBLIC_DEPENDENCY_SPECS:
        if (
            registration_schema_version == REGISTRATION_V2_SCHEMA_VERSION
            and name == "seed_inventory"
        ):
            symbols = _V2_SEED_INVENTORY_PUBLIC_SYMBOLS
        dependencies.append(
            {"name": name, "path": path, "public_symbols": list(symbols)}
        )
    return modules, dependencies


def _git_text(repo_root: Path, *arguments: str, label: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerifierError(f"{label} cannot be resolved from Git") from exc
    return completed.stdout.strip()


def _git_is_ancestor(
    repo_root: Path, ancestor: str, descendant: str, *, label: str
) -> None:
    try:
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, descendant],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise VerifierError(f"{label} cannot be checked") from exc
    if completed.returncode == 1:
        raise VerifierError(f"{label} mismatch")
    if completed.returncode != 0:
        raise VerifierError(f"{label} cannot be checked")


def _git_blob_bytes(
    repo_root: Path,
    commit: str,
    relative_path: str,
    *,
    label: str,
    limit: int,
) -> bytes:
    relative = _canonical_relative_path(relative_path, f"{label} path")
    object_name = f"{commit}:{relative}"
    size_text = _git_text(
        repo_root, "cat-file", "-s", object_name, label=label
    )
    try:
        size = int(size_text)
    except ValueError as exc:
        raise VerifierError(f"{label} Git blob size is invalid") from exc
    if size < 0 or size > limit:
        raise VerifierError(f"{label} exceeds the byte bound")
    try:
        completed = subprocess.run(
            ["git", "show", object_name],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerifierError(f"{label} cannot be read from Git") from exc
    if len(completed.stdout) != size:
        raise VerifierError(f"{label} Git blob changed while read")
    return completed.stdout


def _validate_source_inventory(
    value: Any,
    *,
    repo_root: Path,
    repository_commit: str,
    registration_schema_version: str,
) -> dict[str, Any]:
    inventory = _exact_mapping(
        value,
        {
            "inventory_sha256",
            "modules",
            "public_dependencies",
            "schema_version",
        },
        "source inventory",
    )
    if inventory["schema_version"] != SOURCE_INVENTORY_SCHEMA_VERSION:
        raise VerifierError("source inventory schema mismatch")
    declared_modules, declared_dependencies = _declared_source_rows(
        registration_schema_version
    )
    normalized_groups: list[list[dict[str, Any]]] = []
    for group_name, raw_group, declared, special_field in (
        ("modules", inventory["modules"], declared_modules, "role"),
        (
            "public dependencies",
            inventory["public_dependencies"],
            declared_dependencies,
            "public_symbols",
        ),
    ):
        rows = _exact_list(raw_group, f"source inventory {group_name}")
        if len(rows) != len(declared):
            raise VerifierError(f"source inventory {group_name} length mismatch")
        normalized: list[dict[str, Any]] = []
        for index, (raw, definition) in enumerate(zip(rows, declared, strict=True)):
            fields = {"name", "path", "sha256", "size_bytes", special_field}
            row = _exact_mapping(raw, fields, f"source {group_name}[{index}]")
            if any(row[name] != definition[name] for name in definition):
                raise VerifierError("source inventory declaration mismatch")
            relative = _canonical_relative_path(row["path"], "source path")
            _binding_sha256(row["sha256"], "source digest")
            size = _nonnegative_int(row["size_bytes"], "source size")
            payload = _git_blob_bytes(
                repo_root,
                repository_commit,
                relative,
                label=f"registered source {relative}",
                limit=MAX_ARTIFACT_BYTES,
            )
            if size != len(payload) or row["sha256"] != hashlib.sha256(
                payload
            ).hexdigest():
                raise VerifierError(f"source inventory bytes mismatch: {relative}")
            normalized.append(row)
        normalized_groups.append(normalized)
    body = {
        "modules": normalized_groups[0],
        "public_dependencies": normalized_groups[1],
        "schema_version": SOURCE_INVENTORY_SCHEMA_VERSION,
    }
    if inventory["inventory_sha256"] != _canonical_digest(body):
        raise VerifierError("source inventory body digest mismatch")
    return inventory


def _readiness_reports_path(value: Any, label: str) -> str:
    relative = _canonical_relative_path(value, label)
    if not PurePosixPath(relative).parts or not relative.startswith("reports/"):
        raise VerifierError(f"{label} must be a canonical reports path")
    return relative


def _validate_readiness_evidence(
    value: Any, *, source_commit: str
) -> dict[str, Any]:
    evidence = _exact_mapping(
        value,
        {
            "candidate_artifact",
            "publication_commit",
            "readiness_report",
            "verification_receipt",
        },
        "readiness evidence including verification receipt",
    )
    publication_commit = evidence["publication_commit"]
    if (
        not isinstance(publication_commit, str)
        or _COMMIT_RE.fullmatch(publication_commit) is None
    ):
        raise VerifierError("readiness publication commit mismatch")

    candidate = _exact_mapping(
        evidence["candidate_artifact"],
        {
            "canonical_sha256",
            "canonical_size_bytes",
            "encoding",
            "path",
            "sha256",
            "size_bytes",
        },
        "readiness candidate artifact binding",
    )
    candidate["path"] = _readiness_reports_path(
        candidate["path"], "readiness candidate artifact path"
    )
    if PurePosixPath(candidate["path"]).name != READINESS_CANDIDATE_FILENAME:
        raise VerifierError("readiness candidate artifact filename mismatch")
    if candidate["encoding"] != READINESS_CANDIDATE_ENCODING:
        raise VerifierError("readiness candidate artifact encoding mismatch")
    _binding_sha256(candidate["sha256"], "readiness candidate stored digest")
    _binding_sha256(
        candidate["canonical_sha256"], "readiness candidate canonical digest"
    )
    candidate["size_bytes"] = _positive_int(
        candidate["size_bytes"], "readiness candidate stored size"
    )
    candidate["canonical_size_bytes"] = _positive_int(
        candidate["canonical_size_bytes"], "readiness candidate canonical size"
    )
    if (
        candidate["size_bytes"] > MAX_READINESS_CANDIDATE_STORED_BYTES
        or candidate["canonical_size_bytes"]
        > MAX_READINESS_CANDIDATE_CANONICAL_BYTES
    ):
        raise VerifierError("readiness candidate artifact exceeds the byte bound")

    report = _exact_mapping(
        evidence["readiness_report"],
        {"path", "readiness_identity_sha256", "sha256", "size_bytes"},
        "readiness report binding",
    )
    report["path"] = _readiness_reports_path(
        report["path"], "readiness report path"
    )
    if PurePosixPath(report["path"]).name != READINESS_REPORT_FILENAME:
        raise VerifierError("readiness report filename mismatch")
    if PurePosixPath(report["path"]).parent != PurePosixPath(
        candidate["path"]
    ).parent:
        raise VerifierError("readiness report and candidate must be siblings")
    _binding_sha256(report["sha256"], "readiness report digest")
    _binding_sha256(
        report["readiness_identity_sha256"], "readiness report identity"
    )
    report["size_bytes"] = _positive_int(
        report["size_bytes"], "readiness report size"
    )
    if report["size_bytes"] > MAX_ARTIFACT_BYTES:
        raise VerifierError("readiness report exceeds the byte bound")

    receipt = _exact_mapping(
        evidence["verification_receipt"],
        {"path", "sha256", "size_bytes", "verification_receipt_sha256"},
        "readiness verification receipt binding",
    )
    receipt["path"] = _readiness_reports_path(
        receipt["path"], "readiness verification receipt path"
    )
    expected_receipt_path = (
        f"{READINESS_ATTEMPT_ROOT_PATH}/{source_commit}/"
        f"{READINESS_VERIFICATION_RECEIPT_FILENAME}"
    )
    if receipt["path"] != expected_receipt_path:
        raise VerifierError("readiness verification receipt path mismatch")
    _binding_sha256(receipt["sha256"], "readiness verification receipt digest")
    _binding_sha256(
        receipt["verification_receipt_sha256"],
        "readiness verification receipt identity",
    )
    receipt["size_bytes"] = _positive_int(
        receipt["size_bytes"], "readiness verification receipt size"
    )
    if receipt["size_bytes"] > MAX_ARTIFACT_BYTES:
        raise VerifierError("readiness verification receipt exceeds the byte bound")

    evidence["candidate_artifact"] = candidate
    evidence["readiness_report"] = report
    evidence["verification_receipt"] = receipt
    return evidence


def _validate_bound_payload(
    payload: bytes, binding: Mapping[str, Any], *, label: str
) -> None:
    if (
        len(payload) != binding["size_bytes"]
        or hashlib.sha256(payload).hexdigest() != binding["sha256"]
    ):
        raise VerifierError(f"{label} bytes mismatch")


def _readiness_authority() -> dict[str, bool]:
    return {name: False for name in READINESS_AUTHORITY_NAMES}


def _validate_readiness_authority(value: Any, label: str) -> dict[str, bool]:
    expected = _readiness_authority()
    authority = _exact_mapping(value, set(expected), label)
    if (
        any(type(enabled) is not bool for enabled in authority.values())
        or authority != expected
    ):
        raise VerifierError(f"{label} must remain all false")
    return authority


def _validate_readiness_report(
    value: Any,
    *,
    registration: Mapping[str, Any],
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    report = _exact_mapping(
        value,
        {
            "audit_id",
            "authority",
            "budget",
            "candidate_artifact_binding",
            "cohort",
            "decision",
            "eligibility",
            "gates",
            "limitations",
            "readiness_identity_sha256",
            "rehearsal",
            "schema_version",
            "source_binding",
            "source_commit",
        },
        "readiness report",
    )
    source_commit = registration["repository_commit"]
    if report["schema_version"] != READINESS_REPORT_SCHEMA_VERSION:
        raise VerifierError("readiness report schema mismatch")
    if report["source_commit"] != source_commit:
        raise VerifierError("readiness report source commit mismatch")
    report["authority"] = _validate_readiness_authority(
        report["authority"], "readiness report authority"
    )
    if report["decision"] != {
        "failed_gates": [],
        "reason": "go",
        "status": "go",
    }:
        raise VerifierError("readiness report is not go")
    eligibility = _exact_mapping(
        report["eligibility"],
        {"empirical_successor_registration_proposal_eligible"},
        "readiness eligibility",
    )
    if (
        type(
            eligibility["empirical_successor_registration_proposal_eligible"]
        )
        is not bool
        or eligibility["empirical_successor_registration_proposal_eligible"]
        is not True
    ):
        raise VerifierError("readiness report is not registration eligible")
    report["eligibility"] = eligibility
    expected_gates = {
        name: "passed"
        for name in (
            "artifact_binding",
            "budget_binding",
            "cohort_not_fresh",
            "control_plane_scaling",
            "rehearsal_boundary",
            "source_binding",
        )
    }
    if report["gates"] != expected_gates:
        raise VerifierError("readiness report gates did not all pass")
    _nonempty_string(report["audit_id"], "readiness audit identity")
    identity = report["readiness_identity_sha256"]
    _binding_sha256(identity, "readiness report identity")
    report_body = {
        key: item
        for key, item in report.items()
        if key != "readiness_identity_sha256"
    }
    if identity != _canonical_digest(report_body):
        raise VerifierError("readiness report identity mismatch")
    if identity != registration["readiness_evidence"]["readiness_report"][
        "readiness_identity_sha256"
    ]:
        raise VerifierError("registered readiness identity mismatch")

    candidate_binding = _exact_mapping(
        report["candidate_artifact_binding"],
        {
            "canonical_sha256",
            "canonical_size_bytes",
            "encoding",
            "path",
            "sha256",
            "size_bytes",
        },
        "readiness report candidate binding",
    )
    expected_candidate = dict(
        registration["readiness_evidence"]["candidate_artifact"]
    )
    expected_candidate["path"] = PurePosixPath(expected_candidate["path"]).name
    if candidate_binding != expected_candidate:
        raise VerifierError("readiness report candidate binding mismatch")

    source = _exact_mapping(
        report["source_binding"],
        {
            "bindings",
            "bindings_sha256",
            "head_commit",
            "origin_master_commit",
            "source_commit",
            "status",
            "tracked_clean",
        },
        "readiness source binding",
    )
    if (
        source["source_commit"] != source_commit
        or source["head_commit"] != source_commit
        or source["origin_master_commit"] != source_commit
        or source["status"] != "passed"
        or source["tracked_clean"] is not True
    ):
        raise VerifierError("readiness source binding identity mismatch")
    raw_bindings = _exact_list(
        source["bindings"], "readiness source binding rows"
    )
    if not raw_bindings:
        raise VerifierError("readiness source binding rows are empty")
    bindings: list[dict[str, Any]] = []
    roles: set[str] = set()
    paths: set[str] = set()
    for index, raw in enumerate(raw_bindings):
        row = _exact_mapping(
            raw,
            {"path", "role", "sha256", "size_bytes"},
            f"readiness source binding row[{index}]",
        )
        row["path"] = _canonical_relative_path(
            row["path"], "readiness source binding path"
        )
        row["role"] = _nonempty_string(
            row["role"], "readiness source binding role"
        )
        _binding_sha256(row["sha256"], "readiness source binding digest")
        row["size_bytes"] = _positive_int(
            row["size_bytes"], "readiness source binding size"
        )
        if row["role"] in roles or row["path"] in paths:
            raise VerifierError("readiness source binding roles or paths duplicate")
        roles.add(row["role"])
        paths.add(row["path"])
        payload = _git_blob_bytes(
            repo_root,
            source_commit,
            row["path"],
            label=f"readiness source binding {row['role']}",
            limit=MAX_ARTIFACT_BYTES,
        )
        _validate_bound_payload(
            payload, row, label=f"readiness source binding {row['role']}"
        )
        bindings.append(row)
    _binding_sha256(
        source["bindings_sha256"], "readiness source binding identity"
    )
    if source["bindings_sha256"] != _canonical_digest(bindings):
        raise VerifierError("readiness source binding digest mismatch")
    by_role = {row["role"]: row for row in bindings}

    inventory_by_name = {
        row["name"]: row
        for section in ("modules", "public_dependencies")
        for row in registration["source_inventory"][section]
    }
    required_roles = {
        "control_plane_source": inventory_by_name["control_plane"],
        "seed_inventory_source": inventory_by_name["seed_inventory"],
        "terminal_verifier_source": inventory_by_name["independent_verifier"],
    }
    for role, row in required_roles.items():
        expected = {
            "path": row["path"],
            "role": role,
            "sha256": row["sha256"],
            "size_bytes": row["size_bytes"],
        }
        if by_role.get(role) != expected:
            raise VerifierError(f"readiness source binding mismatch: {role}")
    successor_payload = _git_blob_bytes(
        repo_root,
        source_commit,
        SUCCESSOR_CONTRACT_PATH,
        label="readiness successor contract",
        limit=MAX_ARTIFACT_BYTES,
    )
    expected_successor = {
        "path": SUCCESSOR_CONTRACT_PATH,
        "role": "successor_contract",
        "sha256": hashlib.sha256(successor_payload).hexdigest(),
        "size_bytes": len(successor_payload),
    }
    if by_role.get("successor_contract") != expected_successor:
        raise VerifierError("readiness successor contract source binding mismatch")
    report["source_binding"] = {**source, "bindings": bindings}
    return report, by_role


def _validate_readiness_candidate(
    stored: bytes,
    *,
    binding: Mapping[str, Any],
    source_commit: str,
    source_bindings: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as stream:
            canonical = stream.read(MAX_READINESS_CANDIDATE_CANONICAL_BYTES + 1)
            trailing = stream.read(1)
    except (EOFError, OSError, gzip.BadGzipFile) as exc:
        raise VerifierError(
            "readiness candidate deterministic gzip is invalid"
        ) from exc
    if len(canonical) > MAX_READINESS_CANDIDATE_CANONICAL_BYTES or trailing:
        raise VerifierError(
            "readiness candidate deterministic gzip exceeds canonical bound"
        )
    if (
        len(canonical) != binding["canonical_size_bytes"]
        or hashlib.sha256(canonical).hexdigest()
        != binding["canonical_sha256"]
    ):
        raise VerifierError(
            "readiness candidate deterministic gzip canonical binding mismatch"
        )
    if _deterministic_gzip(canonical) != stored:
        raise VerifierError(
            "readiness candidate deterministic gzip reconstruction mismatch"
        )
    candidate = _parse_canonical_json(canonical, label="readiness candidate")
    candidate = _exact_mapping(
        candidate,
        {
            "authority",
            "candidate_schedule",
            "consumed_cohort",
            "disjointness",
            "historical_seed_inventory",
            "schema_version",
            "source_commit",
        },
        "readiness candidate",
    )
    if candidate["schema_version"] != READINESS_CANDIDATE_SCHEMA_VERSION:
        raise VerifierError("readiness candidate schema mismatch")
    if candidate["source_commit"] != source_commit:
        raise VerifierError("readiness candidate source commit mismatch")
    candidate["authority"] = _validate_readiness_authority(
        candidate["authority"], "readiness candidate authority"
    )

    inventory = _validate_seed_inventory(
        candidate["historical_seed_inventory"],
        source_commit,
        max_rows=MAX_READINESS_CANDIDATE_CANONICAL_BYTES // 64,
    )
    raw_schedule = _exact_mapping(
        candidate["candidate_schedule"],
        {
            "canonical_search_start",
            "inventory_sha256",
            "schema_version",
            "seed_count",
            "seeds",
        },
        "readiness candidate schedule",
    )
    seeds = [
        _nonnegative_int(seed, "readiness candidate seed")
        for seed in _exact_list(raw_schedule["seeds"], "readiness candidate seeds")
    ]
    if (
        raw_schedule["schema_version"] != FRESH_SCHEDULE_SCHEMA_VERSION
        or raw_schedule["canonical_search_start"] != 0
        or type(raw_schedule["canonical_search_start"]) is not int
        or raw_schedule["seed_count"] != SCHEDULED_TRAJECTORIES
        or type(raw_schedule["seed_count"]) is not int
        or len(seeds) != SCHEDULED_TRAJECTORIES
        or seeds != sorted(set(seeds))
    ):
        raise VerifierError("readiness candidate schedule identity mismatch")
    inventory_digest = _canonical_digest_streaming(inventory)
    excluded = set(inventory["excluded_seeds"])
    expected_seeds: list[int] = []
    seed = 0
    while len(expected_seeds) < SCHEDULED_TRAJECTORIES:
        if seed not in excluded:
            expected_seeds.append(seed)
        seed += 1
        if seed > 10_000_001:
            raise VerifierError("readiness candidate schedule exceeds the bound")
    expected_fresh = {
        "canonical_search_start": 0,
        "inventory_sha256": inventory_digest,
        "schema_version": FRESH_SCHEDULE_SCHEMA_VERSION,
        "seed_count": SCHEDULED_TRAJECTORIES,
        "seeds": expected_seeds,
    }
    if raw_schedule != expected_fresh:
        raise VerifierError("readiness candidate schedule differs from inventory")

    consumed = _exact_mapping(
        candidate["consumed_cohort"],
        {
            "registration_binding",
            "registration_id",
            "seed_count",
            "seeds",
            "seeds_sha256",
        },
        "readiness consumed cohort",
    )
    _nonempty_string(consumed["registration_id"], "consumed registration identity")
    consumed_binding = _exact_mapping(
        consumed["registration_binding"],
        {"path", "sha256", "size_bytes"},
        "consumed registration binding",
    )
    consumed_binding["path"] = _readiness_reports_path(
        consumed_binding["path"], "consumed registration path"
    )
    _binding_sha256(
        consumed_binding["sha256"], "consumed registration digest"
    )
    consumed_binding["size_bytes"] = _positive_int(
        consumed_binding["size_bytes"], "consumed registration size"
    )
    expected_consumed_source = source_bindings.get("consumed_registration")
    if expected_consumed_source is None or consumed_binding != {
        key: expected_consumed_source[key]
        for key in ("path", "sha256", "size_bytes")
    }:
        raise VerifierError("consumed cohort registration binding mismatch")
    consumed_seeds = [
        _nonnegative_int(seed, "consumed cohort seed")
        for seed in _exact_list(consumed["seeds"], "consumed cohort seeds")
    ]
    if (
        consumed["seed_count"] != SCHEDULED_TRAJECTORIES
        or type(consumed["seed_count"]) is not int
        or len(consumed_seeds) != SCHEDULED_TRAJECTORIES
        or consumed_seeds != sorted(set(consumed_seeds))
        or consumed["seeds_sha256"] != _canonical_digest(consumed_seeds)
    ):
        raise VerifierError("readiness consumed cohort identity mismatch")
    collisions = sorted(set(seeds) & set(consumed_seeds))
    disjointness = _exact_mapping(
        candidate["disjointness"],
        {"collision_count", "collisions", "status"},
        "readiness candidate disjointness",
    )
    disjointness["collision_count"] = _nonnegative_int(
        disjointness["collision_count"],
        "readiness candidate disjointness collision count",
    )
    disjointness["collisions"] = [
        _nonnegative_int(seed, "readiness candidate disjointness collision")
        for seed in _exact_list(
            disjointness["collisions"],
            "readiness candidate disjointness collisions",
        )
    ]
    if disjointness["status"] not in {"failed", "passed"}:
        raise VerifierError("readiness candidate disjointness status mismatch")
    expected_disjointness = {
        "collision_count": len(collisions),
        "collisions": collisions,
        "status": "passed" if not collisions else "failed",
    }
    if disjointness != expected_disjointness or collisions:
        raise VerifierError("readiness candidate collision check failed")

    candidate["historical_seed_inventory"] = inventory
    candidate["candidate_schedule"] = raw_schedule
    candidate["consumed_cohort"] = {
        **consumed,
        "registration_binding": consumed_binding,
        "seeds": consumed_seeds,
    }
    candidate["disjointness"] = disjointness
    return candidate


def _validate_readiness_verification_receipt(
    value: Any,
    *,
    registration: Mapping[str, Any],
    report: Mapping[str, Any],
    candidate: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = _exact_mapping(
        value,
        {
            "attempt_sha256",
            "intended_output_dir",
            "publication_bindings",
            "schema_version",
            "source_commit",
            "staging_dir",
            "status",
            "verification",
            "verification_receipt_sha256",
        },
        "readiness verification receipt",
    )
    identity = receipt["verification_receipt_sha256"]
    _binding_sha256(identity, "readiness verification receipt identity")
    body = {
        key: item
        for key, item in receipt.items()
        if key != "verification_receipt_sha256"
    }
    if identity != _canonical_digest(body):
        raise VerifierError("readiness verification receipt digest mismatch")
    registered_receipt = registration["readiness_evidence"][
        "verification_receipt"
    ]
    if identity != registered_receipt["verification_receipt_sha256"]:
        raise VerifierError("registered verification receipt identity mismatch")
    _binding_sha256(receipt["attempt_sha256"], "readiness attempt identity")
    _nonempty_string(receipt["intended_output_dir"], "readiness intended output")
    _nonempty_string(receipt["staging_dir"], "readiness staging directory")
    source_commit = registration["repository_commit"]
    if (
        receipt["schema_version"]
        != READINESS_VERIFICATION_RECEIPT_SCHEMA_VERSION
        or receipt["source_commit"] != source_commit
        or receipt["status"] != "staging_independently_verified"
    ):
        raise VerifierError("readiness verification receipt status mismatch")

    expected_names = {
        READINESS_CANDIDATE_FILENAME,
        READINESS_REPORT_FILENAME,
        READINESS_REPORT_MARKDOWN_FILENAME,
    }
    publication = _exact_mapping(
        receipt["publication_bindings"],
        expected_names,
        "verification receipt publication bindings",
    )
    normalized_publication: dict[str, dict[str, Any]] = {}
    for name in sorted(expected_names):
        item = _exact_mapping(
            publication[name],
            {"sha256", "size_bytes"},
            f"verification receipt publication binding {name}",
        )
        _binding_sha256(
            item["sha256"], f"verification receipt publication digest {name}"
        )
        item["size_bytes"] = _positive_int(
            item["size_bytes"], f"verification receipt publication size {name}"
        )
        ceiling = (
            MAX_READINESS_CANDIDATE_STORED_BYTES
            if name == READINESS_CANDIDATE_FILENAME
            else MAX_ARTIFACT_BYTES
        )
        if item["size_bytes"] > ceiling:
            raise VerifierError(
                f"verification receipt publication binding {name} exceeds bound"
            )
        normalized_publication[name] = item
    candidate_binding = registration["readiness_evidence"]["candidate_artifact"]
    report_binding = registration["readiness_evidence"]["readiness_report"]
    if normalized_publication[READINESS_CANDIDATE_FILENAME] != {
        "sha256": candidate_binding["sha256"],
        "size_bytes": candidate_binding["size_bytes"],
    }:
        raise VerifierError("verification receipt candidate publication binding mismatch")
    if normalized_publication[READINESS_REPORT_FILENAME] != {
        "sha256": report_binding["sha256"],
        "size_bytes": report_binding["size_bytes"],
    }:
        raise VerifierError("verification receipt report publication binding mismatch")

    verification = _exact_mapping(
        receipt["verification"],
        {
            "candidate_inventory_sha256",
            "decision",
            "independent_inventory_sha256",
            "proposal_eligible",
            "readiness_identity_sha256",
            "source_commit",
            "status",
        },
        "readiness verification summary",
    )
    if type(verification["proposal_eligible"]) is not bool:
        raise VerifierError(
            "readiness verification proposal eligibility must be boolean"
        )
    expected_verification = {
        "candidate_inventory_sha256": candidate_binding["sha256"],
        "decision": "go",
        "independent_inventory_sha256": candidate["candidate_schedule"][
            "inventory_sha256"
        ],
        "proposal_eligible": True,
        "readiness_identity_sha256": report["readiness_identity_sha256"],
        "source_commit": source_commit,
        "status": "verified",
    }
    if verification != expected_verification:
        raise VerifierError(
            "readiness verification receipt is not the verified go summary"
        )
    receipt["publication_bindings"] = normalized_publication
    receipt["verification"] = verification
    return receipt


def _verify_readiness_bound_registration(
    registration: Mapping[str, Any], *, repo_root: Path
) -> None:
    source_commit = registration["repository_commit"]
    evidence = registration["readiness_evidence"]
    publication_commit = evidence["publication_commit"]
    pushed_head = _git_text(
        repo_root, "rev-parse", "origin/master", label="pushed HEAD"
    )
    if _COMMIT_RE.fullmatch(pushed_head) is None:
        raise VerifierError("pushed HEAD is not a full Git commit")
    _git_is_ancestor(
        repo_root,
        source_commit,
        publication_commit,
        label="readiness source commit publication ancestry",
    )
    _git_is_ancestor(
        repo_root,
        publication_commit,
        pushed_head,
        label="pushed readiness publication ancestry",
    )
    _git_is_ancestor(
        repo_root,
        source_commit,
        pushed_head,
        label="registered source ancestry",
    )

    receipt_binding = evidence["verification_receipt"]
    receipt_payload = _git_blob_bytes(
        repo_root,
        publication_commit,
        receipt_binding["path"],
        label="readiness verification receipt",
        limit=MAX_ARTIFACT_BYTES,
    )
    _validate_bound_payload(
        receipt_payload,
        receipt_binding,
        label="readiness verification receipt binding",
    )
    receipt = _parse_canonical_json(
        receipt_payload, label="readiness verification receipt"
    )

    report_binding = evidence["readiness_report"]
    report_payload = _git_blob_bytes(
        repo_root,
        publication_commit,
        report_binding["path"],
        label="readiness report",
        limit=MAX_ARTIFACT_BYTES,
    )
    _validate_bound_payload(
        report_payload, report_binding, label="readiness report binding"
    )
    report, source_bindings = _validate_readiness_report(
        _parse_canonical_json(report_payload, label="readiness report"),
        registration=registration,
        repo_root=repo_root,
    )

    candidate_binding = evidence["candidate_artifact"]
    candidate_payload = _git_blob_bytes(
        repo_root,
        publication_commit,
        candidate_binding["path"],
        label="readiness candidate artifact",
        limit=MAX_READINESS_CANDIDATE_STORED_BYTES,
    )
    _validate_bound_payload(
        candidate_payload,
        candidate_binding,
        label="readiness candidate artifact binding",
    )
    candidate = _validate_readiness_candidate(
        candidate_payload,
        binding=candidate_binding,
        source_commit=source_commit,
        source_bindings=source_bindings,
    )

    fresh = candidate["candidate_schedule"]
    seeds = fresh["seeds"]
    expected_schedule = {
        "canonical_search_start": fresh["canonical_search_start"],
        "chunk_count": CHUNK_COUNT,
        "chunks": [
            seeds[index : index + TRAJECTORIES_PER_CHUNK]
            for index in range(0, len(seeds), TRAJECTORIES_PER_CHUNK)
        ],
        "episodes_per_chunk": TRAJECTORIES_PER_CHUNK,
        "inventory_sha256": fresh["inventory_sha256"],
        "seeds": seeds,
        "seeds_sha256": _canonical_digest(seeds),
        "selection_schema_version": fresh["schema_version"],
    }
    if registration["schedule"] != expected_schedule:
        raise VerifierError("registration schedule differs from readiness candidate")
    consumed = candidate["consumed_cohort"]
    expected_cohort = {
        "candidate_seed_count": len(seeds),
        "candidate_seeds_sha256": _canonical_digest(seeds),
        "collision_count": 0,
        "collisions": [],
        "consumed_seed_count": len(consumed["seeds"]),
        "consumed_seeds_sha256": _canonical_digest(consumed["seeds"]),
        "status": "passed",
    }
    if report["cohort"] != expected_cohort:
        raise VerifierError("readiness report cohort summary mismatch")
    _validate_readiness_verification_receipt(
        receipt,
        registration=registration,
        report=report,
        candidate=candidate,
    )


def _validate_registration(
    value: Any, *, output: Path, repo_root: Path
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise VerifierError("registration must be a mapping")
    schema_version = value.get("schema_version")
    common_fields = {
        "authority",
        "contract",
        "isolation_identity",
        "native_identity",
        "output_inventory",
        "output_root",
        "pushed_remote_ref",
        "registration_id",
        "repository_commit",
        "runtime_identity",
        "schedule",
        "schema_version",
        "source_inventory",
    }
    if schema_version == REGISTRATION_SCHEMA_VERSION:
        registration_fields = common_fields | {"seed_inventory"}
    elif schema_version == REGISTRATION_V2_SCHEMA_VERSION:
        registration_fields = common_fields | {"readiness_evidence"}
    else:
        raise VerifierError("registration schema mismatch")
    registration = _exact_mapping(
        value,
        registration_fields,
        "registration",
    )
    if (
        registration["authority"] != _AUTHORITY
        or registration["contract"] != _expected_contract()
        or registration["pushed_remote_ref"] != "origin/master"
        or registration["output_inventory"] != _expected_output_inventory()
    ):
        raise VerifierError("registration contract or authority mismatch")
    registration_id = registration["registration_id"]
    if (
        not isinstance(registration_id, str)
        or _IDENTITY_RE.fullmatch(registration_id) is None
    ):
        raise VerifierError("registration identity mismatch")
    commit = registration["repository_commit"]
    if not isinstance(commit, str) or _COMMIT_RE.fullmatch(commit) is None:
        raise VerifierError("registration repository commit mismatch")
    registered_output = _absolute_path(registration["output_root"], "output root")
    if os.path.normcase(str(Path(registered_output).resolve())) != os.path.normcase(
        str(output)
    ):
        raise VerifierError("registration output root mismatch")
    registration["source_inventory"] = _validate_source_inventory(
        registration["source_inventory"],
        repo_root=repo_root,
        repository_commit=commit,
        registration_schema_version=schema_version,
    )
    if schema_version == REGISTRATION_SCHEMA_VERSION:
        registration["seed_inventory"] = _validate_seed_inventory(
            registration["seed_inventory"], commit
        )
        registration["schedule"] = _validate_schedule(
            registration["schedule"], registration["seed_inventory"]
        )
    else:
        registration["readiness_evidence"] = _validate_readiness_evidence(
            registration["readiness_evidence"], source_commit=commit
        )
        _verify_readiness_bound_registration(registration, repo_root=repo_root)
    runtime_identity = _exact_mapping(
        registration["runtime_identity"],
        {"device", "python_executable", "python_version", "torch_version"},
        "runtime identity",
    )
    if runtime_identity["device"] != "cpu":
        raise VerifierError("runtime device must be cpu")
    _absolute_path(runtime_identity["python_executable"], "Python executable")
    for name in ("python_version", "torch_version"):
        _nonempty_string(runtime_identity[name], f"runtime {name}")
    registration["runtime_identity"] = runtime_identity
    registration["native_identity"] = _validate_native_identity(
        registration["native_identity"]
    )
    registration["isolation_identity"] = _validate_isolation_identity(
        registration["isolation_identity"]
    )
    return registration


def _validate_request(
    value: Any, registration: Mapping[str, Any]
) -> dict[str, Any]:
    registration_sha256 = _canonical_digest(registration)
    contract = registration["contract"]
    body = {
        "authority": dict(_AUTHORITY),
        "native_identity": registration["native_identity"],
        "operations": {
            "baseline_fitting": "four-fold-cross-fitted-ridge-v1",
            "environment_construction": True,
            "native_loading": True,
            "optimizer_updates_maximum": MAX_OPTIMIZER_UPDATES,
            "policy_training": True,
        },
        "output_root": registration["output_root"],
        "registration_id": registration["registration_id"],
        "registration_sha256": registration_sha256,
        "repository_commit": registration["repository_commit"],
        "request_id": registration["registration_id"] + ":execution-request-v1",
        "requested_execution_authority": dict(_EXECUTION_AUTHORITY),
        "resources": contract["limits"],
        "resume": contract["lifecycle"],
        "runtime_identity": registration["runtime_identity"],
        "schedule": registration["schedule"],
        "schema_version": EXECUTION_REQUEST_SCHEMA_VERSION,
        "source_inventory_sha256": registration["source_inventory"][
            "inventory_sha256"
        ],
    }
    expected = {**body, "request_sha256": _canonical_digest(body)}
    request = _exact_mapping(value, set(expected), "execution request")
    if request != expected:
        raise VerifierError("execution request binding mismatch")
    return request


def _validate_approval(
    value: Any,
    *,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    approval = _exact_mapping(
        value,
        {
            "approval_sha256",
            "approved_at",
            "approved_request_sha256",
            "provenance",
            "schema_version",
            "verbatim_approval_text",
        },
        "external approval",
    )
    provenance = _exact_mapping(
        approval["provenance"],
        {"message_id", "source", "task_id"},
        "approval provenance",
    )
    if provenance["source"] != "external-human-message":
        raise VerifierError("approval provenance is not external human input")
    for name in ("message_id", "task_id"):
        _nonempty_string(provenance[name], f"approval provenance {name}")
    _nonempty_string(approval["approved_at"], "approval timestamp")
    approval_text = _nonempty_string(
        approval["verbatim_approval_text"], "approval text"
    )
    if (
        approval["schema_version"] != EXTERNAL_APPROVAL_SCHEMA_VERSION
        or approval["approved_request_sha256"] != request["request_sha256"]
        or request["request_sha256"] not in approval_text
    ):
        raise VerifierError("external approval request binding mismatch")
    body = {key: item for key, item in approval.items() if key != "approval_sha256"}
    if approval["approval_sha256"] != _canonical_digest(body):
        raise VerifierError("external approval body digest mismatch")
    return approval


def _validate_authorization(
    value: Any,
    *,
    registration: Mapping[str, Any],
    request: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, str]]:
    body = {
        "approval": approval,
        "authorization_id": registration["registration_id"] + ":authorization-v1",
        "authority": dict(_EXECUTION_AUTHORITY),
        "registration_id": registration["registration_id"],
        "registration_sha256": request["registration_sha256"],
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
    }
    expected = {**body, "authorization_sha256": _canonical_digest(body)}
    authorization = _exact_mapping(value, set(expected), "authorization")
    if authorization != expected:
        raise VerifierError("authorization binding mismatch")
    identity = {
        "authorization_sha256": authorization["authorization_sha256"],
        "logical_execution_id": registration["registration_id"],
        "registration_sha256": request["registration_sha256"],
        "request_sha256": request["request_sha256"],
    }
    return authorization, identity


def _validate_source_preflight(
    value: Any, *, registration: Mapping[str, Any]
) -> dict[str, Any]:
    preflight = _exact_mapping(
        value,
        {
            "checks",
            "pushed_head_commit",
            "registration_sha256",
            "repository_commit",
            "schema_version",
        },
        "source preflight",
    )
    expected_checks = {
        "communication_mod_unchanged",
        "native_module_unchanged",
        "production_checkpoints_unchanged",
        "pushed_registration_exact",
        "pushed_source_exact",
        "runtime_identity_exact",
        "source_inventory_exact",
        "tracked_authorization_exact",
        "tracked_worktree_clean",
    }
    if registration["schema_version"] == REGISTRATION_V2_SCHEMA_VERSION:
        expected_checks.update(
            {
                "readiness_candidate_exact",
                "readiness_publication_exact",
                "readiness_source_exact",
                "readiness_verification_receipt_exact",
            }
        )
    checks = _exact_mapping(
        preflight["checks"], expected_checks, "source preflight checks"
    )
    if (
        preflight["schema_version"] != SOURCE_PREFLIGHT_SCHEMA_VERSION
        or not isinstance(preflight["pushed_head_commit"], str)
        or _COMMIT_RE.fullmatch(preflight["pushed_head_commit"]) is None
        or preflight["registration_sha256"] != _canonical_digest(registration)
        or preflight["repository_commit"] != registration["repository_commit"]
        or any(result is not True for result in checks.values())
    ):
        raise VerifierError("source preflight failed or is unbound")
    return preflight


def _validate_isolation_observation(
    value: Any,
    *,
    registration: Mapping[str, Any],
    phase: str,
) -> dict[str, Any]:
    observation = _exact_mapping(
        value,
        {
            "isolation_identity",
            "matches_registration",
            "phase",
            "registration_sha256",
            "schema_version",
        },
        f"{phase} isolation",
    )
    identity = _validate_isolation_identity(observation["isolation_identity"])
    if (
        observation["schema_version"] != ISOLATION_OBSERVATION_SCHEMA_VERSION
        or observation["phase"] != phase
        or observation["matches_registration"] is not True
        or identity != registration["isolation_identity"]
        or observation["registration_sha256"] != _canonical_digest(registration)
    ):
        raise VerifierError(f"{phase} isolation binding mismatch")
    return observation


def _validate_execution_identity(
    value: Any, expected: Mapping[str, str]
) -> dict[str, str]:
    identity = _exact_mapping(
        value,
        {
            "authorization_sha256",
            "logical_execution_id",
            "registration_sha256",
            "request_sha256",
        },
        "execution identity",
    )
    for name in ("authorization_sha256", "registration_sha256", "request_sha256"):
        _binding_sha256(identity[name], f"execution identity {name}")
    if identity != expected:
        raise VerifierError("execution identity binding mismatch")
    return identity


def _parse_canonical_json_lines(payload: bytes, *, label: str) -> list[dict[str, Any]]:
    if not payload or not payload.endswith(b"\n"):
        raise VerifierError(f"{label} is incomplete")
    lines = payload.splitlines(keepends=True)
    if len(lines) > 2_500:
        raise VerifierError(f"{label} event count exceeds the verifier bound")
    return [
        _parse_canonical_json(line, label=f"{label} line {index}")
        for index, line in enumerate(lines, start=1)
    ]


def _verify_access_journal(
    payload: bytes,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, str],
) -> dict[str, Any]:
    values = _parse_canonical_json_lines(payload, label="access journal")
    expected_header = {
        "event_index": 0,
        "identity": dict(identity),
        "kind": "journal_opened",
        "registration_sha256": _canonical_digest(registration),
        "schedule_sha256": registration["schedule"]["seeds_sha256"],
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
    }
    if values[0] != expected_header:
        raise VerifierError("access journal header mismatch")
    schedule = registration["schedule"]
    pending: dict[str, Any] | None = None
    debited = 0
    completed = 0
    primary_position = 0
    primary_completed = [0] * CHUNK_COUNT
    completed_chunks: set[int] = set()
    primary_interrupted_chunk: int | None = None
    resume_used = False
    resume_chunk: int | None = None
    resume_mode: str | None = None
    resume_position = 0
    resume_completed = 0
    resume_complete = False
    resume_failed = False
    terminal_access_failure = False
    resume_event_index: int | None = None
    last_status: str | None = None
    for event_index, event in enumerate(values[1:], start=1):
        if (
            event.get("event_index") != event_index
            or event.get("schema_version") != ACCESS_JOURNAL_SCHEMA_VERSION
        ):
            raise VerifierError("access journal event sequence or schema mismatch")
        kind = event.get("kind")
        if kind == "access_debited":
            event = _exact_mapping(
                event,
                {
                    "access_ordinal",
                    "attempt_ordinal",
                    "chunk_index",
                    "event_index",
                    "kind",
                    "schema_version",
                    "seed",
                    "status",
                },
                "access debit event",
            )
            if pending is not None:
                raise VerifierError("access journal contains overlapping accesses")
            if terminal_access_failure or resume_failed:
                raise VerifierError("access journal continues after a terminal access")
            access_ordinal = _nonnegative_int(
                event["access_ordinal"], "access ordinal"
            )
            attempt = _nonnegative_int(event["attempt_ordinal"], "attempt ordinal")
            chunk_index = _nonnegative_int(event["chunk_index"], "chunk index")
            seed = _nonnegative_int(event["seed"], "scheduled seed")
            if (
                access_ordinal != debited + 1
                or access_ordinal == 0
                or attempt not in {0, 1}
                or chunk_index >= CHUNK_COUNT
                or event["status"] != "debited"
            ):
                raise VerifierError("access debit coordinate mismatch")
            if attempt == 0:
                if primary_interrupted_chunk is not None:
                    raise VerifierError("primary access continues after interruption")
                if resume_used and not resume_complete:
                    raise VerifierError("primary access overlaps a replay")
                if primary_position >= SCHEDULED_TRAJECTORIES:
                    raise VerifierError("primary access exceeds the schedule")
                if (
                    chunk_index != primary_position // TRAJECTORIES_PER_CHUNK
                    or seed != schedule["seeds"][primary_position]
                ):
                    raise VerifierError("primary access differs from schedule")
                primary_position += 1
            else:
                if (
                    not resume_used
                    or resume_chunk is None
                    or resume_mode != "replay_uncheckpointed_chunk"
                    or resume_complete
                    or resume_failed
                    or resume_position >= TRAJECTORIES_PER_CHUNK
                    or chunk_index != resume_chunk
                    or seed != schedule["chunks"][resume_chunk][resume_position]
                ):
                    raise VerifierError("resume access differs from its fixed chunk")
                resume_position += 1
            pending = {
                "access_ordinal": access_ordinal,
                "attempt_ordinal": attempt,
                "chunk_index": chunk_index,
                "seed": seed,
            }
            debited += 1
            continue
        if kind == "access_terminal":
            event = _exact_mapping(
                event,
                {
                    "access_ordinal",
                    "attempt_ordinal",
                    "chunk_index",
                    "event_index",
                    "kind",
                    "schema_version",
                    "seed",
                    "status",
                },
                "access terminal event",
            )
            coordinate = {
                "access_ordinal": event["access_ordinal"],
                "attempt_ordinal": event["attempt_ordinal"],
                "chunk_index": event["chunk_index"],
                "seed": event["seed"],
            }
            if pending is None or coordinate != pending:
                raise VerifierError("access terminal does not match its debit")
            status = event["status"]
            if status not in {"completed", "failed", "infrastructure_interrupted"}:
                raise VerifierError("access terminal status mismatch")
            attempt = pending["attempt_ordinal"]
            chunk_index = pending["chunk_index"]
            if status == "completed":
                completed += 1
                if attempt == 0:
                    primary_completed[chunk_index] += 1
                    if primary_completed[chunk_index] == TRAJECTORIES_PER_CHUNK:
                        completed_chunks.add(chunk_index)
                else:
                    resume_completed += 1
                    if resume_completed == TRAJECTORIES_PER_CHUNK:
                        resume_complete = True
                        completed_chunks.add(chunk_index)
                        primary_position = max(
                            primary_position,
                            (chunk_index + 1) * TRAJECTORIES_PER_CHUNK,
                        )
            elif status == "infrastructure_interrupted":
                if attempt == 0:
                    primary_interrupted_chunk = chunk_index
                else:
                    resume_failed = True
            else:
                terminal_access_failure = True
            last_status = status
            pending = None
            continue
        if kind == "resume_started":
            event = _exact_mapping(
                event,
                {
                    "attempt_ordinal",
                    "chunk_index",
                    "event_index",
                    "kind",
                    "mode",
                    "schema_version",
                    "status",
                },
                "resume marker",
            )
            if pending is not None or resume_used or terminal_access_failure:
                raise VerifierError("resume marker is not eligible")
            chunk_index = _nonnegative_int(event["chunk_index"], "resume chunk")
            mode = event["mode"]
            if (
                mode not in {"continue_after_checkpoint", "replay_uncheckpointed_chunk"}
                or event["attempt_ordinal"] != 1
                or event["status"] != "resume_used"
            ):
                raise VerifierError("resume marker coordinate mismatch")
            if mode == "replay_uncheckpointed_chunk":
                inferred_partial = (
                    primary_position > 0
                    and primary_position % TRAJECTORIES_PER_CHUNK != 0
                    and chunk_index == primary_position // TRAJECTORIES_PER_CHUNK
                )
                inferred_complete = (
                    chunk_index in completed_chunks
                    and primary_position
                    == (chunk_index + 1) * TRAJECTORIES_PER_CHUNK
                )
                if primary_interrupted_chunk is not None:
                    if chunk_index != primary_interrupted_chunk:
                        raise VerifierError("resume marker interrupted chunk mismatch")
                elif not (inferred_partial or inferred_complete):
                    raise VerifierError("resume lacks an uncheckpointed chunk")
                if any(index not in completed_chunks for index in range(chunk_index)):
                    raise VerifierError("resume skips an incomplete earlier chunk")
                resume_complete = False
            else:
                expected_chunk = primary_position // TRAJECTORIES_PER_CHUNK
                if (
                    primary_interrupted_chunk is not None
                    or debited == 0
                    or primary_position % TRAJECTORIES_PER_CHUNK != 0
                    or chunk_index != expected_chunk
                    or chunk_index >= CHUNK_COUNT
                    or chunk_index in completed_chunks
                    or any(index not in completed_chunks for index in range(chunk_index))
                ):
                    raise VerifierError("checkpoint-boundary resume coordinate mismatch")
                resume_complete = True
            resume_used = True
            resume_chunk = chunk_index
            resume_mode = mode
            resume_event_index = event_index
            primary_interrupted_chunk = None
            continue
        raise VerifierError("access journal event kind mismatch")
    if debited > MAX_ENVIRONMENT_ACCESSES:
        raise VerifierError("access journal exceeds the environment-access limit")
    resume_candidate = primary_interrupted_chunk
    if pending is not None:
        if pending["attempt_ordinal"] == 0:
            resume_candidate = pending["chunk_index"]
        else:
            resume_failed = True
    return {
        "completed_accesses": completed,
        "completed_chunk_indices": sorted(completed_chunks),
        "debited_accesses": debited,
        "events": values,
        "last_access_status": last_status,
        "pending_access": pending,
        "primary_next_position": primary_position,
        "resume_candidate_chunk_index": resume_candidate,
        "resume_chunk_index": resume_chunk,
        "resume_complete": resume_complete,
        "resume_event_index": resume_event_index,
        "resume_failed": resume_failed,
        "resume_mode": resume_mode,
        "resume_used": resume_used,
        "terminal_access_failure": terminal_access_failure,
    }


def _normalize_resources(value: Any) -> dict[str, int | float]:
    resources = _exact_mapping(value, set(_RESOURCE_FIELDS), "resource prefix")
    limits = _resource_limits()
    normalized: dict[str, int | float] = {}
    for name in _RESOURCE_FIELDS:
        item = resources[name]
        if name in _INTEGER_RESOURCE_FIELDS:
            normalized[name] = _nonnegative_int(item, f"resource {name}")
        else:
            numeric = _finite_number(item, "resource charged_seconds")
            if numeric < 0.0:
                raise VerifierError("charged seconds must be nonnegative")
            normalized[name] = numeric
        if normalized[name] > limits[name]:
            raise VerifierError(f"resource {name} exceeds its limit")
    return normalized


def _verify_resource_ledger(
    payload: bytes, *, identity: Mapping[str, str]
) -> dict[str, Any]:
    events = _parse_canonical_json_lines(payload, label="resource ledger")
    header = {
        "identity": dict(identity),
        "kind": "resource_ledger_opened",
        "limits": _resource_limits(),
        "resources": _zero_resources(),
        "revision": 0,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }
    if events[0] != header:
        raise VerifierError("resource ledger header mismatch")
    previous = header
    previous_resources = _zero_resources()
    for revision, event in enumerate(events[1:], start=1):
        event = _exact_mapping(
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
        if (
            event["schema_version"] != RESOURCE_LEDGER_SCHEMA_VERSION
            or event["kind"] != "resource_prefix_advanced"
            or event["revision"] != revision
            or event["previous_event_sha256"] != _canonical_digest(previous)
        ):
            raise VerifierError("resource ledger sequence or hash-chain mismatch")
        reason = _nonempty_string(event["reason"], "resource ledger reason")
        resources = _normalize_resources(event["resources"])
        if any(resources[name] < previous_resources[name] for name in _RESOURCE_FIELDS):
            raise VerifierError("resource ledger is not monotonic")
        if resources == previous_resources:
            if (
                reason != "terminal-attempt-charge"
                or previous.get("reason") == "terminal-attempt-charge"
            ):
                raise VerifierError("resource ledger revision did not advance")
        event["resources"] = resources
        previous = event
        previous_resources = resources
    return {
        "events": events,
        "resources": previous_resources,
        "revision": len(events) - 1,
    }


def _validate_opaque_binding(value: Any, label: str) -> dict[str, Any]:
    binding = _exact_mapping(value, {"payload", "sha256", "size_bytes"}, label)
    if not isinstance(binding["payload"], Mapping):
        raise VerifierError(f"{label} payload must be a mapping")
    payload = dict(binding["payload"])
    encoded = canonical_json_bytes(payload)
    if (
        binding["sha256"] != hashlib.sha256(encoded).hexdigest()
        or binding["size_bytes"] != len(encoded)
        or len(encoded) > MAX_ARTIFACT_BYTES
    ):
        raise VerifierError(f"{label} body digest or size mismatch")
    binding["payload"] = payload
    return binding


def _decode_generator_state(value: Any, label: str) -> bytes:
    payload = _exact_mapping(
        value, {"data_base64", "data_sha256", "dtype", "shape"}, label
    )
    shape = payload["shape"]
    if (
        payload["dtype"] != "uint8"
        or not isinstance(shape, list)
        or len(shape) != 1
        or isinstance(shape[0], bool)
        or not isinstance(shape[0], int)
        or shape[0] <= 0
        or shape[0] > MAX_BINARY_PAYLOAD_BYTES
    ):
        raise VerifierError(f"{label} shape or dtype mismatch")
    encoded = payload["data_base64"]
    if not isinstance(encoded, str) or len(encoded) != 4 * ((shape[0] + 2) // 3):
        raise VerifierError(f"{label} base64 length mismatch")
    try:
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError) as exc:
        raise VerifierError(f"{label} base64 mismatch") from exc
    if (
        len(raw) != shape[0]
        or base64.b64encode(raw).decode("ascii") != encoded
        or hashlib.sha256(raw).hexdigest() != payload["data_sha256"]
    ):
        raise VerifierError(f"{label} byte digest mismatch")
    return raw


def _validate_python_rng_state(value: Any, *, budget: list[int]) -> Any:
    budget[0] -= 1
    if budget[0] < 0:
        raise VerifierError("Python RNG state exceeds the structural bound")
    if isinstance(value, Mapping):
        node = _exact_mapping(value, {"items", "type"}, "Python RNG tuple")
        if node["type"] != "tuple":
            raise VerifierError("Python RNG tuple type mismatch")
        items = _exact_list(node["items"], "Python RNG tuple items")
        return {
            "items": [
                _validate_python_rng_state(item, budget=budget) for item in items
            ],
            "type": "tuple",
        }
    if value is None or (type(value) is int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    raise VerifierError("Python RNG state contains an unsupported value")


def _validate_runtime_checkpoint(value: Any, label: str) -> dict[str, Any]:
    checkpoint = _exact_mapping(
        value,
        {
            "action_generator_state",
            "checkpoint_sha256",
            "coordinates",
            "model",
            "optimizer",
            "python_rng_state",
            "runtime_metadata",
            "schema_version",
        },
        label,
    )
    body = {
        key: item for key, item in checkpoint.items() if key != "checkpoint_sha256"
    }
    if (
        checkpoint["schema_version"] != RUNTIME_CHECKPOINT_SCHEMA_VERSION
        or checkpoint["runtime_metadata"] != _expected_runtime_metadata()
        or checkpoint["checkpoint_sha256"] != _canonical_digest(body)
    ):
        raise VerifierError(f"{label} schema, metadata, or body digest mismatch")
    action_state = _decode_generator_state(
        checkpoint["action_generator_state"], f"{label}.action_generator_state"
    )
    python_state = _validate_python_rng_state(
        checkpoint["python_rng_state"], budget=[10_000]
    )
    coordinates = _exact_mapping(
        checkpoint["coordinates"],
        {
            "completed_decisions",
            "completed_episodes",
            "next_chunk_index",
            "optimizer_updates",
        },
        f"{label}.coordinates",
    )
    normalized_coordinates = {
        name: _nonnegative_int(item, f"{label}.coordinates.{name}")
        for name, item in coordinates.items()
    }
    if (
        normalized_coordinates["next_chunk_index"]
        != normalized_coordinates["optimizer_updates"]
        or normalized_coordinates["completed_episodes"]
        != normalized_coordinates["optimizer_updates"] * TRAJECTORIES_PER_CHUNK
        or normalized_coordinates["optimizer_updates"] > MAX_OPTIMIZER_UPDATES
        or normalized_coordinates["completed_decisions"] > MAX_RETAINED_DECISIONS
    ):
        raise VerifierError(f"{label} coordinate identity mismatch")

    model_rows = _exact_list(checkpoint["model"], f"{label}.model")
    if not model_rows:
        raise VerifierError(f"{label} model is empty")
    model: list[dict[str, Any]] = []
    for index, raw in enumerate(model_rows):
        row = _exact_mapping(raw, {"name", "tensor"}, f"{label}.model[{index}]")
        name = _nonempty_string(row["name"], f"{label}.model[{index}].name")
        values, tensor_bytes, dtype, shape = _decode_float_payload_details(
            row["tensor"], f"{label}.model[{index}].tensor", max_bytes=MAX_BINARY_PAYLOAD_BYTES
        )
        if dtype != "float32" or not values:
            raise VerifierError(f"{label} model tensors must be nonempty float32")
        model.append(
            {
                "name": name,
                "shape": shape,
                "tensor": row["tensor"],
                "tensor_bytes": tensor_bytes,
            }
        )
    names = [row["name"] for row in model]
    if len(set(names)) != len(names):
        raise VerifierError(f"{label} model parameter names are not unique")

    optimizer = _exact_mapping(
        checkpoint["optimizer"],
        {"betas", "epsilon", "learning_rate", "parameters", "weight_decay"},
        f"{label}.optimizer",
    )
    if {
        "betas": optimizer["betas"],
        "epsilon": optimizer["epsilon"],
        "learning_rate": optimizer["learning_rate"],
        "weight_decay": optimizer["weight_decay"],
    } != {
        "betas": [ADAM_BETA1, ADAM_BETA2],
        "epsilon": ADAM_EPSILON,
        "learning_rate": ADAM_LEARNING_RATE,
        "weight_decay": 0.0,
    }:
        raise VerifierError(f"{label} Adam controls mismatch")
    optimizer_rows = _exact_list(
        optimizer["parameters"], f"{label}.optimizer.parameters"
    )
    if len(optimizer_rows) != len(model):
        raise VerifierError(f"{label} optimizer/model layout mismatch")
    normalized_optimizer: list[dict[str, Any]] = []
    for index, (raw, model_row) in enumerate(
        zip(optimizer_rows, model, strict=True)
    ):
        row = _exact_mapping(
            raw,
            {"exp_avg", "exp_avg_sq", "initialized", "name", "step"},
            f"{label}.optimizer.parameters[{index}]",
        )
        if row["name"] != model_row["name"] or type(row["initialized"]) is not bool:
            raise VerifierError(f"{label} optimizer parameter identity mismatch")
        step = _nonnegative_int(row["step"], f"{label} optimizer step")
        if not row["initialized"]:
            if step != 0 or row["exp_avg"] is not None or row["exp_avg_sq"] is not None:
                raise VerifierError(f"{label} uninitialized Adam state mismatch")
            avg_bytes = sq_bytes = None
        else:
            if step == 0:
                raise VerifierError(f"{label} initialized Adam step mismatch")
            _avg_values, avg_bytes, avg_dtype, avg_shape = (
                _decode_float_payload_details(
                    row["exp_avg"],
                    f"{label}.optimizer.parameters[{index}].exp_avg",
                    max_bytes=MAX_BINARY_PAYLOAD_BYTES,
                )
            )
            _sq_values, sq_bytes, sq_dtype, sq_shape = (
                _decode_float_payload_details(
                    row["exp_avg_sq"],
                    f"{label}.optimizer.parameters[{index}].exp_avg_sq",
                    max_bytes=MAX_BINARY_PAYLOAD_BYTES,
                )
            )
            if (
                avg_dtype != "float32"
                or sq_dtype != "float32"
                or avg_shape != model_row["shape"]
                or sq_shape != model_row["shape"]
            ):
                raise VerifierError(f"{label} Adam tensor layout mismatch")
        normalized_optimizer.append(
            {
                "exp_avg_bytes": avg_bytes,
                "exp_avg_sq_bytes": sq_bytes,
                "initialized": row["initialized"],
                "name": row["name"],
                "step": step,
            }
        )
    return {
        "action_generator_bytes": action_state,
        "coordinates": normalized_coordinates,
        "model": model,
        "optimizer": normalized_optimizer,
        "python_rng_state": python_state,
        "raw": checkpoint,
    }


def _verify_bootstrap(
    value: Any,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, str],
) -> dict[str, Any]:
    bootstrap = _exact_mapping(
        value,
        {
            "authority",
            "bootstrap_sha256",
            "identity",
            "registration_sha256",
            "resource_use",
            "runtime_checkpoint",
            "schema_version",
        },
        "bootstrap",
    )
    if (
        bootstrap["schema_version"] != BOOTSTRAP_SCHEMA_VERSION
        or bootstrap["authority"] != _AUTHORITY
        or bootstrap["identity"] != identity
        or bootstrap["registration_sha256"] != _canonical_digest(registration)
        or _normalize_resources(bootstrap["resource_use"]) != _zero_resources()
    ):
        raise VerifierError("bootstrap identity, authority, or resources mismatch")
    body = {
        key: item for key, item in bootstrap.items() if key != "bootstrap_sha256"
    }
    if bootstrap["bootstrap_sha256"] != _canonical_digest(body):
        raise VerifierError("bootstrap body digest mismatch")
    binding = _validate_opaque_binding(
        bootstrap["runtime_checkpoint"], "bootstrap runtime checkpoint"
    )
    runtime = _validate_runtime_checkpoint(
        binding["payload"], "bootstrap runtime checkpoint payload"
    )
    if runtime["coordinates"] != {
        "completed_decisions": 0,
        "completed_episodes": 0,
        "next_chunk_index": 0,
        "optimizer_updates": 0,
    } or any(row["initialized"] for row in runtime["optimizer"]):
        raise VerifierError("bootstrap runtime is not at the zero coordinate")
    return {"raw": bootstrap, "runtime": runtime}


def _bounded_gzip_document(
    path: Path, *, binding: Mapping[str, Any], label: str
) -> tuple[dict[str, Any], int, int]:
    expected_fields = {
        "encoding",
        "path",
        "stored_sha256",
        "stored_size_bytes",
        "uncompressed_sha256",
        "uncompressed_size_bytes",
    }
    normalized = _exact_mapping(binding, expected_fields, f"{label} binding")
    if normalized["encoding"] != "deterministic-gzip-canonical-json-v1":
        raise VerifierError(f"{label} encoding mismatch")
    _canonical_relative_path(normalized["path"], f"{label} path")
    stored_size = _nonnegative_int(
        normalized["stored_size_bytes"], f"{label} stored size"
    )
    uncompressed_size = _nonnegative_int(
        normalized["uncompressed_size_bytes"], f"{label} uncompressed size"
    )
    if (
        stored_size == 0
        or stored_size > MAX_ARTIFACT_BYTES
        or uncompressed_size > MAX_ARTIFACT_BYTES
    ):
        raise VerifierError(f"{label} exceeds the artifact byte bound")
    stored = _read_bounded_file(path, label=label, limit=MAX_ARTIFACT_BYTES)
    canonical = verify_deterministic_gzip(
        stored,
        {
            "canonical_sha256": normalized["uncompressed_sha256"],
            "canonical_size_bytes": uncompressed_size,
            "compression": GZIP_COMPRESSION_IDENTITY,
            "sha256": normalized["stored_sha256"],
            "size_bytes": stored_size,
        },
        max_stored_bytes=MAX_ARTIFACT_BYTES,
        max_uncompressed_bytes=MAX_ARTIFACT_BYTES,
    )
    return _parse_canonical_json(canonical, label=label), stored_size, uncompressed_size


def _verify_chunk_artifact(
    output: Path,
    *,
    binding: Mapping[str, Any],
    chunk_index: int,
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    expected_path = f"checkpoints/chunk_{chunk_index + 1:04d}_evidence.json.gz"
    if binding.get("path") != expected_path:
        raise VerifierError("chunk evidence path mismatch")
    document, stored_size, uncompressed_size = _bounded_gzip_document(
        output / PurePosixPath(expected_path),
        binding=binding,
        label=f"chunk {chunk_index} evidence",
    )
    document = _exact_mapping(
        document,
        {"chunk_index", "evidence", "runtime_checkpoint", "schema_version"},
        f"chunk {chunk_index} evidence document",
    )
    if (
        document["schema_version"] != CHUNK_EVIDENCE_DOCUMENT_SCHEMA_VERSION
        or document["chunk_index"] != chunk_index
    ):
        raise VerifierError("chunk evidence wrapper coordinate mismatch")
    evidence = _exact_mapping(
        document["evidence"], _CHUNK_FIELDS, f"chunk {chunk_index} evidence"
    )
    verified = verify_chunk_evidence(evidence)
    if verified["chunk_index"] != chunk_index:
        raise VerifierError("verified chunk coordinate mismatch")
    trajectory_seeds: dict[str, int] = {}
    for row in evidence["decisions"]:
        trajectory_id = row["trajectory_id"]
        seed = row["seed"]
        if trajectory_id in trajectory_seeds and trajectory_seeds[trajectory_id] != seed:
            raise VerifierError("chunk trajectory seed identity mismatch")
        trajectory_seeds[trajectory_id] = seed
    if sorted(trajectory_seeds.values()) != registration["schedule"]["chunks"][
        chunk_index
    ]:
        raise VerifierError("chunk evidence seeds differ from registered schedule")
    if evidence["torch_version"] != registration["runtime_identity"]["torch_version"]:
        raise VerifierError("chunk Torch version differs from registration")
    runtime_binding = _validate_opaque_binding(
        document["runtime_checkpoint"],
        f"chunk {chunk_index} evidence runtime checkpoint",
    )
    _validate_runtime_checkpoint(
        runtime_binding["payload"],
        f"chunk {chunk_index} evidence runtime checkpoint payload",
    )
    return {
        "evidence": evidence,
        "runtime_checkpoint": runtime_binding,
        "stored_size_bytes": stored_size,
        "uncompressed_size_bytes": uncompressed_size,
        "verified": verified,
    }


def _payload_bytes(
    value: Any, *, dtype: str, shape: Sequence[int], label: str
) -> bytes:
    _values, raw, actual_dtype, actual_shape = _decode_float_payload_details(
        value, label, max_bytes=MAX_BINARY_PAYLOAD_BYTES
    )
    if actual_dtype != dtype or actual_shape != tuple(shape):
        raise VerifierError(f"{label} dtype or shape mismatch")
    return raw


def _verify_rng_diagnostic_chain(
    pre_runtime: Mapping[str, Any],
    evidence: Mapping[str, Any],
    post_runtime: Mapping[str, Any],
) -> None:
    decisions = evidence["decisions"]
    if not decisions:
        raise VerifierError("chunk evidence contains no RNG diagnostics")
    expected = hashlib.sha256(pre_runtime["action_generator_bytes"]).hexdigest()
    for index, row in enumerate(decisions):
        states = row["diagnostic"]["action_generator_state_sha256"]
        if states["before_family"] != expected:
            raise VerifierError(f"action RNG continuity mismatch at decision {index}")
        expected = states["after_conditional"]
    if expected != hashlib.sha256(post_runtime["action_generator_bytes"]).hexdigest():
        raise VerifierError("action RNG checkpoint continuity mismatch")
    if pre_runtime["python_rng_state"] != post_runtime["python_rng_state"]:
        raise VerifierError("unused Python RNG state changed across a chunk")


def _verify_runtime_transition(
    *,
    pre_runtime: Mapping[str, Any],
    evidence: Mapping[str, Any],
    post_runtime: Mapping[str, Any],
    chunk_index: int,
    prior_decisions: int,
) -> int:
    adam_rows = evidence["adam"]["parameters"]
    names = evidence["gradients"]["parameter_names"]
    shapes = evidence["gradients"]["parameter_shapes"]
    if (
        len(adam_rows) != len(names)
        or [row["name"] for row in pre_runtime["model"]] != names
        or [row["name"] for row in post_runtime["model"]] != names
        or [row["name"] for row in pre_runtime["optimizer"]] != names
        or [row["name"] for row in post_runtime["optimizer"]] != names
    ):
        raise VerifierError("runtime/evidence parameter order mismatch")
    pre_parameter_bytes = bytearray()
    for index, (adam_row, shape) in enumerate(zip(adam_rows, shapes, strict=True)):
        shape_tuple = tuple(shape)
        pre_model = pre_runtime["model"][index]
        post_model = post_runtime["model"][index]
        pre_optimizer = pre_runtime["optimizer"][index]
        post_optimizer = post_runtime["optimizer"][index]
        if pre_model["shape"] != shape_tuple or post_model["shape"] != shape_tuple:
            raise VerifierError("runtime/evidence parameter shape mismatch")
        evidence_pre = _payload_bytes(
            adam_row["pre_parameter"],
            dtype="float32",
            shape=shape_tuple,
            label=f"chunk {chunk_index} Adam pre parameter {index}",
        )
        evidence_post = _payload_bytes(
            adam_row["post_parameter"],
            dtype="float32",
            shape=shape_tuple,
            label=f"chunk {chunk_index} Adam post parameter {index}",
        )
        if pre_model["tensor_bytes"] != evidence_pre:
            raise VerifierError("previous model checkpoint differs from Adam pre-state")
        if post_model["tensor_bytes"] != evidence_post:
            raise VerifierError("post model checkpoint differs from Adam post-state")
        pre_parameter_bytes.extend(evidence_pre)
        pre_avg = _payload_bytes(
            adam_row["pre_exp_avg"],
            dtype="float32",
            shape=shape_tuple,
            label=f"chunk {chunk_index} Adam pre first moment {index}",
        )
        pre_sq = _payload_bytes(
            adam_row["pre_exp_avg_sq"],
            dtype="float32",
            shape=shape_tuple,
            label=f"chunk {chunk_index} Adam pre second moment {index}",
        )
        post_avg = _payload_bytes(
            adam_row["post_exp_avg"],
            dtype="float32",
            shape=shape_tuple,
            label=f"chunk {chunk_index} Adam post first moment {index}",
        )
        post_sq = _payload_bytes(
            adam_row["post_exp_avg_sq"],
            dtype="float32",
            shape=shape_tuple,
            label=f"chunk {chunk_index} Adam post second moment {index}",
        )
        if pre_optimizer["initialized"]:
            if (
                pre_optimizer["step"] != adam_row["pre_step"]
                or pre_optimizer["exp_avg_bytes"] != pre_avg
                or pre_optimizer["exp_avg_sq_bytes"] != pre_sq
            ):
                raise VerifierError("previous Adam checkpoint differs from evidence")
        elif (
            adam_row["pre_step"] != 0
            or any(pre_avg)
            or any(pre_sq)
        ):
            raise VerifierError("initial Adam evidence is not zero")
        if (
            not post_optimizer["initialized"]
            or post_optimizer["step"] != adam_row["post_step"]
            or post_optimizer["exp_avg_bytes"] != post_avg
            or post_optimizer["exp_avg_sq_bytes"] != post_sq
        ):
            raise VerifierError("post Adam checkpoint differs from evidence")
    if hashlib.sha256(pre_parameter_bytes).hexdigest() != evidence["gradients"][
        "pre_parameter_sha256"
    ]:
        raise VerifierError("runtime pre-parameter digest differs from evidence")
    expected_pre_coordinates = {
        "completed_decisions": prior_decisions,
        "completed_episodes": chunk_index * TRAJECTORIES_PER_CHUNK,
        "next_chunk_index": chunk_index,
        "optimizer_updates": chunk_index,
    }
    next_decisions = prior_decisions + len(evidence["decisions"])
    expected_post_coordinates = {
        "completed_decisions": next_decisions,
        "completed_episodes": (chunk_index + 1) * TRAJECTORIES_PER_CHUNK,
        "next_chunk_index": chunk_index + 1,
        "optimizer_updates": chunk_index + 1,
    }
    if (
        pre_runtime["coordinates"] != expected_pre_coordinates
        or post_runtime["coordinates"] != expected_post_coordinates
    ):
        raise VerifierError("runtime checkpoint coordinates differ from evidence")
    _verify_rng_diagnostic_chain(pre_runtime, evidence, post_runtime)
    return next_decisions


def _verify_journal_prefix(
    value: Any,
    *,
    journal_bytes: bytes,
    registration: Mapping[str, Any],
    identity: Mapping[str, str],
) -> dict[str, Any]:
    binding = _exact_mapping(value, {"sha256", "size_bytes"}, "journal prefix")
    size = _nonnegative_int(binding["size_bytes"], "journal prefix size")
    if size == 0 or size > len(journal_bytes):
        raise VerifierError("journal prefix size mismatch")
    prefix = journal_bytes[:size]
    if binding["sha256"] != hashlib.sha256(prefix).hexdigest():
        raise VerifierError("journal prefix digest mismatch")
    return _verify_access_journal(
        prefix, registration=registration, identity=identity
    )


def _verify_checkpoint_chain(
    output: Path,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, str],
    journal_bytes: bytes,
    journal: Mapping[str, Any],
    ledger: Mapping[str, Any],
    bootstrap: Mapping[str, Any],
) -> list[dict[str, Any]]:
    directory = output / "checkpoints"
    if directory.exists():
        if directory.is_symlink() or not directory.is_dir():
            raise VerifierError("checkpoint directory must be a non-symlink directory")
        try:
            entries = list(directory.iterdir())
        except OSError as exc:
            raise VerifierError("checkpoint directory is unreadable") from exc
        if any(entry.is_symlink() or not entry.is_file() for entry in entries):
            raise VerifierError("checkpoint inventory contains a non-file or symlink")
        names = sorted(entry.name for entry in entries)
    else:
        names = []
    checkpoint_numbers = sorted(
        int(match.group(1))
        for name in names
        if (match := re.fullmatch(r"checkpoint_([0-9]{4})\.json", name))
    )
    evidence_numbers = sorted(
        int(match.group(1))
        for name in names
        if (match := re.fullmatch(r"chunk_([0-9]{4})_evidence\.json\.gz", name))
    )
    expected_numbers = list(range(1, len(checkpoint_numbers) + 1))
    expected_names = sorted(
        name
        for number in expected_numbers
        for name in (
            f"checkpoint_{number:04d}.json",
            f"chunk_{number:04d}_evidence.json.gz",
        )
    )
    if (
        len(expected_numbers) > CHUNK_COUNT
        or checkpoint_numbers != expected_numbers
        or evidence_numbers != expected_numbers
        or names != expected_names
    ):
        raise VerifierError("checkpoint inventory is noncontiguous or ambiguous")

    previous_sha256 = bootstrap["raw"]["bootstrap_sha256"]
    pre_runtime = bootstrap["runtime"]
    prior_decisions = 0
    cumulative_stored = 0
    cumulative_uncompressed = 0
    previous_prefix_size = 0
    chain: list[dict[str, Any]] = []
    for chunk_index, number in enumerate(expected_numbers):
        checkpoint_path = directory / f"checkpoint_{number:04d}.json"
        checkpoint_bytes = _read_bounded_file(
            checkpoint_path,
            label=f"checkpoint {number}",
            limit=MAX_ARTIFACT_BYTES,
        )
        checkpoint = _parse_canonical_json(
            checkpoint_bytes, label=f"checkpoint {number}"
        )
        checkpoint = _exact_mapping(
            checkpoint,
            {
                "access_journal_prefix",
                "checkpoint_index",
                "checkpoint_sha256",
                "chunk_evidence",
                "chunk_index",
                "identity",
                "previous_checkpoint_sha256",
                "registration_sha256",
                "resource_revision",
                "resource_use",
                "resume_used",
                "runtime_checkpoint",
                "schema_version",
            },
            f"checkpoint {number}",
        )
        body = {
            key: item
            for key, item in checkpoint.items()
            if key != "checkpoint_sha256"
        }
        if (
            checkpoint["schema_version"] != CHECKPOINT_ENVELOPE_SCHEMA_VERSION
            or checkpoint["chunk_index"] != chunk_index
            or checkpoint["checkpoint_index"] != number
            or checkpoint["identity"] != identity
            or checkpoint["registration_sha256"] != _canonical_digest(registration)
            or checkpoint["previous_checkpoint_sha256"] != previous_sha256
            or type(checkpoint["resume_used"]) is not bool
            or checkpoint["checkpoint_sha256"] != _canonical_digest(body)
        ):
            raise VerifierError("checkpoint identity, coordinate, or digest mismatch")
        prefix = _verify_journal_prefix(
            checkpoint["access_journal_prefix"],
            journal_bytes=journal_bytes,
            registration=registration,
            identity=identity,
        )
        prefix_size = checkpoint["access_journal_prefix"]["size_bytes"]
        if (
            prefix_size <= previous_prefix_size
            or prefix["pending_access"] is not None
            or prefix["completed_chunk_indices"] != list(range(chunk_index + 1))
            or prefix["primary_next_position"]
            != (chunk_index + 1) * TRAJECTORIES_PER_CHUNK
            or checkpoint["resume_used"] != prefix["resume_used"]
            or prefix["resume_failed"]
            or prefix["terminal_access_failure"]
            or (
                prefix["resume_mode"] == "replay_uncheckpointed_chunk"
                and not prefix["resume_complete"]
            )
        ):
            raise VerifierError("checkpoint journal prefix is not a closed chunk prefix")
        previous_prefix_size = prefix_size
        chunk = _verify_chunk_artifact(
            output,
            binding=checkpoint["chunk_evidence"],
            chunk_index=chunk_index,
            registration=registration,
        )
        runtime_binding = _validate_opaque_binding(
            checkpoint["runtime_checkpoint"], "runtime checkpoint"
        )
        if runtime_binding != chunk["runtime_checkpoint"]:
            raise VerifierError(
                "checkpoint and chunk evidence runtime bindings differ"
            )
        post_runtime = _validate_runtime_checkpoint(
            runtime_binding["payload"], f"runtime checkpoint {number} payload"
        )
        prior_decisions = _verify_runtime_transition(
            pre_runtime=pre_runtime,
            evidence=chunk["evidence"],
            post_runtime=post_runtime,
            chunk_index=chunk_index,
            prior_decisions=prior_decisions,
        )
        revision = _nonnegative_int(
            checkpoint["resource_revision"], "checkpoint resource revision"
        )
        if revision == 0 or revision > ledger["revision"]:
            raise VerifierError("checkpoint resource revision is unavailable")
        resources = _normalize_resources(checkpoint["resource_use"])
        resource_event = ledger["events"][revision]
        if resource_event["resources"] != resources:
            raise VerifierError("checkpoint resource prefix mismatch")
        if resources["environment_accesses"] != prefix["debited_accesses"]:
            raise VerifierError("checkpoint resource access count differs from journal")
        cumulative_stored += chunk["stored_size_bytes"] + len(checkpoint_bytes)
        cumulative_uncompressed += (
            chunk["uncompressed_size_bytes"] + len(checkpoint_bytes)
        )
        if (
            resources["optimizer_updates"] != number
            or resources["retained_decisions"] != prior_decisions
            or resources["stored_bytes"] != cumulative_stored
            or resources["uncompressed_bytes"] != cumulative_uncompressed
            or resource_event["reason"] != f"complete-chunk-checkpoint-{number}"
        ):
            raise VerifierError("checkpoint resource accounting mismatch")
        chain.append(
            {
                "checkpoint": checkpoint,
                "checkpoint_bytes": checkpoint_bytes,
                "chunk": chunk,
                "journal_prefix": prefix,
                "resource_revision": revision,
                "runtime": post_runtime,
            }
        )
        previous_sha256 = checkpoint["checkpoint_sha256"]
        pre_runtime = post_runtime

    checkpoint_revisions = {
        row["resource_revision"]: index + 1 for index, row in enumerate(chain)
    }
    previous_resources = _zero_resources()
    for revision, event in enumerate(ledger["events"][1:], start=1):
        resources = event["resources"]
        if revision in checkpoint_revisions:
            pass
        elif event["reason"] == "infrastructure-interruption-charge":
            charged_advanced = (
                resources["charged_seconds"] > previous_resources["charged_seconds"]
            )
            access_delta = (
                resources["environment_accesses"]
                - previous_resources["environment_accesses"]
            )
            if access_delta < 0 or not (charged_advanced or access_delta > 0):
                raise VerifierError("infrastructure charge did not advance its prefix")
            if any(
                resources[name] != previous_resources[name]
                for name in _RESOURCE_FIELDS
                if name not in {"charged_seconds", "environment_accesses"}
            ):
                raise VerifierError("infrastructure charge changed non-time resources")
        elif event["reason"] == "terminal-attempt-charge":
            if revision != ledger["revision"]:
                raise VerifierError("terminal attempt charge is not the final revision")
            access_delta = (
                resources["environment_accesses"]
                - previous_resources["environment_accesses"]
            )
            if access_delta < 0 or any(
                resources[name] != previous_resources[name]
                for name in _RESOURCE_FIELDS
                if name not in {"charged_seconds", "environment_accesses"}
            ):
                raise VerifierError("terminal attempt charge changed non-attempt resources")
        else:
            if event["reason"] != "access-journal-reconcile":
                raise VerifierError("non-checkpoint resource reason mismatch")
            access_delta = (
                resources["environment_accesses"]
                - previous_resources["environment_accesses"]
            )
            if access_delta <= 0 or any(
                resources[name] != previous_resources[name]
                for name in _RESOURCE_FIELDS
                if name != "environment_accesses"
            ):
                raise VerifierError("access resource event is not an exact prefix")
        previous_resources = resources
    if ledger["resources"]["environment_accesses"] != journal["debited_accesses"]:
        raise VerifierError("final resource accesses differ from the journal")
    if chain:
        final_checkpoint_resources = chain[-1]["checkpoint"]["resource_use"]
        for name in (
            "optimizer_updates",
            "retained_decisions",
            "stored_bytes",
            "uncompressed_bytes",
        ):
            if ledger["resources"][name] != final_checkpoint_resources[name]:
                raise VerifierError("final resource prefix differs from checkpoint chain")
    elif any(
        ledger["resources"][name] != 0
        for name in (
            "optimizer_updates",
            "retained_decisions",
            "stored_bytes",
            "uncompressed_bytes",
        )
    ):
        raise VerifierError("resource ledger claims training without a checkpoint")
    return chain


def _enumerate_output_files(output: Path) -> list[str]:
    if output.is_symlink() or not output.is_dir():
        raise VerifierError("terminal output root must be a non-symlink directory")
    files: list[str] = []
    stack = [output]
    while stack:
        directory = stack.pop()
        try:
            entries = list(directory.iterdir())
        except OSError as exc:
            raise VerifierError("terminal output tree is unreadable") from exc
        for entry in entries:
            if entry.is_symlink():
                raise VerifierError("terminal output tree contains a symlink")
            if entry.is_dir():
                stack.append(entry)
            elif entry.is_file():
                relative = entry.relative_to(output).as_posix()
                files.append(_canonical_relative_path(relative, "artifact path"))
            else:
                raise VerifierError("terminal output tree contains a non-file")
            if len(files) + len(stack) > 128:
                raise VerifierError("terminal output inventory exceeds the file bound")
    return sorted(files)


def _bounded_gzip_bytes(stored: bytes, *, label: str) -> bytes:
    if len(stored) > MAX_ARTIFACT_BYTES:
        raise VerifierError(f"{label} exceeds the stored-byte bound")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as stream:
            uncompressed = stream.read(MAX_ARTIFACT_BYTES + 1)
    except (EOFError, OSError) as exc:
        raise VerifierError(f"{label} is invalid gzip") from exc
    if len(uncompressed) > MAX_ARTIFACT_BYTES:
        raise VerifierError(f"{label} exceeds the uncompressed-byte bound")
    if _deterministic_gzip(uncompressed) != stored:
        raise VerifierError(f"{label} is not deterministic gzip")
    return uncompressed


def _build_artifact_inventory(
    output: Path,
    *,
    files: Sequence[str],
    excluded: set[str],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    stored_total = 0
    uncompressed_total = 0
    for relative in files:
        if relative in excluded or relative == LEASE_FILENAME:
            continue
        stored = _read_bounded_file(
            output / PurePosixPath(relative),
            label=f"artifact {relative}",
            limit=MAX_ARTIFACT_BYTES,
        )
        if relative.endswith(".gz"):
            uncompressed = _bounded_gzip_bytes(stored, label=f"artifact {relative}")
            encoding = "deterministic-gzip-v1"
        else:
            uncompressed = stored
            encoding = "identity-bytes-v1"
        stored_total += len(stored)
        uncompressed_total += len(uncompressed)
        if stored_total > MAX_STORED_BYTES:
            raise VerifierError("artifact inventory exceeds the stored-byte bound")
        if uncompressed_total > MAX_UNCOMPRESSED_BUNDLE_BYTES:
            raise VerifierError("artifact inventory exceeds the uncompressed-byte bound")
        rows.append(
            {
                "encoding": encoding,
                "path": relative,
                "stored_sha256": hashlib.sha256(stored).hexdigest(),
                "stored_size_bytes": len(stored),
                "uncompressed_sha256": hashlib.sha256(uncompressed).hexdigest(),
                "uncompressed_size_bytes": len(uncompressed),
            }
        )
    return {
        "artifacts": rows,
        "stored_size_bytes": stored_total,
        "uncompressed_size_bytes": uncompressed_total,
    }


def _classify_family_saturation(
    evidences: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    window = evidences[-4:]
    window_indices = [chunk["chunk_index"] for chunk in window]
    if len(window) < 4:
        return {
            "category": None,
            "family": None,
            "multi_family_decisions": 0,
            "stop": False,
            "window_chunk_indices": window_indices,
        }
    for category in ("card_reward", "shop"):
        rows = [
            row["diagnostic"]
            for chunk in window
            for row in chunk["decisions"]
            if row["category"] == category
            and row["diagnostic"]["multi_family"] is True
        ]
        if len(rows) < 64:
            continue
        maxima = [row["raw_score_max_family_ids"] for row in rows]
        if all(
            isinstance(value, list)
            and len(value) == 1
            and isinstance(value[0], str)
            and value[0]
            for value in maxima
        ):
            families = {value[0] for value in maxima}
            if len(families) == 1:
                return {
                    "category": category,
                    "family": next(iter(families)),
                    "multi_family_decisions": len(rows),
                    "stop": True,
                    "window_chunk_indices": window_indices,
                }
    return {
        "category": None,
        "family": None,
        "multi_family_decisions": 0,
        "stop": False,
        "window_chunk_indices": window_indices,
    }


def _verify_failure(
    output: Path, *, details_failure: Any, files: set[str]
) -> dict[str, Any] | None:
    present = FAILURE_FILENAME in files
    if details_failure is None:
        if present:
            raise VerifierError("typed failure artifact is unexpected")
        return None
    if not present:
        raise VerifierError("typed failure artifact is missing")
    failure = _load_canonical_document(output, FAILURE_FILENAME, label="failure witness")
    failure = _exact_mapping(
        failure,
        {
            "exception_type",
            "failure_sha256",
            "infrastructure",
            "message",
            "phase",
            "schema_version",
        },
        "failure witness",
    )
    if (
        failure["schema_version"] != FAILURE_WITNESS_SCHEMA_VERSION
        or failure["phase"] not in {"bootstrap", "terminal", "training"}
        or type(failure["infrastructure"]) is not bool
        or not isinstance(failure["message"], str)
    ):
        raise VerifierError("typed failure witness fields mismatch")
    _nonempty_string(failure["exception_type"], "failure exception type")
    body = {key: item for key, item in failure.items() if key != "failure_sha256"}
    if failure["failure_sha256"] != _canonical_digest(body):
        raise VerifierError("typed failure witness digest mismatch")
    if failure != details_failure:
        raise VerifierError("terminal details differ from typed failure witness")
    return failure


def _require_terminal_attempt_charge(ledger: Mapping[str, Any]) -> None:
    events = ledger.get("events")
    if (
        not isinstance(events, Sequence)
        or not events
        or not isinstance(events[-1], Mapping)
        or events[-1].get("reason") != "terminal-attempt-charge"
    ):
        raise VerifierError("terminal attempt charge is missing")


def _verify_terminal_state(
    *,
    verdict: Any,
    details: Any,
    chain: Sequence[Mapping[str, Any]],
    journal: Mapping[str, Any],
    ledger: Mapping[str, Any],
    output: Path,
    files: set[str],
) -> tuple[str, dict[str, Any]]:
    if not isinstance(verdict, str) or verdict not in _TERMINAL_VERDICTS:
        raise VerifierError("terminal verdict is not registered")
    normalized_details = _exact_mapping(
        details, {"evaluation", "failure", "saturation"}, "terminal details"
    )
    if normalized_details["evaluation"] is not None:
        raise VerifierError("terminal bundle contains unauthorized evaluation")
    evidences = [row["chunk"]["evidence"] for row in chain]
    saturation = _classify_family_saturation(evidences)
    if normalized_details["saturation"] != saturation:
        raise VerifierError("terminal saturation differs from independent replay")
    earliest_saturation: int | None = None
    for count in range(1, len(evidences) + 1):
        if _classify_family_saturation(evidences[:count])["stop"]:
            earliest_saturation = count - 1
            break
    failure = _verify_failure(
        output, details_failure=normalized_details["failure"], files=files
    )
    if journal["pending_access"] is not None:
        raise VerifierError("terminal bundle contains a pending access")
    if failure is not None and failure["infrastructure"] and (
        verdict != "experiment_failed_after_seed_access"
        or journal["resume_used"] is not True
    ):
        raise VerifierError(
            "infrastructure failure is terminal only after the resume is consumed"
        )
    if verdict == "experiment_blocked_before_seed_access":
        if (
            journal["debited_accesses"] != 0
            or chain
            or ledger["resources"] != _zero_resources()
            or failure is None
        ):
            raise VerifierError("prestart terminal verdict contains empirical work")
    elif verdict == "experiment_completed_with_cross_fitted_mechanism_evidence":
        if (
            len(chain) != CHUNK_COUNT
            or journal["completed_chunk_indices"] != list(range(CHUNK_COUNT))
            or journal["primary_next_position"]
            != len(chain) * TRAJECTORIES_PER_CHUNK
            or journal["resume_candidate_chunk_index"] is not None
            or journal["resume_failed"]
            or journal["terminal_access_failure"]
            or (journal["resume_used"] and not journal["resume_complete"])
            or failure is not None
            or earliest_saturation is not None
        ):
            raise VerifierError("completion verdict is early, saturated, or incomplete")
        _require_terminal_attempt_charge(ledger)
    elif verdict == "experiment_stopped_during_training_for_family_saturation":
        if (
            earliest_saturation is None
            or len(chain) != earliest_saturation + 1
            or not saturation["stop"]
            or failure is not None
            or journal["completed_chunk_indices"] != list(range(len(chain)))
            or journal["primary_next_position"]
            != len(chain) * TRAJECTORIES_PER_CHUNK
            or journal["resume_candidate_chunk_index"] is not None
            or journal["resume_failed"]
            or journal["terminal_access_failure"]
            or (journal["resume_used"] and not journal["resume_complete"])
        ):
            raise VerifierError(
                "saturation verdict is not at the earliest checkpoint boundary"
            )
        _require_terminal_attempt_charge(ledger)
    elif journal["debited_accesses"] == 0 or failure is None:
        raise VerifierError("post-start failure lacks access evidence or typed failure")
    else:
        _require_terminal_attempt_charge(ledger)
    return verdict, normalized_details


def _verify_terminal_intent(
    value: Any,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, str],
    journal_bytes: bytes,
    ledger: Mapping[str, Any],
    chain: Sequence[Mapping[str, Any]],
    files: Sequence[str],
    output: Path,
) -> dict[str, Any]:
    intent = _exact_mapping(
        value,
        {
            "artifact_prefix_inventory",
            "authority",
            "checkpoint_sha256s",
            "details",
            "identity",
            "journal_prefix",
            "registration_sha256",
            "resource_revision",
            "resource_use",
            "schema_version",
            "terminal_intent_sha256",
            "verdict",
        },
        "terminal intent",
    )
    if (
        intent["schema_version"] != TERMINAL_INTENT_SCHEMA_VERSION
        or intent["authority"] != _AUTHORITY
        or intent["identity"] != identity
        or intent["registration_sha256"] != _canonical_digest(registration)
        or intent["checkpoint_sha256s"]
        != [row["checkpoint"]["checkpoint_sha256"] for row in chain]
        or intent["resource_revision"] != ledger["revision"]
        or intent["resource_use"] != ledger["resources"]
    ):
        raise VerifierError("terminal intent durable identity mismatch")
    prefix = _exact_mapping(
        intent["journal_prefix"],
        {"sha256", "size_bytes"},
        "terminal journal prefix",
    )
    if (
        prefix["size_bytes"] != len(journal_bytes)
        or prefix["sha256"] != hashlib.sha256(journal_bytes).hexdigest()
    ):
        raise VerifierError("terminal intent journal prefix mismatch")
    observed_prefix_inventory = _build_artifact_inventory(
        output,
        files=files,
        excluded={MANIFEST_FILENAME, TERMINAL_FILENAME, TERMINAL_INTENT_FILENAME},
    )
    if intent["artifact_prefix_inventory"] != observed_prefix_inventory:
        raise VerifierError("terminal intent artifact prefix mismatch")
    body = {
        key: item
        for key, item in intent.items()
        if key != "terminal_intent_sha256"
    }
    if intent["terminal_intent_sha256"] != _canonical_digest(body):
        raise VerifierError("terminal intent body digest mismatch")
    return intent


def _verify_terminal_document(
    value: Any,
    *,
    registration: Mapping[str, Any],
    identity: Mapping[str, str],
    journal: Mapping[str, Any],
    ledger: Mapping[str, Any],
    chain: Sequence[Mapping[str, Any]],
    intent: Mapping[str, Any],
) -> dict[str, Any]:
    terminal = _exact_mapping(
        value,
        {
            "authority",
            "checkpoint_count",
            "completed_chunk_indices",
            "details",
            "identity",
            "registration_sha256",
            "resource_use",
            "resume_used",
            "schema_version",
            "terminal_intent_sha256",
            "terminal_sha256",
            "verdict",
        },
        "terminal",
    )
    if (
        terminal["schema_version"] != TERMINAL_SCHEMA_VERSION
        or terminal["authority"] != _AUTHORITY
        or terminal["identity"] != identity
        or terminal["registration_sha256"] != _canonical_digest(registration)
        or terminal["checkpoint_count"] != len(chain)
        or terminal["completed_chunk_indices"] != journal["completed_chunk_indices"]
        or terminal["resource_use"] != ledger["resources"]
        or terminal["resume_used"] != journal["resume_used"]
        or terminal["terminal_intent_sha256"] != intent["terminal_intent_sha256"]
        or terminal["verdict"] != intent["verdict"]
        or terminal["details"] != intent["details"]
    ):
        raise VerifierError("terminal differs from durable intent or prefixes")
    body = {key: item for key, item in terminal.items() if key != "terminal_sha256"}
    if terminal["terminal_sha256"] != _canonical_digest(body):
        raise VerifierError("terminal body digest mismatch")
    return terminal


def _verify_manifest(
    value: Any,
    *,
    manifest_size: int,
    registration: Mapping[str, Any],
    identity: Mapping[str, str],
    terminal: Mapping[str, Any],
    observed_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    manifest = _exact_mapping(
        value,
        {
            "artifact_inventory",
            "authority",
            "identity",
            "manifest_sha256",
            "registration_sha256",
            "schema_version",
            "terminal_sha256",
        },
        "artifact manifest",
    )
    if (
        manifest["schema_version"] != MANIFEST_SCHEMA_VERSION
        or manifest["authority"] != _AUTHORITY
        or manifest["identity"] != identity
        or manifest["registration_sha256"] != _canonical_digest(registration)
        or manifest["terminal_sha256"] != terminal["terminal_sha256"]
        or manifest["artifact_inventory"] != observed_inventory
    ):
        raise VerifierError("manifest identity or exact file closure mismatch")
    body = {key: item for key, item in manifest.items() if key != "manifest_sha256"}
    if manifest["manifest_sha256"] != _canonical_digest(body):
        raise VerifierError("manifest body digest mismatch")
    if (
        observed_inventory["stored_size_bytes"] + manifest_size > MAX_STORED_BYTES
        or observed_inventory["uncompressed_size_bytes"] + manifest_size
        > MAX_UNCOMPRESSED_BUNDLE_BYTES
    ):
        raise VerifierError("manifest closes an over-limit artifact bundle")
    return manifest


def _verify_terminal_bundle_contents(
    output: Path,
    *,
    root: Path,
    lease_identity: Mapping[str, str] | None,
) -> dict[str, Any]:
    if lease_identity is None:
        try:
            (output / LEASE_FILENAME).lstat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise VerifierError("execution lease liveness is ambiguous") from exc
        else:
            raise VerifierError("execution lease appeared before evidence read")
    files = _enumerate_output_files(output)
    file_set = set(files)

    registration = _validate_registration(
        _load_canonical_document(output, REGISTRATION_FILENAME, label="registration"),
        output=output,
        repo_root=root,
    )
    request = _validate_request(
        _load_canonical_document(
            output, EXECUTION_REQUEST_FILENAME, label="execution request"
        ),
        registration,
    )
    approval = _validate_approval(
        _load_canonical_document(
            output, EXTERNAL_APPROVAL_FILENAME, label="external approval"
        ),
        request=request,
    )
    authorization, identity = _validate_authorization(
        _load_canonical_document(output, AUTHORIZATION_FILENAME, label="authorization"),
        registration=registration,
        request=request,
        approval=approval,
    )
    if lease_identity is not None:
        _validate_execution_identity(lease_identity, identity)
    _validate_source_preflight(
        _load_canonical_document(
            output, SOURCE_PREFLIGHT_FILENAME, label="source preflight"
        ),
        registration=registration,
    )
    _validate_isolation_observation(
        _load_canonical_document(output, PRE_ISOLATION_FILENAME, label="pre isolation"),
        registration=registration,
        phase="pre",
    )

    journal_bytes = _read_bounded_file(
        output / ACCESS_JOURNAL_FILENAME,
        label="access journal",
        limit=MAX_ARTIFACT_BYTES,
    )
    journal = _verify_access_journal(
        journal_bytes, registration=registration, identity=identity
    )
    ledger = _verify_resource_ledger(
        _read_bounded_file(
            output / RESOURCE_LEDGER_FILENAME,
            label="resource ledger",
            limit=MAX_ARTIFACT_BYTES,
        ),
        identity=identity,
    )
    bootstrap = _verify_bootstrap(
        _load_canonical_document(output, BOOTSTRAP_FILENAME, label="bootstrap"),
        registration=registration,
        identity=identity,
    )
    chain = _verify_checkpoint_chain(
        output,
        registration=registration,
        identity=identity,
        journal_bytes=journal_bytes,
        journal=journal,
        ledger=ledger,
        bootstrap=bootstrap,
    )
    if journal["resume_used"]:
        resume_chunk = journal["resume_chunk_index"]
        mode = journal["resume_mode"]
        for index, row in enumerate(chain):
            observed = row["journal_prefix"]["resume_used"]
            expected = index >= resume_chunk
            if mode == "continue_after_checkpoint":
                expected = index >= resume_chunk
            if observed != expected:
                raise VerifierError("checkpoint chain crosses the resume boundary incorrectly")

    _validate_isolation_observation(
        _load_canonical_document(
            output, POST_ISOLATION_FILENAME, label="post isolation"
        ),
        registration=registration,
        phase="post",
    )
    intent = _verify_terminal_intent(
        _load_canonical_document(
            output, TERMINAL_INTENT_FILENAME, label="terminal intent"
        ),
        registration=registration,
        identity=identity,
        journal_bytes=journal_bytes,
        ledger=ledger,
        chain=chain,
        files=files,
        output=output,
    )
    verdict, details = _verify_terminal_state(
        verdict=intent["verdict"],
        details=intent["details"],
        chain=chain,
        journal=journal,
        ledger=ledger,
        output=output,
        files=file_set,
    )
    terminal = _verify_terminal_document(
        _load_canonical_document(output, TERMINAL_FILENAME, label="terminal"),
        registration=registration,
        identity=identity,
        journal=journal,
        ledger=ledger,
        chain=chain,
        intent=intent,
    )
    if terminal["verdict"] != verdict or terminal["details"] != details:
        raise VerifierError("terminal state changed after intent validation")

    required_files = {
        ACCESS_JOURNAL_FILENAME,
        AUTHORIZATION_FILENAME,
        BOOTSTRAP_FILENAME,
        EXECUTION_REQUEST_FILENAME,
        EXTERNAL_APPROVAL_FILENAME,
        MANIFEST_FILENAME,
        POST_ISOLATION_FILENAME,
        PRE_ISOLATION_FILENAME,
        REGISTRATION_FILENAME,
        RESOURCE_LEDGER_FILENAME,
        SOURCE_PREFLIGHT_FILENAME,
        TERMINAL_FILENAME,
        TERMINAL_INTENT_FILENAME,
    }
    required_files.update(
        path
        for number in range(1, len(chain) + 1)
        for path in (
            f"checkpoints/checkpoint_{number:04d}.json",
            f"checkpoints/chunk_{number:04d}_evidence.json.gz",
        )
    )
    if details["failure"] is not None:
        required_files.add(FAILURE_FILENAME)
    closure = file_set - {LEASE_FILENAME}
    if closure != required_files:
        missing = sorted(required_files - closure)
        extra = sorted(closure - required_files)
        raise VerifierError(
            f"terminal exact file closure mismatch; missing={missing}, extra={extra}"
        )
    directories = {
        candidate.relative_to(output).as_posix()
        for candidate in output.rglob("*")
        if candidate.is_dir()
    }
    expected_directories = {"checkpoints"} if chain else set()
    if directories != expected_directories:
        raise VerifierError("terminal exact directory closure mismatch")
    observed_inventory = _build_artifact_inventory(
        output, files=files, excluded={MANIFEST_FILENAME}
    )
    manifest_bytes = _read_bounded_file(
        output / MANIFEST_FILENAME,
        label="artifact manifest",
        limit=MAX_ARTIFACT_BYTES,
    )
    manifest = _verify_manifest(
        _parse_canonical_json(manifest_bytes, label="artifact manifest"),
        manifest_size=len(manifest_bytes),
        registration=registration,
        identity=identity,
        terminal=terminal,
        observed_inventory=observed_inventory,
    )
    return {
        "authorization_sha256": authorization["authorization_sha256"],
        "checkpoint_count": len(chain),
        "completed_chunk_indices": journal["completed_chunk_indices"],
        "manifest_sha256": manifest["manifest_sha256"],
        "registration_sha256": _canonical_digest(registration),
        "resource_use": ledger["resources"],
        "resume_mode": journal["resume_mode"],
        "resume_used": journal["resume_used"],
        "terminal_sha256": terminal["terminal_sha256"],
        "verdict": verdict,
    }


def _lease_path_exists(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise VerifierError("execution lease liveness is ambiguous") from exc
    return True


def _require_closed_lease_free_root(output: Path) -> None:
    reparse_flag = getattr(stat_module, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    for filename in (TERMINAL_FILENAME, MANIFEST_FILENAME):
        path = output / filename
        try:
            observed = path.lstat()
        except OSError as exc:
            raise VerifierError(
                "lease-free verification requires a closed terminal bundle"
            ) from exc
        if (
            stat_module.S_ISLNK(observed.st_mode)
            or not stat_module.S_ISREG(observed.st_mode)
            or bool(getattr(observed, "st_file_attributes", 0) & reparse_flag)
        ):
            raise VerifierError(
                "lease-free verification requires regular terminal markers"
            )


def verify_terminal_bundle(
    output_path: Path | str,
    *,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Independently verify one terminal bundle while holding any stale lease.

    This function intentionally uses only the Python standard library and the
    verifier code in this module. It never imports the producer control plane,
    the Torch runtime, or the native simulator adapter.
    """
    output = Path(output_path).resolve()
    root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
    lease_path = output / LEASE_FILENAME
    if _lease_path_exists(lease_path):
        lease_guard = _hold_inactive_execution_lease(lease_path)
    else:
        # A compliant producer creates its lease before any terminal artifact
        # and never reopens a root that already has both closeout markers.
        _require_closed_lease_free_root(output)
        lease_guard = (
            _hold_inactive_execution_lease(lease_path)
            if _lease_path_exists(lease_path)
            else contextlib.nullcontext(None)
        )
    with lease_guard as lease_identity:
        return _verify_terminal_bundle_contents(
            output,
            root=root,
            lease_identity=lease_identity,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Independently verify one cross-fitted terminal bundle"
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = verify_terminal_bundle(args.output)
    except (OSError, VerifierError) as exc:
        sys.stderr.buffer.write(
            canonical_json_bytes({"error": str(exc), "status": "blocked"})
        )
        return 1
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
