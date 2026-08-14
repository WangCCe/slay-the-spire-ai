## ADDED Requirements

### Requirement: Source-isolated candidate-only partitions
The trainer SHALL deterministically split the committed complete shop sources
into disjoint fit, tune, and one-shot holdout partitions without using full game
state features.

#### Scenario: Corpus is accepted
- **WHEN** the bound corpus identity and required source counts match
- **THEN** every source appears in exactly one partition and candidate features are deterministic

#### Scenario: Corpus differs
- **WHEN** corpus identity, row shape, candidate alignment, or partition support differs
- **THEN** training stops before model fitting

### Requirement: Train-only model selection
The trainer MUST select a checkpoint epoch using only fit and tune sources and
MUST refit the selected configuration on all training sources before holdout
evaluation.

#### Scenario: Tune selection completes
- **WHEN** every fixed epoch has been fitted and evaluated on tune rows
- **THEN** the deterministic metric ordering selects exactly one epoch

### Requirement: One-shot baseline verdict
The trainer SHALL compare the frozen model exactly once with Current and the
deterministic initialization on holdout sources.

#### Scenario: Baseline passes
- **WHEN** trained mean regret improves Current, maximum regret is non-inferior, pairwise accuracy improves initialization, at least one Current decision is corrected, and corrections are not outnumbered by worsened decisions
- **THEN** the verdict permits only a separate fresh shadow-evaluation proposal

#### Scenario: Baseline fails
- **WHEN** any fixed holdout check fails
- **THEN** the verdict is terminal for this model, split, and corpus without same-cohort tuning or rerun

### Requirement: Offline reproducible artifacts
The trainer MUST publish canonical corpus identity, split identity, feature
contract, selected model, metrics, predictions, configuration, and manifest.

#### Scenario: Training completes
- **WHEN** the terminal verdict is written
- **THEN** all artifact hashes and sizes match the manifest and downstream authority remains false

### Requirement: Strict isolation
The trainer MUST NOT load native simulation, protected seed inventories,
production checkpoints, CommunicationMod, or gameplay.

#### Scenario: Offline fit runs
- **WHEN** the CPU training command executes
- **THEN** only the configured output directory is written and Current remains the rollback policy
