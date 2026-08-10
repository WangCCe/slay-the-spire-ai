## MODIFIED Requirements

### Requirement: A future inventory identity requires a path-only predecessor preflight
Before authority publication for an inventory identity following a terminal
predecessor, the system SHALL produce and independently review a source-only
preflight that binds the pushed source repair and its ancestry, current pushed
and tracked-clean state, every exact terminal predecessor, candidate path
identity, generated-root exclusions, and absence of the new output, staging,
attempts, started-receipt, verification, and registration paths. For r4, the
preflight SHALL bind the exact compact-v4 isolated-dispatch observation, all
r1/r2/r3 terminal evidence, the 64 MiB canonical inventory ceiling, the
2,048-byte CLI completion ceiling, and exclusion of the terminal r3 output
root. It SHALL NOT read candidate blobs, seed values, or r3 inventory content.

#### Scenario: Generated and unsupported paths are checked
- **WHEN** the preflight enumerates the registered Git report paths for the fixed source
- **THEN** generated roots are classified before format handling, supported candidate paths are deterministically committed, and any unsupported or ambiguous path blocks the identity before blob access

#### Scenario: The consumed readiness root is revisited
- **WHEN** the exact readiness staging root that terminated r1 is present in the fixed source tree
- **THEN** the preflight binds it as an excluded `staging` root and does not request its gzip blob

#### Scenario: All terminal predecessors are bound for r4
- **WHEN** r4 preflight is rendered before request publication
- **THEN** it binds exact r1/r2/r3 request, launch, receipt where present, failure, review, terminal status, and non-retry identities together with the pushed compact-v4 source and isolated dispatch

#### Scenario: Terminal r3 output is present
- **WHEN** the untracked terminal r3 output path remains on disk during r4 preflight
- **THEN** preflight requires its preservation and exclusion while opening, streaming, hashing, parsing, validating, converting, deleting, or registering its content remains forbidden

#### Scenario: Compact source or output state drifts
- **WHEN** a predecessor identity changes, the fixed compact source ancestry or dispatch binding is not pushed, tracked files are dirty, schema or byte ceilings drift, or any r4 output, staging, attempt, receipt, verification, or registration path exists
- **THEN** r4 remains pre-start NO-GO and no request authorization or build operation becomes eligible
