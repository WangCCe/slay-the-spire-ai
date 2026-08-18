## ADDED Requirements

### Requirement: Optional encounter identity observation
The system SHALL optionally append a deterministic encounter-identity feature
to simulator-only combat observations while preserving the default observation
when the feature is disabled.

#### Scenario: Default observation
- **WHEN** encounter identity is disabled
- **THEN** the runner uses the existing continuous dimension and checkpoint behavior unchanged

#### Scenario: Encounter feature
- **WHEN** a positive encounter bucket count is registered
- **THEN** every supported current and successor state receives exactly one active deterministic encounter bucket appended to its continuous observation

#### Scenario: Invalid encounter metadata
- **WHEN** the native snapshot omits a valid encounter identity in enabled mode
- **THEN** the runner fails without substituting a battle index, floor, or unknown bucket

### Requirement: Parent-equivalent input expansion
The system SHALL expand only a bound simulator parent into the encounter-aware
network and SHALL prove numerical control equivalence before collecting
training transitions.

#### Scenario: Zero-column migration
- **WHEN** an existing simulator-only parent is loaded into an encounter-aware network
- **THEN** legacy continuous and embedding columns and all downstream parameters are copied unchanged while new encounter columns are initialized to zero

#### Scenario: Pre-training equivalence
- **WHEN** migration completes
- **THEN** deterministic probes show numerically equivalent masked Q values and identical greedy actions between the legacy parent and migrated control

#### Scenario: Unsupported initialization
- **WHEN** encounter identity is requested without a structurally compatible simulator parent or equivalence proof fails
- **THEN** the runner stops before native trajectory collection and publishes no candidate

### Requirement: Encounter-aware evidence binding
The system SHALL bind the encounter encoding and parent migration evidence in
simulator-only reports and checkpoints without granting live authority.

#### Scenario: Training report
- **WHEN** encounter-aware training completes
- **THEN** the report records the hash algorithm, bucket count, observed encounter-to-bucket assignments, original and migrated parent hashes, and equivalence metrics

#### Scenario: Production isolation
- **WHEN** an encounter-aware candidate is published
- **THEN** it remains production-incompatible and grants no gameplay, transfer, qualification, or promotion authority
