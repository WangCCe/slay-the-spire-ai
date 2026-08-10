## MODIFIED Requirements

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

## ADDED Requirements

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
