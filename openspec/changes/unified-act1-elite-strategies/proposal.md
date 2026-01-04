# unified-act1-elite-strategies Proposal

## Summary

Implement a unified elite combat strategy framework that applies specialized tactics for all Act 1 elites (Gremlin Nob, Lagavulin, 3 Sentries, Slime Boss) with A20-appropriate early aggression.

## Why

**Problem**: AI struggles against Act 1 elites at A20 because it doesn't apply elite-specific strategies early enough.

**Current State**:
- Gremlin Nob: SKILL penalty implemented (v3.3.1) ✅
- Other elites: Generic "elite" handling only (damage_weight = 4.0-5.0)
- No specialized tactics for Sentries (burst one) or Slime Boss (AOE)
- Lagavulin Siphon Soul progressive scaling not implemented

**A20 Reality**:
- All Act 1 elites are **DPS races** - you cannot win a battle of attrition
- Must kill elites in 3-5 turns before they become unmanageable
- Each elite has a unique mechanic that requires specific counterplay
- **Early aggression is critical** - cannot wait until turn 4-5 to start dealing damage

**Elite-Specific Challenges**:

1. **Gremlin Nob**: +1 Strength per SKILL card played → Already fixed with SKILL penalty
2. **Lagavulin**: Siphon Soul (-1 Dex, -1 Str) every 3 turns → Progressive difficulty scaling
3. **3 Sentries**: Two elites stack Strength simultaneously → Must burst down one ASAP
4. **Slime Boss**: Splits into 3 monsters at 50% HP → Needs AOE + controlled burst

**Gap**: AI treats all elites the same way, missing critical tactical differences.

## What Changes

### Code Changes

1. **spirecomm/ai/heuristics/ironclad_combat.py**:
   - Create `_apply_elite_strategy_override()` method
   - Detect elite type and apply specialized scoring modifiers
   - Implement elite-specific bonus/penalty system
   - Add early aggression for A20 (start damage from turn 1, not turn 4)

2. **Elite Strategy Framework**:
   - **Gremlin Nob**: -50 SKILL penalty (already implemented, preserve)
   - **Lagavulin**: Progressive damage_weight scaling (4.0 → 8.0 based on Siphon count)
   - **3 Sentries**: Single-target focus bonus (+50 for concentrating damage on one)
   - **Slime Boss**: AOE damage multiplier (×1.5 for Cleave/Thunderclap/Whirlwind)

3. **A20 Early Aggression**:
   - Reduce "preparation phase" from 3 turns → 1 turn
   - Apply damage bonuses from turn 1-2, not turn 4-5
   - Penalize low-damage sequences in early turns (turn 2+)

### Spec Changes

- **elite-aggressive-mode**: ADDED "Unified Act 1 Elite Strategy Framework" requirement
  - Elite type detection system
  - Elite-specific scoring modifiers
  - A20 early aggression rules
  - Individual elite tactics (Nob, Lagavulin, Sentries, Slime)
