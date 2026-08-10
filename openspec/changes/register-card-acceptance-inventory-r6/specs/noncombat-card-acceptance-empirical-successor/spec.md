## ADDED Requirements

### Requirement: Registration-only r6 consumes exact verified r5 evidence
R6 SHALL preserve the pushed r5 incident and archive boundaries as terminal and
SHALL NOT rebuild or reverify its inventory. Before mappings reach a pure
producer builder, the allowlisted driver SHALL strict-parse each raw r5 input,
reject duplicate keys, and require byte equality with canonical
trailing-newline JSON. The builder SHALL require complete agreement among the
inventory, build receipt, verification receipt, verification completion, and
standalone result before rendering one registration with the frozen v1 schema
and distinct r6 identity.
The first r6 registration-driver process invocation SHALL use the frozen
canonical request and exact CLI and SHALL consume the identity.
The driver SHALL exclusively publish an immutable started receipt before any
input open. Any process, receipt, input, parsing, validation, access-accounting,
output, or publication failure SHALL be terminal without reopening or retry.
The receipt SHALL bind the request and preflight digests, six input identities,
receipt/output paths, registration identity/schema, implementation and
inventory source commits, and exact command identity.

#### Scenario: Exact r5 evidence agrees
- **WHEN** every allowlisted r5 mapping is canonical and its source, request, authority, receipt, inventory, cohort, role, completion, and standalone bindings agree
- **THEN** the builder returns one canonical all-false r6 registration without filesystem discovery or downstream authority

#### Scenario: Verification prerequisite drifts
- **WHEN** a verification receipt, completion, standalone result, inventory field, or historical authority binding differs or is missing
- **THEN** registration construction fails without publishing a registration or completing parent task 6.2

#### Scenario: Input bytes are noncanonical
- **WHEN** an allowlisted input contains duplicate keys or bytes that differ from canonical trailing-newline JSON
- **THEN** the driver rejects it before decoded mappings reach registration construction

#### Scenario: R5 is treated as registered
- **WHEN** a caller uses the r5 registration identity, writes the r5 registration path, or claims the r5 terminal failure is resolved
- **THEN** r6 fails closed and preserves r5 as verified historical evidence without registration

#### Scenario: Driver fails before input access
- **WHEN** the first r6 driver invocation fails before or during receipt publication and no input has been opened
- **THEN** r6 is still consumed, every created receipt byte is preserved, and same-identity reinvocation is forbidden

### Requirement: Frozen registration validation is independently reproducible
The producer validator and independent standard-library validator SHALL enforce
the exact frozen 16-field registration schema, exact inventory cohorts and role
digests, exact 15-key authority map, exact 10-key empirical-operation map,
all-false values, and canonical trailing-newline self-digest. Missing, unknown,
duplicate, non-boolean, reordered-cohort, or mismatched evidence SHALL fail.

#### Scenario: Producer and standalone validators agree
- **WHEN** both validators receive the same canonical r6 registration and exact r5 inventory
- **THEN** both reproduce the same registration digest, identity, cohort counts, and all-false authority verdict

#### Scenario: Registration grants authority
- **WHEN** any authority or empirical-operation value is true or has a non-boolean representation
- **THEN** both validators reject the registration and no training request becomes eligible

#### Scenario: Registration bytes are noncanonical
- **WHEN** the registration contains duplicate or unknown fields, altered ordering semantics, or bytes that differ from canonical trailing-newline JSON
- **THEN** publication review fails and parent tasks 6.2 and 6.3 remain incomplete

### Requirement: R6 publication completes inventory registration only
Only exact producer registration construction/validation, independent
standalone validation, text-only static review, and pushed tracked-clean
publication SHALL complete parent task 6.2. The registration SHALL be
dual-validated in memory before one exclusive
create/write/flush/fsync publication attempt. Parent task 6.3 and every
training, evaluation, execution, or promotion authority SHALL remain incomplete
and absent.

#### Scenario: Registration publication succeeds
- **WHEN** the canonical r6 registration and review are exact, independently accepted, committed, and pushed
- **THEN** parent task 6.2 is completed while 6.3 remains incomplete and no downstream request is created

#### Scenario: Publication or review fails
- **WHEN** output writing, self-digest validation, independent validation, static review, pushed cleanliness, or access accounting is missing or ambiguous
- **THEN** r6 closes without replacing the registration and parent task 6.2 remains incomplete

#### Scenario: Publication fails after output creation
- **WHEN** exclusive output creation succeeds but canonical write, flush, fsync, or later publication validation fails
- **THEN** the existing complete or partial bytes are preserved, r6 is consumed, and same-identity deletion, retry, repair, or replacement is forbidden
