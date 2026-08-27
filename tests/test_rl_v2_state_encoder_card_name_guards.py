from types import SimpleNamespace
import math

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


def test_rl_v2_card_features_parse_string_turn_cost():
    encoder = StateEncoderV2(_mapper())
    card = _card("Cleave")
    card.cost = 3
    card.cost_for_turn = "2"
    card.is_playable = True

    features = encoder._encode_card_features(card)

    assert features[1] == 2 / 5


def test_rl_v2_card_features_treat_missing_is_playable_as_playable():
    encoder = StateEncoderV2(_mapper())
    card = _card("Cleave")
    card.cost = 1
    card.cost_for_turn = 1

    features = encoder._encode_card_features(card)

    assert features[2] == 1.0


def test_rl_v2_card_features_infer_upgrade_flag_from_suffix():
    encoder = StateEncoderV2(_mapper())
    card = _card("Cleave+1")
    card.cost = 1
    card.cost_for_turn = 1

    features = encoder._encode_card_features(card)

    assert features[0] == 1.0


def test_rl_v2_card_type_features_accept_strings():
    encoder = StateEncoderV2(_mapper())
    card = _card("Cleave")
    card.cost = 1
    card.cost_for_turn = 1
    card.type = "ATTACK"

    features = encoder._encode_card_features(card)

    assert features[3] == 1.0


def test_rl_v2_card_type_features_accept_card_type_attribute():
    encoder = StateEncoderV2(_mapper())
    card = _card("Cleave")
    card.cost = 1
    card.cost_for_turn = 1
    card.card_type = "CardType.SKILL"

    features = encoder._encode_card_features(card)

    assert features[4] == 1.0


def test_rl_v2_monster_features_accept_string_numeric_fields():
    encoder = StateEncoderV2(_mapper())
    monster = _monster(Intent.ATTACK)
    monster.max_hp = "20"
    monster.current_hp = "10"
    monster.block = "5"
    monster.move_adjusted_damage = "12"
    monster.move_hits = "2"

    features = encoder._encode_monster(monster)

    assert features[0] == 1.0
    assert features[1] == 0.5
    assert features[2] == 0.05
    assert abs(features[12] - math.tanh(12 / 50.0)) < 1e-9
    assert features[13] == 0.2


def test_rl_v2_player_features_accept_string_numeric_fields():
    encoder = StateEncoderV2(_mapper())
    game = SimpleNamespace(
        player=SimpleNamespace(
            current_hp="40",
            max_hp="80",
            energy="3",
            block="12",
            powers=[],
        ),
        floor="10",
        draw_pile=[],
        discard_pile=[],
        exhaust_pile=[],
        hand=[],
        character="IRONCLAD",
    )

    features = encoder._encode_player(game)

    assert features[0] == 0.5
    assert features[1] == 0.6
    assert features[2] == 0.12
    assert features[3] == 0.2


def test_rl_v2_player_class_features_accept_strings():
    encoder = StateEncoderV2(_mapper())

    features = encoder._encode_player_class("IRONCLAD")

    assert features[0] == 1.0


def test_rl_v2_relic_ids_accept_strings():
    mapper = IdMapper(
        card_ids={},
        potion_ids={},
        relic_ids={"Sozu": 11},
        card_tags={},
    )
    encoder = StateEncoderV2(mapper)
    game = SimpleNamespace(relics=["Sozu"])

    ids = encoder._encode_relic_ids(game)

    assert ids[0] == 11


def test_rl_v2_potion_ids_accept_strings():
    mapper = IdMapper(
        card_ids={},
        potion_ids={"Fire Potion": 13},
        relic_ids={},
        card_tags={},
    )
    encoder = StateEncoderV2(mapper)
    game = SimpleNamespace(potions=["Fire Potion"])

    ids = encoder._encode_potion_ids(game)

    assert ids[0] == 13


def test_rl_v2_potion_ids_use_get_real_potions_without_raw_potions():
    mapper = IdMapper(
        card_ids={},
        potion_ids={"Strength Potion": 17},
        relic_ids={},
        card_tags={},
    )
    encoder = StateEncoderV2(mapper)
    game = SimpleNamespace(
        get_real_potions=lambda: [SimpleNamespace(potion_id="Strength Potion")]
    )

    ids = encoder._encode_potion_ids(game)

    assert ids[0] == 17


def test_rl_v2_potion_ids_fall_back_from_internal_id_to_display_name():
    mapper = IdMapper(
        card_ids={},
        potion_ids={"Fairy in a Bottle": 20},
        relic_ids={},
        card_tags={},
    )
    encoder = StateEncoderV2(mapper)
    game = SimpleNamespace(
        potions=[SimpleNamespace(potion_id="FairyPotion", name="Fairy in a Bottle")]
    )

    ids = encoder._encode_potion_ids(game)

    assert ids[0] == 20


def test_rl_v2_relic_ids_fall_back_from_internal_id_to_display_name():
    mapper = IdMapper(
        card_ids={},
        potion_ids={},
        relic_ids={"Self-Forming Clay": 134},
        card_tags={},
    )
    encoder = StateEncoderV2(mapper)
    game = SimpleNamespace(
        relics=[SimpleNamespace(relic_id="Self Forming Clay", name="Self-Forming Clay")]
    )

    ids = encoder._encode_relic_ids(game)

    assert ids[0] == 134


def test_rl_v2_inventory_ids_preserve_known_preferred_identity():
    mapper = IdMapper(
        card_ids={},
        potion_ids={"InternalPotion": 7, "Display Potion": 8},
        relic_ids={"InternalRelic": 9, "Display Relic": 10},
        card_tags={},
    )
    encoder = StateEncoderV2(mapper)

    potion_ids = encoder._encode_potion_ids(
        SimpleNamespace(
            potions=[SimpleNamespace(potion_id="InternalPotion", name="Display Potion")]
        )
    )
    relic_ids = encoder._encode_relic_ids(
        SimpleNamespace(
            relics=[SimpleNamespace(relic_id="InternalRelic", name="Display Relic")]
        )
    )

    assert potion_ids[0] == 7
    assert relic_ids[0] == 9


def test_rl_v2_inventory_ids_keep_empty_and_unresolved_objects_zero():
    mapper = IdMapper(
        card_ids={},
        potion_ids={"Known Potion": 5},
        relic_ids={"Known Relic": 6},
        card_tags={},
    )
    encoder = StateEncoderV2(mapper)

    potion_ids = encoder._encode_potion_ids(
        SimpleNamespace(
            potions=[
                SimpleNamespace(potion_id="Potion Slot", name="Potion Slot"),
                SimpleNamespace(potion_id="UnknownPotion", name="Unknown Potion"),
            ]
        )
    )
    relic_ids = encoder._encode_relic_ids(
        SimpleNamespace(
            relics=[SimpleNamespace(relic_id="UnknownRelic", name="Unknown Relic")]
        )
    )

    assert potion_ids[:2] == [0, 0]
    assert relic_ids[0] == 0
    assert len(potion_ids) == StateEncoderV2.POTION_SLOTS
    assert len(relic_ids) == StateEncoderV2.RELIC_SLOTS
    assert mapper.potion_vocab_size == 6
    assert mapper.relic_vocab_size == 7


def test_rl_v2_card_features_treat_missing_cost_as_zero():
    encoder = StateEncoderV2(_mapper())
    card = _card("Cleave")
    card.cost = None
    card.cost_for_turn = None
    card.is_playable = True

    features = encoder._encode_card_features(card)

    assert features[1] == 0.0


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


def test_rl_v2_keyword_encoding_accepts_name_only_power():
    encoder = StateEncoderV2(_mapper())

    encoded = encoder._encode_keyword(
        [SimpleNamespace(name="Artifact", amount=4)],
        "Artifact",
    )

    assert encoded == 4 / 20
