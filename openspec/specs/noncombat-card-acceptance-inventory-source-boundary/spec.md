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

### Requirement: R6 registration access is path-allowlisted and non-discovering
Before any r6 registration input is opened, the system SHALL publish and
independently review an exact allowlist containing only the current r5
inventory, build receipt, verification receipt, verification completion,
standalone verification result, verification review, and the bounded r6 output
paths. The registration driver SHALL NOT enumerate directories, expand globs,
search report roots, inspect predecessor roots, or infer substitute evidence.
The preflight SHALL also bind the pushed r5 incident and archive commits, absent
r5 registration, and unchanged incomplete parent tasks 6.2/6.3. After that
preflight is pushed, the system SHALL publish and review one canonical
self-digested driver request binding the preflight digest, exact six evidence
inputs with six `canonical_json` content kinds, receipt/output paths,
registration identity/schema, implementation and inventory source commits,
exact all-false downstream map, and sole permitted CLI shape with separately
reviewed expected request digest and receipt path. The driver SHALL publish its
invocation receipt before reading the request as its only caller-selected
control path and SHALL NOT open the preflight file.

#### Scenario: Exact allowlist is used
- **WHEN** every input path, content kind, and byte identity equals the pushed r5 evidence and every r6 receipt/output path is absent
- **THEN** the one-shot driver may claim its immutable receipt, open each allowlisted input exactly once, pass the required decoded JSON mappings to the pure registration builder, and account for all six canonical inputs

#### Scenario: Driver request drifts
- **WHEN** the request bytes, self-digest, preflight binding, input set, source commit, receipt/output path, registration identity, downstream map, or command shape differs
- **THEN** the first invocation fails closed without substituting another request or retrying r6

#### Scenario: A self-digested substitute request is supplied
- **WHEN** request bytes are internally canonical and self-digested but differ from the expected request SHA-256 frozen in the exact CLI and invocation receipt
- **THEN** the driver rejects the substitute after preserving the receipt and before evidence access

#### Scenario: A report root is searched
- **WHEN** registration planning or execution enumerates, globs, or text-searches `reports` or another root containing protected predecessor inventories
- **THEN** r6 fails closed before registration publication and grants no downstream authority

#### Scenario: A predecessor path is supplied
- **WHEN** an r1-r4 inventory path, symlink, alias, wildcard, additional file, or unregistered substitute appears in the input set
- **THEN** the driver rejects the access set before opening candidate input bytes

#### Scenario: Directory discovery is attempted
- **WHEN** the driver invokes directory iteration, globbing, recursive search, or root enumeration instead of validating the exact supplied allowlist
- **THEN** r6 fails closed and the first invocation cannot be retried

#### Scenario: R5 terminal state drifts
- **WHEN** the r5 incident/archive commits, absent r5 registration, or parent 6.2/6.3 state differs from the preregistered boundary
- **THEN** r6 remains NO-GO before any registration input is opened

### Requirement: R6 records complete access isolation
The r6 publication review SHALL record that the observed input access set equals
the six-file evidence allowlist plus the single request control input,
predecessor content was not accessed, no unexpected process survived, the
immutable receipt plus registration are the exact driver outputs, and native,
model, environment, gameplay, training, evaluation, OPE, qualification, and
promotion operations were not performed. Independent reviews SHALL receive
exact bounded text only, SHALL have no tool or path access, and SHALL NOT
enumerate or search repository/report roots. The later static review artifact
is created by the owning task after the driver has exited and is accounted
separately from the driver's closed output set.

#### Scenario: Access accounting is exact
- **WHEN** registration construction and both validators finish with the exact allowlisted access set and no prohibited operation
- **THEN** the bounded review may accept the registration for parent task 6.2 only

#### Scenario: Access accounting is incomplete
- **WHEN** any opened path, process, output, or prohibited-operation observation is missing or ambiguous
- **THEN** r6 fails closed without registration acceptance or parent-task changes

#### Scenario: An allowlisted input is reopened
- **WHEN** the observed access ledger contains zero or more than one open for any registered input or contains an additional path
- **THEN** r6 fails closed without deleting evidence or reinvoking the driver

#### Scenario: A reviewer accesses an unregistered path
- **WHEN** implementation or registration review invokes a tool, searches a root, or reads a path outside its exact text input
- **THEN** r6 fails closed and no registration or parent-task change is accepted
