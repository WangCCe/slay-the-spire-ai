"""Fixed-tree seed inventory for the cross-fitted learning successor.

This module is source-only. It intentionally has no project, Torch, or native
simulator imports so registration can build and verify cohorts before runtime
dependencies are eligible to load.
"""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
import math
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any


SEED_INVENTORY_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-seed-inventory-v1"
)
FRESH_SCHEDULE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1"
)
READINESS_CANDIDATE_SCHEMA_VERSION = (
    "noncombat-cross-fitted-empirical-successor-readiness-candidate-v1"
)
READINESS_CANDIDATE_ENCODING = "gzip-mtime-zero-v1"
MAX_READINESS_CANDIDATE_STORED_BYTES = 64 * 1024 * 1024
MAX_READINESS_CANDIDATE_CANONICAL_BYTES = 512 * 1024 * 1024
CANONICAL_SEARCH_START = 0
TRAINING_SEED_COUNT = 512
PREVIOUS_UNTOUCHED_HOLDOUT_START = 71152
PREVIOUS_UNTOUCHED_HOLDOUT_END = 71663

_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
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
        "end_inclusive": PREVIOUS_UNTOUCHED_HOLDOUT_END,
        "name": "previous_untouched_holdout",
        "start_inclusive": PREVIOUS_UNTOUCHED_HOLDOUT_START,
    }
]
_INVENTORY_FIELDS = {
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
_ROW_FIELDS = {"document_index", "json_path", "role", "seed", "source_path"}
_BINDING_FIELDS = {
    "document_count",
    "format",
    "path",
    "row_count",
    "sha256",
    "size_bytes",
}
_SCHEDULE_FIELDS = {
    "canonical_search_start",
    "inventory_sha256",
    "schema_version",
    "seed_count",
    "seeds",
}
_READINESS_AUTHORITY_NAMES = (
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


class SeedInventoryBlocked(RuntimeError):
    """Raised when fixed-tree seed evidence cannot be proven exactly."""


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


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise SeedInventoryBlocked(f"{label} fields mismatch")


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SeedInventoryBlocked(f"{label} must be a mapping")
    return copy.deepcopy(dict(value))


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SeedInventoryBlocked(f"{label} must be a nonnegative integer")
    return value


def _positive_integer(value: object, label: str) -> int:
    result = _nonnegative_integer(value, label)
    if result == 0:
        raise SeedInventoryBlocked(f"{label} must be positive")
    return result


def _repository_commit(value: object) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise SeedInventoryBlocked("repository commit must be 40 lowercase hex characters")
    return value


def _canonical_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise SeedInventoryBlocked(f"{label} must be a canonical repository path")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or str(pure) != value
        or len(pure.parts) < 2
        or pure.parts[0] != "reports"
        or "\n" in value
        or "\r" in value
    ):
        raise SeedInventoryBlocked(f"{label} must be a canonical reports path")
    return value


def _artifact_format(path: str) -> str | None:
    if path.endswith(".jsonl.gz"):
        return "jsonl.gz"
    if path.endswith(".json.gz"):
        return "json.gz"
    if path.endswith(".jsonl"):
        return "jsonl"
    if path.endswith(".json"):
        return "json"
    return None


def _unsupported_seed_candidate(path: str) -> bool:
    folded = path.casefold()
    filename = PurePosixPath(folded).name
    near_structured = filename.endswith(
        (".json.zip", ".json.zst", ".json.bz2", ".json.xz")
    )
    named_seed_evidence = "seed" in folded or "cohort" in folded
    return near_structured or named_seed_evidence


def _git_command(repo_root: Path, args: list[str], *, input_bytes: bytes | None = None) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        input=input_bytes,
        check=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SeedInventoryBlocked(f"git {' '.join(args)} failed: {stderr}")
    return completed.stdout


def _list_report_paths(repo_root: Path, repository_commit: str) -> list[str]:
    raw = _git_command(
        repo_root,
        [
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            repository_commit,
            "--",
            "reports",
        ],
    )
    if raw and not raw.endswith(b"\0"):
        raise SeedInventoryBlocked("git ls-tree response is truncated")
    paths: list[str] = []
    for encoded in raw.split(b"\0"):
        if not encoded:
            continue
        try:
            path = encoded.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise SeedInventoryBlocked("report path is not strict UTF-8") from exc
        paths.append(_canonical_path(path, "tracked report path"))
    if len(paths) != len(set(paths)):
        raise SeedInventoryBlocked("git tree contains duplicate report paths")
    return sorted(paths)


def _git_blob_batch(
    repo_root: Path, *, repository_commit: str, paths: list[str]
) -> dict[str, bytes]:
    ordered = [_canonical_path(path, "seed source path") for path in paths]
    if ordered != sorted(set(ordered)):
        raise SeedInventoryBlocked("seed source paths must be sorted and unique")
    if not ordered:
        return {}
    request = "".join(f"{repository_commit}:{path}\n" for path in ordered).encode(
        "utf-8"
    )
    output = _git_command(repo_root, ["cat-file", "--batch"], input_bytes=request)
    offset = 0
    result: dict[str, bytes] = {}
    for path in ordered:
        line_end = output.find(b"\n", offset)
        if line_end < 0:
            raise SeedInventoryBlocked(f"git cat-file response is truncated for {path}")
        try:
            header = output[offset:line_end].decode("ascii", errors="strict").split()
        except UnicodeDecodeError as exc:
            raise SeedInventoryBlocked(f"git cat-file header is invalid for {path}") from exc
        offset = line_end + 1
        if len(header) != 3 or header[1] != "blob" or not header[2].isdigit():
            raise SeedInventoryBlocked(f"git cat-file did not return a blob for {path}")
        size = int(header[2])
        payload = output[offset : offset + size]
        offset += size
        if len(payload) != size or output[offset : offset + 1] != b"\n":
            raise SeedInventoryBlocked(f"git cat-file blob is truncated for {path}")
        offset += 1
        result[path] = payload
    if offset != len(output):
        raise SeedInventoryBlocked("git cat-file response has trailing bytes")
    return result


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SeedInventoryBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise SeedInventoryBlocked(f"non-finite JSON constant: {value}")


def _parse_json_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SeedInventoryBlocked(f"non-finite JSON number: {value}")
    return result


def _strict_json(payload: bytes, label: str) -> object:
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SeedInventoryBlocked(f"{label} is not strict UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_json_constant,
            parse_float=_parse_json_float,
        )
    except SeedInventoryBlocked:
        raise
    except json.JSONDecodeError as exc:
        raise SeedInventoryBlocked(f"{label} is invalid strict JSON: {exc}") from exc


def _parse_documents(path: str, payload: bytes, format_name: str) -> list[object]:
    if not payload:
        raise SeedInventoryBlocked(f"seed source is empty: {path}")
    if format_name in {"json.gz", "jsonl.gz"}:
        try:
            payload = gzip.decompress(payload)
        except (gzip.BadGzipFile, EOFError, OSError) as exc:
            raise SeedInventoryBlocked(
                f"seed source gzip is invalid: {path}: {exc}"
            ) from exc
        if not payload:
            raise SeedInventoryBlocked(f"seed source gzip is empty: {path}")
        format_name = format_name.removesuffix(".gz")
    if format_name == "json":
        return [_strict_json(payload, path)]
    if format_name != "jsonl":
        raise SeedInventoryBlocked(f"unsupported seed source format: {path}")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SeedInventoryBlocked(f"seed source JSONL is not strict UTF-8: {path}") from exc
    lines = text.splitlines()
    if not lines:
        raise SeedInventoryBlocked(f"seed source JSONL is empty: {path}")
    documents: list[object] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise SeedInventoryBlocked(
                f"seed source JSONL contains a blank line: {path}:{line_number}"
            )
        try:
            value = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_json_constant,
                parse_float=_parse_json_float,
            )
        except SeedInventoryBlocked:
            raise
        except json.JSONDecodeError as exc:
            raise SeedInventoryBlocked(
                f"seed source JSONL is invalid: {path}:{line_number}: {exc}"
            ) from exc
        if not isinstance(value, Mapping):
            raise SeedInventoryBlocked(
                f"seed source JSONL row must be an object: {path}:{line_number}"
            )
        documents.append(value)
    return documents


def _json_pointer(parent: str, token: object) -> str:
    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}"


def _role_for_key(key: str, fallback: str) -> str:
    folded = key.casefold()
    ordered = (
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
    )
    for needle, role in ordered:
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
                    raise SeedInventoryBlocked("JSON object key must be a string")
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

    visit(
        value,
        "",
        seed_context=False,
        role="seed",
        cohorts_mapping=False,
    )
    return rows


def _row_sort_key(row: Mapping[str, Any]) -> tuple[object, ...]:
    return (
        row["seed"],
        row["source_path"],
        row["document_index"],
        row["json_path"],
        row["role"],
    )


def build_seed_inventory(
    repo_root: Path | str, *, repository_commit: str
) -> dict[str, Any]:
    """Build an inventory using blobs from exactly one caller-bound Git tree."""
    commit = _repository_commit(repository_commit)
    root = Path(repo_root).resolve()
    paths = _list_report_paths(root, commit)
    candidates: list[str] = []
    formats: dict[str, str] = {}
    for path in paths:
        format_name = _artifact_format(path)
        if format_name is None:
            if _unsupported_seed_candidate(path):
                raise SeedInventoryBlocked(f"unsupported candidate seed artifact: {path}")
            continue
        candidates.append(path)
        formats[path] = format_name
    blobs = _git_blob_batch(
        root,
        repository_commit=commit,
        paths=sorted(candidates),
    )

    rows: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for path in sorted(candidates):
        payload = blobs[path]
        documents = _parse_documents(path, payload, formats[path])
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
    reserved = set(
        range(
            PREVIOUS_UNTOUCHED_HOLDOUT_START,
            PREVIOUS_UNTOUCHED_HOLDOUT_END + 1,
        )
    )
    excluded = sorted(extracted | reserved)
    inventory = {
        "canonical_search_start": CANONICAL_SEARCH_START,
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
    return validate_seed_inventory(inventory)


def rebuild_seed_inventory(
    repo_root: Path | str, *, repository_commit: str
) -> dict[str, Any]:
    """Independently reconstruct an inventory from its immutable Git tree."""
    return build_seed_inventory(repo_root, repository_commit=repository_commit)


def validate_seed_inventory(value: object) -> dict[str, Any]:
    inventory = _mapping(value, "seed inventory")
    _require_exact_keys(inventory, _INVENTORY_FIELDS, "seed inventory")
    if inventory["schema_version"] != SEED_INVENTORY_SCHEMA_VERSION:
        raise SeedInventoryBlocked("seed inventory schema mismatch")
    commit = _repository_commit(inventory["repository_commit"])
    if (
        isinstance(inventory["canonical_search_start"], bool)
        or inventory["canonical_search_start"] != CANONICAL_SEARCH_START
    ):
        raise SeedInventoryBlocked("seed inventory canonical search start mismatch")
    if inventory["reserved_seed_ranges"] != _RESERVED_SEED_RANGES:
        raise SeedInventoryBlocked("seed inventory reserved ranges mismatch")

    raw_rows = inventory["rows"]
    if not isinstance(raw_rows, list):
        raise SeedInventoryBlocked("seed inventory rows must be a list")
    rows: list[dict[str, Any]] = []
    for index, raw_row in enumerate(raw_rows):
        row = _mapping(raw_row, f"seed row[{index}]")
        _require_exact_keys(row, _ROW_FIELDS, f"seed row[{index}]")
        row["document_index"] = _nonnegative_integer(
            row["document_index"], f"seed row[{index}].document_index"
        )
        if (
            not isinstance(row["json_path"], str)
            or not row["json_path"].startswith("/")
        ):
            raise SeedInventoryBlocked(f"seed row[{index}] JSON path is invalid")
        if row["role"] not in _ROW_ROLES:
            raise SeedInventoryBlocked(f"seed row[{index}] role is invalid")
        row["seed"] = _nonnegative_integer(row["seed"], f"seed row[{index}].seed")
        row["source_path"] = _canonical_path(
            row["source_path"], f"seed row[{index}].source_path"
        )
        if _artifact_format(row["source_path"]) is None:
            raise SeedInventoryBlocked(f"seed row[{index}] source format is invalid")
        rows.append(row)
    if rows != sorted(rows, key=_row_sort_key):
        raise SeedInventoryBlocked("seed inventory rows are not canonical")
    row_identities = {
        (
            row["document_index"],
            row["json_path"],
            row["role"],
            row["seed"],
            row["source_path"],
        )
        for row in rows
    }
    if len(row_identities) != len(rows):
        raise SeedInventoryBlocked("seed inventory rows contain duplicates")

    raw_bindings = inventory["source_bindings"]
    if not isinstance(raw_bindings, list):
        raise SeedInventoryBlocked("seed source bindings must be a list")
    bindings: list[dict[str, Any]] = []
    for index, raw_binding in enumerate(raw_bindings):
        binding = _mapping(raw_binding, f"seed source binding[{index}]")
        _require_exact_keys(
            binding, _BINDING_FIELDS, f"seed source binding[{index}]"
        )
        binding["path"] = _canonical_path(
            binding["path"], f"seed source binding[{index}].path"
        )
        expected_format = _artifact_format(binding["path"])
        if binding["format"] not in _SUPPORTED_FORMATS or binding["format"] != expected_format:
            raise SeedInventoryBlocked(f"seed source binding[{index}] format mismatch")
        digest = binding["sha256"]
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise SeedInventoryBlocked(f"seed source binding[{index}] digest is invalid")
        binding["size_bytes"] = _positive_integer(
            binding["size_bytes"], f"seed source binding[{index}].size_bytes"
        )
        binding["document_count"] = _positive_integer(
            binding["document_count"],
            f"seed source binding[{index}].document_count",
        )
        binding["row_count"] = _positive_integer(
            binding["row_count"], f"seed source binding[{index}].row_count"
        )
        bindings.append(binding)
    if bindings != sorted(bindings, key=lambda row: row["path"]):
        raise SeedInventoryBlocked("seed source bindings are not canonical")
    if len({binding["path"] for binding in bindings}) != len(bindings):
        raise SeedInventoryBlocked("seed source bindings contain duplicate paths")

    rows_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rows_by_source.setdefault(row["source_path"], []).append(row)
    if set(rows_by_source) != {binding["path"] for binding in bindings}:
        raise SeedInventoryBlocked("seed rows and source bindings differ")
    for binding in bindings:
        source_rows = rows_by_source[binding["path"]]
        if binding["row_count"] != len(source_rows) or any(
            row["document_index"] >= binding["document_count"] for row in source_rows
        ):
            raise SeedInventoryBlocked("seed source binding counts mismatch")

    reserved = set(
        range(
            PREVIOUS_UNTOUCHED_HOLDOUT_START,
            PREVIOUS_UNTOUCHED_HOLDOUT_END + 1,
        )
    )
    excluded = sorted({row["seed"] for row in rows} | reserved)
    raw_excluded = inventory["excluded_seeds"]
    if not isinstance(raw_excluded, list):
        raise SeedInventoryBlocked("excluded seeds must be a list")
    normalized_excluded = [
        _nonnegative_integer(seed, "excluded seed") for seed in raw_excluded
    ]
    if normalized_excluded != excluded:
        raise SeedInventoryBlocked("seed inventory exclusion union mismatch")
    if _nonnegative_integer(inventory["row_count"], "seed inventory row count") != len(
        rows
    ):
        raise SeedInventoryBlocked("seed inventory row count mismatch")
    if _nonnegative_integer(
        inventory["source_count"], "seed inventory source count"
    ) != len(bindings):
        raise SeedInventoryBlocked("seed inventory source count mismatch")
    if _nonnegative_integer(
        inventory["excluded_seed_count"], "seed inventory exclusion count"
    ) != len(excluded):
        raise SeedInventoryBlocked("seed inventory exclusion count mismatch")

    inventory["repository_commit"] = commit
    inventory["rows"] = rows
    inventory["source_bindings"] = bindings
    inventory["excluded_seeds"] = excluded
    return inventory


def verify_seed_inventory(
    inventory: object, repo_root: Path | str
) -> dict[str, Any]:
    """Validate and replay an inventory from the commit recorded inside it."""
    normalized = validate_seed_inventory(inventory)
    rebuilt = rebuild_seed_inventory(
        repo_root,
        repository_commit=normalized["repository_commit"],
    )
    if canonical_json_bytes(normalized) != canonical_json_bytes(rebuilt):
        raise SeedInventoryBlocked("seed inventory rebuild mismatch")
    return normalized


def materialize_fresh_schedule(inventory: object) -> dict[str, Any]:
    """Select the first 512 ascending, nonnegative, nonexcluded seeds."""
    normalized = validate_seed_inventory(inventory)
    excluded = set(normalized["excluded_seeds"])
    selected: list[int] = []
    candidate = CANONICAL_SEARCH_START
    while len(selected) < TRAINING_SEED_COUNT:
        if candidate not in excluded:
            selected.append(candidate)
        candidate += 1
    return {
        "canonical_search_start": CANONICAL_SEARCH_START,
        "inventory_sha256": hashlib.sha256(
            canonical_json_bytes(normalized)
        ).hexdigest(),
        "schema_version": FRESH_SCHEDULE_SCHEMA_VERSION,
        "seed_count": TRAINING_SEED_COUNT,
        "seeds": selected,
    }


def validate_fresh_schedule(
    inventory: object, schedule: object
) -> dict[str, Any]:
    normalized_schedule = _mapping(schedule, "fresh schedule")
    _require_exact_keys(normalized_schedule, _SCHEDULE_FIELDS, "fresh schedule")
    if normalized_schedule["schema_version"] != FRESH_SCHEDULE_SCHEMA_VERSION:
        raise SeedInventoryBlocked("fresh schedule schema mismatch")
    if (
        isinstance(normalized_schedule["canonical_search_start"], bool)
        or normalized_schedule["canonical_search_start"] != CANONICAL_SEARCH_START
    ):
        raise SeedInventoryBlocked("fresh schedule canonical start mismatch")
    digest = normalized_schedule["inventory_sha256"]
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise SeedInventoryBlocked("fresh schedule inventory digest is invalid")
    if _nonnegative_integer(normalized_schedule["seed_count"], "fresh schedule count") != TRAINING_SEED_COUNT:
        raise SeedInventoryBlocked("fresh schedule count mismatch")
    raw_seeds = normalized_schedule["seeds"]
    if not isinstance(raw_seeds, list):
        raise SeedInventoryBlocked("fresh schedule seeds must be a list")
    seeds = [_nonnegative_integer(seed, "fresh schedule seed") for seed in raw_seeds]
    if len(seeds) != TRAINING_SEED_COUNT or seeds != sorted(set(seeds)):
        raise SeedInventoryBlocked("fresh schedule seeds are not canonical")
    normalized_schedule["seeds"] = seeds
    expected = materialize_fresh_schedule(inventory)
    if canonical_json_bytes(normalized_schedule) != canonical_json_bytes(expected):
        raise SeedInventoryBlocked("fresh schedule differs from the fixed selection")
    return normalized_schedule


def _readiness_authority() -> dict[str, bool]:
    return {name: False for name in _READINESS_AUTHORITY_NAMES}


def _deterministic_gzip_bytes(payload: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(
        fileobj=buffer, mode="wb", filename="", mtime=0
    ) as handle:
        handle.write(payload)
    return buffer.getvalue()


def validate_readiness_candidate_artifact(
    value: object, *, expected_source_commit: str
) -> dict[str, Any]:
    """Validate one readiness candidate without importing the readiness auditor."""
    artifact = _mapping(value, "readiness candidate artifact")
    _require_exact_keys(
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
        "readiness candidate artifact",
    )
    commit = _repository_commit(expected_source_commit)
    if artifact["schema_version"] != READINESS_CANDIDATE_SCHEMA_VERSION:
        raise SeedInventoryBlocked("readiness candidate schema mismatch")
    if artifact["source_commit"] != commit:
        raise SeedInventoryBlocked("readiness candidate source commit mismatch")
    authority = _mapping(artifact["authority"], "readiness candidate authority")
    expected_authority = _readiness_authority()
    _require_exact_keys(
        authority, set(expected_authority), "readiness candidate authority"
    )
    if (
        any(type(enabled) is not bool for enabled in authority.values())
        or authority != expected_authority
    ):
        raise SeedInventoryBlocked("readiness candidate authority must remain all false")

    inventory = validate_seed_inventory(artifact["historical_seed_inventory"])
    if inventory["repository_commit"] != commit:
        raise SeedInventoryBlocked("readiness inventory source commit mismatch")
    schedule = validate_fresh_schedule(inventory, artifact["candidate_schedule"])

    consumed = _mapping(artifact["consumed_cohort"], "consumed cohort")
    _require_exact_keys(
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
    registration_id = consumed["registration_id"]
    if not isinstance(registration_id, str) or not registration_id:
        raise SeedInventoryBlocked("consumed registration identity is invalid")
    binding = _mapping(consumed["registration_binding"], "consumed registration binding")
    _require_exact_keys(
        binding, {"path", "sha256", "size_bytes"}, "consumed registration binding"
    )
    binding["path"] = _canonical_path(
        binding["path"], "consumed registration binding path"
    )
    if not isinstance(binding["sha256"], str) or _SHA256_RE.fullmatch(
        binding["sha256"]
    ) is None:
        raise SeedInventoryBlocked("consumed registration binding digest is invalid")
    binding["size_bytes"] = _positive_integer(
        binding["size_bytes"], "consumed registration binding size"
    )
    raw_consumed = consumed["seeds"]
    if not isinstance(raw_consumed, list):
        raise SeedInventoryBlocked("consumed cohort seeds must be a list")
    consumed_seeds = [
        _nonnegative_integer(seed, "consumed cohort seed") for seed in raw_consumed
    ]
    consumed_seed_count = _nonnegative_integer(
        consumed["seed_count"], "consumed cohort seed count"
    )
    if (
        len(consumed_seeds) != TRAINING_SEED_COUNT
        or consumed_seeds != sorted(set(consumed_seeds))
        or consumed_seed_count != TRAINING_SEED_COUNT
        or consumed["seeds_sha256"]
        != hashlib.sha256(canonical_json_bytes(consumed_seeds)).hexdigest()
    ):
        raise SeedInventoryBlocked("consumed cohort identity mismatch")

    collisions = sorted(set(schedule["seeds"]) & set(consumed_seeds))
    disjointness = _mapping(artifact["disjointness"], "readiness disjointness")
    _require_exact_keys(
        disjointness,
        {"collision_count", "collisions", "status"},
        "readiness disjointness",
    )
    disjointness["collision_count"] = _nonnegative_integer(
        disjointness["collision_count"], "readiness disjointness collision count"
    )
    raw_collisions = disjointness["collisions"]
    if not isinstance(raw_collisions, list):
        raise SeedInventoryBlocked("readiness disjointness collisions must be a list")
    disjointness["collisions"] = [
        _nonnegative_integer(seed, "readiness disjointness collision")
        for seed in raw_collisions
    ]
    if disjointness["status"] not in {"failed", "passed"}:
        raise SeedInventoryBlocked("readiness disjointness status is invalid")
    expected_disjointness = {
        "collision_count": len(collisions),
        "collisions": collisions,
        "status": "passed" if not collisions else "failed",
    }
    if disjointness != expected_disjointness or collisions:
        raise SeedInventoryBlocked("readiness candidate cohort is not disjoint")

    artifact["authority"] = authority
    artifact["historical_seed_inventory"] = inventory
    artifact["candidate_schedule"] = schedule
    artifact["consumed_cohort"] = {
        **consumed,
        "registration_binding": binding,
        "seed_count": consumed_seed_count,
        "seeds": consumed_seeds,
    }
    artifact["disjointness"] = expected_disjointness
    artifact["source_commit"] = commit
    return artifact


def decode_readiness_candidate_artifact(
    stored: bytes,
    *,
    expected_binding: Mapping[str, Any],
    expected_source_commit: str,
) -> dict[str, Any]:
    """Decode one bounded deterministic-gzip readiness candidate artifact."""
    binding = _mapping(expected_binding, "readiness candidate binding")
    _require_exact_keys(
        binding,
        {
            "canonical_sha256",
            "canonical_size_bytes",
            "encoding",
            "sha256",
            "size_bytes",
        },
        "readiness candidate binding",
    )
    if binding["encoding"] != READINESS_CANDIDATE_ENCODING:
        raise SeedInventoryBlocked("readiness candidate encoding mismatch")
    for field in ("sha256", "canonical_sha256"):
        if not isinstance(binding[field], str) or _SHA256_RE.fullmatch(
            binding[field]
        ) is None:
            raise SeedInventoryBlocked(f"readiness candidate {field} is invalid")
    binding["size_bytes"] = _positive_integer(
        binding["size_bytes"], "readiness candidate stored size"
    )
    binding["canonical_size_bytes"] = _positive_integer(
        binding["canonical_size_bytes"], "readiness candidate canonical size"
    )
    if (
        binding["size_bytes"] > MAX_READINESS_CANDIDATE_STORED_BYTES
        or binding["canonical_size_bytes"] > MAX_READINESS_CANDIDATE_CANONICAL_BYTES
    ):
        raise SeedInventoryBlocked("readiness candidate exceeds byte ceiling")
    if (
        not isinstance(stored, bytes)
        or not stored
        or len(stored) != binding["size_bytes"]
        or hashlib.sha256(stored).hexdigest() != binding["sha256"]
    ):
        raise SeedInventoryBlocked("readiness candidate stored bytes mismatch")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(stored), mode="rb") as handle:
            canonical = handle.read(MAX_READINESS_CANDIDATE_CANONICAL_BYTES + 1)
    except (EOFError, OSError, gzip.BadGzipFile) as exc:
        raise SeedInventoryBlocked("readiness candidate gzip is invalid") from exc
    if len(canonical) > MAX_READINESS_CANDIDATE_CANONICAL_BYTES:
        raise SeedInventoryBlocked("readiness candidate canonical bytes exceed ceiling")
    if _deterministic_gzip_bytes(canonical) != stored:
        raise SeedInventoryBlocked("readiness candidate gzip is not deterministic")
    if (
        len(canonical) != binding["canonical_size_bytes"]
        or hashlib.sha256(canonical).hexdigest() != binding["canonical_sha256"]
    ):
        raise SeedInventoryBlocked("readiness candidate canonical bytes mismatch")
    parsed = _strict_json(canonical, "readiness candidate")
    if canonical_json_bytes(parsed) != canonical:
        raise SeedInventoryBlocked("readiness candidate JSON is not canonical")
    candidate = validate_readiness_candidate_artifact(
        parsed, expected_source_commit=expected_source_commit
    )
    if canonical_json_bytes(candidate) != canonical:
        raise SeedInventoryBlocked("readiness candidate normalization drifted")
    return candidate


__all__ = [
    "CANONICAL_SEARCH_START",
    "FRESH_SCHEDULE_SCHEMA_VERSION",
    "MAX_READINESS_CANDIDATE_CANONICAL_BYTES",
    "MAX_READINESS_CANDIDATE_STORED_BYTES",
    "PREVIOUS_UNTOUCHED_HOLDOUT_END",
    "PREVIOUS_UNTOUCHED_HOLDOUT_START",
    "READINESS_CANDIDATE_ENCODING",
    "READINESS_CANDIDATE_SCHEMA_VERSION",
    "SEED_INVENTORY_SCHEMA_VERSION",
    "TRAINING_SEED_COUNT",
    "SeedInventoryBlocked",
    "build_seed_inventory",
    "canonical_json_bytes",
    "decode_readiness_candidate_artifact",
    "materialize_fresh_schedule",
    "rebuild_seed_inventory",
    "validate_fresh_schedule",
    "validate_readiness_candidate_artifact",
    "validate_seed_inventory",
    "verify_seed_inventory",
]
