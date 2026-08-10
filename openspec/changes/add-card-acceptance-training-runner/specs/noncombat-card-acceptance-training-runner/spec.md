## ADDED Requirements

### Requirement: Training launch is bound to one exact runner command set
The system SHALL publish and independently review one canonical launch manifest
that binds the pushed r6 registration, training request and review, runner
source path/hash/commit, registered experiment source commit/inventory, additive
registration verifier path/hash, Windows interpreter, output root, resource
ceilings, denied operations, and the closed `preflight`, `run-training`, and
`terminalize-dead-owner` CLI shapes. The manifest SHALL grant no authority and
SHALL be pushed before training authorization becomes eligible.

#### Scenario: Exact launch manifest is reviewed
- **WHEN** every registered path, digest, source, interpreter, command, resource, exclusion, and all-false downstream binding agrees
- **THEN** the manifest becomes eligible for source-only preflight without authorizing or starting training

#### Scenario: Runner or command drifts
- **WHEN** runner bytes, source commit, interpreter, registered command name or CLI argument, request, registration, review, output root, resource, or denied operation differs
- **THEN** preflight rejects the launch before runtime/native/model import, output creation, or seed access

### Requirement: Runner validates complete authority before runtime import
The runner SHALL strict-parse canonical registration, request, launch manifest,
stage authorization, delegated or exact external-human approval, and fresh
launch observation; validate their transitive identities and current pushed
source; and reject every missing, changed, stale, revoked, or ambiguous binding
before importing the runtime or constructing an environment.

#### Scenario: Authorization is absent
- **WHEN** source-only preflight is run for the reviewed manifest without a stage authorization
- **THEN** it records readiness only and no runtime, native module, model, environment, seed, checkpoint, or output is accessed

#### Scenario: Launch authority is stale or revoked
- **WHEN** approval or launch observation is unavailable, stale, from another task/request, or records revocation
- **THEN** `run-training` fails before consuming the execution identity or loading runtime dependencies

### Requirement: Runner composes the registered paired training lifecycle
After complete launch validation, the runner SHALL own one immutable execution
context and exclusive lease, use exactly the registration's sorted 512 training
seeds, debit candidate then control access before each environment, enforce the
registered deadline/resources, invoke the fixed paired runtime, publish one
complete checkpoint per 64 pairs, and publish exactly one terminal or rollback
classification that the independent verifier can reconstruct.

#### Scenario: Eight chunks complete without saturation
- **WHEN** all 512 pairs and 16 optimizer steps complete within bounds without the preregistered family-collapse stop
- **THEN** eight complete checkpoint bindings and one no-collapse training terminal are published with 1024 exact environment debits

#### Scenario: Family saturation stops training
- **WHEN** the fixed training family-collapse rule triggers at a complete chunk boundary
- **THEN** the runner publishes the exact terminal stop with zero canary/holdout access and no seal, retry, tuning, or further training

#### Scenario: Failure occurs inside a partial chunk
- **WHEN** process, environment, model, accounting, checkpoint, deadline, byte, or publication failure occurs before the next complete checkpoint
- **THEN** all partial evidence is preserved, same-identity replay is forbidden, and only a later authorized dead-owner terminalization may close the failure

### Requirement: Dead owner can be terminalized without replay
The runner SHALL expose a fully authorized `terminalize-dead-owner` command that
can close an existing nonterminal lifecycle prefix only after proving the
recorded owner is dead and validating the immutable context, lease, journal,
resource ledger, checkpoint prefix, and absence of conflicting terminal state.
It SHALL publish only the prescribed process-failure terminal and rollback
evidence and SHALL NOT restore runtime state, decode or access training seeds,
load runtime/native/model modules, construct an environment, consume a
continuation, or replay training.

#### Scenario: Proven dead owner has a valid partial prefix
- **WHEN** complete authority is valid, the recorded owner is proven dead, and the existing prefix is internally consistent and nonterminal
- **THEN** the terminalizer reclaims the stale-owner lease and publishes exactly one process-failure terminal and its prescribed rollback evidence without empirical access or replay

#### Scenario: Owner or prefix cannot be proven safe to close
- **WHEN** the recorded owner is alive, liveness is ambiguous, the prefix conflicts, or terminal evidence already exists
- **THEN** terminalization refuses without changing the lease, journal, resources, checkpoints, terminal, rollback, or continuation state

#### Scenario: Terminalization attempts empirical execution
- **WHEN** terminalization attempts runtime/native/model import, seed decoding or access, environment construction, checkpoint restoration, continuation consumption, or training replay
- **THEN** the command fails closed and publishes no new lifecycle artifact

### Requirement: Reopen and continuation remain narrowly bounded
The runner SHALL allow idempotent setup only before the first seed and SHALL
allow at most one continuation from the latest fully verified complete training
checkpoint. It SHALL reject partial-chunk, post-completion, post-canary,
changed-model, changed-optimizer, changed-generator, changed-resource, or
second-continuation attempts.

#### Scenario: Setup repeats before seed access
- **WHEN** the same exact identity repeats setup with zero journaled environment debits
- **THEN** the existing setup state may be revalidated without consuming a training continuation

#### Scenario: Complete-boundary continuation is used
- **WHEN** one interrupted run has a verified complete checkpoint, matching resource/journal prefix, dead prior owner, and no later debit
- **THEN** one continuation resumes at the next registered seed and publishes the existing continuation marker

### Requirement: Source-only preflight is execution inert
The runner SHALL expose a bounded source-only preflight that validates canonical
manifest/request/source/path identities and requires an absent output root without
loading native/model/runtime execution modules, decoding training seeds,
constructing an environment, acquiring an execution lease, or writing the
training output root.

#### Scenario: Source-only preflight succeeds
- **WHEN** the reviewed pushed manifest and tracked-clean source match, the output root is absent, and authorization is intentionally absent
- **THEN** preflight returns one bounded all-false readiness result and leaves every empirical operation and output absent

#### Scenario: Source-only preflight finds an existing output root
- **WHEN** the bound output root already exists
- **THEN** preflight returns NO-GO without opening, reading, classifying, or changing any child lifecycle or checkpoint artifact

#### Scenario: A prohibited import or access is attempted
- **WHEN** preflight attempts runtime/native/model import, registration seed decoding, environment construction, lease acquisition, checkpoint access, or output publication
- **THEN** the source-only gate fails and no training authorization becomes eligible
