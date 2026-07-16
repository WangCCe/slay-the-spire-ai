## ADDED Requirements

### Requirement: Preclaim CommunicationMod Handshake
The system SHALL require the actual registered gameplay child to prove CommunicationMod state delivery before the study ledger claims a future slot.

#### Scenario: Preclaim attempt is durable
- **WHEN** the next slot passes run-lock and ordering validation and all registered handshake and gameplay output paths are absent
- **THEN** the parent SHALL capture the initial AI marker count and exclusively publish a bound attempt record before starting the child process
- **AND** any orphaned or duplicate attempt SHALL trigger one global stop without starting or retrying a child for that slot

#### Scenario: Registered child becomes ready
- **WHEN** a launchable registered slot has a valid run lock and the exact child receives and parses an initial CommunicationMod state within the registered deadline
- **THEN** the child SHALL publish an exclusive canonical ready record bound to the registration, run lock, slot, config, token, attempt, and child process while callbacks, exploration initialization, and gameplay actions remain disabled
- **AND** the parent SHALL verify that record and the live child, require unchanged marker count and absent gameplay outputs, and append `slot_started` with the original marker boundary

#### Scenario: Parent releases a claimed child
- **WHEN** the parent has appended `slot_started` for the verified ready child
- **THEN** it SHALL atomically publish the matching release record and the child SHALL validate it before initializing exploration, registering callbacks, or executing gameplay
- **AND** the already received state SHALL be retained for normal startup without being acted on before release or processed twice

#### Scenario: Preclaim handshake fails
- **WHEN** the child times out, exits early, emits malformed readiness, presents an attempt, binding, or PID mismatch, creates duplicate handshake artifacts, grows the AI marker count, or creates a manifest or trace before claim
- **THEN** the parent SHALL terminate the child, append one exact global stop, and leave the registered slot unlaunched
- **AND** it SHALL NOT retry, replace, release, or attribute a manifest, trace, decision, trajectory, or AI marker to that slot

#### Scenario: Failure occurs after claim but before release
- **WHEN** the parent or host fails after `slot_started` but before a valid release is consumed
- **THEN** recovery SHALL preserve the slot as launched and mark it interrupted before globally stopping the study
- **AND** it SHALL NOT roll the slot back to unlaunched or permit another child for that slot

#### Scenario: Ordinary gameplay has no study handshake
- **WHEN** the explicit registered-study handshake environment is absent
- **THEN** coordinator, exploration, and agent startup SHALL retain their existing behavior without creating handshake artifacts
- **AND** no ordinary gameplay or bounded eval command SHALL be treated as a registered slot

### Requirement: Versioned Launchable Handshake Contract
The system SHALL hash-bind the preclaim handshake contract into every future launchable outcome-evidence registration and run lock while preserving historical evidence bytes.

#### Scenario: Future registration is launchable
- **WHEN** a new outcome-evidence registration is generated after this capability is implemented
- **THEN** it SHALL use the new schema version and fix the handshake protocol version, readiness and release deadlines, attempt/ready/release artifact names, implementation files, and fail-closed continuation rule
- **AND** `start` and `run-next` SHALL reject a registration that lacks or changes any required handshake binding

#### Scenario: Historical v1 evidence is inspected
- **WHEN** an existing v1 registration is loaded for read-only verification
- **THEN** the verifier SHALL preserve its original schema and artifact interpretation without rewriting any byte
- **AND** the runner SHALL refuse to launch or resume a v1 registered slot after this change

### Requirement: Independent Blocked-Closeout Verification
The standalone outcome-evidence verifier SHALL independently replay a registered blocked closeout without importing the study finalizer or requiring normal OPE artifacts.

#### Scenario: Ledger selects blocked verification
- **WHEN** the validated append-only ledger contains exactly one global stop and no active slot and the validated claim mode is `integrity_stop`
- **THEN** the verifier SHALL select the blocked branch from those frozen facts rather than a CLI option, report status, or artifact-presence guess
- **AND** it SHALL require a valid terminal slot prefix followed only by registered unlaunched slots

#### Scenario: Blocked closeout is exact
- **WHEN** the claim and closeout are bound to the registration, run lock, source, ledger slot table, and exact global-stop reason
- **THEN** the verifier SHALL independently reconstruct and match the deterministic JSON and Markdown closeout, null unavailable source bindings, blockers, limitations, and all-false authority gates
- **AND** it SHALL require every registered pool, target, readiness, estimate, bootstrap, influence, and comparison artifact to be absent

#### Scenario: Blocked evidence is tampered
- **WHEN** the ledger, claim mode, stop reason, slot accounting, closeout hash, source binding, blocker, authority gate, limitation, Markdown rendering, or forbidden-artifact absence differs from independent replay
- **THEN** the verifier SHALL exit nonzero at the first deterministic mismatch
- **AND** it SHALL NOT fall through to normal verification or report partial success

#### Scenario: Historical blocked artifact is replayed
- **WHEN** the frozen 2026-07-15 v1 registration and blocked artifact root are supplied read-only
- **THEN** the standalone verifier SHALL pass the blocked branch and report its independently checked registration, run-lock, ledger, claim, closeout, and forbidden-artifact facts
- **AND** that pass SHALL NOT authorize OPE, policy comparison, training, reward design, gameplay-policy edits, or live promotion

#### Scenario: Normal closeout remains normal
- **WHEN** the validated ledger has no global stop, all registered slots are terminal, and claim mode is `complete`
- **THEN** the verifier SHALL run the existing full pool, target, readiness, estimate, influence, and closeout replay without weakening any check
- **AND** a mixed normal/blocked claim or artifact set SHALL fail closed
