## MODIFIED Requirements

### Requirement: A future inventory identity requires a path-only predecessor preflight
Before authority publication for an inventory identity following a terminal
predecessor, the system SHALL produce and independently review a source-only
preflight that binds the pushed source repair and its ancestry, current pushed
and tracked-clean state, every exact terminal predecessor, candidate path
identity, generated-root exclusions, and absence of the new output, staging,
attempts, and started-receipt paths. For r3, the preflight SHALL also bind the
exact isolated-dispatch observation and the terminal r1/r2 evidence. The
preflight SHALL NOT read candidate blobs or seed values.

#### Scenario: Generated and unsupported paths are checked
- **WHEN** the preflight enumerates the registered Git report paths for the fixed source
- **THEN** generated roots are classified before format handling, supported candidate paths are deterministically committed, and any unsupported or ambiguous path blocks the identity before blob access

#### Scenario: The consumed readiness root is revisited
- **WHEN** the exact readiness staging root that terminated r1 is present in the fixed source tree
- **THEN** the preflight binds it as an excluded `staging` root and does not request its gzip blob

#### Scenario: Both terminal predecessors are bound for r3
- **WHEN** r3 preflight is rendered before request publication
- **THEN** it binds exact r1 and r2 request, launch, failure, review, terminal status, and non-retry identities together with the pushed isolated-dispatch repair

#### Scenario: Predecessor evidence or output state drifts
- **WHEN** a predecessor request, launch, failure, or review digest changes, the fixed repair ancestry or dispatch binding is not pushed, tracked files are dirty, or the new output, staging, attempts, or started-receipt path exists
- **THEN** the new identity remains pre-start NO-GO and no request authorization or build operation becomes eligible
