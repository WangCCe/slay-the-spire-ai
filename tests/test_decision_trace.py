import json
from types import SimpleNamespace

from spirecomm.ai.decision_trace import (
    build_decision_trace_event,
    write_decision_trace_event,
)
from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.communication.action import EndTurnAction, PlayCardAction, PotionAction


def _card(name="Strike", card_id="Strike_R", cost=1, playable=True):
    return SimpleNamespace(
        name=name,
        card_id=card_id,
        cost_for_turn=cost,
        is_playable=playable,
    )


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
        monsters=[_monster()],
        potions=[SimpleNamespace(name="Fire Potion", potion_id="FirePotion")],
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

    action = CombatRLAgent._with_combat_action_context(EndTurnAction(), _game())

    assert action.expected_floor == 7
    assert action.expected_turn == 2
    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["action"]["type"] == "EndTurnAction"
    assert records[0]["floor"] == 7
