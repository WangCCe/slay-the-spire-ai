## Context
The current RL action space allocates 10 targets per slot, which causes index collisions for potion actions. The project is adopting a new, explicitly specified RL action/observation space defined in `openspec/changes/redesign-rl-spaces/specs/rl-spaces/spec.md` with action_dim=133 and fixed slot counts.

## Goals / Non-Goals
- Goals:
  - Define a compact, collision-free action space with explicit target semantics.
  - Define a fixed observation layout with normalized features and stable categorical IDs.
  - Keep action masking deterministic across screen types.
- Non-Goals:
  - Backward compatibility with old RL checkpoints.
  - Changing non-RL heuristic agents.

## Decisions
- Action space uses fixed indices (0-132) with 6 target slots per card/potion (0=self/aoe, 1-5 monsters).
- Observation space uses 5 monster slots and 10 hand slots with fixed per-slot feature counts.
- Card and potion IDs are categorical inputs mapped via stable dictionaries; unknown maps to 0.
- New checkpoints are versioned and rejected if action/state dimensions mismatch.

## Risks / Trade-offs
- Incompatible with existing RL checkpoints; retraining is required.
- Compact action space may exclude low-frequency UI actions unless mapped to system actions.

## Migration Plan
1. Implement v2 encoders and action masks behind a new RL version flag.
2. Train a new model using the v2 action/observation spaces.
3. Switch default RL agent to v2 once training is validated.
4. Keep v1 path available for rollback during transition.

## Open Questions
- Confirm whether any additional keywords from `export/items.json` must be added beyond the current fixed list.
