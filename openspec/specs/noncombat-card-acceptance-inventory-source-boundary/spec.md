# Noncombat Card-Acceptance Inventory Source-Boundary Specification

## Purpose

Define the fail-closed boundary between historical seed evidence and generated
report roots scanned by the card-acceptance inventory control plane.

## Requirements

### Requirement: Generated report roots are excluded before blob access
The source inventory SHALL classify generated roots from canonical Git paths
before artifact-format handling, unsupported-candidate checks, or Git blob
reads. Hidden directories directly below `reports/` ending in `.staging`,
`.scratch`, `.sealed`, `.temporary`, or `.tmp`, and direct report directories
ending in `_attempts`, SHALL be excluded with their fixed generated-root kind.
Existing exact candidate-output and successor-prefix exclusions SHALL remain.

#### Scenario: Consumed readiness staging root is present
- **WHEN** the source Git tree contains the exact r1-offending readiness staging path
- **THEN** the registry records its direct root as `staging` and never requests its gzip blob

#### Scenario: Representative generated variants are present
- **WHEN** tracked files appear below direct staging, scratch, sealed, temporary, tmp, or attempts roots under `reports/`
- **THEN** every root is classified once with the corresponding fixed kind before any child blob is read

### Requirement: Ordinary historical evidence remains eligible
Generic generated-root matching SHALL be limited to exact direct-root path
shapes. Ordinary files, nested directories, and names that merely contain a
generated-root token SHALL continue through normal format and source validation.

#### Scenario: Similar ordinary names are present
- **WHEN** supported historical evidence uses a normal direct root and has a filename or nested directory containing `staging`, `scratch`, `sealed`, `temporary`, `tmp`, or `attempt`
- **THEN** the path is not excluded solely for containing that token and its blob remains eligible for strict parsing

#### Scenario: Ordinary evidence is malformed
- **WHEN** a non-generated registered source contains malformed or unsupported seed evidence
- **THEN** inventory construction still fails closed rather than suppressing the source as generated output

### Requirement: The failed r1 inventory identity remains terminal
The system SHALL preserve the pushed r1 request, approval, authorization,
launch observation, failure, and failure review as immutable evidence. It SHALL
NOT retry, resume, repair, replace, or complete r1 after its sole build
invocation failed. The repair SHALL grant no new execution authority.

#### Scenario: Source-boundary repair passes
- **WHEN** the generic classifier and all repair verification pass
- **THEN** r1 remains terminal and only a separately reviewed future-identity proposal may become eligible

#### Scenario: Repair verification fails
- **WHEN** a generated path reaches blob access, an ordinary source is over-excluded, or independent review finds an unresolved issue
- **THEN** the repair stops without an inventory build, cohort materialization, native loading, model loading, training, evaluation, or gameplay

### Requirement: A future inventory identity requires a path-only predecessor preflight
Before authority publication for an inventory identity following terminal r1,
the system SHALL produce and independently review a source-only
preflight that binds the pushed receipt-hardening source commit and its repair
ancestry, current pushed and tracked-clean state, exact r1 terminal
evidence, candidate path identity, generated-root exclusions, and absence of
the new output and staging roots. The preflight SHALL NOT read candidate blobs
or seed values.

#### Scenario: Generated and unsupported paths are checked
- **WHEN** the preflight enumerates the registered Git report paths for the fixed source
- **THEN** generated roots are classified before format handling, supported candidate paths are deterministically committed, and any unsupported or ambiguous path blocks the identity before blob access

#### Scenario: The consumed readiness root is revisited
- **WHEN** the exact readiness staging root that terminated r1 is present in the fixed source tree
- **THEN** the preflight binds it as an excluded `staging` root and does not request its gzip blob

#### Scenario: Predecessor evidence or output state drifts
- **WHEN** an r1 request, launch, failure, or review digest changes, the receipt-hardening source or repair ancestry is not pushed, tracked files are dirty, or the new output, staging, or started-receipt path exists
- **THEN** the new identity remains pre-start NO-GO and no request authorization or build operation becomes eligible
