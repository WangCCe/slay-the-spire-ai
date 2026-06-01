"""
Base interfaces and classes for the decision framework.

This module defines the foundational abstractions used throughout the optimized AI system.
All decision components inherit from these base classes to ensure consistency and
enable easy testing/mocking.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from spirecomm.spire.game import Game
from spirecomm.spire.card import Card
from spirecomm.spire.character import Monster
from spirecomm.communication.action import Action
from spirecomm.ai.intent_utils import (
    intent_tokens,
    intent_is_attack,
    intent_is_unknown,
    monster_intends_attack,
)
from spirecomm.ai.incoming_damage import (
    known_unknown_move_has_no_immediate_damage,
    known_unknown_move_immediate_damage,
)
from spirecomm.ai.monster_names import canonical_live_monster_name
from spirecomm.data.loader import game_data_loader


class DecisionContext:
    """
    Encapsulates all context needed for decision making.

    This class pre-computes expensive metrics once and makes them available
    to all decision components, ensuring consistency and efficiency.

    Attributes:
        game: The current game state
        player_hp_pct: Player's HP as percentage (0-1)
        energy_available: Current energy
        incoming_damage: Total damage from monsters this turn
        monsters_alive: List of alive monsters (not gone/half_dead)
        deck_archetype: Detected deck archetype ('poison', 'strength', 'block', etc.)
        card_synergies: Dictionary of synergy scores
        turn: Current turn number
        floor: Current floor number
        act: Current act number
    """

    def __init__(self, game: Game):
        self.game = game
        self.game_id = getattr(game, 'game_id', None)
        
        # Player stats - check if player exists
        if hasattr(game, 'current_hp') and hasattr(game, 'max_hp') and game.max_hp > 0:
            self.player_hp = game.current_hp
            self.player_max_hp = game.max_hp
            self.player_hp_pct = max(0, game.current_hp / max(game.max_hp, 1))
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("[DecisionContext] Game missing HP attributes, using defaults")
            self.player_hp = 80  # Default HP
            self.player_max_hp = 80
            self.player_hp_pct = 1.0  # Default to full HP

        if hasattr(game, 'player') and game.player is not None:
            self.energy_available = game.player.energy if hasattr(game.player, 'energy') else 3
        else:
            self.energy_available = 3  # Default energy

        self.turn = game.turn if hasattr(game, 'turn') else 1
        self.floor = game.floor if hasattr(game, 'floor') else 0
        self.act = game.act if hasattr(game, 'act') else 1

        # Combat state
        self.incoming_damage = self._calculate_incoming_damage()
        self.monsters_alive = [
            m for m in game.monsters
            if not m.is_gone and not m.half_dead and m.current_hp > 0
        ] if hasattr(game, 'monsters') else []

        # Deck analysis - dynamically import DeckAnalyzer to avoid circular imports
        try:
            from spirecomm.ai.heuristics.deck import DeckAnalyzer
            analyzer = DeckAnalyzer()
            
            # Use DeckAnalyzer to get deck archetype
            self.deck_archetype = analyzer.get_archetype(self)
            
            # Calculate synergies using enhanced method
            # First get archetype scores
            archetype_scores = analyzer.get_archetype_score(self)
            self.archetype_scores = archetype_scores  # Save for access by evaluators
            self.archetype_score = max(archetype_scores.values()) if archetype_scores else 0.0  # Max score as confidence

            # Initialize synergies dictionary
            self.card_synergies = {
                'poison': archetype_scores.get('poison', 0.0) * 0.7,
                'strength': archetype_scores.get('strength', 0.0) * 0.7,
                'draw': archetype_scores.get('draw', 0.0) * 0.7,
                'exhaust': archetype_scores.get('exhaust', 0.0) * 0.7,
                'block': archetype_scores.get('block', 0.0) * 0.7,
                'vulnerable': 0.0,
                'weak': 0.0,
                'scaling': archetype_scores.get('scaling', 0.0) * 0.7,
                'storm': archetype_scores.get('storm', 0.0) * 0.7,
                'heal': archetype_scores.get('heal', 0.0) * 0.7,
                'malice': archetype_scores.get('malice', 0.0) * 0.7,
                'combo': archetype_scores.get('combo', 0.0) * 0.7
            }
        except ImportError as e:
            # Fall back to original methods if DeckAnalyzer is not available
            self.deck_archetype = self._analyze_deck_archetype()
            self.card_synergies = self._calculate_synergies()
            # Set default values for archetype scores
            self.archetype_scores = {}
            self.archetype_score = 0.0

        # Hand analysis
        self.hand_size = len(game.hand) if hasattr(game, 'hand') else 0
        self.playable_cards = [
            c for c in game.hand
            if hasattr(c, 'is_playable') and c.is_playable
        ] if hasattr(game, 'hand') else []

        # === 新增：遗物检测 ===
        self.has_snecko_eye = self._has_relic("Snecko Eye")
        self.has_burning_blood = self._has_relic("Burning Blood")

        # === TIMING AWARENESS ===
        # Timing context for dynamic offensive/defensive balance
        # Set externally by TurnTimingClassifier
        self.timing_context = None  # Type: Optional[TimingContext]
        self.has_busted_clock = self._has_relic("Busted Clock")
        self.has_orichalcum = self._has_relic("Orichalcum")
        self.has_paper_crane = self._has_relic("Paper Crane")

        # === 新增：玩家 Power 追踪 ===
        self.strength = self._get_player_power_amount("Strength")
        self.dexterity = self._get_player_power_amount("Dexterity")
        self.vulnerable_stacks = {}  # monster_index -> stacks
        self.weak_stacks = {}  # monster_index -> stacks
        self.frail_stacks = {}  # monster_index -> stacks
        self.thorns_stacks = {}  # monster_index -> stacks

        # 为每个怪物初始化 debuff 追踪（使用索引作为 key）
        for i, monster in enumerate(self.monsters_alive):
            self.vulnerable_stacks[i] = self._get_monster_power_amount(monster, "Vulnerable")
            self.weak_stacks[i] = self._get_monster_power_amount(monster, "Weak")
            self.frail_stacks[i] = self._get_monster_power_amount(monster, "Frail")
            thorns = self._get_monster_power_amount(monster, "Thorns")
            sharp_hide = self._get_monster_power_amount(monster, "Sharp Hide")
            self.thorns_stacks[i] = max(thorns, sharp_hide)

        # === 新增：战斗评估 ===
        self.can_end_combat_this_turn = False  # 将由 CombatEndingDetector 计算

        # === 新增：威胁检测 ===
        # Create threat profiler and analyze enemy threat level
        self.threat_profiler = EnemyThreatProfiler()
        self.threat_category = self.threat_profiler.analyze_threat(self.monsters_alive)

        # Convenience property: is this an elite/scaling fight?
        self.is_elite_fight = self.threat_category in [ThreatCategory.ELITE, ThreatCategory.SCALING]

    @staticmethod
    def _positive_move_hits(monster) -> int:
        try:
            return max(1, int(getattr(monster, 'move_hits', 1) or 1))
        except (TypeError, ValueError):
            return 1

    @classmethod
    def _move_damage_contribution(cls, monster) -> int:
        damage = getattr(monster, 'move_adjusted_damage', None)
        if damage is None:
            return 0
        try:
            return max(0, int(damage)) * cls._positive_move_hits(monster)
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _should_count_immediate_damage(cls, monster) -> bool:
        return monster_intends_attack(monster)

    def _calculate_incoming_damage(self) -> int:
        """Calculate total incoming damage from all monsters.

        Only counts damage from monsters with ATTACK intents.
        Monsters with non-attack intents (DEBUG, DEFEND, BUFF, etc.) are ignored.
        """
        if not hasattr(self.game, 'monsters'):
            return 0

        total = 0
        for monster in self.game.monsters:
            if (
                not getattr(monster, 'is_gone', False)
                and not getattr(monster, 'half_dead', False)
                and getattr(monster, 'current_hp', 1) > 0
            ):
                intent = getattr(monster, 'intent', None)

                if intent_is_unknown(intent):
                    known_damage = known_unknown_move_immediate_damage(monster)
                    if known_damage > 0:
                        total += known_damage
                        continue
                    if known_unknown_move_has_no_immediate_damage(monster):
                        continue
                    total += 5 * self.act
                    continue

                # Calculate damage from attacking monsters
                if (
                    intent_is_attack(intent)
                    and hasattr(monster, 'move_adjusted_damage')
                    and monster.move_adjusted_damage is not None
                ):
                    total += self._move_damage_contribution(monster)
        return total

    def _compute_base_immediate_threat(self, monster) -> int:
        """
        Calculate base immediate threat from current monster state.

        Shared logic between compute_threat() and compute_threat_v2().

        Args:
            monster: Monster to evaluate

        Returns:
            Base threat score from immediate damage and strength
        """
        threat = 0
        if (
            self._should_count_immediate_damage(monster)
            and hasattr(monster, 'move_adjusted_damage')
            and monster.move_adjusted_damage is not None
        ):
            hits = self._positive_move_hits(monster)
            threat += self._move_damage_contribution(monster)

            # Add current Strength to damage
            if hasattr(monster, 'strength') and monster.strength > 0:
                threat += monster.strength * hits
        return threat

    def compute_threat(self, monster) -> int:
        """
        Calculate the threat level of a monster for targeting decisions.

        Higher threat means the monster should be prioritized for:
        - Killing (can be defeated this turn)
        - Debuffing (apply Vulnerable/Weak to reduce incoming damage)
        - High-priority targeting (focus damage on most dangerous enemy)

        Threat components:
        - Expected damage next turn (from move_adjusted_damage)
        - Debuff threat (applies Weak/Vulnerable: +10)
        - Scaling threat (buffs/growth over time: +15)
        - AOE threat (buffs other monsters: +8)

        Args:
            monster: Monster to evaluate

        Returns:
            Threat score (higher = more threatening)
        """
        threat = self._compute_base_immediate_threat(monster)

        # Import Intent enum for comparison
        try:
            from spirecomm.spire.character import Intent
            intent_type = monster.intent if hasattr(monster, 'intent') else None
        except:
            intent_type = None

        # 2. Debuff threat (Weak/Vulnerable are dangerous)
        if intent_type:
            current_intent_tokens = intent_tokens(intent_type)

            # Check if monster applies debuffs
            if (
                'DEBUFF' in current_intent_tokens
                or 'WEAK' in current_intent_tokens
                or 'VULNERABLE' in current_intent_tokens
            ):
                threat += 10  # Debuff application is high threat

        # 3. Scaling threat (elite/boss monsters that grow stronger)
        name = canonical_live_monster_name(monster).lower()
        if name:
            # Known scaling monsters
            scaling_monsters = [
                'gremlin nob', 'gremlin thief', 'gremlin face',
                'slaver', 'sentry', 'hexaghost', 'champ',
                'the guardian', 'bronze automaton',
                'the collector', 'awakened one',
                'reptomancer', 'centurion', 'healer'
            ]
            if any(scaling_name in name for scaling_name in scaling_monsters):
                threat += 15  # Scaling threat

            # Boss threat (Act bosses are very dangerous)
            if 'boss' in name or any(boss in name for boss in ['hexaghost', 'slime boss', 'the guardian']):
                threat += 20  # Extra threat for bosses

        # 4. AOE threat (buffs other monsters)
        if intent_type:
            if 'BUFF' in intent_tokens(intent_type):
                threat += 8  # Buffing allies is threatening

        # 5. High HP threat (more HP = more dangerous if left alive)
        if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp'):
            hp_ratio = monster.current_hp / max(monster.max_hp, 1)
            if hp_ratio > 0.5:  # Monster above 50% HP
                threat += int(hp_ratio * 5)  # Up to +5 for high HP

        return threat

    def compute_threat_v2(self, monster) -> int:
        """
        Calculate enhanced threat level using Wiki monster data for proactive threat assessment.

        This enhanced version incorporates:
        - Immediate threat (current intent damage)
        - Future threat (predicted next 2-3 moves from Wiki patterns)
        - Scaling threat (from Wiki threat profiles)
        - Special ability threat (summoner, hibernation, phase change, etc.)
        - Composition threat (minions, party buffs)

        Args:
            monster: Monster to evaluate

        Returns:
            Enhanced threat score (higher = more threatening)
        """
        # Fallback to original method if monster identity is unavailable
        monster_name = canonical_live_monster_name(monster)
        if not monster_name:
            return self.compute_threat(monster)

        threat = 0

        # Get enhanced monster data from Wiki
        monster_data = game_data_loader.get_enhanced_monster_data(monster_name)

        # If no Wiki data, fallback to original method
        if not monster_data:
            return self.compute_threat(monster)

        # ===== Component 1: Immediate threat (current intent) =====
        threat += self._compute_base_immediate_threat(monster)
        current_intent_tokens = intent_tokens(getattr(monster, 'intent', None))
        if (
            'DEBUFF' in current_intent_tokens
            or 'WEAK' in current_intent_tokens
            or 'VULNERABLE' in current_intent_tokens
        ):
            threat += 10

        # ===== Component 2: Future threat (predict next 2-3 moves) =====
        # Get monster HP percentage for phase detection
        if hasattr(monster, 'current_hp') and hasattr(monster, 'max_hp') and monster.max_hp > 0:
            monster_hp_percent = monster.current_hp / monster.max_hp
        else:
            monster_hp_percent = 1.0

        # Get current Strength for scaling
        current_strength = getattr(monster, 'strength', 0)

        # Predict future moves using Wiki patterns
        predicted_moves = game_data_loader.predict_monster_moves(
            monster_name, self.turn, monster_hp_percent
        )

        # Add threat from predicted moves (discounted by 60% for uncertainty)
        for prediction in predicted_moves:
            move = prediction.get('move', {})
            confidence = prediction.get('confidence', 0.5)

            # Damage threat
            if 'damage' in move and move['damage']:
                hits = move.get('hits', 1)
                damage = move['damage'] * hits
                threat += int(damage * 0.6 * confidence)  # Discount future damage

            # Debuff threat
            if any(key in move for key in ['weak_applied', 'vulnerable_applied', 'frail_applied']):
                threat += int(3 * confidence)

            # Summon threat
            if 'summons' in move:
                threat += int(10 * confidence)

        # ===== Component 3: Scaling threat (from Wiki threat profile) =====
        threat_profile = game_data_loader.get_monster_threat_profile(monster_name)
        if threat_profile:
            scaling_threat = threat_profile.get('scaling_threat', 0)

            # Estimate turns to kill based on HP percentage
            if scaling_threat > 0:
                estimated_ttd = int(10 * monster_hp_percent)  # Rough estimate
                threat += int(scaling_threat * estimated_ttd * 0.3)

            # Strength scaling threat
            if current_strength > 0:
                strength_scaling = threat_profile.get('strength_scaling_threat', 4.0)
                threat += int(strength_scaling * current_strength)

        # ===== Component 4: Special ability threat =====
        special_mechanics = game_data_loader.get_monster_special_mechanics(monster_name)
        if special_mechanics:
            mech_type = special_mechanics.get('type', '')

            # Summoner threat (high priority to kill)
            if mech_type == 'summoner':
                summoning_threat = threat_profile.get('summoning_threat', 20) if threat_profile else 20
                threat += summoning_threat

                # Add minion threat
                minion_count = len([m for m in self.monsters_alive if m.name != monster_name])
                minion_threat = threat_profile.get('minion_threat', 10) if threat_profile else 10
                threat += minion_threat * minion_count

            # Hibernation threat (low while sleeping, high when awake)
            elif mech_type == 'hibernation':
                hibernation_turns = special_mechanics.get('hibernation_turns', 3)
                if self.turn <= hibernation_turns:
                    # Still sleeping - low threat
                    hibernation_threat = threat_profile.get('hibernation_threat', 5) if threat_profile else 5
                    threat = hibernation_threat  # Replace, not add
                else:
                    # Awakened - high threat
                    awakened_threat = threat_profile.get('awakened_threat', 40) if threat_profile else 40
                    threat += awakened_threat

            # Phase change threat
            elif mech_type == 'phase_change' or 'phases' in special_mechanics:
                # Determine current phase
                phases = special_mechanics.get('phases', [])
                current_phase = 1
                for phase in phases:
                    if 'hp_threshold' in phase:
                        if monster_hp_percent < (phase['hp_threshold'] / 100.0):
                            current_phase = phase.get('phase', 2)
                            break

                # Add phase-specific threat
                phase_threat_key = f'phase{current_phase}_threat'
                if threat_profile and phase_threat_key in threat_profile:
                    phase_threat = threat_profile[phase_threat_key]
                    threat += int(phase_threat * 0.5)  # Moderate weight for phase threat

            # Death split threat (prioritize AOE)
            elif mech_type == 'death_split':
                split_hp = special_mechanics.get('hp_threshold', 50)
                if monster_hp_percent < (split_hp / 100.0):
                    # About to split - high threat unless we have AOE
                    threat += 15

            # Charge attack threat
            elif mech_type == 'charge_attack':
                charge_threat = threat_profile.get('charge_threat', 25) if threat_profile else 25
                threat += charge_threat

            # Duo boss threat (both monsters scale together)
            elif mech_type == 'duo_boss':
                party_multiplier = threat_profile.get('party_threat_multiplier', 1.5) if threat_profile else 1.5
                threat = int(threat * party_multiplier)

        # ===== Component 5: Composition threat (party buffs) =====
        # Check if monster buffs other monsters
        if 'BUFF' in current_intent_tokens and len(self.monsters_alive) > 1:
            # Party-wide buff is more threatening with more monsters
            threat += len(self.monsters_alive) * 5

        # ===== Component 6: Base threat adjustment =====
        if threat_profile:
            base_threat = threat_profile.get('base_threat', 20)
            # Blend calculated threat with base threat (70% calculated, 30% base)
            threat = int(threat * 0.7 + base_threat * 0.3)

        return max(threat, 5)  # Minimum threat of 5

    def _analyze_deck_archetype(self) -> str:
        """
        Analyze deck to determine archetype.

        Returns:
            Archetype string: 'poison', 'strength', 'block', 'scaling', 'draw', 'balanced', 'unknown'
        """
        if not hasattr(self.game, 'deck') or not self.game.deck:
            return 'unknown'

        # Use game data to analyze deck archetype
        poison_count = 0
        strength_count = 0
        block_count = 0
        draw_count = 0
        scaling_count = 0
        card_count = len(self.game.deck)
        from spirecomm.ai.heuristics.card_names import card_data_key

        for card in self.game.deck:
            card_name = card_data_key(card)
            card_data = game_data_loader.get_card_data(card_name)
            
            if card_data:
                description = card_data.get('description', '').lower()
                card_type = card_data.get('type', '').lower()
                cost = card_data.get('cost', '0')
                
                # Count archetype-specific cards
                if 'poison' in description or 'catalyst' in card_name:
                    poison_count += 1
                
                if card_type == 'attack' and ('strength' in description or 'deal' in description):
                    strength_count += 1
                
                if card_type == 'skill' and ('block' in description or 'gain' in description):
                    block_count += 1
                
                if 'draw' in description or 'draw' in card_name:
                    draw_count += 1
                
                if any(keyword in description for keyword in ['strength', 'dexterity', 'poison', 'thorns']):
                    scaling_count += 1

        # Normalize counts to percentages
        if card_count > 0:
            poison_pct = poison_count / card_count
            strength_pct = strength_count / card_count
            block_pct = block_count / card_count
            draw_pct = draw_count / card_count
            scaling_pct = scaling_count / card_count
        else:
            return 'unknown'

        # Determine archetype based on dominant strategy
        if poison_pct > 0.2:  # More than 20% poison cards
            return 'poison'
        elif strength_pct > 0.3:  # More than 30% strength-based attack cards
            return 'strength'
        elif block_pct > 0.3:  # More than 30% block cards
            return 'block'
        elif scaling_pct > 0.25:  # More than 25% scaling cards
            return 'scaling'
        elif draw_pct > 0.25:  # More than 25% draw cards
            return 'draw'
        else:
            return 'balanced'  # No clear archetype

    def _calculate_synergies(self) -> Dict[str, float]:
        """
        Calculate synergy scores for different card interactions.

        Returns:
            Dictionary mapping synergy types to scores (0-1)
        """
        synergies = {
            'poison': 0.0,
            'strength': 0.0,
            'draw': 0.0,
            'exhaust': 0.0,
            'block': 0.0,
            'vulnerable': 0.0,
            'weak': 0.0,
            'scaling': 0.0
        }

        if not hasattr(self.game, 'deck') or not self.game.deck:
            return synergies

        deck_cards = self.game.deck
        card_count = len(deck_cards)
        max_synergy = card_count * 0.3  # Normalization factor

        # Track archetype-specific cards
        archetype_count = {
            'poison': 0,
            'strength': 0,
            'draw': 0,
            'exhaust': 0,
            'block': 0,
            'vulnerable': 0,
            'weak': 0,
            'scaling': 0
        }

        # First pass: count cards by archetype
        from spirecomm.ai.heuristics.card_names import card_data_key

        for card in deck_cards:
            card_name = card_data_key(card)
            card_data = game_data_loader.get_card_data(card_name)
            
            if card_data:
                description = card_data.get('description', '').lower()
                
                if 'poison' in description or 'noxious' in description:
                    archetype_count['poison'] += 1
                
                if 'strength' in description or 'gain' in description:
                    archetype_count['strength'] += 1
                
                if 'draw' in description or 'discard' in description:
                    archetype_count['draw'] += 1
                
                if 'exhaust' in description:
                    archetype_count['exhaust'] += 1
                
                if 'block' in description:
                    archetype_count['block'] += 1
                
                if 'vulnerable' in description:
                    archetype_count['vulnerable'] += 1
                
                if 'weak' in description:
                    archetype_count['weak'] += 1
                
                if any(keyword in description for keyword in ['strength', 'dexterity', 'poison', 'thorns']):
                    archetype_count['scaling'] += 1

        # Second pass: calculate synergies based on card combinations
        for i in range(len(deck_cards)):
            for j in range(i + 1, len(deck_cards)):
                card1 = deck_cards[i]
                card2 = deck_cards[j]
                
                card1_name = card_data_key(card1)
                card2_name = card_data_key(card2)
                
                card1_data = game_data_loader.get_card_data(card1_name)
                card2_data = game_data_loader.get_card_data(card2_name)
                
                if card1_data and card2_data:
                    desc1 = card1_data.get('description', '').lower()
                    desc2 = card2_data.get('description', '').lower()
                    
                    # Calculate synergies between specific card types
                    if ('poison' in desc1 and 'poison' in desc2) or ('catalyst' in card1_name and 'poison' in desc2):
                        synergies['poison'] += 0.05
                    
                    if ('strength' in desc1 and 'strength' in desc2) or ('strength' in desc1 and 'attack' in card2_data.get('type', '').lower()):
                        synergies['strength'] += 0.05
                    
                    if ('draw' in desc1 and 'draw' in desc2) or ('draw' in desc1 and 'discard' in desc2):
                        synergies['draw'] += 0.05
                    
                    if ('block' in desc1 and 'block' in desc2) or ('block' in desc1 and card2_data.get('type', '').lower() == 'power'):
                        synergies['block'] += 0.03
                    
                    if ('vulnerable' in desc1 and card2_data.get('type', '').lower() == 'attack'):
                        synergies['vulnerable'] += 0.04
                    
                    if ('weak' in desc1 and card2_data.get('type', '').lower() == 'attack'):
                        synergies['weak'] += 0.04

        # Normalize synergies to 0-1 range
        for key in synergies:
            synergies[key] = min(1.0, synergies[key] / max_synergy)

        return synergies

    def _has_relic(self, relic_id: str) -> bool:
        """
        Check if player has specific relic.

        Args:
            relic_id: The relic identifier (e.g., "Snecko Eye")

        Returns:
            True if player has this relic
        """
        if not hasattr(self.game, 'relics'):
            return False
        return any(self._relic_matches(relic, relic_id) for relic in self.game.relics)

    @staticmethod
    def _relic_matches(relic, relic_id: str) -> bool:
        if relic == relic_id:
            return True
        return any(
            getattr(relic, attr, None) == relic_id
            for attr in ('relic_id', 'name')
        )

    @staticmethod
    def _power_matches(power, power_id: str) -> bool:
        for attr in ('power_id', 'power_name', 'name'):
            if getattr(power, attr, None) == power_id:
                return True
        return False

    def _get_player_power_amount(self, power_id: str) -> int:
        """
        Get amount of specific player power.

        Args:
            power_id: The power identifier (e.g., "Strength")

        Returns:
            Amount of the power, or 0 if not found
        """
        if not hasattr(self.game, 'player') or not hasattr(self.game.player, 'powers'):
            return 0
        for power in self.game.player.powers:
            if self._power_matches(power, power_id):
                return power.amount if hasattr(power, 'amount') else 0
        return 0

    def _get_monster_power_amount(self, monster: Monster, power_id: str) -> int:
        """
        Get amount of specific monster power/debuff.

        Args:
            monster: The monster to check
            power_id: The power identifier (e.g., "Vulnerable")

        Returns:
            Amount of the power, or 0 if not found
        """
        if not hasattr(monster, 'powers'):
            return 0
        for power in monster.powers:
            if self._power_matches(power, power_id):
                return power.amount if hasattr(power, 'amount') else 0
        return 0

    def __repr__(self) -> str:
        return (f"DecisionContext(hp={self.player_hp_pct:.2f}, energy={self.energy_available}, "
                f"archetype={self.deck_archetype}, monsters={len(self.monsters_alive)})")


class DecisionEngine(ABC):
    """
    Base class for all decision components.

    All evaluators and planners inherit from this class, which provides
    a consistent interface for decision making.
    """

    @abstractmethod
    def evaluate(self, context: DecisionContext) -> Any:
        """
        Return evaluation score or decision.

        Args:
            context: The decision context containing game state

        Returns:
            Evaluation result (type varies by subclass)
        """
        pass

    @abstractmethod
    def get_confidence(self, context: DecisionContext) -> float:
        """
        Return confidence 0-1 in this decision.

        Higher confidence means the evaluator is more certain of its recommendation.
        This can be used for weighted voting or fallback strategies.

        Args:
            context: The decision context

        Returns:
            Confidence value between 0 and 1
        """
        pass


class CardEvaluator(DecisionEngine):
    """
    Evaluate card value in current context.

    Card evaluators assign a numeric score to cards based on their current
    strategic value, considering the game state, deck composition, etc.
    """

    @abstractmethod
    def evaluate_card(self, card: Card, context: DecisionContext) -> float:
        """
        Returns card value score (higher is better).

        Args:
            card: The card to evaluate
            context: Current decision context

        Returns:
            Numeric score where higher values indicate better cards
        """
        pass

    def evaluate(self, context: DecisionContext) -> None:
        """Not applicable for CardEvaluator - use evaluate_card instead."""
        raise NotImplementedError("Use evaluate_card() instead")


class CombatPlanner(DecisionEngine):
    """
    Plan optimal combat action sequence.

    Combat planners analyze the current state and determine the best
    sequence of actions to take during a combat turn.
    """

    @abstractmethod
    def plan_turn(self, context: DecisionContext) -> List[Action]:
        """
        Returns ordered list of actions for this turn.

        Args:
            context: Current decision context

        Returns:
            List of actions to execute in order. Empty list means end turn.
        """
        pass

    def evaluate(self, context: DecisionContext) -> List[Action]:
        """
        Alias for plan_turn for DecisionEngine interface.

        Args:
            context: Current decision context

        Returns:
            List of actions to execute
        """
        return self.plan_turn(context)


class StateEvaluator(DecisionEngine):
    """
    Evaluate game state and estimate win probability.

    State evaluators analyze the current game situation and provide
    an estimate of the player's chances of winning.
    """

    @abstractmethod
    def evaluate_state(self, context: DecisionContext) -> float:
        """
        Returns win probability 0-1.

        Args:
            context: Current decision context

        Returns:
            Probability of winning (0 to 1)
        """
        pass

    def evaluate(self, context: DecisionContext) -> float:
        """
        Alias for evaluate_state for DecisionEngine interface.

        Args:
            context: Current decision context

        Returns:
            Win probability 0-1
        """
        return self.evaluate_state(context)


from enum import Enum


class ThreatCategory(Enum):
    """
    Threat level of enemies in combat.

    Used to select appropriate combat mode (aggressive vs balanced).
    """
    REGULAR = 0       # Normal hallway fights
    ELITE = 1         # Act 1/2/3 elites
    BOSS = 2          # Act bosses
    SCALING = 3       # Enemies with dangerous scaling (strength gain, multihit)
    HIGH_DEFENSE = 4  # Enemies with high block/armor


class EnemyThreatProfiler:
    """
    Analyzes enemy composition and determines threat category.

    Detects elite fights, scaling mechanics, and multi-enemy combos
    to trigger appropriate combat mode selection.
    """

    # Elite monster names for detection (case-insensitive substring match)
    ELITE_NAMES = [
        'Gremlin Nob',
        'Slaver',
        'Sentry',
        'The Guardian',
        'Gremlin Leader',
        'Hexaghost',
        'Reptomancer',
        'The Collector',
        'The Champ',
        'Bronze Automaton',
        'The Ascender',
        'The Shield',
        'The Spire'
    ]

    def __init__(self):
        """Initialize the threat profiler."""
        self._cached_threat = None
        self._cached_monsters = None

    def analyze_threat(self, monsters: List[Monster]) -> ThreatCategory:
        """
        Analyze enemy composition and determine threat category.

        Args:
            monsters: List of monsters in current combat

        Returns:
            ThreatCategory indicating the threat level
        """
        # Check cache to avoid redundant computation
        monster_key = tuple(self._monster_cache_key(monster) for monster in monsters)
        if self._cached_threat is not None and self._cached_monsters == monster_key:
            return self._cached_threat

        threat = self._do_analyze_threat(monsters)

        # Cache result
        self._cached_threat = threat
        self._cached_monsters = monster_key

        return threat

    def _monster_cache_key(self, monster: Monster):
        powers = getattr(monster, 'powers', None) or []
        power_key = tuple(
            (
                getattr(power, 'power_id', None),
                getattr(power, 'power_name', None),
                getattr(power, 'name', None),
                getattr(power, 'amount', None),
            )
            for power in powers
        )
        return (
            id(monster),
            canonical_live_monster_name(monster),
            power_key,
        )

    def _do_analyze_threat(self, monsters: List[Monster]) -> ThreatCategory:
        """Internal threat analysis logic."""

        if not monsters:
            return ThreatCategory.REGULAR

        # 1. Check for elites by name
        for monster in monsters:
            if self._is_elite_by_name(monster):
                return ThreatCategory.ELITE

        # 2. Check for scaling mechanics (powers)
        for monster in monsters:
            if self._has_scaling_power(monster):
                return ThreatCategory.SCALING

        # 3. Check for multi-enemy combos (3+ monsters)
        if len(monsters) >= 3:
            return ThreatCategory.SCALING

        # 4. Default to regular
        return ThreatCategory.REGULAR

    def _is_elite_by_name(self, monster: Monster) -> bool:
        """Check if monster is an elite based on name."""
        name = canonical_live_monster_name(monster).lower()
        if not name:
            return False

        for elite_name in self.ELITE_NAMES:
            if elite_name.lower() in name:
                return True

        return False

    def _has_scaling_power(self, monster: Monster) -> bool:
        """Check if monster has dangerous scaling powers."""
        if not hasattr(monster, 'powers'):
            return False

        if not monster.powers:
            return False

        # Check power names for scaling indicators
        scaling_keywords = ['strength', 'ritual', 'thorns', 'anger', 'enrage']
        for power in monster.powers:
            power_name = (
                getattr(power, 'power_id', None)
                or getattr(power, 'power_name', None)
                or getattr(power, 'name', None)
            )
            if power_name is None:
                continue

            power_name = str(power_name).lower()
            for keyword in scaling_keywords:
                if keyword in power_name:
                    return True

        return False

    def clear_cache(self):
        """Clear cached threat analysis (call when combat changes)."""
        self._cached_threat = None
        self._cached_monsters = None
