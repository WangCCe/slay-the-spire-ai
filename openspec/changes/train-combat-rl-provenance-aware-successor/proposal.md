## Why

The fresh action-selection parity replay is the first combat corpus whose direct actions exactly match production-r16 eval-mode decisions while retaining legal executed-action provenance for outer-policy takeovers. It is now suitable for one bounded training attempt, but the repository lacks a deterministic full-network successor runner that consumes those labels without granting training-corpus evidence promotion authority.

## What Changes

- Add a deterministic offline runner that fits one full-network RL v2 successor from the immutable parity replay using the existing one-step TD and provenance-aware parent-policy anchor objectives.
- Freeze a single recipe before execution: combat-group 80/20 development split, parent anchor weight `1.0`, learning rate `1e-4`, batch size `128`, and `256` optimizer updates.
- Report train and validation TD fit, parent/candidate action disagreement, provenance-aware anchor-label agreement, positive-energy End Turn drift, parameter movement, objective losses, and input/output hashes.
- Permit a separate fresh holdout only when the candidate has finite metrics, improves validation TD fit, does not reduce provenance-aware label agreement, changes `2%..15%` of validation greedy actions, and increases positive-energy End Turn decisions by at most two.
- Retain every completed result as development evidence, but forbid same-corpus tuning, gameplay qualification, promotion, or production checkpoint replacement from this change.

## Capabilities

### New Capabilities

- `combat-rl-provenance-aware-successor`: Deterministic bounded training and evidence gates for a full-network combat RL successor fitted from a parity-qualified executed-action replay.

### Modified Capabilities

None.

## Impact

- Adds one analysis runner and focused tests; the production agent and CommunicationMod protocol are unchanged.
- Reads only `reports/combat_rl_action_selection_parity_replay_20260828_r1/rl_combat_model_ep10_steps2109.pth`, bound to SHA-256 `302a7350a7e216ea548025ac4cb588c1ea77872328ccef977f94feab65e03fb4`.
- Writes a new run-scoped report directory and development-only candidate. It does not start the game, modify production checkpoints, or treat training-corpus outcomes as policy-quality evidence.
- Success means one immutable candidate passes every preregistered development gate and becomes eligible only for a separately registered fresh holdout. Otherwise production r16 remains authoritative and no alternate recipe is run on this corpus.
