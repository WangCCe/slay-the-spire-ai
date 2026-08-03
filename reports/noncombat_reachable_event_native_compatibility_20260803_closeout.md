# Reachable Event Native Compatibility Closeout

Date: 2026-08-03

## Result

The one-shot reachable-event API v3 native cohort is complete and preserved
with the structural verdict `reachable_event_native_compatibility_failed`.
The registered seeds `7100..7107` are consumed and are not eligible for retry,
replacement, wider limits, or reinterpretation as policy-quality evidence.

The first execution blocker was:

- reason: `invalid_nonnegative_integer`;
- detail: `shop remove_cost`;
- completed deterministic seed rows: `0`;
- canonical category counts: `0` for route, shop, event, and card reward; and
- execution journal: finalized with the complete cohort marked consumed.

The blocker occurs before Current can evaluate that shop state. The native
adapter serializes `gc_.info.shop.removeCost`; `sts_lightspeed` sets that field
to `-1` after card removal and only exposes another remove action when the
value is not `-1` and the player can afford it. The bridge instead validates
`remove_cost` as nonnegative unconditionally. This is a native sentinel
contract mismatch in shop hydration, not evidence about Current's shop policy.

## Frozen Evidence

- Preregistration commit:
  `1987efb0aa5915d9c9ee925293396089a9d5c5c1`
- Implementation commit:
  `5ec7db56870d5cb26a201bdfac1d4a4c942a7437`
- Registration SHA-256:
  `c22c0f2346ace8c982e1f0701cb8014e92333858531a91e7d566f762268c4d10`
- Seed-inventory SHA-256:
  `208f28aa92fb1e8bdec496ec8fed93afc9645a6bef536065a9161f566a915647`
- Seed-ledger SHA-256:
  `962361229fac2ab1b6f72c7a350a2563c24ef163db7fa61d524cf9ee564db12a`
- Artifact-manifest SHA-256:
  `79aa0771cc162023dcfa898e13100699ccf95750ca0ea7b497337bfd40dd5148`
- Native module SHA-256:
  `410ac6b742192cfcd3568e36975bc87ecab4c2de9093d30113258b74a887e8cb`
- Simulator commit:
  `7476a81954020087da31d41d16fddf475746ec2d`
- Simulator source SHA-256:
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`
- Reachable-event contract:
  `sts_lightspeed_reachable_event_observation_v3`
- Reachable-event contract SHA-256:
  `46a1349443fcec4b224de6b2a5d07a5d5d829ee702a8f549cc3917cf85698d6e`

The preregistration inventory retained 8,250 rows from 68 tracked seed-bearing
JSON sources and excluded 347 distinct prior seeds before deterministically
selecting `7100..7107`. Before execution, the tracked tree was clean, exact
registration and ledger blobs were present at `HEAD`, `HEAD` equaled
`origin/master`, and the canonical output directory did not exist. The whole
cohort was then persisted as consumed before the first environment.

## Verification

- No-native artifact recomputation: passed with preserved verdict
  `reachable_event_native_compatibility_failed`.
- All seven predecessor registration, journal, manifest, ledger, closeout, and
  reachable-surface bindings: unchanged.
- Focused successor, resolver, bridge, adapter, and historical tests:
  `125 passed, 5 skipped in 9.75s`.
- Relevant Python compilation: passed.
- Repository commit gate: `3492 passed, 11 skipped in 228.82s`; gate total
  `232.07s`.
- Strict global OpenSpec validation before spec sync: `60 passed, 0 failed`.
- Strict global OpenSpec validation after spec sync: `60 passed, 0 failed`.
- Strict global OpenSpec validation after archive: `59 passed, 0 failed`.

The completed change is archived at
`openspec/changes/archive/2026-08-03-run-v3-reachable-event-native-compatibility`.

## Authority Boundary

Gameplay, baseline-floor, target-supported outcome, reward, model, OPE,
formal-RL, training, qualification, loading, and promotion authority all
remain false. Zero completed deterministic rows means this result supplies no
baseline-floor or policy-quality estimate.

No Communication Mod or live gameplay process was launched. No gameplay
policy, reward, model, training, qualification, loading, or promotion action
ran. The only native execution was the exact preregistered compatibility
cohort, and it was not retried.

## Project Direction

Formal non-combat RL remains `NO-GO`. The immediate next change should be a
narrow shop sentinel contract repair, beginning with a regression for
`remove_cost == -1` when no remove candidate exists. It should prove the
simulator source semantics, preserve rejection of inconsistent negative costs,
hydrate Current with `purge_available == false`, and leave gameplay policy
scoring unchanged.

This consumed failure is archived before that repair. A later native
compatibility attempt, if still justified after source-level verification,
requires a separately preregistered untouched cohort. It must not reuse these
seeds or start training as a substitute for structural compatibility.
