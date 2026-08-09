## ADDED Requirements

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
