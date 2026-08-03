## Why

The consumed reachable-event native compatibility cohort failed before Current
evaluation with `invalid_nonnegative_integer: shop remove_cost`. The bound
simulator source proves that `remove_cost == -1` is the valid sentinel after a
shop card removal, while the bridge currently rejects every negative value.

## What Changes

- Add an exact bridge contract for the native shop remove-cost sentinel.
- Accept `remove_cost == -1` only when the legal candidate set contains no
  `remove_card` action, and hydrate Current with removal unavailable and a
  policy-inert normalized cost.
- Continue to reject values below `-1`, non-integers, and a `-1` sentinel paired
  with a legal remove action.
- Add regressions for valid sentinel hydration, contradictory candidates,
  invalid negative values, source non-mutation, and ordinary nonnegative cost
  behavior.
- Publish a source-only closeout. Do not run another native cohort, launch
  gameplay, alter shop scoring, or start training in this change.

Success means the sentinel cases pass the exact hydration contract while all
focused bridge, adapter, historical compatibility, and repository commit-gate
tests remain green. Rollback removes only this additive validation helper,
tests, and spec delta; the consumed `7100..7107` failure remains immutable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-current-policy-simulator-bridge`: Define exact native shop
  `remove_cost == -1` hydration and fail-closed consistency rules.

## Impact

- `analysis_scripts/noncombat_current_policy_simulator_bridge.py`
- `tests/test_noncombat_current_policy_simulator_bridge.py`
- The bridge capability spec and a source-only closeout report
- No Communication Mod configuration, gameplay policy, simulator source,
  reward, model, training, seed ledger, or native execution changes
