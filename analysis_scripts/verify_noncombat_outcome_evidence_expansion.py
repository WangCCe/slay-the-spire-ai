"""Independently replay a registered non-combat outcome-evidence study."""

from __future__ import annotations

import os
import sys

_QUALIFICATION_REQUEST_OPTIONS = (
    "--qualification-request-source",
    "--qualification-request",
)
_QUALIFICATION_CLI_REQUESTED = any(
    argument == option or argument.startswith(f"{option}=")
    for argument in sys.argv[1:]
    for option in _QUALIFICATION_REQUEST_OPTIONS
)
if _QUALIFICATION_CLI_REQUESTED:
    sys.dont_write_bytecode = True
    sys.pycache_prefix = os.path.join(
        os.devnull,
        "sts-qualification-pycache",
    )
    if __name__ == "__main__" and (
        not sys.flags.isolated or not sys.flags.no_site
    ):
        sys.stderr.write(
            "qualification verifier requires isolated no-site Python startup "
            "(-I -S)\n"
        )
        raise SystemExit(2)

import argparse
import base64
import fnmatch
import hashlib
import importlib.machinery
import json
import math
import re
import stat
import subprocess
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
else:
    repo_root = str(Path(__file__).resolve().parents[1])


def _qualification_install_source_only_repo_imports(repo_root_value: str) -> None:
    lexical_root = os.path.normcase(os.path.abspath(repo_root_value))

    def is_repo_path(path_value: object) -> bool:
        try:
            lexical_path = os.path.normcase(
                os.path.abspath(os.fspath(path_value))
            )
            return os.path.commonpath((lexical_root, lexical_path)) == lexical_root
        except (OSError, TypeError, ValueError):
            return False

    class NoFollowSourceLoader(importlib.machinery.SourceFileLoader):
        def get_data(self, path_value: str) -> bytes:
            lexical_path = os.path.abspath(path_value)
            if not is_repo_path(lexical_path):
                raise OSError(
                    "qualification repository loader refuses bytecode cache"
                )
            current_path = Path(Path(lexical_path).anchor)
            for part in Path(lexical_path).parts[1:]:
                current_path /= part
                metadata = current_path.lstat()
                file_attributes = getattr(metadata, "st_file_attributes", 0)
                reparse_flag = getattr(
                    stat,
                    "FILE_ATTRIBUTE_REPARSE_POINT",
                    0,
                )
                if stat.S_ISLNK(metadata.st_mode) or bool(
                    file_attributes & reparse_flag
                ):
                    raise ImportError(
                        "qualification repository source contains a symbolic "
                        f"link or reparse point: {current_path}"
                    )
            if not stat.S_ISREG(current_path.lstat().st_mode):
                raise ImportError(
                    "qualification repository source is not a regular file: "
                    f"{current_path}"
                )
            return super().get_data(lexical_path)

    def source_only_path_hook(path_value: str):
        if not is_repo_path(path_value):
            raise ImportError
        return importlib.machinery.FileFinder(
            path_value,
            (
                NoFollowSourceLoader,
                importlib.machinery.SOURCE_SUFFIXES,
            ),
        )

    sys.path_hooks.insert(0, source_only_path_hook)
    for cached_path in tuple(sys.path_importer_cache):
        if is_repo_path(cached_path):
            sys.path_importer_cache.pop(cached_path, None)


if _QUALIFICATION_CLI_REQUESTED:
    _qualification_install_source_only_repo_imports(repo_root)

if not _QUALIFICATION_CLI_REQUESTED:
    from analysis_scripts.verify_noncombat_ope_artifacts import (
        ArtifactVerificationError,
        verify_artifact_pair,
    )
    from analysis_scripts.verify_noncombat_ope_estimates import (
        EstimateVerificationError,
        verify_estimate_artifact,
    )


AUDIT_SCHEMA_VERSION = "noncombat-outcome-evidence-verification-audit-v1"
LEGACY_REGISTRATION_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-registration-v1"
)
REGISTRATION_SCHEMA_VERSION = "noncombat-outcome-evidence-registration-v2"
RUN_LOCK_SCHEMA_VERSION = "noncombat-outcome-evidence-run-lock-v1"
LEDGER_SCHEMA_VERSION = "noncombat-outcome-evidence-ledger-v1"
POOL_SCHEMA_VERSION = "noncombat-outcome-evidence-pool-v1"
CLOSEOUT_SCHEMA_VERSION = "noncombat-outcome-evidence-closeout-v1"
EVIDENCE_GATE_SCHEMA_VERSION = "noncombat-outcome-evidence-gate-v1"
CLAIM_SCHEMA_VERSION = "noncombat-outcome-evidence-finalization-claim-v1"
HANDSHAKE_SCHEMA_VERSION = "noncombat-outcome-evidence-handshake-v1"
HANDSHAKE_ATTEMPT_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-handshake-attempt-v1"
)
HANDSHAKE_READY_SCHEMA_VERSION = "noncombat-outcome-evidence-handshake-ready-v1"
HANDSHAKE_RELEASE_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-handshake-release-v1"
)
QUALIFICATION_REQUEST_V1_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-request-v1"
)
QUALIFICATION_REQUEST_V2_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-request-v2"
)
QUALIFICATION_REQUEST_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-request-v3"
)
QUALIFICATION_RESULT_V1_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-result-v1"
)
QUALIFICATION_RESULT_V2_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-result-v2"
)
QUALIFICATION_RESULT_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-result-v3"
)
QUALIFICATION_ISOLATION_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-isolation-v1"
)
QUALIFICATION_ISOLATION_OBSERVATION_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-isolation-observation-v1"
)
QUALIFICATION_AUDIT_V2_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-verification-audit-v2"
)
QUALIFICATION_AUDIT_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-verification-audit-v3"
)
QUALIFICATION_REVIEW_BINDING_V1_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-review-binding-v1"
)
QUALIFICATION_REVIEW_BINDING_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-review-binding-v3"
)
QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-bootstrap-evidence-v1"
)
QUALIFICATION_BOOTSTRAP_TOKEN_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-qualification-bootstrap-token-v1"
)
QUALIFICATION_BOOTSTRAP_STAGE_NAMES = (
    "launcher_verified",
    "runner_entered",
    "source_verified",
    "request_reviewed",
    "isolation_verified",
)
QUALIFICATION_BOOTSTRAP_FAILURE_DETAILS = {
    "bootstrap_envelope_invalid": "bootstrap envelope validation failed",
    "bootstrap_claim_publish_failed": "bootstrap claim publication failed",
    "runner_validation_failed": "reviewed runner validation failed",
    "runner_entry_validation_failed": "runner entry validation failed",
    "source_validation_failed": "reviewed source validation failed",
    "request_validation_failed": "reviewed request validation failed",
    "prelaunch_isolation_failed": "prelaunch isolation validation failed",
    "unexpected_pre_request_failure": "unexpected pre-request failure",
}
QUALIFICATION_BOOTSTRAP_FAILURE_CODES = frozenset(
    QUALIFICATION_BOOTSTRAP_FAILURE_DETAILS
)
QUALIFICATION_RUNNER_RELATIVE_PATH = (
    "scripts/run_noncombat_outcome_evidence_expansion.py"
)
LEGACY_QUALIFICATION_REQUEST_SCHEMA_VERSION = (
    QUALIFICATION_REQUEST_V1_SCHEMA_VERSION
)
LEGACY_QUALIFICATION_RESULT_SCHEMA_VERSION = QUALIFICATION_RESULT_V1_SCHEMA_VERSION
BLOCKED_ESTIMATE_SCHEMA_VERSION = (
    "noncombat-outcome-evidence-estimate-blocked-v1"
)
ESTIMATE_SCHEMA_VERSION = "noncombat-ope-estimate-v1"
SLOT_COUNT = 24
GAMES_PER_SLOT = 25
SCHEDULED_ATTEMPTS = SLOT_COUNT * GAMES_PER_SLOT
DRAW_BUCKET_COUNT = 10_000
OUTCOME_JOIN_TOLERANCE_SECONDS = 30
WINDOWS_PYTHON = str(Path(r"D:\anaconda\envs\stsai\python.exe").resolve())
QUALIFICATION_GIT_EXECUTABLE = Path(r"C:\Program Files\Git\cmd\git.exe")
QUALIFICATION_INERT_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".log",
    ".md",
    ".tsv",
    ".txt",
}
SELECTION_SCHEMA_VERSION = "noncombat-exploration-selection-v1"
COMMAND_ARGUMENTS = (
    "--agent",
    "combat_rl",
    "--elite-route",
    "conservative",
    "--max-games",
    "25",
    "--ascension",
    "0",
    "--rl-version",
    "v2",
    "--eval",
)
LEGACY_IMPLEMENTATION_PATHS = (
    "analysis_scripts/__init__.py",
    "analysis_scripts/noncombat_exploration_evidence.py",
    "analysis_scripts/noncombat_ope_estimate_artifacts.py",
    "analysis_scripts/noncombat_ope_estimation.py",
    "analysis_scripts/noncombat_ope_readiness.py",
    "analysis_scripts/noncombat_outcome_evidence_expansion.py",
    "analysis_scripts/verify_noncombat_ope_artifacts.py",
    "analysis_scripts/verify_noncombat_ope_estimates.py",
    "analysis_scripts/verify_noncombat_outcome_evidence_expansion.py",
    "main.py",
    "scripts/run_noncombat_outcome_evidence_expansion.py",
    "spirecomm/ai/noncombat_exploration.py",
    "spirecomm/ai/noncombat_exploration_runtime.py",
)
IMPLEMENTATION_PATHS = (
    *LEGACY_IMPLEMENTATION_PATHS,
    "spirecomm/communication/study_handshake.py",
)
CHECKPOINT_PATTERNS = ("rl_combat_model_*.pth", "rl_model_*.pth")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_STUDY_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class OutcomeEvidenceVerificationError(ValueError):
    """Raised when independent study replay cannot close every check."""


class _DuplicateJsonKeyError(ValueError):
    pass


class _Checks:
    def __init__(self) -> None:
        self.count = 0
        self.guarded_root_snapshot: dict[str, Any] | None = None

    def require(self, condition: bool, message: str) -> None:
        self.count += 1
        if condition is not True:
            raise OutcomeEvidenceVerificationError(message)


def _qualification_metadata_is_link_or_reparse(
    metadata: os.stat_result,
) -> bool:
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return stat.S_ISLNK(metadata.st_mode) or bool(
        file_attributes & reparse_flag
    )


def _qualification_lstat(path: Path) -> os.stat_result | None:
    try:
        return Path(path).lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot inspect qualification path entry {path}: {exc}"
        ) from exc


def _qualification_path_entry_exists(path: Path) -> bool:
    return _qualification_lstat(path) is not None


def _qualification_path_is_link_or_reparse(path: Path) -> bool:
    metadata = _qualification_lstat(path)
    return metadata is not None and _qualification_metadata_is_link_or_reparse(
        metadata
    )


def _qualification_path_is_regular_file(path: Path) -> bool:
    metadata = _qualification_lstat(path)
    return (
        metadata is not None
        and not _qualification_metadata_is_link_or_reparse(metadata)
        and stat.S_ISREG(metadata.st_mode)
    )


def _qualification_require_no_follow_path(
    path: Path | str,
    label: str,
    *,
    expected_kind: str | None,
    allow_missing: bool = False,
) -> Path:
    supplied_path = Path(os.fspath(path))
    supplied_components = (
        supplied_path.parts[1:] if supplied_path.anchor else supplied_path.parts
    )
    if any(":" in part for part in supplied_components):
        raise OutcomeEvidenceVerificationError(
            f"qualification {label} contains an alternate data stream"
        )
    if any(part.endswith((".", " ")) for part in supplied_components):
        raise OutcomeEvidenceVerificationError(
            f"qualification {label} contains a Win32 alias component"
        )
    lexical_path = Path(os.path.abspath(supplied_path))
    if lexical_path.drive.startswith("\\\\"):
        raise OutcomeEvidenceVerificationError(
            f"qualification {label} must use a local drive; UNC and device "
            "paths are forbidden"
        )
    if expected_kind not in {None, "directory", "file"}:
        raise OutcomeEvidenceVerificationError(
            "qualification path expected kind is invalid"
        )
    current = Path(lexical_path.anchor)
    for part in lexical_path.parts[1:]:
        current /= part
        metadata = _qualification_lstat(current)
        if metadata is None:
            if allow_missing:
                return lexical_path
            raise OutcomeEvidenceVerificationError(
                f"qualification {label} is missing: {current}"
            )
        if _qualification_metadata_is_link_or_reparse(metadata):
            raise OutcomeEvidenceVerificationError(
                f"qualification {label} contains a symbolic link or reparse "
                f"point: {current}"
            )
    metadata = _qualification_lstat(lexical_path)
    if metadata is None:
        if allow_missing:
            return lexical_path
        raise OutcomeEvidenceVerificationError(
            f"qualification {label} is missing: {lexical_path}"
        )
    if expected_kind is None:
        return lexical_path
    expected_mode = (
        stat.S_ISDIR(metadata.st_mode)
        if expected_kind == "directory"
        else stat.S_ISREG(metadata.st_mode)
    )
    if not expected_mode:
        raise OutcomeEvidenceVerificationError(
            f"qualification {label} is not a regular {expected_kind}: "
            f"{lexical_path}"
        )
    return lexical_path


def _qualification_git_executable() -> str:
    return str(
        _qualification_require_no_follow_path(
            QUALIFICATION_GIT_EXECUTABLE,
            "Git executable",
            expected_kind="file",
        )
    )


def _qualification_git_environment(
    *,
    repo_root: Path,
    git_root: Path,
) -> dict[str, str]:
    environment = {
        key: value
        for key in ("SystemRoot", "WINDIR", "COMSPEC", "TEMP", "TMP")
        if (value := os.environ.get(key))
    }
    environment.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_DIR": str(git_root),
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_WORK_TREE": str(repo_root),
            "LC_ALL": "C",
        }
    )
    return environment


def _qualification_git_command(*arguments: str) -> list[str]:
    return [
        _qualification_git_executable(),
        "--no-pager",
        "--no-replace-objects",
        "--no-lazy-fetch",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=NUL",
        "-c",
        "diff.external=",
        "-c",
        "color.ui=false",
        *arguments,
    ]


def _qualification_lexical_absolute_path(value: Any, field: str) -> Path:
    raw = _required_string(value, field)
    path = Path(raw)
    path_components = path.parts[1:] if path.anchor else path.parts
    if any(":" in part for part in path_components):
        raise OutcomeEvidenceVerificationError(
            f"{field} contains an alternate data stream"
        )
    if any(part.endswith((".", " ")) for part in path_components):
        raise OutcomeEvidenceVerificationError(
            f"{field} contains a Win32 alias component"
        )
    lexical_path = Path(os.path.abspath(raw))
    if not path.is_absolute() or str(lexical_path) != raw:
        raise OutcomeEvidenceVerificationError(
            f"{field} must be lexical absolute"
        )
    if lexical_path.drive.startswith("\\\\"):
        raise OutcomeEvidenceVerificationError(
            f"{field} must use a local drive; UNC and device paths are "
            "forbidden"
        )
    return lexical_path


def _qualification_registration_absolute_paths(value: Any):
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _qualification_registration_absolute_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _qualification_registration_absolute_paths(child)
    elif isinstance(value, str) and Path(value).is_absolute():
        yield value


def _verify_qualification_registration_paths(
    registration: Mapping[str, Any],
    *,
    repo_root: Path,
) -> Path:
    for raw_path in _qualification_registration_absolute_paths(registration):
        _qualification_require_no_follow_path(
            _qualification_lexical_absolute_path(
                raw_path,
                "qualification registered path",
            ),
            "registered path",
            expected_kind=None,
            allow_missing=True,
        )
    registered_repo_root = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            registration.get("repo_root"),
            "qualification registration repository root",
        ),
        "registered repository root",
        expected_kind="directory",
    )
    if registered_repo_root != repo_root:
        raise OutcomeEvidenceVerificationError(
            "qualification registration repository root mismatch"
        )
    integrity_rules = registration.get("integrity_rules")
    implementation_paths = (
        integrity_rules.get("implementation_paths")
        if isinstance(integrity_rules, Mapping)
        else None
    )
    if not isinstance(implementation_paths, list):
        raise OutcomeEvidenceVerificationError(
            "qualification registration implementation paths are invalid"
        )
    for relative_path in implementation_paths:
        candidate = Path(relative_path) if isinstance(relative_path, str) else None
        if (
            candidate is None
            or candidate.is_absolute()
            or "\\" in relative_path
            or candidate.as_posix() != relative_path
            or any(part in {"", ".", ".."} for part in candidate.parts)
        ):
            raise OutcomeEvidenceVerificationError(
                "qualification registration implementation path is invalid"
            )
        _qualification_require_no_follow_path(
            registered_repo_root / candidate,
            f"registered implementation path {relative_path}",
            expected_kind=None,
            allow_missing=True,
        )
    return registered_repo_root


def _qualification_irregular_path_reason(path: Path) -> str | None:
    if not _qualification_path_entry_exists(path):
        return None
    if _qualification_path_is_regular_file(path):
        return None
    if _qualification_path_is_link_or_reparse(path):
        return "is a symbolic link or reparse point"
    return "is not a regular file"


def _qualification_declared_paths(
    request: Mapping[str, Any],
    *,
    qualification_root: Path,
) -> dict[str, Any]:
    handshake = _mapping(
        request.get("handshake"),
        "qualification handshake",
    )
    declared = {
        "attempt": _qualification_lexical_absolute_path(
            handshake.get("attempt_path"),
            "qualification attempt path",
        ),
        "completion": _qualification_lexical_absolute_path(
            request.get("completion_path"),
            "qualification completion path",
        ),
        "failure": _qualification_lexical_absolute_path(
            request.get("failure_path"),
            "qualification failure path",
        ),
        "ready": _qualification_lexical_absolute_path(
            handshake.get("ready_path"),
            "qualification ready path",
        ),
        "release": _qualification_lexical_absolute_path(
            handshake.get("release_path"),
            "qualification release path",
        ),
        "request": _qualification_lexical_absolute_path(
            request.get("request_path"),
            "qualification active request path",
        ),
    }
    expected = {
        "attempt": "qualification-communication-attempt.json",
        "completion": "qualification-completion.json",
        "failure": "qualification-failure.json",
        "ready": "qualification-communication-ready.json",
        "release": "qualification-communication-release.json",
        "request": "qualification-request.json",
    }
    expected_paths = {
        name: Path(os.path.abspath(qualification_root / filename))
        for name, filename in expected.items()
    }
    if declared != expected_paths:
        raise OutcomeEvidenceVerificationError(
            "qualification declared path binding mismatch"
        )
    for name, path in declared.items():
        _qualification_require_no_follow_path(
            path.parent,
            f"{name} path parent",
            expected_kind="directory",
        )
    return declared


def _qualification_bootstrap_declared_paths(
    request: Mapping[str, Any],
    qualification_root: Path,
) -> dict[str, Path]:
    root = _qualification_lexical_absolute_path(
        str(qualification_root),
        "qualification bootstrap root",
    )
    bootstrap = _mapping(
        request.get("bootstrap"),
        "qualification bootstrap",
    )
    checks = _Checks()
    checks.require(
        set(bootstrap)
        == {
            "claim_path",
            "failure_path",
            "handoff_path",
            "schema_version",
            "stage_paths",
            "token_schema_version",
        },
        "qualification bootstrap fields mismatch",
    )
    checks.require(
        bootstrap.get("schema_version")
        == QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION,
        "qualification bootstrap schema mismatch",
    )
    checks.require(
        bootstrap.get("token_schema_version")
        == QUALIFICATION_BOOTSTRAP_TOKEN_SCHEMA_VERSION,
        "qualification bootstrap token schema mismatch",
    )
    stage_rows = _sequence(
        bootstrap.get("stage_paths"),
        "qualification bootstrap stage paths",
    )
    checks.require(
        len(stage_rows) == len(QUALIFICATION_BOOTSTRAP_STAGE_NAMES),
        "qualification bootstrap stage count mismatch",
    )
    declared: dict[str, Path] = {
        "claim": _qualification_lexical_absolute_path(
            bootstrap.get("claim_path"),
            "qualification bootstrap claim path",
        )
    }
    for index, name in enumerate(QUALIFICATION_BOOTSTRAP_STAGE_NAMES, start=1):
        row = _mapping(
            stage_rows[index - 1],
            f"qualification bootstrap stage {index}",
        )
        checks.require(
            set(row) == {"index", "name", "path"}
            and row.get("index") == index
            and row.get("name") == name,
            "qualification bootstrap stage declaration mismatch",
        )
        declared[name] = _qualification_lexical_absolute_path(
            row.get("path"),
            f"qualification bootstrap {name} path",
        )
    declared["failure"] = _qualification_lexical_absolute_path(
        bootstrap.get("failure_path"),
        "qualification bootstrap failure path",
    )
    declared["handoff"] = _qualification_lexical_absolute_path(
        bootstrap.get("handoff_path"),
        "qualification bootstrap handoff path",
    )
    expected_names = {
        "claim": "qualification-bootstrap-claim.json",
        **{
            name: (
                f"qualification-bootstrap-stage-{index:02d}-"
                f"{name.replace('_', '-')}.json"
            )
            for index, name in enumerate(
                QUALIFICATION_BOOTSTRAP_STAGE_NAMES,
                start=1,
            )
        },
        "failure": "qualification-bootstrap-failure.json",
        "handoff": "qualification-bootstrap-handoff.json",
    }
    expected = {
        name: Path(os.path.abspath(root / filename))
        for name, filename in expected_names.items()
    }
    checks.require(
        all(
            str(declared[name]) == str(expected[name])
            for name in expected_names
        )
        and len(set(declared.values())) == len(declared),
        "qualification bootstrap declared path binding mismatch",
    )
    for name, path in declared.items():
        checks.require(
            path.parent == root,
            f"qualification bootstrap {name} is not a direct child",
        )
    return declared


def _qualification_bootstrap_expected_envelope(
    *,
    request: Mapping[str, Any],
    expected_request_file_sha256: str,
    expected_request_size: int,
    review_commit: str,
    runner_sha256: str,
) -> dict[str, Any]:
    qualification_root = _qualification_lexical_absolute_path(
        request.get("qualification_root"),
        "qualification_root",
    )
    _qualification_bootstrap_declared_paths(request, qualification_root)
    if not _is_sha256(expected_request_file_sha256):
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap request file hash is invalid"
        )
    if type(expected_request_size) is not int or expected_request_size <= 0:
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap request size is invalid"
        )
    if not isinstance(review_commit, str) or not _COMMIT_PATTERN.fullmatch(
        review_commit
    ):
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap review commit is invalid"
        )
    if not _is_sha256(runner_sha256):
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap runner hash is invalid"
        )
    qualification_id = request.get("qualification_id")
    source_commit = request.get("source_commit")
    request_hash = request.get("request_hash")
    if not isinstance(qualification_id, str) or not qualification_id:
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap qualification ID is invalid"
        )
    if not isinstance(source_commit, str) or not _COMMIT_PATTERN.fullmatch(
        source_commit
    ):
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap source commit is invalid"
        )
    if not _is_sha256(request_hash):
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap request hash is invalid"
        )
    envelope = {
        "bootstrap": dict(request["bootstrap"]),
        "qualification_id": qualification_id,
        "qualification_root": str(qualification_root),
        "request_file_sha256": expected_request_file_sha256,
        "request_hash": request_hash,
        "request_size": expected_request_size,
        "review_commit": review_commit,
        "runner_sha256": runner_sha256,
        "schema_version": QUALIFICATION_BOOTSTRAP_TOKEN_SCHEMA_VERSION,
        "source_commit": source_commit,
    }
    try:
        return json.loads(_qualification_bootstrap_canonical_json(envelope))
    except (TypeError, ValueError, UnicodeError) as exc:
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap envelope is invalid"
        ) from exc


def _qualification_bootstrap_canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _qualification_bootstrap_load_record_bytes(
    raw: bytes,
    *,
    label: str,
) -> dict[str, Any]:
    try:
        record = json.loads(
            raw.decode("ascii"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
        canonical = _qualification_bootstrap_canonical_json(record).encode(
            "ascii"
        ) + b"\n"
    except (UnicodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise OutcomeEvidenceVerificationError(
            f"qualification bootstrap {label} JSON is invalid"
        ) from exc
    expected_fields = {
        "anchors",
        "created_unix_ns",
        "payload",
        "pid",
        "previous_hash",
        "record_hash",
        "record_type",
        "schema_version",
        "stage_index",
        "stage_name",
    }
    if not isinstance(record, Mapping) or set(record) != expected_fields:
        raise OutcomeEvidenceVerificationError(
            f"qualification bootstrap {label} fields are invalid"
        )
    if raw != canonical:
        raise OutcomeEvidenceVerificationError(
            f"qualification bootstrap {label} is not canonical"
        )
    observed_hash = record.get("record_hash")
    replay = dict(record)
    replay["record_hash"] = None
    if not _is_sha256(observed_hash) or observed_hash != hashlib.sha256(
        _qualification_bootstrap_canonical_json(replay).encode("ascii")
    ).hexdigest():
        raise OutcomeEvidenceVerificationError(
            f"qualification bootstrap {label} self-hash mismatch"
        )
    if (
        record.get("schema_version")
        != QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION
        or type(record.get("created_unix_ns")) is not int
        or record["created_unix_ns"] <= 0
        or type(record.get("pid")) is not int
        or record["pid"] <= 0
        or type(record.get("stage_index")) is not int
        or record["stage_index"] < 0
        or not isinstance(record.get("stage_name"), str)
        or not record["stage_name"]
        or (
            record.get("previous_hash") is not None
            and not _is_sha256(record["previous_hash"])
        )
        or not isinstance(record.get("anchors"), Mapping)
        or not isinstance(record.get("payload"), Mapping)
    ):
        raise OutcomeEvidenceVerificationError(
            f"qualification bootstrap {label} shape is invalid"
        )
    return dict(record)


def _qualification_verify_bootstrap_prefix(
    request: Mapping[str, Any],
    review: Mapping[str, Any],
    *,
    active_request_bytes: bytes | None,
    checks: _Checks,
) -> dict[str, Any]:
    qualification_root = _qualification_lexical_absolute_path(
        request.get("qualification_root"),
        "qualification_root",
    )
    declared = _qualification_bootstrap_declared_paths(
        request,
        qualification_root,
    )
    request_path = _qualification_lexical_absolute_path(
        request.get("request_path"),
        "qualification active request path",
    )
    checks.require(
        request_path
        == Path(os.path.abspath(qualification_root / "qualification-request.json")),
        "qualification active request path mismatch",
    )
    reviewed_request_bytes = review.get("request_bytes")
    review_binding = _mapping(
        review.get("review_binding"),
        "qualification review binding",
    )
    review_commit = review_binding.get("review_commit")
    implementation = _mapping(
        request.get("implementation_sha256"),
        "qualification implementation_sha256",
    )
    runner_sha256 = implementation.get(QUALIFICATION_RUNNER_RELATIVE_PATH)
    if not isinstance(reviewed_request_bytes, bytes):
        raise OutcomeEvidenceVerificationError(
            "qualification reviewed request bytes are invalid"
        )
    try:
        reviewed_request = json.loads(
            reviewed_request_bytes.decode("ascii"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, ValueError, json.JSONDecodeError) as exc:
        raise OutcomeEvidenceVerificationError(
            "qualification reviewed request bytes are invalid"
        ) from exc
    checks.require(
        isinstance(reviewed_request, Mapping)
        and dict(reviewed_request) == dict(request)
        and reviewed_request_bytes
        == _qualification_bootstrap_canonical_json(reviewed_request).encode(
            "ascii"
        )
        + b"\n",
        "qualification reviewed request bytes are not canonical",
    )
    envelope = _qualification_bootstrap_expected_envelope(
        request=request,
        expected_request_file_sha256=hashlib.sha256(
            reviewed_request_bytes
        ).hexdigest(),
        expected_request_size=len(reviewed_request_bytes),
        review_commit=review_commit,
        runner_sha256=runner_sha256,
    )
    canonical_envelope = _qualification_bootstrap_canonical_json(envelope).encode(
        "ascii"
    )
    launch_token = hashlib.sha256(
        b"noncombat-outcome-evidence-qualification-bootstrap-token-v1\x00"
        + canonical_envelope
    ).hexdigest()
    expected_anchors = {
        "envelope_sha256": hashlib.sha256(canonical_envelope).hexdigest(),
        "launch_token": launch_token,
        "qualification_id": request["qualification_id"],
        "request_file_sha256": hashlib.sha256(
            reviewed_request_bytes
        ).hexdigest(),
        "request_hash": request["request_hash"],
        "request_size": len(reviewed_request_bytes),
        "review_commit": review_commit,
        "runner_sha256": runner_sha256,
        "source_commit": request["source_commit"],
    }

    bootstrap_paths = list(declared.values())
    bootstrap_path_set = set(bootstrap_paths)
    lifecycle_paths: set[Path] = set()
    handshake = request.get("handshake")
    if isinstance(handshake, Mapping):
        for name in ("attempt", "ready", "release"):
            value = handshake.get(f"{name}_path")
            if isinstance(value, str):
                lifecycle_paths.add(
                    _qualification_lexical_absolute_path(
                        value,
                        f"qualification {name} path",
                    )
                )
    for field in ("completion_path", "failure_path"):
        value = request.get(field)
        if isinstance(value, str):
            lifecycle_paths.add(
                _qualification_lexical_absolute_path(
                    value,
                    f"qualification {field}",
                )
            )
    dynamic_paths = bootstrap_path_set | lifecycle_paths | {request_path}
    preexisting = _mapping(
        request.get("preexisting_files"),
        "qualification preexisting files",
    )
    preexisting_paths: dict[Path, str] = {}
    for raw_path, expected_hash in preexisting.items():
        path = _qualification_lexical_absolute_path(
            raw_path,
            "qualification preexisting file path",
        )
        checks.require(
            path.is_relative_to(qualification_root)
            and path not in dynamic_paths
            and _is_sha256(expected_hash),
            "qualification preexisting file binding is invalid",
        )
        preexisting_paths[path] = expected_hash
    allowed_directories = {
        parent
        for path in preexisting_paths
        for parent in path.parents
        if parent != qualification_root and parent.is_relative_to(qualification_root)
    }
    exact_paths = {
        os.path.normcase(str(path)): str(path)
        for path in dynamic_paths | set(preexisting_paths) | allowed_directories
    }
    qualification_root = _qualification_require_no_follow_path(
        qualification_root,
        "root",
        expected_kind="directory",
    )

    guarded_snapshot = _qualification_guarded_root_snapshot(qualification_root)
    checks.guarded_root_snapshot = guarded_snapshot
    observed_metadata: dict[Path, tuple[os.stat_result, bool]] = {}
    raw_by_path: dict[Path, bytes] = {}
    invalid_reasons = list(guarded_snapshot["errors"])
    for lexical_path, snapshot_row in guarded_snapshot["entries"].items():
        metadata = snapshot_row["metadata"]
        is_link_or_reparse = snapshot_row["is_link_or_reparse"]
        observed_metadata[lexical_path] = (metadata, is_link_or_reparse)
        expected_lexical = exact_paths.get(os.path.normcase(str(lexical_path)))
        if expected_lexical is not None and str(lexical_path) != expected_lexical:
            invalid_reasons.append(f"case-aliased entry: {lexical_path}")
        if is_link_or_reparse:
            invalid_reasons.append(f"linked or reparse entry: {lexical_path}")
            continue
        if stat.S_ISDIR(metadata.st_mode):
            if lexical_path not in allowed_directories:
                invalid_reasons.append(f"unexpected directory: {lexical_path}")
            continue
        if not stat.S_ISREG(metadata.st_mode):
            invalid_reasons.append(f"non-regular entry: {lexical_path}")
            continue
        if lexical_path not in dynamic_paths and lexical_path not in preexisting_paths:
            invalid_reasons.append(f"unexpected guarded-root entry: {lexical_path}")
        raw = snapshot_row["raw"]
        if raw is None:
            continue
        raw_by_path[lexical_path] = raw
        expected_hash = preexisting_paths.get(lexical_path)
        if expected_hash is not None and hashlib.sha256(raw).hexdigest() != expected_hash:
            invalid_reasons.append(
                f"preexisting file hash mismatch: {lexical_path}"
            )
    for path in preexisting_paths:
        if path not in observed_metadata:
            invalid_reasons.append(f"preexisting file is missing: {path}")
    captured_active_request_bytes = raw_by_path.get(request_path)
    if active_exists := request_path in observed_metadata:
        if captured_active_request_bytes is None:
            invalid_reasons.append("active request bytes are unavailable")
        elif (
            active_request_bytes is not None
            and active_request_bytes != captured_active_request_bytes
        ):
            invalid_reasons.append(
                "active request changed between supplied bytes and guarded snapshot"
            )
    active_request_bytes = captured_active_request_bytes

    inventory_entries = []
    for path in bootstrap_paths:
        metadata_row = observed_metadata.get(path)
        if metadata_row is None:
            continue
        raw = raw_by_path.get(path)
        inventory_entries.append(
            {
                "path": path.name,
                "sha256": None if raw is None else hashlib.sha256(raw).hexdigest(),
                "size": metadata_row[0].st_size,
            }
        )
    bootstrap_inventory = {
        "entries": inventory_entries,
        "entry_count": len(inventory_entries),
        "inventory_sha256": hashlib.sha256(
            _qualification_bootstrap_canonical_json(inventory_entries).encode(
                "ascii"
            )
        ).hexdigest(),
    }
    bootstrap_exists = any(path in observed_metadata for path in bootstrap_paths)
    control_exists = any(path in observed_metadata for path in lifecycle_paths)
    consumed = bootstrap_exists or control_exists or active_exists or bool(
        invalid_reasons
    )

    def result(
        qualification_status: str,
        *,
        partial_stage: str | None,
        evidence_valid: bool,
        evidence_error: str | None,
        claim_hash: str | None = None,
        final_stage_hash: str | None = None,
        handoff_hash: str | None = None,
    ) -> dict[str, Any]:
        return {
            "bootstrap_inventory": bootstrap_inventory,
            "claim_hash": claim_hash,
            "consumed": consumed,
            "evidence_error": evidence_error,
            "evidence_valid": evidence_valid,
            "final_stage_hash": final_stage_hash,
            "handoff_hash": handoff_hash,
            "launch_token": launch_token,
            "partial_stage": partial_stage,
            "qualification_status": qualification_status,
        }

    if not consumed:
        return result(
            "reviewed_prepared",
            partial_stage=None,
            evidence_valid=True,
            evidence_error=None,
        )
    if invalid_reasons:
        return result(
            "sealed_invalid",
            partial_stage="invalid_bootstrap_prefix",
            evidence_valid=False,
            evidence_error="; ".join(invalid_reasons),
        )
    stage_paths = [declared[name] for name in QUALIFICATION_BOOTSTRAP_STAGE_NAMES]
    stage_exists = [path in observed_metadata for path in stage_paths]
    contiguous_count = 0
    for exists in stage_exists:
        if not exists:
            break
        contiguous_count += 1
    malformed_prefix = stage_exists != (
        [True] * contiguous_count
        + [False] * (len(stage_exists) - contiguous_count)
    )
    if declared["claim"] not in observed_metadata or malformed_prefix:
        return result(
            "sealed_invalid",
            partial_stage="invalid_bootstrap_prefix",
            evidence_valid=False,
            evidence_error="qualification bootstrap claim/stage prefix is not contiguous",
        )
    try:
        claim = _qualification_bootstrap_load_record_bytes(
            raw_by_path[declared["claim"]],
            label="claim",
        )
        if (
            claim["record_type"] != "claim"
            or claim["stage_index"] != 0
            or claim["stage_name"] != "claim"
            or claim["previous_hash"] is not None
            or dict(claim["payload"]) != {}
            or dict(claim["anchors"]) != expected_anchors
        ):
            raise OutcomeEvidenceVerificationError(
                "qualification bootstrap claim shape or anchors mismatch"
            )
        previous_hash = claim["record_hash"]
        final_stage_hash = None
        for index in range(contiguous_count):
            name = QUALIFICATION_BOOTSTRAP_STAGE_NAMES[index]
            stage = _qualification_bootstrap_load_record_bytes(
                raw_by_path[declared[name]],
                label=name,
            )
            if stage["pid"] != claim["pid"]:
                raise OutcomeEvidenceVerificationError(
                    "qualification bootstrap stage PID differs from claim"
                )
            if (
                stage["record_type"] != "stage"
                or stage["stage_index"] != index + 1
                or stage["stage_name"] != name
                or stage["previous_hash"] != previous_hash
                or dict(stage["payload"]) != {}
                or dict(stage["anchors"]) != expected_anchors
            ):
                raise OutcomeEvidenceVerificationError(
                    "qualification bootstrap stage chain mismatch"
                )
            previous_hash = stage["record_hash"]
            final_stage_hash = previous_hash
    except (KeyError, OutcomeEvidenceVerificationError) as exc:
        return result(
            "sealed_invalid",
            partial_stage="invalid_bootstrap_prefix",
            evidence_valid=False,
            evidence_error=str(exc),
        )

    failure = None
    if declared["failure"] in observed_metadata:
        try:
            failure = _qualification_bootstrap_load_record_bytes(
                raw_by_path[declared["failure"]],
                label="failure",
            )
            failure_payload = dict(failure["payload"])
            failure_code = failure_payload.get("code")
            if failure["pid"] != claim["pid"]:
                raise OutcomeEvidenceVerificationError(
                    "qualification bootstrap failure PID differs from claim"
                )
            expected_stage_name = (
                "claim"
                if contiguous_count == 0
                else QUALIFICATION_BOOTSTRAP_STAGE_NAMES[contiguous_count - 1]
            )
            if (
                failure["record_type"] != "failure"
                or failure["stage_index"] != contiguous_count
                or failure["stage_name"] != expected_stage_name
                or failure["previous_hash"] != previous_hash
                or dict(failure["anchors"]) != expected_anchors
                or set(failure_payload)
                != {"code", "detail", "errno", "exception_type", "winerror"}
                or failure_code not in QUALIFICATION_BOOTSTRAP_FAILURE_CODES
                or failure_payload["detail"]
                != QUALIFICATION_BOOTSTRAP_FAILURE_DETAILS[failure_code]
                or not isinstance(failure_payload["exception_type"], str)
                or not failure_payload["exception_type"]
                or not failure_payload["exception_type"].isascii()
                or not failure_payload["exception_type"].isidentifier()
                or len(failure_payload["exception_type"]) > 64
                or any(
                    value is not None and type(value) is not int
                    for value in (
                        failure_payload["errno"],
                        failure_payload["winerror"],
                    )
                )
            ):
                raise OutcomeEvidenceVerificationError(
                    "qualification bootstrap failure record mismatch"
                )
        except (KeyError, OutcomeEvidenceVerificationError) as exc:
            return result(
                "sealed_invalid",
                partial_stage="invalid_bootstrap_prefix",
                evidence_valid=False,
                evidence_error=str(exc),
                claim_hash=claim["record_hash"],
                final_stage_hash=final_stage_hash,
            )

    handoff_exists = declared["handoff"] in observed_metadata
    if not active_exists:
        if handoff_exists or control_exists:
            return result(
                "sealed_invalid",
                partial_stage="invalid_bootstrap_prefix",
                evidence_valid=False,
                evidence_error="later qualification evidence exists before active request",
                claim_hash=claim["record_hash"],
                final_stage_hash=final_stage_hash,
            )
        if failure is not None:
            return result(
                "pre_request_partial",
                partial_stage=str(failure["payload"]["code"]),
                evidence_valid=True,
                evidence_error=None,
                claim_hash=claim["record_hash"],
                final_stage_hash=final_stage_hash,
            )
        last_name = (
            "claim"
            if contiguous_count == 0
            else QUALIFICATION_BOOTSTRAP_STAGE_NAMES[contiguous_count - 1]
        )
        return result(
            "pre_request_partial",
            partial_stage=f"abrupt_after_{last_name}",
            evidence_valid=True,
            evidence_error=None,
            claim_hash=claim["record_hash"],
            final_stage_hash=final_stage_hash,
        )
    if failure is not None or contiguous_count != len(
        QUALIFICATION_BOOTSTRAP_STAGE_NAMES
    ):
        return result(
            "sealed_invalid",
            partial_stage="invalid_bootstrap_prefix",
            evidence_valid=False,
            evidence_error="active request follows an incomplete bootstrap prefix",
            claim_hash=claim["record_hash"],
            final_stage_hash=final_stage_hash,
        )
    if (
        active_request_bytes != reviewed_request_bytes
        or request.get("request_hash") != _self_hash(request, "request_hash")
    ):
        return result(
            "active_request_partial",
            partial_stage="invalid_active_request",
            evidence_valid=False,
            evidence_error="active request differs from reviewed canonical bytes",
            claim_hash=claim["record_hash"],
            final_stage_hash=final_stage_hash,
        )
    if not handoff_exists:
        return result(
            "active_request_partial",
            partial_stage="missing_handoff",
            evidence_valid=True,
            evidence_error=None,
            claim_hash=claim["record_hash"],
            final_stage_hash=final_stage_hash,
        )
    try:
        handoff = _qualification_bootstrap_load_record_bytes(
            raw_by_path[declared["handoff"]],
            label="handoff",
        )
        if handoff["pid"] != claim["pid"]:
            return result(
                "sealed_invalid",
                partial_stage="invalid_bootstrap_prefix",
                evidence_valid=False,
                evidence_error=(
                    "qualification bootstrap handoff PID differs from claim"
                ),
                claim_hash=claim["record_hash"],
                final_stage_hash=final_stage_hash,
            )
        expected_payload = {
            "active_request_file_sha256": hashlib.sha256(
                active_request_bytes
            ).hexdigest(),
            "active_request_size": len(active_request_bytes),
            "claim_hash": claim["record_hash"],
            "final_stage_hash": final_stage_hash,
            "request_hash": request["request_hash"],
        }
        if (
            handoff["record_type"] != "handoff"
            or handoff["stage_index"] != 6
            or handoff["stage_name"] != "active_request_handoff"
            or handoff["previous_hash"] != final_stage_hash
            or dict(handoff["anchors"]) != expected_anchors
            or dict(handoff["payload"]) != expected_payload
        ):
            raise OutcomeEvidenceVerificationError(
                "qualification bootstrap handoff mismatch"
            )
    except (KeyError, OutcomeEvidenceVerificationError) as exc:
        return result(
            "active_request_partial",
            partial_stage="invalid_handoff",
            evidence_valid=False,
            evidence_error=str(exc),
            claim_hash=claim["record_hash"],
            final_stage_hash=final_stage_hash,
        )
    return result(
        "handoff_complete",
        partial_stage=None,
        evidence_valid=True,
        evidence_error=None,
        claim_hash=claim["record_hash"],
        final_stage_hash=final_stage_hash,
        handoff_hash=handoff["record_hash"],
    )


def _qualification_no_follow_entries(
    root: Path,
) -> list[tuple[Path, os.stat_result, bool]]:
    root = _qualification_require_no_follow_path(
        root,
        "filesystem root",
        expected_kind="directory",
    )
    root_metadata = _qualification_lstat(root)
    if root_metadata is None:
        return []
    if (
        _qualification_metadata_is_link_or_reparse(root_metadata)
        or not stat.S_ISDIR(root_metadata.st_mode)
    ):
        raise OutcomeEvidenceVerificationError(
            "qualification root is not a regular directory"
        )
    pending = [root]
    entries = []
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as iterator:
                children = sorted(iterator, key=lambda entry: entry.name)
        except OSError as exc:
            raise OutcomeEvidenceVerificationError(
                f"cannot inspect qualification root: {exc}"
            ) from exc
        for child in children:
            path = Path(child.path)
            metadata = _qualification_lstat(path)
            if metadata is None:
                raise OutcomeEvidenceVerificationError(
                    f"qualification artifact disappeared during root scan: {path}"
                )
            is_link_or_reparse = _qualification_metadata_is_link_or_reparse(
                metadata
            )
            entries.append((path, metadata, is_link_or_reparse))
            if stat.S_ISDIR(metadata.st_mode) and not is_link_or_reparse:
                pending.append(path)
    return sorted(entries, key=lambda row: str(row[0]))


def _qualification_expected_bootstrap_summary(
    bootstrap_verification: Mapping[str, Any],
) -> dict[str, Any]:
    inventory = _mapping(
        bootstrap_verification.get("bootstrap_inventory"),
        "qualification bootstrap inventory",
    )
    entries = _sequence(
        inventory.get("entries"),
        "qualification bootstrap inventory entries",
    )
    expected_names = [
        "qualification-bootstrap-claim.json",
        *(
            f"qualification-bootstrap-stage-{index:02d}-"
            f"{name.replace('_', '-')}.json"
            for index, name in enumerate(
                QUALIFICATION_BOOTSTRAP_STAGE_NAMES,
                start=1,
            )
        ),
        "qualification-bootstrap-handoff.json",
    ]
    normalized_entries = []
    for row in entries:
        binding = _mapping(row, "qualification bootstrap inventory row")
        if (
            set(binding) != {"path", "sha256", "size"}
            or not isinstance(binding.get("path"), str)
            or not _is_sha256(binding.get("sha256"))
            or type(binding.get("size")) is not int
            or binding["size"] <= 0
        ):
            raise OutcomeEvidenceVerificationError(
                "qualification bootstrap inventory row is invalid"
            )
        normalized_entries.append(dict(binding))
    if [row["path"] for row in normalized_entries] != expected_names:
        raise OutcomeEvidenceVerificationError(
            "qualification bootstrap inventory order mismatch"
        )
    for field in (
        "claim_hash",
        "final_stage_hash",
        "handoff_hash",
        "launch_token",
    ):
        if not _is_sha256(bootstrap_verification.get(field)):
            raise OutcomeEvidenceVerificationError(
                f"qualification bootstrap {field} is invalid"
            )
    return {
        "claim_hash": bootstrap_verification["claim_hash"],
        "failure_hash": None,
        "final_stage_hash": bootstrap_verification["final_stage_hash"],
        "handoff_hash": bootstrap_verification["handoff_hash"],
        "inventory": normalized_entries,
        "launch_token": bootstrap_verification["launch_token"],
        "schema_version": QUALIFICATION_BOOTSTRAP_EVIDENCE_SCHEMA_VERSION,
    }


def _qualification_read_file_bytes(path: Path, label: str) -> bytes:
    guarded_path = _qualification_require_no_follow_path(
        path,
        label,
        expected_kind="file",
    )
    try:
        before = guarded_path.lstat()
        with open(guarded_path, "rb") as stream:
            handle_before = os.fstat(stream.fileno())
            opened_path = guarded_path.lstat()
            raw = stream.read()
            handle_after = os.fstat(stream.fileno())
        guarded_after = _qualification_require_no_follow_path(
            guarded_path,
            label,
            expected_kind="file",
        )
        after = guarded_after.lstat()
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot read qualification {label}: {exc}"
        ) from exc

    metadata_rows = (
        before,
        handle_before,
        opened_path,
        handle_after,
        after,
    )
    signatures = {
        (
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        for metadata in metadata_rows
    }
    if (
        any(
            _qualification_metadata_is_link_or_reparse(metadata)
            or not stat.S_ISREG(metadata.st_mode)
            for metadata in metadata_rows
        )
        or any(
            not os.path.samestat(before, metadata)
            for metadata in metadata_rows[1:]
        )
        or len(signatures) != 1
        or len(raw) != handle_after.st_size
    ):
        raise OutcomeEvidenceVerificationError(
            f"qualification {label} changed while being read"
        )
    return raw


def _qualification_snapshot_metadata_matches(
    expected: os.stat_result,
    observed: os.stat_result,
) -> bool:
    return os.path.samestat(expected, observed) and (
        expected.st_size,
        expected.st_mtime_ns,
        expected.st_ctime_ns,
        getattr(expected, "st_file_attributes", 0),
    ) == (
        observed.st_size,
        observed.st_mtime_ns,
        observed.st_ctime_ns,
        getattr(observed, "st_file_attributes", 0),
    )


def _qualification_snapshot_file_bytes(
    path: Path,
    *,
    expected_metadata: os.stat_result,
) -> bytes:
    before = _qualification_lstat(path)
    if before is None:
        raise OutcomeEvidenceVerificationError(
            f"qualification guarded-root entry disappeared before snapshot read: {path}"
        )
    if not _qualification_snapshot_metadata_matches(expected_metadata, before):
        raise OutcomeEvidenceVerificationError(
            f"qualification guarded-root entry changed before snapshot read: {path}"
        )
    raw = _qualification_read_file_bytes(
        path,
        f"guarded-root entry {path.name}",
    )
    after = _qualification_lstat(path)
    if after is None:
        raise OutcomeEvidenceVerificationError(
            f"qualification guarded-root entry disappeared during snapshot read: {path}"
        )
    if not _qualification_snapshot_metadata_matches(expected_metadata, after):
        raise OutcomeEvidenceVerificationError(
            f"qualification guarded-root entry changed during snapshot read: {path}"
        )
    return raw


def _qualification_guarded_root_snapshot(root: Path) -> dict[str, Any]:
    entries: dict[Path, dict[str, Any]] = {}
    errors: list[str] = []
    for path, metadata, is_link_or_reparse in _qualification_no_follow_entries(
        root
    ):
        lexical_path = Path(os.path.abspath(path))
        raw = None
        if not is_link_or_reparse and stat.S_ISREG(metadata.st_mode):
            try:
                raw = _qualification_snapshot_file_bytes(
                    lexical_path,
                    expected_metadata=metadata,
                )
            except OutcomeEvidenceVerificationError as exc:
                errors.append(str(exc))
        entries[lexical_path] = {
            "is_link_or_reparse": is_link_or_reparse,
            "metadata": metadata,
            "raw": raw,
        }
    return {
        "entries": entries,
        "errors": errors,
        "root": Path(os.path.abspath(root)),
    }


def _qualification_snapshot_entry(
    guarded_snapshot: Mapping[str, Any],
    path: Path,
) -> Mapping[str, Any] | None:
    entries = guarded_snapshot.get("entries")
    if not isinstance(entries, Mapping):
        raise OutcomeEvidenceVerificationError(
            "qualification guarded-root snapshot entries are invalid"
        )
    row = entries.get(Path(os.path.abspath(path)))
    if row is not None and not isinstance(row, Mapping):
        raise OutcomeEvidenceVerificationError(
            "qualification guarded-root snapshot row is invalid"
        )
    return row


def _qualification_snapshot_regular_file_bytes(
    guarded_snapshot: Mapping[str, Any],
    path: Path,
    *,
    label: str,
    allow_missing: bool = False,
) -> bytes | None:
    row = _qualification_snapshot_entry(guarded_snapshot, path)
    if row is None:
        if allow_missing:
            return None
        raise OutcomeEvidenceVerificationError(
            f"qualification {label} is missing from guarded snapshot"
        )
    metadata = row.get("metadata")
    raw = row.get("raw")
    if (
        not isinstance(metadata, os.stat_result)
        or row.get("is_link_or_reparse") is not False
        or not stat.S_ISREG(metadata.st_mode)
        or not isinstance(raw, bytes)
    ):
        raise OutcomeEvidenceVerificationError(
            f"qualification {label} is not a stable regular snapshot file"
        )
    return raw


def _qualification_file_observation(
    path: Path,
    *,
    label: str,
    allow_missing: bool,
) -> dict[str, Any]:
    observation, _raw = _qualification_file_observation_bytes(
        path,
        label=label,
        allow_missing=allow_missing,
    )
    return observation


def _qualification_file_observation_bytes(
    path: Path,
    *,
    label: str,
    allow_missing: bool,
) -> tuple[dict[str, Any], bytes | None]:
    guarded_path = _qualification_require_no_follow_path(
        path,
        label,
        expected_kind="file",
        allow_missing=allow_missing,
    )
    if not _qualification_path_entry_exists(guarded_path):
        return (
            {
                "exists": False,
                "path": str(guarded_path),
                "sha256": None,
                "size": None,
            },
            None,
        )
    raw = _qualification_read_file_bytes(guarded_path, label)
    return (
        {
            "exists": True,
            "path": str(guarded_path),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
        },
        raw,
    )


def _qualification_marker_count_from_bytes(raw: bytes | None) -> int:
    if raw is None:
        return 0
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot decode qualification marker file: {exc}"
        ) from exc
    markers = [line.strip() for line in lines if line.strip()]
    if any(not marker.isdigit() for marker in markers):
        raise OutcomeEvidenceVerificationError(
            "qualification marker file is invalid"
        )
    return len(markers)


def _qualification_inventory_observation(
    root: Path,
    *,
    patterns: Sequence[str] | None = None,
) -> dict[str, Any]:
    guarded_root = _qualification_require_no_follow_path(
        root,
        "isolation inventory root",
        expected_kind="directory",
    )
    normalized_patterns = None if patterns is None else list(patterns)
    if normalized_patterns is not None and (
        not normalized_patterns
        or normalized_patterns != sorted(set(normalized_patterns))
        or any(
            not isinstance(pattern, str)
            or not pattern
            or "/" in pattern
            or "\\" in pattern
            or pattern in {".", ".."}
            for pattern in normalized_patterns
        )
    ):
        raise OutcomeEvidenceVerificationError(
            "qualification isolation inventory patterns are invalid"
        )
    rows = []
    for path, metadata, is_link_or_reparse in _qualification_no_follow_entries(
        guarded_root
    ):
        if is_link_or_reparse:
            raise OutcomeEvidenceVerificationError(
                "qualification isolation inventory contains a symbolic link "
                "or reparse point"
            )
        if stat.S_ISDIR(metadata.st_mode):
            continue
        if not stat.S_ISREG(metadata.st_mode):
            raise OutcomeEvidenceVerificationError(
                "qualification isolation inventory contains a non-regular entry"
            )
        if normalized_patterns is not None and not any(
            path.match(pattern) for pattern in normalized_patterns
        ):
            continue
        raw = _qualification_read_file_bytes(path, "isolation inventory file")
        rows.append(
            {
                "kind": "file",
                "path": path.relative_to(guarded_root).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
            }
        )
    rows.sort(key=lambda row: row["path"])
    return {
        "entry_count": len(rows),
        "inventory_sha256": hashlib.sha256(
            _canonical_json(rows).encode("utf-8")
        ).hexdigest(),
        "patterns": normalized_patterns,
        "root": str(guarded_root),
        "total_bytes": sum(row["size"] for row in rows),
    }


def _qualification_parse_java_properties(raw: bytes) -> dict[str, str]:
    content = raw.decode("iso-8859-1")
    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    properties: dict[str, str] = {}
    for logical_line in _qualification_java_properties_logical_lines(lines):
        parsed = _qualification_parse_java_property(logical_line)
        if parsed is None:
            continue
        key, value = parsed
        if key in properties:
            raise OutcomeEvidenceVerificationError(
                "qualification CommunicationMod config contains a duplicate "
                "property"
            )
        properties[key] = value
    return properties


def _qualification_java_properties_logical_lines(lines: Sequence[str]):
    pending = ""
    continuing = False
    for natural_line in lines:
        if not continuing and natural_line.lstrip(" \t\f").startswith(("#", "!")):
            yield natural_line
            continue
        piece = natural_line.lstrip(" \t\f") if continuing else natural_line
        pending += piece
        trailing_backslashes = len(pending) - len(pending.rstrip("\\"))
        if trailing_backslashes % 2 == 1:
            pending = pending[:-1]
            continuing = True
            continue
        yield pending
        pending = ""
        continuing = False
    if pending or continuing:
        yield pending


def _qualification_parse_java_property(line: str) -> tuple[str, str] | None:
    content = line.lstrip(" \t\f")
    if not content or content.startswith(("#", "!")):
        return None
    key_end = len(content)
    value_start = len(content)
    escaped = False
    for index, character in enumerate(content):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character in "=: \t\f":
            key_end = index
            value_start = index
            break
    while value_start < len(content) and content[value_start] in " \t\f":
        value_start += 1
    if value_start < len(content) and content[value_start] in "=:":
        value_start += 1
    while value_start < len(content) and content[value_start] in " \t\f":
        value_start += 1
    return (
        _qualification_decode_java_property_escapes(content[:key_end]),
        _qualification_decode_java_property_escapes(content[value_start:]),
    )


def _qualification_decode_java_property_escapes(value: str) -> str:
    decoded = []
    index = 0
    escapes = {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}
    while index < len(value):
        character = value[index]
        if character != "\\":
            decoded.append(character)
            index += 1
            continue
        index += 1
        if index >= len(value):
            raise OutcomeEvidenceVerificationError(
                "invalid trailing escape in qualification CommunicationMod config"
            )
        escaped = value[index]
        if escaped == "u":
            digits = value[index + 1 : index + 5]
            if len(digits) != 4 or any(
                digit not in "0123456789abcdefABCDEF" for digit in digits
            ):
                raise OutcomeEvidenceVerificationError(
                    "invalid Unicode escape in qualification CommunicationMod config"
                )
            decoded.append(chr(int(digits, 16)))
            index += 5
            continue
        decoded.append(escapes.get(escaped, escaped))
        index += 1
    return "".join(decoded)


def _qualification_expected_isolation_observation(
    baseline: Mapping[str, Any],
) -> dict[str, Any]:
    communication = baseline["communication_mod"]
    record = {
        "checkpoints": dict(baseline["checkpoints"]),
        "communication_mod": {
            "exists": True,
            "path": communication["path"],
            "properties": dict(communication["properties"]),
            "sha256": communication["sha256"],
            "size": communication["size"],
        },
        "global_logs": {
            path: dict(observation)
            for path, observation in baseline["global_logs"].items()
        },
        "marker": dict(baseline["marker"]),
        "observation_hash": None,
        "runs": dict(baseline["runs"]),
        "schema_version": QUALIFICATION_ISOLATION_OBSERVATION_SCHEMA_VERSION,
    }
    record["observation_hash"] = _self_hash(record, "observation_hash")
    return record


def _qualification_isolation_mismatches(
    expected: Mapping[str, Any],
    observed: Mapping[str, Any],
) -> list[str]:
    mismatches = []
    for name in ("communication_mod", "marker", "runs", "checkpoints"):
        if observed[name] != expected[name]:
            mismatches.append(name)
    for path, expected_log in expected["global_logs"].items():
        if observed["global_logs"].get(path) != expected_log:
            mismatches.append(f"global_log:{path}")
    return sorted(mismatches)


def _qualification_collect_isolation(
    request: Mapping[str, Any],
) -> dict[str, Any]:
    baseline = _mapping(request.get("isolation"), "qualification isolation")
    communication_path = Path(baseline["communication_mod"]["path"])
    communication, communication_bytes = _qualification_file_observation_bytes(
        communication_path,
        label="CommunicationMod observation",
        allow_missing=True,
    )
    communication["properties"] = (
        _qualification_parse_java_properties(
            communication_bytes
        )
        if communication["exists"]
        else None
    )
    marker_path = Path(baseline["marker"]["path"])
    marker, marker_bytes = _qualification_file_observation_bytes(
        marker_path,
        label="marker observation",
        allow_missing=True,
    )
    marker["line_count"] = _qualification_marker_count_from_bytes(marker_bytes)
    checkpoints = baseline["checkpoints"]
    runs = baseline["runs"]
    record = {
        "checkpoints": _qualification_inventory_observation(
            Path(checkpoints["root"]),
            patterns=checkpoints["patterns"],
        ),
        "communication_mod": communication,
        "global_logs": {
            path: _qualification_file_observation(
                Path(path),
                label="global-log observation",
                allow_missing=True,
            )
            for path in baseline["global_logs"]
        },
        "marker": marker,
        "observation_hash": None,
        "runs": _qualification_inventory_observation(
            Path(runs["root"]),
            patterns=runs["patterns"],
        ),
        "schema_version": QUALIFICATION_ISOLATION_OBSERVATION_SCHEMA_VERSION,
    }
    record["observation_hash"] = _self_hash(record, "observation_hash")
    return json.loads(_canonical_json(record))


def _verify_qualification_file_observation(
    value: Any,
    *,
    expected_path: Path,
    label: str,
    checks: "_Checks",
    extra_fields: set[str] | None = None,
) -> Mapping[str, Any]:
    observation = _mapping(value, f"qualification {label} observation")
    extras = set() if extra_fields is None else set(extra_fields)
    checks.require(
        set(observation) == {"exists", "path", "sha256", "size", *extras},
        f"qualification {label} observation fields mismatch",
    )
    observed_path = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            observation.get("path"),
            f"qualification {label} observation path",
        ),
        f"{label} observation path",
        expected_kind="file",
        allow_missing=True,
    )
    checks.require(
        observed_path == Path(expected_path),
        f"qualification {label} observation path mismatch",
    )
    exists = observation.get("exists")
    checks.require(
        type(exists) is bool,
        f"qualification {label} observation existence is invalid",
    )
    if exists:
        checks.require(
            type(observation.get("size")) is int
            and observation["size"] >= 0
            and _is_sha256(observation.get("sha256")),
            f"qualification {label} observation fingerprint is invalid",
        )
    else:
        checks.require(
            observation.get("size") is None
            and observation.get("sha256") is None,
            f"qualification absent {label} observation fingerprint is invalid",
        )
    return observation


def _verify_qualification_inventory_observation(
    value: Any,
    *,
    expected_root: Path,
    expected_patterns: Sequence[str] | None,
    label: str,
    checks: "_Checks",
) -> Mapping[str, Any]:
    observation = _mapping(value, f"qualification {label} inventory")
    checks.require(
        set(observation)
        == {
            "entry_count",
            "inventory_sha256",
            "patterns",
            "root",
            "total_bytes",
        },
        f"qualification {label} inventory fields mismatch",
    )
    root = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            observation.get("root"),
            f"qualification {label} inventory root",
        ),
        f"{label} inventory root",
        expected_kind="directory",
    )
    normalized_patterns = (
        None if expected_patterns is None else list(expected_patterns)
    )
    checks.require(
        root == Path(expected_root)
        and observation.get("patterns") == normalized_patterns
        and type(observation.get("entry_count")) is int
        and observation["entry_count"] >= 0
        and type(observation.get("total_bytes")) is int
        and observation["total_bytes"] >= 0
        and _is_sha256(observation.get("inventory_sha256")),
        f"qualification {label} inventory binding mismatch",
    )
    return observation


def _verify_qualification_isolation_baseline(
    value: Any,
    *,
    registration: Mapping[str, Any],
    marker_path: Path,
    marker_start_count: int,
    checks: "_Checks",
) -> dict[str, Any]:
    baseline = _mapping(value, "qualification isolation baseline")
    checks.require(
        set(baseline)
        == {
            "baseline_hash",
            "checkpoints",
            "communication_mod",
            "global_logs",
            "marker",
            "runs",
            "schema_version",
        },
        "qualification isolation baseline fields mismatch",
    )
    checks.require(
        baseline.get("schema_version") == QUALIFICATION_ISOLATION_SCHEMA_VERSION,
        "qualification isolation baseline schema mismatch",
    )
    checks.require(
        _is_sha256(baseline.get("baseline_hash"))
        and baseline["baseline_hash"] == _self_hash(baseline, "baseline_hash"),
        "qualification isolation baseline hash mismatch",
    )
    integrity = _mapping(
        registration.get("integrity_rules"),
        "registration integrity rules",
    )
    checkpoint_rule = _mapping(
        integrity.get("checkpoint_inventory"),
        "registration checkpoint inventory",
    )
    checkpoint_root = _qualification_lexical_absolute_path(
        checkpoint_rule.get("root"),
        "registration checkpoint root",
    )
    checkpoint_patterns = _sequence(
        checkpoint_rule.get("patterns"),
        "registration checkpoint patterns",
    )
    game_root = checkpoint_root.parent
    run_root = Path(os.path.abspath(game_root / "runs"))
    _verify_qualification_inventory_observation(
        baseline.get("checkpoints"),
        expected_root=checkpoint_root,
        expected_patterns=checkpoint_patterns,
        label="checkpoint",
        checks=checks,
    )
    _verify_qualification_inventory_observation(
        baseline.get("runs"),
        expected_root=run_root,
        expected_patterns=None,
        label="run",
        checks=checks,
    )

    communication = _mapping(
        baseline.get("communication_mod"),
        "qualification CommunicationMod isolation binding",
    )
    checks.require(
        set(communication)
        == {"original_bytes_b64", "path", "properties", "sha256", "size"},
        "qualification CommunicationMod isolation fields mismatch",
    )
    communication_path = _qualification_lexical_absolute_path(
        communication.get("path"),
        "qualification CommunicationMod isolation path",
    )
    expected_communication_path = _qualification_lexical_absolute_path(
        integrity.get("communication_config_path"),
        "registration CommunicationMod config path",
    )
    checks.require(
        communication_path == expected_communication_path,
        "qualification CommunicationMod isolation path mismatch",
    )
    try:
        original_bytes = base64.b64decode(
            communication.get("original_bytes_b64"),
            validate=True,
        )
    except (TypeError, ValueError) as exc:
        raise OutcomeEvidenceVerificationError(
            "qualification CommunicationMod original bytes are invalid"
        ) from exc
    properties = _mapping(
        communication.get("properties"),
        "qualification CommunicationMod properties",
    )
    checks.require(
        type(communication.get("size")) is int
        and communication["size"] >= 0
        and len(original_bytes) == communication["size"]
        and hashlib.sha256(original_bytes).hexdigest()
        == communication.get("sha256")
        and dict(properties) == _qualification_parse_java_properties(original_bytes),
        "qualification CommunicationMod original-byte binding mismatch",
    )

    marker = _verify_qualification_file_observation(
        baseline.get("marker"),
        expected_path=marker_path,
        label="marker",
        checks=checks,
        extra_fields={"line_count"},
    )
    checks.require(
        type(marker.get("line_count")) is int
        and marker["line_count"] >= 0
        and marker["line_count"] == marker_start_count,
        "qualification isolation marker count mismatch",
    )
    global_logs = _mapping(
        baseline.get("global_logs"),
        "qualification global-log isolation",
    )
    expected_logs = {
        str(Path(os.path.abspath(game_root / "ai_debug.log"))),
        str(Path(os.path.abspath(game_root / "communication_mod_errors.log"))),
    }
    checks.require(
        set(global_logs) == expected_logs,
        "qualification global-log isolation paths mismatch",
    )
    for path, observation in global_logs.items():
        _verify_qualification_file_observation(
            observation,
            expected_path=Path(path),
            label="global log",
            checks=checks,
        )
    return json.loads(_canonical_json(baseline))


def _verify_qualification_isolation_observation(
    value: Any,
    *,
    baseline: Mapping[str, Any],
    checks: "_Checks",
) -> dict[str, Any]:
    observation = _mapping(value, "qualification isolation observation")
    checks.require(
        set(observation)
        == {
            "checkpoints",
            "communication_mod",
            "global_logs",
            "marker",
            "observation_hash",
            "runs",
            "schema_version",
        },
        "qualification isolation observation fields mismatch",
    )
    checks.require(
        observation.get("schema_version")
        == QUALIFICATION_ISOLATION_OBSERVATION_SCHEMA_VERSION,
        "qualification isolation observation schema mismatch",
    )
    checks.require(
        _is_sha256(observation.get("observation_hash"))
        and observation["observation_hash"]
        == _self_hash(observation, "observation_hash"),
        "qualification isolation observation hash mismatch",
    )
    communication = _verify_qualification_file_observation(
        observation.get("communication_mod"),
        expected_path=Path(baseline["communication_mod"]["path"]),
        label="CommunicationMod",
        checks=checks,
        extra_fields={"properties"},
    )
    if communication["exists"]:
        _mapping(
            communication.get("properties"),
            "qualification CommunicationMod observed properties",
        )
    else:
        checks.require(
            communication.get("properties") is None,
            "qualification absent CommunicationMod properties are invalid",
        )
    marker = _verify_qualification_file_observation(
        observation.get("marker"),
        expected_path=Path(baseline["marker"]["path"]),
        label="marker",
        checks=checks,
        extra_fields={"line_count"},
    )
    checks.require(
        type(marker.get("line_count")) is int and marker["line_count"] >= 0,
        "qualification marker observation count is invalid",
    )
    for name in ("checkpoints", "runs"):
        expected = baseline[name]
        _verify_qualification_inventory_observation(
            observation.get(name),
            expected_root=Path(expected["root"]),
            expected_patterns=expected["patterns"],
            label=name,
            checks=checks,
        )
    global_logs = _mapping(
        observation.get("global_logs"),
        "qualification global-log observation",
    )
    checks.require(
        set(global_logs) == set(baseline["global_logs"]),
        "qualification global-log observation paths mismatch",
    )
    for path, file_observation in global_logs.items():
        _verify_qualification_file_observation(
            file_observation,
            expected_path=Path(path),
            label="global log",
            checks=checks,
        )
    return json.loads(_canonical_json(observation))


def _qualification_pid_is_alive(pid: int) -> bool:
    if type(pid) is not int or pid <= 0:
        raise OutcomeEvidenceVerificationError(
            "qualification child PID is invalid"
        )
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = (
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.c_uint32,
        )
        open_process.restype = ctypes.c_void_p
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = (ctypes.c_void_p,)
        close_handle.restype = ctypes.c_int
        handle = open_process(
            process_query_limited_information,
            False,
            pid,
        )
        if handle:
            close_handle(handle)
            return True
        error = ctypes.get_last_error()
        if error == 87:
            return False
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _qualification_validate_git_metadata(repo_root: Path) -> Path:
    repo_root = _qualification_require_no_follow_path(
        repo_root,
        "Git repository root",
        expected_kind="directory",
    )
    git_root = _qualification_require_no_follow_path(
        repo_root / ".git",
        "Git metadata root",
        expected_kind="directory",
    )
    for path, _metadata, is_link_or_reparse in (
        _qualification_no_follow_entries(git_root)
    ):
        if is_link_or_reparse:
            raise OutcomeEvidenceVerificationError(
                "qualification Git metadata contains a symbolic link or "
                f"reparse point: {path}"
            )
    grafts_path = git_root / "info" / "grafts"
    if _qualification_path_entry_exists(grafts_path):
        raise OutcomeEvidenceVerificationError(
            "qualification Git graft metadata is forbidden"
        )
    attributes_path = git_root / "info" / "attributes"
    if _qualification_path_entry_exists(attributes_path):
        raise OutcomeEvidenceVerificationError(
            "qualification Git info attributes are forbidden"
        )
    for relative_path in (
        "commondir",
        "objects/info/alternates",
        "objects/info/http-alternates",
    ):
        if _qualification_path_entry_exists(git_root / relative_path):
            raise OutcomeEvidenceVerificationError(
                "qualification Git metadata indirection is forbidden: "
                f"{relative_path}"
            )
    replace_path = git_root / "refs" / "replace"
    if _qualification_path_entry_exists(replace_path):
        raise OutcomeEvidenceVerificationError(
            "qualification Git replacement refs are forbidden"
        )
    packed_refs_path = git_root / "packed-refs"
    if _qualification_path_entry_exists(packed_refs_path):
        packed_refs_path = _qualification_require_no_follow_path(
            packed_refs_path,
            "Git packed refs",
            expected_kind="file",
        )
        try:
            packed_refs = packed_refs_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OutcomeEvidenceVerificationError(
                f"cannot inspect qualification Git packed refs: {exc}"
            ) from exc
        if any(
            line.partition(" ")[2].startswith("refs/replace/")
            for line in packed_refs.splitlines()
            if line and not line.startswith(("#", "^"))
        ):
            raise OutcomeEvidenceVerificationError(
                "qualification Git packed replacement refs are forbidden"
            )
    for config_name in ("config", "config.worktree"):
        config_path = git_root / config_name
        if not _qualification_path_entry_exists(config_path):
            continue
        config_path = _qualification_require_no_follow_path(
            config_path,
            f"Git repository {config_name}",
            expected_kind="file",
        )
        try:
            config_text = config_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise OutcomeEvidenceVerificationError(
                f"cannot inspect qualification Git config: {exc}"
            ) from exc
        normalized_config = "".join(config_text.casefold().split())
        forbidden_config_tokens = (
            "[include",
            "fsmonitor",
            "hookspath",
            "external=",
            "filter",
            "clean=",
            "process=",
            "attributesfile",
            "textconv",
            "sshcommand",
            "partialclone",
            "promisor",
            "[protocol",
            "protocol.ext.allow",
            "ext::",
        )
        if any(
            token in normalized_config for token in forbidden_config_tokens
        ):
            raise OutcomeEvidenceVerificationError(
                "qualification Git repository config contains an unsafe "
                "execution directive"
            )
    return git_root


def verify_prelock_qualification(
    request_source_path: Path | str,
    result_path: Path | str | None = None,
    *,
    expected_review_commit: str,
    expected_request_hash: str,
    expected_request_file_sha256: str,
    expected_request_size: int,
    expected_result_hash: str | None = None,
    expected_result_file_sha256: str | None = None,
    expected_result_size: int | None = None,
    audit_output_path: Path | str | None = None,
) -> dict[str, Any]:
    """Independently replay one tracked pre-lock qualification evidence chain."""

    result_anchors = _qualification_result_anchors(
        result_path=result_path,
        expected_result_hash=expected_result_hash,
        expected_result_file_sha256=expected_result_file_sha256,
        expected_result_size=expected_result_size,
    )
    checks = _Checks()
    reviewed_source_path = _qualification_require_no_follow_path(
        request_source_path,
        "request source",
        expected_kind="file",
        allow_missing=True,
    )
    review = _load_historical_qualification_review(
        reviewed_source_path,
        expected_review_commit=expected_review_commit,
        expected_request_hash=expected_request_hash,
        expected_request_file_sha256=expected_request_file_sha256,
        expected_request_size=expected_request_size,
        checks=checks,
    )
    request = review["request"]
    request_schema_version = request.get("schema_version")
    current_v3 = request_schema_version == QUALIFICATION_REQUEST_SCHEMA_VERSION
    bootstrap_verification: dict[str, Any] | None = None
    qualification_root = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            request.get("qualification_root"),
            "qualification_root",
        ),
        "root",
        expected_kind="directory",
    )

    def finish_audit(**audit_fields: Any) -> dict[str, Any]:
        audit_fields["audit_schema_version"] = (
            QUALIFICATION_AUDIT_SCHEMA_VERSION
            if current_v3
            else QUALIFICATION_AUDIT_V2_SCHEMA_VERSION
        )
        audit_fields["bootstrap_verification"] = bootstrap_verification
        audit = _qualification_audit(**audit_fields)
        if audit_output_path is not None:
            bound_paths = tuple(
                Path(path)
                for path in _qualification_registration_absolute_paths(request)
            )
            raw_forbidden_roots = request.get("forbidden_paths")
            forbidden_roots = tuple(
                Path(path)
                for path in (
                    raw_forbidden_roots
                    if isinstance(raw_forbidden_roots, list)
                    else ()
                )
                if isinstance(path, str) and Path(path).is_absolute()
            )
            _qualification_write_audit_once(
                audit_output_path,
                render_verification_audit(audit),
                qualification_root=qualification_root,
                protected_paths=bound_paths,
                protected_roots=forbidden_roots,
            )
        return audit
    declared_paths = _qualification_declared_paths(
        request,
        qualification_root=qualification_root,
    )
    request_path = declared_paths["request"]
    completion_path = declared_paths["completion"]
    failure_path = declared_paths["failure"]
    control_paths = tuple(
        declared_paths[name]
        for name in ("attempt", "ready", "release")
    ) + (completion_path, failure_path)
    if current_v3:
        bootstrap_verification = _qualification_verify_bootstrap_prefix(
            request,
            review,
            active_request_bytes=None,
            checks=checks,
        )
        guarded_snapshot = checks.guarded_root_snapshot
        if guarded_snapshot is None:
            raise OutcomeEvidenceVerificationError(
                "qualification guarded-root snapshot is unavailable"
            )
        artifact_inventory = {
            str(qualification_root / row["path"]): {
                "kind": "file" if row["sha256"] is not None else "other",
                "sha256": row["sha256"],
                "size": row["size"],
            }
            for row in bootstrap_verification["bootstrap_inventory"]["entries"]
        }
        bootstrap_status = bootstrap_verification["qualification_status"]
        if bootstrap_status != "handoff_complete":
            if bootstrap_status == "reviewed_prepared":
                _verify_qualification_request(
                    request,
                    request_path=request_path,
                    registration=review["registration"],
                        registration_bytes=review["registration_bytes"],
                        request_review=review["review_binding"],
                        checks=checks,
                        guarded_snapshot=guarded_snapshot,
                    )
            if result_path is not None:
                return finish_audit(
                    checks=checks,
                    review_binding=review["review_binding"],
                    request_hash=request["request_hash"],
                    result_hash=None,
                    qualification_status="sealed_invalid",
                    status="sealed_invalid",
                    partial_stage="invalid_terminal_bootstrap",
                    consumed=True,
                    evidence_valid=False,
                    evidence_error=(
                        bootstrap_verification["evidence_error"]
                        or "qualification terminal evidence lacks a complete "
                        "bootstrap handoff"
                    ),
                    artifact_inventory=artifact_inventory,
                )
            return finish_audit(
                checks=checks,
                review_binding=review["review_binding"],
                request_hash=request["request_hash"],
                result_hash=None,
                qualification_status=bootstrap_status,
                status=bootstrap_status,
                partial_stage=bootstrap_verification["partial_stage"],
                consumed=bootstrap_verification["consumed"],
                evidence_valid=bootstrap_verification["evidence_valid"],
                evidence_error=bootstrap_verification["evidence_error"],
                artifact_inventory=artifact_inventory,
            )
        try:
            context = _verify_qualification_request(
                request,
                request_path=request_path,
                registration=review["registration"],
                registration_bytes=review["registration_bytes"],
                request_review=review["review_binding"],
                checks=checks,
                guarded_snapshot=guarded_snapshot,
            )
        except OutcomeEvidenceVerificationError as exc:
            return finish_audit(
                checks=checks,
                review_binding=review["review_binding"],
                request_hash=request["request_hash"],
                result_hash=None,
                qualification_status="sealed_invalid",
                status="sealed_invalid",
                partial_stage="invalid_active_request",
                consumed=True,
                evidence_valid=False,
                evidence_error=str(exc),
                artifact_inventory=artifact_inventory,
            )
        if result_path is not None:
            try:
                resolved_result_path = _qualification_lexical_absolute_path(
                    os.fspath(result_path),
                    "qualification result path",
                )
                checks.require(
                    resolved_result_path in {completion_path, failure_path},
                    "qualification result path does not match a terminal branch",
                )
                result_bytes = _qualification_snapshot_regular_file_bytes(
                    guarded_snapshot,
                    resolved_result_path,
                    label="result",
                )
                checks.require(
                    len(result_bytes) == result_anchors["size"],
                    "qualification result byte-count anchor mismatch",
                )
                checks.require(
                    hashlib.sha256(result_bytes).hexdigest()
                    == result_anchors["file_sha256"],
                    "qualification result file-SHA anchor mismatch",
                )
                result = _load_qualification_record_bytes(
                    result_bytes,
                    path=resolved_result_path,
                    schema_version=QUALIFICATION_RESULT_SCHEMA_VERSION,
                    hash_field="result_hash",
                    label="qualification result",
                )
                checks.require(
                    result["result_hash"] == result_anchors["result_hash"],
                    "qualification result self-hash anchor mismatch",
                )
                result_verification = _verify_qualification_result(
                    result,
                    result_path=resolved_result_path,
                    request=request,
                    context=context,
                    checks=checks,
                    bootstrap_verification=bootstrap_verification,
                    guarded_snapshot=guarded_snapshot,
                )
            except OutcomeEvidenceVerificationError as exc:
                return finish_audit(
                    checks=checks,
                    review_binding=review["review_binding"],
                    request_hash=request["request_hash"],
                    result_hash=None,
                    qualification_status="sealed_invalid",
                    status="sealed_invalid",
                    partial_stage="invalid_terminal",
                    consumed=True,
                    evidence_valid=False,
                    evidence_error=str(exc),
                    artifact_inventory=artifact_inventory,
                )
            return finish_audit(
                checks=checks,
                review_binding=result["review_binding"],
                request_hash=request["request_hash"],
                result_hash=result["result_hash"],
                qualification_status=result["status"],
                status="verified",
                partial_stage=None,
                consumed=True,
                evidence_valid=True,
                evidence_error=None,
                artifact_inventory=artifact_inventory,
                result_file_sha256=result_anchors["file_sha256"],
                result_size=result_anchors["size"],
                isolation_bound=result_verification["isolation_bound"],
                launch_qualified=result_verification["launch_qualified"],
                isolation_baseline_hash=result_verification[
                    "isolation_baseline_hash"
                ],
                isolation_post_observation_hash=result_verification[
                    "isolation_post_observation_hash"
                ],
            )
        if (
            _qualification_snapshot_entry(guarded_snapshot, completion_path)
            is not None
            or _qualification_snapshot_entry(guarded_snapshot, failure_path)
            is not None
        ):
            return finish_audit(
                checks=checks,
                review_binding=review["review_binding"],
                request_hash=request["request_hash"],
                result_hash=None,
                qualification_status="sealed_invalid",
                status="sealed_invalid",
                partial_stage="terminal_present_without_result",
                consumed=True,
                evidence_valid=False,
                evidence_error="terminal evidence requires explicit replay",
                artifact_inventory=artifact_inventory,
            )
        try:
            partial_stage = _verify_partial_qualification_prefix(
                request,
                context=context,
                checks=checks,
                guarded_snapshot=guarded_snapshot,
            )
        except OutcomeEvidenceVerificationError as exc:
            return finish_audit(
                checks=checks,
                review_binding=review["review_binding"],
                request_hash=request["request_hash"],
                result_hash=None,
                qualification_status="sealed_invalid",
                status="sealed_invalid",
                partial_stage="invalid_control_prefix",
                consumed=True,
                evidence_valid=False,
                evidence_error=str(exc),
                artifact_inventory=artifact_inventory,
            )
        return finish_audit(
            checks=checks,
            review_binding=review["review_binding"],
            request_hash=request["request_hash"],
            result_hash=None,
            qualification_status="partial",
            status="sealed_partial",
            partial_stage=partial_stage,
            consumed=True,
            evidence_valid=True,
            evidence_error=None,
            artifact_inventory=artifact_inventory,
        )
    irregular_control_paths = [
        (path, reason)
        for path in control_paths
        if (reason := _qualification_irregular_path_reason(path)) is not None
    ]
    artifact_inventory = _qualification_audit_inventory(request)
    if irregular_control_paths:
        irregular_path, irregular_reason = irregular_control_paths[0]
        evidence_error = (
            f"qualification control path {irregular_reason}: {irregular_path}"
        )
        if result_path is not None:
            raise OutcomeEvidenceVerificationError(evidence_error)
        return finish_audit(
            checks=checks,
            review_binding=review["review_binding"],
            request_hash=request["request_hash"],
            result_hash=None,
            qualification_status="invalid_partial",
            status="sealed_invalid",
            partial_stage="invalid_control_path",
            consumed=True,
            evidence_valid=False,
            evidence_error=evidence_error,
            artifact_inventory=artifact_inventory,
        )

    request_path_exists = _qualification_path_entry_exists(request_path)
    request_path_is_regular = _qualification_path_is_regular_file(request_path)
    if not request_path_is_regular:
        malformed_active = request_path_exists
        control_exists = any(
            _qualification_path_entry_exists(
                Path(request["handshake"][f"{name}_path"])
            )
            for name in ("attempt", "ready", "release")
        ) or any(
            _qualification_path_entry_exists(path)
            for path in (completion_path, failure_path)
        )
        consumed = malformed_active or control_exists
        if result_path is not None:
            reason = (
                "not a regular file"
                if malformed_active
                else "missing"
            )
            raise OutcomeEvidenceVerificationError(
                f"active qualification request is {reason}"
            )
        if not consumed:
            _verify_qualification_request(
                request,
                request_path=request_path,
                registration=review["registration"],
                registration_bytes=review["registration_bytes"],
                request_review=review["review_binding"],
                checks=checks,
            )
        return finish_audit(
            checks=checks,
            review_binding=review["review_binding"],
            request_hash=request["request_hash"],
            result_hash=None,
            qualification_status=(
                "invalid_partial" if consumed else "not_attempted"
            ),
            status="sealed_invalid" if consumed else "reviewed_prepared",
            partial_stage=(
                "malformed_active_request"
                if malformed_active
                else (
                    "orphan_control_artifacts"
                    if control_exists
                    else "source_only"
                )
            ),
            consumed=consumed,
            evidence_valid=not consumed,
            evidence_error=(
                "active qualification request is not a regular file"
                if malformed_active
                else (
                    "qualification control artifacts exist without an active request"
                    if control_exists
                    else None
                )
            ),
            artifact_inventory=artifact_inventory,
        )
    try:
        active_request_bytes = request_path.read_bytes()
    except OSError as exc:
        if result_path is not None:
            raise OutcomeEvidenceVerificationError(
                f"cannot read active qualification request: {exc}"
            ) from exc
        return finish_audit(
            checks=checks,
            review_binding=review["review_binding"],
            request_hash=request["request_hash"],
            result_hash=None,
            qualification_status="invalid_partial",
            status="sealed_invalid",
            partial_stage="malformed_active_request",
            consumed=True,
            evidence_valid=False,
            evidence_error=f"cannot read active qualification request: {exc}",
            artifact_inventory=artifact_inventory,
        )
    if active_request_bytes != review["request_bytes"]:
        if result_path is not None:
            raise OutcomeEvidenceVerificationError(
                "active request differs from reviewed source bytes"
            )
        return finish_audit(
            checks=checks,
            review_binding=review["review_binding"],
            request_hash=request["request_hash"],
            result_hash=None,
            qualification_status="invalid_partial",
            status="sealed_invalid",
            partial_stage="malformed_active_request",
            consumed=True,
            evidence_valid=False,
            evidence_error="active request differs from reviewed source bytes",
            artifact_inventory=artifact_inventory,
        )

    try:
        context = _verify_qualification_request(
            request,
            request_path=request_path,
            registration=review["registration"],
            registration_bytes=review["registration_bytes"],
            request_review=review["review_binding"],
            checks=checks,
        )
    except OutcomeEvidenceVerificationError as exc:
        if result_path is not None:
            raise
        return finish_audit(
            checks=checks,
            review_binding=review["review_binding"],
            request_hash=request["request_hash"],
            result_hash=None,
            qualification_status="invalid_partial",
            status="sealed_invalid",
            partial_stage="invalid_active_request",
            consumed=True,
            evidence_valid=False,
            evidence_error=str(exc),
            artifact_inventory=artifact_inventory,
        )

    if result_path is None:
        if _qualification_path_entry_exists(
            completion_path
        ) or _qualification_path_entry_exists(failure_path):
            return finish_audit(
                checks=checks,
                review_binding=review["review_binding"],
                request_hash=request["request_hash"],
                result_hash=None,
                qualification_status="invalid_partial",
                status="sealed_invalid",
                partial_stage="terminal_present_without_result",
                consumed=True,
                evidence_valid=False,
                evidence_error="terminal evidence requires explicit replay",
                artifact_inventory=artifact_inventory,
            )
        try:
            partial_stage = _verify_partial_qualification_prefix(
                request,
                context=context,
                checks=checks,
            )
        except OutcomeEvidenceVerificationError as exc:
            return finish_audit(
                checks=checks,
                review_binding=review["review_binding"],
                request_hash=request["request_hash"],
                result_hash=None,
                qualification_status="invalid_partial",
                status="sealed_invalid",
                partial_stage="invalid_control_prefix",
                consumed=True,
                evidence_valid=False,
                evidence_error=str(exc),
                artifact_inventory=artifact_inventory,
            )
        return finish_audit(
            checks=checks,
            review_binding=review["review_binding"],
            request_hash=request["request_hash"],
            result_hash=None,
            qualification_status="partial",
            status="sealed_partial",
            partial_stage=partial_stage,
            consumed=True,
            evidence_valid=True,
            evidence_error=None,
            artifact_inventory=artifact_inventory,
        )

    resolved_result_path = _qualification_require_no_follow_path(
        result_path,
        "result",
        expected_kind="file",
    )
    checks.require(
        resolved_result_path in {completion_path, failure_path},
        "qualification result path does not match a terminal branch",
    )
    try:
        result_bytes = resolved_result_path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot read qualification result: {exc}"
        ) from exc
    checks.require(
        len(result_bytes) == result_anchors["size"],
        "qualification result byte-count anchor mismatch",
    )
    checks.require(
        hashlib.sha256(result_bytes).hexdigest()
        == result_anchors["file_sha256"],
        "qualification result file-SHA anchor mismatch",
    )
    result = _load_qualification_record_bytes(
        result_bytes,
        path=resolved_result_path,
        schema_version={
            QUALIFICATION_REQUEST_V1_SCHEMA_VERSION: QUALIFICATION_RESULT_V1_SCHEMA_VERSION,
            QUALIFICATION_REQUEST_V2_SCHEMA_VERSION: QUALIFICATION_RESULT_V2_SCHEMA_VERSION,
            QUALIFICATION_REQUEST_SCHEMA_VERSION: QUALIFICATION_RESULT_SCHEMA_VERSION,
        }[request["schema_version"]],
        hash_field="result_hash",
        label="qualification result",
    )
    checks.require(
        result["result_hash"] == result_anchors["result_hash"],
        "qualification result self-hash anchor mismatch",
    )
    result_verification = _verify_qualification_result(
        result,
        result_path=resolved_result_path,
        request=request,
        context=context,
        checks=checks,
    )
    return finish_audit(
        checks=checks,
        review_binding=review["review_binding"],
        request_hash=request["request_hash"],
        result_hash=result["result_hash"],
        qualification_status=result["status"],
        status="verified",
        partial_stage=None,
        consumed=True,
        evidence_valid=True,
        evidence_error=None,
        artifact_inventory=artifact_inventory,
        result_file_sha256=result_anchors["file_sha256"],
        result_size=result_anchors["size"],
        isolation_bound=result_verification["isolation_bound"],
        launch_qualified=result_verification["launch_qualified"],
        isolation_baseline_hash=result_verification[
            "isolation_baseline_hash"
        ],
        isolation_post_observation_hash=result_verification[
            "isolation_post_observation_hash"
        ],
    )


def _qualification_result_anchors(
    *,
    result_path: Path | str | None,
    expected_result_hash: Any,
    expected_result_file_sha256: Any,
    expected_result_size: Any,
) -> dict[str, Any] | None:
    values = (
        expected_result_hash,
        expected_result_file_sha256,
        expected_result_size,
    )
    if result_path is None:
        if any(value is not None for value in values):
            raise OutcomeEvidenceVerificationError(
                "qualification result anchors require terminal evidence"
            )
        return None
    if any(value is None for value in values):
        raise OutcomeEvidenceVerificationError(
            "qualification terminal replay requires all result anchors"
        )
    if not _is_sha256(expected_result_hash):
        raise OutcomeEvidenceVerificationError(
            "qualification result self-hash anchor is invalid"
        )
    if not _is_sha256(expected_result_file_sha256):
        raise OutcomeEvidenceVerificationError(
            "qualification result file-SHA anchor is invalid"
        )
    if type(expected_result_size) is not int or expected_result_size <= 0:
        raise OutcomeEvidenceVerificationError(
            "qualification result byte-count anchor is invalid"
        )
    return {
        "file_sha256": expected_result_file_sha256,
        "result_hash": expected_result_hash,
        "size": expected_result_size,
    }


def _qualification_audit(
    *,
    checks: _Checks,
    review_binding: Mapping[str, Any],
    request_hash: str,
    result_hash: str | None,
    qualification_status: str,
    status: str,
    partial_stage: str | None,
    consumed: bool,
    evidence_valid: bool,
    evidence_error: str | None,
    artifact_inventory: Mapping[str, Any],
    result_file_sha256: str | None = None,
    result_size: int | None = None,
    isolation_bound: bool = False,
    launch_qualified: bool = False,
    isolation_baseline_hash: str | None = None,
    isolation_post_observation_hash: str | None = None,
    audit_schema_version: str = QUALIFICATION_AUDIT_V2_SCHEMA_VERSION,
    bootstrap_verification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    audit = {
        "audit_hash": None,
        "artifact_inventory": dict(artifact_inventory),
        "causal_claim_authorized": False,
        "check_count": checks.count,
        "collection_authorized": False,
        "consumed": consumed,
        "evidence_error": evidence_error,
        "evidence_valid": evidence_valid,
        "isolation_baseline_hash": isolation_baseline_hash,
        "isolation_bound": isolation_bound,
        "isolation_post_observation_hash": isolation_post_observation_hash,
        "launch_qualified": launch_qualified,
        "partial_stage": partial_stage,
        "passed": True,
        "qualification_status": qualification_status,
        "request_hash": request_hash,
        "review_binding": dict(review_binding),
        "result_hash": result_hash,
        "result_file_sha256": result_file_sha256,
        "result_size": result_size,
        "gameplay_policy_change_authorized": False,
        "run_lock_authorized": False,
        "schema_version": audit_schema_version,
        "status": status,
        "study_start_authorized": False,
        "training_authorized": False,
        "verifier_implementation_sha256": _file_sha256(Path(__file__)),
    }
    if audit_schema_version == QUALIFICATION_AUDIT_SCHEMA_VERSION:
        if bootstrap_verification is None:
            raise OutcomeEvidenceVerificationError(
                "qualification v3 audit requires bootstrap verification"
            )
        audit.update(
            {
                "bootstrap_inventory": dict(
                    bootstrap_verification["bootstrap_inventory"]
                ),
                "claim_hash": bootstrap_verification["claim_hash"],
                "final_stage_hash": bootstrap_verification["final_stage_hash"],
                "handoff_hash": bootstrap_verification["handoff_hash"],
                "retry_allowed": False,
            }
        )
    audit["audit_hash"] = _self_hash(audit, "audit_hash")
    return json.loads(_canonical_json(audit))


def _qualification_write_audit_once(
    output_path: Path | str,
    rendered: str,
    *,
    qualification_root: Path,
    protected_paths: Sequence[Path] = (),
    protected_roots: Sequence[Path] = (),
) -> None:
    root = _qualification_require_no_follow_path(
        qualification_root,
        "root",
        expected_kind="directory",
    )
    output = _qualification_lexical_absolute_path(
        os.fspath(output_path),
        "qualification audit output path",
    )
    output_parent = _qualification_require_no_follow_path(
        output.parent,
        "audit output parent",
        expected_kind="directory",
    )

    def canonical_path(path: Path, label: str) -> Path:
        guarded = _qualification_require_no_follow_path(
            path,
            label,
            expected_kind=None,
            allow_missing=True,
        )
        try:
            return Path(os.path.realpath(guarded))
        except OSError as exc:
            raise OutcomeEvidenceVerificationError(
                f"cannot canonicalize qualification {label}: {exc}"
            ) from exc

    def same_path(left: Path, right: Path) -> bool:
        return os.path.normcase(os.path.normpath(left)) == os.path.normcase(
            os.path.normpath(right)
        )

    def is_within(path: Path, parent: Path) -> bool:
        try:
            common = os.path.commonpath((path, parent))
        except ValueError:
            return False
        return same_path(Path(common), parent)

    canonical_output = canonical_path(
        output_parent,
        "audit output parent",
    ) / output.name
    canonical_root = canonical_path(root, "root")
    if is_within(canonical_output, canonical_root):
        raise OutcomeEvidenceVerificationError(
            "qualification audit output must be outside qualification root"
        )
    for protected_path in protected_paths:
        if same_path(
            canonical_output,
            canonical_path(protected_path, "request-bound output path"),
        ):
            raise OutcomeEvidenceVerificationError(
                "qualification audit output matches a request-bound or "
                "forbidden path"
            )
    for protected_root in protected_roots:
        if is_within(
            canonical_output,
            canonical_path(protected_root, "forbidden output path"),
        ):
            raise OutcomeEvidenceVerificationError(
                "qualification audit output matches a request-bound or "
                "forbidden path"
            )
    metadata = _qualification_lstat(output)
    if metadata is not None:
        if _qualification_metadata_is_link_or_reparse(metadata):
            raise OutcomeEvidenceVerificationError(
                "qualification audit output is a symbolic link or reparse point"
            )
        raise OutcomeEvidenceVerificationError(
            "qualification audit output already exists"
        )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    try:
        descriptor = os.open(output, flags, 0o600)
    except FileExistsError as exc:
        raise OutcomeEvidenceVerificationError(
            "qualification audit output already exists"
        ) from exc
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot create qualification audit output: {exc}"
        ) from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(rendered.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot publish qualification audit output: {exc}"
        ) from exc


def _qualification_audit_inventory(
    request: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    root = Path(str(request["qualification_root"]))
    inventory = {}
    for path, metadata, is_link_or_reparse in _qualification_no_follow_entries(
        root
    ):
        lexical_path = str(Path(os.path.abspath(path)))
        if is_link_or_reparse:
            inventory[lexical_path] = {
                "kind": "link_or_reparse",
                "sha256": None,
                "size": metadata.st_size,
            }
        elif stat.S_ISREG(metadata.st_mode):
            inventory[lexical_path] = {
                "kind": "file",
                "sha256": _file_sha256(path),
                "size": metadata.st_size,
            }
        else:
            inventory[lexical_path] = {
                "kind": (
                    "directory"
                    if stat.S_ISDIR(metadata.st_mode)
                    else "other"
                ),
                "sha256": None,
                "size": None,
            }
    return inventory


def _load_qualification_record(
    path: Path,
    *,
    schema_version: str | Sequence[str],
    hash_field: str,
    label: str,
) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot read {label}: {exc}"
        ) from exc
    return _load_qualification_record_bytes(
        raw,
        path=path,
        schema_version=schema_version,
        hash_field=hash_field,
        label=label,
    )


def _load_qualification_record_bytes(
    raw: bytes,
    *,
    path: Path,
    schema_version: str | Sequence[str],
    hash_field: str,
    label: str,
) -> dict[str, Any]:
    record = _load_mapping_bytes(raw, path)
    if raw != (_canonical_json(record) + "\n").encode("utf-8"):
        raise OutcomeEvidenceVerificationError(f"{label} is not canonical")
    accepted_schema_versions = (
        (schema_version,)
        if isinstance(schema_version, str)
        else tuple(schema_version)
    )
    if record.get("schema_version") not in accepted_schema_versions:
        raise OutcomeEvidenceVerificationError(f"{label} schema mismatch")
    if not _is_sha256(record.get(hash_field)):
        raise OutcomeEvidenceVerificationError(f"{label} self-hash is invalid")
    if record[hash_field] != _self_hash(record, hash_field):
        raise OutcomeEvidenceVerificationError(f"{label} self-hash mismatch")
    return record


def _existing_qualification_git_anchor(path: Path) -> Path:
    candidate = path
    while True:
        metadata = _qualification_lstat(candidate)
        if metadata is not None:
            if _qualification_metadata_is_link_or_reparse(metadata):
                raise OutcomeEvidenceVerificationError(
                    "qualification request repository anchor contains a "
                    "symbolic link or reparse point"
                )
            if stat.S_ISDIR(metadata.st_mode):
                return candidate
        parent = candidate.parent
        if parent == candidate:
            raise OutcomeEvidenceVerificationError(
                "qualification request repository anchor is unavailable"
            )
        candidate = parent


def _qualification_find_repository_root(path: Path) -> Path:
    candidate = _existing_qualification_git_anchor(path)
    while True:
        if _qualification_path_entry_exists(candidate / ".git"):
            _qualification_validate_git_metadata(candidate)
            return _qualification_require_no_follow_path(
                candidate,
                "repository root",
                expected_kind="directory",
            )
        parent = candidate.parent
        if parent == candidate:
            raise OutcomeEvidenceVerificationError(
                "qualification request repository is unavailable"
            )
        candidate = parent


def _load_historical_qualification_review(
    request_source_path: Path,
    *,
    expected_review_commit: str,
    expected_request_hash: str,
    expected_request_file_sha256: str,
    expected_request_size: int,
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(
        _COMMIT_PATTERN.fullmatch(expected_review_commit) is not None,
        "expected qualification review commit is invalid",
    )
    checks.require(
        _is_sha256(expected_request_hash),
        "expected qualification request hash is invalid",
    )
    checks.require(
        _is_sha256(expected_request_file_sha256),
        "expected qualification request file hash is invalid",
    )
    checks.require(
        type(expected_request_size) is int and expected_request_size > 0,
        "expected qualification request byte count is invalid",
    )
    repo_root = _qualification_find_repository_root(
        request_source_path.parent
    )
    try:
        request_source_relative = request_source_path.relative_to(
            repo_root
        ).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceVerificationError(
            "qualification request source is outside the source repository"
        ) from exc
    checks.require(
        _qualification_git_text(
            repo_root,
            "rev-parse",
            f"{expected_review_commit}^{{commit}}",
        ).lower()
        == expected_review_commit,
        "qualification review commit is unavailable",
    )
    request_bytes = _qualification_git_blob(
        repo_root,
        expected_review_commit,
        request_source_relative,
    )
    checks.require(
        hashlib.sha256(request_bytes).hexdigest()
        == expected_request_file_sha256
        and len(request_bytes) == expected_request_size,
        "qualification request source file binding mismatch",
    )
    request = _load_qualification_record_bytes(
        request_bytes,
        path=request_source_path,
        schema_version=(
            QUALIFICATION_REQUEST_V1_SCHEMA_VERSION,
            QUALIFICATION_REQUEST_V2_SCHEMA_VERSION,
            QUALIFICATION_REQUEST_SCHEMA_VERSION,
        ),
        hash_field="request_hash",
        label="qualification request source",
    )
    checks.require(
        request["request_hash"] == expected_request_hash
        and request.get("request_source_path") == str(request_source_path),
        "qualification request source anchor mismatch",
    )
    source_commit = request.get("source_commit")
    checks.require(
        isinstance(source_commit, str)
        and _COMMIT_PATTERN.fullmatch(source_commit) is not None,
        "qualification source commit is invalid",
    )
    parent_row = _qualification_git_text(
        repo_root,
        "rev-list",
        "--parents",
        "-n",
        "1",
        expected_review_commit,
    ).lower().split()
    checks.require(
        parent_row == [expected_review_commit, source_commit],
        "qualification review commit is not a direct child of the source commit",
    )

    registration_binding = _mapping(
        request.get("registration"),
        "qualification registration",
    )
    checks.require(
        set(registration_binding) == {"canonical_hash", "file_sha256", "path"},
        "qualification registration fields mismatch",
    )
    registration_path = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            registration_binding.get("path"),
            "qualification registration path",
        ),
        "registration path",
        expected_kind=None,
        allow_missing=True,
    )
    try:
        registration_relative = registration_path.relative_to(
            repo_root
        ).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceVerificationError(
            "qualification registration is outside the source repository"
        ) from exc
    registration_source_bytes = _qualification_git_blob(
        repo_root,
        source_commit,
        registration_relative,
    )
    registration_review_bytes = _qualification_git_blob(
        repo_root,
        expected_review_commit,
        registration_relative,
    )
    checks.require(
        registration_source_bytes == registration_review_bytes
        and hashlib.sha256(registration_review_bytes).hexdigest()
        == registration_binding["file_sha256"],
        "qualification registration changed during request review",
    )
    registration = _load_mapping_bytes(
        registration_review_bytes,
        registration_path,
    )
    registration_repo_root = _verify_qualification_registration_paths(
        registration,
        repo_root=repo_root,
    )
    _verify_registration(registration, checks)
    checks.require(
        registration["registration_hash"]
        == registration_binding["canonical_hash"]
        and registration_repo_root == repo_root,
        "qualification registration review binding mismatch",
    )

    implementation_paths = _registered_implementation_paths(registration)
    implementation = _mapping(
        request.get("implementation_sha256"),
        "qualification implementation_sha256",
    )
    checks.require(
        set(implementation) == set(implementation_paths),
        "qualification implementation review fields mismatch",
    )
    for relative_path in implementation_paths:
        source_bytes = _qualification_git_blob(
            repo_root,
            source_commit,
            relative_path,
        )
        review_bytes = _qualification_git_blob(
            repo_root,
            expected_review_commit,
            relative_path,
        )
        checks.require(
            source_bytes == review_bytes
            and hashlib.sha256(source_bytes).hexdigest()
            == implementation[relative_path],
            "qualification implementation changed during request review: "
            f"{relative_path}",
        )
    allowed_paths = _verify_qualification_review_allowed_paths(
        request.get("review_allowed_paths"),
        request_source_relative=request_source_relative,
        protected_paths={registration_relative, *implementation_paths},
        checks=checks,
    )
    diff_paths = sorted(
        path
        for path in _qualification_git_text(
            repo_root,
            "diff",
            "--name-only",
            "--no-renames",
            source_commit,
            expected_review_commit,
        ).splitlines()
        if path
    )
    checks.require(
        diff_paths == allowed_paths,
        "qualification review commit differs from the allowed path set",
    )
    review_binding = _expected_qualification_review_binding(
        request=request,
        review_commit=expected_review_commit,
        request_source_path=request_source_path,
        request_source_relative=request_source_relative,
        request_bytes=request_bytes,
    )
    return {
        "registration": registration,
        "registration_bytes": registration_review_bytes,
        "repo_root": repo_root,
        "request": request,
        "request_bytes": request_bytes,
        "review_binding": review_binding,
    }


def _verify_qualification_review_allowed_paths(
    value: Any,
    *,
    request_source_relative: str,
    protected_paths: set[str],
    checks: _Checks,
) -> list[str]:
    paths = _sequence(value, "qualification review allowed paths")
    normalized = list(paths)
    checks.require(
        bool(normalized)
        and all(isinstance(path, str) and path for path in normalized)
        and normalized == sorted(set(normalized)),
        "qualification review allowed paths are invalid",
    )
    for value_path in normalized:
        candidate = Path(value_path)
        checks.require(
            not candidate.is_absolute()
            and "\\" not in value_path
            and candidate.as_posix() == value_path
            and all(part not in {"", ".", ".."} for part in candidate.parts),
            "qualification review allowed path is not canonical",
        )
        checks.require(
            not _qualification_review_path_is_executable(value_path),
            "qualification review allowlist contains an executable path",
        )
    checks.require(
        request_source_relative in normalized
        and not (set(normalized) & protected_paths),
        "qualification review allowlist source/protected binding mismatch",
    )
    return normalized


def _qualification_review_path_is_executable(relative_path: str) -> bool:
    return Path(relative_path).suffix.casefold() not in QUALIFICATION_INERT_SUFFIXES


def _expected_qualification_review_binding(
    *,
    request: Mapping[str, Any],
    review_commit: str,
    request_source_path: Path,
    request_source_relative: str,
    request_bytes: bytes,
    bootstrap_summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    file_sha256 = hashlib.sha256(request_bytes).hexdigest()
    record = {
        "active_request": {
            "file_sha256": file_sha256,
            "path": request["request_path"],
            "request_hash": request["request_hash"],
            "size": len(request_bytes),
        },
        "allowed_review_paths": list(request["review_allowed_paths"]),
        "implementation_map_sha256": hashlib.sha256(
            _canonical_json(request["implementation_sha256"]).encode("utf-8")
        ).hexdigest(),
        "registration": dict(request["registration"]),
        "request_source": {
            "file_sha256": file_sha256,
            "path": str(request_source_path),
            "relative_path": request_source_relative,
            "request_hash": request["request_hash"],
            "size": len(request_bytes),
        },
        "review_binding_hash": None,
        "review_commit": review_commit,
        "schema_version": (
            QUALIFICATION_REVIEW_BINDING_SCHEMA_VERSION
            if request.get("schema_version") == QUALIFICATION_REQUEST_SCHEMA_VERSION
            else QUALIFICATION_REVIEW_BINDING_V1_SCHEMA_VERSION
        ),
        "source_commit": request["source_commit"],
    }
    if bootstrap_summary is not None:
        if request.get("schema_version") != QUALIFICATION_REQUEST_SCHEMA_VERSION:
            raise OutcomeEvidenceVerificationError(
                "historical qualification review cannot bind bootstrap evidence"
            )
        record["bootstrap"] = dict(bootstrap_summary)
    record["review_binding_hash"] = _self_hash(
        record,
        "review_binding_hash",
    )
    return json.loads(_canonical_json(record))


def _expected_qualification_child_command(
    registration: Mapping[str, Any],
    request_schema_version: str,
) -> list[str]:
    command_record = _mapping(registration.get("command"), "registered command")
    interpreter_flags = ["-I", "-S"]
    if request_schema_version == QUALIFICATION_REQUEST_SCHEMA_VERSION:
        interpreter_flags.append("-B")
    elif request_schema_version not in {
        QUALIFICATION_REQUEST_V1_SCHEMA_VERSION,
        QUALIFICATION_REQUEST_V2_SCHEMA_VERSION,
    }:
        raise OutcomeEvidenceVerificationError(
            "qualification request schema is unsupported"
        )
    return [
        command_record["python_executable"],
        *interpreter_flags,
        command_record["main_path"],
        *_sequence(command_record["arguments"], "registered arguments"),
    ]


def _verify_qualification_request(
    request: Mapping[str, Any],
    *,
    request_path: Path,
    registration: Mapping[str, Any],
    registration_bytes: bytes,
    request_review: Mapping[str, Any],
    checks: _Checks,
    guarded_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    schema_version = request.get("schema_version")
    checks.require(
        schema_version
        in {
            QUALIFICATION_REQUEST_V1_SCHEMA_VERSION,
            QUALIFICATION_REQUEST_V2_SCHEMA_VERSION,
            QUALIFICATION_REQUEST_SCHEMA_VERSION,
        },
        "qualification request schema is unsupported",
    )
    expected_fields = {
        "child_command",
        "completion_path",
        "config",
        "created_unix_ns",
        "failure_path",
        "forbidden_paths",
        "handshake",
        "implementation_sha256",
        "marker",
        "preexisting_files",
        "qualification_id",
        "qualification_root",
        "registration",
        "request_hash",
        "request_path",
        "request_source_path",
        "review_allowed_paths",
        "schema_version",
        "source_commit",
    }
    if schema_version in {
        QUALIFICATION_REQUEST_V2_SCHEMA_VERSION,
        QUALIFICATION_REQUEST_SCHEMA_VERSION,
    }:
        expected_fields.add("isolation")
    if schema_version == QUALIFICATION_REQUEST_SCHEMA_VERSION:
        expected_fields.add("bootstrap")
    checks.require(
        set(request) == expected_fields,
        "qualification request fields mismatch",
    )
    created = _exact_int(
        request.get("created_unix_ns"),
        "qualification request created_unix_ns",
    )
    checks.require(created > 0, "qualification request timestamp is invalid")
    qualification_id = _required_string(
        request.get("qualification_id"),
        "qualification_id",
    )
    checks.require(
        _STUDY_PATTERN.fullmatch(qualification_id) is not None,
        "qualification_id is invalid",
    )
    qualification_root = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            request.get("qualification_root"),
            "qualification_root",
        ),
        "root",
        expected_kind="directory",
    )
    expected_request_path = Path(
        os.path.abspath(qualification_root / "qualification-request.json")
    )
    checks.require(
        qualification_root.is_dir()
        and request_path == expected_request_path
        and request.get("request_path") == str(request_path),
        "qualification request root/path mismatch",
    )
    request_source_path = _qualification_lexical_absolute_path(
        request.get("request_source_path"),
        "qualification request source path",
    )
    checks.require(
        request_source_path != request_path,
        "qualification request source matches its active path",
    )

    registration_binding = _mapping(
        request.get("registration"),
        "qualification registration",
    )
    checks.require(
        set(registration_binding) == {"canonical_hash", "file_sha256", "path"},
        "qualification registration fields mismatch",
    )
    registration_path = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            registration_binding.get("path"),
            "qualification registration path",
        ),
        "registration path",
        expected_kind=None,
        allow_missing=True,
    )
    checks.require(
        registration_binding
        == {
            "canonical_hash": registration["registration_hash"],
            "file_sha256": hashlib.sha256(registration_bytes).hexdigest(),
            "path": str(registration_path),
        },
        "qualification registration binding mismatch",
    )

    source_commit = request.get("source_commit")
    checks.require(
        isinstance(source_commit, str)
        and _COMMIT_PATTERN.fullmatch(source_commit) is not None,
        "qualification source commit is invalid",
    )
    repo_root = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            registration.get("repo_root"),
            "qualification registration repository root",
        ),
        "registered repository root",
        expected_kind="directory",
    )
    implementation = _mapping(
        request.get("implementation_sha256"),
        "qualification implementation_sha256",
    )
    checks.require(
        set(implementation) == set(_registered_implementation_paths(registration))
        and all(_is_sha256(value) for value in implementation.values()),
        "qualification implementation binding mismatch",
    )
    checks.require(
        request_review
        == _expected_qualification_review_binding(
            request=request,
            review_commit=str(request_review["review_commit"]),
            request_source_path=request_source_path,
            request_source_relative=str(
                request_review["request_source"]["relative_path"]
            ),
            request_bytes=(
                _canonical_json(request) + "\n"
            ).encode("utf-8"),
        ),
        "qualification request review binding mismatch",
    )

    checks.require(
        request.get("child_command")
        == _expected_qualification_child_command(registration, schema_version),
        "qualification child command mismatch",
    )
    config_binding = _mapping(request.get("config"), "qualification config")
    checks.require(
        set(config_binding) == {"path", "sha256"},
        "qualification config fields mismatch",
    )
    config_path = _qualification_lexical_absolute_path(
        config_binding.get("path"),
        "qualification config path",
    )
    if guarded_snapshot is None:
        config_path = _qualification_require_no_follow_path(
            config_path,
            "config",
            expected_kind="file",
        )
        checks.require(
            _qualification_path_is_regular_file(config_path)
            and config_path.is_relative_to(qualification_root)
            and config_binding.get("sha256") == _file_sha256(config_path),
            "qualification config binding mismatch",
        )
        config = _load_mapping(config_path)
    else:
        config_raw = _qualification_snapshot_regular_file_bytes(
            guarded_snapshot,
            config_path,
            label="config",
        )
        if config_raw is None:
            raise OutcomeEvidenceVerificationError(
                "qualification config snapshot is missing"
            )
        checks.require(
            config_path.is_relative_to(qualification_root)
            and config_binding.get("sha256")
            == hashlib.sha256(config_raw).hexdigest(),
            "qualification config binding mismatch",
        )
        config = _load_mapping_bytes(config_raw, config_path)
    _verify_qualification_config(
        config,
        config_path=config_path,
        qualification_id=qualification_id,
        registration=registration,
        source_commit=source_commit,
        checks=checks,
    )

    marker_binding = _mapping(request.get("marker"), "qualification marker")
    checks.require(
        set(marker_binding) == {"path", "start_count"},
        "qualification marker fields mismatch",
    )
    marker_path = _qualification_lexical_absolute_path(
        marker_binding.get("path"),
        "qualification marker path",
    )
    integrity_rules = _mapping(
        registration.get("integrity_rules"),
        "registration integrity rules",
    )
    checkpoint_inventory = _mapping(
        integrity_rules.get("checkpoint_inventory"),
        "registration checkpoint inventory",
    )
    checkpoint_root = _qualification_require_no_follow_path(
        _qualification_lexical_absolute_path(
            checkpoint_inventory.get("root"),
            "registration checkpoint root",
        ),
        "registered checkpoint root",
        expected_kind=None,
        allow_missing=True,
    )
    expected_marker_path = Path(
        os.path.abspath(checkpoint_root.parent / "runs" / "ai_games.txt")
    )
    checks.require(
        marker_path == expected_marker_path,
        "qualification marker path does not match the registered game root",
    )
    marker_count = _qualification_marker_count(marker_path)
    if schema_version == QUALIFICATION_REQUEST_V1_SCHEMA_VERSION:
        checks.require(
            marker_binding.get("start_count") == marker_count,
            "qualification marker binding mismatch",
        )
    isolation = None
    if schema_version in {
        QUALIFICATION_REQUEST_V2_SCHEMA_VERSION,
        QUALIFICATION_REQUEST_SCHEMA_VERSION,
    }:
        isolation = _verify_qualification_isolation_baseline(
            request.get("isolation"),
            registration=registration,
            marker_path=marker_path,
            marker_start_count=marker_binding["start_count"],
            checks=checks,
        )

    handshake = _mapping(request.get("handshake"), "qualification handshake")
    expected_handshake = _expected_qualification_handshake(
        qualification_root=qualification_root,
        qualification_id=qualification_id,
        registration=registration,
    )
    checks.require(
        dict(handshake) == expected_handshake,
        "qualification handshake binding mismatch",
    )
    completion_path = Path(
        os.path.abspath(qualification_root / "qualification-completion.json")
    )
    failure_path = Path(
        os.path.abspath(qualification_root / "qualification-failure.json")
    )
    checks.require(
        request.get("completion_path") == str(completion_path)
        and request.get("failure_path") == str(failure_path),
        "qualification terminal path mismatch",
    )
    artifact_root = _qualification_lexical_absolute_path(
        registration.get("artifact_root"),
        "qualification artifact root",
    )
    expected_forbidden = sorted(
        {
            str(artifact_root),
            str(Path(os.path.abspath(artifact_root / "run-lock.json"))),
            str(Path(os.path.abspath(artifact_root / "study-ledger.jsonl"))),
            str(
                _qualification_lexical_absolute_path(
                    config["manifest_path"],
                    "qualification manifest path",
                )
            ),
            str(
                _qualification_lexical_absolute_path(
                    config["trace_path"],
                    "qualification trace path",
                )
            ),
        }
    )
    checks.require(
        request.get("forbidden_paths") == expected_forbidden,
        "qualification forbidden-path binding mismatch",
    )
    for forbidden_path in expected_forbidden:
        _qualification_require_no_follow_path(
            forbidden_path,
            "forbidden path",
            expected_kind=None,
            allow_missing=True,
        )
    checks.require(
        not any(
            _qualification_path_entry_exists(Path(path))
            for path in expected_forbidden
        ),
        "qualification forbidden path exists",
    )
    excluded_paths = {
        request_path,
        completion_path,
        failure_path,
        *(Path(handshake[f"{name}_path"]) for name in ("attempt", "ready", "release")),
        *(Path(path) for path in expected_forbidden),
    }
    if schema_version == QUALIFICATION_REQUEST_SCHEMA_VERSION:
        excluded_paths.update(
            _qualification_bootstrap_declared_paths(
                request,
                qualification_root,
            ).values()
        )
    expected_inventory = _qualification_file_inventory(
        qualification_root,
        excluded_paths=excluded_paths,
        guarded_snapshot=guarded_snapshot,
    )
    checks.require(
        request.get("preexisting_files") == expected_inventory,
        "qualification preexisting file inventory mismatch",
    )
    return {
        "config": config,
        "handshake": expected_handshake,
        "marker_count": marker_count,
        "registration": registration,
        "request_review": request_review,
        "isolation": isolation,
        "isolation_bound": isolation is not None,
        "request_schema_version": schema_version,
    }


def _verify_partial_qualification_prefix(
    request: Mapping[str, Any],
    *,
    context: Mapping[str, Any],
    checks: _Checks,
    guarded_snapshot: Mapping[str, Any] | None = None,
) -> str:
    completion_path = Path(str(request["completion_path"]))
    failure_path = Path(str(request["failure_path"]))
    if guarded_snapshot is None:
        terminal_exists = _qualification_path_entry_exists(
            completion_path
        ) or _qualification_path_entry_exists(failure_path)
    else:
        terminal_exists = (
            _qualification_snapshot_entry(guarded_snapshot, completion_path)
            is not None
            or _qualification_snapshot_entry(guarded_snapshot, failure_path)
            is not None
        )
    checks.require(
        not terminal_exists,
        "partial qualification has a terminal result",
    )

    request_handshake = _mapping(
        request.get("handshake"),
        "qualification handshake",
    )
    paths = {
        name: Path(str(request_handshake[f"{name}_path"]))
        for name in ("attempt", "ready", "release")
    }
    records = {}
    for name, path in paths.items():
        if guarded_snapshot is None:
            if not _qualification_path_entry_exists(path):
                continue
            checks.require(
                _qualification_path_is_regular_file(path),
                f"qualification {name} artifact is not a regular file",
            )
            records[name] = _load_canonical_handshake_record(
                path,
                f"qualification {name}",
            )
        else:
            raw = _qualification_snapshot_regular_file_bytes(
                guarded_snapshot,
                path,
                label=f"{name} artifact",
                allow_missing=True,
            )
            if raw is not None:
                records[name] = _load_canonical_handshake_record_bytes(
                    raw,
                    path=path,
                    label=f"qualification {name}",
                )
    checks.require(
        "ready" not in records or "attempt" in records,
        "qualification ready exists without attempt",
    )
    checks.require(
        "release" not in records or "ready" in records,
        "qualification release exists without ready",
    )

    attempt = None
    ready = None
    if "attempt" in records:
        synthetic_registration = dict(context["registration"])
        synthetic_registration["study_id"] = request["qualification_id"]
        config_bytes = None
        if guarded_snapshot is not None:
            config_bytes = _qualification_snapshot_regular_file_bytes(
                guarded_snapshot,
                Path(str(request["config"]["path"])),
                label="config",
            )
        attempt = _verify_handshake_attempt(
            records["attempt"],
            registration=synthetic_registration,
            run_lock={"run_lock_hash": "0" * 64},
            slot={
                "config_path": request["config"]["path"],
                "session_id": request_handshake["session_id"],
                "slot_number": 1,
            },
            paths=paths,
            rules={
                "readiness_timeout_seconds": 120,
                "release_timeout_seconds": 10,
            },
            expected_marker_start=request["marker"]["start_count"],
            checks=checks,
            config_bytes=config_bytes,
        )
    if "ready" in records:
        ready = _verify_handshake_ready(
            records["ready"],
            attempt=attempt,
            checks=checks,
        )
    if "release" in records:
        _verify_handshake_release(
            records["release"],
            attempt=attempt,
            ready=ready,
            checks=checks,
        )
    _verify_partial_qualification_timestamps(
        request=request,
        handshake_records=records,
        checks=checks,
    )
    if "release" in records:
        return "release_without_result"
    if "ready" in records:
        return "ready_without_release"
    if "attempt" in records:
        return "attempt_only"
    return "request_only"


def _verify_partial_qualification_timestamps(
    *,
    request: Mapping[str, Any],
    handshake_records: Mapping[str, Mapping[str, Any]],
    checks: _Checks,
) -> None:
    previous = _exact_int(
        request.get("created_unix_ns"),
        "qualification request created_unix_ns",
    )
    ordered = True
    for name in ("attempt", "ready", "release"):
        record = handshake_records.get(name)
        if record is None:
            continue
        created = _exact_int(
            record.get("created_unix_ns"),
            f"qualification {name} created_unix_ns",
        )
        ordered = ordered and previous <= created
        previous = created
    checks.require(
        ordered,
        "partial qualification lifecycle timestamp order is invalid",
    )


def _verify_qualification_result_isolation(
    result: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    context: Mapping[str, Any],
    process_pid: int | None,
    checks: _Checks,
) -> dict[str, Any]:
    baseline = _mapping(context.get("isolation"), "qualification isolation baseline")
    isolation = _mapping(
        result.get("isolation"),
        "qualification result isolation",
    )
    checks.require(
        set(isolation)
        == {
            "baseline_hash",
            "child_alive",
            "communication_restored",
            "matched",
            "mismatches",
            "observation_error",
            "post_observation",
            "post_observation_hash",
            "restoration_error",
        },
        "qualification result isolation fields mismatch",
    )
    checks.require(
        isolation.get("baseline_hash") == baseline["baseline_hash"],
        "qualification result isolation baseline binding mismatch",
    )
    for field in ("communication_restored", "matched"):
        checks.require(
            type(isolation.get(field)) is bool,
            f"qualification result isolation {field} flag is invalid",
        )
    mismatches = _sequence(
        isolation.get("mismatches"),
        "qualification result isolation mismatches",
    )
    checks.require(
        list(mismatches) == sorted(set(mismatches))
        and all(isinstance(item, str) and item for item in mismatches),
        "qualification result isolation mismatches are invalid",
    )
    for field in ("observation_error", "restoration_error"):
        error = isolation.get(field)
        checks.require(
            error is None or (isinstance(error, str) and bool(error)),
            f"qualification result isolation {field} is invalid",
        )
    checks.require(
        isolation.get("observation_error") is None,
        "qualification result isolation observation is incomplete",
    )
    post_observation = _verify_qualification_isolation_observation(
        isolation.get("post_observation"),
        baseline=baseline,
        checks=checks,
    )
    checks.require(
        isolation.get("post_observation_hash")
        == post_observation["observation_hash"],
        "qualification result post-observation binding mismatch",
    )
    current_observation = _qualification_collect_isolation(request)
    checks.require(
        current_observation == post_observation,
        "qualification restored isolation resource drift",
    )
    expected_observation = _qualification_expected_isolation_observation(
        baseline
    )
    expected_mismatches = _qualification_isolation_mismatches(
        expected_observation,
        post_observation,
    )
    communication_restored = isolation["communication_restored"]
    if not communication_restored:
        expected_mismatches.append("communication_restore")
    child_alive = isolation.get("child_alive")
    checks.require(
        child_alive is False,
        "qualification result child PID liveness is ambiguous or alive",
    )
    independently_alive = (
        False if process_pid is None else _qualification_pid_is_alive(process_pid)
    )
    checks.require(
        independently_alive is False,
        "qualification owned child PID is still alive",
    )
    expected_mismatches = sorted(set(expected_mismatches))
    checks.require(
        list(mismatches) == expected_mismatches,
        "qualification result isolation mismatch labels differ",
    )
    matched = (
        not expected_mismatches
        and communication_restored is True
        and isolation.get("restoration_error") is None
    )
    checks.require(
        isolation["matched"] is matched,
        "qualification result isolation comparison flag differs",
    )
    isolation_complete = matched and post_observation == expected_observation
    launch_qualified = (
        result.get("status") == "passed" and isolation_complete
    )
    return {
        "isolation_complete": isolation_complete,
        "isolation_baseline_hash": baseline["baseline_hash"],
        "isolation_bound": True,
        "isolation_post_observation_hash": post_observation[
            "observation_hash"
        ],
        "launch_qualified": launch_qualified,
    }


def _verify_qualification_result(
    result: Mapping[str, Any],
    *,
    result_path: Path,
    request: Mapping[str, Any],
    context: Mapping[str, Any],
    checks: _Checks,
    bootstrap_verification: Mapping[str, Any] | None = None,
    guarded_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result_schema_version = result.get("schema_version")
    expected_result_schema = (
        {
            QUALIFICATION_REQUEST_V1_SCHEMA_VERSION: QUALIFICATION_RESULT_V1_SCHEMA_VERSION,
            QUALIFICATION_REQUEST_V2_SCHEMA_VERSION: QUALIFICATION_RESULT_V2_SCHEMA_VERSION,
            QUALIFICATION_REQUEST_SCHEMA_VERSION: QUALIFICATION_RESULT_SCHEMA_VERSION,
        }[context["request_schema_version"]]
    )
    checks.require(
        result_schema_version == expected_result_schema,
        "qualification result schema does not match request",
    )
    expected_fields = {
        "authority",
        "child_command",
        "config",
        "created_unix_ns",
        "ended_unix_ns",
        "failure",
        "forbidden_paths",
        "handshake",
        "implementation_sha256",
        "marker",
        "process",
        "registration",
        "request",
        "review_binding",
        "result_hash",
        "schema_version",
        "source_commit",
        "status",
    }
    if result_schema_version in {
        QUALIFICATION_RESULT_V2_SCHEMA_VERSION,
        QUALIFICATION_RESULT_SCHEMA_VERSION,
    }:
        expected_fields.add("isolation")
    expected_bootstrap = None
    if result_schema_version == QUALIFICATION_RESULT_SCHEMA_VERSION:
        expected_fields.add("bootstrap")
        if bootstrap_verification is None:
            raise OutcomeEvidenceVerificationError(
                "qualification result v3 requires bootstrap replay"
            )
        expected_bootstrap = _qualification_expected_bootstrap_summary(
            bootstrap_verification
        )
        checks.require(
            result.get("bootstrap") == expected_bootstrap,
            "qualification result bootstrap binding mismatch",
        )
    checks.require(
        set(result) == expected_fields,
        "qualification result fields mismatch",
    )
    status = result.get("status")
    checks.require(status in {"passed", "failed"}, "qualification status invalid")
    expected_result_path = Path(
        request["completion_path"] if status == "passed" else request["failure_path"]
    )
    opposite_result_path = Path(
        request["failure_path"] if status == "passed" else request["completion_path"]
    )
    checks.require(
        result_path == expected_result_path,
        "qualification result path contradicts status",
    )
    opposite_exists = (
        _qualification_path_entry_exists(opposite_result_path)
        if guarded_snapshot is None
        else _qualification_snapshot_entry(
            guarded_snapshot,
            opposite_result_path,
        )
        is not None
    )
    checks.require(
        not opposite_exists,
        "qualification terminal branches are not exclusive",
    )
    created = _exact_int(result.get("created_unix_ns"), "qualification result start")
    ended = _exact_int(result.get("ended_unix_ns"), "qualification result end")
    checks.require(
        created > 0 and ended >= created,
        "qualification result timestamps are invalid",
    )
    checks.require(
        result.get("request")
        == {"hash": request["request_hash"], "path": request["request_path"]},
        "qualification result request binding mismatch",
    )
    for field in (
        "child_command",
        "config",
        "implementation_sha256",
        "registration",
        "source_commit",
    ):
        checks.require(
            result.get(field) == request[field],
            f"qualification result {field} binding mismatch",
        )
    expected_review_binding = context["request_review"]
    if result_schema_version == QUALIFICATION_RESULT_SCHEMA_VERSION:
        active_request_bytes = _qualification_snapshot_regular_file_bytes(
            guarded_snapshot,
            Path(request["request_path"]),
            label="active request",
        )
        request_review = _mapping(
            context.get("request_review"),
            "qualification request review binding",
        )
        source_binding = _mapping(
            request_review.get("request_source"),
            "qualification request source review binding",
        )
        expected_review_binding = _expected_qualification_review_binding(
            request=request,
            review_commit=str(request_review["review_commit"]),
            request_source_path=Path(str(source_binding["path"])),
            request_source_relative=str(source_binding["relative_path"]),
            request_bytes=active_request_bytes,
            bootstrap_summary=expected_bootstrap,
        )
    checks.require(
        result.get("review_binding") == expected_review_binding,
        "qualification result review binding mismatch",
    )
    authority = _mapping(result.get("authority"), "qualification authority")
    checks.require(
        set(authority)
        == {
            "causal_claim",
            "collection",
            "gameplay_policy_change",
            "run_lock",
            "study_start",
            "training",
        }
        and all(
            type(value) is bool and value is False
            for value in authority.values()
        ),
        "qualification authority must remain false",
    )
    forbidden = _mapping(
        result.get("forbidden_paths"),
        "qualification forbidden-path evidence",
    )
    expected_forbidden = {
        path: _qualification_path_entry_exists(Path(path))
        for path in request["forbidden_paths"]
    }
    checks.require(
        set(forbidden) == set(expected_forbidden)
        and all(
            type(forbidden[path]) is bool
            and forbidden[path] is expected_forbidden[path]
            for path in expected_forbidden
        ),
        "qualification forbidden-path result mismatch",
    )
    marker = _mapping(result.get("marker"), "qualification marker result")
    checks.require(
        marker
        == {
            "end_count": context["marker_count"],
            "path": request["marker"]["path"],
            "start_count": request["marker"]["start_count"],
        },
        "qualification marker result mismatch",
    )
    process = _mapping(result.get("process"), "qualification process result")
    checks.require(
        set(process)
        == {
            "cleanup_attempted",
            "cleanup_error",
            "exit_code",
            "launch_count",
            "pid",
        },
        "qualification process fields mismatch",
    )
    process_pid = process.get("pid")
    checks.require(
        process_pid is None or (type(process_pid) is int and process_pid > 0),
        "qualification process PID is invalid",
    )
    checks.require(
        type(process.get("launch_count")) is int
        and process["launch_count"] in {0, 1},
        "qualification launch count is invalid",
    )
    exit_code = process.get("exit_code")
    checks.require(
        exit_code is None or type(exit_code) is int,
        "qualification process exit code is invalid",
    )
    cleanup_attempted = process.get("cleanup_attempted")
    cleanup_error = process.get("cleanup_error")
    checks.require(
        type(cleanup_attempted) is bool,
        "qualification cleanup flag is invalid",
    )
    checks.require(
        cleanup_error is None
        or (isinstance(cleanup_error, str) and bool(cleanup_error)),
        "qualification cleanup error is invalid",
    )
    checks.require(
        cleanup_error is None or cleanup_attempted is True,
        "qualification cleanup error lacks an attempted cleanup",
    )
    if result_schema_version in {
        QUALIFICATION_RESULT_V2_SCHEMA_VERSION,
        QUALIFICATION_RESULT_SCHEMA_VERSION,
    }:
        isolation_verification = _verify_qualification_result_isolation(
            result,
            request=request,
            context=context,
            process_pid=process_pid,
            checks=checks,
        )
    else:
        isolation_verification = {
            "isolation_complete": False,
            "isolation_baseline_hash": None,
            "isolation_bound": False,
            "isolation_post_observation_hash": None,
            "launch_qualified": False,
        }
    handshake_records = _verify_qualification_handshake_result(
        result,
        request=request,
        registration=context["registration"],
        checks=checks,
        guarded_snapshot=guarded_snapshot,
    )
    _verify_qualification_lifecycle_timestamps(
        request=request,
        result=result,
        handshake_records=handshake_records,
        checks=checks,
    )
    handshake_complete = all(
        _mapping(result["handshake"][name], f"qualification {name} result").get(
            "sha256"
        )
        is not None
        for name in ("attempt", "ready", "release")
    )
    attempt_hash = result["handshake"]["attempt"]["sha256"]
    ready_hash = result["handshake"]["ready"]["sha256"]
    release_hash = result["handshake"]["release"]["sha256"]
    checks.require(
        process["launch_count"] != 1 or attempt_hash is not None,
        "qualification launched child lacks attempt evidence",
    )
    checks.require(
        process["launch_count"] != 0
        or not any(
            (
                process_pid is not None,
                exit_code is not None,
                cleanup_attempted,
                cleanup_error is not None,
                ready_hash is not None,
                release_hash is not None,
            )
        ),
        "qualification process evidence contradicts launch count",
    )
    checks.require(
        ready_hash is None
        or (
            process["launch_count"] == 1
            and process_pid is not None
            and attempt_hash is not None
        ),
        "qualification ready evidence requires one launched child",
    )
    checks.require(
        release_hash is None or ready_hash is not None,
        "qualification release evidence lacks ready evidence",
    )
    success_evidence_complete = (
        process["launch_count"] == 1
        and process_pid is not None
        and process.get("exit_code") == 0
        and process.get("cleanup_attempted") is False
        and process.get("cleanup_error") is None
        and context["marker_count"] == request["marker"]["start_count"]
        and not any(forbidden.values())
        and handshake_complete
        and (
            result_schema_version == QUALIFICATION_RESULT_V1_SCHEMA_VERSION
            or isolation_verification["isolation_complete"] is True
        )
    )
    if result_schema_version == QUALIFICATION_RESULT_SCHEMA_VERSION:
        checks.require(
            status == "passed" and success_evidence_complete,
            "qualification v3 terminal lifecycle is incomplete",
        )
    if status == "passed":
        checks.require(
            result.get("failure") is None and success_evidence_complete,
            "qualification passed result contradicts evidence",
        )
    else:
        failure = _mapping(result.get("failure"), "qualification failure")
        checks.require(
            set(failure) == {"exception_type", "message", "stage"}
            and all(isinstance(value, str) and value for value in failure.values()),
            "qualification failure evidence is invalid",
        )
        checks.require(
            not success_evidence_complete,
            "qualification failed result does not contradict success evidence",
        )
    return isolation_verification


def _verify_qualification_handshake_result(
    result: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
    guarded_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    handshake_result = _mapping(
        result.get("handshake"),
        "qualification handshake result",
    )
    checks.require(
        set(handshake_result) == {"attempt", "ready", "release"},
        "qualification handshake result fields mismatch",
    )
    request_handshake = request["handshake"]
    records = {}
    for name in ("attempt", "ready", "release"):
        binding = _mapping(
            handshake_result.get(name),
            f"qualification {name} result",
        )
        path = Path(request_handshake[f"{name}_path"])
        raw = None
        if guarded_snapshot is None:
            path_is_regular = _qualification_path_is_regular_file(path)
            expected_sha = _file_sha256(path) if path_is_regular else None
        else:
            raw = _qualification_snapshot_regular_file_bytes(
                guarded_snapshot,
                path,
                label=f"{name} artifact",
                allow_missing=True,
            )
            path_is_regular = raw is not None
            expected_sha = (
                None if raw is None else hashlib.sha256(raw).hexdigest()
            )
        checks.require(
            binding == {"path": str(path), "sha256": expected_sha},
            f"qualification {name} result hash mismatch",
        )
        if path_is_regular:
            records[name] = (
                _load_canonical_handshake_record(
                    path,
                    f"qualification {name}",
                )
                if raw is None
                else _load_canonical_handshake_record_bytes(
                    raw,
                    path=path,
                    label=f"qualification {name}",
                )
            )
    if "attempt" not in records:
        checks.require(
            result["status"] == "failed" and not records,
            "qualification ready/release exists without attempt",
        )
        return records
    synthetic_registration = dict(registration)
    synthetic_registration["study_id"] = request["qualification_id"]
    paths = {
        name: Path(request_handshake[f"{name}_path"])
        for name in ("attempt", "ready", "release")
    }
    slot = {
        "config_path": request["config"]["path"],
        "session_id": request_handshake["session_id"],
        "slot_number": 1,
    }
    attempt = _verify_handshake_attempt(
        records["attempt"],
        registration=synthetic_registration,
        run_lock={"run_lock_hash": "0" * 64},
        slot=slot,
        paths=paths,
        rules={
            "readiness_timeout_seconds": 120,
            "release_timeout_seconds": 10,
        },
        expected_marker_start=request["marker"]["start_count"],
        checks=checks,
        config_bytes=(
            None
            if guarded_snapshot is None
            else _qualification_snapshot_regular_file_bytes(
                guarded_snapshot,
                Path(request["config"]["path"]),
                label="config",
            )
        ),
    )
    if "ready" not in records:
        checks.require(
            result["status"] == "failed" and "release" not in records,
            "qualification release exists without ready",
        )
        return records
    ready = _verify_handshake_ready(records["ready"], attempt=attempt, checks=checks)
    checks.require(
        result["process"]["pid"] == ready["child_pid"],
        "qualification child PID differs from ready",
    )
    if "release" not in records:
        checks.require(
            result["status"] == "failed",
            "passed qualification release is missing",
        )
        return records
    _verify_handshake_release(
        records["release"],
        attempt=attempt,
        ready=ready,
        checks=checks,
    )
    return records


def _verify_qualification_lifecycle_timestamps(
    *,
    request: Mapping[str, Any],
    result: Mapping[str, Any],
    handshake_records: Mapping[str, Mapping[str, Any]],
    checks: _Checks,
) -> None:
    request_created = _exact_int(
        request.get("created_unix_ns"),
        "qualification request created_unix_ns",
    )
    result_started = _exact_int(
        result.get("created_unix_ns"),
        "qualification result start",
    )
    result_ended = _exact_int(
        result.get("ended_unix_ns"),
        "qualification result end",
    )
    ordered = request_created <= result_started
    previous = result_started
    attempt = handshake_records.get("attempt")
    if attempt is not None:
        attempt_created = _exact_int(
            attempt.get("created_unix_ns"),
            "qualification attempt created_unix_ns",
        )
        ordered = ordered and result_started == attempt_created
        previous = attempt_created
    for name in ("ready", "release"):
        record = handshake_records.get(name)
        if record is None:
            continue
        created = _exact_int(
            record.get("created_unix_ns"),
            f"qualification {name} created_unix_ns",
        )
        ordered = ordered and previous <= created
        previous = created
    ordered = ordered and previous <= result_ended
    checks.require(ordered, "qualification lifecycle timestamp order is invalid")


def _verify_qualification_config(
    config: Mapping[str, Any],
    *,
    config_path: Path,
    qualification_id: str,
    registration: Mapping[str, Any],
    source_commit: str,
    checks: _Checks,
) -> None:
    expected_fields = {
        "category_rates_bps",
        "enabled_categories",
        "manifest_path",
        "per_run_alternative_budget",
        "schema_version",
        "seed",
        "session_id",
        "source_commit",
        "study_id",
        "study_registration_hash",
        "study_run_lock_hash",
        "study_slot_number",
        "trace_path",
    }
    checks.require(
        set(config) == expected_fields
        and config.get("schema_version") == "noncombat-exploration-config-v1"
        and config.get("enabled_categories") == ["card_reward", "shop"]
        and config.get("category_rates_bps")
        == {"card_reward": 300, "shop": 1000}
        and config.get("per_run_alternative_budget") == 2
        and config.get("session_id") == f"{qualification_id}-s01"
        and config.get("source_commit") == source_commit
        and config.get("study_id") == qualification_id
        and config.get("study_slot_number") == 1
        and config.get("study_registration_hash")
        == registration["registration_hash"]
        and config.get("study_run_lock_hash") == "0" * 64,
        "qualification exploration config mismatch",
    )
    seed = _exact_int(config.get("seed"), "qualification seed")
    checks.require(
        0 <= seed <= 2**63 - 1,
        "qualification seed is outside the supported range",
    )
    trace_path = _qualification_lexical_absolute_path(
        config.get("trace_path"),
        "qualification trace",
    )
    manifest_path = _qualification_lexical_absolute_path(
        config.get("manifest_path"),
        "qualification manifest",
    )
    checks.require(
        config_path not in {trace_path, manifest_path}
        and trace_path != manifest_path,
        "qualification config/output paths overlap",
    )


def _expected_qualification_handshake(
    *,
    qualification_root: Path,
    qualification_id: str,
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    rules = registration["integrity_rules"]["communication_handshake"]
    return {
        "attempt_path": str(
            Path(
                os.path.abspath(
                    qualification_root
                    / "qualification-communication-attempt.json"
                )
            )
        ),
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "readiness_timeout_seconds": rules["readiness_timeout_seconds"],
        "ready_path": str(
            Path(
                os.path.abspath(
                    qualification_root
                    / "qualification-communication-ready.json"
                )
            )
        ),
        "release_path": str(
            Path(
                os.path.abspath(
                    qualification_root
                    / "qualification-communication-release.json"
                )
            )
        ),
        "release_timeout_seconds": rules["release_timeout_seconds"],
        "run_lock_hash": "0" * 64,
        "session_id": f"{qualification_id}-s01",
        "slot_number": 1,
    }


def _qualification_file_inventory(
    root: Path,
    *,
    excluded_paths: set[Path],
    guarded_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    excluded = {
        Path(os.path.abspath(path)) for path in excluded_paths
    }
    inventory = {}
    if guarded_snapshot is None:
        rows = _qualification_no_follow_entries(root)
    else:
        snapshot_root = guarded_snapshot.get("root")
        if Path(os.path.abspath(snapshot_root)) != Path(os.path.abspath(root)):
            raise OutcomeEvidenceVerificationError(
                "qualification guarded snapshot root mismatch"
            )
        rows = [
            (
                path,
                row["metadata"],
                row["is_link_or_reparse"],
            )
            for path, row in guarded_snapshot["entries"].items()
        ]
    for path, metadata, is_link_or_reparse in rows:
        lexical_path = Path(os.path.abspath(path))
        if is_link_or_reparse:
            raise OutcomeEvidenceVerificationError(
                "qualification root contains a symbolic link or reparse "
                f"point: {path}"
            )
        if lexical_path in excluded or not stat.S_ISREG(metadata.st_mode):
            continue
        if guarded_snapshot is None:
            inventory[str(lexical_path)] = _file_sha256(path)
        else:
            raw = _qualification_snapshot_regular_file_bytes(
                guarded_snapshot,
                lexical_path,
                label=f"preexisting file {lexical_path}",
            )
            if raw is None:
                raise OutcomeEvidenceVerificationError(
                    f"qualification preexisting snapshot is missing: {lexical_path}"
                )
            inventory[str(lexical_path)] = hashlib.sha256(raw).hexdigest()
    return inventory


def _qualification_marker_count(path: Path) -> int:
    guarded_path = _qualification_require_no_follow_path(
        path,
        "marker file",
        expected_kind="file",
        allow_missing=True,
    )
    if not _qualification_path_entry_exists(guarded_path):
        return 0
    if not _qualification_path_is_regular_file(guarded_path):
        raise OutcomeEvidenceVerificationError(
            "qualification marker path is not a regular file"
        )
    try:
        markers = [
            line.strip()
            for line in guarded_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeError) as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot read qualification marker file: {exc}"
        ) from exc
    if any(not marker.isdigit() for marker in markers):
        raise OutcomeEvidenceVerificationError(
            "qualification marker file is invalid"
        )
    return len(markers)


def verify_outcome_evidence_expansion(
    registration_path: Path | str,
) -> dict[str, Any]:
    """Replay registration-through-closeout evidence without study imports."""

    checks = _Checks()
    try:
        registration_path = Path(registration_path).resolve()
        registration_bytes = registration_path.read_bytes()
        registration = _load_mapping_bytes(registration_bytes, registration_path)
        _verify_registration(registration, checks)
        paths = _artifact_paths(registration)

        run_lock = _load_mapping(paths["run_lock"])
        locked_isolation = _verify_run_lock(
            run_lock,
            registration=registration,
            registration_path=registration_path,
            registration_bytes=registration_bytes,
            checks=checks,
        )
        ledger = _verify_ledger(
            paths["ledger"],
            registration=registration,
            run_lock=run_lock,
            checks=checks,
        )
        _verify_handshake_evidence(
            registration=registration,
            run_lock=run_lock,
            ledger=ledger,
            checks=checks,
        )
        claim = _verify_claim(
            paths["claim"],
            registration=registration,
            run_lock=run_lock,
            checks=checks,
        )
        blocked = ledger["global_stop"] is not None
        expected_claim_mode = "integrity_stop" if blocked else "complete"
        checks.require(
            claim["mode"] == expected_claim_mode,
            "ledger and finalization claim mode mismatch",
        )
        implementation_hashes = {
            str(row["relative_path"]): str(row["sha256"])
            for row in run_lock["implementation_files"]
        }
        if blocked:
            blocked_result = _verify_blocked_closeout(
                registration=registration,
                run_lock=run_lock,
                ledger=ledger,
                paths=paths,
                checks=checks,
            )
            return {
                "check_count": checks.count,
                "closeout_hash": blocked_result["closeout_hash"],
                "closeout_mode": "integrity_stop",
                "ledger_final_record_hash": ledger["final_record_hash"],
                "passed": True,
                "registration_hash": registration["registration_hash"],
                "run_lock_hash": run_lock["run_lock_hash"],
                "run_lock_isolation": locked_isolation,
                "schema_version": AUDIT_SCHEMA_VERSION,
                "source_implementation_sha256": implementation_hashes,
                "study_id": registration["study_id"],
                "verifier_implementation_sha256": _file_sha256(Path(__file__)),
            }

        checks.require(
            len(ledger["terminal_slots"]) == SLOT_COUNT,
            "not every registered slot is terminal",
        )
        live_isolation = _verify_live_run_lock_state(
            run_lock,
            registration=registration,
            registration_path=registration_path,
            registration_bytes=registration_bytes,
            checks=checks,
        )

        samples = _load_jsonl(paths["pool_samples"])
        pool = _load_mapping(paths["pool_manifest"])
        pool_result = _verify_pool(
            samples,
            pool,
            registration=registration,
            run_lock=run_lock,
            ledger=ledger,
            checks=checks,
        )
        target = _load_mapping(paths["target"])
        readiness = _load_mapping(paths["readiness"])
        try:
            readiness_audit = verify_artifact_pair(
                paths["pool_samples"],
                paths["target"],
                paths["readiness"],
            )
        except ArtifactVerificationError as exc:
            raise OutcomeEvidenceVerificationError(
                f"OPE readiness replay failed: {exc}"
            ) from exc
        metrics = _recompute_metrics(
            samples,
            target,
            registration=registration,
            pool_result=pool_result,
            checks=checks,
        )
        _verify_readiness_metrics(readiness, metrics, checks)

        estimate = _load_mapping(paths["estimate"])
        estimate_result = _verify_estimate(
            estimate,
            paths=paths,
            registration=registration,
            readiness=readiness,
            readiness_audit=readiness_audit,
            checks=checks,
        )
        expected_gate = _build_evidence_gate(registration, metrics)
        closeout = _load_mapping(paths["closeout"])
        _verify_closeout(
            closeout,
            registration=registration,
            run_lock=run_lock,
            ledger=ledger,
            pool=pool,
            target=target,
            readiness=readiness,
            estimate_result=estimate_result,
            expected_gate=expected_gate,
            paths=paths,
            checks=checks,
        )

        return {
            "ai_marker_file_sha256": pool_result[
                "ai_marker_file_sha256"
            ],
            "check_count": checks.count,
            "closeout_mode": "complete",
            "conservative_join_run_file_sha256": pool_result[
                "conservative_join_run_file_sha256"
            ],
            "conservative_run_inventory_sha256": pool_result[
                "conservative_run_inventory_sha256"
            ],
            "ledger_final_record_hash": ledger["final_record_hash"],
            "live_isolation": live_isolation,
            "passed": True,
            "pool_manifest_hash": pool["pool_manifest_hash"],
            "recomputed": {
                "category_arm_support": metrics["category_arm_support"],
                "complete_trajectory_count": metrics[
                    "complete_trajectory_count"
                ],
                "ess_fraction": _fraction_record(metrics["ess_fraction"]),
                "max_normalized_weight": _fraction_record(
                    metrics["max_normalized_weight"]
                ),
                "nonzero_weight_trajectory_count": metrics[
                    "nonzero_weight_trajectory_count"
                ],
                "outcome_evidence_expansion_ready": expected_gate[
                    "outcome_evidence_expansion_ready"
                ],
                "supported_victories": metrics["supported_victories"],
                "supported_victory_count": metrics[
                    "supported_victory_count"
                ],
            },
            "registration_hash": registration["registration_hash"],
            "run_lock_hash": run_lock["run_lock_hash"],
            "schema_version": AUDIT_SCHEMA_VERSION,
            "source_implementation_sha256": implementation_hashes,
            "study_id": registration["study_id"],
            "terminal_outcome_file_sha256": pool_result[
                "terminal_outcome_file_sha256"
            ],
            "verifier_implementation_sha256": _file_sha256(Path(__file__)),
        }
    except OutcomeEvidenceVerificationError:
        raise
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        raise OutcomeEvidenceVerificationError(
            f"outcome-evidence verification failed: {exc}"
        ) from exc


def render_verification_audit(audit: Mapping[str, Any]) -> str:
    if not isinstance(audit, Mapping) or audit.get("passed") is not True:
        raise OutcomeEvidenceVerificationError("verification audit is not passing")
    return _canonical_json(audit) + "\n"


def _verify_registration(record: Mapping[str, Any], checks: _Checks) -> None:
    supplied_hash = record.get("registration_hash")
    checks.require(_is_sha256(supplied_hash), "registration hash is invalid")
    checks.require(
        supplied_hash == _self_hash(record, "registration_hash"),
        "registration hash mismatch",
    )
    expected = _expected_registration(record)
    expected["registration_hash"] = supplied_hash
    checks.require(record == expected, "registered study contract mismatch")


def _expected_registration(record: Mapping[str, Any]) -> dict[str, Any]:
    schema_version = _required_string(
        record.get("schema_version"),
        "schema_version",
    )
    if schema_version == LEGACY_REGISTRATION_SCHEMA_VERSION:
        implementation_paths = LEGACY_IMPLEMENTATION_PATHS
    elif schema_version == REGISTRATION_SCHEMA_VERSION:
        implementation_paths = IMPLEMENTATION_PATHS
    else:
        raise OutcomeEvidenceVerificationError(
            "registration schema_version is unsupported"
        )
    study_id = _required_string(record.get("study_id"), "study_id")
    if _STUDY_PATTERN.fullmatch(study_id) is None:
        raise OutcomeEvidenceVerificationError("study_id is invalid")
    artifact_root = _absolute_path(record.get("artifact_root"), "artifact_root")
    repo_root = _absolute_path(record.get("repo_root"), "repo_root")
    seed_base = _exact_int(record.get("seed_base"), "seed_base")
    command = _mapping(record.get("command"), "command")
    python_executable = _required_string(
        command.get("python_executable"),
        "python_executable",
    )
    if str(Path(python_executable).resolve()) != WINDOWS_PYTHON:
        raise OutcomeEvidenceVerificationError("registered Python path mismatch")
    integrity = _mapping(record.get("integrity_rules"), "integrity_rules")
    communication_path = _absolute_path(
        integrity.get("communication_config_path"),
        "communication_config_path",
    )
    checkpoint_inventory = _mapping(
        integrity.get("checkpoint_inventory"),
        "checkpoint_inventory",
    )
    checkpoint_root = _absolute_path(
        checkpoint_inventory.get("root"),
        "checkpoint_root",
    )
    slots = []
    for number in range(1, SLOT_COUNT + 1):
        session_id = f"{study_id}-s{number:02d}"
        slots.append(
            {
                "config_path": str(
                    (artifact_root / f"{session_id}-config.json").resolve()
                ),
                "manifest_path": str(
                    (artifact_root / f"{session_id}-manifest.json").resolve()
                ),
                "seed": seed_base + number,
                "session_id": session_id,
                "slot_number": number,
                "trace_path": str(
                    (artifact_root / f"{session_id}-trace.jsonl").resolve()
                ),
            }
        )
    integrity_rules = {
        "checkpoint_inventory": {
            "patterns": list(CHECKPOINT_PATTERNS),
            "root": str(checkpoint_root),
        },
        "communication_config_path": str(communication_path),
        "implementation_paths": list(implementation_paths),
        "launches_per_slot": 1,
        "replacement_slots_forbidden": True,
        "tracked_source_frozen_during_run_lock": True,
    }
    if schema_version == REGISTRATION_SCHEMA_VERSION:
        integrity_rules["communication_handshake"] = {
            "attempt_suffix": "-communication-attempt.json",
            "orphaned_attempt_global_stop": True,
            "protocol_version": "noncombat-outcome-evidence-handshake-v1",
            "readiness_timeout_seconds": 120,
            "ready_suffix": "-communication-ready.json",
            "release_suffix": "-communication-release.json",
            "release_timeout_seconds": 10,
            "required_before_slot_claim": True,
        }
    return {
        "analysis_rules": {
            "bootstrap_confidence_level": {
                "denominator": 100,
                "numerator": 95,
            },
            "bootstrap_replicates": 10_000,
            "bootstrap_seed": (
                f"{study_id}:current-deterministic-bootstrap-v1"
            ),
            "calibration_artifact_relative_path": (
                "reports/noncombat_ope_estimator_calibration_20260714.json"
            ),
            "target_policy_mode": "current_deterministic",
        },
        "artifact_root": str(artifact_root),
        "behavior": {
            "category_rates_bps": {"card_reward": 300, "shop": 1000},
            "enabled_categories": ["card_reward", "shop"],
            "executable_alternatives": {
                "card_reward": "card_reward:skip",
                "shop": "shop:leave",
            },
            "per_run_alternative_budget": 2,
            "shadow_only_categories": ["event", "route"],
        },
        "blinding_rules": {
            "finalization_requires_all_slots_terminal": True,
            "outcome_adaptive_decisions_forbidden": True,
            "outcome_fields_forbidden_during_collection": True,
        },
        "command": {
            "arguments": list(COMMAND_ARGUMENTS),
            "main_path": str((repo_root / "main.py").resolve()),
            "python_executable": python_executable,
        },
        "games_per_slot": GAMES_PER_SLOT,
        "integrity_rules": integrity_rules,
        "output_rules": {
            "canonical_json_line_ending": "LF",
            "closeout_json_filename": "outcome-evidence-closeout.json",
            "closeout_markdown_filename": "outcome-evidence-closeout.md",
            "config_suffix": "-config.json",
            "estimate_json_filename": "ope-estimate.json",
            "estimate_markdown_filename": "ope-estimate.md",
            "finalization_claim_filename": "finalization-claim.json",
            "manifest_suffix": "-manifest.json",
            "monitor_json_filename": "blinded-monitor.json",
            "monitor_markdown_filename": "blinded-monitor.md",
            "pool_manifest_filename": "registered-pool-manifest.json",
            "pool_samples_filename": "registered-pool-samples.jsonl",
            "readiness_json_filename": "ope-readiness.json",
            "readiness_markdown_filename": "ope-readiness.md",
            "run_lock_filename": "run-lock.json",
            "study_ledger_filename": "study-ledger.jsonl",
            "target_manifest_filename": "current-target.json",
            "trace_suffix": "-trace.jsonl",
        },
        "registration_hash": None,
        "repo_root": str(repo_root),
        "scheduled_attempts": SCHEDULED_ATTEMPTS,
        "schema_version": schema_version,
        "seed_base": seed_base,
        "slot_count": SLOT_COUNT,
        "slots": slots,
        "study_id": study_id,
        "thresholds": {
            "maximum_normalized_weight": {"denominator": 20, "numerator": 1},
            "minimum_arm_decisions_per_category": 50,
            "minimum_complete_trajectories": 575,
            "minimum_ess_fraction": {"denominator": 2, "numerator": 1},
            "minimum_nonzero_weight_fraction": {
                "denominator": 2,
                "numerator": 1,
            },
            "minimum_supported_victories": 3,
        },
    }


def _artifact_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    root = Path(str(registration["artifact_root"]))
    rules = _mapping(registration.get("output_rules"), "output_rules")
    repo_root = Path(str(registration["repo_root"]))
    analysis = _mapping(registration.get("analysis_rules"), "analysis_rules")
    return {
        "calibration": repo_root
        / str(analysis["calibration_artifact_relative_path"]),
        "claim": root / str(rules["finalization_claim_filename"]),
        "closeout": root / str(rules["closeout_json_filename"]),
        "closeout_markdown": root
        / str(rules["closeout_markdown_filename"]),
        "estimate": root / str(rules["estimate_json_filename"]),
        "estimate_markdown": root
        / str(rules["estimate_markdown_filename"]),
        "ledger": root / str(rules["study_ledger_filename"]),
        "pool_manifest": root / str(rules["pool_manifest_filename"]),
        "pool_samples": root / str(rules["pool_samples_filename"]),
        "readiness": root / str(rules["readiness_json_filename"]),
        "readiness_markdown": root
        / str(rules["readiness_markdown_filename"]),
        "run_lock": root / str(rules["run_lock_filename"]),
        "target": root / str(rules["target_manifest_filename"]),
    }


def _verify_handshake_evidence(
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    checks: _Checks,
) -> None:
    if registration["schema_version"] == LEGACY_REGISTRATION_SCHEMA_VERSION:
        return

    rules = _mapping(
        registration["integrity_rules"].get("communication_handshake"),
        "communication_handshake",
    )
    terminals = list(ledger["terminal_slots"])
    terminal_count = len(terminals)
    blocked = ledger["global_stop"] is not None
    for raw_slot in registration["slots"]:
        slot = _mapping(raw_slot, "registered slot")
        slot_number = _exact_int(slot.get("slot_number"), "slot_number")
        paths = _handshake_paths(slot, rules)
        if slot_number <= terminal_count:
            terminal = terminals[slot_number - 1]
            checks.require(
                paths["attempt"].is_file(),
                f"slot {slot_number} handshake attempt is missing",
            )
            attempt = _verify_handshake_attempt(
                _load_canonical_handshake_record(
                    paths["attempt"],
                    f"slot {slot_number} handshake attempt",
                ),
                registration=registration,
                run_lock=run_lock,
                slot=slot,
                paths=paths,
                rules=rules,
                expected_marker_start=terminal["marker_start_count"],
                checks=checks,
            )
            checks.require(
                paths["ready"].is_file(),
                f"slot {slot_number} handshake ready record is missing",
            )
            ready = _verify_handshake_ready(
                _load_canonical_handshake_record(
                    paths["ready"],
                    f"slot {slot_number} handshake ready",
                ),
                attempt=attempt,
                checks=checks,
            )
            release_exists = paths["release"].exists()
            if terminal["terminal_status"] == "completed":
                checks.require(
                    paths["release"].is_file(),
                    f"slot {slot_number} handshake release is missing",
                )
            if release_exists:
                _verify_handshake_release(
                    _load_canonical_handshake_record(
                        paths["release"],
                        f"slot {slot_number} handshake release",
                    ),
                    attempt=attempt,
                    ready=ready,
                    checks=checks,
                )
            continue

        is_next_blocked_slot = blocked and slot_number == terminal_count + 1
        if is_next_blocked_slot:
            checks.require(
                not paths["release"].exists(),
                f"unlaunched slot {slot_number} has a handshake release",
            )
            checks.require(
                not paths["ready"].exists() or paths["attempt"].exists(),
                f"unlaunched slot {slot_number} ready has no attempt",
            )
            attempt = None
            if paths["attempt"].exists():
                attempt = _verify_handshake_attempt(
                    _load_canonical_handshake_record(
                        paths["attempt"],
                        f"slot {slot_number} handshake attempt",
                    ),
                    registration=registration,
                    run_lock=run_lock,
                    slot=slot,
                    paths=paths,
                    rules=rules,
                    expected_marker_start=None,
                    checks=checks,
                )
            if paths["ready"].exists():
                _verify_handshake_ready(
                    _load_canonical_handshake_record(
                        paths["ready"],
                        f"slot {slot_number} handshake ready",
                    ),
                    attempt=attempt,
                    checks=checks,
                )
            continue

        checks.require(
            not any(path.exists() for path in paths.values()),
            f"later unlaunched slot {slot_number} has handshake artifacts",
        )


def _handshake_paths(
    slot: Mapping[str, Any],
    rules: Mapping[str, Any],
) -> dict[str, Path]:
    config_path = Path(str(slot["config_path"])).resolve()
    session_id = str(slot["session_id"])
    return {
        "attempt": (
            config_path.parent / f"{session_id}{rules['attempt_suffix']}"
        ).resolve(),
        "ready": (
            config_path.parent / f"{session_id}{rules['ready_suffix']}"
        ).resolve(),
        "release": (
            config_path.parent / f"{session_id}{rules['release_suffix']}"
        ).resolve(),
    }


def _verify_handshake_attempt(
    record: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    slot: Mapping[str, Any],
    paths: Mapping[str, Path],
    rules: Mapping[str, Any],
    expected_marker_start: int | None,
    checks: _Checks,
    config_bytes: bytes | None = None,
) -> dict[str, Any]:
    slot_number = _exact_int(slot.get("slot_number"), "slot_number")
    created_unix_ns = _exact_int(
        record.get("created_unix_ns"),
        "handshake attempt created_unix_ns",
    )
    marker_start = _exact_int(
        record.get("marker_start_count"),
        "handshake attempt marker_start_count",
    )
    checks.require(
        created_unix_ns >= 0 and marker_start >= 0,
        f"slot {slot_number} handshake attempt counters are invalid",
    )
    if expected_marker_start is not None:
        checks.require(
            marker_start == expected_marker_start,
            f"slot {slot_number} handshake marker boundary mismatch",
        )
    config_path = Path(str(slot["config_path"])).resolve()
    if config_bytes is None:
        try:
            config_sha256 = _file_sha256(config_path)
        except OSError as exc:
            raise OutcomeEvidenceVerificationError(
                f"slot {slot_number} handshake config is unreadable: {exc}"
            ) from exc
    else:
        config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    token = _derive_handshake_slot_token(
        registration_hash=str(registration["registration_hash"]),
        run_lock_hash=str(run_lock["run_lock_hash"]),
        slot_number=slot_number,
        session_id=str(slot["session_id"]),
        config_sha256=config_sha256,
    )
    expected = {
        "attempt_hash": None,
        "attempt_path": str(paths["attempt"]),
        "config_path": str(config_path),
        "config_sha256": config_sha256,
        "created_unix_ns": created_unix_ns,
        "marker_start_count": marker_start,
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "readiness_timeout_seconds": rules["readiness_timeout_seconds"],
        "ready_path": str(paths["ready"]),
        "registration_hash": registration["registration_hash"],
        "release_path": str(paths["release"]),
        "release_timeout_seconds": rules["release_timeout_seconds"],
        "run_lock_hash": run_lock["run_lock_hash"],
        "schema_version": HANDSHAKE_ATTEMPT_SCHEMA_VERSION,
        "session_id": slot["session_id"],
        "slot_number": slot_number,
        "slot_token": token,
        "study_id": registration["study_id"],
    }
    expected["attempt_hash"] = _self_hash(expected, "attempt_hash")
    checks.require(
        _canonical_json(record) == _canonical_json(expected),
        f"slot {slot_number} handshake attempt mismatch",
    )
    return expected


def _verify_handshake_ready(
    record: Mapping[str, Any],
    *,
    attempt: Mapping[str, Any] | None,
    checks: _Checks,
) -> dict[str, Any]:
    if attempt is None:
        raise OutcomeEvidenceVerificationError(
            "handshake ready cannot be verified without an attempt"
        )
    slot_number = int(attempt["slot_number"])
    child_pid = _exact_int(record.get("child_pid"), "handshake ready child_pid")
    created_unix_ns = _exact_int(
        record.get("created_unix_ns"),
        "handshake ready created_unix_ns",
    )
    checks.require(
        child_pid > 0 and created_unix_ns >= 0,
        f"slot {slot_number} handshake ready counters are invalid",
    )
    expected = {
        "attempt_hash": attempt["attempt_hash"],
        "child_pid": child_pid,
        "communication_state_received": True,
        "config_path": attempt["config_path"],
        "config_sha256": attempt["config_sha256"],
        "created_unix_ns": created_unix_ns,
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "ready_hash": None,
        "ready_path": attempt["ready_path"],
        "registration_hash": attempt["registration_hash"],
        "run_lock_hash": attempt["run_lock_hash"],
        "schema_version": HANDSHAKE_READY_SCHEMA_VERSION,
        "session_id": attempt["session_id"],
        "slot_number": slot_number,
        "slot_token": attempt["slot_token"],
        "study_id": attempt["study_id"],
    }
    expected["ready_hash"] = _self_hash(expected, "ready_hash")
    checks.require(
        _canonical_json(record) == _canonical_json(expected),
        f"slot {slot_number} handshake ready mismatch",
    )
    return expected


def _verify_handshake_release(
    record: Mapping[str, Any],
    *,
    attempt: Mapping[str, Any],
    ready: Mapping[str, Any],
    checks: _Checks,
) -> None:
    slot_number = int(attempt["slot_number"])
    created_unix_ns = _exact_int(
        record.get("created_unix_ns"),
        "handshake release created_unix_ns",
    )
    checks.require(
        created_unix_ns >= 0,
        f"slot {slot_number} handshake release time is invalid",
    )
    expected = {
        "attempt_hash": attempt["attempt_hash"],
        "child_pid": ready["child_pid"],
        "created_unix_ns": created_unix_ns,
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "ready_hash": ready["ready_hash"],
        "registration_hash": attempt["registration_hash"],
        "release_hash": None,
        "release_path": attempt["release_path"],
        "run_lock_hash": attempt["run_lock_hash"],
        "schema_version": HANDSHAKE_RELEASE_SCHEMA_VERSION,
        "session_id": attempt["session_id"],
        "slot_number": slot_number,
        "slot_token": attempt["slot_token"],
        "study_id": attempt["study_id"],
    }
    expected["release_hash"] = _self_hash(expected, "release_hash")
    checks.require(
        _canonical_json(record) == _canonical_json(expected),
        f"slot {slot_number} handshake release mismatch",
    )


def _derive_handshake_slot_token(
    *,
    registration_hash: str,
    run_lock_hash: str,
    slot_number: int,
    session_id: str,
    config_sha256: str,
) -> str:
    payload = {
        "config_sha256": config_sha256,
        "protocol_version": HANDSHAKE_SCHEMA_VERSION,
        "registration_hash": registration_hash,
        "run_lock_hash": run_lock_hash,
        "session_id": session_id,
        "slot_number": slot_number,
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _load_canonical_handshake_record(
    path: Path,
    label: str,
) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidenceVerificationError(
            f"{label} is missing or unreadable: {exc}"
        ) from exc
    return _load_canonical_handshake_record_bytes(
        data,
        path=path,
        label=label,
    )


def _load_canonical_handshake_record_bytes(
    data: bytes,
    *,
    path: Path,
    label: str,
) -> dict[str, Any]:
    value = _load_mapping_bytes(data, path)
    if data != (_canonical_json(value) + "\n").encode("utf-8"):
        raise OutcomeEvidenceVerificationError(f"{label} is not canonical JSON")
    return value


def _registered_implementation_paths(
    registration: Mapping[str, Any],
) -> tuple[str, ...]:
    integrity = _mapping(registration.get("integrity_rules"), "integrity_rules")
    raw_paths = _sequence(
        integrity.get("implementation_paths"),
        "implementation_paths",
    )
    if any(not isinstance(path, str) or not path for path in raw_paths):
        raise OutcomeEvidenceVerificationError(
            "registration implementation paths are invalid"
        )
    return tuple(raw_paths)


def _verify_run_lock(
    record: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    registration_path: Path,
    registration_bytes: bytes,
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(
        record.get("schema_version") == RUN_LOCK_SCHEMA_VERSION,
        "run lock schema mismatch",
    )
    checks.require(_is_sha256(record.get("run_lock_hash")), "run lock hash invalid")
    checks.require(
        record.get("run_lock_hash") == _self_hash(record, "run_lock_hash"),
        "run lock hash mismatch",
    )
    checks.require(
        record.get("study_id") == registration["study_id"],
        "run lock study mismatch",
    )
    checks.require(
        record.get("repo_root") == registration["repo_root"],
        "run lock repo mismatch",
    )
    checks.require(
        record.get("python_executable")
        == registration["command"]["python_executable"],
        "run lock Python mismatch",
    )
    expected_command = [
        registration["command"]["python_executable"],
        registration["command"]["main_path"],
        *registration["command"]["arguments"],
    ]
    checks.require(record.get("command") == expected_command, "run lock command drift")
    source = _mapping(record.get("source"), "run lock source")
    checks.require(
        _COMMIT_PATTERN.fullmatch(str(source.get("commit"))) is not None,
        "run lock source commit invalid",
    )
    checks.require(
        source.get("tracked_clean") is True
        and source.get("tracked_status") == "",
        "run lock source was not tracked-clean",
    )
    registration_binding = _mapping(
        record.get("registration"),
        "run lock registration",
    )
    checks.require(
        registration_binding
        == {
            "canonical_hash": registration["registration_hash"],
            "file_sha256": hashlib.sha256(registration_bytes).hexdigest(),
            "path": str(registration_path),
        },
        "run lock registration binding mismatch",
    )
    _verify_implementation_files(
        record,
        registration,
        source_commit=str(source["commit"]),
        checks=checks,
    )
    _verify_git_anchor(
        source,
        registration=registration,
        registration_path=registration_path,
        registration_bytes=registration_bytes,
        checks=checks,
    )
    locked_checkpoints = _verify_locked_checkpoint_inventory(
        record,
        registration,
        checks,
    )
    locked_communication = _verify_locked_communication(
        record,
        registration,
        checks,
    )
    return {
        "checkpoints": locked_checkpoints,
        "communication_mod": locked_communication,
    }


def _verify_implementation_files(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    *,
    source_commit: str,
    checks: _Checks,
) -> None:
    rows = _sequence(run_lock.get("implementation_files"), "implementation_files")
    implementation_paths = _registered_implementation_paths(registration)
    checks.require(
        len(rows) == len(implementation_paths),
        "source file count mismatch",
    )
    repo_root = Path(str(registration["repo_root"])).resolve()
    for relative_path, raw_row in zip(implementation_paths, rows, strict=True):
        row = _mapping(raw_row, "implementation file")
        path = (repo_root / relative_path).resolve()
        content = _git_blob(repo_root, source_commit, relative_path)
        checks.require(
            row
            == {
                "path": str(path),
                "relative_path": relative_path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            },
            f"implementation source drift: {relative_path}",
        )


def _verify_git_anchor(
    source: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    registration_path: Path,
    registration_bytes: bytes,
    checks: _Checks,
) -> None:
    repo_root = Path(str(registration["repo_root"])).resolve()
    observed_root = Path(
        _git_text(repo_root, "rev-parse", "--show-toplevel")
    ).resolve()
    checks.require(observed_root == repo_root, "Git repository root mismatch")
    commit = str(source["commit"])
    checks.require(
        _git_text(repo_root, "rev-parse", f"{commit}^{{commit}}") == commit,
        "run lock source commit is unavailable",
    )
    try:
        registration_relative = registration_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceVerificationError(
            "registration file is outside the locked repository"
        ) from exc
    checks.require(
        _git_blob(repo_root, commit, registration_relative) == registration_bytes,
        "committed registration bytes differ from the verified file",
    )


def _verify_locked_checkpoint_inventory(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    checkpoints = _mapping(run_lock.get("checkpoints"), "checkpoints")
    inventory = registration["integrity_rules"]["checkpoint_inventory"]
    root = Path(str(inventory["root"])).resolve()
    patterns = list(inventory["patterns"])
    checks.require(
        set(checkpoints) == {"files", "patterns", "root"}
        and checkpoints.get("patterns") == patterns
        and checkpoints.get("root") == str(root),
        "run lock checkpoint contract mismatch",
    )
    rows = _sequence(checkpoints.get("files"), "checkpoint files")
    normalized_rows = []
    observed_paths = []
    for raw_row in rows:
        row = _mapping(raw_row, "checkpoint file")
        path = _absolute_path(row.get("path"), "checkpoint path")
        size = _exact_int(row.get("size"), "checkpoint size")
        checks.require(
            set(row) == {"path", "sha256", "size"}
            and path.parent == root
            and any(fnmatch.fnmatch(path.name, pattern) for pattern in patterns)
            and _is_sha256(row.get("sha256"))
            and size >= 0,
            "run lock checkpoint row mismatch",
        )
        observed_paths.append(str(path))
        normalized_rows.append(dict(row))
    checks.require(
        len(observed_paths) == len(set(observed_paths))
        and observed_paths == sorted(observed_paths, key=str.casefold),
        "run lock checkpoint order mismatch",
    )
    return {
        "files": normalized_rows,
        "patterns": patterns,
        "root": str(root),
    }


def _verify_locked_communication(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    communication = _mapping(run_lock.get("communication_mod"), "communication_mod")
    expected_path = registration["integrity_rules"]["communication_config_path"]
    checks.require(
        set(communication) == {"path", "semantic_sha256"}
        and communication.get("path") == expected_path
        and _is_sha256(communication.get("semantic_sha256")),
        "run lock CommunicationMod contract mismatch",
    )
    return dict(communication)


def _verify_live_run_lock_state(
    run_lock: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    registration_path: Path,
    registration_bytes: bytes,
    checks: _Checks,
) -> dict[str, Any]:
    source = _mapping(run_lock.get("source"), "run lock source")
    _verify_live_implementation_files(run_lock, registration, checks)
    _verify_live_git_anchor(
        source,
        registration=registration,
        registration_path=registration_path,
        registration_bytes=registration_bytes,
        checks=checks,
    )
    observed_checkpoints = _verify_checkpoint_files(
        run_lock,
        registration,
        checks,
    )
    expected_communication_path = registration["integrity_rules"][
        "communication_config_path"
    ]
    observed_communication = {
        "path": expected_communication_path,
        "semantic_sha256": _properties_semantic_sha256(
            Path(expected_communication_path)
        ),
    }
    checks.require(
        run_lock.get("communication_mod") == observed_communication,
        "CommunicationMod semantic configuration drift",
    )
    return {
        "checkpoints": observed_checkpoints,
        "communication_mod": observed_communication,
    }


def _verify_live_implementation_files(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> None:
    rows = _sequence(run_lock.get("implementation_files"), "implementation_files")
    implementation_paths = _registered_implementation_paths(registration)
    repo_root = Path(str(registration["repo_root"])).resolve()
    for relative_path, raw_row in zip(implementation_paths, rows, strict=True):
        row = _mapping(raw_row, "implementation file")
        path = (repo_root / relative_path).resolve()
        content = path.read_bytes()
        checks.require(
            row
            == {
                "path": str(path),
                "relative_path": relative_path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            },
            f"implementation source drift: {relative_path}",
        )


def _verify_live_git_anchor(
    source: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    registration_path: Path,
    registration_bytes: bytes,
    checks: _Checks,
) -> None:
    repo_root = Path(str(registration["repo_root"])).resolve()
    commit = str(source["commit"])
    checks.require(
        _git_text(repo_root, "rev-parse", "HEAD") == commit,
        "Git HEAD differs from the run lock",
    )
    checks.require(
        _git_text(
            repo_root,
            "status",
            "--porcelain=v1",
            "--untracked-files=no",
        )
        == "",
        "Git tracked worktree differs from the run lock",
    )
    try:
        registration_relative = registration_path.relative_to(repo_root).as_posix()
    except ValueError as exc:
        raise OutcomeEvidenceVerificationError(
            "registration file is outside the locked repository"
        ) from exc
    implementation_paths = _registered_implementation_paths(registration)
    relative_paths = [registration_relative, *implementation_paths]
    _git_text(
        repo_root,
        "ls-files",
        "--error-unmatch",
        "--",
        *relative_paths,
    )
    checks.require(
        _git_blob(repo_root, commit, registration_relative) == registration_bytes,
        "committed registration bytes differ from the verified file",
    )
    for relative_path in implementation_paths:
        checks.require(
            _git_blob(repo_root, commit, relative_path)
            == (repo_root / relative_path).read_bytes(),
            f"committed implementation bytes differ: {relative_path}",
        )


def _git_text(repo_root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [
            _qualification_git_executable(),
            "-C",
            str(repo_root),
            *arguments,
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise OutcomeEvidenceVerificationError(
            f"Git {' '.join(arguments)} failed: {detail}"
        )
    return completed.stdout.strip()


def _qualification_git_text(repo_root: Path, *arguments: str) -> str:
    git_root = _qualification_validate_git_metadata(repo_root)
    completed = subprocess.run(
        _qualification_git_command("-C", str(repo_root), *arguments),
        capture_output=True,
        check=False,
        env=_qualification_git_environment(
            repo_root=Path(repo_root),
            git_root=git_root,
        ),
        text=True,
    )
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0 or stderr:
        detail = stderr or (completed.stdout or "").strip()
        if not detail:
            detail = f"exit code {completed.returncode}"
        raise OutcomeEvidenceVerificationError(
            f"qualification Git {' '.join(arguments)} failed: {detail}"
        )
    return completed.stdout.strip()


def _git_blob(repo_root: Path, commit: str, relative_path: str) -> bytes:
    completed = subprocess.run(
        [
            _qualification_git_executable(),
            "-C",
            str(repo_root),
            "show",
            f"{commit}:{relative_path}",
        ],
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise OutcomeEvidenceVerificationError(
            f"cannot read committed Git blob {relative_path}: {detail}"
        )
    return completed.stdout


def _qualification_git_blob(
    repo_root: Path,
    commit: str,
    relative_path: str,
) -> bytes:
    git_root = _qualification_validate_git_metadata(repo_root)
    completed = subprocess.run(
        _qualification_git_command(
            "-C",
            str(repo_root),
            "show",
            f"{commit}:{relative_path}",
        ),
        capture_output=True,
        check=False,
        env=_qualification_git_environment(
            repo_root=Path(repo_root),
            git_root=git_root,
        ),
    )
    stderr = completed.stderr.decode("utf-8", errors="replace").strip()
    if completed.returncode != 0 or stderr:
        detail = stderr or f"exit code {completed.returncode}"
        raise OutcomeEvidenceVerificationError(
            f"cannot read committed qualification Git blob "
            f"{relative_path}: {detail}"
        )
    return completed.stdout


def _verify_checkpoint_files(
    run_lock: Mapping[str, Any],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    checkpoints = _mapping(run_lock.get("checkpoints"), "checkpoints")
    inventory = registration["integrity_rules"]["checkpoint_inventory"]
    root = Path(str(inventory["root"])).resolve()
    patterns = list(inventory["patterns"])
    paths = {
        path.resolve()
        for pattern in patterns
        for path in root.glob(pattern)
        if path.is_file()
    }
    observed = {
        "files": [
            {
                "path": str(path),
                "sha256": _file_sha256(path),
                "size": len(path.read_bytes()),
            }
            for path in sorted(paths, key=lambda path: str(path).casefold())
        ],
        "patterns": patterns,
        "root": str(root),
    }
    checks.require(
        checkpoints == observed,
        "checkpoint inventory drift",
    )
    return observed


def _verify_ledger(
    path: Path,
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    records = _load_jsonl(path)
    checks.require(bool(records), "study ledger is empty")
    previous_hash = None
    active = None
    terminals = []
    next_slot = 1
    initialized = False
    global_stop = None
    marker_end_cursor = None
    for sequence, raw_record in enumerate(records, start=1):
        record = _mapping(raw_record, f"ledger record {sequence}")
        checks.require(
            record.get("schema_version") == LEDGER_SCHEMA_VERSION,
            "ledger schema mismatch",
        )
        checks.require(record.get("sequence") == sequence, "ledger sequence mismatch")
        checks.require(
            record.get("previous_record_hash") == previous_hash,
            "ledger hash chain mismatch",
        )
        checks.require(
            record.get("record_hash") == _self_hash(record, "record_hash"),
            "ledger record hash mismatch",
        )
        checks.require(
            record.get("registration_hash") == registration["registration_hash"]
            and record.get("run_lock_hash") == run_lock["run_lock_hash"]
            and record.get("study_id") == registration["study_id"],
            "ledger study binding mismatch",
        )
        event = record.get("event")
        payload = _mapping(record.get("payload"), "ledger payload")
        checks.require(
            global_stop is None,
            "ledger event follows the global stop",
        )
        if event == "study_started":
            checks.require(
                not initialized
                and sequence == 1
                and payload == {"slot_count": SLOT_COUNT},
                "ledger initialization mismatch",
            )
            initialized = True
        elif event == "slot_started":
            checks.require(
                initialized and active is None and global_stop is None,
                "invalid ledger slot start state",
            )
            marker_start_count = None
            if registration["schema_version"] == REGISTRATION_SCHEMA_VERSION:
                marker_start_count = _exact_int(
                    payload.get("marker_start_count"),
                    "slot_started marker_start_count",
                )
                expected_start_payload = {
                    "marker_start_count": marker_start_count
                }
            else:
                expected_start_payload = {}
            checks.require(
                record.get("slot_number") == next_slot
                and record.get("session_id")
                == registration["slots"][next_slot - 1]["session_id"]
                and payload == expected_start_payload
                and (marker_start_count is None or marker_start_count >= 0),
                "ledger slot start order mismatch",
            )
            active = {
                "marker_start_count": marker_start_count,
                "session_id": record["session_id"],
                "slot_number": next_slot,
            }
        elif event == "slot_terminal":
            checks.require(active is not None, "terminal ledger row has no active slot")
            checks.require(
                record.get("slot_number") == active["slot_number"]
                and record.get("session_id") == active["session_id"],
                "terminal ledger slot mismatch",
            )
            complete = _exact_int(
                payload.get("complete_trajectories"),
                "complete_trajectories",
            )
            marker_start = _exact_int(
                payload.get("marker_start_count"),
                "marker_start_count",
            )
            marker_end = _exact_int(
                payload.get("marker_end_count"),
                "marker_end_count",
            )
            status = payload.get("terminal_status")
            exit_code = payload.get("process_exit_code")
            expected_status = (
                "completed"
                if exit_code == 0 and complete == GAMES_PER_SLOT
                else "interrupted"
            )
            checks.require(status == expected_status, "ledger terminal status mismatch")
            checks.require(
                0 <= complete <= GAMES_PER_SLOT
                and marker_start >= 0
                and marker_end >= marker_start
                and marker_end - marker_start == complete
                and (
                    active["marker_start_count"] is None
                    or marker_start == active["marker_start_count"]
                ),
                "ledger marker accounting mismatch",
            )
            checks.require(
                marker_end_cursor is None or marker_start == marker_end_cursor,
                "ledger marker intervals are not contiguous",
            )
            terminals.append(
                {
                    "complete_trajectories": complete,
                    "marker_end_count": marker_end,
                    "marker_start_count": marker_start,
                    "process_exit_code": exit_code,
                    "session_id": active["session_id"],
                    "slot_number": active["slot_number"],
                    "terminal_status": status,
                }
            )
            active = None
            marker_end_cursor = marker_end
            next_slot += 1
        elif event == "global_stop":
            reason = _required_string(payload.get("reason"), "global stop reason")
            checks.require(
                initialized
                and active is None
                and record.get("slot_number") is None
                and record.get("session_id") is None
                and payload == {"reason": reason},
                "ledger global stop structure mismatch",
            )
            global_stop = {"reason": reason}
        else:
            raise OutcomeEvidenceVerificationError(
                f"unsupported ledger event: {event}"
            )
        previous_hash = record["record_hash"]
    checks.require(initialized, "ledger was not initialized")
    checks.require(active is None, "ledger has an active final slot")
    return {
        "final_record_hash": previous_hash,
        "global_stop": global_stop,
        "terminal_slots": terminals,
    }


def _verify_claim(
    path: Path,
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    checks: _Checks,
) -> Mapping[str, Any]:
    claim = _load_mapping(path)
    checks.require(
        set(claim)
        == {
            "claim_hash",
            "mode",
            "registration_hash",
            "run_lock_hash",
            "schema_version",
            "study_id",
        },
        "finalization claim fields mismatch",
    )
    checks.require(
        claim.get("schema_version") == CLAIM_SCHEMA_VERSION,
        "finalization claim schema mismatch",
    )
    checks.require(
        claim.get("claim_hash") == _self_hash(claim, "claim_hash"),
        "finalization claim hash mismatch",
    )
    checks.require(
        claim.get("mode") in {"complete", "integrity_stop"}
        and claim.get("study_id") == registration["study_id"]
        and claim.get("registration_hash") == registration["registration_hash"]
        and claim.get("run_lock_hash") == run_lock["run_lock_hash"],
        "finalization claim binding mismatch",
    )
    return claim


def _verify_blocked_closeout(
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    paths: Mapping[str, Path],
    checks: _Checks,
) -> dict[str, Any]:
    stop = _mapping(ledger.get("global_stop"), "ledger global stop")
    stop_reason = _required_string(stop.get("reason"), "global stop reason")
    terminal_slots = _sequence(
        ledger.get("terminal_slots"),
        "ledger terminal slots",
    )
    expected_slots = [
        {
            "session_id": str(row["session_id"]),
            "slot_number": int(row["slot_number"]),
            "terminal_status": str(row["terminal_status"]),
        }
        for row in terminal_slots
    ]
    for raw_slot in registration["slots"][len(expected_slots) :]:
        slot = _mapping(raw_slot, "registered slot")
        expected_slots.append(
            {
                "session_id": str(slot["session_id"]),
                "slot_number": int(slot["slot_number"]),
                "terminal_status": "unlaunched",
            }
        )
    checks.require(
        len(expected_slots) == SLOT_COUNT
        and [row["slot_number"] for row in expected_slots]
        == list(range(1, SLOT_COUNT + 1)),
        "blocked closeout slot accounting mismatch",
    )

    metrics = {
        "all_registered_slots_accounted": False,
        "category_arm_support": {
            "card_reward": {"alternative": 0, "baseline": 0},
            "shop": {"alternative": 0, "baseline": 0},
        },
        "complete_trajectory_count": 0,
        "ess_fraction": Fraction(0, 1),
        "global_integrity_stop": True,
        "max_normalized_weight": Fraction(0, 1),
        "nonzero_weight_trajectory_count": 0,
        "supported_victory_count": 0,
    }
    gate = _build_evidence_gate(registration, metrics)
    expected = {
        "blockers": list(gate["blockers"]),
        "closeout_hash": None,
        "evidence_gate": gate,
        "gates": {
            "causal_uplift_ready": False,
            "dataset_ope_readiness_ready": False,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
            "ope_estimate_ready": False,
            "outcome_evidence_expansion_ready": False,
            "policy_comparison_ready": False,
            "reward_design_ready": False,
        },
        "integrity_stop": {"reason": stop_reason},
        "limitations": [
            "Evidence readiness is separate from policy comparison.",
            (
                "No closeout gate authorizes causal claims, training, reward "
                "design, or live promotion."
            ),
        ],
        "registration_hash": registration["registration_hash"],
        "run_lock_hash": run_lock["run_lock_hash"],
        "schema_version": CLOSEOUT_SCHEMA_VERSION,
        "slots": expected_slots,
        "source": {
            "calibration_file_sha256": None,
            "estimate_file_sha256": None,
            "pool_manifest_hash": None,
            "readiness_file_sha256": None,
            "target_manifest_hash": None,
        },
        "status": "blocked",
        "study_id": registration["study_id"],
    }
    expected["closeout_hash"] = _self_hash(expected, "closeout_hash")
    observed = _load_mapping(paths["closeout"])
    checks.require(
        observed == expected,
        "blocked closeout differs from independent reconstruction",
    )
    checks.require(
        paths["closeout"].read_bytes()
        == (_canonical_json(expected) + "\n").encode("utf-8"),
        "blocked closeout JSON rendering mismatch",
    )
    checks.require(
        paths["closeout_markdown"].read_bytes()
        == _render_blocked_closeout_markdown(expected).encode("utf-8"),
        "blocked closeout Markdown rendering mismatch",
    )
    forbidden = (
        "pool_manifest",
        "pool_samples",
        "target",
        "readiness",
        "readiness_markdown",
        "estimate",
        "estimate_markdown",
    )
    existing = sorted(paths[name].name for name in forbidden if paths[name].exists())
    checks.require(
        not existing,
        "blocked closeout has forbidden normal artifacts: " + ", ".join(existing),
    )
    return expected


def _render_blocked_closeout_markdown(closeout: Mapping[str, Any]) -> str:
    lines = [
        "# Non-combat outcome-evidence closeout",
        "",
        f"- Study: `{closeout.get('study_id')}`",
        f"- Status: `{closeout.get('status')}`",
        "",
        "## Integrity stop",
        "",
        (
            "- Reason: "
            + _canonical_json(
                _mapping(closeout.get("integrity_stop"), "integrity stop").get(
                    "reason"
                )
            )
        ),
        "",
        "## Evidence gate",
        "",
        "| Condition | Observed | Required | Passed |",
        "|---|---|---|---|",
    ]
    conditions = closeout["evidence_gate"]["conditions"]
    for code in sorted(conditions):
        condition = conditions[code]
        lines.append(
            f"| `{code}` | `{_canonical_json(condition['observed'])}` | "
            f"`{_canonical_json(condition['required'])}` | "
            f"{'yes' if condition['passed'] else 'no'} |"
        )
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- `{blocker}`" for blocker in closeout["blockers"])
    if not closeout["blockers"]:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Slot status",
            "",
            "| Slot | Session | Status |",
            "|---:|---|---|",
        ]
    )
    for slot in closeout["slots"]:
        lines.append(
            f"| {slot['slot_number']:02d} | `{slot['session_id']}` | "
            f"{slot['terminal_status']} |"
        )
    lines.extend(["", "## Authority gates", ""])
    for gate_name, ready in sorted(closeout["gates"].items()):
        lines.append(f"- `{gate_name}`: `{'true' if ready else 'false'}`")
    return "\n".join(lines) + "\n"


def _verify_pool(
    samples: Sequence[Mapping[str, Any]],
    pool: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(pool.get("schema_version") == POOL_SCHEMA_VERSION, "pool schema")
    checks.require(
        pool.get("pool_manifest_hash")
        == _self_hash(pool, "pool_manifest_hash"),
        "pool manifest hash mismatch",
    )
    rendered_samples = "".join(_canonical_json(row) + "\n" for row in samples)
    checks.require(
        pool.get("sample_jsonl_sha256")
        == hashlib.sha256(rendered_samples.encode("utf-8")).hexdigest(),
        "pool sample hash mismatch",
    )
    checks.require(
        pool.get("study_id") == registration["study_id"]
        and pool.get("registration_hash") == registration["registration_hash"]
        and pool.get("run_lock_hash") == run_lock["run_lock_hash"],
        "pool study binding mismatch",
    )
    ordered = sorted(samples, key=_sample_sort_key)
    checks.require(list(samples) == ordered, "pool sample order is not canonical")
    sample_ids = set()
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    by_session: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    support = Counter()
    registered_session_ids = {
        slot["session_id"] for slot in registration["slots"]
    }
    for raw_sample in samples:
        sample = _mapping(raw_sample, "pool sample")
        sample_id = _required_string(sample.get("sample_id"), "sample_id")
        checks.require(sample_id not in sample_ids, f"duplicate sample_id: {sample_id}")
        sample_ids.add(sample_id)
        exploration = _mapping(sample.get("exploration"), "sample exploration")
        session_id = _required_string(exploration.get("session_id"), "session_id")
        checks.require(
            session_id in registered_session_ids,
            f"sample belongs to an unregistered session: {sample_id}",
        )
        checks.require(
            sample.get("behavior_policy_commit") == run_lock["source"]["commit"]
            and exploration.get("source_commit")
            == run_lock["source"]["commit"],
            f"sample source lock mismatch: {sample_id}",
        )
        category = sample.get("category")
        arm = exploration.get("selected_arm")
        checks.require(
            category in {"card_reward", "shop"}
            and arm in {"baseline", "alternative"},
            f"unsupported sample arm: {sample_id}",
        )
        _verify_sample_probability(sample, checks)
        group_id = _required_string(
            sample.get("trajectory_group_id"),
            "trajectory_group_id",
        )
        groups[group_id].append(sample)
        by_session[session_id].append(sample)
        support[(category, arm)] += 1
    included = _included_trajectory_rows(groups)
    checks.require(
        pool.get("included_trajectories") == included,
        "pool membership does not match canonical samples",
    )
    aggregate_support = {
        category: {
            arm: support[(category, arm)]
            for arm in ("alternative", "baseline")
        }
        for category in ("card_reward", "shop")
    }
    checks.require(
        pool.get("aggregate_arm_support") == aggregate_support,
        "pool arm support mismatch",
    )
    conservative_joins = _reconstruct_conservative_run_joins(
        registration,
        ledger,
        checks=checks,
    )
    exclusion_accounting = _verify_pool_exclusions(
        pool,
        included,
        registration=registration,
        checks=checks,
    )
    slot_rows = _sequence(pool.get("slots"), "pool slots")
    checks.require(len(slot_rows) == SLOT_COUNT, "pool slot count mismatch")
    terminal_by_slot = {
        row["slot_number"]: row for row in ledger["terminal_slots"]
    }
    included_groups_by_session = Counter(
        row["session_id"] for row in included
    )
    included_run_files_by_session: dict[str, list[str]] = defaultdict(list)
    for row in included:
        included_run_files_by_session[str(row["session_id"])].append(
            str(row["run_file"])
        )
    runs_root = conservative_joins["runs_root"]
    for slot, raw_pool_slot in zip(
        registration["slots"],
        slot_rows,
        strict=True,
    ):
        pool_slot = _mapping(raw_pool_slot, "pool slot")
        number = slot["slot_number"]
        terminal = terminal_by_slot[number]
        session_samples = by_session.get(slot["session_id"], [])
        checks.require(
            pool_slot.get("slot_number") == number
            and pool_slot.get("session_id") == slot["session_id"],
            f"pool slot identity mismatch: {number}",
        )
        checks.require(
            pool_slot.get("terminal_status") == terminal["terminal_status"]
            and pool_slot.get("process_exit_code")
            == terminal["process_exit_code"]
            and pool_slot.get("marker_trajectory_count")
            == terminal["complete_trajectories"],
            f"pool slot lifecycle mismatch: {number}",
        )
        checks.require(
            pool_slot.get("included_decision_count") == len(session_samples)
            and pool_slot.get("included_trajectory_count")
            == included_groups_by_session[slot["session_id"]],
            f"pool slot inclusion accounting mismatch: {number}",
        )
        included_count = included_groups_by_session[slot["session_id"]]
        exclusion = exclusion_accounting[number]
        declared_joined_run_files = sorted(
            [
                *included_run_files_by_session[slot["session_id"]],
                *exclusion["joined_excluded_run_files"],
            ],
            key=lambda value: int(Path(value).stem),
        )
        expected_joined_run_files = sorted(
            conservative_joins["by_slot"][number],
            key=lambda value: int(Path(value).stem),
        )
        checks.require(
            declared_joined_run_files == expected_joined_run_files,
            f"conservative run join mismatch: slot {number}",
        )
        checks.require(
            pool_slot.get("excluded_trajectory_count")
            == terminal["complete_trajectories"] - included_count
            and pool_slot.get("joined_run_count")
            == included_count + exclusion["joined_excluded_count"]
            and pool_slot.get("unresolved_join_count")
            == exclusion["unresolved_join_count"]
            and exclusion["excluded_trajectory_count"]
            == terminal["complete_trajectories"] - included_count,
            f"pool slot exclusion accounting mismatch: {number}",
        )
        _verify_session_artifacts(
            slot,
            pool_slot,
            session_samples,
            joined_run_files=declared_joined_run_files,
            runs_root=runs_root,
            registration=registration,
            run_lock=run_lock,
            checks=checks,
        )
    accounting = _mapping(pool.get("accounting"), "pool accounting")
    marker_count = sum(row["complete_trajectories"] for row in ledger["terminal_slots"])
    excluded_count = marker_count - len(groups)
    checks.require(
        accounting
        == {
            "conservative_joined_run_count": sum(
                included_groups_by_session[slot["session_id"]]
                + exclusion_accounting[slot["slot_number"]][
                    "joined_excluded_count"
                ]
                for slot in registration["slots"]
            ),
            "excluded_trajectory_count": excluded_count,
            "included_decision_count": len(samples),
            "included_trajectory_count": len(groups),
            "marker_trajectory_count": marker_count,
            "registered_slot_count": SLOT_COUNT,
        },
        "pool aggregate accounting mismatch",
    )
    checks.require(
        sum(
            row["excluded_trajectory_count"]
            for row in exclusion_accounting.values()
        )
        == excluded_count,
        "pool exclusion accounting mismatch",
    )
    terminal_outcome_hashes = _verify_terminal_outcomes(
        groups,
        registration,
        checks,
    )
    return {
        "ai_marker_file_sha256": conservative_joins[
            "ai_marker_file_sha256"
        ],
        "category_arm_support": aggregate_support,
        "conservative_join_run_file_sha256": conservative_joins[
            "run_file_sha256"
        ],
        "conservative_run_inventory_sha256": conservative_joins[
            "run_inventory_sha256"
        ],
        "groups": groups,
        "terminal_outcome_file_sha256": terminal_outcome_hashes,
    }


def _reconstruct_conservative_run_joins(
    registration: Mapping[str, Any],
    ledger: Mapping[str, Any],
    *,
    checks: _Checks,
) -> dict[str, Any]:
    checkpoint_root = Path(
        str(registration["integrity_rules"]["checkpoint_inventory"]["root"])
    ).resolve()
    runs_parent = checkpoint_root.parent / "runs"
    runs_root = runs_parent / "IRONCLAD"
    marker_path = runs_parent / "ai_games.txt"
    marker_bytes = marker_path.read_bytes()
    try:
        marker_lines = marker_bytes.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise OutcomeEvidenceVerificationError(
            f"cannot decode AI marker file: {exc}"
        ) from exc
    markers = []
    for line in marker_lines:
        value = line.strip()
        if not value:
            continue
        checks.require(
            value.isdigit(),
            "AI marker file contains an invalid marker",
        )
        markers.append(int(value))

    numeric_run_paths = sorted(
        (path for path in runs_root.glob("*.run") if path.stem.isdigit()),
        key=lambda path: (int(path.stem), path.name),
    )
    run_inventory = [path.name for path in numeric_run_paths]
    run_timestamps = [int(path.stem) for path in numeric_run_paths]
    marker_candidates = [
        tuple(
            run_index
            for run_index, run_timestamp in enumerate(run_timestamps)
            if 0 <= marker_timestamp - run_timestamp <= 10
        )
        for marker_timestamp in markers
    ]
    run_candidate_counts = Counter(
        run_index
        for candidates in marker_candidates
        for run_index in candidates
    )
    joined_by_marker = {
        marker_index: run_timestamps[candidates[0]]
        for marker_index, candidates in enumerate(marker_candidates)
        if len(candidates) == 1
        and run_candidate_counts[candidates[0]] == 1
    }

    by_slot = {}
    joined_run_files = set()
    for terminal in ledger["terminal_slots"]:
        marker_start = int(terminal["marker_start_count"])
        marker_end = int(terminal["marker_end_count"])
        checks.require(
            marker_end <= len(markers),
            (
                "slot marker slice exceeds AI marker file: "
                f"{terminal['slot_number']}"
            ),
        )
        slot_run_files = [
            f"{joined_by_marker[index]}.run"
            for index in range(marker_start, marker_end)
            if index in joined_by_marker
        ]
        by_slot[int(terminal["slot_number"])] = slot_run_files
        joined_run_files.update(slot_run_files)

    return {
        "ai_marker_file_sha256": hashlib.sha256(marker_bytes).hexdigest(),
        "by_slot": by_slot,
        "run_file_sha256": {
            run_file: _file_sha256(runs_root / run_file)
            for run_file in sorted(
                joined_run_files,
                key=lambda value: int(Path(value).stem),
            )
        },
        "run_inventory_sha256": hashlib.sha256(
            _canonical_json(run_inventory).encode("utf-8")
        ).hexdigest(),
        "runs_root": runs_root,
    }


def _verify_pool_exclusions(
    pool: Mapping[str, Any],
    included: Sequence[Mapping[str, Any]],
    *,
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[int, dict[str, Any]]:
    rows = _sequence(pool.get("excluded_trajectories"), "excluded trajectories")
    registered_sessions = {
        slot["slot_number"]: slot["session_id"] for slot in registration["slots"]
    }
    accounting = {
        number: {
            "excluded_trajectory_count": 0,
            "joined_excluded_count": 0,
            "joined_excluded_run_files": [],
            "unresolved_join_count": 0,
        }
        for number in registered_sessions
    }
    included_run_files = [str(row["run_file"]) for row in included]
    checks.require(
        len(included_run_files) == len(set(included_run_files)),
        "included pool run files are not unique",
    )
    seen_run_files = set(included_run_files)
    unresolved_slots = set()
    normalized = []
    for raw_row in rows:
        row = dict(_mapping(raw_row, "excluded trajectory"))
        slot_number = _exact_int(row.get("slot_number"), "exclusion slot_number")
        checks.require(
            slot_number in registered_sessions
            and row.get("session_id") == registered_sessions[slot_number],
            "excluded trajectory slot binding mismatch",
        )
        checks.require(
            row.get("trajectory_session_id") is None,
            "excluded trajectory session attribution mismatch",
        )
        reason = row.get("reason")
        if reason == "no_complete_confirmed_decision":
            checks.require(
                set(row)
                == {
                    "reason",
                    "run_file",
                    "session_id",
                    "slot_number",
                    "trajectory_session_id",
                },
                "joined exclusion fields mismatch",
            )
            run_file = _required_string(row.get("run_file"), "excluded run_file")
            checks.require(
                re.fullmatch(r"[0-9]+\.run", run_file) is not None
                and run_file not in seen_run_files,
                "excluded run file is invalid or duplicated",
            )
            seen_run_files.add(run_file)
            accounting[slot_number]["excluded_trajectory_count"] += 1
            accounting[slot_number]["joined_excluded_count"] += 1
            accounting[slot_number]["joined_excluded_run_files"].append(
                run_file
            )
        elif reason == "run_join_missing_or_ambiguous":
            checks.require(
                set(row)
                == {
                    "count",
                    "reason",
                    "run_file",
                    "session_id",
                    "slot_number",
                    "trajectory_session_id",
                }
                and row.get("run_file") is None
                and slot_number not in unresolved_slots,
                "unresolved exclusion fields mismatch",
            )
            count = _exact_int(row.get("count"), "unresolved exclusion count")
            checks.require(count > 0, "unresolved exclusion count is not positive")
            unresolved_slots.add(slot_number)
            accounting[slot_number]["excluded_trajectory_count"] += count
            accounting[slot_number]["unresolved_join_count"] += count
        else:
            raise OutcomeEvidenceVerificationError(
                f"unsupported trajectory exclusion reason: {reason}"
            )
        normalized.append(row)
    checks.require(
        normalized
        == sorted(
            normalized,
            key=lambda row: (
                int(row["slot_number"]),
                str(row.get("run_file") or ""),
                str(row.get("trajectory_session_id") or ""),
                str(row["reason"]),
            ),
        ),
        "excluded trajectories are not canonically ordered",
    )
    return accounting


def _verify_session_artifacts(
    slot: Mapping[str, Any],
    pool_slot: Mapping[str, Any],
    samples: Sequence[Mapping[str, Any]],
    *,
    joined_run_files: Sequence[str],
    runs_root: Path,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    checks: _Checks,
) -> None:
    config_path = Path(str(slot["config_path"]))
    manifest_path = Path(str(slot["manifest_path"]))
    trace_path = Path(str(slot["trace_path"]))
    hashes = _mapping(pool_slot.get("artifact_hashes"), "artifact hashes")
    checks.require(
        hashes.get("config_sha256") == _file_sha256(config_path)
        and hashes.get("manifest_sha256") == _file_sha256(manifest_path)
        and hashes.get("trace_sha256") == _file_sha256(trace_path),
        f"session artifact hash mismatch: {slot['slot_number']}",
    )
    config = _load_mapping(config_path)
    expected_config = {
        "category_rates_bps": {"card_reward": 300, "shop": 1000},
        "enabled_categories": ["card_reward", "shop"],
        "manifest_path": str(manifest_path),
        "per_run_alternative_budget": 2,
        "schema_version": "noncombat-exploration-config-v1",
        "seed": slot["seed"],
        "session_id": slot["session_id"],
        "source_commit": run_lock["source"]["commit"],
        "study_id": registration["study_id"],
        "study_registration_hash": registration["registration_hash"],
        "study_run_lock_hash": run_lock["run_lock_hash"],
        "study_slot_number": slot["slot_number"],
        "trace_path": str(trace_path),
    }
    checks.require(config == expected_config, "session config contract mismatch")
    manifest = _load_mapping(manifest_path)
    manifest_hash_input = dict(manifest)
    supplied_manifest_hash = manifest_hash_input.pop("manifest_hash", None)
    checks.require(
        supplied_manifest_hash
        == hashlib.sha256(
            _canonical_json(manifest_hash_input).encode("utf-8")
        ).hexdigest()
        and hashes.get("manifest_hash") == supplied_manifest_hash,
        "session manifest hash mismatch",
    )
    effective = _mapping(manifest.get("effective_config"), "effective config")
    effective_without_source = dict(effective)
    source_path = effective_without_source.pop("source_path", None)
    checks.require(
        effective_without_source == config and source_path == str(config_path),
        "session manifest effective config mismatch",
    )
    checks.require(
        manifest.get("effective_config_hash")
        == hashlib.sha256(_canonical_json(effective).encode("utf-8")).hexdigest()
        and manifest.get("config_file_sha256") == _file_sha256(config_path),
        "session manifest config hash mismatch",
    )
    checks.require(
        manifest.get("session_id") == slot["session_id"]
        and manifest.get("trace_path") == str(trace_path)
        and manifest.get("manifest_path") == str(manifest_path)
        and manifest.get("python_executable")
        == registration["command"]["python_executable"]
        and manifest.get("command") == run_lock["command"]
        and manifest.get("source")
        == {"commit": run_lock["source"]["commit"], "tracked_clean": True},
        "session manifest provenance mismatch",
    )
    _verify_manifest_isolation(
        manifest,
        run_lock,
        slot_number=slot["slot_number"],
        checks=checks,
    )
    _verify_trace(
        trace_path,
        samples,
        pool_slot,
        joined_run_files=joined_run_files,
        runs_root=runs_root,
        manifest=manifest,
        checks=checks,
    )


def _verify_manifest_isolation(
    manifest: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    *,
    slot_number: int,
    checks: _Checks,
) -> None:
    pre_session = _mapping(
        manifest.get("pre_session_isolation_hashes"),
        "pre-session isolation hashes",
    )
    pre_by_path = {}
    for raw_path, raw_fingerprint in pre_session.items():
        checks.require(
            isinstance(raw_path, str) and isinstance(raw_fingerprint, Mapping),
            f"session isolation entry is invalid: {slot_number}",
        )
        normalized_path = str(Path(raw_path).resolve()).casefold()
        checks.require(
            normalized_path not in pre_by_path,
            f"session isolation path is duplicated: {slot_number}",
        )
        pre_by_path[normalized_path] = raw_fingerprint

    communication = _mapping(
        run_lock.get("communication_mod"),
        "run-lock CommunicationMod",
    )
    communication_path = str(Path(str(communication["path"])).resolve()).casefold()
    observed_communication = pre_by_path.get(communication_path)
    checks.require(
        isinstance(observed_communication, Mapping)
        and observed_communication.get("semantic_sha256")
        == communication.get("semantic_sha256"),
        f"session CommunicationMod isolation mismatch: {slot_number}",
    )

    checkpoints = _mapping(run_lock.get("checkpoints"), "run-lock checkpoints")
    checkpoint_root = Path(str(checkpoints["root"])).resolve()
    patterns = _sequence(checkpoints.get("patterns"), "checkpoint patterns")
    checks.require(
        all(isinstance(pattern, str) and pattern for pattern in patterns),
        "checkpoint patterns are invalid",
    )
    expected_files = {
        str(Path(str(row["path"])).resolve()).casefold(): row
        for row in _sequence(checkpoints.get("files"), "checkpoint files")
    }
    observed_checkpoint_paths = set()
    for raw_path in pre_session:
        path = Path(str(raw_path)).resolve()
        try:
            path.relative_to(checkpoint_root)
        except ValueError:
            continue
        if any(fnmatch.fnmatchcase(path.name, pattern) for pattern in patterns):
            observed_checkpoint_paths.add(str(path).casefold())
    checks.require(
        observed_checkpoint_paths == set(expected_files),
        f"session checkpoint isolation membership mismatch: {slot_number}",
    )
    for normalized_path, expected in expected_files.items():
        observed = pre_by_path.get(normalized_path)
        checks.require(
            isinstance(observed, Mapping)
            and observed.get("sha256") == expected.get("sha256")
            and observed.get("size") == expected.get("size"),
            f"session checkpoint isolation mismatch: {slot_number}",
        )


def _verify_trace(
    path: Path,
    samples: Sequence[Mapping[str, Any]],
    pool_slot: Mapping[str, Any],
    *,
    joined_run_files: Sequence[str],
    runs_root: Path,
    manifest: Mapping[str, Any],
    checks: _Checks,
) -> None:
    rows = _load_jsonl(path)
    proposed = {}
    resolutions = {}
    for row in rows:
        record = _mapping(row, "trace record")
        decision_id = _required_string(record.get("decision_id"), "decision_id")
        record_type = record.get("record_type")
        target = proposed if record_type == "proposed" else resolutions
        checks.require(
            record_type in {"proposed", "resolution"},
            "unsupported trace record type",
        )
        checks.require(decision_id not in target, "duplicate trace decision record")
        target[decision_id] = record
    checks.require(
        set(resolutions).issubset(proposed),
        "trace resolution references an unknown proposal",
    )
    history_errors = _proposal_history_errors(proposed, manifest)
    expected_exclusion_reasons = {
        decision_id: _expected_export_exclusion_reason(
            proposal,
            resolutions.get(decision_id),
            history_errors.get(decision_id),
            manifest,
        )
        for decision_id, proposal in proposed.items()
    }
    sample_ids = set()
    sample_group_ids = {}
    for sample in samples:
        sample_id = str(sample["sample_id"])
        sample_ids.add(sample_id)
        sample_group_ids[sample_id] = str(sample["trajectory_group_id"])
        checks.require(
            sample_id in proposed and sample_id in resolutions,
            f"pool sample is absent from trace: {sample_id}",
        )
        checks.require(
            expected_exclusion_reasons[sample_id] is None,
            f"included proposal should have been excluded: {sample_id}",
        )
        proposal = proposed[sample_id]
        resolution = resolutions[sample_id]
        exploration = sample["exploration"]
        proposal_body = _mapping(proposal.get("proposal"), "trace proposal")
        selection = _mapping(proposal.get("selection"), "trace selection")
        candidate_actions = _sequence(
            sample.get("candidate_actions"),
            "sample candidate actions",
        )
        selected_candidates = [
            candidate
            for candidate in candidate_actions
            if isinstance(candidate, Mapping)
            and candidate.get("action_id") == sample["selected_action_id"]
        ]
        checks.require(
            proposal.get("session_id") == exploration["session_id"]
            and proposal.get("trajectory_session_id")
            == sample["trajectory_session_id"]
            and proposal.get("category") == sample["category"]
            and proposal.get("decision_index") == exploration["decision_index"],
            f"trace proposal identity mismatch: {sample_id}",
        )
        checks.require(
            exploration.get("proposal_record_hash")
            == hashlib.sha256(
                _canonical_json(proposal).encode("utf-8")
            ).hexdigest()
            and exploration.get("resolution_record_hash")
            == hashlib.sha256(
                _canonical_json(resolution).encode("utf-8")
            ).hexdigest()
            and exploration.get("manifest_hash") == manifest.get("manifest_hash")
            and exploration.get("effective_config_hash")
            == manifest.get("effective_config_hash")
            and exploration.get("config_file_sha256")
            == manifest.get("config_file_sha256"),
            f"trace record or manifest binding mismatch: {sample_id}",
        )
        timestamps = (
            proposal.get("trajectory_started_unix"),
            proposal.get("proposed_unix"),
            resolution.get("resolved_unix"),
        )
        checks.require(
            all(
                not isinstance(value, bool)
                and isinstance(value, (int, float))
                and math.isfinite(float(value))
                and float(value) >= 0
                for value in timestamps
            )
            and float(timestamps[0])
            <= float(timestamps[1])
            <= float(timestamps[2])
            and exploration.get("trajectory_started_unix") == timestamps[0]
            and exploration.get("proposed_unix") == timestamps[1]
            and exploration.get("resolved_unix") == timestamps[2],
            f"trace timestamps are invalid or unbound: {sample_id}",
        )
        checks.require(
            proposal.get("behavior_policy_id") == sample["behavior_policy_id"]
            and proposal_body.get("category") == sample["category"]
            and proposal_body.get("baseline_action_id")
            == exploration["baseline_action_id"]
            and proposal_body.get("alternative_action_id")
            == exploration["alternative_action_id"]
            and proposal_body.get("candidates") == candidate_actions
            and proposal_body.get("state_hash") == exploration["state_hash"]
            and proposal_body.get("execution_eligible") is True
            and proposal_body.get("rollout_mode") == "executable",
            f"trace proposal payload mismatch: {sample_id}",
        )
        checks.require(
            _selection_replays(proposal, selection, manifest),
            f"trace deterministic selection replay mismatch: {sample_id}",
        )
        selected_candidate = _mapping(
            proposal.get("selected_candidate"),
            "trace selected candidate",
        )
        checks.require(
            len(selected_candidates) == 1
            and selected_candidate == selected_candidates[0]
            and selected_candidate.get("available") is True
            and selected_candidate.get("executable") is True,
            f"trace selected candidate is not legal: {sample_id}",
        )
        checks.require(
            selection.get("selected_action_id") == sample["selected_action_id"]
            and selection.get("distribution")
            == exploration["candidate_distribution"]
            and selection.get("distribution_hash")
            == exploration["distribution_hash"]
            and selection.get("state_hash") == exploration["state_hash"]
            and selection.get("session_id") == exploration["session_id"]
            and selection.get("trajectory_session_id")
            == sample["trajectory_session_id"]
            and selection.get("category") == sample["category"]
            and selection.get("decision_index")
            == exploration["decision_index"]
            and selection.get("selected_probability_numerator")
            == exploration["selected_probability"]["numerator"]
            and selection.get("selected_probability_denominator")
            == exploration["selected_probability"]["denominator"]
            and selection.get("selected_action_probability")
            == sample["behavior_action_probability"]
            and exploration.get("candidate_legality") == "valid"
            and exploration.get("replay_status") == "valid"
            and exploration.get("confirmation_status") == "confirmed",
            f"trace propensity mismatch: {sample_id}",
        )
        checks.require(
            resolution.get("decision_id") == sample_id
            and resolution.get("session_id") == exploration["session_id"]
            and resolution.get("category") == sample["category"]
            and resolution.get("status") == "confirmed"
            and resolution.get("executed_known_propensity") is True
            and resolution.get("reason") == "confirmed"
            and exploration.get("confirmation_reason")
            == resolution.get("reason")
            and resolution.get("selected_action_id")
            == sample["selected_action_id"]
            and resolution.get("trajectory_session_id")
            == sample["trajectory_session_id"],
            f"trace confirmation mismatch: {sample_id}",
        )
    exclusions = _sequence(pool_slot.get("export_exclusions"), "export exclusions")
    normalized_exclusions = []
    excluded_ids = set()
    for raw_exclusion in exclusions:
        exclusion = dict(_mapping(raw_exclusion, "export exclusion"))
        decision_id = _required_string(
            exclusion.get("decision_id"),
            "excluded decision_id",
        )
        checks.require(
            decision_id in proposed
            and decision_id not in sample_ids
            and decision_id not in excluded_ids,
            f"export exclusion is not a unique excluded proposal: {decision_id}",
        )
        expected_reason = expected_exclusion_reasons[decision_id]
        checks.require(
            expected_reason is not None,
            (
                "confirmed eligible proposal was exported as an exclusion: "
                f"{decision_id}"
            ),
        )
        reason = _required_string(exclusion.get("reason"), "exclusion reason")
        checks.require(
            set(exclusion).issubset({"category", "decision_id", "detail", "reason"})
            and (
                "category" not in exclusion
                or exclusion["category"] == proposed[decision_id].get("category")
            )
            and (
                "detail" not in exclusion
                or isinstance(exclusion["detail"], str)
                and bool(exclusion["detail"])
            )
            and bool(reason),
            f"export exclusion fields mismatch: {decision_id}",
        )
        checks.require(
            reason == expected_reason,
            (
                "export exclusion reason mismatch: "
                f"{decision_id}: expected {expected_reason}, observed {reason}"
            ),
        )
        excluded_ids.add(decision_id)
        normalized_exclusions.append(exclusion)
    checks.require(
        normalized_exclusions
        == sorted(normalized_exclusions, key=_canonical_json),
        "export exclusions are not canonically ordered",
    )
    checks.require(
        excluded_ids
        == {
            decision_id
            for decision_id, reason in expected_exclusion_reasons.items()
            if reason is not None
        },
        "export exclusion membership mismatch",
    )
    checks.require(
        not excluded_ids,
        "normal closeout contains trace export exclusions",
    )

    unattributed = _sequence(
        pool_slot.get("unattributed_sample_groups"),
        "unattributed groups",
    )
    checks.require(
        len(joined_run_files) == len(set(joined_run_files))
        and len(joined_run_files) == pool_slot.get("joined_run_count"),
        "joined run file membership mismatch",
    )
    joined_outcomes = _load_joined_run_outcomes(
        joined_run_files,
        runs_root=runs_root,
    )
    eligible_by_session: dict[str, list[str]] = defaultdict(list)
    matched_group_by_decision = {}
    for decision_id, proposal in proposed.items():
        if expected_exclusion_reasons[decision_id] is not None:
            continue
        trajectory_session_id = _required_string(
            proposal.get("trajectory_session_id"),
            "eligible trajectory_session_id",
        )
        eligible_by_session[trajectory_session_id].append(decision_id)
        matched_group_by_decision[decision_id] = _replay_outcome_join(
            proposal,
            joined_outcomes,
        )

    expected_unattributed = []
    for trajectory_session_id in sorted(eligible_by_session):
        decision_ids = eligible_by_session[trajectory_session_id]
        matched_groups = [
            matched_group_by_decision[decision_id]
            for decision_id in decision_ids
        ]
        all_matched = all(group_id is not None for group_id in matched_groups)
        unique_groups = {group_id for group_id in matched_groups if group_id}
        if all_matched and len(unique_groups) == 1:
            expected_group = next(iter(unique_groups))
            for decision_id in decision_ids:
                checks.require(
                    decision_id in sample_ids,
                    (
                        "eligible proposal was laundered as unattributed: "
                        f"{decision_id}"
                    ),
                )
                checks.require(
                    sample_group_ids[decision_id] == expected_group,
                    f"independent outcome join mismatch: {decision_id}",
                )
            continue
        checks.require(
            not any(decision_id in sample_ids for decision_id in decision_ids),
            (
                "outcome-incomplete trajectory was included in the pool: "
                f"{trajectory_session_id}"
            ),
        )
        expected_unattributed.append(
            {
                "decision_count": len(decision_ids),
                "reason": (
                    "outcome_join_incomplete"
                    if not all_matched
                    else "trajectory_group_conflict"
                ),
                "trajectory_session_id": trajectory_session_id,
            }
        )

    normalized_unattributed = []
    for raw_group in unattributed:
        group = dict(_mapping(raw_group, "unattributed group"))
        checks.require(
            set(group)
            == {"decision_count", "reason", "trajectory_session_id"}
            and _exact_int(
                group.get("decision_count"),
                "unattributed decision_count",
            )
            > 0
            and group.get("reason")
            in {"outcome_join_incomplete", "trajectory_group_conflict"}
            and isinstance(group.get("trajectory_session_id"), str)
            and bool(group["trajectory_session_id"]),
            "unattributed group fields mismatch",
        )
        normalized_unattributed.append(group)
    checks.require(
        normalized_unattributed == expected_unattributed,
        "unattributed groups do not match independent outcome joins",
    )


def _load_joined_run_outcomes(
    run_files: Sequence[str],
    *,
    runs_root: Path,
) -> list[dict[str, Any]]:
    outcomes = []
    for run_file in run_files:
        if (
            not isinstance(run_file, str)
            or re.fullmatch(r"[0-9]+\.run", run_file) is None
        ):
            raise OutcomeEvidenceVerificationError(
                f"joined run file is invalid: {run_file}"
            )
        completed_unix = int(Path(run_file).stem)
        run_path = runs_root / run_file
        record = _load_mapping(run_path)
        playtime = _coerce_outcome_int(record.get("playtime"), default=0) or 0
        floor_reached = (
            _coerce_outcome_int(record.get("floor_reached"), default=0) or 0
        )
        outcomes.append(
            {
                "end_unix": completed_unix,
                "floor_reached": floor_reached,
                "group_id": f"run:{completed_unix}",
                "start_unix": max(0, completed_unix - playtime),
            }
        )
    return outcomes


def _replay_outcome_join(
    proposal: Mapping[str, Any],
    outcomes: Sequence[Mapping[str, Any]],
) -> str | None:
    proposal_body = _mapping(proposal.get("proposal"), "trace proposal")
    state = _mapping(proposal_body.get("state"), "proposal state")
    try:
        sample_time = float(proposal.get("trajectory_started_unix"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(sample_time):
        return None
    sample_floor = _coerce_outcome_int(state.get("floor"), default=None)
    time_matches = [
        outcome
        for outcome in outcomes
        if float(outcome["start_unix"]) - OUTCOME_JOIN_TOLERANCE_SECONDS
        <= sample_time
        <= float(outcome["end_unix"])
    ]
    matches = [
        outcome
        for outcome in time_matches
        if sample_floor is not None
        and sample_floor >= 0
        and int(outcome["floor_reached"]) > 0
        and sample_floor <= int(outcome["floor_reached"])
    ]
    if len(matches) != 1:
        return None
    return str(matches[0]["group_id"])


def _coerce_outcome_int(value: Any, *, default: int | None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _proposal_history_errors(
    proposed: Mapping[str, Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> dict[str, str]:
    config = _mapping(manifest.get("effective_config"), "effective config")
    session_id = _required_string(config.get("session_id"), "config session_id")
    alternative_limit = _exact_int(
        config.get("per_run_alternative_budget"),
        "alternative budget",
    )
    expected_policy_id = f"known-propensity-epsilon-v1:{session_id}"
    errors: dict[str, str] = {}
    trajectories = {}
    for decision_id, record in proposed.items():
        trajectory_id = str(record.get("trajectory_session_id") or "")
        state = trajectories.setdefault(
            trajectory_id,
            {
                "alternative_attempts": 0,
                "history_invalid": False,
                "next_index": 0,
                "seen_indices": set(),
                "started_unix": record.get("trajectory_started_unix"),
            },
        )
        if state["history_invalid"]:
            errors[decision_id] = "trajectory_history_invalid"
            continue
        raw_index = record.get("decision_index")
        if (
            isinstance(raw_index, bool)
            or not isinstance(raw_index, int)
            or raw_index < 0
        ):
            errors[decision_id] = "trajectory_decision_index_mismatch"
            state["history_invalid"] = True
            continue
        if raw_index in state["seen_indices"]:
            errors[decision_id] = "duplicate_trajectory_decision_index"
            state["history_invalid"] = True
            continue
        if raw_index != state["next_index"]:
            errors[decision_id] = "trajectory_decision_index_mismatch"
            state["history_invalid"] = True
            continue
        state["seen_indices"].add(raw_index)
        state["next_index"] = raw_index + 1
        if record.get("trajectory_started_unix") != state["started_unix"]:
            errors[decision_id] = "trajectory_start_mismatch"
            state["history_invalid"] = True
            continue
        proposal = _mapping(record.get("proposal"), "trace proposal")
        state_hash = str(proposal.get("state_hash") or "")
        if not trajectory_id or not state_hash:
            errors.setdefault(decision_id, "trajectory_identity_invalid")
        else:
            identity = {
                "decision_index": raw_index,
                "namespace": "noncombat-exploration-decision-v1",
                "session_id": session_id,
                "state_hash": state_hash,
                "trajectory_session_id": trajectory_id,
            }
            expected_decision_id = "decision-" + hashlib.sha256(
                _canonical_json(identity).encode("utf-8")
            ).hexdigest()[:32]
            if decision_id != expected_decision_id:
                errors.setdefault(decision_id, "decision_id_mismatch")
        if record.get("behavior_policy_id") != expected_policy_id:
            errors.setdefault(decision_id, "behavior_policy_id_mismatch")
        selection = _mapping(record.get("selection"), "trace selection")
        selected_alternative = selection.get(
            "selected_action_id"
        ) == proposal.get("alternative_action_id")
        budget = _mapping(
            record.get("alternative_attempt_budget"),
            "alternative attempt budget",
        )
        if not (
            type(budget.get("limit")) is int
            and budget.get("limit") == alternative_limit
            and type(budget.get("used_before")) is int
            and budget.get("used_before") == state["alternative_attempts"]
            and budget.get("selected_alternative") is selected_alternative
            and state["alternative_attempts"] < alternative_limit
        ):
            errors.setdefault(
                decision_id,
                "alternative_budget_history_mismatch",
            )
        if decision_id in errors:
            state["history_invalid"] = True
        elif selected_alternative:
            state["alternative_attempts"] += 1
    return errors


def _selection_replays(
    proposal_record: Mapping[str, Any],
    selection: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> bool:
    proposal = _mapping(proposal_record.get("proposal"), "trace proposal")
    config = _mapping(manifest.get("effective_config"), "effective config")
    category = str(proposal.get("category") or "")
    enabled_categories = _sequence(
        config.get("enabled_categories"),
        "enabled categories",
    )
    rates = _mapping(config.get("category_rates_bps"), "category rates")
    epsilon_bps = rates.get(category)
    if (
        category not in enabled_categories
        or isinstance(epsilon_bps, bool)
        or not isinstance(epsilon_bps, int)
        or not 0 <= epsilon_bps <= DRAW_BUCKET_COUNT
    ):
        return False
    candidates = _sequence(proposal.get("candidates"), "proposal candidates")
    candidate_ids = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            return False
        action_id = candidate.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            return False
        candidate_ids.append(action_id)
    baseline_action_id = proposal.get("baseline_action_id")
    alternative_action_id = proposal.get("alternative_action_id")
    if (
        not isinstance(baseline_action_id, str)
        or not isinstance(alternative_action_id, str)
        or baseline_action_id == alternative_action_id
        or len(candidate_ids) != len(set(candidate_ids))
        or baseline_action_id not in candidate_ids
        or alternative_action_id not in candidate_ids
    ):
        return False
    state = proposal.get("state")
    if not isinstance(state, Mapping):
        return False
    expected_state_hash = hashlib.sha256(
        _canonical_json(
            {
                "candidates": list(candidates),
                "category": category,
                "state": state,
            }
        ).encode("utf-8")
    ).hexdigest()
    if proposal.get("state_hash") != expected_state_hash:
        return False
    if proposal.get("execution_eligible") is True:
        by_id = {
            str(candidate["action_id"]): candidate for candidate in candidates
        }
        if any(
            by_id[action_id].get("available") is not True
            or by_id[action_id].get("executable") is not True
            for action_id in (baseline_action_id, alternative_action_id)
        ):
            return False
    seed = config.get("seed")
    decision_index = proposal_record.get("decision_index")
    if (
        isinstance(seed, bool)
        or not isinstance(seed, int)
        or isinstance(decision_index, bool)
        or not isinstance(decision_index, int)
        or decision_index < 0
    ):
        return False
    distribution = [
        {
            "action_id": baseline_action_id,
            "denominator": DRAW_BUCKET_COUNT,
            "numerator": DRAW_BUCKET_COUNT - epsilon_bps,
            "value": (DRAW_BUCKET_COUNT - epsilon_bps) / DRAW_BUCKET_COUNT,
        },
        {
            "action_id": alternative_action_id,
            "denominator": DRAW_BUCKET_COUNT,
            "numerator": epsilon_bps,
            "value": epsilon_bps / DRAW_BUCKET_COUNT,
        },
    ]
    draw_input = {
        "alternative_action_id": alternative_action_id,
        "baseline_action_id": baseline_action_id,
        "candidate_action_ids": candidate_ids,
        "category": category,
        "decision_index": decision_index,
        "epsilon_bps": epsilon_bps,
        "schema_version": SELECTION_SCHEMA_VERSION,
        "seed": seed,
        "session_id": config.get("session_id"),
        "state_hash": proposal.get("state_hash"),
        "trajectory_session_id": proposal_record.get("trajectory_session_id"),
    }
    encoded = _canonical_json(draw_input).encode("utf-8")
    acceptance_limit = (1 << 64) - ((1 << 64) % DRAW_BUCKET_COUNT)
    for draw_counter in range(1_000_000):
        digest = hashlib.sha256(
            encoded + b"\x00" + str(draw_counter).encode("ascii")
        ).digest()
        draw_u64 = int.from_bytes(digest[:8], byteorder="big", signed=False)
        if draw_u64 < acceptance_limit:
            break
    else:
        raise OutcomeEvidenceVerificationError(
            "cannot derive deterministic exploration draw"
        )
    draw_bucket = draw_u64 % DRAW_BUCKET_COUNT
    selected_action_id = (
        alternative_action_id
        if draw_bucket < epsilon_bps
        else baseline_action_id
    )
    selected_probability = next(
        row for row in distribution if row["action_id"] == selected_action_id
    )
    expected = {
        "category": category,
        "decision_index": decision_index,
        "distribution": distribution,
        "distribution_hash": hashlib.sha256(
            _canonical_json(distribution).encode("utf-8")
        ).hexdigest(),
        "draw_bucket": draw_bucket,
        "draw_counter": draw_counter,
        "draw_input_hash": hashlib.sha256(encoded).hexdigest(),
        "draw_u64": draw_u64,
        "schema_version": SELECTION_SCHEMA_VERSION,
        "selected_action_id": selected_action_id,
        "selected_action_probability": selected_probability["value"],
        "selected_probability_denominator": selected_probability["denominator"],
        "selected_probability_numerator": selected_probability["numerator"],
        "session_id": config.get("session_id"),
        "state_hash": proposal.get("state_hash"),
        "trajectory_session_id": proposal_record.get("trajectory_session_id"),
    }
    return dict(selection) == expected


def _expected_export_exclusion_reason(
    proposal: Mapping[str, Any],
    resolution: Mapping[str, Any] | None,
    history_error: str | None,
    manifest: Mapping[str, Any],
) -> str | None:
    proposal_body = _mapping(proposal.get("proposal"), "trace proposal")
    if not bool(proposal_body.get("execution_eligible")):
        return "shadow_only"
    if history_error is not None:
        return history_error
    if not isinstance(resolution, Mapping):
        return "confirmation_missing"
    status = str(resolution.get("status") or "missing")
    if status != "confirmed" or not bool(
        resolution.get("executed_known_propensity")
    ):
        return f"confirmation_{status}"
    if not _resolution_matches_proposal(proposal, resolution):
        return "confirmation_link_mismatch"
    if not _trace_timestamps_are_monotonic(proposal, resolution):
        return "timestamp_order_invalid"
    selection = proposal.get("selection")
    if not isinstance(selection, Mapping):
        return "replay_mismatch"
    try:
        replay_valid = _selection_replays(proposal, selection, manifest)
    except (OutcomeEvidenceVerificationError, KeyError, TypeError, ValueError):
        replay_valid = False
    if not replay_valid:
        return "replay_mismatch"
    try:
        candidate_legal = _selected_candidate_is_legal(proposal, selection)
    except (OutcomeEvidenceVerificationError, KeyError, TypeError, ValueError):
        candidate_legal = False
    if not candidate_legal:
        return "selected_candidate_illegal"
    return None


def _resolution_matches_proposal(
    proposal: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> bool:
    selection = proposal.get("selection")
    return isinstance(selection, Mapping) and all(
        resolution.get(field) == proposal.get(field)
        for field in (
            "decision_id",
            "session_id",
            "trajectory_session_id",
            "category",
        )
    ) and resolution.get("selected_action_id") == selection.get(
        "selected_action_id"
    )


def _selected_candidate_is_legal(
    proposal: Mapping[str, Any],
    selection: Mapping[str, Any],
) -> bool:
    selected_candidate = proposal.get("selected_candidate")
    if not isinstance(selected_candidate, Mapping):
        return False
    if selected_candidate.get("action_id") != selection.get("selected_action_id"):
        return False
    proposal_body = _mapping(proposal.get("proposal"), "trace proposal")
    matching_candidates = [
        candidate
        for candidate in _sequence(
            proposal_body.get("candidates"),
            "proposal candidates",
        )
        if isinstance(candidate, Mapping)
        and candidate.get("action_id") == selection.get("selected_action_id")
    ]
    if len(matching_candidates) != 1:
        return False
    candidate = matching_candidates[0]
    return all(
        (
            candidate.get("available") is True,
            candidate.get("executable") is True,
            selected_candidate.get("available") is True,
            selected_candidate.get("executable") is True,
            selected_candidate.get("kind") == candidate.get("kind"),
            selected_candidate.get("label") == candidate.get("label"),
            selected_candidate.get("raw", {}) == candidate.get("raw", {}),
        )
    )


def _trace_timestamps_are_monotonic(
    proposal: Mapping[str, Any],
    resolution: Mapping[str, Any],
) -> bool:
    values = (
        proposal.get("trajectory_started_unix"),
        proposal.get("proposed_unix"),
        resolution.get("resolved_unix"),
    )
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
        for value in values
    ):
        return False
    started, proposed_unix, resolved_unix = (float(value) for value in values)
    return started <= proposed_unix <= resolved_unix


def _verify_sample_probability(
    sample: Mapping[str, Any],
    checks: _Checks,
) -> None:
    exploration = _mapping(sample.get("exploration"), "sample exploration")
    selected = _fraction(
        exploration.get("selected_probability"),
        "selected probability",
    )
    distribution = _sequence(
        exploration.get("candidate_distribution"),
        "candidate distribution",
    )
    probabilities = {}
    for raw_row in distribution:
        row = _mapping(raw_row, "candidate probability")
        action_id = _required_string(row.get("action_id"), "probability action_id")
        probability = _fraction(row, "candidate probability")
        checks.require(action_id not in probabilities, "duplicate behavior action")
        probabilities[action_id] = probability
    checks.require(
        sum(probabilities.values(), Fraction(0, 1)) == 1,
        "behavior distribution does not sum to one",
    )
    checks.require(
        probabilities.get(sample.get("selected_action_id")) == selected
        and sample.get("behavior_probability_status")
        == "verified_known_propensity"
        and sample.get("behavior_action_probability") == float(selected),
        "selected behavior probability mismatch",
    )


def _included_trajectory_rows(
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    for group_id in sorted(groups, key=_group_sort_key):
        decisions = groups[group_id]
        outcome = _mapping(decisions[0].get("outcome"), "trajectory outcome")
        session_id = decisions[0]["exploration"]["session_id"]
        trajectory_session_id = decisions[0]["trajectory_session_id"]
        for decision in decisions[1:]:
            if (
                decision.get("outcome") != outcome
                or decision["exploration"]["session_id"] != session_id
                or decision.get("trajectory_session_id")
                != trajectory_session_id
            ):
                raise OutcomeEvidenceVerificationError(
                    f"trajectory content conflicts: {group_id}"
                )
        rows.append(
            {
                "decision_count": len(decisions),
                "group_id": group_id,
                "run_file": outcome["run_file"],
                "session_id": session_id,
                "trajectory_session_id": trajectory_session_id,
            }
        )
    return rows


def _verify_terminal_outcomes(
    groups: Mapping[str, Sequence[Mapping[str, Any]]],
    registration: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, str]:
    checkpoint_root = Path(
        registration["integrity_rules"]["checkpoint_inventory"]["root"]
    )
    runs_root = checkpoint_root.resolve().parent / "runs" / "IRONCLAD"
    hashes = {}
    for group_id in sorted(groups, key=_group_sort_key):
        decisions = groups[group_id]
        outcome = _mapping(decisions[0].get("outcome"), "sample outcome")
        run_file = _required_string(outcome.get("run_file"), "run_file")
        run_path = runs_root / run_file
        run_bytes = run_path.read_bytes()
        raw = _load_mapping_bytes(run_bytes, run_path)
        checks.require(
            raw.get("victory") is outcome.get("victory")
            and raw.get("floor_reached") == outcome.get("floor_reached")
            and raw.get("killed_by") == outcome.get("killed_by")
            and raw.get("playtime") == outcome.get("playtime"),
            f"terminal outcome mismatch: {group_id}",
        )
        hashes[run_file] = hashlib.sha256(run_bytes).hexdigest()
    return hashes


def _recompute_metrics(
    samples: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    pool_result: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, Any]:
    checks.require(
        target.get("construction_mode") == "current_deterministic"
        and target.get("diagnostic_only") is False,
        "target is not deterministic Current",
    )
    entries = _sequence(target.get("entries"), "target entries")
    by_sample = {}
    for raw_entry in entries:
        entry = _mapping(raw_entry, "target entry")
        sample_id = _required_string(entry.get("sample_id"), "target sample_id")
        checks.require(sample_id not in by_sample, "duplicate target sample_id")
        probabilities = {}
        for raw_probability in _sequence(
            entry.get("probabilities"),
            "target probabilities",
        ):
            row = _mapping(raw_probability, "target probability")
            action_id = _required_string(row.get("action_id"), "target action")
            probabilities[action_id] = _fraction(row, "target probability")
        checks.require(
            sum(probabilities.values(), Fraction(0, 1)) == 1,
            f"target probabilities do not sum to one: {sample_id}",
        )
        by_sample[sample_id] = probabilities
    checks.require(len(by_sample) == len(samples), "target sample coverage mismatch")
    weights = {}
    outcomes = {}
    arm_decisions = Counter()
    arm_trajectories: dict[tuple[str, str], set[str]] = defaultdict(set)
    for sample in samples:
        sample_id = str(sample["sample_id"])
        checks.require(sample_id in by_sample, f"missing target sample: {sample_id}")
        selected = str(sample["selected_action_id"])
        behavior = _fraction(
            sample["exploration"]["selected_probability"],
            "behavior probability",
        )
        target_probability = by_sample[sample_id].get(selected, Fraction(0, 1))
        group_id = str(sample["trajectory_group_id"])
        category = str(sample["category"])
        selected_arm = str(sample["exploration"]["selected_arm"])
        arm_key = (category, selected_arm)
        arm_decisions[arm_key] += 1
        arm_trajectories[arm_key].add(group_id)
        weights[group_id] = weights.get(group_id, Fraction(1, 1)) * (
            target_probability / behavior
        )
        outcome = sample["outcome"]
        if group_id in outcomes and outcomes[group_id] != outcome:
            raise OutcomeEvidenceVerificationError(
                f"trajectory outcome conflict: {group_id}"
            )
        outcomes[group_id] = outcome
    weight_sum = sum(weights.values(), Fraction(0, 1))
    squared_sum = sum((weight * weight for weight in weights.values()), Fraction(0, 1))
    ess = (
        weight_sum * weight_sum / squared_sum
        if squared_sum > 0
        else Fraction(0, 1)
    )
    trajectory_count = len(weights)
    ess_fraction = ess / (trajectory_count or 1)
    max_normalized = (
        max(weights.values(), default=Fraction(0, 1)) / weight_sum
        if weight_sum > 0
        else Fraction(0, 1)
    )
    supported = [
        {
            "group_id": group_id,
            "weight": _fraction_record(weights[group_id]),
        }
        for group_id in sorted(weights, key=_group_sort_key)
        if outcomes[group_id].get("victory") is True and weights[group_id] > 0
    ]
    readiness_support = {
        category: {
            arm: {
                "decision_count": arm_decisions[(category, arm)],
                "trajectory_count": len(arm_trajectories[(category, arm)]),
            }
            for arm in ("alternative", "baseline")
        }
        for category in ("card_reward", "shop")
    }
    return {
        "all_registered_slots_accounted": True,
        "category_arm_support": pool_result["category_arm_support"],
        "complete_trajectory_count": trajectory_count,
        "ess_fraction": ess_fraction,
        "global_integrity_stop": False,
        "max_normalized_weight": max_normalized,
        "nonzero_weight_trajectory_count": sum(
            weight > 0 for weight in weights.values()
        ),
        "readiness_category_arm_support": readiness_support,
        "supported_victories": supported,
        "supported_victory_count": len(supported),
    }


def _verify_readiness_metrics(
    readiness: Mapping[str, Any],
    metrics: Mapping[str, Any],
    checks: _Checks,
) -> None:
    diagnostics = _mapping(readiness.get("diagnostics"), "readiness diagnostics")
    checks.require(
        diagnostics.get("trajectory_count")
        == metrics["complete_trajectory_count"]
        and diagnostics.get("nonzero_weight_count")
        == metrics["nonzero_weight_trajectory_count"]
        and _fraction(diagnostics.get("ess_fraction"), "readiness ESS fraction")
        == metrics["ess_fraction"]
        and _fraction(
            diagnostics.get("max_normalized_weight"),
            "readiness maximum normalized weight",
        )
        == metrics["max_normalized_weight"]
        and diagnostics.get("category_arm_support")
        == metrics["readiness_category_arm_support"],
        "readiness diagnostics differ from independent metrics",
    )


def _verify_estimate(
    estimate: Mapping[str, Any],
    *,
    paths: Mapping[str, Path],
    registration: Mapping[str, Any],
    readiness: Mapping[str, Any],
    readiness_audit: Mapping[str, Any],
    checks: _Checks,
) -> dict[str, bool]:
    schema = estimate.get("schema_version")
    if schema == ESTIMATE_SCHEMA_VERSION:
        try:
            verify_estimate_artifact(
                sample_path=paths["pool_samples"],
                target_manifest_path=paths["target"],
                readiness_path=paths["readiness"],
                estimate_path=paths["estimate"],
                calibration_path=paths["calibration"],
            )
        except EstimateVerificationError as exc:
            raise OutcomeEvidenceVerificationError(
                f"OPE estimate replay failed: {exc}"
            ) from exc
    elif schema == BLOCKED_ESTIMATE_SCHEMA_VERSION:
        checks.require(
            bool(readiness_audit.get("overlap_blockers")),
            "blocked estimate has no independently replayed overlap blocker",
        )
        source = _mapping(estimate.get("source"), "blocked estimate source")
        expected_source = {
            "calibration_file_sha256": _file_sha256(paths["calibration"]),
            "estimate_artifact_implementation_sha256": _file_sha256(
                Path(registration["repo_root"])
                / "analysis_scripts/noncombat_ope_estimate_artifacts.py"
            ),
            "estimator_implementation_sha256": _file_sha256(
                Path(registration["repo_root"])
                / "analysis_scripts/noncombat_ope_estimation.py"
            ),
            "readiness_file_sha256": _file_sha256(paths["readiness"]),
            "sample_file_sha256": _file_sha256(paths["pool_samples"]),
            "target_file_sha256": _file_sha256(paths["target"]),
        }
        checks.require(source == expected_source, "blocked estimate source mismatch")
        analysis = registration["analysis_rules"]
        checks.require(
            estimate.get("contracts")
            == {
                "bootstrap_confidence_level": {
                    "denominator": 20,
                    "numerator": 19,
                    "value": 0.95,
                },
                "bootstrap_seed": analysis["bootstrap_seed"],
                "primary_outcome": "victory",
                "production_bootstrap_replicates": 10_000,
                "terminal_horizon": "complete_run",
            },
            "blocked estimate production contract mismatch",
        )
        expected_gates = {
            "causal_uplift_ready": False,
            "dataset_estimation_ready": False,
            "formal_noncombat_rl_training_ready": False,
            "live_policy_promotion_ready": False,
            "ope_estimate_ready": False,
            "policy_comparison_ready": False,
            "reward_design_ready": False,
        }
        checks.require(
            estimate.get("estimates") is None
            and estimate.get("bootstrap") is None
            and estimate.get("influence") is None
            and estimate.get("gates") == expected_gates
            and estimate.get("blockers") == ["dataset_estimation_not_ready"]
            and estimate.get("readiness_blockers")
            == sorted(str(value) for value in readiness.get("blockers", [])),
            "blocked estimate widened authority or changed blockers",
        )
    else:
        raise OutcomeEvidenceVerificationError("estimate schema mismatch")
    gates = _mapping(estimate.get("gates"), "estimate gates")
    return {
        "ope_estimate_ready": gates.get("ope_estimate_ready") is True,
        "policy_comparison_ready": gates.get("policy_comparison_ready") is True,
    }


def _build_evidence_gate(
    registration: Mapping[str, Any],
    metrics: Mapping[str, Any],
) -> dict[str, Any]:
    thresholds = registration["thresholds"]
    minimum_nonzero = _fraction(
        thresholds["minimum_nonzero_weight_fraction"],
        "minimum nonzero fraction",
    )
    minimum_ess = _fraction(
        thresholds["minimum_ess_fraction"],
        "minimum ESS fraction",
    )
    maximum_weight = _fraction(
        thresholds["maximum_normalized_weight"],
        "maximum normalized weight",
    )
    conditions = {}

    def add(code: str, observed: Any, required: Any, passed: bool) -> None:
        conditions[code] = {
            "observed": _gate_value(observed),
            "passed": passed is True,
            "required": _gate_value(required),
        }

    add(
        "all_registered_slots_accounted",
        metrics["all_registered_slots_accounted"],
        True,
        metrics["all_registered_slots_accounted"],
    )
    add(
        "no_global_integrity_stop",
        metrics["global_integrity_stop"],
        False,
        not metrics["global_integrity_stop"],
    )
    complete = metrics["complete_trajectory_count"]
    minimum_complete = thresholds["minimum_complete_trajectories"]
    add(
        "minimum_complete_trajectories",
        complete,
        minimum_complete,
        complete >= minimum_complete,
    )
    minimum_arm = thresholds["minimum_arm_decisions_per_category"]
    for category in ("card_reward", "shop"):
        for arm in ("baseline", "alternative"):
            observed = metrics["category_arm_support"][category][arm]
            add(
                f"minimum_{category}_{arm}_decisions",
                observed,
                minimum_arm,
                observed >= minimum_arm,
            )
    minimum_count = (
        complete * minimum_nonzero.numerator
        + minimum_nonzero.denominator
        - 1
    ) // minimum_nonzero.denominator
    nonzero_count = metrics["nonzero_weight_trajectory_count"]
    add(
        "minimum_nonzero_weight_fraction",
        {
            "count": nonzero_count,
            "fraction": _fraction_record(Fraction(nonzero_count, complete or 1)),
        },
        {
            "fraction": _fraction_record(minimum_nonzero),
            "minimum_count": minimum_count,
        },
        nonzero_count >= minimum_count,
    )
    add(
        "minimum_ess_fraction",
        metrics["ess_fraction"],
        minimum_ess,
        metrics["ess_fraction"] >= minimum_ess,
    )
    add(
        "maximum_normalized_weight",
        metrics["max_normalized_weight"],
        maximum_weight,
        metrics["max_normalized_weight"] <= maximum_weight,
    )
    supported = metrics["supported_victory_count"]
    minimum_supported = thresholds["minimum_supported_victories"]
    add(
        "minimum_supported_victories",
        supported,
        minimum_supported,
        supported >= minimum_supported,
    )
    blockers = sorted(
        code for code, condition in conditions.items() if not condition["passed"]
    )
    return {
        "blockers": blockers,
        "conditions": conditions,
        "outcome_evidence_expansion_ready": not blockers,
        "schema_version": EVIDENCE_GATE_SCHEMA_VERSION,
        "study_id": registration["study_id"],
    }


def _verify_closeout(
    closeout: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    run_lock: Mapping[str, Any],
    ledger: Mapping[str, Any],
    pool: Mapping[str, Any],
    target: Mapping[str, Any],
    readiness: Mapping[str, Any],
    estimate_result: Mapping[str, bool],
    expected_gate: Mapping[str, Any],
    paths: Mapping[str, Path],
    checks: _Checks,
) -> None:
    checks.require(
        set(closeout)
        == {
            "blockers",
            "closeout_hash",
            "evidence_gate",
            "gates",
            "integrity_stop",
            "limitations",
            "registration_hash",
            "run_lock_hash",
            "schema_version",
            "slots",
            "source",
            "status",
            "study_id",
        },
        "closeout fields mismatch",
    )
    checks.require(
        closeout.get("schema_version") == CLOSEOUT_SCHEMA_VERSION,
        "closeout schema mismatch",
    )
    checks.require(
        closeout.get("closeout_hash") == _self_hash(closeout, "closeout_hash"),
        "closeout hash mismatch",
    )
    checks.require(
        closeout.get("study_id") == registration["study_id"]
        and closeout.get("registration_hash") == registration["registration_hash"]
        and closeout.get("run_lock_hash") == run_lock["run_lock_hash"],
        "closeout study binding mismatch",
    )
    checks.require(
        closeout.get("source")
        == {
            "calibration_file_sha256": _file_sha256(paths["calibration"]),
            "estimate_file_sha256": _file_sha256(paths["estimate"]),
            "pool_manifest_hash": pool["pool_manifest_hash"],
            "readiness_file_sha256": _file_sha256(paths["readiness"]),
            "target_manifest_hash": target["manifest_hash"],
        },
        "closeout source binding mismatch",
    )
    expected_slots = [
        {
            "session_id": row["session_id"],
            "slot_number": row["slot_number"],
            "terminal_status": row["terminal_status"],
        }
        for row in ledger["terminal_slots"]
    ]
    checks.require(closeout.get("slots") == expected_slots, "closeout slots mismatch")
    checks.require(
        closeout.get("evidence_gate") == expected_gate,
        "closeout evidence gate differs from independent replay",
    )
    readiness_gates = _mapping(readiness.get("readiness"), "readiness gates")
    dataset_ready = (
        readiness_gates.get("outcome_contract_ready") is True
        and readiness_gates.get("overlap_ready") is True
        and readiness_gates.get("target_policy_ready") is True
    )
    evidence_ready = expected_gate["outcome_evidence_expansion_ready"] is True
    expected_gates = {
        "causal_uplift_ready": False,
        "dataset_ope_readiness_ready": dataset_ready,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
        "ope_estimate_ready": estimate_result["ope_estimate_ready"],
        "outcome_evidence_expansion_ready": evidence_ready,
        "policy_comparison_ready": estimate_result["policy_comparison_ready"],
        "reward_design_ready": False,
    }
    checks.require(
        closeout.get("gates") == expected_gates,
        "closeout authority or readiness gates mismatch",
    )
    checks.require(
        closeout.get("limitations")
        == [
            "Evidence readiness is separate from policy comparison.",
            (
                "No closeout gate authorizes causal claims, training, "
                "reward design, or live promotion."
            ),
        ],
        "closeout authority limitations mismatch",
    )
    expected_status = "ready" if evidence_ready else "inconclusive"
    checks.require(
        closeout.get("status") == expected_status
        and closeout.get("blockers") == expected_gate["blockers"]
        and closeout.get("integrity_stop") is None,
        "closeout status mismatch",
    )


def _properties_semantic_sha256(path: Path) -> str:
    content = path.read_text(encoding="iso-8859-1")
    natural_lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    properties = {}
    for logical_line in _java_properties_logical_lines(natural_lines):
        parsed = _parse_java_property(logical_line)
        if parsed is not None:
            key, value = parsed
            properties[key] = value
    payload = (_canonical_json(properties) + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _java_properties_logical_lines(lines: Sequence[str]):
    pending = ""
    continuing = False
    for natural_line in lines:
        if not continuing and natural_line.lstrip(" \t\f").startswith(("#", "!")):
            yield natural_line
            continue
        piece = natural_line.lstrip(" \t\f") if continuing else natural_line
        pending += piece
        trailing_backslashes = len(pending) - len(pending.rstrip("\\"))
        if trailing_backslashes % 2 == 1:
            pending = pending[:-1]
            continuing = True
            continue
        yield pending
        pending = ""
        continuing = False
    if pending or continuing:
        yield pending


def _parse_java_property(line: str) -> tuple[str, str] | None:
    content = line.lstrip(" \t\f")
    if not content or content.startswith(("#", "!")):
        return None
    key_end = len(content)
    value_start = len(content)
    escaped = False
    for index, character in enumerate(content):
        if escaped:
            escaped = False
            continue
        if character == "\\":
            escaped = True
            continue
        if character in "=: \t\f":
            key_end = index
            value_start = index
            break
    while value_start < len(content) and content[value_start] in " \t\f":
        value_start += 1
    if value_start < len(content) and content[value_start] in "=:":
        value_start += 1
    while value_start < len(content) and content[value_start] in " \t\f":
        value_start += 1
    return (
        _decode_java_property_escapes(content[:key_end]),
        _decode_java_property_escapes(content[value_start:]),
    )


def _decode_java_property_escapes(value: str) -> str:
    decoded = []
    index = 0
    escapes = {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}
    while index < len(value):
        character = value[index]
        if character != "\\":
            decoded.append(character)
            index += 1
            continue
        index += 1
        if index >= len(value):
            raise OutcomeEvidenceVerificationError(
                "invalid trailing escape in CommunicationMod config"
            )
        escaped = value[index]
        if escaped == "u":
            digits = value[index + 1 : index + 5]
            if len(digits) != 4 or any(
                digit not in "0123456789abcdefABCDEF" for digit in digits
            ):
                raise OutcomeEvidenceVerificationError(
                    "invalid Unicode escape in CommunicationMod config"
                )
            decoded.append(chr(int(digits, 16)))
            index += 5
            continue
        decoded.append(escapes.get(escaped, escaped))
        index += 1
    return "".join(decoded)


def _load_mapping(path: Path) -> dict[str, Any]:
    return _load_mapping_bytes(path.read_bytes(), path)


def _load_mapping_bytes(data: bytes, path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OutcomeEvidenceVerificationError(f"invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OutcomeEvidenceVerificationError(
            f"JSON artifact is not an object: {path}"
        )
    return value


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise OutcomeEvidenceVerificationError(f"partial JSONL artifact: {path}")
    rows = []
    for line_number, raw_line in enumerate(data.splitlines(), start=1):
        try:
            value = json.loads(
                raw_line.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_constant,
            )
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise OutcomeEvidenceVerificationError(
                f"invalid JSONL row {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(value, dict):
            raise OutcomeEvidenceVerificationError(
                f"JSONL row is not an object: {path}:{line_number}"
            )
        rows.append(value)
    return rows


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _self_hash(value: Mapping[str, Any], field: str) -> str:
    payload = deepcopy(dict(value))
    payload[field] = None
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_PATTERN.fullmatch(value) is not None


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OutcomeEvidenceVerificationError(f"{field} must be an object")
    return value


def _sequence(value: Any, field: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise OutcomeEvidenceVerificationError(f"{field} must be a list")
    return value


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise OutcomeEvidenceVerificationError(f"{field} must be nonempty")
    return value


def _absolute_path(value: Any, field: str) -> Path:
    raw = _required_string(value, field)
    path = Path(raw)
    if not path.is_absolute() or str(path.resolve()) != raw:
        raise OutcomeEvidenceVerificationError(f"{field} must be resolved absolute")
    return path


def _exact_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OutcomeEvidenceVerificationError(f"{field} must be an integer")
    return value


def _fraction(value: Any, field: str) -> Fraction:
    record = _mapping(value, field)
    numerator = _exact_int(record.get("numerator"), f"{field}.numerator")
    denominator = _exact_int(record.get("denominator"), f"{field}.denominator")
    if denominator <= 0 or numerator < 0:
        raise OutcomeEvidenceVerificationError(f"{field} is invalid")
    result = Fraction(numerator, denominator)
    if "value" in record and record.get("value") != float(result):
        raise OutcomeEvidenceVerificationError(f"{field}.value is not exact")
    return result


def _fraction_record(value: Fraction) -> dict[str, int | float]:
    return {
        "denominator": value.denominator,
        "numerator": value.numerator,
        "value": float(value),
    }


def _gate_value(value: Any) -> Any:
    if isinstance(value, Fraction):
        return _fraction_record(value)
    if isinstance(value, Mapping):
        return {
            str(key): _gate_value(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_gate_value(item) for item in value]
    return value


def _group_sort_key(group_id: str) -> int:
    if not group_id.startswith("run:") or not group_id[4:].isdigit():
        raise OutcomeEvidenceVerificationError(f"invalid trajectory group: {group_id}")
    return int(group_id[4:])


def _sample_sort_key(sample: Mapping[str, Any]) -> tuple[int, int, str]:
    return (
        _group_sort_key(str(sample.get("trajectory_group_id"))),
        _exact_int(sample["exploration"].get("decision_index"), "decision_index"),
        str(sample.get("sample_id")),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify a non-combat outcome-evidence study.",
        allow_abbrev=False,
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--registration", type=Path)
    source.add_argument(
        "--qualification-request-source",
        "--qualification-request",
        dest="qualification_request_source",
        type=Path,
    )
    parser.add_argument("--qualification-result", type=Path)
    parser.add_argument("--qualification-request-hash")
    parser.add_argument("--qualification-request-file-sha256")
    parser.add_argument("--qualification-request-size", type=int)
    parser.add_argument("--qualification-review-commit")
    parser.add_argument("--qualification-result-hash")
    parser.add_argument("--qualification-result-file-sha256")
    parser.add_argument("--qualification-result-size", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    qualification_anchor_names = (
        "qualification_request_hash",
        "qualification_request_file_sha256",
        "qualification_request_size",
        "qualification_review_commit",
    )
    supplied_anchors = [
        getattr(args, name) is not None for name in qualification_anchor_names
    ]
    qualification_result_anchor_names = (
        "qualification_result_hash",
        "qualification_result_file_sha256",
        "qualification_result_size",
    )
    supplied_result_anchors = [
        getattr(args, name) is not None
        for name in qualification_result_anchor_names
    ]
    if args.registration is not None and (
        args.qualification_result is not None
        or any(supplied_anchors)
        or any(supplied_result_anchors)
    ):
        parser.error("qualification replay options require a request source")
    if args.qualification_request_source is not None and not all(
        supplied_anchors
    ):
        parser.error(
            "qualification replay requires request hash, file hash, byte count, "
            "and review commit"
        )
    if args.qualification_result is not None and not all(
        supplied_result_anchors
    ):
        parser.error(
            "qualification terminal replay requires result hash, file hash, "
            "and byte count"
        )
    if args.qualification_result is None and any(supplied_result_anchors):
        parser.error("qualification result anchors require terminal evidence")
    try:
        if args.registration is not None:
            audit = verify_outcome_evidence_expansion(args.registration)
        else:
            audit_output_kwargs = (
                {"audit_output_path": args.output}
                if args.output is not None
                else {}
            )
            audit = verify_prelock_qualification(
                args.qualification_request_source,
                args.qualification_result,
                expected_review_commit=args.qualification_review_commit,
                expected_request_hash=args.qualification_request_hash,
                expected_request_file_sha256=(
                    args.qualification_request_file_sha256
                ),
                expected_request_size=args.qualification_request_size,
                expected_result_hash=args.qualification_result_hash,
                expected_result_file_sha256=(
                    args.qualification_result_file_sha256
                ),
                expected_result_size=args.qualification_result_size,
                **audit_output_kwargs,
            )
        rendered = render_verification_audit(audit)
        if args.output is not None and args.registration is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8", newline="")
        print(rendered, end="")
        return 0
    except Exception as exc:
        print(f"[outcome-evidence-verifier] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
