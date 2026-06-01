from types import SimpleNamespace

from spirecomm.ai.rl.action_encoder import ActionEncoder
from spirecomm.communication.action import (
    BuyCardAction,
    BuyPotionAction,
    BuyPurgeAction,
    BuyRelicAction,
    EndTurnAction,
    PlayCardAction,
    PotionAction,
)
from spirecomm.spire.card import CardType
from spirecomm.spire.screen import ScreenType


def _game(**kwargs):
    defaults = dict(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=None,
        in_combat=False,
        choice_available=False,
        choice_list=[],
        available_commands=["choose"],
        proceed_available=False,
        cancel_available=False,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _combat_game(**kwargs):
    defaults = dict(
        screen_type=None,
        screen=None,
        in_combat=True,
        choice_available=False,
        choice_list=[],
        available_commands=[],
        proceed_available=False,
        cancel_available=False,
        end_available=False,
        play_available=True,
        potion_available=True,
        hand=[],
        monsters=[SimpleNamespace(current_hp=10, is_gone=False, half_dead=False)],
        potions=[],
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _potion(name, requires_target=True):
    return SimpleNamespace(
        potion_id=name,
        can_use=True,
        requires_target=requires_target,
    )


def _card(has_target=True, is_playable=True):
    return SimpleNamespace(has_target=has_target, is_playable=is_playable)


def test_legacy_shop_decoder_uses_item_offsets_for_purchases():
    encoder = ActionEncoder()
    card = SimpleNamespace(name="Pommel Strike")
    relic = SimpleNamespace(name="Anchor")
    potion = SimpleNamespace(name="Fire Potion")
    screen = SimpleNamespace(
        cards=[card],
        relics=[relic],
        potions=[potion],
        purge_available=True,
    )
    game = _game(
        screen=screen,
        choice_list=["Pommel Strike", "Anchor", "Fire Potion", "purge"],
        has_potion_space=lambda: True,
    )

    card_action = encoder.decode_action(encoder.SHOP_ACTION_OFFSET, game)
    relic_action = encoder.decode_action(encoder.SHOP_ACTION_OFFSET + 1, game)
    potion_action = encoder.decode_action(encoder.SHOP_ACTION_OFFSET + 2, game)
    purge_action = encoder.decode_action(encoder.SHOP_ACTION_OFFSET + 3, game)

    assert isinstance(card_action, BuyCardAction)
    assert isinstance(relic_action, BuyRelicAction)
    assert isinstance(potion_action, BuyPotionAction)
    assert isinstance(purge_action, BuyPurgeAction)


def test_legacy_shop_mask_uses_structured_items_and_potion_space():
    encoder = ActionEncoder()
    card = SimpleNamespace(name="Pommel Strike")
    relic = SimpleNamespace(name="Anchor")
    potion = SimpleNamespace(name="Fire Potion")
    screen = SimpleNamespace(
        cards=[card],
        relics=[relic],
        potions=[potion],
        purge_available=True,
    )
    game = _game(
        screen=screen,
        choice_list=[],
        has_potion_space=lambda: False,
    )

    mask = encoder.get_action_mask(game)

    assert mask[encoder.SHOP_ACTION_OFFSET]
    assert mask[encoder.SHOP_ACTION_OFFSET + 1]
    assert not mask[encoder.SHOP_ACTION_OFFSET + 2]
    assert mask[encoder.SHOP_ACTION_OFFSET + 3]


def test_legacy_combat_reward_mask_hides_string_potion_reward_when_slots_are_full():
    encoder = ActionEncoder()
    potion_reward = SimpleNamespace(reward_type="POTION")
    gold_reward = SimpleNamespace(reward_type="GOLD")
    game = _game(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward, gold_reward]),
        are_potions_full=lambda: True,
    )

    mask = encoder.get_action_mask(game)

    assert not mask[encoder.CARD_REWARD_OFFSET]
    assert mask[encoder.CARD_REWARD_OFFSET + 1]


def test_legacy_combat_reward_mask_hides_potion_reward_when_space_is_blocked():
    encoder = ActionEncoder()
    potion_reward = SimpleNamespace(reward_type="POTION")
    gold_reward = SimpleNamespace(reward_type="GOLD")
    game = _game(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward, gold_reward]),
        are_potions_full=lambda: False,
        has_potion_space=lambda: False,
    )

    mask = encoder.get_action_mask(game)

    assert not mask[encoder.CARD_REWARD_OFFSET]
    assert mask[encoder.CARD_REWARD_OFFSET + 1]


def test_legacy_potion_mask_respects_potion_available():
    encoder = ActionEncoder()
    game = _combat_game(
        potions=[_potion("Fire Potion")],
        potion_available=False,
    )

    mask = encoder.get_action_mask(game)

    assert not any(mask[encoder.USE_POTION_OFFSET:encoder.END_TURN_ACTION])


def test_legacy_potion_mask_does_not_collide_with_end_turn_action():
    encoder = ActionEncoder()
    game = _combat_game(
        potions=[
            _potion("Fire Potion"),
            _potion("Strength Potion"),
            _potion("Dexterity Potion"),
        ],
        end_available=False,
    )

    mask = encoder.get_action_mask(game)

    assert not mask[encoder.END_TURN_ACTION]


def test_legacy_nontarget_potion_mask_uses_self_slot_only():
    encoder = ActionEncoder()
    game = _combat_game(
        potions=[_potion("Strength Potion", requires_target=False)],
        monsters=[
            SimpleNamespace(current_hp=10, is_gone=False, half_dead=False),
            SimpleNamespace(current_hp=10, is_gone=False, half_dead=False),
        ],
    )

    mask = encoder.get_action_mask(game)

    assert mask[encoder.encode_use_potion(0, 0)]
    assert not mask[encoder.encode_use_potion(0, 1)]


def test_legacy_nontarget_potion_decoder_omits_target():
    encoder = ActionEncoder()
    game = _combat_game(
        potions=[_potion("Strength Potion", requires_target=False)],
        monsters=[SimpleNamespace(current_hp=10, is_gone=False, half_dead=False)],
    )

    action = encoder.decode_action(encoder.encode_use_potion(0, 0), game)

    assert isinstance(action, PotionAction)
    assert action.potion_index == 0
    assert action.target_index is None


def test_legacy_potion_decoder_treats_missing_requires_target_as_not_targeted():
    encoder = ActionEncoder()
    potion = SimpleNamespace(potion_id="Strength Potion", can_use=True)
    game = _combat_game(
        potions=[potion],
        monsters=[SimpleNamespace(current_hp=10, is_gone=False, half_dead=False)],
    )

    mask = encoder.get_action_mask(game)
    action = encoder.decode_action(encoder.encode_use_potion(0, 0), game)

    assert mask[encoder.encode_use_potion(0, 0)]
    assert isinstance(action, PotionAction)
    assert action.potion_index == 0
    assert action.target_index is None


def test_legacy_combat_mask_skips_card_without_cost():
    encoder = ActionEncoder()
    game = _combat_game(
        hand=[_card(has_target=True)],
        player=SimpleNamespace(energy=3),
        end_available=True,
    )

    mask = encoder.get_action_mask(game)

    assert mask[encoder.END_TURN_ACTION]
    assert not any(mask[: encoder.USE_POTION_OFFSET])


def test_legacy_combat_mask_skips_cards_without_player_energy():
    encoder = ActionEncoder()
    card = _card(has_target=True)
    card.cost_for_turn = 1
    game = _combat_game(
        hand=[card],
        end_available=True,
    )

    mask = encoder.get_action_mask(game)

    assert mask[encoder.END_TURN_ACTION]
    assert not any(mask[: encoder.USE_POTION_OFFSET])


def test_legacy_combat_mask_parses_string_turn_cost():
    encoder = ActionEncoder()
    card = _card(has_target=True)
    card.cost = 3
    card.cost_for_turn = "2"
    game = _combat_game(
        hand=[card],
        player=SimpleNamespace(energy=1),
        end_available=True,
    )

    mask = encoder.get_action_mask(game)

    assert mask[encoder.END_TURN_ACTION]
    assert not any(mask[: encoder.USE_POTION_OFFSET])


def test_legacy_hand_select_mask_accepts_string_num_cards_for_confirm():
    encoder = ActionEncoder()
    game = _game(
        screen_type=ScreenType.HAND_SELECT,
        screen=SimpleNamespace(
            cards=[SimpleNamespace(name="Strike"), SimpleNamespace(name="Defend")],
            selected_cards=[SimpleNamespace(name="Strike"), SimpleNamespace(name="Defend")],
            num_cards="2",
            can_pick_zero=False,
        ),
        available_commands=["key", "click"],
    )

    mask = encoder.get_action_mask(game)

    assert mask[encoder.CONFIRM_ACTION]


def test_legacy_potion_decoder_falls_back_for_unusable_potion():
    encoder = ActionEncoder()
    potion = _potion("Fire Potion")
    potion.can_use = False
    game = _combat_game(
        potions=[potion],
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_use_potion(0, 0), game)

    assert isinstance(action, EndTurnAction)


def test_legacy_potion_decoder_falls_back_for_empty_potion_slot():
    encoder = ActionEncoder()
    game = _combat_game(
        potions=[_potion("Potion Slot")],
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_use_potion(0, 0), game)

    assert isinstance(action, EndTurnAction)


def test_legacy_potion_mask_skips_string_empty_potion_slot():
    encoder = ActionEncoder()
    game = _combat_game(
        potions=["Potion Slot"],
        end_available=True,
    )

    mask = encoder.get_action_mask(game)

    assert mask[encoder.END_TURN_ACTION]
    assert not any(mask[encoder.USE_POTION_OFFSET:encoder.END_TURN_ACTION])


def test_legacy_potion_mask_uses_get_real_potions_without_raw_potions():
    encoder = ActionEncoder()
    potion = _potion("Fire Potion", requires_target=False)
    game = _combat_game(end_available=True)
    del game.potions
    game.get_real_potions = lambda: [potion]

    mask = encoder.get_action_mask(game)

    assert mask[encoder.encode_use_potion(0, 0)]


def test_legacy_potion_decoder_uses_get_real_potions_without_raw_potions():
    encoder = ActionEncoder()
    potion = _potion("Fire Potion", requires_target=False)
    game = _combat_game(end_available=True)
    del game.potions
    game.get_real_potions = lambda: [potion]

    action = encoder.decode_action(encoder.encode_use_potion(0, 0), game)

    assert isinstance(action, PotionAction)
    assert action.potion_index == 0
    assert action.target_index is None


def test_legacy_potion_decoder_falls_back_for_string_empty_potion_slot():
    encoder = ActionEncoder()
    game = _combat_game(
        potions=["Potion Slot"],
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_use_potion(0, 0), game)

    assert isinstance(action, EndTurnAction)


def test_legacy_potion_decoder_falls_back_for_dead_target():
    encoder = ActionEncoder()
    game = _combat_game(
        potions=[_potion("Fire Potion", requires_target=True)],
        monsters=[SimpleNamespace(current_hp=0, is_gone=False, half_dead=False)],
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_use_potion(0, 0), game)

    assert isinstance(action, EndTurnAction)


def test_legacy_card_decoder_falls_back_for_unplayable_card():
    encoder = ActionEncoder()
    game = _combat_game(
        hand=[_card(has_target=True, is_playable=False)],
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_play_card(0, 0), game)

    assert isinstance(action, EndTurnAction)


def test_legacy_card_decoder_falls_back_for_dead_target():
    encoder = ActionEncoder()
    game = _combat_game(
        hand=[_card(has_target=True)],
        monsters=[SimpleNamespace(current_hp=0, is_gone=False, half_dead=False)],
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_play_card(0, 0), game)

    assert isinstance(action, EndTurnAction)


def test_legacy_card_decoder_keeps_valid_targeted_card():
    encoder = ActionEncoder()
    game = _combat_game(
        hand=[_card(has_target=True)],
        monsters=[SimpleNamespace(current_hp=10, is_gone=False, half_dead=False)],
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_play_card(0, 0), game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0


def test_legacy_card_decoder_infers_target_for_name_only_attack_without_has_target():
    encoder = ActionEncoder()
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        is_playable=True,
    )
    game = _combat_game(
        hand=[strike],
        monsters=[SimpleNamespace(current_hp=10, is_gone=False, half_dead=False)],
        player=SimpleNamespace(energy=1),
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_play_card(0, 0), game)
    mask = encoder.get_action_mask(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0
    assert mask[encoder.encode_play_card(0, 0)]


def test_legacy_card_mask_ignores_misleading_aoe_target_flag():
    encoder = ActionEncoder()
    cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        cost=1,
        cost_for_turn=1,
        has_target=True,
        is_playable=True,
    )
    game = _combat_game(
        hand=[cleave],
        monsters=[
            SimpleNamespace(current_hp=10, is_gone=False, half_dead=False),
            SimpleNamespace(current_hp=10, is_gone=False, half_dead=False),
        ],
        player=SimpleNamespace(energy=1),
        end_available=True,
    )

    action = encoder.decode_action(encoder.encode_play_card(0, 0), game)
    mask = encoder.get_action_mask(game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index is None
    assert mask[encoder.encode_play_card(0, 0)]
    assert not mask[encoder.encode_play_card(0, 1)]
