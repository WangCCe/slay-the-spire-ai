from pathlib import Path
import json
import os
import subprocess
import sys

import numpy as np
import pytest

from spirecomm.ai.rl.v2.id_mapping import IdMapper, build_id_mapper


REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_DIR = REPO_ROOT / "simulator_adapters" / "sts_lightspeed"
COMBAT_SOURCE = ADAPTER_DIR / "combat_adapter.cpp"
CMAKE_SOURCE = ADAPTER_DIR / "CMakeLists.txt"


def test_combat_adapter_is_a_separate_offline_native_target():
    cmake = CMAKE_SOURCE.read_text(encoding="utf-8")

    assert "pybind11_add_module(sts_lightspeed_combat_adapter" in cmake
    assert "combat_adapter.cpp" in cmake
    assert "target_include_directories(sts_lightspeed_combat_adapter" in cmake
    assert "target_compile_options(sts_lightspeed_combat_adapter" in cmake
    assert "target_link_options(sts_lightspeed_combat_adapter" in cmake
    assert "target_link_libraries(sts_lightspeed_combat_adapter" in cmake
    assert "-static-libgcc" in cmake
    assert '"-Wl,-Bstatic"' in cmake
    assert "stdc++" in cmake
    assert "winpthread" in cmake
    assert "ucrtbase" in cmake


def test_combat_adapter_declares_the_offline_environment_contract():
    source = COMBAT_SOURCE.read_text(encoding="utf-8")

    assert '"sts-lightspeed-combat-adapter-v3"' in source
    assert '"sts-lightspeed-combat-state-v3"' in source
    assert '"sts_lightspeed_combat_simulation"' in source
    assert "MAX_BATTLE_INDEX" in source
    assert "MAX_OUT_OF_COMBAT_ACTIONS" in source
    assert "MAX_PRIOR_BATTLE_ACTIONS" in source
    assert "advanceToBattle" in source
    assert "playPriorBattle" in source
    assert '"progression"' in source
    assert 'py::init<std::uint64_t, int, int>()' in source
    assert "MAX_CARD_SELECT_SETTLEMENTS" in source
    assert "enumerateCardSelectActions" in source
    assert "stepBattleCardSelect" in source
    assert '"card_select_settlement"' in source
    assert 'module.doc() = "Offline-only combat adapter POC for sts_lightspeed"' in source
    assert 'PYBIND11_MODULE(sts_lightspeed_combat_adapter, module)' in source
    for binding in (
        '.def("clone"',
        '.def("legal_actions_json"',
        '.def("snapshot_json"',
        '.def("status_json"',
        '.def("step"',
        '.def("terminal"',
    ):
        assert binding in source


def test_combat_adapter_does_not_reference_live_runtime_or_models():
    source = COMBAT_SOURCE.read_text(encoding="utf-8")

    for forbidden in (
        "CommunicationMod",
        "RLAgentV2",
        "torch",
        "checkpoint",
        "run_training_batch",
    ):
        assert forbidden not in source


def _snapshot(*, card_name="Strike"):
    powers = {
        "Artifact": 0,
        "Confused": 0,
        "Dexterity": 0,
        "Frail": 0,
        "Intangible": 0,
        "Mantra": 0,
        "Metallicize": 0,
        "PlatedArmor": 0,
        "Poison": 0,
        "Regen": 0,
        "Ritual": 0,
        "Strength": 0,
        "Thorns": 0,
        "Vigor": 0,
        "Vulnerable": 0,
        "Weak": 0,
    }
    return {
        "adapter_api_version": "sts-lightspeed-combat-adapter-v3",
        "card_select_settlement": {"count": 0, "tasks": []},
        "progression": {
            "act": 1,
            "baseline_policy": "native_simple_agent_v1",
            "deck_size": 10,
            "encounter": "JAW_WORM",
            "floor": 1,
            "player_current_hp": 70,
            "player_max_hp": 80,
            "reached_battle_index": 0,
            "relic_count": 1,
            "requested_battle_index": 0,
        },
        "rl_action_dim": 133,
        "schema_version": "sts-lightspeed-combat-state-v3",
        "source_type": "sts_lightspeed_combat_simulation",
        "supported": True,
        "terminal": False,
        "unsupported_reason": "",
        "state": {
            "act": 1,
            "ascension": 0,
            "battle_index": 0,
            "decision_count": 0,
            "deck_size": 10,
            "encounter": "JAW_WORM",
            "floor": 1,
            "input_state": "PLAYER_NORMAL",
            "outcome": "undecided",
            "seed": "7",
            "relic_count": 1,
            "turn": 1,
            "player": {
                "block": 5,
                "character": "IRONCLAD",
                "current_hp": 70,
                "energy": 3,
                "max_hp": 80,
                "powers": powers,
            },
            "piles": {"discard": 1, "draw": 4, "exhaust": 0},
            "hand": [
                {
                    "card_type": "ATTACK",
                    "cost": 1,
                    "cost_for_turn": 1,
                    "id": "STRIKE_RED",
                    "name": card_name,
                    "playable": True,
                    "requires_target": True,
                    "slot": 0,
                    "upgrade_count": 0,
                    "upgraded": False,
                }
            ],
            "monsters": [
                {
                    "block": 0,
                    "current_hp": 40,
                    "half_dead": False,
                    "id": "JAW_WORM",
                    "intent": "ATTACK",
                    "is_gone": False,
                    "max_hp": 44,
                    "move_adjusted_damage": 11,
                    "move_hits": 1,
                    "name": "Jaw Worm",
                    "native_slot": 0,
                    "powers": powers,
                    "targetable": True,
                }
            ],
            "potions": [
                {
                    "empty": False,
                    "id": "Fire Potion",
                    "name": "Fire Potion",
                    "requires_target": True,
                    "slot": 0,
                }
            ],
            "relics": [{"id": "Burning Blood", "name": "Burning Blood", "slot": 0}],
        },
    }


def _actions():
    return [
        {
            "action_id": "play_card:0:1",
            "available": True,
            "kind": "play_card",
            "native_target": 0,
            "rl_action_index": 1,
            "source_slot": 0,
            "target_slot": 1,
        },
        {
            "action_id": "use_potion:0:1",
            "available": True,
            "kind": "use_potion",
            "native_target": 0,
            "rl_action_index": 61,
            "source_slot": 0,
            "target_slot": 1,
        },
        {
            "action_id": "end_turn",
            "available": True,
            "kind": "end_turn",
            "native_target": -1,
            "rl_action_index": 90,
            "source_slot": -1,
            "target_slot": 0,
        },
    ]


def _mapper():
    return IdMapper(
        card_ids={"Strike": 4},
        potion_ids={
            "Blessing of the Forge": 6,
            "Fire Potion": 3,
            "Essence of Steel": 4,
            "Gambler's Brew": 5,
            "Ghost in a Jar": 7,
            "Heart of Iron": 8,
            "Elixir": 9,
            "Fairy in a Bottle": 10,
        },
        relic_ids={
            "Burning Blood": 2,
            "Philosopher's Stone": 3,
            "Gold-Plated Cables": 4,
        },
        card_tags={"Strike": []},
    )


def test_rl_v2_bridge_encodes_exact_shapes_and_action_correspondence():
    from analysis_scripts.combat_lightspeed_bridge import encode_rl_v2

    mapped = encode_rl_v2(_snapshot(), _actions(), id_mapper=_mapper())

    assert mapped.state.continuous.shape == (328,)
    assert mapped.state.card_ids.shape == (10,)
    assert mapped.state.potion_ids.shape == (5,)
    assert mapped.state.relic_ids.shape == (40,)
    assert mapped.action_mask.shape == (133,)
    assert mapped.action_mask.dtype == np.bool_
    assert np.flatnonzero(mapped.action_mask).tolist() == [1, 61, 90]
    assert mapped.state.card_ids[0] == 4
    assert mapped.state.potion_ids[0] == 3
    assert mapped.state.relic_ids[0] == 2


def test_rl_v2_bridge_rejects_unknown_required_identity():
    from analysis_scripts.combat_lightspeed_bridge import CombatBridgeError, encode_rl_v2

    with pytest.raises(CombatBridgeError, match="unknown_card_identity"):
        encode_rl_v2(_snapshot(card_name="Unknown Strike"), _actions(), id_mapper=_mapper())


def test_rl_v2_bridge_uses_canonical_relic_id_not_display_name():
    from analysis_scripts.combat_lightspeed_bridge import encode_rl_v2

    snapshot = _snapshot()
    snapshot["state"]["relics"] = [
        {
            "id": "Philosopher's Stone",
            "name": "Philosophers Stone",
            "slot": 0,
        }
    ]

    mapped = encode_rl_v2(snapshot, _actions(), id_mapper=_mapper())

    assert mapped.state.relic_ids[0] == 3


def test_rl_v2_bridge_uses_canonical_potion_id_not_display_name():
    from analysis_scripts.combat_lightspeed_bridge import encode_rl_v2

    snapshot = _snapshot()
    snapshot["state"]["potions"] = [
        {
            "empty": False,
            "id": "Essence of Steel",
            "name": "Essence Of Steel",
            "requires_target": False,
            "slot": 0,
        }
    ]

    mapped = encode_rl_v2(snapshot, _actions(), id_mapper=_mapper())

    assert mapped.state.potion_ids[0] == 4


def test_rl_v2_bridge_normalizes_audited_native_identity_aliases():
    from analysis_scripts.combat_lightspeed_bridge import encode_rl_v2

    snapshot = _snapshot()
    snapshot["state"]["potions"] = [
        {
            "empty": False,
            "id": "GamblersBrew",
            "name": "Gamblers Brew",
            "requires_target": False,
            "slot": 0,
        },
        {
            "empty": False,
            "id": "BlessingOfTheForge",
            "name": "Blessing Of The Forge",
            "requires_target": False,
            "slot": 1,
        },
        {
            "empty": False,
            "id": "EssenceOfSteel",
            "name": "Essence Of Steel",
            "requires_target": False,
            "slot": 2,
        },
        {
            "empty": False,
            "id": "GhostInAJar",
            "name": "Ghost In A Jar",
            "requires_target": False,
            "slot": 3,
        },
        {
            "empty": False,
            "id": "HeartOfIron",
            "name": "Heart Of Iron",
            "requires_target": False,
            "slot": 4,
        },
    ]
    snapshot["state"]["relics"] = [
        {"id": "Cables", "name": "Goldplated Cables", "slot": 0}
    ]

    mapped = encode_rl_v2(snapshot, _actions(), id_mapper=_mapper())

    assert mapped.state.potion_ids[0] == 5
    assert mapped.state.potion_ids[1] == 6
    assert mapped.state.potion_ids[2] == 4
    assert mapped.state.potion_ids[3] == 7
    assert mapped.state.potion_ids[4] == 8
    assert mapped.state.relic_ids[0] == 4


@pytest.mark.parametrize(
    ("native_id", "native_name", "expected_id"),
    (
        ("BlessingOfTheForge", "Blessing Of The Forge", 6),
        ("ElixirPotion", "Elixir Potion", 9),
        ("EssenceOfSteel", "Essence Of Steel", 4),
        ("FairyPotion", "Fairy Potion", 10),
        ("GamblersBrew", "Gamblers Brew", 5),
        ("GhostInAJar", "Ghost In A Jar", 7),
        ("HeartOfIron", "Heart Of Iron", 8),
    ),
)
def test_rl_v2_bridge_normalizes_every_audited_native_potion_alias(
    native_id,
    native_name,
    expected_id,
):
    from analysis_scripts.combat_lightspeed_bridge import encode_rl_v2

    snapshot = _snapshot()
    snapshot["state"]["potions"] = [
        {
            "empty": False,
            "id": native_id,
            "name": native_name,
            "requires_target": False,
            "slot": 0,
        }
    ]

    mapped = encode_rl_v2(snapshot, _actions(), id_mapper=_mapper())

    assert mapped.state.potion_ids[0] == expected_id


def test_rl_v2_bridge_rejects_inconsistent_card_select_settlement_evidence():
    from analysis_scripts.combat_lightspeed_bridge import CombatBridgeError, encode_rl_v2

    snapshot = _snapshot()
    snapshot["card_select_settlement"] = {"count": 1, "tasks": []}
    with pytest.raises(CombatBridgeError, match="card_select_settlement_count_mismatch"):
        encode_rl_v2(snapshot, _actions(), id_mapper=_mapper())


def test_rl_v2_bridge_rejects_inconsistent_progression_evidence():
    from analysis_scripts.combat_lightspeed_bridge import CombatBridgeError, encode_rl_v2

    snapshot = _snapshot()
    snapshot["progression"]["reached_battle_index"] = 1
    with pytest.raises(CombatBridgeError, match="progression_battle_index_mismatch"):
        encode_rl_v2(snapshot, _actions(), id_mapper=_mapper())


def test_native_wrapper_rejects_explicit_unsupported_status():
    from analysis_scripts.combat_lightspeed_bridge import (
        CombatBridgeError,
        NativeCombatEnvironment,
    )

    class UnsupportedNative:
        @staticmethod
        def status_json():
            return json.dumps(
                {
                    "card_select_settlement": {"count": 0, "tasks": []},
                    "input_state": "CARD_SELECT",
                    "progression": _snapshot()["progression"],
                    "supported": False,
                    "unsupported_reason": "card_select",
                }
            )

    environment = NativeCombatEnvironment(UnsupportedNative())
    with pytest.raises(CombatBridgeError, match="native_state_unsupported: card_select"):
        environment.mapped_state(id_mapper=_mapper())


def test_opt_in_native_environment_mapping_clone_and_provenance():
    from analysis_scripts.combat_lightspeed_bridge import (
        NativeCombatEnvironment,
        canonical_json_bytes,
        collect_provenance,
        load_native_module,
    )

    names = (
        "STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE",
        "STS_LIGHTSPEED_SIMULATOR_REPO",
        "STS_ITEMS_JSON",
    )
    values = {name: os.environ.get(name) for name in names}
    if not all(values.values()):
        pytest.skip("native combat adapter paths are not configured")

    dll_directory = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(
        values["STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE"],
        dll_directories=(() if not dll_directory else (dll_directory,)),
    )
    build_info = json.loads(module.build_info_json())
    assert build_info["card_select_settlement_max"] == 8
    assert build_info["card_select_settlement_policy"] == "native_simple_agent_v1"
    assert "HEADBUTT" in build_info["supported_card_select_tasks"]
    assert "HOLOGRAM" not in build_info["supported_card_select_tasks"]
    id_mapper = build_id_mapper(values["STS_ITEMS_JSON"])

    default_first = NativeCombatEnvironment.reset(module, seed=0, ascension=0)
    explicit_first = NativeCombatEnvironment.reset(
        module, seed=0, ascension=0, battle_index=0
    )
    assert canonical_json_bytes(default_first.snapshot()) == canonical_json_bytes(
        explicit_first.snapshot()
    )

    environment = NativeCombatEnvironment.reset(
        module, seed=0, ascension=0, battle_index=1
    )
    repeated = NativeCombatEnvironment.reset(
        module, seed=0, ascension=0, battle_index=1
    )
    assert canonical_json_bytes(environment.snapshot()) == canonical_json_bytes(repeated.snapshot())
    assert canonical_json_bytes(environment.legal_actions()) == canonical_json_bytes(repeated.legal_actions())
    progression = environment.snapshot()["progression"]
    assert progression["requested_battle_index"] == 1
    assert progression["reached_battle_index"] == 1
    assert progression["floor"] > 1
    assert progression["deck_size"] >= 10
    assert progression["relic_count"] >= 1

    mapped = environment.mapped_state(id_mapper=id_mapper)
    assert mapped.state.continuous.shape == (328,)
    assert mapped.state.card_ids.shape == (10,)
    assert mapped.state.potion_ids.shape == (5,)
    assert mapped.state.relic_ids.shape == (40,)
    assert mapped.action_mask.shape == (133,)

    action_id = environment.legal_actions()[0]["action_id"]
    original_snapshot = canonical_json_bytes(environment.snapshot())
    left = environment.clone()
    right = environment.clone()
    left.step(action_id)
    right.step(action_id)
    assert canonical_json_bytes(environment.snapshot()) == original_snapshot
    assert canonical_json_bytes(left.snapshot()) == canonical_json_bytes(right.snapshot())
    assert canonical_json_bytes(left.legal_actions()) == canonical_json_bytes(right.legal_actions())
    assert canonical_json_bytes(left.status()) == canonical_json_bytes(right.status())

    provenance = collect_provenance(
        repo_root=REPO_ROOT,
        simulator_repo=values["STS_LIGHTSPEED_SIMULATOR_REPO"],
        module_path=values["STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE"],
        native_module=module,
    )
    assert len(provenance["adapter_source_sha256"]) == 64
    assert len(provenance["module_sha256"]) == 64
    assert len(provenance["simulator_source_sha256"]) == 64

    with pytest.raises(ValueError, match="battle_index must be in range"):
        NativeCombatEnvironment.reset(module, seed=0, ascension=0, battle_index=64)


def test_native_snapshot_tolerates_expired_player_status_map_entry():
    from analysis_scripts.combat_lightspeed_bridge import (
        NativeCombatEnvironment,
        load_native_module,
    )

    module_path = os.environ.get("STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE")
    if not module_path:
        pytest.skip("native combat adapter path is not configured")
    dll_directory = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(
        module_path,
        dll_directories=(() if not dll_directory else (dll_directory,)),
    )
    environment = NativeCombatEnvironment.reset(
        module,
        seed=82001,
        ascension=0,
        battle_index=9,
    )
    for action_id in (
        "play_card:0:1",
        "play_card:0:1",
        "play_card:0:0",
        "use_potion:0:0",
        "play_card:4:1",
        "use_potion:1:0",
        "end_turn",
    ):
        environment.step(action_id)

    snapshot = environment.snapshot()

    assert snapshot["state"]["input_state"] == "PLAYER_NORMAL"
    assert snapshot["state"]["turn"] == 1


@pytest.mark.parametrize("battle_index", (6, 9))
def test_native_reset_settles_supported_initial_card_select(battle_index):
    from analysis_scripts.combat_lightspeed_bridge import (
        NativeCombatEnvironment,
        load_native_module,
    )

    module_path = os.environ.get("STS_LIGHTSPEED_COMBAT_ADAPTER_MODULE")
    if not module_path:
        pytest.skip("native combat adapter path is not configured")
    dll_directory = os.environ.get("STS_LIGHTSPEED_MINGW_BIN")
    module = load_native_module(
        module_path,
        dll_directories=(() if not dll_directory else (dll_directory,)),
    )

    environment = NativeCombatEnvironment.reset(
        module,
        seed=90048,
        ascension=0,
        battle_index=battle_index,
    )

    status = environment.status()
    assert status["supported"] is True
    assert status["input_state"] == "PLAYER_NORMAL"
    assert status["progression"]["reached_battle_index"] == battle_index
    assert status["card_select_settlement"] == {"count": 0, "tasks": []}


def test_production_agent_import_does_not_load_combat_bridge():
    code = (
        "import sys;"
        f"sys.path.insert(0, {str(REPO_ROOT)!r});"
        "import spirecomm.ai.rl.v2.agent;"
        "assert 'analysis_scripts.combat_lightspeed_bridge' not in sys.modules;"
        "assert 'sts_lightspeed_combat_adapter' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
