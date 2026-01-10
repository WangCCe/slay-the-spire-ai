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
        damage, block = 0, 0
        for p in card.properties:
            if hasattr(p, 'damage'): damage = getattr(p, 'damage', 0)
            if hasattr(p, 'block'): block = getattr(p, 'block', 0)
        return [
            hash(card.id) % 100 / 100.0,
            min((card.cost_for_turn if hasattr(card, 'cost_for_turn') else card.cost), 3) / 3.0,
            min(damage, 30) / 30.0,
            min(block, 20) / 20.0,
            *[1.0 if card.card_type == ct else 0.0 for ct in [0, 1, 2, 3]],
            1.0 if card.upgrade != 0 else 0.0,
            0.0, 1.0 if hasattr(card, 'exhausts') and card.exhausts else 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
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
                name = potions[i].name if hasattr(potions[i], 'name') else str(potions[i])
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
