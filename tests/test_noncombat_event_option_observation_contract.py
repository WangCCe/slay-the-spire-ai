from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from analysis_scripts.noncombat_event_option_observation_contract import (
    ALL_FALSE_AUTHORITY,
    CANONICAL_ARTIFACT_NAMES,
    EVENT_RULES,
    INPUT_SCHEMA_VERSION,
    ContractBlocked,
    build_artifacts,
    build_event_observation,
    canonical_json_bytes,
    load_canonical_json,
    load_registration,
    registry_sha256,
    sha256_bytes,
    validate_contract_registry,
    validate_registration,
    verify_bound_file,
    write_or_verify_artifacts,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
R2_INVENTORY = (
    REPO_ROOT
    / "reports"
    / "noncombat_event_semantics_coverage_audit_20260802_r2"
    / "event_inventory.json"
)


def _binding(path="reports/example.json", *, sha256="a" * 64, size_bytes=1):
    return {"path": path, "sha256": sha256, "size_bytes": size_bytes}


def _registration():
    upstream = {
        name: _binding(f"upstream/{name}.cpp")
        for name in (
            "display_labels",
            "event_identities",
            "event_save_ids",
            "execution",
            "legal_actions",
        )
    }
    return {
        "audit": {
            "directory": "reports/audit_r2",
            "inventory": _binding("reports/audit_r2/event_inventory.json"),
            "manifest": _binding("reports/audit_r2/artifact_manifest.json"),
            "registration": _binding("reports/audit_r2_input.json"),
        },
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "expected": {
            "alias_count": 47,
            "event_count": 25,
            "registry_sha256": registry_sha256(),
            "rule_kind_counts": {
                "cursed_tome_phase": 1,
                "nloth_relic": 1,
                "static": 23,
            },
            "unaccounted_surface_count": 0,
        },
        "implementation": {
            "commit": "b" * 40,
            "source_files": [
                "analysis_scripts/noncombat_event_option_observation_contract.py"
            ],
            "source_sha256": "c" * 64,
        },
        "output": {
            "artifact_names": list(CANONICAL_ARTIFACT_NAMES),
            "directory": "reports/contract",
        },
        "schema_version": INPUT_SCHEMA_VERSION,
        "source_identity": {
            "current_repository_commit": "d" * 40,
            "current_source": _binding("spirecomm/ai/agent.py"),
            "simulator_parent_commit": "e" * 40,
            "simulator_source_sha256": "f" * 64,
            "upstream_source_files": upstream,
        },
    }


def _candidate(event_id, simulator_choice_index):
    return {
        "event_id": event_id,
        "simulator_choice_index": simulator_choice_index,
    }


def _rule(canonical_id):
    return next(rule for rule in EVENT_RULES if rule["canonical_id"] == canonical_id)


def test_validator_import_graph_excludes_runtime_policy_and_native_modules():
    source_path = (
        REPO_ROOT
        / "analysis_scripts"
        / "noncombat_event_option_observation_contract.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")

    assert not any(
        name.startswith(("analysis_scripts.", "spirecomm", "torch"))
        for name in imported
    )


def test_registration_is_strict_and_all_authority_is_false(tmp_path):
    registration = _registration()

    assert validate_registration(registration) == registration

    registration["authority"]["training_authorized"] = True
    with pytest.raises(ContractBlocked, match="contract_authority_mismatch"):
        validate_registration(registration)

    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema_version": 1, "schema_version": 2}\n')
    with pytest.raises(ContractBlocked, match="duplicate_json_key"):
        load_registration(duplicate)


def test_bound_file_and_canonical_json_fail_closed(tmp_path):
    source = tmp_path / "source.json"
    source.write_bytes(canonical_json_bytes({"value": 1}))
    binding = {
        "path": "source.json",
        "sha256": sha256_bytes(source.read_bytes()),
        "size_bytes": source.stat().st_size,
    }

    assert verify_bound_file(tmp_path, binding) == source
    assert load_canonical_json(source, "source") == {"value": 1}

    source.write_text('{"value": 1}', encoding="utf-8")
    with pytest.raises(ContractBlocked, match="bound_file_identity_mismatch"):
        verify_bound_file(tmp_path, binding)
    with pytest.raises(ContractBlocked, match="contract_artifact_not_canonical"):
        load_canonical_json(source, "source")


def test_artifact_writer_rejects_extra_managed_file(tmp_path):
    artifacts = {name: name.encode("ascii") for name in CANONICAL_ARTIFACT_NAMES}
    output = tmp_path / "output"

    write_or_verify_artifacts(output, artifacts, recompute=False)
    write_or_verify_artifacts(output, artifacts, recompute=True)
    (output / "extra.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ContractBlocked, match="artifact_recompute_mismatch"):
        write_or_verify_artifacts(output, artifacts, recompute=True)


def test_registry_reconciles_all_corrected_r2_events_and_aliases():
    inventory = json.loads(R2_INVENTORY.read_bytes())

    contract = validate_contract_registry(EVENT_RULES, inventory)

    assert contract["event_count"] == 25
    assert contract["alias_count"] == 47
    assert contract["unaccounted_surface_count"] == 0
    assert contract["rule_kind_counts"] == {
        "cursed_tome_phase": 1,
        "nloth_relic": 1,
        "static": 23,
    }
    mindbloom = next(
        row for row in contract["events"] if row["canonical_id"] == "MindBloom"
    )
    assert mindbloom["upstream_event_id"] == "Mindbloom"
    assert mindbloom["current_event_id"] == "MindBloom"


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda rules: rules.pop(), "contract_registry_event_identity_mismatch"),
        (
            lambda rules: rules[0]["aliases"].append("Unexpected"),
            "contract_registry_alias_mismatch",
        ),
        (
            lambda rules: rules[0]["options"][0].__setitem__("label", "Wrong"),
            "contract_registry_static_label_mismatch",
        ),
    ],
)
def test_registry_rejects_missing_alias_or_static_label_drift(mutation, reason):
    inventory = json.loads(R2_INVENTORY.read_bytes())
    rules = copy.deepcopy(EVENT_RULES)
    mutation(rules)

    with pytest.raises(ContractBlocked, match=reason):
        validate_contract_registry(rules, inventory)


def test_observation_mapping_is_reversible_for_contiguous_and_sparse_indices():
    contiguous = build_event_observation(
        _rule("Big Fish"),
        candidates=[
            _candidate("Big Fish", 0),
            _candidate("Big Fish", 1),
            _candidate("Big Fish", 2),
        ],
        event_data=0,
    )
    sparse = build_event_observation(
        _rule("The Cleric"),
        candidates=[_candidate("The Cleric", 2)],
        event_data=0,
    )

    assert [row["current_position"] for row in contiguous["options"]] == [0, 1, 2]
    assert [row["simulator_choice_index"] for row in contiguous["options"]] == [
        0,
        1,
        2,
    ]
    assert sparse["options"] == [
        {
            "current_position": 0,
            "label": "Leave",
            "simulator_choice_index": 2,
        }
    ]

    with pytest.raises(ContractBlocked, match="contract_candidate_index_unsupported"):
        build_event_observation(
            _rule("The Cleric"),
            candidates=[_candidate("The Cleric", 9)],
            event_data=0,
        )


@pytest.mark.parametrize(
    ("event_data", "indices", "labels"),
    [
        (0, [0, 1], ["Read", "Leave"]),
        (1, [2], ["Continue"]),
        (2, [3], ["Continue"]),
        (3, [4], ["Continue"]),
        (4, [5, 6], ["Take", "Stop"]),
    ],
)
def test_cursed_tome_phase_table_is_exact(event_data, indices, labels):
    observation = build_event_observation(
        _rule("Cursed Tome"),
        candidates=[_candidate("Cursed Tome", index) for index in indices],
        event_data=event_data,
    )

    assert [row["simulator_choice_index"] for row in observation["options"]] == indices
    assert [row["label"] for row in observation["options"]] == labels


@pytest.mark.parametrize(
    ("event_data", "indices", "reason"),
    [
        (5, [], "contract_event_phase_unsupported"),
        (2, [2], "contract_event_phase_candidates_mismatch"),
        (0, [1, 0], "contract_candidate_order_invalid"),
    ],
)
def test_cursed_tome_rejects_unknown_phase_or_candidate_drift(
    event_data, indices, reason
):
    with pytest.raises(ContractBlocked, match=reason):
        build_event_observation(
            _rule("Cursed Tome"),
            candidates=[_candidate("Cursed Tome", index) for index in indices],
            event_data=event_data,
        )


def test_nloth_labels_bind_exact_offered_relic_records():
    relics = [
        {"id": "BURNING_BLOOD", "name": "Burning Blood"},
        {"id": "ANCHOR", "name": "Anchor"},
        {"id": "BLACK_BLOOD", "name": "Black Blood"},
    ]
    offered = [
        {
            "relic_id": "BURNING_BLOOD",
            "relic_name": "Burning Blood",
            "relic_slot": 0,
            "simulator_choice_index": 0,
        },
        {
            "relic_id": "BLACK_BLOOD",
            "relic_name": "Black Blood",
            "relic_slot": 2,
            "simulator_choice_index": 1,
        },
    ]

    observation = build_event_observation(
        _rule("N'loth"),
        candidates=[
            _candidate("Nloth", 0),
            _candidate("Nloth", 1),
            _candidate("Nloth", 2),
        ],
        event_data=0,
        snapshot_relics=relics,
        offered_relics=offered,
    )

    assert [row["label"] for row in observation["options"]] == [
        "Offer Burning Blood",
        "Offer Black Blood",
        "Leave",
    ]

    with pytest.raises(ContractBlocked, match="contract_nloth_context_missing"):
        build_event_observation(
            _rule("N'loth"),
            candidates=[
                _candidate("Nloth", 0),
                _candidate("Nloth", 1),
                _candidate("Nloth", 2),
            ],
            event_data=0,
        )

    offered[1]["relic_name"] = "Anchor"
    with pytest.raises(ContractBlocked, match="contract_nloth_relic_mismatch"):
        build_event_observation(
            _rule("N'loth"),
            candidates=[
                _candidate("Nloth", 0),
                _candidate("Nloth", 1),
                _candidate("Nloth", 2),
            ],
            event_data=0,
            snapshot_relics=relics,
            offered_relics=offered,
        )


def test_mindbloom_normalizes_current_identity_and_unknown_event_fails():
    observation = build_event_observation(
        _rule("MindBloom"),
        candidates=[_candidate("Mindbloom", 0)],
        event_data=0,
    )

    assert observation["current_event_id"] == "MindBloom"
    assert observation["upstream_event_id"] == "Mindbloom"

    with pytest.raises(ContractBlocked, match="contract_candidate_event_mismatch"):
        build_event_observation(
            _rule("MindBloom"),
            candidates=[_candidate("Mind Bloom", 0)],
            event_data=0,
        )


def test_contract_artifacts_keep_readiness_and_authority_false():
    inventory = json.loads(R2_INVENTORY.read_bytes())
    contract = validate_contract_registry(EVENT_RULES, inventory)

    artifacts = build_artifacts(
        registration=_registration(),
        registration_sha256="1" * 64,
        contract=contract,
    )

    assert set(artifacts) == set(CANONICAL_ARTIFACT_NAMES)
    metrics = json.loads(artifacts["metrics.json"])
    assert metrics["authority"] == ALL_FALSE_AUTHORITY
    assert metrics["adapter_ready"] is False
    assert metrics["resolver_ready"] is False
    assert metrics["event_count"] == 25
    assert metrics["alias_count"] == 47
