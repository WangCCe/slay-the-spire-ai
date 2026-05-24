from types import SimpleNamespace

from spirecomm.ai.rl.v2.action_encoder import ActionEncoderV2
from spirecomm.ai.rl.v2 import action_space as space
from spirecomm.spire.screen import ScreenType


def _make_card(has_target=True, is_playable=True):
    return SimpleNamespace(has_target=has_target, is_playable=is_playable)


def _make_monster(hp=10, is_gone=False):
    return SimpleNamespace(current_hp=hp, is_gone=is_gone)


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
