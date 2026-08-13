# noncombat-large-corpus-state-conditioned-card-ranking Specification

## Purpose
TBD - created by archiving change train-large-corpus-state-conditioned-card-ranker. Update Purpose after archive.
## Requirements
### Requirement: Bound merged source-only inputs
The runner SHALL bind the existing corpus, rare-card corpus and projection
diagnostics, r7 entry checkpoint, source bytes, and fixed training
configuration. It MUST NOT load native code, construct environments, access
reserved audit seeds, or read development before train-only selection passes.

#### Scenario: Input preflight passes
- **WHEN** every corpus, checkpoint, source, partition, projection, and schedule identity matches
- **THEN** train-only crossfit may begin with native, gameplay, development, and audit access disabled

#### Scenario: Bound input differs
- **WHEN** any source, dataset, checkpoint, seed, row, projection, or schedule differs
- **THEN** the runner fails before training or development access

### Requirement: Deterministic state-conditioned mini-batch training
The runner SHALL restore the r7 entry and train exactly the existing candidate
card family head and conditional state-conditioned ranker using registered Adam
and the existing margin-weighted pairwise objective. It SHALL optimize only
unequal-return rows in deterministic 64-row batches while evaluating every
complete compatible row.

#### Scenario: One epoch runs
- **WHEN** informative train rows and optimizer ownership validate
- **THEN** every informative row contributes exactly once in fixed order and all losses, gradients, optimizer state, and parameters remain finite

#### Scenario: Frozen state changes
- **WHEN** a control, non-card, generator, feature, optimizer, or input boundary differs
- **THEN** training fails and no model receives downstream authority

### Requirement: Train-only seed-level epoch selection
The runner SHALL use five disjoint train-seed folds and fixed epoch checkpoints
`1`, `2`, `4`, and `8`. Every fold SHALL start from identical entry bytes, fit
only the other folds, and score its held-out rows without update.

#### Scenario: A checkpoint passes crossfit
- **WHEN** cross-fitted mean regret decreases, maximum regret does not increase, pairwise accuracy increases, unique-best accuracy does not decrease, at least eight actions are corrected, and worsened actions do not exceed corrected actions
- **THEN** the fixed selection ordering chooses one epoch count without development access

#### Scenario: No checkpoint passes crossfit
- **WHEN** every fixed checkpoint fails at least one train-only gate
- **THEN** the verdict is not ready and final fitting, development, audit, tuning, and retry are blocked

### Requirement: Persist-before-read one-shot development gate
The runner SHALL fit one final model on all informative train rows for the
selected epoch count, write and restore canonical complete model bytes, and
only then read and evaluate merged development exactly once.

#### Scenario: Development passes
- **WHEN** overall mean regret and pairwise accuracy improve, maximum regret and unique-best accuracy do not regress, at least four actions are corrected, worsened actions do not exceed corrected actions, and rare-only mean regret, pairwise accuracy, and best-take-to-skip safety all pass
- **THEN** the verdict authorizes only a separate untouched-audit proposal

#### Scenario: Development fails
- **WHEN** any fixed overall or rare-only gate fails
- **THEN** the model is not ready and no parameter, epoch, batch, source, development, audit, or live retry is authorized

### Requirement: Canonical isolated evidence without downstream authority
The runner SHALL publish canonical configuration, folds, losses, metrics,
predictions, restored model, report, and manifest artifacts while preserving
entry and production isolation. Native, gameplay, CommunicationMod, formal RL,
OPE, policy-quality, audit, qualification, production loading, and promotion
authority SHALL remain false.

#### Scenario: Execution completes
- **WHEN** train-only selection stops or one-shot development completes
- **THEN** exact artifacts and the stop reason are published without modifying production state or accessing `92320..92383`
