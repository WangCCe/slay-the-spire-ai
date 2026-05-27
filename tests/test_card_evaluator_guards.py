from spirecomm.ai.heuristics import card as card_module
from spirecomm.ai.heuristics.card import SynergyCardEvaluator
from spirecomm.spire.card import Card, CardRarity, CardType


class _FakeCardDataLoader:
    def __init__(self, cards):
        self.cards = cards

    def get_card_data(self, card_name):
        return self.cards.get(card_name.lower())


def test_defensive_detection_uses_base_name_for_upgraded_cards(monkeypatch):
    monkeypatch.setattr(
        card_module,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "shrug it off": {
                    "name": "Shrug It Off",
                    "type": "SKILL",
                    "rarity": "COMMON",
                    "cost": "1",
                    "description": "Gain 8 Block. Draw 1 card.",
                },
            }
        ),
    )
    shrug_plus = Card(
        "Shrug It Off",
        "Shrug It Off+",
        CardType.SKILL,
        CardRarity.COMMON,
        upgrades=1,
        cost=1,
    )

    assert SynergyCardEvaluator(player_class="IRONCLAD")._is_defensive_card(shrug_plus) is True
