## Why

The action-relative matched live gate exposed a repeatable safety-boundary gap:
on seed 6 the candidate replaced a guard-selected lethal `Bash+` with `Defend`
while neither Louse was attacking, extending the fight from two turns to four
and increasing damage from zero to ten. A second common state on seed 8 also
replaced lethal `Carnage` with `Defend+`, so the fixed late safety policy must
preserve target-lethal guard actions before another candidate is evaluated live.

## What Changes

- Detect when the completed guard action is a legal attack that kills its
  selected living target in the current state.
- Veto an action-relative takeover when that guard is target-lethal and the
  proposed candidate does not itself kill a living target.
- Record a stable veto reason while preserving existing fail-closed behavior,
  candidate authority, and trace completeness.
- Add regressions for the observed multi-monster lethal-attack-versus-defense
  boundary and for allowed lethal-to-lethal or nonlethal takeovers.
- Success means the observed seed-6 state retains `Bash+` without broadly
  disabling candidate takeovers. This change does not retrain, retune, replay
  the closed cohort, launch gameplay, or promote a checkpoint.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-action-relative-matched-live-gate`: require the fixed safety veto
  to preserve a guard-selected target-lethal attack from a nonlethal candidate.

## Impact

The change is limited to the late candidate safety decision in
`spirecomm/ai/rl/agent.py`, its focused tests, and the action-relative matched
gate contract. It changes no artifact schema, model, threshold, production
configuration, or ordinary parent behavior. Rollback is removal of the new
veto predicate and its contract while retaining the existing candidate runtime.
