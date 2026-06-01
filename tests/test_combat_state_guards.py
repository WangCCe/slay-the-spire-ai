from types import SimpleNamespace

from spirecomm.ai.heuristics.combat_state import player_block_value


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
