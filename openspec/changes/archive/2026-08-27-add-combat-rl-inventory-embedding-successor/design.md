## Context

Production r16 remains the deployed combat policy. The r2 replay was collected
with the corrected inventory encoder, epsilon zero, and no optimizer updates;
its sanitized copy removes exactly one transition whose stored successor crossed
a floor boundary. The remaining transition tensors are valid for one-step TD,
but removal means array adjacency must not be used to reconstruct long returns.

The prior successor line updated the whole network with eight full-gradient SGD
steps and then interpolated by one half. Its r17-r19 candidates moved only about
`7e-6` in relative L2 and produced no demonstrated live benefit. This experiment
instead asks whether newly visible inventory identities support a localized
policy update.

## Goals / Non-Goals

**Goals:**

- Fit a deterministic development candidate from corrected real replay.
- Restrict trainable state to observed nonzero potion and relic embedding rows.
- Measure one-step loss, action drift, End Turn direction, inventory strata, and
  exact tensor isolation on a deterministic combat-group split.
- Preserve a frozen, reproducible candidate for a later independent holdout when
  fixed development gates pass.

**Non-Goals:**

- Production promotion, live evaluation, online learning, or checkpoint
  replacement.
- Full-return reconstruction from the sanitized tensor order.
- Hyperparameter or threshold sweeps on r2 or any future holdout.
- Updating card embeddings, dense layers, zero inventory rows, or unobserved
  inventory rows.

## Decisions

1. **Use stored one-step successors.** Targets are computed from each row's
   stored `next_*`, `done`, and frozen parent target network. Full-return and
   n-step alternatives were rejected because deleting the invalid boundary row
   intentionally breaks sequence adjacency without invalidating stored one-step
   successors.

2. **Train inventory embeddings only.** Every parameter is frozen except potion
   and relic embedding matrices. Gradient masks preserve row zero and all rows
   absent from the training partition exactly. This makes the candidate's source
   of change directly auditable and leaves CommunicationMod compatibility
   unchanged.

3. **Use one fixed optimizer dose.** The runner performs deterministic Adam
   minibatches over the training combat groups with no interpolation or sweep.
   TD loss is combined with a frozen-parent legal-action SmoothL1 anchor. Exact
   seed, epochs, learning rate, weights, and group allocation are report fields.

4. **Split by combat groups, not individual rows.** Groups end at replay `done`
   rows; a fixed seeded permutation assigns complete groups to development
   validation. The known post-removal residual grouping imperfection cannot
   corrupt one-step targets and is recorded as a limitation.

5. **Separate materiality from promotion.** Eligibility requires lower
   validation one-step loss, exact parameter isolation, overall action
   disagreement between fixed lower and upper bounds, and a bounded
   positive-energy End Turn increase. Passing authorizes only a separately
   collected fresh holdout; failing still preserves the report and a
   development-only candidate for diagnosis.

## Risks / Trade-offs

- [One-step reward may weakly identify long-lived relic value] -> Treat this as
  a bounded first test; use fresh outcome evidence before broader training.
- [All combats contain at least one relic] -> Report potion-present and relic
  count strata rather than claiming a no-inventory control that does not exist.
- [A localized embedding update can still alter many actions] -> Enforce fixed
  action-drift and End Turn gates and retain production r16 on every result.
- [The internal validation split is not an independent policy-quality holdout]
  -> Grant no live or promotion authority and collect a new cohort only after
  freezing the recipe and checkpoint hash.

## Migration Plan

There is no production migration. Run the new tool against the immutable
sanitized r2 checkpoint, publish its isolated output directory, and leave
CommunicationMod plus all production checkpoints untouched. Rollback deletes
only the new tool, tests, OpenSpec change, and report directory.

## Open Questions

None before implementation. A later decision will choose between LightSTS
screening and direct fresh real replay based on the candidate's measured drift.
