# Shop Remove-Cost Sentinel Repair Closeout

Date: 2026-08-03

## Result

The source-only bridge repair for the native shop card-removal sentinel is
complete. `hydrate_game` now treats exactly `remove_cost == -1` as removal
already consumed only when the validated legal candidate set contains no
`remove_card` action. It exposes `purge_available == false` and normalizes the
typed `ShopScreen.purge_cost` to `0`, which is policy-inert behind that flag.

The bridge continues to preserve every nonnegative cost. It rejects `-1` when
a legal remove candidate exists and retains the existing field-specific
failure for values below `-1`, booleans, non-integers, and missing values. The
snapshot and candidate records remain byte-for-byte unchanged.

The exact Current session regression proves that an empty post-removal shop
maps to the sole legal `shop:leave` action without fallback or tracker use.

## Source Evidence

- `sts_lightspeed/src/game/Shop.cpp` sets `removeCost = -1` immediately after
  `buyCardRemove`.
- `sts_lightspeed/src/sim/search/GameAction.cpp` exposes card removal only when
  `removeCost != -1` and current gold covers the cost.
- The bound API v3 adapter serializes `gc_.info.shop.removeCost` without
  rewriting the sentinel.
- The consumed native failure remains
  `invalid_nonnegative_integer: shop remove_cost` with zero completed rows.

Implementation commit:
`119e33b678a9917c14affb670572874a5ad4f9aa`.

## Verification

- Red proof before implementation: `2 failed, 7 passed` with both failures at
  the old unconditional nonnegative validator.
- Sentinel hydration and exact Current-session regressions:
  `10 passed, 52 deselected in 0.74s`.
- Focused bridge, successor evaluator, reachable resolver, adapter, and
  historical compatibility regressions: `135 passed, 5 skipped in 10.27s`.
- Relevant Python compilation: passed.
- Repository commit gate: `3502 passed, 11 skipped in 237.70s`; gate total
  `241.07s`.
- Strict global OpenSpec validation before spec sync: `60 passed, 0 failed`.
- Strict global OpenSpec validation after spec sync: `60 passed, 0 failed`.
- Strict global OpenSpec validation after archive: `59 passed, 0 failed`.

The completed change is archived at
`openspec/changes/archive/2026-08-03-fix-shop-remove-cost-sentinel`.

## Frozen Failure Boundary

The successor registration, seed ledger, artifact manifest, journal, and
result remain byte-identical to their archived evidence:

- registration SHA-256:
  `c22c0f2346ace8c982e1f0701cb8014e92333858531a91e7d566f762268c4d10`;
- seed-ledger SHA-256:
  `962361229fac2ab1b6f72c7a350a2563c24ef163db7fa61d524cf9ee564db12a`;
- artifact-manifest SHA-256:
  `79aa0771cc162023dcfa898e13100699ccf95750ca0ea7b497337bfd40dd5148`;
- journal: finalized with seeds `7100..7107` consumed; and
- verdict: `reachable_event_native_compatibility_failed`.

This implementation does not repair, retry, or reinterpret that result.

## Authority Boundary

Gameplay, native compatibility, baseline-floor, target-supported outcome,
reward, model, OPE, formal-RL, training, qualification, loading, and promotion
authority all remain false. No native module was loaded, no seed was accessed,
no Communication Mod or gameplay process was launched, and no model or trainer
ran in this change.

## Project Direction

Formal non-combat RL remains `NO-GO`. Before spending another untouched native
cohort, the next step should audit the adjacent shop inventory sentinel:
`sts_lightspeed` sets sold card, relic, and potion prices to `-1`, while the
bridge currently rejects negative shop item prices. That is a separate
contract surface and was not changed here.

Any repair must first prove whether sold entries remain serialized, how their
absence from legal candidates should map to Current's visible shop inventory,
and which inconsistent combinations must fail closed. Only after the bounded
shop-domain audit is complete should the project decide whether another
preregistered native compatibility cohort is justified.
