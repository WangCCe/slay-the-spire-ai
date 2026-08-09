## ADDED Requirements

### Requirement: A future inventory identity requires a path-only predecessor preflight
Before authority publication for an inventory identity following terminal r1,
the system SHALL produce and independently review a source-only preflight that
binds the pushed receipt-hardening source commit and its repair ancestry,
current pushed and tracked-clean state, exact r1 terminal evidence, candidate
path identity, generated-root exclusions, and
absence of the new output and staging roots. The preflight SHALL NOT read
candidate blobs or seed values.

#### Scenario: Generated and unsupported paths are checked
- **WHEN** the preflight enumerates the registered Git report paths for the fixed source
- **THEN** generated roots are classified before format handling, supported candidate paths are deterministically committed, and any unsupported or ambiguous path blocks the identity before blob access

#### Scenario: The consumed readiness root is revisited
- **WHEN** the exact readiness staging root that terminated r1 is present in the fixed source tree
- **THEN** the preflight binds it as an excluded `staging` root and does not request its gzip blob

#### Scenario: Predecessor evidence or output state drifts
- **WHEN** an r1 request, launch, failure, or review digest changes, the receipt-hardening source or repair ancestry is not pushed, tracked files are dirty, or the new output, staging, or started-receipt path exists
- **THEN** the new identity remains pre-start NO-GO and no request authorization or build operation becomes eligible
