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
    resolve_event_option_observation,
    resolve_event_option_semantics,
)
from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    REPO_ROOT
    / "reports"
    / "noncombat_event_option_observation_contract_20260802"
    / "contract.json"
)
CONTRACT_SHA256 = (
    "785e5db26d4cecaa843c7ee3e9e276fdc98c4b77b6a61e88f4520824a50bf3fc"
)
CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _rule(canonical_id: str):
    return next(
        row for row in CONTRACT["events"] if row["canonical_id"] == canonical_id
    )


def _snapshot(
    rule,
    *,
    event_data=0,
    adapter_api_version=ADAPTER_API_VERSION,
    relics=None,
    offered_relics=None,
):
    context = {
        "event_data": event_data,
        "event_id": rule["upstream_event_id"],
        "event_name": rule["event_game_name"],
    }
    if offered_relics is not None:
        context["offered_relics"] = copy.deepcopy(offered_relics)
    return {
        "adapter_api_version": adapter_api_version,
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


def _candidates(rule, indices):
    return [
        {
            "action_id": f"event:{rule['upstream_event_id']}:{index}",
            "available": True,
            "category": "event",
            "kind": "event_option",
            "label": f"{rule['event_game_name']} option {index}",
            "raw": {
                "event_id": rule["upstream_event_id"],
                "idx1": index,
                "idx2": 0,
            },
        }
        for index in indices
    ]


def _provenance():
    identity = event_option_semantics_identity()
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


def _assert_observation(rule, observation, indices, labels):
    assert observation["canonical_id"] == rule["canonical_id"]
    assert observation["current_event_id"] == rule["current_event_id"]
    assert observation["options"] == [
        {
            "choice_index": position,
            "current_position": position,
            "label": label,
            "simulator_choice_index": simulator_index,
            "text": label,
        }
        for position, (simulator_index, label) in enumerate(zip(indices, labels))
    ]


def test_total_semantics_identity_binds_canonical_contract_and_counts():
    identity = event_option_semantics_identity()

    assert identity["contract_id"] == "sts_lightspeed_total_event_observation_v2"
    assert identity["schema_version"] == "sts-lightspeed-event-option-observation-v2"
    assert identity["observation_contract"] == {
        "alias_count": 47,
        "event_count": 25,
        "path": (
            "reports/noncombat_event_option_observation_contract_20260802/"
            "contract.json"
        ),
        "schema_version": "noncombat-event-option-observation-contract-v1",
        "sha256": CONTRACT_SHA256,
    }


def test_all_23_static_rules_resolve_from_contract_without_mutation():
    static_rules = [rule for rule in CONTRACT["events"] if rule["kind"] == "static"]
    assert len(static_rules) == 23

    for rule in static_rules:
        indices = [option["simulator_choice_index"] for option in rule["options"]]
        labels = [option["label"] for option in rule["options"]]
        snapshot = _snapshot(rule)
        candidates = _candidates(rule, indices)
        provenance = _provenance()
        before = copy.deepcopy((snapshot, candidates, provenance))

        observation = resolve_event_option_observation(
            snapshot=snapshot,
            candidates=candidates,
            simulator_provenance=provenance,
        )

        _assert_observation(rule, observation, indices, labels)
        assert (snapshot, candidates, provenance) == before


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
def test_all_cursed_tome_phases_preserve_sparse_indices(
    event_data, indices, labels
):
    rule = _rule("Cursed Tome")

    observation = resolve_event_option_observation(
        snapshot=_snapshot(rule, event_data=event_data),
        candidates=_candidates(rule, indices),
        simulator_provenance=_provenance(),
    )

    _assert_observation(rule, observation, indices, labels)


def test_nloth_labels_bind_exact_v3_offer_records():
    rule = _rule("N'loth")
    relics = [
        {"data": 0, "id": "BURNING_BLOOD", "name": "Burning Blood"},
        {"data": 0, "id": "ANCHOR", "name": "Anchor"},
        {"data": 0, "id": "BAG_OF_MARBLES", "name": "Bag Of Marbles"},
    ]
    offered = [
        {
            "relic_id": "ANCHOR",
            "relic_name": "Anchor",
            "relic_slot": 1,
            "simulator_choice_index": 0,
        },
        {
            "relic_id": "BAG_OF_MARBLES",
            "relic_name": "Bag Of Marbles",
            "relic_slot": 2,
            "simulator_choice_index": 1,
        },
    ]

    observation = resolve_event_option_observation(
        snapshot=_snapshot(rule, relics=relics, offered_relics=offered),
        candidates=_candidates(rule, [0, 1, 2]),
        simulator_provenance=_provenance(),
    )

    _assert_observation(
        rule,
        observation,
        [0, 1, 2],
        ["Offer Anchor", "Offer Bag Of Marbles", "Leave"],
    )


@pytest.mark.parametrize(
    ("adapter_api_version", "mutation", "reason"),
    [
        (
            "sts-lightspeed-noncombat-adapter-v2",
            lambda snapshot: None,
            "event_option_semantics_nloth_context_missing",
        ),
        (
            ADAPTER_API_VERSION,
            lambda snapshot: snapshot["state"]["decision_context"].update(
                {
                    "offered_relics": [
                        {
                            "relic_id": "ANCHOR",
                            "relic_name": "Wrong",
                            "relic_slot": 0,
                            "simulator_choice_index": 0,
                        },
                        {
                            "relic_id": "ANCHOR",
                            "relic_name": "Anchor",
                            "relic_slot": 0,
                            "simulator_choice_index": 1,
                        },
                    ]
                }
            ),
            "event_option_semantics_nloth_relic_mismatch",
        ),
    ],
)
def test_nloth_missing_or_inconsistent_context_fails_closed(
    adapter_api_version, mutation, reason
):
    rule = _rule("N'loth")
    snapshot = _snapshot(
        rule,
        adapter_api_version=adapter_api_version,
        relics=[{"data": 0, "id": "ANCHOR", "name": "Anchor"}],
    )
    mutation(snapshot)

    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_event_option_observation(
            snapshot=snapshot,
            candidates=_candidates(rule, [0, 1, 2]),
            simulator_provenance=_provenance(),
        )

    assert exc_info.value.reason == reason


def test_mindbloom_and_nloth_use_registered_current_ids():
    for canonical_id, current_id in (("MindBloom", "MindBloom"), ("N'loth", "N'loth")):
        rule = _rule(canonical_id)
        if canonical_id == "N'loth":
            relics = [
                {"data": 0, "id": "ANCHOR", "name": "Anchor"},
                {"data": 0, "id": "LANTERN", "name": "Lantern"},
            ]
            offered = [
                {
                    "relic_id": relics[index]["id"],
                    "relic_name": relics[index]["name"],
                    "relic_slot": index,
                    "simulator_choice_index": index,
                }
                for index in (0, 1)
            ]
            snapshot = _snapshot(rule, relics=relics, offered_relics=offered)
        else:
            snapshot = _snapshot(rule)
        indices = [option["simulator_choice_index"] for option in rule["options"]]

        observation = resolve_event_option_observation(
            snapshot=snapshot,
            candidates=_candidates(rule, indices),
            simulator_provenance=_provenance(),
        )

        assert observation["current_event_id"] == current_id


def test_legacy_semantics_wrapper_returns_versioned_rows():
    rule = _rule("Liars Game")
    observation = resolve_event_option_observation(
        snapshot=_snapshot(
            rule, adapter_api_version="sts-lightspeed-noncombat-adapter-v2"
        ),
        candidates=_candidates(rule, [0, 1]),
        simulator_provenance=_provenance(),
    )

    assert resolve_event_option_semantics(
        snapshot=_snapshot(
            rule, adapter_api_version="sts-lightspeed-noncombat-adapter-v2"
        ),
        candidates=_candidates(rule, [0, 1]),
        simulator_provenance=_provenance(),
    ) == observation["options"]


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (
            lambda snapshot, candidates, provenance: candidates.reverse(),
            "event_option_semantics_candidate_order_invalid",
        ),
        (
            lambda snapshot, candidates, provenance: provenance.update(
                {"simulator_commit": "0" * 40}
            ),
            "event_option_semantics_provenance_mismatch",
        ),
        (
            lambda snapshot, candidates, provenance: snapshot["state"][
                "decision_context"
            ].update({"event_name": "Wrong"}),
            "event_option_semantics_event_identity_mismatch",
        ),
    ],
)
def test_total_resolver_rejects_order_provenance_or_identity_drift(mutate, reason):
    rule = _rule("Liars Game")
    snapshot = _snapshot(rule)
    candidates = _candidates(rule, [0, 1])
    provenance = _provenance()
    mutate(snapshot, candidates, provenance)

    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_event_option_observation(
            snapshot=snapshot,
            candidates=candidates,
            simulator_provenance=provenance,
        )

    assert exc_info.value.reason == reason


def test_contract_hash_drift_is_rechecked_without_cache(tmp_path, monkeypatch):
    rule = _rule("Liars Game")
    resolve_event_option_observation(
        snapshot=_snapshot(rule),
        candidates=_candidates(rule, [0, 1]),
        simulator_provenance=_provenance(),
    )
    drifted = tmp_path / "contract.json"
    drifted.write_bytes(CONTRACT_PATH.read_bytes() + b"\n")
    monkeypatch.setattr(semantics_module, "_CONTRACT_PATH", drifted)

    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_event_option_observation(
            snapshot=_snapshot(rule),
            candidates=_candidates(rule, [0, 1]),
            simulator_provenance=_provenance(),
        )

    assert exc_info.value.reason == "event_option_semantics_contract_hash_mismatch"
    assert hashlib.sha256(drifted.read_bytes()).hexdigest() != CONTRACT_SHA256
