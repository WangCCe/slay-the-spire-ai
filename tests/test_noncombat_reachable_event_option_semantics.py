from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

import analysis_scripts.noncombat_event_option_semantics as semantics_module
from analysis_scripts.noncombat_event_option_semantics import (
    EventOptionSemanticsError,
    event_option_semantics_identity,
    reachable_event_option_semantics_identity,
    resolve_event_option_observation,
    resolve_reachable_event_option_observation,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SUCCESSOR_PATH = (
    REPO_ROOT
    / "reports"
    / "noncombat_reachable_event_surface_audit_20260803"
    / "successor_contract.json"
)
SUCCESSOR_SHA256 = (
    "46a1349443fcec4b224de6b2a5d07a5d5d829ee702a8f549cc3917cf85698d6e"
)
PREDECESSOR_SHA256 = (
    "785e5db26d4cecaa843c7ee3e9e276fdc98c4b77b6a61e88f4520824a50bf3fc"
)
SUCCESSOR = json.loads(SUCCESSOR_PATH.read_text(encoding="utf-8"))


def _snapshot(
    event_id: str,
    event_name: str,
    *,
    event_data: int = 0,
    relics=None,
    offered_relics=None,
):
    context = {
        "event_data": event_data,
        "event_id": event_id,
        "event_name": event_name,
    }
    if offered_relics is not None:
        context["offered_relics"] = copy.deepcopy(offered_relics)
    return {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_control": {"history": [], "policy_id": "fake_baseline_v1"},
        "category": "event",
        "decision_count": 0,
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "state": {
            "ascension": 0,
            "decision_context": context,
            "relics": copy.deepcopy(relics or []),
        },
        "terminal": False,
    }


def _candidates(event_id: str, choices: list[tuple[int, str]]):
    return [
        {
            "action_id": f"event:{event_id}:{position}:{simulator_index}",
            "available": True,
            "category": "event",
            "kind": "event_option",
            "label": label,
            "raw": {
                "event_id": event_id,
                "idx1": simulator_index,
                "idx2": 0,
            },
        }
        for position, (simulator_index, label) in enumerate(choices)
    ]


def _provenance():
    identity = reachable_event_option_semantics_identity()
    return {
        "adapter_commit": "a" * 40,
        "adapter_source_sha256": "b" * 64,
        "build": {
            "adapter_api_version": ADAPTER_API_VERSION,
            "compiler": "test compiler",
            "cpp_standard": 201703,
            "python": "3.10.18",
        },
        "module_sha256": "c" * 64,
        "simulator_commit": identity["simulator_commit"],
        "simulator_source_sha256": identity["simulator_source_sha256"],
        "submodules": {"json": "d" * 40, "pybind11": "e" * 40},
    }


def test_reachable_identity_versions_successor_without_changing_predecessor():
    predecessor = event_option_semantics_identity()
    successor = reachable_event_option_semantics_identity()

    assert predecessor["contract_id"] == "sts_lightspeed_total_event_observation_v2"
    assert successor["contract_id"] == "sts_lightspeed_reachable_event_observation_v3"
    assert successor["schema_version"] == "sts-lightspeed-event-option-observation-v3"
    assert successor["observation_contract"] == {
        "disabled_event_count": 2,
        "direct_transition_count": 1,
        "event_option_target_count": 48,
        "explicit_event_count": 25,
        "generic_event_count": 23,
        "partition_sha256": SUCCESSOR["partition_sha256"],
        "path": (
            "reports/noncombat_reachable_event_surface_audit_20260803/"
            "successor_contract.json"
        ),
        "pool_declared_count": 51,
        "schema_version": SUCCESSOR["schema_version"],
        "sha256": SUCCESSOR_SHA256,
    }
    assert successor["predecessor_observation_contract"]["sha256"] == (
        PREDECESSOR_SHA256
    )
    assert successor["current_policy"]["ast_sha256"] == (
        SUCCESSOR["identity"]["current_ast_sha256"]
    )


def test_successor_keeps_predecessor_bytes_and_all_authority_false():
    predecessor_path = REPO_ROOT / event_option_semantics_identity()[
        "observation_contract"
    ]["path"]

    assert hashlib.sha256(predecessor_path.read_bytes()).hexdigest() == (
        PREDECESSOR_SHA256
    )
    assert SUCCESSOR["authority"]
    assert all(value is False for value in SUCCESSOR["authority"].values())
    assert SUCCESSOR["resolver_ready"] is False
    assert SUCCESSOR["adapter_ready"] is False


def test_predecessor_resolver_return_shape_remains_historical():
    rule = next(
        row for row in SUCCESSOR["explicit_events"] if row["canonical_id"] == "Big Fish"
    )
    indices = [option["simulator_choice_index"] for option in rule["options"]]

    observation = resolve_event_option_observation(
        snapshot=_snapshot(rule["upstream_event_id"], rule["event_game_name"]),
        candidates=_candidates(
            rule["upstream_event_id"],
            [(index, f"candidate {index}") for index in indices],
        ),
        simulator_provenance=_provenance(),
    )

    assert set(observation) == {
        "canonical_id",
        "current_event_id",
        "event_data",
        "options",
    }


@pytest.mark.parametrize(
    ("event_data", "choices"),
    [
        (0, [(1, "Reach into the ooze"), (4, "Leave")]),
        (3, [(2, "Try again"), (7, "Back away")]),
    ],
)
def test_scrap_ooze_uses_dynamic_candidate_labels_and_sparse_indices(
    event_data, choices
):
    snapshot = _snapshot("Scrap Ooze", "Scrap Ooze", event_data=event_data)
    candidates = _candidates("Scrap Ooze", choices)
    before = copy.deepcopy((snapshot, candidates))

    observation = resolve_reachable_event_option_observation(
        snapshot=snapshot,
        candidates=candidates,
        simulator_provenance=_provenance(),
    )

    assert observation["canonical_id"] == "Scrap Ooze"
    assert observation["current_event_id"] == "Scrap Ooze"
    assert observation["event_data"] == event_data
    assert observation["semantic_source"] == (
        "sts_lightspeed_reachable_event_observation_v3"
    )
    assert observation["options"] == [
        {
            "choice_index": position,
            "current_position": position,
            "label": label,
            "simulator_choice_index": simulator_index,
            "text": label,
        }
        for position, (simulator_index, label) in enumerate(choices)
    ]
    assert (snapshot, candidates) == before


def test_explicit_rule_precedes_candidate_derived_labels():
    rule = next(
        row for row in SUCCESSOR["explicit_events"] if row["canonical_id"] == "Big Fish"
    )
    indices = [option["simulator_choice_index"] for option in rule["options"]]
    candidates = _candidates(
        rule["upstream_event_id"],
        [(index, f"untrusted native label {index}") for index in indices],
    )

    observation = resolve_reachable_event_option_observation(
        snapshot=_snapshot(rule["upstream_event_id"], rule["event_game_name"]),
        candidates=candidates,
        simulator_provenance=_provenance(),
    )

    assert [row["label"] for row in observation["options"]] == [
        option["label"] for option in rule["options"]
    ]


def test_reachable_successor_preserves_all_static_explicit_rules():
    rules = [row for row in SUCCESSOR["explicit_events"] if row["kind"] == "static"]
    assert len(rules) == 23

    for rule in rules:
        choices = [
            (option["simulator_choice_index"], f"candidate {position}")
            for position, option in enumerate(rule["options"])
        ]
        observation = resolve_reachable_event_option_observation(
            snapshot=_snapshot(
                rule["upstream_event_id"], rule["event_game_name"]
            ),
            candidates=_candidates(rule["upstream_event_id"], choices),
            simulator_provenance=_provenance(),
        )

        assert [row["label"] for row in observation["options"]] == [
            option["label"] for option in rule["options"]
        ]


@pytest.mark.parametrize(
    ("event_data", "indices"),
    [(0, [0, 1]), (1, [2]), (2, [3]), (3, [4]), (4, [5, 6])],
)
def test_reachable_successor_preserves_all_cursed_tome_phases(
    event_data, indices
):
    rule = next(
        row
        for row in SUCCESSOR["explicit_events"]
        if row["kind"] == "cursed_tome_phase"
    )

    observation = resolve_reachable_event_option_observation(
        snapshot=_snapshot(
            rule["upstream_event_id"],
            rule["event_game_name"],
            event_data=event_data,
        ),
        candidates=_candidates(
            rule["upstream_event_id"],
            [(index, f"candidate {index}") for index in indices],
        ),
        simulator_provenance=_provenance(),
    )

    assert [row["simulator_choice_index"] for row in observation["options"]] == (
        indices
    )


def test_reachable_successor_preserves_nloth_dynamic_relic_context():
    rule = next(
        row
        for row in SUCCESSOR["explicit_events"]
        if row["kind"] == "nloth_relic"
    )
    relics = [
        {"data": 0, "id": "ANCHOR", "name": "Anchor"},
        {"data": 0, "id": "LANTERN", "name": "Lantern"},
    ]
    offered = [
        {
            "relic_id": relic["id"],
            "relic_name": relic["name"],
            "relic_slot": index,
            "simulator_choice_index": index,
        }
        for index, relic in enumerate(relics)
    ]

    observation = resolve_reachable_event_option_observation(
        snapshot=_snapshot(
            rule["upstream_event_id"],
            rule["event_game_name"],
            relics=relics,
            offered_relics=offered,
        ),
        candidates=_candidates(
            rule["upstream_event_id"],
            [(0, "candidate 0"), (1, "candidate 1"), (2, "candidate 2")],
        ),
        simulator_provenance=_provenance(),
    )

    assert [row["label"] for row in observation["options"]] == [
        "Offer Anchor",
        "Offer Lantern",
        "Leave",
    ]


def test_unknown_event_does_not_fall_back_to_position_zero():
    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_reachable_event_option_observation(
            snapshot=_snapshot("Unknown Event", "Unknown Event"),
            candidates=_candidates("Unknown Event", [(0, "Choose")]),
            simulator_provenance=_provenance(),
        )

    assert exc_info.value.reason == "event_option_semantics_event_unsupported"


def test_generic_event_name_must_match_registered_identity():
    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_reachable_event_option_observation(
            snapshot=_snapshot("Scrap Ooze", "Wrong Name"),
            candidates=_candidates("Scrap Ooze", [(0, "Reach")]),
            simulator_provenance=_provenance(),
        )

    assert exc_info.value.reason == "event_option_semantics_event_identity_mismatch"


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda rows: rows.reverse(),
            "event_option_semantics_candidate_order_invalid",
        ),
        (
            lambda rows: rows[1]["raw"].update({"idx1": rows[0]["raw"]["idx1"]}),
            "event_option_semantics_candidate_index_duplicate",
        ),
        (
            lambda rows: rows[0]["raw"].update({"event_id": "Wrong"}),
            "event_option_semantics_candidate_event_mismatch",
        ),
        (
            lambda rows: rows[0].update({"label": ""}),
            "event_option_semantics_input_invalid",
        ),
    ],
)
def test_generic_candidate_drift_fails_closed(mutate, reason):
    candidates = _candidates("Scrap Ooze", [(1, "Reach"), (4, "Leave")])
    mutate(candidates)

    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_reachable_event_option_observation(
            snapshot=_snapshot("Scrap Ooze", "Scrap Ooze"),
            candidates=candidates,
            simulator_provenance=_provenance(),
        )

    assert exc_info.value.reason == reason


def test_current_branch_drift_invalidates_generic_proof(tmp_path, monkeypatch):
    source = semantics_module._CURRENT_POLICY_PATH.read_text(encoding="utf-8")
    assert '"Big Fish", "BigFish"' in source
    drifted = tmp_path / "agent.py"
    drifted.write_text(
        source.replace('"Big Fish", "BigFish"', '"Big Fish Drift", "BigFish"', 1),
        encoding="utf-8",
    )
    monkeypatch.setattr(semantics_module, "_CURRENT_POLICY_PATH", drifted)

    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_reachable_event_option_observation(
            snapshot=_snapshot("Scrap Ooze", "Scrap Ooze"),
            candidates=_candidates("Scrap Ooze", [(0, "Reach")]),
            simulator_provenance=_provenance(),
        )

    assert exc_info.value.reason == "event_option_semantics_current_ast_mismatch"


def test_successor_contract_hash_is_rechecked_without_cache(tmp_path, monkeypatch):
    drifted = tmp_path / "successor_contract.json"
    drifted.write_bytes(SUCCESSOR_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(semantics_module, "_REACHABLE_CONTRACT_PATH", drifted)

    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_reachable_event_option_observation(
            snapshot=_snapshot("Scrap Ooze", "Scrap Ooze"),
            candidates=_candidates("Scrap Ooze", [(0, "Reach")]),
            simulator_provenance=_provenance(),
        )

    assert exc_info.value.reason == "event_option_semantics_contract_hash_mismatch"
