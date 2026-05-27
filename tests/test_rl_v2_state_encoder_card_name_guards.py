from types import SimpleNamespace

from spirecomm.ai.rl.v2.id_mapping import IdMapper
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2


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


def test_rl_v2_card_ids_strip_counted_upgrade_suffix():
    encoder = StateEncoderV2(_mapper())

    ids = encoder._encode_card_ids(_game([_card("Cleave+1")]))

    assert ids[0] == 7


def test_rl_v2_card_tags_strip_counted_upgrade_suffix():
    encoder = StateEncoderV2(_mapper())

    tags = encoder._encode_card_tags(_card("Cleave+1"))

    assert tags[StateEncoderV2.TAGS.index("AOE")] == 1.0
