import json
from types import SimpleNamespace

from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.ai.sim_divergence import (
    observe_next_state,
    record_expected_action,
    reset_pending_divergence,
)
from spirecomm.communication.action import EndTurnAction, PlayCardAction
from spirecomm.spire.card import CardType
from spirecomm.spire.character import Intent


def _card(
    name="Strike",
    card_id="Strike_R",
    card_type=CardType.ATTACK,
    cost=1,
    damage=6,
    block=0,
    upgrades=0,
):
    return SimpleNamespace(
        name=name,
        card_id=card_id,
        type=card_type,
        cost=cost,
        cost_for_turn=cost,
        damage=damage,
        block=block,
        upgrades=upgrades,
        is_playable=True,
        has_target=card_type == CardType.ATTACK,
    )


def _monster(
    name="Cultist",
    monster_id="Cultist",
    hp=42,
    block=0,
    damage=6,
    hits=1,
    intent=Intent.ATTACK,
    index=0,
):
    return SimpleNamespace(
        name=name,
        monster_id=monster_id,
        current_hp=hp,
        max_hp=max(hp, 1),
        block=block,
        intent=intent,
        move_adjusted_damage=damage,
        move_hits=hits,
        monster_index=index,
        is_gone=False,
        half_dead=False,
        powers=[],
    )


def _game(**kwargs):
    defaults = dict(
        floor=16,
        turn=5,
        act=1,
        room_type="MonsterRoomBoss",
        screen_type=None,
        in_combat=True,
        current_hp=13,
        max_hp=80,
        player=SimpleNamespace(current_hp=13, max_hp=80, block=5, energy=2),
        hand=[],
        monsters=[],
        potions=[],
        play_available=True,
        end_available=True,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_sim_divergence_is_disabled_without_env(monkeypatch, tmp_path):
    monkeypatch.delenv("STS_SIM_DIVERGENCE_TRACE_FILE", raising=False)
    reset_pending_divergence()

    trace_path = tmp_path / "sim_divergence.jsonl"
    before = _game(hand=[_card()], monsters=[_monster()])

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is False
    assert observe_next_state(before, path=trace_path) is False
    assert not trace_path.exists()


def test_guardian_sharp_hide_diff_is_attributed(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    twin_strike = _card(
        name="Twin Strike",
        card_id="Twin Strike",
        card_type=CardType.ATTACK,
        cost=1,
        damage=10,
    )
    guardian = _monster(
        name="The Guardian",
        monster_id="TheGuardian",
        hp=165,
        damage=8,
        hits=2,
        intent=Intent.ATTACK_BUFF,
    )
    before = _game(hand=[twin_strike], monsters=[guardian])

    actual_guardian = _monster(
        name="The Guardian",
        monster_id="TheGuardian",
        hp=155,
        damage=8,
        hits=2,
        intent=Intent.ATTACK_BUFF,
    )
    actual = _game(
        current_hp=13,
        player=SimpleNamespace(current_hp=13, max_hp=80, block=2, energy=1),
        hand=[],
        monsters=[actual_guardian],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is True

    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["event_type"] == "sim_divergence"
    assert records[0]["reason"] == "guardian_sharp_hide_reflection"
    assert records[0]["action"]["card"]["name"] == "Twin Strike"
    assert records[0]["diffs"]["player.block"] == {"expected": 5, "actual": 2}


def test_upgraded_attack_damage_does_not_create_false_monster_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    strike_plus = _card(name="Strike+", card_id="Strike_R", damage=6, upgrades=1)
    before = _game(
        floor=8,
        turn=1,
        current_hp=55,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=3),
        hand=[strike_plus],
        monsters=[_monster(name="Slaver", monster_id="SlaverBlue", hp=48, damage=12)],
    )
    actual = _game(
        floor=8,
        turn=1,
        current_hp=55,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Slaver", monster_id="SlaverBlue", hp=39, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_headbutt_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    headbutt = _card(
        name="Headbutt",
        card_id="Headbutt",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=6,
        turn=2,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=3),
        hand=[headbutt],
        monsters=[_monster(name="Slaver", monster_id="SlaverBlue", hp=30, damage=12)],
    )
    actual = _game(
        floor=6,
        turn=2,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Slaver", monster_id="SlaverBlue", hp=21, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_clothesline_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    clothesline = _card(
        name="Clothesline",
        card_id="Clothesline",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=16,
        turn=9,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=3),
        hand=[clothesline],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=154, damage=6)],
    )
    actual = _game(
        floor=16,
        turn=9,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=142, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_hemokinesis_zero_live_damage_matches_live_effect(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    hemokinesis = _card(
        name="Hemokinesis",
        card_id="Hemokinesis",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=5,
        turn=2,
        player=SimpleNamespace(current_hp=50, max_hp=80, block=0, energy=3),
        hand=[hemokinesis],
        monsters=[_monster(name="Gremlin", monster_id="GremlinWarrior", hp=22, damage=3)],
    )
    actual = _game(
        floor=5,
        turn=2,
        player=SimpleNamespace(current_hp=48, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Gremlin", monster_id="GremlinWarrior", hp=7, damage=3)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_upgraded_skill_block_does_not_create_false_player_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    defend_plus = _card(
        name="Defend+",
        card_id="Defend_R",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=5,
        upgrades=1,
    )
    before = _game(
        floor=8,
        turn=1,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=1),
        hand=[defend_plus],
        monsters=[_monster(name="Slaver", monster_id="SlaverBlue", hp=48, damage=12)],
    )
    actual = _game(
        floor=8,
        turn=1,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=8, energy=0),
        hand=[],
        monsters=[_monster(name="Slaver", monster_id="SlaverBlue", hp=48, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_armaments_block_does_not_create_false_player_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    armaments_plus = _card(
        name="Armaments+",
        card_id="Armaments",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=16,
        turn=11,
        player=SimpleNamespace(current_hp=20, max_hp=80, block=11, energy=2),
        hand=[armaments_plus, _card(name="Strike", damage=6)],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=94, damage=14)],
    )
    actual = _game(
        floor=16,
        turn=11,
        player=SimpleNamespace(current_hp=20, max_hp=80, block=16, energy=1),
        hand=[_card(name="Strike+", damage=9, upgrades=1)],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=94, damage=14)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_energy_refresh_does_not_create_false_player_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=4,
        turn=1,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=22, damage=0, intent=Intent.NONE)],
    )
    actual = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=22, damage=0, intent=Intent.NONE)],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_combat_rl_checks_pending_divergence_on_next_state(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    strike = _card(name="Strike", damage=6)
    cultist = _monster(hp=42, damage=0, intent=Intent.NONE)
    before = _game(
        floor=3,
        turn=1,
        room_type="Monster",
        current_hp=70,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=1),
        hand=[strike],
        monsters=[cultist],
    )
    record_expected_action(PlayCardAction(card_index=0, target_index=0), before)

    actual = _game(
        floor=3,
        turn=1,
        room_type="Monster",
        current_hp=70,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(hp=41, damage=0, intent=Intent.NONE)],
    )
    agent = CombatRLAgent.__new__(CombatRLAgent)
    agent.fallback_agent = SimpleNamespace(get_next_action_in_game=lambda _game: EndTurnAction())
    agent.rl_agent = SimpleNamespace(get_next_action_in_game=lambda _game: EndTurnAction())
    agent.use_rl_for_combat = True
    agent.rl_failure_count = 0
    agent.max_rl_failures = 3
    agent._fallback_turn_key = None
    agent._reward_screen_key = None
    agent._reward_screen_waited = False
    agent.reward_screen_wait = 0

    agent.get_next_action_in_game(actual)

    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["reason"] == "monster_state_mismatch"
    assert records[0]["diffs"]["monsters[0].hp"] == {"expected": 36, "actual": 41}
