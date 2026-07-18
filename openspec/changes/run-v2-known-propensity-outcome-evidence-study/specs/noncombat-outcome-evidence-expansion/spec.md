## ADDED Requirements

### Requirement: Fresh V2 Study Isolation
The system SHALL keep a newly registered v2 outcome-evidence study independent from every historical study and from all pre-registration operational evidence.

#### Scenario: Fresh v2 identity is registered
- **WHEN** the v2 study registration is rendered for review
- **THEN** it SHALL use the approved study ID, seed base, registration path, and previously absent artifact root
- **AND** every slot, configuration, manifest, trace, run lock, ledger, pool, estimate, and closeout path SHALL derive only from that registration

#### Scenario: Historical evidence is available
- **WHEN** the immutable v1 root or its reports are present during v2 qualification, collection, or finalization
- **THEN** they MAY be verified read-only as compatibility evidence
- **AND** no v1 decision, trajectory, slot, handshake, outcome, or artifact SHALL enter the v2 pool or satisfy a v2 gate

#### Scenario: Candidate identity collides
- **WHEN** the approved v2 study root, active qualification root, study ID, session ID, or output path already contains unrelated or previously launched bytes
- **THEN** qualification and launch SHALL fail before creating a run lock
- **AND** the system SHALL NOT delete, overwrite, reinterpret, or silently rename the colliding evidence

#### Scenario: A failed pre-lock qualification identity is preserved
- **WHEN** any reviewed qualification attempt stops before successful ready/release and its self-hashed failure record replays exactly
- **THEN** the failed qualification root SHALL remain immutable and SHALL NOT be retried, reused, deleted, or interpreted as a successful qualification
- **AND** one separately named, previously absent qualification root MAY be authorized only by an explicit reviewed planning amendment
- **AND** when no implementation binding changed, the unchanged canonical registration, study root, seed schedule, behavior policy, and thresholds SHALL remain fixed
- **AND** the new root SHALL repeat the complete dry-run, snapshot, real-child attempt/ready/release smoke, restoration, isolation, and independent-attestation gate

#### Scenario: The r3 evidence boundary is carried forward
- **WHEN** the preserved r3 root replays a valid attempt and ready, an absent release, failure-record self-hash `e495ce302f0ddf9628962e0d4147614a0cf9b9c7c010f256662a98eae76b033d`, file SHA-256 `5a3c47f5b93d7c1f66b5de6c32d3af139188b60735fa36733c6b3c6ee772cfec`, and final inventory `2a63cf3b7505ebf6d9e2f605eade7deec3c0afdaaa4da90ca6a99b517c82cb16`
- **THEN** the system SHALL preserve r3 as an immutable release-side external orchestration failure with no implementation-defect finding, retry authority, or start authority
- **AND** it SHALL NOT rely on a narrower unpreserved monitor mechanism to design, justify, or interpret any replacement qualification

#### Scenario: The prepared r4 candidate is superseded before launch
- **WHEN** independent review finds that the unlaunched r4 request/result contract does not bind broad isolation into independently replayable evidence
- **THEN** the static-config-only r4 root and prep-only request anchors SHALL remain unconsumed historical context and SHALL NOT authorize a live launch
- **AND** any replacement SHALL use a new source snapshot, regenerated implementation bindings, request v2, a direct-child review commit, and a previously absent qualification root

#### Scenario: The r5 replacement is prepared offline
- **WHEN** the isolation repair is committed as S `22cfd8b0c235af51b12911c0cb949f7e28a31ce6` and the previously absent r5 root is prepared
- **THEN** that root SHALL contain only its canonical static config before review commit R
- **AND** canonical request v2 SHALL bind S, the unchanged registration, all registration-bound implementation hashes, CommunicationMod bytes and semantic properties, marker bytes and line count, recursive run inventory, registered checkpoint-pattern inventory, global logs, and the exact seven-path inert review allowlist
- **AND** the request source SHALL remain unconsumed and no active request, child, handshake, terminal, study artifact, run lock, ledger, collection, OPE, training, or policy authority SHALL exist before tracked-clean `HEAD == R` passes independent replay

#### Scenario: The r5 launcher exits before active request publication
- **WHEN** one real r5 ModTheSpire invocation applies CommunicationMod's implicit 10-second external-process initialization timeout and kills the qualifier before its longer reviewed preflight publishes the active request
- **THEN** r5 SHALL remain a static-config-only, unconsumed pre-request operational identity with no attempt, ready, release, completion, failure, study artifact, marker, run, checkpoint, global-log, run-lock, ledger, collection, OPE, training, or policy authority
- **AND** the exact pre-r5 CommunicationMod bytes SHALL be restored and all request-bound isolation resources SHALL match before the game process is stopped
- **AND** r5 SHALL NOT be retried or reinterpreted as a protocol failure terminal

#### Scenario: The r6 replacement binds an explicit CommunicationMod initialization timeout
- **WHEN** the previously absent r6 root and request v2 are prepared at source snapshot S `2936c547bd7917fdbbc487470326716129e3fbe2`
- **THEN** the r6 root SHALL contain only its canonical static config before review commit R
- **AND** the request-bound 535-byte CommunicationMod baseline SHALL equal the preserved 505-byte pre-r6 baseline plus exactly `maxInitializationTimeout=120`
- **AND** the launch configuration SHALL preserve that exact non-command property while replacing only `command` with the trusted qualifier launcher
- **AND** the qualifier SHALL restore the exact 535-byte r6 baseline before terminal sealing, while the original 505-byte configuration remains preserved for final post-study restoration

#### Scenario: The r6 launcher times out before active request publication
- **WHEN** one real r6 ModTheSpire invocation uses reviewed R `9542af3aae8f93fa29eeaeefabcc5a1860a0107a`, the exact 20-token trusted launcher, and explicit `maxInitializationTimeout=120`, but CommunicationMod kills the silent external process before the active request is published
- **THEN** r6 SHALL remain a static-config-only, unconsumed pre-request operational identity with no attempt, ready, release, completion, failure, study artifact, marker, run, checkpoint, global-log, run-lock, ledger, collection, OPE, training, or policy authority
- **AND** the system SHALL preserve only the independently supported boundary that the process stopped between launch and active request publication; offline timing SHALL NOT be reinterpreted as proof of the unobserved live stage
- **AND** the exact 535-byte CommunicationMod baseline SHALL be restored, all request-bound isolation resources SHALL match, the game SHALL be stopped, and r6 SHALL NOT be retried
- **AND** no replacement identity SHALL be prepared until a separate reviewed change makes the pre-request stage durably diagnosable or another explicit amendment supplies equivalent evidence

#### Scenario: A qualification exposes an implementation defect
- **WHEN** a failed pre-lock qualification proves that a registration-bound implementation or handshake contract is defective before any registered study artifact exists
- **THEN** the failed qualification root and superseded registration bytes SHALL remain immutable pre-lock evidence
- **AND** the implementation SHALL be repaired only in a separate regression-backed change
- **AND** the next candidate SHALL regenerate and independently review the registration, implementation hashes, and qualification bindings before a newly named qualification root is authorized
- **AND** no result from the defective registration or failed root SHALL authorize `start`, a run lock, ledger creation, slot claim, pooling, OPE, training, or promotion

### Requirement: Pre-Collection Launch Qualification
The system SHALL require a source-bound, outcome-free launch qualification before creating the fresh v2 run lock or claiming a registered slot.

#### Scenario: Candidate qualifies for launch
- **WHEN** the canonical v2 registration and registration-bound implementation are ready for pre-collection review
- **THEN** qualification SHALL replay the canonical registration bytes regenerated after the isolation repair and all preserved historical identities through retired r6, verify all 24 dry-run launches, and complete one real-child no-action CommunicationMod attempt/ready/release/zero-exit lifecycle in a separately reviewed, previously absent replacement qualification root outside the registered study root
- **AND** the committed request SHALL bind source snapshot S, exact registration and implementation hashes, and one sorted inert review allowlist
- **AND** launch SHALL prove `HEAD == R`, supply the full R plus request self-hash/file-SHA/size as external anchors, and use the fixed stdlib `python -I -S -c` trusted launcher before the qualifier publishes any active request, attempt, or child process
- **AND** the registration and attempt SHALL bind the fixed 120-second readiness deadline and unchanged 10-second release deadline
- **AND** it SHALL prove that no ledger, exploration manifest, trace, gameplay action, AI marker, checkpoint mutation, persistent CommunicationMod drift, or surviving process resulted from the smoke
- **AND** the owner-controlled qualifier SHALL own request publication, attempt, the only child launch, immediate-ready acceptance, release, zero-exit wait, cleanup, and terminal sealing without any external ready/release monitor, while CommunicationMod configuration SHALL be compared semantically during execution and restored byte-for-byte afterward

#### Scenario: Qualification evidence is reviewed
- **WHEN** the no-action qualification succeeds
- **THEN** its canonical completion SHALL be exclusively published with a self-hash and SHALL bind the request/review chain, registration hash, source and implementation hashes, command, Windows Python path, configuration, marker boundary, handshake hashes, one-launch process evidence, forbidden paths, cleanup, and uniformly false study/training/policy authority
- **AND** the terminal result self-hash, file SHA-256, size, R, request self-hash, request file SHA-256, and request size SHALL be preserved externally before independent replay
- **AND** an independent verifier SHALL exclusively publish an attestation outside the qualification root and every request-bound or forbidden path before `start` is permitted
- **AND** the request, completion, attestation, handshake records, isolation result, and every bound source or runtime value SHALL replay exactly immediately before `start`
- **AND** only the reviewed inert request/amendment paths MAY be tracked before qualification; no runtime terminal or attestation artifact SHALL be tracked until the run-lock window has closed and the study has been independently verified

#### Scenario: Qualified candidate drifts before start
- **WHEN** S/R ancestry or diff, request or reviewer-attestation bytes, request/terminal self-hash/file-SHA/size anchors, a handshake-record hash, isolation result, registration bytes, registration-bound implementation file, command, Python path, approved study-launch CommunicationMod semantic record, checkpoint snapshot, or any other qualification binding differs after review
- **THEN** the candidate SHALL require a new qualification and review before run-lock creation
- **AND** no prior smoke or favorable test result SHALL authorize launch of the changed candidate

#### Scenario: Qualification fails
- **WHEN** canonical replay, dry-run, real-child readiness, release, isolation restoration, process cleanup, or independent review fails
- **THEN** no run lock, study ledger, or registered slot SHALL be created
- **AND** any implementation repair SHALL occur in a separate regression-backed change followed by a newly reviewed registration candidate
- **AND** when no implementation or registration binding changed and no registered study artifact exists, any replacement qualification root SHALL still require an explicit reviewed amendment and a complete fresh qualification rather than retrying the failed identity
- **AND** any temporarily applied CommunicationMod configuration SHALL be restored to the verified pre-study baseline before exit

#### Scenario: Start fails before publishing study state
- **WHEN** `start` exits without publishing a run lock, ledger, child process, or other study artifact
- **THEN** the system SHALL prove that absence, restore the verified pre-study CommunicationMod baseline, and require fresh qualification and review before another attempt
- **AND** it SHALL NOT present the failed attempt as a registered slot or outcome sample

### Requirement: Registered V2 Study Closeout
The fresh v2 study SHALL preserve the registered schedule and authority boundary through exactly one independently verified terminal closeout.

#### Scenario: Qualified study starts
- **WHEN** launch qualification passes and the final source is tracked-clean with unchanged qualified bindings
- **THEN** the study SHALL create one run lock and execute only the 24 ordered registered slots through the v2 preclaim handshake
- **AND** tracked source, rates, thresholds, target policy, estimator, commands, and outcome blinding SHALL remain unchanged until closeout

#### Scenario: Collection terminates normally
- **WHEN** all 24 registered slots are completed or interrupted without a global stop
- **THEN** finalization SHALL run exactly once and the standalone verifier SHALL replay the normal pool, target, readiness, estimate, influence, comparison, and closeout artifacts
- **AND** the result SHALL be reported as ready or inconclusive without authorizing causal uplift, formal training, gameplay-policy edits, or live promotion

#### Scenario: Collection stops globally
- **WHEN** any registered global integrity condition prevents later slot launch or normal all-slot attribution
- **THEN** later slots SHALL remain unlaunched and finalization SHALL emit only the registered blocked closeout
- **AND** the standalone verifier SHALL replay the blocked branch without permitting repair, retry, replacement, extension, pooling, OPE, training, or promotion under that registration

#### Scenario: All-terminal rule is scoped to normal finalization
- **WHEN** the registration contains `finalization_requires_all_slots_terminal=true`
- **THEN** that rule SHALL gate only normal pool/OPE finalization in the absence of a global stop
- **AND** a recorded global stop SHALL select the blocked-closeout exception with a terminal slot prefix followed only by registered unlaunched slots
