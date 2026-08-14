## ADDED Requirements

### Requirement: Opt-in state-conditioned shop rows
The collector SHALL capture separate versioned state and candidate tensors when
explicitly requested and SHALL preserve its existing default artifact contract.

#### Scenario: Feature capture is enabled
- **WHEN** an eligible complete shop source is projected
- **THEN** its state and candidate tensors align exactly with its legal candidates and outcomes

#### Scenario: Feature capture is disabled
- **WHEN** the existing collector runs without a projector
- **THEN** its source row serialization contains no feature fields

### Requirement: Disjoint fresh shop partitions
The experiment MUST collect train and development outcomes from fixed,
non-overlapping fresh A0 seed schedules under frozen Current continuation.

#### Scenario: Train support passes
- **WHEN** train complete, informative, action-kind, replay, and identity floors pass
- **THEN** train-only model selection may begin before development construction

#### Scenario: Train support fails
- **WHEN** any train support floor fails
- **THEN** execution stops without accessing development seeds

### Requirement: Train-only state-conditioned selection
The experiment SHALL select one fixed checkpoint on a source-isolated internal
tune split and refit it on all train rows before development access.

#### Scenario: Checkpoint selection completes
- **WHEN** every fixed epoch has train and tune metrics
- **THEN** deterministic regret and pairwise ordering selects exactly one epoch

### Requirement: One-shot development verdict
The experiment SHALL compare the frozen ranker exactly once with Current and
deterministic initialization on the fixed development partition.

#### Scenario: Ranker passes
- **WHEN** mean regret improves Current, maximum regret is non-inferior, pairwise accuracy improves initialization, at least one Current decision is corrected, and corrections are not outnumbered by worsened decisions
- **THEN** the verdict permits only a separate fresh shadow-evaluation proposal

#### Scenario: Ranker fails
- **WHEN** any fixed development gate fails
- **THEN** the verdict is terminal for the cohort and configuration without tuning or rerun

### Requirement: Reproducible isolated execution
The experiment MUST publish canonical datasets, model, metrics, configuration,
report, and manifest while keeping gameplay and production policy isolated.

#### Scenario: Fixed experiment runs
- **WHEN** the registered native CPU experiment executes
- **THEN** no gameplay, CommunicationMod, production checkpoint, protected seed inventory, qualification, promotion, or live policy operation occurs
