# Change: Improve power card scoring

## Why
Power-only turns can score the same as an empty sequence, causing the planner to skip playing beneficial powers such as Corruption. This produces suboptimal turns and contradicts expected strategic play.

## What Changes
- Add a baseline score bonus for POWER cards in the full combat scoring path.
- Add a POWER card bonus in FastScore so power cards are not filtered out early.
- Scale the baseline bonus by early-turn timing to favor setup powers earlier in a fight.

## Impact
- Affected specs: `openspec/specs/ai-combat/spec.md`
- Affected code: `spirecomm/ai/heuristics/ironclad_combat.py`, `spirecomm/ai/heuristics/simulation.py`
