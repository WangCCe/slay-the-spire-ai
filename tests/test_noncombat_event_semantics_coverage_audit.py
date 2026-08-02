from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

import analysis_scripts.noncombat_event_semantics_coverage_audit as audit_module
from analysis_scripts.noncombat_event_semantics_coverage_audit import (
    ALL_FALSE_AUTHORITY,
    CANONICAL_ARTIFACT_NAMES,
    SIMULATOR_SOURCE_PATHS,
    AuditBlocked,
    build_artifacts,
    build_event_inventory,
    canonical_json_bytes,
    hash_bound_files,
    hash_simulator_sources,
    index_cpp_event_cases,
    parse_current_event_surface,
    parse_event_identities,
    sha256_bytes,
    summarize_display_case,
    summarize_execution_case,
    summarize_legal_case,
    validate_event_registry,
    validate_registration,
    verify_bound_file,
    verify_registration_identity,
    write_or_verify_artifacts,
)


CURRENT_SOURCE = """
class SimpleAgent:
    def _choose_event_option(self):
        event_id = self.game.event_id
        risky_event_ids = {"Risk", "A"}
        labels_for_selection = self.game.labels
        choice_index = 0
        if event_id in {"A", "AliasA"}:
            for idx, label in enumerate(labels_for_selection):
                if "take" in label.lower():
                    choice_index = idx
                    break
        elif event_id in {"B"}:
            choice_index = 1
        elif event_id in risky_event_ids:
            for idx, label in enumerate(labels_for_selection):
                if "leave" in label.lower():
                    choice_index = idx
                    break
        if event_id in {"A", "AliasA"}:
            self.mode = "after-selection"
        return choice_index
"""


EVENTS_SOURCE = r'''
enum class Event : std::uint8_t {
    INVALID = 0,
    EVENT_A,
    EVENT_B,
    EVENT_RISK,
};
static constexpr const char *eventIdStrings[] = {
    "INVALID",
    "A",
    "B",
    "Risk",
};
static constexpr const char *eventGameNames[] = {
    "INVALID",
    "Event A",
    "Event B",
    "Risk Event",
};
'''


SAVE_SOURCE = r'''
NLOHMANN_JSON_SERIALIZE_ENUM(Event, {
    {Event::INVALID, nullptr},
    {Event::EVENT_A, "A"},
    {Event::EVENT_B, "B"},
    {Event::EVENT_RISK, "Risk"},
})
'''


LEGAL_SOURCE = r'''
int search::GameAction::getValidEventSelectBits(const GameContext &gc) {
    switch (gc.curEvent) {
        case Event::EVENT_A:
        case Event::EVENT_B:
            return 0x3;
        case Event::EVENT_RISK:
            if (gc.info.eventData == 0) {
                return 0b101;
            }
            return 0x7;
    }
}
'''


DISPLAY_SOURCE = r'''
void ConsoleSimulator::printEventActions(std::ostream &os) const {
    switch (gc->curEvent) {
        case Event::EVENT_A:
        case Event::EVENT_B:
            os << "0: [Take] Gain something.\n";
            os << "1: [Leave] Nothing happens.\n";
            break;
        case Event::EVENT_RISK:
            if (gc->info.eventData == 0) {
                os << "0: [Fight] Begin combat.\n";
            }
            os << "2: [Leave] Nothing happens.\n";
            break;
    }
}
'''


EXECUTION_SOURCE = r'''
void GameContext::chooseEventOption(int idx) {
    switch (curEvent) {
        case Event::EVENT_A:
        case Event::EVENT_B:
            switch (idx) {
                case 0: gainGold(10); break;
                case 1: regainControl(); break;
            }
            break;
        case Event::EVENT_RISK:
            if (info.eventData == 0) {
                enterCombat();
            } else {
                regainControl();
            }
            break;
    }
}
'''


def _registry():
    return [
        {"aliases": ["A", "AliasA"], "canonical_id": "A", "upstream_enum": "EVENT_A"},
        {"aliases": ["B"], "canonical_id": "B", "upstream_enum": "EVENT_B"},
        {"aliases": ["Risk"], "canonical_id": "Risk", "upstream_enum": "EVENT_RISK"},
    ]


def _registration():
    binding = {"path": "source.py", "sha256": "1" * 64, "size_bytes": 1}
    simulator_sources = {
        "display_labels": {**binding, "path": "src/sim/ConsoleSimulator.cpp"},
        "event_identities": {**binding, "path": "include/constants/Events.h"},
        "event_save_ids": {**binding, "path": "include/constants/SaveFileMappings.h"},
        "execution": {**binding, "path": "src/game/GameContext.cpp"},
        "legal_actions": {**binding, "path": "src/sim/search/GameAction.cpp"},
    }
    return {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "current": {
            "class_name": "SimpleAgent",
            "function_name": "_choose_event_option",
            "repository_commit": "2" * 40,
            "source": {**binding, "path": "spirecomm/ai/agent.py"},
        },
        "events": _registry(),
        "implementation": {
            "commit": "3" * 40,
            "source_files": [
                "analysis_scripts/noncombat_event_semantics_coverage_audit.py"
            ],
            "source_sha256": "4" * 64,
        },
        "output": {
            "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
            "directory": "reports/static_event_audit",
        },
        "schema_version": "noncombat-event-semantics-coverage-audit-input-v1",
        "simulator": {
            "dirty": True,
            "parent_commit": "5" * 40,
            "root": "D:/simulator",
            "source_file_count": 5,
            "source_files": simulator_sources,
            "source_sha256": "6" * 64,
            "submodules": {"json": "7" * 40, "pybind11": "8" * 40},
        },
    }


def _upstream_summaries():
    identities = parse_event_identities(EVENTS_SOURCE, SAVE_SOURCE)
    legal_cases = index_cpp_event_cases(
        LEGAL_SOURCE,
        signature="int search::GameAction::getValidEventSelectBits",
        source_path="src/sim/search/GameAction.cpp",
    )
    display_cases = index_cpp_event_cases(
        DISPLAY_SOURCE,
        signature="void ConsoleSimulator::printEventActions",
        source_path="src/sim/ConsoleSimulator.cpp",
    )
    execution_cases = index_cpp_event_cases(
        EXECUTION_SOURCE,
        signature="void GameContext::chooseEventOption",
        source_path="src/game/GameContext.cpp",
    )
    return {
        "display": {
            name: summarize_display_case(case) for name, case in display_cases.items()
        },
        "execution": {
            name: summarize_execution_case(case)
            for name, case in execution_cases.items()
        },
        "identities": identities,
        "legal": {
            name: summarize_legal_case(case) for name, case in legal_cases.items()
        },
    }


def test_current_ast_inventory_is_ordered_complete_and_stable():
    first = parse_current_event_surface(
        CURRENT_SOURCE, class_name="SimpleAgent", function_name="_choose_event_option"
    )
    second = parse_current_event_surface(
        "\n" + CURRENT_SOURCE.replace("        event_id", "        # comment\n        event_id"),
        class_name="SimpleAgent",
        function_name="_choose_event_option",
    )

    assert first["aliases"] == ["A", "AliasA", "B", "Risk"]
    assert first["risky_aliases"] == ["A", "Risk"]
    assert [branch["kind"] for branch in first["branches"]] == [
        "explicit",
        "explicit",
        "risky_fallback",
    ]
    assert [branch["label_sensitive"] for branch in first["branches"]] == [
        True,
        False,
        True,
    ]
    assert [branch["ast_sha256"] for branch in first["branches"]] == [
        branch["ast_sha256"] for branch in second["branches"]
    ]


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ("class SimpleAgent: pass", "current_function_missing"),
        (
            CURRENT_SOURCE.replace(
                'elif event_id in {"B"}:', 'elif event_id == "B":'
            ),
            "current_branch_condition_unrepresentable",
        ),
    ],
)
def test_current_ast_inventory_fails_closed(source, reason):
    with pytest.raises(AuditBlocked, match=reason):
        parse_current_event_surface(
            source, class_name="SimpleAgent", function_name="_choose_event_option"
        )


def test_event_registry_requires_exact_alias_and_unique_canonical_mapping():
    surface = parse_current_event_surface(
        CURRENT_SOURCE, class_name="SimpleAgent", function_name="_choose_event_option"
    )
    mapping = validate_event_registry(_registry(), surface)
    assert mapping["AliasA"]["upstream_enum"] == "EVENT_A"

    stale = _registry()
    stale[0]["aliases"].append("Stale")
    with pytest.raises(AuditBlocked, match="event_registry_alias_mismatch"):
        validate_event_registry(stale, surface)

    duplicate = _registry()
    duplicate[1]["aliases"] = ["A", "B"]
    with pytest.raises(AuditBlocked, match="event_registry_alias_duplicate"):
        validate_event_registry(duplicate, surface)

    duplicate_enum = _registry()
    duplicate_enum[1]["upstream_enum"] = "EVENT_A"
    with pytest.raises(AuditBlocked, match="event_registry_upstream_enum_duplicate"):
        validate_event_registry(duplicate_enum, surface)


def test_cpp_identity_and_case_index_preserve_shared_and_conditional_sources():
    upstream = _upstream_summaries()
    assert {
        key: upstream["identities"]["EVENT_A"][key]
        for key in ("event_game_name", "event_id", "save_id")
    } == {
        "event_game_name": "Event A",
        "event_id": "A",
        "save_id": "A",
    }
    assert upstream["identities"]["EVENT_A"]["source_refs"]["enum"] == {
        "line": 4,
        "path": "include/constants/Events.h",
    }
    assert upstream["legal"]["EVENT_A"]["case_group"] == ["EVENT_A", "EVENT_B"]
    assert upstream["legal"]["EVENT_A"]["legal_indices"] == [0, 1]
    assert upstream["legal"]["EVENT_RISK"]["legal_indices"] == [0, 1, 2]
    assert upstream["legal"]["EVENT_RISK"]["phase_sensitive"] is True
    assert upstream["display"]["EVENT_A"]["display_entries"] == [
        {"index": 0, "label": "Take"},
        {"index": 1, "label": "Leave"},
    ]
    assert upstream["execution"]["EVENT_A"]["effect_indices"] == [0, 1]
    assert upstream["execution"]["EVENT_RISK"]["conditional"] is True


def test_cpp_case_index_rejects_duplicate_event_case():
    source = LEGAL_SOURCE.replace(
        "    }\n}", "        case Event::EVENT_A: return 1;\n    }\n}"
    )
    with pytest.raises(AuditBlocked, match="cpp_event_case_duplicate"):
        index_cpp_event_cases(
            source,
            signature="int search::GameAction::getValidEventSelectBits",
            source_path="legal.cpp",
        )


def test_event_inventory_reconciles_complete_and_partial_rows():
    surface = parse_current_event_surface(
        CURRENT_SOURCE, class_name="SimpleAgent", function_name="_choose_event_option"
    )
    registry = validate_event_registry(_registry(), surface)
    rows = build_event_inventory(surface, registry, _upstream_summaries())

    by_id = {row["canonical_id"]: row for row in rows}
    assert list(by_id) == ["A", "B", "Risk"]
    assert by_id["A"]["status"] == "source_complete"
    assert by_id["A"]["resolver_ready"] is False
    assert by_id["Risk"]["status"] == "source_partial"
    assert by_id["Risk"]["blockers"] == ["display_indices_missing:1"]


def test_registration_is_strict_and_authority_is_all_false():
    registration = _registration()
    assert validate_registration(registration) == registration

    registration["authority"]["training_authorized"] = True
    with pytest.raises(AuditBlocked, match="authority_must_be_all_false"):
        validate_registration(registration)

    registration = _registration()
    registration["implementation"]["source_files"].append("unexpected.py")
    with pytest.raises(AuditBlocked, match="implementation_source_files_mismatch"):
        validate_registration(registration)


def test_bound_file_verification_detects_source_drift(tmp_path):
    path = tmp_path / "source.py"
    path.write_text("original\n", encoding="utf-8")
    binding = {
        "path": "source.py",
        "sha256": sha256_bytes(path.read_bytes()),
        "size_bytes": path.stat().st_size,
    }
    assert verify_bound_file(tmp_path, binding, repository_relative=True) == path

    path.write_text("changed\n", encoding="utf-8")
    with pytest.raises(AuditBlocked, match="bound_file_identity_mismatch"):
        verify_bound_file(tmp_path, binding, repository_relative=True)


def test_registration_identity_binds_full_and_selected_sources(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    simulator = tmp_path / "simulator"
    implementation_path = (
        repo / "analysis_scripts" / "noncombat_event_semantics_coverage_audit.py"
    )
    current_path = repo / "spirecomm" / "ai" / "agent.py"
    implementation_path.parent.mkdir(parents=True)
    current_path.parent.mkdir(parents=True)
    implementation_path.write_text("audit implementation\n", encoding="utf-8")
    current_path.write_text(CURRENT_SOURCE, encoding="utf-8")
    for relative in SIMULATOR_SOURCE_PATHS.values():
        path = simulator / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"source: {relative}\n", encoding="utf-8")
    for name in ("json", "pybind11"):
        (simulator / name).mkdir(parents=True)

    registration = _registration()
    registration["implementation"]["source_sha256"] = hash_bound_files(
        repo, registration["implementation"]["source_files"]
    )
    registration["current"]["source"] = {
        "path": "spirecomm/ai/agent.py",
        "sha256": sha256_bytes(current_path.read_bytes()),
        "size_bytes": current_path.stat().st_size,
    }
    registration["simulator"]["root"] = str(simulator.resolve())
    source_hash, source_count = hash_simulator_sources(simulator)
    registration["simulator"]["source_sha256"] = source_hash
    registration["simulator"]["source_file_count"] = source_count
    for name, relative in SIMULATOR_SOURCE_PATHS.items():
        path = simulator / relative
        registration["simulator"]["source_files"][name] = {
            "path": relative,
            "sha256": sha256_bytes(path.read_bytes()),
            "size_bytes": path.stat().st_size,
        }

    def fake_git(path, *args):
        resolved = Path(path).resolve()
        if args == ("status", "--porcelain"):
            assert resolved == simulator.resolve()
            return " M selected-source"
        assert args == ("rev-parse", "HEAD")
        if resolved == simulator.resolve():
            return registration["simulator"]["parent_commit"]
        return registration["simulator"]["submodules"][resolved.name]

    monkeypatch.setattr(audit_module, "_git", fake_git)
    monkeypatch.setattr(
        audit_module, "_verify_sources_at_commit", lambda *args, **kwargs: None
    )
    identities = verify_registration_identity(validate_registration(registration), repo)
    assert identities["current_source"] == current_path.resolve()
    assert set(identities["simulator_sources"]) == set(SIMULATOR_SOURCE_PATHS)

    selected = simulator / SIMULATOR_SOURCE_PATHS["legal_actions"]
    selected.write_text("drifted\n", encoding="utf-8")
    with pytest.raises(AuditBlocked, match="simulator_full_source_identity_mismatch"):
        verify_registration_identity(validate_registration(registration), repo)


def test_artifacts_are_canonical_recomputable_and_reject_extra_files(tmp_path):
    surface = parse_current_event_surface(
        CURRENT_SOURCE, class_name="SimpleAgent", function_name="_choose_event_option"
    )
    rows = build_event_inventory(
        surface, validate_event_registry(_registry(), surface), _upstream_summaries()
    )
    artifacts = build_artifacts(
        registration=_registration(), registration_sha256="9" * 64, rows=rows
    )
    assert list(artifacts) == list(CANONICAL_ARTIFACT_NAMES)
    metrics = json.loads(artifacts["metrics.json"])
    manifest = json.loads(artifacts["artifact_manifest.json"])
    assert metrics["authority"] == ALL_FALSE_AUTHORITY
    assert metrics["resolver_ready"] is False
    assert manifest["artifact_hashes"]["metrics.json"] == sha256_bytes(
        artifacts["metrics.json"]
    )

    output = tmp_path / "output"
    write_or_verify_artifacts(output, artifacts, recompute=False)
    write_or_verify_artifacts(output, artifacts, recompute=True)
    (output / "extra.txt").write_text("unexpected", encoding="utf-8")
    with pytest.raises(AuditBlocked, match="artifact_recompute_mismatch"):
        write_or_verify_artifacts(output, artifacts, recompute=True)


def test_audit_import_does_not_load_gameplay_or_native_modules():
    source = Path(audit_module.__file__).read_text(encoding="utf-8")
    imported_modules = {
        node.module
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    imported_modules.update(
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not any(name.startswith("spirecomm") for name in imported_modules)
    assert "analysis_scripts.noncombat_simulator_adapter" not in imported_modules
    assert "sts_lightspeed_noncombat_adapter" not in imported_modules
    assert canonical_json_bytes({"b": 1, "a": 2}) == b'{\n  "a": 2,\n  "b": 1\n}\n'
