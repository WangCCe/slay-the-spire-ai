"""
Relic evaluation system for optimized AI decision-making.

This module provides comprehensive relic evaluation based on:
- Actual relic effects from game data
- Synergies with current deck archetype
- Contextual value based on game state
- Relic combinations and interactions
"""

import re
from typing import Dict, List, Optional, Any
from spirecomm.ai.decision.base import DecisionEngine, DecisionContext
from spirecomm.data.loader import game_data_loader
from spirecomm.spire.relic import Relic


class RelicEvaluator(DecisionEngine):
    """
    Evaluate relics based on their actual effects and synergies.
    
    Provides numerical scores for relics considering:
    - Intrinsic value of the relic effect
    - Synergy with current deck archetype
    - Contextual value (HP, act, floor, etc.)
    - Combinations with other relics
    """
    
    def __init__(self):
        """Initialize the relic evaluator with effect value mappings."""
        # Base values for different relic effect types
        self.EFFECT_VALUES = {
            # Core effects
            'draw': 0.8,           # Card draw effects
            'energy': 1.0,         # Energy generation
            'heal': 0.6,           # Healing effects
            'damage': 0.7,         # Damage effects
            'block': 0.5,          # Block effects
            'scaling': 1.2,        # Scaling stats (strength, dexterity)
            'exhaust': 0.4,        # Exhaust mechanics
            'retain': 0.9,         # Card retention
            'remove': 0.7,         # Card removal
            'cost': 0.8,           # Cost reduction
            
            # Status effects
            'vulnerable': 0.6,     # Vulnerable application
            'weak': 0.5,           # Weak application
            'poison': 0.8,         # Poison application
            'regen': 0.7,          # Regeneration
            
            # Utility
            'relic': 0.5,          # Additional relics
            'potion': 0.4,         # Potion effects
            'gold': 0.3,           # Gold generation
            'shop': 0.4,           # Shop benefits
            'event': 0.3,          # Event benefits
        }
        
        # Archetype-specific relic bonuses
        self.ARCHETYPE_BONUSES = {
            'strength': {
                'strength': 1.5,    # Strength scaling relics
                'damage': 1.2,      # Damage relics
                'exhaust': 0.8,     # Exhaust synergy
            },
            'poison': {
                'poison': 2.0,      # Poison scaling relics
                'weak': 1.3,        # Weak synergy
                'draw': 1.2,        # Draw synergy
            },
            'block': {
                'block': 1.5,       # Block scaling relics
                'retain': 1.2,      # Retain synergy
                'heal': 1.1,        # Healing synergy
            },
            'draw': {
                'draw': 1.5,        # Draw scaling relics
                'energy': 1.3,      # Energy synergy
                'cost': 1.2,        # Cost reduction synergy
            },
            'exhaust': {
                'exhaust': 1.8,     # Exhaust scaling relics
                'draw': 1.3,        # Draw synergy
                'retain': 1.1,      # Retain synergy
            },
        }
    
    def evaluate(self, context: DecisionContext) -> Dict[str, float]:
        """
        Evaluate all relics in the current game context.
        
        Args:
            context: The decision context containing game state
            
        Returns:
            Dictionary mapping relic IDs to their evaluation scores
        """
        if not hasattr(context.game, 'relics') or not context.game.relics:
            return {}
        
        scores = {}
        for relic in context.game.relics:
            scores[relic.relic_id] = self.evaluate_relic(relic, context)
        
        return scores
    
    def evaluate_relic(self, relic: Relic, context: DecisionContext) -> float:
        """
        Evaluate a single relic based on its effects and context.
        
        Args:
            relic: The relic to evaluate
            context: The decision context containing game state
            
        Returns:
            Numerical score representing the relic's value (higher is better)
        """
        # Get relic data from game data loader
        relic_name = relic.relic_id.replace('+', '').lower()
        relic_data = game_data_loader.get_relic_data(relic_name)
        
        if not relic_data:
            return 0.0  # Unknown relic
        
        # Base score calculation
        base_score = self._calculate_base_value(relic_data)
        
        # Archetype synergy bonus
        archetype_bonus = self._calculate_archetype_bonus(relic_data, context)
        
        # Contextual modifier based on game state
        context_modifier = self._calculate_context_modifier(relic_data, context)
        
        # Relic combination bonus
        combination_bonus = self._calculate_combination_bonus(relic, context)
        
        # Calculate total score
        total_score = base_score * (1 + archetype_bonus) * (1 + context_modifier) + combination_bonus
        
        return max(0.1, total_score)  # Ensure minimum value
    
    def _calculate_base_value(self, relic_data: Dict[str, Any]) -> float:
        """
        Calculate the base value of a relic based on its effects.
        
        Args:
            relic_data: Relic data from game data loader
            
        Returns:
            Base value score
        """
        description = relic_data.get('description', '').lower()
        tier = relic_data.get('tier', '').lower()
        
        # Tier multiplier
        tier_multipliers = {
            'boss': 3.0,
            'rare': 2.0,
            'uncommon': 1.5,
            'common': 1.0,
            'starter': 0.5,
        }
        tier_multiplier = tier_multipliers.get(tier, 1.0)
        
        # Calculate effect value
        effect_score = 0.0
        
        # Draw effects
        if any(term in description for term in ['draw', 'add', 'gain']):
            # Count how many cards are drawn
            draw_match = re.search(r'(\d+) cards?', description)
            if draw_match:
                cards = int(draw_match.group(1))
                effect_score += cards * self.EFFECT_VALUES['draw']
            else:
                effect_score += self.EFFECT_VALUES['draw']
        
        # Energy effects
        if any(term in description for term in ['energy', 'power']):
            energy_match = re.search(r'(\d+) energy', description)
            if energy_match:
                energy = int(energy_match.group(1))
                effect_score += energy * self.EFFECT_VALUES['energy']
            else:
                effect_score += self.EFFECT_VALUES['energy'] * 0.8
        
        # Healing effects
        if any(term in description for term in ['heal', 'regenerate', 'recover']):
            heal_match = re.search(r'(\d+) hp', description)
            if heal_match:
                heal = int(heal_match.group(1))
                effect_score += heal * self.EFFECT_VALUES['heal'] * 0.1
            else:
                effect_score += self.EFFECT_VALUES['heal']
        
        # Damage effects
        if any(term in description for term in ['damage', 'attack', 'strike']):
            damage_match = re.search(r'(\d+) damage', description)
            if damage_match:
                damage = int(damage_match.group(1))
                effect_score += damage * self.EFFECT_VALUES['damage'] * 0.1
            else:
                effect_score += self.EFFECT_VALUES['damage']
        
        # Block effects
        if any(term in description for term in ['block', 'shield']):
            block_match = re.search(r'(\d+) block', description)
            if block_match:
                block = int(block_match.group(1))
                effect_score += block * self.EFFECT_VALUES['block'] * 0.1
            else:
                effect_score += self.EFFECT_VALUES['block']
        
        # Scaling effects (strength, dexterity, poison)
        if any(term in description for term in ['strength', 'dexterity', 'poison']):
            scaling_match = re.search(r'(\d+) (strength|dexterity|poison)', description)
            if scaling_match:
                amount = int(scaling_match.group(1))
                effect = scaling_match.group(2)
                effect_score += amount * self.EFFECT_VALUES['scaling'] * 0.2
            else:
                effect_score += self.EFFECT_VALUES['scaling']
        
        # Exhaust effects
        if 'exhaust' in description:
            effect_score += self.EFFECT_VALUES['exhaust']
        
        # Retain effects
        if 'retain' in description:
            effect_score += self.EFFECT_VALUES['retain']
        
        # Cost reduction effects
        if any(term in description for term in ['cost', 'reduce', 'cheaper']):
            effect_score += self.EFFECT_VALUES['cost']
        
        # Vulnerable effects
        if 'vulnerable' in description:
            effect_score += self.EFFECT_VALUES['vulnerable']
        
        # Weak effects
        if 'weak' in description:
            effect_score += self.EFFECT_VALUES['weak']
        
        # Gold effects
        if any(term in description for term in ['gold', 'coins', 'treasure']):
            gold_match = re.search(r'(\d+) gold', description)
            if gold_match:
                gold = int(gold_match.group(1))
                effect_score += gold * self.EFFECT_VALUES['gold'] * 0.01
            else:
                effect_score += self.EFFECT_VALUES['gold']
        
        # Apply tier multiplier
        return effect_score * tier_multiplier
    
    def _calculate_archetype_bonus(self, relic_data: Dict[str, Any], context: DecisionContext) -> float:
        """
        Calculate bonus based on relic synergy with current deck archetype.
        
        Args:
            relic_data: Relic data from game data loader
            context: The decision context containing game state
            
        Returns:
            Bonus multiplier (0-2)
        """
        description = relic_data.get('description', '').lower()
        archetype = context.deck_archetype
        
        if archetype not in self.ARCHETYPE_BONUSES or archetype == 'unknown' or archetype == 'balanced':
            return 0.0
        
        bonus = 0.0
        archetype_bonuses = self.ARCHETYPE_BONUSES[archetype]
        
        # Check for archetype-relevant effects
        for effect, multiplier in archetype_bonuses.items():
            if effect in description:
                bonus += multiplier * 0.2  # Apply a portion of the multiplier
        
        return min(1.0, bonus)  # Cap at 100% bonus
    
    def _calculate_context_modifier(self, relic_data: Dict[str, Any], context: DecisionContext) -> float:
        """
        Calculate modifier based on current game context.
        
        Args:
            relic_data: Relic data from game data loader
            context: The decision context containing game state
            
        Returns:
            Contextual modifier (-0.5 to 1.0)
        """
        description = relic_data.get('description', '').lower()
        modifier = 0.0
        
        # HP-based modifiers
        if any(term in description for term in ['heal', 'regenerate', 'recover']):
            # More valuable when HP is low
            modifier += (1.0 - context.player_hp_pct) * 0.5
        
        # Act-based modifiers
        if context.act == 1:
            # In Act 1, focus on survival and consistency
            if any(term in description for term in ['block', 'heal', 'damage']):
                modifier += 0.3
        elif context.act == 3:
            # In Act 3, focus on scaling and endgame power
            if 'scaling' in description or any(term in description for term in ['strength', 'dexterity', 'poison']):
                modifier += 0.5
        
        # Floor-based modifiers
        if context.floor > 40:  # Near endgame
            if any(term in description for term in ['boss', 'elite', 'damage']):
                modifier += 0.4
        
        return max(-0.5, min(1.0, modifier))  # Clamp to reasonable range
    
    def _calculate_combination_bonus(self, relic: Relic, context: DecisionContext) -> float:
        """
        Calculate bonus for relic combinations.
        
        Args:
            relic: The relic to evaluate
            context: The decision context containing game state
            
        Returns:
            Combination bonus score
        """
        if not hasattr(context.game, 'relics') or not context.game.relics:
            return 0.0
        
        bonus = 0.0
        relic_id = relic.relic_id.lower()
        
        # Check for specific relic combinations
        relic_combinations = {
            'snecko eye': {
                'cursed key': 0.5,  # More cards = more curse chances, but also more value
                'runic pyramid': 1.0,  # Keep cards with random costs
            },
            'burning blood': {
                'reaper': 2.0,  # Perfect synergy
                'blood vial': 1.5,  # Additional healing
            },
            'barricade': {
                'body slam': 2.0,  # Core synergy
                'entrench': 1.5,  # Block scaling
            },
            'demon form': {
                'limit break': 2.0,  # Core strength synergy
                'double tap': 1.5,  # Reuse powers
            },
            'corruption': {
                'feel no pain': 2.0,  # Core exhaust synergy
                'dark embrace': 1.5,  # Draw exhaust synergy
            },
        }
        
        # Apply combination bonuses
        if relic_id in relic_combinations:
            for other_relic_id, combo_bonus in relic_combinations[relic_id].items():
                if any(r.relic_id.lower() == other_relic_id for r in context.game.relics):
                    bonus += combo_bonus
        
        return bonus
    
    def get_confidence(self, context: DecisionContext) -> float:
        """
        Return confidence in relic evaluations.
        
        Args:
            context: The decision context containing game state
            
        Returns:
            Confidence value between 0 and 1
        """
        # Higher confidence when we have more information about the deck and relics
        if hasattr(context.game, 'relics') and len(context.game.relics) > 0:
            return 0.8
        return 0.5
    
    def suggest_best_relic(self, relics: List[Relic], context: DecisionContext) -> Optional[Relic]:
        """
        Suggest the best relic from a list based on current context.
        
        Args:
            relics: List of relics to choose from
            context: The decision context containing game state
            
        Returns:
            The best relic, or None if the list is empty
        """
        if not relics:
            return None
        
        # Evaluate all relics
        relic_scores = [(self.evaluate_relic(relic, context), relic) for relic in relics]
        
        # Sort by score descending
        relic_scores.sort(reverse=True, key=lambda x: x[0])
        
        return relic_scores[0][1] if relic_scores else None
