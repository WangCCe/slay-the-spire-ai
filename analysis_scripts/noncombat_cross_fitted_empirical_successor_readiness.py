"""Source-only readiness gate for a later cross-fitted empirical proposal.

The module has a standard-library-only import graph. It may inspect committed
bytes and exercise synthetic control-plane bookkeeping, but it never imports
Torch, the native adapter, or the empirical runtime and grants no empirical
authority.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
from ctypes import wintypes
import gc
import gzip
import hashlib
import importlib.abc
import io
import json
import math
import os
import queue
import re
import secrets
import signal
import shutil
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any


REPORT_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-report-v1"
)
CANDIDATE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-candidate-v1"
)
REPORT_FILENAME = "readiness_report.json"
REPORT_MARKDOWN_FILENAME = "readiness_report.md"
CANDIDATE_INVENTORY_FILENAME = "candidate_seed_inventory.json.gz"
PUBLICATION_FILENAMES = (
    CANDIDATE_INVENTORY_FILENAME,
    REPORT_FILENAME,
    REPORT_MARKDOWN_FILENAME,
)
ATTEMPT_ROOT_PATH = (
    "reports/noncombat_cross_fitted_empirical_successor_readiness_attempts"
)
ATTEMPT_STARTED_FILENAME = "attempt_started.json"
ATTEMPT_TERMINAL_FILENAME = "attempt_terminal.json"
ATTEMPT_VERIFIED_FILENAME = "attempt_verified.json"

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

HISTORICAL_TRAINING_EPISODES = 512
HISTORICAL_OPTIMIZER_UPDATES = 8
HISTORICAL_CHECKPOINTS = 8
HISTORICAL_TRAINING_CHUNKS = 8
HISTORICAL_EVALUATION_EPISODES = 0
HISTORICAL_SOURCE_CHARGED_SECONDS = Decimal("2165.4520000000193")
HISTORICAL_CHARGED_SECONDS = Decimal("2165.452")
CONTROL_RESERVATION_SECONDS = Decimal("3600.000")
HISTORICAL_MULTIPLIER = Decimal("3.000")
EMPIRICAL_CEILING_SECONDS = Decimal("14400.000")
PROJECTED_TOTAL_SECONDS = Decimal("10096.356")
PROJECTED_MARGIN_SECONDS = Decimal("4303.644")
STAGE_CEILING_SECONDS = Decimal("300.000")
INDEPENDENT_VERIFIER_CEILING_SECONDS = 900
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
MAX_CANDIDATE_STORED_BYTES = 64 * 1024 * 1024
MAX_CANDIDATE_CANONICAL_BYTES = 512 * 1024 * 1024
MAX_REPORT_ARTIFACT_BYTES = 4 * 1024 * 1024
GZIP_ENCODING = "gzip-mtime-zero-v1"
_IS_WINDOWS = os.name == "nt"
_PROCESS_JOB_EVENT_ENV = "STS_READINESS_PROCESS_JOB_EVENT"

_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_AUDIT_ID_RE = re.compile(r"[a-z0-9][a-z0-9._:-]{7,191}")
_DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{3}")


class _WindowsJobBasicAccountingInformation(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_longlong),
        ("TotalKernelTime", ctypes.c_longlong),
        ("ThisPeriodTotalUserTime", ctypes.c_longlong),
        ("ThisPeriodTotalKernelTime", ctypes.c_longlong),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


class _WindowsJobBasicLimitInformation(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _WindowsJobIoCounters(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _WindowsJobExtendedLimitInformation(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _WindowsJobBasicLimitInformation),
        ("IoInfo", _WindowsJobIoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _WindowsProcessStartEvent:
    def __init__(self) -> None:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateEventW.argtypes = [
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateEventW.restype = wintypes.HANDLE
        kernel32.SetEvent.argtypes = [wintypes.HANDLE]
        kernel32.SetEvent.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        self.name = (
            f"Local\\sts-readiness-job-{os.getpid()}-{time.time_ns()}"
        )
        self._kernel32 = kernel32
        self._handle = kernel32.CreateEventW(None, True, False, self.name)
        if not self._handle:
            raise ReadinessBlocked(
                f"Windows process start event failed: {ctypes.get_last_error()}"
            )

    def release(self) -> None:
        if self._handle is None or not self._kernel32.SetEvent(self._handle):
            raise ReadinessBlocked(
                f"Windows process start release failed: {ctypes.get_last_error()}"
            )

    def close(self) -> None:
        handle = self._handle
        if handle is None:
            return
        self._handle = None
        if not self._kernel32.CloseHandle(handle):
            raise ReadinessBlocked(
                f"Windows process start event close failed: {ctypes.get_last_error()}"
            )


def _wait_for_windows_process_job_assignment() -> None:
    event_name = os.environ.pop(_PROCESS_JOB_EVENT_ENV, None)
    if event_name is None:
        return
    if not _IS_WINDOWS:
        raise ReadinessBlocked("Windows process job event reached another platform")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.OpenEventW.restype = wintypes.HANDLE
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    synchronize = 0x00100000
    wait_object_0 = 0
    handle = kernel32.OpenEventW(synchronize, False, event_name)
    if not handle:
        raise ReadinessBlocked(
            f"Windows process start event open failed: {ctypes.get_last_error()}"
        )
    try:
        if kernel32.WaitForSingleObject(handle, 30_000) != wait_object_0:
            raise ReadinessBlocked("Windows process job assignment handshake timed out")
    finally:
        kernel32.CloseHandle(handle)


class _WindowsKillOnCloseJob:
    _JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1
    _JOB_OBJECT_BASIC_PROCESS_ID_LIST = 3
    _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    def __init__(self, process: subprocess.Popen[Any]):
        if not _IS_WINDOWS:
            raise ReadinessBlocked("Windows process job requested on another platform")
        raw_process_handle = getattr(process, "_handle", None)
        if raw_process_handle is None:
            raise ReadinessBlocked("spawned process handle is unavailable")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.SetInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        kernel32.SetInformationJobObject.restype = wintypes.BOOL
        kernel32.AssignProcessToJobObject.argtypes = [
            wintypes.HANDLE,
            wintypes.HANDLE,
        ]
        kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
        kernel32.QueryInformationJobObject.argtypes = [
            wintypes.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.c_void_p,
        ]
        kernel32.QueryInformationJobObject.restype = wintypes.BOOL
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.TerminateJobObject.restype = wintypes.BOOL
        kernel32.OpenProcess.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        ]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.WaitForSingleObject.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateJobObjectW(None, None)
        if not handle:
            raise ReadinessBlocked(
                f"Windows process job creation failed: {ctypes.get_last_error()}"
            )
        self._kernel32 = kernel32
        self._handle = handle
        try:
            limits = _WindowsJobExtendedLimitInformation()
            limits.BasicLimitInformation.LimitFlags = (
                self._JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )
            if not kernel32.SetInformationJobObject(
                handle,
                self._JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(limits),
                ctypes.sizeof(limits),
            ):
                raise ReadinessBlocked(
                    "Windows process job limit setup failed: "
                    f"{ctypes.get_last_error()}"
                )
            if not kernel32.AssignProcessToJobObject(
                handle, wintypes.HANDLE(int(raw_process_handle))
            ):
                raise ReadinessBlocked(
                    "Windows process job assignment failed: "
                    f"{ctypes.get_last_error()}"
                )
        except BaseException:
            self.close()
            raise

    def _active_processes(self) -> int:
        if self._handle is None:
            return 0
        accounting = _WindowsJobBasicAccountingInformation()
        if not self._kernel32.QueryInformationJobObject(
            self._handle,
            self._JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION,
            ctypes.byref(accounting),
            ctypes.sizeof(accounting),
            None,
        ):
            raise ReadinessBlocked(
                "Windows process job query failed: "
                f"{ctypes.get_last_error()}"
            )
        return int(accounting.ActiveProcesses)

    def _active_process_handles(self) -> list[int]:
        capacity = 1024
        process_id_list_type = type(
            "_WindowsJobProcessIdList",
            (ctypes.Structure,),
            {
                "_fields_": [
                    ("NumberOfAssignedProcesses", wintypes.DWORD),
                    ("NumberOfProcessIdsInList", wintypes.DWORD),
                    ("ProcessIdList", ctypes.c_size_t * capacity),
                ]
            },
        )
        process_ids = process_id_list_type()
        if not self._kernel32.QueryInformationJobObject(
            self._handle,
            self._JOB_OBJECT_BASIC_PROCESS_ID_LIST,
            ctypes.byref(process_ids),
            ctypes.sizeof(process_ids),
            None,
        ):
            raise ReadinessBlocked(
                "Windows process job member query failed: "
                f"{ctypes.get_last_error()}"
            )
        listed = int(process_ids.NumberOfProcessIdsInList)
        assigned = int(process_ids.NumberOfAssignedProcesses)
        if assigned > capacity or listed > capacity or listed != assigned:
            raise ReadinessBlocked(
                "Windows process job member list exceeds fixed supervision capacity"
            )
        synchronize = 0x00100000
        handles: list[int] = []
        try:
            for index in range(listed):
                process_id = int(process_ids.ProcessIdList[index])
                handle = self._kernel32.OpenProcess(
                    synchronize, False, process_id
                )
                if not handle:
                    error = ctypes.get_last_error()
                    if error == 87:
                        continue
                    raise ReadinessBlocked(
                        "Windows supervised process handle open failed: "
                        f"{error}"
                    )
                handles.append(handle)
            return handles
        except BaseException:
            for handle in handles:
                self._kernel32.CloseHandle(handle)
            raise

    def terminate_and_wait(self, timeout_seconds: int) -> None:
        if self._handle is None or self._active_processes() == 0:
            return
        process_handles = self._active_process_handles()
        try:
            if not self._kernel32.TerminateJobObject(self._handle, 1):
                raise ReadinessBlocked(
                    "Windows process job termination failed: "
                    f"{ctypes.get_last_error()}"
                )
            deadline = time.monotonic() + timeout_seconds
            for handle in process_handles:
                remaining_ms = max(
                    0, math.ceil((deadline - time.monotonic()) * 1000)
                )
                if self._kernel32.WaitForSingleObject(handle, remaining_ms) != 0:
                    raise ReadinessBlocked(
                        "process tree termination could not confirm descendant exit"
                    )
            if self._active_processes() != 0:
                raise ReadinessBlocked(
                    "process tree termination left active job processes"
                )
        finally:
            for handle in process_handles:
                self._kernel32.CloseHandle(handle)

    def close(self) -> None:
        handle = getattr(self, "_handle", None)
        if handle is None:
            return
        self._handle = None
        if not self._kernel32.CloseHandle(handle):
            raise ReadinessBlocked(
                f"Windows process job close failed: {ctypes.get_last_error()}"
            )
_LIMITATIONS = (
    "This source-only result does not establish policy quality or causal effect.",
    "Candidate seed integers are data only and were not used to construct an environment.",
    "A go result permits only a separately reviewed empirical registration proposal.",
    "Native loading, seed access, fitting, training, evaluation, gameplay, qualification, and promotion remain unauthorized.",
)


class ReadinessBlocked(RuntimeError):
    """Raised when a fixed readiness contract cannot be proven exactly."""


class ReadinessAttemptTerminal(ReadinessBlocked):
    """Raised after a source-keyed attempt records one terminal no-go."""

    def __init__(self, result: Mapping[str, Any]) -> None:
        self.result = dict(result)
        super().__init__(self.result["decision"]["reason"])


class ReadinessSourceConsumed(ReadinessBlocked):
    """Raised when another canonical attempt already owns the source commit."""


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


def _canonical_stream_digest(value: object) -> str:
    encoder = json.JSONEncoder(
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256()
    for text in encoder.iterencode(value):
        digest.update(text.encode("utf-8"))
    digest.update(b"\n")
    return digest.hexdigest()


def deterministic_gzip_bytes(payload: bytes) -> bytes:
    if not isinstance(payload, bytes) or not payload:
        raise ReadinessBlocked("candidate canonical payload must be nonempty bytes")
    if len(payload) > MAX_CANDIDATE_CANONICAL_BYTES:
        raise ReadinessBlocked("candidate canonical payload exceeds byte ceiling")
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", filename="", mtime=0) as handle:
        handle.write(payload)
    stored = buffer.getvalue()
    if len(stored) > MAX_CANDIDATE_STORED_BYTES:
        raise ReadinessBlocked("candidate gzip payload exceeds stored byte ceiling")
    return stored


def bounded_gzip_payload(stored: bytes) -> bytes:
    if not isinstance(stored, bytes) or not stored:
        raise ReadinessBlocked("candidate gzip payload must be nonempty bytes")
    if len(stored) > MAX_CANDIDATE_STORED_BYTES:
        raise ReadinessBlocked("candidate gzip payload exceeds stored byte ceiling")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as handle:
            payload = handle.read(MAX_CANDIDATE_CANONICAL_BYTES + 1)
    except (EOFError, OSError, gzip.BadGzipFile) as exc:
        raise ReadinessBlocked("candidate gzip payload is invalid") from exc
    if len(payload) > MAX_CANDIDATE_CANONICAL_BYTES:
        raise ReadinessBlocked("candidate canonical payload exceeds byte ceiling")
    if deterministic_gzip_bytes(payload) != stored:
        raise ReadinessBlocked("candidate gzip payload is not deterministic")
    return payload


def decode_candidate_artifact(stored: bytes) -> dict[str, Any]:
    payload = bounded_gzip_payload(stored)
    return validate_candidate_artifact(
        _strict_json_bytes(payload, "candidate canonical inventory")
    )


def _candidate_binding_from_encoded(
    canonical: bytes, stored: bytes
) -> dict[str, Any]:
    if not canonical or len(canonical) > MAX_CANDIDATE_CANONICAL_BYTES:
        raise ReadinessBlocked("candidate canonical payload exceeds byte ceiling")
    if not stored or len(stored) > MAX_CANDIDATE_STORED_BYTES:
        raise ReadinessBlocked("candidate gzip payload exceeds stored byte ceiling")
    return {
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "canonical_size_bytes": len(canonical),
        "encoding": GZIP_ENCODING,
        "path": CANDIDATE_INVENTORY_FILENAME,
        "sha256": hashlib.sha256(stored).hexdigest(),
        "size_bytes": len(stored),
    }


def _encode_validated_candidate(
    candidate: Mapping[str, Any]
) -> tuple[bytes, bytes, dict[str, Any]]:
    canonical = canonical_json_bytes(candidate)
    stored = deterministic_gzip_bytes(canonical)
    return canonical, stored, _candidate_binding_from_encoded(canonical, stored)


def _write_canonical_gzip_file(
    destination: Path | str, value: object
) -> dict[str, Any]:
    path = Path(destination).resolve()
    encoder = json.JSONEncoder(
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    canonical_hash = hashlib.sha256()
    canonical_size = 0
    try:
        with path.open("xb") as raw:
            with gzip.GzipFile(
                fileobj=raw, mode="wb", filename="", mtime=0
            ) as compressed:
                for text in encoder.iterencode(value):
                    payload = text.encode("utf-8")
                    canonical_size += len(payload)
                    if canonical_size > MAX_CANDIDATE_CANONICAL_BYTES:
                        raise ReadinessBlocked(
                            "candidate canonical payload exceeds byte ceiling"
                        )
                    canonical_hash.update(payload)
                    compressed.write(payload)
                canonical_size += 1
                if canonical_size > MAX_CANDIDATE_CANONICAL_BYTES:
                    raise ReadinessBlocked(
                        "candidate canonical payload exceeds byte ceiling"
                    )
                canonical_hash.update(b"\n")
                compressed.write(b"\n")
            raw.flush()
            os.fsync(raw.fileno())
    except (OSError, TypeError, ValueError) as exc:
        raise ReadinessBlocked("candidate streaming gzip publication failed") from exc
    stored_size = path.stat().st_size
    if stored_size <= 0 or stored_size > MAX_CANDIDATE_STORED_BYTES:
        raise ReadinessBlocked("candidate gzip payload exceeds stored byte ceiling")
    stored_hash = hashlib.sha256()
    with path.open("rb") as handle:
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


def build_candidate_binding(candidate_artifact: Mapping[str, Any]) -> dict[str, Any]:
    candidate = validate_candidate_artifact(candidate_artifact)
    _canonical, _stored, binding = _encode_validated_candidate(candidate)
    return binding


def readiness_authority() -> dict[str, bool]:
    return {name: False for name in AUTHORITY_NAMES}


def _empirical_operations() -> dict[str, bool]:
    return {name: False for name in EMPIRICAL_OPERATION_NAMES}


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReadinessBlocked(f"{label} must be a mapping")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ReadinessBlocked(f"{label} fields mismatch")


def _commit(value: object, label: str = "source commit") -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise ReadinessBlocked(f"{label} must be 40 lowercase hex characters")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ReadinessBlocked(f"{label} must be a SHA-256 digest")
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReadinessBlocked(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: object, label: str) -> int:
    result = _nonnegative_int(value, label)
    if result == 0:
        raise ReadinessBlocked(f"{label} must be positive")
    return result


def _canonical_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ReadinessBlocked(f"{label} must be a canonical repository path")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.as_posix() != value:
        raise ReadinessBlocked(f"{label} must be a canonical repository path")
    return value


def _decimal_string(value: object, label: str) -> Decimal:
    if not isinstance(value, str) or _DECIMAL_RE.fullmatch(value) is None:
        raise ReadinessBlocked(f"{label} must be a canonical three-place decimal")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ReadinessBlocked(f"{label} is invalid") from exc
    if not result.is_finite():
        raise ReadinessBlocked(f"{label} must be finite")
    return result


def _strict_json_bytes(payload: bytes, label: str) -> object:
    if not payload or not payload.endswith(b"\n"):
        raise ReadinessBlocked(f"{label} must end with one canonical newline")

    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ReadinessBlocked(f"{label} contains duplicate key {key}")
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise ReadinessBlocked(f"{label} contains non-finite value {value}")

    try:
        value = json.loads(
            payload.decode("utf-8", errors="strict"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except ReadinessBlocked:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReadinessBlocked(f"{label} is invalid JSON") from exc
    if canonical_json_bytes(value) != payload:
        raise ReadinessBlocked(f"{label} is not canonical JSON")
    return value


def classify_decision(failed_gates: Sequence[str]) -> dict[str, Any]:
    if isinstance(failed_gates, (str, bytes)):
        raise ReadinessBlocked("failure gates must be a sequence")
    observed = list(failed_gates)
    if len(observed) != len(set(observed)):
        raise ReadinessBlocked("failure gate list contains duplicates")
    unknown = set(observed) - set(FAILURE_GATE_ORDER)
    if unknown:
        raise ReadinessBlocked(f"unknown failure gate: {sorted(unknown)[0]}")
    ordered = [gate for gate in FAILURE_GATE_ORDER if gate in observed]
    if not ordered:
        return {"failed_gates": [], "reason": "go", "status": "go"}
    return {
        "failed_gates": ordered,
        "reason": f"no_go_{ordered[0]}",
        "status": "no_go",
    }


def _historical_count(
    execution: Mapping[str, Any], training: Mapping[str, Any], field: str
) -> int:
    if field == "training_episodes":
        left = execution.get("completed_training_episodes")
        right = training.get("episodes")
        if left != right:
            raise ReadinessBlocked("budget binding training episode counts differ")
        return _nonnegative_int(left, "historical training episodes")
    if field == "evaluation_episodes":
        return _nonnegative_int(
            training.get("evaluation_episodes"), "historical evaluation episodes"
        )
    return _nonnegative_int(execution.get(field), f"historical {field}")


def build_budget_evidence(historical_document: Mapping[str, Any]) -> dict[str, Any]:
    document = _mapping(historical_document, "historical throughput")
    execution = _mapping(document.get("execution"), "historical execution")
    training = _mapping(document.get("training"), "historical training")
    counts = {
        "checkpoint_count": _historical_count(
            execution, training, "checkpoint_count"
        ),
        "evaluation_episodes": _historical_count(
            execution, training, "evaluation_episodes"
        ),
        "optimizer_updates": _historical_count(
            execution, training, "optimizer_updates"
        ),
        "training_chunk_count": _historical_count(
            execution, training, "training_chunk_count"
        ),
        "training_episodes": _historical_count(
            execution, training, "training_episodes"
        ),
    }
    expected_counts = {
        "checkpoint_count": HISTORICAL_CHECKPOINTS,
        "evaluation_episodes": HISTORICAL_EVALUATION_EPISODES,
        "optimizer_updates": HISTORICAL_OPTIMIZER_UPDATES,
        "training_chunk_count": HISTORICAL_TRAINING_CHUNKS,
        "training_episodes": HISTORICAL_TRAINING_EPISODES,
    }
    if counts != expected_counts:
        raise ReadinessBlocked("budget binding historical counts drifted")
    observed = execution.get("charged_seconds")
    if not isinstance(observed, Decimal):
        raise ReadinessBlocked(
            "budget binding charged seconds must remain a JSON number"
        )
    if not observed.is_finite():
        raise ReadinessBlocked("budget binding charged seconds are invalid")
    if observed != HISTORICAL_SOURCE_CHARGED_SECONDS:
        raise ReadinessBlocked("budget binding historical charge drifted")
    projection = (
        CONTROL_RESERVATION_SECONDS
        + (HISTORICAL_MULTIPLIER * HISTORICAL_CHARGED_SECONDS)
    ).quantize(Decimal("0.001"))
    margin = (EMPIRICAL_CEILING_SECONDS - projection).quantize(Decimal("0.001"))
    if projection != PROJECTED_TOTAL_SECONDS or margin != PROJECTED_MARGIN_SECONDS:
        raise ReadinessBlocked("budget binding fixed arithmetic drifted")
    return {
        "ceiling_seconds": format(EMPIRICAL_CEILING_SECONDS, "f"),
        "control_reservation_seconds": format(CONTROL_RESERVATION_SECONDS, "f"),
        "historical_charged_seconds": format(HISTORICAL_CHARGED_SECONDS, "f"),
        "historical_counts": counts,
        "historical_multiplier": format(HISTORICAL_MULTIPLIER, "f"),
        "margin_seconds": format(margin, "f"),
        "projected_total_seconds": format(projection, "f"),
        "status": "passed",
    }


def validate_budget_evidence(value: object) -> dict[str, Any]:
    budget = _mapping(value, "budget evidence")
    _exact_keys(
        budget,
        {
            "ceiling_seconds",
            "control_reservation_seconds",
            "historical_charged_seconds",
            "historical_counts",
            "historical_multiplier",
            "margin_seconds",
            "projected_total_seconds",
            "status",
        },
        "budget evidence",
    )
    expected = build_budget_evidence(
        {
            "execution": {
                "charged_seconds": HISTORICAL_SOURCE_CHARGED_SECONDS,
                "checkpoint_count": HISTORICAL_CHECKPOINTS,
                "completed_training_episodes": HISTORICAL_TRAINING_EPISODES,
                "optimizer_updates": HISTORICAL_OPTIMIZER_UPDATES,
                "training_chunk_count": HISTORICAL_TRAINING_CHUNKS,
            },
            "training": {
                "episodes": HISTORICAL_TRAINING_EPISODES,
                "evaluation_episodes": HISTORICAL_EVALUATION_EPISODES,
            },
        }
    )
    if budget != expected:
        raise ReadinessBlocked("budget binding evidence differs from fixed equation")
    return budget


def _validate_inventory_shape(value: object, source_commit: str) -> dict[str, Any]:
    inventory = _mapping(value, "historical seed inventory")
    expected_fields = {
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
    _exact_keys(inventory, expected_fields, "historical seed inventory")
    if inventory["repository_commit"] != source_commit:
        raise ReadinessBlocked("historical seed inventory commit mismatch")
    start = _nonnegative_int(
        inventory["canonical_search_start"], "canonical search start"
    )
    excluded = inventory["excluded_seeds"]
    if not isinstance(excluded, list):
        raise ReadinessBlocked("excluded seed inventory must be a list")
    normalized = [_nonnegative_int(seed, "excluded seed") for seed in excluded]
    if normalized != sorted(set(normalized)):
        raise ReadinessBlocked("excluded seeds must be ascending and unique")
    if inventory["excluded_seed_count"] != len(normalized):
        raise ReadinessBlocked("excluded seed count mismatch")
    if not isinstance(inventory["rows"], list) or not isinstance(
        inventory["source_bindings"], list
    ):
        raise ReadinessBlocked("seed inventory rows or bindings are invalid")
    if inventory["row_count"] != len(inventory["rows"]):
        raise ReadinessBlocked("seed inventory row count mismatch")
    if inventory["source_count"] != len(inventory["source_bindings"]):
        raise ReadinessBlocked("seed inventory source count mismatch")
    inventory["canonical_search_start"] = start
    inventory["excluded_seeds"] = normalized
    return inventory


def _canonical_candidate_seeds(inventory: Mapping[str, Any]) -> list[int]:
    excluded = set(inventory["excluded_seeds"])
    candidate = inventory["canonical_search_start"]
    seeds: list[int] = []
    while len(seeds) < SCHEDULE_SIZE:
        if candidate not in excluded:
            seeds.append(candidate)
        candidate += 1
    return seeds


def _validate_candidate_schedule(
    value: object, inventory: Mapping[str, Any]
) -> dict[str, Any]:
    schedule = _mapping(value, "candidate schedule")
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
    if schedule["canonical_search_start"] != inventory["canonical_search_start"]:
        raise ReadinessBlocked("candidate canonical search start mismatch")
    if schedule["inventory_sha256"] != _canonical_stream_digest(inventory):
        raise ReadinessBlocked("candidate inventory identity mismatch")
    if schedule["schema_version"] != (
        "noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1"
    ):
        raise ReadinessBlocked("candidate schedule schema mismatch")
    seeds = schedule["seeds"]
    if not isinstance(seeds, list):
        raise ReadinessBlocked("candidate seeds must be a list")
    normalized = [_nonnegative_int(seed, "candidate seed") for seed in seeds]
    if schedule["seed_count"] != SCHEDULE_SIZE or len(normalized) != SCHEDULE_SIZE:
        raise ReadinessBlocked("candidate schedule must contain exactly 512 seeds")
    if normalized != _canonical_candidate_seeds(inventory):
        raise ReadinessBlocked("candidate schedule is not the canonical selection")
    schedule["seeds"] = normalized
    return schedule


def _consumed_cohort(
    registration: Mapping[str, Any], binding: Mapping[str, Any]
) -> dict[str, Any]:
    value = _mapping(registration, "consumed registration")
    registration_id = value.get("registration_id")
    if not isinstance(registration_id, str) or not registration_id:
        raise ReadinessBlocked("consumed registration identity is invalid")
    schedule = _mapping(value.get("schedule"), "consumed schedule")
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
        raise ReadinessBlocked("consumed schedule provenance mismatch")
    seeds = schedule.get("seeds")
    if not isinstance(seeds, list):
        raise ReadinessBlocked("consumed schedule seeds must be a list")
    normalized = [_nonnegative_int(seed, "consumed seed") for seed in seeds]
    if len(normalized) != SCHEDULE_SIZE or normalized != sorted(set(normalized)):
        raise ReadinessBlocked("consumed cohort must contain 512 ascending seeds")
    chunks = schedule.get("chunks")
    if (
        not isinstance(chunks, list)
        or len(chunks) != 8
        or any(not isinstance(chunk, list) or len(chunk) != CHUNK_SIZE for chunk in chunks)
    ):
        raise ReadinessBlocked("consumed cohort chunk count mismatch")
    normalized_chunks = [
        [_nonnegative_int(seed, "consumed chunk seed") for seed in chunk]
        for chunk in chunks
    ]
    flattened = [seed for chunk in normalized_chunks for seed in chunk]
    if (
        len(flattened) != SCHEDULE_SIZE
        or flattened != normalized
        or schedule.get("chunk_count") != 8
        or schedule.get("episodes_per_chunk") != CHUNK_SIZE
    ):
        raise ReadinessBlocked("consumed cohort chunk structure mismatch")
    declared_digest = schedule.get("seeds_sha256")
    if declared_digest != canonical_digest(normalized):
        raise ReadinessBlocked("consumed cohort seed digest mismatch")
    bound = _mapping(binding, "consumed registration binding")
    _exact_keys(bound, {"path", "sha256", "size_bytes"}, "consumed binding")
    if bound["path"] != CONSUMED_REGISTRATION_PATH:
        raise ReadinessBlocked("consumed registration binding path mismatch")
    _digest(bound["sha256"], "consumed registration binding")
    _positive_int(bound["size_bytes"], "consumed registration byte size")
    return {
        "registration_binding": bound,
        "registration_id": registration_id,
        "seed_count": len(normalized),
        "seeds": normalized,
        "seeds_sha256": canonical_digest(normalized),
    }


def build_candidate_artifact(
    *,
    source_commit: str,
    historical_inventory: Mapping[str, Any],
    candidate_schedule: Mapping[str, Any],
    consumed_registration: Mapping[str, Any],
    consumed_registration_binding: Mapping[str, Any],
) -> dict[str, Any]:
    commit = _commit(source_commit)
    inventory = _validate_inventory_shape(historical_inventory, commit)
    schedule = _validate_candidate_schedule(candidate_schedule, inventory)
    consumed = _consumed_cohort(
        consumed_registration, consumed_registration_binding
    )
    collisions = sorted(set(schedule["seeds"]) & set(consumed["seeds"]))
    artifact = {
        "authority": readiness_authority(),
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
    return validate_candidate_artifact(artifact)


def validate_candidate_artifact(value: object) -> dict[str, Any]:
    artifact = _mapping(value, "candidate artifact")
    _exact_keys(
        artifact,
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
    if artifact["schema_version"] != CANDIDATE_SCHEMA_VERSION:
        raise ReadinessBlocked("candidate artifact schema mismatch")
    commit = _commit(artifact["source_commit"])
    if artifact["authority"] != readiness_authority():
        raise ReadinessBlocked("candidate artifact authority must remain all false")
    inventory = _validate_inventory_shape(
        artifact["historical_seed_inventory"], commit
    )
    schedule = _validate_candidate_schedule(artifact["candidate_schedule"], inventory)
    consumed_raw = _mapping(artifact["consumed_cohort"], "consumed cohort")
    _exact_keys(
        consumed_raw,
        {
            "registration_binding",
            "registration_id",
            "seed_count",
            "seeds",
            "seeds_sha256",
        },
        "consumed cohort",
    )
    seeds = consumed_raw["seeds"]
    if not isinstance(seeds, list):
        raise ReadinessBlocked("consumed cohort seeds must be a list")
    normalized_consumed = [
        _nonnegative_int(seed, "consumed cohort seed") for seed in seeds
    ]
    if (
        len(normalized_consumed) != SCHEDULE_SIZE
        or normalized_consumed != sorted(set(normalized_consumed))
        or consumed_raw["seed_count"] != SCHEDULE_SIZE
        or consumed_raw["seeds_sha256"] != canonical_digest(normalized_consumed)
    ):
        raise ReadinessBlocked("consumed cohort identity mismatch")
    binding = _mapping(
        consumed_raw["registration_binding"], "consumed registration binding"
    )
    _exact_keys(binding, {"path", "sha256", "size_bytes"}, "consumed binding")
    if binding["path"] != CONSUMED_REGISTRATION_PATH:
        raise ReadinessBlocked("consumed registration path mismatch")
    _digest(binding["sha256"], "consumed registration digest")
    _positive_int(binding["size_bytes"], "consumed registration size")
    if not isinstance(consumed_raw["registration_id"], str) or not consumed_raw[
        "registration_id"
    ]:
        raise ReadinessBlocked("consumed registration identity is invalid")
    disjointness = _mapping(artifact["disjointness"], "cohort disjointness")
    _exact_keys(
        disjointness,
        {"collision_count", "collisions", "status"},
        "cohort disjointness",
    )
    observed_collisions = sorted(set(schedule["seeds"]) & set(normalized_consumed))
    expected_status = "passed" if not observed_collisions else "failed"
    if disjointness != {
        "collision_count": len(observed_collisions),
        "collisions": observed_collisions,
        "status": expected_status,
    }:
        raise ReadinessBlocked("cohort collision evidence mismatch")
    artifact["historical_seed_inventory"] = inventory
    artifact["candidate_schedule"] = schedule
    artifact["consumed_cohort"] = {
        **consumed_raw,
        "registration_binding": binding,
        "seeds": normalized_consumed,
    }
    artifact["disjointness"] = disjointness
    return artifact


def _git_text(repo_root: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReadinessBlocked(
            f"no_go_source_binding: Git {' '.join(args)} failed"
        ) from exc
    return completed.stdout.strip()


def _git_blob(repo_root: Path, commit: str, path: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "show", f"{commit}:{path}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ReadinessBlocked(
            f"no_go_source_binding: cannot read bound Git blob {path}"
        ) from exc
    return completed.stdout


def _worktree_blob(repo_root: Path, path: str) -> bytes:
    try:
        return (repo_root / PurePosixPath(path)).read_bytes()
    except OSError as exc:
        raise ReadinessBlocked(
            f"no_go_source_binding: cannot read tracked worktree file {path}"
        ) from exc


def observe_source_binding(
    repo_root: Path | str,
    *,
    source_commit: str,
    required_paths: Sequence[tuple[str, str]] = BOUND_INPUT_PATHS,
    git_text: Callable[..., str] = _git_text,
    blob_reader: Callable[[Path, str, str], bytes] = _git_blob,
    worktree_reader: Callable[[Path, str], bytes] = _worktree_blob,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = _commit(source_commit)
    try:
        head = git_text(root, "rev-parse", "HEAD").strip()
        origin = git_text(root, "rev-parse", "origin/master").strip()
        status = git_text(
            root, "status", "--porcelain", "--untracked-files=no"
        ).strip()
    except ReadinessBlocked:
        raise
    except Exception as exc:
        raise ReadinessBlocked(
            "no_go_source_binding: Git observer failed"
        ) from exc
    if head != commit or origin != commit or status:
        raise ReadinessBlocked(
            "no_go_source_binding: HEAD, origin/master, or tracked status drifted"
        )
    normalized_paths: list[tuple[str, str]] = []
    seen_roles: set[str] = set()
    seen_paths: set[str] = set()
    for role, path in required_paths:
        if not isinstance(role, str) or not role or role in seen_roles:
            raise ReadinessBlocked("no_go_source_binding: binding role is invalid")
        canonical_path = _canonical_path(path, "bound input path")
        if canonical_path in seen_paths:
            raise ReadinessBlocked("no_go_source_binding: duplicate binding path")
        seen_roles.add(role)
        seen_paths.add(canonical_path)
        normalized_paths.append((role, canonical_path))
    bindings: list[dict[str, Any]] = []
    for role, path in normalized_paths:
        try:
            payload = blob_reader(root, commit, path)
            worktree_payload = worktree_reader(root, path)
        except ReadinessBlocked:
            raise
        except Exception as exc:
            raise ReadinessBlocked(
                f"no_go_source_binding: cannot observe {path}"
            ) from exc
        if not isinstance(payload, bytes) or not payload:
            raise ReadinessBlocked(
                f"no_go_source_binding: bound Git blob is empty: {path}"
            )
        if payload != worktree_payload:
            raise ReadinessBlocked(
                f"no_go_source_binding: worktree bytes differ: {path}"
            )
        bindings.append(
            {
                "path": path,
                "role": role,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    return {
        "bindings": bindings,
        "bindings_sha256": canonical_digest(bindings),
        "head_commit": head,
        "origin_master_commit": origin,
        "source_commit": commit,
        "status": "passed",
        "tracked_clean": True,
    }


def _parse_bound_json(
    payload: bytes,
    label: str,
    *,
    exact_decimals: bool = False,
) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ReadinessBlocked(f"{label} contains duplicate key {key}")
            result[key] = item
        return result

    def reject_constant(value: str) -> None:
        raise ReadinessBlocked(f"{label} contains non-finite value {value}")

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
    except ReadinessBlocked:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReadinessBlocked(f"{label} is invalid JSON") from exc
    if not isinstance(value, dict):
        raise ReadinessBlocked(f"{label} must be a JSON object")
    return value


def _source_binding_by_path(
    source_binding: Mapping[str, Any], path: str
) -> dict[str, Any]:
    normalized = validate_source_binding(source_binding)
    rows = [row for row in normalized["bindings"] if row["path"] == path]
    if len(rows) != 1:
        raise ReadinessBlocked(f"source binding is missing exact path {path}")
    return rows[0]


def load_bound_evidence(
    repo_root: Path | str,
    *,
    source_binding: Mapping[str, Any],
    blob_reader: Callable[[Path, str, str], bytes] = _git_blob,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    source = validate_source_binding(source_binding)
    observed_inputs = [
        (row["role"], row["path"]) for row in source["bindings"]
    ]
    if observed_inputs != list(BOUND_INPUT_PATHS):
        raise ReadinessBlocked(
            "no_go_source_binding: source binding input inventory mismatch"
        )
    commit = source["source_commit"]

    def bound_payload(path: str) -> bytes:
        try:
            payload = blob_reader(root, commit, path)
        except Exception as exc:
            raise ReadinessBlocked(
                f"no_go_source_binding: cannot reload evidence {path}"
            ) from exc
        binding = _source_binding_by_path(source, path)
        if binding["sha256"] != hashlib.sha256(payload).hexdigest() or binding[
            "size_bytes"
        ] != len(payload):
            raise ReadinessBlocked(
                f"no_go_source_binding: evidence binding drifted for {path}"
            )
        return payload

    registration_payload = bound_payload(CONSUMED_REGISTRATION_PATH)
    registration = _parse_bound_json(
        registration_payload, "consumed registration"
    )
    schedule = _mapping(registration.get("schedule"), "consumed schedule")
    seeds = schedule.get("seeds")
    if (
        len(registration_payload) != CONSUMED_REGISTRATION_SIZE_BYTES
        or registration.get("registration_id")
        != "noncombat-cross-fitted-hierarchical-learning-successor-20260806-r1"
        or not isinstance(seeds, list)
        or len(seeds) != SCHEDULE_SIZE
    ):
        raise ReadinessBlocked("no_go_source_binding: consumed registration drifted")
    consumed_registration = {
        "registration_id": registration["registration_id"],
        "schedule": schedule,
    }
    registration_source_binding = _source_binding_by_path(
        source, CONSUMED_REGISTRATION_PATH
    )
    consumed_registration_binding = {
        key: registration_source_binding[key]
        for key in ("path", "sha256", "size_bytes")
    }
    try:
        _consumed_cohort(
            consumed_registration,
            consumed_registration_binding,
        )
    except ReadinessBlocked as exc:
        raise ReadinessBlocked(
            "no_go_source_binding: consumed registration schedule drifted"
        ) from exc
    del registration_payload, registration, schedule, seeds

    terminal = _parse_bound_json(
        bound_payload(CONSUMED_TERMINAL_PATH), "consumed terminal"
    )
    resources = _mapping(terminal.get("resource_use"), "consumed resources")
    if (
        terminal.get("verdict") != "experiment_failed_after_seed_access"
        or terminal.get("checkpoint_count") != 0
        or resources.get("environment_accesses") != 12
    ):
        raise ReadinessBlocked("no_go_source_binding: consumed terminal drifted")
    terminal_sha256 = terminal.get("terminal_sha256")

    manifest = _parse_bound_json(
        bound_payload(CONSUMED_MANIFEST_PATH), "consumed manifest"
    )
    if manifest.get("terminal_sha256") != terminal_sha256:
        raise ReadinessBlocked("no_go_source_binding: terminal manifest drifted")
    del manifest, terminal, resources

    bottleneck = _parse_bound_json(
        bound_payload(BOTTLENECK_AUDIT_PATH), "bottleneck audit"
    )
    finding_ids = {
        row.get("finding_id")
        for row in bottleneck.get("findings", [])
        if isinstance(row, Mapping)
    }
    if not {
        "repeated_full_registration_validation_dominates_each_access",
        "noninfrastructure_terminal_failure_does_not_persist_elapsed_charge",
        "producer_terminal_publication_has_large_revalidation_tail",
        "outer_wait_timeout_did_not_represent_child_exit",
    }.issubset(finding_ids):
        raise ReadinessBlocked("no_go_source_binding: bottleneck evidence drifted")
    del bottleneck, finding_ids

    repair = _parse_bound_json(
        bound_payload(CONTROL_PLANE_REPAIR_PATH), "control-plane repair"
    )
    structural = _mapping(repair.get("structural_evidence"), "repair structural evidence")
    validations = _mapping(
        structural.get("complete_registration_validations"),
        "repair validation evidence",
    )
    if (
        repair.get("verdict")
        != "source_only_control_plane_repaired_no_empirical_authority"
        or repair.get("scope", {}).get("source_only") is not True
        or validations
        != {
            "after_64_accesses": 1,
            "after_same_process_terminal_closeout": 1,
            "context_creation": 1,
        }
    ):
        raise ReadinessBlocked("no_go_source_binding: repair closeout drifted")
    del repair, structural, validations

    historical = _parse_bound_json(
        bound_payload(HISTORICAL_THROUGHPUT_PATH),
        "historical throughput",
        exact_decimals=True,
    )
    for path in (SUCCESSOR_CONTRACT_PATH, READINESS_CHANGE_SPEC_PATH):
        try:
            text = bound_payload(path).decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise ReadinessBlocked("no_go_source_binding: contract is not UTF-8") from exc
        for token in (
            "512",
            "14,400",
            "authority",
            "seed",
        ):
            if token not in text:
                raise ReadinessBlocked(
                    f"no_go_source_binding: contract token missing: {token}"
                )
    return {
        "consumed_registration": consumed_registration,
        "consumed_registration_binding": consumed_registration_binding,
        "historical_throughput": historical,
    }


def _read_git_blob_exact(stream: Any, size: int, path: str) -> bytes:
    remaining = size
    chunks: list[bytes] = []
    while remaining:
        payload = stream.read(remaining)
        if not payload:
            raise ReadinessBlocked(
                f"no_go_cohort_not_fresh: Git blob is truncated for {path}"
            )
        chunks.append(payload)
        remaining -= len(payload)
    return b"".join(chunks)


def _iter_seed_git_blobs(
    repo_root: Path, *, commit: str, paths: Sequence[str]
) -> Any:
    ordered = list(paths)
    if ordered != sorted(set(ordered)):
        raise ReadinessBlocked(
            "no_go_cohort_not_fresh: seed source paths are not sorted and unique"
        )
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
        raise ReadinessBlocked(
            "no_go_cohort_not_fresh: Git blob streaming failed"
        ) from exc
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        process.wait()
        raise ReadinessBlocked(
            "no_go_cohort_not_fresh: Git blob streaming pipes are unavailable"
        )
    try:
        for path in ordered:
            process.stdin.write(f"{commit}:{path}\n".encode("utf-8"))
            process.stdin.flush()
            raw_header = process.stdout.readline()
            if not raw_header.endswith(b"\n"):
                raise ReadinessBlocked(
                    f"no_go_cohort_not_fresh: Git blob header is truncated for {path}"
                )
            try:
                header = raw_header.decode("ascii", errors="strict").split()
            except UnicodeError as exc:
                raise ReadinessBlocked(
                    f"no_go_cohort_not_fresh: Git blob header is invalid for {path}"
                ) from exc
            if len(header) != 3 or header[1] != "blob" or not header[2].isdigit():
                raise ReadinessBlocked(
                    f"no_go_cohort_not_fresh: Git object is not a blob for {path}"
                )
            payload = _read_git_blob_exact(process.stdout, int(header[2]), path)
            if process.stdout.read(1) != b"\n":
                raise ReadinessBlocked(
                    f"no_go_cohort_not_fresh: Git blob terminator is missing for {path}"
                )
            yield path, payload
        process.stdin.close()
        return_code = process.wait(timeout=30)
        if return_code != 0:
            detail = process.stderr.read(2000).decode(
                "utf-8", errors="replace"
            ).strip()
            raise ReadinessBlocked(
                "no_go_cohort_not_fresh: Git blob streaming failed"
                + (f": {detail}" if detail else "")
            )
    except BaseException:
        if process.poll() is None:
            process.kill()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise ReadinessBlocked(
                "no_go_cohort_not_fresh: Git blob stream did not terminate"
            ) from exc
        raise
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            try:
                stream.close()
            except OSError:
                pass


def _build_streamed_seed_inventory(
    repo_root: Path | str,
    *,
    repository_commit: str,
    seed_module: Any,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = _commit(repository_commit)
    paths = seed_module._list_report_paths(root, commit)
    candidates: list[str] = []
    formats: dict[str, str] = {}
    for path in paths:
        if seed_module._is_readiness_derived_report_path(path):
            continue
        format_name = seed_module._artifact_format(path)
        if format_name is None:
            if seed_module._unsupported_seed_candidate(path):
                raise ReadinessBlocked(
                    f"no_go_cohort_not_fresh: unsupported seed artifact: {path}"
                )
            continue
        candidates.append(path)
        formats[path] = format_name

    rows: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for path, payload in _iter_seed_git_blobs(
        root, commit=commit, paths=sorted(candidates)
    ):
        documents = seed_module._parse_documents(path, payload, formats[path])
        source_rows: list[dict[str, Any]] = []
        for document_index, document in enumerate(documents):
            source_rows.extend(
                seed_module._seed_rows(
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

    rows.sort(key=seed_module._row_sort_key)
    extracted = {row["seed"] for row in rows}
    reserved = set(
        range(
            seed_module.PREVIOUS_UNTOUCHED_HOLDOUT_START,
            seed_module.PREVIOUS_UNTOUCHED_HOLDOUT_END + 1,
        )
    )
    excluded = sorted(extracted | reserved)
    inventory = {
        "canonical_search_start": seed_module.CANONICAL_SEARCH_START,
        "excluded_seed_count": len(excluded),
        "excluded_seeds": excluded,
        "repository_commit": commit,
        "reserved_seed_ranges": [
            dict(item) for item in seed_module._RESERVED_SEED_RANGES
        ],
        "row_count": len(rows),
        "rows": rows,
        "schema_version": seed_module.SEED_INVENTORY_SCHEMA_VERSION,
        "source_bindings": bindings,
        "source_count": len(bindings),
    }
    return _validate_inventory_shape(inventory, commit)


def _materialize_streamed_fresh_schedule(
    inventory: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _validate_inventory_shape(
        inventory, _commit(inventory.get("repository_commit"))
    )
    seeds = _canonical_candidate_seeds(normalized)
    return {
        "canonical_search_start": normalized["canonical_search_start"],
        "inventory_sha256": _canonical_stream_digest(normalized),
        "schema_version": (
            "noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1"
        ),
        "seed_count": SCHEDULE_SIZE,
        "seeds": seeds,
    }


def build_candidate_from_git(
    repo_root: Path | str,
    *,
    source_binding: Mapping[str, Any],
    bound_evidence: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(repo_root).resolve()
    source = validate_source_binding(source_binding)
    commit = source["source_commit"]
    try:
        if bound_evidence is None:
            evidence = load_bound_evidence(root, source_binding=source)
        else:
            evidence = _mapping(bound_evidence, "bound evidence")
        _exact_keys(
            evidence,
            {
                "consumed_registration",
                "consumed_registration_binding",
                "historical_throughput",
            },
            "bound evidence",
        )
        _consumed_cohort(
            evidence["consumed_registration"],
            evidence["consumed_registration_binding"],
        )
    except Exception as exc:
        raise ReadinessBlocked(
            "no_go_source_binding: bound evidence validation failed"
        ) from exc
    try:
        seed_module = __import__(
            "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_seed_inventory",
            fromlist=["build_seed_inventory"],
        )
        inventory = _build_streamed_seed_inventory(
            root,
            repository_commit=commit,
            seed_module=seed_module,
        )
        schedule = _materialize_streamed_fresh_schedule(inventory)
    except Exception as exc:
        raise ReadinessBlocked("no_go_cohort_not_fresh: inventory rebuild failed") from exc
    candidate = build_candidate_artifact(
        source_commit=commit,
        historical_inventory=inventory,
        candidate_schedule=schedule,
        consumed_registration=evidence["consumed_registration"],
        consumed_registration_binding=evidence[
            "consumed_registration_binding"
        ],
    )
    return candidate, evidence


def validate_source_binding(value: object) -> dict[str, Any]:
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
        or binding["tracked_clean"] is not True
        or binding["status"] != "passed"
    ):
        raise ReadinessBlocked("source binding is not a pushed clean identity")
    rows = binding["bindings"]
    if not isinstance(rows, list) or not rows:
        raise ReadinessBlocked("source bindings must be a nonempty list")
    normalized: list[dict[str, Any]] = []
    roles: set[str] = set()
    paths: set[str] = set()
    for index, raw in enumerate(rows):
        row = _mapping(raw, f"source binding[{index}]")
        _exact_keys(row, {"path", "role", "sha256", "size_bytes"}, "source row")
        row["path"] = _canonical_path(row["path"], "source row path")
        if not isinstance(row["role"], str) or not row["role"]:
            raise ReadinessBlocked("source row role is invalid")
        row["sha256"] = _digest(row["sha256"], "source row digest")
        row["size_bytes"] = _positive_int(row["size_bytes"], "source row size")
        if row["role"] in roles or row["path"] in paths:
            raise ReadinessBlocked("source binding roles and paths must be unique")
        roles.add(row["role"])
        paths.add(row["path"])
        normalized.append(row)
    if binding["bindings_sha256"] != canonical_digest(normalized):
        raise ReadinessBlocked("source binding digest mismatch")
    binding["bindings"] = normalized
    return binding


def validate_rehearsal_summary(value: object) -> dict[str, Any]:
    rehearsal = _mapping(value, "rehearsal summary")
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
        "rehearsal summary",
    )
    if rehearsal["blocked_imports"] != list(BLOCKED_REHEARSAL_IMPORTS):
        raise ReadinessBlocked("no_go_rehearsal_boundary: blocked imports drifted")
    if rehearsal["child_exit_code"] != 0 or rehearsal["verified"] is not True:
        raise ReadinessBlocked("no_go_rehearsal_boundary: child did not verify")
    counts = _mapping(
        rehearsal["context_validation_count"], "context validation counts"
    )
    _exact_keys(
        counts,
        {"after_chunk", "after_closeout", "after_setup"},
        "context validation counts",
    )
    if counts != {"after_chunk": 1, "after_closeout": 1, "after_setup": 1}:
        raise ReadinessBlocked(
            "no_go_control_plane_scaling: registration validation count grew"
        )
    operations = _mapping(rehearsal["empirical_operations"], "empirical operations")
    if operations != _empirical_operations():
        raise ReadinessBlocked(
            "no_go_rehearsal_boundary: empirical operation was observed"
        )
    if rehearsal["registration_size_bytes"] != CONSUMED_REGISTRATION_SIZE_BYTES:
        raise ReadinessBlocked("no_go_control_plane_scaling: registration size drifted")
    scratch = _mapping(rehearsal["scratch_artifacts"], "scratch artifacts")
    _exact_keys(scratch, {"file_count", "sha256", "size_bytes"}, "scratch artifacts")
    _positive_int(scratch["file_count"], "scratch file count")
    _digest(scratch["sha256"], "scratch digest")
    _positive_int(scratch["size_bytes"], "scratch size")
    stages = rehearsal["stage_results"]
    if not isinstance(stages, list) or len(stages) != len(REHEARSAL_STAGE_ORDER):
        raise ReadinessBlocked("no_go_rehearsal_boundary: stage inventory mismatch")
    normalized_stages: list[dict[str, str]] = []
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
            or _decimal_string(stage["ceiling_seconds"], "stage ceiling")
            != STAGE_CEILING_SECONDS
        ):
            raise ReadinessBlocked("no_go_rehearsal_boundary: stage failed")
        elapsed = _decimal_string(stage["elapsed_seconds"], "stage elapsed time")
        if elapsed < 0 or elapsed > STAGE_CEILING_SECONDS:
            raise ReadinessBlocked("no_go_rehearsal_boundary: stage timed out")
        normalized_stages.append(stage)
    if (
        rehearsal["status"] != "passed"
        or rehearsal["synthetic_control_positions"] != CHUNK_SIZE
        or rehearsal["terminal_verdict"] != "experiment_failed_after_seed_access"
    ):
        raise ReadinessBlocked("no_go_rehearsal_boundary: closeout witness drifted")
    rehearsal["context_validation_count"] = counts
    rehearsal["empirical_operations"] = operations
    rehearsal["scratch_artifacts"] = scratch
    rehearsal["stage_results"] = normalized_stages
    return rehearsal


def _artifact_binding(value: object, *, expected_path: str) -> dict[str, Any]:
    binding = _mapping(value, "candidate artifact binding")
    _exact_keys(
        binding,
        {
            "canonical_sha256",
            "canonical_size_bytes",
            "encoding",
            "path",
            "sha256",
            "size_bytes",
        },
        "candidate binding",
    )
    if binding["path"] != expected_path:
        raise ReadinessBlocked("candidate artifact binding path mismatch")
    if binding["encoding"] != GZIP_ENCODING:
        raise ReadinessBlocked("candidate artifact encoding mismatch")
    binding["canonical_sha256"] = _digest(
        binding["canonical_sha256"], "candidate canonical digest"
    )
    binding["canonical_size_bytes"] = _positive_int(
        binding["canonical_size_bytes"], "candidate canonical size"
    )
    if binding["canonical_size_bytes"] > MAX_CANDIDATE_CANONICAL_BYTES:
        raise ReadinessBlocked("candidate canonical artifact exceeds byte ceiling")
    binding["sha256"] = _digest(binding["sha256"], "candidate artifact digest")
    binding["size_bytes"] = _positive_int(
        binding["size_bytes"], "candidate artifact size"
    )
    if binding["size_bytes"] > MAX_CANDIDATE_STORED_BYTES:
        raise ReadinessBlocked("candidate artifact exceeds byte ceiling")
    return binding


def _assemble_report(
    *,
    audit_id: str,
    source: Mapping[str, Any],
    candidate: Mapping[str, Any],
    candidate_binding: Mapping[str, Any],
    rehearsal_summary: Mapping[str, Any],
    budget_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(audit_id, str) or _AUDIT_ID_RE.fullmatch(audit_id) is None:
        raise ReadinessBlocked("audit identity is invalid")
    failed_gates: list[str] = []
    if candidate["disjointness"]["status"] != "passed":
        failed_gates.append("cohort_not_fresh")
    gates = {gate: "passed" for gate in FAILURE_GATE_ORDER}
    for gate in failed_gates:
        gates[gate] = "failed"
    decision = classify_decision(failed_gates)
    candidate_seeds = candidate["candidate_schedule"]["seeds"]
    consumed_seeds = candidate["consumed_cohort"]["seeds"]
    body = {
        "audit_id": audit_id,
        "authority": readiness_authority(),
        "budget": budget_evidence,
        "candidate_artifact_binding": candidate_binding,
        "cohort": {
            "candidate_seed_count": len(candidate_seeds),
            "candidate_seeds_sha256": canonical_digest(candidate_seeds),
            "collision_count": candidate["disjointness"]["collision_count"],
            "collisions": candidate["disjointness"]["collisions"],
            "consumed_seed_count": len(consumed_seeds),
            "consumed_seeds_sha256": canonical_digest(consumed_seeds),
            "status": candidate["disjointness"]["status"],
        },
        "decision": decision,
        "eligibility": {
            "empirical_successor_registration_proposal_eligible": (
                decision["status"] == "go"
            )
        },
        "gates": gates,
        "limitations": list(_LIMITATIONS),
        "rehearsal": rehearsal_summary,
        "schema_version": REPORT_SCHEMA_VERSION,
        "source_binding": source,
        "source_commit": source["source_commit"],
    }
    return {**body, "readiness_identity_sha256": canonical_digest(body)}


def build_report(
    *,
    audit_id: str,
    source_binding: Mapping[str, Any],
    candidate_artifact: Mapping[str, Any],
    candidate_binding: Mapping[str, Any],
    rehearsal: Mapping[str, Any],
    budget: Mapping[str, Any],
) -> dict[str, Any]:
    source = validate_source_binding(source_binding)
    candidate = validate_candidate_artifact(candidate_artifact)
    bound_candidate = _artifact_binding(
        candidate_binding, expected_path=CANDIDATE_INVENTORY_FILENAME
    )
    if bound_candidate != build_candidate_binding(candidate):
        raise ReadinessBlocked("candidate artifact binding differs from bytes")
    rehearsal_summary = validate_rehearsal_summary(rehearsal)
    budget_evidence = validate_budget_evidence(budget)
    return _assemble_report(
        audit_id=audit_id,
        source=source,
        candidate=candidate,
        candidate_binding=bound_candidate,
        rehearsal_summary=rehearsal_summary,
        budget_evidence=budget_evidence,
    )


def validate_report(value: object) -> dict[str, Any]:
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
        raise ReadinessBlocked("readiness report schema mismatch")
    if not isinstance(report["audit_id"], str) or _AUDIT_ID_RE.fullmatch(
        report["audit_id"]
    ) is None:
        raise ReadinessBlocked("audit identity is invalid")
    if report["authority"] != readiness_authority():
        raise ReadinessBlocked("readiness report authority must remain all false")
    source = validate_source_binding(report["source_binding"])
    if report["source_commit"] != source["source_commit"]:
        raise ReadinessBlocked("report source commit mismatch")
    budget = validate_budget_evidence(report["budget"])
    rehearsal = validate_rehearsal_summary(report["rehearsal"])
    candidate_binding = _artifact_binding(
        report["candidate_artifact_binding"],
        expected_path=CANDIDATE_INVENTORY_FILENAME,
    )
    cohort = _mapping(report["cohort"], "report cohort")
    _exact_keys(
        cohort,
        {
            "candidate_seed_count",
            "candidate_seeds_sha256",
            "collision_count",
            "collisions",
            "consumed_seed_count",
            "consumed_seeds_sha256",
            "status",
        },
        "report cohort",
    )
    if cohort["candidate_seed_count"] != SCHEDULE_SIZE or cohort[
        "consumed_seed_count"
    ] != SCHEDULE_SIZE:
        raise ReadinessBlocked("report cohort count mismatch")
    _digest(cohort["candidate_seeds_sha256"], "candidate seed digest")
    _digest(cohort["consumed_seeds_sha256"], "consumed seed digest")
    collisions = cohort["collisions"]
    if not isinstance(collisions, list):
        raise ReadinessBlocked("report collisions must be a list")
    normalized_collisions = [
        _nonnegative_int(seed, "report collision seed") for seed in collisions
    ]
    if normalized_collisions != sorted(set(normalized_collisions)):
        raise ReadinessBlocked("report collisions must be ascending and unique")
    expected_cohort_status = "passed" if not normalized_collisions else "failed"
    if (
        cohort["collision_count"] != len(normalized_collisions)
        or cohort["status"] != expected_cohort_status
    ):
        raise ReadinessBlocked("report cohort status mismatch")
    gates = _mapping(report["gates"], "readiness gates")
    if set(gates) != set(FAILURE_GATE_ORDER) or any(
        status not in {"passed", "failed"} for status in gates.values()
    ):
        raise ReadinessBlocked("readiness gate inventory mismatch")
    expected_failed = [gate for gate in FAILURE_GATE_ORDER if gates[gate] == "failed"]
    if gates["cohort_not_fresh"] != (
        "passed" if cohort["status"] == "passed" else "failed"
    ):
        raise ReadinessBlocked("cohort gate and evidence disagree")
    for gate in (
        "source_binding",
        "rehearsal_boundary",
        "control_plane_scaling",
        "budget_binding",
        "artifact_binding",
    ):
        if gates[gate] != "passed":
            raise ReadinessBlocked(f"published {gate} gate lacks valid evidence")
    expected_decision = classify_decision(expected_failed)
    if report["decision"] != expected_decision:
        raise ReadinessBlocked("readiness decision precedence mismatch")
    expected_eligibility = {
        "empirical_successor_registration_proposal_eligible": (
            expected_decision["status"] == "go"
        )
    }
    if report["eligibility"] != expected_eligibility:
        raise ReadinessBlocked("proposal eligibility mismatch")
    if report["limitations"] != list(_LIMITATIONS):
        raise ReadinessBlocked("readiness limitations drifted")
    digest = _digest(report["readiness_identity_sha256"], "readiness identity")
    body = {
        key: item for key, item in report.items() if key != "readiness_identity_sha256"
    }
    if digest != canonical_digest(body):
        raise ReadinessBlocked("readiness report identity mismatch")
    report["source_binding"] = source
    report["budget"] = budget
    report["rehearsal"] = rehearsal
    report["candidate_artifact_binding"] = candidate_binding
    report["cohort"] = {**cohort, "collisions": normalized_collisions}
    report["gates"] = gates
    return report


def render_markdown(report: Mapping[str, Any]) -> str:
    value = validate_report(report)
    lines = [
        "# Cross-Fitted Empirical Successor Readiness",
        "",
        f"- Decision: `{value['decision']['status']}`",
        f"- Reason: `{value['decision']['reason']}`",
        "- Empirical successor registration proposal eligible: "
        f"`{str(value['eligibility']['empirical_successor_registration_proposal_eligible']).lower()}`",
        f"- Source commit: `{value['source_commit']}`",
        f"- Readiness identity: `{value['readiness_identity_sha256']}`",
        "- Native loading, seed access, fitting, training, evaluation, gameplay, qualification, and promotion authority: `false`",
        "",
        "## Gates",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{gate}` | `{value['gates'][gate]}` |" for gate in FAILURE_GATE_ORDER)
    lines.extend(
        [
            "",
            "## Cohort",
            "",
            f"- Candidate seeds: `{value['cohort']['candidate_seed_count']}`",
            f"- Consumed seeds excluded as a whole: `{value['cohort']['consumed_seed_count']}`",
            f"- Collisions: `{value['cohort']['collision_count']}`",
            "",
            "## Rehearsal",
            "",
            f"- Actual registration bytes: `{value['rehearsal']['registration_size_bytes']}`",
            f"- Synthetic control positions: `{value['rehearsal']['synthetic_control_positions']}`",
            "- Complete registration validation counts: "
            f"`{json.dumps(value['rehearsal']['context_validation_count'], sort_keys=True, separators=(',', ':'))}`",
            "- Scratch artifacts were independently verified and are not part of this publication.",
            "",
            "## Fixed Budget",
            "",
            f"- Control reservation: `{value['budget']['control_reservation_seconds']}` seconds",
            f"- Historical workload: `{value['budget']['historical_charged_seconds']}` seconds",
            f"- Historical multiplier: `{value['budget']['historical_multiplier']}`",
            f"- Projected total: `{value['budget']['projected_total_seconds']}` seconds",
            f"- Margin: `{value['budget']['margin_seconds']}` seconds",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in value["limitations"])
    return "\n".join(lines) + "\n"


def build_publication_artifacts(
    *, report: Mapping[str, Any], candidate_artifact: Mapping[str, Any]
) -> dict[str, bytes]:
    candidate = validate_candidate_artifact(candidate_artifact)
    value = validate_report(report)
    _candidate_canonical, candidate_payload, expected_binding = (
        _encode_validated_candidate(candidate)
    )
    if value["candidate_artifact_binding"] != expected_binding:
        raise ReadinessBlocked("candidate artifact binding mismatch")
    artifacts = {
        CANDIDATE_INVENTORY_FILENAME: candidate_payload,
        REPORT_FILENAME: canonical_json_bytes(value),
        REPORT_MARKDOWN_FILENAME: render_markdown(value).encode("utf-8"),
    }
    validate_publication_artifacts(artifacts)
    return artifacts


def validate_publication_artifacts(
    artifacts: Mapping[str, bytes]
) -> dict[str, Any]:
    if set(artifacts) != set(PUBLICATION_FILENAMES):
        raise ReadinessBlocked("publication artifact inventory mismatch")
    for name, payload in artifacts.items():
        if not isinstance(payload, bytes) or not payload:
            raise ReadinessBlocked(f"publication artifact is empty: {name}")
        ceiling = (
            MAX_CANDIDATE_STORED_BYTES
            if name == CANDIDATE_INVENTORY_FILENAME
            else MAX_REPORT_ARTIFACT_BYTES
        )
        if len(payload) > ceiling:
            raise ReadinessBlocked(f"publication artifact exceeds ceiling: {name}")
    candidate = decode_candidate_artifact(
        artifacts[CANDIDATE_INVENTORY_FILENAME]
    )
    report = validate_report(
        _strict_json_bytes(artifacts[REPORT_FILENAME], "readiness report")
    )
    expected_binding = build_candidate_binding(candidate)
    if report["candidate_artifact_binding"] != expected_binding:
        raise ReadinessBlocked("candidate artifact binding mismatch")
    candidate_seeds = candidate["candidate_schedule"]["seeds"]
    consumed_seeds = candidate["consumed_cohort"]["seeds"]
    if (
        report["source_commit"] != candidate["source_commit"]
        or report["cohort"]["candidate_seeds_sha256"]
        != canonical_digest(candidate_seeds)
        or report["cohort"]["consumed_seeds_sha256"]
        != canonical_digest(consumed_seeds)
        or report["cohort"]["collisions"]
        != candidate["disjointness"]["collisions"]
    ):
        raise ReadinessBlocked("candidate and report cohort evidence differ")
    expected_markdown = render_markdown(report).encode("utf-8")
    if artifacts[REPORT_MARKDOWN_FILENAME] != expected_markdown:
        raise ReadinessBlocked("readiness Markdown differs from report")
    return report


def _write_canonical_once(path: Path, value: Mapping[str, Any]) -> None:
    payload = canonical_json_bytes(value)
    _write_bytes_once(path, payload)


def _write_bytes_once(path: Path, payload: bytes) -> None:
    if not isinstance(payload, bytes) or not payload:
        raise ReadinessBlocked("write-once evidence payload is empty")
    try:
        with path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise ReadinessBlocked(f"write-once evidence failed: {path.name}") from exc


def _attempt_started_record(
    *,
    source_commit: str,
    audit_id: str,
    scratch_root: Path,
    output_dir: Path,
    staging_dir: Path,
) -> dict[str, Any]:
    body = {
        "audit_id": audit_id,
        "authority": readiness_authority(),
        "empirical_operations": _empirical_operations(),
        "output_dir": str(output_dir),
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-attempt-v1"
        ),
        "scratch_root": str(scratch_root),
        "source_commit": source_commit,
        "staging_dir": str(staging_dir),
        "status": "started",
    }
    return {**body, "attempt_sha256": canonical_digest(body)}


def _claim_readiness_attempt(
    repo_root: Path | str,
    *,
    source_commit: str,
    audit_id: str,
    scratch_root: Path | str,
    output_dir: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = _commit(source_commit)
    if not isinstance(audit_id, str) or _AUDIT_ID_RE.fullmatch(audit_id) is None:
        raise ReadinessBlocked("audit identity is invalid")
    scratch = Path(scratch_root).resolve()
    output = Path(output_dir).resolve()
    attempt_parent = root / PurePosixPath(ATTEMPT_ROOT_PATH)
    attempt_dir = attempt_parent / commit
    claim_staging = attempt_parent / (
        f".{commit}.{os.getpid()}.{time.time_ns()}.claim"
    )
    staging = output.parent / f".{output.name}.{commit}.staging"
    attempt_parent.mkdir(parents=True, exist_ok=True)
    started = _attempt_started_record(
        source_commit=commit,
        audit_id=audit_id,
        scratch_root=scratch,
        output_dir=output,
        staging_dir=staging,
    )
    try:
        claim_staging.mkdir()
        _write_canonical_once(
            claim_staging / ATTEMPT_STARTED_FILENAME, started
        )
        os.rename(claim_staging, attempt_dir)
    except OSError as exc:
        if claim_staging.exists():
            shutil.rmtree(claim_staging)
        if attempt_dir.exists():
            raise ReadinessSourceConsumed(
                "readiness source identity is already consumed"
            ) from exc
        raise ReadinessBlocked("cannot claim readiness source identity") from exc
    except BaseException:
        if claim_staging.exists():
            shutil.rmtree(claim_staging)
        raise
    return {
        "attempt_dir": attempt_dir,
        "output_dir": output,
        "scratch_root": scratch,
        "staging_dir": staging,
        "started": started,
    }


def _recover_owned_readiness_attempt(
    repo_root: Path,
    *,
    source_commit: str,
    audit_id: str,
    scratch_root: Path,
    output_dir: Path,
) -> dict[str, Any] | None:
    attempt_dir = repo_root / PurePosixPath(ATTEMPT_ROOT_PATH) / source_commit
    staging = output_dir.parent / f".{output_dir.name}.{source_commit}.staging"
    expected = _attempt_started_record(
        source_commit=source_commit,
        audit_id=audit_id,
        scratch_root=scratch_root,
        output_dir=output_dir,
        staging_dir=staging,
    )
    started_path = attempt_dir / ATTEMPT_STARTED_FILENAME
    if not started_path.is_file():
        return None
    try:
        observed = _strict_json_bytes(
            started_path.read_bytes(), "readiness attempt start"
        )
    except (OSError, ReadinessBlocked):
        return None
    if observed != expected:
        return None
    return {
        "attempt_dir": attempt_dir,
        "output_dir": output_dir,
        "scratch_root": scratch_root,
        "staging_dir": staging,
        "started": expected,
    }


def _failure_gate(exc: BaseException, default_gate: str) -> str:
    message = str(exc)
    explicit = re.match(
        r"no_go_("
        + "|".join(re.escape(gate) for gate in FAILURE_GATE_ORDER)
        + r")(?::(?:\s|$)|$)",
        message,
    )
    if explicit is not None:
        return explicit.group(1)
    return default_gate


def _scratch_verifier_failure_gate(stderr: bytes) -> str:
    default_gate = "rehearsal_boundary"
    try:
        payload = _strict_json_bytes(stderr, "scratch verifier failure")
    except ReadinessBlocked:
        return default_gate
    if not isinstance(payload, Mapping):
        return default_gate
    error = payload.get("error")
    if not isinstance(error, str):
        return default_gate
    gate = _failure_gate(ReadinessBlocked(error), default_gate)
    return "control_plane_scaling" if gate == "control_plane_scaling" else default_gate


def _terminalize_attempt_no_go(
    attempt: Mapping[str, Any], *, gate: str, error: BaseException
) -> dict[str, Any]:
    if gate not in FAILURE_GATE_ORDER:
        raise ReadinessBlocked("attempt terminal gate is invalid")
    started = _mapping(attempt.get("started"), "attempt start")
    body = {
        "attempt_sha256": started["attempt_sha256"],
        "audit_id": started["audit_id"],
        "authority": readiness_authority(),
        "decision": classify_decision([gate]),
        "empirical_operations": _empirical_operations(),
        "failure": {
            "message": str(error)[-2000:],
            "type": type(error).__name__,
        },
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-attempt-terminal-v1"
        ),
        "source_commit": started["source_commit"],
        "status": "terminal_no_go",
    }
    terminal = {**body, "terminal_sha256": canonical_digest(body)}
    _write_canonical_once(
        Path(attempt["attempt_dir"]) / ATTEMPT_TERMINAL_FILENAME,
        terminal,
    )
    return terminal


def _installed_publication_boundary_crossed(attempt: Mapping[str, Any]) -> bool:
    attempt_dir = Path(attempt["attempt_dir"])
    output = Path(attempt["output_dir"])
    staging = Path(attempt["staging_dir"])
    return (
        (attempt_dir / ATTEMPT_VERIFIED_FILENAME).is_file()
        and output.exists()
        and not staging.exists()
    )


def _staging_directory_identity(staging: Path) -> tuple[int, int]:
    try:
        observed = os.lstat(staging)
    except OSError as exc:
        raise ReadinessBlocked(
            "no_go_artifact_binding: runner-owned staging identity is unavailable"
        ) from exc
    if not stat.S_ISDIR(observed.st_mode):
        raise ReadinessBlocked(
            "no_go_artifact_binding: runner-owned staging is not a directory"
        )
    return observed.st_dev, observed.st_ino


def _remove_owned_staging(
    staging: Path,
    *,
    expected_staging: Path,
    owned_identity: tuple[int, int] | None,
) -> None:
    if staging != expected_staging:
        raise ReadinessBlocked(
            "no_go_artifact_binding: runner-owned staging path changed"
        )
    if not os.path.lexists(staging):
        return
    if owned_identity is None:
        raise ReadinessBlocked(
            "no_go_artifact_binding: runner-owned staging identity was not recorded"
        )
    quarantine = staging.parent / (
        f"{staging.name}.{secrets.token_hex(32)}.cleanup"
    )
    if os.path.lexists(quarantine):
        raise ReadinessBlocked(
            "no_go_artifact_binding: staging cleanup quarantine already exists"
        )
    try:
        os.rename(staging, quarantine)
    except OSError as exc:
        raise ReadinessBlocked(
            "no_go_artifact_binding: runner-owned staging quarantine failed: "
            f"{exc}"
        ) from exc

    def restore_quarantine() -> None:
        if os.path.lexists(staging):
            raise ReadinessBlocked(
                "no_go_artifact_binding: staging quarantine restore path is occupied"
            )
        try:
            os.rename(quarantine, staging)
        except OSError as exc:
            raise ReadinessBlocked(
                "no_go_artifact_binding: staging quarantine restore failed: "
                f"{exc}"
            ) from exc
        if os.path.lexists(quarantine) or not os.path.lexists(staging):
            raise ReadinessBlocked(
                "no_go_artifact_binding: staging quarantine restore is incomplete"
            )

    try:
        quarantined_identity = _staging_directory_identity(quarantine)
    except BaseException as identity_exc:
        try:
            restore_quarantine()
        except BaseException as restore_exc:
            raise ReadinessBlocked(
                "no_go_artifact_binding: staging quarantine identity failed and "
                f"restore failed: {identity_exc}; {restore_exc}"
            ) from restore_exc
        raise
    if quarantined_identity != owned_identity:
        try:
            restore_quarantine()
        except BaseException as restore_exc:
            raise ReadinessBlocked(
                "no_go_artifact_binding: runner-owned staging identity changed and "
                f"restore failed: {restore_exc}"
            ) from restore_exc
        raise ReadinessBlocked(
            "no_go_artifact_binding: runner-owned staging identity changed"
        )
    try:
        shutil.rmtree(quarantine)
    except OSError as exc:
        try:
            restore_quarantine()
        except BaseException as restore_exc:
            raise ReadinessBlocked(
                "no_go_artifact_binding: runner-owned staging removal and restore "
                f"failed: {exc}; {restore_exc}"
            ) from restore_exc
        raise ReadinessBlocked(
            "no_go_artifact_binding: runner-owned staging removal failed: "
            f"{exc}"
        ) from exc
    if os.path.lexists(quarantine):
        raise ReadinessBlocked(
            "no_go_artifact_binding: staging cleanup quarantine remains"
        )
    if os.path.lexists(staging):
        raise ReadinessBlocked(
            "no_go_artifact_binding: staging path was replaced during cleanup"
        )


def _staging_cleanup_failure(
    original_error: BaseException, cleanup_error: BaseException
) -> ReadinessBlocked:
    original = str(original_error)[-800:]
    cleanup = str(cleanup_error)[-800:]
    failure = ReadinessBlocked(
        "no_go_artifact_binding: runner-owned staging cleanup failed: "
        f"{type(cleanup_error).__name__}: {cleanup}; original failure: "
        f"{type(original_error).__name__}: {original}"
    )
    if hasattr(failure, "add_note"):
        failure.add_note(f"original failure: {original_error}")
        failure.add_note(f"staging cleanup failure: {cleanup_error}")
    return failure


def _stream_file_binding(path: Path, label: str) -> dict[str, Any]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            for payload in iter(lambda: handle.read(1024 * 1024), b""):
                size += len(payload)
                digest.update(payload)
    except OSError as exc:
        raise ReadinessBlocked(f"{label} cannot be read") from exc
    return {"sha256": digest.hexdigest(), "size_bytes": size}


def _validate_publication_bindings(
    value: object, label: str
) -> dict[str, dict[str, Any]]:
    bindings = _mapping(value, label)
    _exact_keys(bindings, set(PUBLICATION_FILENAMES), label)
    normalized: dict[str, dict[str, Any]] = {}
    for name in PUBLICATION_FILENAMES:
        binding = _mapping(bindings[name], f"{label} {name}")
        _exact_keys(binding, {"sha256", "size_bytes"}, f"{label} {name}")
        digest = _digest(binding["sha256"], f"{label} {name} digest")
        size = _positive_int(binding["size_bytes"], f"{label} {name} size")
        ceiling = (
            MAX_CANDIDATE_STORED_BYTES
            if name == CANDIDATE_INVENTORY_FILENAME
            else MAX_REPORT_ARTIFACT_BYTES
        )
        if size > ceiling:
            raise ReadinessBlocked(f"{label} {name} exceeds byte ceiling")
        normalized[name] = {"sha256": digest, "size_bytes": size}
    return normalized


def _observe_publication_bindings(
    directory: Path, label: str
) -> dict[str, dict[str, Any]]:
    try:
        paths = list(directory.iterdir())
    except OSError as exc:
        raise ReadinessBlocked(f"{label} directory cannot be read") from exc
    if (
        {path.name for path in paths} != set(PUBLICATION_FILENAMES)
        or any(not path.is_file() or path.is_symlink() for path in paths)
    ):
        raise ReadinessBlocked(f"{label} closure mismatch")
    return {
        name: _stream_file_binding(directory / name, f"{label} {name}")
        for name in PUBLICATION_FILENAMES
    }


def _remove_sealed_snapshot(sealed: Path) -> None:
    if not sealed.exists():
        return
    if not sealed.is_dir() or sealed.is_symlink():
        raise ReadinessBlocked(
            "no_go_artifact_binding: sealed snapshot path is not a directory"
        )
    try:
        shutil.rmtree(sealed)
    except OSError as exc:
        raise ReadinessBlocked(
            "no_go_artifact_binding: sealed snapshot cleanup failed"
        ) from exc
    if sealed.exists():
        raise ReadinessBlocked(
            "no_go_artifact_binding: sealed snapshot remains after cleanup"
        )


def _seal_verified_staging(
    staging: Path,
    output: Path,
    *,
    publication_bindings: Mapping[str, Any],
    sealed_path: Path,
    owned_staging_identity: tuple[int, int],
) -> Path:
    if _staging_directory_identity(staging) != owned_staging_identity:
        raise ReadinessBlocked(
            "no_go_artifact_binding: runner-owned staging identity changed before sealing"
        )
    expected = _validate_publication_bindings(
        publication_bindings, "verified publication bindings"
    )
    observed_names = _observe_publication_bindings(
        staging, "verified staging publication"
    )
    if observed_names != expected:
        raise ReadinessBlocked(
            "no_go_artifact_binding: staging bytes changed after verification"
        )
    sealed = sealed_path.resolve()
    sealed_name = re.fullmatch(
        rf"\.{re.escape(output.name)}\.([0-9a-f]{{64}})\.sealed",
        sealed.name,
    )
    if sealed.parent != output.parent or sealed_name is None:
        raise ReadinessBlocked(
            "no_go_artifact_binding: sealed snapshot identity is invalid"
        )
    try:
        try:
            sealed.mkdir()
            for name in PUBLICATION_FILENAMES:
                source = staging / name
                destination = sealed / name
                digest = hashlib.sha256()
                size = 0
                with source.open("rb") as reader, destination.open("xb") as writer:
                    for payload in iter(lambda: reader.read(1024 * 1024), b""):
                        size += len(payload)
                        digest.update(payload)
                        writer.write(payload)
                    writer.flush()
                    os.fsync(writer.fileno())
                if {
                    "sha256": digest.hexdigest(),
                    "size_bytes": size,
                } != expected[name]:
                    raise ReadinessBlocked(
                        "no_go_artifact_binding: staging changed while sealing"
                    )
        except OSError as exc:
            raise ReadinessBlocked(
                "no_go_artifact_binding: cannot seal verified staging"
            ) from exc
        if _observe_publication_bindings(sealed, "sealed publication") != expected:
            raise ReadinessBlocked(
                "no_go_artifact_binding: sealed publication binding mismatch"
            )
        _remove_owned_staging(
            staging,
            expected_staging=staging,
            owned_identity=owned_staging_identity,
        )
        return sealed
    except BaseException as exc:
        try:
            _remove_sealed_snapshot(sealed)
        except BaseException as cleanup_exc:
            if hasattr(exc, "add_note"):
                exc.add_note(f"sealed cleanup also failed: {cleanup_exc}")
        raise


def _recover_installed_publication(
    attempt: Mapping[str, Any],
) -> dict[str, Any]:
    started = _mapping(attempt.get("started"), "attempt start")
    output = Path(attempt["output_dir"])
    staging = Path(attempt["staging_dir"])
    if not output.is_dir() or staging.exists():
        raise ReadinessBlocked("installed publication boundary is incomplete")

    receipt = _mapping(
        _strict_json_bytes(
            (
                Path(attempt["attempt_dir"]) / ATTEMPT_VERIFIED_FILENAME
            ).read_bytes(),
            "readiness verification receipt",
        ),
        "readiness verification receipt",
    )
    _exact_keys(
        receipt,
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
    receipt_body = {
        key: value
        for key, value in receipt.items()
        if key != "verification_receipt_sha256"
    }
    if receipt["verification_receipt_sha256"] != canonical_digest(receipt_body):
        raise ReadinessBlocked("readiness verification receipt digest mismatch")
    if (
        receipt["attempt_sha256"] != started["attempt_sha256"]
        or receipt["intended_output_dir"] != str(output)
        or receipt["schema_version"]
        != "noncombat-cross-fitted-empirical-successor-readiness-attempt-verified-v1"
        or receipt["source_commit"] != started["source_commit"]
        or receipt["staging_dir"] != str(staging)
        or receipt["status"] != "staging_independently_verified"
    ):
        raise ReadinessBlocked("readiness verification receipt identity mismatch")

    publication_bindings = _validate_publication_bindings(
        receipt["publication_bindings"], "receipt publication bindings"
    )
    if (
        _observe_publication_bindings(output, "installed publication")
        != publication_bindings
    ):
        raise ReadinessBlocked("installed publication binding mismatch")
    report = validate_report(
        _strict_json_bytes(
            (output / REPORT_FILENAME).read_bytes(), "installed readiness report"
        )
    )
    candidate_binding = _artifact_binding(
        report["candidate_artifact_binding"],
        expected_path=CANDIDATE_INVENTORY_FILENAME,
    )
    verification = _mapping(receipt["verification"], "verification summary")
    _exact_keys(
        verification,
        {
            "candidate_inventory_sha256",
            "decision",
            "independent_inventory_sha256",
            "proposal_eligible",
            "readiness_identity_sha256",
            "source_commit",
            "status",
        },
        "verification summary",
    )
    expected_verification = {
        "candidate_inventory_sha256": publication_bindings[
            CANDIDATE_INVENTORY_FILENAME
        ]["sha256"],
        "decision": report["decision"]["status"],
        "independent_inventory_sha256": _digest(
            verification.get("independent_inventory_sha256"),
            "independent inventory digest",
        ),
        "proposal_eligible": report["eligibility"][
            "empirical_successor_registration_proposal_eligible"
        ],
        "readiness_identity_sha256": report["readiness_identity_sha256"],
        "source_commit": started["source_commit"],
        "status": "verified",
    }
    if (
        verification != expected_verification
        or report["decision"]["status"] != "go"
        or report["audit_id"] != started["audit_id"]
        or candidate_binding["sha256"]
        != publication_bindings[CANDIDATE_INVENTORY_FILENAME]["sha256"]
        or candidate_binding["size_bytes"]
        != publication_bindings[CANDIDATE_INVENTORY_FILENAME]["size_bytes"]
    ):
        raise ReadinessBlocked("installed publication differs from verified staging")
    return {
        "audit_id": started["audit_id"],
        "authority": readiness_authority(),
        "decision": report["decision"],
        "output_dir": str(output),
        "schema_version": (
            "noncombat-cross-fitted-empirical-successor-readiness-run-v1"
        ),
        "source_commit": started["source_commit"],
        "verification": verification,
    }


class _BlockedRehearsalImport(importlib.abc.MetaPathFinder):
    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: object | None = None,
    ) -> None:
        del path, target
        if any(
            fullname == prefix or fullname.startswith(prefix + ".")
            for prefix in BLOCKED_REHEARSAL_IMPORTS
        ):
            raise ImportError(f"source-only rehearsal blocked import: {fullname}")
        return None


def _synthetic_execution_identity(
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


def _named_tree_binding(root: Path, *, excluded: set[str]) -> dict[str, Any]:
    rows: list[tuple[str, bytes]] = []
    for candidate in sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix(),
    ):
        relative = candidate.relative_to(root).as_posix()
        if relative in excluded:
            continue
        rows.append((relative, candidate.read_bytes()))
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


def _emit_child_event(value: Mapping[str, Any]) -> None:
    sys.stdout.buffer.write(canonical_json_bytes(value))
    sys.stdout.buffer.flush()


def _stage_elapsed(started: float) -> tuple[float, str]:
    elapsed = max(0.0, time.perf_counter() - started)
    return elapsed, f"{elapsed:.3f}"


def _rehearsal_child(
    *, repo_root: Path, source_commit: str, scratch_root: Path
) -> int:
    root = repo_root.resolve()
    commit = _commit(source_commit)
    scratch = scratch_root.resolve()
    if scratch.exists():
        raise ReadinessBlocked("source-only rehearsal scratch root already exists")
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.mkdir()
    output = scratch / "control"

    preloaded = [
        name
        for name in sys.modules
        if any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in BLOCKED_REHEARSAL_IMPORTS
        )
    ]
    if preloaded:
        raise ReadinessBlocked(
            "source-only rehearsal started with a blocked module preloaded"
        )
    blocker = _BlockedRehearsalImport()
    sys.meta_path.insert(0, blocker)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    stage_results: list[dict[str, str]] = []
    validation_counts: dict[str, int] = {}
    lease: Any | None = None
    original_validate: Callable[..., Any] | None = None
    try:
        _emit_child_event({"kind": "stage_started", "stage": "context_setup"})
        stage_started = time.perf_counter()
        control = __import__(
            "analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment",
            fromlist=["validate_registration"],
        )
        consumed_payload = _git_blob(root, commit, CONSUMED_REGISTRATION_PATH)
        if len(consumed_payload) != CONSUMED_REGISTRATION_SIZE_BYTES:
            raise ReadinessBlocked("actual-scale registration byte size drifted")
        registration = _strict_json_bytes(
            consumed_payload, "consumed actual-scale registration"
        )
        if not isinstance(registration, dict):
            raise ReadinessBlocked("consumed registration is not an object")
        registration = copy.deepcopy(registration)
        registration["registration_id"] = (
            "source-only-readiness-rehearsal-" + commit[:12]
        )
        registration["output_root"] = output.as_posix()
        identity = _synthetic_execution_identity(registration, commit)
        original_validate = control.validate_registration
        validation_calls = 0

        def counted_validate(value: Mapping[str, Any]) -> dict[str, Any]:
            nonlocal validation_calls
            validation_calls += 1
            return original_validate(value)

        control.validate_registration = counted_validate
        context = control._build_validated_execution_context(
            registration, identity, output
        )
        lease = control.ExecutionLease(output, identity=identity)
        lease.__enter__()
        control._atomic_write_once(
            output / control.REGISTRATION_FILENAME,
            control.canonical_json_bytes(registration),
        )
        control.initialize_access_journal(
            output,
            registration=context,
            identity=identity,
            lease=lease,
        )
        control.initialize_resource_ledger(
            output,
            registration=context,
            identity=identity,
            lease=lease,
        )
        control.publish_bootstrap(
            output,
            registration=context,
            identity=identity,
            lease=lease,
            runtime_checkpoint_payload={
                "coordinates": {
                    "completed_decisions": 0,
                    "completed_episodes": 0,
                    "next_chunk_index": 0,
                    "optimizer_updates": 0,
                },
                "kind": "source-only-synthetic-control-bootstrap",
            },
        )
        validation_counts["after_setup"] = validation_calls
        elapsed, elapsed_text = _stage_elapsed(stage_started)
        if elapsed > float(STAGE_CEILING_SECONDS):
            raise ReadinessBlocked("context setup exceeded its fixed ceiling")
        stage = {
            "ceiling_seconds": format(STAGE_CEILING_SECONDS, "f"),
            "elapsed_seconds": elapsed_text,
            "name": "context_setup",
            "status": "passed",
        }
        stage_results.append(stage)
        _emit_child_event(
            {"elapsed_seconds": elapsed_text, "kind": "stage_completed", "stage": "context_setup"}
        )

        _emit_child_event({"kind": "stage_started", "stage": "control_chunk"})
        stage_started = time.perf_counter()
        for seed in registration["schedule"]["chunks"][0]:
            control.begin_environment_access(
                output,
                registration=context,
                identity=identity,
                lease=lease,
                chunk_index=0,
                seed=seed,
                attempt_ordinal=0,
            )
            control.complete_environment_access(
                output,
                registration=context,
                identity=identity,
                lease=lease,
                status="completed",
            )
        validation_counts["after_chunk"] = validation_calls
        elapsed, elapsed_text = _stage_elapsed(stage_started)
        if elapsed > float(STAGE_CEILING_SECONDS):
            raise ReadinessBlocked("control chunk exceeded its fixed ceiling")
        stage = {
            "ceiling_seconds": format(STAGE_CEILING_SECONDS, "f"),
            "elapsed_seconds": elapsed_text,
            "name": "control_chunk",
            "status": "passed",
        }
        stage_results.append(stage)
        _emit_child_event(
            {"elapsed_seconds": elapsed_text, "kind": "stage_completed", "stage": "control_chunk"}
        )

        _emit_child_event({"kind": "stage_started", "stage": "terminal_closeout"})
        stage_started = time.perf_counter()
        ledger = control.load_resource_ledger(output, identity=identity)
        control.advance_resource_ledger(
            output,
            registration=context,
            identity=identity,
            lease=lease,
            resources=ledger["resources"],
            reason="terminal-attempt-charge",
        )
        intent = control.publish_terminal_intent(
            output,
            registration=context,
            identity=identity,
            lease=lease,
            verdict="experiment_failed_after_seed_access",
            details={
                "reason": "source_only_synthetic_control_rehearsal_complete",
                "source_only": True,
                "synthetic_control_positions": CHUNK_SIZE,
            },
        )
        bundle = control.publish_terminal_bundle(
            output,
            registration=context,
            identity=identity,
            lease=lease,
            terminal_intent=intent,
        )
        if control.validate_terminal_bundle(
            output, registration=context, identity=identity
        ) != bundle:
            raise ReadinessBlocked("producer terminal verification differed")
        validation_counts["after_closeout"] = validation_calls
        elapsed, elapsed_text = _stage_elapsed(stage_started)
        if elapsed > float(STAGE_CEILING_SECONDS):
            raise ReadinessBlocked("terminal closeout exceeded its fixed ceiling")
        stage = {
            "ceiling_seconds": format(STAGE_CEILING_SECONDS, "f"),
            "elapsed_seconds": elapsed_text,
            "name": "terminal_closeout",
            "status": "passed",
        }
        stage_results.append(stage)
        _emit_child_event(
            {"elapsed_seconds": elapsed_text, "kind": "stage_completed", "stage": "terminal_closeout"}
        )
    finally:
        if lease is not None:
            lease.__exit__(*sys.exc_info())
        if "control" in locals() and original_validate is not None:
            control.validate_registration = original_validate
        if blocker in sys.meta_path:
            sys.meta_path.remove(blocker)

    raw_result = {
        "blocked_imports": list(BLOCKED_REHEARSAL_IMPORTS),
        "context_validation_count": validation_counts,
        "empirical_operations": _empirical_operations(),
        "producer_verified": True,
        "registration_size_bytes": len(consumed_payload),
        "schema_version": (
            "noncombat-cross-fitted-readiness-rehearsal-child-v1"
        ),
        "scratch_artifacts": _named_tree_binding(
            output, excluded={".execution.lease"}
        ),
        "stage_results": stage_results,
        "synthetic_control_positions": CHUNK_SIZE,
        "terminal_verdict": bundle["terminal"]["verdict"],
    }
    (scratch / "child_result.json").write_bytes(canonical_json_bytes(raw_result))
    _emit_child_event({"kind": "rehearsal_result", "result": raw_result})
    return 0


def _stream_reader(
    stream: Any, messages: queue.Queue[tuple[str, str | None]], label: str
) -> None:
    try:
        for line in stream:
            messages.put((label, line))
    finally:
        messages.put((label, None))


def _spawn_process_tree(
    command: Sequence[str], **kwargs: Any
) -> subprocess.Popen[Any]:
    options = dict(kwargs)
    start_event: _WindowsProcessStartEvent | None = None
    if _IS_WINDOWS:
        options["creationflags"] = options.get("creationflags", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
        start_event = _WindowsProcessStartEvent()
        environment = dict(options.get("env") or os.environ)
        environment[_PROCESS_JOB_EVENT_ENV] = start_event.name
        options["env"] = environment
    else:
        options["start_new_session"] = True
    try:
        process = subprocess.Popen(list(command), **options)
        if _IS_WINDOWS:
            process._readiness_job = _WindowsKillOnCloseJob(process)
            process._readiness_start_event = start_event
            start_event.release()
        return process
    except BaseException:
        candidate = locals().get("process")
        if candidate is not None:
            job = getattr(candidate, "_readiness_job", None)
            try:
                if job is not None:
                    job.terminate_and_wait(10)
                elif candidate.poll() is None:
                    candidate.kill()
                candidate.wait(timeout=10)
            except (ReadinessBlocked, subprocess.TimeoutExpired):
                if candidate.poll() is None:
                    candidate.kill()
            finally:
                if job is not None:
                    job.close()
                    candidate._readiness_job = None
        if start_event is not None:
            start_event.close()
        raise


def _close_process_start_event(process: subprocess.Popen[Any]) -> None:
    start_event = getattr(process, "_readiness_start_event", None)
    if start_event is None:
        return
    try:
        start_event.close()
    finally:
        process._readiness_start_event = None


def _terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    if getattr(process, "_readiness_tree_confirmed", False):
        if process.poll() is None:
            raise ReadinessBlocked(
                "process tree confirmation exists while child is still running"
            )
        return
    pid = getattr(process, "pid", None)
    tree_confirmed = False
    job = getattr(process, "_readiness_job", None)
    if _IS_WINDOWS and job is not None:
        try:
            job.terminate_and_wait(10)
            tree_confirmed = True
        finally:
            try:
                job.close()
            finally:
                process._readiness_job = None
                _close_process_start_event(process)
    elif _IS_WINDOWS and isinstance(pid, int) and pid > 0:
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                check=False,
                capture_output=True,
                timeout=15,
            )
            tree_confirmed = result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            tree_confirmed = False
    elif isinstance(pid, int) and pid > 0:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            tree_confirmed = True
        except (PermissionError, OSError):
            tree_confirmed = False
        else:
            deadline = time.monotonic() + 10
            while True:
                try:
                    os.killpg(pid, 0)
                except ProcessLookupError:
                    tree_confirmed = True
                    break
                except (PermissionError, OSError):
                    break
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.01)
    if process.poll() is None:
        process.kill()
    try:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            if process.poll() is None:
                process.kill()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired as final_exc:
                raise ReadinessBlocked(
                    "process tree termination could not confirm child exit"
                ) from final_exc
    finally:
        _close_process_start_event(process)
    if process.poll() is None:
        raise ReadinessBlocked("process tree termination did not confirm child exit")
    if not tree_confirmed:
        raise ReadinessBlocked(
            "process tree termination could not confirm descendant exit"
        )
    process._readiness_tree_confirmed = True


def _terminate_rehearsal_child(process: subprocess.Popen[str]) -> None:
    _terminate_process_tree(process)


def _run_supervised_command(
    command: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: float,
    timeout_message: str,
) -> subprocess.CompletedProcess[bytes]:
    process = _spawn_process_tree(
        command,
        cwd=cwd,
        env=dict(environment),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        raise ReadinessBlocked(timeout_message) from exc
    except BaseException:
        _terminate_process_tree(process)
        raise
    _terminate_process_tree(process)
    return subprocess.CompletedProcess(
        list(command), process.returncode, stdout=stdout, stderr=stderr
    )


def _run_independent_verifier(
    command: Sequence[str], *, cwd: Path, environment: Mapping[str, str]
) -> subprocess.CompletedProcess[bytes]:
    return _run_supervised_command(
        command,
        cwd=cwd,
        environment=environment,
        timeout_seconds=INDEPENDENT_VERIFIER_CEILING_SECONDS,
        timeout_message=(
            "no_go_artifact_binding: independent verifier timeout"
        ),
    )


def _monitor_rehearsal_child_impl(
    process: subprocess.Popen[str],
) -> dict[str, Any]:
    if process.stdout is None or process.stderr is None:
        raise ReadinessBlocked("rehearsal child pipes are unavailable")
    messages: queue.Queue[tuple[str, str | None]] = queue.Queue()
    stdout_thread = threading.Thread(
        target=_stream_reader,
        args=(process.stdout, messages, "stdout"),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_stream_reader,
        args=(process.stderr, messages, "stderr"),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    expected_stage = 0
    active_stage: str | None = None
    deadline = time.monotonic() + 30.0
    stderr_parts: list[str] = []
    final_result: dict[str, Any] | None = None
    stdout_eof = False
    while final_result is None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            _terminate_rehearsal_child(process)
            stage = active_stage or "stage_transition"
            raise ReadinessBlocked(
                f"no_go_rehearsal_boundary: {stage} watchdog expired"
            )
        try:
            label, line = messages.get(timeout=remaining)
        except queue.Empty as exc:
            _terminate_rehearsal_child(process)
            stage = active_stage or "stage_transition"
            raise ReadinessBlocked(
                f"no_go_rehearsal_boundary: {stage} watchdog expired"
            ) from exc
        if label == "stderr":
            if line is not None and sum(map(len, stderr_parts)) < 65_536:
                stderr_parts.append(line)
            continue
        if line is None:
            stdout_eof = True
            break
        try:
            event = _strict_json_bytes(line.encode("utf-8"), "child event")
        except ReadinessBlocked:
            _terminate_rehearsal_child(process)
            raise
        if not isinstance(event, dict):
            _terminate_rehearsal_child(process)
            raise ReadinessBlocked("rehearsal child event is not an object")
        kind = event.get("kind")
        if kind == "stage_started":
            if (
                active_stage is not None
                or expected_stage >= len(REHEARSAL_STAGE_ORDER)
                or event != {
                    "kind": "stage_started",
                    "stage": REHEARSAL_STAGE_ORDER[expected_stage],
                }
            ):
                _terminate_rehearsal_child(process)
                raise ReadinessBlocked("rehearsal stage start order mismatch")
            active_stage = REHEARSAL_STAGE_ORDER[expected_stage]
            deadline = time.monotonic() + float(STAGE_CEILING_SECONDS)
        elif kind == "stage_completed":
            if (
                active_stage is None
                or event.get("stage") != active_stage
                or set(event) != {"elapsed_seconds", "kind", "stage"}
            ):
                _terminate_rehearsal_child(process)
                raise ReadinessBlocked("rehearsal stage completion order mismatch")
            elapsed = _decimal_string(event["elapsed_seconds"], "child stage elapsed")
            if elapsed > STAGE_CEILING_SECONDS:
                _terminate_rehearsal_child(process)
                raise ReadinessBlocked("no_go_rehearsal_boundary: stage exceeded ceiling")
            expected_stage += 1
            active_stage = None
            deadline = time.monotonic() + 30.0
        elif kind == "rehearsal_result":
            if (
                active_stage is not None
                or expected_stage != len(REHEARSAL_STAGE_ORDER)
                or set(event) != {"kind", "result"}
            ):
                _terminate_rehearsal_child(process)
                raise ReadinessBlocked("rehearsal result arrived before closeout")
            final_result = _mapping(event["result"], "child rehearsal result")
        else:
            _terminate_rehearsal_child(process)
            raise ReadinessBlocked("unknown rehearsal child event")
    if final_result is None:
        _terminate_rehearsal_child(process)
        detail = "".join(stderr_parts).strip()[-2000:]
        raise ReadinessBlocked(
            "no_go_rehearsal_boundary: child exited before result"
            + (f": {detail}" if detail else "")
        )
    try:
        return_code = process.wait(timeout=10)
    except subprocess.TimeoutExpired as exc:
        _terminate_rehearsal_child(process)
        raise ReadinessBlocked("rehearsal child did not exit after result") from exc
    _terminate_rehearsal_child(process)
    if return_code != 0 or stdout_eof and final_result is None:
        detail = "".join(stderr_parts).strip()[-2000:]
        raise ReadinessBlocked(
            f"rehearsal child failed with exit code {return_code}: {detail}"
        )
    return final_result


def _monitor_rehearsal_child(
    process: subprocess.Popen[str],
) -> dict[str, Any]:
    try:
        return _monitor_rehearsal_child_impl(process)
    except BaseException:
        _terminate_rehearsal_child(process)
        raise


def run_actual_scale_rehearsal(
    repo_root: Path | str,
    *,
    source_commit: str,
    scratch_root: Path | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = _commit(source_commit)
    scratch = Path(scratch_root).resolve()
    if scratch.exists():
        raise ReadinessBlocked("source-only rehearsal scratch root already exists")
    script = Path(__file__).resolve()
    command = [
        sys.executable,
        "-I",
        str(script),
        "_rehearse-child",
        "--repo-root",
        str(root),
        "--source-commit",
        commit,
        "--scratch-root",
        str(scratch),
    ]
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    process = _spawn_process_tree(
        command,
        cwd=root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="strict",
        bufsize=1,
    )
    child_result = _monitor_rehearsal_child(process)
    verifier_script = root / PurePosixPath(READINESS_VERIFIER_SOURCE_PATH)
    verification = _run_supervised_command(
        [
            sys.executable,
            "-I",
            str(verifier_script),
            "_verify-rehearsal",
            "--repo-root",
            str(root),
            "--source-commit",
            commit,
            "--scratch-root",
            str(scratch),
            "--expected-child-pid",
            str(process.pid),
        ],
        cwd=root,
        environment=environment,
        timeout_seconds=float(STAGE_CEILING_SECONDS),
        timeout_message=(
            "no_go_rehearsal_boundary: independent scratch verifier timeout"
        ),
    )
    if verification.returncode != 0:
        detail = verification.stderr.decode("utf-8", errors="replace").strip()[-2000:]
        gate = _scratch_verifier_failure_gate(verification.stderr)
        raise ReadinessBlocked(
            f"no_go_{gate}: independent scratch verification failed"
            + (f": {detail}" if detail else "")
        )
    verified = _strict_json_bytes(
        verification.stdout, "independent rehearsal verification"
    )
    if not isinstance(verified, dict):
        raise ReadinessBlocked("independent rehearsal result is not an object")
    expected_child_fields = {
        key: value
        for key, value in verified.items()
        if key not in {"child_exit_code", "status", "verified"}
    }
    expected_child_fields["producer_verified"] = True
    expected_child_fields["schema_version"] = (
        "noncombat-cross-fitted-readiness-rehearsal-child-v1"
    )
    if child_result != expected_child_fields:
        raise ReadinessBlocked("independent rehearsal result differs from child witness")
    summary = {
        key: value
        for key, value in verified.items()
        if key not in {"producer_verified", "schema_version"}
    }
    summary = validate_rehearsal_summary(summary)
    shutil.rmtree(scratch)
    if scratch.exists():
        raise ReadinessBlocked("verified rehearsal scratch cleanup failed")
    return summary


def run_readiness_audit(
    *,
    repo_root: Path | str,
    source_commit: str,
    scratch_root: Path | str,
    output_dir: Path | str,
    audit_id: str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    commit = _commit(source_commit)
    scratch = Path(scratch_root).resolve()
    output = Path(output_dir).resolve()
    root_text = str(root)
    if not sys.path or sys.path[0] != root_text:
        sys.path.insert(0, root_text)
    attempt: dict[str, Any] | None = None
    expected_staging = output.parent / f".{output.name}.{commit}.staging"
    staging = expected_staging
    staging_owned = False
    staging_identity: tuple[int, int] | None = None
    sealed: Path | None = None
    active_gate = "source_binding"
    try:
        attempt = _claim_readiness_attempt(
            root,
            source_commit=commit,
            audit_id=audit_id,
            scratch_root=scratch,
            output_dir=output,
        )
        staging = Path(attempt["staging_dir"])
        if scratch.exists():
            raise ReadinessBlocked(
                "no_go_source_binding: rehearsal scratch root already exists"
            )
        if os.path.lexists(output) or os.path.lexists(staging):
            raise ReadinessBlocked(
                "no_go_source_binding: publication or staging root already exists"
            )
        if scratch == output or scratch in output.parents or output in scratch.parents:
            raise ReadinessBlocked(
                "no_go_source_binding: scratch and publication roots are not isolated"
            )

        source = observe_source_binding(root, source_commit=commit)
        candidate, evidence = build_candidate_from_git(
            root,
            source_binding=source,
        )
        active_gate = "cohort_not_fresh"
        if candidate["disjointness"]["status"] != "passed":
            raise ReadinessBlocked(
                "no_go_cohort_not_fresh: candidate intersects consumed cohort"
            )
        active_gate = "rehearsal_boundary"
        rehearsal = run_actual_scale_rehearsal(
            root,
            source_commit=commit,
            scratch_root=scratch,
        )
        active_gate = "budget_binding"
        budget = build_budget_evidence(evidence["historical_throughput"])
        active_gate = "artifact_binding"
        output.parent.mkdir(parents=True, exist_ok=True)
        staging.mkdir()
        staging_owned = True
        staging_identity = _staging_directory_identity(staging)
        candidate_binding = _write_canonical_gzip_file(
            staging / CANDIDATE_INVENTORY_FILENAME,
            candidate,
        )
        report = _assemble_report(
            audit_id=audit_id,
            source=validate_source_binding(source),
            candidate=candidate,
            candidate_binding=_artifact_binding(
                candidate_binding,
                expected_path=CANDIDATE_INVENTORY_FILENAME,
            ),
            rehearsal_summary=validate_rehearsal_summary(rehearsal),
            budget_evidence=validate_budget_evidence(budget),
        )
        report = validate_report(report)
        _write_canonical_once(staging / REPORT_FILENAME, report)
        _write_bytes_once(
            staging / REPORT_MARKDOWN_FILENAME,
            render_markdown(report).encode("utf-8"),
        )
        if {path.name for path in staging.iterdir()} != set(PUBLICATION_FILENAMES):
            raise ReadinessBlocked(
                "no_go_artifact_binding: staged publication closure mismatch"
            )
        publication_bindings = _observe_publication_bindings(
            staging, "staged publication"
        )

        expected_inventory_sha256 = candidate["candidate_schedule"][
            "inventory_sha256"
        ]
        del candidate, evidence
        gc.collect()

        verifier_script = root / PurePosixPath(READINESS_VERIFIER_SOURCE_PATH)
        environment = dict(os.environ)
        environment.pop("PYTHONPATH", None)
        verification = _run_independent_verifier(
            [
                sys.executable,
                "-I",
                str(verifier_script),
                "--repo-root",
                str(root),
                "--output-dir",
                str(staging),
            ],
            cwd=root,
            environment=environment,
        )
        if verification.returncode != 0:
            detail = verification.stderr.decode(
                "utf-8", errors="replace"
            ).strip()[-2000:]
            raise ReadinessBlocked(
                "no_go_artifact_binding: independent publication verification failed"
                + (f": {detail}" if detail else "")
            )
        verified = _strict_json_bytes(
            verification.stdout, "independent publication verification"
        )
        expected_verification = {
            "candidate_inventory_sha256": candidate_binding["sha256"],
            "decision": report["decision"]["status"],
            "independent_inventory_sha256": expected_inventory_sha256,
            "proposal_eligible": report["eligibility"][
                "empirical_successor_registration_proposal_eligible"
            ],
            "readiness_identity_sha256": report["readiness_identity_sha256"],
            "source_commit": commit,
            "status": "verified",
        }
        if verified != expected_verification:
            raise ReadinessBlocked(
                "no_go_artifact_binding: verifier summary differs from publication"
            )
        if report["decision"]["status"] != "go":
            raise ReadinessBlocked(report["decision"]["reason"])
        verification_body = {
            "attempt_sha256": attempt["started"]["attempt_sha256"],
            "intended_output_dir": str(output),
            "publication_bindings": publication_bindings,
            "schema_version": (
                "noncombat-cross-fitted-empirical-successor-readiness-attempt-verified-v1"
            ),
            "source_commit": commit,
            "staging_dir": str(staging),
            "status": "staging_independently_verified",
            "verification": verified,
        }
        verification_receipt = {
            **verification_body,
            "verification_receipt_sha256": canonical_digest(verification_body),
        }
        _write_canonical_once(
            Path(attempt["attempt_dir"]) / ATTEMPT_VERIFIED_FILENAME,
            verification_receipt,
        )
        sealed = output.parent / (
            f".{output.name}.{secrets.token_hex(32)}.sealed"
        )
        _seal_verified_staging(
            staging,
            output,
            publication_bindings=publication_bindings,
            sealed_path=sealed,
            owned_staging_identity=staging_identity,
        )
        try:
            os.replace(sealed, output)
        except BaseException as exc:
            try:
                _remove_sealed_snapshot(sealed)
            except BaseException as cleanup_exc:
                if hasattr(exc, "add_note"):
                    exc.add_note(f"sealed cleanup also failed: {cleanup_exc}")
            raise
        return {
            "audit_id": audit_id,
            "authority": readiness_authority(),
            "decision": report["decision"],
            "output_dir": str(output),
            "schema_version": (
                "noncombat-cross-fitted-empirical-successor-readiness-run-v1"
            ),
            "source_commit": commit,
            "verification": verified,
        }
    except ReadinessSourceConsumed:
        raise
    except ReadinessAttemptTerminal:
        raise
    except BaseException as exc:
        interrupted = exc if not isinstance(exc, Exception) else None
        if attempt is None:
            attempt = _recover_owned_readiness_attempt(
                root,
                source_commit=commit,
                audit_id=audit_id,
                scratch_root=scratch,
                output_dir=output,
            )
        if attempt is None:
            raise
        if sealed is not None and sealed.exists():
            try:
                _remove_sealed_snapshot(sealed)
            except BaseException as cleanup_exc:
                if hasattr(exc, "add_note"):
                    exc.add_note(f"sealed cleanup also failed: {cleanup_exc}")
        installed_boundary_crossed = _installed_publication_boundary_crossed(attempt)
        if installed_boundary_crossed:
            try:
                recovered = _recover_installed_publication(attempt)
            except BaseException as recovery_exc:
                exc = ReadinessBlocked(
                    "no_go_artifact_binding: installed publication recovery failed"
                )
                if hasattr(exc, "add_note"):
                    exc.add_note(str(recovery_exc))
                active_gate = "artifact_binding"
            else:
                if interrupted is not None:
                    raise interrupted
                return recovered
        if staging_owned and not installed_boundary_crossed:
            try:
                _remove_owned_staging(
                    staging,
                    expected_staging=expected_staging,
                    owned_identity=staging_identity,
                )
            except BaseException as cleanup_exc:
                exc = _staging_cleanup_failure(exc, cleanup_exc)
                active_gate = "artifact_binding"
        gate = _failure_gate(exc, active_gate)
        terminal = _terminalize_attempt_no_go(
            attempt,
            gate=gate,
            error=exc,
        )
        if interrupted is not None:
            raise interrupted
        raise ReadinessAttemptTerminal(terminal) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--scratch-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--audit-id", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _wait_for_windows_process_job_assignment()
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "_rehearse-child":
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--repo-root", type=Path, required=True)
        parser.add_argument("--source-commit", required=True)
        parser.add_argument("--scratch-root", type=Path, required=True)
        child = parser.parse_args(arguments[1:])
        try:
            return _rehearsal_child(
                repo_root=child.repo_root,
                source_commit=child.source_commit,
                scratch_root=child.scratch_root,
            )
        except BaseException as exc:
            sys.stderr.buffer.write(
                canonical_json_bytes(
                    {
                        "error": str(exc),
                        "status": "rehearsal_child_failed",
                        "type": type(exc).__name__,
                    }
                )
            )
            return 1
    try:
        audit = _build_parser().parse_args(arguments)
        result = run_readiness_audit(
            repo_root=audit.repo_root,
            source_commit=audit.source_commit,
            scratch_root=audit.scratch_root,
            output_dir=audit.output_dir,
            audit_id=audit.audit_id,
        )
    except ReadinessAttemptTerminal as exc:
        sys.stderr.buffer.write(canonical_json_bytes(exc.result))
        return 1
    except (ReadinessBlocked, OSError, subprocess.SubprocessError) as exc:
        sys.stderr.buffer.write(
            canonical_json_bytes(
                {
                    "error": str(exc),
                    "status": "readiness_failed",
                    "type": type(exc).__name__,
                }
            )
        )
        return 1
    sys.stdout.buffer.write(canonical_json_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
