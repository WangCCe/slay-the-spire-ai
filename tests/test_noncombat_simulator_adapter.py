from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    EventOptionSemanticsError,
    NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    TRANSITION_SCHEMA_VERSION,
    NativeSimulatorEnvironment,
    SimulatorAdapterError,
    build_transition,
    collect_provenance,
    event_option_semantics_identity,
    hash_compiled_simulator_sources,
    load_native_module,
    resolve_event_option_semantics,
    validate_candidates,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "noncombat_simulator_adapter"
    / "historical_prefixes_20260802.json"
)


def _snapshot(category: str | None, *, terminal: bool = False, floor: int = 1):
    return {
        "adapter_api_version": ADAPTER_API_VERSION,
        "baseline_control": {
            "history": ["combat:CULTIST"],
            "policy_id": "fake_baseline_v1",
        },
        "category": category,
        "decision_count": 2,
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "state": {"floor": floor, "outcome": "player_loss" if terminal else "undecided"},
        "terminal": terminal,
    }


def _candidate(action_id: str = "route:map_node:1:0"):
    return {
        "action_id": action_id,
        "available": True,
        "category": "route",
        "kind": "map_node",
        "label": "M@1,0",
        "raw": {"x": 1, "y": 0},
    }


def _provenance():
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
        "simulator_commit": "d" * 40,
        "simulator_source_sha256": "e" * 64,
        "submodules": {"json": "f" * 40, "pybind11": "1" * 40},
    }


def _event_snapshot(*, ascension=0, event_data=0, event_id="Liars Game"):
    snapshot = _snapshot("event")
    snapshot["state"].update(
        {
            "ascension": ascension,
            "decision_context": {
                "event_data": event_data,
                "event_id": event_id,
                "event_name": "The Ssssserpent",
            },
        }
    )
    return snapshot


def _event_candidate(index, *, action_id=None):
    return {
        "action_id": action_id or f"event:the_ssssserpent:option:{index}",
        "available": True,
        "category": "event",
        "kind": "event_option",
        "label": f"The Ssssserpent option {index}",
        "raw": {"event_id": "Liars Game", "idx1": index, "idx2": 0},
    }


def _event_semantics_provenance():
    provenance = _provenance()
    identity = event_option_semantics_identity()
    provenance["simulator_commit"] = identity["simulator_commit"]
    provenance["simulator_source_sha256"] = identity["simulator_source_sha256"]
    return provenance


@pytest.mark.parametrize(
    ("ascension", "expected_text"),
    [
        (0, "Gain 175 Gold. Become Cursed - Doubt."),
        (15, "Gain 150 Gold. Become Cursed - Doubt."),
    ],
)
def test_liars_game_semantics_are_exact_source_bound_and_non_mutating(
    ascension, expected_text
):
    snapshot = _event_snapshot(ascension=ascension)
    candidates = [_event_candidate(0), _event_candidate(1)]
    provenance = _event_semantics_provenance()
    before_snapshot = json.dumps(snapshot, sort_keys=True)
    before_candidates = json.dumps(candidates, sort_keys=True)
    before_provenance = json.dumps(provenance, sort_keys=True)

    semantics = resolve_event_option_semantics(
        snapshot=snapshot,
        candidates=candidates,
        simulator_provenance=provenance,
    )

    assert semantics == [
        {"choice_index": 0, "label": "Agree", "text": expected_text},
        {"choice_index": 1, "label": "Disagree", "text": "Nothing happens."},
    ]
    assert json.dumps(snapshot, sort_keys=True) == before_snapshot
    assert json.dumps(candidates, sort_keys=True) == before_candidates
    assert json.dumps(provenance, sort_keys=True) == before_provenance


@pytest.mark.parametrize(
    ("snapshot", "candidates", "reason"),
    [
        (
            _event_snapshot(event_id="Big Fish"),
            [_event_candidate(0), _event_candidate(1)],
            "event_option_semantics_event_unsupported",
        ),
        (
            _event_snapshot(event_data=1),
            [_event_candidate(0), _event_candidate(1)],
            "event_option_semantics_phase_unsupported",
        ),
        (
            _event_snapshot(),
            [_event_candidate(0)],
            "event_option_semantics_candidate_indices_mismatch",
        ),
        (
            _event_snapshot(),
            [
                _event_candidate(0),
                _event_candidate(0, action_id="event:the_ssssserpent:option:duplicate"),
            ],
            "event_option_semantics_candidate_index_duplicate",
        ),
    ],
)
def test_event_semantics_reject_unsupported_or_incomplete_state(
    snapshot, candidates, reason
):
    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_event_option_semantics(
            snapshot=snapshot,
            candidates=candidates,
            simulator_provenance=_event_semantics_provenance(),
        )

    assert exc_info.value.reason == reason


@pytest.mark.parametrize("field", ["simulator_commit", "simulator_source_sha256"])
def test_event_semantics_reject_simulator_identity_drift(field):
    provenance = _event_semantics_provenance()
    provenance[field] = "0" * len(provenance[field])

    with pytest.raises(EventOptionSemanticsError) as exc_info:
        resolve_event_option_semantics(
            snapshot=_event_snapshot(),
            candidates=[_event_candidate(0), _event_candidate(1)],
            simulator_provenance=provenance,
        )

    assert exc_info.value.reason == "event_option_semantics_provenance_mismatch"


class _FakeNativeBaselineEnvironment:
    def __init__(self, *, mutate_on_query: bool = False):
        self._snapshot = _snapshot("route")
        self._candidates = [_candidate()]
        self._mutate_on_query = mutate_on_query

    def snapshot_json(self):
        return json.dumps(self._snapshot, sort_keys=True)

    def legal_actions_json(self):
        return json.dumps(self._candidates, sort_keys=True)

    def native_baseline_action_json(self):
        if self._mutate_on_query:
            self._snapshot["decision_count"] += 1
        return json.dumps(
            {
                "action_id": self._candidates[0]["action_id"],
                "category": "route",
                "policy_id": NATIVE_TARGET_POLICY_ID,
                "schema_version": NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
            },
            sort_keys=True,
        )

    def step_native_baseline(self):
        action_id = self._candidates[0]["action_id"]
        self._snapshot = _snapshot(None, terminal=True, floor=2)
        return action_id


def test_native_baseline_wrapper_is_candidate_legal_and_non_mutating():
    environment = NativeSimulatorEnvironment(
        _FakeNativeBaselineEnvironment(),
        _provenance(),
    )
    before = environment.snapshot()
    before_candidates = environment.legal_actions()

    first = environment.native_baseline_action()
    second = environment.native_baseline_action()

    assert first == second == {
        "action_id": "route:map_node:1:0",
        "category": "route",
        "policy_id": NATIVE_TARGET_POLICY_ID,
        "schema_version": NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
    }
    assert environment.snapshot() == before
    assert environment.legal_actions() == before_candidates

    transition = environment.step_native_baseline()
    assert transition["selected_action_id"] == first["action_id"]
    assert transition["successor"]["terminal"] is True


def test_native_baseline_wrapper_rejects_query_side_effects():
    environment = NativeSimulatorEnvironment(
        _FakeNativeBaselineEnvironment(mutate_on_query=True),
        _provenance(),
    )

    with pytest.raises(SimulatorAdapterError, match="mutated source snapshot"):
        environment.native_baseline_action()


def test_transition_schema_keeps_simulator_evidence_separate():
    transition = build_transition(
        before=_snapshot("route"),
        candidates=[_candidate()],
        selected_action_id="route:map_node:1:0",
        after=_snapshot(None, terminal=True, floor=2),
        provenance=_provenance(),
    )

    assert transition["schema_version"] == TRANSITION_SCHEMA_VERSION
    assert transition["source_type"] == SOURCE_TYPE
    assert transition["evidence_class"] == "simulator_transition"
    assert set(transition["training_authority"].values()) == {False}
    assert set(transition["live_evidence"].values()) == {False}
    assert transition["baseline_control"]["policy_id"] == "fake_baseline_v1"


def test_transition_requires_selected_candidate_and_unique_ids():
    duplicate = [_candidate(), _candidate()]
    with pytest.raises(SimulatorAdapterError, match="duplicate candidate"):
        validate_candidates(duplicate, category="route")

    with pytest.raises(SimulatorAdapterError, match="not a reported candidate"):
        build_transition(
            before=_snapshot("route"),
            candidates=[_candidate()],
            selected_action_id="route:map_node:3:0",
            after=_snapshot("route"),
            provenance=_provenance(),
        )


def test_transition_rejects_missing_physical_provenance():
    provenance = _provenance()
    del provenance["simulator_source_sha256"]
    with pytest.raises(SimulatorAdapterError, match="simulator_source_sha256"):
        build_transition(
            before=_snapshot("route"),
            candidates=[_candidate()],
            selected_action_id="route:map_node:1:0",
            after=_snapshot("route"),
            provenance=provenance,
        )


def test_compiled_source_hash_is_path_and_content_bound(tmp_path):
    include = tmp_path / "include"
    source = tmp_path / "src"
    include.mkdir()
    source.mkdir()
    (include / "a.h").write_text("alpha\n", encoding="utf-8")
    (source / "b.cpp").write_text("beta\n", encoding="utf-8")

    first, count = hash_compiled_simulator_sources(tmp_path)
    second, second_count = hash_compiled_simulator_sources(tmp_path)
    assert first == second
    assert count == second_count == 2

    (source / "b.cpp").write_text("changed\n", encoding="utf-8")
    changed, _ = hash_compiled_simulator_sources(tmp_path)
    assert changed != first


def test_historical_prefix_fixture_is_frozen_and_complete():
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture["schema_version"] == "sts-lightspeed-historical-prefix-v1"
    assert len(fixture["runs"]) == 6
    assert len({run["run_file"] for run in fixture["runs"]}) == 6
    assert sum(len(run["decisions"]) for run in fixture["runs"]) == 12
    for run in fixture["runs"]:
        assert len(run["sha256"]) == 64
        assert run["size_bytes"] > 0
        assert [decision["floor"] for decision in run["decisions"]] == [0, 1]
        for decision in run["decisions"]:
            assert decision["candidates"] == sorted(decision["candidates"])
            assert decision["picked"] in decision["candidates"]


def _integration_settings():
    module_path = os.environ.get("STS_LIGHTSPEED_ADAPTER_MODULE")
    simulator_root = os.environ.get("STS_LIGHTSPEED_ROOT")
    mingw_bin = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    if not module_path or not simulator_root or not mingw_bin:
        pytest.skip("set STS_LIGHTSPEED_ADAPTER_MODULE, STS_LIGHTSPEED_ROOT, and STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(module_path, dll_directories=[mingw_bin])
    provenance = collect_provenance(
        simulator_repo=simulator_root,
        module_path=module_path,
        adapter_repo=REPO_ROOT,
        adapter_source_paths=[
            REPO_ROOT / "analysis_scripts" / "noncombat_simulator_adapter.py",
            REPO_ROOT / "analysis_scripts" / "noncombat_simulator_fit.py",
            REPO_ROOT / "simulator_adapters" / "sts_lightspeed" / "CMakeLists.txt",
            REPO_ROOT / "simulator_adapters" / "sts_lightspeed" / "noncombat_adapter.cpp",
        ],
        native_module=module,
    )
    return module, provenance


def _run_first_candidate_policy(module, seed: int):
    environment = module.Environment(seed, 0)
    categories: set[str] = set()
    decisions = 0
    while not environment.terminal():
        assert decisions < 500
        snapshot = json.loads(environment.snapshot_json())
        actions = json.loads(environment.legal_actions_json())
        categories.add(snapshot["category"])
        environment.step(actions[0]["action_id"])
        decisions += 1
    terminal = json.loads(environment.snapshot_json())
    return {
        "categories": sorted(categories),
        "decisions": decisions,
        "floor": terminal["state"]["floor"],
        "outcome": terminal["state"]["outcome"],
    }


def test_native_adapter_clone_legality_and_four_category_smoke():
    module, provenance = _integration_settings()
    environment = NativeSimulatorEnvironment(module.Environment(0, 0), provenance)
    categories: set[str] = set()
    checked_candidates = 0

    while not environment.snapshot()["terminal"]:
        before = environment.snapshot()
        before_bytes = environment.native.snapshot_json()
        actions = environment.legal_actions()
        categories.add(before["category"])
        for action in actions:
            branch = environment.clone()
            transition = branch.step(action["action_id"])
            assert transition["selected_action_id"] == action["action_id"]
            assert environment.native.snapshot_json() == before_bytes
            checked_candidates += 1
        environment.step(actions[0]["action_id"])

    assert categories == {"card_reward", "event", "route", "shop"}
    assert checked_candidates == 46


def test_native_adapter_repeated_seed_batch_is_deterministic():
    module, _ = _integration_settings()
    first = [_run_first_candidate_policy(module, seed) for seed in range(20)]
    second = [_run_first_candidate_policy(module, seed) for seed in range(20)]

    assert first == second
    assert all(row["outcome"] in {"player_loss", "player_victory"} for row in first)
    assert set().union(*(row["categories"] for row in first)) == {
        "card_reward",
        "event",
        "route",
        "shop",
    }


def test_native_adapter_matches_all_historical_prefixes():
    module, _ = _integration_settings()
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for run in fixture["runs"]:
        probe = json.loads(
            module.historical_prefix_json(
                int(run["seed_played"]) % (1 << 64),
                run["ascension_level"],
                run["decisions"][0]["picked"],
            )
        )
        assert probe["neow_candidates"] == run["decisions"][0]["candidates"]
        assert probe["floor_one_candidates"] == run["decisions"][1]["candidates"]


def test_native_simple_agent_target_policy_is_deterministic_and_candidate_legal():
    module, provenance = _integration_settings()
    first_rows = []
    all_categories: set[str] = set()

    for seed in range(20):
        environment = NativeSimulatorEnvironment(module.Environment(seed, 0), provenance)
        actions = []
        decisions = 0
        while not environment.snapshot()["terminal"]:
            assert decisions < 500
            before = environment.snapshot()
            candidates = environment.legal_actions()
            before_snapshot_bytes = json.dumps(before, sort_keys=True)
            before_candidate_bytes = json.dumps(candidates, sort_keys=True)

            first = environment.native_baseline_action()
            second = environment.native_baseline_action()
            assert first == second
            assert first["action_id"] in {
                candidate["action_id"] for candidate in candidates
            }
            assert json.dumps(environment.snapshot(), sort_keys=True) == before_snapshot_bytes
            assert json.dumps(environment.legal_actions(), sort_keys=True) == before_candidate_bytes

            transition = environment.step_native_baseline()
            assert transition["selected_action_id"] == first["action_id"]
            all_categories.add(first["category"])
            actions.append(first["action_id"])
            decisions += 1

        terminal = environment.snapshot()
        first_rows.append(
            {
                "actions": actions,
                "floor": terminal["state"]["floor"],
                "outcome": terminal["state"]["outcome"],
                "seed": seed,
            }
        )

    second_rows = []
    for seed in range(20):
        environment = NativeSimulatorEnvironment(module.Environment(seed, 0), provenance)
        actions = []
        while not environment.snapshot()["terminal"]:
            actions.append(environment.native_baseline_action()["action_id"])
            environment.step_native_baseline()
        terminal = environment.snapshot()
        second_rows.append(
            {
                "actions": actions,
                "floor": terminal["state"]["floor"],
                "outcome": terminal["state"]["outcome"],
                "seed": seed,
            }
        )

    assert first_rows == second_rows
    assert all_categories == {"card_reward", "event", "route", "shop"}


def test_native_baseline_query_fails_after_general_policy_step():
    module, _ = _integration_settings()
    environment = module.Environment(0, 0)
    candidates = json.loads(environment.legal_actions_json())
    baseline = json.loads(environment.native_baseline_action_json())
    alternative = next(
        candidate["action_id"]
        for candidate in candidates
        if candidate["action_id"] != baseline["action_id"]
    )

    environment.step(alternative)

    with pytest.raises(RuntimeError, match="baseline-following"):
        environment.native_baseline_action_json()
