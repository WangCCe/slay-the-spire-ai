# Technical Design: Unified Act 1 Elite Strategy Framework

## Architecture Overview

```
_score_sequence()
  ↓
_detect_elite_type()
  ↓
_apply_elite_strategy_override()
  ├→ Gremlin Nob: SKILL penalty (-50)
  ├→ Lagavulin: Progressive scaling (4.0 → 8.0)
  ├→ 3 Sentries: Single-target bonus (+50)
  └→ Slime Boss: AOE multiplier (×1.5)
  ↓
_calculate_base_score()
  ↓
_apply_elite_modifiers()
  ↓
return score
```

## Elite Detection System

### 1. Elite Type Enumeration

```python
from enum import Enum

class EliteType(Enum):
    GREMLIN_NOB = "Gremlin Nob"
    LAGAVULIN = "Lagavulin"
    THREE_SENTRIES = "3 Sentries"  # or "The Sentry"
    SLIME_BOSS = "Slime Boss"
    UNKNOWN = "Unknown"
```

### 2. Detection Logic

```python
def _detect_elite_type(self, context: DecisionContext) -> EliteType:
    """
    Detect which elite we're fighting to apply specialized strategy.

    Returns:
        EliteType enum value indicating the elite (or UNKNOWN)
    """
    if not context.monsters_alive:
        return EliteType.UNKNOWN

    monster_ids = [m.monster_id for m in context.monsters_alive]
    monster_names = [m.name for m in context.monsters_alive]

    # Gremlin Nob: Easy detection
    if "Gremlin Nob" in monster_ids:
        return EliteType.GREMLIN_NOB

    # Lagavulin: Single elite with specific name
    if "Lagavulin" in monster_ids:
        return EliteType.LAGAVULIN

    # 3 Sentries: Three monsters with "Sentry" in name
    sentry_count = sum(1 for name in monster_names if "Sentry" in name)
    if sentry_count >= 2:  # Usually 3, but might kill one already
        return EliteType.THREE_SENTRIES

    # Slime Boss: Has "Slime" in name and is elite
    if len(context.monsters_alive) == 1:
        monster = context.monsters_alive[0]
        if "Slime" in monster.monster_id and hasattr(monster, 'elite'):
            return EliteType.SLIME_BOSS

    return EliteType.UNKNOWN
```

## Elite-Specific Strategies

### 1. Gremlin Nob (Preserve Existing Implementation)

**Mechanic**: +1 Strength per SKILL card played

**Strategy** (Already implemented in v3.3.1):
```python
if elite_type == EliteType.GREMLIN_NOB:
    # In card evaluation loop:
    if card.type == CardType.SKILL:
        score -= 50
```

**Verification**: Ensure existing SKILL penalty still works

---

### 2. Lagavulin Progressive Scaling

**Mechanic**: Siphon Soul every 3 turns (turns 6, 9, 12, ...) → -1 Dex, -1 Str

**Strategy**: Exponential damage_weight increase

```python
def _apply_lagavulin_strategy(self, context: DecisionContext, base_score: float) -> float:
    """
    Apply Lagavulin-specific strategy: progressive scaling based on Siphon Soul count.

    Formula: damage_weight = 4.0 + (siphon_count × 1.5), capped at 8.0
    """
    if context.turn < 6:
        siphon_count = 0
        damage_weight = 5.0  # Early hibernation phase
    else:
        siphon_count = (context.turn - 6) // 3 + 1
        damage_weight = min(8.0, 4.0 + (siphon_count * 1.5))

    # Apply progressive damage bonus
    damage_bonus = final_state.total_damage_dealt * damage_weight

    # Low-damage penalty after first Siphon (turn 6+)
    if context.turn >= 6:
        min_damage_needed = 15 + (siphon_count * 5)
        if final_state.total_damage_dealt < min_damage_needed:
            score -= 200  # Prolonging fight = death

    # Pre-Siphon burst bonus
    turns_until_siphon = 2 - (context.turn - 5) % 3
    if turns_until_siphon == 1 and final_state.total_damage_dealt > 30:
        score += 100

    return score
```

---

### 3. 3 Sentries: Single-Target Focus

**Mechanic**: Two elites stack Strength simultaneously via Focus

**Strategy**: Bonus for concentrating damage on one target

```python
def _apply_sentries_strategy(self, context: DecisionContext, sequence: List[Action], score: float) -> float:
    """
    Apply 3 Sentries strategy: reward focusing damage on one elite.

    Principle: "Burst down one" is better than spreading damage evenly.
    """
    if len(context.monsters_alive) < 2:
        return score  # Only one left, normal priority

    # Check if damage is concentrated on one target
    damage_distribution = self._calculate_damage_distribution(sequence, context)

    # Calculate concentration: highest_damage / total_damage
    if damage_distribution['total_damage'] > 0:
        concentration = damage_distribution['highest_damage'] / damage_distribution['total_damage']
    else:
        concentration = 0.0

    # Bonus: 70%+ damage on one target = +50 points
    if concentration >= 0.7:
        score += 50
        logger.info(f"[SENTRIES_FOCUS] +50 for concentrating {concentration:.1%} damage")

    # Penalty: Evenly spread damage (<50% on any target) = -30 points
    elif concentration < 0.5 and damage_distribution['total_damage'] > 15:
        score -= 30
        logger.info(f"[SENTRIES_SPREAD] -30 for spreading damage too evenly")

    return score

def _calculate_damage_distribution(self, sequence: List[Action], context: DecisionContext) -> Dict:
    """Calculate how damage is distributed across monsters."""
    damage_by_target = {}

    for action in sequence:
        if isinstance(action, PlayCardAction):
            card = action.card
            if hasattr(card, 'damage') and card.damage > 0:
                target = action.target_monster if hasattr(action, 'target_monster') else None
                if target:
                    damage_by_target[target] = damage_by_target.get(target, 0) + card.damage

    if damage_by_target:
        return {
            'highest_damage': max(damage_by_target.values()),
            'total_damage': sum(damage_by_target.values())
        }
    else:
        return {'highest_damage': 0, 'total_damage': 0}
```

---

### 4. Slime Boss: AOE Priority

**Mechanic**: Splits into 3 monsters at 50% HP → AOE becomes critical

**Strategy**: Bonus for AOE attacks, especially near split threshold

```python
def _apply_slime_boss_strategy(self, context: DecisionContext, sequence: List[Action], score: float) -> float:
    """
    Apply Slime Boss strategy: reward AOE damage.

    Principle: AOE cards are highly valuable because:
    1. They damage the boss before split
    2. They hit all spawned slimes
    3. Cleave/Thunderclap/Whirlwind scale with monster count
    """
    if not context.monsters_alive:
        return score

    slime_boss = context.monsters_alive[0]
    hp_pct = slime_boss.current_hp / slime_boss.max_hp

    # AOE cards list
    aoe_cards = ['Cleave', 'Thunderclap', 'Whirlwind', 'Immolate']

    for action in sequence:
        if isinstance(action, PlayCardAction):
            card = action.card
            card_id = card.card_id

            # AOE damage multiplier (×1.5)
            if card_id in aoe_cards:
                # Calculate bonus based on monster count and card damage
                monster_count = len(context.monsters_alive)
                if hasattr(card, 'damage'):
                    aoe_damage = card.damage * monster_count
                    score += aoe_damage * 1.5
                    logger.info(f"[SLIME_AOE] +{aoe_damage * 1.5:.1f} for {card_id} ({monster_count} targets)")

            # Near split threshold (40-60% HP): Extra bonus for high damage
            if 0.4 < hp_pct < 0.6:
                if hasattr(card, 'damage') and card.damage > 12:
                    score += 30  # Bonus for big hits near split point
                    logger.info(f"[SLIME_BURST] +30 for high damage near split")

    return score
```

## A20 Early Aggression System

### Problem: Current AI Waits Too Long

**Current behavior**:
- Turn 1-3: "Preparation phase" (play Powers, setup)
- Turn 4-5: Start dealing damage
- **Too slow for A20 elites!**

**New behavior**:
- Turn 1: Start dealing meaningful damage IMMEDIATELY
- Turn 2: High damage expected (15+)
- Turn 3+: Must be killing or very close

### Implementation

```python
def _apply_a20_early_aggression(self, context: DecisionContext, score: float) -> float:
    """
    Apply A20-specific early aggression rules.

    At A20, elites kill you if you wait. Must damage from turn 1.
    """
    # Turn 1: At least some damage (8+)
    if context.turn == 1:
        if final_state.total_damage_dealt < 8:
            score -= 50  # Penalty for passive turn 1

    # Turn 2: Significant damage expected (15+)
    if context.turn == 2:
        if final_state.total_damage_dealt < 15:
            score -= 100  # Heavy penalty for slow turn 2

    # Turn 3+: Kill pressure
    if context.turn >= 3:
        # Check if we're making progress toward lethal
        total_monster_hp = sum(m.current_hp for m in context.monsters_alive)
        initial_monster_hp = sum(m.max_hp for m in context.monsters_alive)
        damage_so_far = initial_monster_hp - total_monster_hp

        # Expected minimum damage per turn
        min_expected = context.turn * 12  # 12 HP per turn average
        if damage_so_far < min_expected:
            score -= 150  # Very heavy penalty for falling behind

    return score
```

## Unified Integration Point

### Main Method: `_apply_elite_strategy_override()`

```python
def _apply_elite_strategy_override(
    self,
    context: DecisionContext,
    sequence: List[Action],
    final_state: SimulationState,
    initial_state: SimulationState,
    base_score: float
) -> float:
    """
    Apply elite-specific strategy overrides.

    This is the unified entry point for all elite tactics.
    """
    score = base_score

    # Detect elite type
    elite_type = self._detect_elite_type(context)

    # Apply elite-specific modifiers
    if elite_type == EliteType.GREMLIN_NOB:
        # SKILL penalty already applied in card loop (preserve v3.3.1 logic)
        pass

    elif elite_type == EliteType.LAGAVULIN:
        score = self._apply_lagavulin_strategy(context, sequence, score)

    elif elite_type == EliteType.THREE_SENTRIES:
        score = self._apply_sentries_strategy(context, sequence, score)

    elif elite_type == EliteType.SLIME_BOSS:
        score = self._apply_slime_boss_strategy(context, sequence, score)

    # A20 Early Aggression (applies to ALL elites)
    if context.ascension >= 20:
        score = self._apply_a20_early_aggression(context, sequence, score)

    return score
```

## Testing Strategy

### Elite Detection Tests

```python
# Test 1: Gremlin Nob detection
context = create_mock_context(monsters=["Gremlin Nob"])
assert _detect_elite_type(context) == EliteType.GREMLIN_NOB

# Test 2: Lagavulin detection
context = create_mock_context(monsters=["Lagavulin"])
assert _detect_elite_type(context) == EliteType.LAGAVULIN

# Test 3: 3 Sentries detection
context = create_mock_context(monsters=["The Sentry", "The Sentry", "The Sentry"])
assert _detect_elite_type(context) == EliteType.THREE_SENTRIES

# Test 4: Slime Boss detection
context = create_mock_context(monsters=["Slime Boss"])
assert _detect_elite_type(context) == EliteType.SLIME_BOSS
```

### Scoring Tests

```python
# Test Lagavulin progressive scaling
assert _get_lagavulin_damage_weight(turn=5) == 5.0  # Hibernating
assert _get_lagavulin_damage_weight(turn=6) == 5.5  # 1st Siphon
assert _get_lagavulin_damage_weight(turn=9) == 7.0  # 2nd Siphon
assert _get_lagavulin_damage_weight(turn=12) == 8.0  # 3rd Siphon (capped)

# Test Sentries focus bonus
sequence_concentrated = [Attack(target=sentry_1, damage=20)]
sequence_spread = [Attack(target=sentry_1, damage=10), Attack(target=sentry_2, damage=10)]
assert score(sequence_concentrated) > score(sequence_spread)

# Test Slime AOE bonus
sequence_with_cleave = [PlayCard("Cleave", damage=8)]
sequence_without_aoe = [PlayCard("Strike_R", damage=6)]
assert score(sequence_with_cleave) > score(sequence_without_aoe)
```

## Rollback Plan

If unified system causes issues:

1. **Disable individual elite strategies**:
   - Comment out specific `_apply_*_strategy()` calls
   - Keep framework but disable problematic tactic

2. **Reduce A20 early aggression penalties**:
   - Turn 1 threshold: 8 → 5 damage
   - Turn 2 threshold: 15 → 10 damage
   - Remove early aggression entirely if too harsh

3. **Revert to old system**:
   - Keep only Gremlin Nob SKILL penalty (v3.3.1)
   - Remove all other elite-specific logic

## Future Enhancements

1. **Act 2 elites**: Slavers, Book of Stabbing (different mechanics)
2. **Adaptive targeting**: Learn which targeting works best for each elite
3. **Potion integration**: Auto-use attack potions on high-priority targets
4. **Health-based scaling**: Adjust aggression based on current HP % (low HP = more cautious)
