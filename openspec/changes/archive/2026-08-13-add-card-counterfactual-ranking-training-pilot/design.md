## Context

Trajectory-level REINFORCE updates changed the card policy without changing its
greedy decisions. The completed counterfactual credit POC instead found local
action-return differences in 11 of 15 states and unique best actions in seven.
Those labels use the formal reward contract and a common native continuation,
but all observed branches lost, so this pilot tests prediction of floor-progress
rankings rather than victory improvement.

## Goals / Non-Goals

**Goals:**

- Run real model fitting against direct action-level counterfactual rankings.
- Measure generalization on a disjoint, already-consumed seed partition.
- Keep data generation, optimizer steps, gates, and production isolation fixed.

**Non-Goals:**

- Formal non-combat RL, fresh evaluation, OPE, qualification, or promotion.
- Bottled imitation or continued trajectory-level REINFORCE.
- Victory-probability claims or production checkpoint loading.

## Decisions

### Use a disjoint consumed-seed split

Train seeds are `1000..1015`; holdout seeds are `1016..1023`. Each partition
evaluates at most two card states per seed and stops before any source whose full
candidate set would exceed the 128/64 branch budget. Holdout labels are collected
before fitting and never enter the loss. The already-registered Courier restock
blocker may censor at most two train seeds and one holdout seed without
replacement; training requires at least 24 complete train and 12 complete
holdout source states.

### Restart optimizer state for the changed objective

The entry model is restored from tracked r7 `checkpoint_004.json`, but a new
registered candidate-card Adam optimizer is created. Reusing moments from the
trajectory objective was rejected because they encode gradients for a different
loss and were associated with behavior-insensitive movement.

### Train return-margin-weighted pairwise rankings

For every action pair with unequal returns, the better action's joint hierarchical
log probability is ranked above the worse action using logistic loss weighted by
the absolute return margin. Equal-return pairs are omitted. Thirty-two full-batch
steps are fixed before execution; there is no epoch selection on holdout data.

### Gate only on disjoint counterfactual prediction

The pilot passes only when train loss decreases, held-out mean top-action regret
strictly decreases, weighted pairwise accuracy strictly increases, unique-best
top-1 accuracy and maximum regret do not regress, and at least one wrong held-out
greedy action changes to a return-best action. The checkpoint remains local even
on pass.

## Risks / Trade-offs

- [Labels contain no victory examples] -> Limit the claim to floor-progress
  ranking generalization and require later broader outcome evidence.
- [Small holdout can be noisy] -> Use exact disjoint seeds and paired before/after
  metrics without tuning thresholds.
- [Counterfactual generation is expensive] -> Cap total continuations at 192 and
  stop only at whole-source boundaries.
- [Known Courier restock semantics are unsupported] -> Censor only that registered
  blocker within fixed 2/1 seed limits and do not replace censored seeds.
- [Training can damage existing policy behavior] -> Require held-out regret,
  pairwise accuracy, unique-best accuracy, and maximum-regret guards; retain r7
  and native SimpleAgent as rollback.
