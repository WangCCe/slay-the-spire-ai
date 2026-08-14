## Why

The first state-conditioned and Current-relative shop rankers depended on one 16-source tuning split and failed to improve Current on fresh cohorts. Four completed cohorts now provide 112 unique, schema-compatible source states, so grouped cross-validation can replace split-specific threshold selection before another external evaluation.

## What Changes

- Aggregate the four historical shop counterfactual datasets behind explicit hashes and source-level deduplication.
- Train and select a small Current-relative ensemble and vote quorum using deterministic grouped cross-validation and out-of-fold evidence instead of a single tune split.
- Freeze the selected ensemble and vote-quorum override rule before collecting one entirely new simulator cohort.
- Report Current, raw ensemble, and gated ensemble regret plus corrected/worsened decisions on both out-of-fold and fresh data.
- Stop without policy integration when the fresh gate fails; do not modify gameplay, CommunicationMod, production checkpoints, or protected seed inventories.

Success requires the fresh gated ensemble to improve Current mean regret, remain noninferior on maximum regret, correct at least one Current decision, and not worsen more decisions than it corrects. The rollback boundary is the standalone analysis runner, tests, and report artifacts; no learned policy is installed by this change.

## Capabilities

### New Capabilities

- `noncombat-cross-validated-shop-ranking`: Defines source-bound historical aggregation, grouped out-of-fold model selection, frozen ensemble training, and a fresh simulator evaluation gate for shop decisions.

### Modified Capabilities

None.

## Impact

The change adds one analysis runner, focused tests, a repo-local OpenSpec capability, and bounded report artifacts. It reuses the existing native simulator bridge and state-conditioned shop feature/model code, requires Windows Python for native execution, and has no production gameplay or checkpoint impact.
