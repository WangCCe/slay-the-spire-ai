from types import SimpleNamespace

from spirecomm.ai.agent import TurnPlanSignature
from spirecomm.spire.character import Intent


def _card(card_id, name, uuid=None):
    return SimpleNamespace(card_id=card_id, name=name, uuid=uuid)


def _monster():
    return SimpleNamespace(
        current_hp=40,
        block=0,
        intent=Intent.ATTACK,
        is_gone=False,
        half_dead=False,
    )


def _game(hand):
    return SimpleNamespace(
        hand=hand,
        player=SimpleNamespace(energy=3),
        monsters=[_monster()],
    )


def test_turn_plan_signature_distinguishes_cards_when_uuid_is_missing():
    strike_signature = TurnPlanSignature(_game([_card("Strike_R", "Strike")]))
    defend_signature = TurnPlanSignature(_game([_card("Defend_R", "Defend")]))

    assert strike_signature.hand_cards != defend_signature.hand_cards
    assert strike_signature != defend_signature
