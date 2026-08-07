## ADDED Requirements

### Requirement: Execution reuses one validated registration context
Before native loading or seed access, the producer SHALL validate the complete
registration, canonical digest, execution identity, and output root once and
store them in one private process-local execution context. The producer SHALL
reuse that context for access-journal, resource-ledger, checkpoint, failure,
isolation, and terminal operations. After context creation, those operations
SHALL NOT call complete registration validation, recompute its canonical digest
from the full mapping, or deep-copy its source inventory per seed or nested
helper. Journal/event bytes, schedule coordinates, hash chains, resource
monotonicity, lease identity, and output identity SHALL remain validated at
their existing durable boundaries.

#### Scenario: A context is created from raw inputs
- **WHEN** an authorized execution presents a complete registration, identity, and output root
- **THEN** the producer performs one complete boundary validation, binds the canonical registration digest and output identity, and creates no native, seed, fitting, or training authority

#### Scenario: One synthetic chunk records 64 accesses
- **WHEN** source-only fixtures debit and close 64 registered accesses through one validated context
- **THEN** the count of complete registration validations is independent of the access count while every journal event, schedule coordinate, resource revision, and lease check remains valid

#### Scenario: Raw boundary input is corrupt
- **WHEN** a raw registration, digest, identity, output root, schedule, or source binding differs before context creation
- **THEN** context creation fails closed and no trusted context, dependency load, output lease, or seed access is produced

#### Scenario: The caller mutates its original mapping
- **WHEN** the caller changes the raw registration after context creation
- **THEN** the private context retains its independently owned validated values and later durable evidence cannot observe the caller mutation

### Requirement: Every terminal path records elapsed resource use
After the runtime attempt clock starts, the producer SHALL advance the durable
resource ledger with the bounded elapsed charge before publishing any terminal
intent. This SHALL apply to completion, family saturation, infrastructure
interruption, algorithm failure, evidence failure, and resource failure,
including a post-start failure before the first checkpoint. The charged value
SHALL remain monotonic, SHALL include prior resume charge, and SHALL not exceed
the registered ceiling. The independent verifier SHALL reconcile the terminal
resource revision and reject a producer terminal that omits its required final
attempt-charge event.

#### Scenario: The deadline fires before the first checkpoint
- **WHEN** at least one seed debit exists and the registered wall-time deadline fires before a complete chunk is published
- **THEN** the terminal resource ledger records the fixed time ceiling and the exact access prefix before classifying `experiment_failed_after_seed_access`

#### Scenario: A non-infrastructure algorithm failure occurs
- **WHEN** a finite elapsed attempt fails after seed access without an infrastructure exception
- **THEN** the producer durably charges that elapsed prefix before failure, isolation, intent, terminal, and manifest publication

#### Scenario: A resume inherits prior charge
- **WHEN** the sole permitted infrastructure resume starts from a nonzero charged prefix
- **THEN** its final charge is the bounded sum of the prior prefix and current attempt elapsed time and no failure path resets it to zero

#### Scenario: A terminal charge witness is missing
- **WHEN** a post-start terminal bundle lacks the required final attempt-charge revision or its terminal resource coordinate differs
- **THEN** independent verification rejects the bundle even if its artifact hashes otherwise agree

### Requirement: Producer terminal publication reuses validated state
The live producer SHALL carry the validated execution context and immutable
terminal intent forward through terminal and manifest publication without
reopening the complete registration or revalidating the just-published intent
through the recovery path. It SHALL build only the phase-appropriate prefix and
final managed inventories. A later process recovering interrupted terminal
publication SHALL still independently reopen and validate the exact context,
intent, durable prefixes, terminal document, and manifest before completing
only uniquely reconstructable bytes.

#### Scenario: One process closes a terminal failure
- **WHEN** failure, post-isolation, terminal intent, terminal, and manifest are published by the same lease owner
- **THEN** closeout reuses its validated context and in-memory intent, performs no complete registration validation in nested terminal helpers, and publishes the same canonical terminal schemas and hashes

#### Scenario: Terminal publication is interrupted
- **WHEN** the original process exits after intent or terminal publication
- **THEN** a later source-bound recovery performs full boundary validation once and completes only the missing byte-identical terminal artifact without reopening training

#### Scenario: A managed artifact changes during closeout
- **WHEN** the prefix or final managed inventory differs from the state bound by intent or terminal
- **THEN** publication fails closed and does not reuse an in-memory object to bypass byte verification

### Requirement: True child liveness governs output visibility
Execution supervision SHALL treat the actual Python evidence process as the
lease owner. Completion, timeout, or failure of an outer shell, wrapper, task,
or waiting cell SHALL NOT establish process exit. Monitoring SHALL retain the
output root as active until the true child is absent and its exclusive lease is
no longer locked. A verifier encountering a live or unreadable lease SHALL fail
closed without reading terminal evidence.

#### Scenario: The outer wrapper times out
- **WHEN** a wrapper stops waiting but the registered Python child remains alive
- **THEN** monitoring continues with child liveness only and does not inspect, verify, mutate, resume, or replace the active output root

#### Scenario: The true child exits
- **WHEN** the actual lease-owning Python process has ended and the lease is readable
- **THEN** post-exit terminal inspection and independent verification may begin

#### Scenario: Child liveness is ambiguous
- **WHEN** monitoring cannot prove whether the true lease owner is alive
- **THEN** the output remains active and no terminal or stale-lease conclusion is made

### Requirement: The repair grants no empirical authority
This source-only repair SHALL preserve every consumed terminal artifact and
seed identity and SHALL NOT authorize native loading, seed access, model
fitting, training, evaluation, gameplay, CommunicationMod, formal RL,
qualification, or promotion. Any later mechanism execution SHALL require a new
pushed source identity, fresh registration and cohort decision, exact request,
and separate explicit human approval.

#### Scenario: Source-only repair tests pass
- **WHEN** context, journal, resource, terminal, recovery, liveness, corruption, and performance regressions pass
- **THEN** the change becomes eligible only for source review and publication and no empirical execution authority is inferred
