from types import SimpleNamespace

from spirecomm.ai.heuristics.card_types import card_type_name, is_attack_card, is_card_type
from spirecomm.spire.card import Card, CardRarity, CardType


def test_card_type_name_accepts_card_objects_enums_and_strings():
    strike = Card("Strike_R", "Strike", CardType.ATTACK, CardRarity.BASIC)

    assert card_type_name(strike) == "ATTACK"
    assert card_type_name(CardType.SKILL) == "SKILL"
    assert card_type_name("CardType.POWER") == "POWER"
    assert card_type_name("status") == "STATUS"
    assert card_type_name(None) == ""


def test_card_type_matchers_accept_namespaced_strings():
    card = SimpleNamespace(type="CardType.ATTACK")

    assert is_card_type(card, "ATTACK") is True
    assert is_card_type(card, CardType.ATTACK) is True
    assert is_attack_card(card) is True
