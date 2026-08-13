## Context

The persisted scorer-pilot datasets contain 46 complete card-reward source
states from 23 already-exposed seeds, with four legal actions and formal
counterfactual returns per state. The r7 entry policy is highly saturated: a
small scorer update cannot flip actions, while updating both hidden matrices
overfits. A development probe showed that cross-fitted per-card uplift has
useful signal but can make unsafe skip/take changes when it replaces the entry
policy.

## Goals / Non-Goals

**Goals:**

- Estimate the generalization of a frozen-entry plus card-uplift residual using
  nested seed-grouped cross-fitting.
- Select regularization and residual strength without evaluating a candidate on
  the same seed used to fit or select it.
- Publish enough fold and action-level evidence for a later audit go/no-go.

**Non-Goals:**

- Access audit seeds `1024..1031`, reconstruct native branches, or run gameplay.
- Tune the neural hidden layers, optimize on the prior development partition,
  or claim policy quality.
- Produce or load a production checkpoint.

## Decisions

### Use a frozen base plus empirical card uplift

The entry score for every action is its frozen r7 joint log probability. For
each card id, the fit-only uplift is the mean of `take_return - skip_return`,
shrunk toward the fit-only global take uplift. Skip has zero uplift. A candidate
score is `entry_score + strength * uplift`. This retains state-conditioned entry
behavior while adding an interpretable card-value correction; no neural tensor
is updated.

### Use a fixed 12-configuration grid

The only candidates are the Cartesian product of shrinkage pseudo-counts
`{1, 3, 10}` and residual strengths `{16, 32, 64, 128}`. The grid was fixed
after the exposed development probe. No value may be added, removed, or changed
after execution.

### Use nested seed-grouped cross-fitting

Sorted seeds are assigned round-robin to four outer folds. Within each outer
fit set, sorted seeds are assigned round-robin to three inner folds. Each
configuration receives inner cross-fitted predictions. Selection is
lexicographic by lower mean regret, lower maximum regret, higher weighted
pairwise accuracy, higher unique-best accuracy, lower strength, then higher
shrinkage. The selected configuration is fitted on the full outer fit set and
evaluated once on the outer held-out seeds.

### Compare only materialized outer predictions

The terminal gate compares aggregated outer-held-out residual predictions with
the frozen entry on the same 46 rows. Mean regret must decrease, maximum regret
must not increase, weighted pairwise accuracy must increase, unique-best
accuracy must not decrease, and at least two entry mistakes must be corrected.
No outer fold may increase maximum regret, and at least three of four folds must
not increase mean regret. Passing authorizes only a separate audit proposal.

## Risks / Trade-offs

- [Only 23 seeds are available] -> Keep seeds intact, publish every fold, and
  require fold-level safety rather than relying only on aggregate metrics.
- [Repeated cards leak across decisions] -> Group by seed in both inner and
  outer folds; card identity can generalize only from other seeds.
- [The grid was informed by an exposed probe] -> Treat all cross-fit output as
  development evidence and leave audit untouched.
- [Empirical uplift cannot model novel cards well] -> Shrink unknown cards to
  the fit-only global prior and report their count.
- [A residual can override a valuable skip decision] -> Keep frozen entry
  scores in composition and require maximum-regret safety per outer fold.

## Migration Plan

There is no production migration. On failure, discard the source-only residual
artifact and retain the tracked r7/native policy. On success, create a separate
audit change with fixed fitting and evaluation rules.

## Open Questions

None. The dataset identities, folds, grid, selection rule, and gates are fixed
before implementation.
