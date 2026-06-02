from types import SimpleNamespace

from spirecomm.ai.rl.reward import RewardCalculator
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.screen import ScreenType


def _card(card_id, upgrades=0):
    return SimpleNamespace(card_id=card_id, name=card_id, upgrades=upgrades)


def test_rl_card_priority_score_treats_counted_upgraded_cards_as_base_cards():
    calc = RewardCalculator()
    game = SimpleNamespace(character=PlayerClass.IRONCLAD)

    base_score = calc._priority_score(_card("Demon Form"), game)
    upgraded_score = calc._priority_score(_card("Demon Form+1", upgrades=1), game)

    assert upgraded_score == base_score


def _game(floor, gold=0):
    return SimpleNamespace(
        floor=floor,
        in_combat=False,
        screen_type=ScreenType.MAP,
        deck=[],
        relics=[],
        gold=gold,
        player=SimpleNamespace(current_hp=70, max_hp=80),
    )


def _combat_game(monsters, player_hp=70, turn=1, max_hp=80):
    return SimpleNamespace(
        floor=1,
        in_combat=True,
        screen_type=ScreenType.NONE,
        deck=[],
        relics=[],
        gold=0,
        turn=turn,
        monsters=monsters,
        player=SimpleNamespace(current_hp=player_hp, max_hp=max_hp, energy=3, block=0),
    )


def test_rl_step_reward_uses_observed_floor_delta_after_reset():
    calc = RewardCalculator()
    info = {}

    reward = calc.calculate_step_reward(_game(10), _game(9), debug_info=info)

    assert info["progress_reward"] == calc.FLOOR_REWARD_SCALE
    assert reward == calc.FLOOR_REWARD_SCALE


def test_rl_step_reward_accepts_numeric_string_floor_delta():
    calc = RewardCalculator()
    info = {}

    reward = calc.calculate_step_reward(_game("10"), _game("9"), debug_info=info)

    assert info["floor_advanced"] is True
    assert info["progress_reward"] == calc.FLOOR_REWARD_SCALE
    assert reward == calc.FLOOR_REWARD_SCALE


def test_rl_reward_power_amount_accepts_name_only_power():
    calc = RewardCalculator()
    entity = SimpleNamespace(powers=[SimpleNamespace(name="Vulnerable", amount=2)])

    assert calc._get_power_amount(entity, "Vulnerable") == 2


def test_rl_step_reward_accepts_numeric_string_gold_delta():
    calc = RewardCalculator()
    info = {}

    reward = calc.calculate_step_reward(
        _game(10, gold="42"),
        _game(10, gold="32"),
        debug_info=info,
    )

    expected = 10 * calc.GOLD_REWARD_SCALE
    assert info["gold_reward"] == expected
    assert info["acquisition_reward"] == expected
    assert reward == expected


def test_rl_step_reward_accepts_numeric_string_monster_hp_for_damage_delta():
    calc = RewardCalculator()
    info = {}
    last_game = _combat_game([
        SimpleNamespace(monster_index=0, current_hp="12", powers=[]),
    ])
    current_game = _combat_game([
        SimpleNamespace(monster_index=0, current_hp="7", powers=[]),
    ])

    reward = calc.calculate_step_reward(current_game, last_game, debug_info=info)

    assert info["damage_dealt"] == 5
    assert info["total_monster_hp_delta"] == 5
    assert reward == 5 * calc.DAMAGE_REWARD_SCALE


def test_rl_step_reward_accepts_numeric_string_turn_delta():
    calc = RewardCalculator()
    info = {}

    reward = calc.calculate_step_reward(
        _combat_game([], turn="10"),
        _combat_game([], turn="9"),
        debug_info=info,
    )

    assert info["turn_ended"] is True
    assert info["combat_reward"] == calc.TURN_END_PENALTY
    assert reward == calc.TURN_END_PENALTY


def test_rl_step_reward_accepts_numeric_string_player_max_hp_for_hp_loss_penalty():
    calc = RewardCalculator()
    info = {}

    reward = calc.calculate_step_reward(
        _combat_game([], player_hp="60", max_hp="80"),
        _combat_game([], player_hp="70", max_hp="80"),
        debug_info=info,
    )

    expected = -calc.HP_LOSS_PENALTY * (10 / 80)
    assert info["hp_lost"] == 10
    assert info["combat_reward"] == expected
    assert reward == expected


def test_rl_victory_detection_accepts_numeric_string_final_floor():
    calc = RewardCalculator()
    game = SimpleNamespace(
        screen_type="GAME_OVER",
        floor="55",
        player=SimpleNamespace(current_hp=0),
    )

    assert calc._is_victory(game) is True
