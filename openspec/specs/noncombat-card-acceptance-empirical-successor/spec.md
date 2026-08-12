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

### Requirement: Training authority waits for a reviewed executable runner
The empirical successor SHALL keep the pushed r6 registration and bounded
training request immutable and request-only until one exact training runner,
launch-manifest schema, closed command set, source-only preflight, independent
verifier, focused tests, registered repository gates, and text-only source
review are committed and pushed. Parent task 6.4 SHALL remain incomplete until
one exact r6 launch manifest is independently reviewed and pushed, and task 6.5
SHALL remain blocked until separate valid approval and launch observations exist.

#### Scenario: Request exists but runner is absent
- **WHEN** the r6 training request is reviewed and pushed but no reviewed executable runner/manifest boundary exists
- **THEN** request publication remains valid while authorization, native/model loading, environment construction, seed access, and training remain ineligible

#### Scenario: Runner source boundary is complete
- **WHEN** runner source, tests, launch-manifest schema, source-only preflight, independent verification, configured gates, and review are pushed without empirical access
- **THEN** only publishing the deterministic zero-progress control anchor and then rendering/reviewing one exact launch manifest become eligible; authorization and execution remain separate later boundaries

### Requirement: The successor is additive and source isolated
The capability SHALL add a new card-acceptance empirical control plane, Torch
runtime, seed-inventory utility, independent standard-library verifier, schemas,
tests, and reports without editing or importing private helpers from a consumed
empirical runner. Control-only import and commands SHALL NOT import Torch,
native adapter, gameplay, CommunicationMod, or environment modules. Every
direct and transitive behavioral dependency used at runtime SHALL be present in
the new source binding.

#### Scenario: Source-only control is imported
- **WHEN** registration, request, authorization, inventory, rollback-planning, or verification modules are imported, or request render/pre-build validation commands execute
- **THEN** no Torch/native module is imported, no environment is constructed, no seed is discovered or accessed, and no model is fitted or loaded

#### Scenario: A consumed empirical identity is proposed as fresh evidence
- **WHEN** a prior cohort, reserved seed, inventory, source registration, authorization, checkpoint, output root, runtime schema, verifier result, canary, holdout, or outcome is supplied as a new candidate or control identity
- **THEN** the capability rejects it before native loading or seed access

### Requirement: Consumed evidence is preserved byte for byte
Before implementation edits, the capability SHALL bind the reviewed
pre-implementation Git tree and publish a canonical preservation manifest in an
independently reviewed, committed, and pushed boundary. Its closed source-path
array SHALL contain exactly the consumed cross-fitted control plane, Torch
runtime, independent verifier, seed-inventory utility, and main successor spec
paths named in the design. Its closed artifact-file array SHALL contain exactly
the 20260808-r2 registration/review, request/review, standing delegation,
delegated approval/review, authorization/review, execution preflight,
JSON/Markdown postmortem, and r5 readiness closeout paths named in the design.
Its closed artifact-root array SHALL contain exactly the r2 execution root, r5
readiness publication root, and the source-keyed r5 readiness-attempt root bound
by the consumed registration. The manifest SHALL bind both closed arrays, exact
file SHA-256 identities, canonical directory-inventory digests, the baseline Git
tree, and its own digest. Source qualification SHALL reobserve the same arrays
and reject a changed, missing, extra, reordered, omitted, or newly importing
consumed identity. Preservation SHALL NOT make consumed bytes eligible as fresh
evidence.

#### Scenario: Source implementation preserves consumed identities
- **WHEN** source-only qualification reobserves every registered consumed path and the independently pushed baseline tree/manifest
- **THEN** file bytes, ordered directory inventories, counts, sizes, and digests exactly match the pre-edit manifest and consumed modules do not import the successor

#### Scenario: The preservation baseline is incomplete or late
- **WHEN** implementation edits predate the pushed manifest boundary or a consumed path/root is absent from either closed array
- **THEN** source qualification fails rather than absorbing the drift into a new baseline

#### Scenario: One consumed byte is mutated
- **WHEN** a synthetic preservation fixture changes, removes, adds, or reorders one consumed entry
- **THEN** preservation validation fails before registration eligibility

### Requirement: Composite initialization is deterministic and storage disjoint
With model seed `0`, the runtime SHALL construct exactly one CPU float32
`StateConditionedCandidateRanker(HASH_DIM, DEFAULT_HIDDEN_DIM)` base state and
copy every state-dict key and tensor byte into exactly five independent
rankers: `candidate.card_policy.family_head`,
`candidate.card_policy.conditional_ranker`,
`candidate.frozen_noncard_ranker`, `control.shared_card_ranker`, and
`control.frozen_noncard_ranker`. The control shared ranker SHALL produce both
family logits over the same canonical mean family features and conditional
logits over candidates. The destination key sets, shapes, dtypes, values, and
per-tensor SHA-256 identities SHALL equal the base mapping, while parameter
objects and storage SHALL be pairwise disjoint. The paired bootstrap SHALL bind
all five rankers and each arm's separate card/non-card generators under new
schemas and checkpoint identities.

#### Scenario: Bootstrap is reproduced
- **WHEN** two fresh runtimes use the registered model and generator seeds
- **THEN** their canonical paired checkpoint bytes and digest are exact and all five rankers match the base values without shared objects or storage

#### Scenario: One destination mapping drifts
- **WHEN** a key is absent, extra, renamed, reordered, reshaped, recast, changed in value, or shares parameter/storage identity with another head
- **THEN** bootstrap and checkpoint validation fail before an optimizer or environment is constructed

### Requirement: Both arms train only their card-reward parameters
The candidate optimizer SHALL contain all and only `family_head.*` and
`conditional_ranker.*` parameters in canonical name order. The control
optimizer SHALL contain all and only `shared_card_ranker.*` once, even though
both family and conditional terms differentiate through it. Both
`frozen_noncard_ranker` copies SHALL have `requires_grad=false`, SHALL be absent
from both optimizers, and SHALL remain byte-identical to bootstrap and each
other in every checkpoint, canary, holdout, and terminal artifact. Each arm
SHALL sample family then candidate with its own identically seeded checkpointed
card generator. Every other noncombat decision SHALL use that arm's frozen
ranker and separate identically seeded non-card generator.

#### Scenario: A card reward is sampled during training
- **WHEN** either arm reaches a valid card reward with one or more explicit families
- **THEN** that arm samples the sorted family distribution first, samples a candidate within that family second, and applies only the aligned legal action ID

#### Scenario: A non-card decision is reached
- **WHEN** either arm reaches route, shop, event, or another non-card-reward decision
- **THEN** only that arm's frozen non-card ranker and non-card generator select among legal candidates and no trainable card parameter or card generator is advanced

#### Scenario: Frozen behavior changes
- **WHEN** any frozen parameter byte, optimizer membership, generator ownership, candidate projection, or non-card selection rule differs
- **THEN** the current chunk or frozen evaluation fails closed and no subsequent seed is accessed

### Requirement: Frozen evaluation is deterministic and tie free
Candidate and control evaluation SHALL select a card reward by the unique
maximum family logit followed by the unique maximum conditional logit within
that family. Non-card evaluation SHALL select the unique maximum frozen-ranker
candidate score. Candidate order, family probability, joint probability, and
lexical order SHALL NOT break a maximum tie.

#### Scenario: Both greedy stages are unique
- **WHEN** one family and one candidate within it are unique maxima
- **THEN** the runtime applies exactly that legal action and retains both maximum sets and margins

#### Scenario: A maximum is tied
- **WHEN** either the family stage or selected-family conditional stage has more than one maximum identity
- **THEN** the evaluation fails before applying an action rather than selecting a tie member

### Requirement: Advantages are cross-fitted and unscaled
Every paired update SHALL contain exactly 64 complete trajectories per arm from
the same ordered training-seed slice. Each arm SHALL separately reuse the
registered four-fold, trajectory-disjoint baseline contract with 16 held-out
and 48 fit trajectories per fold, 128 pre-decision state features, ridge
coefficient `0.001`, CPU float64 canonical arithmetic, prediction clipping to
`[0, 3]`, and formal undiscounted return. Each policy weight SHALL equal exactly
`return_to_go - clipped_held_out_prediction` with no later centering,
normalization, standardization, learned scale, category transform, or clipping.

#### Scenario: A card-reward advantage is constructed
- **WHEN** its complete trajectory, fold, fit-set, feature, return, prediction, clipping, and decision provenance pass the cross-fitted contract
- **THEN** the selected family and conditional terms receive the same exact held-out residual advantage

#### Scenario: Post-decision data reaches the baseline
- **WHEN** selected action/family, score, reward, successor state, terminal outcome, seed, or another post-decision value appears in baseline features
- **THEN** the complete chunk is rejected before loss construction

### Requirement: The objective has four fixed head-owned components
For exactly `M` valid card-reward decisions in one arm's chunk, where `M > 0`,
that arm's full loss SHALL be the ordered sum of:

```
card_reward_family_policy =
    -sum(selected_family_log_probability * advantage) / M
card_reward_conditional_policy =
    -sum(selected_conditional_log_probability * advantage) / M
family_entropy_regularizer = -0.01 * mean(family_entropy)
conditional_entropy_regularizer =
    -0.01 * mean(mean(per_family_conditional_entropies))
```

Both arms SHALL use the same four component formulas and coefficients. The two
policy coefficients SHALL be one. The inner conditional entropy mean
SHALL weight every explicit family equally within one decision. Expected
conditional entropy and joint entropy SHALL remain diagnostic and SHALL NOT
enter the loss. No caller override is permitted.

#### Scenario: A valid chunk builds its loss
- **WHEN** every card-reward term and advantage is finite and identity aligned
- **THEN** all four connected scalar components appear in canonical order, reconstruct the separately supplied full loss, and preserve selected-family versus selected-conditional gradient ownership

#### Scenario: A chunk has no card reward
- **WHEN** 64 complete trajectories contain zero valid card-reward decisions
- **THEN** the identity terminates as an algorithm failure before an optimizer step rather than substituting a zero-loss update

#### Scenario: A cross-head entropy is added
- **WHEN** expected conditional entropy, joint entropy, family-probability weighting of conditional entropy, or another unregistered component reaches the loss
- **THEN** objective validation fails before gradient construction

### Requirement: Matched fixed Adam updates are independently replayable
The runtime SHALL use exactly one CPU `torch.optim.Adam` per arm: candidate over
both disjoint card heads and control over its shared card ranker. Each optimizer
SHALL have one parameter group with learning rate `0.001`, betas
`(0.9, 0.999)`, epsilon `1e-8`, zero weight decay, no AMSGrad, and no alternate
maximize, foreach, capturable, differentiable, or fused mode. Separately per
arm, the runtime SHALL independently differentiate the four components and
separately supplied full loss, prove ordered float64 gradient reconstruction
and registered ownership, compute one arm-local global norm clip factor at
ceiling `1.0`, install the canonical CPU float32 gradient, and retain complete
pre/post parameter and Adam state for standard-library replay.

#### Scenario: A valid update is applied
- **WHEN** both arms' scalar, gradient, ownership, finiteness, reconstruction, clipping, parameter-order, and optimizer checks pass
- **THEN** exactly one Adam step per arm consumes its installed gradient and the independent verifier reproduces both parameter and moment transitions within fixed reviewed tolerances

#### Scenario: A training control drifts
- **WHEN** model seed, architecture, parameter set/order, coefficient, optimizer option, gradient ceiling, reward, discount, or advantage arithmetic differs from registration
- **THEN** execution fails before the affected optimizer step and cannot tune or retry the identity

### Requirement: Fresh cohorts are selected once from an explicit inventory
After clean reviewed source publication, a separate exact tracked inventory
authorization SHALL permit only registered repository evidence reads, seed
discovery, and cohort materialization; native loading, environment seed access,
model loading, fitting, training, and evaluation SHALL remain false. Under that
authority, a standard-library `build-inventory` operation SHALL bind
one fixed Git tree, scan an explicit ordered historical source set, and exclude
every used, selected, reserved, diagnostic, failed-access, training, evaluation,
canary, and holdout seed. Candidate output, staging, sealed, scratch, attempt,
and temporary roots SHALL be excluded before traversal and SHALL NOT be
recursively ingested. One fixed ascending algorithm SHALL select exactly 512
unique training seeds, 128 canary seeds, and 512 holdout seeds with pairwise
disjoint roles and zero historical collisions.

Import, request rendering, and pre-build request/authorization validation SHALL
NOT scan historical inputs, discover seed values, or materialize a cohort.
Rendering or validating the inventory request/authorization SHALL NOT itself
grant the `build-inventory` operation. After a successful build, a distinct
`verify-inventory` operation under the same exact inventory authorization MAY
read the materialized inventory and registered historical source identities to
reconstruct provenance, exclusions, and selected values. It SHALL NOT select,
replace, or materialize a cohort or import native, model, environment, fitting,
training, or evaluation runtime.

#### Scenario: A fresh inventory is registered
- **WHEN** the exact inventory authorization validates, `build-inventory` publishes once, and the post-build independent `verify-inventory` operation scans the registered source identities
- **THEN** they reconstruct identical ordered provenance, exclusions, selected values, role digests, and whole-inventory SHA-256

#### Scenario: Pre-build validation attempts post-build verification
- **WHEN** an import, render, or pre-build validation command attempts to scan historical sources or read selected seed values
- **THEN** it fails before seed discovery because only separately authorized `build-inventory` and post-build `verify-inventory` have that source-only authority

#### Scenario: Inventory build lacks exact authority
- **WHEN** `build-inventory` is requested with only source publication, proposal approval, render/validate output, or an authority map that enables native/environment/model operations
- **THEN** seed discovery and cohort materialization are rejected

#### Scenario: An output root enters the inventory
- **WHEN** a candidate, staging, sealed, scratch, attempt, temporary, or recursively generated artifact path would be traversed
- **THEN** inventory construction fails before selection rather than admitting self-generated rows

### Requirement: Training is bounded and detects exact family collapse
Training SHALL execute at most 512 registered pairs in the same arm order, with
64 seeds per paired chunk, at most 1,024 training episode accesses, at most
eight updates per arm, and at most 16 total training optimizer steps. If no registered
early-collapse gate fires, it SHALL execute exactly all 512 pairs and eight
updates per arm. There SHALL be no epoch replay, checkpoint selection, or
extension. After each complete paired checkpoint, the runtime
SHALL inspect the candidate's trailing four complete chunks. If they contain at
least 64 valid multi-family card rewards and every unique greedy family has the
same identity, it SHALL publish
`experiment_stopped_during_training_for_family_saturation` before another seed,
canary, or holdout access. Control saturation and every other diagnostic SHALL
be retained but SHALL NOT stop, extend, or tune training.

#### Scenario: Training completes without exact collapse
- **WHEN** all eight registered paired chunks finish and no candidate four-chunk saturation predicate is true
- **THEN** terminal candidate and trained-control checkpoints become eligible for a separate candidate/control seal

#### Scenario: Fewer than four chunks are complete
- **WHEN** the candidate has fewer than four complete paired chunks
- **THEN** the saturation predicate is ineligible and cannot stop training

#### Scenario: Exact collapse is observed
- **WHEN** the first eligible trailing four-chunk window meets every denominator and singleton-family condition
- **THEN** training closes at its latest complete checkpoint with zero canary and holdout access and no replacement initialization or coefficient

### Requirement: Candidate and control are sealed before canary access
Only an independently verified exact
`training_completed_without_family_saturation` verdict proving 512 pairs, eight
complete chunks, eight updates per arm, and no collapse or failure may produce a
tracked source-only seal before canary access. The seal SHALL bind the source
commit; candidate and control source, checkpoint, and configuration SHA-256
identities; seed-inventory SHA-256; exact family/conditional/base mapping;
candidate-disabled default; exact experiment-local control target; production
CommunicationMod configuration; production checkpoint inventory; output root;
and rollback authority. Candidate and control SHALL remain frozen after sealing.
A collapse or failure checkpoint SHALL remain immutable evidence but SHALL NOT
be seal- or canary-eligible.

#### Scenario: A complete seal is published
- **WHEN** the exact no-collapse completion verdict, all 512 pairs, all eight complete chunks, all eight updates per arm, and both frozen trained-arm checkpoints independently verify
- **THEN** producer and verifier reconstruct every required binding and candidate remains disabled pending a separate exact canary authorization

#### Scenario: Collapse or failure evidence is offered for sealing
- **WHEN** training stopped for family saturation, ended in failure, completed fewer than 512 pairs or eight chunks, or lacks eight updates per arm
- **THEN** seal publication and canary eligibility are rejected while the checkpoint remains evidence only

#### Scenario: A sealed identity changes
- **WHEN** source, checkpoint, config, target, seed inventory, production inventory, or output binding differs after sealing
- **THEN** canary access is rejected and rollback keeps the candidate disabled

### Requirement: The at-most-once canary is structural
One separately authorized canary SHALL use exactly 128 registered paired seeds.
For every seed, candidate and control SHALL each execute twice from the exact
same seed and frozen arm; the second execution SHALL reproduce the first arm's
decision and terminal payload exactly. Before either replay environment is
constructed, each first-run candidate and control decision/terminal payload
SHALL be published to a write-once, seed-ordered, hash-chained output commitment
bound to the sealed arm source, checkpoint, and config hashes. Replay and
control reproduction SHALL be judged only against those registered commitment
bytes. A first output SHALL NOT be replaced, repaired, or rehashed after replay.
The canary SHALL therefore consume at most 512 environment episode accesses and
SHALL perform no update to either sealed arm.

Candidate-arm valid multi-family card rewards SHALL provide a selected-family
denominator of at least 64 and a unique-greedy-family denominator of at least
64. Every counted family set SHALL contain at least two identities. The maximum
selected-family rate and maximum unique-greedy-family rate SHALL each be no
greater than `0.95`. All actions SHALL be legal and every identity,
probability, score, tie set, and terminal SHALL verify.

The canary SHALL choose the first eligible candidate-arm decision in exact
`(seed, decision_index, decision_id)` order. Eligibility SHALL require a valid
multi-family card reward, finite terms, and one selected legal action. It SHALL
clone the sealed candidate model and exact candidate Adam state, zero gradients
with `set_to_none=true`, and build exactly
`-selected_family_log_probability - 0.01 * family_entropy`, using synthetic
unit advantage one and no conditional or cross-head term. It SHALL
differentiate canonical candidate parameters, apply the registered global norm
clip `1.0`, and replay exactly one candidate Adam step.

The shadow gate SHALL require a finite nonzero family gradient, at least one
changed family parameter, exact unchanged conditional parameter and Adam-state
bytes, exact unchanged conditional logits, probabilities, and selected term at
the same decision, and independent replay of the changed family state. The
shadow clone SHALL never replace or mutate a sealed arm or environment.

#### Scenario: Every canary gate passes
- **WHEN** both-arm exact replay, legality, control reproduction, both concentration gates, denominator/cardinality gates, and family-only shadow invariance all pass
- **THEN** and only then may a separate exact holdout request be published while both arms remain frozen

#### Scenario: One canary gate fails
- **WHEN** any registered identity, replay, legality, denominator, concentration, shadow, resource, publication, or authority gate fails
- **THEN** the canary identity terminates, candidate remains disabled, and all 512 holdout seeds remain unaccessed

### Requirement: The untouched holdout has preregistered outcome classes
After a passing canary and separate exact authorization, one at-most-once
holdout SHALL execute the frozen candidate and control once on each of exactly
512 untouched paired seeds, for at most 1,024 episode accesses. It SHALL reapply
legality, identity, finite-output, and candidate concentration gates. It SHALL
use the existing formal-reward `floor_progress` channel as its floor endpoint.
In ascending registered seed order, each paired difference SHALL be candidate
`floor_progress` minus control `floor_progress`. A fresh standard-library
`random.Random(0)` SHALL generate exactly 10,000 resamples in outer-resample,
inner-draw order; each resample SHALL make exactly 512 consecutive
`randrange(512)` calls with replacement and store their arithmetic mean. After
sorting the 10,000 means ascending, quantiles `p=0.025` and `p=0.975` SHALL use
linear interpolation at `(10000 - 1) * p` between the values at
`floor(position)` and `ceil(position)`. The paired-floor signal SHALL mean only
that the resulting lower endpoint is strictly greater than zero.

Only after all 512 pairs and every structural, concentration, resource,
bootstrap, and publication check pass SHALL the normal terminal outcome be
exactly one of:

- `victory_and_floor_signal` when candidate victories are strictly greater than
  control victories and the paired-floor lower bound is greater than zero;
- `floor_only_signal` when candidate and control victories are equal and the
  paired-floor lower bound is greater than zero;
- `inconclusive_signal` when candidate victories are strictly greater and the
  paired-floor lower bound is not greater than zero, or candidate victories are
  strictly fewer and the paired-floor lower bound is greater than zero; or
- `no_learning_signal` for the remaining two cells: equal victories without a
  floor signal, or fewer candidate victories without a floor signal.

The predicates SHALL be pairwise disjoint and exhaustive over the exact
three-way victory comparison and binary paired-floor signal. The verifier SHALL
reconstruct the complete six-cell truth table before accepting one class.

Only `victory_and_floor_signal` SHALL satisfy this experiment's preregistered
policy-quality evidence threshold. No class SHALL grant production loading,
gameplay, qualification, or promotion authority.

#### Scenario: Holdout is complete
- **WHEN** all 512 pairs and all structural, concentration, resource, bootstrap, and publication checks pass
- **THEN** the independent verifier reconstructs exactly one outcome class from raw registered pair evidence

#### Scenario: Holdout does not complete validly
- **WHEN** a structural, concentration, resource, bootstrap, access, or publication failure occurs before normal closeout
- **THEN** the run publishes its separately classified failure verdict and SHALL NOT publish any of the four evidence outcome classes

#### Scenario: Holdout is requested before canary passage
- **WHEN** canary is absent, incomplete, failed, changed, retried, resumed, or not independently verified
- **THEN** holdout environment construction and seed access are rejected

### Requirement: Empirical stages require separate exact tracked authority
Source implementation, inventory request/authorization, fresh registration,
training request/authorization,
post-training seal, canary request/authorization, and holdout
request/authorization SHALL be separate tracked and pushed boundaries. An exact
request MAY use a canonical delegated-approval resolution only when a recorded
solo-maintainer grant under the existing standing-delegation schema explicitly
covers this repository, request class, fixed exclusions, and revocation rule,
and has not been revoked. The grant SHALL predate and remain
outside the successor request and SHALL bind verbatim external-human grant
text, timestamp, message/task IDs, source kind, scope, exclusions, revocation
rule, and self-digest. This change, its producer, and its request SHALL NOT
create or modify the grant. The resolution SHALL bind the exact independently
reviewed request digest and thereby bind that request's resource bounds,
execution authority, and false downstream authorities. It SHALL NOT be
represented as verbatim external-human text.

Before authorization publication, one source-only validation operation SHALL
consume the exact request, original independent-review bytes, approval record,
and authorization record. It SHALL validate both approval modes, recompute the
review byte digest, and prove every request-review-approval-authorization link;
standalone validation of digest-shaped authorization fields is insufficient.

Approval publication and every inventory, training, canary, and holdout launch
SHALL require a fresh authoritative current-conversation revocation observation
binding checked-at time and the latest observed human-message watermark. If the
controller cannot inspect that conversation state, or a later explicit
revocation is observed, delegated approval and launch SHALL fail closed. The
independent verifier SHALL validate canonical provenance and observation
bindings while treating human identity and conversation truth as a declared
procedural trust boundary.

As an alternative to delegated approval, exact external-human approval SHALL be
valid only after the one exact request and its independent review are tracked and
pushed. Its canonical record SHALL bind the request digest, verbatim approval
text, timestamp, message/task IDs, source kind `external-human`, repository and
request class, requested scope, ceilings, exclusions, every false downstream
authority, and a self-digest. The message SHALL postdate and unambiguously
approve that request. The producer and verifier SHALL NOT generate, amend, or
reinterpret it. Approval publication and launch SHALL apply the same fresh
current-conversation watermark and later-revocation rules used by delegated
approval; human identity and conversation truth remain the same procedural trust
boundary.

#### Scenario: Standing delegation resolves an exact request
- **WHEN** canonical grant, scope, revocation state, registration, request, independent review, and digest bindings all validate
- **THEN** a tracked authorization may be published without requiring the maintainer to transcribe the generated tuple

#### Scenario: Authorization publication omits approval evidence
- **WHEN** an authorization has a valid self-digest but its review bytes or approval record are absent, changed, or do not bind the same request
- **THEN** publication validation rejects it before the authorization becomes a tracked execution boundary

#### Scenario: Delegation is revoked after authorization publication
- **WHEN** the fresh launch-time observation contains a later explicit human revocation than the bound grant or approval
- **THEN** the static authorization cannot start or resume inventory, training, canary, or holdout work

#### Scenario: Current revocation state is unavailable
- **WHEN** delegated or exact external-human authority is proposed but authoritative current-conversation state or its latest human-message watermark cannot be inspected
- **THEN** approval publication and launch are rejected pending restored authoritative observation and a valid exact approval path

#### Scenario: Exact external approval binds one request
- **WHEN** a post-request external-human message and its canonical record bind the exact pushed request/review, scope, ceilings, exclusions, false authorities, provenance, self-digest, and fresh non-revocation observation
- **THEN** a tracked authorization may be published for only that request

#### Scenario: External approval is broad, inferred, or stale
- **WHEN** human text predates the request, omits its exact binding, is generated or reinterpreted by the producer, exceeds scope, or has a later revocation
- **THEN** authorization publication and stage launch fail closed

#### Scenario: Authority is inferred from proposal approval
- **WHEN** only proposal approval, broad unbound permission, agent review, or an unpushed request exists
- **THEN** native loading, environment construction, seed access, fitting, training, canary, and holdout remain blocked

### Requirement: Execution lifecycle is fail closed and resource monotonic
Before runtime import, the producer SHALL validate pushed source, tracked-clean
state, exact registration and authorization, Windows interpreter, native bytes
and provenance, production isolation, absent or exactly reopenable output,
exclusive lease, stage authority, and a fresh launch-time revocation observation
when delegated or exact external-human authority is used. It SHALL capture one immutable private
execution context and reuse it without per-seed registration rescans or deep
copies. Every seed access SHALL be write-ahead journaled and every terminal path
SHALL charge final elapsed time and reconcile the exact access prefix.

Setup may repeat only before the first seed under the same identity. Before
canary, at most one manual training continuation SHALL be allowed from a
complete 64-seed paired checkpoint when no later arm debit exists. A partial
uncheckpointed chunk SHALL be terminal. After canary start, no continuation,
resume, retry, replacement, update, tuning, source change, threshold change, or
seed substitution SHALL be permitted. Lease ownership SHALL bind the true
runtime child process; active output may be read or reclaimed only after that
process is proven dead.

#### Scenario: Complete-boundary training continuation is valid
- **WHEN** the sole continuation restores both exact arm models, both optimizers, every arm generator, checkpoint coordinate, registration, authorization, fresh revocation observation, and resource prefix with no later debit
- **THEN** it continues at the next registered primary seed without replaying a completed or partial chunk

#### Scenario: A wrapper exits while its child is alive
- **WHEN** the shell or launcher process exits but the lease-bound runtime child remains alive
- **THEN** monitoring treats execution as active and does not read, reclaim, repair, resume, or replace its output

#### Scenario: Dead-owner terminalization uses a fresh command observation
- **WHEN** a pushed terminalization authority has a fresh non-revoked launch observation and binds a dead owner's original pushed run envelope
- **THEN** the fresh observation authorizes only the closure command, the original run observation reconstructs the lease-bound lifecycle identity, both chains require the same request, approval, and authorization, and registration remains opaque

#### Scenario: Terminalization cannot reconstruct the original run identity
- **WHEN** the bound original run envelope, launch observation, request, approval, authorization, lease, or failure prefix differs
- **THEN** terminalization fails before closure publication, performs no empirical access, and grants no training retry

#### Scenario: A terminal path omits elapsed charge
- **WHEN** failure occurs before the first checkpoint or in any later stage
- **THEN** terminal publication is invalid unless final charged time and exact access prefix are durably reconciled

### Requirement: Resource and publication bounds are fixed
The complete logical execution SHALL be CPU-only at ascension `0` and SHALL use
at most 1,024 paired training episode accesses, eight training optimizer updates
per arm, 16 total training optimizer steps, one separately charged isolated
canary shadow optimizer step that cannot mutate either sealed arm, 512 canary
accesses, 1,024 holdout accesses, 2,560 total environment episode accesses, 500
decisions per episode, and 28,800 charged seconds. Any one managed artifact
SHALL be no
larger than 64 MiB, all stored managed artifacts no larger than 256 MiB, and all
canonical uncompressed payload no larger than 512 MiB.

Managed evidence SHALL use deterministic canonical JSON plus bounded
little-endian binary/gzip payloads with `mtime=0`. Checkpoints and stage markers
SHALL be write once or byte identical. Terminal intent SHALL bind the complete
artifact prefix; terminal and manifest SHALL publish only after intent, with
manifest last. No unbounded decision rows or tensors may appear inline in
canonical report JSON.

#### Scenario: A resource bound would be crossed
- **WHEN** the next access, update, decision, elapsed charge, stored artifact, or canonical payload would exceed registration
- **THEN** execution stops before that operation and preserves one terminal resource failure without raising a bound or retrying

#### Scenario: Existing publication bytes drift
- **WHEN** a write-once path exists with different bytes, a staging sibling is ambiguous, or terminal order is incomplete
- **THEN** publication fails closed without overwriting, deleting, repairing, or replacing evidence

### Requirement: Rollback restores control targeting and verifies production
The registered rollback authority SHALL name the exact experiment-local target,
control checkpoint/config, production CommunicationMod configuration, production
checkpoint inventory, candidate-disabled value, and trigger classes
`authority`, `canary`, `holdout`, `identity`, `legality`, `preflight`, and
`publication`. On any trigger, rollback SHALL preserve immutable empirical
evidence, restore the experiment target binding to the exact control, keep
candidate enablement false, verify the production identities, and grant no
promotion authority. It SHALL NOT tune, replace, retry, resume after canary, or
rewrite a consumed result.

Every rollback-required failure terminal SHALL map to exactly one fixed trigger
class under this precedence and closed mapping:

- `authority`: grant, revocation, approval, authorization, or stage authority;
- `identity`: source, checkpoint, config, cohort, target, production, child,
  process, or lease identity;
- `legality`: candidate/action legality, schema, finiteness, objective support,
  or a zero-card-reward chunk;
- `preflight`: interpreter, native, isolation, output, dependency, or setup
  failure before the first debit;
- `canary`: registered training-family saturation or a canary gate/failure;
- `holdout`: a holdout gate, access, evaluation, or classification failure;
- `publication`: resource/time/access accounting, partial chunk, journal,
  evidence, byte bound, staging, checkpoint, terminal, or manifest failure not
  already classified above.

The mapping SHALL NOT extend or rename the fixed trigger tuple. An unmapped or
multiply classified rollback-required failure terminal SHALL invalidate
rollback and failure publication. The four complete holdout evidence classes
SHALL be normal closeout outcomes rather than rollback failure triggers. Normal
closeout SHALL still restore the exact experiment-local control target, keep the
candidate disabled, verify production isolation, and grant no downstream
authority.

#### Scenario: A registered gate fails
- **WHEN** any rollback trigger is observed and exact rollback authority validates
- **THEN** the control target is restored and verified, candidate is disabled, production identities are verified, and the failure remains immutable

#### Scenario: Every rollback-required failure path is classified
- **WHEN** training collapse, zero-card algorithm failure, resource/time failure, partial chunk, child/lease failure, canary failure, holdout failure, or publication failure reaches failure terminalization
- **THEN** the exact precedence assigns one and only one fixed rollback trigger before terminal publication

#### Scenario: A complete holdout closes normally
- **WHEN** the independent verifier reconstructs one of the four complete holdout evidence classes
- **THEN** normal closeout restores and verifies the control target and production isolation without manufacturing a rollback failure trigger

#### Scenario: Production inventory drift is external
- **WHEN** production configuration or checkpoint bytes differ even though the experiment never had authority to change them
- **THEN** rollback records terminal isolation failure and cannot silently manufacture or substitute production checkpoint bytes

### Requirement: Independent verification keeps downstream authority false
The independent verifier SHALL use only the Python standard library and SHALL
reconstruct source/config/checkpoint identities, seed roles and access prefixes,
initialization mapping, cross-fitted folds and advantages, four-component loss,
gradient ownership and Adam transitions, frozen non-card bytes, exact replay,
canary denominators/rates/shadow invariance, holdout bootstrap/classification,
resource accounting, rollback observation, isolation, terminal intent, and
manifest closure. Every registration and terminal SHALL keep formal RL, causal,
OPE, production model loading, gameplay, CommunicationMod, qualification, and
promotion authority false.

#### Scenario: Source-only implementation is complete
- **WHEN** focused synthetic, preservation, control, lifecycle, verifier, import-isolation, configured repository gates, strict OpenSpec validation, deterministic publication, and independent review pass
- **THEN** only the source implementation becomes eligible for a separate fresh all-false registration and no gameplay validation is required because production behavior is unchanged

#### Scenario: A terminal summary lacks raw support
- **WHEN** a checkpoint, denominator, rate, paired outcome, bootstrap bound, verdict, rollback, isolation, or authority claim cannot be reconstructed from bound raw evidence
- **THEN** independent verification rejects the bundle without inferring success from producer hashes or summaries
