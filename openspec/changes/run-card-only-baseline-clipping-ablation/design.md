## Context

The r1 continuation restored r7 checkpoint `004`, then ran 16 candidate-only
chunks with a four-fold ridge baseline whose held-out predictions are clipped to
`[0, 3]`. The fixed-probe diagnostic found coherent parameter movement but weak,
non-monotonic function movement. A prior first-chunk diagnostic observed 133
lower-clipped predictions among 566 card decisions, making clipping a concrete
single-variable mechanism candidate.

The experiment must retain the current candidate card policy, native
SimpleAgent non-card behavior, Adam state, fixed validation probe, consumed seed
schedule, and production isolation. Only one branch may replace each clipped
held-out prediction with its already-computed finite `unclipped` value.

## Goals / Non-Goals

**Goals:**

- Isolate the one-step effect of baseline lower clipping on advantages,
  gradients, parameters, and the card policy function.
- Charge only one 64-trajectory collection by recomputing both branches from the
  same stored states, candidates, selected actions, rewards, and returns.
- Prove the current-semantics branch reproduces existing checkpoint `005`.
- Persist enough compact telemetry to make a four-step ablation go/no-go without
  replaying this cohort again.

**Non-Goals:**

- Estimating policy quality, causal outcome lift, or fresh-cohort performance.
- Selecting, promoting, or loading either branch as a gameplay policy.
- Changing learning rate, entropy, architecture, reward, seed schedule, or
  optimizer behavior.
- Running CommunicationMod or Slay the Spire.

## Decisions

### Collect one trajectory cohort and rebuild policy terms

The runtime restores checkpoint `004`, collects the registered candidate-only
chunk once, and validates the same bounded Courier censoring contract as r1.
Branch A keeps the rollout policy terms. Branch B forwards the exact stored
state/candidate tensors through its independently restored checkpoint `004`
model and rebuilds terms for the already-selected action. This avoids a second
environment collection while ensuring gradients belong to each branch model.

Alternative: collect each branch independently. Rejected because post-update
behavior cannot affect the first chunk, so a second 64-access collection adds no
information and introduces avoidable trajectory identity risk.

### Reuse one fitted baseline and alter only its exposed prediction

The cross-fitted ridge models and held-out predictions are fit once from the
shared trajectories. Branch A uses `prediction.clipped`; branch B uses
`prediction.unclipped`. Both use fixed unit scale and the same raw returns.
No baseline is refit and no advantage centering or normalization is added.

Alternative: center or standardize advantages. Rejected because that changes a
second mechanism and would not isolate clipping.

### Treat existing checkpoint 005 as a reproduction oracle

Branch A must reproduce the candidate model bytes in r1 checkpoint `005`
exactly. A mismatch blocks interpretation of branch B and stops the experiment.
Optimizer/checkpoint structural validation is also retained, but only model-byte
identity is compared because the ablation runner has a different journal schema.

### Use mechanism-only progression criteria

After both updates, the runner compares applied gradients and fixed-probe policy
surfaces. It may propose a separately registered four-step ablation only when A
reproduces, all support/isolation checks pass, neither branch collapses, and B
differs materially by at least one of: an exact probe action difference, mean
joint total variation of at least `0.001`, or applied-gradient cosine at most
`0.99`. These criteria authorize only a proposal, not training continuation or
fresh evaluation.

## Risks / Trade-offs

- [One cohort may not represent later chunks] -> Use the result only to decide
  whether a separately registered four-step ablation is worth its access cost.
- [Recomputed terms could drift from rollout terms] -> Require exact selected
  action, candidate order, family order, and entry-model identity before either
  optimizer step.
- [Private runtime helpers could create ownership mistakes] -> Add positive and
  reverse ownership regressions and validate branch-local optimizer parameters.
- [Current branch may fail exact reproduction] -> Stop before interpreting or
  reporting a clipping mechanism verdict; do not tune or retry the same identity.
- [Unclipped predictions can be outside return support] -> Permit them only in
  branch B of this single exploratory step and report their range/count.
