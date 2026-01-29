# Change: Improve RL card reward learning signal

## Why
The RL agent currently does not encode card reward options in its state and receives a weak, heuristic-only reward signal.
Adding explicit card option features and stronger choice rewards should help the agent learn better card selection.

## What Changes
- Extend the RL state encoder with card reward option features (cost/type/rarity/damage/block/etc.).
- Reuse reserved feature slots without changing the overall state dimension.
- Strengthen card choice rewards using relative scoring versus available options.

## Impact
- Affected specs: rl-card-reward-learning (new)
- Affected code: `spirecomm/ai/rl/state_encoder.py`, `spirecomm/ai/rl/reward.py`
