## Context

The available shop corpus contains four completed simulator cohorts with 112 unique source hashes. Every row uses a 1024-wide state vector and an `N x 1024` candidate matrix, but cohort-level Current mean regret ranges from about 0.132 to 0.320. The previous ranker selected epochs and a score margin on one 16-source split; that calibration did not transfer to its fresh cohort.

## Goals / Non-Goals

**Goals:**

- Bind and deduplicate all four historical datasets without accessing protected seed inventories.
- Use deterministic source-level folds to obtain out-of-fold predictions for every historical row.
- Select one epoch and override threshold from aggregate OOF evidence, then fit a small multi-seed ensemble on all 112 rows.
- Evaluate the frozen ensemble once on 32 new source states and emit auditable artifacts.

**Non-Goals:**

- Integrating the ranker into Current or CommunicationMod.
- Reusing any historical row for the final external gate.
- Searching new architectures, reward definitions, or broad hyperparameter grids.
- Claiming formal RL readiness or policy promotion.

## Decisions

### Bind four historical partitions by byte hash

The runner will require exact file hashes, compatible feature widths, and globally unique source hashes. This turns completed no-go cohorts into a larger development corpus without silently changing their evidence. Recollecting those seeds was rejected because it would spend simulator time without increasing independent support.

### Use deterministic five-fold source grouping

Each source hash will map to one of five folds. For each candidate epoch, five fixed initialization seeds will train on four folds and produce ensemble predictions only for the held-out fold. This gives every selection row an out-of-fit prediction and reduces dependence on one lucky initialization. A single random train/tune split was rejected because it already produced a false-positive selection.

### Select a bounded vote-quorum override rule from OOF predictions

Each of five independently initialized models votes for one candidate. The ensemble proposes the plurality candidate, using mean Current-centered score and action id only for deterministic tie breaking; Current remains selected unless the proposal receives a registered `3/5`, `4/5`, or `5/5` quorum. Eligible configurations must improve Current mean regret, remain noninferior on maximum regret, correct at least three rows, make at least five overrides, and not worsen more rows than they correct. Selection then minimizes mean regret with deterministic tie breaks. A raw score margin was rejected because its scale changed between small-split and full-corpus fitting in the previous experiment.

### Freeze before one 32-source external evaluation

After OOF selection, five models with the selected epoch count will be fit on all 112 historical rows. Their identities and the vote quorum will be serialized before collecting a new 32-source cohort from a disjoint seed schedule. The fresh gate compares gated ensemble decisions directly with Current and is terminal for this architecture: failure means no retry, quorum change, or policy integration.

## Risks / Trade-offs

- [Historical cohorts have different regret distributions] -> Preserve cohort labels in reports and require every fold to contain sources from multiple cohorts.
- [OOF epoch/quorum selection can still overfit 112 rows] -> Keep the search grid small and reserve a completely new 32-source external gate.
- [Five-fold, five-seed fitting increases CPU work] -> Reuse in-memory tensors and keep epoch candidates bounded; simulator collection remains the dominant cost.
- [Ensemble latency may exceed a live budget] -> This change does not authorize live use; any later shadow proposal must measure latency separately.

## Migration Plan

Add the standalone runner and focused tests, run selection-only preflight, commit the frozen implementation, then execute one native fresh evaluation. On failure, archive the no-go artifacts and leave Current unchanged. Rollback is deletion of the standalone runner, tests, and generated report directory.

## Open Questions

None. The fresh result determines whether a separate live-shadow proposal is justified.
