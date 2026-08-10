# Noncombat Card-Acceptance Empirical Successor Specification

## Purpose

Define durable one-shot execution and distinct successor identity boundaries
for source-only card-acceptance inventory construction.
## Requirements
### Requirement: Inventory build start is durably one-shot
After all pre-start authority and source validations pass, `build-inventory`
SHALL atomically claim the request-bound started path through exclusive file
creation, write the canonical receipt, flush it, and fsync it before historical
path discovery, blob reads, or seed discovery. Existence is the consumption
boundary: an in-progress, empty, partial, invalid, or complete receipt SHALL
block every later invocation of the same request regardless of output or
staging state. The receipt bytes SHALL remain immutable after success or
failure. Process creation or failure before receipt creation SHALL NOT by
itself classify the request as started or terminal. A pre-start invocation MAY
be repeated only after a bounded failure artifact and independent review prove
that the exact source, command, request, path, approval, authorization,
resource, cohort, and authority bindings are unchanged; every registered write
surface is absent or unchanged; no unexpected child remains; and no candidate
blob, seed, or cohort was accessed. A fresh reviewed revocation observation MAY
replace only the prior launch observation for the same exact authority chain.
The original launch SHALL remain immutable, and a separate canonical
reinvocation review SHALL bind the pre-start failure, original launch,
replacement launch, unchanged request/approval/authorization chain,
external-only repair, complete side-effect verdict, and one-use eligibility.
Any missing or ambiguous observation or other changed binding requires a
distinct successor identity. Separately registered source/path preflights MAY
enumerate Git paths before request publication; they are not build-owned
historical path discovery or candidate-blob processing. Each request permits at
most one reviewed pre-start reinvocation. Starting that second process consumes
its eligibility even if no receipt is created; another pre-start failure closes
the request and requires a distinct successor.

#### Scenario: First invocation fails before publication
- **WHEN** an authorized inventory invocation writes its started receipt and then fails during historical source processing before output or staging publication
- **THEN** a second invocation with the same request is rejected before source discovery and cannot resume, retry, replace, or repair the consumed identity

#### Scenario: A partial receipt already exists
- **WHEN** the request-bound started path contains an empty file, truncated JSON, or invalid canonical receipt from an interrupted first invocation
- **THEN** every later invocation is rejected before source discovery and the existing bytes are preserved without parsing, repair, replacement, or deletion

#### Scenario: Receipt write is interrupted
- **WHEN** exclusive receipt creation succeeds but canonical writing, flush, or fsync is interrupted or fails
- **THEN** the existing empty or partial path consumes the request, remains immutable evidence, and blocks every later invocation before source discovery

#### Scenario: Validation fails before start
- **WHEN** the `build-inventory` invocation fails authority, source inventory, pushed ancestry, tracked cleanliness, output absence, request identity, or process-entrypoint validation before receipt creation
- **THEN** no started receipt, build-owned historical path discovery, candidate-blob read, seed discovery, cohort materialization, or output publication occurs and the identity is not consumed solely by process creation

#### Scenario: Exact pre-start invocation is reconsidered
- **WHEN** a bounded independently reviewed pre-start failure proves every registered write/process/access surface complete and clean and an external-only repair leaves request/source/authority bytes unchanged
- **THEN** the exact invocation may be repeated with a fresh reviewed revocation observation only after a canonical reinvocation review binds the failure, immutable original launch, replacement launch, unchanged authority chain, and one-use eligibility

#### Scenario: Replacement launch is not chained
- **WHEN** a new launch observation lacks the exact pre-start failure, original-launch, unchanged-authority, complete-side-effect, or one-use review binding
- **THEN** it cannot authorize another invocation of the same request

#### Scenario: Reviewed reinvocation starts
- **WHEN** the sole canonical reinvocation review authorizes invocation ordinal two and that process is created
- **THEN** its one-use eligibility is consumed and no second reinvocation review may authorize the same request

#### Scenario: Reviewed reinvocation fails before receipt
- **WHEN** invocation ordinal two fails before receipt creation
- **THEN** the system publishes a reviewed prestart-terminal artifact, closes the current identity without registration, and requires a distinct successor rather than a third invocation

#### Scenario: Pre-start side effects are incomplete or ambiguous
- **WHEN** the failure artifact or review cannot prove one registered path, child-process, tracked-file, candidate-blob, seed, or cohort observation
- **THEN** the current identity remains blocked and the same request cannot be invoked again

#### Scenario: A pre-start repair changes a binding
- **WHEN** correcting a pre-start failure would change code, source commit, command, request, path, approval, authorization, resource, cohort, authority, or another non-revocation bound byte
- **THEN** the current identity remains blocked and only a distinct preregistered successor may use the changed binding

#### Scenario: Inventory publication succeeds
- **WHEN** the started request builds and publishes its inventory successfully
- **THEN** the immutable receipt remains as separate execution evidence and does not grant verification, registration, training, or downstream authority

### Requirement: Terminal inventory predecessor requires a distinct preregistered identity
After an authorized inventory identity terminates in failure, the successor
control plane SHALL preserve that identity and SHALL require a separately
reviewed source commit, request id, output root, request, approval,
authorization, and launch observation before another inventory identity can
start. A predecessor request, approval, authorization, launch, receipt, output,
or verification artifact SHALL NOT authorize the successor identity. r1, r2,
and r3 SHALL remain terminal while r4 uses the pushed compact-v4 source and a
distinct authority chain.

#### Scenario: Distinct r2 passes every pre-start gate
- **WHEN** r1 is terminal, the pushed receipt-hardening source and path preflight are exact, r2 output and receipt are absent, and fresh r2 authority artifacts validate
- **THEN** the system permits at most one r2 `build-inventory` invocation with no native, model, environment, training, evaluation, or gameplay authority

#### Scenario: R2 predecessor or identity artifact is substituted
- **WHEN** r2 uses an r1 request, approval, authorization, or launch binding, or any registered r2 source, request id, path, digest, or authority field drifts
- **THEN** the system stops before blob reads, seed discovery, cohort materialization, or output publication

#### Scenario: The r2 invocation fails after start
- **WHEN** the sole r2 build invocation reaches any terminal failure
- **THEN** the system preserves a reviewed failure, creates no registration, and does not retry, resume, tune, or replace the identity

#### Scenario: The r2 invocation succeeds
- **WHEN** r2 publishes exactly one inventory and a distinct read-only verification reconstructs the same source registry, exclusions, rows, and cohorts
- **THEN** the system may publish one all-false registration for exactly 512 training, 128 canary, and 512 holdout seeds without granting training or downstream execution authority

#### Scenario: Distinct r3 passes every pre-start gate
- **WHEN** r1 and r2 are terminal, the pushed isolated-dispatch source and exact dispatch/path preflights are verified, r3 output and receipt are absent, and fresh r3 authority artifacts validate
- **THEN** the system permits one receipt-defined logical r3 build start with no native, model, environment, training, evaluation, gameplay, qualification, or promotion authority

#### Scenario: R3 predecessor or identity artifact is substituted
- **WHEN** r3 uses an r1/r2 request, approval, authorization, or launch binding, or any registered r3 source, request id, path, digest, dispatch, or authority field drifts
- **THEN** the system stops before blob reads, seed discovery, cohort materialization, or output publication

#### Scenario: The r3 invocation fails after start
- **WHEN** the r3 build writes any started receipt and reaches a terminal failure
- **THEN** the system preserves its receipt, output, reviewed failure, and unverified status; creates no registration; and does not retry, resume, verify, convert, tune, or replace r3

#### Scenario: Distinct r4 passes every pre-start gate
- **WHEN** r1/r2/r3 are terminal, the pushed compact-v4 source and exact dispatch/path preflights are verified, r4 write surfaces are absent, and fresh r4 authority artifacts validate
- **THEN** the system permits one receipt-defined logical r4 build start with no native, model, environment, training, evaluation, gameplay, qualification, promotion, or downstream authority

#### Scenario: R4 predecessor or identity artifact is substituted
- **WHEN** r4 uses any predecessor request, approval, authorization, launch, receipt, output, or verification binding, or any registered r4 source, request id, path, digest, dispatch, schema, byte ceiling, or authority field drifts
- **THEN** the system stops before blob reads, seed discovery, cohort materialization, output publication, or registration

#### Scenario: The r4 invocation fails after start
- **WHEN** r4 writes any started receipt and reaches a build, compactness, publication, completion, or verification failure
- **THEN** the system preserves reviewed terminal evidence, creates no registration, and does not retry, resume, tune, raise bounds, or replace the identity

#### Scenario: The r4 invocation succeeds
- **WHEN** r4 publishes a bounded v4 inventory and distinct source-only plus standalone verification reconstruct every aggregate, cohort, digest, authority, receipt, and output binding
- **THEN** the system may publish one all-false registration for exactly 512 training, 128 canary, and 512 holdout seeds without granting training or downstream execution authority

### Requirement: A successor entrypoint is proven in exact isolated dispatch
Before authority publication for a successor inventory identity, the system
SHALL execute a side-effect-free dispatch check using the registered
interpreter, working directory, isolated-mode flag, and seed-inventory script
path. The check SHALL import the configured control module from its fixed
repository path and emit a deterministic canonical binding without reading
authority artifacts, Git evidence, candidate blobs, or seeds and without
creating receipt, staging, output, cohort, or registration artifacts. The
binding SHALL include the normalized interpreter, working directory, script
path and digest, validated command tuple, isolated-mode state, control module
and path, and experiment-contract digest. A successor preflight and source
inventory SHALL reproduce that binding before request publication.

#### Scenario: Exact isolated dispatch succeeds
- **WHEN** the fixed seed-inventory script runs `check-dispatch` through the registered interpreter and `-I` entrypoint
- **THEN** it exits successfully with canonical evidence binding the complete process tuple, script identity, configured control module and path, and experiment contract digest

#### Scenario: Dispatch identity drifts
- **WHEN** the interpreter, working directory, command, script identity, isolated mode, configured module, resolved module path, repeated canonical output, source inventory, or pushed source commit drifts
- **THEN** successor authority publication remains blocked before request, source, receipt, output, or seed access

#### Scenario: Dispatch check passes
- **WHEN** the exact isolated dispatch check and its no-side-effect regressions pass
- **THEN** the result establishes only source-entrypoint readiness and grants no inventory invocation, registration, native, model, environment, training, evaluation, gameplay, qualification, or promotion authority

### Requirement: Verified r3 inventory registration remains execution-inert
Only a successful r3 inventory followed by distinct read-only reconstruction
SHALL become eligible for one canonical registration. The registration SHALL
bind the fixed source/request/authorization/launch/receipt/inventory identities,
the exact ordered 512 training, 128 canary, and 512 holdout cohorts, their role
digests, and an all-false downstream authority and empirical-operation map. It
SHALL use the preregistered schema and field set, derive its self-digest from
canonical JSON, reject every missing, unknown, duplicate, or non-boolean
authority/operation field, and grant no training-request or execution authority.

#### Scenario: Independent reconstruction matches
- **WHEN** the read-only verifier reproduces every source row, exclusion, cohort, role digest, whole-inventory digest, and authority binding from the closed r3 output
- **THEN** one all-false registration may be published and parent task 6.2 may be completed while task 6.3 remains incomplete

#### Scenario: Reconstruction or registration review fails
- **WHEN** any source row, exclusion, cohort, digest, authority binding, output closure, receipt identity, or all-false field differs or cannot be independently reconstructed
- **THEN** no registration is published, parent task 6.2 remains incomplete, and no training or downstream authority becomes eligible

#### Scenario: Registration schema is frozen before seed access
- **WHEN** the r3 planning boundary is published
- **THEN** the registration schema version, identity, exact field set, canonical self-digest rule, cohort/role mapping, and the closed fifteen-key authority plus ten-key empirical-operation maps are fixed before build and cannot change in response to the inventory outcome

### Requirement: Verified compact r4 inventory registration remains execution-inert
Only a bounded successful r4 v4 inventory followed by distinct source-only
reconstruction and standalone structural verification SHALL become eligible
for one canonical registration. The registration SHALL bind the fixed source,
request, authorization, launch, receipt, inventory, exact ordered 512 training,
128 canary, and 512 holdout cohorts, role digests, and all-false downstream
authority and empirical-operation maps. Build completion alone SHALL grant no
verification, registration, training-request, or execution authority.

#### Scenario: Compact reconstruction matches
- **WHEN** source-only verification rescans the fixed Git bytes and the standalone verifier reproduces source counts, total row count, exclusions, cohorts, role and whole digests, receipt, output closure, schema v4, and byte ceilings
- **THEN** one all-false r4 registration may be published and parent task 6.2 may be completed while task 6.3 remains incomplete

#### Scenario: Reconstruction or registration review fails
- **WHEN** any source identity, aggregate count, exclusion, cohort, digest, authority binding, output closure, receipt identity, schema, byte ceiling, or all-false field differs or cannot be independently reconstructed
- **THEN** no registration is published, parent task 6.2 remains incomplete, and no training or downstream authority becomes eligible

#### Scenario: Terminal r3 bytes are offered as r4 evidence
- **WHEN** r4 planning, preflight, build, verification, or registration attempts to read, hash, parse, convert, or bind the unverified r3 inventory content
- **THEN** r4 fails closed before registration and the r3 artifact remains preserved and unverified

#### Scenario: Registration schema is frozen before seed access
- **WHEN** the r4 planning boundary is published
- **THEN** the registration schema version, r4 identity, exact field set, canonical self-digest rule, cohort/role mapping, and closed authority plus empirical-operation maps are fixed before build and cannot change in response to inventory outcome

### Requirement: Inventory CLI completion output is bounded
After `build-inventory` or `verify-inventory` returns a validated inventory,
the CLI SHALL write one canonical completion envelope rather than serializing
the full inventory to stdout. The envelope schema version SHALL be
`noncombat-card-acceptance-empirical-successor-inventory-cli-completion-v1` and
its exact fourteen fields SHALL be `schema_version`, `operation`, `status`,
`request_sha256`, `output_path`, `inventory_path`, `inventory_size_bytes`,
`inventory_file_sha256`, `inventory_sha256`,
`inventory_launch_observation_sha256`,
`operation_launch_observation_sha256`, `receipt_path`, `receipt_sha256`, and
`completion_sha256`. The only valid operation/status pairs SHALL be
`build-inventory`/`published` and `verify-inventory`/`verified`. All paths SHALL
be resolved absolute paths rendered with forward slashes. `completion_sha256`
SHALL be the production canonical SHA-256 over the exact other thirteen fields,
excluding `completion_sha256` itself, including the canonical trailing newline;
the complete encoded envelope SHALL be no more than 2,048 bytes.

Completion generation SHALL require a closed output containing only a regular
non-symlink `seed_inventory.json`, no staging root, a canonical regular
non-symlink receipt with exact request/authorization/launch/source bindings,
stable identity before and after receipt reading, and matching returned-artifact
identities. It SHALL read the inventory bytes
once through a fixed-size streaming SHA-256, bind the resulting
`inventory_file_sha256`, and require regular-file identity and size to remain
unchanged before, during, and immediately after that read. It SHALL NOT parse
or reconstruct inventory content, alter direct Python operation results, or
grant verification, registration, training, or downstream authority.
`inventory_launch_observation_sha256` SHALL bind the build launch recorded by
the artifact and receipt, while `operation_launch_observation_sha256` SHALL bind
the current CLI operation launch. They SHALL match for build and MAY differ for
a distinctly authorized verification.

#### Scenario: Large build result completes with bounded stdout
- **WHEN** `build-inventory` returns a validated mapping whose non-envelope content is arbitrarily large and its closed output and receipt identities match
- **THEN** the CLI exits successfully and stdout contains only the canonical completion envelope within 2,048 bytes

#### Scenario: Verification result uses the same bounded contract
- **WHEN** `verify-inventory` independently reconstructs a closed inventory successfully
- **THEN** the CLI emits a `verified` completion envelope that separately binds the inventory/build launch and current verification launch and does not serialize reconstructed rows, exclusions, or cohorts

#### Scenario: Completion identity drifts
- **WHEN** the output is not closed, staging exists, the inventory or receipt is missing, non-regular, symlinked, noncanonical, or digest-invalid, receipt identity changes during reading, inventory identity or size changes during hashing, or request/authorization/launch/source/artifact identities differ
- **THEN** completion generation fails closed without writing partial or full inventory stdout and grants no registration or downstream authority

#### Scenario: Completion exceeds its frozen bound
- **WHEN** the canonical completion envelope would exceed 2,048 bytes
- **THEN** the CLI fails before writing stdout rather than truncating, streaming, or weakening the identity

#### Scenario: Dispatch and direct APIs remain compatible
- **WHEN** callers invoke `check-dispatch`, `build_inventory`, or `verify_inventory` directly
- **THEN** dispatch canonical bytes and direct full-mapping return semantics remain unchanged while only build/verify CLI result publication uses the bounded envelope

### Requirement: Seed inventory evidence is compact and bounded
The source-only seed inventory SHALL use schema
`noncombat-card-acceptance-empirical-successor-seed-inventory-v4`. It SHALL bind
the exact ordered source registry, each source byte SHA-256, size, format,
document count, and seed-occurrence row count; the total row count; the complete
sorted unique excluded-seed set and digest; fixed cohorts and role digests;
authority evidence; and the whole-inventory digest. It SHALL NOT inline
per-occurrence provenance rows.

Build and the source-only `verify-inventory` operation SHALL independently
traverse the same registered source bytes with the existing role semantics and
compare the exact source registry, per-source and total row counts, excluded
seeds, cohorts, and digests. The separate successor verifier SHALL accept only
the exact v4 field set and SHALL independently validate aggregate count
consistency, canonical excluded seeds, fixed cohort selection, role digests, and
the whole-inventory digest without repository-read authority. Inventory
construction SHALL accumulate counts and unique seeds without retaining a
repository-wide occurrence-row list. Canonical inventory bytes SHALL be no more
than 64 MiB and SHALL be checked before staging or output publication.

#### Scenario: Repeated provenance does not expand publication
- **WHEN** one or more registered fixtures contain arbitrarily many repeated occurrences of the same seed under valid seed contexts
- **THEN** row counts include every occurrence while the inventory stores only source identities, aggregate counts, and the unique excluded seed once

#### Scenario: Independent compact reconstruction matches
- **WHEN** build and verification scan the same closed registered source bytes
- **THEN** they reconstruct identical source identities, per-source and total row counts, excluded seeds, cohorts, role digests, and whole-inventory digest without comparing inline occurrence rows

#### Scenario: Independent successor verification receives v4 evidence
- **WHEN** the standalone successor verifier receives a structurally valid compact inventory after source-only reconstruction
- **THEN** it validates the exact v4 fields, aggregate counts, canonical excluded seeds, fixed cohorts, authority bindings, and digests without requiring inline rows or repository access

#### Scenario: Aggregate evidence drifts
- **WHEN** a source byte identity, document count, row count, total row count, excluded seed, cohort, role digest, or inventory digest differs during validation or independent verification
- **THEN** verification fails closed and no registration or downstream authority is granted

#### Scenario: Canonical inventory exceeds its ceiling
- **WHEN** validated canonical inventory bytes would exceed 64 MiB
- **THEN** build fails before creating staging or output publication rather than truncating, compressing, splitting, or raising the bound

#### Scenario: Legacy inline rows are supplied
- **WHEN** a v3 inventory or a v4 mapping containing `rows` is supplied to the compact validator
- **THEN** it is rejected as the wrong schema or an unknown-field mapping and cannot be used for verification or registration

#### Scenario: Terminal r3 evidence is present
- **WHEN** the compact source repair and its tests are executed
- **THEN** the r3 output and receipt are not read, modified, deleted, verified, converted, or registered and parent task 6.2 remains incomplete

### Requirement: Inventory verification is distinctly authorized and durably one-shot
The production `verify-inventory` CLI and direct API SHALL require an exact
canonical `inventory-verification` stage request, independently reviewed stage
authorization, matching delegated or exact external-human approval record, and
fresh launch observation in addition to the immutable inventory build request
and authorization. Build approval and launch identity SHALL be reconstructed
from the canonical build receipt and the inventory's embedded authority
evidence rather than accepted as caller-selected build files. The verification
request SHALL bind the exact build request, authorization, launch, receipt,
inventory file and semantic digests, fixed
source commit and source inventory, compact-v4 schema, 64 MiB inventory
ceiling, 2,048-byte completion ceiling, read-only reconstruction authority,
and all-false downstream authority. Missing, unknown, predecessor, stale,
noncanonical, broadened, or mismatched verification evidence SHALL be rejected
before inventory, registered historical Git blob, seed, cohort, native, model,
environment, training, evaluation, gameplay, or registration access.

After all authority and source-identity validation passes, verification SHALL
atomically create its request-bound execution receipt, write canonical bytes,
flush, and fsync before opening the inventory or reconstructing registered
historical evidence. Receipt path existence SHALL consume the verification
identity regardless of whether bytes are empty, partial, invalid, or complete.
The receipt SHALL remain immutable after success or failure and SHALL block
every later invocation of the same verification request. A successful
verification SHALL emit only a canonical bounded completion that separately
binds the build identity and verification request, authorization, launch, and
receipt; it SHALL grant no registration, training, or downstream authority.

#### Scenario: Legacy verification command is attempted
- **WHEN** `verify-inventory` is invoked with only the build request, build authorization, approval, and launch arguments used before this change
- **THEN** argument validation fails before the operation function, inventory, Git blob, seed, cohort, or receipt access

#### Scenario: Direct API omits distinct verification authority
- **WHEN** a caller invokes `verify_inventory()` with only build authority or omits any verification request, authorization, approval, or fresh launch input
- **THEN** the function rejects the call before verification receipt creation, inventory reading, registered historical Git blob access, seed discovery, or cohort reconstruction

#### Scenario: Distinct verification authority is exact
- **WHEN** the verification request, reviewed authorization, approval record, fresh launch, source identity, build prerequisites, schemas, ceilings, and all-false authority maps match exactly
- **THEN** the operation may create one verification receipt and begin source-only inventory reconstruction without cohort materialization or downstream authority

#### Scenario: Declared build or verification binding is substituted
- **WHEN** any supplied build request/authorization, canonical build receipt, verification request/review/approval/authorization/launch, declared inventory digest, source identity, schema, ceiling, prerequisite, or authority field differs
- **THEN** verification fails before verification receipt creation, inventory reading, registered historical blob access, or seed discovery

#### Scenario: Materialized inventory content drifts
- **WHEN** the declared authority is exact but the opened inventory file, embedded build approval/launch evidence, compact semantics, source reconstruction, cohort, or digest differs
- **THEN** the mismatch is detected after the verification receipt and closes the request terminally without retry or registration

#### Scenario: Receipt creation is interrupted
- **WHEN** exclusive verification receipt creation succeeds but canonical write, flush, or fsync is interrupted or fails
- **THEN** the existing empty or partial receipt remains immutable, consumes the identity, and blocks every later invocation before evidence access

#### Scenario: Verification identity already started
- **WHEN** an empty, partial, invalid, or complete verification receipt path already exists
- **THEN** the operation rejects the invocation without parsing, deleting, replacing, or repairing the receipt and without inventory or historical evidence access

#### Scenario: Verification fails after receipt
- **WHEN** inventory closure, compact validation, source reconstruction, cohort verification, digest comparison, or completion construction fails after the receipt exists
- **THEN** the request is terminal without retry, resume, replacement, registration, tuning, raised bounds, or downstream authority

#### Scenario: Exact verification succeeds
- **WHEN** one authorized verification reconstructs the compact inventory and all build/source/cohort/digest bindings exactly
- **THEN** it emits one canonical verification completion within 2,048 bytes that binds both immutable receipts and every operation identity without serializing rows, exclusions, or cohorts

#### Scenario: Verification stdout publication fails
- **WHEN** reconstruction and completion construction succeed after receipt creation but writing the canonical completion to stdout fails or is interrupted
- **THEN** the existing verification receipt consumes the identity and every later invocation is rejected before inventory or historical evidence access

#### Scenario: Build CLI remains compatible
- **WHEN** callers use the existing exact `build-inventory` CLI arguments and direct build API
- **THEN** build request validation, receipt semantics, inventory publication, direct return value, and bounded build completion remain unchanged

### Requirement: Registration-only r6 consumes exact verified r5 evidence
R6 SHALL preserve the pushed r5 incident and archive boundaries as terminal and
SHALL NOT rebuild or reverify its inventory. Before mappings reach a pure
producer builder, the allowlisted driver SHALL strict-parse each of the six
raw JSON r5 evidence inputs, reject duplicate keys, and require byte equality
with canonical trailing-newline JSON. The builder SHALL require complete
agreement among the inventory, build receipt, verification receipt,
verification completion, and the exact five-field result freshly reconstructed
by the independent standard-library verifier before rendering one registration
with the frozen v1 schema and distinct r6 identity. The historical standalone
wrapper SHALL remain an exact hash-pinned review prerequisite but SHALL NOT
authorize construction. The first r6 registration-driver process invocation
SHALL use the frozen canonical request and exact CLI and SHALL consume the
identity. The exact CLI SHALL carry a separately reviewed expected request
SHA-256 and receipt path. The driver SHALL exclusively publish an immutable
started receipt before request resolution or any input open. The receipt SHALL
bind the exact command, expected request digest, receipt path, and registration
identity; the expected request digest SHALL transitively bind the preflight,
six evidence identities, output path, source commits, and downstream denial.
Any process, receipt, input, parsing, validation, access-accounting, output, or
publication failure SHALL be terminal without reopening or retry.

#### Scenario: Exact r5 evidence agrees
- **WHEN** every allowlisted r5 mapping is canonical, historical standalone/review mappings are exact, and fresh standalone reconstruction agrees with source, request, authority, receipt, inventory, cohort, role, and completion bindings
- **THEN** the builder returns one canonical all-false r6 registration without filesystem discovery or downstream authority

#### Scenario: Verification prerequisite drifts
- **WHEN** a verification receipt, completion, standalone result, inventory field, or historical authority binding differs or is missing
- **THEN** registration construction fails without publishing a registration or completing parent task 6.2

#### Scenario: JSON input bytes are noncanonical
- **WHEN** one of the six allowlisted JSON evidence inputs contains duplicate keys or bytes that differ from canonical trailing-newline JSON
- **THEN** the driver rejects it before decoded mappings reach registration construction

#### Scenario: Verification review bytes drift
- **WHEN** the allowlisted verification review differs from canonical trailing-newline JSON or its registered path, hash, size, or `canonical_json` content kind
- **THEN** the driver rejects it without publishing registration

#### Scenario: R5 is treated as registered
- **WHEN** a caller uses the r5 registration identity, writes the r5 registration path, or claims the r5 terminal failure is resolved
- **THEN** r6 fails closed and preserves r5 as verified historical evidence without registration

#### Scenario: Driver fails before input access
- **WHEN** the first r6 driver invocation fails before or during receipt publication and no input has been opened
- **THEN** r6 is still consumed, every created receipt byte is preserved, and same-identity reinvocation is forbidden

#### Scenario: Request parsing fails
- **WHEN** the registered invocation encounters malformed request bytes, a wrong root, or missing isolated mode
- **THEN** its invocation receipt already exists with the trusted request digest and exact command, and r6 remains terminal without reinvocation

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
dual-validated in memory before one exclusive create/write/flush/fsync
publication attempt. Parent task 6.3 and every training, evaluation, execution,
or promotion authority SHALL remain incomplete and absent.

#### Scenario: Registration publication succeeds
- **WHEN** the canonical r6 registration and review are exact, independently accepted, committed, and pushed
- **THEN** parent task 6.2 is completed while 6.3 remains incomplete and no downstream request is created

#### Scenario: Publication or review fails
- **WHEN** output writing, self-digest validation, independent validation, static review, pushed cleanliness, or access accounting is missing or ambiguous
- **THEN** r6 closes without replacing the registration and parent task 6.2 remains incomplete

#### Scenario: Publication fails after output creation
- **WHEN** exclusive output creation succeeds but canonical write, flush, fsync, or later publication validation fails
- **THEN** the existing complete or partial bytes are preserved, r6 is consumed, and same-identity deletion, retry, repair, or replacement is forbidden
