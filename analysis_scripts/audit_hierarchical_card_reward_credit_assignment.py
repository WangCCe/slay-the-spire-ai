"""Read-only credit-assignment audit for the terminal hierarchical experiment."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
import gzip
import hashlib
import io
import json
import math
from numbers import Real
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import tempfile
from typing import Any, BinaryIO


AUDIT_SCHEMA_VERSION = (
    "noncombat-hierarchical-card-reward-credit-assignment-audit-v1"
)
PREIMPLEMENTATION_SCHEMA_VERSION = (
    "noncombat-hierarchical-card-reward-credit-assignment-audit-"
    "preimplementation-v1"
)
LEASE_SCHEMA_VERSION = "noncombat-hierarchical-simulator-learning-lease-v1"
TRAINING_ROWS_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-training-rows-v1"
)
TRAINING_CHUNK_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-chunk-summary-v1"
)
TRAINING_ROW_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-training-row-v1"
)
MANIFEST_SCHEMA_VERSION = (
    "noncombat-hierarchical-simulator-learning-artifact-manifest-v1"
)
LOGICAL_EXECUTION_ID = (
    "noncombat-hierarchical-simulator-learning-20260806-r1"
)
TERMINAL_VERDICT = (
    "experiment_stopped_during_training_for_family_saturation"
)
DEFAULT_SOURCE_PATH = (
    "analysis_scripts/audit_hierarchical_card_reward_credit_assignment.py"
)
DEFAULT_TEST_PATH = (
    "tests/test_audit_hierarchical_card_reward_credit_assignment.py"
)
DEFAULT_PREIMPLEMENTATION_PATH = (
    "reports/noncombat_hierarchical_card_reward_credit_assignment_"
    "audit_20260806_preimplementation.json"
)
DEFAULT_TERMINAL_DIRECTORY = (
    "reports/noncombat_hierarchical_simulator_learning_successor_20260806"
)
DEFAULT_POSTMORTEM_PATH = (
    "reports/noncombat_hierarchical_simulator_learning_successor_"
    "20260806_postmortem.json"
)
DEFAULT_JSON_REPORT_PATH = (
    "reports/noncombat_hierarchical_card_reward_credit_assignment_"
    "audit_20260806.json"
)
DEFAULT_MARKDOWN_REPORT_PATH = (
    "reports/noncombat_hierarchical_card_reward_credit_assignment_"
    "audit_20260806.md"
)

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
RECORDED_EXECUTION_ENABLED = frozenset(
    {
        "environment_construction_authorized",
        "execution_authorized",
        "fresh_evidence_authorized",
        "model_fitting_authorized",
        "native_loading_authorized",
        "seed_access_authorized",
        "training_authorized",
    }
)

LIMITATIONS = (
    "Direct family-logit pressure is a factorized coordinate derivative, not "
    "the full shared-parameter gradient.",
    "Recorded reward-to-go associations are trajectory-confounded and are not "
    "causal card values or intervention effects.",
    "Repeated decisions within a seed are not treated as independent samples.",
    "The audit estimates no policy value, OPE quantity, confidence interval, "
    "p-value, or target-supported outcome.",
    "No verdict authorizes training, replay, seed access, model loading, "
    "gameplay, qualification, or promotion.",
)

_COMMIT_RE = re.compile(r"[0-9a-f]{40,64}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_GIT_OBJECT_RE = re.compile(r"[0-9a-f]{40,64}")
_SUPPORT_MINIMUM_ROWS = 64
_SUPPORT_MINIMUM_FAMILY_ROWS = 16
_ENTROPY_COEFFICIENT = 0.01
_MAX_GZIP_BYTES = 64 * 1024 * 1024


class CreditAssignmentAuditError(ValueError):
    """Raised when immutable evidence or audit arithmetic is invalid."""


def audit_authority() -> dict[str, bool]:
    """Return the exact all-false downstream authority map."""
    return {name: False for name in AUTHORITY_NAMES}


def recorded_execution_authority() -> dict[str, bool]:
    """Return the exact authority granted to the consumed historical run."""
    return {
        name: name in RECORDED_EXECUTION_ENABLED for name in AUTHORITY_NAMES
    }


def _reject_constant(value: str) -> None:
    raise CreditAssignmentAuditError(
        f"JSON contains non-finite constant: {value}"
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CreditAssignmentAuditError(
                f"JSON contains duplicate key: {key}"
            )
        result[key] = value
    return result


def canonical_json_bytes(value: object) -> bytes:
    """Serialize strict canonical JSON used by every audit artifact."""
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CreditAssignmentAuditError(
            f"value is not canonical JSON: {exc}"
        ) from exc


def _matches_canonical_json_bytes(value: object, raw: bytes) -> bool:
    encoder = json.JSONEncoder(
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    )
    offset = 0
    try:
        for chunk in encoder.iterencode(value):
            encoded = chunk.encode("utf-8")
            if not raw.startswith(encoded, offset):
                return False
            offset += len(encoded)
    except (TypeError, ValueError) as exc:
        raise CreditAssignmentAuditError(
            f"value is not canonical JSON: {exc}"
        ) from exc
    return len(raw) == offset + 1 and raw[offset:] == b"\n"


def parse_canonical_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    """Parse one unique-key canonical JSON object."""
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreditAssignmentAuditError(
            f"{label} is invalid JSON: {exc}"
        ) from exc
    result = _mapping(value, label)
    if not _matches_canonical_json_bytes(result, raw):
        raise CreditAssignmentAuditError(f"{label} is not canonical JSON")
    return dict(result)


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise CreditAssignmentAuditError(f"{label} must be a mapping")
    return value


def _sequence(value: Any, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CreditAssignmentAuditError(f"{label} must be a sequence")
    return value


def _exact_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise CreditAssignmentAuditError(
            f"{label} keys mismatch: expected {sorted(expected)}, "
            f"got {sorted(value)}"
        )


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise CreditAssignmentAuditError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _finite(
    value: Any,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise CreditAssignmentAuditError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise CreditAssignmentAuditError(f"{label} must be finite")
    if minimum is not None and result < minimum:
        raise CreditAssignmentAuditError(f"{label} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise CreditAssignmentAuditError(f"{label} must be <= {maximum}")
    return result


def _nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise CreditAssignmentAuditError(
            f"{label} must be a nonempty string"
        )
    return value


def _canonical_relative_path(value: Any, label: str = "path") -> str:
    path = _nonempty_string(value, label)
    if "\\" in path:
        raise CreditAssignmentAuditError(
            f"{label} must be a canonical relative path"
        )
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or str(pure) != path:
        raise CreditAssignmentAuditError(
            f"{label} must be a canonical relative path"
        )
    return path


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise CreditAssignmentAuditError(f"{label} must be a lowercase SHA-256")
    return value


def _is_reparse_point(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except FileNotFoundError:
        return False
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return path.is_symlink() or bool(reparse_flag and attributes & reparse_flag)


def _regular_file(path: Path, label: str) -> Path:
    if _is_reparse_point(path) or not path.is_file():
        raise CreditAssignmentAuditError(
            f"{label} must be a regular non-symlink file"
        )
    return path


def _hash_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _validate_basic_binding(
    binding: Mapping[str, Any], label: str
) -> tuple[str, int, str]:
    path = _canonical_relative_path(binding.get("path"), f"{label}.path")
    size = _integer(binding.get("size_bytes"), f"{label}.size_bytes")
    digest = _sha256(binding.get("sha256"), f"{label}.sha256")
    return path, size, digest


def verify_file_binding(
    path: Path | str, binding: Mapping[str, Any], label: str
) -> None:
    """Verify one regular file against size and SHA-256."""
    target = _regular_file(Path(path), label)
    _relative, expected_size, expected_digest = _validate_basic_binding(
        binding, label
    )
    size, digest = _hash_file(target)
    if size != expected_size or digest != expected_digest:
        raise CreditAssignmentAuditError(f"{label} stored identity mismatch")


def _verify_payload_binding(
    payload: bytes, binding: Mapping[str, Any], label: str
) -> None:
    _relative, expected_size, expected_digest = _validate_basic_binding(
        binding, label
    )
    if (
        len(payload) != expected_size
        or hashlib.sha256(payload).hexdigest() != expected_digest
    ):
        raise CreditAssignmentAuditError(f"{label} stored identity mismatch")


def load_bound_json(
    path: Path | str, binding: Mapping[str, Any], label: str
) -> tuple[dict[str, Any], bytes]:
    target = _regular_file(Path(path), label)
    raw = target.read_bytes()
    _verify_payload_binding(raw, binding, label)
    return parse_canonical_json_bytes(raw, label), raw


def load_bound_gzip_json(
    path: Path | str, binding: Mapping[str, Any], label: str
) -> tuple[dict[str, Any], bytes]:
    """Verify gzip stored/canonical bytes before parsing canonical JSON."""
    expected_keys = {
        "canonical_sha256",
        "canonical_size_bytes",
        "compression",
        "path",
        "sha256",
        "size_bytes",
    }
    _exact_keys(binding, expected_keys, f"{label} binding")
    if binding.get("compression") != "gzip-mtime-zero-v1":
        raise CreditAssignmentAuditError(
            f"{label} compression identity mismatch"
        )
    _relative, stored_size, _stored_digest = _validate_basic_binding(
        binding, label
    )
    expected_size = _integer(
        binding.get("canonical_size_bytes"),
        f"{label}.canonical_size_bytes",
    )
    if stored_size > _MAX_GZIP_BYTES or expected_size > _MAX_GZIP_BYTES:
        raise CreditAssignmentAuditError(f"{label} exceeds bounded gzip size")
    target = _regular_file(Path(path), label)
    stored = target.read_bytes()
    _verify_payload_binding(stored, binding, label)
    if len(stored) < 10 or stored[:3] != b"\x1f\x8b\x08" or stored[4:8] != b"\0\0\0\0":
        raise CreditAssignmentAuditError(f"{label} gzip header is invalid")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as stream:
            raw = stream.read(expected_size + 1)
            trailing = stream.read(1)
    except (EOFError, OSError) as exc:
        raise CreditAssignmentAuditError(f"{label} gzip payload is invalid") from exc
    expected_digest = _sha256(
        binding.get("canonical_sha256"), f"{label}.canonical_sha256"
    )
    if (
        trailing
        or len(raw) != expected_size
        or hashlib.sha256(raw).hexdigest() != expected_digest
    ):
        raise CreditAssignmentAuditError(f"{label} canonical identity mismatch")
    return parse_canonical_json_bytes(raw, label), raw


def lock_file(handle: BinaryIO) -> None:
    """Acquire the verifier-compatible one-byte non-blocking lease lock."""
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def unlock_file(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def hold_inactive_lease(
    path: Path | str,
    binding: Mapping[str, Any],
    expected_identity: Mapping[str, Any],
) -> Iterator[bytes]:
    """Lock first, then validate immutable lease bytes for the full audit."""
    target = _regular_file(Path(path), "execution lease")
    with target.open("r+b", buffering=0) as handle:
        try:
            lock_file(handle)
        except OSError as exc:
            raise CreditAssignmentAuditError(
                "terminal output is owned by an active execution"
            ) from exc
        try:
            handle.seek(0)
            before = handle.read()
            _relative, expected_size, expected_digest = _validate_basic_binding(
                binding, "execution lease"
            )
            if (
                len(before) != expected_size
                or hashlib.sha256(before).hexdigest() != expected_digest
            ):
                raise CreditAssignmentAuditError(
                    "execution lease stored identity mismatch"
                )
            value = parse_canonical_json_bytes(before, "execution lease")
            _exact_keys(value, {"identity", "schema_version"}, "execution lease")
            if value.get("schema_version") != LEASE_SCHEMA_VERSION:
                raise CreditAssignmentAuditError("execution lease schema mismatch")
            if value.get("identity") != dict(expected_identity):
                raise CreditAssignmentAuditError("execution lease identity mismatch")
            yield before
            handle.seek(0)
            if handle.read() != before:
                raise CreditAssignmentAuditError(
                    "execution lease changed during audit"
                )
        finally:
            unlock_file(handle)


def _git(repo_root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise CreditAssignmentAuditError("Git is unavailable") from exc
    if completed.returncode != 0:
        message = completed.stderr.decode("utf-8", errors="replace").strip()
        raise CreditAssignmentAuditError(
            f"git {' '.join(args)} failed: {message}"
        )
    return completed.stdout


def _git_optional(repo_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise CreditAssignmentAuditError("Git is unavailable") from exc


def verify_head_source(
    repo_root: Path | str, source_relative_path: str
) -> dict[str, Any]:
    """Require worktree source bytes to equal one tracked HEAD blob."""
    root = Path(repo_root).resolve(strict=True)
    relative = _canonical_relative_path(source_relative_path, "source path")
    commit = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    if not _COMMIT_RE.fullmatch(commit):
        raise CreditAssignmentAuditError("HEAD commit identity is invalid")
    completed = _git_optional(root, "show", f"HEAD:{relative}")
    if completed.returncode != 0:
        raise CreditAssignmentAuditError(
            f"source path must be tracked at HEAD: {relative}"
        )
    target = _regular_file(root / Path(relative), "audit source")
    worktree = target.read_bytes()
    if worktree != completed.stdout:
        raise CreditAssignmentAuditError("audit source differs from HEAD")
    blob = _git(root, "rev-parse", f"HEAD:{relative}").decode("ascii").strip()
    if not _GIT_OBJECT_RE.fullmatch(blob):
        raise CreditAssignmentAuditError("audit source Git blob is invalid")
    return {
        "commit": commit,
        "git_blob": blob,
        "path": relative,
        "sha256": hashlib.sha256(worktree).hexdigest(),
        "size_bytes": len(worktree),
    }


def float32(value: float) -> float:
    try:
        return struct.unpack("<f", struct.pack("<f", float(value)))[0]
    except (OverflowError, struct.error) as exc:
        raise CreditAssignmentAuditError("float32 arithmetic overflowed") from exc


def float32_sum(values: Sequence[float]) -> float:
    return float32(math.fsum(float32(value) for value in values))


def float32_mean(values: Sequence[float]) -> float:
    if not values:
        raise CreditAssignmentAuditError("float32 reduction is empty")
    return float32(float32_sum(values) / len(values))


def float32_population_std(
    values: Sequence[float], *, mean: float
) -> float:
    if not values:
        raise CreditAssignmentAuditError("float32 reduction is empty")
    squared = [
        float32(float32(value - mean) * float32(value - mean))
        for value in values
    ]
    variance = float32(float32_sum(squared) / len(values))
    return float32(math.sqrt(variance))


def reconstruct_normalized_returns(
    rows: Sequence[Mapping[str, Any]], episode_seeds: Sequence[int]
) -> dict[str, Any]:
    """Reconstruct registered reward-to-go and float32 normalization."""
    source_rows = list(_sequence(rows, "training rows"))
    seeds = [
        _integer(seed, f"episode_seeds[{index}]")
        for index, seed in enumerate(_sequence(episode_seeds, "episode seeds"))
    ]
    if len(set(seeds)) != len(seeds):
        raise CreditAssignmentAuditError("episode seeds must be unique")
    ordered_rows: list[Mapping[str, Any]] = []
    returns: list[float] = []
    for seed in seeds:
        episode_rows = [row for row in source_rows if row.get("seed") == seed]
        if not episode_rows:
            raise CreditAssignmentAuditError(f"seed {seed} has no training rows")
        for index, row in enumerate(episode_rows):
            if row.get("decision_index") != index:
                raise CreditAssignmentAuditError(
                    f"seed {seed} decision order mismatch"
                )
        ordered_rows.extend(episode_rows)
        running = 0.0
        episode_returns: list[float] = []
        for index, row in reversed(list(enumerate(episode_rows))):
            reward = _mapping(
                row.get("formal_reward"),
                f"seed {seed} decision {index} formal reward",
            )
            running = _finite(
                reward.get("scalar_reward"),
                f"seed {seed} decision {index} scalar reward",
            ) + running
            if not math.isfinite(running):
                raise CreditAssignmentAuditError("reward-to-go is not finite")
            episode_returns.append(running)
        returns.extend(reversed(episode_returns))
    if ordered_rows != source_rows or len(returns) != len(source_rows):
        raise CreditAssignmentAuditError("training row order mismatch")
    float_returns = [float32(value) for value in returns]
    mean = float32_mean(float_returns)
    standard_deviation = float32_population_std(float_returns, mean=mean)
    if abs(standard_deviation - 1e-12) <= 1e-15:
        raise CreditAssignmentAuditError(
            "return normalization is ambiguous at epsilon"
        )
    if standard_deviation > 1e-12:
        denominator = float32(standard_deviation + float32(1e-8))
        normalized = [
            float32(float32(value - mean) / denominator)
            for value in float_returns
        ]
    else:
        normalized = [0.0 for _ in float_returns]
    return {
        "mean": mean,
        "normalized_returns": normalized,
        "reward_to_go": float_returns,
        "standard_deviation": standard_deviation,
    }


def _entropy(probabilities: Sequence[float]) -> float:
    result = 0.0
    for probability in probabilities:
        value = _finite(probability, "probability", minimum=0.0, maximum=1.0)
        if value > 0.0:
            result -= value * math.log(value)
    return result


def reconstruct_conditional_entropies(
    row: Mapping[str, Any], label: str
) -> dict[str, Any]:
    """Reconstruct each family conditional entropy and its expectation."""
    candidates = _sequence(row.get("candidates"), f"{label}.candidates")
    conditionals = _mapping(
        row.get("conditional_probabilities"),
        f"{label}.conditional_probabilities",
    )
    family_order = list(
        _sequence(row.get("family_order"), f"{label}.family_order")
    )
    family_probabilities = _mapping(
        row.get("family_probabilities"), f"{label}.family_probabilities"
    )
    if len(set(family_order)) != len(family_order) or set(family_probabilities) != set(family_order):
        raise CreditAssignmentAuditError(f"{label} family identity mismatch")
    by_family_probabilities: dict[str, list[float]] = {
        family: [] for family in family_order
    }
    action_ids: list[str] = []
    for index, raw_candidate in enumerate(candidates):
        candidate = _mapping(raw_candidate, f"{label}.candidates[{index}]")
        _exact_keys(candidate, {"action_id", "kind"}, f"{label}.candidates[{index}]")
        action_id = _nonempty_string(
            candidate.get("action_id"), f"{label}.candidates[{index}].action_id"
        )
        family = _nonempty_string(
            candidate.get("kind"), f"{label}.candidates[{index}].kind"
        )
        if family not in by_family_probabilities or action_id in action_ids:
            raise CreditAssignmentAuditError(f"{label} candidate family mismatch")
        action_ids.append(action_id)
        by_family_probabilities[family].append(
            _finite(
                conditionals.get(action_id),
                f"{label}.conditional_probabilities[{action_id}]",
                minimum=0.0,
                maximum=1.0,
            )
        )
    if set(conditionals) != set(action_ids):
        raise CreditAssignmentAuditError(f"{label} conditional identity mismatch")
    by_family: dict[str, float] = {}
    expected = 0.0
    family_total = 0.0
    for family in family_order:
        probabilities = by_family_probabilities[family]
        if not probabilities or not math.isclose(
            math.fsum(probabilities), 1.0, rel_tol=1e-12, abs_tol=1e-12
        ):
            raise CreditAssignmentAuditError(
                f"{label} conditional probabilities do not sum to one"
            )
        family_probability = _finite(
            family_probabilities.get(family),
            f"{label}.family_probabilities[{family}]",
            minimum=0.0,
            maximum=1.0,
        )
        family_total += family_probability
        by_family[family] = _entropy(probabilities)
        expected += family_probability * by_family[family]
    if not math.isclose(family_total, 1.0, rel_tol=1e-12, abs_tol=1e-12):
        raise CreditAssignmentAuditError(
            f"{label} family probabilities do not sum to one"
        )
    recorded = _mapping(row.get("entropies"), f"{label}.entropies")
    observed = _finite(
        recorded.get("expected_conditional"),
        f"{label}.entropies.expected_conditional",
        minimum=0.0,
    )
    if not math.isclose(observed, expected, rel_tol=2e-12, abs_tol=2e-12):
        raise CreditAssignmentAuditError(
            f"{label} expected conditional entropy mismatch"
        )
    return {"by_family": by_family, "expected": expected}


def direct_take_pressure(
    *,
    normalized_return: Real,
    selected_family: str,
    take_probability: Real,
    family_entropy: Real,
    take_conditional_entropy: Real,
    expected_conditional_entropy: Real,
    chunk_decision_count: int,
) -> dict[str, float]:
    """Return exact row-local negative-gradient components for take logit."""
    advantage = _finite(normalized_return, "normalized return")
    probability = _finite(
        take_probability, "take probability", minimum=0.0, maximum=1.0
    )
    if probability <= 0.0:
        raise CreditAssignmentAuditError("take probability must be positive")
    family_h = _finite(family_entropy, "family entropy", minimum=0.0)
    take_h = _finite(
        take_conditional_entropy,
        "take conditional entropy",
        minimum=0.0,
    )
    expected_h = _finite(
        expected_conditional_entropy,
        "expected conditional entropy",
        minimum=0.0,
    )
    count = _integer(
        chunk_decision_count, "chunk decision count", minimum=1
    )
    indicator = 1.0 if selected_family == "take" else 0.0
    policy = advantage * (indicator - probability) / count
    family_term = (
        -_ENTROPY_COEFFICIENT
        * probability
        * (math.log(probability) + family_h)
        / count
    )
    conditional_term = (
        _ENTROPY_COEFFICIENT
        * probability
        * (take_h - expected_h)
        / count
    )
    combined = policy + family_term + conditional_term
    if not all(
        math.isfinite(value)
        for value in (policy, family_term, conditional_term, combined)
    ):
        raise CreditAssignmentAuditError("direct pressure is not finite")
    return {
        "combined": combined,
        "expected_conditional_entropy": conditional_term,
        "family_entropy": family_term,
        "policy": policy,
    }


def stratum_labels(
    *,
    effective_floor: Real,
    card_reward_ordinal: int,
    take_probability: Real,
    family_margin: Real,
) -> dict[str, str]:
    floor = _finite(effective_floor, "effective floor", minimum=0.0)
    ordinal = _integer(card_reward_ordinal, "card reward ordinal")
    probability = _finite(
        take_probability, "take probability", minimum=0.0, maximum=1.0
    )
    margin = _finite(family_margin, "family margin", minimum=0.0)
    return {
        "effective_floor": "<17" if floor < 17.0 else "17..33" if floor < 34.0 else ">=34",
        "family_margin": (
            "[0,0.025)"
            if margin < 0.025
            else "[0.025,0.05)"
            if margin < 0.05
            else "[0.05,0.075)"
            if margin < 0.075
            else "[0.075,+inf)"
        ),
        "ordinal": "first" if ordinal == 0 else "second" if ordinal == 1 else "later",
        "take_propensity": (
            "[0,0.50)"
            if probability < 0.50
            else "[0.50,0.51)"
            if probability < 0.51
            else "[0.51,0.52)"
            if probability < 0.52
            else "[0.52,1]"
        ),
    }


def _mean(values: Sequence[float]) -> float | None:
    return math.fsum(values) / len(values) if values else None


def _pressure_value(row: Mapping[str, Any], name: str) -> float:
    key = f"{name}_pressure" if name != "combined" else "combined_pressure"
    if key in row:
        return _finite(row[key], key)
    pressure = _mapping(row.get("pressure"), "row.pressure")
    return _finite(pressure.get(name), f"row.pressure.{name}")


def summarize_stratum(
    name: str, rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Summarize one fixed decision-level descriptive stratum."""
    values = list(_sequence(rows, f"stratum {name} rows"))
    selected_counts = Counter(
        _nonempty_string(row.get("selected_family"), "selected family")
        for row in values
    )
    take_count = selected_counts.get("take", 0)
    skip_count = selected_counts.get("skip", 0)
    support = (
        "supported"
        if len(values) >= _SUPPORT_MINIMUM_ROWS
        and take_count >= _SUPPORT_MINIMUM_FAMILY_ROWS
        and skip_count >= _SUPPORT_MINIMUM_FAMILY_ROWS
        else "insufficient"
    )
    component_names = (
        "policy",
        "family_entropy",
        "expected_conditional_entropy",
        "combined",
    )
    components = {}
    for component in component_names:
        component_values = [_pressure_value(row, component) for row in values]
        components[component] = {
            "mean": _mean(component_values),
            "sum": math.fsum(component_values),
        }
    associations = {}
    for family in sorted(selected_counts):
        family_rows = [row for row in values if row.get("selected_family") == family]
        associations[family] = {
            "count": len(family_rows),
            "mean_normalized_return": _mean(
                [_finite(row.get("normalized_return"), "normalized return") for row in family_rows]
            ),
            "mean_reward_to_go": _mean(
                [_finite(row.get("reward_to_go"), "reward to go") for row in family_rows]
            ),
        }
    result: dict[str, Any] = {
        "combined_pressure_mean": components["combined"]["mean"],
        "combined_pressure_sum": components["combined"]["sum"],
        "eligible_count": len(values),
        "label": name,
        "pressure_components": components,
        "selected_family_associations": associations,
        "selected_family_counts": dict(sorted(selected_counts.items())),
        "skip_count": skip_count,
        "support": support,
        "take_count": take_count,
    }
    optional_metrics = {
        "mean_expected_conditional_entropy": (
            "expected_conditional_entropy"
        ),
        "mean_family_entropy": "family_entropy",
        "mean_family_margin": "family_margin",
        "mean_normalized_return": "normalized_return",
        "mean_reward_to_go": "reward_to_go",
        "mean_take_conditional_entropy": "take_conditional_entropy",
        "mean_take_probability": "take_probability",
    }
    for output_name, row_name in optional_metrics.items():
        present = [
            _finite(row[row_name], row_name)
            for row in values
            if row_name in row
        ]
        result[output_name] = _mean(present)
    return result


def summarize_seed_clusters(
    rows: Sequence[Mapping[str, Any]],
    *,
    all_seeds: Sequence[int] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        seed = _integer(row.get("seed"), "seed")
        grouped[seed].append(row)
    seeds = (
        sorted({_integer(seed, "seed") for seed in all_seeds})
        if all_seeds is not None
        else sorted(grouped)
    )
    result = []
    for seed in seeds:
        seed_rows = grouped.get(seed, [])
        take_rows = [row for row in seed_rows if row.get("selected_family") == "take"]
        skip_rows = [row for row in seed_rows if row.get("selected_family") == "skip"]
        result.append(
            {
                "combined_pressure_sum": math.fsum(
                    _pressure_value(row, "combined") for row in seed_rows
                ),
                "eligible_count": len(seed_rows),
                "mean_reward_to_go": _mean(
                    [_finite(row.get("reward_to_go"), "reward to go") for row in seed_rows]
                ),
                "seed": seed,
                "skip_count": len(skip_rows),
                "skip_mean_reward_to_go": _mean(
                    [_finite(row.get("reward_to_go"), "reward to go") for row in skip_rows]
                ),
                "take_count": len(take_rows),
                "take_mean_reward_to_go": _mean(
                    [_finite(row.get("reward_to_go"), "reward to go") for row in take_rows]
                ),
            }
        )
    return result


def classify_verdict(
    *,
    reconstruction_valid: bool,
    global_supported: bool,
    supported_dimensions: Mapping[str, bool],
    chunk_pressures: Sequence[Real],
    terminal_window_margins: Sequence[Real],
    nonchunk_strata: Sequence[Mapping[str, Any]],
) -> str:
    """Apply the pre-registered four-way verdict precedence."""
    if reconstruction_valid is not True:
        raise CreditAssignmentAuditError(
            "invalid reconstruction must abort without a verdict"
        )
    expected_dimensions = {
        "effective_floor",
        "family_margin",
        "ordinal",
        "take_propensity",
    }
    if set(supported_dimensions) != expected_dimensions or any(
        type(value) is not bool for value in supported_dimensions.values()
    ):
        raise CreditAssignmentAuditError("supported dimensions are invalid")
    if not global_supported or not all(supported_dimensions.values()):
        return "insufficient_overlap_or_evidence"
    pressures = [
        _finite(value, f"chunk pressure[{index}]")
        for index, value in enumerate(chunk_pressures)
    ]
    margins = [
        _finite(value, f"terminal margin[{index}]", minimum=0.0)
        for index, value in enumerate(terminal_window_margins)
    ]
    if len(pressures) != 8 or len(margins) != 4:
        raise CreditAssignmentAuditError("verdict coordinates are invalid")
    margins_grow = all(
        current > previous
        for previous, current in zip(margins[:-1], margins[1:], strict=True)
    )
    if any(value <= 0.0 for value in pressures) or not margins_grow:
        return "direct_take_pressure_not_aligned"
    for index, raw_stratum in enumerate(nonchunk_strata):
        stratum = _mapping(raw_stratum, f"nonchunk stratum[{index}]")
        if stratum.get("support") == "supported" and _finite(
            stratum.get("combined_pressure_sum"),
            f"nonchunk stratum[{index}] pressure",
        ) <= 0.0:
            return "direct_take_pressure_aligned_but_stratum_heterogeneous"
    return "direct_take_pressure_consistently_aligned"


def render_markdown(report: Mapping[str, Any]) -> str:
    """Render the bounded human summary from the canonical report object."""
    verdict = _mapping(report.get("verdict"), "report.verdict")
    analysis = _mapping(report.get("analysis"), "report.analysis")
    reconstruction = _mapping(
        report.get("reconstruction"), "report.reconstruction"
    )
    global_summary = _mapping(
        analysis.get("global_summary"), "report.analysis.global_summary"
    )
    terminal_window = _mapping(
        analysis.get("terminal_window"), "report.analysis.terminal_window"
    )
    lines = [
        "# Hierarchical Card-Reward Credit-Assignment Audit",
        "",
        "## Verdict",
        "",
        f"`{verdict['classification']}`",
        "",
        "This verdict is descriptive only. It does not authorize an algorithm "
        "change or another empirical run.",
        "",
        "## Evidence",
        "",
        f"- Training chunks: {reconstruction['chunk_count']}",
        f"- Training episodes: {reconstruction['training_episode_count']}",
        f"- Aligned decisions: {reconstruction['decision_count']}",
        f"- Eligible card rewards: {analysis['eligible_decision_count']}",
        f"- Recorded take selections: {global_summary['take_count']}",
        f"- Recorded skip selections: {global_summary['skip_count']}",
        f"- Global support: {global_summary['support']}",
        "- Terminal-window mean margins: "
        + ", ".join(
            f"{float(value):.9f}"
            for value in terminal_window["mean_take_family_margins"]
        ),
        "",
        "## Chunk Pressure",
        "",
        "| Chunk | Eligible | Take | Skip | Combined pressure | Mean margin |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for chunk in analysis.get("chunk_summaries", []):
        lines.append(
            "| {chunk_index} | {eligible_count} | {take_count} | {skip_count} | "
            "{combined_pressure_sum:.12g} | {mean_family_margin:.9f} |".format(
                **chunk
            )
        )
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.get("limitations", []))
    lines.extend(["", "## Authority", ""])
    authority = _mapping(report.get("authority"), "report.authority")
    lines.extend(f"- {name}: false" for name in sorted(authority))
    lines.append("")
    return "\n".join(lines)


def _stage_payload(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    ) as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
        return Path(stream.name)


def _write_pair_with_rollback(
    output_json: Path,
    json_payload: bytes,
    output_markdown: Path,
    markdown_payload: bytes,
) -> None:
    if output_json.resolve(strict=False) == output_markdown.resolve(strict=False):
        raise CreditAssignmentAuditError("JSON and Markdown outputs must differ")
    staged: list[Path] = []
    backups: dict[Path, Path | None] = {}
    installed: list[Path] = []
    try:
        staged_json = _stage_payload(output_json, json_payload)
        staged_markdown = _stage_payload(output_markdown, markdown_payload)
        staged.extend((staged_json, staged_markdown))
        for output in (output_json, output_markdown):
            backups[output] = (
                _stage_payload(output, output.read_bytes())
                if output.exists()
                else None
            )
        os.replace(staged_json, output_json)
        installed.append(output_json)
        os.replace(staged_markdown, output_markdown)
        installed.append(output_markdown)
    except BaseException:
        for output in reversed(installed):
            backup = backups.get(output)
            if backup is None:
                output.unlink(missing_ok=True)
            else:
                os.replace(backup, output)
                backups[output] = None
        raise
    finally:
        for path in staged:
            path.unlink(missing_ok=True)
        for path in backups.values():
            if path is not None:
                path.unlink(missing_ok=True)


def publish_reports(
    report: Mapping[str, Any],
    output_json: Path | str,
    output_markdown: Path | str,
) -> None:
    """Atomically publish canonical JSON and generated Markdown."""
    value = dict(report)
    if value.get("schema_version") != AUDIT_SCHEMA_VERSION:
        raise CreditAssignmentAuditError("report schema mismatch")
    authority = _mapping(value.get("authority"), "report.authority")
    if authority != audit_authority():
        raise CreditAssignmentAuditError("report authority must be all false")
    downstream = _mapping(
        _mapping(value.get("verdict"), "report.verdict").get(
            "downstream_authority"
        ),
        "report.verdict.downstream_authority",
    )
    if downstream != audit_authority():
        raise CreditAssignmentAuditError(
            "report downstream authority must be all false"
        )
    json_payload = canonical_json_bytes(value)
    markdown_payload = render_markdown(value).encode("utf-8")
    _write_pair_with_rollback(
        Path(output_json),
        json_payload,
        Path(output_markdown),
        markdown_payload,
    )


def _all_false_authority(value: Any, label: str) -> dict[str, bool]:
    authority = _mapping(value, label)
    if authority != audit_authority():
        raise CreditAssignmentAuditError(
            f"{label} must be exact all-false authority"
        )
    return audit_authority()


def _git_blob_at_commit(repo_root: Path, commit: str, relative: str) -> bytes:
    if not _COMMIT_RE.fullmatch(commit):
        raise CreditAssignmentAuditError("planning commit is invalid")
    path = _canonical_relative_path(relative, "planning path")
    completed = _git_optional(repo_root, "show", f"{commit}:{path}")
    if completed.returncode != 0:
        raise CreditAssignmentAuditError(
            f"planning path is absent from commit: {path}"
        )
    return completed.stdout


def _verify_git_binding(
    repo_root: Path,
    commit: str,
    binding: Mapping[str, Any],
    label: str,
) -> None:
    relative, expected_size, expected_digest = _validate_basic_binding(
        binding, label
    )
    payload = _git_blob_at_commit(repo_root, commit, relative)
    if (
        len(payload) != expected_size
        or hashlib.sha256(payload).hexdigest() != expected_digest
    ):
        raise CreditAssignmentAuditError(f"{label} Git identity mismatch")


def _repo_binding_path(
    repo_root: Path, binding: Mapping[str, Any], label: str
) -> Path:
    relative = _canonical_relative_path(binding.get("path"), f"{label}.path")
    target = (repo_root / Path(relative)).resolve(strict=False)
    try:
        target.relative_to(repo_root)
    except ValueError as exc:
        raise CreditAssignmentAuditError(f"{label} escapes repository") from exc
    return target


def _expected_preimplementation_contract() -> dict[str, bool]:
    return {
        "audit_source_committed": False,
        "consumed_experiment_immutable": True,
        "environment_constructed": False,
        "experiment_rerun": False,
        "model_loaded": False,
        "native_loaded": False,
        "seed_accessed": False,
        "source_only": True,
        "terminal_bundle_read_only": True,
        "torch_imported": False,
        "verifier_executed_source_only": True,
    }


def _expected_planned_paths() -> dict[str, str]:
    return {
        "json_report": DEFAULT_JSON_REPORT_PATH,
        "markdown_report": DEFAULT_MARKDOWN_REPORT_PATH,
        "source": DEFAULT_SOURCE_PATH,
        "tests": DEFAULT_TEST_PATH,
    }


def _expected_input_paths() -> dict[str, str]:
    terminal = DEFAULT_TERMINAL_DIRECTORY
    return {
        "artifact_manifest": f"{terminal}/artifact_manifest.json",
        "authorization": f"{terminal}/authorization.json",
        "execution_journal": f"{terminal}/execution_journal.json",
        "isolation": f"{terminal}/isolation.json",
        "lease_control": f"{terminal}/.execution.lease",
        "metrics": f"{terminal}/metrics.json",
        "postmortem": DEFAULT_POSTMORTEM_PATH,
        "registration": f"{terminal}/registration.json",
        "terminal": f"{terminal}/terminal.json",
        "training_rows": f"{terminal}/training_rows.json.gz",
        "verifier_source": (
            "analysis_scripts/verify_noncombat_hierarchical_"
            "simulator_learning_experiment.py"
        ),
    }


def validate_preimplementation_record(
    repo_root: Path | str,
    record_path: Path | str = DEFAULT_PREIMPLEMENTATION_PATH,
    *,
    locked_lease_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Validate the fixed source-only record and every bound existing input."""
    root = Path(repo_root).resolve(strict=True)
    path = Path(record_path)
    if not path.is_absolute():
        path = root / path
    raw = _regular_file(path, "preimplementation record").read_bytes()
    record = parse_canonical_json_bytes(raw, "preimplementation record")
    _exact_keys(
        record,
        {
            "authority",
            "contract",
            "identity",
            "inputs",
            "planned_paths",
            "planning",
            "schema_version",
            "verifier_result",
        },
        "preimplementation record",
    )
    if record.get("schema_version") != PREIMPLEMENTATION_SCHEMA_VERSION:
        raise CreditAssignmentAuditError("preimplementation schema mismatch")
    _all_false_authority(
        record.get("authority"), "preimplementation authority"
    )
    if record.get("contract") != _expected_preimplementation_contract():
        raise CreditAssignmentAuditError("preimplementation contract mismatch")
    identity = _mapping(record.get("identity"), "preimplementation identity")
    _exact_keys(
        identity,
        {
            "audit_change",
            "consumed_logical_execution_id",
            "planning_commit",
        },
        "preimplementation identity",
    )
    if (
        identity.get("audit_change")
        != "audit-hierarchical-card-reward-credit-assignment"
        or identity.get("consumed_logical_execution_id")
        != LOGICAL_EXECUTION_ID
    ):
        raise CreditAssignmentAuditError("preimplementation identity mismatch")
    planning_commit = _nonempty_string(
        identity.get("planning_commit"), "planning commit"
    )
    if not _COMMIT_RE.fullmatch(planning_commit):
        raise CreditAssignmentAuditError("planning commit is invalid")
    if record.get("planned_paths") != _expected_planned_paths():
        raise CreditAssignmentAuditError("planned paths mismatch")

    planning = _mapping(record.get("planning"), "preimplementation planning")
    _exact_keys(planning, {"commit", "files"}, "preimplementation planning")
    if planning.get("commit") != planning_commit:
        raise CreditAssignmentAuditError("planning commit mismatch")
    planning_files = _mapping(
        planning.get("files"), "preimplementation planning files"
    )
    if set(planning_files) != {"design", "proposal", "spec", "tasks"}:
        raise CreditAssignmentAuditError("planning file set mismatch")
    for name in sorted(planning_files):
        binding = _mapping(
            planning_files[name], f"preimplementation planning.{name}"
        )
        _exact_keys(
            binding,
            {"path", "sha256", "size_bytes"},
            f"preimplementation planning.{name}",
        )
        _verify_git_binding(
            root,
            planning_commit,
            binding,
            f"preimplementation planning.{name}",
        )

    inputs = _mapping(record.get("inputs"), "preimplementation inputs")
    expected_input_names = set(_expected_input_paths()) | {"checkpoints"}
    if set(inputs) != expected_input_names:
        raise CreditAssignmentAuditError("preimplementation input set mismatch")
    expected_paths = _expected_input_paths()
    for name, expected_path in sorted(expected_paths.items()):
        binding = _mapping(inputs[name], f"preimplementation input {name}")
        if binding.get("path") != expected_path:
            raise CreditAssignmentAuditError(
                f"preimplementation input path mismatch: {name}"
            )
        if name == "training_rows":
            load_bound_gzip_json(
                _repo_binding_path(root, binding, name), binding, name
            )
        elif name == "lease_control":
            _exact_keys(
                binding,
                {
                    "analytical_evidence",
                    "exclusive_nonblocking_lock_required",
                    "path",
                    "sha256",
                    "size_bytes",
                    "tracked",
                },
                "preimplementation lease control",
            )
            if (
                binding.get("analytical_evidence") is not False
                or binding.get("exclusive_nonblocking_lock_required") is not True
                or binding.get("tracked") is not False
            ):
                raise CreditAssignmentAuditError(
                    "preimplementation lease control mismatch"
                )
            if locked_lease_bytes is None:
                verify_file_binding(
                    _repo_binding_path(root, binding, name), binding, name
                )
            else:
                _verify_payload_binding(locked_lease_bytes, binding, name)
        else:
            _exact_keys(
                binding,
                {"path", "sha256", "size_bytes"},
                f"preimplementation input {name}",
            )
            verify_file_binding(
                _repo_binding_path(root, binding, name), binding, name
            )

    checkpoints = _sequence(
        inputs.get("checkpoints"), "preimplementation checkpoints"
    )
    if len(checkpoints) != 8:
        raise CreditAssignmentAuditError("checkpoint binding count mismatch")
    for index, raw_binding in enumerate(checkpoints, start=1):
        binding = _mapping(raw_binding, f"checkpoint binding {index}")
        _exact_keys(
            binding,
            {"path", "sha256", "size_bytes"},
            f"checkpoint binding {index}",
        )
        expected_path = (
            f"{DEFAULT_TERMINAL_DIRECTORY}/checkpoints/"
            f"checkpoint_{index:04d}.json"
        )
        if binding.get("path") != expected_path:
            raise CreditAssignmentAuditError("checkpoint path mismatch")
        verify_file_binding(
            _repo_binding_path(root, binding, f"checkpoint {index}"),
            binding,
            f"checkpoint {index}",
        )

    verifier_result = _mapping(
        record.get("verifier_result"), "preimplementation verifier result"
    )
    expected_verifier = {
        "artifact_count": 22,
        "checkpoint_count": 8,
        "logical_execution_id": LOGICAL_EXECUTION_ID,
        "repository_identity_verified": True,
        "training_chunk_count": 8,
        "verdict": TERMINAL_VERDICT,
        "verification": "verified",
    }
    if verifier_result != expected_verifier:
        raise CreditAssignmentAuditError(
            "preimplementation verifier result mismatch"
        )
    postmortem_binding = _mapping(inputs["postmortem"], "postmortem binding")
    postmortem, _ = load_bound_json(
        _repo_binding_path(root, postmortem_binding, "postmortem"),
        postmortem_binding,
        "postmortem",
    )
    verification = _mapping(postmortem.get("verification"), "postmortem verification")
    if (
        verification.get("artifact_count") != 22
        or verification.get("checkpoint_count") != 8
        or verification.get("training_chunk_count") != 8
        or verification.get("repository_identity_verified") is not True
        or verification.get("standard_library_verifier") != "valid"
        or verification.get("verdict") != TERMINAL_VERDICT
    ):
        raise CreditAssignmentAuditError("postmortem verifier result mismatch")
    return record


def _verify_tracked_paths(repo_root: Path, relative_paths: Sequence[str]) -> None:
    paths = sorted(
        {
            _canonical_relative_path(path, "tracked input path")
            for path in relative_paths
        }
    )
    if not paths:
        raise CreditAssignmentAuditError("tracked input path set is empty")
    tracked = set(
        _git(repo_root, "ls-tree", "-r", "--name-only", "HEAD", "--", *paths)
        .decode("utf-8")
        .splitlines()
    )
    if tracked != set(paths):
        raise CreditAssignmentAuditError("required analytical input is untracked")
    completed = _git_optional(repo_root, "diff", "--quiet", "HEAD", "--", *paths)
    if completed.returncode not in {0, 1}:
        raise CreditAssignmentAuditError("Git input identity check failed")
    if completed.returncode == 1:
        raise CreditAssignmentAuditError(
            "required analytical input differs from HEAD"
        )


def _terminal_snapshot(terminal_root: Path) -> tuple[tuple[str, int, str], ...]:
    rows = []
    for candidate in sorted(
        (path for path in terminal_root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(terminal_root).as_posix(),
    ):
        relative = candidate.relative_to(terminal_root).as_posix()
        if relative == ".execution.lease":
            continue
        if _is_reparse_point(candidate):
            raise CreditAssignmentAuditError(
                "terminal bundle contains a reparse point"
            )
        size, digest = _hash_file(candidate)
        rows.append((relative, size, digest))
    return tuple(rows)


def _validate_manifest(
    manifest: Mapping[str, Any], terminal_root: Path
) -> dict[str, dict[str, Any]]:
    _exact_keys(
        manifest,
        {
            "artifact_count",
            "artifacts",
            "authority",
            "identity",
            "manifest_kind",
            "schema_version",
            "verdict",
        },
        "terminal artifact manifest",
    )
    if (
        manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or manifest.get("manifest_kind") != "full_terminal"
        or manifest.get("verdict") != TERMINAL_VERDICT
        or manifest.get("artifact_count") != 22
    ):
        raise CreditAssignmentAuditError("terminal manifest contract mismatch")
    _all_false_authority(manifest.get("authority"), "terminal manifest authority")
    identity = _mapping(manifest.get("identity"), "terminal manifest identity")
    _exact_keys(
        identity,
        {
            "authorization_sha256",
            "logical_execution_id",
            "registration_sha256",
        },
        "terminal manifest identity",
    )
    if identity.get("logical_execution_id") != LOGICAL_EXECUTION_ID:
        raise CreditAssignmentAuditError("terminal manifest identity mismatch")
    _sha256(identity.get("authorization_sha256"), "authorization identity")
    _sha256(identity.get("registration_sha256"), "registration identity")
    artifacts = _sequence(manifest.get("artifacts"), "terminal artifacts")
    if len(artifacts) != 22:
        raise CreditAssignmentAuditError("terminal artifact count mismatch")
    bindings: dict[str, dict[str, Any]] = {}
    for index, raw_binding in enumerate(artifacts):
        binding = dict(_mapping(raw_binding, f"terminal artifact[{index}]"))
        path = _canonical_relative_path(
            binding.get("path"), f"terminal artifact[{index}].path"
        )
        expected_keys = (
            {
                "canonical_sha256",
                "canonical_size_bytes",
                "compression",
                "path",
                "sha256",
                "size_bytes",
            }
            if path == "training_rows.json.gz"
            else {"path", "sha256", "size_bytes"}
        )
        _exact_keys(binding, expected_keys, f"terminal artifact {path}")
        if path in bindings:
            raise CreditAssignmentAuditError("duplicate terminal artifact path")
        verify_file_binding(terminal_root / Path(path), binding, path)
        bindings[path] = binding
    if list(bindings) != sorted(bindings):
        raise CreditAssignmentAuditError("terminal artifacts are not sorted")
    expected_inventory = set(bindings) | {"artifact_manifest.json"}
    observed_inventory = {
        path.relative_to(terminal_root).as_posix()
        for path in terminal_root.rglob("*")
        if path.is_file()
        and path.relative_to(terminal_root).as_posix() != ".execution.lease"
    }
    if observed_inventory != expected_inventory:
        raise CreditAssignmentAuditError("terminal artifact inventory mismatch")
    return bindings


_TRAINING_ROW_KEYS = {
    "action_generator_state_sha256",
    "candidate_scores",
    "candidates",
    "category",
    "chunk_index",
    "conditional_probabilities",
    "decision_id",
    "decision_index",
    "entropies",
    "family_order",
    "family_probabilities",
    "family_score_margin",
    "formal_reward",
    "joint_probabilities",
    "joint_probability_max_action_ids",
    "legal_action_ids",
    "multi_family",
    "raw_score_max_action_ids",
    "raw_score_max_family_ids",
    "schema_version",
    "score_greedy_action_ids",
    "score_greedy_family_ids",
    "score_margin",
    "seed",
    "selected_action_id",
    "selected_family",
    "selected_terms",
    "selection_mode",
    "state_effect",
}

_TRAINING_CHUNK_KEYS = {
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


def _close(actual: Any, expected: float, label: str) -> float:
    value = _finite(actual, label)
    if not math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12):
        raise CreditAssignmentAuditError(f"{label} differs from recomputation")
    return value


def _close_training(actual: Any, expected: float, label: str) -> float:
    value = _finite(actual, label)
    if not math.isclose(value, expected, rel_tol=2e-5, abs_tol=2e-6):
        raise CreditAssignmentAuditError(
            f"{label} differs from registered objective evidence"
        )
    return value


def _softmax(values: Sequence[float]) -> list[float]:
    if not values:
        raise CreditAssignmentAuditError("softmax input is empty")
    maximum = max(values)
    weights = [math.exp(value - maximum) for value in values]
    denominator = math.fsum(weights)
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise CreditAssignmentAuditError("diagnostic softmax is invalid")
    return [weight / denominator for weight in weights]


def _margin(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    ordered = sorted(values, reverse=True)
    return ordered[0] - ordered[1]


def _validate_optional_margin(
    value: Any, expected: float | None, label: str
) -> float | None:
    if expected is None:
        if value is not None:
            raise CreditAssignmentAuditError(f"{label} must be null")
        return None
    return _close(value, expected, label)


def _validate_training_row(
    value: Any,
    *,
    chunk_index: int,
    row_index: int,
    previous_generator_after: str | None,
) -> tuple[dict[str, Any], str]:
    label = f"chunk {chunk_index} training row[{row_index}]"
    row = dict(_mapping(value, label))
    _exact_keys(row, _TRAINING_ROW_KEYS, label)
    if (
        row.get("schema_version") != TRAINING_ROW_SCHEMA_VERSION
        or row.get("selection_mode") != "family-first-then-conditional-v1"
        or row.get("chunk_index") != chunk_index
    ):
        raise CreditAssignmentAuditError(f"{label} schema or coordinate mismatch")
    seed = _integer(row.get("seed"), f"{label}.seed")
    decision_index = _integer(
        row.get("decision_index"), f"{label}.decision_index"
    )
    if row.get("decision_id") != f"seed-{seed}:decision-{decision_index}":
        raise CreditAssignmentAuditError(f"{label} decision identity mismatch")
    if row.get("category") not in {"card_reward", "event", "route", "shop"}:
        raise CreditAssignmentAuditError(f"{label} category mismatch")

    candidates = list(_sequence(row.get("candidates"), f"{label}.candidates"))
    action_ids: list[str] = []
    families: list[str] = []
    for candidate_index, raw_candidate in enumerate(candidates):
        candidate = _mapping(
            raw_candidate, f"{label}.candidates[{candidate_index}]"
        )
        _exact_keys(
            candidate,
            {"action_id", "kind"},
            f"{label}.candidates[{candidate_index}]",
        )
        action_ids.append(
            _nonempty_string(
                candidate.get("action_id"),
                f"{label}.candidates[{candidate_index}].action_id",
            )
        )
        families.append(
            _nonempty_string(
                candidate.get("kind"),
                f"{label}.candidates[{candidate_index}].kind",
            )
        )
    if not action_ids or len(set(action_ids)) != len(action_ids):
        raise CreditAssignmentAuditError(f"{label} candidate identity mismatch")
    if list(_sequence(row.get("legal_action_ids"), f"{label}.legal_action_ids")) != action_ids:
        raise CreditAssignmentAuditError(f"{label} legal action order mismatch")
    family_order = list(
        _sequence(row.get("family_order"), f"{label}.family_order")
    )
    if family_order != sorted(set(families)):
        raise CreditAssignmentAuditError(f"{label} family order mismatch")
    if row.get("multi_family") is not (len(family_order) > 1):
        raise CreditAssignmentAuditError(f"{label} multi-family mismatch")

    score_mapping = _mapping(row.get("candidate_scores"), f"{label}.scores")
    if set(score_mapping) != set(action_ids):
        raise CreditAssignmentAuditError(f"{label} score identity mismatch")
    scores = [
        _finite(score_mapping[action_id], f"{label}.score[{action_id}]")
        for action_id in action_ids
    ]
    family_logits = [
        max(
            score
            for score, candidate_family in zip(scores, families, strict=True)
            if candidate_family == family
        )
        for family in family_order
    ]
    expected_family_probabilities = _softmax(family_logits)
    family_probability_mapping = _mapping(
        row.get("family_probabilities"), f"{label}.family_probabilities"
    )
    if set(family_probability_mapping) != set(family_order):
        raise CreditAssignmentAuditError(
            f"{label} family probability identity mismatch"
        )
    for family, expected in zip(
        family_order, expected_family_probabilities, strict=True
    ):
        _close(
            family_probability_mapping[family],
            expected,
            f"{label} family probability {family}",
        )

    conditional_mapping = _mapping(
        row.get("conditional_probabilities"),
        f"{label}.conditional_probabilities",
    )
    joint_mapping = _mapping(
        row.get("joint_probabilities"), f"{label}.joint_probabilities"
    )
    if set(conditional_mapping) != set(action_ids) or set(joint_mapping) != set(action_ids):
        raise CreditAssignmentAuditError(
            f"{label} candidate probability identity mismatch"
        )
    expected_conditionals: dict[str, float] = {}
    expected_joint: dict[str, float] = {}
    conditional_entropies: dict[str, float] = {}
    for family_index, family in enumerate(family_order):
        indices = [
            index
            for index, candidate_family in enumerate(families)
            if candidate_family == family
        ]
        probabilities = _softmax([scores[index] for index in indices])
        conditional_entropies[family] = _entropy(probabilities)
        for index, probability in zip(indices, probabilities, strict=True):
            action_id = action_ids[index]
            expected_conditionals[action_id] = probability
            expected_joint[action_id] = (
                expected_family_probabilities[family_index] * probability
            )
    for action_id in action_ids:
        _close(
            conditional_mapping[action_id],
            expected_conditionals[action_id],
            f"{label} conditional probability {action_id}",
        )
        _close(
            joint_mapping[action_id],
            expected_joint[action_id],
            f"{label} joint probability {action_id}",
        )

    maximum_score = max(scores)
    raw_max_actions = sorted(
        action_id
        for action_id, score in zip(action_ids, scores, strict=True)
        if score == maximum_score
    )
    family_by_action = dict(zip(action_ids, families, strict=True))
    raw_max_families = sorted(
        {family_by_action[action_id] for action_id in raw_max_actions}
    )
    if (
        row.get("raw_score_max_action_ids") != raw_max_actions
        or row.get("score_greedy_action_ids") != raw_max_actions
        or row.get("raw_score_max_family_ids") != raw_max_families
        or row.get("score_greedy_family_ids") != raw_max_families
    ):
        raise CreditAssignmentAuditError(f"{label} raw maximum mismatch")
    maximum_joint = max(expected_joint.values())
    joint_max_actions = sorted(
        action_id
        for action_id, probability in expected_joint.items()
        if probability == maximum_joint
    )
    if row.get("joint_probability_max_action_ids") != joint_max_actions:
        raise CreditAssignmentAuditError(f"{label} joint maximum mismatch")
    _validate_optional_margin(
        row.get("score_margin"), _margin(scores), f"{label} score margin"
    )
    family_margin = _validate_optional_margin(
        row.get("family_score_margin"),
        _margin(family_logits),
        f"{label} family score margin",
    )

    selected_action = _nonempty_string(
        row.get("selected_action_id"), f"{label}.selected_action_id"
    )
    if selected_action not in action_ids:
        raise CreditAssignmentAuditError(f"{label} selected action is illegal")
    selected_index = action_ids.index(selected_action)
    selected_family = families[selected_index]
    if row.get("selected_family") != selected_family:
        raise CreditAssignmentAuditError(f"{label} selected family mismatch")
    selected_terms = _mapping(
        row.get("selected_terms"), f"{label}.selected_terms"
    )
    _exact_keys(
        selected_terms,
        {
            "conditional_log_probability",
            "family_log_probability",
            "joint_log_probability",
        },
        f"{label}.selected_terms",
    )
    family_probability = expected_family_probabilities[
        family_order.index(selected_family)
    ]
    conditional_probability = expected_conditionals[selected_action]
    _close(
        selected_terms.get("family_log_probability"),
        math.log(family_probability),
        f"{label} selected family log probability",
    )
    _close(
        selected_terms.get("conditional_log_probability"),
        math.log(conditional_probability),
        f"{label} selected conditional log probability",
    )
    _close(
        selected_terms.get("joint_log_probability"),
        math.log(family_probability) + math.log(conditional_probability),
        f"{label} selected joint log probability",
    )

    family_entropy = _entropy(expected_family_probabilities)
    expected_conditional_entropy = math.fsum(
        probability * conditional_entropies[family]
        for family, probability in zip(
            family_order, expected_family_probabilities, strict=True
        )
    )
    joint_entropy = _entropy(list(expected_joint.values()))
    entropies = _mapping(row.get("entropies"), f"{label}.entropies")
    _exact_keys(
        entropies,
        {"expected_conditional", "family", "joint"},
        f"{label}.entropies",
    )
    _close(entropies.get("family"), family_entropy, f"{label} family entropy")
    _close(
        entropies.get("expected_conditional"),
        expected_conditional_entropy,
        f"{label} expected conditional entropy",
    )
    _close(entropies.get("joint"), joint_entropy, f"{label} joint entropy")
    _close(
        entropies.get("joint"),
        family_entropy + expected_conditional_entropy,
        f"{label} entropy identity",
    )

    reward = _mapping(row.get("formal_reward"), f"{label}.formal_reward")
    _exact_keys(
        reward,
        {"floor_progress", "scalar_reward", "terminal_victory"},
        f"{label}.formal_reward",
    )
    floor_progress = _finite(
        reward.get("floor_progress"), f"{label} floor progress", minimum=0.0
    )
    victory = reward.get("terminal_victory")
    if type(victory) is not int or victory not in {0, 1}:
        raise CreditAssignmentAuditError(f"{label} victory channel mismatch")
    _close(
        reward.get("scalar_reward"),
        2.0 * victory + floor_progress,
        f"{label} scalar reward",
    )

    state_effect = _mapping(row.get("state_effect"), f"{label}.state_effect")
    _exact_keys(
        state_effect,
        {
            "actual_scores",
            "max_abs_relative_score_change",
            "nonzero",
            "relative_order_changed",
            "zero_state_scores",
        },
        f"{label}.state_effect",
    )
    if list(state_effect.get("actual_scores", [])) != scores:
        raise CreditAssignmentAuditError(f"{label} state score mismatch")

    hashes = _mapping(
        row.get("action_generator_state_sha256"), f"{label}.generator_hashes"
    )
    _exact_keys(
        hashes,
        {"after_conditional", "after_family", "before_family"},
        f"{label}.generator_hashes",
    )
    for name, digest in hashes.items():
        _sha256(digest, f"{label}.generator_hashes.{name}")
    if len(set(hashes.values())) != 3:
        raise CreditAssignmentAuditError(f"{label} generator did not advance")
    if (
        previous_generator_after is not None
        and hashes.get("before_family") != previous_generator_after
    ):
        raise CreditAssignmentAuditError(f"{label} generator chain mismatch")

    normalized = dict(row)
    normalized["_computed"] = {
        "conditional_entropies": conditional_entropies,
        "expected_conditional_entropy": expected_conditional_entropy,
        "family_entropy": family_entropy,
        "family_margin": family_margin,
        "raw_max_families": raw_max_families,
    }
    return normalized, _nonempty_string(
        hashes.get("after_conditional"), f"{label}.after_conditional"
    )


def _reconstruct_chunk_objective(
    rows: Sequence[Mapping[str, Any]],
    episode_seeds: Sequence[int],
) -> tuple[dict[str, float], dict[str, Any]]:
    returns = reconstruct_normalized_returns(rows, episode_seeds)
    normalized = returns["normalized_returns"]
    policy_loss = -sum(
        _finite(
            _mapping(row.get("selected_terms"), "selected terms").get(
                "joint_log_probability"
            ),
            "joint log probability",
        )
        * weight
        for row, weight in zip(rows, normalized, strict=True)
    ) / len(rows)
    mean_family_entropy = sum(
        _finite(
            _mapping(row.get("entropies"), "entropies").get("family"),
            "family entropy",
        )
        for row in rows
    ) / len(rows)
    mean_conditional_entropy = sum(
        _finite(
            _mapping(row.get("entropies"), "entropies").get(
                "expected_conditional"
            ),
            "expected conditional entropy",
        )
        for row in rows
    ) / len(rows)
    objective = {
        "loss": (
            policy_loss
            - _ENTROPY_COEFFICIENT * mean_family_entropy
            - _ENTROPY_COEFFICIENT * mean_conditional_entropy
        ),
        "mean_expected_conditional_entropy": mean_conditional_entropy,
        "mean_family_entropy": mean_family_entropy,
        "normalized_return_mean": float32_mean(normalized),
        "normalized_return_std": float32_population_std(
            normalized, mean=float32_mean(normalized)
        ),
        "policy_loss": policy_loss,
    }
    return objective, returns


def _validate_terminal_metadata(
    terminal_root: Path,
    bindings: Mapping[str, Mapping[str, Any]],
    manifest_identity: Mapping[str, Any],
) -> dict[str, Any]:
    loaded = {}
    for name in (
        "authorization.json",
        "evaluation.json",
        "execution_journal.json",
        "isolation.json",
        "metrics.json",
        "registration.json",
        "report.json",
        "terminal.json",
    ):
        loaded[name], _ = load_bound_json(
            terminal_root / name, bindings[name], name
        )
    authorization = loaded["authorization.json"]
    registration = loaded["registration.json"]
    terminal = loaded["terminal.json"]
    journal = loaded["execution_journal.json"]
    metrics = loaded["metrics.json"]
    evaluation = loaded["evaluation.json"]
    isolation = loaded["isolation.json"]
    report = loaded["report.json"]
    for name, value in loaded.items():
        if "authority" not in value:
            continue
        if name == "authorization.json":
            if value["authority"] != recorded_execution_authority():
                raise CreditAssignmentAuditError(
                    "authorization.json authority mismatch"
                )
        else:
            _all_false_authority(value["authority"], f"{name} authority")
    if (
        authorization.get("logical_experiment_id") != LOGICAL_EXECUTION_ID
        or registration.get("logical_experiment_id") != LOGICAL_EXECUTION_ID
    ):
        raise CreditAssignmentAuditError("registration identity mismatch")
    if (
        bindings["authorization.json"]["sha256"]
        != manifest_identity.get("authorization_sha256")
        or bindings["registration.json"]["sha256"]
        != manifest_identity.get("registration_sha256")
    ):
        raise CreditAssignmentAuditError("manifest control identity mismatch")
    for name, value in (("journal", journal), ("terminal", terminal)):
        if value.get("identity") != dict(manifest_identity):
            raise CreditAssignmentAuditError(f"{name} identity mismatch")
    if (
        terminal.get("verdict") != TERMINAL_VERDICT
        or terminal.get("holdout_accessed") is not False
        or terminal.get("checkpoint_count") != 8
        or terminal.get("training_rows_binding")
        != bindings["training_rows.json.gz"]
    ):
        raise CreditAssignmentAuditError("terminal verdict contract mismatch")
    if (
        metrics.get("verdict") != TERMINAL_VERDICT
        or metrics.get("checkpoint_count") != 8
        or metrics.get("training_chunk_count") != 8
        or metrics.get("isolation_unchanged") is not True
        or metrics.get("formal_rl_readiness_established") is not False
        or metrics.get("policy_quality_established") is not False
        or metrics.get("target_supported_outcomes_established") is not False
    ):
        raise CreditAssignmentAuditError("terminal metrics mismatch")
    resources = _mapping(metrics.get("resource_use"), "terminal resource use")
    if (
        resources.get("evaluation_episodes") != 0
        or resources.get("training_episodes") != 512
        or resources.get("total_episodes") != 512
        or resources.get("optimizer_updates") != 8
    ):
        raise CreditAssignmentAuditError("terminal resource use mismatch")
    if evaluation.get("evaluation") is not None:
        raise CreditAssignmentAuditError("evaluation evidence was accessed")
    if isolation.get("unchanged") is not True or isolation.get("pre") != isolation.get("post"):
        raise CreditAssignmentAuditError("terminal isolation mismatch")
    records = list(_sequence(journal.get("records"), "journal records"))
    if (
        len(records) != 12
        or [record.get("sequence") for record in records] != list(range(12))
        or records[-1].get("state") != "terminal"
        or records[-2].get("state") != "training_stopped_family_saturation"
    ):
        raise CreditAssignmentAuditError("execution journal mismatch")
    classification = _mapping(
        _mapping(records[-2].get("details"), "saturation details").get(
            "classification"
        ),
        "saturation classification",
    )
    if (
        classification.get("verdict") != TERMINAL_VERDICT
        or classification.get("window_chunk_indices") != [4, 5, 6, 7]
        or classification.get("saturated") is not True
    ):
        raise CreditAssignmentAuditError("saturation classification mismatch")
    if (
        report.get("logical_execution_id") != LOGICAL_EXECUTION_ID
        or report.get("verdict") != TERMINAL_VERDICT
        or report.get("formal_rl_readiness") != "unchanged_not_ready"
        or report.get("policy_quality_claim") is not False
        or report.get("target_supported_outcome_claim") is not False
    ):
        raise CreditAssignmentAuditError("terminal report mismatch")
    cohorts = _mapping(registration.get("cohorts"), "registration cohorts")
    train_seeds = [
        _integer(seed, f"registration train seed[{index}]")
        for index, seed in enumerate(
            _sequence(cohorts.get("train"), "registration train seeds")
        )
    ]
    if len(train_seeds) != 1024 or len(set(train_seeds)) != 1024:
        raise CreditAssignmentAuditError("registration training cohort mismatch")
    return {
        "registration": registration,
        "train_seeds": train_seeds,
    }


def _analyze_training_rows(
    training: Mapping[str, Any], train_seeds: Sequence[int]
) -> dict[str, Any]:
    _exact_keys(
        training,
        {"authority", "chunk_count", "chunks", "schema_version"},
        "training rows",
    )
    if training.get("schema_version") != TRAINING_ROWS_SCHEMA_VERSION:
        raise CreditAssignmentAuditError("training rows schema mismatch")
    _all_false_authority(training.get("authority"), "training rows authority")
    chunks = list(_sequence(training.get("chunks"), "training chunks"))
    if training.get("chunk_count") != 8 or len(chunks) != 8:
        raise CreditAssignmentAuditError("training chunk count mismatch")
    if len(train_seeds) < 512:
        raise CreditAssignmentAuditError("registered training cohort is incomplete")

    aligned_rows: list[dict[str, Any]] = []
    eligible_rows: list[dict[str, Any]] = []
    reconciliation: list[dict[str, Any]] = []
    previous_generator_after: str | None = None
    for chunk_index, raw_chunk in enumerate(chunks):
        chunk = dict(_mapping(raw_chunk, f"training chunk {chunk_index}"))
        _exact_keys(chunk, _TRAINING_CHUNK_KEYS, f"training chunk {chunk_index}")
        if (
            chunk.get("schema_version") != TRAINING_CHUNK_SCHEMA_VERSION
            or chunk.get("chunk_index") != chunk_index
            or chunk.get("complete") is not True
            or chunk.get("family_entropy_coefficient") != 0.01
            or chunk.get("conditional_entropy_coefficient") != 0.01
            or chunk.get("optimizer_update") != chunk_index + 1
        ):
            raise CreditAssignmentAuditError(
                f"training chunk {chunk_index} contract mismatch"
            )
        if chunk.get("episodes") != 64:
            raise CreditAssignmentAuditError(
                f"training chunk {chunk_index} episode count mismatch"
            )
        episode_seeds = [
            _integer(seed, f"training chunk {chunk_index} seed[{index}]")
            for index, seed in enumerate(
                _sequence(
                    chunk.get("episode_seeds"),
                    f"training chunk {chunk_index} episode seeds",
                )
            )
        ]
        expected_seeds = list(train_seeds[chunk_index * 64 : (chunk_index + 1) * 64])
        if episode_seeds != expected_seeds:
            raise CreditAssignmentAuditError(
                f"training chunk {chunk_index} seed order mismatch"
            )
        raw_rows = list(
            _sequence(
                chunk.get("diagnostic_rows"),
                f"training chunk {chunk_index} diagnostic rows",
            )
        )
        if not raw_rows or chunk.get("decisions") != len(raw_rows):
            raise CreditAssignmentAuditError(
                f"training chunk {chunk_index} decision count mismatch"
            )
        normalized_rows: list[dict[str, Any]] = []
        decision_indexes: dict[int, list[int]] = {
            seed: [] for seed in episode_seeds
        }
        for row_index, raw_row in enumerate(raw_rows):
            row, previous_generator_after = _validate_training_row(
                raw_row,
                chunk_index=chunk_index,
                row_index=row_index,
                previous_generator_after=previous_generator_after,
            )
            seed = row["seed"]
            if seed not in decision_indexes:
                raise CreditAssignmentAuditError(
                    f"training chunk {chunk_index} contains an unregistered seed"
                )
            decision_indexes[seed].append(row["decision_index"])
            normalized_rows.append(row)
        if any(
            indexes != list(range(len(indexes)))
            for indexes in decision_indexes.values()
        ):
            raise CreditAssignmentAuditError(
                f"training chunk {chunk_index} decision coordinates mismatch"
            )
        if chunk.get("categories") != sorted(
            {row["category"] for row in normalized_rows}
        ):
            raise CreditAssignmentAuditError(
                f"training chunk {chunk_index} category summary mismatch"
            )
        objective, returns = _reconstruct_chunk_objective(
            normalized_rows, episode_seeds
        )
        for name, expected in objective.items():
            _close_training(
                chunk.get(name),
                expected,
                f"training chunk {chunk_index} {name}",
            )
        gradient_before = _finite(
            chunk.get("gradient_norm_before_clip"),
            f"training chunk {chunk_index} gradient before clip",
            minimum=0.0,
        )
        gradient_after = _finite(
            chunk.get("gradient_norm_after_clip"),
            f"training chunk {chunk_index} gradient after clip",
            minimum=0.0,
        )
        if gradient_after > 1.0 + 1e-6 or gradient_after > gradient_before + 1e-6:
            raise CreditAssignmentAuditError(
                f"training chunk {chunk_index} gradient clipping mismatch"
            )
        resources = _mapping(
            chunk.get("resource_use"),
            f"training chunk {chunk_index} resource use",
        )
        if (
            resources.get("evaluation_episodes") != 0
            or resources.get("optimizer_updates") != chunk_index + 1
            or resources.get("training_episodes") != (chunk_index + 1) * 64
            or resources.get("total_episodes") != (chunk_index + 1) * 64
            or resources.get("completed_decisions")
            != sum(len(item.get("diagnostic_rows", [])) for item in chunks[: chunk_index + 1])
        ):
            raise CreditAssignmentAuditError(
                f"training chunk {chunk_index} resource accounting mismatch"
            )
        reconciliation.append(
            {
                "chunk_index": chunk_index,
                "decision_count": len(normalized_rows),
                "loss": objective["loss"],
                "mean_expected_conditional_entropy": objective[
                    "mean_expected_conditional_entropy"
                ],
                "mean_family_entropy": objective["mean_family_entropy"],
                "normalized_return_mean": objective["normalized_return_mean"],
                "normalized_return_std": objective["normalized_return_std"],
                "policy_loss": objective["policy_loss"],
                "recorded_loss": _finite(chunk.get("loss"), "recorded loss"),
                "recorded_policy_loss": _finite(
                    chunk.get("policy_loss"), "recorded policy loss"
                ),
            }
        )

        floor_progress_by_seed = {seed: 0.0 for seed in episode_seeds}
        card_ordinal_by_seed = {seed: 0 for seed in episode_seeds}
        reward_to_go = returns["reward_to_go"]
        normalized_returns = returns["normalized_returns"]
        for row_index, row in enumerate(normalized_rows):
            seed = row["seed"]
            effective_floor = floor_progress_by_seed[seed] * 57.0
            ordinal = card_ordinal_by_seed[seed]
            computed = _mapping(row.get("_computed"), "computed row evidence")
            family_margin = computed.get("family_margin")
            family_order = list(row["family_order"])
            eligible = (
                row["category"] == "card_reward"
                and row["multi_family"] is True
                and "take" in family_order
                and "skip" in family_order
            )
            aligned: dict[str, Any] = {
                "card_reward_ordinal": ordinal,
                "category": row["category"],
                "chunk_index": chunk_index,
                "decision_index": row["decision_index"],
                "effective_floor": effective_floor,
                "eligible_card_reward": eligible,
                "family_margin": family_margin,
                "normalized_return": normalized_returns[row_index],
                "raw_score_max_family_ids": list(
                    row["raw_score_max_family_ids"]
                ),
                "reward_to_go": reward_to_go[row_index],
                "seed": seed,
                "selected_family": row["selected_family"],
                "take_probability": None,
            }
            if eligible:
                if family_margin is None:
                    raise CreditAssignmentAuditError(
                        "eligible card reward lacks a family margin"
                    )
                take_probability = _finite(
                    _mapping(
                        row.get("family_probabilities"), "family probabilities"
                    ).get("take"),
                    "take probability",
                    minimum=0.0,
                    maximum=1.0,
                )
                conditional_entropies = _mapping(
                    computed.get("conditional_entropies"),
                    "computed conditional entropies",
                )
                pressure = direct_take_pressure(
                    normalized_return=normalized_returns[row_index],
                    selected_family=row["selected_family"],
                    take_probability=take_probability,
                    family_entropy=computed["family_entropy"],
                    take_conditional_entropy=conditional_entropies["take"],
                    expected_conditional_entropy=computed[
                        "expected_conditional_entropy"
                    ],
                    chunk_decision_count=len(normalized_rows),
                )
                labels = stratum_labels(
                    effective_floor=effective_floor,
                    card_reward_ordinal=ordinal,
                    take_probability=take_probability,
                    family_margin=family_margin,
                )
                aligned.update(
                    {
                        "combined_pressure": pressure["combined"],
                        "expected_conditional_entropy": computed[
                            "expected_conditional_entropy"
                        ],
                        "expected_conditional_entropy_pressure": pressure[
                            "expected_conditional_entropy"
                        ],
                        "family_entropy": computed["family_entropy"],
                        "family_entropy_pressure": pressure["family_entropy"],
                        "policy_pressure": pressure["policy"],
                        "strata": labels,
                        "take_conditional_entropy": conditional_entropies[
                            "take"
                        ],
                        "take_probability": take_probability,
                    }
                )
                eligible_rows.append(aligned)
            aligned_rows.append(aligned)
            reward = _mapping(row.get("formal_reward"), "formal reward")
            floor_progress_by_seed[seed] = math.fsum(
                (
                    floor_progress_by_seed[seed],
                    _finite(
                        reward.get("floor_progress"),
                        "floor progress",
                        minimum=0.0,
                    ),
                )
            )
            if row["category"] == "card_reward":
                card_ordinal_by_seed[seed] += 1

    if len(aligned_rows) != 11807:
        raise CreditAssignmentAuditError("aligned decision count mismatch")
    if len(eligible_rows) != 3559:
        raise CreditAssignmentAuditError("eligible card-reward count mismatch")

    global_summary = summarize_stratum("all", eligible_rows)
    chunk_summaries = []
    for chunk_index in range(8):
        summary = summarize_stratum(
            str(chunk_index),
            [row for row in eligible_rows if row["chunk_index"] == chunk_index],
        )
        summary["chunk_index"] = chunk_index
        chunk_summaries.append(summary)

    fixed_labels = {
        "effective_floor": ["<17", "17..33", ">=34"],
        "family_margin": [
            "[0,0.025)",
            "[0.025,0.05)",
            "[0.05,0.075)",
            "[0.075,+inf)",
        ],
        "ordinal": ["first", "second", "later"],
        "take_propensity": [
            "[0,0.50)",
            "[0.50,0.51)",
            "[0.51,0.52)",
            "[0.52,1]",
        ],
    }
    strata: dict[str, list[dict[str, Any]]] = {}
    supported_dimensions: dict[str, bool] = {}
    nonchunk_summaries: list[dict[str, Any]] = []
    for dimension, labels in fixed_labels.items():
        summaries = []
        for label in labels:
            summary = summarize_stratum(
                label,
                [
                    row
                    for row in eligible_rows
                    if _mapping(row.get("strata"), "row strata").get(dimension)
                    == label
                ],
            )
            summary["dimension"] = dimension
            summaries.append(summary)
            nonchunk_summaries.append(summary)
        strata[dimension] = summaries
        supported_dimensions[dimension] = any(
            summary["support"] == "supported" for summary in summaries
        )

    seed_clusters = summarize_seed_clusters(
        eligible_rows, all_seeds=train_seeds[:512]
    )
    terminal_chunks = chunk_summaries[4:8]
    terminal_rows = [
        row for row in eligible_rows if row["chunk_index"] in {4, 5, 6, 7}
    ]
    if (
        len(terminal_rows) != 1847
        or any(row["raw_score_max_family_ids"] != ["take"] for row in terminal_rows)
    ):
        raise CreditAssignmentAuditError(
            "terminal family-saturation evidence mismatch"
        )
    terminal_margins = [
        _finite(chunk["mean_family_margin"], "terminal mean family margin")
        for chunk in terminal_chunks
    ]
    chunk_pressures = [
        _finite(chunk["combined_pressure_sum"], "chunk pressure")
        for chunk in chunk_summaries
    ]
    verdict = classify_verdict(
        reconstruction_valid=True,
        global_supported=global_summary["support"] == "supported",
        supported_dimensions=supported_dimensions,
        chunk_pressures=chunk_pressures,
        terminal_window_margins=terminal_margins,
        nonchunk_strata=nonchunk_summaries,
    )
    aligned_payload = canonical_json_bytes(aligned_rows)
    return {
        "analysis": {
            "chunk_summaries": chunk_summaries,
            "eligible_decision_count": len(eligible_rows),
            "global_summary": global_summary,
            "seed_clusters": seed_clusters,
            "strata": strata,
            "supported_dimensions": supported_dimensions,
            "terminal_window": {
                "chunk_indices": [4, 5, 6, 7],
                "eligible_decision_count": len(terminal_rows),
                "mean_take_family_margins": terminal_margins,
                "strictly_growing": all(
                    current > previous
                    for previous, current in zip(
                        terminal_margins[:-1],
                        terminal_margins[1:],
                        strict=True,
                    )
                ),
                "unique_take_raw_maximum_count": len(terminal_rows),
            },
        },
        "reconstruction": {
            "aligned_rows": aligned_rows,
            "aligned_rows_sha256": hashlib.sha256(aligned_payload).hexdigest(),
            "chunk_count": 8,
            "chunk_objective_reconciliation": reconciliation,
            "decision_count": len(aligned_rows),
            "objective_reconciled": True,
            "training_episode_count": 512,
        },
        "verdict": verdict,
    }


def _forbidden_loaded_modules() -> list[str]:
    forbidden_fragments = (
        "noncombat_hierarchical_simulator_learning_runtime",
        "noncombat_simulator_adapter",
        "sts_lightspeed_noncombat_adapter",
    )
    return sorted(
        name
        for name in sys.modules
        if name == "torch"
        or name.startswith("torch.")
        or any(fragment in name for fragment in forbidden_fragments)
    )


def build_repository_audit(repo_root: Path | str) -> dict[str, Any]:
    """Build the canonical report from only the fixed immutable repository inputs."""
    root = Path(repo_root).resolve(strict=True)
    if _forbidden_loaded_modules():
        raise CreditAssignmentAuditError(
            "forbidden Torch, runtime, or native module was already loaded"
        )
    source_identity = verify_head_source(root, DEFAULT_SOURCE_PATH)
    test_identity = verify_head_source(root, DEFAULT_TEST_PATH)
    preimplementation_identity = verify_head_source(
        root, DEFAULT_PREIMPLEMENTATION_PATH
    )
    preimplementation_path = root / DEFAULT_PREIMPLEMENTATION_PATH
    preimplementation_head = parse_canonical_json_bytes(
        _git_blob_at_commit(
            root,
            preimplementation_identity["commit"],
            DEFAULT_PREIMPLEMENTATION_PATH,
        ),
        "HEAD preimplementation record",
    )
    head_inputs = _mapping(
        preimplementation_head.get("inputs"),
        "HEAD preimplementation inputs",
    )
    lease_binding = _mapping(
        head_inputs.get("lease_control"), "HEAD lease binding"
    )
    if lease_binding.get("path") != _expected_input_paths()["lease_control"]:
        raise CreditAssignmentAuditError("HEAD lease path mismatch")
    expected_identity = {
        "authorization_sha256": _sha256(
            _mapping(
                head_inputs.get("authorization"),
                "HEAD authorization binding",
            ).get("sha256"),
            "HEAD authorization SHA-256",
        ),
        "logical_execution_id": LOGICAL_EXECUTION_ID,
        "registration_sha256": _sha256(
            _mapping(
                head_inputs.get("registration"),
                "HEAD registration binding",
            ).get("sha256"),
            "HEAD registration SHA-256",
        ),
    }
    with hold_inactive_lease(
        _repo_binding_path(root, lease_binding, "execution lease"),
        lease_binding,
        expected_identity,
    ) as locked_lease_bytes:
        preimplementation = validate_preimplementation_record(
            root,
            preimplementation_path,
            locked_lease_bytes=locked_lease_bytes,
        )
        if preimplementation != preimplementation_head:
            raise CreditAssignmentAuditError(
                "preimplementation record differs from HEAD"
            )
        inputs = _mapping(
            preimplementation.get("inputs"), "preimplementation inputs"
        )
        manifest_binding = _mapping(
            inputs.get("artifact_manifest"), "artifact manifest binding"
        )
        manifest_path = _repo_binding_path(
            root, manifest_binding, "artifact manifest"
        )
        terminal_root = (root / DEFAULT_TERMINAL_DIRECTORY).resolve(
            strict=True
        )
        before = _terminal_snapshot(terminal_root)
        manifest, _ = load_bound_json(
            manifest_path, manifest_binding, "terminal artifact manifest"
        )
        bindings = _validate_manifest(manifest, terminal_root)
        if manifest.get("identity") != expected_identity:
            raise CreditAssignmentAuditError("terminal manifest identity drift")
        checkpoint_bindings = list(
            _sequence(inputs.get("checkpoints"), "checkpoint bindings")
        )
        for index, preimplementation_binding in enumerate(
            checkpoint_bindings, start=1
        ):
            expected = dict(_mapping(preimplementation_binding, "checkpoint binding"))
            expected["path"] = f"checkpoints/checkpoint_{index:04d}.json"
            if bindings[expected["path"]] != expected:
                raise CreditAssignmentAuditError(
                    "checkpoint manifest/preimplementation mismatch"
                )
        expected_training = dict(
            _mapping(inputs.get("training_rows"), "training rows binding")
        )
        expected_training["path"] = "training_rows.json.gz"
        if bindings["training_rows.json.gz"] != expected_training:
            raise CreditAssignmentAuditError(
                "training manifest/preimplementation mismatch"
            )
        tracked_paths = [
            DEFAULT_SOURCE_PATH,
            DEFAULT_PREIMPLEMENTATION_PATH,
            DEFAULT_POSTMORTEM_PATH,
            _mapping(inputs.get("verifier_source"), "verifier binding")["path"],
            f"{DEFAULT_TERMINAL_DIRECTORY}/artifact_manifest.json",
        ] + [
            f"{DEFAULT_TERMINAL_DIRECTORY}/{relative}" for relative in bindings
        ]
        _verify_tracked_paths(root, tracked_paths)
        metadata = _validate_terminal_metadata(
            terminal_root,
            bindings,
            _mapping(manifest.get("identity"), "manifest identity"),
        )
        training, _ = load_bound_gzip_json(
            terminal_root / "training_rows.json.gz",
            bindings["training_rows.json.gz"],
            "training rows",
        )
        analyzed = _analyze_training_rows(training, metadata["train_seeds"])
        after = _terminal_snapshot(terminal_root)
        if after != before:
            raise CreditAssignmentAuditError(
                "terminal bundle changed during audit"
            )
        _verify_tracked_paths(root, tracked_paths)
        if verify_head_source(root, DEFAULT_SOURCE_PATH) != source_identity:
            raise CreditAssignmentAuditError(
                "audit source identity changed during analysis"
            )
        if verify_head_source(root, DEFAULT_TEST_PATH) != test_identity:
            raise CreditAssignmentAuditError(
                "audit test identity changed during analysis"
            )
        if (
            verify_head_source(root, DEFAULT_PREIMPLEMENTATION_PATH)
            != preimplementation_identity
        ):
            raise CreditAssignmentAuditError(
                "preimplementation identity changed during analysis"
            )
    if _forbidden_loaded_modules():
        raise CreditAssignmentAuditError(
            "audit loaded a forbidden Torch, runtime, or native module"
        )
    report = {
        "analysis": analyzed["analysis"],
        "authority": audit_authority(),
        "identity": {
            "logical_execution_id": LOGICAL_EXECUTION_ID,
            "preimplementation": preimplementation_identity,
            "source": source_identity,
            "tests": test_identity,
        },
        "integrity": {
            "checkpoint_count": 8,
            "consumed_artifact_count": 22,
            "input_bindings_verified": True,
            "consumed_input_bindings": dict(inputs),
            "lease_locked_before_validation": True,
            "preimplementation_binding": {
                "path": DEFAULT_PREIMPLEMENTATION_PATH,
                "sha256": preimplementation_identity["sha256"],
                "size_bytes": preimplementation_identity["size_bytes"],
            },
            "source_only": True,
            "terminal_artifact_bindings": [
                dict(_mapping(binding, "terminal artifact binding"))
                for binding in manifest["artifacts"]
            ],
            "terminal_bundle_unchanged": True,
            "torch_native_runtime_imports": [],
            "verifier_result": preimplementation["verifier_result"],
        },
        "limitations": list(LIMITATIONS),
        "reconstruction": analyzed["reconstruction"],
        "schema_version": AUDIT_SCHEMA_VERSION,
        "verdict": {
            "classification": analyzed["verdict"],
            "downstream_authority": audit_authority(),
        },
    }
    canonical_json_bytes(report)
    return report


def _parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        description=(
            "Publish the fixed source-only hierarchical card-reward "
            "credit-assignment audit. This command accepts no overrides."
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    del args
    repo_root = Path(__file__).resolve().parents[1]
    report = build_repository_audit(repo_root)
    publish_reports(
        report,
        repo_root / DEFAULT_JSON_REPORT_PATH,
        repo_root / DEFAULT_MARKDOWN_REPORT_PATH,
    )
    print(
        json.dumps(
            {
                "eligible_decision_count": report["analysis"][
                    "eligible_decision_count"
                ],
                "schema_version": report["schema_version"],
                "verdict": report["verdict"]["classification"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
