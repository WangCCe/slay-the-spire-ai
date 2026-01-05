# Fix Multi-Monster Scoring in Beam Search

## Why

The beam search combat simulator's final outcome score (`calculate_outcome_score`) does not account for multi-monster scenarios, causing the AI to prioritize defense over damage when facing 3+ monsters. This leads to suboptimal decisions and a 24.5% death rate on Floor 6 multi-enemy fights.

## What Changes

- Add monster count detection to `calculate_outcome_score()` in `simulation.py`
- Apply adaptive damage weighting based on monster count (1.0× for 1 monster, 1.3× for 2 monsters, 1.8× for 3+ monsters)
- Add AOE card bonus points in multi-monster scenarios (+20 for 2 monsters, +40 for 3+ monsters)
- Apply Floor 6-7 special AOE priority (additional 0.2-0.4× multiplier) to reduce death spike
- Add comprehensive logging for multi-monster score adjustments

## Impact

**Affected specs:**
- `ai-combat` - Add multi-monster scoring requirements to outcome score calculation

**Affected code:**
- `spirecomm/ai/heuristics/simulation.py:679-682` - Modify `calculate_outcome_score()` to apply monster-count-aware damage weighting
- `spirecomm/ai/statistics.py:90` - Update AI version to 3.5.1-multi-monster-scoring

## Problem Analysis

### Current Issue

The beam search combat planner uses a two-stage scoring system where FastScore (Stage 1) has multi-monster bonuses, but Outcome Score (Stage 2) uses flat damage weighting without monster count consideration. This causes defensive cards to outscore damage cards in multi-monster fights.

**Evidence from 92 games (v3.4.7-fix-player-hp)**:
- Floor 6 deaths: 23 (24.5%) - highest death floor
- Root cause: Beam search doesn't prioritize damage when facing 3 monsters
- Result: AI prioritizes defense over damage, gets focused down

### Why This Matters

FastScore applies multi-monster bonuses during candidate selection, but the final evaluation (Outcome Score) doesn't account for them. This creates a scoring mismatch where AOE cards look good during filtering but lose to defensive cards during final ranking.
