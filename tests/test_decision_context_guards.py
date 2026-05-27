from types import SimpleNamespace

import spirecomm.ai.decision.base as decision_base
from spirecomm.ai.decision.base import DecisionContext
from spirecomm.spire.card import Card, CardRarity, CardType


class _FakeCardDataLoader:
    def __init__(self, cards):
        self.cards = cards

    def get_card_data(self, card_name):
        return self.cards.get(card_name.lower())


def _context_for_deck(deck):
    context = DecisionContext.__new__(DecisionContext)
    context.game = SimpleNamespace(deck=deck)
    return context


def test_legacy_deck_archetype_uses_display_name_for_basic_card_ids(monkeypatch):
    monkeypatch.setattr(
        decision_base,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "strike": {
                    "description": "Deal 6 damage.",
                    "type": "ATTACK",
                    "cost": "1",
                },
            }
        ),
    )
    deck = [
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC, cost=1)
        for _ in range(4)
    ]

    assert _context_for_deck(deck)._analyze_deck_archetype() == "strength"


def test_legacy_synergies_use_display_name_for_basic_attack_ids(monkeypatch):
    monkeypatch.setattr(
        decision_base,
        "game_data_loader",
        _FakeCardDataLoader(
            {
                "uppercut": {
                    "description": "Deal 13 damage. Apply 1 Weak. Apply 1 Vulnerable.",
                    "type": "ATTACK",
                    "cost": "2",
                },
                "strike": {
                    "description": "Deal 6 damage.",
                    "type": "ATTACK",
                    "cost": "1",
                },
            }
        ),
    )
    deck = [
        Card("Uppercut", "Uppercut+", CardType.ATTACK, CardRarity.UNCOMMON, upgrades=1, cost=2),
        Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC, cost=1),
    ]

    synergies = _context_for_deck(deck)._calculate_synergies()

    assert synergies["vulnerable"] > 0
    assert synergies["weak"] > 0
