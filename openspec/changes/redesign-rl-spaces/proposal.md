# Change: Redesign RL Action and Observation Spaces (v2)

## Why
The current RL action encoding assumes 10 targets per slot, which causes index collisions for potion actions. We are redesigning the RL action and observation spaces to be consistent, compact (133 actions), and explicitly specified for a new model.

## What Changes
- Define a new action space layout with fixed indices (action_dim=133) and explicit target semantics.
- Define a new observation space layout (~307 dims) with fixed slot counts and normalized features.
- Add strict action masking rules based on screen type and available commands.
- Introduce stable categorical ID mappings for cards and potions for embedding inputs.
- **BREAKING**: New model is incompatible with the old RL action/state encodings.

## Impact
- Affected specs: `rl-spaces`
- Affected code: `spirecomm/ai/rl/action_encoder.py`, `spirecomm/ai/rl/state_encoder.py`, `spirecomm/ai/rl/network.py`, `spirecomm/ai/rl/trainer.py`, new RL data/mapping utilities
- Training: Requires new model training and checkpoint format/versioning
