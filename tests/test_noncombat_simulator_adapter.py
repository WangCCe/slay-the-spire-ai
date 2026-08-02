from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    SOURCE_TYPE,
    STATE_SCHEMA_VERSION,
    TRANSITION_SCHEMA_VERSION,
    NativeSimulatorEnvironment,
    SimulatorAdapterError,
    build_transition,
    collect_provenance,
    hash_compiled_simulator_sources,
    load_native_module,
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
