from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from analysis_scripts.noncombat_simulator_adapter import (
    ADAPTER_API_VERSION,
    HISTORICAL_ADAPTER_API_VERSIONS,
    MODULE_NAME,
    NATIVE_BASELINE_ACTION_SCHEMA_VERSION,
    NATIVE_TARGET_POLICY_ID,
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
    validate_snapshot,
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


def test_adapter_v3_source_exports_exact_nloth_offer_identity():
    assert ADAPTER_API_VERSION == "sts-lightspeed-noncombat-adapter-v3"
    assert "sts-lightspeed-noncombat-adapter-v2" in HISTORICAL_ADAPTER_API_VERSIONS

    source = (
        REPO_ROOT
        / "simulator_adapters"
        / "sts_lightspeed"
        / "noncombat_adapter.cpp"
    ).read_text(encoding="utf-8")
    for token in (
        'ADAPTER_API_VERSION = "sts-lightspeed-noncombat-adapter-v3"',
        'state["decision_context"]["offered_relics"]',
        "gc_.info.relicIdx0",
        "gc_.info.relicIdx1",
        '"simulator_choice_index"',
        '"relic_slot"',
        '"relic_id"',
        '"relic_name"',
    ):
        assert token in source


def test_adapter_v3_source_filters_only_sold_shop_inventory_slots():
    source = (
        REPO_ROOT
        / "simulator_adapters"
        / "sts_lightspeed"
        / "noncombat_adapter.cpp"
    ).read_text(encoding="utf-8")

    for inventory_kind, price_accessor in (
        ("card", "cardPrice"),
        ("relic", "relicPrice"),
        ("potion", "potionPrice"),
    ):
        assert f"const int price = gc_.info.shop.{price_accessor}(i);" in source
        assert (
            f'if (!shopItemIsVisible(price, "{inventory_kind}", i))' in source
        )

    assert "bool shopItemIsVisible(int price, const char *kind, int slot)" in source
    assert "if (price < -1)" in source
    assert "return price != -1;" in source
    assert 'card["price"] = price;' in source
    assert source.count('{"price", price}') >= 2
    assert "cardJson(gc_.info.shop.cards[i], i)" in source
    assert source.count('{"slot", i}') >= 2


def test_adapter_v3_source_enforces_native_shop_support_envelope():
    source = (
        REPO_ROOT
        / "simulator_adapters"
        / "sts_lightspeed"
        / "noncombat_adapter.cpp"
    ).read_text(encoding="utf-8")

    def member_source(signature: str) -> str:
        start = source.index(signature)
        end = source.index("\n    }\n", start)
        return source[start:end]

    for signature in (
        "std::string snapshotJson() const",
        "std::vector<Candidate> legalCandidates() const",
        "std::string probeNativeBaselineAction(",
    ):
        assert "assertSupportedCurrentDecision();" in member_source(signature)

    for token in (
        "void assertSupportedCurrentDecision() const",
        "sts::RelicId::THE_COURIER",
        '"unsupported_shop_courier_restock_semantics"',
        "bool shopPotionPurchaseSupported() const",
        "sts::RelicId::SOZU",
        "gc_.potionCount < gc_.potionCapacity",
    ):
        assert token in source

    legal_candidates = member_source(
        "std::vector<Candidate> legalCandidates() const"
    )
    assert "action.getRewardsActionType() == Type::POTION" in legal_candidates
    assert "!shopPotionPurchaseSupported()" in legal_candidates
    assert "shopPotionPurchaseSupported()" not in member_source(
        "void appendDecisionContext(json &state) const"
    )


def test_snapshot_reader_preserves_historical_v2_identity_without_defaults():
    snapshot = _snapshot("event")
    snapshot["adapter_api_version"] = "sts-lightspeed-noncombat-adapter-v2"
    snapshot["state"]["decision_context"] = {
        "event_data": 0,
        "event_id": "Liars Game",
        "event_name": "The Ssssserpent",
    }

    normalized = validate_snapshot(snapshot)

    assert normalized["adapter_api_version"] == (
        "sts-lightspeed-noncombat-adapter-v2"
    )
    assert "offered_relics" not in normalized["state"]["decision_context"]


def test_new_module_loader_rejects_historical_v2_module(tmp_path, monkeypatch):
    module_path = tmp_path / "adapter.pyd"
    module_path.write_bytes(b"not loaded")
    legacy = SimpleNamespace(
        __file__=str(module_path),
        adapter_api_version=lambda: "sts-lightspeed-noncombat-adapter-v2",
    )
    monkeypatch.setitem(sys.modules, MODULE_NAME, legacy)

    with pytest.raises(SimulatorAdapterError, match="adapter API mismatch"):
        load_native_module(module_path)


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


_SHOP_COLLECTION_BY_ACTION_KIND = {
    "buy_card": "cards",
    "buy_potion": "potions",
    "buy_relic": "relics",
}


def _validated_shop_inventory(snapshot, actions):
    context = snapshot["state"]["decision_context"]
    by_collection = {}
    for collection in _SHOP_COLLECTION_BY_ACTION_KIND.values():
        entries = context[collection]
        slots = [entry["slot"] for entry in entries]
        assert all(isinstance(slot, int) and not isinstance(slot, bool) for slot in slots)
        assert len(slots) == len(set(slots))
        assert all(
            isinstance(entry["price"], int)
            and not isinstance(entry["price"], bool)
            and entry["price"] >= 0
            for entry in entries
        )
        by_collection[collection] = {entry["slot"]: entry for entry in entries}

    legal_inventory_slots = set()
    for action in actions:
        collection = _SHOP_COLLECTION_BY_ACTION_KIND.get(action["kind"])
        if collection is None:
            continue
        slot = action["raw"]["slot"]
        legal_inventory_slots.add((collection, slot))
        assert by_collection[collection][slot]["price"] == action["raw"]["price"]

    gold = snapshot["state"]["gold"]
    unaffordable = 0
    for collection, entries in by_collection.items():
        for slot, entry in entries.items():
            if entry["price"] > gold:
                unaffordable += 1
                assert (collection, slot) not in legal_inventory_slots
    return by_collection, unaffordable


def _run_first_candidate_policy(module, seed: int):
    environment = module.Environment(seed, 0)
    categories: set[str] = set()
    decisions = 0
    shop_purchases = 0
    shop_snapshots = 0
    sold_slots_absent = 0
    unaffordable_shop_items = 0
    while not environment.terminal():
        assert decisions < 500
        snapshot = json.loads(environment.snapshot_json())
        actions = json.loads(environment.legal_actions_json())
        categories.add(snapshot["category"])
        if snapshot["category"] == "shop":
            _, unaffordable = _validated_shop_inventory(snapshot, actions)
            shop_snapshots += 1
            unaffordable_shop_items += unaffordable

        selected = actions[0]
        collection = _SHOP_COLLECTION_BY_ACTION_KIND.get(selected["kind"])
        selected_slot = selected["raw"].get("slot") if collection else None
        environment.step(selected["action_id"])
        if collection is not None:
            shop_purchases += 1
            after = json.loads(environment.snapshot_json())
            if after["category"] == "shop":
                after_actions = json.loads(environment.legal_actions_json())
                after_inventory, _ = _validated_shop_inventory(after, after_actions)
                has_courier = any(
                    relic["id"] == "THE_COURIER" for relic in after["state"]["relics"]
                )
                if has_courier:
                    assert selected_slot in after_inventory[collection]
                else:
                    assert selected_slot not in after_inventory[collection]
                    sold_slots_absent += 1
        decisions += 1
    terminal = json.loads(environment.snapshot_json())
    return {
        "categories": sorted(categories),
        "decisions": decisions,
        "floor": terminal["state"]["floor"],
        "outcome": terminal["state"]["outcome"],
        "shop_purchases": shop_purchases,
        "shop_snapshots": shop_snapshots,
        "sold_slots_absent": sold_slots_absent,
        "unaffordable_shop_items": unaffordable_shop_items,
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
    assert sum(row["shop_snapshots"] for row in first) > 0
    assert sum(row["shop_purchases"] for row in first) > 0
    assert sum(row["sold_slots_absent"] for row in first) > 0
    assert sum(row["unaffordable_shop_items"] for row in first) > 0


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
    courier_reason = "unsupported_shop_courier_restock_semantics"

    def run_once(*, verify_queries: bool):
        rows = []
        categories: set[str] = set()
        for seed in range(20):
            environment = NativeSimulatorEnvironment(
                module.Environment(seed, 0), provenance
            )
            actions = []
            blocker = None
            decisions = 0
            while True:
                before = environment.snapshot()
                if before["terminal"]:
                    terminal = before
                    break
                assert decisions < 500

                candidates = environment.legal_actions() if verify_queries else None
                if verify_queries:
                    before_snapshot_bytes = json.dumps(before, sort_keys=True)
                    before_candidate_bytes = json.dumps(candidates, sort_keys=True)

                first = environment.native_baseline_action()
                if verify_queries:
                    second = environment.native_baseline_action()
                    assert first == second
                    assert first["action_id"] in {
                        candidate["action_id"] for candidate in candidates
                    }
                    assert (
                        json.dumps(environment.snapshot(), sort_keys=True)
                        == before_snapshot_bytes
                    )
                    assert (
                        json.dumps(environment.legal_actions(), sort_keys=True)
                        == before_candidate_bytes
                    )

                categories.add(first["category"])
                actions.append(first["action_id"])
                try:
                    transition = environment.step_native_baseline()
                except RuntimeError as exc:
                    assert str(exc) == courier_reason
                    blocker = {
                        "action_id": first["action_id"],
                        "category": first["category"],
                        "decision_count": before["decision_count"],
                        "reason": str(exc),
                    }
                    terminal = before
                    break
                assert transition["selected_action_id"] == first["action_id"]
                decisions += 1

            rows.append(
                {
                    "actions": actions,
                    "blocker": blocker,
                    "floor": terminal["state"]["floor"],
                    "outcome": (
                        None if blocker is not None else terminal["state"]["outcome"]
                    ),
                    "seed": seed,
                }
            )
        return rows, categories

    first_rows, all_categories = run_once(verify_queries=True)
    second_rows, second_categories = run_once(verify_queries=False)
    assert first_rows == second_rows
    assert all_categories == second_categories
    assert all_categories == {"card_reward", "event", "route", "shop"}
    blockers = [
        {
            "floor": row["floor"],
            "seed": row["seed"],
            **row["blocker"],
        }
        for row in first_rows
        if row["blocker"] is not None
    ]
    assert blockers == [
        {
            "action_id": "route:map_node:6:4",
            "category": "route",
            "decision_count": 39,
            "floor": 21,
            "reason": courier_reason,
            "seed": 10,
        }
    ]


def test_native_baseline_query_continues_after_card_policy_step():
    module, _ = _integration_settings()
    environment = module.Environment(0, 0)
    for _ in range(100):
        candidates = json.loads(environment.legal_actions_json())
        if candidates and candidates[0]["category"] == "card_reward" and len(candidates) > 1:
            break
        environment.step_native_baseline()
    else:
        raise AssertionError("fixture did not reach a multi-action card reward")
    baseline = json.loads(environment.native_baseline_action_json())
    alternative = next(
        candidate["action_id"]
        for candidate in candidates
        if candidate["action_id"] != baseline["action_id"]
    )

    environment.step(alternative)

    continued = json.loads(environment.native_baseline_action_json())
    assert continued["policy_id"] == NATIVE_TARGET_POLICY_ID


def test_native_baseline_query_fails_after_general_noncard_policy_step():
    module, _ = _integration_settings()
    environment = module.Environment(0, 0)
    for _ in range(100):
        candidates = json.loads(environment.legal_actions_json())
        if candidates and candidates[0]["category"] != "card_reward" and len(candidates) > 1:
            break
        environment.step_native_baseline()
    else:
        raise AssertionError("fixture did not reach a multi-action non-card decision")
    baseline = json.loads(environment.native_baseline_action_json())
    alternative = next(
        candidate["action_id"]
        for candidate in candidates
        if candidate["action_id"] != baseline["action_id"]
    )

    environment.step(alternative)

    with pytest.raises(RuntimeError, match="baseline-following"):
        environment.native_baseline_action_json()
