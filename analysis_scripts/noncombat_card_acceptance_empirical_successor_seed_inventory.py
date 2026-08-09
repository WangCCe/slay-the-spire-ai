"""Source-only seed inventory for the card-acceptance empirical successor.

The module reads only caller-bound Git blobs. It has no Torch, native adapter,
gameplay, model, or environment imports.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib
import json
import math
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any


SOURCE_REGISTRY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-seed-source-registry-v1"
)
SEED_INVENTORY_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-seed-inventory-v3"
)
INVENTORY_AUTHORITY_EVIDENCE_SCHEMA_VERSION = (
    "noncombat-card-acceptance-empirical-successor-"
    "seed-inventory-authority-evidence-v1"
)
OUTPUT_ROOT_POLICY_VERSION = (
    "noncombat-card-acceptance-empirical-successor-output-root-policy-v1"
)
INVENTORY_FILENAME = "seed_inventory.json"
CANONICAL_SEARCH_START = 0
TRAINING_SEED_COUNT = 512
CANARY_SEED_COUNT = 128
HOLDOUT_SEED_COUNT = 512

_CONTROL_MODULE = (
    "analysis_scripts.noncombat_card_acceptance_empirical_successor_experiment"
)
_COMMIT_RE = re.compile(r"[0-9a-f]{40}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_SUPPORTED_FORMATS = ("json", "jsonl", "json.gz", "jsonl.gz")
_ROLE_COUNTS = {
    "canary": CANARY_SEED_COUNT,
    "holdout": HOLDOUT_SEED_COUNT,
    "training": TRAINING_SEED_COUNT,
}
_ROLE_ORDER = ("training", "canary", "holdout")
_ROW_ROLES = {
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
_COHORT_ROLES = {
    "canary": "canary",
    "diagnostic": "diagnostic",
    "evaluation": "evaluation",
    "fit": "training",
    "holdout": "holdout",
    "qualification": "qualification",
    "train": "training",
    "training": "training",
    "validation": "holdout",
}
_GENERATED_ROOT_KINDS = (
    "attempt",
    "candidate",
    "scratch",
    "sealed",
    "staging",
    "temporary",
)
_SUCCESSOR_REPORT_PREFIX = "noncombat_card_acceptance_empirical_successor_"
_SUCCESSOR_HIDDEN_PREFIX = ".noncombat_card_acceptance_empirical_successor_"

_SOURCE_FIELDS = {
    "document_count",
    "format",
    "path",
    "row_count",
    "sha256",
    "size_bytes",
}
_ROW_FIELDS = {"document_index", "json_path", "role", "seed", "source_path"}
_ROOT_FIELDS = {"kind", "path"}
_POLICY_FIELDS = {
    "candidate_output_root",
    "excluded_kinds",
    "registered_source_root",
    "schema_version",
}
_REGISTRY_FIELDS = {
    "excluded_roots",
    "output_root_policy",
    "registry_sha256",
    "repository_commit",
    "schema_version",
    "source_count",
    "sources",
}
_INVENTORY_FIELDS = {
    "authority_evidence",
    "authorization_sha256",
    "cohort_counts",
    "cohorts",
    "excluded_seed_count",
    "excluded_seeds",
    "excluded_seeds_sha256",
    "inventory_sha256",
    "launch_authority_sha256",
    "request_sha256",
    "repository_commit",
    "role_sha256",
    "row_count",
    "rows",
    "schema_version",
    "source_inventory_sha256",
    "source_registry",
}
_AUTHORITY_EVIDENCE_FIELDS = {
    "approval_record",
    "authority_evidence_sha256",
    "authorization",
    "build_launch_observation",
    "request",
    "schema_version",
    "source_inventory",
}


class SeedInventoryBlocked(RuntimeError):
    """Raised before an ambiguous or unauthorized inventory operation."""


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


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise SeedInventoryBlocked(f"{label} must be a mapping")
    return copy.deepcopy(dict(value))


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise SeedInventoryBlocked(f"{label} fields mismatch")


def _nonnegative_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SeedInventoryBlocked(f"{label} must be a nonnegative integer")
    return value


def _positive_integer(value: object, label: str) -> int:
    result = _nonnegative_integer(value, label)
    if result == 0:
        raise SeedInventoryBlocked(f"{label} must be positive")
    return result


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise SeedInventoryBlocked(f"{label} must be 64 lowercase hex characters")
    return value


def _commit(value: object) -> str:
    if not isinstance(value, str) or _COMMIT_RE.fullmatch(value) is None:
        raise SeedInventoryBlocked(
            "repository commit must be 40 lowercase hex characters"
        )
    return value


def _canonical_report_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise SeedInventoryBlocked(f"{label} must be a canonical reports path")
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
    for suffix, name in (
        (".jsonl.gz", "jsonl.gz"),
        (".json.gz", "json.gz"),
        (".jsonl", "jsonl"),
        (".json", "json"),
    ):
        if path.endswith(suffix):
            return name
    return None


def _unsupported_seed_candidate(path: str) -> bool:
    folded = path.casefold()
    filename = PurePosixPath(folded).name
    near_structured = filename.endswith(
        (".json.zip", ".json.zst", ".json.bz2", ".json.xz")
    )
    return near_structured or "seed" in folded or "cohort" in folded


def _git_command(
    repo_root: Path, args: list[str], *, input_bytes: bytes | None = None
) -> bytes:
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


def _repository_relative_path(repo_root: Path, value: str) -> str | None:
    try:
        relative = Path(value).resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    result = relative.as_posix()
    if not result or result == ".":
        return None
    return result


def _candidate_root_details(
    repo_root: Path, output_root: str
) -> tuple[str | None, str, str]:
    relative = _repository_relative_path(repo_root, output_root)
    if relative is None:
        return None, "", ""
    pure = PurePosixPath(relative)
    return relative, pure.parent.as_posix(), pure.name


def _root_match(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _classify_generated_root(
    path: str, *, repo_root: Path, output_root: str
) -> tuple[str, str] | None:
    candidate, parent, basename = _candidate_root_details(repo_root, output_root)
    if candidate is not None and _root_match(path, candidate):
        return "candidate", candidate

    pure = PurePosixPath(path)
    ancestors = [PurePosixPath(*pure.parts[:index]) for index in range(2, len(pure.parts))]
    for ancestor in ancestors:
        root = ancestor.as_posix()
        name = ancestor.name
        ancestor_parent = ancestor.parent.as_posix()
        if candidate is not None and ancestor_parent == parent:
            if name == f"{basename}_attempts":
                return "attempt", root
            hidden_prefix = f".{basename}."
            if name.startswith(hidden_prefix):
                for suffix, kind in (
                    (".scratch", "scratch"),
                    (".sealed", "sealed"),
                    (".staging", "staging"),
                    (".temporary", "temporary"),
                    (".tmp", "temporary"),
                ):
                    if name.endswith(suffix):
                        return kind, root

        if ancestor.parent.as_posix() != "reports":
            continue
        if name.startswith(_SUCCESSOR_HIDDEN_PREFIX):
            for suffix, kind in (
                (".scratch", "scratch"),
                (".sealed", "sealed"),
                (".staging", "staging"),
                (".temporary", "temporary"),
                (".tmp", "temporary"),
            ):
                if name.endswith(suffix):
                    return kind, root
            return "temporary", root
        if name.startswith(_SUCCESSOR_REPORT_PREFIX):
            if "attempt" in name:
                return "attempt", root
            return "candidate", root
    return None


def _list_tree_report_paths(repo_root: Path, repository_commit: str) -> list[str]:
    raw = _git_command(
        repo_root,
        ["ls-tree", "-r", "-z", repository_commit, "--", "reports"],
    )
    if raw and not raw.endswith(b"\0"):
        raise SeedInventoryBlocked("git ls-tree response is truncated")
    paths: list[str] = []
    for encoded in raw.split(b"\0"):
        if not encoded:
            continue
        try:
            metadata, encoded_path = encoded.split(b"\t", 1)
            mode, object_type, _object_id = metadata.decode("ascii").split()
            path = encoded_path.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise SeedInventoryBlocked("git ls-tree entry is malformed") from exc
        if object_type != "blob" or mode not in {"100644", "100755"}:
            raise SeedInventoryBlocked(f"historical source is not a regular blob: {path}")
        paths.append(_canonical_report_path(path, "tracked report path"))
    if paths != sorted(set(paths)):
        raise SeedInventoryBlocked("tracked report paths are not sorted and unique")
    return paths


def _list_registered_source_paths(
    repo_root: Path, *, repository_commit: str, output_root: str
) -> tuple[list[str], list[dict[str, str]]]:
    candidates: list[str] = []
    excluded: dict[str, str] = {}
    for path in _list_tree_report_paths(repo_root, repository_commit):
        generated = _classify_generated_root(
            path,
            repo_root=repo_root,
            output_root=output_root,
        )
        if generated is not None:
            kind, root = generated
            previous = excluded.setdefault(root, kind)
            if previous != kind:
                raise SeedInventoryBlocked("generated output root classification is ambiguous")
            continue
        if _artifact_format(path) is not None:
            candidates.append(path)
        elif _unsupported_seed_candidate(path):
            raise SeedInventoryBlocked(f"unsupported candidate seed artifact: {path}")
    return candidates, [
        {"kind": excluded[path], "path": path} for path in sorted(excluded)
    ]


def _git_blob_batch(
    repo_root: Path, *, repository_commit: str, paths: list[str]
) -> dict[str, bytes]:
    ordered = [_canonical_report_path(path, "seed source path") for path in paths]
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
            raise SeedInventoryBlocked(f"seed source gzip is invalid: {path}: {exc}") from exc
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
        documents.append(_strict_json(line.encode("utf-8"), f"{path}:{line_number}"))
    return documents


def _json_pointer(parent: str, token: object) -> str:
    escaped = str(token).replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}"


def _semantic_role(key: str, fallback: str) -> str:
    folded = key.casefold().replace("-", "_")
    for needle, role in (
        ("failed_access", "failed_access"),
        ("failed_seed", "failed_access"),
        ("diagnostic", "diagnostic"),
        ("reserved", "reserved"),
        ("used", "used"),
        ("canary", "canary"),
        ("holdout", "holdout"),
        ("validation", "holdout"),
        ("evaluation", "evaluation"),
        ("qualification", "qualification"),
        ("training", "training"),
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
                    raise SeedInventoryBlocked("JSON object key must be a string")
                folded = key.casefold()
                key_has_seed = "seed" in folded
                cohort_role = _COHORT_ROLES.get(folded) if cohorts_mapping else None
                child_role = cohort_role or _semantic_role(key, role)
                visit(
                    node[key],
                    _json_pointer(pointer, key),
                    seed_context=seed_context or key_has_seed or cohort_role is not None,
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


def _output_root_policy(repo_root: Path, output_root: str) -> dict[str, Any]:
    candidate = _repository_relative_path(repo_root, output_root)
    return {
        "candidate_output_root": candidate,
        "excluded_kinds": list(_GENERATED_ROOT_KINDS),
        "registered_source_root": "reports",
        "schema_version": OUTPUT_ROOT_POLICY_VERSION,
    }


def _build_source_registry_and_rows(
    repo_root: Path, *, repository_commit: str, output_root: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[int]]:
    paths, excluded_roots = _list_registered_source_paths(
        repo_root,
        repository_commit=repository_commit,
        output_root=output_root,
    )
    blobs = _git_blob_batch(
        repo_root,
        repository_commit=repository_commit,
        paths=paths,
    )
    sources: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for path in paths:
        payload = blobs[path]
        format_name = _artifact_format(path)
        if format_name is None:
            raise SeedInventoryBlocked(f"registered source format changed: {path}")
        documents = _parse_documents(path, payload, format_name)
        source_rows: list[dict[str, Any]] = []
        for document_index, document in enumerate(documents):
            source_rows.extend(
                _seed_rows(
                    document,
                    source_path=path,
                    document_index=document_index,
                )
            )
        rows.extend(source_rows)
        sources.append(
            {
                "document_count": len(documents),
                "format": format_name,
                "path": path,
                "row_count": len(source_rows),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    rows.sort(key=_row_sort_key)
    registry_body = {
        "excluded_roots": excluded_roots,
        "output_root_policy": _output_root_policy(repo_root, output_root),
        "repository_commit": repository_commit,
        "schema_version": SOURCE_REGISTRY_SCHEMA_VERSION,
        "source_count": len(sources),
        "sources": sources,
    }
    registry = {
        **registry_body,
        "registry_sha256": _canonical_sha256(registry_body),
    }
    return registry, rows, sorted({row["seed"] for row in rows})


def _validate_inventory_authority(
    *,
    repo_root: Path,
    request: object,
    authorization: object,
    approval_record: object,
    launch_observation: object,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    if not isinstance(authorization, Mapping):
        raise SeedInventoryBlocked("inventory authorization must be a mapping")
    try:
        control = importlib.import_module(_CONTROL_MODULE)
        normalized_request = control.validate_stage_request(request)
        if normalized_request["stage"] != "inventory":
            raise SeedInventoryBlocked("inventory operation requires inventory stage")
        normalized_authorization = control.validate_stage_authorization(
            authorization,
            normalized_request,
        )
        expected = control.stage_execution_authority("inventory")
        approval = _mapping(approval_record, "inventory approval record")
        if approval.get("approval_mode") == "standing-delegation":
            normalized_launch = control.validate_delegated_stage_launch(
                request=normalized_request,
                authorization=normalized_authorization,
                delegated_approval=approval,
                launch_observation=launch_observation,
            )
        elif approval.get("approval_mode") == "external-human-approval":
            normalized_launch = control.validate_external_human_stage_launch(
                request=normalized_request,
                authorization=normalized_authorization,
                external_approval=approval,
                launch_observation=launch_observation,
            )
        else:
            raise SeedInventoryBlocked("inventory approval mode is invalid")
    except SeedInventoryBlocked:
        raise
    except Exception as exc:
        raise SeedInventoryBlocked(f"inventory authorization is invalid: {exc}") from exc
    if (
        normalized_request["execution_authority"] != expected
        or normalized_authorization["execution_authority"] != expected
        or set(normalized_request["downstream_authority"].values()) != {False}
        or set(normalized_authorization["downstream_authority"].values()) != {False}
    ):
        raise SeedInventoryBlocked("inventory authority map is invalid")

    try:
        if not repo_root.is_dir():
            raise SeedInventoryBlocked("source repository root is missing")
        top_level = Path(
            _git_command(repo_root, ["rev-parse", "--show-toplevel"])
            .decode("utf-8", errors="strict")
            .strip()
        ).resolve()
        if top_level != repo_root:
            raise SeedInventoryBlocked("repository root is not the Git top level")
        expected_commit = normalized_request["source_commit"]
        head = (
            _git_command(repo_root, ["rev-parse", "HEAD"])
            .decode("ascii", errors="strict")
            .strip()
        )
        remote = (
            _git_command(repo_root, ["rev-parse", "origin/master"])
            .decode("ascii", errors="strict")
            .strip()
        )
        tracked_status = _git_command(
            repo_root,
            ["status", "--porcelain=v1", "--untracked-files=no"],
        )
        if head != expected_commit or remote != expected_commit:
            raise SeedInventoryBlocked(
                "source commit is not the exact pushed origin/master identity"
            )
        if tracked_status:
            raise SeedInventoryBlocked("source tracked worktree is not clean")
        source_inventory = _mapping(
            control.build_source_inventory(repo_root),
            "source inventory",
        )
        source_digest = _digest(
            source_inventory.get("inventory_sha256"),
            "source inventory digest",
        )
        if source_digest != normalized_request["source_inventory_sha256"]:
            raise SeedInventoryBlocked("source inventory digest differs from request")
        preservation = _mapping(
            source_inventory.get("consumed_evidence_preservation"),
            "consumed evidence preservation",
        )
        if preservation.get("verified") is not True:
            raise SeedInventoryBlocked("consumed evidence preservation is not verified")
        _digest(
            preservation.get("manifest_sha256"),
            "consumed evidence preservation manifest digest",
        )
    except (OSError, UnicodeDecodeError, SeedInventoryBlocked) as exc:
        raise SeedInventoryBlocked(f"source qualification failed: {exc}") from exc
    except Exception as exc:
        raise SeedInventoryBlocked(f"source qualification failed: {exc}") from exc
    return (
        normalized_request,
        normalized_authorization,
        approval,
        normalized_launch,
        source_inventory,
    )


def _normalize_authority_evidence(value: object) -> dict[str, Any]:
    evidence = _mapping(value, "inventory authority evidence")
    _require_exact_keys(
        evidence,
        _AUTHORITY_EVIDENCE_FIELDS,
        "inventory authority evidence",
    )
    if evidence["schema_version"] != INVENTORY_AUTHORITY_EVIDENCE_SCHEMA_VERSION:
        raise SeedInventoryBlocked("inventory authority evidence schema mismatch")
    body = {
        key: item
        for key, item in evidence.items()
        if key != "authority_evidence_sha256"
    }
    if _digest(
        evidence["authority_evidence_sha256"],
        "inventory authority evidence digest",
    ) != _canonical_sha256(body):
        raise SeedInventoryBlocked("inventory authority evidence digest mismatch")

    request = _mapping(evidence["request"], "inventory evidence request")
    authorization = _mapping(
        evidence["authorization"],
        "inventory evidence authorization",
    )
    approval = _mapping(
        evidence["approval_record"],
        "inventory evidence approval record",
    )
    launch = _mapping(
        evidence["build_launch_observation"],
        "inventory evidence build launch observation",
    )
    source_inventory = _mapping(
        evidence["source_inventory"],
        "inventory evidence source inventory",
    )
    try:
        control = importlib.import_module(_CONTROL_MODULE)
        normalized_request = control.validate_stage_request(request)
        normalized_authorization = control.validate_stage_authorization(
            authorization,
            normalized_request,
        )
        if approval.get("approval_mode") == "standing-delegation":
            normalized_approval = control.validate_delegated_approval(
                approval,
                normalized_request,
            )
            normalized_launch = control.validate_delegated_stage_launch(
                request=normalized_request,
                authorization=normalized_authorization,
                delegated_approval=normalized_approval,
                launch_observation=launch,
            )
        elif approval.get("approval_mode") == "external-human-approval":
            normalized_approval = control.validate_external_human_approval(
                approval,
                normalized_request,
            )
            normalized_launch = control.validate_external_human_stage_launch(
                request=normalized_request,
                authorization=normalized_authorization,
                external_approval=normalized_approval,
                launch_observation=launch,
            )
        else:
            raise SeedInventoryBlocked("inventory evidence approval mode is invalid")
    except SeedInventoryBlocked:
        raise
    except Exception as exc:
        raise SeedInventoryBlocked(
            f"inventory authority evidence is invalid: {exc}"
        ) from exc

    source_body = {
        key: item
        for key, item in source_inventory.items()
        if key != "inventory_sha256"
    }
    source_digest = _digest(
        source_inventory.get("inventory_sha256"),
        "inventory evidence source inventory digest",
    )
    if source_digest != _canonical_sha256(source_body):
        raise SeedInventoryBlocked("inventory evidence source inventory digest mismatch")
    preservation = _mapping(
        source_inventory.get("consumed_evidence_preservation"),
        "inventory evidence consumed preservation",
    )
    if preservation.get("verified") is not True:
        raise SeedInventoryBlocked("inventory evidence preservation is not verified")
    _digest(
        preservation.get("manifest_sha256"),
        "inventory evidence preservation manifest digest",
    )
    if normalized_request["source_inventory_sha256"] != source_digest:
        raise SeedInventoryBlocked("inventory evidence source binding mismatch")
    return {
        **evidence,
        "approval_record": normalized_approval,
        "authorization": normalized_authorization,
        "build_launch_observation": normalized_launch,
        "request": normalized_request,
        "source_inventory": source_inventory,
    }


def _build_authority_evidence(
    *,
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    approval_record: Mapping[str, Any],
    build_launch_observation: Mapping[str, Any],
    source_inventory: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "approval_record": copy.deepcopy(dict(approval_record)),
        "authorization": copy.deepcopy(dict(authorization)),
        "build_launch_observation": copy.deepcopy(
            dict(build_launch_observation)
        ),
        "request": copy.deepcopy(dict(request)),
        "schema_version": INVENTORY_AUTHORITY_EVIDENCE_SCHEMA_VERSION,
        "source_inventory": copy.deepcopy(dict(source_inventory)),
    }
    return _normalize_authority_evidence(
        {**body, "authority_evidence_sha256": _canonical_sha256(body)}
    )


def _select_fresh_cohorts(excluded_seeds: list[int]) -> dict[str, list[int]]:
    excluded = set(excluded_seeds)
    total = sum(_ROLE_COUNTS.values())
    selected: list[int] = []
    candidate = CANONICAL_SEARCH_START
    while len(selected) < total:
        if candidate not in excluded:
            selected.append(candidate)
        candidate += 1
    training_end = TRAINING_SEED_COUNT
    canary_end = training_end + CANARY_SEED_COUNT
    return {
        "training": selected[:training_end],
        "canary": selected[training_end:canary_end],
        "holdout": selected[canary_end:],
    }


def _verify_materialized_cohorts(
    cohorts: Mapping[str, list[int]], excluded_seeds: list[int]
) -> None:
    excluded = set(excluded_seeds)
    candidate = CANONICAL_SEARCH_START
    seen: set[int] = set()
    for role in _ROLE_ORDER:
        values = cohorts[role]
        for value in values:
            while candidate in excluded:
                candidate += 1
            if value != candidate:
                raise SeedInventoryBlocked(
                    "inventory cohorts differ from fixed ascending selection"
                )
            if value in seen:
                raise SeedInventoryBlocked("inventory cohorts are not pairwise disjoint")
            seen.add(value)
            candidate += 1


def _inventory_body(
    *,
    request: Mapping[str, Any],
    authorization: Mapping[str, Any],
    authority_evidence: Mapping[str, Any],
    launch_observation: Mapping[str, Any],
    source_registry: Mapping[str, Any],
    rows: list[dict[str, Any]],
    excluded_seeds: list[int],
    cohorts: Mapping[str, list[int]],
) -> dict[str, Any]:
    return {
        "authority_evidence": copy.deepcopy(dict(authority_evidence)),
        "authorization_sha256": authorization["authorization_sha256"],
        "cohort_counts": copy.deepcopy(_ROLE_COUNTS),
        "cohorts": copy.deepcopy(dict(cohorts)),
        "excluded_seed_count": len(excluded_seeds),
        "excluded_seeds": list(excluded_seeds),
        "excluded_seeds_sha256": _canonical_sha256(excluded_seeds),
        "launch_authority_sha256": launch_observation["observation_sha256"],
        "request_sha256": request["request_sha256"],
        "repository_commit": request["source_commit"],
        "role_sha256": {
            role: _canonical_sha256(cohorts[role]) for role in _ROLE_ORDER
        },
        "row_count": len(rows),
        "rows": copy.deepcopy(rows),
        "schema_version": SEED_INVENTORY_SCHEMA_VERSION,
        "source_inventory_sha256": request["source_inventory_sha256"],
        "source_registry": copy.deepcopy(dict(source_registry)),
    }


def _normalize_source_registry(value: object) -> dict[str, Any]:
    registry = _mapping(value, "seed source registry")
    _require_exact_keys(registry, _REGISTRY_FIELDS, "seed source registry")
    if registry["schema_version"] != SOURCE_REGISTRY_SCHEMA_VERSION:
        raise SeedInventoryBlocked("seed source registry schema mismatch")
    registry["repository_commit"] = _commit(registry["repository_commit"])

    policy = _mapping(registry["output_root_policy"], "output root policy")
    _require_exact_keys(policy, _POLICY_FIELDS, "output root policy")
    if (
        policy["schema_version"] != OUTPUT_ROOT_POLICY_VERSION
        or policy["registered_source_root"] != "reports"
        or policy["excluded_kinds"] != list(_GENERATED_ROOT_KINDS)
    ):
        raise SeedInventoryBlocked("output root policy mismatch")
    candidate = policy["candidate_output_root"]
    if candidate is not None:
        policy["candidate_output_root"] = _canonical_report_path(
            candidate,
            "candidate output root",
        )

    raw_roots = registry["excluded_roots"]
    if not isinstance(raw_roots, list):
        raise SeedInventoryBlocked("excluded roots must be a list")
    roots: list[dict[str, str]] = []
    for index, raw_root in enumerate(raw_roots):
        root = _mapping(raw_root, f"excluded root[{index}]")
        _require_exact_keys(root, _ROOT_FIELDS, f"excluded root[{index}]")
        if root["kind"] not in _GENERATED_ROOT_KINDS:
            raise SeedInventoryBlocked(f"excluded root[{index}] kind mismatch")
        root["path"] = _canonical_report_path(
            root["path"], f"excluded root[{index}] path"
        )
        roots.append(root)
    if roots != sorted(roots, key=lambda row: row["path"]):
        raise SeedInventoryBlocked("excluded roots are not canonical")
    if len({root["path"] for root in roots}) != len(roots):
        raise SeedInventoryBlocked("excluded roots contain duplicates")

    raw_sources = registry["sources"]
    if not isinstance(raw_sources, list):
        raise SeedInventoryBlocked("registered sources must be a list")
    sources: list[dict[str, Any]] = []
    for index, raw_source in enumerate(raw_sources):
        source = _mapping(raw_source, f"registered source[{index}]")
        _require_exact_keys(source, _SOURCE_FIELDS, f"registered source[{index}]")
        source["path"] = _canonical_report_path(
            source["path"], f"registered source[{index}] path"
        )
        expected_format = _artifact_format(source["path"])
        if source["format"] not in _SUPPORTED_FORMATS or source["format"] != expected_format:
            raise SeedInventoryBlocked(f"registered source[{index}] format mismatch")
        source["sha256"] = _digest(
            source["sha256"], f"registered source[{index}] digest"
        )
        source["size_bytes"] = _positive_integer(
            source["size_bytes"], f"registered source[{index}] size"
        )
        source["document_count"] = _positive_integer(
            source["document_count"], f"registered source[{index}] document count"
        )
        source["row_count"] = _nonnegative_integer(
            source["row_count"], f"registered source[{index}] row count"
        )
        if any(_root_match(source["path"], root["path"]) for root in roots):
            raise SeedInventoryBlocked("generated root entered registered sources")
        sources.append(source)
    if sources != sorted(sources, key=lambda row: row["path"]):
        raise SeedInventoryBlocked("registered sources are not canonical")
    if len({source["path"] for source in sources}) != len(sources):
        raise SeedInventoryBlocked("registered sources contain duplicates")
    if _nonnegative_integer(registry["source_count"], "source count") != len(sources):
        raise SeedInventoryBlocked("registered source count mismatch")

    normalized = {
        **registry,
        "excluded_roots": roots,
        "output_root_policy": policy,
        "sources": sources,
    }
    body = {key: value for key, value in normalized.items() if key != "registry_sha256"}
    if _digest(normalized["registry_sha256"], "source registry digest") != _canonical_sha256(body):
        raise SeedInventoryBlocked("seed source registry digest mismatch")
    return normalized


def validate_inventory(value: object) -> dict[str, Any]:
    inventory = _mapping(value, "seed inventory")
    _require_exact_keys(inventory, _INVENTORY_FIELDS, "seed inventory")
    if inventory["schema_version"] != SEED_INVENTORY_SCHEMA_VERSION:
        raise SeedInventoryBlocked("seed inventory schema mismatch")
    inventory["repository_commit"] = _commit(inventory["repository_commit"])
    inventory["request_sha256"] = _digest(
        inventory["request_sha256"], "inventory request digest"
    )
    inventory["authorization_sha256"] = _digest(
        inventory["authorization_sha256"], "inventory authorization digest"
    )
    inventory["launch_authority_sha256"] = _digest(
        inventory["launch_authority_sha256"], "inventory launch authority digest"
    )
    inventory["source_inventory_sha256"] = _digest(
        inventory["source_inventory_sha256"], "inventory source inventory digest"
    )
    authority_evidence = _normalize_authority_evidence(
        inventory["authority_evidence"]
    )
    if inventory["request_sha256"] != authority_evidence["request"]["request_sha256"]:
        raise SeedInventoryBlocked("inventory request authority evidence binding mismatch")
    if (
        inventory["authorization_sha256"]
        != authority_evidence["authorization"]["authorization_sha256"]
    ):
        raise SeedInventoryBlocked(
            "inventory authorization authority evidence binding mismatch"
        )
    if (
        inventory["launch_authority_sha256"]
        != authority_evidence["build_launch_observation"]["observation_sha256"]
    ):
        raise SeedInventoryBlocked("inventory build launch authority binding mismatch")
    if (
        inventory["source_inventory_sha256"]
        != authority_evidence["source_inventory"]["inventory_sha256"]
    ):
        raise SeedInventoryBlocked("inventory source inventory binding mismatch")
    if inventory["repository_commit"] != authority_evidence["request"]["source_commit"]:
        raise SeedInventoryBlocked("inventory source commit binding mismatch")
    registry = _normalize_source_registry(inventory["source_registry"])
    if registry["repository_commit"] != inventory["repository_commit"]:
        raise SeedInventoryBlocked("inventory repository binding mismatch")

    raw_rows = inventory["rows"]
    if not isinstance(raw_rows, list):
        raise SeedInventoryBlocked("seed inventory rows must be a list")
    rows: list[dict[str, Any]] = []
    for index, raw_row in enumerate(raw_rows):
        row = _mapping(raw_row, f"seed row[{index}]")
        _require_exact_keys(row, _ROW_FIELDS, f"seed row[{index}]")
        row["document_index"] = _nonnegative_integer(
            row["document_index"], f"seed row[{index}] document index"
        )
        if not isinstance(row["json_path"], str) or not row["json_path"].startswith("/"):
            raise SeedInventoryBlocked(f"seed row[{index}] JSON path is invalid")
        if row["role"] not in _ROW_ROLES:
            raise SeedInventoryBlocked(f"seed row[{index}] role is invalid")
        row["seed"] = _nonnegative_integer(row["seed"], f"seed row[{index}] seed")
        row["source_path"] = _canonical_report_path(
            row["source_path"], f"seed row[{index}] source path"
        )
        rows.append(row)
    if rows != sorted(rows, key=_row_sort_key):
        raise SeedInventoryBlocked("seed inventory rows are not canonical")
    identities = {
        (
            row["document_index"],
            row["json_path"],
            row["role"],
            row["seed"],
            row["source_path"],
        )
        for row in rows
    }
    if len(identities) != len(rows):
        raise SeedInventoryBlocked("seed inventory rows contain duplicates")
    sources = {source["path"]: source for source in registry["sources"]}
    rows_by_source = {path: [] for path in sources}
    for row in rows:
        if row["source_path"] not in rows_by_source:
            raise SeedInventoryBlocked("seed row source is not registered")
        rows_by_source[row["source_path"]].append(row)
    for path, source in sources.items():
        if source["row_count"] != len(rows_by_source[path]) or any(
            row["document_index"] >= source["document_count"]
            for row in rows_by_source[path]
        ):
            raise SeedInventoryBlocked("seed source row counts mismatch")
    if _nonnegative_integer(inventory["row_count"], "inventory row count") != len(rows):
        raise SeedInventoryBlocked("seed inventory row count mismatch")

    excluded = sorted({row["seed"] for row in rows})
    raw_excluded = inventory["excluded_seeds"]
    if not isinstance(raw_excluded, list):
        raise SeedInventoryBlocked("excluded seeds must be a list")
    normalized_excluded = [
        _nonnegative_integer(seed, "excluded seed") for seed in raw_excluded
    ]
    if normalized_excluded != excluded:
        raise SeedInventoryBlocked("seed inventory exclusion union mismatch")
    if _nonnegative_integer(
        inventory["excluded_seed_count"], "excluded seed count"
    ) != len(excluded):
        raise SeedInventoryBlocked("seed inventory exclusion count mismatch")
    if _digest(
        inventory["excluded_seeds_sha256"], "excluded seeds digest"
    ) != _canonical_sha256(excluded):
        raise SeedInventoryBlocked("excluded seeds digest mismatch")

    if inventory["cohort_counts"] != _ROLE_COUNTS:
        raise SeedInventoryBlocked("inventory cohort counts mismatch")
    raw_cohorts = _mapping(inventory["cohorts"], "inventory cohorts")
    _require_exact_keys(raw_cohorts, set(_ROLE_ORDER), "inventory cohorts")
    cohorts: dict[str, list[int]] = {}
    for role in _ROLE_ORDER:
        raw_values = raw_cohorts[role]
        if not isinstance(raw_values, list):
            raise SeedInventoryBlocked(f"{role} cohort must be a list")
        values = [_nonnegative_integer(seed, f"{role} seed") for seed in raw_values]
        if len(values) != _ROLE_COUNTS[role] or values != sorted(set(values)):
            raise SeedInventoryBlocked(f"{role} cohort is not canonical")
        if set(values) & set(excluded):
            raise SeedInventoryBlocked(f"{role} cohort collides with history")
        cohorts[role] = values
    if len(set().union(*(set(cohorts[role]) for role in _ROLE_ORDER))) != sum(
        _ROLE_COUNTS.values()
    ):
        raise SeedInventoryBlocked("inventory cohorts are not pairwise disjoint")
    _verify_materialized_cohorts(cohorts, excluded)

    role_sha256 = _mapping(inventory["role_sha256"], "role digests")
    _require_exact_keys(role_sha256, set(_ROLE_ORDER), "role digests")
    expected_role_sha256 = {
        role: _canonical_sha256(cohorts[role]) for role in _ROLE_ORDER
    }
    if role_sha256 != expected_role_sha256:
        raise SeedInventoryBlocked("inventory role digest mismatch")

    normalized = {
        **inventory,
        "authority_evidence": authority_evidence,
        "cohorts": cohorts,
        "excluded_seeds": excluded,
        "role_sha256": role_sha256,
        "rows": rows,
        "source_registry": registry,
    }
    body = {key: value for key, value in normalized.items() if key != "inventory_sha256"}
    if _digest(normalized["inventory_sha256"], "inventory digest") != _canonical_sha256(body):
        raise SeedInventoryBlocked("seed inventory digest mismatch")
    return normalized


def _inventory_paths(request: Mapping[str, Any]) -> tuple[Path, Path]:
    output = Path(request["output_root"]).resolve()
    staging = output.with_name(
        f".{output.name}.{request['request_sha256']}.staging"
    )
    return output, staging


def _require_unmaterialized(request: Mapping[str, Any]) -> None:
    output, staging = _inventory_paths(request)
    if output.exists():
        raise SeedInventoryBlocked("inventory output already exists")
    if staging.exists():
        raise SeedInventoryBlocked("inventory staging already exists")


def _publish_inventory_once(
    request: Mapping[str, Any], artifact: Mapping[str, Any]
) -> None:
    output, staging = _inventory_paths(request)
    _require_unmaterialized(request)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        staging.mkdir()
        path = staging / INVENTORY_FILENAME
        with path.open("xb") as handle:
            handle.write(canonical_json_bytes(artifact))
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(staging, output)
    except FileExistsError as exc:
        raise SeedInventoryBlocked("inventory publication target already exists") from exc
    except OSError as exc:
        raise SeedInventoryBlocked(f"inventory publication failed: {exc}") from exc


def build_inventory(
    *,
    repo_root: Path | str,
    request: object,
    authorization: object,
    approval_record: object,
    launch_observation: object,
) -> dict[str, Any]:
    """Build and publish one authorized inventory at the request-bound root."""
    root = Path(repo_root).resolve()
    (
        normalized_request,
        normalized_authorization,
        normalized_approval,
        normalized_launch,
        source_inventory,
    ) = _validate_inventory_authority(
        repo_root=root,
        request=request,
        authorization=authorization,
        approval_record=approval_record,
        launch_observation=launch_observation,
    )
    _require_unmaterialized(normalized_request)
    registry, rows, excluded = _build_source_registry_and_rows(
        root,
        repository_commit=normalized_request["source_commit"],
        output_root=normalized_request["output_root"],
    )
    cohorts = _select_fresh_cohorts(excluded)
    authority_evidence = _build_authority_evidence(
        request=normalized_request,
        authorization=normalized_authorization,
        approval_record=normalized_approval,
        build_launch_observation=normalized_launch,
        source_inventory=source_inventory,
    )
    body = _inventory_body(
        request=normalized_request,
        authorization=normalized_authorization,
        authority_evidence=authority_evidence,
        launch_observation=normalized_launch,
        source_registry=registry,
        rows=rows,
        excluded_seeds=excluded,
        cohorts=cohorts,
    )
    artifact = validate_inventory(
        {**body, "inventory_sha256": _canonical_sha256(body)}
    )
    _publish_inventory_once(normalized_request, artifact)
    return artifact


def _read_materialized_inventory(request: Mapping[str, Any]) -> dict[str, Any]:
    output, staging = _inventory_paths(request)
    if staging.exists():
        raise SeedInventoryBlocked("inventory staging is ambiguous")
    if not output.is_dir() or output.is_symlink():
        raise SeedInventoryBlocked("materialized inventory output is missing")
    entries = sorted(path.name for path in output.iterdir())
    if entries != [INVENTORY_FILENAME]:
        raise SeedInventoryBlocked("materialized inventory output is not closed")
    path = output / INVENTORY_FILENAME
    if not path.is_file() or path.is_symlink():
        raise SeedInventoryBlocked("materialized inventory file is invalid")
    return validate_inventory(_strict_json(path.read_bytes(), INVENTORY_FILENAME))


def verify_inventory(
    *,
    repo_root: Path | str,
    request: object,
    authorization: object,
    approval_record: object,
    launch_observation: object,
) -> dict[str, Any]:
    """Read and reconstruct an inventory without selecting or publishing cohorts."""
    root = Path(repo_root).resolve()
    (
        normalized_request,
        normalized_authorization,
        _normalized_approval,
        _normalized_launch,
        _source_inventory,
    ) = (
        _validate_inventory_authority(
            repo_root=root,
            request=request,
            authorization=authorization,
            approval_record=approval_record,
            launch_observation=launch_observation,
        )
    )
    materialized = _read_materialized_inventory(normalized_request)
    build_evidence = materialized["authority_evidence"]
    if (
        materialized["request_sha256"] != normalized_request["request_sha256"]
        or materialized["authorization_sha256"]
        != normalized_authorization["authorization_sha256"]
        or materialized["repository_commit"] != normalized_request["source_commit"]
        or materialized["source_inventory_sha256"]
        != normalized_request["source_inventory_sha256"]
        or materialized["launch_authority_sha256"]
        != build_evidence["build_launch_observation"]["observation_sha256"]
    ):
        raise SeedInventoryBlocked("materialized inventory authority binding mismatch")

    registry, rows, excluded = _build_source_registry_and_rows(
        root,
        repository_commit=normalized_request["source_commit"],
        output_root=normalized_request["output_root"],
    )
    if canonical_json_bytes(materialized["source_registry"]) != canonical_json_bytes(
        registry
    ):
        raise SeedInventoryBlocked("inventory source registry reconstruction mismatch")
    if materialized["rows"] != rows or materialized["excluded_seeds"] != excluded:
        raise SeedInventoryBlocked("inventory historical reconstruction mismatch")
    _verify_materialized_cohorts(materialized["cohorts"], excluded)
    return materialized


def _load_json_file(path: str, label: str) -> dict[str, Any]:
    value = _strict_json(Path(path).read_bytes(), label)
    return _mapping(value, label)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("build-inventory", "verify-inventory"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("--repo-root", required=True)
        command_parser.add_argument("--request", required=True)
        command_parser.add_argument("--authorization", required=True)
        command_parser.add_argument("--approval-record", required=True)
        command_parser.add_argument("--launch-observation", required=True)
    args = parser.parse_args(argv)
    request = _load_json_file(args.request, "inventory request")
    authorization = _load_json_file(args.authorization, "inventory authorization")
    approval_record = _load_json_file(args.approval_record, "inventory approval record")
    launch_observation = _load_json_file(
        args.launch_observation,
        "inventory launch observation",
    )
    operation = build_inventory if args.command == "build-inventory" else verify_inventory
    try:
        artifact = operation(
            repo_root=args.repo_root,
            request=request,
            authorization=authorization,
            approval_record=approval_record,
            launch_observation=launch_observation,
        )
    except (OSError, SeedInventoryBlocked) as exc:
        parser.error(str(exc))
    sys.stdout.buffer.write(canonical_json_bytes(artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CANARY_SEED_COUNT",
    "CANONICAL_SEARCH_START",
    "HOLDOUT_SEED_COUNT",
    "INVENTORY_FILENAME",
    "INVENTORY_AUTHORITY_EVIDENCE_SCHEMA_VERSION",
    "SEED_INVENTORY_SCHEMA_VERSION",
    "SOURCE_REGISTRY_SCHEMA_VERSION",
    "SeedInventoryBlocked",
    "TRAINING_SEED_COUNT",
    "build_inventory",
    "canonical_json_bytes",
    "validate_inventory",
    "verify_inventory",
]
