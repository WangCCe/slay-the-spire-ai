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


def test_rl_state_encoder_falls_back_to_base_cost_when_turn_cost_is_none():
    encoder = StateEncoder()
    card = _card("Cleave")
    card.cost = 2
    card.cost_for_turn = None

    features = encoder._encode_single_card(card)

    assert features[1] == 2 / 3


def test_rl_state_encoder_treats_missing_cost_as_zero():
    encoder = StateEncoder()
    card = _card("Discovery")
    card.cost = None
    card.cost_for_turn = None

    features = encoder._encode_single_card(card)

    assert features[1] == 0.0


def test_rl_state_encoder_card_type_features_accept_strings():
    encoder = StateEncoder()
    card = _card("Cleave")
    card.type = "ATTACK"

    features = encoder._encode_single_card(card)

    assert features[4] == 1.0


def test_rl_card_reward_features_infer_upgrade_flag_from_suffix():
    encoder = StateEncoder()

    features = encoder._encode_card_reward_card(_card("Cleave+1"))

    assert features[11] == 1.0


def test_rl_state_encoder_intent_encoding_accepts_string_representations():
    encoder = StateEncoder()

    assert encoder._encode_intent("Intent.ATTACK_DEBUFF") == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Attack/Debuff") == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.DEFEND_BUFF") == [0.0, 1.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.BUFF") == [0.0, 0.0, 1.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.STRONG_DEBUFF") == [0.0, 0.0, 0.0, 1.0, 0.0]
    assert encoder._encode_intent("NOT_ATTACK") == [0.0, 0.0, 0.0, 0.0, 1.0]
