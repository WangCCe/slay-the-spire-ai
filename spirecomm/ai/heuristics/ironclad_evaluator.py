"""
Ironclad-specific card evaluator with expert strategy integration.

Based on A20 high-level player research and current meta strategies (2023-2025).
Key improvements over generic SynergyCardEvaluator:
- Expert-based card priority tiers
- Archetype-aware evaluation (strength, exhaust, body_slam)
- HP-aware risk assessment
- Energy curve management
- Act 1 aggressive strategy support
"""

from .card import SynergyCardEvaluator
from .card_names import canonical_card_name
from ..decision.base import DecisionContext
from spirecomm.spire.card import Card


class IroncladCardEvaluator(SynergyCardEvaluator):
    """
    Ironclad-specific card evaluator based on expert strategies.

    Key insights from high-level play:
    - Reaper is core card (not tier 4) - critical for strength decks
    - Shrug It Off is tier 0 (0 cost 8 block + draw)
    - Demon Form should be played by turn 2-3
    - Limit Break when Strength >= 5
    - Act 1: Take 2-3 elites (Ironclad is strongest early)
    - Keep deck small (<20 cards)
    """

    # Expert-based card priority adjustments.
    #
    # These are baseline values. Act 1 applies an additional layer below that
    # favors immediate damage and penalizes cards that need an engine first.
    PROMOTED_CARDS = {
        'Reaper': 95,        # From tier 4 → tier 1 (critical sustain)
        'Shrug It Off': 98,  # From tier 2 → tier 0 (best block card)
        'Feel No Pain': 72,  # Strong with exhaust support, speculative early
        'Spot Weakness': 85, # Consistent strength gain
        'Disarm': 82,        # Powerful single-target defense
        'Headbutt': 88,      # Retrieval + damage + synergy
        'Perfected Strike': 85,  # Core attack card, excellent scaling
        'Iron Wave': 75,     # From default → tier 2 (excellent block+damage hybrid)
        'Flame Barrier': 70, # Good block+damage hybrid, synergizes with Body Slam
        'Impervious': 72,    # High block + draw, excellent for block decks
        'Barricade': 62,     # Strong payoff, bad before block density exists
        'Entrench': 45,      # Requires block engine; dangerous speculative Act 1 pick
        'Rage': 75,          # Excellent damage boost, especially with Strength
        'Whirlwind': 78,     # AOE damage, synergizes with Strength
        'Battle Trance': 80,  # Key card draw, essential for consistency
        'Double Tap': 72,    # Enables powerful combos, especially with heavy hitters
        'Immolate': 95,      # Premium Act 1 AoE frontload; adds a Burn, not HP loss
        'Metallicize': 70,   # Good persistent block, great for early game
        'Feed': 72,          # Damage + max HP gain, excellent sustain
        'Heavy Blade': 75,   # Scales well with Strength, efficient damage
        'Fiend Fire': 70,     # Powerful AOE damage, synergizes with exhaust
        'Hemokinesis': 84,   # Act 1 premium frontloaded damage
        'Carnage': 83,       # Act 1 premium frontloaded damage
        'Pommel Strike': 84,
        'Anger': 82,
        'Clothesline': 82,
        'Uppercut': 84,
        'Cleave': 80,
        'Thunderclap': 83,
    }

    DEMOTED_CARDS = {
        'Searing Blow': 20,  # Requires heavy upgrade investment
        'Wild Strike': 25,   # Adds random card, bloats deck
        'Flex': 45,          # Needs payoff; weak standalone reward
        'Clash': 28,         # Unreliable once skills/statuses enter the deck
        'Body Slam': 38,     # Great only after block density exists
        'Limit Break': 35,   # Great only after strength support exists
        'Warcry': 30,        # Low-impact Act 1 filler
        'Rupture': 25,       # Needs self-damage engine
    }

    # Archetype-specific bonuses
    ARCHETYPE_BONUS_CARDS = {
        'strength': {
            'Demon Form': 35,
            'Limit Break': 35,
            'Inflame': 25,
            'Spot Weakness': 20,
            'Reaper': 30,
            'Disarm': 15,
            'Body Slam': 25,
            'Heavy Blade': 20,
        },
        'exhaust': {
            'Corruption': 35,
            'Feel No Pain': 30,
            'Dark Embrace': 25,
            'Offering': 20,
            'Second Wind': 15,
        },
        'body_slam': {
            'Barricade': 40,
            'Body Slam': 35,
            'Entrench': 30,
            'Iron Wave': 25,
            'Impervious': 20,
            'Flame Barrier': 20,
        },
    }

    # Act 1 damage priorities (early game survival through frontloaded damage)
    ACT_1_DAMAGE_PRIORITY = {
        'Whirlwind', 'Pommel Strike', 'Cleave', 'Fiend Fire',
        'Inflame', 'Rampage', 'Heavy Blade', 'Headbutt',
        'Uppercut', 'Spot Weakness', 'Twin Strike', 'Reaper',
        'Hemokinesis', 'Carnage', 'Anger', 'Clothesline',
        'Thunderclap', 'Immolate',
    }

    ACT_1_PREMIUM_FRONTLOAD = {
        'Pommel Strike', 'Anger', 'Clothesline', 'Uppercut',
        'Hemokinesis', 'Carnage', 'Cleave', 'Headbutt',
        'Twin Strike', 'Iron Wave', 'Whirlwind', 'Thunderclap', 'Immolate',
    }

    ACT_1_SURVIVAL_BLOCK = {
        'Shrug It Off', 'Flame Barrier', 'Power Through',
        'Ghostly Armor', 'True Grit', 'Impervious',
    }

    ACT_1_FRONTLOAD_COVERAGE = ACT_1_PREMIUM_FRONTLOAD | {
        'Immolate', 'Bludgeon', 'Heavy Blade', 'Perfected Strike',
    }

    SPECULATIVE_ENGINE_CARDS = {
        'Body Slam', 'Limit Break', 'Entrench', 'Barricade',
        'Feel No Pain', 'Dark Embrace', 'Rupture', 'Warcry',
    }

    STRENGTH_SUPPORT = {'Demon Form', 'Inflame', 'Spot Weakness', 'Flex'}
    BLOCK_SUPPORT = {
        'Shrug It Off', 'Flame Barrier', 'Impervious', 'Power Through',
        'Ghostly Armor', 'Metallicize', 'Iron Wave', 'True Grit',
    }
    EXHAUST_SUPPORT = {'Corruption', 'True Grit', 'Second Wind', 'Fiend Fire', 'Sever Soul'}
    SELF_DAMAGE_SUPPORT = {'Offering', 'Bloodletting', 'Hemokinesis', 'Combust', 'Brutality'}

    # HP-cost cards (spend HP to play)
    HP_COST_CARDS = {
        'Offering', 'Bloodletting', 'Hemokinesis',
    }

    # Self-damage cards (deal HP loss as a side effect)
    SELF_DAMAGE_CARDS = {
        'Combust', 'Brutality',
    }

    def __init__(self, player_class='IRONCLAD'):
        """Initialize Ironclad evaluator with expert priorities."""
        super().__init__(player_class)

        # Override baseline scores with expert priorities
        for card_id, score in self.PROMOTED_CARDS.items():
            self.baseline_scores[card_id] = score

        for card_id, score in self.DEMOTED_CARDS.items():
            self.baseline_scores[card_id] = score

    @staticmethod
    def _card_name(card: Card) -> str:
        return canonical_card_name(card)

    def evaluate_card(self, card: Card, context: DecisionContext) -> float:
        """
        Evaluate card for Ironclad with expert strategy integration.

        Evaluation flow:
        1. Get baseline from expert priorities
        2. Apply HP-aware modifier (penalize risky cards at low HP)
        3. Apply archetype-specific bonus
        4. Consider energy curve
        5. Act 1 special handling (aggressive damage)
        """
        # 1. Baseline from expert priorities
        card_id = self._card_name(card)
        baseline = self.baseline_scores.get(card_id, 50)

        # 2. HP-aware modifier
        hp_modifier = self._calculate_hp_aware_modifier(card, context)

        # 3. Archetype bonus
        archetype_bonus = self._calculate_archetype_bonus(card, context)

        # 4. Energy curve consideration
        energy_modifier = self._evaluate_energy_curve(card, context)

        # 5. Act 1 frontload/support-aware adjustment
        act_bonus = self._calculate_act_1_bonus(card, context)
        support_adjustment = self._calculate_support_adjustment(card, context)

        # Final score
        final_score = (baseline * hp_modifier) + archetype_bonus + act_bonus + support_adjustment

        # Apply energy curve modifier as multiplier
        final_score *= energy_modifier

        return max(0, min(100, final_score))

    def _calculate_hp_aware_modifier(self, card: Card, context: DecisionContext) -> float:
        """
        Adjust card value based on current HP situation.

        Rules:
        - HP < 30%: Heavy penalty for HP-cost/self-damage cards
        - HP < 50%: Moderate penalty for risky cards
        - HP > 80%: Can afford high-risk cards
        - HP < 40%: Bonus for defensive cards
        """
        modifier = 1.0
        hp_pct = self._non_negative_float(getattr(context, 'player_hp_pct', 0))
        card_id = self._card_name(card)

        if hp_pct < 0.3:
            # Critical HP - avoid all HP costs
            if card_id in self.HP_COST_CARDS:
                return 0.1  # Almost never pick
            if card_id in self.SELF_DAMAGE_CARDS:
                modifier *= 0.3
            # Prioritize defense heavily
            if self._is_defensive_card(card):
                modifier *= 2.5

        elif hp_pct < 0.5:
            # Low HP - moderate caution
            if card_id in self.HP_COST_CARDS:
                modifier *= 0.4
            if card_id in self.SELF_DAMAGE_CARDS:
                modifier *= 0.7
            if self._is_defensive_card(card):
                modifier *= 1.5

        elif hp_pct > 0.8:
            # High HP - can take risks
            if card_id in ['Offering', 'Bloodletting', 'Hemokinesis']:
                modifier *= 1.3  # These are powerful when safe

        return modifier

    def _calculate_archetype_bonus(self, card: Card, context: DecisionContext) -> float:
        """
        Calculate archetype-specific bonus.

        If deck has clear archetype, bonus cards that fit it
        and penalize cards that don't.
        """
        archetype = context.deck_archetype

        # If no clear archetype or flexible, no bonus/penalty
        if archetype == 'unknown' or archetype == 'balanced' or archetype == 'flexible':
            return 0.0

        # Get archetype-specific bonuses
        archetype_cards = self.ARCHETYPE_BONUS_CARDS.get(archetype, {})
        card_id = self._card_name(card)

        # Check if card fits archetype
        if card_id in archetype_cards:
            return archetype_cards[card_id]

        # Small penalty for cards that don't fit archetype
        # (only if archetype is well-established)
        archetype_score = self._non_negative_float(getattr(context, 'archetype_score', 0))
        if archetype_score > 0.5:
            return -10

        return 0.0

    def _evaluate_energy_curve(self, card: Card, context: DecisionContext) -> float:
        """
        Evaluate if card fits deck's energy curve.

        Target distribution (for 15-card deck):
        - 0-cost: 2-3 cards (15-20%)
        - 1-cost: 3-4 cards (20-25%)
        - 2-cost: 5-6 cards (33-40%)
        - 3-cost: 2-3 cards (15-20%)
        - 4+ cost: 0-1 cards (0-10%)
        """
        if not hasattr(context.game, 'deck') or not context.game.deck:
            return 1.0

        deck = context.game.deck
        deck_size = len(deck)

        def normalized_base_cost(deck_card) -> int:
            cost = getattr(deck_card, 'cost', 1)
            if cost is None:
                return 1
            try:
                return int(cost)
            except (TypeError, ValueError):
                return 1

        # Count cards by cost
        cost_counts = {}
        for c in deck:
            cost = normalized_base_cost(c)
            cost_counts[cost] = cost_counts.get(cost, 0) + 1

        card_cost = normalized_base_cost(card)

        # Ideal percentages
        ideal_percentages = {
            0: 0.18,   # 0-cost: ~15-20%
            1: 0.23,   # 1-cost: ~20-25%
            2: 0.37,   # 2-cost: ~33-40%
            3: 0.17,   # 3-cost: ~15-20%
        }

        current_pct = cost_counts.get(card_cost, 0) / deck_size
        ideal_pct = ideal_percentages.get(card_cost, 0.05)

        # Adjust modifier
        if current_pct > ideal_pct * 1.8:
            modifier = 0.6  # Too many of this cost
        elif current_pct > ideal_pct * 1.4:
            modifier = 0.8  # Slightly too many
        elif current_pct < ideal_pct * 0.4:
            modifier = 1.3  # Need more of this cost
        else:
            modifier = 1.0  # Good balance

        if (
            context.act == 1
            and self._card_name(card) in self.ACT_1_SURVIVAL_BLOCK
            and self._act_1_survival_gap(context)[0]
        ):
            return max(modifier, 1.0)

        return modifier

    def _calculate_act_1_bonus(self, card: Card, context: DecisionContext) -> float:
        """
        Act 1 specific bonuses for early game aggression.

        Ironclad is strongest in Act 1. Prioritize:
        - Damage cards (to kill elites)
        - Win condition cards (Demon Form, Limit Break, Barricade)
        """
        if context.act != 1:
            return 0.0

        deck_size = len(context.game.deck) if hasattr(context.game, 'deck') else 10
        floor = getattr(context, 'floor', 0) or 0
        bonus = 0.0
        card_id = self._card_name(card)

        if card_id in self.ACT_1_PREMIUM_FRONTLOAD:
            if deck_size <= 13 or floor <= 8:
                bonus += 22
            else:
                bonus += 10
        elif card_id in self.ACT_1_DAMAGE_PRIORITY:
            if deck_size <= 13:
                bonus += 14

        # True solo win conditions remain attractive, but slower engines should
        # not beat first-cycle damage before the deck can survive Act 1 elites.
        if card_id in ['Demon Form', 'Corruption']:
            bonus += 14
        elif card_id in ['Limit Break', 'Barricade']:
            bonus -= 20

        if card_id in self.SPECULATIVE_ENGINE_CARDS and deck_size <= 14:
            bonus -= 18

        needs_survival, block_support, frontload = self._act_1_survival_gap(context)
        if needs_survival:
            if card_id in self.ACT_1_SURVIVAL_BLOCK:
                bonus += 42 if block_support == 0 else 30
            elif card_id in self.ACT_1_DAMAGE_PRIORITY and frontload >= 1:
                bonus -= 18

        return bonus

    def _act_1_survival_gap(self, context: DecisionContext) -> tuple:
        """Return whether Act 1 needs non-basic block before adding more attacks."""
        if context.act != 1:
            return (False, 0, 0)

        deck = list(getattr(context.game, 'deck', []) or [])
        deck_ids = [self._card_name(c) for c in deck]
        floor = getattr(context, 'floor', 0) or 0

        block_support = sum(1 for card_id in deck_ids if card_id in self.BLOCK_SUPPORT)
        frontload = sum(1 for card_id in deck_ids if card_id in self.ACT_1_FRONTLOAD_COVERAGE)

        if block_support == 0 and (frontload >= 1 or floor >= 4):
            return (True, block_support, frontload)
        if block_support == 1 and (frontload >= 2 or floor >= 8):
            return (True, block_support, frontload)
        if floor >= 12 and block_support < 3:
            return (True, block_support, frontload)

        return (False, block_support, frontload)

    def _calculate_support_adjustment(self, card: Card, context: DecisionContext) -> float:
        """Reward payoff cards only when the current deck can actually support them."""
        deck = list(getattr(context.game, 'deck', []) or [])
        card_ids = [self._card_name(c) for c in deck]

        def count(names):
            return sum(1 for card_id in card_ids if card_id in names)

        strength_support = count(self.STRENGTH_SUPPORT)
        block_support = count(self.BLOCK_SUPPORT)
        exhaust_support = count(self.EXHAUST_SUPPORT)
        self_damage_support = count(self.SELF_DAMAGE_SUPPORT)

        card_id = self._card_name(card)
        if card_id == 'Limit Break':
            return 28 if strength_support >= 2 else -35
        if card_id == 'Body Slam':
            return 30 if block_support >= 3 else -30
        if card_id in {'Entrench', 'Barricade'}:
            return 24 if block_support >= 3 else -32
        if card_id in {'Feel No Pain', 'Dark Embrace'}:
            return 24 if exhaust_support >= 2 else -22
        if card_id == 'Rupture':
            return 26 if self_damage_support >= 2 else -34
        if card_id == 'Flex':
            has_payoff = any(card_id in card_ids for card_id in ('Heavy Blade', 'Limit Break', 'Reaper'))
            return 12 if has_payoff else -18

        return 0.0

    def _is_defensive_card(self, card: Card) -> bool:
        """Check if card is primarily defensive."""
        defensive_keywords = [
            'defend', 'block', 'iron wave', 'flame barrier', 'impervious',
            'entrench', 'shrug it off', 'sentinel', 'ghostly armor',
        ]

        card_id_lower = self._card_name(card).lower()

        for keyword in defensive_keywords:
            if keyword in card_id_lower:
                return True

        return False
