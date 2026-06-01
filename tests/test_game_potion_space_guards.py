from types import SimpleNamespace

from spirecomm.spire.game import Game


def _game(relics=None, potions=None, ascension_level=0):
    game = Game()
    game.relics = relics or []
    game.potions = potions or []
    game.ascension_level = ascension_level
    return game


def _potion(potion_id):
    return SimpleNamespace(potion_id=potion_id)


def test_has_potion_space_respects_string_sozu_relic():
    game = _game(
        relics=["Sozu"],
        potions=[_potion("Potion Slot")],
    )

    assert game.has_potion_space() is False


def test_has_potion_space_counts_string_potion_belt_slots():
    game = _game(
        relics=["Potion Belt"],
        potions=[
            _potion("FirePotion"),
            _potion("StrengthPotion"),
            _potion("FearPotion"),
        ],
    )

    assert game.has_potion_space() is True
