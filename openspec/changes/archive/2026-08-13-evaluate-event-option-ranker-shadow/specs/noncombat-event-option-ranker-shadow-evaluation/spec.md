## ADDED Requirements

### Requirement: Bound selected model
The evaluator SHALL verify and load the exact manifest-bound event model and
selected confidence threshold without changing either.

#### Scenario: Model identity matches
- **WHEN** the model bytes, schema, architecture, state, and manifest binding match
- **THEN** the evaluator may construct the fresh shadow partition

#### Scenario: Model identity differs
- **WHEN** any required model identity or round-trip check differs
- **THEN** the evaluator stops before native seed access

### Requirement: Disjoint no-training shadow cohort
The evaluator SHALL use the fixed fresh seed schedule exactly once and MUST NOT
fit, tune, select, or retry a model or confidence threshold.

#### Scenario: Fresh evaluation runs
- **WHEN** model preflight passes
- **THEN** every eligible source is evaluated under the bound selected policy and Current comparator

### Requirement: Fixed replication gate
The evaluator SHALL decide replication using fixed support, diversity, regret,
and correction gates.

#### Scenario: Benefit replicates
- **WHEN** complete, informative, and event-diversity floors pass, selected mean regret improves Current, p95 and maximum regret do not worsen, at least one action change and correction occur, and corrections are not outnumbered by regressions
- **THEN** the verdict permits a separate full-trajectory simulator-shadow proposal

#### Scenario: Replication fails
- **WHEN** any fixed gate is unmet
- **THEN** the verdict terminates this model without tuning or rerunning the fresh cohort

### Requirement: Auditable offline evidence
The evaluator SHALL publish canonical dataset, metrics, configuration, identity,
per-event diagnostics, and manifest artifacts with downstream authority false.

#### Scenario: Terminal report is written
- **WHEN** evaluation completes
- **THEN** the dataset round-trips exactly and every manifest-bound artifact matches its recorded identity

### Requirement: Offline isolation
The evaluator MUST NOT launch gameplay or CommunicationMod, access a production
checkpoint, fit a model, alter live policy behavior, qualify, or promote.

#### Scenario: Shadow execution
- **WHEN** the evaluator runs
- **THEN** only the new report directory is written and no production authority is granted
