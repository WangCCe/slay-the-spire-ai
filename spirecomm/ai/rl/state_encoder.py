"""
State encoder - FIXED VERSION (781 dims)
"""
import hashlib
import re
import numpy as np
from typing import List, Tuple
from spirecomm.ai.heuristics.card_costs import raw_card_cost
from spirecomm.ai.heuristics.card_names import canonical_card_name
from spirecomm.ai.heuristics.card_types import card_requires_target, card_type_name
from spirecomm.ai.heuristics.card_upgrades import is_card_upgraded
from spirecomm.spire.game import Game
from spirecomm.spire.identifiers import potion_id, relic_id
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster, PlayerClass, Intent
from spirecomm.ai.intent_utils import intent_is_attack, intent_tokens

_UPGRADE_SUFFIX_RE = re.compile(r'\+\d*$')


class StateEncoder:
    CARD_REWARD_MAX_OPTIONS = 3
    CARD_REWARD_FEATURES_PER_CARD = 15  # Increased from 12 to 15 (added exhausts, card_id_hash, magic_number)
    FUTURE_RESERVED_SIZE = 128

    def __init__(self):
        self.feature_dim = 781  # UNCHANGED - using reserved space for new features

    def encode(self, game: Game) -> np.ndarray:
        features = []
        features.extend(self._encode_player_state(game))
        features.extend(self._encode_hand_cards(game))
        features.extend(self._encode_deck_composition(game))
        features.extend(self._encode_monster_states(game))
        features.extend(self._encode_relics(game))
        features.extend(self._encode_potions(game))
        features.extend(self._encode_context(game))
        features.extend(self._encode_player_powers(game))
        features.extend(self._encode_orbs(game))
        features.extend(self._encode_combat_piles(game))
        features.extend(self._encode_screen_meta(game))
        features.extend(self._encode_choice_buckets(game))
        features.extend(self._encode_future_reserved(game))
        return np.array(features, dtype=np.float32)

    def _encode_player_state(self, game: Game) -> List[float]:
        if game.player is None:
            return [0.0] * 20
        player = game.player
        import math
        strength = self._get_power_amount(getattr(player, 'powers', []), "Strength")
        dexterity = self._get_power_amount(getattr(player, 'powers', []), "Dexterity")
        player_class = self._player_class_name(game.character or PlayerClass.IRONCLAD)
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
            1.0 if player_class == 'IRONCLAD' else 0.0,
            1.0 if player_class == 'THE_SILENT' else 0.0,
            1.0 if player_class == 'DEFECT' else 0.0,
            0.0,  # Placeholder for 4th class (Watcher)
            min(strength, 10) / 10.0,
            min(dexterity, 10) / 10.0,
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
        damage, block = self._extract_card_damage_block(card)

        normalized_card_type = card_type_name(card)

        card_id_hash = 0.0
        card_key = self._card_hash_key(card)
        if card_key is not None:
            card_id_hash = self._stable_hash(card_key, 100) / 100.0

        card_name = canonical_card_name(card)
        weak_cards = {"Clothesline", "Uppercut", "Shockwave"}
        vulnerable_cards = {"Bash", "Uppercut", "Shockwave", "Thunderclap"}

        return [
            card_id_hash,
            min(raw_card_cost(card), 3) / 3.0,
            min(damage, 30) / 30.0,
            min(block, 20) / 20.0,
            1.0 if normalized_card_type == 'ATTACK' else 0.0,
            1.0 if normalized_card_type == 'SKILL' else 0.0,
            1.0 if normalized_card_type == 'POWER' else 0.0,
            1.0 if normalized_card_type in ('STATUS', 'CURSE') else 0.0,
            1.0 if is_card_upgraded(card) else 0.0,
            0.0,  # is_ethereal (not exposed)
            1.0 if (hasattr(card, 'exhausts') and card.exhausts) else 0.0,
            0.0,  # has_retain (not exposed)
            1.0 if card_requires_target(card) else 0.0,
            1.0 if card_name in weak_cards else 0.0,
            1.0 if card_name in vulnerable_cards else 0.0,
        ]

    @staticmethod
    def _card_rarity_name(rarity) -> str:
        if rarity is None:
            return ''
        if hasattr(rarity, 'name'):
            return str(rarity.name).upper()
        value = str(rarity).upper()
        if value.startswith('CARDRARITY.'):
            return value.split('.', 1)[1]
        return value

    @staticmethod
    def _player_class_name(player_class) -> str:
        if player_class is None:
            return ''
        if hasattr(player_class, 'name'):
            return str(player_class.name).upper()
        value = str(player_class).upper()
        if value.startswith('PLAYERCLASS.'):
            return value.split('.', 1)[1]
        return value

    def _encode_deck_composition(self, game: Game) -> List[float]:
        counts = [0.0] * 120
        cards = game.deck if game.deck else []
        if not cards:
            cards = []
            if game.draw_pile:
                cards.extend(game.draw_pile)
            if game.discard_pile:
                cards.extend(game.discard_pile)
            if game.hand:
                cards.extend(game.hand)
        for card in cards:
            card_key = self._card_hash_key(card)
            if card_key is None:
                continue
            idx = self._stable_hash(card_key, 120)
            counts[idx] = min(counts[idx] + 1.0, 5.0)
        return [count / 5.0 for count in counts]

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
        max_hp = self._safe_float(getattr(monster, 'max_hp', 0.0), default=0.0)
        current_hp = self._safe_float(getattr(monster, 'current_hp', 0.0), default=0.0)
        hp_norm = current_hp / max_hp if max_hp > 0 else 0.0
        intent_flags = self._encode_intent(monster.intent if hasattr(monster, 'intent') else Intent.UNKNOWN)
        move_damage = self._safe_float(getattr(monster, 'move_adjusted_damage', 0), default=0.0)
        move_hits = self._safe_float(getattr(monster, 'move_hits', 0), default=0.0)
        strength = self._get_power_amount(getattr(monster, 'powers', []), "Strength")
        weak = self._get_power_amount(getattr(monster, 'powers', []), "Weak")
        frail = self._get_power_amount(getattr(monster, 'powers', []), "Frail")
        vulnerable = self._get_power_amount(getattr(monster, 'powers', []), "Vulnerable")
        poison = self._get_power_amount(getattr(monster, 'powers', []), "Poison")
        artifact = self._get_power_amount(getattr(monster, 'powers', []), "Artifact")
        metallicize = self._get_power_amount(getattr(monster, 'powers', []), "Metallicize")
        regen = self._get_power_amount(getattr(monster, 'powers', []), "Regeneration")
        move_id = max(self._safe_int(getattr(monster, 'move_id', -1)), 0)
        last_move_id = max(self._safe_int(getattr(monster, 'last_move_id', -1)), 0)
        second_last_move_id = max(self._safe_int(getattr(monster, 'second_last_move_id', -1)), 0)
        return [
            self._stable_hash(getattr(monster, 'monster_id', getattr(monster, 'name', 'Unknown')), 60) / 60.0,
            hp_norm,
            min(math.log10(max_hp + 1) / 2.5, 1.0),
            min(self._safe_float(getattr(monster, 'block', 0.0), default=0.0), 20) / 20.0,
            *intent_flags,
            min(move_damage, 50) / 50.0,
            min(move_hits, 5) / 5.0,
            0.0,  # intent block (not exposed)
            min(strength, 20) / 20.0,
            min(weak, 5) / 5.0,
            min(frail, 5) / 5.0,
            min(vulnerable, 5) / 5.0,
            min(poison, 20) / 20.0,
            min(artifact, 5) / 5.0,
            min(metallicize, 10) / 10.0,
            min(regen, 10) / 10.0,
            min(move_id, 50) / 50.0,
            min(last_move_id, 50) / 50.0,
            min(second_last_move_id, 50) / 50.0,
            1.0 if getattr(monster, 'is_gone', False) else 0.0,
            1.0 if getattr(monster, 'is_minion', False) else 0.0,
            1.0 if getattr(monster, 'half_dead', False) else 0.0,
            0.0, 0.0, 0.0, 0.0,
        ]

    def _encode_relics(self, game: Game) -> List[float]:
        relics = [0.0] * 89
        for relic in game.relics if game.relics else []:
            relic_key = relic_id(relic)
            if relic_key is None:
                continue
            idx = self._stable_hash(relic_key, 89)
            relics[idx] = 1.0
        return relics

    def _encode_potions(self, game: Game) -> List[float]:
        potions = game.potions if game.potions else []
        features = []
        for i in range(5):
            if i < len(potions):
                # Safely get potion name/id
                potion = potions[i]
                potion_key = potion_id(potion)
                if potion_key == "Potion Slot":
                    features.extend([0.0, 0.0, 0.0])
                    continue

                # Check if potion is a primitive type (number) or object
                if isinstance(potion, (int, float, np.integer, np.floating)):
                    # It's a number, use it directly
                    potion_hash = abs(int(potion)) % 30 / 30.0
                    can_use = 0.0
                elif hasattr(potion, 'potion_id'):
                    potion_hash = self._stable_hash(potion.potion_id, 30) / 30.0
                    can_use = 1.0 if getattr(potion, 'can_use', False) else 0.0
                elif hasattr(potion, 'name'):
                    potion_hash = self._stable_hash(potion.name, 30) / 30.0
                    can_use = 1.0 if getattr(potion, 'can_use', False) else 0.0
                elif hasattr(potion, 'id'):
                    potion_hash = self._stable_hash(potion.id, 30) / 30.0
                    can_use = 1.0 if getattr(potion, 'can_use', False) else 0.0
                else:
                    # Convert to string safely
                    try:
                        potion_hash = self._stable_hash(str(potion), 30) / 30.0
                    except Exception:
                        potion_hash = 0.0
                    can_use = 0.0

                features.extend([potion_hash, 1.0, can_use])
            else:
                features.extend([0.0] * 3)
        return features

    def _encode_context(self, game: Game) -> List[float]:
        from spirecomm.spire.screen import ScreenType

        room_type = game.room_type if game.room_type else "MONSTER"
        screen_type = getattr(game, 'screen_type', None)
        combat_screen = game.in_combat and screen_type in (None, ScreenType.NONE)
        combat_reward = screen_type == ScreenType.COMBAT_REWARD
        hand_select = screen_type == ScreenType.HAND_SELECT
        grid_select = screen_type == ScreenType.GRID
        event_screen = screen_type == ScreenType.EVENT
        shop_screen = screen_type in (ScreenType.SHOP_ROOM, ScreenType.SHOP_SCREEN)
        map_screen = screen_type == ScreenType.MAP
        rest_screen = screen_type == ScreenType.REST
        other_screen = not any(
            [
                combat_screen,
                combat_reward,
                hand_select,
                grid_select,
                event_screen,
                shop_screen,
                map_screen,
                rest_screen,
            ]
        )
        choice_size = len(game.choice_list) if game.choice_list else 0
        num_required = getattr(game.screen, 'num_cards', 0) if hasattr(game, 'screen') else 0
        selected_cards = getattr(game.screen, 'selected_cards', []) if hasattr(game, 'screen') else []
        can_confirm = 1.0 if getattr(game, 'proceed_available', False) else 0.0
        if hand_select and hasattr(game.screen, 'can_pick_zero'):
            if game.screen.can_pick_zero:
                can_confirm = 1.0
        if hand_select and num_required and len(selected_cards) >= num_required:
            can_confirm = 1.0
        if grid_select and getattr(game.screen, 'confirm_up', False):
            can_confirm = 1.0
        available = getattr(game, "available_commands", []) or []
        available_set = {str(cmd).lower() for cmd in available}

        return [
            *[1.0 if room_type == rt else 0.0 for rt in
              ["MONSTER", "EVENT", "SHOP", "REST", "TREASURE", "BOSS"]],
            min((game.turn if hasattr(game, 'turn') else 0), 20) / 20.0,
            1.0 if combat_screen else 0.0,
            1.0 if combat_reward else 0.0,
            1.0 if hand_select else 0.0,
            1.0 if grid_select else 0.0,
            1.0 if event_screen else 0.0,
            1.0 if shop_screen else 0.0,
            1.0 if map_screen else 0.0,
            1.0 if rest_screen else 0.0,
            1.0 if other_screen else 0.0,
            1.0 if game.choice_available else 0.0,
            min(choice_size, 10) / 10.0,
            min(num_required, 5) / 5.0,
            min(len(selected_cards), 5) / 5.0,
            can_confirm,
            1.0 if getattr(game, 'cancel_available', False) else 0.0,
            1.0 if getattr(game, 'proceed_available', False) else 0.0,
            min(len(game.hand) if game.hand else 0, 10) / 10.0,
            min((game.player.energy if game.player else 0), 5) / 5.0,
            min(max((game.player.energy if game.player else 0), 3), 5) / 5.0,
            1.0 if "confirm" in available_set else 0.0,
            1.0 if "proceed" in available_set else 0.0,
            1.0 if "cancel" in available_set else 0.0,
            1.0 if "choose" in available_set else 0.0,
            1.0 if "click" in available_set else 0.0,
            1.0 if "key" in available_set else 0.0,
            min(len(available_set), 10) / 10.0,
        ]

    def _encode_player_powers(self, game: Game) -> List[float]:
        if game.player is None:
            return [0.0] * 12
        player = game.player
        weak = self._get_power_amount(getattr(player, 'powers', []), "Weak")
        vulnerable = self._get_power_amount(getattr(player, 'powers', []), "Vulnerable")
        frail = self._get_power_amount(getattr(player, 'powers', []), "Frail")
        poison = self._get_power_amount(getattr(player, 'powers', []), "Poison")
        artifact = self._get_power_amount(getattr(player, 'powers', []), "Artifact")
        plated_armor = self._get_power_amount(getattr(player, 'powers', []), "Plated Armor")
        intangible = self._get_power_amount(getattr(player, 'powers', []), "Intangible")
        buffer = self._get_power_amount(getattr(player, 'powers', []), "Buffer")
        metallicize = self._get_power_amount(getattr(player, 'powers', []), "Metallicize")
        regen = self._get_power_amount(getattr(player, 'powers', []), "Regeneration")
        ritual = self._get_power_amount(getattr(player, 'powers', []), "Ritual")
        thorns = self._get_power_amount(getattr(player, 'powers', []), "Thorns")
        return [
            min(weak, 5) / 5.0,
            min(vulnerable, 5) / 5.0,
            min(frail, 5) / 5.0,
            min(poison, 30) / 30.0,
            min(artifact, 5) / 5.0,
            min(plated_armor, 20) / 20.0,
            min(intangible, 5) / 5.0,
            min(buffer, 5) / 5.0,
            min(metallicize, 20) / 20.0,
            min(regen, 20) / 20.0,
            min(ritual, 20) / 20.0,
            min(thorns, 20) / 20.0,
        ]

    def _encode_orbs(self, game: Game) -> List[float]:
        if game.player is None:
            return [0.0] * 16
        orbs = getattr(game.player, 'orbs', []) or []
        features = []
        for i in range(4):
            if i < len(orbs):
                orb = orbs[i]
                orb_id = getattr(orb, 'orb_id', None) or getattr(orb, 'name', None)
                orb_hash = self._stable_hash(orb_id, 20) / 20.0 if orb_id else 0.0
                evoke_amount = self._safe_float(getattr(orb, 'evoke_amount', 0.0), default=0.0)
                passive_amount = self._safe_float(getattr(orb, 'passive_amount', 0.0), default=0.0)
                features.extend([
                    orb_hash,
                    min(evoke_amount, 20) / 20.0,
                    min(passive_amount, 20) / 20.0,
                    0.0,
                ])
            else:
                features.extend([0.0, 0.0, 0.0, 1.0])
        return features

    def _encode_combat_piles(self, game: Game) -> List[float]:
        exhaust_size = len(game.exhaust_pile) if game.exhaust_pile else 0
        limbo_size = len(game.limbo) if game.limbo else 0
        discarded = getattr(game, 'cards_discarded_this_turn', 0) or 0
        card_in_play = getattr(game, 'card_in_play', None)
        card_in_play_id = getattr(card_in_play, 'card_id', None) if card_in_play else None
        if card_in_play_id is None and card_in_play is not None:
            card_in_play_id = getattr(card_in_play, 'name', None)
        if card_in_play_id is None and card_in_play is not None:
            card_in_play_id = getattr(card_in_play, 'id', None)
        card_in_play_hash = self._stable_hash(card_in_play_id, 50) / 50.0 if card_in_play_id else 0.0

        potions = game.potions if game.potions else []
        real_potions = [p for p in potions if potion_id(p) != "Potion Slot"]
        empty_slots = len(potions) - len(real_potions)
        potions_full = 1.0 if hasattr(game, 'are_potions_full') and game.are_potions_full() else 0.0
        potion_available = 1.0 if getattr(game, 'potion_available', False) else 0.0

        return [
            min(exhaust_size, 30) / 30.0,
            min(limbo_size, 10) / 10.0,
            min(discarded, 10) / 10.0,
            card_in_play_hash,
            min(len(real_potions), 5) / 5.0,
            min(empty_slots, 5) / 5.0,
            potions_full,
            potion_available,
        ]

    def _encode_screen_meta(self, game: Game) -> List[float]:
        from spirecomm.spire.game import RoomPhase

        room_phase = getattr(game, 'room_phase', None)
        screen_up = 1.0 if getattr(game, 'screen_up', False) else 0.0
        play_available = 1.0 if getattr(game, 'play_available', False) else 0.0
        end_available = 1.0 if getattr(game, 'end_available', False) else 0.0
        act_boss = getattr(game, 'act_boss', None)
        act_boss_hash = self._stable_hash(act_boss, 20) / 20.0 if act_boss else 0.0

        return [
            1.0 if room_phase == RoomPhase.COMBAT else 0.0,
            1.0 if room_phase == RoomPhase.EVENT else 0.0,
            1.0 if room_phase == RoomPhase.COMPLETE else 0.0,
            1.0 if room_phase == RoomPhase.INCOMPLETE else 0.0,
            screen_up,
            play_available,
            end_available,
            act_boss_hash,
        ]

    def _encode_choice_buckets(self, game: Game) -> List[float]:
        buckets = [0.0] * 32
        choices = game.choice_list if game.choice_list else []
        for choice in choices:
            key = str(choice)
            idx = self._stable_hash(key, 32)
            buckets[idx] = min(buckets[idx] + 1.0, 3.0)
        return [val / 3.0 for val in buckets]

    def _encode_future_reserved(self, game: Game) -> List[float]:
        reserved = [0.0] * self.FUTURE_RESERVED_SIZE
        card_reward_features = self._encode_card_reward_options(game)
        if card_reward_features:
            reserved[:len(card_reward_features)] = card_reward_features
        return reserved

    def _encode_card_reward_options(self, game: Game) -> List[float]:
        from spirecomm.spire.screen import ScreenType

        total = self.CARD_REWARD_FEATURES_PER_CARD * self.CARD_REWARD_MAX_OPTIONS
        if getattr(game, 'screen_type', None) != ScreenType.CARD_REWARD:
            return [0.0] * total

        screen = getattr(game, 'screen', None)
        candidates = getattr(screen, 'cards', None) if screen else None
        if not candidates:
            return [0.0] * total

        features = []
        for i in range(self.CARD_REWARD_MAX_OPTIONS):
            if i < len(candidates):
                features.extend(self._encode_card_reward_card(candidates[i]))
            else:
                features.extend([0.0] * self.CARD_REWARD_FEATURES_PER_CARD)
        return features

    def _encode_card_reward_card(self, card: Card) -> List[float]:
        damage, block = self._extract_card_damage_block(card)
        cost = getattr(card, 'cost_for_turn', None)
        if cost is None:
            cost = getattr(card, 'cost', 0)
        cost = self._safe_int(cost, default=0)

        normalized_card_type = card_type_name(card)
        type_flags = [0.0, 0.0, 0.0, 0.0]
        if normalized_card_type == 'ATTACK':
            type_flags[0] = 1.0
        elif normalized_card_type == 'SKILL':
            type_flags[1] = 1.0
        elif normalized_card_type == 'POWER':
            type_flags[2] = 1.0
        elif normalized_card_type in ('STATUS', 'CURSE'):
            type_flags[3] = 1.0

        rarity = getattr(card, 'rarity', None)
        rarity_name = self._card_rarity_name(rarity)
        rarity_flags = [0.0, 0.0, 0.0, 0.0]
        if rarity_name == 'BASIC':
            rarity_flags[0] = 1.0
        elif rarity_name == 'COMMON':
            rarity_flags[1] = 1.0
        elif rarity_name == 'UNCOMMON':
            rarity_flags[2] = 1.0
        elif rarity_name == 'RARE':
            rarity_flags[3] = 1.0

        upgrades_flag = 1.0 if is_card_upgraded(card) else 0.0
        exhausts_flag = 1.0 if getattr(card, 'exhausts', False) else 0.0

        # NEW: Add card ID hash to let network learn card-specific patterns
        card_id_hash = 0.0
        card_key = self._card_hash_key(card)
        if card_key:
            card_id_hash = self._stable_hash(card_key, 500) / 500.0

        # NEW: Extract magic number (skill values) from properties
        magic_number = 0.0
        if hasattr(card, 'properties') and card.properties:
            try:
                for prop in card.properties:
                    if hasattr(prop, 'magic_number'):
                        magic_number = min(abs(getattr(prop, 'magic_number', 0)), 20) / 20.0
                        break
            except:
                pass

        return [
            min(cost, 3) / 3.0,
            *type_flags,
            *rarity_flags,
            min(damage, 30) / 30.0,
            min(block, 20) / 20.0,
            upgrades_flag,
            exhausts_flag,  # NEW: Exhaust cards are powerful
            card_id_hash,  # NEW: Let network learn card-specific value
            magic_number,  # NEW: Skill effect magnitude
        ]

    @staticmethod
    def _extract_card_damage_block(card: Card) -> Tuple[float, float]:
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

        return damage, block

    @staticmethod
    def _card_hash_key(card: Card):
        card_id = getattr(card, 'card_id', None)
        if card_id is None:
            card_id = getattr(card, 'name', None)
        if card_id is None:
            card_id = getattr(card, 'id', None)
        if card_id is None:
            return None
        return _UPGRADE_SUFFIX_RE.sub('', str(card_id))

    @staticmethod
    def _stable_hash(value, modulo):
        encoded = str(value).encode('utf-8')
        digest = hashlib.md5(encoded).hexdigest()
        return int(digest, 16) % modulo

    @staticmethod
    def _safe_int(value, default=-1):
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_float(value, default=0.0):
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _get_power_amount(powers, power_id):
        for power in powers or []:
            if getattr(power, 'power_id', None) == power_id:
                return power.amount
            if getattr(power, 'power_name', None) == power_id:
                return power.amount
        return 0

    @staticmethod
    def _encode_intent(intent):
        tokens = intent_tokens(intent)
        if intent_is_attack(intent):
            return [1.0, 0.0, 0.0, 0.0, 0.0]
        if "DEFEND" in tokens:
            return [0.0, 1.0, 0.0, 0.0, 0.0]
        if "BUFF" in tokens:
            return [0.0, 0.0, 1.0, 0.0, 0.0]
        if "DEBUFF" in tokens:
            return [0.0, 0.0, 0.0, 1.0, 0.0]
        return [0.0, 0.0, 0.0, 0.0, 1.0]
