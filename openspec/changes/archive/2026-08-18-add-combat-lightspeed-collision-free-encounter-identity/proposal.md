## Why

The 64-bucket hash experiment reduced the battle-index-9 reward regression from
`-0.702` to `-0.058`, but 42 observed encounters occupied only 31 buckets and
several unrelated bosses and normal fights collided. LightSTS already defines
a stable 63-entry `MonsterEncounter` name table, so the same 64 input columns
can carry collision-free identity without changing model width or training
budget.

## What Changes

- Add a source-bound collision-free encounter encoding as an opt-in alternative
  to the existing hash encoding.
- Reserve bucket 0 and map the 63 canonical LightSTS encounter names to buckets
  1 through 63 in enum order.
- Reject unknown names and bind the vocabulary hash and assignments in evidence.
- Run one same-budget experiment on fresh cohorts; no hash bucket retuning or
  live transfer is allowed.

Success requires all existing technical, aggregate, index 0, and index 9
guardrails. Failure retains r4 and ends this representation experiment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-training-smoke`: Allow a registered collision-free,
  source-bound encounter encoding in addition to the existing hash encoding.

## Impact

Only the simulator training runner, focused tests, OpenSpec contract, and
simulator-only evidence change. Network width remains 392 for both encounter
encodings. Production RL, CommunicationMod, and gameplay remain untouched.
