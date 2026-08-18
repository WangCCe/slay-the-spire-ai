## Why

The simulator smoke currently trains one-step Double DQN targets while keeping
the target network frozen for the bounded optimizer run. Fresh kill and combat
terminal rewards therefore cannot propagate through multiple newly collected
transitions during that run. The collision-free experiment produced positive
policy signals but also exposed two bounded incomplete training trajectories,
making complete-trajectory target semantics the next higher-value training
question.

## What Changes

- Add an opt-in discounted complete-trajectory return target for simulator-only
  combat training while preserving one-step TD as the default.
- Track transitions by source profile and exclude an entire trajectory from the
  return objective unless it reaches a supported terminal outcome.
- Bind target mode, discount, eligible/excluded trajectory counts, transformed
  target statistics, and source-transition identity in reports and checkpoints.
- Run one fresh matched one-step-versus-return experiment on identical complete
  trajectories. Success requires technical integrity plus aggregate, battle
  index 0, and battle index 9 guardrails against both `r4` and the matched
  one-step arm.
- Do not run the game, load a production checkpoint, retry an accessed cohort,
  or grant live transfer or promotion authority.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-training-smoke`: Allow a registered simulator-only
  complete-trajectory discounted-return target and bind its evidence.

## Impact

The simulator training runner, focused tests, OpenSpec contract, and bounded
LightSTS evidence are affected. The generic DQN trainer, default one-step
behavior, production RL checkpoints, CommunicationMod, and gameplay remain
unchanged. The success metric is a fresh matched policy-quality pass with no
technical blocker; otherwise `r4` remains the retained parent and the return
objective is not advanced.
