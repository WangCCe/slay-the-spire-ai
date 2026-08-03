from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from analysis_scripts.noncombat_current_policy_simulator_bridge import (
    ALL_FALSE_AUTHORITY,
    BridgeBlocked,
    CurrentPolicyBridgeSession,
    MetadataCatalog,
    REGISTERED_SOURCE_FILES,
    V1_REGISTERED_SOURCE_FILES,
    build_artifacts,
    classify_stage1,
    enrich_event_option_semantics,
    hydrate_game,
    map_current_action,
    run_stage2_compatibility,
    validate_stage2_native_identity,
    validate_successor_registration,
    validate_registration,
    validate_successor_evidence,
)
from analysis_scripts.noncombat_event_option_semantics import (
    event_option_semantics_identity,
    reachable_event_option_semantics_identity,
)
from analysis_scripts.noncombat_simulator_adapter import (
    canonical_json_bytes,
    sha256_bytes,
)
from spirecomm.communication.action import (
    BuyCardAction,
    BuyPotionAction,
    BuyRelicAction,
    CancelAction,
    CardRewardAction,
    ChooseAction,
    ChooseMapNodeAction,
    LeaveAction,
)
from spirecomm.spire.card import Card, CardRarity, CardType
from spirecomm.spire.map import Node
from spirecomm.spire.potion import Potion
from spirecomm.spire.relic import Relic
from spirecomm.spire.screen import ScreenType


def _candidate(category, kind, action_id, *, label="candidate", **raw):
    return {
        "action_id": action_id,
        "available": True,
        "category": category,
        "kind": kind,
        "label": label,
        "raw": raw,
    }


def _state(**overrides):
    state = {
        "act": 1,
        "ascension": 0,
        "blue_key": False,
        "boss": "THE_GUARDIAN",
        "cur_hp": 70,
        "cur_map_node": {"x": -1, "y": -1},
        "cur_room": "INVALID",
        "decision_context": {},
        "deck": [
            {
                "id": "STRIKE_RED",
                "misc": 0,
                "name": "Strike",
                "slot": 0,
                "upgrade_count": 0,
                "upgraded": False,
            }
        ],
        "encounter": "INVALID",
        "floor": 0,
        "gold": 99,
        "green_key": False,
        "map": {
            "burning_elite": {"buff": 0, "x": -1, "y": -1},
            "nodes": [
                {
                    "edges": [],
                    "room": "MONSTER",
                    "symbol": "M",
                    "x": 0,
                    "y": 0,
                }
            ],
        },
        "max_hp": 80,
        "outcome": "undecided",
        "potions": [
            {"id": "EMPTY_POTION_SLOT", "name": "EMPTY_POTION_SLOT", "slot": 0}
        ],
        "red_key": False,
        "relics": [{"data": 0, "id": "BURNING_BLOOD", "name": "Burning Blood"}],
        "screen_state": "MAP_SCREEN",
        "seed": "4000",
    }
    state.update(overrides)
    return state


def _snapshot(category, state):
    return {
        "adapter_api_version": "sts-lightspeed-noncombat-adapter-v2",
        "baseline_control": {
            "history": [],
            "policy_id": "sts_lightspeed_simple_agent_no_potions_v1",
        },
        "category": category,
        "schema_version": "sts-lightspeed-state-v1",
        "source_type": "sts_lightspeed_simulation",
        "state": state,
        "terminal": False,
    }


def _adapter_provenance():
    semantics = event_option_semantics_identity()
    return {
        "adapter_commit": "a" * 40,
        "adapter_source_sha256": "b" * 64,
        "build": {
            "adapter_api_version": "sts-lightspeed-noncombat-adapter-v2",
            "compiler": "test compiler",
            "cpp_standard": 201703,
            "python": sys.version.split()[0],
        },
        "module_sha256": "c" * 64,
        "simulator_commit": semantics["simulator_commit"],
        "simulator_source_sha256": semantics["simulator_source_sha256"],
        "submodules": {"json": "d" * 40, "pybind11": "e" * 40},
    }


def _current_policy():
    return {
        "ascension": 0,
        "character": "IRONCLAD",
        "elite_mode": "conservative",
        "gameplay_io_enabled": False,
        "policy_id": "current_optimized_ironclad_a0_conservative_snapshot_v1",
        "screen_entrypoint": "handle_screen",
        "tracker_enabled": False,
        "use_optimized_card_selection": True,
        "use_optimized_combat": True,
    }


def _successor_registration():
    repo_root = Path(__file__).resolve().parents[1]
    predecessor = json.loads(
        (
            repo_root
            / "reports"
            / "noncombat_current_policy_simulator_bridge_20260802_input.json"
        ).read_text(encoding="utf-8")
    )
    successor = copy.deepcopy(predecessor)
    successor["schema_version"] = (
        "noncombat-current-policy-simulator-bridge-input-v2"
    )
    successor["identity"]["event_option_semantics"] = (
        event_option_semantics_identity()
    )
    successor["identity"]["predecessor_registration"] = {
        "path": (
            "reports/noncombat_current_policy_simulator_bridge_20260802_input.json"
        ),
        "sha256": "1" * 64,
        "size_bytes": 1,
    }
    successor["identity"]["predecessor_manifest"] = {
        "path": (
            "reports/noncombat_current_policy_simulator_bridge_20260802/"
            "artifact_manifest.json"
        ),
        "sha256": "2" * 64,
        "size_bytes": 1,
    }
    successor["identity"]["implementation"]["commit"] = "3" * 40
    successor["identity"]["implementation"]["source_files"] = list(
        REGISTERED_SOURCE_FILES
    )
    successor["identity"]["implementation"]["source_sha256"] = "4" * 64
    successor["output"]["directory"] = (
        "reports/noncombat_current_policy_simulator_bridge_20260802_r2"
    )
    return successor, predecessor


def _write_successor_evidence(tmp_path):
    successor, predecessor = _successor_registration()
    predecessor_relative = Path(
        "reports/noncombat_current_policy_simulator_bridge_20260802_input.json"
    )
    predecessor_path = tmp_path / predecessor_relative
    predecessor_path.parent.mkdir(parents=True)
    predecessor_bytes = canonical_json_bytes(predecessor)
    predecessor_path.write_bytes(predecessor_bytes)

    manifest_relative = (
        Path(predecessor["output"]["directory"]) / "artifact_manifest.json"
    )
    manifest_path = tmp_path / manifest_relative
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "artifact_hashes": {
            name: str(index) * 64
            for index, name in enumerate(
                [
                    "configuration.json",
                    "execution_journal.json",
                    "metrics.json",
                    "report.md",
                    "row_results.json",
                ],
                start=1,
            )
        },
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "registration_sha256": sha256_bytes(predecessor_bytes),
        "schema_version": (
            "noncombat-current-policy-simulator-bridge-manifest-v1"
        ),
        "stage2_executed": False,
        "verdict": "frozen_bridge_not_compatible",
    }
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)

    successor["identity"]["predecessor_registration"] = {
        "path": predecessor_relative.as_posix(),
        "sha256": sha256_bytes(predecessor_bytes),
        "size_bytes": len(predecessor_bytes),
    }
    successor["identity"]["predecessor_manifest"] = {
        "path": manifest_relative.as_posix(),
        "sha256": sha256_bytes(manifest_bytes),
        "size_bytes": len(manifest_bytes),
    }
    return successor, manifest, manifest_path


def _stage2_native_identity(registration):
    provenance = registration["identity"]["adapter_provenance"]
    return {
        "build": copy.deepcopy(provenance["build"]),
        "module_sha256": provenance["module_sha256"],
        "module_size_bytes": provenance["module_size_bytes"],
        "simulator_commit": provenance["simulator_commit"],
        "simulator_dirty": provenance["simulator_dirty"],
        "simulator_source_file_count": provenance["simulator_source_file_count"],
        "simulator_source_sha256": provenance["simulator_source_sha256"],
        "submodules": copy.deepcopy(provenance["submodules"]),
    }


class _FakeStage2Environment:
    def __init__(self, seed, *, divergent=False, never_terminal=False):
        self.seed = seed
        self.decision_index = 0
        self.divergent = divergent
        self.never_terminal = never_terminal

    def snapshot(self):
        terminal = not self.never_terminal and self.decision_index >= 2
        return {
            "category": None if terminal else "route",
            "decision_count": self.decision_index,
            "state": {
                "floor": self.decision_index,
                "outcome": "player_loss" if terminal else "undecided",
                "seed": str(self.seed),
            },
            "terminal": terminal,
        }

    def legal_actions(self):
        suffix = 1 if self.divergent and self.decision_index == 1 else 0
        return [
            _candidate(
                "route",
                "map_node",
                f"route:map_node:{suffix}:{self.decision_index}",
                x=suffix,
                y=self.decision_index,
            )
        ]

    def step(self, action_id):
        self.decision_index += 1
        return {"selected_action_id": action_id}


class _FakeStage2Session:
    def evaluate(self, *, snapshot, candidates, decision_index):
        candidate = candidates[0]
        return {
            "action_id": candidate["action_id"],
            "action_type": "ChooseMapNodeAction",
            "category": snapshot["category"],
            "fallback_used": False,
            "input_candidates_sha256": sha256_bytes(
                canonical_json_bytes(candidates)
            ),
            "input_snapshot_sha256": sha256_bytes(canonical_json_bytes(snapshot)),
            "policy_id": "current_optimized_ironclad_a0_conservative_snapshot_v1",
            "source_mutated": False,
            "tracker_enabled": False,
        }


def _liars_game_state(*, inline_semantics=None):
    context = {
        "event_data": 0,
        "event_id": "Liars Game",
        "event_name": "The Ssssserpent",
    }
    if inline_semantics is not None:
        context["option_semantics"] = inline_semantics
    return _state(
        cur_room="EVENT",
        decision_context=context,
        screen_state="EVENT_SCREEN",
    )


def _liars_game_candidates():
    return [
        _candidate(
            "event",
            "event_option",
            "event:the_ssssserpent:option:0",
            idx1=0,
            idx2=0,
            event_id="Liars Game",
        ),
        _candidate(
            "event",
            "event_option",
            "event:the_ssssserpent:option:1",
            idx1=1,
            idx2=0,
            event_id="Liars Game",
        ),
    ]


def _event_state(event_id, event_name, event_data=0, *, inline_semantics=None):
    context = {
        "event_data": event_data,
        "event_id": event_id,
        "event_name": event_name,
    }
    if inline_semantics is not None:
        context["option_semantics"] = copy.deepcopy(inline_semantics)
    return _state(
        cur_room="EVENT",
        decision_context=context,
        screen_state="EVENT_SCREEN",
    )


def _event_candidates(event_id, event_name, indices):
    slug = event_name.lower().replace(" ", "_")
    return [
        _candidate(
            "event",
            "event_option",
            f"event:{slug}:option:{index}",
            idx1=index,
            idx2=0,
            event_id=event_id,
        )
        for index in indices
    ]


def _shop_state(remove_cost, **inventory):
    context = {
        "cards": [],
        "potions": [],
        "relics": [],
        "remove_cost": remove_cost,
    }
    context.update(inventory)
    return _state(
        cur_room="SHOP",
        decision_context=context,
        screen_state="SHOP_SCREEN",
    )


def _metadata_catalog(
    tmp_path, potion_names, relic_names=("Burning Blood",)
):
    path = tmp_path / "items.json"
    path.write_text(
        json.dumps(
            {
                "cards": [
                    {
                        "name": "Strike",
                        "rarity": "Basic",
                        "type": "Attack",
                        "cost": "1",
                    },
                    {
                        "name": "Armaments",
                        "rarity": "Common",
                        "type": "Skill",
                        "cost": "1",
                    },
                ],
                "relics": [{"name": name} for name in relic_names],
                "potions": [{"name": name} for name in potion_names],
            }
        ),
        encoding="utf-8",
    )
    return MetadataCatalog(path)


@pytest.fixture
def metadata(tmp_path):
    return _metadata_catalog(tmp_path, ["Attack Potion"])


@pytest.mark.parametrize(
    ("relic_id", "native_name", "metadata_name"),
    [
        ("BIRD_FACED_URN", "Bird Faced Urn", "Bird-Faced Urn"),
        ("CAPTAINS_WHEEL", "Captains Wheel", "Captain's Wheel"),
        ("CHARONS_ASHES", "Charons Ashes", "Charon's Ashes"),
        ("NILRYS_CODEX", "Nilrys Codex", "Nilry's Codex"),
        (
            "PHILOSOPHERS_STONE",
            "Philosophers Stone",
            "Philosopher's Stone",
        ),
        ("SELF_FORMING_CLAY", "Self Forming Clay", "Self-Forming Clay"),
        ("DU_VU_DOLL", "Du Vu Doll", "Du-Vu Doll"),
        (
            "GOLD_PLATED_CABLES",
            "Goldplated Cables",
            "Gold-Plated Cables",
        ),
        ("NEOWS_LAMENT", "Neows Lament", "Neow's Lament"),
        ("SLAVERS_COLLAR", "Slavers Collar", "Slaver's Collar"),
        ("DOLLYS_MIRROR", "Dollys Mirror", "Dolly's Mirror"),
        ("LEES_WAFFLE", "Lees Waffle", "Lee's Waffle"),
        ("NLOTHS_GIFT", "Nloths Gift", "N'loth's Gift"),
        (
            "NLOTHS_HUNGRY_FACE",
            "Nloths Hungry Face",
            "N'loth's Hungry Face",
        ),
        ("PANDORAS_BOX", "Pandoras Box", "Pandora's Box"),
    ],
)
def test_registered_relic_metadata_aliases_use_canonical_name(
    tmp_path, relic_id, native_name, metadata_name
):
    catalog = _metadata_catalog(
        tmp_path, ["Attack Potion"], relic_names=[metadata_name]
    )
    source = {
        "data": 3,
        "id": relic_id,
        "name": native_name,
        "price": 111,
        "slot": 4,
    }
    before = copy.deepcopy(source)

    relic = catalog.relic(source, role="shop_relic")

    assert relic.relic_id == relic_id
    assert relic.name == metadata_name
    assert relic.counter == 3
    assert relic.price == 111
    assert relic._bridge_source_slot == 4
    assert source == before


@pytest.mark.parametrize(
    ("relic_id", "native_name"),
    [("CIRCLET", "Circlet"), ("RED_CIRCLET", "Red Circlet")],
)
def test_registered_relic_metadata_exemptions_hydrate_exact_identity(
    tmp_path, relic_id, native_name
):
    catalog = _metadata_catalog(tmp_path, ["Attack Potion"])
    source = {"data": 2, "id": relic_id, "name": native_name, "slot": 1}
    before = copy.deepcopy(source)

    relic = catalog.relic(source, role="run")

    assert relic.relic_id == relic_id
    assert relic.name == native_name
    assert relic.counter == 2
    assert relic._bridge_source_slot == 1
    assert source == before


@pytest.mark.parametrize(
    ("relic_id", "native_name", "metadata_names"),
    [
        ("BIRD_FACED_URN", "Renamed Urn", ["Bird-Faced Urn"]),
        (
            "BIRD_FACED_URN",
            "Burning Blood",
            ["Bird-Faced Urn", "Burning Blood"],
        ),
        ("UNKNOWN_RELIC", "Bird Faced Urn", ["Bird-Faced Urn"]),
        ("BIRD_FACED_URN", "Bird Faced Urn", ["Burning Blood"]),
        ("CIRCLET", "Renamed Circlet", ["Burning Blood"]),
        ("UNKNOWN_RELIC", "Circlet", ["Burning Blood"]),
    ],
)
def test_relic_metadata_identities_fail_closed_when_inconsistent(
    tmp_path, relic_id, native_name, metadata_names
):
    catalog = _metadata_catalog(
        tmp_path, ["Attack Potion"], relic_names=metadata_names
    )

    with pytest.raises(BridgeBlocked, match="relic_metadata_missing"):
        catalog.relic(
            {"data": 0, "id": relic_id, "name": native_name, "slot": 0},
            role="run",
        )


def test_exact_relic_metadata_name_path_remains_unchanged(tmp_path):
    catalog = _metadata_catalog(tmp_path, ["Attack Potion"])

    relic = catalog.relic(
        {"data": 0, "id": "BURNING_BLOOD", "name": "burning blood"},
        role="run",
    )

    assert relic.relic_id == "BURNING_BLOOD"
    assert relic.name == "burning blood"


@pytest.mark.parametrize(
    ("potion_id", "native_name", "metadata_name", "effect_type"),
    [
        ("ELIXIR_POTION", "Elixir Potion", "Elixir", "exhaust_hand_select"),
        ("FAIRY_POTION", "Fairy Potion", "Fairy in a Bottle", "fairy"),
        (
            "GAMBLERS_BREW",
            "Gamblers Brew",
            "Gambler's Brew",
            "discard_draw",
        ),
    ],
)
def test_registered_potion_metadata_aliases_use_canonical_name(
    tmp_path, potion_id, native_name, metadata_name, effect_type
):
    catalog = _metadata_catalog(tmp_path, [metadata_name])
    source = {
        "id": potion_id,
        "name": native_name,
        "price": 77,
        "slot": 2,
    }
    before = copy.deepcopy(source)

    potion = catalog.potion(source, role="shop_potion")

    assert potion.potion_id == potion_id
    assert potion.name == metadata_name
    assert potion.effect_type == effect_type
    assert potion.price == 77
    assert potion._bridge_source_slot == 2
    assert source == before


@pytest.mark.parametrize(
    ("potion_id", "native_name", "metadata_names"),
    [
        ("ELIXIR_POTION", "Renamed Elixir", ["Elixir"]),
        (
            "ELIXIR_POTION",
            "Attack Potion",
            ["Attack Potion", "Elixir"],
        ),
        ("UNKNOWN_POTION", "Elixir Potion", ["Elixir"]),
        ("ELIXIR_POTION", "Elixir Potion", ["Attack Potion"]),
    ],
)
def test_potion_metadata_aliases_fail_closed_for_inconsistent_identity(
    tmp_path, potion_id, native_name, metadata_names
):
    catalog = _metadata_catalog(tmp_path, metadata_names)

    with pytest.raises(BridgeBlocked, match="potion_metadata_missing"):
        catalog.potion(
            {"id": potion_id, "name": native_name, "price": 0, "slot": 0},
            role="run",
        )


def test_exact_potion_metadata_name_path_remains_unchanged(tmp_path):
    catalog = _metadata_catalog(tmp_path, ["Attack Potion"])

    potion = catalog.potion(
        {"id": "ATTACK_POTION", "name": "attack potion", "slot": 0},
        role="run",
    )

    assert potion.potion_id == "ATTACK_POTION"
    assert potion.name == "attack potion"
    assert potion.effect_type == "card_choice_attack"


def test_route_action_maps_by_coordinate():
    candidates = [
        _candidate("route", "map_node", "route:map_node:0:0", x=0, y=0),
        _candidate("route", "map_node", "route:map_node:2:0", x=2, y=0),
    ]

    action_id = map_current_action(
        category="route",
        action=ChooseMapNodeAction(Node(2, 0, "M")),
        candidates=candidates,
    )

    assert action_id == "route:map_node:2:0"


def test_card_reward_uses_source_slot_even_with_duplicate_names():
    card = Card("ARMAMENTS", "Armaments", CardType.SKILL, CardRarity.COMMON)
    action = CardRewardAction(card)
    action._bridge_source_slot = 1
    candidates = [
        _candidate(
            "card_reward",
            "take",
            "card_reward:take:0:0:armaments",
            label="Armaments",
            slot=0,
            reward_index=0,
        ),
        _candidate(
            "card_reward",
            "take",
            "card_reward:take:0:1:armaments",
            label="Armaments",
            slot=1,
            reward_index=0,
        ),
    ]

    assert (
        map_current_action(
            category="card_reward", action=action, candidates=candidates
        )
        == "card_reward:take:0:1:armaments"
    )


def test_duplicate_card_name_without_source_slot_fails_closed():
    card = Card("ARMAMENTS", "Armaments", CardType.SKILL, CardRarity.COMMON)
    candidates = [
        _candidate(
            "card_reward",
            "take",
            "card_reward:take:0:0:armaments",
            label="Armaments",
            slot=0,
        ),
        _candidate(
            "card_reward",
            "take",
            "card_reward:take:0:1:armaments",
            label="Armaments",
            slot=1,
        ),
    ]

    with pytest.raises(BridgeBlocked, match="missing_source_slot"):
        map_current_action(
            category="card_reward",
            action=CardRewardAction(card),
            candidates=candidates,
        )


@pytest.mark.parametrize(
    ("action", "kind", "expected"),
    [
        (CardRewardAction(bowl=True), "bowl", "card_reward:bowl:0"),
        (CancelAction(), "skip", "card_reward:skip:0"),
    ],
)
def test_card_reward_abstention_modes_map_exactly(action, kind, expected):
    candidates = [_candidate("card_reward", kind, expected)]

    assert (
        map_current_action(
            category="card_reward", action=action, candidates=candidates
        )
        == expected
    )


@pytest.mark.parametrize(
    ("action", "kind", "slot", "expected"),
    [
        (BuyCardAction(Card("A", "A", CardType.ATTACK, CardRarity.COMMON)), "buy_card", 2, "shop:buy_card:2:a"),
        (BuyRelicAction(Relic("R", "R")), "buy_relic", 1, "shop:buy_relic:1:r"),
        (BuyPotionAction(Potion("P", "P", False, False, False)), "buy_potion", 0, "shop:buy_potion:0:p"),
    ],
)
def test_shop_inventory_actions_map_by_captured_slot(action, kind, slot, expected):
    action._bridge_source_slot = slot
    candidates = [_candidate("shop", kind, expected, slot=slot)]

    assert map_current_action(category="shop", action=action, candidates=candidates) == expected


def test_shop_hydration_preserves_sparse_visible_source_slots(metadata):
    snapshot = _snapshot(
        "shop",
        _shop_state(
            75,
            cards=[
                {
                    "id": "ARMAMENTS",
                    "misc": 0,
                    "name": "Armaments",
                    "price": 150,
                    "slot": 5,
                    "upgrade_count": 0,
                    "upgraded": False,
                }
            ],
            relics=[
                {
                    "id": "BURNING_BLOOD",
                    "name": "Burning Blood",
                    "price": 200,
                    "slot": 2,
                }
            ],
            potions=[
                {
                    "id": "ATTACK_POTION",
                    "name": "Attack Potion",
                    "price": 120,
                    "slot": 1,
                }
            ],
        ),
    )
    candidates = [_candidate("shop", "leave", "shop:leave")]

    game = hydrate_game(snapshot, candidates, metadata)

    assert [card._bridge_source_slot for card in game.screen.cards] == [5]
    assert [card.price for card in game.screen.cards] == [150]
    assert [relic._bridge_source_slot for relic in game.screen.relics] == [2]
    assert [relic.price for relic in game.screen.relics] == [200]
    assert [potion._bridge_source_slot for potion in game.screen.potions] == [1]
    assert [potion.price for potion in game.screen.potions] == [120]


def test_shop_hydration_resolves_registered_potion_alias_without_mutation(tmp_path):
    metadata = _metadata_catalog(tmp_path, ["Elixir"])
    snapshot = _snapshot(
        "shop",
        _shop_state(
            75,
            potions=[
                {
                    "id": "ELIXIR_POTION",
                    "name": "Elixir Potion",
                    "price": 65,
                    "slot": 2,
                }
            ],
        ),
    )
    candidates = [_candidate("shop", "leave", "shop:leave")]
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)

    game = hydrate_game(snapshot, candidates, metadata)

    potion = game.screen.potions[0]
    assert potion.potion_id == "ELIXIR_POTION"
    assert potion.name == "Elixir"
    assert potion.effect_type == "exhaust_hand_select"
    assert potion._bridge_source_slot == 2
    assert potion.price == 65
    assert snapshot == before_snapshot
    assert candidates == before_candidates


def test_shop_hydration_resolves_registered_relic_alias_without_mutation(tmp_path):
    metadata = _metadata_catalog(
        tmp_path,
        ["Attack Potion"],
        relic_names=["Burning Blood", "Pandora's Box"],
    )
    snapshot = _snapshot(
        "shop",
        _shop_state(
            75,
            relics=[
                {
                    "id": "PANDORAS_BOX",
                    "name": "Pandoras Box",
                    "price": 300,
                    "slot": 1,
                }
            ],
        ),
    )
    candidates = [_candidate("shop", "leave", "shop:leave")]
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)

    game = hydrate_game(snapshot, candidates, metadata)

    relic = game.screen.relics[0]
    assert relic.relic_id == "PANDORAS_BOX"
    assert relic.name == "Pandora's Box"
    assert relic._bridge_source_slot == 1
    assert relic.price == 300
    assert snapshot == before_snapshot
    assert candidates == before_candidates


@pytest.mark.parametrize(
    ("inventory_kind", "entry", "reason"),
    [
        (
            "cards",
            {
                "id": "ARMAMENTS",
                "misc": 0,
                "name": "Armaments",
                "price": -1,
                "slot": 5,
                "upgrade_count": 0,
                "upgraded": False,
            },
            "card_price_invalid",
        ),
        (
            "relics",
            {
                "id": "BURNING_BLOOD",
                "name": "Burning Blood",
                "price": -1,
                "slot": 2,
            },
            "relic_price_invalid",
        ),
        (
            "potions",
            {
                "id": "ATTACK_POTION",
                "name": "Attack Potion",
                "price": -1,
                "slot": 1,
            },
            "potion_price_invalid",
        ),
    ],
)
def test_shop_hydration_rejects_sold_inventory_entries(
    inventory_kind, entry, reason, metadata
):
    snapshot = _snapshot(
        "shop", _shop_state(75, **{inventory_kind: [entry]})
    )
    candidates = [_candidate("shop", "leave", "shop:leave")]

    with pytest.raises(BridgeBlocked, match=reason):
        hydrate_game(snapshot, candidates, metadata)


@pytest.mark.parametrize(
    ("action", "kind", "expected"),
    [
        (ChooseAction(name="purge"), "remove_card", "shop:remove_card"),
        (LeaveAction(), "leave", "shop:leave"),
    ],
)
def test_shop_control_actions_map_exactly(action, kind, expected):
    candidates = [_candidate("shop", kind, expected)]

    assert map_current_action(category="shop", action=action, candidates=candidates) == expected


def test_shop_hydration_normalizes_consumed_remove_sentinel_without_mutation(
    metadata,
):
    snapshot = _snapshot("shop", _shop_state(-1))
    candidates = [_candidate("shop", "leave", "shop:leave")]
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)

    game = hydrate_game(snapshot, candidates, metadata)

    assert game.screen_type is ScreenType.SHOP_SCREEN
    assert game.screen.purge_available is False
    assert game.screen.purge_cost == 0
    assert snapshot == before_snapshot
    assert candidates == before_candidates


def test_shop_hydration_rejects_remove_candidate_with_consumed_sentinel(metadata):
    snapshot = _snapshot("shop", _shop_state(-1))
    candidates = [
        _candidate("shop", "remove_card", "shop:remove_card"),
        _candidate("shop", "leave", "shop:leave"),
    ]

    with pytest.raises(
        BridgeBlocked, match="shop_remove_cost_sentinel_candidate_mismatch"
    ):
        hydrate_game(snapshot, candidates, metadata)


@pytest.mark.parametrize("remove_cost", [-2, True, 1.5, None, "75"])
def test_shop_hydration_rejects_unproven_remove_cost(remove_cost, metadata):
    snapshot = _snapshot("shop", _shop_state(remove_cost))
    candidates = [_candidate("shop", "leave", "shop:leave")]

    with pytest.raises(BridgeBlocked, match="invalid_nonnegative_integer"):
        hydrate_game(snapshot, candidates, metadata)


@pytest.mark.parametrize(
    ("remove_cost", "remove_available"),
    [(0, False), (75, True)],
)
def test_shop_hydration_preserves_nonnegative_remove_cost(
    remove_cost, remove_available, metadata
):
    snapshot = _snapshot("shop", _shop_state(remove_cost))
    candidates = [_candidate("shop", "leave", "shop:leave")]
    if remove_available:
        candidates.insert(
            0, _candidate("shop", "remove_card", "shop:remove_card")
        )

    game = hydrate_game(snapshot, candidates, metadata)

    assert game.screen.purge_available is remove_available
    assert game.screen.purge_cost == remove_cost


def test_current_session_accepts_consumed_shop_remove_sentinel(metadata):
    snapshot = _snapshot("shop", _shop_state(-1))
    candidates = [_candidate("shop", "leave", "shop:leave")]
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)
    session = CurrentPolicyBridgeSession(
        metadata=metadata,
        current_policy=_current_policy(),
        require_global_metadata_match=False,
    )

    result = session.evaluate(
        snapshot=snapshot,
        candidates=candidates,
        decision_index=1,
    )

    assert result["action_id"] == "shop:leave"
    assert result["category"] == "shop"
    assert result["fallback_used"] is False
    assert snapshot == before_snapshot
    assert candidates == before_candidates


def test_event_hydration_requires_exact_option_semantics(metadata):
    state = _state(
        cur_room="EVENT",
        decision_context={
            "event_data": 0,
            "event_id": "Liars Game",
            "event_name": "The Ssssserpent",
        },
        screen_state="EVENT_SCREEN",
    )
    candidates = [
        _candidate("event", "event_option", "event:ssssserpent:option:0", idx1=0),
        _candidate("event", "event_option", "event:ssssserpent:option:1", idx1=1),
    ]

    with pytest.raises(BridgeBlocked, match="missing_event_option_semantics"):
        hydrate_game(_snapshot("event", state), candidates, metadata)


def test_event_hydration_preserves_semantic_labels(metadata):
    state = _state(
        cur_room="EVENT",
        decision_context={
            "event_data": 0,
            "event_id": "Liars Game",
            "event_name": "The Ssssserpent",
            "option_semantics": [
                {"choice_index": 0, "label": "Agree", "text": "Gain gold"},
                {
                    "choice_index": 1,
                    "label": "Disagree",
                    "text": "Nothing happens.",
                },
            ],
        },
        screen_state="EVENT_SCREEN",
    )
    candidates = [
        _candidate("event", "event_option", "event:ssssserpent:option:0", idx1=0),
        _candidate("event", "event_option", "event:ssssserpent:option:1", idx1=1),
    ]

    game = hydrate_game(_snapshot("event", state), candidates, metadata)

    assert game.screen_type is ScreenType.EVENT
    assert [option.label for option in game.screen.options] == ["Agree", "Disagree"]
    assert [option.choice_index for option in game.choice_list] == [0, 1]


def test_bridge_enriches_missing_event_semantics_without_mutating_sources():
    snapshot = _snapshot("event", _liars_game_state())
    candidates = _liars_game_candidates()
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)

    enriched, source = enrich_event_option_semantics(
        snapshot=snapshot,
        candidates=candidates,
        simulator_provenance=_adapter_provenance(),
    )

    assert source == "sts_lightspeed_reachable_event_observation_v3"
    assert enriched["state"]["decision_context"]["option_semantics"] == [
        {
            "choice_index": 0,
            "current_position": 0,
            "label": "Agree",
            "simulator_choice_index": 0,
            "text": "Agree",
        },
        {
            "choice_index": 1,
            "current_position": 1,
            "label": "Disagree",
            "simulator_choice_index": 1,
            "text": "Disagree",
        },
    ]
    assert snapshot == before_snapshot
    assert candidates == before_candidates


def test_bridge_preserves_valid_inline_event_semantics():
    inline = [
        {"choice_index": 0, "label": "Inline Accept", "text": "Inline text"},
        {"choice_index": 1, "label": "Inline Leave", "text": "Inline text"},
    ]
    snapshot = _snapshot(
        "event", _liars_game_state(inline_semantics=copy.deepcopy(inline))
    )
    drifted = _adapter_provenance()
    drifted["simulator_commit"] = "0" * 40

    enriched, source = enrich_event_option_semantics(
        snapshot=snapshot,
        candidates=_liars_game_candidates(),
        simulator_provenance=drifted,
    )

    assert source == "inline_legacy_contiguous"
    assert enriched["state"]["decision_context"]["option_semantics"] == [
        {
            **row,
            "current_position": index,
            "simulator_choice_index": index,
        }
        for index, row in enumerate(inline)
    ]


def test_bridge_preserves_versioned_inline_coordinates():
    inline = [
        {
            "choice_index": 0,
            "current_position": 0,
            "label": "Leave",
            "simulator_choice_index": 2,
            "text": "Leave",
        }
    ]
    snapshot = _snapshot(
        "event",
        _event_state("The Cleric", "The Cleric", inline_semantics=inline),
    )
    candidates = _event_candidates("The Cleric", "The Cleric", [2])

    enriched, source = enrich_event_option_semantics(
        snapshot=snapshot,
        candidates=candidates,
        simulator_provenance=None,
    )

    assert source == "inline_v2"
    assert enriched["state"]["decision_context"]["option_semantics"] == inline


def test_bridge_rejects_ambiguous_sparse_legacy_inline_semantics():
    inline = [{"choice_index": 0, "label": "Leave", "text": "Leave"}]
    snapshot = _snapshot(
        "event",
        _event_state("The Cleric", "The Cleric", inline_semantics=inline),
    )

    with pytest.raises(
        BridgeBlocked, match="event_option_semantics_legacy_ambiguous"
    ):
        enrich_event_option_semantics(
            snapshot=snapshot,
            candidates=_event_candidates("The Cleric", "The Cleric", [2]),
            simulator_provenance=None,
        )


@pytest.mark.parametrize(
    ("event_id", "event_name", "event_data", "simulator_index", "label"),
    [
        ("The Cleric", "The Cleric", 0, 2, "Leave"),
        ("Cursed Tome", "Cursed Tome", 2, 3, "Continue"),
    ],
)
def test_sparse_event_position_maps_back_to_simulator_choice_index(
    metadata, event_id, event_name, event_data, simulator_index, label
):
    snapshot = _snapshot(
        "event", _event_state(event_id, event_name, event_data=event_data)
    )
    candidates = _event_candidates(event_id, event_name, [simulator_index])

    enriched, _ = enrich_event_option_semantics(
        snapshot=snapshot,
        candidates=candidates,
        simulator_provenance=_adapter_provenance(),
    )
    semantics = enriched["state"]["decision_context"]["option_semantics"]
    game = hydrate_game(enriched, candidates, metadata)
    action_id = map_current_action(
        category="event",
        action=ChooseAction(0),
        candidates=candidates,
        event_semantics_validated=True,
        event_option_semantics=semantics,
    )

    assert semantics == [
        {
            "choice_index": 0,
            "current_position": 0,
            "label": label,
            "simulator_choice_index": simulator_index,
            "text": label,
        }
    ]
    assert game.choice_list[0].choice_index == 0
    assert action_id == candidates[0]["action_id"]


def test_event_reverse_mapping_rejects_invalid_current_position():
    candidates = _event_candidates("The Cleric", "The Cleric", [2])
    semantics = [
        {
            "choice_index": 0,
            "current_position": 0,
            "label": "Leave",
            "simulator_choice_index": 2,
            "text": "Leave",
        }
    ]

    with pytest.raises(BridgeBlocked, match="event_option_position_invalid"):
        map_current_action(
            category="event",
            action=ChooseAction(1),
            candidates=candidates,
            event_semantics_validated=True,
            event_option_semantics=semantics,
        )


def test_bridge_propagates_event_semantics_blocker():
    snapshot = _snapshot("event", _liars_game_state())
    snapshot["state"]["decision_context"]["event_id"] = "Big Fish"

    with pytest.raises(
        BridgeBlocked, match="event_option_semantics_event_identity_mismatch"
    ):
        enrich_event_option_semantics(
            snapshot=snapshot,
            candidates=_liars_game_candidates(),
            simulator_provenance=_adapter_provenance(),
        )


def test_current_session_uses_resolved_liars_game_semantics(metadata):
    snapshot = _snapshot("event", _liars_game_state())
    candidates = _liars_game_candidates()
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)
    session = CurrentPolicyBridgeSession(
        metadata=metadata,
        current_policy=_current_policy(),
        require_global_metadata_match=False,
        simulator_provenance=_adapter_provenance(),
    )

    result = session.evaluate(
        snapshot=snapshot,
        candidates=candidates,
        decision_index=11,
    )

    assert result["action_id"] == "event:the_ssssserpent:option:1"
    assert result["event_semantics_source"] == (
        "sts_lightspeed_reachable_event_observation_v3"
    )
    assert result["event_observation"] == {
        "current_event_id": "Liars Game",
        "current_position": 1,
        "event_data": 0,
        "selected_action_id": "event:the_ssssserpent:option:1",
        "semantics_source": "sts_lightspeed_reachable_event_observation_v3",
        "simulator_choice_index": 1,
        "upstream_event_id": "Liars Game",
    }
    assert snapshot == before_snapshot
    assert candidates == before_candidates


def test_current_session_maps_cleric_visible_position_to_sparse_candidate(metadata):
    snapshot = _snapshot(
        "event", _event_state("The Cleric", "The Cleric", event_data=0)
    )
    candidates = _event_candidates("The Cleric", "The Cleric", [2])
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)
    session = CurrentPolicyBridgeSession(
        metadata=metadata,
        current_policy=_current_policy(),
        require_global_metadata_match=False,
        simulator_provenance=_adapter_provenance(),
    )

    result = session.evaluate(
        snapshot=snapshot,
        candidates=candidates,
        decision_index=1,
    )

    assert result["action_id"] == candidates[0]["action_id"]
    assert result["event_semantics_source"] == (
        "sts_lightspeed_reachable_event_observation_v3"
    )
    assert result["event_observation"] == {
        "current_event_id": "The Cleric",
        "current_position": 0,
        "event_data": 0,
        "selected_action_id": candidates[0]["action_id"],
        "semantics_source": "sts_lightspeed_reachable_event_observation_v3",
        "simulator_choice_index": 2,
        "upstream_event_id": "The Cleric",
    }
    assert snapshot == before_snapshot
    assert candidates == before_candidates


def test_current_session_maps_generic_scrap_ooze_position_to_sparse_candidate(
    metadata,
):
    snapshot = _snapshot(
        "event", _event_state("Scrap Ooze", "Scrap Ooze", event_data=3)
    )
    candidates = [
        _candidate(
            "event",
            "event_option",
            "event:scrap_ooze:option:2",
            label="Try again",
            event_id="Scrap Ooze",
            idx1=2,
            idx2=0,
        ),
        _candidate(
            "event",
            "event_option",
            "event:scrap_ooze:option:7",
            label="Back away",
            event_id="Scrap Ooze",
            idx1=7,
            idx2=0,
        ),
    ]
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)
    session = CurrentPolicyBridgeSession(
        metadata=metadata,
        current_policy=_current_policy(),
        require_global_metadata_match=False,
        simulator_provenance=_adapter_provenance(),
    )

    result = session.evaluate(
        snapshot=snapshot,
        candidates=candidates,
        decision_index=1,
    )

    assert result["action_id"] == "event:scrap_ooze:option:2"
    assert result["event_observation"] == {
        "current_event_id": "Scrap Ooze",
        "current_position": 0,
        "event_data": 3,
        "selected_action_id": "event:scrap_ooze:option:2",
        "semantics_source": "sts_lightspeed_reachable_event_observation_v3",
        "simulator_choice_index": 2,
        "upstream_event_id": "Scrap Ooze",
    }
    assert snapshot == before_snapshot
    assert candidates == before_candidates


def test_historical_semantics_identity_keeps_predecessor_resolver():
    snapshot = _snapshot("event", _liars_game_state())

    enriched, source = enrich_event_option_semantics(
        snapshot=snapshot,
        candidates=_liars_game_candidates(),
        simulator_provenance=_adapter_provenance(),
        semantics_identity=event_option_semantics_identity(),
    )

    assert source == "sts_lightspeed_total_event_observation_v2"
    assert enriched["state"]["decision_context"]["event_id"] == "Liars Game"


def test_hydration_keeps_snapshot_and_candidates_unchanged(metadata):
    snapshot = _snapshot("route", _state())
    candidates = [
        _candidate("route", "map_node", "route:map_node:0:0", x=0, y=0)
    ]
    before_snapshot = copy.deepcopy(snapshot)
    before_candidates = copy.deepcopy(candidates)

    game = hydrate_game(snapshot, candidates, metadata)

    assert game.screen_type is ScreenType.MAP
    assert snapshot == before_snapshot
    assert candidates == before_candidates


def test_hydration_reconstructs_explicit_virtual_boss_root(metadata):
    state = _state()
    state["map"]["nodes"][0].update(
        {"edges": [{"x": 3, "y": 15}], "x": 0, "y": 14}
    )
    state["cur_map_node"] = {"x": 0, "y": 14}
    candidates = [
        _candidate(
            "route",
            "map_node",
            "route:map_node:3:15",
            room="BOSS",
            x=3,
            y=15,
        )
    ]

    game = hydrate_game(_snapshot("route", state), candidates, metadata)

    assert game.map.get_node(3, 15).symbol == "B"
    assert game.screen.boss_available is True


def test_stage1_failure_keeps_stage2_and_all_authority_closed():
    result = classify_stage1(
        row_results=[
            {"category": "route", "status": "passed"},
            {
                "category": "event",
                "status": "failed",
                "reason": "missing_event_option_semantics",
            },
        ],
        category_minimums={"event": 1, "route": 1},
    )

    assert result["verdict"] == "frozen_bridge_not_compatible"
    assert result["stage2_authorized"] is False
    assert result["authority"] == ALL_FALSE_AUTHORITY


def test_registration_rejects_any_positive_authority():
    registration = {
        "authority": {**ALL_FALSE_AUTHORITY, "training_authorized": True},
        "current_policy": {},
        "identity": {},
        "output": {},
        "schema_version": "noncombat-current-policy-simulator-bridge-input-v1",
        "stage1": {},
        "stage2": {},
    }

    with pytest.raises(BridgeBlocked, match="authority"):
        validate_registration(registration)


def test_successor_registration_accepts_only_declared_identity_changes():
    successor, predecessor = _successor_registration()

    comparison = validate_successor_registration(successor, predecessor)

    assert comparison["status"] == "passed"
    assert comparison["predecessor_schema_version"] == (
        "noncombat-current-policy-simulator-bridge-input-v1"
    )
    assert comparison["successor_schema_version"] == (
        "noncombat-current-policy-simulator-bridge-input-v2"
    )
    assert "stage1" in comparison["immutable_paths"]
    assert "identity.implementation" in comparison["mutable_paths"]


def test_v2_registration_rejects_reachable_successor_identity():
    successor, _ = _successor_registration()
    successor["identity"]["event_option_semantics"] = (
        reachable_event_option_semantics_identity()
    )

    with pytest.raises(BridgeBlocked, match="event_option_semantics_identity_mismatch"):
        validate_registration(successor)


def test_v1_registration_preserves_historical_source_file_contract():
    _, predecessor = _successor_registration()

    normalized = validate_registration(predecessor)
    assert normalized["identity"]["implementation"]["source_files"] == list(
        V1_REGISTERED_SOURCE_FILES
    )

    predecessor["identity"]["implementation"]["source_files"] = list(
        REGISTERED_SOURCE_FILES
    )
    with pytest.raises(BridgeBlocked, match="implementation_source_files_mismatch"):
        validate_registration(predecessor)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("identity", "adapter_provenance", "simulator_dirty"), False),
        (("identity", "frozen_demonstrations", "sha256"), "5" * 64),
        (("identity", "metadata", "sha256"), "6" * 64),
        (("identity", "prior_seed_evidence", "sha256"), "7" * 64),
        (("identity", "runtime", "python"), "9.9.9"),
        (("stage1", "category_minimums", "event"), 2),
        (("stage1", "replay_count"), 3),
        (("stage1", "rows", 0, "decision_index"), 99),
    ],
)
def test_successor_registration_rejects_immutable_identity_or_stage1_drift(
    path, value
):
    successor, predecessor = _successor_registration()
    target = successor
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value

    with pytest.raises(BridgeBlocked, match="successor_immutable_field_mismatch"):
        validate_successor_registration(successor, predecessor)


def test_successor_registration_rejects_stage2_seed_or_limit_drift():
    successor, predecessor = _successor_registration()
    successor["stage2"]["reused_seeds"] = [2000, 2001]
    successor["stage2"]["max_episodes"] = 2

    with pytest.raises(BridgeBlocked, match="successor_immutable_field_mismatch"):
        validate_successor_registration(successor, predecessor)


def test_successor_registration_rejects_current_policy_drift():
    successor, predecessor = _successor_registration()
    successor["current_policy"]["elite_mode"] = "aggressive"

    with pytest.raises(BridgeBlocked, match="current_policy_configuration_mismatch"):
        validate_successor_registration(successor, predecessor)


def test_successor_registration_rejects_authority_drift():
    successor, predecessor = _successor_registration()
    successor["authority"]["training_authorized"] = True

    with pytest.raises(BridgeBlocked, match="authority_must_be_all_false"):
        validate_successor_registration(successor, predecessor)


def test_successor_evidence_binds_predecessor_manifest_and_registration(tmp_path):
    successor, _, _ = _write_successor_evidence(tmp_path)

    comparison = validate_successor_evidence(
        validate_registration(successor), tmp_path
    )

    assert comparison["status"] == "passed"
    assert comparison["predecessor_verdict"] == "frozen_bridge_not_compatible"
    assert comparison["predecessor_registration"] == successor["identity"][
        "predecessor_registration"
    ]


def test_successor_evidence_rejects_manifest_registration_mismatch(tmp_path):
    successor, manifest, manifest_path = _write_successor_evidence(tmp_path)
    manifest["registration_sha256"] = "f" * 64
    manifest_bytes = canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    successor["identity"]["predecessor_manifest"].update(
        {
            "sha256": sha256_bytes(manifest_bytes),
            "size_bytes": len(manifest_bytes),
        }
    )

    with pytest.raises(
        BridgeBlocked, match="predecessor_manifest_registration_mismatch"
    ):
        validate_successor_evidence(validate_registration(successor), tmp_path)


def test_successor_artifacts_disclose_comparison(tmp_path):
    successor, _, _ = _write_successor_evidence(tmp_path)
    normalized = validate_registration(successor)
    comparison = validate_successor_evidence(normalized, tmp_path)
    classification = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "category_coverage": {
            "card_reward": True,
            "event": True,
            "route": True,
            "shop": True,
        },
        "passed": True,
        "stage2_authorized": True,
        "verdict": "frozen_bridge_structurally_compatible",
    }

    artifacts = build_artifacts(
        registration=normalized,
        registration_sha256="a" * 64,
        row_results=[],
        classification=classification,
        successor_comparison=comparison,
    )

    configuration = json.loads(artifacts["configuration.json"])
    metrics = json.loads(artifacts["metrics.json"])
    manifest = json.loads(artifacts["artifact_manifest.json"])
    assert configuration["successor_comparison"]["status"] == "passed"
    assert metrics["schema_version"].endswith("metrics-v2")
    assert manifest["schema_version"].endswith("manifest-v2")
    assert b"## Successor Integrity" in artifacts["report.md"]


def test_stage2_native_identity_accepts_exact_registration_and_rejects_drift():
    successor, _ = _successor_registration()
    actual = _stage2_native_identity(successor)

    assert validate_stage2_native_identity(successor, actual) == actual

    actual["module_sha256"] = "0" * 64
    with pytest.raises(BridgeBlocked, match="stage2_native_identity_mismatch"):
        validate_stage2_native_identity(successor, actual)


def test_stage2_runs_only_registered_seeds_with_deterministic_replay():
    successor, _ = _successor_registration()
    factory_calls = []

    def environment_factory(seed):
        factory_calls.append(seed)
        return _FakeStage2Environment(seed)

    result = run_stage2_compatibility(
        registration=successor,
        environment_factory=environment_factory,
        session_factory=_FakeStage2Session,
        native_identity=_stage2_native_identity(successor),
    )

    assert result["status"] == "passed"
    assert result["seeds"] == [2000, 2001, 2002, 2003]
    assert result["replay_count"] == 2
    assert [row["decision_count"] for row in result["rows"]] == [2, 2, 2, 2]
    assert factory_calls == [
        2000,
        2000,
        2001,
        2001,
        2002,
        2002,
        2003,
        2003,
    ]


def test_stage2_rejects_nondeterministic_trajectory():
    successor, _ = _successor_registration()
    calls = 0

    def environment_factory(seed):
        nonlocal calls
        calls += 1
        return _FakeStage2Environment(seed, divergent=(calls == 2))

    with pytest.raises(BridgeBlocked, match="stage2_trajectory_nondeterministic"):
        run_stage2_compatibility(
            registration=successor,
            environment_factory=environment_factory,
            session_factory=_FakeStage2Session,
            native_identity=_stage2_native_identity(successor),
        )


def test_stage2_rejects_decision_bound_exhaustion():
    successor, _ = _successor_registration()

    with pytest.raises(BridgeBlocked, match="stage2_decision_limit_exceeded"):
        run_stage2_compatibility(
            registration=successor,
            environment_factory=lambda seed: _FakeStage2Environment(
                seed, never_terminal=True
            ),
            session_factory=_FakeStage2Session,
            native_identity=_stage2_native_identity(successor),
        )


def test_stage2_result_is_published_in_canonical_artifacts():
    successor, predecessor = _successor_registration()
    comparison = validate_successor_registration(successor, predecessor)
    comparison.update(
        {
            "predecessor_manifest": successor["identity"][
                "predecessor_manifest"
            ],
            "predecessor_registration": successor["identity"][
                "predecessor_registration"
            ],
            "predecessor_verdict": "frozen_bridge_not_compatible",
        }
    )
    stage2_result = run_stage2_compatibility(
        registration=successor,
        environment_factory=_FakeStage2Environment,
        session_factory=_FakeStage2Session,
        native_identity=_stage2_native_identity(successor),
    )
    classification = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "category_coverage": {
            "card_reward": True,
            "event": True,
            "route": True,
            "shop": True,
        },
        "passed": True,
        "stage2_authorized": True,
        "verdict": "frozen_bridge_structurally_compatible",
    }

    artifacts = build_artifacts(
        registration=validate_registration(successor),
        registration_sha256="a" * 64,
        row_results=[],
        classification=classification,
        successor_comparison=comparison,
        stage2_result=stage2_result,
    )

    metrics = json.loads(artifacts["metrics.json"])
    manifest = json.loads(artifacts["artifact_manifest.json"])
    assert metrics["stage2"]["executed"] is True
    assert metrics["stage2"]["result"]["seeds"] == [2000, 2001, 2002, 2003]
    assert manifest["stage2_executed"] is True
    assert len(manifest["stage2_result_sha256"]) == 64
    assert b"registered reused-seed compatibility check passed" in artifacts[
        "report.md"
    ]


def test_stage2_failure_is_preserved_in_canonical_artifacts():
    successor, predecessor = _successor_registration()
    comparison = validate_successor_registration(successor, predecessor)
    comparison.update(
        {
            "predecessor_manifest": successor["identity"][
                "predecessor_manifest"
            ],
            "predecessor_registration": successor["identity"][
                "predecessor_registration"
            ],
            "predecessor_verdict": "frozen_bridge_not_compatible",
        }
    )
    stage2_result = {
        "detail": "Big Fish",
        "max_decisions_per_episode": 500,
        "native_identity": _stage2_native_identity(successor),
        "reason": "event_option_semantics_event_unsupported",
        "replay_count": 2,
        "schema_version": (
            "noncombat-current-policy-simulator-bridge-stage2-v1"
        ),
        "seeds": [2000, 2001, 2002, 2003],
        "status": "failed",
    }
    classification = {
        "authority": copy.deepcopy(ALL_FALSE_AUTHORITY),
        "category_coverage": {
            "card_reward": True,
            "event": True,
            "route": True,
            "shop": True,
        },
        "passed": True,
        "stage2_authorized": True,
        "verdict": "frozen_bridge_structurally_compatible",
    }

    artifacts = build_artifacts(
        registration=validate_registration(successor),
        registration_sha256="a" * 64,
        row_results=[],
        classification=classification,
        successor_comparison=comparison,
        stage2_result=stage2_result,
    )

    metrics = json.loads(artifacts["metrics.json"])
    assert metrics["stage2"]["executed"] is True
    assert metrics["stage2"]["reason"] == (
        "event_option_semantics_event_unsupported"
    )
    assert b"failed closed" in artifacts["report.md"]


def test_script_path_entrypoint_can_import_repository_modules():
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            str(
                repo_root
                / "analysis_scripts"
                / "noncombat_current_policy_simulator_bridge.py"
            ),
            "--help",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert "--registration" in completed.stdout
