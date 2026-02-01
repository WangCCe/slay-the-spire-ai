# Change: Update RL reward shaping for combat and progression

## Why
Current RL reward shaping has mismatches with the intended spec and encourages suboptimal behavior (e.g., misaligned victory signals, overly strong end-turn penalties, and ambiguous vulnerable/kill rewards).

## What Changes
- Remove effective block reward from the spec and align implementation to HP loss only.
- Relax per-turn penalty to -0.05 and remove extra end-turn penalties.
- Change kill rewards to a per-combat diminishing formula: base / (1 + kill_index).
- Remove damage reward cap and compute effective damage only (no overkill).
- Apply vulnerable bonus only to damage dealt to vulnerable targets.
- Enforce enemy strength gain penalty as -1.0 * strength gained (no cap).
- Clarify combat-win (+20) vs run-victory (+500) signals.

## Impact
- Affected specs: rl-reward (new capability)
- Affected code: spirecomm/ai/rl/reward.py, REWARD_FUNCTION.md
