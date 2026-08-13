## Context

The event-option outcome POC showed repeatable action-level signal, but Current
already tied for the best observed return on 80.33% of sources. A raw learned
ranker therefore has more opportunities to regress than to improve. The route
experiment demonstrated that better aggregate ranking accuracy is insufficient
when a learned policy worsens tail regret.

## Goals / Non-Goals

**Goals:**

- Collect state-conditioned event outcomes on fresh train and development seeds.
- Train one CPU pairwise ranker and a conservative Current-override policy.
- Select every model and override choice without development access.
- Decide readiness against Current using mean and tail regret.

**Non-Goals:**

- Policy-gradient training, online exploration, gameplay, or CommunicationMod.
- Production checkpoint access, policy promotion, or same-cohort tuning.
- Route, shop, or card-reward learning.

## Decisions

### Fixed cohorts and support floors

Use train seeds `94100..94227` and development seeds `94228..94259`. Collect at
most two eligible multi-option events per seed. Require at least 192 complete and
72 informative train sources before development access, then at least 48
complete, 16 informative, and 8 distinct-event development sources. The output
directory is new and development is collected exactly once.

### Reuse the exact state/candidate projection

Generalize the route partition collector only at its category boundary and keep
its route wrapper unchanged. Event rows use the same exact API v3 state and
candidate feature tensors, fresh Current sessions, immutable branch clones, and
registered Courier censor. Dataset schemas remain category-specific even though
the in-memory row shape and training primitives are shared.

### Train-only model and override selection

Split train rows by seed: seeds divisible by four form tune; all others form fit.
For each fixed checkpoint epoch, fit from the same deterministic initialization.
Evaluate raw ranker and conservative overrides on tune. An override selects the
ranker's action only when its sigmoid score advantage over Current meets one of
the fixed confidence thresholds `0.50, 0.55, 0.60, 0.70, 0.80, 0.90`; otherwise
it retains Current. Select by mean regret, then maximum regret, worsened count,
corrected count, higher confidence, and lower epoch. Preserve the selected fit
model rather than retraining it, so threshold calibration does not change after
selection.

### Single-use development gate

After selection, collect development once and report Current, untrained, raw,
and gated policies. A go requires gated mean regret to improve Current, gated
maximum and 95th-percentile regret to be no worse than Current, at least one
action change and correction, no more worsened than corrected sources, and raw
weighted pairwise accuracy above the deterministic untrained model. Failure is
terminal for this configuration and cohort.

## Risks / Trade-offs

- [Development contains rare high-impact outcomes] -> Bind maximum and p95 regret
  and publish per-source predictions rather than relying on mean regret alone.
- [Confidence scale changes with retraining] -> Do not retrain after train-tune
  selection.
- [Sparse events produce weak per-event estimates] -> Require event diversity and
  report per-event support; do not claim event-specific quality from one sample.
- [Courier restock blocks a continuation] -> Censor only the registered boundary
  within fixed limits and exclude incomplete rows.
- [A no-change gate wins tune] -> Development cannot pass the strict improvement
  gate, yielding an honest no-go rather than promotion by fallback.

## Migration Plan

Add the generic category collector boundary, event runner, tests, and one report.
No production migration occurs. Rollback removes those additions and leaves the
Current policy unchanged.

## Open Questions

If the gated ranker passes, a later change must decide whether to deploy it only
in simulator shadow evaluation or use it as an initialization for broader RL.
