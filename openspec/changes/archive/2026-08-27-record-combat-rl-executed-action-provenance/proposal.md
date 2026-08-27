## Why

Fresh production-r16 replay contains 3,433 executed transitions, but every `anchor_to_executed_action` value is false even though the matched live canary logs roughly 400 `ENERGY_GUARD` replacements per ten-game arm. On the same fresh replay, frozen-parent greedy actions agree with executed actions on only 35.97% of rows, so later anchored training cannot distinguish direct parent actions from outer-guard replacements and fallback takeover actions.

## What Changes

- Record whether each pending live RL transition retained the RL-proposed action or was bound to a different action emitted by an outer safety guard.
- Mark actions created during fallback takeover, when no matching RL proposal exists for that state, as executed-action anchor overrides.
- Persist the provenance through the existing replay schema and pass it into the existing parent-anchor override path.
- Add regression coverage for unchanged actions, guard replacements, fallback-only actions, invalid actions, and replay round trips.
- Validate the fix with a bounded fresh zero-update production-r16 replay collection whose override count is nonzero and reconciles with retained guard/takeover evidence.
- Do not train, tune, promote, alter guard decisions, or change production checkpoint weights in this change.

Success requires focused tests, the qualified commit gate, and a fresh replay report showing that every marked row is legal while direct unchanged RL actions remain unmarked. The rollback boundary is the collection-side provenance assignment: replay schema version 1 remains loadable as all-false and runtime action selection must remain byte-for-byte unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-parent-policy-anchor`: require live replay collection to mark rows whose executed action differs from, or has no corresponding, RL proposal so the existing executed-action anchor override can be used without contradictory labels.

## Impact

- `spirecomm/ai/rl/v2/agent.py`: pending-transition provenance and replay insertion.
- `tests/test_rl_v2_training_transitions.py`: collection and persistence regressions.
- Fresh replay evidence under `reports/`; no CommunicationMod protocol or action-selection behavior changes.
