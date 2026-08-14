## Context

The candidate-only shop baseline lowered holdout mean regret from 0.237640 to
0.194577 but failed the fixed pairwise gate. The collector already has exact
API v3 snapshots and legal candidates at each source; it currently discards the
state-conditioned projection before publishing the outcome row.

## Goals / Non-Goals

**Goals:**
- Capture separate state and candidate tensors without changing default shop
  corpus bytes.
- Collect fixed, disjoint fresh train and development shop cohorts.
- Fit and select one CPU state-conditioned ranker before one development access.
- Publish complete source, dataset, model, metric, and manifest identity.

**Non-Goals:**
- Tune on or rerun development, reuse prior shop sources, or inspect protected
  seed inventories.
- Launch gameplay or CommunicationMod, access production checkpoints, or alter
  live policy.
- Claim causal value, formal RL qualification, or promotion readiness.

## Decisions

1. Add an opt-in projector argument to the existing collector. Projected tensors
   remain in-memory for training and are sparse-encoded only when explicitly
   present; the default collector serialization omits them exactly as before.
2. Use train seeds `95300..95395` and development seeds `95396..95427`, with
   maximum 64/16 complete sources and 768/256 branches. Train must provide at
   least 48 complete and 18 informative sources; development must provide 12
   complete and 4 informative sources.
3. Hash-split train rows into fit/tune, select from epochs `1, 2, 4, 8, 16`,
   refit on all train rows, then construct and evaluate development exactly once.
4. Require development mean regret to improve Current, maximum regret to be
   non-inferior, pairwise accuracy to improve deterministic initialization, and
   at least one correction with worsened decisions not exceeding corrections.

## Risks / Trade-offs

- [Native collection dominates runtime] -> Run one fixed cohort and spend no
  time on full-suite pytest or broad review during execution.
- [Development support may be small] -> Enforce preregistered source and signal
  floors before interpreting policy metrics.
- [State hashing can collide] -> Bind the existing versioned policy-input
  projection and preserve exact sparse tensors in canonical datasets.
