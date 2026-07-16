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
- **WHEN** the approved v2 study root, qualification root, study ID, session ID, or output path already contains unrelated or previously launched bytes
- **THEN** qualification and launch SHALL fail before creating a run lock
- **AND** the system SHALL NOT delete, overwrite, reinterpret, or silently rename the colliding evidence

### Requirement: Pre-Collection Launch Qualification
The system SHALL require a source-bound, outcome-free launch qualification before creating the fresh v2 run lock or claiming a registered slot.

#### Scenario: Candidate qualifies for launch
- **WHEN** the canonical v2 registration and registration-bound implementation are ready for pre-collection review
- **THEN** qualification SHALL replay the registration bytes, verify all 24 dry-run launches, and complete one real-child no-action CommunicationMod attempt/ready/release smoke outside the registered study root
- **AND** it SHALL prove that no ledger, exploration manifest, trace, gameplay action, AI marker, checkpoint mutation, persistent CommunicationMod drift, or surviving process resulted from the smoke

#### Scenario: Qualification evidence is reviewed
- **WHEN** the no-action qualification succeeds
- **THEN** its external report SHALL be exclusively published with a self-hash and SHALL bind the registration hash, source commit, registration-bound implementation hashes, command, Windows Python path, dry-run digest, pre-smoke CommunicationMod baseline, approved study-launch CommunicationMod semantics, checkpoint snapshot, handshake record hashes, and isolation result
- **AND** an independent review SHALL exclusively publish a self-hashed attestation bound to the qualification-report hash before `start` is permitted
- **AND** the report, attestation, handshake records, isolation result, and every bound source or runtime value SHALL replay exactly immediately before `start`
- **AND** no tracked qualification artifact SHALL be written until the run-lock window has closed and the study has been independently verified

#### Scenario: Qualified candidate drifts before start
- **WHEN** the qualification report or reviewer attestation bytes, their self-hashes, a handshake-record hash, isolation result, source commit, registration bytes, registration-bound implementation file, command, Python path, approved study-launch CommunicationMod semantic record, checkpoint snapshot, or any other qualification binding differs after review
- **THEN** the candidate SHALL require a new qualification and review before run-lock creation
- **AND** no prior smoke or favorable test result SHALL authorize launch of the changed candidate

#### Scenario: Qualification fails
- **WHEN** canonical replay, dry-run, real-child readiness, release, isolation restoration, process cleanup, or independent review fails
- **THEN** no run lock, study ledger, or registered slot SHALL be created
- **AND** any implementation repair SHALL occur in a separate regression-backed change followed by a newly reviewed registration candidate
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
