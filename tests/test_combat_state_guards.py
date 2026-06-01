from types import SimpleNamespace

from spirecomm.ai.heuristics.combat_state import (
    card_play_key,
    draw_pile_count,
    is_card_played,
    mark_card_played,
    monster_power_amount,
    player_has_power,
    player_debuff_stacks,
    player_power_amount,
    power_amount,
    power_identifier,
    power_name,
    power_signature,
    player_block_value,
)


def test_player_block_value_prefers_context_field():
    context = SimpleNamespace(
        player_block=12,
        game=SimpleNamespace(player=SimpleNamespace(block=3)),
    )

    assert player_block_value(context) == 12


def test_player_block_value_falls_back_to_game_player_block():
    context = SimpleNamespace(game=SimpleNamespace(player=SimpleNamespace(block="7")))

    assert player_block_value(context) == 7


def test_player_block_value_clamps_missing_invalid_or_negative_values():
    assert player_block_value(SimpleNamespace(player_block=-4)) == 0
    assert player_block_value(SimpleNamespace(player_block="not-a-number")) == 0
    assert player_block_value(SimpleNamespace()) == 0
    assert player_block_value(None) == 0


def test_draw_pile_count_prefers_game_draw_pile_length():
    context = SimpleNamespace(
        game=SimpleNamespace(draw_pile=[object(), object(), object()]),
        draw_pile_size=9,
    )

    assert draw_pile_count(context) == 3


def test_draw_pile_count_accepts_numeric_pile_and_size_fallback():
    assert draw_pile_count(SimpleNamespace(game=SimpleNamespace(draw_pile=4))) == 4
    assert draw_pile_count(SimpleNamespace(draw_pile_size="6")) == 6


def test_draw_pile_count_clamps_missing_invalid_or_negative_values():
    assert draw_pile_count(SimpleNamespace(draw_pile=-2)) == 0
    assert draw_pile_count(SimpleNamespace(draw_pile_size="not-a-number")) == 0
    assert draw_pile_count(SimpleNamespace()) == 0
    assert draw_pile_count(None) == 0


def test_card_play_key_prefers_uuid_and_keeps_uuidless_duplicates_distinct():
    first = SimpleNamespace(uuid="same-card")
    second = SimpleNamespace(uuid="same-card")
    uuidless_first = SimpleNamespace()
    uuidless_second = SimpleNamespace()

    assert card_play_key(first) == "same-card"
    assert card_play_key(second) == "same-card"
    assert card_play_key(uuidless_first) != card_play_key(uuidless_second)
    assert card_play_key(None) is None


def test_mark_card_played_records_uuid_and_object_identity():
    played_cards = set()
    card = SimpleNamespace(uuid="card-uuid")
    uuidless_card = SimpleNamespace()

    mark_card_played(played_cards, card)
    mark_card_played(played_cards, uuidless_card)
    before_none = set(played_cards)
    mark_card_played(played_cards, None)

    assert "card-uuid" in played_cards
    assert id(card) in played_cards
    assert id(uuidless_card) in played_cards
    assert played_cards == before_none


def test_is_card_played_checks_uuid_or_object_identity():
    card = SimpleNamespace(uuid="card-uuid")
    uuidless_card = SimpleNamespace()

    assert is_card_played({"card-uuid"}, card) is True
    assert is_card_played({id(card)}, card) is True
    assert is_card_played({id(uuidless_card)}, uuidless_card) is True
    assert is_card_played(set(), card) is False
    assert is_card_played({"card-uuid"}, None) is False


def test_power_name_reads_known_power_identifier_fields_in_order():
    assert power_name(SimpleNamespace(name="Name", power_name="PowerName", power_id="PowerId")) == "Name"
    assert power_name(SimpleNamespace(power_name="PowerName", power_id="PowerId")) == "PowerName"
    assert power_name(SimpleNamespace(power_id="PowerId")) == "PowerId"
    assert power_name(SimpleNamespace()) is None


def test_power_identifier_and_signature_prefer_protocol_id_for_state_keys():
    power = SimpleNamespace(
        name="Localized Strength",
        power_name="Strength Display",
        power_id="Strength",
        amount=2,
    )

    assert power_identifier(power) == "Strength"
    assert power_signature(power) == ("Strength", 2)
    assert power_signature(SimpleNamespace(power_name="Weak")) == ("Weak", None)
    assert power_signature(SimpleNamespace()) == (None, None)


def test_power_amount_reads_named_power_with_configurable_missing_amount():
    powers = [
        SimpleNamespace(power_name="Strength", amount=3),
        SimpleNamespace(power_id="Vulnerable"),
        SimpleNamespace(name="Display", power_id="Dexterity", amount=2),
    ]

    assert power_amount(powers, "Strength") == 3
    assert power_amount(powers, "Vulnerable", missing_amount=1) == 1
    assert power_amount(powers, "Vulnerable", missing_amount=0) == 0
    assert power_amount(powers, "Dexterity") == 2
    assert power_amount(powers, "Missing", missing_amount=1) == 0
    assert power_amount(None, "Strength", missing_amount=1) == 0


def test_player_power_amount_reads_player_powers_with_zero_default_amount():
    context = SimpleNamespace(
        game=SimpleNamespace(
            player=SimpleNamespace(
                powers=[
                    SimpleNamespace(power_name="Strength", amount=3),
                    SimpleNamespace(power_id="Dexterity"),
                ]
            )
        )
    )

    assert player_power_amount(context, "Strength") == 3
    assert player_power_amount(context, "Dexterity") == 0
    assert player_power_amount(context, "Missing") == 0


def test_player_debuff_stacks_reads_player_powers_with_one_default_amount():
    context = SimpleNamespace(
        game=SimpleNamespace(
            player=SimpleNamespace(
                powers=[
                    SimpleNamespace(name="Weak", amount=2),
                    SimpleNamespace(power_name="Frail"),
                ]
            )
        )
    )

    assert player_debuff_stacks(context, "Weak") == 2
    assert player_debuff_stacks(context, "Frail") == 1
    assert player_debuff_stacks(context, "Missing") == 0


def test_player_has_power_checks_presence_independent_of_amount():
    context = SimpleNamespace(
        game=SimpleNamespace(
            player=SimpleNamespace(
                powers=[
                    SimpleNamespace(power_name="Juggernaut", amount=0),
                    SimpleNamespace(power_id="Rupture"),
                ]
            )
        )
    )

    assert player_has_power(context, "Juggernaut") is True
    assert player_has_power(context, "Rupture") is True
    assert player_has_power(context, "Missing") is False
    assert player_has_power(SimpleNamespace(), "Rupture") is False
    assert player_has_power(None, "Rupture") is False


def test_monster_power_amount_prefers_direct_amount_then_power_amount():
    monster = SimpleNamespace(
        vulnerable="2",
        powers=[
            SimpleNamespace(power_name="Vulnerable", amount=4),
            SimpleNamespace(power_id="Poison"),
        ],
    )

    assert monster_power_amount(monster, "Vulnerable") == 2
    assert monster_power_amount(monster, "Poison") == 1
    assert monster_power_amount(monster, "Missing") == 0


def test_monster_power_amount_clamps_invalid_direct_amounts():
    assert monster_power_amount(SimpleNamespace(weak=-3), "Weak") == 0
    assert monster_power_amount(SimpleNamespace(frail="not-a-number"), "Frail") == 0
    assert monster_power_amount(SimpleNamespace(), "Artifact") == 0
    assert monster_power_amount(None, "Artifact") == 0
