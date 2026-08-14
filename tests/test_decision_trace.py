import json
from types import SimpleNamespace

from spirecomm.ai.decision_trace import (
    build_decision_trace_event,
    write_decision_trace_event,
)
from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.communication.action import (
    BuyCardAction,
    CancelAction,
    CardRewardAction,
    ChooseAction,
    ChooseMapNodeAction,
    EndTurnAction,
    PlayCardAction,
    PotionAction,
)


def _card(name="Strike", card_id="Strike_R", cost=1, playable=True, price=0):
    return SimpleNamespace(
        name=name,
        card_id=card_id,
        cost_for_turn=cost,
        cost=cost,
        is_playable=playable,
        price=price,
    )


def _relic(name="Burning Blood", relic_id="BurningBlood", price=0):
    return SimpleNamespace(name=name, relic_id=relic_id, price=price, counter=0)


def _potion(name="Fire Potion", potion_id="FirePotion", price=0):
    return SimpleNamespace(
        name=name,
        potion_id=potion_id,
        can_use=True,
        can_discard=True,
        requires_target=False,
        price=price,
    )


def _node(x=0, y=0, symbol="M", children=None):
    node = SimpleNamespace(x=x, y=y, symbol=symbol, children=children or [])
    return node


def _monster(name="Cultist", hp=42, damage=6, intent="ATTACK"):
    return SimpleNamespace(
        name=name,
        monster_id=name,
        current_hp=hp,
        max_hp=hp,
        block=0,
        intent=intent,
        move_adjusted_damage=damage,
        move_hits=1,
        is_gone=False,
        half_dead=False,
    )


def _game():
    return SimpleNamespace(
        floor=7,
        turn=2,
        act=1,
        room_type="Monster",
        screen_type=None,
        in_combat=True,
        current_hp=44,
        max_hp=80,
        player=SimpleNamespace(current_hp=44, max_hp=80, block=5, energy=2),
        hand=[_card("Strike"), _card("Defend", card_id="Defend_R", playable=False)],
        deck=[_card("Strike"), _card("Defend", card_id="Defend_R"), _card("Bash", card_id="Bash")],
        relics=[_relic()],
        gold=123,
        monsters=[_monster()],
        potions=[_potion()],
        available_commands=["choose", "cancel"],
    )


def test_decision_trace_event_is_json_safe_and_keeps_combat_context():
    action = PlayCardAction(card_index=0, target_index=0)

    event = build_decision_trace_event(
        action,
        _game(),
        source="combat_rl",
        decision_path="rl_validated",
    )

    assert event["source"] == "combat_rl"
    assert event["decision_path"] == "rl_validated"
    assert event["floor"] == 7
    assert event["turn"] == 2
    assert event["player"]["energy"] == 2
    assert event["hand"][0]["name"] == "Strike"
    assert event["monsters"][0]["name"] == "Cultist"
    assert event["action"]["type"] == "PlayCardAction"
    assert event["action"]["card_index"] == 0
    assert event["action"]["target_index"] == 0
    json.dumps(event)


def test_decision_trace_resolves_bound_potion_index():
    fire = SimpleNamespace(name="Fire Potion", potion_id="FirePotion")
    elixir = SimpleNamespace(name="Elixir", potion_id="ElixirPotion")
    game = _game()
    game.potions = [fire, elixir]

    event = build_decision_trace_event(
        PotionAction(True, potion=elixir),
        game,
        source="combat_rl",
    )

    assert event["action"]["type"] == "PotionAction"
    assert event["action"]["potion_index"] == 1
    assert event["action"]["potion"]["id"] == "ElixirPotion"


def test_decision_trace_writer_is_disabled_without_env(monkeypatch, tmp_path):
    monkeypatch.delenv("STS_DECISION_TRACE_FILE", raising=False)
    trace_path = tmp_path / "trace.jsonl"

    assert write_decision_trace_event(EndTurnAction(), _game(), path=None) is False
    assert not trace_path.exists()


def test_combat_action_context_writes_decision_trace_when_enabled(monkeypatch, tmp_path):
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("STS_DECISION_TRACE_FILE", str(trace_path))

    agent = CombatRLAgent.__new__(CombatRLAgent)
    agent.rl_agent = None
    action = agent._with_combat_action_context(EndTurnAction(), _game())

    assert action.expected_floor == 7
    assert action.expected_turn == 2
    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["action"]["type"] == "EndTurnAction"
    assert records[0]["floor"] == 7


def test_noncombat_preview_defers_trace_until_selected_action_commit(
    monkeypatch,
    tmp_path,
):
    trace_path = tmp_path / "trace.jsonl"
    monkeypatch.setenv("STS_DECISION_TRACE_FILE", str(trace_path))
    agent = CombatRLAgent.__new__(CombatRLAgent)
    game = _game()
    baseline = CardRewardAction(_card("Anger", card_id="Anger"))

    agent._noncombat_exploration_preview = True
    assert agent._finalize_fallback_action(baseline, game) is baseline
    assert not trace_path.exists()

    agent._noncombat_exploration_preview = False
    selected = CancelAction()
    assert agent._finalize_fallback_action(selected, game) is selected
    records = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["action"]["type"] for record in records] == ["CancelAction"]


def test_decision_trace_includes_card_reward_snapshot():
    game = _game()
    offering = _card("Offering", card_id="Offering")
    flex = _card("Flex", card_id="Flex")
    game.screen_type = "ScreenType.CARD_REWARD"
    game.screen = SimpleNamespace(cards=[offering, flex], can_bowl=True, can_skip=True)

    event = build_decision_trace_event(
        CardRewardAction(flex),
        game,
        source="combat_rl",
    )

    assert event["gold"] == 123
    assert event["deck"][0]["name"] == "Strike"
    assert event["relics"][0]["name"] == "Burning Blood"
    assert event["available_commands"] == ["choose", "cancel"]
    assert event["screen"]["type"] == "ScreenType.CARD_REWARD"
    assert [card["name"] for card in event["screen"]["cards"]] == ["Offering", "Flex"]
    assert event["screen"]["can_bowl"] is True
    assert event["screen"]["can_skip"] is True
    assert event["action"]["name"] == "Flex"


def test_decision_trace_includes_shop_and_event_snapshots():
    game = _game()
    anger = _card("Anger", card_id="Anger", price=55)
    game.screen_type = "ScreenType.SHOP_SCREEN"
    game.screen = SimpleNamespace(
        cards=[anger],
        relics=[_relic("Bag of Marbles", "BagOfMarbles", price=150)],
        potions=[_potion("Strength Potion", "StrengthPotion", price=65)],
        purge_available=True,
        purge_cost=75,
    )

    shop_event = build_decision_trace_event(BuyCardAction(anger), game, source="combat_rl")

    assert shop_event["screen"]["type"] == "ScreenType.SHOP_SCREEN"
    assert shop_event["screen"]["cards"][0]["name"] == "Anger"
    assert shop_event["screen"]["cards"][0]["price"] == 55
    assert shop_event["screen"]["relics"][0]["name"] == "Bag of Marbles"
    assert shop_event["screen"]["potions"][0]["name"] == "Strength Potion"
    assert shop_event["screen"]["purge_available"] is True
    assert shop_event["screen"]["purge_cost"] == 75
    assert shop_event["action"]["name"] == "Anger"

    game.screen_type = "ScreenType.EVENT"
    game.screen = SimpleNamespace(
        event_name="Golden Shrine",
        event_id="GoldenShrine",
        options=[
            SimpleNamespace(text="Pray", label="Pray", disabled=False, choice_index=0),
            SimpleNamespace(text="Desecrate", label="Desecrate", disabled=False, choice_index=1),
        ],
    )

    event = build_decision_trace_event(ChooseAction(choice_index=1), game, source="combat_rl")

    assert event["screen"]["type"] == "ScreenType.EVENT"
    assert event["screen"]["event_name"] == "Golden Shrine"
    assert [option["label"] for option in event["screen"]["options"]] == ["Pray", "Desecrate"]
    assert event["action"]["choice_index"] == 1


def test_decision_trace_includes_map_snapshot_and_choice_index():
    game = _game()
    rest = _node(1, 1, "R")
    elite = _node(2, 1, "E")
    start = _node(0, 0, "M", children=[rest, elite])
    game.screen_type = "ScreenType.MAP"
    game.screen = SimpleNamespace(current_node=start, next_nodes=[rest, elite], boss_available=False)
    game.map = SimpleNamespace(nodes={0: {0: start}, 1: {1: rest, 2: elite}})

    event = build_decision_trace_event(ChooseMapNodeAction(elite), game, source="combat_rl")

    assert event["screen"]["type"] == "ScreenType.MAP"
    assert event["screen"]["current_node"]["symbol"] == "M"
    assert [node["symbol"] for node in event["screen"]["next_nodes"]] == ["R", "E"]
    assert event["screen"]["map"]["nodes"][0]["children"] == [{"x": 1, "y": 1}, {"x": 2, "y": 1}]
    assert event["action"]["choice_index"] == 1
    assert event["action"]["node"] == {"x": 2, "y": 1, "symbol": "E"}


def test_decision_trace_map_paths_resolve_screen_nodes_through_full_map():
    game = _game()
    rest = _node(1, 1, "R", children=[_node(1, 2, "$")])
    elite = _node(2, 1, "E", children=[_node(2, 2, "R")])
    start = _node(0, 0, "M", children=[rest, elite])
    screen_rest_copy = _node(1, 1, "R")
    screen_elite_copy = _node(2, 1, "E")
    game.screen_type = "ScreenType.MAP"
    game.screen = SimpleNamespace(
        current_node=start,
        next_nodes=[screen_rest_copy, screen_elite_copy],
        boss_available=False,
    )
    game.map = SimpleNamespace(nodes={0: {0: start}, 1: {1: rest, 2: elite}})

    event = build_decision_trace_event(ChooseMapNodeAction(screen_elite_copy), game, source="combat_rl")

    assert event["screen"]["paths"] == [
        {"choice": 0, "label": "R@1,1 -> $@1,2", "nodes": ["R", "$"]},
        {"choice": 1, "label": "E@2,1 -> R@2,2", "nodes": ["E", "R"]},
    ]
