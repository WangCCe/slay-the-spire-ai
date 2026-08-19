## Why

The promoted r16 policy still produced no victory in the fresh five-game live batch on 2026-08-19, including Act 1 boss deaths from healthy entry HP, while the matched LightSTS full-episode-return candidate underperformed its one-step control. A frozen-parent n-step target is the smallest training experiment that tests intermediate credit assignment without repeating either failed extreme.

## What Changes

- Add an opt-in LightSTS replay target mode that sums a bounded reward horizon and bootstraps from the frozen initialized parent policy.
- Require complete, contiguous trajectories and record horizon, discount, parent parameter identity, target summaries, and transformed transition identity in the report and checkpoint binding.
- Keep one-step TD as the default and keep discounted full-episode return unchanged.
- Validate the capability with deterministic unit coverage and a bounded matched simulator experiment against the existing one-step control.
- Success means technical completion plus a preregistered held-out improvement at the later battle indices without aggregate or early-battle regression; simulator success grants no live or promotion authority.
- Non-goals are production checkpoint loading, CommunicationMod changes, online gameplay training, reward redesign, simulator-mechanics claims, and automatic promotion.
- Rollback is removal of the opt-in mode and its report fields; the default one-step path remains behaviorally unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-training-smoke`: Add bounded frozen-parent n-step replay targets and their provenance contract.

## Impact

- `analysis_scripts/combat_lightspeed_training_smoke.py`
- `tests/test_combat_lightspeed_training_smoke.py`
- `openspec/specs/combat-lightspeed-training-smoke/spec.md`
- Simulator-only reports and checkpoints produced by the opt-in mode

No production gameplay configuration, checkpoint, native module, or CommunicationMod protocol changes are included.
