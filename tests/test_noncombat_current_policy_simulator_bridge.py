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
    MetadataCatalog,
    classify_stage1,
    hydrate_game,
    map_current_action,
    validate_registration,
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


@pytest.fixture
def metadata(tmp_path):
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
                "relics": [{"name": "Burning Blood"}],
                "potions": [{"name": "Attack Potion"}],
            }
        ),
        encoding="utf-8",
    )
    return MetadataCatalog(path)


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
                {"choice_index": 1, "label": "Leave", "text": "Leave"},
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
    assert [option.label for option in game.screen.options] == ["Agree", "Leave"]
    assert [option.choice_index for option in game.choice_list] == [0, 1]


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
