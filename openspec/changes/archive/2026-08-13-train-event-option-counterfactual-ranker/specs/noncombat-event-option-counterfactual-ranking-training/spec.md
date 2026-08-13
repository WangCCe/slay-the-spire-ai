## ADDED Requirements

### Requirement: Disjoint event learning partitions
The experiment SHALL collect state-conditioned event-option outcomes from fixed,
disjoint train and single-use development seed schedules.

#### Scenario: Train support is sufficient
- **WHEN** train collection reaches the fixed complete and informative floors
- **THEN** model selection may proceed without development access

#### Scenario: Train support is insufficient
- **WHEN** train collection misses either fixed support floor
- **THEN** the experiment stops before constructing the development partition

### Requirement: Train-only conservative policy selection
The experiment SHALL select both checkpoint epoch and Current-override confidence
using only the train-internal fit and tune split.

#### Scenario: Learned override is confident
- **WHEN** the ranker's score advantage over Current reaches the selected fixed confidence threshold
- **THEN** the gated policy selects the ranker's action

#### Scenario: Learned override is not confident
- **WHEN** the score advantage is below the selected threshold
- **THEN** the gated policy retains Current's legal action

### Requirement: Single-use policy-quality gate
The experiment MUST access development exactly once after selection and SHALL
compare gated, raw, untrained, and Current policies on fixed regret and ranking
metrics.

#### Scenario: Event ranker is ready
- **WHEN** development support passes, gated mean regret strictly improves Current, maximum and p95 regret do not worsen, at least one correction and action change occur, corrected sources are not outnumbered by worsened sources, and raw pairwise accuracy exceeds untrained
- **THEN** the verdict permits a separate shadow-evaluation proposal

#### Scenario: Any readiness gate fails
- **WHEN** any fixed development gate is unmet
- **THEN** the verdict is no-go for this model, configuration, and cohort without tuning or rerunning development

### Requirement: Reproducible offline artifacts
The experiment SHALL bind source, native, bridge, partitions, selected model,
configuration, and per-source predictions in canonical artifacts.

#### Scenario: Experiment completes
- **WHEN** the fixed run reaches a terminal verdict
- **THEN** train and development datasets round-trip exactly and every published artifact matches its manifest identity

### Requirement: Offline isolation
The experiment MUST NOT launch gameplay or CommunicationMod, access a production
checkpoint, alter policy behavior, qualify, promote, or perform online RL.

#### Scenario: Training execution
- **WHEN** the offline CPU experiment runs
- **THEN** downstream authority remains false and only the new report directory is written
