## ADDED Requirements

### Requirement: Training launch is bound to one exact runner command set
The system SHALL publish and independently review one canonical launch manifest
that binds the pushed r6 registration, training request and review, runner
source path/hash/commit, registered experiment source commit/inventory, additive
registration verifier path/hash, exact source-inventory path/hash already bound
by the r6 registration request, Windows interpreter, output root, resource
ceilings, denied operations, and the closed `preflight`, `run-training`, and
`terminalize-dead-owner` CLI shapes. It SHALL also bind one canonical rollback
authority and hash, exact candidate-disabled control target, control checkpoint/
configuration identities, and read-only production-isolation identities. The
manifest SHALL grant no authority and SHALL be pushed before training
authorization becomes eligible.

#### Scenario: Exact launch manifest is reviewed
- **WHEN** every registered path, digest, source, interpreter, command, resource, exclusion, and all-false downstream binding agrees
- **THEN** the manifest becomes eligible for source-only preflight without authorizing or starting training

#### Scenario: Runner or command drifts
- **WHEN** runner bytes, source commit, interpreter, registered command name or CLI argument, request, registration, review, output root, resource, or denied operation differs
- **THEN** preflight rejects the launch before runtime/native/model import, output creation, or seed access

### Requirement: Complete authority binds each runner command transitively
The system SHALL compute a canonical runner composite binding the request,
registration, launch manifest, exact command, rollback authority, output and
resources, and SHALL prove its operations are a strict subset of the request's
execution authority and all-false downstream terms. Under standing delegation,
a deterministic resolver MAY bind that composite only after validating the
immutable broad grant/exclusions, delegated stage approval, and a fresh runner
launch observation naming the composite digest. Under exact external-human
authority, the approval message and fresh runner launch observation SHALL name
the composite digest verbatim.

The system SHALL independently review and push one all-false command-specific
envelope that binds the stage authorization, authority mode/record, launch
observation and composite before its command. The envelope SHALL NOT grant
authority by itself or change any request term.

#### Scenario: Complete authority and composite agree
- **WHEN** the stage authorization and validated standing-delegation resolution or exact external-human approval plus fresh runner observation transitively bind the exact request-subordinate manifest/command/rollback composite
- **THEN** one all-false command-specific envelope becomes eligible for independent review and pushed publication without starting or broadening training

#### Scenario: Composite is missing or not transitively authorized
- **WHEN** the command-specific envelope is absent, unpushed, stale, revoked, changed, reused by the wrong command, or does not bind any authority, manifest, command, rollback, request, output, or resource edge exactly
- **THEN** `run-training` and `terminalize-dead-owner` fail before lease acquisition, rollback-context construction, runtime import, output change, or empirical access

### Requirement: Runner validates complete authority before runtime import
The runner SHALL strict-parse canonical registration, request, launch manifest,
stage authorization, delegated or exact external-human approval, fresh launch
observation, and the command-specific envelope; validate their transitive identities and current pushed
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

The runner SHALL keep the r6 registration bytes/self-digest immutable. Only
after complete authority and independently validating the registration against
the manifest-bound source inventory plus the manifest-bound rollback
authority may it create a process-local validated registration view that adds
`rollback_authority_sha256` while retaining the original registration identity.
It SHALL publish a write-once runner-launch marker binding the manifest,
run-envelope, command, and rollback identities before empirical access.

The runner SHALL publish a canonical zero-progress initial checkpoint bound to
the registered matched bootstrap. Each completed chunk SHALL publish a chain
record binding the predecessor checkpoint file digest, exact initial component
hashes/counters, final checkpoint file digest, exact final component hashes/
counters, and chunk seeds. Every chunk's initial canonical checkpoint bytes
SHALL equal its predecessor's final bytes; a continuation restore SHALL
re-encode identically before the next environment access.

#### Scenario: Eight chunks complete without saturation
- **WHEN** all 512 pairs and 16 optimizer steps complete within bounds without the preregistered family-collapse stop
- **THEN** eight complete checkpoint bindings and one no-collapse training terminal are published with 1024 exact environment debits

#### Scenario: Chunk state does not equal its predecessor
- **WHEN** any model, optimizer, generator, counter, canonical checkpoint byte, or predecessor digest differs before a new chunk
- **THEN** the runner rejects the chunk before its first environment debit and publishes no successor checkpoint binding

#### Scenario: Family saturation stops training
- **WHEN** the fixed training family-collapse rule triggers at a complete chunk boundary
- **THEN** the runner executes the registered candidate-disabled rollback, publishes the exact terminal stop with zero canary/holdout access, and permits no seal, retry, tuning, or further training

#### Scenario: Failure occurs inside a partial chunk
- **WHEN** process, environment, model, accounting, checkpoint, deadline, byte, or publication failure occurs before the next complete checkpoint
- **THEN** all partial evidence is preserved, same-identity replay is forbidden, and only a later authorized dead-owner terminalization may close the failure

### Requirement: Dead owner can be terminalized without replay
The runner SHALL expose a fully authorized `terminalize-dead-owner` command that
can close an existing nonterminal lifecycle prefix only after proving the
recorded owner is dead and validating the immutable context, lease, journal,
resource ledger, checkpoint prefix, and absence of conflicting terminal state.
It SHALL publish only the prescribed process-failure terminal and rollback
evidence. It MAY reobserve control checkpoint/configuration and production
isolation bytes and restore the exact candidate-disabled experiment-local target
JSON required by registered rollback. It SHALL NOT restore a training/runtime
checkpoint, load checkpoint bytes as a model, restore runtime state, decode or
access training seeds, load runtime/native/model modules, construct an
environment, consume a continuation, or replay training.

The terminalizer SHALL hold a bound sibling guard outside the managed output
while revalidating owner death, exact lease bytes, the envelope-bound prefix and
terminal absence immediately before stale-lease reclamation. A conflict SHALL
leave the execution lease and managed output unchanged.

#### Scenario: Proven dead owner has a valid partial prefix
- **WHEN** the recorded owner is proven dead, the existing prefix is internally consistent and nonterminal, and a fresh reviewed pushed terminalization envelope binds that owner, lease, run envelope, prefix, failure classification, manifest and rollback identity
- **THEN** the terminalizer reclaims the stale-owner lease, publishes a closure marker binding the terminalization-envelope SHA, restores only the exact experiment-local candidate-disabled control target, reobserves bound control/production identities without model loading, and publishes exactly one process-failure terminal and registered rollback evidence without empirical access or replay

#### Scenario: A prior run envelope is offered for terminalization
- **WHEN** terminalization authority reuses the run envelope or omits a fresh owner/prefix-bound terminalization envelope
- **THEN** terminalization refuses before stale-lease reclamation or output change

#### Scenario: Terminalizer dies after closure starts
- **WHEN** the terminalizer owner dies after lease reclamation or identical closure-marker publication and the original failure prefix plus any durable closure suffix remain exact
- **THEN** the same terminalization envelope may resume only the idempotent rollback/terminal sequence after a fresh liveness check, without runtime, seed, environment, continuation, or training access

#### Scenario: Terminalizer resume finds drift or staging
- **WHEN** a closure-only resume finds changed failure evidence, a different closure marker or classification, unbound suffix artifacts, or ambiguous staging
- **THEN** it preserves all bytes and refuses without repair, deletion, replay, or a new classification

#### Scenario: Owner or prefix cannot be proven safe to close
- **WHEN** the recorded owner is alive, liveness is ambiguous, the prefix conflicts, or terminal evidence already exists
- **THEN** terminalization refuses without changing the lease, journal, resources, checkpoints, terminal, rollback, or continuation state

#### Scenario: Terminalization attempts empirical execution
- **WHEN** terminalization attempts runtime/native/model import, seed decoding or access, environment construction, training/runtime checkpoint restoration, checkpoint model loading, continuation consumption, or training replay
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
training output root. It SHALL validate the canonical rollback-authority document
and digest without opening its control checkpoint/configuration or production
isolation paths, and SHALL validate the source-inventory binding from the r6
registration request without opening or decoding that inventory.

#### Scenario: Source-only preflight succeeds
- **WHEN** the reviewed pushed manifest and tracked-clean source match, the output root is absent, and authorization is intentionally absent
- **THEN** preflight returns one bounded all-false readiness result and leaves every empirical operation and output absent

#### Scenario: Source-only preflight finds an existing output root
- **WHEN** the bound output root already exists
- **THEN** preflight returns NO-GO without opening, reading, classifying, or changing any child lifecycle or checkpoint artifact

#### Scenario: A prohibited import or access is attempted
- **WHEN** preflight attempts runtime/native/model import, registration seed decoding, environment construction, lease acquisition, rollback-target/control/production path access, checkpoint/configuration access, or output publication
- **THEN** the source-only gate fails and no training authorization becomes eligible
