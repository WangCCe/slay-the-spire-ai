## MODIFIED Requirements

### Requirement: Inventory build start is durably one-shot
After all pre-start authority and source validations pass, `build-inventory`
SHALL atomically persist a canonical request-bound started receipt before
historical path discovery, blob reads, or seed discovery. An existing or partial
receipt SHALL block every later invocation of the same request regardless of
output or staging state. The receipt SHALL remain immutable after success or
failure. Process creation or failure before receipt creation SHALL NOT by
itself classify the request as started or terminal. A pre-start invocation MAY
be repeated only after independent review proves that the exact source,
command, request, path, approval, authorization, launch observation, and bytes
are unchanged and that no receipt or empirical side effect exists; otherwise a
distinct successor identity is required.

#### Scenario: First invocation fails before publication
- **WHEN** an authorized inventory invocation writes its started receipt and then fails during historical source processing before output or staging publication
- **THEN** a second invocation with the same request is rejected before source discovery and cannot resume, retry, replace, or repair the consumed identity

#### Scenario: A partial receipt already exists
- **WHEN** the request-bound started path contains an empty file, truncated JSON, or invalid canonical receipt from an interrupted first invocation
- **THEN** every later invocation is rejected before source discovery and the existing bytes are preserved without parsing, repair, replacement, or deletion

#### Scenario: Validation fails before start
- **WHEN** authority, source inventory, pushed ancestry, tracked cleanliness, output absence, request identity, or process-entrypoint validation fails before receipt creation
- **THEN** no started receipt, historical path discovery, blob read, seed discovery, cohort materialization, or output publication occurs and the identity is not consumed solely by process creation

#### Scenario: Exact pre-start invocation is reconsidered
- **WHEN** an independently reviewed pre-start failure created no receipt or empirical side effect and an external-only repair leaves every bound input byte unchanged
- **THEN** the exact invocation may be repeated without treating it as a retry of started inventory work

#### Scenario: A pre-start repair changes a binding
- **WHEN** correcting a pre-start failure would change code, source commit, command, request, path, approval, authorization, launch observation, or another bound byte
- **THEN** the current identity remains blocked and only a distinct preregistered successor may use the changed binding

#### Scenario: Inventory publication succeeds
- **WHEN** the started request builds and publishes its inventory successfully
- **THEN** the immutable receipt remains as separate execution evidence and does not grant verification, registration, training, or downstream authority

### Requirement: Terminal inventory predecessor requires a distinct preregistered identity
After an authorized inventory identity terminates in failure, the successor
control plane SHALL preserve that identity and SHALL require a separately
reviewed source commit, request id, output root, request, approval,
authorization, and launch observation before another inventory identity can
start. A predecessor request, approval, authorization, or launch artifact SHALL
NOT authorize the successor identity. r1 and r2 SHALL remain terminal while r3
uses the pushed isolated-dispatch repair and a distinct authority chain.

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
- **THEN** the system preserves a reviewed failure, creates no registration, and does not retry, resume, tune, or replace the identity

#### Scenario: The r3 invocation succeeds
- **WHEN** r3 publishes exactly one inventory and a distinct read-only verification reconstructs the same source registry, exclusions, rows, and cohorts
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

## ADDED Requirements

### Requirement: Verified r3 inventory registration remains execution-inert
Only a successful r3 inventory followed by distinct read-only reconstruction
SHALL become eligible for one canonical registration. The registration SHALL
bind the fixed source/request/authorization/launch/receipt/inventory identities,
the exact ordered 512 training, 128 canary, and 512 holdout cohorts, their role
digests, and an all-false downstream authority and empirical-operation map. It
SHALL use the preregistered schema and field set, derive its self-digest from
canonical JSON, and grant no training-request or execution authority.

#### Scenario: Independent reconstruction matches
- **WHEN** the read-only verifier reproduces every source row, exclusion, cohort, role digest, whole-inventory digest, and authority binding from the closed r3 output
- **THEN** one all-false registration may be published and parent task 6.2 may be completed while task 6.3 remains incomplete

#### Scenario: Reconstruction or registration review fails
- **WHEN** any source row, exclusion, cohort, digest, authority binding, output closure, receipt identity, or all-false field differs or cannot be independently reconstructed
- **THEN** no registration is published, parent task 6.2 remains incomplete, and no training or downstream authority becomes eligible

#### Scenario: Registration schema is frozen before seed access
- **WHEN** the r3 planning boundary is published
- **THEN** the registration schema version, identity, exact field set, canonical self-digest rule, cohort/role mapping, and all-false authority key sets are fixed before build and cannot change in response to the inventory outcome
