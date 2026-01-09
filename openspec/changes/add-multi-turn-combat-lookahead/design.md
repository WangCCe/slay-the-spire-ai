## Context
Beam search currently evaluates a single player turn and applies a static future-damage heuristic. This misses the compound damage impact of enemy intents over the next 1-2 turns, especially for low-scaling monsters that reward defensive play.

## Goals / Non-Goals
- Goals: estimate follow-on damage for the next 1-2 enemy turns after a candidate sequence; use wiki move prediction when available; keep decision latency within existing bounds.
- Non-Goals: full multi-turn player+enemy minimax, exhaustive state simulation, or new external dependencies.

## Decisions
- Decision: add a lightweight enemy-only lookahead that applies predicted monster moves (damage + Weak/Frail/Vulnerable debuffs) to the post-sequence state and produces a penalty score.
- Decision: cap lookahead depth to 2 turns and reduce to 1 on simple fights or when predictions are unavailable.

## Risks / Trade-offs
- Added compute time during beam search; mitigated by depth gating and no-player-action lookahead.
- Prediction errors from wiki data can skew penalties; mitigated by falling back to current intent when prediction is missing.

## Migration Plan
- Implement behind default-on path in beam search scoring.
- Validate via logs on known seeds and ensure latency stays within target.

## Open Questions
- Exact penalty weight vs existing W_DEATHRISK scaling.
