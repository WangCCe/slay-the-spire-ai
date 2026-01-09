# Change: Add multi-turn combat lookahead

## Why
Beam search scoring is currently dominated by immediate damage/block and does not reflect cumulative damage taken over the next turns. This causes low-scaling fights (e.g., Blue Slaver) to favor attack-heavy lines that lose more HP overall.

## What Changes
- Add limited multi-turn enemy lookahead after a candidate sequence to estimate follow-on damage and debuff impact.
- Integrate lookahead penalties into beam search scoring when enhanced monster data is available.
- Gate lookahead depth based on fight complexity to keep latency within combat decision limits.

## Impact
- Affected specs: combat-simulation-enhancement
- Affected code: spirecomm/ai/heuristics/simulation.py, spirecomm/ai/heuristics/ironclad_combat.py
