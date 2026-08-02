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


def test_cpp_comment_mask_preserves_layout_and_literal_markers():
    source = (
        'active(); // return 0x7; eventData\n'
        'const char *url = "https://example.test/*live*/";\n'
        "const char slash = '/'; /* case 9: */ tail();\n"
        'const char *escaped = "quote: \\" // still literal";\n'
    )

    masked = audit_module._mask_cpp_comments(source)

    assert len(masked) == len(source)
    assert [index for index, char in enumerate(masked) if char == "\n"] == [
        index for index, char in enumerate(source) if char == "\n"
    ]
    assert "return 0x7" not in masked
    assert "case 9" not in masked
    assert '"https://example.test/*live*/"' in masked
    assert '"quote: \\" // still literal"' in masked
    assert "tail();" in masked


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ('R"tag(// not a comment)tag"', "cpp_raw_string_unsupported"),
        ("/* never closed", "cpp_block_comment_unterminated"),
        ('"never closed', "cpp_string_literal_unterminated"),
        ("'never closed", "cpp_character_literal_unterminated"),
    ],
)
def test_cpp_comment_mask_fails_closed_on_ambiguous_lexical_input(source, reason):
    with pytest.raises(AuditBlocked, match=reason):
        audit_module._mask_cpp_comments(source)


def test_cpp_case_summaries_ignore_all_commented_semantic_tokens():
    legal_source = r'''
int search::GameAction::getValidEventSelectBits(const GameContext &gc) {
    switch (gc.curEvent) {
        /* case Event::COMMENTED: return 0xF; */
        case Event::EVENT_A:
            // if (gc.info.eventData == 7) { return 0x6; }
            /* return 0x4; */
            return 0x1;
    }
}
'''
    display_source = r'''
void ConsoleSimulator::printEventActions(std::ostream &os) const {
    switch (gc->curEvent) {
        case Event::EVENT_A:
            // os << "1: [Commented Line] ignored\n";
            /* os << "2: [Commented Block] ignored\n"; */
            os << "0: [Active] text with // and /* markers.\n";
            break;
    }
}
'''
    execution_source = r'''
void GameContext::chooseEventOption(int idx) {
    switch (curEvent) {
        case Event::EVENT_A:
            // case 8: ignored(); break;
            /* case 9: ignored(); break; */
            switch (idx) { case 0: active(); break; }
            break;
    }
}
'''

    legal_cases = index_cpp_event_cases(
        legal_source,
        signature="int search::GameAction::getValidEventSelectBits",
        source_path="legal.cpp",
    )
    display_cases = index_cpp_event_cases(
        display_source,
        signature="void ConsoleSimulator::printEventActions",
        source_path="display.cpp",
    )
    execution_cases = index_cpp_event_cases(
        execution_source,
        signature="void GameContext::chooseEventOption",
        source_path="execution.cpp",
    )

    assert set(legal_cases) == {"EVENT_A"}
    assert legal_cases["EVENT_A"]["text"].count("return") == 3
    assert len(legal_cases["EVENT_A"]["analysis_text"]) == len(
        legal_cases["EVENT_A"]["text"]
    )
    legal = summarize_legal_case(legal_cases["EVENT_A"])
    assert legal["return_expressions"] == ["0x1"]
    assert legal["conditional"] is False
    assert legal["phase_sensitive"] is False
    assert legal["source_sha256"] == sha256_bytes(
        legal_cases["EVENT_A"]["text"].encode("utf-8")
    )
    assert summarize_display_case(display_cases["EVENT_A"])["display_entries"] == [
        {"index": 0, "label": "Active"}
    ]
    assert summarize_execution_case(execution_cases["EVENT_A"])[
        "effect_indices"
    ] == [0]


def _delta_payloads():
    surface = parse_current_event_surface(
        CURRENT_SOURCE, class_name="SimpleAgent", function_name="_choose_event_option"
    )
    successor_rows = build_event_inventory(
        surface, validate_event_registry(_registry(), surface), _upstream_summaries()
    )
    predecessor_rows = copy.deepcopy(successor_rows)
    predecessor_rows[0]["display_labels"]["display_entries"].append(
        {"index": 0, "label": "Commented"}
    )
    predecessor_rows[0]["display_labels"]["display_entries"].sort(
        key=lambda entry: (entry["index"], entry["label"])
    )

    def metrics(registration_sha256):
        return {
            "alias_count": 4,
            "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
            "event_count": 3,
            "label_sensitive_event_count": 2,
            "registration_sha256": registration_sha256,
            "resolver_ready": False,
            "schema_version": "noncombat-event-semantics-coverage-metrics-v1",
            "status_counts": {"source_complete": 2, "source_partial": 1},
            "unaccounted_current_alias_count": 0,
        }

    predecessor_registration = _registration()
    predecessor_registration["output"]["directory"] = "reports/predecessor"
    successor_registration = copy.deepcopy(predecessor_registration)
    successor_registration["implementation"]["commit"] = "a" * 40
    successor_registration["implementation"]["source_sha256"] = "b" * 64
    successor_registration["output"]["directory"] = "reports/successor"
    expected = {
        "added_display_entries": [],
        "alias_count": 4,
        "event_count": 3,
        "removed_display_entries": [
            {"canonical_id": "A", "index": 0, "label": "Commented"}
        ],
        "status_counts": {"source_complete": 2, "source_partial": 1},
        "unaccounted_current_alias_count": 0,
    }
    return {
        "expected": expected,
        "predecessor_inventory": {
            "rows": predecessor_rows,
            "schema_version": "noncombat-event-semantics-coverage-inventory-v1",
        },
        "predecessor_metrics": metrics("c" * 64),
        "predecessor_registration": predecessor_registration,
        "successor_inventory": {
            "rows": successor_rows,
            "schema_version": "noncombat-event-semantics-coverage-inventory-v1",
        },
        "successor_metrics": metrics("d" * 64),
        "successor_registration": successor_registration,
    }


def test_registered_delta_allows_only_declared_display_entry_removals():
    comparison = audit_module.compare_audit_payloads(**_delta_payloads())

    assert comparison["added_display_entries"] == []
    assert comparison["removed_display_entries"] == [
        {"canonical_id": "A", "index": 0, "label": "Commented"}
    ]
    assert comparison["status"] == "passed"


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (
            lambda payloads: payloads["successor_metrics"].__setitem__(
                "event_count", 4
            ),
            "delta_metric_invariant_mismatch",
        ),
        (
            lambda payloads: payloads["successor_metrics"]["authority"].__setitem__(
                "training_authorized", True
            ),
            "delta_authority_mismatch",
        ),
        (
            lambda payloads: (
                payloads["successor_inventory"]["rows"][0]["display_labels"][
                    "display_entries"
                ].append({"index": 9, "label": "Unexpected"}),
                payloads["successor_inventory"]["rows"][0]["display_labels"][
                    "display_indices"
                ].append(9),
            ),
            "delta_display_entries_mismatch",
        ),
        (
            lambda payloads: payloads["successor_registration"]["current"].__setitem__(
                "repository_commit", "f" * 40
            ),
            "delta_registration_immutable_field_mismatch",
        ),
    ],
)
def test_registered_delta_rejects_unexpected_drift(mutation, reason):
    payloads = _delta_payloads()
    mutation(payloads)

    with pytest.raises(AuditBlocked, match=reason):
        audit_module.compare_audit_payloads(**payloads)


def _file_binding(root: Path, path: Path):
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
    }


def _write_delta_fixture(tmp_path: Path):
    payloads = _delta_payloads()
    reports = tmp_path / "reports"
    reports.mkdir()
    predecessor_registration_path = reports / "predecessor_input.json"
    successor_registration_path = reports / "successor_input.json"
    predecessor_registration_path.write_bytes(
        canonical_json_bytes(payloads["predecessor_registration"])
    )
    successor_registration_path.write_bytes(
        canonical_json_bytes(payloads["successor_registration"])
    )
    predecessor_artifacts = build_artifacts(
        registration=payloads["predecessor_registration"],
        registration_sha256=sha256_bytes(predecessor_registration_path.read_bytes()),
        rows=payloads["predecessor_inventory"]["rows"],
    )
    successor_artifacts = build_artifacts(
        registration=payloads["successor_registration"],
        registration_sha256=sha256_bytes(successor_registration_path.read_bytes()),
        rows=payloads["successor_inventory"]["rows"],
    )
    predecessor_dir = tmp_path / "reports" / "predecessor"
    successor_dir = tmp_path / "reports" / "successor"
    write_or_verify_artifacts(predecessor_dir, predecessor_artifacts, recompute=False)
    write_or_verify_artifacts(successor_dir, successor_artifacts, recompute=False)
    delta_registration = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "expected": payloads["expected"],
        "output_path": "reports/predecessor_to_successor_delta.json",
        "predecessor": {
            "directory": "reports/predecessor",
            "manifest": _file_binding(
                tmp_path, predecessor_dir / "artifact_manifest.json"
            ),
            "registration": _file_binding(
                tmp_path, predecessor_registration_path
            ),
        },
        "schema_version": audit_module.DELTA_INPUT_SCHEMA_VERSION,
        "successor": {
            "directory": "reports/successor",
            "registration": _file_binding(tmp_path, successor_registration_path),
        },
    }
    delta_registration_path = reports / "delta_input.json"
    delta_registration_path.write_bytes(canonical_json_bytes(delta_registration))
    return delta_registration, delta_registration_path


def test_registered_delta_report_is_hash_bound_atomic_and_recomputable(tmp_path):
    registration, registration_path = _write_delta_fixture(tmp_path)

    first = audit_module.run_registered_delta(
        registration_path=registration_path,
        repo_root=tmp_path,
        recompute=False,
    )
    second = audit_module.run_registered_delta(
        registration_path=registration_path,
        repo_root=tmp_path,
        recompute=True,
    )

    assert first == second
    assert first["removed_display_entry_count"] == 1
    report_path = tmp_path / registration["output_path"]
    report = json.loads(report_path.read_bytes())
    assert report["comparison"]["status"] == "passed"
    assert report["authority"] == ALL_FALSE_AUTHORITY

    registration["predecessor"]["manifest"]["sha256"] = "f" * 64
    registration_path.write_bytes(canonical_json_bytes(registration))
    with pytest.raises(AuditBlocked, match="bound_file_identity_mismatch"):
        audit_module.run_registered_delta(
            registration_path=registration_path,
            repo_root=tmp_path,
            recompute=True,
        )


@pytest.mark.parametrize(
    ("artifact_name", "field", "value", "reason"),
    [
        ("metrics.json", "unexpected", True, "object_keys_mismatch"),
        (
            "metrics.json",
            "schema_version",
            "unexpected-metrics-schema",
            "delta_metrics_schema_mismatch",
        ),
        (
            "artifact_manifest.json",
            "schema_version",
            "unexpected-manifest-schema",
            "delta_manifest_schema_mismatch",
        ),
        (
            "artifact_manifest.json",
            "status_counts",
            {"source_complete": 3},
            "delta_manifest_metrics_mismatch",
        ),
    ],
)
def test_registered_delta_rejects_artifact_shape_or_schema_drift(
    tmp_path, artifact_name, field, value, reason
):
    registration, registration_path = _write_delta_fixture(tmp_path)
    artifact_path = (
        tmp_path / registration["successor"]["directory"] / artifact_name
    )
    artifact = json.loads(artifact_path.read_bytes())
    artifact[field] = value
    artifact_path.write_bytes(canonical_json_bytes(artifact))

    with pytest.raises(AuditBlocked, match=reason):
        audit_module.run_registered_delta(
            registration_path=registration_path,
            repo_root=tmp_path,
            recompute=True,
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
