## Context

The bound epoch-4 model passed every development check except comparison with a
single untrained initialization. Post-hoc diagnosis, which has no promotion
authority, showed the fixed initialization was at the 98.4th percentile of 64
untrained models while the trained model exceeded 62 of 64.

## Goals / Non-Goals

**Goals:**
- Evaluate the exact frozen model on one disjoint fresh cohort.
- Replace initialization lottery with a preregistered 32-seed distribution and
  a fixed 75th-percentile threshold.
- Preserve Current regret and correction guardrails.

**Non-Goals:**
- Retrain, tune, alter, or reinterpret the previous no-go.
- Use the new cohort more than once or change thresholds after access.
- Launch gameplay, modify policy, or authorize promotion.

## Decisions

1. Bind model SHA-256 `3aa983a52a8bbe385735c6c18cd1b4b7f06c20b987edd7a07da8a30a51708b06`.
2. Collect at most 16 complete sources from fresh seeds `95428..95459`, with
   minimum 12 complete, 4 informative, 4 action kinds, and 4 exact replays.
3. Evaluate untrained model seeds `0..31`; nearest-rank index 23 is the fixed
   75th-percentile threshold. The trained model must strictly exceed it.
4. Keep mean-regret improvement, maximum-regret non-inferiority, at least one
   correction, and worsened-not-more-than-corrected as coequal pass gates.

## Risks / Trade-offs

- [The cohort remains small] -> Require all gates and permit only live shadow,
  never direct intervention or promotion.
- [Distribution evaluation reuses one fresh dataset 33 times] -> All model
  seeds and quantile rules are frozen before access; no fitting or selection is
  performed.
