import json
from types import SimpleNamespace

from spirecomm.ai.rl.agent import CombatRLAgent
from spirecomm.ai.sim_divergence import (
    observe_next_state,
    record_expected_action,
    reset_pending_divergence,
)
from spirecomm.communication.action import (
    CancelAction,
    CardRewardAction,
    CardSelectAction,
    EndTurnAction,
    PlayCardAction,
    PotionAction,
)
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
    max_hp=None,
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
        max_hp=max(max_hp if max_hp is not None else hp, 1),
        block=block,
        intent=intent,
        move_adjusted_damage=damage,
        move_hits=hits,
        monster_index=index,
        is_gone=False,
        half_dead=False,
        powers=list(powers or []),
    )


def _relic(name, relic_id=None, counter=0):
    return SimpleNamespace(name=name, relic_id=relic_id or name, counter=counter)


def _potion(name, potion_id=None, effect_type="utility", effect_value=0, target_type="none"):
    return SimpleNamespace(
        name=name,
        potion_id=potion_id or name,
        effect_type=effect_type,
        effect_value=effect_value,
        target_type=target_type,
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


def test_blue_candle_curse_play_loses_one_hp(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    parasite = _card(
        name="Parasite",
        card_id="Parasite",
        card_type=CardType.CURSE,
        cost=0,
        damage=0,
    )
    before = _game(
        player=SimpleNamespace(current_hp=80, max_hp=80, block=8, energy=2),
        hand=[parasite],
        relics=[_relic("Burning Blood"), _relic("Blue Candle")],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=220, damage=9)],
    )
    actual = _game(
        player=SimpleNamespace(current_hp=79, max_hp=80, block=8, energy=2),
        hand=[],
        relics=[_relic("Burning Blood"), _relic("Blue Candle")],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=220, damage=9)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_curse_play_without_blue_candle_does_not_lose_hp(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    parasite = _card(
        name="Parasite",
        card_id="Parasite",
        card_type=CardType.CURSE,
        cost=0,
        damage=0,
    )
    before = _game(
        player=SimpleNamespace(current_hp=80, max_hp=80, block=8, energy=2),
        hand=[parasite],
        relics=[_relic("Burning Blood")],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=220, damage=9)],
    )
    actual = _game(
        player=SimpleNamespace(current_hp=80, max_hp=80, block=8, energy=2),
        hand=[],
        relics=[_relic("Burning Blood")],
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=220, damage=9)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_malleable_gains_block_after_attack_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    strike = _card(name="Strike", card_id="Strike_R", damage=6)
    before = _game(
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=3),
        hand=[strike],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=30,
                powers=[Power("Malleable", "Malleable", 3)],
            )
        ],
    )
    actual = _game(
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=24,
                block=3,
                powers=[Power("Malleable", "Malleable", 4)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_malleable_multi_hit_block_does_not_absorb_later_hits(monkeypatch, tmp_path):
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
    before = _game(
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=3),
        hand=[twin_strike],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=76,
                intent=Intent.STRONG_DEBUFF,
                powers=[
                    Power("Malleable", "Malleable", 3),
                    Power("Strength", "Strength", 1),
                ],
            )
        ],
    )
    actual = _game(
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=66,
                block=7,
                intent=Intent.STRONG_DEBUFF,
                powers=[
                    Power("Malleable", "Malleable", 5),
                    Power("Strength", "Strength", 1),
                ],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_guardian_sharp_hide_reflection_spends_block(monkeypatch, tmp_path):
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
        powers=[Power("Sharp Hide", "Sharp Hide", 3)],
    )
    before = _game(hand=[twin_strike], monsters=[guardian])

    actual_guardian = _monster(
        name="The Guardian",
        monster_id="TheGuardian",
        hp=155,
        damage=8,
        hits=2,
        intent=Intent.ATTACK_BUFF,
        powers=[Power("Sharp Hide", "Sharp Hide", 3)],
    )
    actual = _game(
        current_hp=13,
        player=SimpleNamespace(current_hp=13, max_hp=80, block=2, energy=1),
        hand=[],
        monsters=[actual_guardian],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_guardian_sharp_hide_reflection_damages_hp_without_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    strike = _card(name="Strike", card_id="Strike_R", damage=6)
    guardian = _monster(
        name="The Guardian",
        monster_id="TheGuardian",
        hp=165,
        damage=8,
        hits=2,
        intent=Intent.ATTACK_BUFF,
        powers=[Power("Sharp Hide", "Sharp Hide", 3)],
    )
    before = _game(
        player=SimpleNamespace(current_hp=20, max_hp=80, block=0, energy=1),
        hand=[strike],
        monsters=[guardian],
    )

    actual = _game(
        current_hp=17,
        player=SimpleNamespace(current_hp=17, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=159,
                damage=8,
                hits=2,
                intent=Intent.ATTACK_BUFF,
                powers=[Power("Sharp Hide", "Sharp Hide", 3)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_guardian_mode_shift_gains_block_and_keeps_bash_vulnerable(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bash = _card(name="Bash", card_id="Bash", cost=2, damage=8)
    guardian = _monster(
        name="The Guardian",
        monster_id="TheGuardian",
        hp=218,
        block=0,
        powers=[Power("Mode Shift", "Mode Shift", 8)],
    )
    before = _game(
        player=SimpleNamespace(current_hp=76, max_hp=80, block=10, energy=2),
        hand=[bash],
        monsters=[guardian],
    )
    actual = _game(
        player=SimpleNamespace(current_hp=76, max_hp=80, block=10, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=210,
                block=20,
                damage=-1,
                intent=Intent.BUFF,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


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


def test_headbutt_ornamental_fan_settles_after_card_select(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Ornamental Fan")]

    first_strike = _card(name="Strike", card_id="Strike_R", damage=6)
    first_before = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=0, energy=3),
        hand=[first_strike],
        relics=relics,
        monsters=[_monster(name="Bronze Orb", monster_id="BronzeOrb", hp=47, damage=8)],
    )
    first_actual = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=0, energy=2),
        hand=[],
        relics=relics,
        monsters=[_monster(name="Bronze Orb", monster_id="BronzeOrb", hp=41, damage=8)],
    )

    second_strike = _card(name="Strike", card_id="Strike_R", damage=6)
    second_before = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=0, energy=2),
        hand=[second_strike],
        relics=relics,
        monsters=[_monster(name="Bronze Orb", monster_id="BronzeOrb", hp=41, damage=8)],
    )
    second_actual = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=0, energy=1),
        hand=[],
        relics=relics,
        monsters=[_monster(name="Bronze Orb", monster_id="BronzeOrb", hp=35, damage=8)],
    )

    headbutt = _card(
        name="Headbutt",
        card_id="Headbutt",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    headbutt_before = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=0, energy=1),
        hand=[headbutt],
        relics=relics,
        monsters=[_monster(name="Bronze Orb", monster_id="BronzeOrb", hp=35, damage=8)],
    )
    select_screen = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=0, energy=0),
        hand=[],
        relics=relics,
        monsters=[_monster(name="Bronze Orb", monster_id="BronzeOrb", hp=26, damage=8)],
    )
    after_select = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=4, energy=0),
        hand=[],
        relics=relics,
        monsters=[_monster(name="Bronze Orb", monster_id="BronzeOrb", hp=26, damage=8)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), first_before) is True
    assert observe_next_state(first_actual) is False
    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), second_before) is True
    assert observe_next_state(second_actual) is False
    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), headbutt_before) is True
    assert observe_next_state(select_screen) is False
    assert record_expected_action(CardSelectAction([first_strike]), select_screen) is True
    assert observe_next_state(after_select) is False
    assert not trace_path.exists()


def test_headbutt_nunchaku_energy_settles_after_card_select(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Nunchaku", counter=9)]
    headbutt = _card(
        name="Headbutt",
        card_id="Headbutt",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=38,
        turn=4,
        player=SimpleNamespace(current_hp=49, max_hp=80, block=0, energy=1),
        hand=[headbutt],
        relics=relics,
        monsters=[_monster(name="Transient", monster_id="Transient", hp=120, damage=40)],
    )
    select_screen = _game(
        floor=38,
        turn=4,
        player=SimpleNamespace(current_hp=49, max_hp=80, block=0, energy=0),
        hand=[],
        relics=relics,
        monsters=[_monster(name="Transient", monster_id="Transient", hp=111, damage=40)],
    )
    after_select = _game(
        floor=38,
        turn=4,
        player=SimpleNamespace(current_hp=49, max_hp=80, block=0, energy=1),
        hand=[],
        relics=relics,
        monsters=[_monster(name="Transient", monster_id="Transient", hp=111, damage=40)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(select_screen) is False
    assert record_expected_action(CardSelectAction([headbutt]), select_screen) is True
    assert observe_next_state(after_select) is False
    assert not trace_path.exists()


def test_headbutt_guardian_mode_shift_settles_after_card_select(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    headbutt_plus = _card(
        name="Headbutt+",
        card_id="Headbutt",
        card_type=CardType.ATTACK,
        cost=1,
        damage=12,
        upgrades=1,
    )
    strike = _card(name="Strike", card_id="Strike_R", damage=6)
    before = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(current_hp=77, max_hp=80, block=24, energy=1),
        hand=[headbutt_plus, strike],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=220,
                damage=24,
                intent=Intent.ATTACK,
                powers=[
                    Power("Mode Shift", "Mode Shift", 10),
                    Power("Vulnerable", "Vulnerable", 3),
                    Power("Weakened", "Weakened", 1),
                ],
            )
        ],
    )
    select_screen = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(current_hp=77, max_hp=80, block=24, energy=0),
        hand=[strike],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=202,
                damage=24,
                intent=Intent.ATTACK,
                powers=[
                    Power("Mode Shift", "Mode Shift", -8),
                    Power("Vulnerable", "Vulnerable", 3),
                    Power("Weakened", "Weakened", 1),
                ],
            )
        ],
    )
    after_select = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(current_hp=77, max_hp=80, block=24, energy=0),
        hand=[strike],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=202,
                block=20,
                damage=-1,
                intent=Intent.BUFF,
                powers=[
                    Power("Vulnerable", "Vulnerable", 3),
                    Power("Weakened", "Weakened", 1),
                ],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(select_screen) is False
    assert record_expected_action(CardSelectAction([strike]), select_screen) is True
    assert observe_next_state(after_select) is False
    assert not trace_path.exists()


def test_headbutt_guardian_sharp_hide_settles_after_card_select(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    headbutt_plus = _card(
        name="Headbutt+",
        card_id="Headbutt",
        card_type=CardType.ATTACK,
        cost=1,
        damage=12,
        upgrades=1,
    )
    defend = _card(name="Defend+", card_id="Defend_R", card_type=CardType.SKILL, block=8, upgrades=1)
    before = _game(
        floor=16,
        turn=4,
        player=SimpleNamespace(current_hp=60, max_hp=80, block=0, energy=1),
        hand=[headbutt_plus, defend],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=106,
                damage=6,
                hits=2,
                intent=Intent.ATTACK_BUFF,
                powers=[
                    Power("Vulnerable", "Vulnerable", 1),
                    Power("Sharp Hide", "Sharp Hide", 3),
                    Power("Weakened", "Weakened", 2),
                ],
            )
        ],
    )
    select_screen = _game(
        floor=16,
        turn=4,
        player=SimpleNamespace(current_hp=60, max_hp=80, block=0, energy=0),
        hand=[defend],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=88,
                damage=6,
                hits=2,
                intent=Intent.ATTACK_BUFF,
                powers=[
                    Power("Vulnerable", "Vulnerable", 1),
                    Power("Sharp Hide", "Sharp Hide", 3),
                    Power("Weakened", "Weakened", 2),
                ],
            )
        ],
    )
    after_select = _game(
        floor=16,
        turn=4,
        player=SimpleNamespace(current_hp=57, max_hp=80, block=0, energy=0),
        hand=[defend],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=88,
                damage=6,
                hits=2,
                intent=Intent.ATTACK_BUFF,
                powers=[
                    Power("Vulnerable", "Vulnerable", 1),
                    Power("Sharp Hide", "Sharp Hide", 3),
                    Power("Weakened", "Weakened", 2),
                ],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(select_screen) is False
    assert record_expected_action(CardSelectAction([defend]), select_screen) is True
    assert observe_next_state(after_select) is False
    assert not trace_path.exists()


def test_headbutt_guardian_sharp_hide_block_loss_settles_after_card_select(
    monkeypatch,
    tmp_path,
):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    headbutt_plus = _card(
        name="Headbutt+",
        card_id="Headbutt",
        card_type=CardType.ATTACK,
        cost=1,
        damage=12,
        upgrades=1,
    )
    defend = _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, block=5)
    before = _game(
        floor=16,
        turn=8,
        player=SimpleNamespace(
            current_hp=2,
            max_hp=80,
            block=7,
            energy=2,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[headbutt_plus, defend],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=97,
                damage=0,
                intent=Intent.ATTACK_BUFF,
                powers=[Power("Sharp Hide", "Sharp Hide", 3)],
            )
        ],
    )
    select_screen = _game(
        floor=16,
        turn=8,
        player=SimpleNamespace(
            current_hp=2,
            max_hp=80,
            block=7,
            energy=1,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[defend],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=85,
                damage=0,
                intent=Intent.ATTACK_BUFF,
                powers=[Power("Sharp Hide", "Sharp Hide", 3)],
            )
        ],
    )
    after_select = _game(
        floor=16,
        turn=8,
        player=SimpleNamespace(
            current_hp=2,
            max_hp=80,
            block=4,
            energy=1,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[defend],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=85,
                damage=0,
                intent=Intent.ATTACK_BUFF,
                powers=[Power("Sharp Hide", "Sharp Hide", 3)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(select_screen) is False
    assert record_expected_action(CardSelectAction([defend]), select_screen) is True
    assert observe_next_state(after_select) is False
    assert not trace_path.exists()


def test_headbutt_malleable_block_settles_after_card_select(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    headbutt_plus = _card(
        name="Headbutt+",
        card_id="Headbutt",
        card_type=CardType.ATTACK,
        cost=1,
        damage=12,
        upgrades=1,
    )
    strike = _card(name="Strike", card_id="Strike_R", damage=6)
    before = _game(
        floor=30,
        turn=2,
        player=SimpleNamespace(
            current_hp=18,
            max_hp=85,
            block=0,
            energy=2,
            powers=[
                Power("Frail", "Frail", 2),
                Power("Weakened", "Weakened", 2),
            ],
        ),
        hand=[headbutt_plus, strike],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=42,
                block=3,
                damage=7,
                hits=3,
                powers=[
                    Power("Malleable", "Malleable", 4),
                    Power("Vulnerable", "Vulnerable", 2),
                ],
            )
        ],
    )
    select_screen = _game(
        floor=30,
        turn=2,
        player=SimpleNamespace(
            current_hp=18,
            max_hp=85,
            block=0,
            energy=1,
            powers=[
                Power("Frail", "Frail", 2),
                Power("Weakened", "Weakened", 2),
            ],
        ),
        hand=[strike],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=32,
                block=0,
                damage=7,
                hits=3,
                powers=[
                    Power("Malleable", "Malleable", 5),
                    Power("Vulnerable", "Vulnerable", 2),
                ],
            )
        ],
    )
    after_select = _game(
        floor=30,
        turn=2,
        player=SimpleNamespace(
            current_hp=18,
            max_hp=85,
            block=0,
            energy=1,
            powers=[
                Power("Frail", "Frail", 2),
                Power("Weakened", "Weakened", 2),
            ],
        ),
        hand=[strike],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=32,
                block=4,
                damage=7,
                hits=3,
                powers=[
                    Power("Malleable", "Malleable", 5),
                    Power("Vulnerable", "Vulnerable", 2),
                ],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(select_screen) is False
    assert record_expected_action(CardSelectAction([strike]), select_screen) is True
    assert observe_next_state(after_select) is False
    assert not trace_path.exists()


def test_headbutt_malleable_block_settles_after_card_select_with_implicit_target(
    monkeypatch,
    tmp_path,
):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    headbutt = _card(
        name="Headbutt",
        card_id="Headbutt",
        card_type=CardType.ATTACK,
        cost=1,
        damage=12,
    )
    strike = _card(name="Strike", card_id="Strike_R", damage=6)
    before = _game(
        floor=25,
        turn=3,
        player=SimpleNamespace(current_hp=5, max_hp=80, block=0, energy=1),
        hand=[headbutt, strike],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=20,
                block=3,
                damage=7,
                hits=3,
                powers=[Power("Malleable", "Malleable", 4)],
            )
        ],
    )
    select_screen = _game(
        floor=25,
        turn=3,
        player=SimpleNamespace(current_hp=5, max_hp=80, block=0, energy=0),
        hand=[strike],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=11,
                block=0,
                damage=7,
                hits=3,
                powers=[Power("Malleable", "Malleable", 5)],
            )
        ],
    )
    after_select = _game(
        floor=25,
        turn=3,
        player=SimpleNamespace(current_hp=5, max_hp=80, block=0, energy=0),
        hand=[strike],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=11,
                block=4,
                damage=7,
                hits=3,
                powers=[Power("Malleable", "Malleable", 5)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=None), before) is True
    assert observe_next_state(select_screen) is False
    assert record_expected_action(CardSelectAction([strike]), select_screen) is True
    assert observe_next_state(after_select) is False
    assert not trace_path.exists()


def test_card_select_without_headbutt_boundary_still_reports_player_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    selected_card = _card(name="Strike", card_id="Strike_R", damage=6)
    before = _game(
        floor=20,
        turn=3,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=42, damage=6)],
    )
    actual = _game(
        floor=20,
        turn=3,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=4, energy=1),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=42, damage=6)],
    )

    assert record_expected_action(CardSelectAction([selected_card]), before) is True
    assert observe_next_state(actual) is True
    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["reason"] == "player_state_mismatch"
    assert records[0]["diffs"]["player.block"] == {"expected": 0, "actual": 4}


def test_feed_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    feed = _card(
        name="Feed",
        card_id="Feed",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=2),
        hand=[feed],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=30, damage=11)],
    )
    actual = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=20, damage=11)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_feed_plus_uses_upgrade_damage_bonus(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    feed_plus = _card(
        name="Feed+",
        card_id="Feed",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=12,
        turn=1,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=3),
        hand=[feed_plus],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=30, damage=6)],
    )
    actual = _game(
        floor=12,
        turn=1,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=18, damage=6)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_mind_blast_zero_live_damage_uses_draw_pile_count(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    mind_blast = _card(
        name="Mind Blast+",
        card_id="Mind Blast",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        upgrades=1,
    )
    draw_pile = [
        _card(name=f"Draw {index}", card_id=f"Draw {index}")
        for index in range(7)
    ]
    before = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=75, max_hp=80, block=0, energy=3),
        hand=[mind_blast],
        draw_pile=draw_pile,
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=30, damage=-1, intent=Intent.BUFF)],
    )
    actual = _game(
        floor=7,
        turn=1,
        player=SimpleNamespace(current_hp=75, max_hp=80, block=0, energy=2),
        hand=[],
        draw_pile=draw_pile,
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=23, damage=-1, intent=Intent.BUFF)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_havoc_plus_uses_known_draw_pile_top_skill_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    havoc = _card(
        name="Havoc+",
        card_id="Havoc",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        upgrades=1,
    )
    bottom_strike = _card(name="Strike", card_id="Strike_R", damage=6, cost=1)
    top_defend = _card(
        name="Defend",
        card_id="Defend_R",
        card_type=CardType.SKILL,
        damage=0,
        block=5,
        cost=1,
    )
    before = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=10, energy=0),
        hand=[havoc],
        draw_pile=[bottom_strike, top_defend],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=45, damage=-1, intent=Intent.BUFF)],
    )
    actual = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=15, energy=0),
        hand=[],
        draw_pile=[bottom_strike],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=45, damage=-1, intent=Intent.BUFF)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_havoc_plus_uses_known_draw_pile_top_attack_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    havoc = _card(
        name="Havoc+",
        card_id="Havoc",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        upgrades=1,
    )
    bottom_defend = _card(
        name="Defend",
        card_id="Defend_R",
        card_type=CardType.SKILL,
        damage=0,
        block=5,
        cost=1,
    )
    top_strike = _card(name="Strike", card_id="Strike_R", damage=6, cost=1)
    before = _game(
        floor=8,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=10, energy=0),
        hand=[havoc],
        draw_pile=[bottom_defend, top_strike],
        monsters=[_monster(name="Slaver", monster_id="SlaverRed", hp=22, damage=8)],
    )
    actual = _game(
        floor=8,
        turn=2,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=10, energy=0),
        hand=[],
        draw_pile=[bottom_defend],
        monsters=[_monster(name="Slaver", monster_id="SlaverRed", hp=16, damage=8)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
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


def test_player_weak_and_target_vulnerable_use_combined_attack_multiplier(
    monkeypatch,
    tmp_path,
):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=27,
        turn=3,
        player=SimpleNamespace(
            current_hp=10,
            max_hp=80,
            block=0,
            energy=2,
            powers=[Power("Weakened", "Weakened", 1)],
        ),
        hand=[
            _card(
                name="Pommel Strike+",
                card_id="Pommel Strike",
                cost=1,
                damage=10,
                upgrades=1,
            )
        ],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=68,
                block=3,
                damage=0,
                powers=[
                    Power("Malleable", "Malleable", 4),
                    Power("Vulnerable", "Vulnerable", 1),
                ],
            )
        ],
    )
    actual = _game(
        floor=27,
        turn=3,
        player=SimpleNamespace(
            current_hp=10,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Weakened", "Weakened", 1)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=60,
                block=4,
                damage=0,
                powers=[
                    Power("Malleable", "Malleable", 5),
                    Power("Vulnerable", "Vulnerable", 1),
                ],
            )
        ],
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


def test_juggernaut_damages_single_alive_monster_when_block_is_gained(monkeypatch, tmp_path):
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
        floor=28,
        turn=3,
        player=SimpleNamespace(
            current_hp=42,
            max_hp=80,
            block=0,
            energy=2,
            powers=[Power("Juggernaut", "Juggernaut", 5)],
        ),
        hand=[defend_plus],
        monsters=[_monster(name="Shelled Parasite", monster_id="ShelledParasite", hp=72, block=13, damage=0)],
    )
    actual = _game(
        floor=28,
        turn=3,
        player=SimpleNamespace(
            current_hp=42,
            max_hp=80,
            block=8,
            energy=1,
            powers=[Power("Juggernaut", "Juggernaut", 5)],
        ),
        hand=[],
        monsters=[_monster(name="Shelled Parasite", monster_id="ShelledParasite", hp=72, block=8, damage=0)],
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


def test_nunchaku_counter_nine_attack_gains_one_energy(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bash = _card(name="Bash", card_id="Bash", damage=8, cost=2)
    relics = [_relic("Nunchaku", counter=9)]
    before = _game(
        floor=11,
        turn=2,
        player=SimpleNamespace(current_hp=59, max_hp=80, block=0, energy=3),
        hand=[bash],
        monsters=[_monster(name="Spike Slime (L)", monster_id="SpikeSlime_L", hp=50, damage=0)],
        relics=relics,
    )
    actual = _game(
        floor=11,
        turn=2,
        player=SimpleNamespace(current_hp=59, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Spike Slime (L)", monster_id="SpikeSlime_L", hp=42, damage=0)],
        relics=[_relic("Nunchaku", counter=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_pen_nib_counter_nine_doubles_attack_before_target_vulnerable(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    strike = _card(name="Strike", card_id="Strike_R", damage=6, cost=1)
    before = _game(
        floor=12,
        turn=1,
        player=SimpleNamespace(
            current_hp=66,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Pen Nib", "Pen Nib", 1)],
        ),
        hand=[strike],
        monsters=[
            _monster(
                name="Looter",
                monster_id="Looter",
                hp=36,
                damage=10,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
        relics=[_relic("Burning Blood", counter=-1), _relic("Pen Nib", counter=9)],
    )
    actual = _game(
        floor=12,
        turn=1,
        player=SimpleNamespace(current_hp=66, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(
                name="Looter",
                monster_id="Looter",
                hp=18,
                damage=10,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
        relics=[_relic("Burning Blood", counter=-1), _relic("Pen Nib", counter=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_pen_nib_counter_nine_doubles_attack_before_player_weak(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    blood_for_blood = _card(
        name="Blood for Blood+",
        card_id="Blood for Blood",
        damage=22,
        cost=1,
        upgrades=1,
    )
    before = _game(
        floor=24,
        turn=6,
        player=SimpleNamespace(
            current_hp=35,
            max_hp=80,
            block=11,
            energy=1,
            powers=[
                Power("Hex", "Hex", 1),
                Power("Pen Nib", "Pen Nib", 1),
                Power("Weakened", "Weakened", 4),
            ],
        ),
        hand=[blood_for_blood],
        monsters=[
            _monster(name="Cultist", monster_id="Cultist", hp=0, damage=6),
            _monster(
                name="Chosen",
                monster_id="Chosen",
                hp=46,
                damage=8,
                hits=2,
                index=1,
                powers=[Power("Strength", "Strength", 6), Power("Weakened", "Weakened", 1)],
            ),
        ],
        relics=[_relic("Burning Blood", counter=-1), _relic("Pen Nib", counter=9)],
    )
    before.monsters[0].is_gone = True
    actual = _game(
        floor=24,
        turn=6,
        player=SimpleNamespace(
            current_hp=35,
            max_hp=80,
            block=11,
            energy=0,
            powers=[Power("Hex", "Hex", 1), Power("Weakened", "Weakened", 4)],
        ),
        hand=[],
        monsters=[
            _monster(name="Cultist", monster_id="Cultist", hp=0, damage=6),
            _monster(
                name="Chosen",
                monster_id="Chosen",
                hp=13,
                damage=8,
                hits=2,
                index=1,
                powers=[Power("Strength", "Strength", 6), Power("Weakened", "Weakened", 1)],
            ),
        ],
        relics=[_relic("Burning Blood", counter=-1), _relic("Pen Nib", counter=0)],
    )
    actual.monsters[0].is_gone = True

    assert record_expected_action(PlayCardAction(card_index=0, target_index=1), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_energy_potion_gains_two_energy(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    potion = _potion(
        "Energy Potion",
        effect_type="energy",
        effect_value=2,
        target_type="self",
    )
    before = _game(
        floor=4,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=3),
        hand=[_card(name="Heavy Blade", card_id="Heavy Blade", damage=14)],
        monsters=[_monster(name="Fat Gremlin", monster_id="FatGremlin", hp=13, damage=0)],
        potions=[potion],
    )
    actual = _game(
        floor=4,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=5),
        hand=[_card(name="Heavy Blade", card_id="Heavy Blade", damage=14)],
        monsters=[_monster(name="Fat Gremlin", monster_id="FatGremlin", hp=13, damage=0)],
        potions=[],
    )

    assert record_expected_action(PotionAction(use=True, potion=potion), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_block_potion_gains_twelve_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    potion = _potion(
        "Block Potion",
        effect_type="block",
        effect_value=12,
        target_type="self",
    )
    before = _game(
        floor=10,
        turn=2,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=3),
        hand=[_card(name="Strike", card_id="Strike_R")],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=20, damage=0)],
        potions=[potion],
    )
    actual = _game(
        floor=10,
        turn=2,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=12, energy=3),
        hand=[_card(name="Strike", card_id="Strike_R")],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=20, damage=0)],
        potions=[],
    )

    assert record_expected_action(PotionAction(use=True, potion=potion), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_explosive_potion_deals_ten_to_all_monsters(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    potion = _potion(
        "Explosive Potion",
        effect_type="damage",
        effect_value=10,
        target_type="all_monsters",
    )
    before = _game(
        floor=30,
        turn=1,
        player=SimpleNamespace(current_hp=58, max_hp=80, block=45, energy=2),
        hand=[_card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=5)],
        monsters=[
            _monster(name="Cultist", monster_id="Cultist", hp=51, damage=0, index=0),
            _monster(name="Cultist", monster_id="Cultist", hp=50, damage=0, index=1),
            _monster(name="Cultist", monster_id="Cultist", hp=53, damage=0, index=2),
        ],
        potions=[potion],
    )
    actual = _game(
        floor=30,
        turn=1,
        player=SimpleNamespace(current_hp=58, max_hp=80, block=45, energy=2),
        hand=[_card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=5)],
        monsters=[
            _monster(name="Cultist", monster_id="Cultist", hp=41, damage=0, index=0),
            _monster(name="Cultist", monster_id="Cultist", hp=40, damage=0, index=1),
            _monster(name="Cultist", monster_id="Cultist", hp=43, damage=0, index=2),
        ],
        potions=[],
    )

    assert record_expected_action(PotionAction(use=True, potion=potion), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_fruit_juice_gains_max_hp_and_current_hp(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    potion = _potion(
        "Fruit Juice",
        potion_id="Fruit Juice",
        effect_type="max_hp",
        effect_value=5,
        target_type="self",
    )
    before = _game(
        floor=8,
        turn=1,
        player=SimpleNamespace(current_hp=74, max_hp=80, block=0, energy=1),
        hand=[_card(name="Strike", card_id="Strike_R")],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=20, damage=0)],
        potions=[potion],
    )
    actual = _game(
        floor=8,
        turn=1,
        player=SimpleNamespace(current_hp=79, max_hp=85, block=0, energy=1),
        hand=[_card(name="Strike", card_id="Strike_R")],
        monsters=[_monster(name="Fungi Beast", monster_id="FungiBeast", hp=20, damage=0)],
        potions=[],
    )

    assert record_expected_action(PotionAction(use=True, potion=potion), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_blood_potion_heals_percent_of_max_hp(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    potion = _potion(
        "Blood Potion",
        potion_id="BloodPotion",
        effect_type="heal_percent",
        effect_value=0.2,
        target_type="self",
    )
    before = _game(
        floor=21,
        turn=1,
        player=SimpleNamespace(current_hp=34, max_hp=80, block=0, energy=3),
        hand=[_card(name="Strike", card_id="Strike_R")],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=99, damage=10)],
        potions=[potion],
    )
    actual = _game(
        floor=21,
        turn=1,
        player=SimpleNamespace(current_hp=50, max_hp=80, block=0, energy=3),
        hand=[_card(name="Strike", card_id="Strike_R")],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=99, damage=10)],
        potions=[],
    )

    assert record_expected_action(PotionAction(use=True, potion=potion), before) is True
    assert observe_next_state(actual) is False
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


def test_sword_boomerang_multi_monster_random_hits_do_not_report_distribution(
    monkeypatch,
    tmp_path,
):
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
        floor=8,
        turn=2,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=1),
        hand=[sword_boomerang],
        monsters=[
            _monster(name="Fungi Beast", monster_id="FungiBeast", hp=15, damage=9),
            _monster(name="Fungi Beast", monster_id="FungiBeast", hp=13, damage=6, index=1),
        ],
    )
    actual = _game(
        floor=8,
        turn=2,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(name="Fungi Beast", monster_id="FungiBeast", hp=12, damage=9),
            _monster(name="Fungi Beast", monster_id="FungiBeast", hp=7, damage=6, index=1),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
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


def test_fiend_fire_zero_live_damage_uses_other_hand_cards_as_hits(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    fiend_fire = _card(
        name="Fiend Fire",
        card_id="Fiend Fire",
        card_type=CardType.ATTACK,
        cost=0,
        damage=0,
    )
    before = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(current_hp=68, max_hp=80, block=0, energy=4),
        hand=[
            fiend_fire,
            _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=5),
            _card(name="Bash", card_id="Bash", damage=8, cost=2),
            _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=5),
            _card(name="Carnage+", card_id="Carnage", damage=28, cost=0, upgrades=1),
            _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=5),
            _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=5),
        ],
        monsters=[
            _monster(name="Looter", monster_id="Looter", hp=0, damage=7, index=0),
            _monster(name="Mugger", monster_id="Mugger", hp=51, damage=10, index=1),
        ],
    )
    actual = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(current_hp=68, max_hp=80, block=0, energy=4),
        hand=[],
        monsters=[
            _monster(name="Looter", monster_id="Looter", hp=0, damage=7, index=0),
            _monster(name="Mugger", monster_id="Mugger", hp=9, damage=10, index=1),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=1), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_fiend_fire_zero_live_damage_repeats_against_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    fiend_fire = _card(
        name="Fiend Fire",
        card_id="Fiend Fire",
        card_type=CardType.ATTACK,
        cost=2,
        damage=0,
    )
    before = _game(
        floor=20,
        turn=2,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=3),
        hand=[
            _card(name="Carnage+", card_id="Carnage", damage=28, cost=2, upgrades=1),
            _card(name="Havoc", card_id="Havoc", card_type=CardType.SKILL, damage=0, cost=1),
            _card(name="Clothesline", card_id="Clothesline", damage=12, cost=2),
            _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=5),
            _card(name="Defend", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=5),
            fiend_fire,
            _card(name="Carnage+", card_id="Carnage", damage=28, cost=2, upgrades=1),
        ],
        monsters=[
            _monster(
                name="Spheric Guardian",
                monster_id="SphericGuardian",
                hp=20,
                block=44,
                damage=10,
            )
        ],
    )
    actual = _game(
        floor=20,
        turn=2,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[
            _monster(
                name="Spheric Guardian",
                monster_id="SphericGuardian",
                hp=20,
                block=2,
                damage=10,
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=5, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_fiend_fire_plus_uses_ten_damage_per_other_hand_card(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    fiend_fire_plus = _card(
        name="Fiend Fire+",
        card_id="Fiend Fire",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=44, max_hp=80, block=0, energy=3),
        hand=[
            _card(name="Defend+", card_id="Defend_R", card_type=CardType.SKILL, damage=0, block=8, upgrades=1),
            fiend_fire_plus,
            _card(name="Rampage", card_id="Rampage", damage=8),
            _card(name="Iron Wave+", card_id="Iron Wave", damage=7, block=7, upgrades=1),
        ],
        monsters=[_monster(name="Mystic", monster_id="Healer", hp=40, damage=0, index=0)],
    )
    actual = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=44, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Mystic", monster_id="Healer", hp=10, damage=0, index=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=1, target_index=0), before) is True
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


def test_sever_soul_triggers_feel_no_pain_for_each_exhausted_non_attack(monkeypatch, tmp_path):
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
        floor=21,
        turn=4,
        player=SimpleNamespace(
            current_hp=45,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Feel No Pain", "Feel No Pain", 4)],
        ),
        hand=[
            _card(name="Defend+", card_id="Defend_R", card_type=CardType.SKILL, cost=1, damage=0, block=5, upgrades=1),
            sever_soul_plus,
            _card(name="Defend+", card_id="Defend_R", card_type=CardType.SKILL, cost=1, damage=0, block=5, upgrades=1),
        ],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=40, damage=0)],
    )
    actual = _game(
        floor=21,
        turn=4,
        player=SimpleNamespace(
            current_hp=45,
            max_hp=80,
            block=8,
            energy=1,
            powers=[Power("Feel No Pain", "Feel No Pain", 4)],
        ),
        hand=[],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=18, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=1, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_true_grit_triggers_feel_no_pain_for_one_exhausted_card(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    true_grit = _card(
        name="True Grit",
        card_id="True Grit",
        card_type=CardType.SKILL,
        cost=1,
        damage=0,
        block=7,
    )
    before = _game(
        floor=21,
        turn=3,
        player=SimpleNamespace(
            current_hp=70,
            max_hp=80,
            block=0,
            energy=3,
            powers=[
                Power("Feel No Pain", "Feel No Pain", 3),
                Power("Frail", "Frail", 2),
            ],
        ),
        hand=[true_grit, _card(name="Strike", card_id="Strike_R")],
        monsters=[_monster(name="Shelled Parasite", monster_id="Shelled Parasite", hp=57, damage=0)],
    )
    actual = _game(
        floor=21,
        turn=3,
        player=SimpleNamespace(
            current_hp=70,
            max_hp=80,
            block=8,
            energy=2,
            powers=[
                Power("Feel No Pain", "Feel No Pain", 3),
                Power("Frail", "Frail", 2),
            ],
        ),
        hand=[],
        monsters=[_monster(name="Shelled Parasite", monster_id="Shelled Parasite", hp=57, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_corruption_skill_exhaust_triggers_feel_no_pain(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    defend = _card(
        name="Defend",
        card_id="Defend_R",
        card_type=CardType.SKILL,
        cost=0,
        damage=0,
        block=5,
    )
    before = _game(
        floor=33,
        turn=5,
        player=SimpleNamespace(
            current_hp=44,
            max_hp=87,
            block=0,
            energy=1,
            powers=[
                Power("Feel No Pain", "Feel No Pain", 4),
                Power("Corruption", "Corruption", -1),
            ],
        ),
        hand=[defend],
        monsters=[_monster(name="The Champ", monster_id="Champ", hp=340, damage=0)],
    )
    actual = _game(
        floor=33,
        turn=5,
        player=SimpleNamespace(
            current_hp=44,
            max_hp=87,
            block=9,
            energy=1,
            powers=[
                Power("Feel No Pain", "Feel No Pain", 4),
                Power("Corruption", "Corruption", -1),
            ],
        ),
        hand=[],
        monsters=[_monster(name="The Champ", monster_id="Champ", hp=340, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
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


def test_wild_strike_zero_live_damage_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    wild_strike = _card(
        name="Wild Strike",
        card_id="Wild Strike",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=8,
        turn=1,
        player=SimpleNamespace(current_hp=77, max_hp=80, block=0, energy=3),
        hand=[wild_strike],
        monsters=[_monster(name="Acid Slime (M)", monster_id="AcidSlime_M", hp=32, damage=10)],
    )
    actual = _game(
        floor=8,
        turn=1,
        player=SimpleNamespace(current_hp=77, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Acid Slime (M)", monster_id="AcidSlime_M", hp=20, damage=10)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_wild_strike_vulnerable_target_uses_base_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    wild_strike = _card(
        name="Wild Strike",
        card_id="Wild Strike",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
    )
    before = _game(
        floor=5,
        turn=1,
        player=SimpleNamespace(current_hp=69, max_hp=80, block=0, energy=1),
        hand=[wild_strike],
        monsters=[
            _monster(
                name="Cultist",
                monster_id="Cultist",
                hp=46,
                damage=0,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )
    actual = _game(
        floor=5,
        turn=1,
        player=SimpleNamespace(current_hp=69, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Cultist",
                monster_id="Cultist",
                hp=28,
                damage=0,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_wild_strike_plus_zero_live_damage_uses_upgrade_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    wild_strike_plus = _card(
        name="Wild Strike+",
        card_id="Wild Strike",
        card_type=CardType.ATTACK,
        cost=1,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=12,
        turn=1,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=2),
        hand=[wild_strike_plus],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=50, damage=12)],
    )
    actual = _game(
        floor=12,
        turn=1,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=33, damage=12)],
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


def test_paper_phrog_vulnerable_target_uses_bonus_multiplier(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(current_hp=49, max_hp=80, block=0, energy=1),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6)],
        relics=[_relic("Paper Phrog", counter=-1)],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=209,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=2,
        player=SimpleNamespace(current_hp=49, max_hp=80, block=0, energy=0),
        hand=[],
        relics=[_relic("Paper Phrog", counter=-1)],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=199,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_paper_phrog_vulnerable_target_applies_after_strength(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(
            current_hp=74,
            max_hp=80,
            block=0,
            energy=1,
            powers=[Power("Strength", "Strength", 5), Power("Strength Down", "Flex", 5)],
        ),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6)],
        relics=[_relic("Paper Phrog", counter=-1)],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=250,
                powers=[Power("Vulnerable", "Vulnerable", 3)],
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=1,
        player=SimpleNamespace(
            current_hp=74,
            max_hp=80,
            block=0,
            energy=0,
            powers=[Power("Strength", "Strength", 5), Power("Strength Down", "Flex", 5)],
        ),
        hand=[],
        relics=[_relic("Paper Phrog", counter=-1)],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=231,
                powers=[Power("Vulnerable", "Vulnerable", 3)],
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


def test_flight_halves_attack_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=18,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=3),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6)],
        monsters=[
            _monster(
                name="Byrd",
                monster_id="Byrd",
                hp=27,
                damage=6,
                intent=Intent.ATTACK,
                powers=[Power("Flight", "Flight", 3)],
            )
        ],
    )
    actual = _game(
        floor=18,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(
                name="Byrd",
                monster_id="Byrd",
                hp=24,
                damage=6,
                intent=Intent.ATTACK,
                powers=[Power("Flight", "Flight", 2)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_flight_halves_odd_attack_damage_with_flooring(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    headbutt = _card(name="Headbutt", card_id="Headbutt", damage=9)
    before = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=3),
        hand=[headbutt],
        monsters=[
            _monster(
                name="Byrd",
                monster_id="Byrd",
                hp=21,
                damage=13,
                intent=Intent.ATTACK,
                powers=[Power("Strength", "Strength", 1), Power("Flight", "Flight", 3)],
            )
        ],
    )
    actual = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(
                name="Byrd",
                monster_id="Byrd",
                hp=17,
                damage=13,
                intent=Intent.ATTACK,
                powers=[Power("Strength", "Strength", 1), Power("Flight", "Flight", 2)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_flight_zero_after_attack_sets_stun_intent(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    heavy_blade = _card(name="Heavy Blade", card_id="Heavy Blade", damage=14)
    before = _game(
        floor=24,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=3),
        hand=[heavy_blade],
        monsters=[
            _monster(
                name="Byrd",
                monster_id="Byrd",
                hp=19,
                damage=0,
                intent=Intent.BUFF,
                powers=[Power("Flight", "Flight", 1)],
            )
        ],
    )
    actual = _game(
        floor=24,
        turn=1,
        player=SimpleNamespace(current_hp=72, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[
            _monster(
                name="Byrd",
                monster_id="Byrd",
                hp=12,
                damage=0,
                intent=Intent.STUN,
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


def test_double_tap_replays_attack_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bash_plus = _card(
        name="Bash+",
        card_id="Bash",
        card_type=CardType.ATTACK,
        cost=2,
        damage=12,
        upgrades=1,
    )
    before = _game(
        floor=21,
        turn=3,
        player=SimpleNamespace(
            current_hp=60,
            max_hp=80,
            block=18,
            energy=2,
            powers=[Power("Double Tap", "Double Tap", 1)],
        ),
        hand=[bash_plus],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=49, damage=10)],
    )
    actual = _game(
        floor=21,
        turn=3,
        player=SimpleNamespace(
            current_hp=60,
            max_hp=80,
            block=18,
            energy=0,
            powers=[Power("Double Tap", "Double Tap", 1)],
        ),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=25, damage=10)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_necronomicon_replays_first_two_cost_attack(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    bash = _card(
        name="Bash",
        card_id="Bash",
        card_type=CardType.ATTACK,
        cost=2,
        damage=8,
    )
    before = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=4),
        hand=[bash],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=50, damage=10)],
        relics=[_relic("Necronomicon")],
    )
    actual = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=34, damage=10)],
        relics=[_relic("Necronomicon")],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_necronomicon_ignores_prior_one_cost_attacks(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Necronomicon")]
    strike_before = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=4),
        hand=[_card(name="Strike", card_id="Strike_R", damage=6, cost=1)],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=80, damage=10)],
        relics=relics,
    )
    strike_actual = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=74, damage=10)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), strike_before) is True
    assert observe_next_state(strike_actual) is False

    bash_before = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=3),
        hand=[_card(name="Bash", card_id="Bash", damage=8, cost=2)],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=74, damage=10)],
        relics=relics,
    )
    bash_actual = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=1),
        hand=[],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=58, damage=10)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), bash_before) is True
    assert observe_next_state(bash_actual) is False
    assert not trace_path.exists()


def test_necronomicon_replays_only_once_per_turn(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Necronomicon")]
    bash_before = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=4),
        hand=[_card(name="Bash", card_id="Bash", damage=8, cost=2)],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=80, damage=10)],
        relics=relics,
    )
    bash_actual = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=2),
        hand=[],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=64, damage=10)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), bash_before) is True
    assert observe_next_state(bash_actual) is False

    clothesline_before = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=2),
        hand=[_card(name="Clothesline", card_id="Clothesline", damage=12, cost=2)],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=64, damage=10)],
        relics=relics,
    )
    clothesline_actual = _game(
        floor=23,
        turn=1,
        player=SimpleNamespace(current_hp=63, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Mugger", monster_id="Mugger", hp=52, damage=10)],
        relics=relics,
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), clothesline_before) is True
    assert observe_next_state(clothesline_actual) is False
    assert not trace_path.exists()


def test_double_tap_replays_attack_block_effect(monkeypatch, tmp_path):
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
        floor=18,
        turn=1,
        player=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Double Tap", "Double Tap", 1)],
        ),
        hand=[iron_wave],
        monsters=[_monster(name="Spheric Guardian", monster_id="SphericGuardian", hp=20, block=40, damage=0)],
    )
    actual = _game(
        floor=18,
        turn=1,
        player=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            block=10,
            energy=2,
            powers=[Power("Double Tap", "Double Tap", 1)],
        ),
        hand=[],
        monsters=[_monster(name="Spheric Guardian", monster_id="SphericGuardian", hp=20, block=30, damage=0)],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_double_tap_replays_attack_self_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    hemokinesis_plus = _card(
        name="Hemokinesis+",
        card_id="Hemokinesis",
        card_type=CardType.ATTACK,
        cost=1,
        damage=20,
        upgrades=1,
    )
    before = _game(
        floor=24,
        turn=2,
        player=SimpleNamespace(
            current_hp=74,
            max_hp=80,
            block=10,
            energy=1,
            powers=[Power("Double Tap", "Double Tap", 1)],
        ),
        hand=[hemokinesis_plus],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=64, damage=0)],
    )
    actual = _game(
        floor=24,
        turn=2,
        player=SimpleNamespace(
            current_hp=70,
            max_hp=80,
            block=10,
            energy=0,
            powers=[Power("Double Tap", "Double Tap", 1)],
        ),
        hand=[],
        monsters=[_monster(name="Chosen", monster_id="Chosen", hp=24, damage=0)],
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


def test_whirlwind_target_vulnerable_is_applied_per_energy_hit(monkeypatch, tmp_path):
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
        floor=33,
        turn=2,
        player=SimpleNamespace(
            current_hp=39,
            max_hp=80,
            block=0,
            energy=2,
            powers=[Power("Strength", "Strength", 2)],
        ),
        hand=[whirlwind],
        monsters=[
            _monster(
                name="Champ",
                monster_id="Champ",
                hp=390,
                damage=0,
                intent=Intent.NONE,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )
    actual = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(
            current_hp=39,
            max_hp=80,
            block=0,
            energy=0,
            powers=[Power("Strength", "Strength", 2)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Champ",
                monster_id="Champ",
                hp=370,
                damage=0,
                intent=Intent.NONE,
                powers=[Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_whirlwind_triggers_malleable_for_each_energy_hit(monkeypatch, tmp_path):
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
        floor=29,
        turn=1,
        player=SimpleNamespace(
            current_hp=46,
            max_hp=80,
            block=0,
            energy=2,
            powers=[Power("Strength", "Strength", 1)],
        ),
        hand=[whirlwind],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=79,
                damage=0,
                intent=Intent.STRONG_DEBUFF,
                powers=[Power("Malleable", "Malleable", 3)],
            )
        ],
    )
    actual = _game(
        floor=29,
        turn=1,
        player=SimpleNamespace(
            current_hp=46,
            max_hp=80,
            block=0,
            energy=0,
            powers=[Power("Strength", "Strength", 1)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Snake Plant",
                monster_id="SnakePlant",
                hp=67,
                block=7,
                damage=0,
                intent=Intent.STRONG_DEBUFF,
                powers=[Power("Malleable", "Malleable", 5)],
            )
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


def test_end_turn_next_monster_intent_change_does_not_create_false_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=16,
        turn=12,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=9, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=151,
                damage=5,
                hits=4,
                intent=Intent.ATTACK,
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=13,
        player=SimpleNamespace(current_hp=24, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=151,
                damage=0,
                intent=Intent.DEFEND,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_next_monster_block_gain_does_not_create_false_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=2,
        turn=1,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Jaw Worm",
                monster_id="JawWorm",
                hp=23,
                damage=0,
                intent=Intent.DEFEND,
            )
        ],
    )
    actual = _game(
        floor=2,
        turn=2,
        player=SimpleNamespace(current_hp=70, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Jaw Worm",
                monster_id="JawWorm",
                hp=23,
                block=6,
                damage=7,
                intent=Intent.ATTACK,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_nilrys_codex_end_turn_screen_boundary_does_not_create_false_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Burning Blood"), _relic("Nilry's Codex")]
    before = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=10, energy=5),
        hand=[],
        relics=relics,
        monsters=[
            _monster(name="Bronze Automaton", monster_id="BronzeAutomaton", hp=300, damage=4),
            _monster(name="Bronze Orb", monster_id="BronzeOrb", hp=55, damage=0, index=1),
        ],
    )
    actual = _game(
        floor=33,
        turn=2,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=10, energy=5),
        hand=[],
        relics=relics,
        monsters=[
            _monster(name="Bronze Automaton", monster_id="BronzeAutomaton", hp=300, damage=4),
            _monster(name="Bronze Orb", monster_id="BronzeOrb", hp=55, damage=8, index=1),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_nilrys_codex_card_reward_boundary_does_not_create_false_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Burning Blood"), _relic("Nilry's Codex")]
    before = _game(
        floor=33,
        turn=4,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=13, energy=0),
        hand=[],
        relics=relics,
        monsters=[
            _monster(name="Bronze Automaton", monster_id="BronzeAutomaton", hp=300, damage=0),
            _monster(name="Bronze Orb", monster_id="BronzeOrb", hp=55, damage=8, index=1),
        ],
    )
    actual = _game(
        floor=33,
        turn=4,
        player=SimpleNamespace(current_hp=76, max_hp=80, block=0, energy=4),
        hand=[],
        relics=relics,
        monsters=[
            _monster(name="Bronze Automaton", monster_id="BronzeAutomaton", hp=300, damage=8),
            _monster(
                name="Bronze Orb",
                monster_id="BronzeOrb",
                hp=55,
                block=9,
                damage=0,
                intent=Intent.DEFEND_BUFF,
                index=1,
            ),
        ],
    )

    assert record_expected_action(
        CardRewardAction(_card(name="Sentinel", card_id="Sentinel")),
        before,
    ) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_nilrys_codex_cancel_boundary_does_not_create_false_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Burning Blood"), _relic("Nilry's Codex")]
    before = _game(
        floor=33,
        turn=7,
        player=SimpleNamespace(current_hp=55, max_hp=80, block=9, energy=0),
        hand=[],
        relics=relics,
        monsters=[
            _monster(name="Bronze Automaton", monster_id="BronzeAutomaton", hp=220, damage=0),
            _monster(name="Bronze Orb", monster_id="BronzeOrb", hp=40, damage=21, index=1),
        ],
    )
    actual = _game(
        floor=33,
        turn=7,
        player=SimpleNamespace(current_hp=16, max_hp=80, block=0, energy=4),
        hand=[],
        relics=relics,
        monsters=[
            _monster(name="Bronze Automaton", monster_id="BronzeAutomaton", hp=220, damage=0),
            _monster(name="Bronze Orb", monster_id="BronzeOrb", hp=40, damage=0, intent=Intent.STUN, index=1),
        ],
    )

    assert record_expected_action(CancelAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_combat_finished_after_expected_kill_does_not_create_false_diff(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    strike = _card(name="Strike", card_id="Strike_R", damage=6)
    before = _game(
        floor=7,
        turn=3,
        player=SimpleNamespace(current_hp=74, max_hp=80, block=0, energy=1),
        hand=[strike],
        relics=[_relic("Burning Blood")],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=6, damage=9)],
    )
    actual = _game(
        floor=7,
        turn=0,
        in_combat=False,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=0),
        hand=[],
        relics=[_relic("Burning Blood")],
        monsters=[],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_unexpected_combat_exit_still_reports_when_expected_monster_survives(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    strike = _card(name="Strike", card_id="Strike_R", damage=6)
    before = _game(
        floor=7,
        turn=3,
        player=SimpleNamespace(current_hp=74, max_hp=80, block=0, energy=1),
        hand=[strike],
        relics=[_relic("Burning Blood")],
        monsters=[_monster(name="Cultist", monster_id="Cultist", hp=12, damage=9)],
    )
    actual = _game(
        floor=7,
        turn=0,
        in_combat=False,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=0),
        hand=[],
        relics=[_relic("Burning Blood")],
        monsters=[],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is True
    records = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["reason"] == "monster_state_mismatch"
    assert records[0]["expected"]["monsters"][0]["hp"] == 6


def test_darkling_attack_death_enters_half_dead_without_false_divergence(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    strike = _card(name="Strike", card_id="Strike_R", damage=6, cost=1)
    before = _game(
        floor=35,
        turn=2,
        player=SimpleNamespace(current_hp=85, max_hp=85, block=16, energy=1),
        hand=[strike],
        monsters=[
            _monster(
                name="Darkling",
                monster_id="Darkling",
                hp=6,
                max_hp=50,
                damage=8,
                intent=Intent.ATTACK,
            ),
            _monster(
                name="Darkling",
                monster_id="Darkling",
                hp=37,
                max_hp=48,
                block=12,
                damage=9,
                intent=Intent.ATTACK,
                index=1,
            ),
        ],
    )
    killed_darkling = _monster(
        name="Darkling",
        monster_id="Darkling",
        hp=0,
        max_hp=50,
        damage=-1,
        intent=Intent.UNKNOWN,
    )
    killed_darkling.is_gone = True
    killed_darkling.half_dead = True
    actual = _game(
        floor=35,
        turn=2,
        player=SimpleNamespace(current_hp=85, max_hp=85, block=16, energy=1),
        hand=[],
        monsters=[
            killed_darkling,
            _monster(
                name="Darkling",
                monster_id="Darkling",
                hp=37,
                max_hp=48,
                block=12,
                damage=9,
                intent=Intent.ATTACK,
                index=1,
            ),
        ],
    )

    assert record_expected_action(PlayCardAction(card_index=0, target_index=0), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_darkling_buff_turn_revives_half_dead_monster_without_false_divergence(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    reviving_darkling = _monster(
        name="Darkling",
        monster_id="Darkling",
        hp=0,
        max_hp=50,
        damage=-1,
        intent=Intent.BUFF,
    )
    reviving_darkling.is_gone = True
    reviving_darkling.half_dead = True
    before = _game(
        floor=35,
        turn=4,
        player=SimpleNamespace(current_hp=85, max_hp=85, block=16, energy=0),
        hand=[],
        monsters=[
            reviving_darkling,
            _monster(
                name="Darkling",
                monster_id="Darkling",
                hp=15,
                max_hp=48,
                damage=-1,
                intent=Intent.DEFEND,
                index=1,
            ),
        ],
    )
    actual = _game(
        floor=35,
        turn=5,
        player=SimpleNamespace(current_hp=85, max_hp=85, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Darkling",
                monster_id="Darkling",
                hp=25,
                max_hp=50,
                damage=8,
                hits=2,
                intent=Intent.ATTACK,
            ),
            _monster(
                name="Darkling",
                monster_id="Darkling",
                hp=15,
                max_hp=48,
                block=12,
                damage=9,
                intent=Intent.ATTACK,
                index=1,
            ),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_resets_monster_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=4,
        turn=1,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Jaw Worm",
                monster_id="JawWorm",
                hp=22,
                block=5,
                damage=0,
                intent=Intent.NONE,
            )
        ],
    )
    actual = _game(
        floor=4,
        turn=2,
        player=SimpleNamespace(current_hp=65, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Jaw Worm",
                monster_id="JawWorm",
                hp=22,
                block=0,
                damage=0,
                intent=Intent.NONE,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_burn_damage_uses_remaining_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    burn = _card(
        name="Burn",
        card_id="Burn",
        card_type=CardType.STATUS,
        cost=0,
        damage=0,
    )
    before = _game(
        floor=16,
        turn=9,
        player=SimpleNamespace(current_hp=29, max_hp=80, block=11, energy=0),
        hand=[burn],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=125,
                damage=4,
                hits=6,
                intent=Intent.ATTACK_DEBUFF,
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=10,
        player=SimpleNamespace(current_hp=14, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=125,
                damage=4,
                hits=6,
                intent=Intent.ATTACK_DEBUFF,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_burn_plus_damage_uses_remaining_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    burn_plus = _card(
        name="Burn+",
        card_id="Burn",
        card_type=CardType.STATUS,
        cost=0,
        damage=0,
        upgrades=1,
    )
    before = _game(
        floor=16,
        turn=10,
        player=SimpleNamespace(current_hp=14, max_hp=80, block=3, energy=0),
        hand=[burn_plus, burn_plus],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=107,
                damage=0,
                intent=Intent.NONE,
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=11,
        player=SimpleNamespace(current_hp=9, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=107,
                damage=0,
                intent=Intent.NONE,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_brutality_loses_one_hp_after_monster_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=6,
        turn=4,
        player=SimpleNamespace(
            current_hp=63,
            max_hp=80,
            block=0,
            energy=0,
            powers=[Power("Brutality", "Brutality", 1)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Gremlin Nob",
                monster_id="GremlinNob",
                hp=22,
                damage=21,
                intent=Intent.ATTACK,
            )
        ],
    )
    actual = _game(
        floor=6,
        turn=5,
        player=SimpleNamespace(
            current_hp=41,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Brutality", "Brutality", 1)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Gremlin Nob",
                monster_id="GremlinNob",
                hp=22,
                damage=21,
                intent=Intent.ATTACK,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_regeneration_heals_player(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=22,
        turn=3,
        player=SimpleNamespace(
            current_hp=50,
            max_hp=80,
            block=5,
            energy=0,
            powers=[Power("Regeneration", "Regen", 4)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Snecko",
                monster_id="Snecko",
                hp=74,
                damage=12,
                intent=Intent.ATTACK,
            )
        ],
    )
    actual = _game(
        floor=22,
        turn=4,
        player=SimpleNamespace(
            current_hp=47,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Regeneration", "Regen", 3)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Snecko",
                monster_id="Snecko",
                hp=74,
                damage=0,
                intent=Intent.NONE,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_metallicize_block_reduces_incoming_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            block=0,
            energy=0,
            powers=[
                Power("Metallicize", "Metallicize", 6),
                Power("Dexterity", "Dexterity", 2),
            ],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Spike Slime (S)",
                monster_id="SpikeSlime_S",
                hp=13,
                damage=5,
                intent=Intent.ATTACK,
            ),
            _monster(
                name="Acid Slime (S)",
                monster_id="AcidSlime_S",
                hp=8,
                damage=3,
                intent=Intent.ATTACK,
                index=1,
            ),
            _monster(
                name="Spike Slime (S)",
                monster_id="SpikeSlime_S",
                hp=13,
                damage=5,
                intent=Intent.ATTACK,
                index=2,
            ),
            _monster(
                name="Spike Slime (S)",
                monster_id="SpikeSlime_S",
                hp=2,
                damage=3,
                intent=Intent.ATTACK,
                index=3,
            ),
        ],
    )
    actual = _game(
        floor=11,
        turn=2,
        player=SimpleNamespace(
            current_hp=70,
            max_hp=80,
            block=0,
            energy=3,
            powers=[
                Power("Metallicize", "Metallicize", 6),
                Power("Dexterity", "Dexterity", 2),
            ],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Spike Slime (S)",
                monster_id="SpikeSlime_S",
                hp=13,
                damage=5,
                intent=Intent.ATTACK,
            ),
            _monster(
                name="Acid Slime (S)",
                monster_id="AcidSlime_S",
                hp=8,
                damage=3,
                intent=Intent.ATTACK,
                index=1,
            ),
            _monster(
                name="Spike Slime (S)",
                monster_id="SpikeSlime_S",
                hp=13,
                damage=5,
                intent=Intent.ATTACK,
                index=2,
            ),
            _monster(
                name="Spike Slime (S)",
                monster_id="SpikeSlime_S",
                hp=2,
                damage=3,
                intent=Intent.ATTACK,
                index=3,
            ),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_plated_armor_block_reduces_incoming_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=18,
        turn=3,
        player=SimpleNamespace(
            current_hp=77,
            max_hp=80,
            block=0,
            energy=0,
            powers=[Power("Plated Armor", "Plated Armor", 4)],
        ),
        hand=[],
        monsters=[
            _monster(name="Looter", monster_id="Looter", hp=22, damage=10),
            _monster(name="Mugger", monster_id="Mugger", hp=36, damage=10, index=1),
        ],
    )
    actual = _game(
        floor=18,
        turn=4,
        player=SimpleNamespace(
            current_hp=61,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Plated Armor", "Plated Armor", 2)],
        ),
        hand=[],
        monsters=[
            _monster(name="Looter", monster_id="Looter", hp=22, damage=10),
            _monster(name="Mugger", monster_id="Mugger", hp=36, damage=10, index=1),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_shelled_parasite_attack_buff_heals_self(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=18,
        turn=4,
        player=SimpleNamespace(current_hp=68, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Shelled Parasite",
                monster_id="Shelled Parasite",
                hp=33,
                max_hp=68,
                block=0,
                damage=10,
                intent=Intent.ATTACK_BUFF,
                powers=[Power("Plated Armor", "Plated Armor", 11)],
            )
        ],
    )
    actual = _game(
        floor=18,
        turn=5,
        player=SimpleNamespace(current_hp=58, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Shelled Parasite",
                monster_id="Shelled Parasite",
                hp=43,
                max_hp=68,
                block=11,
                damage=18,
                intent=Intent.ATTACK_DEBUFF,
                powers=[Power("Plated Armor", "Plated Armor", 11)],
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_shelled_parasite_attack_buff_heals_unblocked_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=18,
        turn=6,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=3, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Shelled Parasite",
                monster_id="Shelled Parasite",
                hp=31,
                max_hp=68,
                block=0,
                damage=10,
                intent=Intent.ATTACK_BUFF,
                powers=[Power("Plated Armor", "Plated Armor", 7)],
            )
        ],
    )
    actual = _game(
        floor=18,
        turn=7,
        player=SimpleNamespace(current_hp=28, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Shelled Parasite",
                monster_id="Shelled Parasite",
                hp=38,
                max_hp=68,
                block=7,
                damage=6,
                hits=2,
                intent=Intent.ATTACK,
                powers=[Power("Plated Armor", "Plated Armor", 7)],
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_orichalcum_block_reduces_incoming_damage(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=10,
        turn=2,
        player=SimpleNamespace(current_hp=64, max_hp=85, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Red Slaver", monster_id="SlaverRed", hp=11, damage=13)],
        relics=[_relic("Burning Blood"), _relic("Orichalcum"), _relic("Pear")],
    )
    actual = _game(
        floor=10,
        turn=2,
        player=SimpleNamespace(current_hp=57, max_hp=85, block=0, energy=3),
        hand=[],
        monsters=[_monster(name="Red Slaver", monster_id="SlaverRed", hp=11, damage=13)],
        relics=[_relic("Burning Blood"), _relic("Orichalcum"), _relic("Pear")],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_horn_cleat_grants_block_after_monster_attacks(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=11,
        turn=1,
        player=SimpleNamespace(current_hp=80, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Blue Slaver", monster_id="SlaverBlue", hp=15, damage=12)],
        relics=[_relic("Burning Blood"), _relic("Horn Cleat", relic_id="HornCleat", counter=1)],
    )
    actual = _game(
        floor=11,
        turn=2,
        player=SimpleNamespace(current_hp=68, max_hp=80, block=14, energy=3),
        hand=[],
        monsters=[_monster(name="Blue Slaver", monster_id="SlaverBlue", hp=15, damage=12)],
        relics=[_relic("Burning Blood"), _relic("Horn Cleat", relic_id="HornCleat", counter=-1)],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_captains_wheel_grants_block_after_monster_attacks(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=6,
        turn=3,
        player=SimpleNamespace(current_hp=40, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[_monster(name="Spike Slime (S)", monster_id="SpikeSlime_S", hp=11, damage=5)],
        relics=[_relic("Burning Blood"), _relic("Captain's Wheel", relic_id="CaptainsWheel", counter=2)],
    )
    actual = _game(
        floor=6,
        turn=4,
        player=SimpleNamespace(current_hp=35, max_hp=80, block=18, energy=3),
        hand=[],
        monsters=[_monster(name="Spike Slime (S)", monster_id="SpikeSlime_S", hp=11, damage=5)],
        relics=[_relic("Burning Blood"), _relic("Captain's Wheel", relic_id="CaptainsWheel", counter=-1)],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_slime_split_boundary_ignores_monster_lifecycle_diffs(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=16,
        turn=6,
        player=SimpleNamespace(current_hp=43, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Slime Boss",
                monster_id="SlimeBoss",
                hp=47,
                max_hp=140,
                damage=0,
                intent=Intent.UNKNOWN,
                powers=[Power("Split", "Split", -1), Power("Vulnerable", "Vulnerable", 2)],
            )
        ],
    )
    split_boss = _monster(
        name="Slime Boss",
        monster_id="SlimeBoss",
        hp=0,
        max_hp=140,
        damage=0,
        intent=Intent.UNKNOWN,
        index=1,
    )
    split_boss.is_gone = True
    actual = _game(
        floor=16,
        turn=7,
        player=SimpleNamespace(current_hp=43, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Spike Slime (L)",
                monster_id="SpikeSlime_L",
                hp=35,
                max_hp=53,
                damage=16,
                intent=Intent.ATTACK_DEBUFF,
                powers=[Power("Split", "Split", -1)],
            ),
            split_boss,
            _monster(
                name="Acid Slime (L)",
                monster_id="AcidSlime_L",
                hp=43,
                max_hp=53,
                damage=16,
                intent=Intent.UNKNOWN,
                index=2,
                powers=[Power("Split", "Split", -1)],
            ),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_self_forming_clay_block_tracks_each_hp_loss(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Burning Blood"), _relic("Self Forming Clay")]
    before = _game(
        floor=11,
        turn=3,
        player=SimpleNamespace(current_hp=40, max_hp=80, block=3, energy=0),
        hand=[],
        relics=relics,
        monsters=[
            _monster(name="Spike Slime (S)", monster_id="SpikeSlime_S", hp=11, damage=5),
            _monster(name="Acid Slime (S)", monster_id="AcidSlime_S", hp=12, damage=3, index=1),
            _monster(name="Spike Slime (S)", monster_id="SpikeSlime_S", hp=7, damage=5, index=2),
        ],
    )
    actual = _game(
        floor=11,
        turn=4,
        player=SimpleNamespace(current_hp=30, max_hp=80, block=9, energy=3),
        hand=[],
        relics=relics,
        monsters=[
            _monster(name="Spike Slime (S)", monster_id="SpikeSlime_S", hp=11, damage=5),
            _monster(name="Acid Slime (S)", monster_id="AcidSlime_S", hp=12, damage=3, index=1),
            _monster(name="Spike Slime (S)", monster_id="SpikeSlime_S", hp=7, damage=5, index=2),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_next_turn_block_stacks_with_self_forming_clay(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Burning Blood"), _relic("Self-Forming Clay", relic_id="Self Forming Clay")]
    before = _game(
        floor=16,
        turn=14,
        player=SimpleNamespace(
            current_hp=40,
            max_hp=80,
            block=8,
            energy=0,
            powers=[
                Power("Evolve", "Evolve", 2),
                Power("Vulnerable", "Vulnerable", 1),
                Power("Next Turn Block", "Self-Forming Clay", 3),
                Power("Weakened", "Weakened", 1),
            ],
        ),
        hand=[],
        relics=relics,
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=134, damage=13)],
    )
    actual = _game(
        floor=16,
        turn=15,
        player=SimpleNamespace(
            current_hp=35,
            max_hp=80,
            block=6,
            energy=3,
            powers=[Power("Evolve", "Evolve", 2)],
        ),
        hand=[],
        relics=relics,
        monsters=[_monster(name="The Guardian", monster_id="TheGuardian", hp=134, damage=13)],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_self_forming_clay_does_not_grant_block_after_death(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    relics = [_relic("Burning Blood"), _relic("Self-Forming Clay", relic_id="Self Forming Clay")]
    before = _game(
        floor=16,
        turn=23,
        player=SimpleNamespace(
            current_hp=10,
            max_hp=80,
            block=10,
            energy=0,
            powers=[Power("Evolve", "Evolve", 2)],
        ),
        hand=[],
        relics=relics,
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=50,
                damage=5,
                hits=4,
                powers=[Power("Mode Shift", "Mode Shift", 50)],
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=23,
        player=SimpleNamespace(
            current_hp=0,
            max_hp=80,
            block=0,
            energy=0,
            powers=[
                Power("Evolve", "Evolve", 2),
                Power("Next Turn Block", "Self-Forming Clay", 3),
            ],
        ),
        hand=[],
        relics=relics,
        monsters=[
            _monster(
                name="The Guardian",
                monster_id="TheGuardian",
                hp=50,
                damage=-1,
                hits=1,
                powers=[Power("Mode Shift", "Mode Shift", 50)],
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_barricade_retains_remaining_block_after_attacks(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=28,
        turn=7,
        player=SimpleNamespace(
            current_hp=73,
            max_hp=80,
            block=18,
            energy=0,
            powers=[Power("Barricade", "Barricade", -1)],
        ),
        hand=[],
        monsters=[_monster(name="Snecko", monster_id="Snecko", hp=3, damage=16)],
    )
    actual = _game(
        floor=28,
        turn=8,
        player=SimpleNamespace(
            current_hp=73,
            max_hp=80,
            block=2,
            energy=3,
            powers=[Power("Barricade", "Barricade", -1)],
        ),
        hand=[],
        monsters=[_monster(name="Snecko", monster_id="Snecko", hp=3, damage=16)],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_combust_loses_hp_and_damages_all_monsters(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=4,
        turn=3,
        player=SimpleNamespace(
            current_hp=79,
            max_hp=80,
            block=5,
            energy=0,
            powers=[Power("Combust", "Combust", 5)],
        ),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=17, damage=6)],
    )
    actual = _game(
        floor=4,
        turn=4,
        player=SimpleNamespace(
            current_hp=77,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Combust", "Combust", 5)],
        ),
        hand=[],
        monsters=[_monster(name="Jaw Worm", monster_id="JawWorm", hp=12, damage=0)],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_mercury_hourglass_damages_monsters(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=33,
        turn=3,
        player=SimpleNamespace(current_hp=76, max_hp=85, block=5, energy=0),
        hand=[],
        relics=[_relic("Mercury Hourglass")],
        monsters=[
            _monster(
                name="The Champ",
                monster_id="Champ",
                hp=317,
                damage=0,
                intent=Intent.BUFF,
            )
        ],
    )
    actual = _game(
        floor=33,
        turn=4,
        player=SimpleNamespace(current_hp=76, max_hp=85, block=0, energy=3),
        hand=[],
        relics=[_relic("Mercury Hourglass")],
        monsters=[
            _monster(
                name="The Champ",
                monster_id="Champ",
                hp=314,
                damage=0,
                intent=Intent.BUFF,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_mercury_hourglass_hits_monster_plated_armor_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=18,
        turn=2,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=0),
        hand=[],
        relics=[_relic("Mercury Hourglass")],
        monsters=[
            _monster(
                name="Shelled Parasite",
                monster_id="Shelled Parasite",
                hp=48,
                max_hp=68,
                block=0,
                damage=0,
                intent=Intent.ATTACK,
                powers=[Power("Plated Armor", "Plated Armor", 12)],
            )
        ],
    )
    actual = _game(
        floor=18,
        turn=3,
        player=SimpleNamespace(current_hp=64, max_hp=80, block=0, energy=3),
        hand=[],
        relics=[_relic("Mercury Hourglass")],
        monsters=[
            _monster(
                name="Shelled Parasite",
                monster_id="Shelled Parasite",
                hp=48,
                max_hp=68,
                block=9,
                damage=10,
                intent=Intent.ATTACK_BUFF,
                powers=[Power("Plated Armor", "Plated Armor", 12)],
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_mercury_hourglass_hits_monster_barricade_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=28,
        turn=3,
        player=SimpleNamespace(current_hp=48, max_hp=80, block=0, energy=0),
        hand=[],
        relics=[_relic("Mercury Hourglass")],
        monsters=[
            _monster(name="Sentry", monster_id="Sentry", hp=0, block=0, damage=9),
            _monster(
                name="Spheric Guardian",
                monster_id="SphericGuardian",
                hp=20,
                max_hp=20,
                block=39,
                damage=0,
                intent=Intent.ATTACK_DEBUFF,
                index=1,
                powers=[Power("Barricade", "Barricade", -1), Power("Artifact", "Artifact", 3)],
            ),
        ],
    )
    before.monsters[0].is_gone = True
    actual = _game(
        floor=28,
        turn=4,
        player=SimpleNamespace(current_hp=48, max_hp=80, block=0, energy=3),
        hand=[],
        relics=[_relic("Mercury Hourglass")],
        monsters=[
            _monster(name="Sentry", monster_id="Sentry", hp=0, block=0, damage=9),
            _monster(
                name="Spheric Guardian",
                monster_id="SphericGuardian",
                hp=20,
                max_hp=20,
                block=36,
                damage=10,
                hits=2,
                intent=Intent.ATTACK,
                index=1,
                powers=[Power("Barricade", "Barricade", -1), Power("Artifact", "Artifact", 3)],
            ),
        ],
    )
    actual.monsters[0].is_gone = True

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_mystic_heal_hp_change_is_ignored_without_move_history(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=30,
        turn=3,
        player=SimpleNamespace(current_hp=60, max_hp=80, block=20, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Centurion",
                monster_id="Centurion",
                hp=52,
                max_hp=80,
                damage=0,
                intent=Intent.DEFEND,
            ),
            _monster(
                name="Mystic",
                monster_id="Healer",
                hp=43,
                max_hp=55,
                damage=0,
                intent=Intent.BUFF,
                index=1,
            ),
        ],
    )
    actual = _game(
        floor=30,
        turn=4,
        player=SimpleNamespace(current_hp=60, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Centurion",
                monster_id="Centurion",
                hp=68,
                max_hp=80,
                damage=0,
                intent=Intent.DEFEND,
            ),
            _monster(
                name="Mystic",
                monster_id="Healer",
                hp=55,
                max_hp=55,
                damage=0,
                intent=Intent.BUFF,
                index=1,
            ),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_mystic_strength_buff_does_not_report_hp_divergence(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=24,
        turn=8,
        player=SimpleNamespace(current_hp=44, max_hp=80, block=0, energy=0),
        hand=[],
        monsters=[
            _monster(
                name="Centurion",
                monster_id="Centurion",
                hp=51,
                max_hp=80,
                damage=14,
                intent=Intent.ATTACK,
                powers=[Power("Strength", "Strength", 2)],
            ),
            _monster(
                name="Mystic",
                monster_id="Healer",
                hp=32,
                max_hp=55,
                damage=0,
                intent=Intent.BUFF,
                index=1,
                powers=[Power("Strength", "Strength", 2)],
            ),
        ],
    )
    actual = _game(
        floor=24,
        turn=9,
        player=SimpleNamespace(current_hp=30, max_hp=80, block=0, energy=3),
        hand=[],
        monsters=[
            _monster(
                name="Centurion",
                monster_id="Centurion",
                hp=51,
                max_hp=80,
                damage=0,
                intent=Intent.DEFEND,
                powers=[Power("Strength", "Strength", 4)],
            ),
            _monster(
                name="Mystic",
                monster_id="Healer",
                hp=32,
                max_hp=55,
                damage=0,
                intent=Intent.BUFF,
                index=1,
                powers=[Power("Strength", "Strength", 4)],
            ),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_thorns_damages_each_attacking_hit(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=16,
        turn=3,
        player=SimpleNamespace(
            current_hp=80,
            max_hp=80,
            block=20,
            energy=0,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=209,
                damage=7,
                hits=6,
                intent=Intent.ATTACK,
            )
        ],
    )
    actual = _game(
        floor=16,
        turn=4,
        player=SimpleNamespace(
            current_hp=58,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Hexaghost",
                monster_id="Hexaghost",
                hp=191,
                damage=7,
                hits=6,
                intent=Intent.ATTACK,
            )
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_thorns_bypasses_monster_block(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=2,
        turn=1,
        player=SimpleNamespace(
            current_hp=78,
            max_hp=80,
            block=0,
            energy=0,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Fuzzy Louse",
                monster_id="FuzzyLouseDefensive",
                hp=5,
                block=1,
                damage=7,
                intent=Intent.ATTACK,
            ),
            _monster(
                name="Fuzzy Louse",
                monster_id="FuzzyLouseNormal",
                hp=4,
                block=5,
                damage=5,
                intent=Intent.ATTACK,
                index=1,
            ),
        ],
    )
    actual = _game(
        floor=2,
        turn=2,
        player=SimpleNamespace(
            current_hp=66,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Fuzzy Louse",
                monster_id="FuzzyLouseDefensive",
                hp=2,
                block=0,
                damage=7,
                intent=Intent.ATTACK,
            ),
            _monster(
                name="Fuzzy Louse",
                monster_id="FuzzyLouseNormal",
                hp=1,
                block=0,
                damage=-1,
                intent=Intent.BUFF,
                index=1,
            ),
        ],
    )

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_thorns_killed_monster_still_deals_current_attack_damage(
    monkeypatch,
    tmp_path,
):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=11,
        turn=2,
        player=SimpleNamespace(
            current_hp=53,
            max_hp=80,
            block=5,
            energy=0,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Acid Slime (M)",
                monster_id="AcidSlime_M",
                hp=20,
                max_hp=32,
                damage=10,
                intent=Intent.ATTACK,
            ),
            _monster(
                name="Looter",
                monster_id="Looter",
                hp=3,
                max_hp=46,
                damage=10,
                intent=Intent.ATTACK,
                index=1,
            ),
        ],
    )
    actual = _game(
        floor=11,
        turn=3,
        player=SimpleNamespace(
            current_hp=38,
            max_hp=80,
            block=0,
            energy=3,
            powers=[Power("Thorns", "Thorns", 3)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Acid Slime (M)",
                monster_id="AcidSlime_M",
                hp=17,
                max_hp=32,
                damage=-1,
                intent=Intent.DEBUFF,
            ),
            _monster(
                name="Looter",
                monster_id="Looter",
                hp=0,
                max_hp=46,
                damage=10,
                intent=Intent.ATTACK,
                index=1,
            ),
        ],
    )
    actual.monsters[1].is_gone = True

    assert record_expected_action(EndTurnAction(), before) is True
    assert observe_next_state(actual) is False
    assert not trace_path.exists()


def test_end_turn_flame_barrier_damages_attacker(monkeypatch, tmp_path):
    trace_path = tmp_path / "sim_divergence.jsonl"
    monkeypatch.setenv("STS_SIM_DIVERGENCE_TRACE_FILE", str(trace_path))
    reset_pending_divergence()

    before = _game(
        floor=14,
        turn=3,
        player=SimpleNamespace(
            current_hp=48,
            max_hp=80,
            block=10,
            energy=0,
            powers=[Power("Flame Barrier", "Flame Barrier", 6)],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Slaver",
                monster_id="SlaverBlue",
                hp=8,
                damage=7,
                hits=1,
                intent=Intent.ATTACK_DEBUFF,
            )
        ],
    )
    actual = _game(
        floor=14,
        turn=4,
        player=SimpleNamespace(
            current_hp=48,
            max_hp=80,
            block=0,
            energy=3,
            powers=[],
        ),
        hand=[],
        monsters=[
            _monster(
                name="Slaver",
                monster_id="SlaverBlue",
                hp=2,
                damage=7,
                hits=1,
                intent=Intent.ATTACK_DEBUFF,
            )
        ],
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
