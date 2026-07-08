## ADDED Requirements

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
