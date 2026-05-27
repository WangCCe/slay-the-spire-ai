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


def _game(floor):
    return SimpleNamespace(
        floor=floor,
        in_combat=False,
        screen_type=ScreenType.MAP,
        deck=[],
        relics=[],
        gold=0,
        player=SimpleNamespace(current_hp=70, max_hp=80),
    )


def test_rl_step_reward_uses_observed_floor_delta_after_reset():
    calc = RewardCalculator()
    info = {}

    reward = calc.calculate_step_reward(_game(10), _game(9), debug_info=info)

    assert info["progress_reward"] == calc.FLOOR_REWARD_SCALE
    assert reward == calc.FLOOR_REWARD_SCALE
