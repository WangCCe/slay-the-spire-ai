from spirecomm.spire.character import Monster, Player
from spirecomm.spire.game import Game
from spirecomm.spire.power import Power
from spirecomm.spire.potion import Potion
from spirecomm.spire.relic import Relic
from spirecomm.spire.screen import GridSelectScreen, HandSelectScreen, ShopScreen


def test_game_from_json_coerces_decimal_string_global_and_combat_fields():
    game = Game.from_json(
        {
            "current_hp": "70.0",
            "max_hp": "80.0",
            "floor": "12.0",
            "act": "2.0",
            "gold": "123.0",
            "seed": "456.0",
            "class": "IRONCLAD",
            "ascension_level": "5.0",
            "relics": [],
            "deck": [],
            "map": None,
            "potions": [],
            "is_screen_up": False,
            "screen_type": None,
            "screen_state": None,
            "room_phase": "COMBAT",
            "room_type": "Monster",
            "combat_state": {
                "player": {
                    "max_hp": "80.0",
                    "current_hp": "70.0",
                    "block": "5.0",
                    "energy": "3.0",
                    "powers": [],
                    "orbs": [],
                },
                "monsters": [],
                "draw_pile": [],
                "discard_pile": [],
                "exhaust_pile": [],
                "hand": [],
                "limbo": [],
                "card_in_play": None,
                "turn": "3.0",
                "cards_discarded_this_turn": "2.0",
            },
        },
        [],
    )

    assert game.current_hp == 70
    assert game.max_hp == 80
    assert game.floor == 12
    assert game.act == 2
    assert game.gold == 123
    assert game.seed == 456
    assert game.ascension_level == 5
    assert game.turn == 3
    assert game.cards_discarded_this_turn == 2


def test_player_from_json_coerces_decimal_string_numeric_fields():
    player = Player.from_json(
        {
            "max_hp": "80.0",
            "current_hp": "70.0",
            "block": "5.0",
            "energy": "3.0",
            "powers": [],
            "orbs": [],
        }
    )

    assert player.max_hp == 80
    assert player.current_hp == 70
    assert player.block == 5
    assert player.energy == 3


def test_monster_from_json_coerces_decimal_string_numeric_fields():
    monster = Monster.from_json(
        {
            "name": "Jaw Worm",
            "id": "JawWorm",
            "max_hp": "44.0",
            "current_hp": "31.0",
            "block": "6.0",
            "intent": "ATTACK",
            "half_dead": False,
            "is_gone": False,
            "move_id": "2.0",
            "last_move_id": "1.0",
            "second_last_move_id": "0.0",
            "move_base_damage": "11.0",
            "move_adjusted_damage": "13.0",
            "move_hits": "2.0",
            "powers": [],
        }
    )

    assert monster.max_hp == 44
    assert monster.current_hp == 31
    assert monster.block == 6
    assert monster.move_id == 2
    assert monster.last_move_id == 1
    assert monster.second_last_move_id == 0
    assert monster.move_base_damage == 11
    assert monster.move_adjusted_damage == 13
    assert monster.move_hits == 2


def test_power_from_json_coerces_decimal_string_numeric_fields():
    power = Power.from_json(
        {
            "id": "Strength",
            "name": "Strength",
            "amount": "2.0",
            "damage": "3.0",
            "misc": "4.0",
        }
    )

    assert power.amount == 2
    assert power.damage == 3
    assert power.misc == 4


def test_potion_from_json_coerces_decimal_string_price():
    potion = Potion.from_json(
        {
            "id": "Fire Potion",
            "name": "Fire Potion",
            "can_use": True,
            "can_discard": True,
            "requires_target": True,
            "price": "50.0",
        }
    )

    assert potion.price == 50


def test_relic_from_json_coerces_decimal_string_numeric_fields():
    relic = Relic.from_json(
        {
            "id": "Pen Nib",
            "name": "Pen Nib",
            "counter": "9.0",
            "price": "150.0",
        }
    )

    assert relic.counter == 9
    assert relic.price == 150


def test_shop_screen_from_json_coerces_decimal_string_purge_cost():
    screen = ShopScreen.from_json(
        {
            "cards": [],
            "relics": [],
            "potions": [],
            "purge_available": True,
            "purge_cost": "75.0",
        }
    )

    assert screen.purge_cost == 75


def test_grid_select_screen_from_json_coerces_decimal_string_num_cards():
    screen = GridSelectScreen.from_json(
        {
            "cards": [],
            "selected_cards": [],
            "num_cards": "2.0",
            "any_number": False,
            "confirm_up": False,
            "for_upgrade": False,
            "for_transform": False,
            "for_purge": True,
        }
    )

    assert screen.num_cards == 2


def test_hand_select_screen_from_json_coerces_decimal_string_num_cards():
    screen = HandSelectScreen.from_json(
        {
            "hand": [],
            "selected": [],
            "max_cards": "2.0",
            "can_pick_zero": False,
        }
    )

    assert screen.num_cards == 2
