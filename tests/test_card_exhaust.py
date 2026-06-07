from types import SimpleNamespace

from spirecomm.ai.heuristics.card_exhaust import (
    card_exhausts_itself,
    description_exhausts_itself,
)


def test_card_exhausts_itself_uses_live_exhausts_flag():
    card = SimpleNamespace(name="Shockwave", exhausts=True)

    assert card_exhausts_itself(card)


def test_description_exhausts_itself_requires_terminal_exhaust_clause():
    assert description_exhausts_itself("Apply 3 Weak.\nExhaust.")
    assert not description_exhausts_itself("Exhaust 1 card. Draw 2 cards.")
