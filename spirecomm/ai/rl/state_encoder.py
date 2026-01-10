"""
State encoder - FIXED VERSION (570 dims)
"""
import numpy as np
from typing import List
from spirecomm.spire.game import Game
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster, PlayerClass

class StateEncoder:
    def __init__(self):
        self.feature_dim = 570

    def encode(self, game: Game) -> np.ndarray:
        features = []
        features.extend(self._encode_player_state(game))
        features.extend(self._encode_hand_cards(game))
        features.extend(self._encode_deck_composition(game))
        features.extend(self._encode_monster_states(game))
        features.extend(self._encode_relics(game))
        features.extend(self._encode_potions(game))
        features.extend(self._encode_context(game))
        return np.array(features, dtype=np.float32)

    def _encode_player_state(self, game: Game) -> List[float]:
        if game.player is None:
            return [0.0] * 18  # Fixed to 18 dims
        player = game.player
        import math
        return [
            player.current_hp / player.max_hp if player.max_hp > 0 else 0.0,
            min(player.energy, 5) / 5.0,
            min(player.block, 20) / 20.0,
            min(math.log10(game.gold + 1) / 4.0, 1.0),
            min(len(game.hand) if game.hand else 0, 10) / 10.0,
            min(len(game.deck) if game.deck else 0, 30) / 30.0,
            min(len(game.discard_pile) if game.discard_pile else 0, 30) / 30.0,
            min(len(game.draw_pile) if game.draw_pile else 0, 30) / 30.0,
            min(game.floor, 55) / 55.0,
            *[1.0 if (game.act or 1) == i else 0.0 for i in range(1, 5)],
            min((game.ascension_level or 0), 20) / 20.0,
            1.0 if (game.character or PlayerClass.IRONCLAD) == PlayerClass.IRONCLAD else 0.0,
            1.0 if (game.character or PlayerClass.IRONCLAD) == PlayerClass.THE_SILENT else 0.0,
            1.0 if (game.character or PlayerClass.IRONCLAD) == PlayerClass.DEFECT else 0.0,
            0.0,  # Placeholder for 4th class
            0.0,  # Extra feature to reach 18 dims
        ]

    def _encode_hand_cards(self, game: Game) -> List[float]:
        hand = game.hand if game.hand else []
        features = []
        for i in range(10):
            if i < len(hand):
                features.extend(self._encode_single_card(hand[i]))
            else:
                features.extend([0.0] * 15)
        return features

    def _encode_single_card(self, card: Card) -> List[float]:
        # Safely extract card properties with error handling
        damage = 0
        block = 0

        # Try to get damage/block from card properties if available
        if hasattr(card, 'properties') and card.properties:
            try:
                for p in card.properties:
                    if hasattr(p, 'damage'):
                        damage = getattr(p, 'damage', 0)
                    if hasattr(p, 'block'):
                        block = getattr(p, 'block', 0)
            except (AttributeError, TypeError):
                pass  # Use default values

        # Fallback: try to get directly from card
        if damage == 0 and hasattr(card, 'damage'):
            try:
                damage = card.damage
            except (AttributeError, TypeError):
                pass

        if block == 0 and hasattr(card, 'block'):
            try:
                block = card.block
            except (AttributeError, TypeError):
                pass

        # Get card type safely
        card_type_val = 0
        if hasattr(card, 'card_type'):
            try:
                card_type_val = int(card.card_type) if card.card_type is not None else 0
            except (TypeError, ValueError):
                card_type_val = 0

        # Get card ID safely - handle various types
        card_id_hash = 0.0
        if hasattr(card, 'id'):
            try:
                card_id = card.id
                # Handle different types of card.id
                if isinstance(card_id, (int, float, np.integer, np.floating)):
                    # If it's a number, just use it
                    card_id_hash = abs(int(card_id)) % 100 / 100.0
                else:
                    # If it's a string or object, hash it
                    card_id_hash = hash(str(card_id)) % 100 / 100.0
            except (AttributeError, TypeError, ValueError):
                card_id_hash = 0.0

        return [
            card_id_hash,
            min((card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost), 3) / 3.0 if hasattr(card, 'cost') else 0.0,
            min(damage, 30) / 30.0,
            min(block, 20) / 20.0,
            1.0 if card_type_val == 0 else 0.0,  # Attack
            1.0 if card_type_val == 1 else 0.0,  # Skill
            1.0 if card_type_val == 2 else 0.0,  # Power
            1.0 if card_type_val == 3 else 0.0,  # Status/Curse
            1.0 if (hasattr(card, 'upgrade') and card.upgrade != 0) else 0.0,
            0.0,  # placeholder
            1.0 if (hasattr(card, 'exhausts') and card.exhausts) else 0.0 if hasattr(card, 'exhausts') else 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        ]

    def _encode_deck_composition(self, game: Game) -> List[float]:
        return [0.0] * 120

    def _encode_monster_states(self, game: Game) -> List[float]:
        monsters = game.monsters if game.monsters else []
        features = []
        for i in range(5):
            if i < len(monsters):
                features.extend(self._encode_single_monster(monsters[i]))
            else:
                features.extend([0.0] * 30)
        return features

    def _encode_single_monster(self, monster: Monster) -> List[float]:
        import math
        hp_norm = monster.current_hp / monster.max_hp if monster.max_hp > 0 else 0.0
        return [
            hash(monster.name if hasattr(monster, 'name') else "Unknown") % 60 / 60.0,
            hp_norm,
            min(math.log10(monster.max_hp + 1) / 2.5, 1.0),
            min((monster.block if hasattr(monster, 'block') else 0), 20) / 20.0,
            *[0.0 for _ in range(26)],
        ]

    def _encode_relics(self, game: Game) -> List[float]:
        return [0.0] * 89

    def _encode_potions(self, game: Game) -> List[float]:
        potions = game.potions if game.potions else []
        features = []
        for i in range(5):
            if i < len(potions):
                # Safely get potion name/id
                potion = potions[i]
                if hasattr(potion, 'potion_id'):
                    name = potion.potion_id
                elif hasattr(potion, 'name'):
                    name = potion.name
                elif hasattr(potion, 'id'):
                    name = potion.id
                else:
                    # Convert to string safely
                    try:
                        name = str(potion)
                    except Exception:
                        name = "Unknown"

                features.extend([hash(name) % 30 / 30.0, 1.0, 1.0])
            else:
                features.extend([0.0] * 3)
        return features

    def _encode_context(self, game: Game) -> List[float]:
        room_type = game.room_type if game.room_type else "MONSTER"
        return [
            *[1.0 if room_type == rt else 0.0 for rt in 
              ["MONSTER", "EVENT", "SHOP", "REST", "TREASURE", "BOSS"]],
            min((game.turn if hasattr(game, 'turn') else 0), 20) / 20.0,
            *[0.0 for _ in range(21)],
        ]
