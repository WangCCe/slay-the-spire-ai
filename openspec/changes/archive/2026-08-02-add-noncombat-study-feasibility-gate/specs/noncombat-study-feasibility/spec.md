## ADDED Requirements

### Requirement: Deterministic Study Operating Characteristics
The system SHALL compute deterministic planning-only operating characteristics from a registered attempt budget, registered supported-victory threshold, and source-bound reference evidence.

#### Scenario: Valid reference evidence is audited
- **WHEN** a canonical manifest binds one registration and one readiness artifact with valid hashes, sizes, complete trajectory outcomes, and exact target weights
- **THEN** the analyzer SHALL derive the scheduled attempts and required supported victories from the registration
- **AND** it SHALL derive complete trajectories, raw victories, and target-supported victories from exact trajectory identities and rational target-weight numerators
- **AND** it SHALL report the plug-in probability of meeting the registered supported-victory threshold plus deterministic 50%, 80%, and 90% required-rate thresholds and a fixed sensitivity table

#### Scenario: Raw victory has zero target support
- **WHEN** a complete trajectory has `victory=true` and target-weight numerator zero
- **THEN** the analyzer SHALL count it as a raw victory and not as a target-supported victory
- **AND** it SHALL NOT use that raw victory to increase the supported-victory plug-in rate or feasibility result

### Requirement: Source-Qualified Feasibility Classification
The system SHALL classify feasibility as demonstrated only from sufficiently large source-comparable evidence and SHALL expose historical evidence separately.

#### Scenario: Feasibility is demonstrated
- **WHEN** at least 100 complete reference trajectories are source-comparable, their exact supported-victory count is positive, and the observed plug-in probability of meeting the registered threshold is at least 0.80
- **THEN** the report SHALL set `study_feasibility=demonstrated`
- **AND** it SHALL state that this permits only a separate reviewed launch amendment

#### Scenario: Feasibility is not demonstrated
- **WHEN** the reference has fewer than 100 complete trajectories, is historical-only or otherwise source-incomparable, has no supported victory, or has plug-in pass probability below 0.80
- **THEN** the report SHALL set `study_feasibility=not_demonstrated` and enumerate every blocker
- **AND** it SHALL NOT recommend extending attempts, lowering the victory threshold, substituting floor reached, or treating raw victories as supported

### Requirement: Offline Feasibility Artifact Boundary
The feasibility analyzer SHALL remain offline-only and SHALL emit deterministic, provenance-bound artifacts with all gameplay and training authority closed.

#### Scenario: Audit artifacts are generated
- **WHEN** analysis succeeds
- **THEN** canonical JSON and Markdown SHALL bind input paths, hashes, sizes, observed counts, arithmetic configuration, operating characteristics, result, blockers, and limitations
- **AND** rerunning with identical bytes and configuration SHALL reproduce identical output bytes

#### Scenario: Inputs or outputs are invalid
- **WHEN** an input is missing, non-canonical, duplicate-keyed, hash-mismatched, structurally inconsistent, or an output path collides with an input
- **THEN** analysis SHALL fail before publishing either output
- **AND** it SHALL leave CommunicationMod, game files, qualification roots, study state, checkpoints, models, policies, rewards, and training state unchanged

#### Scenario: Feasibility result is interpreted
- **WHEN** the result is either `demonstrated` or `not_demonstrated`
- **THEN** qualification preparation, study start, gameplay collection, OPE policy claims, causal claims, reward changes, formal training, and live promotion SHALL remain unauthorized
