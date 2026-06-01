from types import SimpleNamespace

from spirecomm.ai.heuristics.combat_state import draw_pile_count, player_block_value


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
