from types import SimpleNamespace

from spirecomm.ai.rl.v2.action_encoder import ActionEncoderV2
from spirecomm.ai.rl.v2 import action_space as space
from spirecomm.communication.action import (
    BossRewardAction,
    BuyCardAction,
    BuyPotionAction,
    BuyPurgeAction,
    ChooseAction,
    CombatRewardAction,
    EndTurnAction,
    LeaveAction,
    PlayCardAction,
    PotionAction,
    ProceedAction,
)
from spirecomm.spire.card import CardType
from spirecomm.spire.screen import RewardType, ScreenType


def _make_card(has_target=True, is_playable=True):
    return SimpleNamespace(has_target=has_target, is_playable=is_playable)


def _make_monster(hp=10, is_gone=False, half_dead=False):
    return SimpleNamespace(current_hp=hp, is_gone=is_gone, half_dead=half_dead)


def _make_game(**kwargs):
    defaults = dict(
        screen_type=None,
        in_combat=False,
        hand=[],
        monsters=[],
        potions=[],
        play_available=True,
        end_available=True,
        choice_available=False,
        choice_list=[],
        available_commands=[],
        screen=None,
        potion_available=True,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_action_dim_constants():
    assert space.ACTION_DIM == 133
    assert space.encode_play_card(3, 5) == 23
    assert space.encode_use_potion(2, 1) == 73


def test_encode_potion_action_uses_get_real_potions_without_raw_potions():
    encoder = ActionEncoderV2()
    potion = SimpleNamespace(
        potion_id="Strength Potion",
        can_use=True,
        requires_target=False,
    )
    game = _make_game(screen_type=None, in_combat=True)
    del game.potions
    game.get_real_potions = lambda: [potion]

    action_index = encoder.encode_action(PotionAction(True, potion=potion), game)

    assert action_index == space.encode_use_potion(0, 0)


def test_encode_play_card_action_accepts_numeric_string_card_index():
    encoder = ActionEncoderV2()
    game = _make_game(screen_type=None, in_combat=True, hand=[_make_card()])

    action_index = encoder.encode_action(
        PlayCardAction(card_index="0", target_index=None),
        game,
    )

    assert action_index == space.encode_play_card(0, 0)


def test_encode_play_card_action_relocates_card_uuid_before_stale_index():
    encoder = ActionEncoderV2()
    hand = [
        SimpleNamespace(uuid="flex", has_target=False, is_playable=True),
        SimpleNamespace(uuid="strike", has_target=True, is_playable=True),
    ]
    stale_strike = SimpleNamespace(
        uuid="strike", has_target=True, is_playable=True
    )
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=hand,
        monsters=[_make_monster()],
    )

    action_index = encoder.encode_action(
        PlayCardAction(card=stale_strike, card_index=0, target_index=0),
        game,
    )

    assert action_index == space.encode_play_card(1, 1)
    assert encoder.get_action_mask(game)[action_index]


def test_encode_play_card_action_rejects_nonfinite_card_index():
    encoder = ActionEncoderV2()
    game = _make_game(screen_type=None, in_combat=True, hand=[_make_card()])

    action_index = encoder.encode_action(
        PlayCardAction(card_index=float("inf"), target_index=None),
        game,
    )

    assert action_index is None


def test_encode_play_card_action_accepts_decimal_string_target_index():
    encoder = ActionEncoderV2()
    game = _make_game(screen_type=None, in_combat=True, hand=[_make_card()])

    action_index = encoder.encode_action(
        PlayCardAction(card_index=0, target_index="0.0"),
        game,
    )

    assert action_index == space.encode_play_card(0, 1)


def test_encode_potion_action_accepts_numeric_string_potion_index():
    encoder = ActionEncoderV2()
    potion = SimpleNamespace(
        potion_id="Strength Potion",
        can_use=True,
        requires_target=False,
    )
    game = _make_game(screen_type=None, in_combat=True, potions=[potion])

    action_index = encoder.encode_action(
        PotionAction(True, potion_index="0"),
        game,
    )

    assert action_index == space.encode_use_potion(0, 0)


def test_combat_mask_targets():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=True)],
        monsters=[_make_monster(), _make_monster()],
    )

    mask = encoder.get_action_mask(game)
    assert len(mask) == space.ACTION_DIM

    assert mask[space.encode_play_card(0, 1)]
    assert mask[space.encode_play_card(0, 2)]
    assert not mask[space.encode_play_card(0, 3)]


def test_combat_mask_ignores_half_dead_monsters():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=True)],
        monsters=[_make_monster(half_dead=True), _make_monster()],
    )

    mask = encoder.get_action_mask(game)

    assert not mask[space.encode_play_card(0, 1)]
    assert mask[space.encode_play_card(0, 2)]


def test_combat_mask_accepts_numeric_string_monster_hp():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=True)],
        monsters=[_make_monster(hp="0"), _make_monster(hp="12")],
    )

    mask = encoder.get_action_mask(game)

    assert not mask[space.encode_play_card(0, 1)]
    assert mask[space.encode_play_card(0, 2)]


def test_combat_mask_nontarget_card():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=False)],
        monsters=[_make_monster(), _make_monster()],
    )

    mask = encoder.get_action_mask(game)
    assert mask[space.encode_play_card(0, 0)]
    assert not mask[space.encode_play_card(0, 1)]


def test_combat_mask_requires_potion_available():
    encoder = ActionEncoderV2()
    potion = SimpleNamespace(potion_id="Fire Potion", can_use=True, requires_target=True)
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[],
        monsters=[_make_monster()],
        potions=[potion],
        potion_available=False,
    )

    mask = encoder.get_action_mask(game)

    assert not mask[space.encode_use_potion(0, 1)]


def test_combat_decoder_falls_back_for_unplayable_card_slot():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=True, is_playable=False)],
        monsters=[_make_monster()],
        end_available=True,
    )

    action = encoder.decode_action(space.encode_play_card(0, 1), game)

    assert isinstance(action, EndTurnAction)


def test_combat_decoder_falls_back_for_target_on_nontarget_card():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=False, is_playable=True)],
        monsters=[_make_monster()],
        end_available=True,
    )

    action = encoder.decode_action(space.encode_play_card(0, 1), game)

    assert isinstance(action, EndTurnAction)


def test_combat_decoder_falls_back_for_half_dead_target():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=True, is_playable=True)],
        monsters=[_make_monster(half_dead=True)],
        end_available=True,
    )

    action = encoder.decode_action(space.encode_play_card(0, 1), game)

    assert isinstance(action, EndTurnAction)


def test_combat_decoder_keeps_valid_card_and_potion_actions():
    encoder = ActionEncoderV2()
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        can_use=True,
        requires_target=True,
    )
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=True, is_playable=True)],
        monsters=[_make_monster()],
        potions=[potion],
    )

    card_action = encoder.decode_action(space.encode_play_card(0, 1), game)
    potion_action = encoder.decode_action(space.encode_use_potion(0, 1), game)

    assert isinstance(card_action, PlayCardAction)
    assert card_action.card_index == 0
    assert card_action.target_index == 0
    assert isinstance(potion_action, PotionAction)
    assert potion_action.potion_index == 0
    assert potion_action.target_index == 0


def test_combat_decoder_accepts_numeric_string_monster_hp():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[_make_card(has_target=True, is_playable=True)],
        monsters=[_make_monster(hp="12")],
    )

    action = encoder.decode_action(space.encode_play_card(0, 1), game)

    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0


def test_combat_mask_and_decoder_infer_target_for_name_only_attack_without_has_target():
    encoder = ActionEncoderV2()
    strike = SimpleNamespace(
        name="Strike",
        type=CardType.ATTACK,
        is_playable=True,
    )
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[strike],
        monsters=[_make_monster()],
    )

    mask = encoder.get_action_mask(game)
    action = encoder.decode_action(space.encode_play_card(0, 1), game)

    assert not mask[space.encode_play_card(0, 0)]
    assert mask[space.encode_play_card(0, 1)]
    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index == 0


def test_combat_mask_and_decoder_ignore_misleading_aoe_target_flag():
    encoder = ActionEncoderV2()
    cleave = SimpleNamespace(
        name="Cleave",
        type=CardType.ATTACK,
        has_target=True,
        is_playable=True,
    )
    game = _make_game(
        screen_type=None,
        in_combat=True,
        hand=[cleave],
        monsters=[_make_monster(), _make_monster()],
    )

    mask = encoder.get_action_mask(game)
    action = encoder.decode_action(space.encode_play_card(0, 0), game)

    assert mask[space.encode_play_card(0, 0)]
    assert not mask[space.encode_play_card(0, 1)]
    assert not mask[space.encode_play_card(0, 2)]
    assert isinstance(action, PlayCardAction)
    assert action.card_index == 0
    assert action.target_index is None


def test_combat_decoder_falls_back_for_unavailable_potion_slot():
    encoder = ActionEncoderV2()
    potion = SimpleNamespace(
        potion_id="Potion Slot",
        can_use=False,
        requires_target=True,
    )
    game = _make_game(
        screen_type=None,
        in_combat=True,
        potions=[potion],
        monsters=[_make_monster()],
        end_available=True,
    )

    action = encoder.decode_action(space.encode_use_potion(0, 1), game)

    assert isinstance(action, EndTurnAction)


def test_combat_mask_skips_string_empty_potion_slot():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        potions=["Potion Slot"],
        end_available=True,
    )

    mask = encoder.get_action_mask(game)

    assert mask[space.END_TURN_ACTION]
    assert not any(mask[space.USE_POTION_OFFSET:space.END_TURN_ACTION])


def test_combat_mask_uses_get_real_potions_without_raw_potions():
    encoder = ActionEncoderV2()
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        can_use=True,
        requires_target=False,
    )
    game = _make_game(
        screen_type=None,
        in_combat=True,
        monsters=[_make_monster()],
    )
    del game.potions
    game.get_real_potions = lambda: [potion]

    mask = encoder.get_action_mask(game)

    assert mask[space.encode_use_potion(0, 0)]


def test_combat_decoder_uses_get_real_potions_without_raw_potions():
    encoder = ActionEncoderV2()
    potion = SimpleNamespace(
        potion_id="Fire Potion",
        can_use=True,
        requires_target=False,
    )
    game = _make_game(
        screen_type=None,
        in_combat=True,
        monsters=[_make_monster()],
        end_available=True,
    )
    del game.potions
    game.get_real_potions = lambda: [potion]

    action = encoder.decode_action(space.encode_use_potion(0, 0), game)

    assert isinstance(action, PotionAction)
    assert action.potion_index == 0
    assert action.target_index is None


def test_combat_decoder_falls_back_for_string_empty_potion_slot():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=None,
        in_combat=True,
        potions=["Potion Slot"],
        end_available=True,
    )

    action = encoder.decode_action(space.encode_use_potion(0, 0), game)

    assert isinstance(action, EndTurnAction)


def test_map_choice_truncation():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=ScreenType.MAP,
        in_combat=False,
        choice_available=True,
        choice_list=["a", "b", "c"],
    )

    mask = encoder.get_action_mask(game)
    for idx in range(3):
        assert mask[space.MAP_OFFSET + idx]
    for idx in range(3, space.MAP_COUNT):
        assert not mask[space.MAP_OFFSET + idx]


def test_encode_choose_action_accepts_decimal_string_choice_index():
    encoder = ActionEncoderV2()
    game = _make_game(
        screen_type=ScreenType.EVENT,
        choice_available=True,
        choice_list=["leave", "fight"],
    )

    action_index = encoder.encode_action(ChooseAction("1.0"), game)

    assert action_index == space.EVENT_OFFSET + 1


def test_shop_mask_hides_unaffordable_purchases_and_purge():
    encoder = ActionEncoderV2()
    expensive_card = SimpleNamespace(name="Inflame", price=75)
    cheap_card = SimpleNamespace(name="Pommel Strike", price=30)
    expensive_relic = SimpleNamespace(name="Anchor", price=150)
    expensive_potion = SimpleNamespace(name="Fire Potion", price=50)
    screen = SimpleNamespace(
        cards=[expensive_card, cheap_card],
        relics=[expensive_relic],
        potions=[expensive_potion],
        purge_available=True,
        purge_cost=100,
    )
    game = _make_game(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=screen,
        gold=40,
        has_potion_space=lambda: True,
    )

    mask = encoder.get_action_mask(game)

    assert not mask[space.SHOP_OFFSET]
    assert mask[space.SHOP_OFFSET + 1]
    assert not mask[space.SHOP_OFFSET + 2]
    assert not mask[space.SHOP_OFFSET + 3]
    assert not mask[space.SHOP_OFFSET + 4]


def test_shop_mask_accepts_decimal_string_gold_and_price():
    encoder = ActionEncoderV2()
    cheap_card = SimpleNamespace(name="Pommel Strike", price="30.0")
    screen = SimpleNamespace(
        cards=[cheap_card],
        relics=[],
        potions=[],
        purge_available=False,
    )
    game = _make_game(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=screen,
        gold="40.0",
    )

    mask = encoder.get_action_mask(game)

    assert mask[space.SHOP_OFFSET]


def test_shop_mask_rejects_nonfinite_gold_and_price():
    encoder = ActionEncoderV2()
    card = SimpleNamespace(name="Pommel Strike", price=float("inf"))
    screen = SimpleNamespace(
        cards=[card],
        relics=[],
        potions=[],
        purge_available=False,
    )
    game = _make_game(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=screen,
        gold=float("inf"),
    )

    mask = encoder.get_action_mask(game)

    assert not mask[space.SHOP_OFFSET]


def test_shop_mask_accepts_decimal_string_gold_and_purge_cost():
    encoder = ActionEncoderV2()
    screen = SimpleNamespace(
        cards=[],
        relics=[],
        potions=[],
        purge_available=True,
        purge_cost="40.0",
    )
    game = _make_game(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=screen,
        gold="40.0",
    )

    mask = encoder.get_action_mask(game)

    assert mask[space.SHOP_OFFSET]


def test_shop_encoder_rejects_unaffordable_buy_card_action():
    encoder = ActionEncoderV2()
    expensive_card = SimpleNamespace(name="Inflame", price=75)
    screen = SimpleNamespace(
        cards=[expensive_card],
        relics=[],
        potions=[],
        purge_available=False,
    )
    game = _make_game(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=screen,
        gold=40,
    )

    assert encoder.encode_action(BuyCardAction(expensive_card), game) is None


def test_shop_decoder_falls_back_for_unaffordable_purchase_slots():
    encoder = ActionEncoderV2()
    expensive_card = SimpleNamespace(name="Inflame", price=75)
    cheap_potion = SimpleNamespace(name="Fire Potion", price=20)
    screen = SimpleNamespace(
        cards=[expensive_card],
        relics=[],
        potions=[cheap_potion],
        purge_available=True,
        purge_cost=100,
    )
    game = _make_game(
        screen_type=ScreenType.SHOP_ROOM,
        screen=screen,
        gold=40,
        has_potion_space=lambda: True,
    )

    assert isinstance(encoder.decode_action(space.SHOP_OFFSET, game), LeaveAction)
    assert isinstance(encoder.decode_action(space.SHOP_OFFSET + 1, game), BuyPotionAction)
    assert isinstance(encoder.decode_action(space.SHOP_OFFSET + 2, game), LeaveAction)


def test_shop_screen_decoder_uses_purchase_actions_for_item_slots():
    encoder = ActionEncoderV2()
    cheap_card = SimpleNamespace(name="Pommel Strike", price=30)
    cheap_potion = SimpleNamespace(name="Fire Potion", price=20)
    screen = SimpleNamespace(
        cards=[cheap_card],
        relics=[],
        potions=[cheap_potion],
        purge_available=True,
        purge_cost=40,
    )
    game = _make_game(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=screen,
        gold=40,
        has_potion_space=lambda: True,
    )

    assert isinstance(encoder.decode_action(space.SHOP_OFFSET, game), BuyCardAction)
    assert isinstance(encoder.decode_action(space.SHOP_OFFSET + 1, game), BuyPotionAction)
    assert isinstance(encoder.decode_action(space.SHOP_OFFSET + 2, game), BuyPurgeAction)


def test_combat_reward_mask_hides_potion_reward_when_potion_slots_are_full():
    encoder = ActionEncoderV2()
    potion_reward = SimpleNamespace(
        reward_type=RewardType.POTION,
        potion=SimpleNamespace(name="Fire Potion"),
    )
    gold_reward = SimpleNamespace(reward_type=RewardType.GOLD, gold=25)
    game = _make_game(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward, gold_reward]),
        are_potions_full=lambda: True,
    )

    mask = encoder.get_action_mask(game)

    assert not mask[space.REWARD_OFFSET]
    assert mask[space.REWARD_OFFSET + 1]


def test_combat_reward_mask_hides_namespaced_string_potion_reward_when_slots_are_full():
    encoder = ActionEncoderV2()
    potion_reward = SimpleNamespace(reward_type="RewardType.POTION")
    gold_reward = SimpleNamespace(reward_type=RewardType.GOLD, gold=25)
    game = _make_game(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward, gold_reward]),
        are_potions_full=lambda: True,
    )

    mask = encoder.get_action_mask(game)

    assert not mask[space.REWARD_OFFSET]
    assert mask[space.REWARD_OFFSET + 1]


def test_combat_reward_mask_hides_potion_reward_when_potion_space_is_blocked():
    encoder = ActionEncoderV2()
    potion_reward = SimpleNamespace(
        reward_type=RewardType.POTION,
        potion=SimpleNamespace(name="Fire Potion"),
    )
    gold_reward = SimpleNamespace(reward_type=RewardType.GOLD, gold=25)
    game = _make_game(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward, gold_reward]),
        are_potions_full=lambda: False,
        has_potion_space=lambda: False,
    )

    mask = encoder.get_action_mask(game)

    assert not mask[space.REWARD_OFFSET]
    assert mask[space.REWARD_OFFSET + 1]


def test_combat_reward_decoder_falls_back_for_full_potion_slots():
    encoder = ActionEncoderV2()
    potion_reward = SimpleNamespace(
        reward_type=RewardType.POTION,
        potion=SimpleNamespace(name="Fire Potion"),
    )
    game = _make_game(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward]),
        available_commands=["proceed"],
        are_potions_full=lambda: True,
    )

    action = encoder.decode_action(space.REWARD_OFFSET, game)

    assert isinstance(action, ProceedAction)


def test_combat_reward_encoder_rejects_full_slot_potion_reward():
    encoder = ActionEncoderV2()
    potion_reward = SimpleNamespace(
        reward_type=RewardType.POTION,
        potion=SimpleNamespace(name="Fire Potion"),
    )
    game = _make_game(
        screen_type=ScreenType.COMBAT_REWARD,
        screen=SimpleNamespace(rewards=[potion_reward]),
        are_potions_full=lambda: True,
    )

    assert encoder.encode_action(CombatRewardAction(potion_reward), game) is None


def test_boss_reward_mask_uses_screen_relics():
    encoder = ActionEncoderV2()
    relics = [
        SimpleNamespace(name="Black Star"),
        SimpleNamespace(name="Coffee Dripper"),
    ]
    game = _make_game(
        screen_type=ScreenType.BOSS_REWARD,
        screen=SimpleNamespace(relics=relics),
    )

    mask = encoder.get_action_mask(game)

    assert mask[space.REWARD_OFFSET]
    assert mask[space.REWARD_OFFSET + 1]
    assert not mask[space.REWARD_OFFSET + 2]


def test_boss_reward_decoder_returns_boss_reward_action():
    encoder = ActionEncoderV2()
    relics = [
        SimpleNamespace(name="Black Star"),
        SimpleNamespace(name="Coffee Dripper"),
    ]
    game = _make_game(
        screen_type=ScreenType.BOSS_REWARD,
        screen=SimpleNamespace(relics=relics),
    )

    action = encoder.decode_action(space.REWARD_OFFSET + 1, game)

    assert isinstance(action, BossRewardAction)
    assert action.name == "Coffee Dripper"
