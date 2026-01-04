# add-gremlin-nob-skill-penalty Proposal

## Summary

Add card type-based scoring penalty for Gremlin Nob fights to discourage playing SKILL cards (which include most defensive cards). Gremlin Nob gains +1 Strength each time the player plays a SKILL card, making defensive plays actively detrimental.

## Why

**Problem**: AI loses Act 1 elite fights, particularly against Gremlin Nob. Analysis shows AI plays SKILL-type cards (Defend_R, Battle Trance, True Grit, etc.) against Gremlin Nob, which triggers its passive ability: **+1 Strength per SKILL card played**.

**Root Cause**:
- Gremlin Nob's mechanic: When player plays a SKILL → Nob gains +1 Strength permanently
- Current code only penalizes `block_gained` value (line 362: `-block_gained * 10`)
- This misses SKILL cards with other effects (draw cards, buffs, upgrades)
- Each SKILL makes Nob stronger → more damage → AI dies

**Impact**:
- Turn 1: AI plays 2 Defend → Nob has +2 Strength
- Turn 2: AI plays Battle Trance → Nob has +3 Strength
- Turn 3: Nob's Bludgeon deals 35 damage (32 + 3) → one-shots AI

**Solution**: Add card type detection to penalize ALL SKILL cards (not just block-gaining ones), while preserving ATTACK and POWER cards.

## Motivation

Current implementation penalizes `block_gained` against Gremlin Nob (line 362 in ironclad_combat.py), but this misses the core issue:

**Gremlin Nob's actual mechanic**: When player plays a SKILL card → Gremlin Nob gains +1 Strength → Damage increases permanently

**Problem with current approach**:
- `block_penalty = True` only penalizes the block value gained
- AI may still play SKILL cards for their effects (e.g., Battle Trance for draw, Armaments to upgrade)
- Each SKILL played makes Nob stronger, causing exponentially more damage in later turns

**Why this matters**:
- Most Ironclad defensive cards are SKILL type (Defend_R, Iron Wave doesn't count as it's ATTACK)
- Powers like Demon Form, Inflame are SKILL (but worth playing early)
- Drawing cards (Battle Trance) is SKILL (makes Nob stronger)

## Proposed Solution

Add a **card type penalty** in the scoring function that:
1. Detects when fighting Gremlin Nob
2. Identifies SKILL-type cards (except Powers worth playing early)
3. Applies a heavy penalty to discourage SKILL card plays
4. Allows exception for early Powers (Demon Form ≤ turn 3)

This complements the existing `block_penalty` by targeting the root cause (playing SKILLs) rather than just the symptom (gaining block).

## Scope

**In Scope**:
- Modify `_score_sequence()` in `ironclad_combat.py` to add SKILL card penalty
- Add card type detection using `card.type` (CardType.ATTACK, SKILL, POWER)
- Exclude early Powers from penalty (demon_form ≤ turn 3)
- Log when SKILL penalty is applied

**Out of Scope**:
- Changes to other elites (Lagavulin, Sentries, Slime Boss)
- Changes to card selection priority (CARD_PRIORITY_LIST)
- Changes to map routing priorities
- Changes to potion usage logic (separate change)

## Dependencies

- Depends on existing `_has_gremlin_nob()` function
- Depends on CardType enum in `spirecomm/spire/card.py`
- Related to (but not modifying) `elite-aggressive-mode` spec

## Impact

**Expected Benefits**:
- AI will avoid playing defensive SKILLs against Gremlin Nob
- AI will prioritize ATTACK cards even more strongly
- Faster kills → less damage taken overall

**Potential Risks**:
- May over-penalize useful SKILLs (e.g., Spot Weakness if it's SKILL)
- Need to verify Powers are excluded from penalty

**Mitigation**:
- Exclude Powers from penalty (they're worth the Strength gain)
- Add logging to track penalty application
- Test against actual Gremlin Nob fights

## Alternatives Considered

1. **Only rely on existing block_penalty**
   - Rejected: Doesn't address SKILL effects (draw, buff, etc.)

2. **Modify card priority list**
   - Rejected: Affects all fights, not just Gremlin Nob

3. **Add new combat mode**
   - Rejected: `elite-aggressive-mode` spec already exists

4. **Per-card whitelist of allowed SKILLs**
   - Rejected: Too complex, Powers exception covers most cases

## Success Criteria

1. AI plays significantly fewer SKILL cards against Gremlin Nob
2. AI prioritizes ATTACK cards (Strike, Pommel Strike, etc.)
3. AI still plays Powers (Demon Form) early in the fight
4. Win rate against Gremlin Nob improves (tracked in ai_game_stats.csv)
