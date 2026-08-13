## Context

The source-only nested cross-fit improved all aggregate development metrics,
did not worsen maximum regret in any outer fold, and selected
`shrinkage=3, strength=128` in two folds versus one selection for each other
configuration. Audit seeds `1024..1031` remain untouched because the prior
scorer-only development gate failed before audit construction.

## Goals / Non-Goals

**Goals:**

- Fit the fixed card-uplift residual on all 46 exposed source states before any
  audit access.
- Collect and evaluate one bounded audit cohort with paired frozen-entry and
  residual predictions.
- Produce a reproducible fresh-evaluation proposal go/no-go.

**Non-Goals:**

- Search configurations, refit after audit access, or update neural weights.
- Use fresh seeds, run gameplay/OPE, or promote/load a production model.
- Retry a logically completed audit after an unfavorable result.

## Decisions

### Fix the unique modal outer configuration

The audit uses `shrinkage=3` and `strength=128`. No selection rule or alternate
configuration is present in the audit runner. The uplift model is fitted from
all exposed rows and canonically encoded before constructing the native audit
environment.

### Reuse the registered native and collection boundary

The runner binds the scorer-pilot native identity and production-isolation
metadata, then collects only seeds `1024..1031`, at most two card states per
seed, at most 64 action branches, and at most one registered Courier censor.
At least 12 complete source states are required. The game and CommunicationMod
must remain absent.

### Evaluate one paired audit

Frozen r7 joint log probabilities and the fixed uplift model score identical
audit actions. Passing requires lower mean regret, nonincreasing maximum regret,
higher weighted pairwise accuracy, nondecreasing unique-best accuracy, and at
least one corrected entry mistake. The model is not fitted again after audit
access.

## Risks / Trade-offs

- [The audit is small] -> Require 12 complete states and report every prediction
  and action flip.
- [Courier can block one seed] -> Allow only the already-registered blocker and
  do not replace the seed.
- [A fixed global uplift can miss state-specific skip value] -> Retain frozen
  entry logits and require maximum-regret safety.
- [Native loading can fail before collection] -> Fail before audit access where
  possible; do not change module, seed, or configuration after a started run.

## Migration Plan

No production migration occurs. A negative audit discards the experiment model.
A positive audit permits only a separately registered fresh-evaluation proposal.

## Open Questions

None.
