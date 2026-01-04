# Technical Design: Gremlin Nob SKILL Card Penalty

## Problem Analysis

### Gremlin Nob's Mechanic

When the player plays a SKILL card, Gremlin Nob gains +1 Strength. This includes:
- Defend_R (basic defense)
- True Grit (defend + exhaust)
- Shrug It Off (defend + draw)
- Battle Trance (draw 3)
- Armaments (upgrade cards in hand)
- Spot Weakness (conditional Strength - **if SKILL**)
- Most non-attack, non-power cards

**Impact**:
- Turn 1: Play 2 Defend → Nob has +2 Strength → +2 damage on all attacks
- Turn 2: Play Battle Trance → Nob has +3 Strength → +3 damage
- Turn 3: Nob's Rage attack deals 8 + 3 = 11 damage
- Turn 4: Nob's Bludgeon deals 32 + 3 = 35 damage (one-shots most A20 builds)

### Current Implementation Gap

```python
# Line 337-341 in ironclad_combat.py
elif has_gremlin_nob or has_lagavulin or has_cultist:
    damage_weight = 4.0
    block_penalty = True

# Line 359-362
if block_penalty and block_gained > 0:
    score -= block_gained * 10
```

This penalizes the **block value** (5 block × 10 = 50 points lost) but doesn't penalize:
- SKILL cards that don't gain block (Battle Trance for draw)
- SKILL cards with minimal block (True Grit: 5 block but exhausts card)
- Powers that are worth the Strength tradeoff

## Solution Design

### Card Type Detection

Use existing `CardType` enum from `spirecomm/spire/card.py`:

```python
class CardType(Enum):
    ATTACK = 1  # Safe to play (Iron Wave, Pommel Strike, etc.)
    SKILL = 2   # DANGER: Triggers Nob's Strength gain
    POWER = 3   # Safe (Demon Form, Inflame worth playing early)
    STATUS = 4  # Usually irrelevant
    CURSE = 5   # Usually irrelevant
```

### Penalty Application

Add to existing scoring loop (around line 375 in ironclad_combat.py):

```python
# 5. Strategic bonus for card types
for action in sequence:
    if isinstance(action, PlayCardAction):
        card = action.card

        # NEW: Gremlin Nob SKILL penalty
        if has_gremlin_nob:
            if hasattr(card, 'type'):
                from spirecomm.spire.card import CardType
                if card.type == CardType.SKILL:
                    # Powers are handled separately below
                    score -= 50  # Heavy penalty for any SKILL
                    logger.info(f"[SKILL_PENALTY] -50 for {card.card_id} against Gremlin Nob")

        # Powers are valuable early (existing logic, preserve)
        if card_id == 'Demon Form' and context.turn <= 3:
            score += 50  # Outweighs penalty
```

### Why -50 Penalty?

**Reasoning**:
1. **Overwhelms card benefits**:
   - Battle Trance: +45 (3 cards × 15) - 50 = -5 net
   - Armaments: maybe +30-40 for upgrade - 50 = negative
   - Defend_R: 10 (5 block × 2) - 50 = -40

2. **Preserves early Powers**:
   - Demon Form (turn 1-3): +50 bonus - 50 penalty = 0 net
   - Still worth playing for long-term Strength scaling

3. **ATTACK cards unaffected**:
   - Iron Wave: 10 (block) + 15 (damage) = +25
   - Pommel Strike: 30+ (damage) + 15 (draw) = +45
   - Strike: 18+ (damage) = positive

### Exceptions

**Powers excluded**:
- Demon Form: Worth playing early (already has +50 bonus for turn ≤ 3)
- Inflame: Worth the +2 Strength tradeoff
- Other Powers: Long-term value outweighs Nob's Strength gain

**Implementation**:
- Check `card.type == CardType.SKILL` before penalty
- Powers are `CardType.POWER`, so they're auto-excluded
- Demon Form gets explicit +50 to offset any future changes

## Testing Strategy

### Unit-Level Verification

1. **Card Type Detection**:
   ```python
   # Test known cards
   assert Defend_R.type == CardType.SKILL
   assert Iron Wave.type == CardType.ATTACK
   assert Demon Form.type == CardType.POWER
   ```

2. **Scoring Impact**:
   ```python
   # Gremlin Nob fight
   play_defend = score([PlayCardAction(Defend_R)])
   play_strike = score([PlayCardAction(Strike_R)])

   assert play_strike > play_defend  # Attack preferred
   assert play_defend < 0  # Defend penalized
   ```

### Integration Testing

Run AI against Gremlin Nob:
- Count SKILL cards played per fight
- Compare win rate before/after
- Check `ai_debug.log` for penalty messages

### Edge Cases

1. **Powers with SKILL-like effects**:
   - Spot Weakness: Needs testing (is it SKILL or POWER?)
   - If SKILL: May need whitelist exception

2. **ATTACK cards with SKILL effects**:
   - Iron Wave: ATTACK type → no penalty ✅
   - Reaper: ATTACK type → no penalty ✅

3. **Multi-card sequences**:
   - Defend + Strike: Penalty only on Defend
   - Battle Trance + 3 Attacks: Penalty only on Battle Trance

## Rollback Plan

If penalty is too harsh:
1. Reduce penalty from -50 to -30
2. Add whitelist for specific SKILLs
3. Make penalty conditional on turn number

If win rate doesn't improve:
1. Check logs for penalty application
2. Verify card type detection working
3. May need additional changes (potion usage, targeting)

## Future Enhancements

1. **Turn-based penalty scaling**:
   - Turn 1-2: -30 (early game, some SKILLs okay)
   - Turn 3+: -50 (late game, all SKILLs bad)

2. **Whitelist for beneficial SKILLs**:
   - Spot Weakness (if SKILL type)
   - Disarm (useful debuff)

3. **Dynamic penalty based on Nob's Strength**:
   - Penalty increases as Nob's Strength increases
   - Discourages SKILLs even more when Nob is already strong

For now, keeping it simple: flat -50 for all SKILLs (except Powers with existing bonuses).
