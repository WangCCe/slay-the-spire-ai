import copy
import json

import pytest

from analysis_scripts.noncombat_reachable_event_surface_audit import (
    ALL_FALSE_AUTHORITY,
    ReachableSurfaceBlocked,
    build_successor_contract,
    classify_surface_partitions,
    load_registration,
    parse_a0_pool_declarations,
    parse_permanent_disable_evidence,
    validate_successor_contract,
    write_or_verify_artifacts,
)


def _pool_source(*, duplicate=False, unsupported=False):
    act1_events = "Event::EXPLICIT, Event::GENERIC"
    if duplicate:
        act1_events = "Event::EXPLICIT, Event::EXPLICIT"
    declaration = (
        "std::vector<Event> events {" + act1_events + "};"
        if unsupported
        else "const std::array<Event,2> events {" + act1_events + "};"
    )
    return f"""
namespace EventPools {{
const std::array<Event,2> oneTimeEventsAsc0 {{Event::DISABLED, Event::DIRECT}};
const std::array<Event,1> oneTimeEventsAsc15 {{Event::IGNORED}};
namespace Act1 {{
{declaration}
const std::array<Event,1> shrines {{Event::SHRINE}};
}}
namespace Act2 {{
const std::array<Event,1> events {{Event::GENERIC_TWO}};
const std::array<Event,1> shrines {{Event::SHRINE}};
}}
namespace Act3 {{
const std::array<Event,1> events {{Event::GENERIC_THREE}};
const std::array<Event,1> shrines {{Event::SHRINE}};
}}
}}
"""


def _predecessor_contract():
    return {
        "schema_version": "noncombat-event-option-observation-contract-v1",
        "event_count": 1,
        "alias_count": 1,
        "unaccounted_surface_count": 0,
        "rule_kind_counts": {"static": 1},
        "registry_sha256": "a" * 64,
        "resolver_ready": False,
        "adapter_ready": False,
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "events": [
            {
                "aliases": ["Explicit"],
                "canonical_id": "Explicit",
                "current_event_id": "Explicit",
                "event_game_name": "Explicit",
                "kind": "static",
                "options": [
                    {"label": "Take", "simulator_choice_index": 0},
                ],
                "upstream_enum": "EXPLICIT",
                "upstream_event_id": "Explicit",
            }
        ],
    }


def _identity(enum_name):
    label = enum_name.replace("_", " ").title()
    return {
        "event_game_name": label,
        "event_id": label,
        "save_id": label,
        "source_refs": {},
    }


def _partition_inputs():
    pool = {
        "declaration_count": 7,
        "declarations": [],
        "pool_declared_events": [
            "DIRECT",
            "DISABLED",
            "EXPLICIT",
            "GENERIC",
            "GENERIC_THREE",
            "GENERIC_TWO",
            "SHRINE",
        ],
    }
    identities = {name: _identity(name) for name in pool["pool_declared_events"]}
    legal = {
        name: {"legal_indices": [0, 1], "dynamic_return_expressions": []}
        for name in pool["pool_declared_events"]
    }
    legal["DIRECT"] = {"legal_indices": [], "dynamic_return_expressions": []}
    setup = {
        "DIRECT": {
            "analysis_text": (
                "case Event::DIRECT:\n"
                "  openCardSelectScreen(CardSelectScreenType::DIRECT, 1);\n"
                "  break;\n"
            ),
            "line_start": 10,
            "line_end": 12,
            "source_path": "src/game/GameContext.cpp",
        }
    }
    current_surface = {
        "aliases": ["Explicit"],
        "ast_sha256": "b" * 64,
        "branches": [],
        "risky_aliases": [],
    }
    expected = {
        "pool_declared_count": 7,
        "runtime_disabled_count": 1,
        "direct_transition_count": 1,
        "event_option_target_count": 5,
        "explicit_event_count": 1,
        "generic_event_count": 4,
    }
    return pool, identities, legal, setup, current_surface, expected


def test_pool_parser_reads_exact_a0_declarations_and_deduplicates_shared_shrines():
    result = parse_a0_pool_declarations(_pool_source())

    assert result["declaration_count"] == 7
    assert [row["scope"] for row in result["declarations"]] == [
        "EventPools::oneTimeEventsAsc0",
        "EventPools::Act1::events",
        "EventPools::Act1::shrines",
        "EventPools::Act2::events",
        "EventPools::Act2::shrines",
        "EventPools::Act3::events",
        "EventPools::Act3::shrines",
    ]
    assert result["pool_declared_events"] == [
        "DIRECT",
        "DISABLED",
        "EXPLICIT",
        "GENERIC",
        "GENERIC_THREE",
        "GENERIC_TWO",
        "SHRINE",
    ]


def test_pool_parser_rejects_duplicate_within_one_declaration():
    with pytest.raises(ReachableSurfaceBlocked) as excinfo:
        parse_a0_pool_declarations(_pool_source(duplicate=True))

    assert excinfo.value.reason == "event_pool_declaration_duplicate"


def test_pool_parser_rejects_unsupported_container_instead_of_guessing():
    with pytest.raises(ReachableSurfaceBlocked) as excinfo:
        parse_a0_pool_declarations(_pool_source(unsupported=True))

    assert excinfo.value.reason == "event_pool_declaration_missing_or_ambiguous"


def test_permanent_disable_parser_requires_flags_and_selection_guards():
    header = """
static constexpr bool disableColosseum = true;
static constexpr bool disableMatchAndKeep = true;
"""
    source = """
case Event::COLOSSEUM:
    return curMapNodeY > 7 && !disableColosseum;
if (shrine != Event::MATCH_AND_KEEP || !disableMatchAndKeep) {
    tempShrines[tempLength++] = shrine;
}
"""

    result = parse_permanent_disable_evidence(header, source)

    assert sorted(result) == ["COLOSSEUM", "MATCH_AND_KEEP"]
    assert all(row["disabled"] is True for row in result.values())


def test_permanent_disable_parser_rejects_guard_drift():
    header = """
static constexpr bool disableColosseum = true;
static constexpr bool disableMatchAndKeep = true;
"""
    source = """
case Event::COLOSSEUM:
    return curMapNodeY > 7;
if (shrine != Event::MATCH_AND_KEEP) {
    tempShrines[tempLength++] = shrine;
}
"""

    with pytest.raises(ReachableSurfaceBlocked) as excinfo:
        parse_permanent_disable_evidence(header, source)

    assert excinfo.value.reason == "permanent_disable_guard_missing"


def test_partition_reconciles_disabled_direct_explicit_and_generic_events():
    pool, identities, legal, setup, current, expected = _partition_inputs()

    result = classify_surface_partitions(
        pool_inventory=pool,
        event_identities=identities,
        legal_summaries=legal,
        setup_cases=setup,
        disabled_evidence={
            "DISABLED": {"disabled": True, "reason": "compile_time_guard"}
        },
        current_surface=current,
        predecessor_contract=_predecessor_contract(),
        expected_counts=expected,
    )

    assert result["counts"] == expected
    assert [row["upstream_enum"] for row in result["disabled_events"]] == [
        "DISABLED"
    ]
    assert [row["upstream_enum"] for row in result["direct_transitions"]] == [
        "DIRECT"
    ]
    assert [row["upstream_enum"] for row in result["explicit_events"]] == [
        "EXPLICIT"
    ]
    assert [row["upstream_enum"] for row in result["generic_events"]] == [
        "GENERIC",
        "GENERIC_THREE",
        "GENERIC_TWO",
        "SHRINE",
    ]


def test_partition_rejects_unexplained_reachable_event_with_no_legal_actions():
    pool, identities, legal, setup, current, expected = _partition_inputs()
    setup.clear()

    with pytest.raises(ReachableSurfaceBlocked) as excinfo:
        classify_surface_partitions(
            pool_inventory=pool,
            event_identities=identities,
            legal_summaries=legal,
            setup_cases=setup,
            disabled_evidence={
                "DISABLED": {"disabled": True, "reason": "compile_time_guard"}
            },
            current_surface=current,
            predecessor_contract=_predecessor_contract(),
            expected_counts=expected,
        )

    assert excinfo.value.reason == "reachable_event_without_legal_actions"
    assert excinfo.value.detail == "DIRECT"


def test_partition_rejects_current_alias_on_generic_identity():
    pool, identities, legal, setup, current, expected = _partition_inputs()
    current["aliases"].append(identities["GENERIC"]["event_id"])

    with pytest.raises(ReachableSurfaceBlocked) as excinfo:
        classify_surface_partitions(
            pool_inventory=pool,
            event_identities=identities,
            legal_summaries=legal,
            setup_cases=setup,
            disabled_evidence={
                "DISABLED": {"disabled": True, "reason": "compile_time_guard"}
            },
            current_surface=current,
            predecessor_contract=_predecessor_contract(),
            expected_counts=expected,
        )

    assert excinfo.value.reason == "generic_event_current_alias_overlap"


def test_successor_contract_preserves_explicit_rules_and_registers_generic_set():
    pool, identities, legal, setup, current, expected = _partition_inputs()
    inventory = classify_surface_partitions(
        pool_inventory=pool,
        event_identities=identities,
        legal_summaries=legal,
        setup_cases=setup,
        disabled_evidence={
            "DISABLED": {"disabled": True, "reason": "compile_time_guard"}
        },
        current_surface=current,
        predecessor_contract=_predecessor_contract(),
        expected_counts=expected,
    )
    identity = {
        "audit_evidence_sha256": "c" * 64,
        "current_ast_sha256": current["ast_sha256"],
        "predecessor_contract_sha256": "d" * 64,
        "simulator_source_sha256": "e" * 64,
    }

    contract = build_successor_contract(
        predecessor_contract=_predecessor_contract(),
        surface_inventory=inventory,
        identity=identity,
    )

    validated = validate_successor_contract(contract)
    assert validated == contract
    assert validated["event_option_target_count"] == 5
    assert len(validated["explicit_events"]) == 1
    assert len(validated["generic_events"]) == 4
    assert validated["authority"] == ALL_FALSE_AUTHORITY


def test_successor_contract_rejects_explicit_generic_overlap():
    pool, identities, legal, setup, current, expected = _partition_inputs()
    inventory = classify_surface_partitions(
        pool_inventory=pool,
        event_identities=identities,
        legal_summaries=legal,
        setup_cases=setup,
        disabled_evidence={
            "DISABLED": {"disabled": True, "reason": "compile_time_guard"}
        },
        current_surface=current,
        predecessor_contract=_predecessor_contract(),
        expected_counts=expected,
    )
    contract = build_successor_contract(
        predecessor_contract=_predecessor_contract(),
        surface_inventory=inventory,
        identity={
            "audit_evidence_sha256": "c" * 64,
            "current_ast_sha256": current["ast_sha256"],
            "predecessor_contract_sha256": "d" * 64,
            "simulator_source_sha256": "e" * 64,
        },
    )
    contract["generic_events"].append(copy.deepcopy(contract["explicit_events"][0]))
    contract["generic_event_count"] += 1

    with pytest.raises(ReachableSurfaceBlocked) as excinfo:
        validate_successor_contract(contract)

    assert excinfo.value.reason == "successor_explicit_generic_overlap"


def test_registration_loader_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"schema_version":"a","schema_version":"b"}\n')

    with pytest.raises(ReachableSurfaceBlocked) as excinfo:
        load_registration(path)

    assert excinfo.value.reason == "reachable_surface_registration_duplicate_key"


def test_artifact_recompute_rejects_extra_managed_file(tmp_path):
    artifacts = {
        "artifact_manifest.json": b"{}\n",
        "configuration.json": b"{}\n",
        "current_partition.json": b"{}\n",
        "metrics.json": b"{}\n",
        "pool_inventory.json": b"{}\n",
        "report.md": b"report\n",
        "successor_contract.json": b"{}\n",
        "target_inventory.json": b"{}\n",
    }
    write_or_verify_artifacts(tmp_path, artifacts, recompute=False)
    (tmp_path / "extra.json").write_text(json.dumps({"extra": True}))

    with pytest.raises(ReachableSurfaceBlocked) as excinfo:
        write_or_verify_artifacts(tmp_path, artifacts, recompute=True)

    assert excinfo.value.reason == "reachable_surface_artifact_set_mismatch"
