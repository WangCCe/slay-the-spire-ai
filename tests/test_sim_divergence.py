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
