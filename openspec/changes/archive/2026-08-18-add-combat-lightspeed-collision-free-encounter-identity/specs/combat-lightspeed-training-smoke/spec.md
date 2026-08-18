## MODIFIED Requirements

### Requirement: Optional encounter identity observation
The system SHALL optionally append a deterministic registered encounter-identity
feature to simulator-only combat observations while preserving the default
observation when the feature is disabled.

#### Scenario: Default observation
- **WHEN** encounter identity is disabled
- **THEN** the runner uses the existing continuous dimension and checkpoint behavior unchanged

#### Scenario: Hash encounter feature
- **WHEN** the registered hash encoding and a positive bucket count are selected
- **THEN** every supported current and successor state receives exactly one deterministic hashed encounter bucket appended to its continuous observation

#### Scenario: Collision-free encounter feature
- **WHEN** the registered LightSTS enum-v1 encoding and 64 buckets are selected
- **THEN** bucket zero remains reserved and every canonical LightSTS encounter maps to a unique bucket from 1 through 63 in source order

#### Scenario: Invalid encounter metadata
- **WHEN** the native snapshot omits a valid encounter identity or enum-v1 receives an unknown identity
- **THEN** the runner fails without substituting a battle index, floor, hash, or unknown bucket

#### Scenario: Encoding evidence
- **WHEN** encounter identity is enabled
- **THEN** the report and simulator-only checkpoint bind the encoding name, bucket count, assignments, and canonical vocabulary hash when applicable
