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


def _game_state(character):
    return SimpleNamespace(
        player=SimpleNamespace(current_hp=70, max_hp=80, energy=3, block=0, powers=[]),
        gold=0,
        hand=[],
        deck=[],
        discard_pile=[],
        draw_pile=[],
        floor=1,
        act=1,
        ascension_level=0,
        character=character,
    )


def test_rl_state_encoder_hand_card_hash_strips_counted_upgrade_suffix():
    encoder = StateEncoder()

    base_features = encoder._encode_single_card(_card("Cleave"))
    upgraded_features = encoder._encode_single_card(_card("Cleave+1", upgrades=1))

    assert upgraded_features[0] == base_features[0]


def test_rl_state_encoder_hand_card_hash_accepts_name_only_card():
    encoder = StateEncoder()
    card = SimpleNamespace(
        name="Bash",
        type=CardType.ATTACK,
        cost=2,
        cost_for_turn=2,
        upgrades=0,
        has_target=True,
        exhausts=False,
        properties=[],
    )

    features = encoder._encode_single_card(card)

    assert features[0] == encoder._stable_hash("Bash", 100) / 100.0


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


def test_rl_state_encoder_card_type_features_accept_card_type_attribute():
    encoder = StateEncoder()
    card = SimpleNamespace(
        name="Defend",
        card_type="CardType.SKILL",
        cost=1,
        cost_for_turn=1,
        upgrades=0,
        has_target=False,
        exhausts=False,
        properties=[],
    )

    features = encoder._encode_single_card(card)

    assert features[5] == 1.0


def test_rl_state_encoder_card_stats_accept_string_damage_and_block():
    encoder = StateEncoder()
    card = _card("Iron Wave")
    card.damage = "5"
    card.block = "5"

    features = encoder._encode_single_card(card)

    assert features[2] == 5 / 30
    assert features[3] == 5 / 20


def test_rl_state_encoder_infers_target_feature_for_name_only_attack_without_has_target():
    encoder = StateEncoder()
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        upgrades=0,
        exhausts=False,
        properties=[],
    )

    features = encoder._encode_single_card(strike)

    assert features[12] == 1.0


def test_rl_state_encoder_ignores_misleading_aoe_target_flag():
    encoder = StateEncoder()
    cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        upgrades=0,
        has_target=True,
        exhausts=False,
        properties=[],
    )

    features = encoder._encode_single_card(cleave)

    assert features[12] == 0.0


def test_rl_card_reward_features_infer_upgrade_flag_from_suffix():
    encoder = StateEncoder()

    features = encoder._encode_card_reward_card(_card("Cleave+1"))

    assert features[11] == 1.0


def test_rl_card_reward_features_accept_string_type_and_rarity():
    encoder = StateEncoder()
    card = _card("Cleave")
    card.type = "ATTACK"
    card.rarity = "UNCOMMON"

    features = encoder._encode_card_reward_card(card)

    assert features[1] == 1.0
    assert features[7] == 1.0


def test_rl_card_reward_features_accept_card_type_attribute():
    encoder = StateEncoder()
    card = SimpleNamespace(
        name="Inflame",
        card_type="CardType.POWER",
        rarity="UNCOMMON",
        cost=1,
        cost_for_turn=1,
        upgrades=0,
        exhausts=False,
        properties=[],
    )

    features = encoder._encode_card_reward_card(card)

    assert features[3] == 1.0


def test_rl_state_encoder_player_class_features_accept_strings():
    encoder = StateEncoder()

    features = encoder._encode_player_state(_game_state("IRONCLAD"))

    assert features[14] == 1.0


def test_rl_state_encoder_player_state_accepts_string_numeric_fields():
    encoder = StateEncoder()
    game = _game_state("IRONCLAD")
    game.player.current_hp = "40"
    game.player.max_hp = "80"
    game.player.energy = "3"
    game.player.block = "12"
    game.gold = "99"
    game.floor = "10"
    game.act = "2"
    game.ascension_level = "10"

    features = encoder._encode_player_state(game)

    assert features[0] == 0.5
    assert features[1] == 0.6
    assert features[2] == 0.6
    assert features[3] == 0.5
    assert features[8] == 10 / 55
    assert features[9:13] == [0.0, 1.0, 0.0, 0.0]
    assert features[13] == 0.5


def test_rl_state_encoder_context_accepts_string_energy():
    encoder = StateEncoder()
    game = SimpleNamespace(
        room_type="MONSTER",
        screen_type=None,
        in_combat=True,
        choice_list=[],
        choice_available=False,
        available_commands=[],
        turn=2,
        hand=[],
        player=SimpleNamespace(energy="4"),
    )

    features = encoder._encode_context(game)

    assert features[24] == 0.8
    assert features[25] == 0.8


def test_rl_state_encoder_context_accepts_string_hand_select_requirement():
    from spirecomm.spire.screen import ScreenType

    encoder = StateEncoder()
    game = SimpleNamespace(
        room_type="MONSTER",
        screen_type=ScreenType.HAND_SELECT,
        in_combat=True,
        choice_list=[],
        choice_available=False,
        available_commands=[],
        turn=2,
        hand=[],
        player=SimpleNamespace(energy=3),
        proceed_available=False,
        cancel_available=False,
        screen=SimpleNamespace(
            num_cards="2",
            selected_cards=[SimpleNamespace(name="Strike"), SimpleNamespace(name="Defend")],
            can_pick_zero=False,
        ),
    )

    features = encoder._encode_context(game)

    assert features[18] == 2 / 5
    assert features[19] == 2 / 5
    assert features[20] == 1.0


def test_rl_state_encoder_power_amount_accepts_name_only_power():
    encoder = StateEncoder()

    amount = encoder._get_power_amount(
        [SimpleNamespace(name="Strength", amount=3)],
        "Strength",
    )

    assert amount == 3


def test_rl_state_encoder_relic_features_accept_strings():
    encoder = StateEncoder()
    game = SimpleNamespace(relics=["Sozu"])

    features = encoder._encode_relics(game)

    assert features[encoder._stable_hash("Sozu", 89)] == 1.0
    assert sum(features) == 1.0


def test_rl_state_encoder_potion_slot_string_is_empty():
    encoder = StateEncoder()
    game = SimpleNamespace(potions=["Potion Slot"])

    features = encoder._encode_potions(game)

    assert features[0] == 0.0
    assert features[1] == 0.0
    assert features[2] == 0.0


def test_rl_state_encoder_name_only_potion_slot_has_no_identity_hash():
    encoder = StateEncoder()
    game = SimpleNamespace(potions=[SimpleNamespace(name="Potion Slot", can_use=False)])

    features = encoder._encode_potions(game)

    assert features[:3] == [0.0, 0.0, 0.0]


def test_rl_state_encoder_treats_missing_potion_can_use_as_usable():
    encoder = StateEncoder()
    game = SimpleNamespace(potions=[SimpleNamespace(potion_id="Strength Potion")])

    features = encoder._encode_potions(game)

    assert features[1] == 1.0
    assert features[2] == 1.0


def test_rl_state_encoder_treats_string_potion_as_usable():
    encoder = StateEncoder()
    game = SimpleNamespace(potions=["Fire Potion"])

    features = encoder._encode_potions(game)

    assert features[1] == 1.0
    assert features[2] == 1.0


def test_rl_state_encoder_potion_features_use_get_real_potions_without_raw_potions():
    encoder = StateEncoder()
    potion = SimpleNamespace(potion_id="Strength Potion")
    game = SimpleNamespace(get_real_potions=lambda: [potion])

    features = encoder._encode_potions(game)

    assert features[0] == encoder._stable_hash("Strength Potion", 30) / 30.0
    assert features[1] == 1.0
    assert features[2] == 1.0


def test_rl_state_encoder_combat_piles_card_in_play_accepts_name_only_card():
    encoder = StateEncoder()
    game = SimpleNamespace(
        exhaust_pile=[],
        limbo=[],
        cards_discarded_this_turn=0,
        card_in_play=SimpleNamespace(name="Bash"),
        potions=[],
        potion_available=False,
        are_potions_full=lambda: False,
    )

    features = encoder._encode_combat_piles(game)

    assert features[3] == encoder._stable_hash("Bash", 50) / 50.0


def test_rl_state_encoder_combat_piles_accepts_string_discard_count():
    encoder = StateEncoder()
    game = SimpleNamespace(
        exhaust_pile=[],
        limbo=[],
        cards_discarded_this_turn="4",
        card_in_play=None,
        potions=[],
        potion_available=False,
        are_potions_full=lambda: False,
    )

    features = encoder._encode_combat_piles(game)

    assert features[2] == 0.4


def test_rl_state_encoder_combat_piles_count_string_potion_slots_as_empty():
    encoder = StateEncoder()
    game = SimpleNamespace(
        exhaust_pile=[],
        limbo=[],
        cards_discarded_this_turn=0,
        card_in_play=None,
        potions=["Potion Slot", "Fire Potion"],
        potion_available=False,
        are_potions_full=lambda: False,
    )

    features = encoder._encode_combat_piles(game)

    assert features[4] == 1 / 5
    assert features[5] == 1 / 5


def test_rl_state_encoder_combat_piles_infers_potion_available_for_usable_potion():
    encoder = StateEncoder()
    game = SimpleNamespace(
        exhaust_pile=[],
        limbo=[],
        cards_discarded_this_turn=0,
        card_in_play=None,
        potions=[SimpleNamespace(potion_id="Strength Potion")],
        are_potions_full=lambda: False,
    )

    features = encoder._encode_combat_piles(game)

    assert features[7] == 1.0


def test_rl_state_encoder_combat_piles_counts_get_real_potions_without_raw_potions():
    encoder = StateEncoder()
    potion = SimpleNamespace(potion_id="Strength Potion")
    game = SimpleNamespace(
        exhaust_pile=[],
        limbo=[],
        cards_discarded_this_turn=0,
        card_in_play=None,
        get_real_potions=lambda: [potion],
        are_potions_full=lambda: False,
    )

    features = encoder._encode_combat_piles(game)

    assert features[4] == 1 / 5
    assert features[5] == 0.0
    assert features[7] == 1.0


def test_rl_state_encoder_intent_encoding_accepts_string_representations():
    encoder = StateEncoder()

    assert encoder._encode_intent("Intent.ATTACK_DEBUFF") == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Attack/Debuff") == [1.0, 0.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.DEFEND_BUFF") == [0.0, 1.0, 0.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.BUFF") == [0.0, 0.0, 1.0, 0.0, 0.0]
    assert encoder._encode_intent("Intent.STRONG_DEBUFF") == [0.0, 0.0, 0.0, 1.0, 0.0]
    assert encoder._encode_intent("NOT_ATTACK") == [0.0, 0.0, 0.0, 0.0, 1.0]
