"""Independent standard-library verifier for successor readiness evidence."""

from __future__ import annotations

import argparse
import copy
import ctypes
from ctypes import wintypes
import gc
import gzip
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any


REPORT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-report-v1"
)
CANDIDATE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-candidate-v1"
)
SEED_INVENTORY_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-seed-inventory-v1"
)
FRESH_SCHEDULE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1"
)
REPORT_FILENAME = "readiness_report.json"
REPORT_MARKDOWN_FILENAME = "readiness_report.md"
CANDIDATE_INVENTORY_FILENAME = "candidate_seed_inventory.json.gz"
PUBLICATION_FILENAMES = (
    CANDIDATE_INVENTORY_FILENAME,
    REPORT_FILENAME,
    REPORT_MARKDOWN_FILENAME,
)
CONSUMED_REGISTRATION_PATH = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_"
    "20260806_r1/registration.json"
)
CONSUMED_TERMINAL_PATH = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_"
    "20260806_r1/terminal.json"
)
CONSUMED_MANIFEST_PATH = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_"
    "20260806_r1/artifact_manifest.json"
)
BOTTLENECK_AUDIT_PATH = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_"
    "20260806_r1_execution_bottleneck_audit.json"
)
CONTROL_PLANE_REPAIR_PATH = (
    "reports/noncombat_cross_fitted_hierarchical_learning_successor_"
    "20260807_control_plane_repair.json"
)
HISTORICAL_THROUGHPUT_PATH = (
    "reports/noncombat_hierarchical_simulator_learning_successor_"
    "20260806_postmortem.json"
)
SUCCESSOR_CONTRACT_PATH = (
    "openspec/specs/noncombat-cross-fitted-hierarchical-learning-successor/"
    "spec.md"
)
READINESS_CHANGE_SPEC_PATH = (
    "openspec/specs/noncombat-cross-fitted-empirical-successor-readiness/"
    "spec.md"
)
AUDITOR_SOURCE_PATH = (
    "analysis_scripts/noncombat_cross_fitted_empirical_successor_readiness.py"
)
READINESS_VERIFIER_SOURCE_PATH = (
    "analysis_scripts/verify_noncombat_cross_fitted_empirical_successor_"
    "readiness.py"
)
SEED_INVENTORY_SOURCE_PATH = (
    "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_"
    "inventory.py"
)
CONTROL_PLANE_SOURCE_PATH = (
    "analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py"
)
TERMINAL_VERIFIER_SOURCE_PATH = (
    "analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_"
    "experiment.py"
)
BOUND_INPUT_PATHS = (
    ("readiness_auditor_source", AUDITOR_SOURCE_PATH),
    ("readiness_verifier_source", READINESS_VERIFIER_SOURCE_PATH),
    ("seed_inventory_source", SEED_INVENTORY_SOURCE_PATH),
    ("control_plane_source", CONTROL_PLANE_SOURCE_PATH),
    ("terminal_verifier_source", TERMINAL_VERIFIER_SOURCE_PATH),
    ("consumed_registration", CONSUMED_REGISTRATION_PATH),
    ("consumed_terminal", CONSUMED_TERMINAL_PATH),
    ("consumed_manifest", CONSUMED_MANIFEST_PATH),
    ("execution_bottleneck_audit", BOTTLENECK_AUDIT_PATH),
    ("control_plane_repair_closeout", CONTROL_PLANE_REPAIR_PATH),
    ("historical_throughput", HISTORICAL_THROUGHPUT_PATH),
    ("successor_contract", SUCCESSOR_CONTRACT_PATH),
    ("readiness_change_spec", READINESS_CHANGE_SPEC_PATH),
)
CONTROL_AUTHORITY_NAMES = (
    "communication_mod",
    "environment_construction",
    "evaluation",
    "execution",
    "formal_rl",
    "gameplay",
    "model_fitting",
    "model_loading",
    "native_loading",
    "policy_promotion",
    "qualification",
    "seed_access",
    "training",
)
LEASE_FILENAME = ".execution.lease"
ACCESS_JOURNAL_FILENAME = "access_journal.jsonl"
RESOURCE_LEDGER_FILENAME = "resource_ledger.jsonl"
BOOTSTRAP_FILENAME = "bootstrap.json"
REGISTRATION_FILENAME = "registration.json"
TERMINAL_INTENT_FILENAME = "terminal_intent.json"
TERMINAL_FILENAME = "terminal.json"
MANIFEST_FILENAME = "artifact_manifest.json"
LEASE_SCHEMA_VERSION = "noncombat-cross-fitted-hierarchical-learning-lease-v1"
ACCESS_JOURNAL_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-access-journal-v2"
)
RESOURCE_LEDGER_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-resource-ledger-v1"
)
BOOTSTRAP_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-bootstrap-v1"
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
CHILD_RESULT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-readiness-rehearsal-child-v1"
)

AUTHORITY_NAMES = (
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
EMPIRICAL_OPERATION_NAMES = (
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
)
FAILURE_GATE_ORDER = (
    "source_binding",
    "cohort_not_fresh",
    "rehearsal_boundary",
    "control_plane_scaling",
    "budget_binding",
    "artifact_binding",
)
REHEARSAL_STAGE_ORDER = ("context_setup", "control_chunk", "terminal_closeout")
BLOCKED_REHEARSAL_IMPORTS = (
    "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_runtime",
    "analysis_scripts.noncombat_simulator_adapter",
    "sts_lightspeed_noncombat_adapter",
    "torch",
)
SCHEDULE_SIZE = 512
CHUNK_SIZE = 64
CONSUMED_CANONICAL_SEARCH_START = 0
CONSUMED_INVENTORY_SHA256 = (
    "435cf41b1cff21178d6de253677544b0e96f8b8ec431c181981aef36591a7174"
)
CONSUMED_SELECTION_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1"
)
CONSUMED_REGISTRATION_SIZE_BYTES = 63_171_200
STAGE_CEILING_SECONDS = Decimal("300.000")
MAX_CANDIDATE_STORED_BYTES = 64 * 1024 * 1024
MAX_CANDIDATE_CANONICAL_BYTES = 512 * 1024 * 1024
MAX_IN_MEMORY_CANDIDATE_CANONICAL_BYTES = 16 * 1024 * 1024
MAX_REPORT_ARTIFACT_BYTES = 4 * 1024 * 1024
GZIP_ENCODING = "gzip-mtime-zero-v1"
_PROCESS_JOB_EVENT_ENV = "STS_READINESS_PROCESS_JOB_EVENT"

_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_AUDIT_ID_RE = re.compile(r"[a-z0-9][a-z0-9._:-]{7,191}")
_DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{3}")
_LIMITATIONS = (
    "This source-only result does not establish policy quality or causal effect.",
    "Candidate seed integers are data only and were not used to construct an environment.",
    "A go result permits only a separately reviewed empirical registration proposal.",
    "Native loading, seed access, fitting, training, evaluation, gameplay, qualification, and promotion remain unauthorized.",
)
_SUPPORTED_FORMATS = ("json", "jsonl", "json.gz", "jsonl.gz")
_ROW_ROLES = {
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
_COHORT_ROLES = {
    "canary": "canary",
    "diagnostic": "diagnostic",
    "fit": "training",
    "holdout": "holdout",
    "qualification": "qualification",
    "train": "training",
    "training": "training",
    "validation": "holdout",
}
_RESERVED_SEED_RANGES = [
    {
        "end_inclusive": 71663,
        "name": "previous_untouched_holdout",
        "start_inclusive": 71152,
    }
]


class VerificationError(RuntimeError):
    """Raised when readiness evidence is not independently reproducible."""


def _wait_for_windows_process_job_assignment() -> None:
    event_name = os.environ.pop(_PROCESS_JOB_EVENT_ENV, None)
    if event_name is None:
        return
    if os.name != "nt":
        raise VerificationError("Windows process job event reached another platform")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.OpenEventW.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    handle = kernel32.OpenEventW(0x00100000, False, event_name)
    if not handle:
        raise VerificationError(
            f"Windows process start event open failed: {ctypes.get_last_error()}"
        )
    try:
        if kernel32.WaitForSingleObject(handle, 30_000) != 0:
            raise VerificationError(
                "Windows process job assignment handshake timed out"
            )
    finally:
        kernel32.CloseHandle(handle)


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def canonical_digest(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _deterministic_gzip(payload: bytes) -> bytes:
    if not payload or len(payload) > MAX_CANDIDATE_CANONICAL_BYTES:
        raise VerificationError("candidate canonical payload exceeds limits")
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=0) as handle:
        handle.write(payload)
    stored = buffer.getvalue()
    if len(stored) > MAX_CANDIDATE_STORED_BYTES:
        raise VerificationError("candidate gzip payload exceeds stored limit")
    return stored


def _canonical_stream_digest(value: object) -> tuple[str, int]:
    encoder = json.JSONEncoder(
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256()
    size = 0
    for text in encoder.iterencode(value):
        payload = text.encode("utf-8")
        digest.update(payload)
        size += len(payload)
    digest.update(b"\n")
    return digest.hexdigest(), size + 1


def _write_expected_candidate_gzip(
    destination: Path, value: object
) -> dict[str, Any]:
    encoder = json.JSONEncoder(
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    canonical_hash = hashlib.sha256()
    canonical_size = 0
    try:
        with destination.open("xb") as raw:
            with gzip.GzipFile(
                fileobj=raw, mode="wb", filename="", mtime=0
            ) as compressed:
                for text in encoder.iterencode(value):
                    payload = text.encode("utf-8")
                    canonical_size += len(payload)
                    if canonical_size > MAX_CANDIDATE_CANONICAL_BYTES:
                        raise VerificationError(
                            "expected candidate canonical bytes exceed ceiling"
                        )
                    canonical_hash.update(payload)
                    compressed.write(payload)
                canonical_size += 1
                if canonical_size > MAX_CANDIDATE_CANONICAL_BYTES:
                    raise VerificationError(
                        "expected candidate canonical bytes exceed ceiling"
                    )
                canonical_hash.update(b"\n")
                compressed.write(b"\n")
            raw.flush()
            os.fsync(raw.fileno())
    except (OSError, TypeError, ValueError) as exc:
        raise VerificationError("expected candidate streaming gzip failed") from exc
    stored_size = destination.stat().st_size
    if stored_size <= 0 or stored_size > MAX_CANDIDATE_STORED_BYTES:
        raise VerificationError("expected candidate gzip exceeds ceiling")
    stored_hash = hashlib.sha256()
    with destination.open("rb") as handle:
        for payload in iter(lambda: handle.read(1024 * 1024), b""):
            stored_hash.update(payload)
    return {
        "canonical_sha256": canonical_hash.hexdigest(),
        "canonical_size_bytes": canonical_size,
        "encoding": GZIP_ENCODING,
        "path": CANDIDATE_INVENTORY_FILENAME,
        "sha256": stored_hash.hexdigest(),
        "size_bytes": stored_size,
    }


def _files_equal(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as left_handle, right.open("rb") as right_handle:
        while True:
            left_payload = left_handle.read(1024 * 1024)
            right_payload = right_handle.read(1024 * 1024)
            if left_payload != right_payload:
                return False
            if not left_payload:
                return True


def _bounded_gzip(stored: bytes) -> bytes:
    if not stored or len(stored) > MAX_CANDIDATE_STORED_BYTES:
        raise VerificationError("candidate gzip payload exceeds stored limit")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as handle:
            canonical = handle.read(MAX_IN_MEMORY_CANDIDATE_CANONICAL_BYTES + 1)
    except (EOFError, OSError, gzip.BadGzipFile) as exc:
        raise VerificationError("candidate gzip payload is invalid") from exc
    if len(canonical) > MAX_IN_MEMORY_CANDIDATE_CANONICAL_BYTES:
        raise VerificationError(
            "candidate requires the streamed publication verifier"
        )
    if _deterministic_gzip(canonical) != stored:
        raise VerificationError("candidate gzip payload is not deterministic")
    return canonical


def _authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def _control_authority() -> dict[str, bool]:
    return {name: False for name in CONTROL_AUTHORITY_NAMES}


def _empirical_operations() -> dict[str, bool]:
    return {name: False for name in EMPIRICAL_OPERATION_NAMES}


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise VerificationError(f"{label} must be a mapping")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise VerificationError(f"{label} fields mismatch")


def _commit(value: object, label: str = "source commit") -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise VerificationError(f"{label} is invalid")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise VerificationError(f"{label} is invalid")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise VerificationError(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: object, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise VerificationError(f"{label} must be positive")
    return result


def _canonical_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise VerificationError(f"{label} is invalid")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        raise VerificationError(f"{label} is invalid")
    return value


def _decimal(value: object, label: str) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_RE.fullmatch(value) is None:
        raise VerificationError(f"{label} is not a canonical decimal")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise VerificationError(f"{label} is invalid") from exc
    if not result.is_finite():
        raise VerificationError(f"{label} is not finite")
    return result


def _strict_json(payload: bytes, label: str) -> object:
    if not payload or not payload.endswith(b"\n"):
        raise VerificationError(f"{label} is not newline-terminated")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise VerificationError(f"{label} has duplicate key {key}")
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise VerificationError(f"{label} has non-finite value {value}")

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except VerificationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} is invalid JSON") from exc
    if canonical_json_bytes(value) != payload:
        raise VerificationError(f"{label} is not canonical JSON")
    return value


def _git_command(
    repo_root: Path, args: Sequence[str], *, input_bytes: bytes | None = None
) -> bytes:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            input=input_bytes,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(f"Git {' '.join(args)} failed") from exc
    return completed.stdout


def _artifact_format(path: str) -> str | None:
    for suffix in (".jsonl.gz", ".json.gz", ".jsonl", ".json"):
        if path.endswith(suffix):
            return suffix.removeprefix(".")
    return None


def _unsupported_seed_candidate(path: str) -> bool:
    folded = path.casefold()
    filename = PurePosixPath(folded).name
    near_structured = filename.endswith(
        (".json.zip", ".json.zst", ".json.bz2", ".json.xz")
    )
    return near_structured or "seed" in folded or "cohort" in folded


def _list_report_paths(repo_root: Path, commit: str) -> list[str]:
    raw = _git_command(
        repo_root,
        ("ls-tree", "-r", "--name-only", "-z", commit, "--", "reports"),
    )
    if raw and not raw.endswith(b"\0"):
        raise VerificationError("Git report path inventory is truncated")
    paths: list[str] = []
    for encoded in raw.split(b"\0"):
        if not encoded:
            continue
        try:
            path = encoded.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise VerificationError("Git report path is not UTF-8") from exc
        path = _canonical_path(path, "tracked report path")
        if not path.startswith("reports/"):
            raise VerificationError("tracked report path escapes reports")
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise VerificationError("Git report tree contains duplicate paths")
    return sorted(paths)


def _read_exact(stream: Any, size: int, label: str) -> bytes:
    remaining = size
    chunks: list[bytes] = []
    while remaining:
        payload = stream.read(remaining)
        if not payload:
            raise VerificationError(f"Git blob is truncated for {label}")
        chunks.append(payload)
        remaining -= len(payload)
    return b"".join(chunks)


def _iter_git_blobs(
    repo_root: Path, *, commit: str, paths: Sequence[str]
) -> Any:
    ordered = list(paths)
    if ordered != sorted(set(ordered)):
        raise VerificationError("Git blob paths are not sorted and unique")
    if not ordered:
        return
    try:
        process = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            cwd=repo_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )
    except OSError as exc:
        raise VerificationError("Git cat-file streaming process failed") from exc
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise VerificationError("Git cat-file streaming pipes are unavailable")
    try:
        for path in ordered:
            process.stdin.write(f"{commit}:{path}\n".encode("utf-8"))
            process.stdin.flush()
            header_payload = process.stdout.readline()
            if not header_payload.endswith(b"\n"):
                raise VerificationError(f"Git blob header is truncated for {path}")
            try:
                header = header_payload.decode(
                    "ascii", errors="strict"
                ).split()
            except UnicodeError as exc:
                raise VerificationError(
                    f"Git blob header is invalid for {path}"
                ) from exc
            if len(header) != 3 or header[1] != "blob" or not header[2].isdigit():
                raise VerificationError(f"Git object is not a blob for {path}")
            size = int(header[2])
            payload = _read_exact(process.stdout, size, path)
            if process.stdout.read(1) != b"\n":
                raise VerificationError(f"Git blob terminator is missing for {path}")
            yield path, payload
        process.stdin.close()
        return_code = process.wait(timeout=30)
        if return_code != 0:
            detail = process.stderr.read(2000).decode(
                "utf-8", errors="replace"
            ).strip()
            raise VerificationError(
                "Git cat-file streaming process failed"
                + (f": {detail}" if detail else "")
            )
    except BaseException:
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise VerificationError(
                "Git cat-file streaming process did not terminate"
            ) from exc
        raise
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            try:
                stream.close()
            except OSError:
                pass


def _parse_seed_json(payload: bytes, label: str) -> object:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise VerificationError(f"duplicate JSON key in {label}: {key}")
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise VerificationError(f"non-finite JSON value in {label}: {value}")

    try:
        return json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except VerificationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"seed source is invalid JSON: {label}") from exc


def _parse_seed_documents(
    path: str, payload: bytes, format_name: str
) -> list[object]:
    if not payload:
        raise VerificationError(f"seed source is empty: {path}")
    if format_name in {"json.gz", "jsonl.gz"}:
        try:
            payload = gzip.decompress(payload)
        except (EOFError, OSError, gzip.BadGzipFile) as exc:
            raise VerificationError(f"seed source gzip is invalid: {path}") from exc
        if not payload:
            raise VerificationError(f"seed source gzip is empty: {path}")
        format_name = format_name.removesuffix(".gz")
    if format_name == "json":
        return [_parse_seed_json(payload, path)]
    if format_name != "jsonl":
        raise VerificationError(f"unsupported seed source format: {path}")
    try:
        lines = payload.decode("utf-8", errors="strict").splitlines()
    except UnicodeError as exc:
        raise VerificationError(f"seed JSONL is not UTF-8: {path}") from exc
    if not lines:
        raise VerificationError(f"seed JSONL is empty: {path}")
    documents: list[object] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise VerificationError(
                f"seed JSONL has a blank line: {path}:{line_number}"
            )
        documents.append(_parse_seed_json(line.encode("utf-8"), path))
    return documents


def _json_pointer(parent: str, token: object) -> str:
    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}"


def _role_for_key(key: str, fallback: str) -> str:
    folded = key.casefold()
    for needle, role in (
        ("diagnostic", "diagnostic"),
        ("reserved", "reserved"),
        ("used", "used"),
        ("canary", "canary"),
        ("holdout", "holdout"),
        ("validation", "holdout"),
        ("qualification", "qualification"),
        ("train", "training"),
        ("fit", "training"),
        ("smoke", "smoke"),
        ("consumed", "consumed"),
        ("selected", "selected"),
    ):
        if needle in folded:
            return role
    return fallback


def _seed_scalar(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdigit():
        return int(value)
    return None


def _seed_rows(
    value: object, *, source_path: str, document_index: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def visit(
        node: object,
        pointer: str,
        *,
        seed_context: bool,
        role: str,
        cohorts_mapping: bool,
    ) -> None:
        if isinstance(node, Mapping):
            for key in sorted(node):
                if not isinstance(key, str):
                    raise VerificationError("JSON object key is not a string")
                folded = key.casefold()
                key_has_seed = "seed" in folded
                cohort_role = _COHORT_ROLES.get(folded) if cohorts_mapping else None
                child_context = seed_context or key_has_seed or cohort_role is not None
                child_role = role
                if key_has_seed:
                    child_role = _role_for_key(key, "seed")
                elif cohort_role is not None:
                    child_role = cohort_role
                visit(
                    node[key],
                    _json_pointer(pointer, key),
                    seed_context=child_context,
                    role=child_role,
                    cohorts_mapping=folded == "cohorts",
                )
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                visit(
                    child,
                    _json_pointer(pointer, index),
                    seed_context=seed_context,
                    role=role,
                    cohorts_mapping=False,
                )
            return
        seed = _seed_scalar(node) if seed_context else None
        if seed is not None:
            rows.append(
                {
                    "document_index": document_index,
                    "json_path": pointer,
                    "role": role,
                    "seed": seed,
                    "source_path": source_path,
                }
            )

    visit(value, "", seed_context=False, role="seed", cohorts_mapping=False)
    return rows


def _row_sort_key(row: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        row["seed"],
        row["source_path"],
        row["document_index"],
        row["json_path"],
        row["role"],
    )


def rebuild_seed_inventory(
    repo_root: Path | str, *, repository_commit: str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = _commit(repository_commit, "inventory commit")
    tracked_paths = _list_report_paths(root, commit)
    candidates: list[str] = []
    formats: dict[str, str] = {}
    for path in tracked_paths:
        format_name = _artifact_format(path)
        if format_name is None:
            if _unsupported_seed_candidate(path):
                raise VerificationError(
                    f"unsupported candidate seed artifact: {path}"
                )
            continue
        candidates.append(path)
        formats[path] = format_name
    rows: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for path, payload in _iter_git_blobs(
        root, commit=commit, paths=sorted(candidates)
    ):
        documents = _parse_seed_documents(path, payload, formats[path])
        source_rows: list[dict[str, Any]] = []
        for document_index, document in enumerate(documents):
            source_rows.extend(
                _seed_rows(
                    document,
                    source_path=path,
                    document_index=document_index,
                )
            )
        if not source_rows:
            continue
        rows.extend(source_rows)
        bindings.append(
            {
                "document_count": len(documents),
                "format": formats[path],
                "path": path,
                "row_count": len(source_rows),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    rows.sort(key=_row_sort_key)
    extracted = {row["seed"] for row in rows}
    reserved = set(range(71152, 71664))
    excluded = sorted(extracted | reserved)
    return {
        "canonical_search_start": 0,
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": commit,
        "reserved_seed_ranges": copy.deepcopy(_RESERVED_SEED_RANGES),
        "row_count": len(rows),
        "rows": rows,
        "schema_version": SEED_INVENTORY_SCHEMA_VERSION,
        "source_bindings": bindings,
        "source_count": len(bindings),
    }


def _git_blob(repo_root: Path, commit: str, path: str) -> bytes:
    return _git_command(repo_root, ("show", f"{commit}:{path}"))


def _synthetic_identity(
    registration: Mapping[str, Any], source_commit: str
) -> dict[str, str]:
    return {
        "authorization_sha256": hashlib.sha256(
            f"readiness-synthetic-authorization:{source_commit}".encode("ascii")
        ).hexdigest(),
        "logical_execution_id": registration["registration_id"],
        "registration_sha256": canonical_digest(registration),
        "request_sha256": hashlib.sha256(
            f"readiness-synthetic-request:{source_commit}".encode("ascii")
        ).hexdigest(),
    }


def _canonical_file(path: Path, label: str, *, limit: int) -> dict[str, Any]:
    try:
        if not path.is_file() or path.stat().st_size > limit:
            raise VerificationError(f"{label} is missing or oversized")
        payload = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"cannot read {label}") from exc
    value = _strict_json(payload, label)
    return _mapping(value, label)


def _canonical_json_lines(path: Path, label: str, *, limit: int) -> list[dict[str, Any]]:
    try:
        if not path.is_file() or path.stat().st_size > limit:
            raise VerificationError(f"{label} is missing or oversized")
        payload = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"cannot read {label}") from exc
    if not payload or not payload.endswith(b"\n"):
        raise VerificationError(f"{label} is incomplete")
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(payload.splitlines(keepends=True), start=1):
        value = _strict_json(line, f"{label} line {line_number}")
        rows.append(_mapping(value, f"{label} line {line_number}"))
    return rows


def _verify_context_validation_count(value: object) -> dict[str, Any]:
    observed = _mapping(value, "complete registration validation counts")
    expected = {"after_chunk": 1, "after_closeout": 1, "after_setup": 1}
    if observed != expected:
        raise VerificationError(
            "no_go_control_plane_scaling: complete registration validation "
            "count grew"
        )
    return observed


def _zero_resources() -> dict[str, int | float]:
    return {
        "charged_seconds": 0.0,
        "environment_accesses": 0,
        "optimizer_updates": 0,
        "retained_decisions": 0,
        "stored_bytes": 0,
        "uncompressed_bytes": 0,
    }


def _resource_limits(registration: Mapping[str, Any]) -> dict[str, int | float]:
    limits = registration["contract"]["limits"]
    return {
        "charged_seconds": limits["max_charged_seconds"],
        "environment_accesses": limits["max_environment_accesses"],
        "optimizer_updates": limits["max_optimizer_updates"],
        "retained_decisions": limits["max_retained_decisions"],
        "stored_bytes": limits["max_stored_bytes"],
        "uncompressed_bytes": limits["max_uncompressed_bytes"],
    }


def _verify_journal(
    path: Path, *, registration: Mapping[str, Any], identity: Mapping[str, Any]
) -> bytes:
    rows = _canonical_json_lines(path, "synthetic access journal", limit=4 * 1024 * 1024)
    if len(rows) != 1 + (2 * CHUNK_SIZE):
        raise VerificationError("synthetic access journal row count mismatch")
    expected_header = {
        "event_index": 0,
        "identity": identity,
        "kind": "journal_opened",
        "registration_sha256": canonical_digest(registration),
        "schedule_sha256": registration["schedule"]["seeds_sha256"],
        "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
    }
    if rows[0] != expected_header:
        raise VerificationError("synthetic access journal header mismatch")
    for index, seed in enumerate(registration["schedule"]["chunks"][0], start=1):
        coordinate = {
            "access_ordinal": index,
            "attempt_ordinal": 0,
            "chunk_index": 0,
            "seed": seed,
        }
        debit = {
            **coordinate,
            "event_index": (2 * index) - 1,
            "kind": "access_debited",
            "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
            "status": "debited",
        }
        terminal = {
            **coordinate,
            "event_index": 2 * index,
            "kind": "access_terminal",
            "schema_version": ACCESS_JOURNAL_SCHEMA_VERSION,
            "status": "completed",
        }
        if rows[(2 * index) - 1] != debit or rows[2 * index] != terminal:
            raise VerificationError("synthetic access journal coordinate mismatch")
    return path.read_bytes()


def _verify_resource_ledger(
    path: Path, *, registration: Mapping[str, Any], identity: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, int | float]]:
    rows = _canonical_json_lines(path, "synthetic resource ledger", limit=4 * 1024 * 1024)
    if len(rows) != CHUNK_SIZE + 2:
        raise VerificationError("synthetic resource ledger revision count mismatch")
    header = {
        "identity": identity,
        "kind": "resource_ledger_opened",
        "limits": _resource_limits(registration),
        "resources": _zero_resources(),
        "revision": 0,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }
    if rows[0] != header:
        raise VerificationError("synthetic resource ledger header mismatch")
    previous = header
    for revision in range(1, CHUNK_SIZE + 1):
        resources = _zero_resources()
        resources["environment_accesses"] = revision
        expected = {
            "kind": "resource_prefix_advanced",
            "previous_event_sha256": canonical_digest(previous),
            "reason": "access-journal-reconcile",
            "resources": resources,
            "revision": revision,
            "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
        }
        if rows[revision] != expected:
            raise VerificationError("synthetic resource ledger access revision mismatch")
        previous = expected
    terminal_resources = _zero_resources()
    terminal_resources["environment_accesses"] = CHUNK_SIZE
    final = {
        "kind": "resource_prefix_advanced",
        "previous_event_sha256": canonical_digest(previous),
        "reason": "terminal-attempt-charge",
        "resources": terminal_resources,
        "revision": CHUNK_SIZE + 1,
        "schema_version": RESOURCE_LEDGER_SCHEMA_VERSION,
    }
    if rows[-1] != final:
        raise VerificationError("synthetic terminal attempt charge mismatch")
    return rows, terminal_resources


def _verify_bootstrap(
    value: Mapping[str, Any], *, registration: Mapping[str, Any], identity: Mapping[str, Any]
) -> None:
    bootstrap = _mapping(value, "synthetic bootstrap")
    _exact_keys(
        bootstrap,
        {
            "authority",
            "bootstrap_sha256",
            "identity",
            "registration_sha256",
            "resource_use",
            "runtime_checkpoint",
            "schema_version",
        },
        "synthetic bootstrap",
    )
    checkpoint = _mapping(bootstrap["runtime_checkpoint"], "synthetic checkpoint")
    _exact_keys(checkpoint, {"payload", "sha256", "size_bytes"}, "synthetic checkpoint")
    checkpoint_payload = canonical_json_bytes(checkpoint["payload"])
    expected_checkpoint = {
        "payload": {
            "coordinates": {
                "completed_decisions": 0,
                "completed_episodes": 0,
                "next_chunk_index": 0,
                "optimizer_updates": 0,
            },
            "kind": "source-only-synthetic-control-bootstrap",
        },
        "sha256": hashlib.sha256(checkpoint_payload).hexdigest(),
        "size_bytes": len(checkpoint_payload),
    }
    if checkpoint != expected_checkpoint:
        raise VerificationError("synthetic bootstrap checkpoint binding mismatch")
    body = {
        key: item for key, item in bootstrap.items() if key != "bootstrap_sha256"
    }
    if (
        bootstrap["schema_version"] != BOOTSTRAP_SCHEMA_VERSION
        or bootstrap["authority"] != _control_authority()
        or bootstrap["identity"] != identity
        or bootstrap["registration_sha256"] != canonical_digest(registration)
        or bootstrap["resource_use"] != _zero_resources()
        or bootstrap["bootstrap_sha256"] != canonical_digest(body)
    ):
        raise VerificationError("synthetic bootstrap identity mismatch")


def _artifact_inventory(output: Path, *, excluded: set[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(
        (candidate for candidate in output.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(output).as_posix(),
    ):
        relative = path.relative_to(output).as_posix()
        if relative == LEASE_FILENAME or relative in excluded:
            continue
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        rows.append(
            {
                "encoding": "identity-bytes-v1",
                "path": relative,
                "stored_sha256": digest,
                "stored_size_bytes": len(payload),
                "uncompressed_sha256": digest,
                "uncompressed_size_bytes": len(payload),
            }
        )
    return {
        "artifacts": rows,
        "stored_size_bytes": sum(row["stored_size_bytes"] for row in rows),
        "uncompressed_size_bytes": sum(
            row["uncompressed_size_bytes"] for row in rows
        ),
    }


def _named_tree_binding(root: Path, *, excluded: set[str]) -> dict[str, Any]:
    rows: list[tuple[str, bytes]] = []
    for path in sorted(
        (candidate for candidate in root.rglob("*") if candidate.is_file()),
        key=lambda candidate: candidate.relative_to(root).as_posix(),
    ):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        rows.append((relative, path.read_bytes()))
    digest = hashlib.sha256()
    for name, payload in rows:
        encoded = name.encode("utf-8")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return {
        "file_count": len(rows),
        "sha256": digest.hexdigest(),
        "size_bytes": sum(len(payload) for _, payload in rows),
    }


def verify_rehearsal_scratch(
    scratch_root: Path | str,
    *,
    repo_root: Path | str,
    source_commit: str,
    expected_child_pid: int,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    scratch = Path(scratch_root).resolve()
    commit = _commit(source_commit)
    child_pid = _positive_int(expected_child_pid, "expected child process id")
    if not scratch.is_dir():
        raise VerificationError("rehearsal scratch root is missing")
    if {path.name for path in scratch.iterdir()} != {"child_result.json", "control"}:
        raise VerificationError("rehearsal scratch root closure mismatch")
    output = scratch / "control"
    expected_files = {
        ACCESS_JOURNAL_FILENAME,
        BOOTSTRAP_FILENAME,
        LEASE_FILENAME,
        MANIFEST_FILENAME,
        REGISTRATION_FILENAME,
        RESOURCE_LEDGER_FILENAME,
        TERMINAL_FILENAME,
        TERMINAL_INTENT_FILENAME,
    }
    observed_files = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
    }
    observed_directories = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_dir()
    }
    if observed_files != expected_files or observed_directories:
        raise VerificationError("synthetic control output closure mismatch")

    consumed_payload = _git_blob(root, commit, CONSUMED_REGISTRATION_PATH)
    if len(consumed_payload) != CONSUMED_REGISTRATION_SIZE_BYTES:
        raise VerificationError("actual-scale registration byte size drifted")
    consumed = _mapping(_strict_json(consumed_payload, "consumed registration"), "consumed registration")
    expected_registration = copy.deepcopy(consumed)
    expected_registration["registration_id"] = (
        "source-only-readiness-rehearsal-" + commit[:12]
    )
    expected_registration["output_root"] = output.as_posix()
    registration = _canonical_file(
        output / REGISTRATION_FILENAME,
        "synthetic registration",
        limit=64 * 1024 * 1024,
    )
    if registration != expected_registration:
        raise VerificationError("synthetic registration derivation mismatch")
    identity = _synthetic_identity(registration, commit)
    lease = _canonical_file(
        output / LEASE_FILENAME, "synthetic execution lease", limit=64 * 1024
    )
    owner = _mapping(lease.get("owner"), "synthetic lease owner")
    if (
        lease.get("schema_version") != LEASE_SCHEMA_VERSION
        or lease.get("identity") != identity
        or lease.get("reclaimed_owner") is not None
        or owner.get("process_id") != child_pid
        or not isinstance(owner.get("acquired_at_ns"), int)
        or not isinstance(owner.get("token"), str)
        or re.fullmatch(r"[0-9a-f]{32}", owner["token"]) is None
    ):
        raise VerificationError("synthetic lease identity mismatch")

    journal_payload = _verify_journal(
        output / ACCESS_JOURNAL_FILENAME,
        registration=registration,
        identity=identity,
    )
    ledger_rows, resources = _verify_resource_ledger(
        output / RESOURCE_LEDGER_FILENAME,
        registration=registration,
        identity=identity,
    )
    _verify_bootstrap(
        _canonical_file(
            output / BOOTSTRAP_FILENAME,
            "synthetic bootstrap",
            limit=4 * 1024 * 1024,
        ),
        registration=registration,
        identity=identity,
    )

    intent = _canonical_file(
        output / TERMINAL_INTENT_FILENAME,
        "synthetic terminal intent",
        limit=4 * 1024 * 1024,
    )
    intent_body = {
        key: item for key, item in intent.items() if key != "terminal_intent_sha256"
    }
    expected_details = {
        "reason": "source_only_synthetic_control_rehearsal_complete",
        "source_only": True,
        "synthetic_control_positions": CHUNK_SIZE,
    }
    if (
        intent.get("schema_version") != TERMINAL_INTENT_SCHEMA_VERSION
        or intent.get("authority") != _control_authority()
        or intent.get("identity") != identity
        or intent.get("registration_sha256") != canonical_digest(registration)
        or intent.get("verdict") != "experiment_failed_after_seed_access"
        or intent.get("details") != expected_details
        or intent.get("checkpoint_sha256s") != []
        or intent.get("resource_revision") != len(ledger_rows) - 1
        or intent.get("resource_use") != resources
        or intent.get("journal_prefix")
        != {
            "sha256": hashlib.sha256(journal_payload).hexdigest(),
            "size_bytes": len(journal_payload),
        }
        or intent.get("artifact_prefix_inventory")
        != _artifact_inventory(
            output,
            excluded={MANIFEST_FILENAME, TERMINAL_FILENAME, TERMINAL_INTENT_FILENAME},
        )
        or intent.get("terminal_intent_sha256") != canonical_digest(intent_body)
    ):
        raise VerificationError("synthetic terminal intent mismatch")

    terminal = _canonical_file(
        output / TERMINAL_FILENAME,
        "synthetic terminal",
        limit=4 * 1024 * 1024,
    )
    terminal_body = {
        key: item for key, item in terminal.items() if key != "terminal_sha256"
    }
    if (
        terminal.get("schema_version") != TERMINAL_SCHEMA_VERSION
        or terminal.get("authority") != _control_authority()
        or terminal.get("identity") != identity
        or terminal.get("registration_sha256") != canonical_digest(registration)
        or terminal.get("terminal_intent_sha256")
        != intent["terminal_intent_sha256"]
        or terminal.get("verdict") != "experiment_failed_after_seed_access"
        or terminal.get("details") != expected_details
        or terminal.get("checkpoint_count") != 0
        or terminal.get("completed_chunk_indices") != [0]
        or terminal.get("resume_used") is not False
        or terminal.get("resource_use") != resources
        or terminal.get("terminal_sha256") != canonical_digest(terminal_body)
    ):
        raise VerificationError("synthetic terminal mismatch")

    manifest = _canonical_file(
        output / MANIFEST_FILENAME,
        "synthetic artifact manifest",
        limit=4 * 1024 * 1024,
    )
    manifest_body = {
        key: item for key, item in manifest.items() if key != "manifest_sha256"
    }
    if (
        manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION
        or manifest.get("authority") != _control_authority()
        or manifest.get("identity") != identity
        or manifest.get("registration_sha256") != canonical_digest(registration)
        or manifest.get("terminal_sha256") != terminal["terminal_sha256"]
        or manifest.get("artifact_inventory")
        != _artifact_inventory(output, excluded={MANIFEST_FILENAME})
        or manifest.get("manifest_sha256") != canonical_digest(manifest_body)
    ):
        raise VerificationError("synthetic manifest mismatch")

    child = _canonical_file(
        scratch / "child_result.json",
        "rehearsal child result",
        limit=4 * 1024 * 1024,
    )
    expected_child_fields = {
        "blocked_imports",
        "context_validation_count",
        "empirical_operations",
        "producer_verified",
        "registration_size_bytes",
        "schema_version",
        "scratch_artifacts",
        "stage_results",
        "synthetic_control_positions",
        "terminal_verdict",
    }
    if set(child) != expected_child_fields:
        raise VerificationError("rehearsal child result fields mismatch")
    context_validation_count = _verify_context_validation_count(
        child["context_validation_count"]
    )
    if (
        child["schema_version"] != CHILD_RESULT_SCHEMA_VERSION
        or child["producer_verified"] is not True
        or child["blocked_imports"] != list(BLOCKED_REHEARSAL_IMPORTS)
        or child["empirical_operations"] != _empirical_operations()
        or child["registration_size_bytes"] != len(consumed_payload)
        or child["scratch_artifacts"]
        != _named_tree_binding(output, excluded={LEASE_FILENAME})
        or child["synthetic_control_positions"] != CHUNK_SIZE
        or child["terminal_verdict"] != "experiment_failed_after_seed_access"
    ):
        raise VerificationError("rehearsal child witness mismatch")
    stages = child["stage_results"]
    if not isinstance(stages, list) or len(stages) != 3:
        raise VerificationError("rehearsal child stage inventory mismatch")
    for expected_name, raw in zip(REHEARSAL_STAGE_ORDER, stages, strict=True):
        stage = _mapping(raw, "rehearsal child stage")
        if (
            set(stage) != {"ceiling_seconds", "elapsed_seconds", "name", "status"}
            or stage["name"] != expected_name
            or stage["status"] != "passed"
            or _decimal(stage["ceiling_seconds"], "stage ceiling")
            != STAGE_CEILING_SECONDS
            or _decimal(stage["elapsed_seconds"], "stage elapsed")
            > STAGE_CEILING_SECONDS
        ):
            raise VerificationError("rehearsal child stage boundary mismatch")
    return {
        "blocked_imports": child["blocked_imports"],
        "child_exit_code": 0,
        "context_validation_count": context_validation_count,
        "empirical_operations": child["empirical_operations"],
        "registration_size_bytes": child["registration_size_bytes"],
        "scratch_artifacts": child["scratch_artifacts"],
        "stage_results": child["stage_results"],
        "status": "passed",
        "synthetic_control_positions": child["synthetic_control_positions"],
        "terminal_verdict": child["terminal_verdict"],
        "verified": True,
    }


def _canonical_candidates(inventory: Mapping[str, Any]) -> list[int]:
    start = _nonnegative_int(
        inventory.get("canonical_search_start"), "canonical search start"
    )
    raw_excluded = inventory.get("excluded_seeds")
    if not isinstance(raw_excluded, list):
        raise VerificationError("historical inventory excluded seeds are invalid")
    excluded = [_nonnegative_int(seed, "excluded seed") for seed in raw_excluded]
    if excluded != sorted(set(excluded)):
        raise VerificationError("historical inventory excluded seeds are not canonical")
    if inventory.get("excluded_seed_count") != len(excluded):
        raise VerificationError("historical inventory excluded count mismatch")
    result: list[int] = []
    candidate = start
    excluded_set = set(excluded)
    while len(result) < SCHEDULE_SIZE:
        if candidate not in excluded_set:
            result.append(candidate)
        candidate += 1
    return result


def _build_expected_candidate(
    inventory_value: Mapping[str, Any],
    *,
    source_commit: str,
    consumed_cohort: Mapping[str, Any],
) -> dict[str, Any]:
    commit = _commit(source_commit)
    inventory = _mapping(inventory_value, "independently rebuilt inventory")
    if (
        inventory.get("schema_version") != SEED_INVENTORY_SCHEMA_VERSION
        or inventory.get("repository_commit") != commit
    ):
        raise VerificationError("independently rebuilt inventory identity mismatch")
    inventory_sha256, _inventory_size = _canonical_stream_digest(inventory)
    seeds = _canonical_candidates(inventory)
    schedule = {
        "canonical_search_start": inventory["canonical_search_start"],
        "inventory_sha256": inventory_sha256,
        "schema_version": FRESH_SCHEDULE_SCHEMA_VERSION,
        "seed_count": SCHEDULE_SIZE,
        "seeds": seeds,
    }
    consumed = _mapping(consumed_cohort, "independently rebuilt consumed cohort")
    consumed_seeds = consumed.get("seeds")
    if not isinstance(consumed_seeds, list):
        raise VerificationError("independently rebuilt consumed seeds are invalid")
    collisions = sorted(set(seeds) & set(consumed_seeds))
    return {
        "authority": _authority(),
        "candidate_schedule": schedule,
        "consumed_cohort": consumed,
        "disjointness": {
            "collision_count": len(collisions),
            "collisions": collisions,
            "status": "passed" if not collisions else "failed",
        },
        "historical_seed_inventory": inventory,
        "schema_version": CANDIDATE_SCHEMA_VERSION,
        "source_commit": commit,
    }


def _verify_candidate(
    value: object,
    independently_rebuilt_inventory: Mapping[str, Any] | None = None,
    *,
    independently_rebuilt_inventory_sha256: str | None = None,
    expected_consumed_cohort: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidate = _mapping(value, "candidate artifact")
    _exact_keys(
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
        "candidate artifact",
    )
    if candidate["schema_version"] != CANDIDATE_SCHEMA_VERSION:
        raise VerificationError("candidate schema mismatch")
    commit = _commit(candidate["source_commit"])
    if candidate["authority"] != _authority():
        raise VerificationError("candidate authority is not all false")
    inventory = _mapping(
        candidate["historical_seed_inventory"], "historical seed inventory"
    )
    if inventory.get("schema_version") != SEED_INVENTORY_SCHEMA_VERSION:
        raise VerificationError("historical inventory schema mismatch")
    if inventory.get("repository_commit") != commit:
        raise VerificationError("historical inventory commit mismatch")
    inventory_sha256 = canonical_digest(inventory)
    if independently_rebuilt_inventory is not None:
        rebuilt = _mapping(
            independently_rebuilt_inventory, "independently rebuilt inventory"
        )
        if inventory != rebuilt:
            raise VerificationError(
                "historical inventory independent rebuild mismatch"
            )
        rebuilt_sha256 = canonical_digest(rebuilt)
        if independently_rebuilt_inventory_sha256 is not None and (
            independently_rebuilt_inventory_sha256 != rebuilt_sha256
        ):
            raise VerificationError("independent inventory digest input mismatch")
    elif independently_rebuilt_inventory_sha256 is not None:
        rebuilt_sha256 = _digest(
            independently_rebuilt_inventory_sha256,
            "independently rebuilt inventory digest",
        )
    else:
        raise VerificationError("independent historical inventory is required")
    if inventory_sha256 != rebuilt_sha256:
        raise VerificationError("historical inventory independent digest mismatch")
    expected_candidates = _canonical_candidates(inventory)
    schedule = _mapping(candidate["candidate_schedule"], "candidate schedule")
    _exact_keys(
        schedule,
        {
            "canonical_search_start",
            "inventory_sha256",
            "schema_version",
            "seed_count",
            "seeds",
        },
        "candidate schedule",
    )
    if (
        schedule["canonical_search_start"] != inventory["canonical_search_start"]
        or schedule["inventory_sha256"] != inventory_sha256
        or schedule["schema_version"] != FRESH_SCHEDULE_SCHEMA_VERSION
        or schedule["seed_count"] != SCHEDULE_SIZE
        or schedule["seeds"] != expected_candidates
    ):
        raise VerificationError("candidate schedule is not the fixed selection")
    consumed = _mapping(candidate["consumed_cohort"], "consumed cohort")
    _exact_keys(
        consumed,
        {
            "registration_binding",
            "registration_id",
            "seed_count",
            "seeds",
            "seeds_sha256",
        },
        "consumed cohort",
    )
    raw_consumed = consumed["seeds"]
    if not isinstance(raw_consumed, list):
        raise VerificationError("consumed cohort seeds are invalid")
    consumed_seeds = [
        _nonnegative_int(seed, "consumed cohort seed") for seed in raw_consumed
    ]
    if (
        consumed["seed_count"] != SCHEDULE_SIZE
        or len(consumed_seeds) != SCHEDULE_SIZE
        or consumed_seeds != sorted(set(consumed_seeds))
        or consumed["seeds_sha256"] != canonical_digest(consumed_seeds)
    ):
        raise VerificationError("consumed cohort identity mismatch")
    if not isinstance(consumed["registration_id"], str) or not consumed[
        "registration_id"
    ]:
        raise VerificationError("consumed cohort registration identity is invalid")
    binding = _mapping(consumed["registration_binding"], "consumed binding")
    _exact_keys(binding, {"path", "sha256", "size_bytes"}, "consumed binding")
    if binding["path"] != CONSUMED_REGISTRATION_PATH:
        raise VerificationError("consumed cohort binding path mismatch")
    _digest(binding["sha256"], "consumed binding digest")
    _positive_int(binding["size_bytes"], "consumed binding size")
    normalized_consumed = {
        **consumed,
        "registration_binding": binding,
        "seeds": consumed_seeds,
    }
    if expected_consumed_cohort is not None and normalized_consumed != _mapping(
        expected_consumed_cohort, "independently reconstructed consumed cohort"
    ):
        raise VerificationError("consumed cohort differs from bound registration")
    collisions = sorted(set(expected_candidates) & set(consumed_seeds))
    disjointness = _mapping(candidate["disjointness"], "cohort disjointness")
    expected_disjointness = {
        "collision_count": len(collisions),
        "collisions": collisions,
        "status": "passed" if not collisions else "failed",
    }
    if disjointness != expected_disjointness:
        raise VerificationError("cohort collision evidence mismatch")
    candidate["historical_seed_inventory"] = inventory
    candidate["candidate_schedule"] = schedule
    candidate["consumed_cohort"] = normalized_consumed
    candidate["disjointness"] = disjointness
    return candidate


def _verify_source_binding(value: object) -> dict[str, Any]:
    binding = _mapping(value, "source binding")
    _exact_keys(
        binding,
        {
            "bindings",
            "bindings_sha256",
            "head_commit",
            "origin_master_commit",
            "source_commit",
            "status",
            "tracked_clean",
        },
        "source binding",
    )
    commit = _commit(binding["source_commit"])
    if (
        binding["head_commit"] != commit
        or binding["origin_master_commit"] != commit
        or binding["status"] != "passed"
        or binding["tracked_clean"] is not True
    ):
        raise VerificationError("source binding is not pushed and clean")
    rows = binding["bindings"]
    if not isinstance(rows, list) or not rows:
        raise VerificationError("source binding rows are invalid")
    normalized: list[dict[str, Any]] = []
    roles: set[str] = set()
    paths: set[str] = set()
    for raw in rows:
        row = _mapping(raw, "source binding row")
        _exact_keys(row, {"path", "role", "sha256", "size_bytes"}, "source row")
        row["path"] = _canonical_path(row["path"], "source path")
        if not isinstance(row["role"], str) or not row["role"]:
            raise VerificationError("source role is invalid")
        row["sha256"] = _digest(row["sha256"], "source digest")
        row["size_bytes"] = _positive_int(row["size_bytes"], "source size")
        if row["role"] in roles or row["path"] in paths:
            raise VerificationError("source roles or paths are duplicated")
        roles.add(row["role"])
        paths.add(row["path"])
        normalized.append(row)
    if binding["bindings_sha256"] != canonical_digest(normalized):
        raise VerificationError("source binding digest mismatch")
    binding["bindings"] = normalized
    return binding


def _json_object(
    payload: bytes,
    label: str,
    *,
    exact_decimals: bool = False,
) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise VerificationError(f"{label} has duplicate key {key}")
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise VerificationError(f"{label} has non-finite value {value}")

    try:
        options: dict[str, Any] = {
            "object_pairs_hook": reject_duplicates,
            "parse_constant": reject_constant,
        }
        if exact_decimals:
            options["parse_float"] = Decimal
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            **options,
        )
    except VerificationError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"{label} is invalid JSON") from exc
    return _mapping(value, label)


def _exact_historical_charge(value: object) -> Decimal:
    if not isinstance(value, Decimal):
        raise VerificationError(
            "historical charged seconds must remain a JSON number"
        )
    if not value.is_finite() or value != Decimal("2165.4520000000193"):
        raise VerificationError("historical charged seconds drifted")
    return value


def _verify_live_source_binding(
    repo_root: Path, value: object
) -> dict[str, Any]:
    source = _verify_source_binding(value)
    commit = source["source_commit"]
    expected_roles_and_paths = list(BOUND_INPUT_PATHS)
    observed_roles_and_paths = [
        (row["role"], row["path"]) for row in source["bindings"]
    ]
    if observed_roles_and_paths != expected_roles_and_paths:
        raise VerificationError("source binding input inventory mismatch")
    try:
        head = _git_command(repo_root, ("rev-parse", "HEAD")).decode(
            "ascii", errors="strict"
        ).strip()
        origin = _git_command(repo_root, ("rev-parse", "origin/master")).decode(
            "ascii", errors="strict"
        ).strip()
        tracked_status = _git_command(
            repo_root,
            ("status", "--porcelain", "--untracked-files=no"),
        )
    except UnicodeError as exc:
        raise VerificationError("Git source identity is not ASCII") from exc
    if head != commit or origin != commit or tracked_status:
        raise VerificationError("live source is not the pushed clean identity")

    for row in source["bindings"]:
        path = row["path"]
        blob = _git_blob(repo_root, commit, path)
        try:
            worktree = (repo_root / PurePosixPath(path)).read_bytes()
        except OSError as exc:
            raise VerificationError(f"cannot read bound worktree path {path}") from exc
        expected = {
            "path": path,
            "role": row["role"],
            "sha256": hashlib.sha256(blob).hexdigest(),
            "size_bytes": len(blob),
        }
        if row != expected or worktree != blob:
            raise VerificationError(f"bound source bytes drifted: {path}")
    return source


def _verify_consumed_schedule(value: object) -> list[int]:
    schedule = _mapping(value, "consumed schedule")
    _exact_keys(
        schedule,
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
        "consumed schedule",
    )
    if (
        _nonnegative_int(
            schedule["canonical_search_start"],
            "consumed schedule canonical search start",
        )
        != CONSUMED_CANONICAL_SEARCH_START
        or _digest(
            schedule["inventory_sha256"], "consumed schedule inventory digest"
        )
        != CONSUMED_INVENTORY_SHA256
        or schedule["selection_schema_version"]
        != CONSUMED_SELECTION_SCHEMA_VERSION
    ):
        raise VerificationError("consumed schedule provenance mismatch")
    raw_seeds = schedule.get("seeds")
    chunks = schedule.get("chunks")
    if (
        not isinstance(raw_seeds, list)
        or not isinstance(chunks, list)
        or len(chunks) != 8
        or any(
            not isinstance(chunk, list) or len(chunk) != CHUNK_SIZE
            for chunk in chunks
        )
    ):
        raise VerificationError("consumed registration schedule is invalid")
    seeds = [_nonnegative_int(seed, "consumed seed") for seed in raw_seeds]
    normalized_chunks = [
        [_nonnegative_int(seed, "consumed chunk seed") for seed in chunk]
        for chunk in chunks
    ]
    flattened = [seed for chunk in normalized_chunks for seed in chunk]
    if (
        len(seeds) != SCHEDULE_SIZE
        or seeds != sorted(set(seeds))
        or schedule.get("chunk_count") != 8
        or schedule.get("episodes_per_chunk") != CHUNK_SIZE
        or flattened != seeds
        or schedule.get("seeds_sha256") != canonical_digest(seeds)
    ):
        raise VerificationError("consumed registration schedule drifted")
    return seeds


def _verify_bound_evidence(
    repo_root: Path, source: Mapping[str, Any]
) -> dict[str, Any]:
    commit = _commit(source.get("source_commit"), "bound evidence commit")
    bindings = {
        row["path"]: row
        for row in source.get("bindings", [])
        if isinstance(row, Mapping) and isinstance(row.get("path"), str)
    }

    def bound_payload(path: str) -> bytes:
        binding = bindings.get(path)
        if binding is None:
            raise VerificationError(f"bound evidence path is missing: {path}")
        payload = _git_blob(repo_root, commit, path)
        if (
            hashlib.sha256(payload).hexdigest() != binding.get("sha256")
            or len(payload) != binding.get("size_bytes")
        ):
            raise VerificationError(f"bound evidence bytes drifted: {path}")
        return payload

    registration_payload = bound_payload(CONSUMED_REGISTRATION_PATH)
    registration = _json_object(registration_payload, "consumed registration")
    schedule = _mapping(registration.get("schedule"), "consumed schedule")
    seeds = _verify_consumed_schedule(schedule)
    if (
        len(registration_payload) != CONSUMED_REGISTRATION_SIZE_BYTES
        or registration.get("registration_id")
        != "noncombat-cross-fitted-hierarchical-learning-successor-20260806-r1"
    ):
        raise VerificationError("consumed registration identity drifted")
    registration_id = registration["registration_id"]
    del registration_payload, registration, schedule

    terminal = _json_object(
        bound_payload(CONSUMED_TERMINAL_PATH), "consumed terminal"
    )
    resources = _mapping(terminal.get("resource_use"), "consumed resources")
    if (
        terminal.get("verdict") != "experiment_failed_after_seed_access"
        or terminal.get("checkpoint_count") != 0
        or resources.get("environment_accesses") != 12
    ):
        raise VerificationError("consumed terminal evidence drifted")
    manifest = _json_object(
        bound_payload(CONSUMED_MANIFEST_PATH), "consumed manifest"
    )
    if manifest.get("terminal_sha256") != terminal.get("terminal_sha256"):
        raise VerificationError("consumed terminal manifest drifted")
    del manifest, terminal, resources

    bottleneck = _json_object(
        bound_payload(BOTTLENECK_AUDIT_PATH), "execution bottleneck audit"
    )
    findings = bottleneck.get("findings")
    if not isinstance(findings, list):
        raise VerificationError("execution bottleneck findings are invalid")
    finding_ids = {
        row.get("finding_id") for row in findings if isinstance(row, Mapping)
    }
    required_findings = {
        "repeated_full_registration_validation_dominates_each_access",
        "noninfrastructure_terminal_failure_does_not_persist_elapsed_charge",
        "producer_terminal_publication_has_large_revalidation_tail",
        "outer_wait_timeout_did_not_represent_child_exit",
    }
    if not required_findings.issubset(finding_ids):
        raise VerificationError("execution bottleneck evidence drifted")
    del bottleneck, findings, finding_ids

    repair = _json_object(
        bound_payload(CONTROL_PLANE_REPAIR_PATH), "control-plane repair closeout"
    )
    scope = _mapping(repair.get("scope"), "control-plane repair scope")
    structural = _mapping(
        repair.get("structural_evidence"), "control-plane structural evidence"
    )
    validations = _mapping(
        structural.get("complete_registration_validations"),
        "control-plane validation counts",
    )
    if (
        repair.get("verdict")
        != "source_only_control_plane_repaired_no_empirical_authority"
        or scope.get("source_only") is not True
        or validations
        != {
            "after_64_accesses": 1,
            "after_same_process_terminal_closeout": 1,
            "context_creation": 1,
        }
    ):
        raise VerificationError("control-plane repair evidence drifted")
    del repair, scope, structural, validations

    historical = _json_object(
        bound_payload(HISTORICAL_THROUGHPUT_PATH),
        "historical throughput",
        exact_decimals=True,
    )
    execution = _mapping(historical.get("execution"), "historical execution")
    training = _mapping(historical.get("training"), "historical training")
    charged = _exact_historical_charge(execution.get("charged_seconds"))
    historical_counts = {
        "checkpoint_count": execution.get("checkpoint_count"),
        "evaluation_episodes": training.get("evaluation_episodes"),
        "optimizer_updates": execution.get("optimizer_updates"),
        "training_chunk_count": execution.get("training_chunk_count"),
        "training_episodes": execution.get("completed_training_episodes"),
    }
    if (
        historical_counts
        != {
            "checkpoint_count": 8,
            "evaluation_episodes": 0,
            "optimizer_updates": 8,
            "training_chunk_count": 8,
            "training_episodes": 512,
        }
        or training.get("episodes") != 512
    ):
        raise VerificationError("historical throughput evidence drifted")
    _verify_budget(
        {
            "ceiling_seconds": "14400.000",
            "control_reservation_seconds": "3600.000",
            "historical_charged_seconds": "2165.452",
            "historical_counts": historical_counts,
            "historical_multiplier": "3.000",
            "margin_seconds": "4303.644",
            "projected_total_seconds": "10096.356",
            "status": "passed",
        }
    )
    del historical, execution, training
    for path in (SUCCESSOR_CONTRACT_PATH, READINESS_CHANGE_SPEC_PATH):
        try:
            text = bound_payload(path).decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise VerificationError("bound contract is not UTF-8") from exc
        if any(token not in text for token in ("512", "14,400", "authority", "seed")):
            raise VerificationError(f"bound contract tokens drifted: {path}")

    registration_row = next(
        row
        for row in source["bindings"]
        if row["path"] == CONSUMED_REGISTRATION_PATH
    )
    return {
        "registration_binding": {
            key: registration_row[key] for key in ("path", "sha256", "size_bytes")
        },
        "registration_id": registration_id,
        "seed_count": SCHEDULE_SIZE,
        "seeds": seeds,
        "seeds_sha256": canonical_digest(seeds),
    }


def _verify_budget(value: object) -> dict[str, Any]:
    budget = _mapping(value, "budget evidence")
    expected = {
        "ceiling_seconds": "14400.000",
        "control_reservation_seconds": "3600.000",
        "historical_charged_seconds": "2165.452",
        "historical_counts": {
            "checkpoint_count": 8,
            "evaluation_episodes": 0,
            "optimizer_updates": 8,
            "training_chunk_count": 8,
            "training_episodes": 512,
        },
        "historical_multiplier": "3.000",
        "margin_seconds": "4303.644",
        "projected_total_seconds": "10096.356",
        "status": "passed",
    }
    if budget != expected:
        raise VerificationError("budget binding differs from fixed equation")
    projection = Decimal(budget["control_reservation_seconds"]) + (
        Decimal(budget["historical_multiplier"])
        * Decimal(budget["historical_charged_seconds"])
    )
    if (
        projection != Decimal(budget["projected_total_seconds"])
        or Decimal(budget["ceiling_seconds"]) - projection
        != Decimal(budget["margin_seconds"])
    ):
        raise VerificationError("budget arithmetic mismatch")
    return budget


def _verify_rehearsal(value: object) -> dict[str, Any]:
    rehearsal = _mapping(value, "rehearsal")
    _exact_keys(
        rehearsal,
        {
            "blocked_imports",
            "child_exit_code",
            "context_validation_count",
            "empirical_operations",
            "registration_size_bytes",
            "scratch_artifacts",
            "stage_results",
            "status",
            "synthetic_control_positions",
            "terminal_verdict",
            "verified",
        },
        "rehearsal",
    )
    if (
        rehearsal["blocked_imports"] != list(BLOCKED_REHEARSAL_IMPORTS)
        or rehearsal["child_exit_code"] != 0
        or rehearsal["verified"] is not True
        or rehearsal["empirical_operations"] != _empirical_operations()
        or rehearsal["registration_size_bytes"]
        != CONSUMED_REGISTRATION_SIZE_BYTES
        or rehearsal["synthetic_control_positions"] != CHUNK_SIZE
        or rehearsal["terminal_verdict"] != "experiment_failed_after_seed_access"
        or rehearsal["status"] != "passed"
    ):
        raise VerificationError("rehearsal boundary evidence mismatch")
    if rehearsal["context_validation_count"] != {
        "after_chunk": 1,
        "after_closeout": 1,
        "after_setup": 1,
    }:
        raise VerificationError("control-plane scaling evidence mismatch")
    scratch = _mapping(rehearsal["scratch_artifacts"], "scratch artifacts")
    _exact_keys(scratch, {"file_count", "sha256", "size_bytes"}, "scratch artifacts")
    _positive_int(scratch["file_count"], "scratch file count")
    _digest(scratch["sha256"], "scratch digest")
    _positive_int(scratch["size_bytes"], "scratch size")
    stages = rehearsal["stage_results"]
    if not isinstance(stages, list) or len(stages) != 3:
        raise VerificationError("rehearsal stage inventory mismatch")
    for expected_name, raw in zip(REHEARSAL_STAGE_ORDER, stages, strict=True):
        stage = _mapping(raw, "rehearsal stage")
        _exact_keys(
            stage,
            {"ceiling_seconds", "elapsed_seconds", "name", "status"},
            "rehearsal stage",
        )
        if (
            stage["name"] != expected_name
            or stage["status"] != "passed"
            or _decimal(stage["ceiling_seconds"], "stage ceiling")
            != STAGE_CEILING_SECONDS
        ):
            raise VerificationError("rehearsal stage boundary mismatch")
        elapsed = _decimal(stage["elapsed_seconds"], "stage elapsed")
        if elapsed < 0 or elapsed > STAGE_CEILING_SECONDS:
            raise VerificationError("rehearsal stage exceeded ceiling")
    return rehearsal


def _classify(failed: Sequence[str]) -> dict[str, Any]:
    ordered = [gate for gate in FAILURE_GATE_ORDER if gate in failed]
    if len(ordered) != len(set(failed)) or set(failed) - set(FAILURE_GATE_ORDER):
        raise VerificationError("decision failure gate inventory is invalid")
    if not ordered:
        return {"failed_gates": [], "reason": "go", "status": "go"}
    return {
        "failed_gates": ordered,
        "reason": f"no_go_{ordered[0]}",
        "status": "no_go",
    }


def _render_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Cross-Fitted Empirical Successor Readiness",
        "",
        f"- Decision: `{report['decision']['status']}`",
        f"- Reason: `{report['decision']['reason']}`",
        "- Empirical successor registration proposal eligible: "
        f"`{str(report['eligibility']['empirical_successor_registration_proposal_eligible']).lower()}`",
        f"- Source commit: `{report['source_commit']}`",
        f"- Readiness identity: `{report['readiness_identity_sha256']}`",
        "- Native loading, seed access, fitting, training, evaluation, gameplay, qualification, and promotion authority: `false`",
        "",
        "## Gates",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{gate}` | `{report['gates'][gate]}` |" for gate in FAILURE_GATE_ORDER)
    lines.extend(
        [
            "",
            "## Cohort",
            "",
            f"- Candidate seeds: `{report['cohort']['candidate_seed_count']}`",
            f"- Consumed seeds excluded as a whole: `{report['cohort']['consumed_seed_count']}`",
            f"- Collisions: `{report['cohort']['collision_count']}`",
            "",
            "## Rehearsal",
            "",
            f"- Actual registration bytes: `{report['rehearsal']['registration_size_bytes']}`",
            f"- Synthetic control positions: `{report['rehearsal']['synthetic_control_positions']}`",
            "- Complete registration validation counts: "
            f"`{json.dumps(report['rehearsal']['context_validation_count'], sort_keys=True, separators=(',', ':'))}`",
            "- Scratch artifacts were independently verified and are not part of this publication.",
            "",
            "## Fixed Budget",
            "",
            f"- Control reservation: `{report['budget']['control_reservation_seconds']}` seconds",
            f"- Historical workload: `{report['budget']['historical_charged_seconds']}` seconds",
            f"- Historical multiplier: `{report['budget']['historical_multiplier']}`",
            f"- Projected total: `{report['budget']['projected_total_seconds']}` seconds",
            f"- Margin: `{report['budget']['margin_seconds']}` seconds",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["limitations"])
    return "\n".join(lines) + "\n"


def _verify_report(
    value: object,
    *,
    candidate: Mapping[str, Any],
    candidate_binding: Mapping[str, Any],
) -> dict[str, Any]:
    report = _mapping(value, "readiness report")
    _exact_keys(
        report,
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
    if report["schema_version"] != REPORT_SCHEMA_VERSION:
        raise VerificationError("readiness report schema mismatch")
    if not isinstance(report["audit_id"], str) or _AUDIT_ID_RE.fullmatch(
        report["audit_id"]
    ) is None:
        raise VerificationError("audit identity is invalid")
    if report["authority"] != _authority():
        raise VerificationError("readiness authority is not all false")
    source = _verify_source_binding(report["source_binding"])
    if report["source_commit"] != source["source_commit"] or report[
        "source_commit"
    ] != candidate["source_commit"]:
        raise VerificationError("source commit differs across artifacts")
    budget = _verify_budget(report["budget"])
    rehearsal = _verify_rehearsal(report["rehearsal"])
    binding = _mapping(report["candidate_artifact_binding"], "candidate binding")
    expected_binding = _mapping(candidate_binding, "expected candidate binding")
    if binding != expected_binding:
        raise VerificationError("candidate artifact binding mismatch")
    cohort = _mapping(report["cohort"], "report cohort")
    candidate_seeds = candidate["candidate_schedule"]["seeds"]
    consumed_seeds = candidate["consumed_cohort"]["seeds"]
    expected_cohort = {
        "candidate_seed_count": len(candidate_seeds),
        "candidate_seeds_sha256": canonical_digest(candidate_seeds),
        "collision_count": candidate["disjointness"]["collision_count"],
        "collisions": candidate["disjointness"]["collisions"],
        "consumed_seed_count": len(consumed_seeds),
        "consumed_seeds_sha256": canonical_digest(consumed_seeds),
        "status": candidate["disjointness"]["status"],
    }
    if cohort != expected_cohort:
        raise VerificationError("report and candidate cohort evidence differ")
    gates = _mapping(report["gates"], "readiness gates")
    if set(gates) != set(FAILURE_GATE_ORDER) or any(
        item not in {"passed", "failed"} for item in gates.values()
    ):
        raise VerificationError("readiness gate order or status is invalid")
    expected_failed = [gate for gate in FAILURE_GATE_ORDER if gates[gate] == "failed"]
    expected_cohort_gate = "passed" if cohort["status"] == "passed" else "failed"
    if gates["cohort_not_fresh"] != expected_cohort_gate:
        raise VerificationError("cohort gate differs from collision evidence")
    for gate in (
        "source_binding",
        "rehearsal_boundary",
        "control_plane_scaling",
        "budget_binding",
        "artifact_binding",
    ):
        if gates[gate] != "passed":
            raise VerificationError(f"{gate} is not independently supported")
    decision = _classify(expected_failed)
    if report["decision"] != decision:
        raise VerificationError("typed decision precedence mismatch")
    eligibility = {
        "empirical_successor_registration_proposal_eligible": decision[
            "status"
        ]
        == "go"
    }
    if report["eligibility"] != eligibility:
        raise VerificationError("proposal eligibility mismatch")
    if report["limitations"] != list(_LIMITATIONS):
        raise VerificationError("limitations drifted")
    body = {
        key: item for key, item in report.items() if key != "readiness_identity_sha256"
    }
    if report["readiness_identity_sha256"] != canonical_digest(body):
        raise VerificationError("readiness identity mismatch")
    report["source_binding"] = source
    report["budget"] = budget
    report["rehearsal"] = rehearsal
    return report


def verify_publication_payloads(
    artifacts: Mapping[str, bytes],
    *,
    independently_rebuilt_inventory: Mapping[str, Any] | None = None,
    independently_rebuilt_inventory_sha256: str | None = None,
    expected_consumed_cohort: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if set(artifacts) != set(PUBLICATION_FILENAMES):
        raise VerificationError("publication artifact closure mismatch")
    for name, payload in artifacts.items():
        if not isinstance(payload, bytes) or not payload:
            raise VerificationError(f"publication artifact is empty: {name}")
        ceiling = (
            MAX_CANDIDATE_STORED_BYTES
            if name == CANDIDATE_INVENTORY_FILENAME
            else MAX_REPORT_ARTIFACT_BYTES
        )
        if len(payload) > ceiling:
            raise VerificationError(f"publication artifact exceeds ceiling: {name}")
    candidate_payload = artifacts[CANDIDATE_INVENTORY_FILENAME]
    candidate_canonical = _bounded_gzip(candidate_payload)
    candidate = _verify_candidate(
        _strict_json(candidate_canonical, "candidate inventory"),
        independently_rebuilt_inventory,
        independently_rebuilt_inventory_sha256=(
            independently_rebuilt_inventory_sha256
        ),
        expected_consumed_cohort=expected_consumed_cohort,
    )
    report = _verify_report(
        _strict_json(artifacts[REPORT_FILENAME], "readiness report"),
        candidate=candidate,
        candidate_binding={
            "canonical_sha256": hashlib.sha256(candidate_canonical).hexdigest(),
            "canonical_size_bytes": len(candidate_canonical),
            "encoding": GZIP_ENCODING,
            "path": CANDIDATE_INVENTORY_FILENAME,
            "sha256": hashlib.sha256(candidate_payload).hexdigest(),
            "size_bytes": len(candidate_payload),
        },
    )
    expected_markdown = _render_markdown(report).encode("utf-8")
    if artifacts[REPORT_MARKDOWN_FILENAME] != expected_markdown:
        raise VerificationError("readiness Markdown differs from JSON")
    return {
        "candidate_inventory_sha256": hashlib.sha256(candidate_payload).hexdigest(),
        "decision": report["decision"]["status"],
        "proposal_eligible": report["eligibility"][
            "empirical_successor_registration_proposal_eligible"
        ],
        "readiness_identity_sha256": report["readiness_identity_sha256"],
        "source_commit": report["source_commit"],
    }


def verify_publication(
    output_dir: Path | str, *, repo_root: Path | str
) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    root = Path(repo_root).resolve()
    if not output.is_dir():
        raise VerificationError("readiness publication directory is missing")
    children = list(output.iterdir())
    if any(not path.is_file() for path in children) or {
        path.name for path in children
    } != set(PUBLICATION_FILENAMES):
        raise VerificationError("readiness publication closure mismatch")
    candidate_path = output / CANDIDATE_INVENTORY_FILENAME
    artifacts: dict[str, bytes] = {}
    for name in PUBLICATION_FILENAMES:
        path = output / name
        ceiling = (
            MAX_CANDIDATE_STORED_BYTES
            if name == CANDIDATE_INVENTORY_FILENAME
            else MAX_REPORT_ARTIFACT_BYTES
        )
        try:
            if path.stat().st_size <= 0 or path.stat().st_size > ceiling:
                raise VerificationError(
                    f"readiness publication artifact size is invalid: {name}"
                )
            if name != CANDIDATE_INVENTORY_FILENAME:
                artifacts[name] = path.read_bytes()
        except OSError as exc:
            raise VerificationError(
                f"cannot read readiness publication artifact: {name}"
            ) from exc

    preliminary_report = _mapping(
        _strict_json(artifacts[REPORT_FILENAME], "readiness report"),
        "readiness report",
    )
    source = _verify_live_source_binding(
        root, preliminary_report.get("source_binding")
    )
    if preliminary_report.get("source_commit") != source["source_commit"]:
        raise VerificationError("readiness report source identity mismatch")
    expected_consumed = _verify_bound_evidence(root, source)

    rebuilt = rebuild_seed_inventory(
        root, repository_commit=source["source_commit"]
    )
    expected_candidate = _build_expected_candidate(
        rebuilt,
        source_commit=source["source_commit"],
        consumed_cohort=expected_consumed,
    )
    rebuilt_sha256 = expected_candidate["candidate_schedule"][
        "inventory_sha256"
    ]
    descriptor, expected_name = tempfile.mkstemp(
        prefix=f".{output.name}.expected-",
        suffix=".json.gz",
        dir=output.parent,
    )
    os.close(descriptor)
    expected_path = Path(expected_name)
    expected_path.unlink()
    try:
        candidate_binding = _write_expected_candidate_gzip(
            expected_path, expected_candidate
        )
        if not _files_equal(candidate_path, expected_path):
            raise VerificationError(
                "published candidate differs from independent canonical rebuild"
            )
        report = _verify_report(
            preliminary_report,
            candidate=expected_candidate,
            candidate_binding=candidate_binding,
        )
        expected_markdown = _render_markdown(report).encode("utf-8")
        if artifacts[REPORT_MARKDOWN_FILENAME] != expected_markdown:
            raise VerificationError("readiness Markdown differs from JSON")
        verified = {
            "candidate_inventory_sha256": candidate_binding["sha256"],
            "decision": report["decision"]["status"],
            "proposal_eligible": report["eligibility"][
                "empirical_successor_registration_proposal_eligible"
            ],
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "source_commit": report["source_commit"],
        }
        if verified["source_commit"] != source["source_commit"]:
            raise VerificationError("verified publication source identity mismatch")
        return {
            **verified,
            "independent_inventory_sha256": rebuilt_sha256,
            "status": "verified",
        }
    finally:
        try:
            expected_path.unlink()
        except FileNotFoundError:
            pass
        del expected_candidate, rebuilt
        gc.collect()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _wait_for_windows_process_job_assignment()
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if arguments and arguments[0] == "_verify-rehearsal":
            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument("--repo-root", type=Path, required=True)
            parser.add_argument("--source-commit", required=True)
            parser.add_argument("--scratch-root", type=Path, required=True)
            parser.add_argument("--expected-child-pid", type=int, required=True)
            rehearsal = parser.parse_args(arguments[1:])
            result = verify_rehearsal_scratch(
                rehearsal.scratch_root,
                repo_root=rehearsal.repo_root,
                source_commit=rehearsal.source_commit,
                expected_child_pid=rehearsal.expected_child_pid,
            )
        else:
            publication = _build_parser().parse_args(arguments)
            result = verify_publication(
                publication.output_dir, repo_root=publication.repo_root
            )
    except (VerificationError, OSError, subprocess.SubprocessError) as exc:
        sys.stderr.buffer.write(
            canonical_json_bytes(
                {
                    "error": str(exc),
                    "status": "verification_failed",
                    "type": type(exc).__name__,
                }
            )
        )
        return 1
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
