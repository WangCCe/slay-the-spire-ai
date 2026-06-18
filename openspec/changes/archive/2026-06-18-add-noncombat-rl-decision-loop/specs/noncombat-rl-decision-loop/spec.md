## ADDED Requirements
### Requirement: Canonical Non-Combat Decision Samples
The system SHALL produce versioned, JSON-serializable decision samples for shop, event, route, and card-reward decisions.

#### Scenario: Complete trace row becomes a trainable sample
- **WHEN** a decision trace row contains the selected action, screen context, player state, deck, relics, and category-specific options
- **THEN** the exporter records a sample with category, floor, act, state snapshot, candidate actions, current-policy label, Bottled-style reference label, evidence quality, and source metadata

#### Scenario: Partial trace row preserves limitations
- **WHEN** a decision trace row is missing context required for complete candidate actions or labels
- **THEN** the exporter still records the sample when possible and marks evidence quality and limitations so it is not treated as complete training evidence

### Requirement: Candidate Action Normalization
The system SHALL normalize candidate actions across shop, event, route, and card-reward decisions into a shared action shape.

#### Scenario: Category candidates are normalized
- **WHEN** the exporter processes any supported non-combat category
- **THEN** each candidate action includes a stable action id, kind, label, availability flag, and raw source payload where available

#### Scenario: Selected action maps to a candidate
- **WHEN** the selected current-policy action is present among normalized candidates
- **THEN** the sample records the selected action id and preserves the current-policy choice label

### Requirement: Conservative Live Outcome Join
The system SHALL attach live outcome data to decision samples only when the sample can be matched to exactly one reliable run record.

#### Scenario: Unique run match attaches outcome
- **WHEN** a sample trace timestamp can be matched to exactly one AI-marked `.run` record within the accepted run timestamp and playtime window
- **THEN** the sample records outcome fields including victory, floor reached, killed-by, playtime, and outcome join status `matched`

#### Scenario: Missing or ambiguous run match is explicit
- **WHEN** no reliable run match exists or multiple run records could match the sample
- **THEN** the sample records outcome join status `missing` or `ambiguous` and the promotion gate excludes that sample from live-outcome metrics

### Requirement: Offline Evaluation And Promotion Gate
The system SHALL produce a deterministic offline report and promotion gate for non-combat RL readiness.

#### Scenario: Gate blocks incomplete readiness
- **WHEN** state, action, reward, or evaluation definitions are missing tests or report coverage
- **THEN** the gate reports `blocked` and lists the missing readiness areas

#### Scenario: Gate summarizes fresh eval evidence
- **WHEN** a bounded fresh eval has decision samples and matched live outcomes
- **THEN** the report includes sample counts by category, evidence quality, candidate coverage, Bottled agreement, repeated high-confidence gaps, live outcome metrics, and promotion status

### Requirement: Non-Combat Reward Readiness Contract
The system SHALL define the reward-readiness contract needed before formal non-combat RL training can begin.

#### Scenario: Reward contract is reported
- **WHEN** the offline evaluator renders non-combat RL readiness
- **THEN** it reports the reward components, required outcome fields, exclusions, and unresolved reward gaps used by the training guard

#### Scenario: Missing reward contract blocks training
- **WHEN** reward components or required outcome fields are not defined or tested
- **THEN** the promotion gate reports formal non-combat RL training as blocked by reward readiness

### Requirement: Formal Non-Combat RL Training Guard
The system SHALL prevent formal non-combat RL training from being treated as ready until the decision loop is fully defined and verified.

#### Scenario: Combat RL smoke remains allowed
- **WHEN** a developer runs a small combat RL smoke training or dry-run command
- **THEN** the report may use it as training-pipeline health evidence without marking formal non-combat RL training as ready

#### Scenario: Non-combat training remains blocked before readiness
- **WHEN** the state schema, action schema, reward definition, or evaluation gate lacks tests and report support
- **THEN** the system reports formal non-combat RL training as blocked
