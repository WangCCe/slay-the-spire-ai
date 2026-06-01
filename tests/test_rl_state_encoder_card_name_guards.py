from types import SimpleNamespace

from spirecomm.ai.rl.state_encoder import StateEncoder
from spirecomm.spire.card import CardType


def _card(card_id, upgrades=0):
    return SimpleNamespace(
        card_id=card_id,
        id=card_id,
        name=card_id,
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        upgrades=upgrades,
        has_target=True,
        exhausts=False,
        properties=[],
    )


def _game(deck):
    return SimpleNamespace(deck=deck, draw_pile=[], discard_pile=[], hand=[])


def test_rl_state_encoder_hand_card_hash_strips_counted_upgrade_suffix():
    encoder = StateEncoder()

    base_features = encoder._encode_single_card(_card("Cleave"))
    upgraded_features = encoder._encode_single_card(_card("Cleave+1", upgrades=1))

    assert upgraded_features[0] == base_features[0]


def test_rl_state_encoder_deck_composition_strips_counted_upgrade_suffix():
    encoder = StateEncoder()

    base_counts = encoder._encode_deck_composition(_game([_card("Cleave")]))
    upgraded_counts = encoder._encode_deck_composition(_game([_card("Cleave+1", upgrades=1)]))

    assert upgraded_counts == base_counts


def test_rl_state_encoder_traits_strip_counted_upgrade_suffix():
    encoder = StateEncoder()

    bash_features = encoder._encode_single_card(_card("Bash+1", upgrades=1))

    assert bash_features[-1] == 1.0


def test_rl_state_encoder_treats_none_upgrades_as_base_card():
    encoder = StateEncoder()

    features = encoder._encode_single_card(_card("Cleave", upgrades=None))

    assert features[8] == 0.0


def test_rl_state_encoder_intent_encoding_accepts_string_representations():
    encoder = StateEncoder()

    assert encoder._encode_intent("Intent.ATTACK_DEBUFF") == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Attack/Debuff") == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.DEFEND_BUFF") == [0.0, 1.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.BUFF") == [0.0, 0.0, 1.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.STRONG_DEBUFF") == [0.0, 0.0, 0.0, 1.0, 0.0]
    assert encoder._encode_intent("NOT_ATTACK") == [0.0, 0.0, 0.0, 0.0, 1.0]
