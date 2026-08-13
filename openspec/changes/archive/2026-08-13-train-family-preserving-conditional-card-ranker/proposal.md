## Why

The merged-corpus full-head model improved train crossfit but changed 40
development decisions from skip to take and failed rare-card generalization.
Read-only recomputation also found that the existing report used joint-action
argmax while the simulator executes a two-stage family-then-action policy, so
the next experiment needs lower capacity and policy-aligned metrics.

## What Changes

- Freeze the r7 family head and every non-conditional parameter, then train
  only the conditional ranker's 64-value scorer weight on unequal take-vs-take
  counterfactual pairs.
- Select one fixed epoch count with five seed-disjoint train-only folds before
  reading development.
- Evaluate actual two-stage greedy actions, take-only pairwise ordering, and
  overall/rare regret without permitting any family-choice change.
- Publish one source-bound pass/no-go result. A pass permits only a separate
  reserved-audit proposal; a failure restores the r7 entry boundary.
- Do not access `92320..92383`, load native code, run gameplay, tune after
  results, or modify production checkpoints.

Success requires train-only crossfit and one-shot development to improve
take-only ordering and two-stage mean regret without increasing maximum regret,
decreasing unique-best accuracy, changing any entry family choice, or worsening
more actions than are corrected. Rare development must pass the same safety
direction. Rollback is the unchanged r7 entry checkpoint.

## Capabilities

### New Capabilities

- `noncombat-family-preserving-conditional-card-ranking`: Bounded 64-parameter
  take-only fitting and policy-aligned two-stage evaluation on the merged
  counterfactual corpus.

### Modified Capabilities

None.

## Impact

This adds one source-only experiment runner, focused tests, and canonical
reports. It reuses tracked corpus and checkpoint artifacts and the existing
CPU ranker; it changes no CommunicationMod, simulator, gameplay, production
policy, native module, or reserved seed inventory.
