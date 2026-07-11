# noncombat-rl-decision-loop Specification

## Purpose
TBD - created by archiving change add-noncombat-rl-decision-loop. Update Purpose after archive.
## Requirements
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

### Requirement: Bottled Policy Oracle Adapter
The system SHALL provide an offline-only adapter that evaluates Ironclad non-combat decision samples against the local Bottled `REQUESTED_STRIKE` policy.

#### Scenario: Native Bottled oracle evaluates a supported sample
- **GIVEN** a complete shop, card-reward, event, or route decision sample
- **AND** a readable local Bottled checkout containing the `REQUESTED_STRIKE` strategy
- **WHEN** the Bottled oracle adapter evaluates the sample
- **THEN** it returns a reference label, confidence, concise reason, raw Bottled command or decision payload where available, source metadata, and limitations
- **AND** it does not launch Slay the Spire, CommunicationMod, or a live gameplay process

#### Scenario: Missing or incompatible Bottled context is explicit
- **GIVEN** a sample that cannot be represented faithfully for a Bottled handler
- **OR** the Bottled checkout is missing, unreadable, or incompatible
- **WHEN** the adapter evaluates the sample
- **THEN** it returns an `unsupported`, `partial`, or `error` oracle result with limitations
- **AND** it SHALL NOT emit a native high-confidence Bottled label for that sample

#### Scenario: Combat remains feasibility-only
- **GIVEN** a combat decision sample or combat trace row
- **WHEN** the Bottled oracle adapter is requested to inspect combat support
- **THEN** it reports feasibility and missing context
- **AND** it SHALL NOT replace the current combat policy or mark combat replacement as ready

### Requirement: Bottled Oracle Labels In Samples And Reports
The system SHALL include native Bottled oracle evidence in non-combat samples and current-vs-Bottled disagreement reports.

#### Scenario: Oracle label maps to a normalized candidate action
- **GIVEN** a native Bottled oracle result for a complete supported sample
- **AND** the oracle label or command corresponds to one of the normalized candidate actions
- **WHEN** the sample is exported or reported
- **THEN** the Bottled label includes the mapped candidate action id, oracle source mode, strategy name, Bottled repo path, Bottled commit when available, confidence, reason, and limitations

#### Scenario: Unmapped oracle label remains auditable
- **GIVEN** a native Bottled oracle result whose label or command cannot be mapped to a normalized candidate action
- **WHEN** the sample is exported or reported
- **THEN** the raw oracle label or command is preserved
- **AND** the candidate action id is left empty with an explicit limitation

#### Scenario: Disagreement report separates oracle modes
- **GIVEN** a report that includes native Bottled oracle rows and Bottled-style fallback rows
- **WHEN** current-vs-Bottled agreement and mismatch summaries are rendered
- **THEN** the report distinguishes native Bottled oracle evidence from fallback evidence
- **AND** repeated high-confidence repair candidates are ranked only when evidence quality, oracle mode, and outcome coverage justify them

### Requirement: Live Gameplay And Training Guards Remain Intact
The system SHALL keep Bottled oracle evaluation read-only and SHALL preserve existing live gameplay and formal non-combat RL training guards.

#### Scenario: Oracle execution does not alter live configuration
- **GIVEN** a developer runs the Bottled oracle adapter or non-combat report command
- **WHEN** the command completes successfully or fails
- **THEN** it SHALL NOT modify CommunicationMod `config.properties`, checkpoints, live agent code paths, or run launcher defaults

#### Scenario: Formal non-combat RL training remains blocked
- **GIVEN** Bottled oracle labels are present in samples and reports
- **WHEN** the non-combat RL readiness gate is evaluated
- **THEN** formal non-combat RL training remains blocked unless the existing state, action, reward, and evaluation readiness requirements are all satisfied by tests and reports
