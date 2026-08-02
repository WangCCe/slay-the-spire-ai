"""Audit the complete source-bound event surface without native execution."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from analysis_scripts.noncombat_event_semantics_coverage_audit import (
    AuditBlocked,
    _mask_cpp_comments,
    _verify_sources_at_commit,
    hash_bound_files,
    hash_simulator_sources,
    index_cpp_event_cases,
    parse_current_event_surface,
    parse_event_identities,
    summarize_display_case,
    summarize_execution_case,
    summarize_legal_case,
    validate_event_registry,
    verify_bound_file,
)
from analysis_scripts.noncombat_simulator_adapter import (
    canonical_json_bytes,
    sha256_file,
)


SUCCESSOR_CONTRACT_SCHEMA_VERSION = (
    "noncombat-reachable-event-option-observation-contract-v1"
)
SUCCESSOR_CONTRACT_ID = "sts_lightspeed_reachable_event_observation_v3"
INPUT_SCHEMA_VERSION = "noncombat-reachable-event-surface-audit-input-v1"
POOL_INVENTORY_SCHEMA_VERSION = "noncombat-reachable-event-pool-inventory-v1"
TARGET_INVENTORY_SCHEMA_VERSION = "noncombat-reachable-event-target-inventory-v1"
CURRENT_PARTITION_SCHEMA_VERSION = "noncombat-reachable-event-current-partition-v1"
METRICS_SCHEMA_VERSION = "noncombat-reachable-event-surface-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-reachable-event-surface-manifest-v1"
DEFAULT_REGISTRATION_PATH = Path(
    "reports/noncombat_reachable_event_surface_audit_20260803_input.json"
)
DEFAULT_OUTPUT_DIRECTORY = Path(
    "reports/noncombat_reachable_event_surface_audit_20260803"
)
CANONICAL_ARTIFACT_NAMES = (
    "artifact_manifest.json",
    "configuration.json",
    "current_partition.json",
    "metrics.json",
    "pool_inventory.json",
    "report.md",
    "successor_contract.json",
    "target_inventory.json",
)
IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_reachable_event_surface_audit.py",
    "tests/test_noncombat_reachable_event_surface_audit.py",
)
SIMULATOR_SOURCE_PATHS = {
    "display_labels": "src/sim/ConsoleSimulator.cpp",
    "event_definitions": "include/constants/Events.h",
    "event_save_ids": "include/constants/SaveFileMappings.h",
    "game_context": "src/game/GameContext.cpp",
    "game_header": "include/game/GameContext.h",
    "legal_actions": "src/sim/search/GameAction.cpp",
}
PREDECESSOR_PATHS = {
    "compatibility_closeout": (
        "reports/noncombat_total_event_native_compatibility_20260803_closeout.md"
    ),
    "compatibility_journal": (
        "reports/noncombat_total_event_native_compatibility_20260803/"
        "execution_journal.json"
    ),
    "compatibility_manifest": (
        "reports/noncombat_total_event_native_compatibility_20260803/"
        "artifact_manifest.json"
    ),
    "observation_contract": (
        "reports/noncombat_event_option_observation_contract_20260802/contract.json"
    ),
}
EXPECTED_POOL_SCOPES = (
    ("EventPools", "oneTimeEventsAsc0"),
    ("EventPools::Act1", "events"),
    ("EventPools::Act1", "shrines"),
    ("EventPools::Act2", "events"),
    ("EventPools::Act2", "shrines"),
    ("EventPools::Act3", "events"),
    ("EventPools::Act3", "shrines"),
)
EXPECTED_COUNT_KEYS = {
    "direct_transition_count",
    "event_option_target_count",
    "explicit_event_count",
    "generic_event_count",
    "pool_declared_count",
    "runtime_disabled_count",
}
ALL_FALSE_AUTHORITY = {
    "baseline_floor_authorized": False,
    "formal_rl_readiness_authorized": False,
    "fresh_evidence_authorized": False,
    "gameplay_authorized": False,
    "model_authorized": False,
    "ope_authorized": False,
    "policy_loading_authorized": False,
    "promotion_authorized": False,
    "qualification_authorized": False,
    "reward_authorized": False,
    "target_supported_outcome_authorized": False,
    "training_authorized": False,
}


class ReachableSurfaceBlocked(RuntimeError):
    """Raised when static reachable-surface closure cannot be proved."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _line_number(value: str, offset: int) -> int:
    return value.count("\n", 0, offset) + 1


def _masked_cpp(value: str) -> str:
    try:
        return _mask_cpp_comments(value)
    except AuditBlocked as exc:
        raise ReachableSurfaceBlocked(exc.reason, exc.detail) from exc


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReachableSurfaceBlocked("reachable_surface_input_invalid", label)
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReachableSurfaceBlocked("reachable_surface_input_invalid", label)
    return list(value)


def _require_exact_keys(
    value: Mapping[str, Any], expected: set[str], label: str
) -> None:
    actual = set(value)
    if actual != expected:
        raise ReachableSurfaceBlocked(
            "reachable_surface_input_invalid",
            {
                "label": label,
                "missing": sorted(expected - actual),
                "unexpected": sorted(actual - expected),
            },
        )


def _extract_brace_block(
    source: str,
    analysis: str,
    *,
    header_pattern: str,
    label: str,
    base_offset: int = 0,
) -> tuple[str, int, int]:
    matches = list(re.finditer(header_pattern, analysis, flags=re.MULTILINE))
    if len(matches) != 1:
        raise ReachableSurfaceBlocked(
            "event_pool_namespace_missing_or_ambiguous", label
        )
    opening = analysis.find("{", matches[0].start(), matches[0].end())
    if opening < 0:
        raise ReachableSurfaceBlocked("event_pool_namespace_invalid", label)
    depth = 0
    closing = None
    for index in range(opening, len(analysis)):
        if analysis[index] == "{":
            depth += 1
        elif analysis[index] == "}":
            depth -= 1
            if depth == 0:
                closing = index
                break
    if closing is None:
        raise ReachableSurfaceBlocked("event_pool_namespace_invalid", label)
    return source[opening + 1 : closing], base_offset + opening + 1, closing


def _parse_event_array(
    block_source: str,
    *,
    block_offset: int,
    full_source: str,
    variable_name: str,
    scope: str,
) -> dict[str, Any]:
    analysis = _masked_cpp(block_source)
    pattern = re.compile(
        rf"\bconst\s+std::array\s*<\s*Event\s*,\s*(\d+)\s*>\s+"
        rf"{re.escape(variable_name)}\s*\{{([^{{}}]*)\}}\s*;",
        flags=re.DOTALL,
    )
    matches = list(pattern.finditer(analysis))
    if len(matches) != 1:
        raise ReachableSurfaceBlocked(
            "event_pool_declaration_missing_or_ambiguous", scope
        )
    match = matches[0]
    declared_count = int(match.group(1))
    raw_items = match.group(2).split(",")
    events = []
    for raw_item in raw_items:
        item = raw_item.strip()
        if not item:
            continue
        parsed = re.fullmatch(r"Event::([A-Z][A-Z0-9_]*)", item)
        if parsed is None:
            raise ReachableSurfaceBlocked(
                "event_pool_declaration_item_unsupported",
                {"scope": scope, "item": item},
            )
        events.append(parsed.group(1))
    if len(events) != declared_count:
        raise ReachableSurfaceBlocked(
            "event_pool_declared_count_mismatch",
            {"actual": len(events), "declared": declared_count, "scope": scope},
        )
    if len(events) != len(set(events)):
        duplicates = sorted(
            name for name in set(events) if events.count(name) > 1
        )
        raise ReachableSurfaceBlocked(
            "event_pool_declaration_duplicate",
            {"duplicates": duplicates, "scope": scope},
        )
    start = block_offset + match.start()
    end = block_offset + match.end()
    return {
        "declared_count": declared_count,
        "events": events,
        "line_end": _line_number(full_source, max(start, end - 1)),
        "line_start": _line_number(full_source, start),
        "scope": scope,
        "source_sha256": _sha256_bytes(
            full_source[start:end].encode("utf-8")
        ),
    }


def parse_a0_pool_declarations(
    source: str, *, source_path: str = "include/constants/Events.h"
) -> dict[str, Any]:
    """Parse the exact seven A0 pool declarations from active C++ source."""

    if not isinstance(source, str):
        raise ReachableSurfaceBlocked("event_pool_source_invalid")
    analysis = _masked_cpp(source)
    event_pools_source, event_pools_offset, _ = _extract_brace_block(
        source,
        analysis,
        header_pattern=r"\bnamespace\s+EventPools\s*\{",
        label="EventPools",
    )
    declarations = [
        _parse_event_array(
            event_pools_source,
            block_offset=event_pools_offset,
            full_source=source,
            variable_name="oneTimeEventsAsc0",
            scope="EventPools::oneTimeEventsAsc0",
        )
    ]
    pools_analysis = _masked_cpp(event_pools_source)
    for act in ("Act1", "Act2", "Act3"):
        act_source, act_offset, _ = _extract_brace_block(
            event_pools_source,
            pools_analysis,
            header_pattern=rf"\bnamespace\s+{act}\s*\{{",
            label=f"EventPools::{act}",
            base_offset=event_pools_offset,
        )
        for variable in ("events", "shrines"):
            declarations.append(
                _parse_event_array(
                    act_source,
                    block_offset=act_offset,
                    full_source=source,
                    variable_name=variable,
                    scope=f"EventPools::{act}::{variable}",
                )
            )
    scopes = [(row["scope"].rsplit("::", 1)[0], row["scope"].rsplit("::", 1)[1]) for row in declarations]
    if tuple(scopes) != EXPECTED_POOL_SCOPES:
        raise ReachableSurfaceBlocked("event_pool_scope_order_mismatch")
    pool_events = sorted(
        {event for declaration in declarations for event in declaration["events"]}
    )
    return {
        "declaration_count": len(declarations),
        "declarations": declarations,
        "pool_declared_events": pool_events,
        "source_path": source_path,
        "source_sha256": _sha256_bytes(source.encode("utf-8")),
    }


def _unique_pattern(
    analysis: str, pattern: str, *, reason: str, detail: object
) -> re.Match[str]:
    matches = list(re.finditer(pattern, analysis, flags=re.DOTALL))
    if len(matches) != 1:
        raise ReachableSurfaceBlocked(reason, detail)
    return matches[0]


def parse_permanent_disable_evidence(
    header_source: str,
    game_source: str,
    *,
    header_path: str = "include/game/GameContext.h",
    game_path: str = "src/game/GameContext.cpp",
) -> dict[str, dict[str, Any]]:
    """Read the two permanent event guards used by the registered build."""

    header_analysis = _masked_cpp(header_source)
    game_analysis = _masked_cpp(game_source)
    definitions = {
        "COLOSSEUM": "disableColosseum",
        "MATCH_AND_KEEP": "disableMatchAndKeep",
    }
    guard_patterns = {
        "COLOSSEUM": (
            r"case\s+Event::COLOSSEUM\s*:(?:(?!case\s+Event::).)*?"
            r"return\s+curMapNodeY\s*>\s*7\s*&&\s*!disableColosseum\s*;"
        ),
        "MATCH_AND_KEEP": (
            r"if\s*\(\s*shrine\s*!=\s*Event::MATCH_AND_KEEP\s*\|\|\s*"
            r"!disableMatchAndKeep\s*\)"
        ),
    }
    result = {}
    for event, flag in definitions.items():
        flag_match = _unique_pattern(
            header_analysis,
            rf"\bstatic\s+constexpr\s+bool\s+{flag}\s*=\s*(true|false)\s*;",
            reason="permanent_disable_flag_missing_or_ambiguous",
            detail=flag,
        )
        guard_match = _unique_pattern(
            game_analysis,
            guard_patterns[event],
            reason="permanent_disable_guard_missing",
            detail=event,
        )
        result[event] = {
            "disabled": flag_match.group(1) == "true",
            "flag": flag,
            "flag_line": _line_number(header_source, flag_match.start()),
            "flag_path": header_path,
            "guard_line": _line_number(game_source, guard_match.start()),
            "guard_path": game_path,
            "reason": "compile_time_guard",
        }
    return result


def _event_identity_row(
    upstream_enum: str, identity: Mapping[str, Any]
) -> dict[str, Any]:
    normalized = _mapping(identity, f"event identity {upstream_enum}")
    required = {"event_game_name", "event_id", "save_id", "source_refs"}
    if not required.issubset(normalized):
        raise ReachableSurfaceBlocked(
            "event_identity_incomplete", upstream_enum
        )
    values = [
        normalized["event_game_name"],
        normalized["event_id"],
        normalized["save_id"],
    ]
    if not all(isinstance(value, str) and value for value in values):
        raise ReachableSurfaceBlocked("event_identity_incomplete", upstream_enum)
    return {
        "event_game_name": normalized["event_game_name"],
        "save_id": normalized["save_id"],
        "source_refs": copy.deepcopy(normalized["source_refs"]),
        "upstream_enum": upstream_enum,
        "upstream_event_id": normalized["event_id"],
    }


def _direct_transition_row(
    upstream_enum: str,
    identity: Mapping[str, Any],
    setup_case: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if setup_case is None:
        return None
    case = _mapping(setup_case, f"setup case {upstream_enum}")
    analysis_text = case.get("analysis_text")
    if not isinstance(analysis_text, str):
        return None
    pattern = (
        rf"\bopenCardSelectScreen\s*\(\s*"
        rf"CardSelectScreenType::{re.escape(upstream_enum)}\s*,"
    )
    if re.search(pattern, analysis_text) is None:
        return None
    row = _event_identity_row(upstream_enum, identity)
    row["reason"] = "direct_card_select_transition"
    row["setup_source"] = {
        key: case[key]
        for key in ("line_end", "line_start", "source_path")
        if key in case
    }
    return row


def _registered_explicit_aliases(
    predecessor_contract: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    contract = _mapping(predecessor_contract, "predecessor contract")
    events = [
        _mapping(value, f"predecessor event[{index}]")
        for index, value in enumerate(_sequence(contract.get("events"), "events"))
    ]
    enums = []
    aliases = []
    for event in events:
        upstream_enum = event.get("upstream_enum")
        if not isinstance(upstream_enum, str) or not upstream_enum:
            raise ReachableSurfaceBlocked("predecessor_event_identity_invalid")
        enums.append(upstream_enum)
        raw_aliases = _sequence(event.get("aliases"), "event aliases")
        if not raw_aliases or not all(
            isinstance(alias, str) and alias for alias in raw_aliases
        ):
            raise ReachableSurfaceBlocked("predecessor_event_alias_invalid")
        aliases.extend(raw_aliases)
    if len(enums) != len(set(enums)) or len(aliases) != len(set(aliases)):
        raise ReachableSurfaceBlocked("predecessor_event_identity_ambiguous")
    return events, set(enums), set(aliases)


def classify_surface_partitions(
    *,
    pool_inventory: Mapping[str, Any],
    event_identities: Mapping[str, Mapping[str, Any]],
    legal_summaries: Mapping[str, Mapping[str, Any]],
    setup_cases: Mapping[str, Mapping[str, Any]],
    disabled_evidence: Mapping[str, Mapping[str, Any]],
    current_surface: Mapping[str, Any],
    predecessor_contract: Mapping[str, Any],
    expected_counts: Mapping[str, int],
) -> dict[str, Any]:
    """Reconcile pool, runtime, target, explicit, and generic identities."""

    pool = _mapping(pool_inventory, "pool inventory")
    pool_events = _sequence(pool.get("pool_declared_events"), "pool events")
    if (
        not pool_events
        or not all(isinstance(event, str) and event for event in pool_events)
        or pool_events != sorted(set(pool_events))
    ):
        raise ReachableSurfaceBlocked("event_pool_inventory_invalid")
    missing_identities = sorted(set(pool_events) - set(event_identities))
    if missing_identities:
        raise ReachableSurfaceBlocked(
            "event_pool_identity_missing", missing_identities
        )
    predecessor_events, explicit_enums, registered_aliases = (
        _registered_explicit_aliases(predecessor_contract)
    )
    current = _mapping(current_surface, "current surface")
    current_aliases = set(_sequence(current.get("aliases"), "current aliases"))
    if current_aliases != registered_aliases:
        extra = sorted(current_aliases - registered_aliases)
        missing = sorted(registered_aliases - current_aliases)
        generic_identity_values = {
            value
            for enum_name in set(pool_events) - explicit_enums
            for key, value in _mapping(
                event_identities[enum_name], f"identity {enum_name}"
            ).items()
            if key in {"event_game_name", "event_id", "save_id"}
            and isinstance(value, str)
        }
        overlap = sorted(set(extra).intersection(generic_identity_values))
        if overlap:
            raise ReachableSurfaceBlocked(
                "generic_event_current_alias_overlap", overlap
            )
        raise ReachableSurfaceBlocked(
            "current_predecessor_alias_mismatch",
            {"extra": extra, "missing": missing},
        )

    disabled_names = {
        name
        for name, evidence in disabled_evidence.items()
        if _mapping(evidence, f"disabled evidence {name}").get("disabled") is True
    }
    if not disabled_names.issubset(pool_events):
        raise ReachableSurfaceBlocked(
            "disabled_event_not_in_pool", sorted(disabled_names - set(pool_events))
        )
    disabled_rows = []
    for name in sorted(disabled_names):
        row = _event_identity_row(name, event_identities[name])
        row["disable_evidence"] = copy.deepcopy(dict(disabled_evidence[name]))
        disabled_rows.append(row)

    direct_rows = []
    target_names = []
    for name in pool_events:
        if name in disabled_names:
            continue
        legal = _mapping(legal_summaries.get(name), f"legal summary {name}")
        indices = legal.get("legal_indices")
        dynamic = legal.get("dynamic_return_expressions")
        if not isinstance(indices, list) or not isinstance(dynamic, list):
            raise ReachableSurfaceBlocked("event_legal_summary_invalid", name)
        if not indices and not dynamic:
            direct = _direct_transition_row(
                name, event_identities[name], setup_cases.get(name)
            )
            if direct is None:
                raise ReachableSurfaceBlocked(
                    "reachable_event_without_legal_actions", name
                )
            direct["legal_summary"] = copy.deepcopy(legal)
            direct_rows.append(direct)
            continue
        target_names.append(name)

    target_set = set(target_names)
    if not explicit_enums.issubset(target_set):
        raise ReachableSurfaceBlocked(
            "explicit_event_not_reachable_target",
            sorted(explicit_enums - target_set),
        )
    generic_names = sorted(target_set - explicit_enums)
    for name in generic_names:
        identity = _mapping(event_identities[name], f"identity {name}")
        aliases = {
            identity.get("event_game_name"),
            identity.get("event_id"),
            identity.get("save_id"),
        }
        overlap = sorted(
            alias for alias in aliases.intersection(current_aliases) if alias
        )
        if overlap:
            raise ReachableSurfaceBlocked(
                "generic_event_current_alias_overlap",
                {"aliases": overlap, "upstream_enum": name},
            )

    explicit_rules = {
        event["upstream_enum"]: event for event in predecessor_events
    }
    explicit_rows = []
    for name in sorted(explicit_enums):
        row = _event_identity_row(name, event_identities[name])
        row["handling"] = "explicit_policy_sensitive"
        row["legal_summary"] = copy.deepcopy(dict(legal_summaries[name]))
        row["predecessor_rule_sha256"] = _sha256_bytes(
            canonical_json_bytes(explicit_rules[name])
        )
        explicit_rows.append(row)
    generic_rows = []
    for name in generic_names:
        row = _event_identity_row(name, event_identities[name])
        row["handling"] = "generic_position_zero_default"
        row["legal_summary"] = copy.deepcopy(dict(legal_summaries[name]))
        generic_rows.append(row)

    actual_counts = {
        "direct_transition_count": len(direct_rows),
        "event_option_target_count": len(target_names),
        "explicit_event_count": len(explicit_rows),
        "generic_event_count": len(generic_rows),
        "pool_declared_count": len(pool_events),
        "runtime_disabled_count": len(disabled_rows),
    }
    expected = _mapping(expected_counts, "expected counts")
    if set(expected) != EXPECTED_COUNT_KEYS or any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in expected.values()
    ):
        raise ReachableSurfaceBlocked("expected_partition_counts_invalid")
    if actual_counts != expected:
        raise ReachableSurfaceBlocked(
            "reachable_surface_partition_mismatch",
            {"actual": actual_counts, "expected": expected},
        )
    if (
        actual_counts["pool_declared_count"]
        != actual_counts["runtime_disabled_count"]
        + actual_counts["direct_transition_count"]
        + actual_counts["event_option_target_count"]
        or actual_counts["event_option_target_count"]
        != actual_counts["explicit_event_count"]
        + actual_counts["generic_event_count"]
    ):
        raise ReachableSurfaceBlocked("reachable_surface_partition_invariant")
    return {
        "counts": actual_counts,
        "current_ast_sha256": current.get("ast_sha256"),
        "direct_transitions": direct_rows,
        "disabled_events": disabled_rows,
        "explicit_events": explicit_rows,
        "generic_events": generic_rows,
        "pool_declared_events": [
            _event_identity_row(name, event_identities[name]) for name in pool_events
        ],
    }


def _contract_partition_payload(contract: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "direct_transitions": contract["direct_transitions"],
        "disabled_events": contract["disabled_events"],
        "explicit_events": contract["explicit_events"],
        "generic_events": contract["generic_events"],
        "identity": contract["identity"],
    }


def _generic_contract_row(value: Mapping[str, Any]) -> dict[str, Any]:
    row = _mapping(value, "generic event")
    return {
        "current_event_id": row["upstream_event_id"],
        "event_game_name": row["event_game_name"],
        "kind": "generic_default",
        "save_id": row["save_id"],
        "upstream_enum": row["upstream_enum"],
        "upstream_event_id": row["upstream_event_id"],
    }


def _excluded_contract_row(value: Mapping[str, Any]) -> dict[str, Any]:
    row = _mapping(value, "excluded event")
    result = {
        "event_game_name": row["event_game_name"],
        "save_id": row["save_id"],
        "upstream_enum": row["upstream_enum"],
        "upstream_event_id": row["upstream_event_id"],
    }
    if "disable_evidence" in row:
        result["reason"] = "permanently_disabled"
    else:
        result["reason"] = row.get("reason")
    return result


def build_successor_contract(
    *,
    predecessor_contract: Mapping[str, Any],
    surface_inventory: Mapping[str, Any],
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    inventory = _mapping(surface_inventory, "surface inventory")
    counts = _mapping(inventory.get("counts"), "surface counts")
    identity_value = _mapping(identity, "contract identity")
    expected_identity_keys = {
        "audit_evidence_sha256",
        "current_ast_sha256",
        "predecessor_contract_sha256",
        "simulator_source_sha256",
    }
    _require_exact_keys(identity_value, expected_identity_keys, "contract identity")
    if not all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        for value in identity_value.values()
    ):
        raise ReachableSurfaceBlocked("successor_contract_identity_invalid")
    explicit_rules, _, _ = _registered_explicit_aliases(predecessor_contract)
    generic_events = [
        _generic_contract_row(row)
        for row in _sequence(inventory.get("generic_events"), "generic events")
    ]
    disabled_events = [
        _excluded_contract_row(row)
        for row in _sequence(inventory.get("disabled_events"), "disabled events")
    ]
    direct_transitions = [
        _excluded_contract_row(row)
        for row in _sequence(
            inventory.get("direct_transitions"), "direct transitions"
        )
    ]
    contract = {
        "adapter_ready": False,
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "contract_id": SUCCESSOR_CONTRACT_ID,
        "direct_transition_count": counts["direct_transition_count"],
        "direct_transitions": direct_transitions,
        "disabled_event_count": counts["runtime_disabled_count"],
        "disabled_events": disabled_events,
        "event_option_target_count": counts["event_option_target_count"],
        "explicit_event_count": counts["explicit_event_count"],
        "explicit_events": copy.deepcopy(explicit_rules),
        "generic_event_count": counts["generic_event_count"],
        "generic_events": generic_events,
        "identity": copy.deepcopy(identity_value),
        "partition_sha256": "",
        "pool_declared_count": counts["pool_declared_count"],
        "predecessor_schema_version": predecessor_contract.get("schema_version"),
        "resolver_ready": False,
        "schema_version": SUCCESSOR_CONTRACT_SCHEMA_VERSION,
    }
    contract["partition_sha256"] = _sha256_bytes(
        canonical_json_bytes(_contract_partition_payload(contract))
    )
    return validate_successor_contract(contract)


def validate_successor_contract(value: object) -> dict[str, Any]:
    contract = _mapping(value, "successor contract")
    expected_keys = {
        "adapter_ready",
        "authority",
        "contract_id",
        "direct_transition_count",
        "direct_transitions",
        "disabled_event_count",
        "disabled_events",
        "event_option_target_count",
        "explicit_event_count",
        "explicit_events",
        "generic_event_count",
        "generic_events",
        "identity",
        "partition_sha256",
        "pool_declared_count",
        "predecessor_schema_version",
        "resolver_ready",
        "schema_version",
    }
    _require_exact_keys(contract, expected_keys, "successor contract")
    if (
        contract["schema_version"] != SUCCESSOR_CONTRACT_SCHEMA_VERSION
        or contract["contract_id"] != SUCCESSOR_CONTRACT_ID
    ):
        raise ReachableSurfaceBlocked("successor_contract_schema_mismatch")
    if (
        contract["authority"] != ALL_FALSE_AUTHORITY
        or contract["adapter_ready"] is not False
        or contract["resolver_ready"] is not False
    ):
        raise ReachableSurfaceBlocked("successor_contract_authority_invalid")
    explicit = _sequence(contract["explicit_events"], "explicit events")
    generic = _sequence(contract["generic_events"], "generic events")
    disabled = _sequence(contract["disabled_events"], "disabled events")
    direct = _sequence(contract["direct_transitions"], "direct transitions")
    identity = _mapping(contract["identity"], "successor identity")
    identity_keys = {
        "audit_evidence_sha256",
        "current_ast_sha256",
        "predecessor_contract_sha256",
        "simulator_source_sha256",
    }
    _require_exact_keys(identity, identity_keys, "successor identity")
    for key, digest in identity.items():
        _validate_sha256(digest, f"successor identity.{key}")
    if not isinstance(contract["predecessor_schema_version"], str) or not contract[
        "predecessor_schema_version"
    ]:
        raise ReachableSurfaceBlocked(
            "successor_contract_predecessor_schema_invalid"
        )
    preliminary_sets = []
    for label, rows in (
        ("explicit", explicit),
        ("generic", generic),
        ("disabled", disabled),
        ("direct", direct),
    ):
        names = []
        for index, raw_row in enumerate(rows):
            row = _mapping(raw_row, f"{label}[{index}]")
            name = row.get("upstream_enum")
            if not isinstance(name, str) or not name:
                raise ReachableSurfaceBlocked(
                    "successor_contract_event_identity_invalid", label
                )
            names.append(name)
        preliminary_sets.append(set(names))
    if preliminary_sets[0].intersection(preliminary_sets[1]):
        raise ReachableSurfaceBlocked("successor_explicit_generic_overlap")
    sets = []
    for label, rows in (
        ("explicit", explicit),
        ("generic", generic),
        ("disabled", disabled),
        ("direct", direct),
    ):
        names = []
        for index, raw_row in enumerate(rows):
            row = _mapping(raw_row, f"{label}[{index}]")
            name = row.get("upstream_enum")
            if not isinstance(name, str) or not name:
                raise ReachableSurfaceBlocked(
                    "successor_contract_event_identity_invalid", label
                )
            if label == "generic":
                _require_exact_keys(
                    row,
                    {
                        "current_event_id",
                        "event_game_name",
                        "kind",
                        "save_id",
                        "upstream_enum",
                        "upstream_event_id",
                    },
                    f"generic[{index}]",
                )
                if row["kind"] != "generic_default" or row[
                    "current_event_id"
                ] != row["upstream_event_id"]:
                    raise ReachableSurfaceBlocked(
                        "successor_contract_generic_rule_invalid", name
                    )
                if not all(
                    isinstance(row[key], str) and row[key]
                    for key in (
                        "current_event_id",
                        "event_game_name",
                        "save_id",
                        "upstream_event_id",
                    )
                ):
                    raise ReachableSurfaceBlocked(
                        "successor_contract_generic_rule_invalid", name
                    )
            elif label in {"disabled", "direct"}:
                _require_exact_keys(
                    row,
                    {
                        "event_game_name",
                        "reason",
                        "save_id",
                        "upstream_enum",
                        "upstream_event_id",
                    },
                    f"{label}[{index}]",
                )
                if not all(
                    isinstance(row[key], str) and row[key]
                    for key in (
                        "event_game_name",
                        "reason",
                        "save_id",
                        "upstream_event_id",
                    )
                ):
                    raise ReachableSurfaceBlocked(
                        "successor_contract_excluded_rule_invalid", name
                    )
            names.append(name)
        if len(names) != len(set(names)):
            raise ReachableSurfaceBlocked(
                "successor_contract_event_identity_duplicate", label
            )
        sets.append(set(names))
    all_names: set[str] = set()
    for names in sets:
        if all_names.intersection(names):
            raise ReachableSurfaceBlocked("successor_partition_overlap")
        all_names.update(names)
    if (
        contract["explicit_event_count"] != len(explicit)
        or contract["generic_event_count"] != len(generic)
        or contract["disabled_event_count"] != len(disabled)
        or contract["direct_transition_count"] != len(direct)
        or contract["event_option_target_count"] != len(explicit) + len(generic)
        or contract["pool_declared_count"] != len(all_names)
    ):
        raise ReachableSurfaceBlocked("successor_contract_count_mismatch")
    expected_partition_sha256 = _sha256_bytes(
        canonical_json_bytes(_contract_partition_payload(contract))
    )
    if contract["partition_sha256"] != expected_partition_sha256:
        raise ReachableSurfaceBlocked("successor_contract_partition_hash_mismatch")
    return copy.deepcopy(contract)


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReachableSurfaceBlocked(
                "reachable_surface_registration_duplicate_key", key
            )
        result[key] = value
    return result


def _load_json_path(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except ReachableSurfaceBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReachableSurfaceBlocked(
            "reachable_surface_json_load_failed",
            {"label": label, "path": str(path)},
        ) from exc
    return _mapping(value, label)


def _validate_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ReachableSurfaceBlocked(
            "reachable_surface_registration_invalid", label
        )
    return value


def _validate_commit(value: object, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ReachableSurfaceBlocked(
            "reachable_surface_registration_invalid", label
        )
    return value


def _validated_binding(value: object, label: str) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_exact_keys(binding, {"path", "sha256", "size_bytes"}, label)
    if not isinstance(binding["path"], str) or not binding["path"]:
        raise ReachableSurfaceBlocked(
            "reachable_surface_registration_invalid", label
        )
    _validate_sha256(binding["sha256"], f"{label}.sha256")
    if (
        isinstance(binding["size_bytes"], bool)
        or not isinstance(binding["size_bytes"], int)
        or binding["size_bytes"] < 0
    ):
        raise ReachableSurfaceBlocked(
            "reachable_surface_registration_invalid", label
        )
    return binding


def validate_registration(value: object) -> dict[str, Any]:
    registration = _mapping(value, "registration")
    _require_exact_keys(
        registration,
        {
            "authority",
            "current",
            "expected_partition",
            "implementation",
            "output",
            "predecessors",
            "schema_version",
            "simulator",
        },
        "registration",
    )
    if registration["schema_version"] != INPUT_SCHEMA_VERSION:
        raise ReachableSurfaceBlocked(
            "reachable_surface_registration_schema_mismatch"
        )
    if registration["authority"] != ALL_FALSE_AUTHORITY:
        raise ReachableSurfaceBlocked(
            "reachable_surface_registration_authority_invalid"
        )

    implementation = _mapping(registration["implementation"], "implementation")
    _require_exact_keys(
        implementation, {"commit", "source_files", "source_sha256"}, "implementation"
    )
    _validate_commit(implementation["commit"], "implementation.commit")
    source_files = _sequence(implementation["source_files"], "source_files")
    if tuple(source_files) != IMPLEMENTATION_SOURCE_FILES:
        raise ReachableSurfaceBlocked(
            "reachable_surface_implementation_sources_mismatch"
        )
    _validate_sha256(implementation["source_sha256"], "implementation.source_sha256")

    current = _mapping(registration["current"], "current")
    _require_exact_keys(
        current,
        {"class_name", "function_name", "repository_commit", "source"},
        "current",
    )
    if (
        current["class_name"] != "SimpleAgent"
        or current["function_name"] != "_choose_event_option"
    ):
        raise ReachableSurfaceBlocked("reachable_surface_current_target_mismatch")
    _validate_commit(current["repository_commit"], "current.repository_commit")
    current["source"] = _validated_binding(current["source"], "current.source")

    simulator = _mapping(registration["simulator"], "simulator")
    _require_exact_keys(
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
    if not isinstance(simulator["root"], str) or not simulator["root"]:
        raise ReachableSurfaceBlocked("reachable_surface_simulator_root_invalid")
    _validate_commit(simulator["parent_commit"], "simulator.parent_commit")
    if not isinstance(simulator["dirty"], bool):
        raise ReachableSurfaceBlocked("reachable_surface_simulator_dirty_invalid")
    _validate_sha256(simulator["source_sha256"], "simulator.source_sha256")
    if (
        isinstance(simulator["source_file_count"], bool)
        or not isinstance(simulator["source_file_count"], int)
        or simulator["source_file_count"] <= 0
    ):
        raise ReachableSurfaceBlocked(
            "reachable_surface_simulator_source_count_invalid"
        )
    submodules = _mapping(simulator["submodules"], "simulator.submodules")
    _require_exact_keys(submodules, {"json", "pybind11"}, "simulator.submodules")
    for name, commit in submodules.items():
        _validate_commit(commit, f"simulator.submodules.{name}")
    source_bindings = _mapping(
        simulator["source_files"], "simulator.source_files"
    )
    if set(source_bindings) != set(SIMULATOR_SOURCE_PATHS):
        raise ReachableSurfaceBlocked(
            "reachable_surface_simulator_source_roles_mismatch"
        )
    simulator["source_files"] = {
        name: _validated_binding(binding, f"simulator.source_files.{name}")
        for name, binding in source_bindings.items()
    }

    predecessors = _mapping(registration["predecessors"], "predecessors")
    if set(predecessors) != set(PREDECESSOR_PATHS):
        raise ReachableSurfaceBlocked(
            "reachable_surface_predecessor_roles_mismatch"
        )
    registration["predecessors"] = {
        name: _validated_binding(binding, f"predecessors.{name}")
        for name, binding in predecessors.items()
    }

    expected = _mapping(registration["expected_partition"], "expected_partition")
    if set(expected) != EXPECTED_COUNT_KEYS or any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in expected.values()
    ):
        raise ReachableSurfaceBlocked(
            "reachable_surface_expected_partition_invalid"
        )

    output = _mapping(registration["output"], "output")
    _require_exact_keys(output, {"artifact_names", "directory"}, "output")
    if tuple(_sequence(output["artifact_names"], "output.artifact_names")) != (
        CANONICAL_ARTIFACT_NAMES
    ):
        raise ReachableSurfaceBlocked("reachable_surface_output_names_mismatch")
    directory = output["directory"]
    if (
        not isinstance(directory, str)
        or not directory
        or PurePosixPath(directory).is_absolute()
        or ".." in PurePosixPath(directory).parts
    ):
        raise ReachableSurfaceBlocked("reachable_surface_output_directory_invalid")
    return copy.deepcopy(registration)


def load_registration(path: Path | str) -> dict[str, Any]:
    registration = _load_json_path(Path(path).resolve(), "registration")
    return validate_registration(registration)


def _git_text(repo: Path, *args: str) -> str:
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
        raise ReachableSurfaceBlocked(
            "reachable_surface_git_query_failed", list(args)
        ) from exc
    return completed.stdout.strip()


def _file_binding(path: Path, display_path: str) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ReachableSurfaceBlocked("reachable_surface_bound_file_missing", display_path)
    return {
        "path": display_path,
        "sha256": sha256_file(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def _verify_old_audit_call(callable_value, *args, **kwargs):
    try:
        return callable_value(*args, **kwargs)
    except AuditBlocked as exc:
        raise ReachableSurfaceBlocked(exc.reason, exc.detail) from exc


def _assert_clean_pushed_head(repo_root: Path) -> str:
    if _git_text(repo_root, "status", "--porcelain", "--untracked-files=no"):
        raise ReachableSurfaceBlocked("reachable_surface_tracked_tree_dirty")
    head = _git_text(repo_root, "rev-parse", "HEAD")
    origin = _git_text(repo_root, "rev-parse", "origin/master")
    if head != origin:
        raise ReachableSurfaceBlocked(
            "reachable_surface_head_not_pushed",
            {"head": head, "origin_master": origin},
        )
    return _validate_commit(head, "HEAD")


def build_default_registration(
    *, repo_root: Path | str, simulator_root: Path | str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    simulator_path = Path(simulator_root).resolve()
    head = _assert_clean_pushed_head(root)
    registration_path = root / DEFAULT_REGISTRATION_PATH
    output_path = root / DEFAULT_OUTPUT_DIRECTORY
    if registration_path.exists() or output_path.exists():
        raise ReachableSurfaceBlocked(
            "reachable_surface_registration_or_output_exists"
        )
    simulator_source_sha256, simulator_source_count = _verify_old_audit_call(
        hash_simulator_sources, simulator_path
    )
    registration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "current": {
            "class_name": "SimpleAgent",
            "function_name": "_choose_event_option",
            "repository_commit": head,
            "source": _file_binding(
                root / "spirecomm/ai/agent.py", "spirecomm/ai/agent.py"
            ),
        },
        "expected_partition": {
            "direct_transition_count": 1,
            "event_option_target_count": 48,
            "explicit_event_count": 25,
            "generic_event_count": 23,
            "pool_declared_count": 51,
            "runtime_disabled_count": 2,
        },
        "implementation": {
            "commit": head,
            "source_files": list(IMPLEMENTATION_SOURCE_FILES),
            "source_sha256": _verify_old_audit_call(
                hash_bound_files, root, IMPLEMENTATION_SOURCE_FILES
            ),
        },
        "output": {
            "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
            "directory": DEFAULT_OUTPUT_DIRECTORY.as_posix(),
        },
        "predecessors": {
            name: _file_binding(root / relative, relative)
            for name, relative in PREDECESSOR_PATHS.items()
        },
        "schema_version": INPUT_SCHEMA_VERSION,
        "simulator": {
            "dirty": bool(_git_text(simulator_path, "status", "--porcelain")),
            "parent_commit": _git_text(simulator_path, "rev-parse", "HEAD"),
            "root": str(simulator_path),
            "source_file_count": simulator_source_count,
            "source_files": {
                name: _file_binding(simulator_path / relative, relative)
                for name, relative in SIMULATOR_SOURCE_PATHS.items()
            },
            "source_sha256": simulator_source_sha256,
            "submodules": {
                name: _git_text(simulator_path / name, "rev-parse", "HEAD")
                for name in ("json", "pybind11")
            },
        },
    }
    return validate_registration(registration)


def write_default_registration(
    *, repo_root: Path | str, simulator_root: Path | str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    registration = build_default_registration(
        repo_root=root, simulator_root=simulator_root
    )
    path = root / DEFAULT_REGISTRATION_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(registration))
    loaded = load_registration(path)
    verify_registration_identity(loaded, root)
    return {
        "registration_path": DEFAULT_REGISTRATION_PATH.as_posix(),
        "registration_sha256": sha256_file(path),
    }


def verify_registration_identity(
    registration: Mapping[str, Any], repo_root: Path | str
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    implementation = registration["implementation"]
    actual_implementation = _verify_old_audit_call(
        hash_bound_files, root, implementation["source_files"]
    )
    if actual_implementation != implementation["source_sha256"]:
        raise ReachableSurfaceBlocked(
            "reachable_surface_implementation_hash_mismatch"
        )
    _verify_old_audit_call(
        _verify_sources_at_commit,
        root,
        implementation["commit"],
        implementation["source_files"],
    )

    current = registration["current"]
    current_path = _verify_old_audit_call(
        verify_bound_file,
        root,
        current["source"],
        repository_relative=True,
    )
    _verify_old_audit_call(
        _verify_sources_at_commit,
        root,
        current["repository_commit"],
        [current["source"]["path"]],
    )

    simulator = registration["simulator"]
    simulator_root = Path(simulator["root"]).resolve()
    if not simulator_root.is_dir():
        raise ReachableSurfaceBlocked("reachable_surface_simulator_root_missing")
    actual_parent = _git_text(simulator_root, "rev-parse", "HEAD")
    actual_dirty = bool(_git_text(simulator_root, "status", "--porcelain"))
    actual_source_hash, actual_source_count = _verify_old_audit_call(
        hash_simulator_sources, simulator_root
    )
    actual_submodules = {
        name: _git_text(simulator_root / name, "rev-parse", "HEAD")
        for name in ("json", "pybind11")
    }
    if (
        actual_parent != simulator["parent_commit"]
        or actual_dirty != simulator["dirty"]
        or actual_source_hash != simulator["source_sha256"]
        or actual_source_count != simulator["source_file_count"]
        or actual_submodules != simulator["submodules"]
    ):
        raise ReachableSurfaceBlocked(
            "reachable_surface_simulator_identity_mismatch",
            {
                "dirty": actual_dirty,
                "parent_commit": actual_parent,
                "source_file_count": actual_source_count,
                "source_sha256": actual_source_hash,
                "submodules": actual_submodules,
            },
        )
    simulator_paths = {
        name: _verify_old_audit_call(
            verify_bound_file,
            simulator_root,
            binding,
            repository_relative=True,
        )
        for name, binding in simulator["source_files"].items()
    }
    predecessor_paths = {
        name: _verify_old_audit_call(
            verify_bound_file, root, binding, repository_relative=True
        )
        for name, binding in registration["predecessors"].items()
    }
    return {
        "current_source": current_path,
        "predecessors": predecessor_paths,
        "simulator_root": simulator_root,
        "simulator_sources": simulator_paths,
    }


def _source_case_summaries(
    *, legal_source: str, display_source: str, game_source: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    legal_cases = _verify_old_audit_call(
        index_cpp_event_cases,
        legal_source,
        signature="int search::GameAction::getValidEventSelectBits",
        source_path=SIMULATOR_SOURCE_PATHS["legal_actions"],
    )
    setup_cases = _verify_old_audit_call(
        index_cpp_event_cases,
        game_source,
        signature="void GameContext::setupEvent",
        source_path=SIMULATOR_SOURCE_PATHS["game_context"],
    )
    display_cases = _verify_old_audit_call(
        index_cpp_event_cases,
        display_source,
        signature="void ConsoleSimulator::printEventActions",
        source_path=SIMULATOR_SOURCE_PATHS["display_labels"],
    )
    execution_cases = _verify_old_audit_call(
        index_cpp_event_cases,
        game_source,
        signature="void GameContext::chooseEventOption",
        source_path=SIMULATOR_SOURCE_PATHS["game_context"],
    )
    legal = {
        name: summarize_legal_case(case) for name, case in legal_cases.items()
    }
    display = {
        name: summarize_display_case(case) for name, case in display_cases.items()
    }
    execution = {
        name: summarize_execution_case(case)
        for name, case in execution_cases.items()
    }
    return legal, setup_cases, display, execution


def analyze_registered_sources(
    registration: Mapping[str, Any], identities: Mapping[str, Any]
) -> dict[str, Any]:
    paths = identities["simulator_sources"]
    events_source = paths["event_definitions"].read_text(encoding="utf-8")
    save_source = paths["event_save_ids"].read_text(encoding="utf-8")
    header_source = paths["game_header"].read_text(encoding="utf-8")
    game_source = paths["game_context"].read_text(encoding="utf-8")
    legal_source = paths["legal_actions"].read_text(encoding="utf-8")
    display_source = paths["display_labels"].read_text(encoding="utf-8")
    current_source = identities["current_source"].read_text(encoding="utf-8")
    predecessor_contract = _load_json_path(
        identities["predecessors"]["observation_contract"],
        "predecessor observation contract",
    )

    pool_inventory = parse_a0_pool_declarations(events_source)
    disabled_evidence = parse_permanent_disable_evidence(
        header_source, game_source
    )
    event_identities = _verify_old_audit_call(
        parse_event_identities,
        events_source,
        save_source,
        events_path=SIMULATOR_SOURCE_PATHS["event_definitions"],
        save_path=SIMULATOR_SOURCE_PATHS["event_save_ids"],
    )
    current_surface = _verify_old_audit_call(
        parse_current_event_surface,
        current_source,
        class_name=registration["current"]["class_name"],
        function_name=registration["current"]["function_name"],
    )
    predecessor_registry = [
        {
            "aliases": copy.deepcopy(event["aliases"]),
            "canonical_id": event["canonical_id"],
            "upstream_enum": event["upstream_enum"],
        }
        for event in _sequence(predecessor_contract.get("events"), "events")
    ]
    _verify_old_audit_call(
        validate_event_registry, predecessor_registry, current_surface
    )
    legal, setup_cases, display, execution = _source_case_summaries(
        legal_source=legal_source,
        display_source=display_source,
        game_source=game_source,
    )
    surface = classify_surface_partitions(
        pool_inventory=pool_inventory,
        event_identities=event_identities,
        legal_summaries=legal,
        setup_cases=setup_cases,
        disabled_evidence=disabled_evidence,
        current_surface=current_surface,
        predecessor_contract=predecessor_contract,
        expected_counts=registration["expected_partition"],
    )
    target_rows = []
    for handling, rows in (
        ("explicit", surface["explicit_events"]),
        ("generic", surface["generic_events"]),
    ):
        for raw_row in rows:
            row = copy.deepcopy(raw_row)
            name = row["upstream_enum"]
            if name not in display or name not in execution:
                raise ReachableSurfaceBlocked(
                    "reachable_target_source_case_missing",
                    {"handling": handling, "upstream_enum": name},
                )
            row["display_summary"] = display[name]
            row["execution_summary"] = execution[name]
            target_rows.append(row)
    target_rows.sort(key=lambda row: row["upstream_enum"])
    partitions = {}
    for label, rows in (
        ("runtime_disabled", surface["disabled_events"]),
        ("direct_transition", surface["direct_transitions"]),
        ("explicit", surface["explicit_events"]),
        ("generic", surface["generic_events"]),
    ):
        for row in rows:
            name = row["upstream_enum"]
            if name in partitions:
                raise ReachableSurfaceBlocked(
                    "reachable_surface_partition_overlap", name
                )
            partitions[name] = label
    pool_rows = []
    memberships: dict[str, list[str]] = {}
    for declaration in pool_inventory["declarations"]:
        for name in declaration["events"]:
            memberships.setdefault(name, []).append(declaration["scope"])
    for identity in surface["pool_declared_events"]:
        row = copy.deepcopy(identity)
        row["partition"] = partitions[row["upstream_enum"]]
        row["pool_memberships"] = sorted(memberships[row["upstream_enum"]])
        pool_rows.append(row)
    return {
        "current_surface": current_surface,
        "pool_inventory": pool_inventory,
        "pool_rows": pool_rows,
        "predecessor_contract": predecessor_contract,
        "surface": surface,
        "target_rows": target_rows,
    }


def _artifact_binding(name: str, payload: bytes) -> dict[str, Any]:
    return {
        "path": name,
        "sha256": _sha256_bytes(payload),
        "size_bytes": len(payload),
    }


def _build_report(counts: Mapping[str, int]) -> bytes:
    lines = [
        "# Non-Combat Reachable Event Surface Audit",
        "",
        "## Result",
        "",
        "`reachable_event_surface_closed`",
        "",
        "## Partition",
        "",
        f"- Pool-declared identities: `{counts['pool_declared_count']}`.",
        f"- Permanently disabled identities: `{counts['runtime_disabled_count']}`.",
        f"- Direct-transition identities: `{counts['direct_transition_count']}`.",
        f"- Event-option targets: `{counts['event_option_target_count']}`.",
        f"- Explicit Current events: `{counts['explicit_event_count']}`.",
        f"- Generic Current-default events: `{counts['generic_event_count']}`.",
        "",
        "## Authority",
        "",
        "This source-only result authorizes no native execution, seed use, gameplay,",
        "baseline, outcome, reward, model, OPE, formal RL, training, loading,",
        "qualification, or promotion.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def build_audit_artifacts(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    analysis: Mapping[str, Any],
) -> dict[str, bytes]:
    surface = analysis["surface"]
    counts = surface["counts"]
    pool_payload = {
        "declaration_count": analysis["pool_inventory"]["declaration_count"],
        "declarations": analysis["pool_inventory"]["declarations"],
        "events": analysis["pool_rows"],
        "schema_version": POOL_INVENTORY_SCHEMA_VERSION,
    }
    target_payload = {
        "events": analysis["target_rows"],
        "schema_version": TARGET_INVENTORY_SCHEMA_VERSION,
    }
    current_payload = {
        "current_surface": analysis["current_surface"],
        "explicit_upstream_enums": [
            row["upstream_enum"] for row in surface["explicit_events"]
        ],
        "generic_upstream_enums": [
            row["upstream_enum"] for row in surface["generic_events"]
        ],
        "schema_version": CURRENT_PARTITION_SCHEMA_VERSION,
    }
    evidence_payload = {
        "counts": counts,
        "current_partition": current_payload,
        "pool_inventory": pool_payload,
        "target_inventory": target_payload,
    }
    audit_evidence_sha256 = _sha256_bytes(canonical_json_bytes(evidence_payload))
    successor = build_successor_contract(
        predecessor_contract=analysis["predecessor_contract"],
        surface_inventory=surface,
        identity={
            "audit_evidence_sha256": audit_evidence_sha256,
            "current_ast_sha256": analysis["current_surface"]["ast_sha256"],
            "predecessor_contract_sha256": registration["predecessors"][
                "observation_contract"
            ]["sha256"],
            "simulator_source_sha256": registration["simulator"]["source_sha256"],
        },
    )
    successor_bytes = canonical_json_bytes(successor)
    metrics = {
        "audit_evidence_sha256": audit_evidence_sha256,
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "counts": counts,
        "registration_sha256": registration_sha256,
        "schema_version": METRICS_SCHEMA_VERSION,
        "status": "passed",
        "successor_contract_sha256": _sha256_bytes(successor_bytes),
        "verdict": "reachable_event_surface_closed",
    }
    payloads = {
        "configuration.json": canonical_json_bytes(
            {
                "registration": copy.deepcopy(dict(registration)),
                "registration_sha256": registration_sha256,
                "schema_version": INPUT_SCHEMA_VERSION,
            }
        ),
        "current_partition.json": canonical_json_bytes(current_payload),
        "metrics.json": canonical_json_bytes(metrics),
        "pool_inventory.json": canonical_json_bytes(pool_payload),
        "report.md": _build_report(counts),
        "successor_contract.json": successor_bytes,
        "target_inventory.json": canonical_json_bytes(target_payload),
    }
    manifest = {
        "artifact_bindings": {
            name: _artifact_binding(name, payload)
            for name, payload in sorted(payloads.items())
        },
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "counts": counts,
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "successor_contract_sha256": _sha256_bytes(successor_bytes),
        "verdict": "reachable_event_surface_closed",
    }
    payloads["artifact_manifest.json"] = canonical_json_bytes(manifest)
    if set(payloads) != set(CANONICAL_ARTIFACT_NAMES):
        raise ReachableSurfaceBlocked("reachable_surface_artifact_names_invalid")
    return payloads


def write_or_verify_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    recompute: bool,
) -> None:
    root = Path(output_dir).resolve()
    expected_names = set(CANONICAL_ARTIFACT_NAMES)
    if set(artifacts) != expected_names or any(
        not isinstance(payload, bytes) for payload in artifacts.values()
    ):
        raise ReachableSurfaceBlocked("reachable_surface_artifact_payload_invalid")
    if recompute:
        if not root.is_dir():
            raise ReachableSurfaceBlocked("reachable_surface_output_missing")
        actual_names = {path.name for path in root.iterdir() if path.is_file()}
        if actual_names != expected_names or any(path.is_dir() for path in root.iterdir()):
            raise ReachableSurfaceBlocked(
                "reachable_surface_artifact_set_mismatch",
                {
                    "actual": sorted(actual_names),
                    "expected": sorted(expected_names),
                },
            )
        for name, expected in artifacts.items():
            if (root / name).read_bytes() != expected:
                raise ReachableSurfaceBlocked(
                    "reachable_surface_artifact_bytes_mismatch", name
                )
        return
    if root.exists():
        if not root.is_dir() or any(root.iterdir()):
            raise ReachableSurfaceBlocked("reachable_surface_output_already_exists")
    else:
        root.mkdir(parents=True)
    for name, payload in artifacts.items():
        (root / name).write_bytes(payload)


def run_audit(
    *,
    registration_path: Path | str,
    repo_root: Path | str,
    recompute: bool,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    input_path = Path(registration_path).resolve()
    registration = load_registration(input_path)
    identities = verify_registration_identity(registration, root)
    analysis = analyze_registered_sources(registration, identities)
    registration_sha256 = sha256_file(input_path)
    artifacts = build_audit_artifacts(
        registration=registration,
        registration_sha256=registration_sha256,
        analysis=analysis,
    )
    output = (root / registration["output"]["directory"]).resolve()
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise ReachableSurfaceBlocked(
            "reachable_surface_output_escapes_repository"
        ) from exc
    write_or_verify_artifacts(output, artifacts, recompute=recompute)
    return {
        "counts": analysis["surface"]["counts"],
        "output_directory": registration["output"]["directory"],
        "registration_sha256": registration_sha256,
        "verdict": "reachable_event_surface_closed",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register")
    register.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    register.add_argument("--simulator-repo", type=Path, required=True)
    publish = commands.add_parser("publish")
    publish.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    verify = commands.add_parser("verify")
    verify.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = args.repo_root.resolve()
        if args.command == "register":
            result = write_default_registration(
                repo_root=root, simulator_root=args.simulator_repo.resolve()
            )
        else:
            result = run_audit(
                registration_path=root / DEFAULT_REGISTRATION_PATH,
                repo_root=root,
                recompute=args.command == "verify",
            )
    except ReachableSurfaceBlocked as exc:
        print(json.dumps({"detail": exc.detail, "reason": exc.reason}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
