"""Audit Current-relevant event semantics from bound source files only."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


INPUT_SCHEMA_VERSION = "noncombat-event-semantics-coverage-audit-input-v1"
INVENTORY_SCHEMA_VERSION = "noncombat-event-semantics-coverage-inventory-v1"
METRICS_SCHEMA_VERSION = "noncombat-event-semantics-coverage-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-event-semantics-coverage-manifest-v1"
IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_event_semantics_coverage_audit.py",
)
SIMULATOR_SOURCE_PATHS = {
    "display_labels": "src/sim/ConsoleSimulator.cpp",
    "event_identities": "include/constants/Events.h",
    "event_save_ids": "include/constants/SaveFileMappings.h",
    "execution": "src/game/GameContext.cpp",
    "legal_actions": "src/sim/search/GameAction.cpp",
}
CANONICAL_ARTIFACT_NAMES = (
    "configuration.json",
    "event_inventory.json",
    "metrics.json",
    "report.md",
    "artifact_manifest.json",
)
ALL_FALSE_AUTHORITY = {
    "formal_rl_readiness_authorized": False,
    "gameplay_authorized": False,
    "model_fitting_authorized": False,
    "promotion_authorized": False,
    "resolver_extension_authorized": False,
    "reward_authorized": False,
    "seed_use_authorized": False,
    "simulator_execution_authorized": False,
    "training_authorized": False,
}


class AuditBlocked(ValueError):
    """Raised when static coverage evidence cannot remain exact."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path | str) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AuditBlocked("mapping_required", label)
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AuditBlocked("sequence_required", label)
    return list(value)


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise AuditBlocked(
            "object_keys_mismatch",
            {"actual": sorted(actual), "expected": sorted(expected), "label": label},
        )


def _is_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditBlocked("duplicate_json_key", key)
        result[key] = value
    return result


def _validated_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AuditBlocked("relative_path_required", label)
    normalized = value.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts or normalized != pure.as_posix():
        raise AuditBlocked("invalid_relative_path", {"label": label, "path": value})
    return normalized


def _validated_binding(value: object, label: str) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    binding["path"] = _validated_relative_path(binding["path"], f"{label}.path")
    if not _is_hex(binding["sha256"], 64):
        raise AuditBlocked("invalid_binding_sha256", label)
    if (
        isinstance(binding["size_bytes"], bool)
        or not isinstance(binding["size_bytes"], int)
        or binding["size_bytes"] <= 0
    ):
        raise AuditBlocked("invalid_binding_size", label)
    return binding


def _validated_events(value: object) -> list[dict[str, Any]]:
    events = []
    canonical_ids: set[str] = set()
    upstream_enums: set[str] = set()
    aliases: set[str] = set()
    for index, raw in enumerate(_sequence(value, "events")):
        event = _mapping(raw, f"events[{index}]")
        _require_keys(
            event,
            {"aliases", "canonical_id", "upstream_enum"},
            f"events[{index}]",
        )
        canonical_id = event["canonical_id"]
        upstream_enum = event["upstream_enum"]
        if not isinstance(canonical_id, str) or not canonical_id:
            raise AuditBlocked("event_registry_canonical_id_invalid", index)
        if canonical_id in canonical_ids:
            raise AuditBlocked("event_registry_canonical_id_duplicate", canonical_id)
        canonical_ids.add(canonical_id)
        if not isinstance(upstream_enum, str) or not re.fullmatch(
            r"[A-Z][A-Z0-9_]*", upstream_enum
        ):
            raise AuditBlocked("event_registry_upstream_enum_invalid", upstream_enum)
        if upstream_enum in upstream_enums:
            raise AuditBlocked(
                "event_registry_upstream_enum_duplicate", upstream_enum
            )
        upstream_enums.add(upstream_enum)
        event_aliases = _sequence(event["aliases"], f"events[{index}].aliases")
        if not event_aliases or any(
            not isinstance(alias, str) or not alias for alias in event_aliases
        ):
            raise AuditBlocked("event_registry_alias_invalid", canonical_id)
        if event_aliases != sorted(set(event_aliases)):
            raise AuditBlocked("event_registry_alias_order_or_duplicate", canonical_id)
        for alias in event_aliases:
            if alias in aliases:
                raise AuditBlocked("event_registry_alias_duplicate", alias)
            aliases.add(alias)
        events.append(
            {
                "aliases": event_aliases,
                "canonical_id": canonical_id,
                "upstream_enum": upstream_enum,
            }
        )
    if not events or [event["canonical_id"] for event in events] != sorted(
        canonical_ids
    ):
        raise AuditBlocked("event_registry_canonical_order_invalid")
    return events


def validate_registration(value: object) -> dict[str, Any]:
    registration = _mapping(copy.deepcopy(value), "registration")
    _require_keys(
        registration,
        {
            "authority",
            "current",
            "events",
            "implementation",
            "output",
            "schema_version",
            "simulator",
        },
        "registration",
    )
    if registration["schema_version"] != INPUT_SCHEMA_VERSION:
        raise AuditBlocked("registration_schema_mismatch")
    authority = _mapping(registration["authority"], "authority")
    if authority != ALL_FALSE_AUTHORITY:
        raise AuditBlocked("authority_must_be_all_false", authority)
    registration["authority"] = authority

    implementation = _mapping(registration["implementation"], "implementation")
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "implementation",
    )
    if not _is_hex(implementation["commit"], 40):
        raise AuditBlocked("implementation_commit_invalid")
    if implementation["source_files"] != list(IMPLEMENTATION_SOURCE_FILES):
        raise AuditBlocked("implementation_source_files_mismatch")
    if not _is_hex(implementation["source_sha256"], 64):
        raise AuditBlocked("implementation_source_sha256_invalid")
    registration["implementation"] = implementation

    current = _mapping(registration["current"], "current")
    _require_keys(
        current,
        {
            "class_name",
            "function_name",
            "repository_commit",
            "source",
        },
        "current",
    )
    for field in ("class_name", "function_name"):
        if not isinstance(current[field], str) or not current[field]:
            raise AuditBlocked("current_target_invalid", field)
    if not _is_hex(current["repository_commit"], 40):
        raise AuditBlocked("current_repository_commit_invalid")
    current["source"] = _validated_binding(current["source"], "current.source")
    registration["current"] = current

    simulator = _mapping(registration["simulator"], "simulator")
    _require_keys(
        simulator,
        {
            "dirty",
            "parent_commit",
            "root",
            "source_file_count",
            "source_files",
            "source_sha256",
            "submodules",
        },
        "simulator",
    )
    if not isinstance(simulator["root"], str) or not Path(
        simulator["root"]
    ).is_absolute():
        raise AuditBlocked("simulator_root_invalid")
    if not _is_hex(simulator["parent_commit"], 40):
        raise AuditBlocked("simulator_parent_commit_invalid")
    if not isinstance(simulator["dirty"], bool):
        raise AuditBlocked("simulator_dirty_invalid")
    if not _is_hex(simulator["source_sha256"], 64):
        raise AuditBlocked("simulator_source_sha256_invalid")
    if (
        isinstance(simulator["source_file_count"], bool)
        or not isinstance(simulator["source_file_count"], int)
        or simulator["source_file_count"] <= 0
    ):
        raise AuditBlocked("simulator_source_file_count_invalid")
    submodules = _mapping(simulator["submodules"], "simulator.submodules")
    _require_keys(submodules, {"json", "pybind11"}, "simulator.submodules")
    if any(not _is_hex(commit, 40) for commit in submodules.values()):
        raise AuditBlocked("simulator_submodule_commit_invalid")
    simulator["submodules"] = submodules
    source_files = _mapping(simulator["source_files"], "simulator.source_files")
    if set(source_files) != set(SIMULATOR_SOURCE_PATHS):
        raise AuditBlocked("simulator_source_file_keys_mismatch")
    normalized_sources = {}
    for name, expected_path in SIMULATOR_SOURCE_PATHS.items():
        binding = _validated_binding(
            source_files[name], f"simulator.source_files.{name}"
        )
        if binding["path"] != expected_path:
            raise AuditBlocked(
                "simulator_source_path_mismatch",
                {"actual": binding["path"], "expected": expected_path, "name": name},
            )
        normalized_sources[name] = binding
    simulator["source_files"] = normalized_sources
    registration["simulator"] = simulator

    registration["events"] = _validated_events(registration["events"])
    output = _mapping(registration["output"], "output")
    _require_keys(output, {"artifact_names", "directory"}, "output")
    output["directory"] = _validated_relative_path(
        output["directory"], "output.directory"
    )
    if output["artifact_names"] != list(CANONICAL_ARTIFACT_NAMES):
        raise AuditBlocked("output_artifact_names_mismatch")
    registration["output"] = output
    return registration


def load_registration(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except AuditBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditBlocked("registration_load_failed", str(exc)) from exc
    return validate_registration(value)


def verify_bound_file(
    root: Path | str,
    binding: Mapping[str, Any],
    *,
    repository_relative: bool,
) -> Path:
    base = Path(root).resolve()
    path = (
        (base / str(binding["path"])).resolve()
        if repository_relative
        else Path(str(binding["path"])).resolve()
    )
    if repository_relative:
        try:
            path.relative_to(base)
        except ValueError as exc:
            raise AuditBlocked("bound_file_escapes_root", binding["path"]) from exc
    if not path.is_file():
        raise AuditBlocked("bound_file_missing", str(binding["path"]))
    actual = {
        "path": str(binding["path"]),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
    if actual != dict(binding):
        raise AuditBlocked(
            "bound_file_identity_mismatch",
            {"actual": actual, "registered": dict(binding)},
        )
    return path


def hash_bound_files(repo_root: Path | str, source_files: Sequence[str]) -> str:
    root = Path(repo_root).resolve()
    digest = hashlib.sha256()
    for relative in source_files:
        path = (root / relative).resolve()
        try:
            canonical_relative = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise AuditBlocked("implementation_source_escapes_repository", relative) from exc
        if not path.is_file():
            raise AuditBlocked("implementation_source_missing", relative)
        relative_bytes = canonical_relative.encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative_bytes).to_bytes(4, "big"))
        digest.update(relative_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def hash_simulator_sources(repo_root: Path | str) -> tuple[str, int]:
    root = Path(repo_root).resolve()
    files = sorted(
        (
            path
            for source_root in (root / "include", root / "src")
            for path in source_root.rglob("*")
            if path.is_file()
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest(), len(files)


def _git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AuditBlocked("git_identity_query_failed", list(args)) from exc
    return completed.stdout.strip()


def _verify_sources_at_commit(
    repo_root: Path, commit: str, source_files: Sequence[str]
) -> None:
    for relative in source_files:
        try:
            completed = subprocess.run(
                ["git", "show", f"{commit}:{relative}"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise AuditBlocked("source_not_available_at_commit", relative) from exc
        if completed.stdout != (repo_root / relative).read_bytes():
            raise AuditBlocked("source_differs_from_registered_commit", relative)


def verify_registration_identity(
    registration: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    implementation = registration["implementation"]
    actual_implementation_hash = hash_bound_files(
        root, implementation["source_files"]
    )
    if actual_implementation_hash != implementation["source_sha256"]:
        raise AuditBlocked("implementation_source_hash_mismatch")
    _verify_sources_at_commit(
        root, implementation["commit"], implementation["source_files"]
    )

    current = registration["current"]
    current_path = verify_bound_file(root, current["source"], repository_relative=True)
    _verify_sources_at_commit(
        root, current["repository_commit"], [current["source"]["path"]]
    )

    simulator = registration["simulator"]
    simulator_root = Path(simulator["root"]).resolve()
    if not simulator_root.is_dir():
        raise AuditBlocked("simulator_root_missing", str(simulator_root))
    actual_parent = _git(simulator_root, "rev-parse", "HEAD")
    if actual_parent != simulator["parent_commit"]:
        raise AuditBlocked(
            "simulator_parent_commit_mismatch",
            {"actual": actual_parent, "registered": simulator["parent_commit"]},
        )
    actual_dirty = bool(_git(simulator_root, "status", "--porcelain"))
    if actual_dirty != simulator["dirty"]:
        raise AuditBlocked(
            "simulator_dirty_state_mismatch",
            {"actual": actual_dirty, "registered": simulator["dirty"]},
        )
    actual_source_hash, actual_source_count = hash_simulator_sources(simulator_root)
    if (
        actual_source_hash != simulator["source_sha256"]
        or actual_source_count != simulator["source_file_count"]
    ):
        raise AuditBlocked(
            "simulator_full_source_identity_mismatch",
            {
                "actual_count": actual_source_count,
                "actual_sha256": actual_source_hash,
                "registered_count": simulator["source_file_count"],
                "registered_sha256": simulator["source_sha256"],
            },
        )
    actual_submodules = {
        name: _git(simulator_root / name, "rev-parse", "HEAD")
        for name in ("json", "pybind11")
    }
    if actual_submodules != simulator["submodules"]:
        raise AuditBlocked(
            "simulator_submodule_identity_mismatch",
            {"actual": actual_submodules, "registered": simulator["submodules"]},
        )
    simulator_paths = {
        name: verify_bound_file(
            simulator_root, binding, repository_relative=True
        )
        for name, binding in simulator["source_files"].items()
    }
    return {
        "current_source": current_path,
        "simulator_root": simulator_root,
        "simulator_sources": simulator_paths,
    }


def _literal_string_set(node: ast.AST, reason: str) -> list[str]:
    if not isinstance(node, (ast.Set, ast.List, ast.Tuple)):
        raise AuditBlocked(reason)
    values = []
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            raise AuditBlocked(reason)
        values.append(element.value)
    if not values or len(values) != len(set(values)):
        raise AuditBlocked(reason)
    return sorted(values)


def _assigned_name(node: ast.stmt, name: str) -> ast.AST | None:
    if isinstance(node, ast.Assign):
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return node.value
    if isinstance(node, ast.AnnAssign):
        if isinstance(node.target, ast.Name) and node.target.id == name:
            return node.value
    return None


def _event_branch_condition(
    node: ast.AST, risky_aliases: Sequence[str]
) -> tuple[str, list[str]]:
    if not (
        isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Name)
        and node.left.id == "event_id"
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.In)
        and len(node.comparators) == 1
    ):
        raise AuditBlocked("current_branch_condition_unrepresentable")
    comparator = node.comparators[0]
    if isinstance(comparator, ast.Name) and comparator.id == "risky_event_ids":
        return "risky_fallback", list(risky_aliases)
    return "explicit", _literal_string_set(
        comparator, "current_branch_aliases_unrepresentable"
    )


def _ast_hash(statements: Sequence[ast.stmt]) -> str:
    normalized = ast.dump(
        ast.Module(body=list(statements), type_ignores=[]),
        annotate_fields=True,
        include_attributes=False,
    ).encode("utf-8")
    return sha256_bytes(normalized)


def parse_current_event_surface(
    source: str, *, class_name: str, function_name: str
) -> dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise AuditBlocked("current_source_syntax_invalid", str(exc)) from exc
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    ]
    if len(classes) != 1:
        raise AuditBlocked("current_class_missing_or_ambiguous", class_name)
    functions = [
        node
        for node in classes[0].body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == function_name
    ]
    if len(functions) != 1:
        raise AuditBlocked("current_function_missing", function_name)
    function = functions[0]
    risky_values = [
        value
        for statement in function.body
        if (value := _assigned_name(statement, "risky_event_ids")) is not None
    ]
    if len(risky_values) != 1:
        raise AuditBlocked("current_risky_set_missing_or_ambiguous")
    risky_aliases = _literal_string_set(
        risky_values[0], "current_risky_aliases_unrepresentable"
    )

    choice_index_seen = False
    chain: ast.If | None = None
    for statement in function.body:
        if _assigned_name(statement, "choice_index") is not None:
            choice_index_seen = True
            continue
        if choice_index_seen and isinstance(statement, ast.If):
            if any(
                isinstance(node, ast.Name) and node.id == "event_id"
                for node in ast.walk(statement.test)
            ):
                chain = statement
                break
    if chain is None:
        raise AuditBlocked("current_primary_event_chain_missing")

    branches = []
    explicit_aliases: set[str] = set()
    risky_seen = False
    current: ast.If | None = chain
    while current is not None:
        kind, aliases = _event_branch_condition(current.test, risky_aliases)
        if kind == "risky_fallback":
            if risky_seen:
                raise AuditBlocked("current_risky_branch_duplicate")
            risky_seen = True
        else:
            duplicates = explicit_aliases.intersection(aliases)
            if duplicates:
                raise AuditBlocked(
                    "current_explicit_alias_duplicate", sorted(duplicates)
                )
            explicit_aliases.update(aliases)
        body_end = max(
            int(getattr(statement, "end_lineno", statement.lineno))
            for statement in current.body
        )
        string_literals = sorted(
            {
                node.value
                for statement in current.body
                for node in ast.walk(statement)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            }
        )
        branches.append(
            {
                "aliases": aliases,
                "ast_sha256": _ast_hash(current.body),
                "branch_order": len(branches),
                "kind": kind,
                "label_sensitive": any(
                    isinstance(node, ast.Name)
                    and node.id == "labels_for_selection"
                    for statement in current.body
                    for node in ast.walk(statement)
                ),
                "line_end": body_end,
                "line_start": current.lineno,
                "string_literals": string_literals,
            }
        )
        if not current.orelse:
            current = None
        elif len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            current = current.orelse[0]
        else:
            raise AuditBlocked("current_branch_else_unrepresentable")
    if not risky_seen:
        raise AuditBlocked("current_risky_branch_missing")
    aliases = sorted(explicit_aliases.union(risky_aliases))
    return {
        "aliases": aliases,
        "ast_sha256": _ast_hash(function.body),
        "branches": branches,
        "class_name": class_name,
        "function_name": function_name,
        "line_end": int(getattr(function, "end_lineno", function.lineno)),
        "line_start": function.lineno,
        "risky_aliases": risky_aliases,
    }


def validate_event_registry(
    registry: object, surface: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    events = _validated_events(registry)
    alias_mapping: dict[str, dict[str, Any]] = {}
    for event in events:
        for alias in event["aliases"]:
            if alias in alias_mapping:
                raise AuditBlocked("event_registry_alias_duplicate", alias)
            alias_mapping[alias] = event
    actual = set(alias_mapping)
    expected = set(surface["aliases"])
    if actual != expected:
        raise AuditBlocked(
            "event_registry_alias_mismatch",
            {"extra": sorted(actual - expected), "missing": sorted(expected - actual)},
        )
    explicit_owner: dict[str, int] = {}
    for branch in surface["branches"]:
        if branch["kind"] != "explicit":
            continue
        for alias in branch["aliases"]:
            canonical_id = alias_mapping[alias]["canonical_id"]
            previous = explicit_owner.setdefault(canonical_id, branch["branch_order"])
            if previous != branch["branch_order"]:
                raise AuditBlocked(
                    "event_registry_canonical_split_across_branches", canonical_id
                )
    return alias_mapping


def _strip_cpp_comments(value: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", "", value, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", without_blocks)


def _line_number(value: str, offset: int) -> int:
    return value.count("\n", 0, offset) + 1


def _cpp_string_literals(block: str, block_offset: int, source: str) -> list[tuple[str, int]]:
    values = []
    for match in re.finditer(r'"(?:\\.|[^"\\])*"', block):
        try:
            decoded = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise AuditBlocked("cpp_string_literal_invalid", match.group(0)) from exc
        values.append((decoded, _line_number(source, block_offset + match.start())))
    return values


def parse_event_identities(
    events_source: str,
    save_source: str,
    *,
    events_path: str = "include/constants/Events.h",
    save_path: str = "include/constants/SaveFileMappings.h",
) -> dict[str, dict[str, Any]]:
    enum_match = re.search(
        r"enum\s+class\s+Event\b[^\{]*\{(?P<body>.*?)\};",
        events_source,
        flags=re.DOTALL,
    )
    if enum_match is None:
        raise AuditBlocked("event_enum_block_missing")
    enum_body = _strip_cpp_comments(enum_match.group("body"))
    enum_names = []
    enum_lines = {}
    body_offset = enum_match.start("body")
    for match in re.finditer(r"\b([A-Z][A-Z0-9_]*)\b\s*(?:=\s*[^,]+)?\s*(?:,|$)", enum_body):
        name = match.group(1)
        if name in enum_lines:
            raise AuditBlocked("event_enum_duplicate", name)
        enum_names.append(name)
        enum_lines[name] = _line_number(events_source, body_offset + match.start())
    if not enum_names:
        raise AuditBlocked("event_enum_empty")

    def parse_array(name: str) -> tuple[list[str], list[int]]:
        match = re.search(
            rf"\b{name}\s*\[\s*\]\s*=\s*\{{(?P<body>.*?)\}}\s*;",
            events_source,
            flags=re.DOTALL,
        )
        if match is None:
            raise AuditBlocked("event_identity_array_missing", name)
        literals = _cpp_string_literals(
            match.group("body"), match.start("body"), events_source
        )
        return [value for value, _ in literals], [line for _, line in literals]

    event_ids, event_id_lines = parse_array("eventIdStrings")
    game_names, game_name_lines = parse_array("eventGameNames")
    if len(event_ids) != len(enum_names) or len(game_names) != len(enum_names):
        raise AuditBlocked(
            "event_identity_array_length_mismatch",
            {
                "enum": len(enum_names),
                "event_ids": len(event_ids),
                "game_names": len(game_names),
            },
        )

    save_match = re.search(
        r"NLOHMANN_JSON_SERIALIZE_ENUM\s*\(\s*Event\s*,\s*\{(?P<body>.*?)\}\s*\)",
        save_source,
        flags=re.DOTALL,
    )
    if save_match is None:
        raise AuditBlocked("event_save_mapping_missing")
    save_ids: dict[str, str | None] = {}
    save_lines: dict[str, int] = {}
    for match in re.finditer(
        r"\{\s*Event::([A-Z][A-Z0-9_]*)\s*,\s*(nullptr|\"(?:\\.|[^\"\\])*\")\s*\}",
        save_match.group("body"),
    ):
        enum_name = match.group(1)
        if enum_name in save_ids:
            raise AuditBlocked("event_save_mapping_duplicate", enum_name)
        raw = match.group(2)
        save_ids[enum_name] = None if raw == "nullptr" else json.loads(raw)
        save_lines[enum_name] = _line_number(
            save_source, save_match.start("body") + match.start()
        )

    result = {}
    for index, enum_name in enumerate(enum_names):
        result[enum_name] = {
            "event_game_name": game_names[index],
            "event_id": event_ids[index],
            "save_id": save_ids.get(enum_name),
            "source_refs": {
                "enum": {"line": enum_lines[enum_name], "path": events_path},
                "event_game_name": {
                    "line": game_name_lines[index],
                    "path": events_path,
                },
                "event_id": {"line": event_id_lines[index], "path": events_path},
                "save_id": (
                    {"line": save_lines[enum_name], "path": save_path}
                    if enum_name in save_lines
                    else None
                ),
            },
        }
    return result


def _find_matching_cpp_brace(source: str, opening: int) -> int:
    depth = 0
    state = "code"
    index = opening
    while index < len(source):
        character = source[index]
        next_character = source[index + 1] if index + 1 < len(source) else ""
        if state == "code":
            if character == "/" and next_character == "/":
                state = "line_comment"
                index += 2
                continue
            if character == "/" and next_character == "*":
                state = "block_comment"
                index += 2
                continue
            if character == '"':
                state = "string"
            elif character == "'":
                state = "char"
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    return index
        elif state == "line_comment":
            if character == "\n":
                state = "code"
        elif state == "block_comment":
            if character == "*" and next_character == "/":
                state = "code"
                index += 2
                continue
        elif state in {"string", "char"}:
            if character == "\\":
                index += 2
                continue
            if (state == "string" and character == '"') or (
                state == "char" and character == "'"
            ):
                state = "code"
        index += 1
    raise AuditBlocked("cpp_function_brace_unclosed")


def _cpp_line_is_trivia(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("//")


def index_cpp_event_cases(
    source: str, *, signature: str, source_path: str
) -> dict[str, dict[str, Any]]:
    occurrences = [match.start() for match in re.finditer(re.escape(signature), source)]
    if len(occurrences) != 1:
        raise AuditBlocked(
            "cpp_function_missing_or_ambiguous",
            {"count": len(occurrences), "signature": signature},
        )
    signature_start = occurrences[0]
    opening = source.find("{", signature_start + len(signature))
    if opening < 0:
        raise AuditBlocked("cpp_function_opening_brace_missing", signature)
    closing = _find_matching_cpp_brace(source, opening)
    function_source = source[signature_start : closing + 1]
    base_line = _line_number(source, signature_start)
    lines = function_source.splitlines()
    labels = []
    for line_index, line in enumerate(lines):
        match = re.match(
            r"^\s*case\s+Event::([A-Z][A-Z0-9_]*)\s*:\s*(.*)$", line
        )
        if match:
            labels.append(
                {
                    "enum": match.group(1),
                    "line_index": line_index,
                    "tail": match.group(2).strip(),
                }
            )
    if not labels:
        raise AuditBlocked("cpp_event_cases_missing", signature)
    seen = set()
    for label in labels:
        if label["enum"] in seen:
            raise AuditBlocked("cpp_event_case_duplicate", label["enum"])
        seen.add(label["enum"])

    groups: list[list[dict[str, Any]]] = []
    for label in labels:
        if not groups:
            groups.append([label])
            continue
        previous = groups[-1][-1]
        between = lines[previous["line_index"] + 1 : label["line_index"]]
        previous_has_body = bool(
            previous["tail"] and not previous["tail"].startswith("//")
        )
        if not previous_has_body and all(_cpp_line_is_trivia(line) for line in between):
            groups[-1].append(label)
        else:
            groups.append([label])

    indexed: dict[str, dict[str, Any]] = {}
    for group_index, group in enumerate(groups):
        start_index = group[0]["line_index"]
        end_index = (
            groups[group_index + 1][0]["line_index"] - 1
            if group_index + 1 < len(groups)
            else len(lines) - 2
        )
        text = "\n".join(lines[start_index : end_index + 1]) + "\n"
        value = {
            "case_group": [entry["enum"] for entry in group],
            "line_end": base_line + end_index,
            "line_start": base_line + start_index,
            "source_path": source_path,
            "text": text,
        }
        for entry in group:
            indexed[entry["enum"]] = value
    return indexed


def _case_summary_base(case: Mapping[str, Any]) -> dict[str, Any]:
    text = str(case["text"])
    return {
        "case_group": list(case["case_group"]),
        "conditional": bool(re.search(r"\b(?:if|switch|for)\s*\(", text)),
        "line_end": int(case["line_end"]),
        "line_start": int(case["line_start"]),
        "phase_sensitive": "eventData" in text,
        "source_path": str(case["source_path"]),
        "source_sha256": sha256_bytes(text.encode("utf-8")),
    }


def summarize_legal_case(case: Mapping[str, Any]) -> dict[str, Any]:
    summary = _case_summary_base(case)
    expressions = [
        match.group(1).strip()
        for match in re.finditer(r"\breturn\s+([^;]+);", str(case["text"]))
    ]
    literal_masks = []
    dynamic_expressions = []
    legal_indices: set[int] = set()
    for expression in expressions:
        if re.fullmatch(r"(?:0[xX][0-9A-Fa-f]+|0[bB][01]+|\d+)", expression):
            mask = int(expression, 0)
            literal_masks.append(mask)
            bit = 0
            value = mask
            while value:
                if value & 1:
                    legal_indices.add(bit)
                value >>= 1
                bit += 1
        else:
            dynamic_expressions.append(expression)
    summary.update(
        {
            "dynamic_return_expressions": sorted(set(dynamic_expressions)),
            "legal_indices": sorted(legal_indices),
            "literal_masks": sorted(set(literal_masks)),
            "return_expressions": expressions,
        }
    )
    return summary


def summarize_display_case(case: Mapping[str, Any]) -> dict[str, Any]:
    summary = _case_summary_base(case)
    entries = set()
    for literal, _ in _cpp_string_literals(str(case["text"]), 0, str(case["text"])):
        match = re.match(r"\s*(\d+)\s*:\s*(?:\[([^\]]+)\])?\s*(.*)", literal)
        if match is None:
            continue
        label = match.group(2) or match.group(3).strip()
        entries.add((int(match.group(1)), label))
    display_entries = [
        {"index": index, "label": label}
        for index, label in sorted(entries, key=lambda item: (item[0], item[1]))
    ]
    summary.update(
        {
            "display_entries": display_entries,
            "display_indices": sorted({entry["index"] for entry in display_entries}),
        }
    )
    return summary


def summarize_execution_case(case: Mapping[str, Any]) -> dict[str, Any]:
    summary = _case_summary_base(case)
    effect_indices = sorted(
        {
            int(match.group(1))
            for match in re.finditer(r"\bcase\s+(\d+)\s*:", str(case["text"]))
        }
    )
    summary["effect_indices"] = effect_indices
    return summary


def build_event_inventory(
    surface: Mapping[str, Any],
    alias_mapping: Mapping[str, Mapping[str, Any]],
    upstream: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    events_by_id: dict[str, dict[str, Any]] = {}
    for event in alias_mapping.values():
        events_by_id[event["canonical_id"]] = dict(event)
    rows = []
    risky_aliases = set(surface["risky_aliases"])
    for canonical_id in sorted(events_by_id):
        event = events_by_id[canonical_id]
        aliases = set(event["aliases"])
        matching_explicit = [
            branch
            for branch in surface["branches"]
            if branch["kind"] == "explicit"
            and aliases.intersection(branch["aliases"])
        ]
        if len(matching_explicit) > 1:
            raise AuditBlocked(
                "event_registry_canonical_split_across_branches", canonical_id
            )
        if matching_explicit:
            branch = matching_explicit[0]
        else:
            branch = next(
                candidate
                for candidate in surface["branches"]
                if candidate["kind"] == "risky_fallback"
            )
        enum_name = event["upstream_enum"]
        identity = upstream["identities"].get(enum_name)
        legal = upstream["legal"].get(enum_name)
        display = upstream["display"].get(enum_name)
        execution = upstream["execution"].get(enum_name)
        blockers = []
        if identity is None or identity.get("save_id") is None:
            blockers.append("event_identity_missing")
        if legal is None:
            blockers.append("legal_action_case_missing")
        if display is None:
            blockers.append("display_label_case_missing")
        if execution is None:
            blockers.append("execution_case_missing")
        if legal is not None:
            blockers.extend(
                f"legal_return_dynamic:{expression}"
                for expression in legal["dynamic_return_expressions"]
            )
        if legal is not None and display is not None:
            missing_indices = sorted(
                set(legal["legal_indices"]) - set(display["display_indices"])
            )
            blockers.extend(
                f"display_indices_missing:{index}" for index in missing_indices
            )
        rows.append(
            {
                "aliases": event["aliases"],
                "blockers": sorted(blockers),
                "canonical_id": canonical_id,
                "current_branch": dict(branch),
                "display_labels": display,
                "event_identity": identity,
                "execution": execution,
                "legal_actions": legal,
                "resolver_ready": False,
                "risky_aliases": sorted(aliases.intersection(risky_aliases)),
                "status": "source_complete" if not blockers else "source_partial",
                "upstream_enum": enum_name,
            }
        )
    covered_aliases = {
        alias for row in rows for alias in row["aliases"]
    }
    if covered_aliases != set(surface["aliases"]):
        raise AuditBlocked("inventory_alias_reconciliation_failed")
    return rows


def _report_markdown(rows: Sequence[Mapping[str, Any]]) -> str:
    counts = Counter(str(row["status"]) for row in rows)
    lines = [
        "# Current Event Semantics Source Coverage Audit",
        "",
        "This is read-only source coverage evidence. It is not resolver readiness, policy quality, simulator compatibility, or training authority.",
        "",
        "## Summary",
        "",
        f"- Canonical Current events: {len(rows)}",
        f"- Source-complete: {counts['source_complete']}",
        f"- Source-partial: {counts['source_partial']}",
        "- Resolver ready: false",
        "",
        "## Inventory",
        "",
        "| Current event | Upstream enum | Branch | Label-sensitive | Legal indices | Display indices | Phase-sensitive | Status | Blockers |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        legal = row["legal_actions"] or {}
        display = row["display_labels"] or {}
        phase_sensitive = any(
            bool((row[key] or {}).get("phase_sensitive"))
            for key in ("legal_actions", "display_labels", "execution")
        )
        blockers = ", ".join(row["blockers"]) or "none"
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['canonical_id']}`",
                    f"`{row['upstream_enum']}`",
                    f"`{row['current_branch']['kind']}`",
                    str(row["current_branch"]["label_sensitive"]).lower(),
                    ", ".join(str(value) for value in legal.get("legal_indices", []))
                    or "none",
                    ", ".join(
                        str(value) for value in display.get("display_indices", [])
                    )
                    or "none",
                    str(phase_sensitive).lower(),
                    f"`{row['status']}`",
                    blockers,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Authority",
            "",
            *[
                f"- `{name}`: `{str(value).lower()}`"
                for name, value in sorted(ALL_FALSE_AUTHORITY.items())
            ],
            "",
            "A separate reviewed adapter-contract change is required before resolver extension or another compatibility evaluation.",
            "",
        ]
    )
    return "\n".join(lines)


def build_artifacts(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, bytes]:
    normalized_registration = validate_registration(registration)
    statuses = Counter(str(row["status"]) for row in rows)
    alias_count = len({alias for row in rows for alias in row["aliases"]})
    metrics = {
        "alias_count": alias_count,
        "authority": dict(ALL_FALSE_AUTHORITY),
        "event_count": len(rows),
        "label_sensitive_event_count": sum(
            bool(row["current_branch"]["label_sensitive"]) for row in rows
        ),
        "registration_sha256": registration_sha256,
        "resolver_ready": False,
        "schema_version": METRICS_SCHEMA_VERSION,
        "status_counts": dict(sorted(statuses.items())),
        "unaccounted_current_alias_count": 0,
    }
    payloads = {
        "configuration.json": canonical_json_bytes(
            {
                "registration": normalized_registration,
                "registration_sha256": registration_sha256,
                "schema_version": INPUT_SCHEMA_VERSION,
            }
        ),
        "event_inventory.json": canonical_json_bytes(
            {"rows": list(rows), "schema_version": INVENTORY_SCHEMA_VERSION}
        ),
        "metrics.json": canonical_json_bytes(metrics),
        "report.md": _report_markdown(rows).encode("utf-8"),
    }
    manifest = {
        "artifact_hashes": {
            name: sha256_bytes(data) for name, data in sorted(payloads.items())
        },
        "authority": dict(ALL_FALSE_AUTHORITY),
        "event_count": len(rows),
        "registration_sha256": registration_sha256,
        "resolver_ready": False,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "status_counts": dict(sorted(statuses.items())),
    }
    payloads["artifact_manifest.json"] = canonical_json_bytes(manifest)
    return {name: payloads[name] for name in CANONICAL_ARTIFACT_NAMES}


def write_or_verify_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    recompute: bool,
) -> None:
    directory = Path(output_dir)
    expected_names = set(CANONICAL_ARTIFACT_NAMES)
    if set(artifacts) != expected_names:
        raise AuditBlocked("artifact_name_set_invalid")
    actual_names = (
        {path.name for path in directory.iterdir() if path.is_file()}
        if directory.is_dir()
        else set()
    )
    if recompute:
        if actual_names != expected_names:
            raise AuditBlocked(
                "artifact_recompute_mismatch",
                {"actual": sorted(actual_names), "expected": sorted(expected_names)},
            )
        for name, expected in artifacts.items():
            if (directory / name).read_bytes() != expected:
                raise AuditBlocked("artifact_recompute_mismatch", name)
        return
    if actual_names:
        raise AuditBlocked("output_directory_not_empty", str(directory))
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in artifacts.items():
        temporary = directory / f".{name}.tmp"
        temporary.write_bytes(data)
        temporary.replace(directory / name)


def run_audit(
    *,
    registration_path: Path | str,
    repo_root: Path | str,
    recompute: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    input_path = Path(registration_path).resolve()
    registration = load_registration(input_path)
    identities = verify_registration_identity(registration, root)
    current_source = identities["current_source"].read_text(encoding="utf-8")
    surface = parse_current_event_surface(
        current_source,
        class_name=registration["current"]["class_name"],
        function_name=registration["current"]["function_name"],
    )
    alias_mapping = validate_event_registry(registration["events"], surface)
    source_paths = identities["simulator_sources"]
    event_identities = parse_event_identities(
        source_paths["event_identities"].read_text(encoding="utf-8"),
        source_paths["event_save_ids"].read_text(encoding="utf-8"),
        events_path=registration["simulator"]["source_files"]["event_identities"][
            "path"
        ],
        save_path=registration["simulator"]["source_files"]["event_save_ids"][
            "path"
        ],
    )
    legal_cases = index_cpp_event_cases(
        source_paths["legal_actions"].read_text(encoding="utf-8"),
        signature="int search::GameAction::getValidEventSelectBits",
        source_path=registration["simulator"]["source_files"]["legal_actions"][
            "path"
        ],
    )
    display_cases = index_cpp_event_cases(
        source_paths["display_labels"].read_text(encoding="utf-8"),
        signature="void ConsoleSimulator::printEventActions",
        source_path=registration["simulator"]["source_files"]["display_labels"][
            "path"
        ],
    )
    execution_cases = index_cpp_event_cases(
        source_paths["execution"].read_text(encoding="utf-8"),
        signature="void GameContext::chooseEventOption",
        source_path=registration["simulator"]["source_files"]["execution"]["path"],
    )
    upstream = {
        "display": {
            name: summarize_display_case(case)
            for name, case in display_cases.items()
        },
        "execution": {
            name: summarize_execution_case(case)
            for name, case in execution_cases.items()
        },
        "identities": event_identities,
        "legal": {
            name: summarize_legal_case(case) for name, case in legal_cases.items()
        },
    }
    rows = build_event_inventory(surface, alias_mapping, upstream)
    artifacts = build_artifacts(
        registration=registration,
        registration_sha256=sha256_file(input_path),
        rows=rows,
    )
    output_dir = (root / registration["output"]["directory"]).resolve()
    try:
        output_dir.relative_to(root)
    except ValueError as exc:
        raise AuditBlocked("output_directory_escapes_repository") from exc
    write_or_verify_artifacts(output_dir, artifacts, recompute=recompute)
    status_counts = Counter(row["status"] for row in rows)
    return {
        "alias_count": len(surface["aliases"]),
        "event_count": len(rows),
        "output_directory": str(output_dir),
        "resolver_ready": False,
        "status_counts": dict(sorted(status_counts.items())),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", required=True)
    parser.add_argument(
        "--repo-root", default=str(Path(__file__).resolve().parents[1])
    )
    parser.add_argument("--recompute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = run_audit(
            registration_path=args.registration,
            repo_root=args.repo_root,
            recompute=args.recompute,
        )
    except AuditBlocked as exc:
        print(
            json.dumps(
                {"detail": exc.detail, "reason": exc.reason, "status": "blocked"},
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
