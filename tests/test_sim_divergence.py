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
from spirecomm.spire.power import Power


def _card(
    name="Strike",
    card_id="Strike_R",
    card_type=CardType.ATTACK,
    cost=1,
    damage=6,
    block=0,
    upgrades=0,
    uuid="",
    misc=0,
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
        uuid=uuid,
        misc=misc,
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
    powers=None,
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
        powers=list(powers or []),
    )


def _relic(name, relic_id=None):
    return SimpleNamespace(name=name, relic_id=relic_id or name)


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
        relics=[],
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


def test_rampage_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    rampage = _card(
        name="Rampage",
        card_id="Rampage",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        uuid="rampage-1",
    )
    before = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=2),
        hand=[rampage],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=17, damage=6)],
    )
    actual = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=9, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_second_rampage_play_uses_accumulated_combat_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    first_rampage = _card(
        name="Rampage",
        card_id="Rampage",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        uuid="rampage-1",
    )
    first_before = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=2),
        hand=[first_rampage],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=60, damage=6)],
    )
    first_actual = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=52, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), first_before) is True
    assert observe_next_state(first_actual) is False

    second_rampage = _card(
        name="Rampage",
        card_id="Rampage",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        uuid="rampage-1",
    )
    second_before = _game(
        floor=14,
        turn=4,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=1),
        hand=[second_rampage],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=52, damage=6)],
    )
    second_actual = _game(
        floor=14,
        turn=4,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=39, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), second_before) is True
    assert observe_next_state(second_actual) is False
    assert not trace_path.exists()


def test_second_rampage_plus_play_uses_upgraded_combat_scaling(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    first_rampage = _card(
        name="Rampage+",
        card_id="Rampage",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        upgrades=1,
        uuid="rampage-1",
    )
    first_before = _game(
        floor=16,
        turn=3,
        player=SimpleNamespace(current_hp=42, max_hp=80, block=0, energy=2),
        hand=[first_rampage],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=80, damage=6)],
    )
    first_actual = _game(
        floor=16,
        turn=3,
        player=SimpleNamespace(current_hp=42, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=72, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), first_before) is True
    assert observe_next_state(first_actual) is False

    second_rampage = _card(
        name="Rampage+",
        card_id="Rampage",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        upgrades=1,
        uuid="rampage-1",
    )
    second_before = _game(
        floor=16,
        turn=6,
        player=SimpleNamespace(current_hp=42, max_hp=80, block=0, energy=1),
        hand=[second_rampage],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=72, damage=6)],
    )
    second_actual = _game(
        floor=16,
        turn=6,
        player=SimpleNamespace(current_hp=42, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=56, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), second_before) is True
    assert observe_next_state(second_actual) is False
    assert not trace_path.exists()


def test_rampage_accumulated_damage_resets_on_next_floor(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    rampage = _card(
        name="Rampage",
        card_id="Rampage",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        uuid="rampage-1",
    )
    first_before = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=2),
        hand=[rampage],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=60, damage=6)],
    )
    first_actual = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=52, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), first_before) is True
    assert observe_next_state(first_actual) is False

    next_floor_rampage = _card(
        name="Rampage",
        card_id="Rampage",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        uuid="rampage-1",
    )
    next_floor_before = _game(
        floor=15,
        turn=1,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=1),
        hand=[next_floor_rampage],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=60, damage=6)],
    )
    next_floor_actual = _game(
        floor=15,
        turn=1,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=52, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), next_floor_before) is True
    assert observe_next_state(next_floor_actual) is False
    assert not trace_path.exists()


def test_reckless_charge_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    reckless_charge = _card(
        name="Reckless Charge",
        card_id="Reckless Charge",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
    )
    before = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=3),
        hand=[reckless_charge],
        monsters=[_monster(name="Acid Slime (S)", monster_id="AcidSlime_S", hp=30, damage=6)],
    )
    actual = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[_monster(name="Acid Slime (S)", monster_id="AcidSlime_S", hp=23, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_reckless_charge_plus_zero_live_damage_uses_upgrade_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    reckless_charge_plus = _card(
        name="Reckless Charge+",
        card_id="Reckless Charge",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(current_hp=66, max_hp=80, block=0, energy=3),
        hand=[reckless_charge_plus],
        monsters=[_monster(name="Acid Slime (L)", monster_id="AcidSlime_L", hp=53, damage=16)],
    )
    actual = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(current_hp=66, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[_monster(name="Acid Slime (L)", monster_id="AcidSlime_L", hp=43, damage=16)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_uppercut_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    uppercut = _card(
        name="Uppercut",
        card_id="Uppercut",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=24,
        turn=2,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=3),
        hand=[uppercut],
        monsters=[
            _monster(name="Chosen", monster_id="Chosen", hp=73, damage=0, intent=Intent.STRONG_DEBUFF),
            _monster(name="Cultist", monster_id="Cultist", hp=52, damage=6),
        ],
    )
    actual = _game(
        floor=24,
        turn=2,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[
            _monster(name="Chosen", monster_id="Chosen", hp=60, damage=0, intent=Intent.STRONG_DEBUFF),
            _monster(name="Cultist", monster_id="Cultist", hp=52, damage=6),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_missing_target_attack_hits_only_live_monster(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    uppercut = _card(
        name="Uppercut",
        card_id="Uppercut",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
    )
    before = _game(
        floor=19,
        turn=2,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=3),
        hand=[uppercut],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=73, damage=0, intent=Intent.STRONG_DEBUFF)],
    )
    actual = _game(
        floor=19,
        turn=2,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=60, damage=0, intent=Intent.STRONG_DEBUFF)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_heavy_blade_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    heavy_blade = _card(
        name="Heavy Blade",
        card_id="Heavy Blade",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=3),
        hand=[heavy_blade],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=244, damage=6)],
    )
    actual = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=230, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_heavy_blade_zero_live_damage_uses_strength_scaling(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    heavy_blade = _card(
        name="Heavy Blade",
        card_id="Heavy Blade",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=28,
        turn=3,
        player=SimpleNamespace(
            current_hp=42,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Strength", "Strength", 3)],
        ),
        hand=[heavy_blade],
        monsters=[_monster(name="Centurion", monster_id="Centurion", hp=57, damage=7)],
    )
    actual = _game(
        floor=28,
        turn=3,
        player=SimpleNamespace(
            current_hp=42,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Strength", "Strength", 3)],
        ),
        hand=[],
        monsters=[_monster(name="Centurion", monster_id="Centurion", hp=34, damage=7)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_player_strength_increases_attack_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(
            current_hp=69,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Strength", "Strength", 2)],
        ),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6)],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=240, damage=0)],
    )
    actual = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(
            current_hp=69,
            max_hp=80,
            block=0,
            energy=2,
            powers=[Power("Strength", "Strength", 2)],
        ),
        hand=[],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=232, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_player_weak_reduces_attack_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(
            current_hp=52,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Weakened", "Weakened", 1)],
        ),
        hand=[_card(name="Bash", card_id="Bash", damage=8, cost=2)],
        monsters=[_monster(name="Acid Slime (S)", monster_id="AcidSlime_S", hp=9, damage=0)],
    )
    actual = _game(
        floor=14,
        turn=2,
        player=SimpleNamespace(
            current_hp=52,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Weakened", "Weakened", 1)],
        ),
        hand=[],
        monsters=[_monster(name="Acid Slime (S)", monster_id="AcidSlime_S", hp=3, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_rage_adds_block_when_attack_is_played(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=16,
        turn=5,
        player=SimpleNamespace(
            current_hp=50,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Rage", "Rage", 3)],
        ),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6)],
        monsters=[_monster(name="Slime Boss", monster_id="SlimeBoss", hp=73, damage=0)],
    )
    actual = _game(
        floor=16,
        turn=5,
        player=SimpleNamespace(
            current_hp=50,
            max_hp=80,
            block=3,
            energy=2,
            powers=[Power("Rage", "Rage", 3)],
        ),
        hand=[],
        monsters=[_monster(name="Slime Boss", monster_id="SlimeBoss", hp=67, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_rage_block_is_not_reduced_by_frail(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=16,
        turn=8,
        player=SimpleNamespace(
            current_hp=43,
            max_hp=80,
            block=11,
            energy=2,
            powers=[Power("Rage", "Rage", 3), Power("Frail", "Frail", 3)],
        ),
        hand=[_card(name="Pommel Strike+", card_id="Pommel Strike", damage=10, upgrades=1)],
        monsters=[_monster(name="Spike Slime (L)", monster_id="SpikeSlime_L", hp=37, damage=0)],
    )
    actual = _game(
        floor=16,
        turn=8,
        player=SimpleNamespace(
            current_hp=43,
            max_hp=80,
            block=14,
            energy=1,
            powers=[Power("Rage", "Rage", 3), Power("Frail", "Frail", 3)],
        ),
        hand=[],
        monsters=[_monster(name="Spike Slime (L)", monster_id="SpikeSlime_L", hp=27, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_rage_does_not_trigger_on_skill(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    defend = _card(
        name="Defend",
        card_id="Defend_R",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=5,
    )
    before = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(
            current_hp=55,
            max_hp=80,
            block=0,
            energy=2,
            powers=[Power("Rage", "Rage", 3)],
        ),
        hand=[defend],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=85, damage=0)],
    )
    actual = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(
            current_hp=55,
            max_hp=80,
            block=5,
            energy=1,
            powers=[Power("Rage", "Rage", 3)],
        ),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=85, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_ornamental_fan_adds_block_on_every_third_attack(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Ornamental Fan")]
    first_before = _game(
        floor=22,
        turn=1,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=0, energy=3),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6)],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=80, damage=0)],
        relics=relics,
    )
    first_actual = _game(
        floor=22,
        turn=1,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=74, damage=0)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), first_before) is True
    assert observe_next_state(first_actual) is False

    second_before = _game(
        floor=22,
        turn=1,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=0, energy=2),
        hand=[_card(name="Sever Soul", card_id="Sever Soul", damage=16, cost=1)],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=74, damage=0)],
        relics=relics,
    )
    second_actual = _game(
        floor=22,
        turn=1,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=58, damage=0)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), second_before) is True
    assert observe_next_state(second_actual) is False

    third_before = _game(
        floor=22,
        turn=1,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=0, energy=1),
        hand=[_card(name="Anger", card_id="Anger", damage=6, cost=0)],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=58, damage=0)],
        relics=relics,
    )
    third_actual = _game(
        floor=22,
        turn=1,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=4, energy=1),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=52, damage=0)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), third_before) is True
    assert observe_next_state(third_actual) is False
    assert not trace_path.exists()


def test_ornamental_fan_attack_count_resets_each_turn(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Ornamental Fan")]
    first_before = _game(
        floor=24,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=3),
        hand=[_card(name="Immolate", card_id="Immolate", damage=21, cost=1)],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=80, damage=0)],
        relics=relics,
    )
    first_actual = _game(
        floor=24,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=59, damage=0)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), first_before) is True
    assert observe_next_state(first_actual) is False

    second_before = _game(
        floor=24,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=2),
        hand=[_card(name="Sever Soul", card_id="Sever Soul", damage=16, cost=1)],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=59, damage=0)],
        relics=relics,
    )
    second_actual = _game(
        floor=24,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=43, damage=0)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), second_before) is True
    assert observe_next_state(second_actual) is False

    next_turn_before = _game(
        floor=24,
        turn=2,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=3),
        hand=[_card(name="Clothesline", card_id="Clothesline", damage=12, cost=1)],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=43, damage=0)],
        relics=relics,
    )
    next_turn_actual = _game(
        floor=24,
        turn=2,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=31, damage=0)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), next_turn_before) is True
    assert observe_next_state(next_turn_actual) is False
    assert not trace_path.exists()


def test_reaper_zero_live_damage_hits_all_and_heals_unblocked_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    reaper = _card(name="Reaper", card_id="Reaper", cost=2, damage=0)
    before = _game(
        floor=14,
        turn=1,
        player=SimpleNamespace(current_hp=51, max_hp=80, block=0, energy=2),
        hand=[reaper],
        monsters=[
            _monster(name="Louse", monster_id="LouseNormal", hp=6, block=6, damage=0),
            _monster(
                name="Louse",
                monster_id="LouseDefensive",
                hp=16,
                block=0,
                damage=0,
                powers=[Power("Curl Up", "Curl Up", 4)],
            ),
            _monster(
                name="Louse",
                monster_id="LouseDefensive",
                hp=16,
                block=0,
                damage=0,
                powers=[Power("Curl Up", "Curl Up", 3)],
            ),
        ],
    )
    actual = _game(
        floor=14,
        turn=1,
        player=SimpleNamespace(current_hp=59, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(name="Louse", monster_id="LouseNormal", hp=6, block=2, damage=0),
            _monster(name="Louse", monster_id="LouseDefensive", hp=12, block=4, damage=0),
            _monster(name="Louse", monster_id="LouseDefensive", hp=12, block=3, damage=0),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_reaper_plus_heal_caps_at_max_hp_after_strength_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    reaper_plus = _card(name="Reaper+", card_id="Reaper", cost=2, damage=0, upgrades=1)
    before = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(
            current_hp=66,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Strength", "Strength", 2)],
        ),
        hand=[reaper_plus],
        monsters=[
            _monster(name="Looter", monster_id="Looter", hp=11, damage=0),
            _monster(name="Mugger", monster_id="Mugger", hp=12, damage=0),
        ],
    )
    actual = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Strength", "Strength", 2)],
        ),
        hand=[],
        monsters=[
            _monster(name="Looter", monster_id="Looter", hp=4, damage=0),
            _monster(name="Mugger", monster_id="Mugger", hp=5, damage=0),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_explicit_heavy_blade_damage_uses_strength_multiplier(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    heavy_blade = _card(
        name="Heavy Blade",
        card_id="Heavy Blade",
        card_type=CardType.ATTACK,
        cost=2,
        damage=14,
    )
    before = _game(
        floor=18,
        turn=1,
        player=SimpleNamespace(
            current_hp=77,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Strength", "Strength", 2)],
        ),
        hand=[heavy_blade],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=44, damage=0)],
    )
    actual = _game(
        floor=18,
        turn=1,
        player=SimpleNamespace(
            current_hp=77,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Strength", "Strength", 2)],
        ),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=24, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_twin_strike_plus_uses_upgraded_damage_per_hit(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    twin_strike_plus = _card(
        name="Twin Strike+",
        card_id="Twin Strike",
        card_type=CardType.ATTACK,
        cost=1,
        damage=12,
        upgrades=1,
    )
    before = _game(
        floor=10,
        turn=1,
        player=SimpleNamespace(current_hp=53, max_hp=80, block=0, energy=3),
        hand=[twin_strike_plus],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=40, damage=12)],
    )
    actual = _game(
        floor=10,
        turn=1,
        player=SimpleNamespace(current_hp=53, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=26, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_twin_strike_strength_applies_to_each_hit(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    twin_strike_plus = _card(
        name="Twin Strike+",
        card_id="Twin Strike",
        card_type=CardType.ATTACK,
        cost=1,
        damage=12,
        upgrades=1,
    )
    before = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(
            current_hp=53,
            max_hp=80,
            block=3,
            energy=3,
            powers=[Power("Strength", "Strength", 6)],
        ),
        hand=[twin_strike_plus],
        monsters=[_monster(name="The Champ", monster_id="Champ", hp=367, damage=12)],
    )
    actual = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(
            current_hp=53,
            max_hp=80,
            block=3,
            energy=2,
            powers=[Power("Strength", "Strength", 6)],
        ),
        hand=[],
        monsters=[_monster(name="The Champ", monster_id="Champ", hp=341, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_twin_strike_strength_hits_block_per_hit(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    twin_strike_plus = _card(
        name="Twin Strike+",
        card_id="Twin Strike",
        card_type=CardType.ATTACK,
        cost=1,
        damage=12,
        upgrades=1,
    )
    before = _game(
        floor=31,
        turn=1,
        player=SimpleNamespace(
            current_hp=50,
            max_hp=80,
            block=13,
            energy=2,
            powers=[Power("Strength", "Strength", 3)],
        ),
        hand=[twin_strike_plus],
        monsters=[
            _monster(name="Sentry", monster_id="Sentry", hp=42, damage=9, index=0),
            _monster(
                name="Spheric Guardian",
                monster_id="SphericGuardian",
                hp=20,
                block=40,
                damage=10,
                index=1,
            ),
        ],
    )
    actual = _game(
        floor=31,
        turn=1,
        player=SimpleNamespace(
            current_hp=50,
            max_hp=80,
            block=13,
            energy=1,
            powers=[Power("Strength", "Strength", 3)],
        ),
        hand=[],
        monsters=[
            _monster(name="Sentry", monster_id="Sentry", hp=42, damage=9, index=0),
            _monster(
                name="Spheric Guardian",
                monster_id="SphericGuardian",
                hp=20,
                block=20,
                damage=10,
                index=1,
            ),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=1), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_sword_boomerang_single_live_monster_uses_three_hits(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    sword_boomerang = _card(
        name="Sword Boomerang",
        card_id="Sword Boomerang",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=1),
        hand=[sword_boomerang],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=48, damage=6)],
    )
    actual = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=39, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_sword_boomerang_vulnerable_block_is_applied_per_hit(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    sword_boomerang = _card(
        name="Sword Boomerang",
        card_id="Sword Boomerang",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=18,
        turn=6,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=4),
        hand=[sword_boomerang],
        monsters=[
            _monster(
                name="Shelled Parasite",
                monster_id="ShelledParasite",
                hp=42,
                block=11,
                damage=18,
                powers=[Power("Vulnerable", "Vulnerable", 1)],
            )
        ],
    )
    actual = _game(
        floor=18,
        turn=6,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Shelled Parasite",
                monster_id="ShelledParasite",
                hp=41,
                block=0,
                damage=18,
                powers=[Power("Vulnerable", "Vulnerable", 1)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_sword_boomerang_plus_uses_four_hits(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    sword_boomerang_plus = _card(
        name="Sword Boomerang+",
        card_id="Sword Boomerang",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=1),
        hand=[sword_boomerang_plus],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=48, damage=6)],
    )
    actual = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=36, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_pummel_zero_live_damage_uses_four_hits(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    pummel = _card(
        name="Pummel",
        card_id="Pummel",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=1),
        hand=[pummel],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=44, damage=12)],
    )
    actual = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=36, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_pummel_strength_applies_to_each_hit(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    pummel = _card(
        name="Pummel",
        card_id="Pummel",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(
            current_hp=72,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Strength", "Strength", 3)],
        ),
        hand=[pummel],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=26, damage=10)],
    )
    actual = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(
            current_hp=72,
            max_hp=80,
            block=0,
            energy=0,
            powers=[Power("Strength", "Strength", 3)],
        ),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=6, damage=10)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_pummel_vulnerable_applies_to_each_hit(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    pummel = _card(
        name="Pummel",
        card_id="Pummel",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=2,
        turn=2,
        player=SimpleNamespace(current_hp=73, max_hp=80, block=0, energy=1),
        hand=[pummel],
        monsters=[
            _monster(
                name="Cultist",
                monster_id="Cultist",
                hp=39,
                damage=6,
                powers=[Power("Vulnerable", "Vulnerable", 1)],
            )
        ],
    )
    actual = _game(
        floor=2,
        turn=2,
        player=SimpleNamespace(current_hp=73, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Cultist",
                monster_id="Cultist",
                hp=27,
                damage=6,
                powers=[Power("Vulnerable", "Vulnerable", 1)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_pummel_plus_uses_five_hits(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    pummel_plus = _card(
        name="Pummel+",
        card_id="Pummel",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=1),
        hand=[pummel_plus],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=44, damage=12)],
    )
    actual = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=34, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_dropkick_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    dropkick = _card(
        name="Dropkick",
        card_id="Dropkick",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=12,
        turn=4,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=3),
        hand=[dropkick],
        monsters=[_monster(name="Spike Slime (M)", monster_id="SpikeSlime_M", hp=9, damage=0)],
    )
    actual = _game(
        floor=12,
        turn=4,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Spike Slime (M)", monster_id="SpikeSlime_M", hp=4, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_dropkick_vulnerable_target_refunds_energy(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    dropkick = _card(
        name="Dropkick",
        card_id="Dropkick",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=1),
        hand=[dropkick],
        monsters=[
            _monster(
                name="Slime Boss",
                monster_id="SlimeBoss",
                hp=132,
                damage=0,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[
            _monster(
                name="Slime Boss",
                monster_id="SlimeBoss",
                hp=125,
                damage=0,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_sever_soul_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    sever_soul = _card(
        name="Sever Soul",
        card_id="Sever Soul",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=14,
        turn=1,
        player=SimpleNamespace(current_hp=58, max_hp=80, block=0, energy=3),
        hand=[sever_soul, _card(name="Defend", card_type=CardType.SKILL, damage=0, block=5)],
        monsters=[_monster(name="Louse", monster_id="FuzzyLouseNormal", hp=22, damage=0)],
    )
    actual = _game(
        floor=14,
        turn=1,
        player=SimpleNamespace(current_hp=58, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Louse", monster_id="FuzzyLouseNormal", hp=6, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_sever_soul_plus_zero_live_damage_uses_upgrade_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    sever_soul_plus = _card(
        name="Sever Soul+",
        card_id="Sever Soul",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=33,
        turn=5,
        player=SimpleNamespace(current_hp=40, max_hp=80, block=0, energy=3),
        hand=[sever_soul_plus, _card(name="Burn", card_type=CardType.STATUS, damage=0)],
        monsters=[_monster(name="Bronze Automaton", monster_id="BronzeAutomaton", hp=172, damage=0)],
    )
    actual = _game(
        floor=33,
        turn=5,
        player=SimpleNamespace(current_hp=40, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Bronze Automaton", monster_id="BronzeAutomaton", hp=150, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_swift_strike_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    swift_strike = _card(
        name="Swift Strike",
        card_id="Swift Strike",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
    )
    before = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=3),
        hand=[swift_strike],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=27, damage=12)],
    )
    actual = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=20, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_swift_strike_plus_zero_live_damage_uses_upgrade_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    swift_strike_plus = _card(
        name="Swift Strike+",
        card_id="Swift Strike",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=24,
        turn=3,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=4),
        hand=[swift_strike_plus],
        monsters=[_monster(name="Centurion", monster_id="Centurion", hp=47, damage=12)],
    )
    actual = _game(
        floor=24,
        turn=3,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=4),
        hand=[],
        monsters=[_monster(name="Centurion", monster_id="Centurion", hp=37, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_bludgeon_plus_zero_live_damage_uses_upgrade_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bludgeon_plus = _card(
        name="Bludgeon+",
        card_id="Bludgeon",
        card_type=CardType.ATTACK,
        cost=3,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=33,
        turn=1,
        player=SimpleNamespace(
            current_hp=47,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Strength", "Strength", 1)],
        ),
        hand=[bludgeon_plus],
        monsters=[_monster(name="The Champ", monster_id="Champ", hp=420, damage=16)],
    )
    actual = _game(
        floor=33,
        turn=1,
        player=SimpleNamespace(
            current_hp=47,
            max_hp=80,
            block=0,
            energy=0,
            powers=[Power("Strength", "Strength", 1)],
        ),
        hand=[],
        monsters=[_monster(name="The Champ", monster_id="Champ", hp=377, damage=16)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_searing_blow_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    searing_blow = _card(
        name="Searing Blow",
        card_id="Searing Blow",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=16,
        turn=3,
        player=SimpleNamespace(current_hp=59, max_hp=80, block=0, energy=3),
        hand=[searing_blow],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=202, damage=0)],
    )
    actual = _game(
        floor=16,
        turn=3,
        player=SimpleNamespace(current_hp=59, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=190, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_searing_blow_vulnerable_target_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    searing_blow = _card(
        name="Searing Blow",
        card_id="Searing Blow",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=3),
        hand=[searing_blow],
        monsters=[
            _monster(
                name="Jaw Worm",
                monster_id="JawWorm",
                hp=30,
                damage=0,
                powers=[Power("Vulnerable", "Vulnerable", 1)],
            )
        ],
    )
    actual = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[
            _monster(
                name="Jaw Worm",
                monster_id="JawWorm",
                hp=12,
                damage=0,
                powers=[Power("Vulnerable", "Vulnerable", 1)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_searing_blow_plus_two_uses_special_upgrade_scaling(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    searing_blow_plus_two = _card(
        name="Searing Blow+2",
        card_id="Searing Blow",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
        upgrades=2,
    )
    before = _game(
        floor=28,
        turn=3,
        player=SimpleNamespace(current_hp=67, max_hp=80, block=0, energy=3),
        hand=[searing_blow_plus_two],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=60, damage=0)],
    )
    actual = _game(
        floor=28,
        turn=3,
        player=SimpleNamespace(current_hp=67, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=39, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_immolate_zero_live_damage_hits_all_monsters(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    immolate = _card(
        name="Immolate",
        card_id="Immolate",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=19,
        turn=2,
        player=SimpleNamespace(current_hp=73, max_hp=80, block=0, energy=4),
        hand=[immolate],
        monsters=[
            _monster(name="Looter", monster_id="Looter", hp=48, damage=11, index=0),
            _monster(name="Mugger", monster_id="Mugger", hp=48, damage=11, index=1),
        ],
    )
    actual = _game(
        floor=19,
        turn=2,
        player=SimpleNamespace(current_hp=73, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(name="Looter", monster_id="Looter", hp=27, damage=11, index=0),
            _monster(name="Mugger", monster_id="Mugger", hp=27, damage=11, index=1),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_immolate_plus_zero_live_damage_uses_upgrade_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    immolate_plus = _card(
        name="Immolate+",
        card_id="Immolate",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=18,
        turn=3,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=4),
        hand=[immolate_plus],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=62, damage=0)],
    )
    actual = _game(
        floor=18,
        turn=3,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=34, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_vulnerable_target_damage_does_not_create_false_monster_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=1,
        turn=2,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=1),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6)],
        monsters=[
            _monster(
                name="Jaw Worm",
                monster_id="JawWorm",
                hp=30,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )
    actual = _game(
        floor=1,
        turn=2,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Jaw Worm",
                monster_id="JawWorm",
                hp=21,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_curl_up_target_gains_block_after_surviving_attack(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=3),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6)],
        monsters=[
            _monster(
                name="Louse",
                monster_id="FuzzyLouseDefensive",
                hp=12,
                damage=0,
                intent=Intent.NONE,
                powers=[Power("Curl Up", "Curl Up", 5)],
            )
        ],
    )
    actual = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(
                name="Louse",
                monster_id="FuzzyLouseDefensive",
                hp=6,
                block=5,
                damage=0,
                intent=Intent.NONE,
                powers=[],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_frail_player_block_does_not_create_false_player_diff(monkeypatch, tmp_path):
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
        floor=12,
        turn=2,
        player=SimpleNamespace(
            current_hp=55,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Frail", "Frail", 2)],
        ),
        hand=[defend_plus],
        monsters=[_monster(name="Sentry", monster_id="Sentry", hp=38, damage=10)],
    )
    actual = _game(
        floor=12,
        turn=2,
        player=SimpleNamespace(
            current_hp=55,
            max_hp=80,
            block=6,
            energy=0,
            powers=[Power("Frail", "Frail", 2)],
        ),
        hand=[],
        monsters=[_monster(name="Sentry", monster_id="Sentry", hp=38, damage=10)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_dexterity_increases_skill_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    defend = _card(
        name="Defend",
        card_id="Defend_R",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=5,
    )
    before = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(
            current_hp=72,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Dexterity", "Dexterity", 1)],
        ),
        hand=[defend],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=199, damage=0)],
    )
    actual = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(
            current_hp=72,
            max_hp=80,
            block=6,
            energy=2,
            powers=[Power("Dexterity", "Dexterity", 1)],
        ),
        hand=[],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=199, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_negative_dexterity_reduces_skill_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    defend = _card(
        name="Defend",
        card_id="Defend_R",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=5,
    )
    before = _game(
        floor=6,
        turn=6,
        player=SimpleNamespace(
            current_hp=41,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Dexterity", "Dexterity", -1)],
        ),
        hand=[defend],
        monsters=[_monster(name="Lagavulin", monster_id="Lagavulin", hp=21, damage=0)],
    )
    actual = _game(
        floor=6,
        turn=6,
        player=SimpleNamespace(
            current_hp=41,
            max_hp=80,
            block=4,
            energy=0,
            powers=[Power("Dexterity", "Dexterity", -1)],
        ),
        hand=[],
        monsters=[_monster(name="Lagavulin", monster_id="Lagavulin", hp=21, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_iron_wave_attack_block_matches_live_effect(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    iron_wave = _card(
        name="Iron Wave",
        card_id="Iron Wave",
        card_type=CardType.ATTACK,
        cost=1,
        damage=5,
        block=5,
    )
    before = _game(
        floor=10,
        turn=1,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=3),
        hand=[iron_wave],
        monsters=[_monster(name="Acid Slime (L)", monster_id="AcidSlime_L", hp=69, damage=16)],
    )
    actual = _game(
        floor=10,
        turn=1,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=5, energy=2),
        hand=[],
        monsters=[_monster(name="Acid Slime (L)", monster_id="AcidSlime_L", hp=64, damage=16)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_cleave_hits_all_live_monsters_without_target(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    cleave = _card(
        name="Cleave",
        card_id="Cleave",
        card_type=CardType.ATTACK,
        cost=1,
        damage=8,
    )
    before = _game(
        floor=2,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=2),
        hand=[cleave],
        monsters=[
            _monster(name="Louse", monster_id="FuzzyLouseDefensive", hp=14, damage=0, intent=Intent.NONE),
            _monster(name="Louse", monster_id="FuzzyLouseNormal", hp=11, damage=0, intent=Intent.NONE),
        ],
    )
    actual = _game(
        floor=2,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[
            _monster(name="Louse", monster_id="FuzzyLouseDefensive", hp=6, damage=0, intent=Intent.NONE),
            _monster(name="Louse", monster_id="FuzzyLouseNormal", hp=3, damage=0, intent=Intent.NONE),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_thunderclap_zero_live_damage_hits_all_monsters(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    thunderclap = _card(
        name="Thunderclap",
        card_id="Thunderclap",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=62, max_hp=80, block=0, energy=1),
        hand=[thunderclap],
        monsters=[
            _monster(name="Louse", monster_id="FuzzyLouseNormal", hp=10, block=7, damage=0, intent=Intent.NONE),
            _monster(name="Cultist", monster_id="Cultist", hp=43, damage=0, intent=Intent.NONE),
        ],
    )
    actual = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=62, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(name="Louse", monster_id="FuzzyLouseNormal", hp=10, block=3, damage=0, intent=Intent.NONE),
            _monster(name="Cultist", monster_id="Cultist", hp=39, damage=0, intent=Intent.NONE),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_whirlwind_zero_live_damage_spends_energy_for_all_enemy_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    whirlwind = _card(
        name="Whirlwind",
        card_id="Whirlwind",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
    )
    before = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(current_hp=58, max_hp=80, block=0, energy=3),
        hand=[whirlwind],
        monsters=[
            _monster(name="Slime Boss", monster_id="SlimeBoss", hp=120, damage=0, intent=Intent.NONE),
            _monster(name="Acid Slime (L)", monster_id="AcidSlime_L", hp=54, damage=11),
        ],
    )
    actual = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(current_hp=58, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(name="Slime Boss", monster_id="SlimeBoss", hp=105, damage=0, intent=Intent.NONE),
            _monster(name="Acid Slime (L)", monster_id="AcidSlime_L", hp=39, damage=11),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_whirlwind_plus_uses_upgraded_damage_per_energy(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    whirlwind_plus = _card(
        name="Whirlwind+",
        card_id="Whirlwind",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=27,
        turn=3,
        player=SimpleNamespace(current_hp=47, max_hp=80, block=0, energy=2),
        hand=[whirlwind_plus],
        monsters=[
            _monster(name="Centurion", monster_id="Centurion", hp=83, damage=12),
            _monster(name="Mystic", monster_id="Mystic", hp=50, damage=0, intent=Intent.NONE),
        ],
    )
    actual = _game(
        floor=27,
        turn=3,
        player=SimpleNamespace(current_hp=47, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(name="Centurion", monster_id="Centurion", hp=67, damage=12),
            _monster(name="Mystic", monster_id="Mystic", hp=34, damage=0, intent=Intent.NONE),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_finesse_zero_live_block_uses_base_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    finesse = _card(
        name="Finesse",
        card_id="Finesse",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
    )
    before = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=0),
        hand=[finesse],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=27, damage=11)],
    )
    actual = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=2, energy=0),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=27, damage=11)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_finesse_plus_zero_live_block_uses_upgrade_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    finesse_plus = _card(
        name="Finesse+",
        card_id="Finesse",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=0),
        hand=[finesse_plus],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=27, damage=11)],
    )
    actual = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=4, energy=0),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=27, damage=11)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_second_wind_zero_live_block_counts_non_attack_cards(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    second_wind = _card(
        name="Second Wind",
        card_id="Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=0,
    )
    before = _game(
        floor=7,
        turn=4,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=0, energy=3),
        hand=[
            _card(name="Clothesline", card_id="Clothesline", card_type=CardType.ATTACK, cost=2, damage=12),
            _card(name="Slimed", card_id="Slimed", card_type=CardType.STATUS, cost=1, damage=0),
            second_wind,
            _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, cost=1, damage=0, block=5),
            _card(name="Slimed", card_id="Slimed", card_type=CardType.STATUS, cost=1, damage=0),
        ],
        monsters=[_monster(name="Spike Slime (L)", monster_id="SpikeSlime_L", hp=45, damage=11)],
    )
    actual = _game(
        floor=7,
        turn=4,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=15, energy=2),
        hand=[],
        monsters=[_monster(name="Spike Slime (L)", monster_id="SpikeSlime_L", hp=45, damage=11)],
    )

    assert record_expected_action(PlayCardAction(card_index=2), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_second_wind_plus_uses_upgraded_block_per_non_attack(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    second_wind_plus = _card(
        name="Second Wind+",
        card_id="Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=20,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=4),
        hand=[
            _card(name="Offering+", card_id="Offering", card_type=CardType.SKILL, cost=0, damage=0, upgrades=1),
            _card(name="Evolve", card_id="Evolve", card_type=CardType.POWER, cost=1, damage=0),
            _card(name="Strike", card_id="Strike_R", card_type=CardType.ATTACK, cost=1, damage=6),
            second_wind_plus,
            _card(name="Sever Soul", card_id="Sever Soul", card_type=CardType.ATTACK, cost=2, damage=16),
        ],
        monsters=[_monster(name="Centurion", monster_id="Centurion", hp=83, damage=12)],
    )
    actual = _game(
        floor=20,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=14, energy=3),
        hand=[],
        monsters=[_monster(name="Centurion", monster_id="Centurion", hp=83, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=3), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_second_wind_plus_applies_dexterity_per_exhausted_non_attack(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    second_wind_plus = _card(
        name="Second Wind+",
        card_id="Second Wind",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=16,
        turn=6,
        player=SimpleNamespace(
            current_hp=60,
            max_hp=80,
            block=12,
            energy=2,
            powers=[Power("Dexterity", "Dexterity", 1)],
        ),
        hand=[
            second_wind_plus,
            _card(name="Slimed", card_id="Slimed", card_type=CardType.STATUS, cost=1, damage=0),
            _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, cost=1, damage=0, block=5),
            _card(name="Strike", card_id="Strike_R", card_type=CardType.ATTACK, cost=1, damage=6),
        ],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=136, damage=0)],
    )
    actual = _game(
        floor=16,
        turn=6,
        player=SimpleNamespace(
            current_hp=60,
            max_hp=80,
            block=28,
            energy=1,
            powers=[Power("Dexterity", "Dexterity", 1)],
        ),
        hand=[],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=136, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
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


def test_blood_for_blood_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    blood_for_blood = _card(
        name="Blood for Blood",
        card_id="Blood for Blood",
        card_type=CardType.ATTACK,
        cost=3,
        damage=0,
    )
    before = _game(
        floor=7,
        turn=2,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=3),
        hand=[blood_for_blood],
        monsters=[_monster(name="Looter", monster_id="Looter", hp=30, damage=10)],
    )
    actual = _game(
        floor=7,
        turn=2,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Looter", monster_id="Looter", hp=12, damage=10)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_blood_for_blood_plus_uses_upgrade_damage_bonus(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    blood_for_blood_plus = _card(
        name="Blood for Blood+",
        card_id="Blood for Blood",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=16,
        turn=10,
        player=SimpleNamespace(current_hp=14, max_hp=80, block=0, energy=2),
        hand=[blood_for_blood_plus],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=57,
                damage=0,
                intent=Intent.NONE,
                powers=[Power("Vulnerable", "Vulnerable", 4)],
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=10,
        player=SimpleNamespace(current_hp=14, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=24,
                damage=0,
                intent=Intent.NONE,
                powers=[Power("Vulnerable", "Vulnerable", 4)],
            )
        ],
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


def test_bloodletting_hp_energy_effect_does_not_create_false_player_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bloodletting = _card(
        name="Bloodletting",
        card_id="Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
    )
    before = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=74, max_hp=80, block=0, energy=0),
        hand=[bloodletting],
        monsters=[_monster(name="Looter", monster_id="Looter", hp=30, damage=10)],
    )
    actual = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=71, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Looter", monster_id="Looter", hp=30, damage=10)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_upgraded_bloodletting_gains_three_energy(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bloodletting_plus = _card(
        name="Bloodletting+",
        card_id="Bloodletting",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=74, max_hp=80, block=0, energy=0),
        hand=[bloodletting_plus],
        monsters=[_monster(name="Looter", monster_id="Looter", hp=30, damage=10)],
    )
    actual = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=71, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[_monster(name="Looter", monster_id="Looter", hp=30, damage=10)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_offering_hp_energy_effect_does_not_create_false_player_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    offering = _card(
        name="Offering",
        card_id="Offering",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
    )
    before = _game(
        floor=12,
        turn=1,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=0),
        hand=[offering],
        monsters=[_monster(name="Slaver", monster_id="SlaverBlue", hp=48, damage=12)],
    )
    actual = _game(
        floor=12,
        turn=1,
        player=SimpleNamespace(current_hp=58, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Slaver", monster_id="SlaverBlue", hp=48, damage=12)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_seeing_red_energy_gain_does_not_create_false_player_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    seeing_red = _card(
        name="Seeing Red",
        card_id="Seeing Red",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=0,
    )
    before = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=1),
        hand=[seeing_red],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=40, damage=6)],
    )
    actual = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=40, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_zero_cost_seeing_red_gains_two_energy(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    seeing_red_plus = _card(
        name="Seeing Red+",
        card_id="Seeing Red",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=20,
        turn=3,
        player=SimpleNamespace(current_hp=68, max_hp=80, block=8, energy=2),
        hand=[seeing_red_plus],
        monsters=[_monster(name="Byrd", monster_id="Byrd", hp=15, damage=0, intent=Intent.NONE)],
    )
    actual = _game(
        floor=20,
        turn=3,
        player=SimpleNamespace(current_hp=68, max_hp=80, block=8, energy=4),
        hand=[],
        monsters=[_monster(name="Byrd", monster_id="Byrd", hp=15, damage=0, intent=Intent.NONE)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_bandage_up_heals_and_caps_at_max_hp(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bandage_up = _card(
        name="Bandage Up",
        card_id="Bandage Up",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
    )
    before = _game(
        floor=5,
        turn=1,
        player=SimpleNamespace(current_hp=78, max_hp=80, block=0, energy=0),
        hand=[bandage_up],
        monsters=[_monster(name="Louse", monster_id="FuzzyLouseNormal", hp=16, damage=6)],
    )
    actual = _game(
        floor=5,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Louse", monster_id="FuzzyLouseNormal", hp=16, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_bandage_up_plus_heals_six(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bandage_up_plus = _card(
        name="Bandage Up+",
        card_id="Bandage Up",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=16,
        turn=3,
        player=SimpleNamespace(current_hp=45, max_hp=80, block=0, energy=0),
        hand=[bandage_up_plus],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=180, damage=6)],
    )
    actual = _game(
        floor=16,
        turn=3,
        player=SimpleNamespace(current_hp=51, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=180, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_good_instincts_zero_live_block_uses_base_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    good_instincts = _card(
        name="Good Instincts",
        card_id="Good Instincts",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
    )
    before = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=0),
        hand=[good_instincts],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=40, damage=6)],
    )
    actual = _game(
        floor=1,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=6, energy=0),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=40, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_good_instincts_plus_zero_live_block_uses_upgrade_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    good_instincts_plus = _card(
        name="Good Instincts+",
        card_id="Good Instincts",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=19,
        turn=5,
        player=SimpleNamespace(current_hp=74, max_hp=80, block=0, energy=0),
        hand=[good_instincts_plus],
        monsters=[_monster(name="Shelled Parasite", monster_id="Shelled Parasite", hp=68, damage=10)],
    )
    actual = _game(
        floor=19,
        turn=5,
        player=SimpleNamespace(current_hp=74, max_hp=80, block=9, energy=0),
        hand=[],
        monsters=[_monster(name="Shelled Parasite", monster_id="Shelled Parasite", hp=68, damage=10)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_sentinel_zero_live_block_uses_base_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    sentinel = _card(
        name="Sentinel",
        card_id="Sentinel",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=0,
    )
    before = _game(
        floor=13,
        turn=2,
        player=SimpleNamespace(current_hp=67, max_hp=80, block=0, energy=1),
        hand=[sentinel],
        monsters=[_monster(name="Spike Slime (L)", monster_id="SpikeSlime_L", hp=41, damage=16)],
    )
    actual = _game(
        floor=13,
        turn=2,
        player=SimpleNamespace(current_hp=67, max_hp=80, block=5, energy=0),
        hand=[],
        monsters=[_monster(name="Spike Slime (L)", monster_id="SpikeSlime_L", hp=41, damage=16)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_sentinel_plus_zero_live_block_uses_upgrade_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    sentinel_plus = _card(
        name="Sentinel+",
        card_id="Sentinel",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=0,
        upgrades=1,
    )
    before = _game(
        floor=16,
        turn=4,
        player=SimpleNamespace(current_hp=50, max_hp=80, block=3, energy=2),
        hand=[sentinel_plus],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=205, damage=6)],
    )
    actual = _game(
        floor=16,
        turn=4,
        player=SimpleNamespace(current_hp=50, max_hp=80, block=11, energy=1),
        hand=[],
        monsters=[_monster(name="Hexaghost", monster_id="Hexaghost", hp=205, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
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
