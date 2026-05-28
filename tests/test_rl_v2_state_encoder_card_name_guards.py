from types import SimpleNamespace

from spirecomm.ai.rl.v2.id_mapping import IdMapper
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2
from spirecomm.spire.character import Intent


def _card(card_id):
    return SimpleNamespace(card_id=card_id, name=card_id)


def _game(hand):
    return SimpleNamespace(hand=hand)


def _mapper():
    return IdMapper(
        card_ids={"Cleave": 7, "Strike_R": 8},
        potion_ids={},
        relic_ids={},
        card_tags={"Cleave": ["AOE"], "Strike_R": []},
    )


def _monster(intent):
    return SimpleNamespace(
        max_hp=20,
        current_hp=20,
        block=0,
        is_gone=False,
        intent=intent,
        move_adjusted_damage=0,
        move_hits=0,
        powers=[],
    )


def _intent_one_hot(encoder, intent):
    features = encoder._encode_monster(_monster(intent))
    return features[3 : 3 + len(encoder.INTENT_ORDER)]


def _expected_intent(encoder, intent):
    one_hot = [0.0] * len(encoder.INTENT_ORDER)
    one_hot[encoder.INTENT_ORDER.index(intent)] = 1.0
    return one_hot


def test_rl_v2_card_ids_strip_counted_upgrade_suffix():
    encoder = StateEncoderV2(_mapper())

    ids = encoder._encode_card_ids(_game([_card("Cleave+1")]))

    assert ids[0] == 7


def test_rl_v2_card_tags_strip_counted_upgrade_suffix():
    encoder = StateEncoderV2(_mapper())

    tags = encoder._encode_card_tags(_card("Cleave+1"))

    assert tags[StateEncoderV2.TAGS.index("AOE")] == 1.0


def test_rl_v2_monster_intent_encoding_accepts_string_representations():
    encoder = StateEncoderV2(_mapper())

    assert _intent_one_hot(encoder, "Intent.ATTACK_DEBUFF") == _expected_intent(
        encoder, Intent.ATTACK_DEBUFF
    )
    assert _intent_one_hot(encoder, "Attack/Debuff") == _expected_intent(
        encoder, Intent.ATTACK_DEBUFF
    )
    assert _intent_one_hot(encoder, "Intent.DEFEND_BUFF") == _expected_intent(
        encoder, Intent.DEFEND_BUFF
    )
    assert _intent_one_hot(encoder, "Intent.STRONG_DEBUFF") == _expected_intent(
        encoder, Intent.DEBUFF
    )
    assert _intent_one_hot(encoder, "NOT_ATTACK") == [0.0] * len(encoder.INTENT_ORDER)
