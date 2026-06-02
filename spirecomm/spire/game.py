from enum import Enum

import spirecomm.spire.relic
import spirecomm.spire.card
import spirecomm.spire.character
import spirecomm.spire.map
import spirecomm.spire.potion
import spirecomm.spire.screen
from spirecomm.spire.identifiers import potion_id, relic_id


def _safe_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return default


class RoomPhase(Enum):
    COMBAT = 1,
    EVENT = 2,
    COMPLETE = 3,
    INCOMPLETE = 4


class Game:

    def __init__(self):

        # General state

        self.current_action = None
        self.current_hp = 0
        self.max_hp = 0
        self.floor = 0
        self.act = 0
        self.gold = 0
        self.seed = 0
        self.character = None
        self.ascension_level = None
        self.relics = []
        self.deck = []
        self.potions = []
        self.map = []

        # Combat state

        self.in_combat = False
        self.player = None
        self.monsters = []
        self.draw_pile = []
        self.discard_pile = []
        self.exhaust_pile = []
        self.hand = []
        self.limbo = []
        self.card_in_play = None
        self.turn = 0
        self.cards_discarded_this_turn = 0

        # Current Screen

        self.screen = None
        self.screen_up = False
        self.screen_type = None
        self.room_phase = None
        self.room_type = None
        self.choice_list = []
        self.choice_available = False

        # Available Commands

        self.end_available = False
        self.potion_available = False
        self.play_available = False
        self.proceed_available = False
        self.cancel_available = False

    @classmethod
    def from_json(cls, json_state, available_commands):
        game = cls()
        game.current_action = json_state.get("current_action", None)
        game.current_hp = _safe_int(json_state.get("current_hp"), 0)
        game.max_hp = _safe_int(json_state.get("max_hp"), 0)
        game.floor = _safe_int(json_state.get("floor"), 0)
        game.act = _safe_int(json_state.get("act"), 0)
        game.gold = _safe_int(json_state.get("gold"), 0)
        game.seed = _safe_int(json_state.get("seed"), 0)
        # Handle None class field (can happen on game over or special screens)
        class_name = json_state.get("class")
        if class_name is not None:
            game.character = spirecomm.spire.character.PlayerClass[class_name]
        else:
            game.character = None
        game.ascension_level = _safe_int(json_state.get("ascension_level"), 0)

        # Handle list fields that may be None
        relics_data = json_state.get("relics")
        game.relics = [spirecomm.spire.relic.Relic.from_json(json_relic) for json_relic in relics_data] if relics_data else []

        deck_data = json_state.get("deck")
        game.deck = [spirecomm.spire.card.Card.from_json(json_card) for json_card in deck_data] if deck_data else []

        map_data = json_state.get("map")
        game.map = spirecomm.spire.map.Map.from_json(map_data) if map_data else None

        potions_data = json_state.get("potions")
        game.potions = [spirecomm.spire.potion.Potion.from_json(potion) for potion in potions_data] if potions_data else []

        game.act_boss = json_state.get("act_boss", None)

        # Screen State

        game.screen_up = json_state.get("is_screen_up", False)

        # Handle screen_type and room_phase that may be None
        screen_type_name = json_state.get("screen_type")
        game.screen_type = spirecomm.spire.screen.ScreenType[screen_type_name] if screen_type_name else None

        screen_state_data = json_state.get("screen_state")
        game.screen = spirecomm.spire.screen.screen_from_json(game.screen_type, screen_state_data) if game.screen_type else None

        room_phase_name = json_state.get("room_phase")
        game.room_phase = RoomPhase[room_phase_name] if room_phase_name else None

        game.room_type = json_state.get("room_type")
        game.choice_available = "choice_list" in json_state
        if game.choice_available:
            game.choice_list = json_state.get("choice_list")

        # Combat state

        game.in_combat = game.room_phase == RoomPhase.COMBAT if game.room_phase else False
        if game.in_combat:
            combat_state = json_state.get("combat_state")
            if combat_state:
                game.player = spirecomm.spire.character.Player.from_json(combat_state.get("player"))

                monsters_data = combat_state.get("monsters")
                game.monsters = [spirecomm.spire.character.Monster.from_json(json_monster) for json_monster in monsters_data] if monsters_data else []
                for i, monster in enumerate(game.monsters):
                    monster.monster_index = i

                draw_pile_data = combat_state.get("draw_pile")
                game.draw_pile = [spirecomm.spire.card.Card.from_json(json_card) for json_card in draw_pile_data] if draw_pile_data else []

                discard_pile_data = combat_state.get("discard_pile")
                game.discard_pile = [spirecomm.spire.card.Card.from_json(json_card) for json_card in discard_pile_data] if discard_pile_data else []

                exhaust_pile_data = combat_state.get("exhaust_pile")
                game.exhaust_pile = [spirecomm.spire.card.Card.from_json(json_card) for json_card in exhaust_pile_data] if exhaust_pile_data else []

                hand_data = combat_state.get("hand")
                game.hand = [spirecomm.spire.card.Card.from_json(json_card) for json_card in hand_data] if hand_data else []

                limbo_data = combat_state.get("limbo")
                game.limbo = [spirecomm.spire.card.Card.from_json(json_card) for json_card in limbo_data] if limbo_data else []

                game.card_in_play = combat_state.get("card_in_play", None)
                if game.card_in_play is not None:
                    game.card_in_play = spirecomm.spire.card.Card.from_json(game.card_in_play)
                game.turn = _safe_int(combat_state.get("turn", 0), 0)
                game.cards_discarded_this_turn = _safe_int(
                    combat_state.get("cards_discarded_this_turn", 0),
                    0,
                )

        # Available Commands

        game.end_available = "end" in available_commands
        game.potion_available = "potion" in available_commands
        game.play_available = "play" in available_commands
        game.proceed_available = "proceed" in available_commands or "confirm" in available_commands
        game.cancel_available = "cancel" in available_commands or "leave" in available_commands \
                                or "return" in available_commands or "skip" in available_commands
        game.available_commands = list(available_commands) if available_commands is not None else []

        return game

    def are_potions_full(self):
        for potion in self.potions:
            if potion_id(potion) == "Potion Slot":
                return False
        return True

    def has_potion_space(self):
        """Return True if the player can obtain another potion."""
        relic_ids = {relic_id(relic) for relic in self.relics or []}
        if "Sozu" in relic_ids:
            return False

        potions = self.potions or []
        for potion in potions:
            if potion_id(potion) == "Potion Slot":
                return True

        ascension = self.ascension_level or 0
        base_slots = 2 if ascension >= 11 else 3
        if "Potion Belt" in relic_ids:
            base_slots += 2

        real_potions = [
            potion
            for potion in potions
            if potion_id(potion) != "Potion Slot"
        ]
        return len(real_potions) < base_slots

    def get_real_potions(self):
        potions = []
        for potion in self.potions:
            if potion_id(potion) != "Potion Slot":
                potions.append(potion)
        return potions
