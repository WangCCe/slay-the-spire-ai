# noncombat-outcome-evidence-expansion Specification

## Purpose
Define a pre-registered, source-bound, blinded, and fail-closed study lifecycle for expanding known-propensity non-combat outcome evidence without authorizing training or live promotion.

## Requirements

### Requirement: Immutable Outcome-Evidence Registration
The system SHALL require a committed, versioned registration that fixes the outcome-evidence study before any registered game starts.

#### Scenario: Registration is valid
- **WHEN** the study registration is created
- **THEN** it SHALL contain exactly 24 ordered slots of 25 games, deterministic session IDs and seeds, the fixed eval command contract, `card_reward=300` basis points, `shop=1000` basis points, a two-attempt per-run alternative budget, output naming rules, integrity rules, final evidence thresholds, and a canonical registration hash
- **AND** it SHALL fix deterministic Current, the committed calibration artifact path, the deterministic bootstrap seed, the 95 percent confidence level, and exactly 10,000 production bootstrap replicates
- **AND** it SHALL identify `card_reward:skip` and `shop:leave` as the only executable alternatives while event and route remain shadow-only

#### Scenario: Registration-controlled value changes
- **WHEN** any registered slot, seed, session ID, command field, exploration rate, budget, threshold, or output rule differs from the committed registration
- **THEN** the study SHALL reject the changed value
- **AND** it SHALL NOT silently regenerate or partially apply the schedule

### Requirement: Source-Bound Study Run Lock
The system SHALL bind all registered sessions to one immutable clean source and live-isolation lock created before the first slot launches.

#### Scenario: Study lock is created
- **WHEN** the start command runs from a tracked-clean source before slot one
- **THEN** it SHALL bind the registration bytes and hash, actual HEAD, hash-bound implementation files, Windows Python path, exact child command, CommunicationMod semantic configuration, and checkpoint isolation snapshot
- **AND** every generated slot configuration and session manifest SHALL reference the same run-lock hash

#### Scenario: Locked source or live state drifts
- **WHEN** a later slot observes a different source, registration, command, Python path, CommunicationMod semantic configuration, or checkpoint snapshot
- **THEN** the system SHALL record a global integrity stop before launching another game
- **AND** the affected study SHALL NOT qualify through later restoration or additional collection

### Requirement: Fixed Non-Replacement Slot Schedule
The system SHALL enforce the 24-slot registration as an outcome-independent upper bound of 600 game attempts.

#### Scenario: Registered slot launches normally
- **WHEN** the next ordered slot has not previously launched and the run lock remains valid
- **THEN** the runner SHALL launch it at most once with `--max-games 25` and `--eval`
- **AND** it SHALL reject training flags, model mutation flags, unregistered session IDs, and out-of-order replacement slots

#### Scenario: Slot exits before 25 complete trajectories
- **WHEN** a launched slot exits early for an operational reason without a global integrity failure
- **THEN** the ledger SHALL mark that slot terminally interrupted and preserve its complete eligible evidence
- **AND** the system SHALL NOT restart, replace, or add games to that slot

#### Scenario: Outcome evidence appears during collection
- **WHEN** a victory, supported victory, OPE estimate, or comparison result could be derived before slot 24 is terminal
- **THEN** that outcome SHALL NOT change the registered schedule, rates, thresholds, source, or continuation rule
- **AND** no success-based early stop or post-slot-24 extension SHALL be permitted

### Requirement: Blinded Structural Collection Monitor
The system SHALL provide a collection-time monitor that exposes integrity and progress without exposing study outcomes or policy evaluation.

#### Scenario: Study remains in collection phase
- **WHEN** at least one registered slot is not terminal and no global integrity closeout has started
- **THEN** monitor output MAY report slot lifecycle, process exit, artifact existence, manifest and configuration hashes, exact replay and confirmation counts, conservative run-join completeness, and isolation status
- **AND** it SHALL omit victory values and counts, floor reached, killed-by values, target weights, ESS, OPE estimates, bootstrap and influence results, and policy-comparison gates

#### Scenario: Blinded artifact is rendered
- **WHEN** a machine-readable or Markdown collection monitor artifact is written
- **THEN** its schema and rendered text SHALL contain none of the registered forbidden outcome or evaluation fields
- **AND** deterministic rendering SHALL be invariant to input enumeration order

### Requirement: Fail-Closed Study Integrity
The system SHALL stop registered collection when evidence can no longer be attributed to the frozen study contract.

#### Scenario: Global integrity condition fails
- **WHEN** source or isolation drifts, a launched session is missing from the ledger, exact replay or confirmation fails, a manifest hash mismatches, or an unregistered session is presented as study evidence
- **THEN** the system SHALL append the exact global stop reason and prevent later slot launches
- **AND** finalization SHALL produce a blocked closeout without treating restoration or selective exclusion as a cure

#### Scenario: Gameplay diagnosis requires inspection
- **WHEN** an operationally stuck or failed process requires logs or a screenshot to diagnose safely
- **THEN** the operator MAY inspect the minimum evidence required to stop or recover the process
- **AND** any observed outcome SHALL NOT alter the registered experiment or authorize a replacement slot

### Requirement: Deterministic All-Slot Finalization
The system SHALL finalize the registered study exactly once from every registered slot after collection becomes terminal.

#### Scenario: All slots are terminal
- **WHEN** all 24 slots are completed or interrupted without a global integrity stop
- **THEN** finalization SHALL enumerate the committed slot table, verify every launched session, and include every structurally eligible trajectory from those sessions
- **AND** it SHALL write deterministic pool, target, readiness, estimate, verification, and closeout artifacts with complete inclusion and exclusion accounting

#### Scenario: Finalization is claimed exactly once
- **WHEN** finalization is ready to publish its registered artifacts
- **THEN** it SHALL atomically and exclusively create the registered finalization claim before replacing any final artifact
- **AND** an existing claim or final artifact SHALL reject the attempt before pool or outcome processing, while a failed artifact transaction SHALL retain the claim and fail closed

#### Scenario: Operator supplies a selective input set
- **WHEN** requested finalization omits a registered launched slot, adds an unregistered slot, duplicates a trajectory, or changes canonical input order
- **THEN** selective omission, addition, or duplication SHALL fail closed
- **AND** input reordering alone SHALL NOT change canonical output bytes or gates

#### Scenario: Study stopped globally
- **WHEN** a global integrity stop has made later collection invalid
- **THEN** finalization SHALL be allowed only as a blocked closeout that preserves collected source evidence
- **AND** it SHALL write no pool, target, readiness, estimate, bootstrap, influence, or comparison artifact and SHALL represent those unavailable source bindings as null
- **AND** it SHALL NOT emit a passing outcome-evidence gate

### Requirement: Outcome-Evidence Authority Boundary
The system SHALL report evidence expansion separately from policy comparison, formal training, reward design, causal claims, and live promotion.

#### Scenario: Outcome-evidence expansion passes
- **WHEN** every registered integrity and evidence-expansion condition passes
- **THEN** the report SHALL set only `outcome_evidence_expansion_ready` according to this study gate and SHALL run the existing OPE estimate and comparison gates unchanged
- **AND** causal uplift, formal non-combat RL training, reward design, and live policy promotion SHALL remain unauthorized

#### Scenario: Fixed evidence remains insufficient
- **WHEN** the registered limit is reached but any evidence-expansion threshold fails
- **THEN** the closeout SHALL report the observed shortfall as inconclusive or blocked
- **AND** it SHALL NOT lower thresholds, append replacement games, substitute floor reached for victory, or claim policy quality

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

### Requirement: Observable Future Qualification Gate
The system SHALL require every future replacement outcome-evidence qualification to pass the versioned pre-request observability contract before it can support a later reviewed `start` decision.

#### Scenario: A future replacement is prepared
- **WHEN** the observability implementation has passed regression, full-suite, strict OpenSpec, byte, and independent source-only review and a separate amendment prepares a previously absent qualification identity
- **THEN** that identity SHALL use qualification request/result/review-binding v3 and bootstrap-evidence v1 with a fresh source snapshot, review commit, request anchors, launch token, root, and exact CommunicationMod baseline
- **AND** no v1/v2 request, retired root, copied prefix, timeout increase, or cleanup operation SHALL substitute for a fresh v3 identity

#### Scenario: A future replacement supports start review
- **WHEN** a future v3 identity has one exact claim/stage/active-request/handoff/attempt/ready/release/zero-exit/terminal chain, restored request-bound isolation, no surviving child, externally pinned terminal anchors, and passing independent attestation
- **THEN** that evidence SHALL remain input only to a separate later review of whether to create the registered study run lock
- **AND** it SHALL NOT itself create the run lock, start collection, interpret OPE, change gameplay policy, make causal claims, train a model, or promote a policy

#### Scenario: Historical r1 through r6 evidence is verified within its preserved boundary
- **WHEN** the preserved r1-r6 roots, requests, terminals, reports, audits, and recorded absences are inspected after v3 observability is implemented
- **THEN** every available historical byte SHALL retain its exact path, size, and SHA-256 and every unavailable artifact SHALL remain explicitly absent
- **AND** evidence-derived classification SHALL remain distinct from any separately reviewed consumed, failed, obsolete, prepared, partial, or retired governance disposition
- **AND** complete public v1/v2 replay SHALL be required only when the preserved bundle contains every request, review, and Git anchor required by that verifier path
- **AND** no missing request, result, review commit, audit byte, Git anchor, bootstrap field, or root artifact SHALL be synthesized to make an incomplete historical bundle replayable
- **AND** no historical v1/v2 identity SHALL be retried, upgraded in place, or used to authorize a future launch or `start`

#### Scenario: Observability implementation is complete but no replacement exists
- **WHEN** this change passes all offline implementation and review gates but no separate replacement amendment has been approved
- **THEN** the registered v2 study root SHALL remain absent and collection SHALL remain blocked
- **AND** completion of observability alone SHALL NOT authorize r7 preparation, a live game launch, study evidence collection, OPE interpretation, training, or policy change
