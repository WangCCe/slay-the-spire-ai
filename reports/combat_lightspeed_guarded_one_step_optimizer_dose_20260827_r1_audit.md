# Guarded one-step optimizer dose audit

## Decision

Run one fresh, preregistered 64/128/256-update LightSTS dose comparison. Do not
extend the current guarded one-step recipe with another anchor or encounter
identity variant before this comparison resolves whether the fixed 256-update
budget is itself causing policy drift.

## Evidence

- Every registered combat LightSTS fit inspected through 2026-08-27 used 256
  optimizer updates. There is no existing dose or early-stop comparison.
- Recent fits reduce TD and anchor losses cleanly while ending roughly 1.1 to
  1.25 L2 units from the frozen production-r16 parent; held-out outcomes often
  degrade despite those lower losses.
- Raw frozen-parent anchoring is materially better than no anchor, but it has
  not made the 256-update candidate improve on production r16.
- Proxy-aware anchor labels were rejected on a fresh cohort: proxy minus raw
  reward was -0.6853 and HP was -0.6082.
- Collision-free enum-v1 encounter identity was technically valid and mildly
  positive relative to its fresh control, but failed the preregistered policy
  gate and still underperformed production r16.
- Prior n-step results used an older r4 parent and did not establish a robust
  successor; they do not answer whether the current r16 recipe is over-updated.

## Scope

The comparison reuses the existing committed runner and immutable native module.
It performs CPU-only simulator fitting and evaluation. It does not start Slay
the Spire or CommunicationMod, load or modify the production checkpoint, tune
the cohort after observing results, package a candidate, or authorize promotion.

