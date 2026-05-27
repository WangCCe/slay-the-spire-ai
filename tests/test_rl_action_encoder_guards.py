from types import SimpleNamespace

from spirecomm.ai.rl.action_encoder import ActionEncoder
from spirecomm.communication.action import (
    BuyCardAction,
    BuyPotionAction,
    BuyPurgeAction,
    BuyRelicAction,
)
from spirecomm.spire.screen import ScreenType


def _game(**kwargs):
    defaults = dict(
        screen_type=ScreenType.SHOP_SCREEN,
        screen=None,
        choice_list=[],
        available_commands=["choose"],
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


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
