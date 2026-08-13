## ADDED Requirements

### Requirement: Bound source-only training inputs
The runner SHALL bind the expanded train and development datasets, corpus
report and registration, frozen r7 entry checkpoint, source bytes, and fixed
configuration grid. It MUST NOT load native code, construct environments, or
access the reserved audit schedule.

#### Scenario: Input preflight passes
- **WHEN** every bound artifact and source byte matches and the corpus verdict is ready
- **THEN** train-only configuration selection may begin without native, gameplay, or audit access

#### Scenario: Input lineage differs
- **WHEN** any dataset, checkpoint, source, schedule, or corpus verdict differs
- **THEN** the runner fails before fitting a model

### Requirement: Train-only residual selection
The runner SHALL compare the fixed hierarchical card-uplift configurations
using five disjoint seed-level folds over train rows only. Development rows MUST
NOT affect configuration selection, fitting targets, or tie-breaking.

#### Scenario: Configuration is selected
- **WHEN** every fixed configuration has complete cross-fitted train predictions
- **THEN** the deterministic metric ordering selects exactly one configuration

#### Scenario: Fold isolation differs
- **WHEN** a train seed is missing, duplicated, or appears in both fit and held-out rows
- **THEN** the runner fails without development access

### Requirement: Frozen one-shot development evaluation
The runner SHALL fit the selected residual once on all train rows, persist and
restore its canonical bytes, and then evaluate development exactly once.
Unseen development card ids MUST use the train-only global uplift prior.

#### Scenario: Development gate passes
- **WHEN** all fixed train cross-fit and development regret, ranking, correction, and safety checks pass
- **THEN** the verdict authorizes only a separate reserved-audit proposal

#### Scenario: Development gate fails
- **WHEN** any fixed check fails
- **THEN** the verdict is not ready and no retry, grid change, audit access, production loading, or promotion is authorized

### Requirement: Reproducible no-authority artifacts
The runner SHALL publish canonical configuration, folds, metrics, predictions,
selected model, report, and manifest artifacts with training, evaluation, and
policy authority false beyond the registered source-only development study.

#### Scenario: Artifacts are published
- **WHEN** the fixed run completes
- **THEN** every artifact has a final-path hash and the entry checkpoint remains byte-identical
