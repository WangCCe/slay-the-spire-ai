## ADDED Requirements

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
