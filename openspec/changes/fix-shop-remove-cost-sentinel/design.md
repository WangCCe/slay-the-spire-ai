## Context

The finalized reachable-event native gate failed on the first seed while
hydrating a shop snapshot. `sts_lightspeed` initializes a nonnegative card
removal cost, sets it to `-1` after `buyCardRemove`, and rejects card-removal
actions whenever that sentinel is present. The adapter preserves the raw value,
but the bridge currently passes it through a general nonnegative validator.

The repair must preserve fail-closed bridge behavior and Current's exact
non-combat entrypoint. It must not revise the consumed native result or use a
new cohort as an implementation test.

## Goals / Non-Goals

**Goals:**

- Represent the simulator's exact `-1` sentinel as removal unavailable in a
  hydrated `ShopScreen`.
- Prove consistency between the sentinel and the legal candidate set.
- Preserve ordinary nonnegative cost hydration and source non-mutation.
- Keep invalid negative and contradictory states field-specific and fail-closed.

**Non-Goals:**

- Changing Current's shop ranking, purge budget, purchase sequence, or mapping.
- Changing the native adapter or simulator source.
- Reinterpreting or retrying the consumed compatibility cohort.
- Running gameplay, a fresh native cohort, model fitting, or RL training.

## Decisions

### Normalize the valid sentinel only at the hydration boundary

Add a small helper that accepts the raw cost and the candidate-derived
`purge_available` flag. A nonnegative integer is preserved. Exactly `-1` is
accepted only when removal is unavailable and is normalized to `0` for the
typed `ShopScreen`; Current ignores that cost whenever `purge_available` is
false.

Alternative considered: store `-1` directly in `ShopScreen`. Rejected because
Communication Mod hydration defaults an absent purge cost to `0`, and retaining
a negative value needlessly expands the Current-facing state contract.

### Fail contradictory native states closed

If `-1` appears alongside a legal `remove_card` candidate, emit a dedicated
bridge blocker before Current executes. Values below `-1`, booleans,
non-integers, and missing values retain the existing nonnegative-integer
failure. Positive costs without a legal candidate remain valid because native
legality also depends on current gold.

Alternative considered: treat every negative value as unavailable. Rejected
because only `-1` is proven by the bound simulator source.

### Keep verification source-only

Add direct hydration regressions and run focused bridge, successor evaluator,
adapter, and historical compatibility tests plus the repository commit gate.
No native module or seed is needed to prove this local contract.

## Risks / Trade-offs

- [The sentinel masks an inconsistent legal action] -> Reject `-1` whenever a
  remove candidate exists.
- [A normalized zero affects policy] -> Expose it only with
  `purge_available == false`, which gates all Current purge-cost use.
- [Future simulator sentinel behavior changes] -> Keep the accepted value exact
  and source-backed; other negatives continue to fail.
- [A source-only pass is mistaken for native compatibility] -> Preserve all
  downstream authority as false and require a separate future registration.

## Migration Plan

1. Publish and push this plan.
2. Add failing hydration regressions.
3. Implement the helper and rerun focused and commit-gate verification.
4. Publish a source-only closeout, sync the bridge spec, archive, and push.

Rollback removes the helper and regressions. It does not alter either consumed
native cohort or any frozen artifact.

## Open Questions

None. The exact sentinel and legal-action condition are proven by the bound
simulator source used by the failed cohort.
