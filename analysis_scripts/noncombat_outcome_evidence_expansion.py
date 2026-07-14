"""Pre-registered, fixed-schedule non-combat outcome evidence study helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


REGISTRATION_SCHEMA_VERSION = "noncombat-outcome-evidence-registration-v1"
RUN_LOCK_SCHEMA_VERSION = "noncombat-outcome-evidence-run-lock-v1"
SLOT_COUNT = 24
GAMES_PER_SLOT = 25
SCHEDULED_ATTEMPTS = SLOT_COUNT * GAMES_PER_SLOT
COMMAND_ARGUMENTS = (
    "--agent",
    "combat_rl",
    "--elite-route",
    "conservative",
    "--max-games",
    str(GAMES_PER_SLOT),
    "--ascension",
    "0",
    "--rl-version",
    "v2",
    "--eval",
)
_STUDY_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SUPPORTED_WINDOWS_PYTHON = str(Path(r"D:\anaconda\envs\stsai\python.exe").resolve())
DEFAULT_COMMUNICATION_CONFIG_PATH = str(
    Path(
        r"C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties"
    ).resolve()
)
DEFAULT_CHECKPOINT_ROOT = str(
    Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints").resolve()
)
CHECKPOINT_PATTERNS = ("rl_combat_model_*.pth", "rl_model_*.pth")
RUN_LOCK_IMPLEMENTATION_PATHS = (
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


class OutcomeEvidenceRegistrationError(ValueError):
    """Raised when a study registration is malformed or has been changed."""


class OutcomeEvidenceRunLockError(RuntimeError):
    """Raised when the immutable study run lock cannot be proven valid."""


@dataclass(frozen=True)
class GitSourceSnapshot:
    commit: str
    tracked_clean: bool
    tracked_status: str


@dataclass(frozen=True)
class RegisteredSlot:
    slot_number: int
    session_id: str
    seed: int
    config_path: str
    manifest_path: str
    trace_path: str

    def to_record(self) -> dict[str, Any]:
        return {
            "config_path": self.config_path,
            "manifest_path": self.manifest_path,
            "seed": self.seed,
            "session_id": self.session_id,
            "slot_number": self.slot_number,
            "trace_path": self.trace_path,
        }


@dataclass(frozen=True)
class OutcomeEvidenceRegistration:
    study_id: str
    artifact_root: str
    repo_root: str
    seed_base: int
    python_executable: str
    communication_config_path: str
    checkpoint_root: str
    slots: tuple[RegisteredSlot, ...]
    registration_hash: str

    def to_record(self) -> dict[str, Any]:
        record = _registration_body(self)
        record["registration_hash"] = self.registration_hash
        return record


def build_registration(
    *,
    study_id: str,
    artifact_root: Path | str,
    repo_root: Path | str,
    seed_base: int,
    python_executable: Path | str,
    communication_config_path: Path | str = DEFAULT_COMMUNICATION_CONFIG_PATH,
    checkpoint_root: Path | str = DEFAULT_CHECKPOINT_ROOT,
) -> OutcomeEvidenceRegistration:
    """Build the one fixed 24-by-25 registration used by this study."""

    if not isinstance(study_id, str) or not _STUDY_ID_PATTERN.fullmatch(study_id):
        raise OutcomeEvidenceRegistrationError(
            "study_id must contain only lowercase letters, digits, and hyphens"
        )
    _require_exact_int(seed_base, "seed_base")

    normalized_artifact_root = str(Path(artifact_root).resolve())
    normalized_repo_root = str(Path(repo_root).resolve())
    normalized_python = str(Path(python_executable).resolve())
    normalized_communication_config = str(Path(communication_config_path).resolve())
    normalized_checkpoint_root = str(Path(checkpoint_root).resolve())

    slots = tuple(
        _build_slot(
            study_id=study_id,
            artifact_root=Path(normalized_artifact_root),
            seed_base=seed_base,
            slot_number=slot_number,
        )
        for slot_number in range(1, SLOT_COUNT + 1)
    )
    registration = OutcomeEvidenceRegistration(
        study_id=study_id,
        artifact_root=normalized_artifact_root,
        repo_root=normalized_repo_root,
        seed_base=seed_base,
        python_executable=normalized_python,
        communication_config_path=normalized_communication_config,
        checkpoint_root=normalized_checkpoint_root,
        slots=slots,
        registration_hash="",
    )
    digest = _hash_registration_record(_record_with_null_hash(registration))
    return replace(registration, registration_hash=digest)


def canonical_registration_hash(record: Mapping[str, Any]) -> str:
    """Return the canonical hash after replacing the self-hash with null."""

    if not isinstance(record, Mapping):
        raise OutcomeEvidenceRegistrationError("registration must be a JSON object")
    hash_input = dict(record)
    hash_input["registration_hash"] = None
    return _hash_registration_record(hash_input)


def validate_registration(
    payload: Mapping[str, Any],
) -> OutcomeEvidenceRegistration:
    """Validate all registered values before checking the canonical hash."""

    record = _require_mapping(payload, "registration")
    expected_top_level = {
        "artifact_root",
        "behavior",
        "blinding_rules",
        "command",
        "games_per_slot",
        "integrity_rules",
        "output_rules",
        "registration_hash",
        "repo_root",
        "scheduled_attempts",
        "schema_version",
        "seed_base",
        "slot_count",
        "slots",
        "study_id",
        "thresholds",
    }
    _require_exact_fields(record, expected_top_level, "registration")

    study_id = _require_string(record["study_id"], "study_id")
    artifact_root = _require_string(record["artifact_root"], "artifact_root")
    repo_root = _require_string(record["repo_root"], "repo_root")
    seed_base = _require_exact_int(record["seed_base"], "seed_base")
    command = _require_mapping(record["command"], "command")
    _require_exact_fields(
        command, {"arguments", "main_path", "python_executable"}, "command"
    )
    python_executable = _require_string(
        command["python_executable"], "command.python_executable"
    )
    integrity_rules = _require_mapping(record["integrity_rules"], "integrity_rules")
    communication_config_path = _require_string(
        integrity_rules.get("communication_config_path"),
        "integrity_rules.communication_config_path",
    )
    checkpoint_inventory = _require_mapping(
        integrity_rules.get("checkpoint_inventory"),
        "integrity_rules.checkpoint_inventory",
    )
    checkpoint_root = _require_string(
        checkpoint_inventory.get("root"),
        "integrity_rules.checkpoint_inventory.root",
    )

    expected = build_registration(
        study_id=study_id,
        artifact_root=artifact_root,
        repo_root=repo_root,
        seed_base=seed_base,
        python_executable=python_executable,
        communication_config_path=communication_config_path,
        checkpoint_root=checkpoint_root,
    )
    expected_record = expected.to_record()

    for key in sorted(expected_top_level - {"registration_hash"}):
        _assert_exact_value(record[key], expected_record[key], key)

    supplied_hash = _require_string(record["registration_hash"], "registration_hash")
    if not _SHA256_PATTERN.fullmatch(supplied_hash):
        raise OutcomeEvidenceRegistrationError(
            "registration_hash must be a lowercase SHA-256 hash"
        )
    canonical_hash = canonical_registration_hash(record)
    if supplied_hash != canonical_hash:
        raise OutcomeEvidenceRegistrationError("registration hash mismatch")
    return expected


def render_registration_json(
    registration: OutcomeEvidenceRegistration | Mapping[str, Any],
) -> str:
    """Render canonical UTF-8 JSON with a single LF terminator."""

    if isinstance(registration, OutcomeEvidenceRegistration):
        validated = validate_registration(registration.to_record())
    else:
        validated = validate_registration(registration)
    return _canonical_json(validated.to_record()) + "\n"


def load_registration(path: Path | str) -> OutcomeEvidenceRegistration:
    """Load strict JSON, rejecting duplicate keys and non-standard constants."""

    registration_path = Path(path)
    try:
        text = registration_path.read_text(encoding="utf-8")
        payload = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except OutcomeEvidenceRegistrationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OutcomeEvidenceRegistrationError(
            f"cannot load registration {registration_path}: {exc}"
        ) from exc
    return validate_registration(payload)


def create_run_lock(
    *,
    registration_path: Path | str,
    lock_path: Path | str,
    repo_root: Path | str,
    child_command: Sequence[str],
    created_unix_ns: int | None = None,
) -> dict[str, Any]:
    """Atomically bind a committed registration to one clean source snapshot."""

    resolved_lock_path = Path(lock_path).resolve()
    if resolved_lock_path.exists():
        raise OutcomeEvidenceRunLockError(
            f"run lock already exists for this study: {resolved_lock_path}"
        )
    registration, registration_file_sha256, source = _validate_run_lock_inputs(
        registration_path=registration_path,
        repo_root=repo_root,
        child_command=child_command,
    )
    expected_lock_path = Path(registration.artifact_root) / "run-lock.json"
    if resolved_lock_path != expected_lock_path.resolve():
        raise OutcomeEvidenceRunLockError(
            f"lock path differs from registered output: {resolved_lock_path}"
        )
    if created_unix_ns is None:
        created_unix_ns = time.time_ns()
    if type(created_unix_ns) is not int or created_unix_ns <= 0:
        raise OutcomeEvidenceRunLockError("created_unix_ns must be a positive integer")

    command = _normalize_child_command(child_command)
    record = {
        "checkpoints": _checkpoint_inventory_snapshot(
            Path(registration.checkpoint_root)
        ),
        "command": command,
        "communication_mod": _communication_mod_snapshot(
            Path(registration.communication_config_path)
        ),
        "created_unix_ns": created_unix_ns,
        "implementation_files": _implementation_snapshot(Path(repo_root)),
        "python_executable": registration.python_executable,
        "registration": {
            "canonical_hash": registration.registration_hash,
            "file_sha256": registration_file_sha256,
            "path": str(Path(registration_path).resolve()),
        },
        "repo_root": registration.repo_root,
        "run_lock_hash": None,
        "schema_version": RUN_LOCK_SCHEMA_VERSION,
        "source": {
            "commit": source.commit,
            "tracked_clean": True,
            "tracked_status": "",
        },
        "study_id": registration.study_id,
    }
    record["run_lock_hash"] = _hash_run_lock_record(record)
    _publish_json_once(resolved_lock_path, _canonical_json(record) + "\n")
    return json.loads(_canonical_json(record))


def validate_run_lock(
    *,
    lock_path: Path | str,
    registration_path: Path | str,
    repo_root: Path | str,
    child_command: Sequence[str],
) -> dict[str, Any]:
    """Recompute every source and live-isolation binding in a run lock."""

    record = _load_run_lock(Path(lock_path))
    expected_fields = {
        "checkpoints",
        "command",
        "communication_mod",
        "created_unix_ns",
        "implementation_files",
        "python_executable",
        "registration",
        "repo_root",
        "run_lock_hash",
        "schema_version",
        "source",
        "study_id",
    }
    _require_run_lock_fields(record, expected_fields, "run lock")
    if record["schema_version"] != RUN_LOCK_SCHEMA_VERSION:
        raise OutcomeEvidenceRunLockError("run lock schema_version mismatch")
    supplied_hash = record["run_lock_hash"]
    if not isinstance(supplied_hash, str) or not _SHA256_PATTERN.fullmatch(
        supplied_hash
    ):
        raise OutcomeEvidenceRunLockError("run_lock_hash is not a SHA-256 hash")
    if supplied_hash != canonical_run_lock_hash(record):
        raise OutcomeEvidenceRunLockError("run lock hash mismatch")

    registration, registration_file_sha256, source = _validate_run_lock_inputs(
        registration_path=registration_path,
        repo_root=repo_root,
        child_command=child_command,
    )
    expected_registration = {
        "canonical_hash": registration.registration_hash,
        "file_sha256": registration_file_sha256,
        "path": str(Path(registration_path).resolve()),
    }
    actual_registration = record["registration"]
    if not isinstance(actual_registration, Mapping):
        raise OutcomeEvidenceRunLockError("run lock registration must be an object")
    if actual_registration.get("file_sha256") != registration_file_sha256:
        raise OutcomeEvidenceRunLockError("registration bytes changed after run lock")
    _assert_run_lock_value(
        actual_registration, expected_registration, "registration"
    )
    _assert_run_lock_value(record["study_id"], registration.study_id, "study_id")
    _assert_run_lock_value(record["repo_root"], registration.repo_root, "repo_root")
    _assert_run_lock_value(
        record["python_executable"],
        registration.python_executable,
        "python_executable",
    )
    _assert_run_lock_value(
        record["command"], _normalize_child_command(child_command), "command"
    )
    _assert_run_lock_value(
        record["source"],
        {
            "commit": source.commit,
            "tracked_clean": True,
            "tracked_status": "",
        },
        "source",
    )

    expected_implementation = _implementation_snapshot(Path(repo_root))
    if record["implementation_files"] != expected_implementation:
        raise OutcomeEvidenceRunLockError("source file hash drift detected")
    expected_communication = _communication_mod_snapshot(
        Path(registration.communication_config_path)
    )
    if record["communication_mod"] != expected_communication:
        raise OutcomeEvidenceRunLockError(
            "CommunicationMod semantic configuration drift detected"
        )
    expected_checkpoints = _checkpoint_inventory_snapshot(
        Path(registration.checkpoint_root)
    )
    if record["checkpoints"] != expected_checkpoints:
        raise OutcomeEvidenceRunLockError("checkpoint drift detected")
    if type(record["created_unix_ns"]) is not int or record["created_unix_ns"] <= 0:
        raise OutcomeEvidenceRunLockError(
            "created_unix_ns must be a positive integer"
        )
    return json.loads(_canonical_json(record))


def canonical_run_lock_hash(record: Mapping[str, Any]) -> str:
    if not isinstance(record, Mapping):
        raise OutcomeEvidenceRunLockError("run lock must be a JSON object")
    hash_input = dict(record)
    hash_input["run_lock_hash"] = None
    return _hash_run_lock_record(hash_input)


def _validate_run_lock_inputs(
    *,
    registration_path: Path | str,
    repo_root: Path | str,
    child_command: Sequence[str],
) -> tuple[OutcomeEvidenceRegistration, str, GitSourceSnapshot]:
    resolved_registration_path = Path(registration_path).resolve()
    resolved_repo_root = Path(repo_root).resolve()
    if _git_repository_root(resolved_repo_root) != resolved_repo_root:
        raise OutcomeEvidenceRunLockError(
            "repo_root must be the Git repository top level"
        )
    try:
        registration_bytes = resolved_registration_path.read_bytes()
        registration = load_registration(resolved_registration_path)
    except (OSError, OutcomeEvidenceRegistrationError) as exc:
        raise OutcomeEvidenceRunLockError(f"invalid registration: {exc}") from exc
    if registration.repo_root != str(resolved_repo_root):
        raise OutcomeEvidenceRunLockError("registration repo_root mismatch")
    try:
        registration_relative_path = resolved_registration_path.relative_to(
            resolved_repo_root
        )
    except ValueError as exc:
        raise OutcomeEvidenceRunLockError(
            "registration must be inside the registered repository"
        ) from exc
    if registration.python_executable.casefold() != SUPPORTED_WINDOWS_PYTHON.casefold():
        raise OutcomeEvidenceRunLockError(
            "study requires the supported Windows Python executable: "
            + SUPPORTED_WINDOWS_PYTHON
        )

    command = _normalize_child_command(child_command)
    command_record = registration.to_record()["command"]
    expected_command = [
        command_record["python_executable"],
        command_record["main_path"],
        *command_record["arguments"],
    ]
    if command != expected_command:
        raise OutcomeEvidenceRunLockError("child command differs from registration")
    if "--train" in command or "--eval" not in command:
        raise OutcomeEvidenceRunLockError(
            "child command must be eval-only and must not train"
        )

    source = _inspect_git_source(resolved_repo_root)
    if not source.tracked_clean:
        raise OutcomeEvidenceRunLockError(
            "tracked source is dirty; refusing run lock: " + source.tracked_status
        )
    if not re.fullmatch(r"[0-9a-f]{40}", source.commit):
        raise OutcomeEvidenceRunLockError("source commit is not a Git SHA-1")
    _verify_head_file(
        repo_root=resolved_repo_root,
        relative_path=registration_relative_path,
        working_bytes=registration_bytes,
        label="registration file",
    )
    for relative_path in RUN_LOCK_IMPLEMENTATION_PATHS:
        resolved_path = (resolved_repo_root / relative_path).resolve()
        try:
            working_bytes = resolved_path.read_bytes()
        except OSError as exc:
            raise OutcomeEvidenceRunLockError(
                f"cannot read implementation file {relative_path}: {exc}"
            ) from exc
        _verify_head_file(
            repo_root=resolved_repo_root,
            relative_path=Path(relative_path),
            working_bytes=working_bytes,
            label=f"implementation file {relative_path}",
        )
    return (
        registration,
        hashlib.sha256(registration_bytes).hexdigest(),
        source,
    )


def _normalize_child_command(child_command: Sequence[str]) -> list[str]:
    if isinstance(child_command, (str, bytes)) or not isinstance(
        child_command, Sequence
    ):
        raise OutcomeEvidenceRunLockError("child command must be a sequence")
    command = list(child_command)
    if not command or any(not isinstance(value, str) for value in command):
        raise OutcomeEvidenceRunLockError(
            "child command must contain only nonempty string arguments"
        )
    if any(not value for value in command):
        raise OutcomeEvidenceRunLockError(
            "child command must contain only nonempty string arguments"
        )
    return command


def _inspect_git_source(repo_root: Path) -> GitSourceSnapshot:
    commit = _run_git(repo_root, "rev-parse", "HEAD").strip().lower()
    tracked_status = _run_git(
        repo_root, "status", "--porcelain", "--untracked-files=no"
    ).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise OutcomeEvidenceRunLockError(
            f"git returned an invalid source commit: {commit!r}"
        )
    return GitSourceSnapshot(
        commit=commit,
        tracked_clean=not tracked_status,
        tracked_status=tracked_status,
    )


def _run_git(repo_root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(f"unable to run git: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise OutcomeEvidenceRunLockError(
            f"git {' '.join(arguments)} failed: {detail}"
        )
    return result.stdout


def _git_repository_root(repo_root: Path) -> Path:
    return Path(_run_git(repo_root, "rev-parse", "--show-toplevel").strip()).resolve()


def _head_blob_bytes(repo_root: Path, relative_path: Path) -> bytes | None:
    git_path = relative_path.as_posix()
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{git_path}"],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
        )
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(f"unable to run git: {exc}") from exc
    if result.returncode != 0:
        return None
    return result.stdout


def _verify_head_file(
    *,
    repo_root: Path,
    relative_path: Path,
    working_bytes: bytes,
    label: str,
) -> None:
    head_bytes = _head_blob_bytes(repo_root, relative_path)
    if head_bytes is None:
        raise OutcomeEvidenceRunLockError(f"{label} must be committed at HEAD")
    if working_bytes != head_bytes and _filtered_working_blob_oid(
        repo_root, relative_path, working_bytes
    ) != _git_blob_oid(head_bytes):
        raise OutcomeEvidenceRunLockError(f"{label} bytes differ from HEAD")


def _filtered_working_blob_oid(
    repo_root: Path, relative_path: Path, working_bytes: bytes
) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "hash-object",
                f"--path={relative_path.as_posix()}",
                "--stdin",
            ],
            cwd=str(repo_root),
            check=False,
            capture_output=True,
            input=working_bytes,
        )
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(f"unable to run git: {exc}") from exc
    oid = result.stdout.decode("ascii", errors="strict").strip().lower()
    if result.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", oid):
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise OutcomeEvidenceRunLockError(
            f"git hash-object failed for {relative_path}: {detail}"
        )
    return oid


def _git_blob_oid(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("ascii")
    return hashlib.sha1(header + content).hexdigest()


def _implementation_snapshot(repo_root: Path) -> list[dict[str, Any]]:
    snapshot = []
    for relative_path in RUN_LOCK_IMPLEMENTATION_PATHS:
        path = (repo_root / relative_path).resolve()
        try:
            path.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise OutcomeEvidenceRunLockError(
                f"source file escapes repository: {relative_path}"
            ) from exc
        fingerprint = _required_file_snapshot(path, "source file")
        snapshot.append(
            {
                "path": str(path),
                "relative_path": relative_path,
                **fingerprint,
            }
        )
    return snapshot


def _communication_mod_snapshot(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise OutcomeEvidenceRunLockError(
            f"CommunicationMod config is not a file: {resolved}"
        )
    try:
        semantic_sha256 = _properties_semantic_sha256(resolved)
    except (OSError, UnicodeError, OutcomeEvidenceRunLockError):
        raise
    return {"path": str(resolved), "semantic_sha256": semantic_sha256}


def _checkpoint_inventory_snapshot(checkpoint_root: Path) -> dict[str, Any]:
    resolved_root = checkpoint_root.resolve()
    if not resolved_root.is_dir():
        raise OutcomeEvidenceRunLockError(
            f"registered checkpoint root is not a directory: {resolved_root}"
        )
    checkpoint_paths = {
        path.resolve()
        for pattern in CHECKPOINT_PATTERNS
        for path in resolved_root.glob(pattern)
        if path.is_file()
    }
    ordered_paths = sorted(checkpoint_paths, key=lambda path: str(path).casefold())
    if not ordered_paths:
        raise OutcomeEvidenceRunLockError(
            "registered checkpoint inventory contains no matching checkpoints"
        )
    return {
        "files": [
            {"path": str(path), **_required_file_snapshot(path, "checkpoint")}
            for path in ordered_paths
        ],
        "patterns": list(CHECKPOINT_PATTERNS),
        "root": str(resolved_root),
    }


def _required_file_snapshot(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise OutcomeEvidenceRunLockError(f"required {label} is missing: {path}")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(
            f"cannot read {label} {path}: {exc}"
        ) from exc
    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _properties_semantic_sha256(path: Path) -> str:
    try:
        content = path.read_text(encoding="iso-8859-1")
        natural_lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        properties: dict[str, str] = {}
        for logical_line in _java_properties_logical_lines(natural_lines):
            parsed = _parse_java_property(logical_line)
            if parsed is not None:
                key, value = parsed
                properties[key] = value
    except (OSError, UnicodeError) as exc:
        raise OutcomeEvidenceRunLockError(
            f"cannot read CommunicationMod config {path}: {exc}"
        ) from exc
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
    decoded: list[str] = []
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
            raise OutcomeEvidenceRunLockError(
                "invalid trailing escape in CommunicationMod config"
            )
        escaped = value[index]
        if escaped == "u":
            digits = value[index + 1 : index + 5]
            if len(digits) != 4 or any(
                digit not in "0123456789abcdefABCDEF" for digit in digits
            ):
                raise OutcomeEvidenceRunLockError(
                    "invalid Unicode escape in CommunicationMod config"
                )
            decoded.append(chr(int(digits, 16)))
            index += 5
            continue
        decoded.append(escapes.get(escaped, escaped))
        index += 1
    return "".join(decoded)


def _load_run_lock(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except OutcomeEvidenceRegistrationError as exc:
        raise OutcomeEvidenceRunLockError(str(exc)) from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OutcomeEvidenceRunLockError(f"cannot load run lock {path}: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise OutcomeEvidenceRunLockError("run lock must be a JSON object")
    return payload


def _publish_json_once(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
        temporary_path = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary_path, path)
    except FileExistsError as exc:
        raise OutcomeEvidenceRunLockError(
            f"run lock already exists for this study: {path}"
        ) from exc
    except OSError as exc:
        raise OutcomeEvidenceRunLockError(f"cannot publish run lock {path}: {exc}") from exc
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def _require_run_lock_fields(
    value: Mapping[str, Any], expected: set[str], field: str
) -> None:
    actual = set(value)
    if actual != expected:
        raise OutcomeEvidenceRunLockError(
            f"{field} fields mismatch: missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def _assert_run_lock_value(actual: Any, expected: Any, path: str) -> None:
    try:
        _assert_exact_value(actual, expected, path)
    except OutcomeEvidenceRegistrationError as exc:
        raise OutcomeEvidenceRunLockError(str(exc)) from exc


def _hash_run_lock_record(record: Mapping[str, Any]) -> str:
    try:
        payload = _canonical_json(record).encode("utf-8")
    except OutcomeEvidenceRegistrationError as exc:
        raise OutcomeEvidenceRunLockError(str(exc)) from exc
    return hashlib.sha256(payload).hexdigest()


def _build_slot(
    *, study_id: str, artifact_root: Path, seed_base: int, slot_number: int
) -> RegisteredSlot:
    suffix = f"s{slot_number:02d}"
    session_id = f"{study_id}-{suffix}"
    return RegisteredSlot(
        slot_number=slot_number,
        session_id=session_id,
        seed=seed_base + slot_number,
        config_path=str((artifact_root / f"{session_id}-config.json").resolve()),
        manifest_path=str((artifact_root / f"{session_id}-manifest.json").resolve()),
        trace_path=str((artifact_root / f"{session_id}-trace.jsonl").resolve()),
    )


def _registration_body(registration: OutcomeEvidenceRegistration) -> dict[str, Any]:
    return {
        "artifact_root": registration.artifact_root,
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
            "outcome_fields_forbidden_during_collection": True,
            "outcome_adaptive_decisions_forbidden": True,
        },
        "command": {
            "arguments": list(COMMAND_ARGUMENTS),
            "main_path": str((Path(registration.repo_root) / "main.py").resolve()),
            "python_executable": registration.python_executable,
        },
        "games_per_slot": GAMES_PER_SLOT,
        "integrity_rules": {
            "checkpoint_inventory": {
                "patterns": list(CHECKPOINT_PATTERNS),
                "root": registration.checkpoint_root,
            },
            "communication_config_path": registration.communication_config_path,
            "implementation_paths": list(RUN_LOCK_IMPLEMENTATION_PATHS),
            "launches_per_slot": 1,
            "replacement_slots_forbidden": True,
            "tracked_source_frozen_during_run_lock": True,
        },
        "output_rules": {
            "canonical_json_line_ending": "LF",
            "config_suffix": "-config.json",
            "manifest_suffix": "-manifest.json",
            "monitor_json_filename": "blinded-monitor.json",
            "monitor_markdown_filename": "blinded-monitor.md",
            "run_lock_filename": "run-lock.json",
            "study_ledger_filename": "study-ledger.jsonl",
            "trace_suffix": "-trace.jsonl",
        },
        "repo_root": registration.repo_root,
        "scheduled_attempts": SCHEDULED_ATTEMPTS,
        "schema_version": REGISTRATION_SCHEMA_VERSION,
        "seed_base": registration.seed_base,
        "slot_count": SLOT_COUNT,
        "slots": [slot.to_record() for slot in registration.slots],
        "study_id": registration.study_id,
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


def _record_with_null_hash(
    registration: OutcomeEvidenceRegistration,
) -> dict[str, Any]:
    record = _registration_body(registration)
    record["registration_hash"] = None
    return record


def _hash_registration_record(record: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(record).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise OutcomeEvidenceRegistrationError(
            f"registration is not canonical JSON: {exc}"
        ) from exc


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OutcomeEvidenceRegistrationError(f"{field} must be an object")
    return value


def _require_exact_fields(
    value: Mapping[str, Any], expected: set[str], field: str
) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise OutcomeEvidenceRegistrationError(
            f"{field} fields mismatch: missing={missing}, unknown={unknown}"
        )


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise OutcomeEvidenceRegistrationError(f"{field} must be a string")
    return value


def _require_exact_int(value: Any, field: str) -> int:
    if type(value) is not int:
        raise OutcomeEvidenceRegistrationError(f"{field} must be an exact integer")
    return value


def _assert_exact_value(actual: Any, expected: Any, path: str) -> None:
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            raise OutcomeEvidenceRegistrationError(f"{_field_label(path)} must be an object")
        _require_exact_fields(actual, set(expected), path)
        for key in sorted(expected):
            _assert_exact_value(actual[key], expected[key], f"{path}.{key}")
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            raise OutcomeEvidenceRegistrationError(f"{_field_label(path)} must be a list")
        if len(actual) != len(expected):
            raise OutcomeEvidenceRegistrationError(
                f"{_field_label(path)} must contain exactly {len(expected)} entries"
            )
        for index, expected_item in enumerate(expected):
            _assert_exact_value(actual[index], expected_item, f"{path}[{index}]")
        return

    if type(actual) is not type(expected) or actual != expected:
        raise OutcomeEvidenceRegistrationError(
            f"{_field_label(path)} differs from the registered value"
        )


def _field_label(path: str) -> str:
    leaf = path.rsplit(".", 1)[-1]
    if leaf == "per_run_alternative_budget":
        return "alternative budget"
    return leaf


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OutcomeEvidenceRegistrationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise OutcomeEvidenceRegistrationError(f"invalid JSON constant: {value}")
