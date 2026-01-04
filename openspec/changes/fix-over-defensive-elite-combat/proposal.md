# Proposal: Fix Over-Defensive Elite Combat Behavior

## Summary

Fix the Ironclad OptimizedAgent's **over-defensive behavior** in Act 1 elite fights by implementing aggressive combat modes that prioritize fast kills over defense. The AI currently plays too cautiously, prolonging elite fights which leads to taking more damage overall due to enemy scaling mechanics.

## Problem Statement

**Current Situation:**
- **User Feedback**: "AI在过度防御" (AI is over-defending)
- **Recent Attempt**: Commit f91ddd9 reduced BLOCK_WEIGHT from 5.0 → 1.5 to prioritize attacking
- **Result**: Still insufficient - AI continues to prioritize defense in elite fights

**Root Causes:**
1. **Static defensive mindset**: Current weights don't distinguish between regular fights and elite DPS races
   - Block still valued at 1.5 points per block
   - Damage valued at 2.0 points per damage
   - Not enough gap to favor aggressive play

2. **Elite fight misunderstanding**: AI treats elites like regular monsters
   - Doesn't recognize that elites are DPS checks, not attrition fights
   - Doesn't account for elite scaling mechanics (Gremlin Nob, Slaver combo, etc.)
   - Plays defensively when it should rush to kill

3. **Insufficient damage prioritization**: Current weights still favor defense in many scenarios
   - Example: Defend_R (5 block) = 7.5 points vs Strike_R (6 damage) = 12 points
   - Gap isn't large enough - AI still plays defense "just to be safe"

4. **No aggressive mode**: No context-aware strategy switching
   - AI plays the same way against Fungi Beast as Gremlin Nob
   - Doesn't recognize when fast kill is mandatory

## Why Current Approach Fails at High Ascension

Based on community research ([sources below](#sources)):

**Act 1 Elite Mechanics:**
- **Low HP pools, high scaling**: Elites have ~80-120 HP but scale damage/abilities rapidly
- **DPS checks**: You cannot outlast elites - they become exponentially more dangerous each turn
- **Resource efficiency**: Every turn spent defending is damage not dealt, extending the fight

**Why Defense Loses:**
- **Gremlin Nob**: Gains strength each time attacked, deals massive AOE damage if not killed quickly
- **Slavers**: Combo chain attacks that scale if both survive
- **Sentry**: Multiple targets with powerful intents that require fast elimination

**Community Consensus:**
> "Act 1 elites are DPS checks - you cannot win a battle of attrition. Any card plays used for defense are generally suboptimal."
> — [How to Beat the Act 1 Elites EVERY TIME!](https://www.youtube.com/watch?v=ZCUB2c-24ng)

> "Defense is low priority until you have at least 2-3 good damage cards. Be aggressive in Act 1."
> — [Ironclad A20 Deck Guide](https://steamcommunity.com/sharedfiles/filedetails?id=2429404117)

## Proposed Solution

Implement **context-aware aggressive combat modes** that dramatically prioritize damage in elite fights while maintaining balanced play in regular combats.

### Key Changes

1. **Elite-specific damage boost** (New capability: `elite-aggressive-mode`)
   - Increase DAMAGE_WEIGHT to 4.0-5.0 in elite fights (2-2.5× current value)
   - Decrease BLOCK_WEIGHT to 0.5 in elite fights (33% of current value)
   - Creates 10:1 damage:block ratio (from 1.33:1)

2. **Fast-kill detection** (New capability: `dps-check-detection`)
   - Detect when enemy is "elite" or has scaling mechanics
   - Detect when player can kill in 1-2 turns (burst damage potential)
   - Switch to aggressive mode when kill is achievable

3. **Monster threat profiling** (New capability: `scaling-threat-evaluation`)
   - Identify enemies with dangerous scaling (strength gain, multihit, combo)
   - Apply additional "urgency bonus" to damage output
   - Penalty for prolonging fight against scaling enemies

4. **Turn-by-turn aggression scaling** (New capability: `progressive-aggression`)
   - Turn 1-2: Maximum aggression (rush to kill)
   - Turn 3+: Evaluate based on remaining HP
   - If enemy HP < 30%: Hyper-aggressive (finish them off)
   - If enemy HP > 50% after turn 3: Defensive pivot (plan failed)

## Affected Components

- **spirecomm/ai/heuristics/simulation.py**:
  - Add elite/scaling detection to scoring
  - Implement mode-based weight selection (aggressive vs balanced)
  - Add "urgency bonus" for fast kills

- **spirecomm/ai/heuristics/ironclad_combat.py**:
  - Update scoring to prioritize lethal damage
  - Add elite fight detection
  - Implement aggressive mode weights

- **spirecomm/ai/decision/base.py**:
  - Add enemy threat profiling (scaling detection)
  - Identify elite monster types
  - Add "killable in 2 turns" calculation

## Expected Outcomes

- **Immediate**: AI kills Act 1 elites 2-3 turns faster on average
- **Short-term**: Take less total damage in elite fights (despite being more "aggressive")
- **Long-term**: Higher win rate in Act 1, more successful runs at A16-A20

## Success Metrics

1. **Elite fight duration**: Reduced from 6-8 turns → 3-5 turns
2. **Damage taken**: Lower total damage in elite fights (despite less blocking)
3. **Win rate**: Increased percentage of elite victories at A16-A20
4. **Death to elites**: Fewer deaths caused by elite fights

## Why This Works

**Math Example - Gremlin Nob (A20, 92 HP):**

*Current (Defensive) Approach:*
- Turn 1: Iron Wave (5 block, 5 dmg), Defend (5 block)
- Turn 2: Bash (8 dmg), Strike (6 dmg)
- Turn 3: Strike (6 dmg), Defend (5 block)
- Total damage: 25 dmg over 3 turns → Nob enraged → AI dies

*Proposed (Aggressive) Approach:*
- Turn 1: Clothesline (12 dmg), Bash (8 dmg) + Vulnerable, Strike (6 dmg)
- Turn 2: Heavy Blade (14 dmg), Strike (6 dmg with Vulnerable)
- Total damage: 46 dmg over 2 turns → Nob nearly dead → AI wins

**Key Insight**: By NOT defending, the AI deals **21 more damage** in the same timeframe. Even if Nob deals 20 damage to the AI, that's better than Nob gaining strength and AOEing for 40+ damage.

## Alternatives Considered

1. **Just increase DAMAGE_WEIGHT globally**:
   - **Rejected**: Would make AI too aggressive in regular fights, wasting HP
   - **Better approach**: Context-aware aggression (elites only)

2. **Just decrease BLOCK_WEIGHT globally**:
   - **Rejected**: AI tried this (commit f91ddd9), still not aggressive enough
   - **Better approach**: Elite-specific mode switching

3. **Hardcode elite-specific strategies**:
   - **Rejected**: Too brittle, wouldn't generalize to new content
   - **Better approach**: Generic threat detection system

## Related Changes

- Partially reverses: `improve-high-ascension-survival` (deleted proposal)
- Builds on: commit f91ddd9 (reduce defense weight) - amplifies the aggressive direction
- Related to: `optimize-beam-search-combat` (archived, created ai-combat spec)

## Risks and Mitigations

**Risk**: AI becomes too aggressive, takes too much damage in regular fights
**Mitigation**: Only apply aggressive weights in elite/scaling fights, not regular combats

**Risk**: AI overcommits and dies trying to rush elite
**Mitigation**: Progressive aggression - if not close to kill by turn 3, pivot to defense

**Risk**: Fails against certain elite patterns (e.g., high defense elites)
**Mitigation**: Threat profiling detects enemy armor/buff patterns and adjusts

## Sources

Community research on high ascension elite combat:

- [How to Beat the Act 1 Elites EVERY TIME! - YouTube](https://www.youtube.com/watch?v=ZCUB2c-24ng)
- [High Ascension levels Ironclad - Reddit](https://www.reddit.com/r/slaythespire/comments/155zllv/high_ascension_levels_ironclad_what_is_most/)
- [Ironclad A20 Deck Guide - Steam Community](https://steamcommunity.com/sharedfiles/filedetails?id=2429404117)
- [How to Crush Elites - YouTube](https://www.youtube.com/watch?v=KlA-bwkn-_w)

## Implementation Notes

- **Backward compatible**: Regular fights use balanced weights
- **Testable**: Can verify elite fight performance specifically
- **Tunable**: Damage multipliers can be adjusted based on testing
- **Focused scope**: Only affects combat decision weights, no card selection or map routing changes
