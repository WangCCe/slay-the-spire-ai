from types import SimpleNamespace

from spirecomm.ai.rl.reward import RewardCalculator
from spirecomm.spire.character import PlayerClass


def _card(card_id, upgrades=0):
    return SimpleNamespace(card_id=card_id, name=card_id, upgrades=upgrades)


def test_rl_card_priority_score_treats_counted_upgraded_cards_as_base_cards():
    calc = RewardCalculator()
    game = SimpleNamespace(character=PlayerClass.IRONCLAD)

    base_score = calc._priority_score(_card("Demon Form"), game)
    upgraded_score = calc._priority_score(_card("Demon Form+1", upgrades=1), game)

    assert upgraded_score == base_score
