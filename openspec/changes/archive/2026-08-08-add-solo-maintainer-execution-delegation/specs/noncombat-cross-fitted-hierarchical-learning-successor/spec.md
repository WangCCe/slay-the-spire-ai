## MODIFIED Requirements

### Requirement: Registration, human approval, authorization, and execution are separate irreversible stages
Planning, source implementation, fresh inventory and all-false registration,
read-only exact execution request, exact approval, tracked authorization, one
evidence-bearing execution, and terminal closeout SHALL be separate boundaries.
The execution request SHALL bind the pushed registration, native identity, exact
cohort/resources/output/retry terms, and false downstream authorities. An
authorization SHALL bind the complete normalized approval and canonical request
digest. Exact approval SHALL be either historical external-human approval v1 or
delegated approval v2. Historical v1 SHALL retain its verbatim external human
text, time, available task provenance, and explicit approval of the exact
request. Delegated v2 SHALL embed a canonical standing-delegation manifest that
preserves the exact external human grant and provenance, closed repository and
request-class scope, exclusions, revocation rule, and self-digest; it SHALL also
embed a deterministic machine resolution binding that delegation digest to the
exact request digest and resolution time. Agent review, an untracked or
unscoped permission, or generated text mislabeled as verbatim human input SHALL
NOT substitute for either approval mode. A durable first-seed journal marker
SHALL distinguish pre-start setup from empirical execution. A manual pre-start
re-entry SHALL preserve the exact registration, authorization, source-bound
static documents, native identity, cohort, controls, and output root and SHALL
NOT consume the post-start resume. It SHALL not automatically loop or substitute
any term. After the marker, algorithm or evidence failure SHALL be terminal,
while at most one infrastructure interruption MAY resume only the same identity
and replay only its incomplete registered chunk.

#### Scenario: An exact request has only agent review
- **WHEN** the registration and execution request are valid but neither exact external-human approval v1 nor exact delegated approval v2 is present
- **THEN** no authorization may be published and native loading, environment construction, seed access, fitting, and training remain rejected

#### Scenario: Historical v1 approval is bound
- **WHEN** a separate human message explicitly approves the reviewed canonical request and its exact bounds under the historical v1 schema
- **THEN** a tracked authorization may bind that request and verbatim approval without treating the human identity as a cryptographic claim

#### Scenario: Standing delegation resolves one exact request
- **WHEN** a canonical v1 delegation matches the registration scope and the exact execution-request schema version and a v2 resolution binds its self-digest to the exact reviewed request digest
- **THEN** a tracked authorization may embed that complete delegated approval without requiring the maintainer to transcribe the generated tuple
- **AND** generated resolution content SHALL NOT be represented as verbatim external human text

#### Scenario: Approval schema is hybrid or unknown
- **WHEN** an approval mixes v1 and v2 fields, omits a required field, adds an unknown field, or names an unsupported schema or approval mode
- **THEN** approval and authorization validation fail closed before dependency loading

#### Scenario: Delegation scope or content drifts
- **WHEN** grant text, grant time, provenance, pushed remote, registration-id prefix, request class, exclusion set, revocation rule, delegation digest, resolver kind, resolution time, or either bound digest differs
- **THEN** delegated approval and authorization are invalid and execution remains blocked

#### Scenario: The approval resolves a different request
- **WHEN** approved request digest, cohort, resource term, output root, retry rule, or false authority differs from the authorization candidate
- **THEN** the authorization is invalid and execution remains blocked

#### Scenario: Setup fails before seed access
- **WHEN** native loading, isolation, source, output-root, or process setup fails and the durable first-seed marker is absent
- **THEN** a later manual invocation may reopen only the exact source-bound static setup inventory or initialized zero-debit bootstrap with identical registration, authorization, source, native module, cohort, controls, and output root, without consuming the post-start resume

#### Scenario: A setup re-entry would change a term or loop automatically
- **WHEN** setup retry proposes a different module, seed, cohort, parameter, output root, or automatic retry cycle
- **THEN** the control plane rejects it before dependency loading or environment access

#### Scenario: Infrastructure interrupts one incomplete chunk
- **WHEN** the first post-start infrastructure interruption leaves a valid bootstrap or complete checkpoint and sufficient registered access/time budget
- **THEN** the same identity may restore exact model, optimizer, Python RNG, Torch generator, and chunk coordinates and replay only that incomplete chunk while retaining all previously debited resources

#### Scenario: A chunk has all episode terminals but no checkpoint
- **WHEN** infrastructure interrupts after all 64 registered episode accesses finish but before that chunk's complete checkpoint is durably published
- **THEN** the checkpoint coordinate still defines the chunk as incomplete and the sole resume may replay exactly that chunk without treating its access-only prefix as a complete update

#### Scenario: Infrastructure interrupts at a complete checkpoint boundary
- **WHEN** infrastructure interrupts after a complete checkpoint and before the next registered seed is debited
- **THEN** the sole resume restores that checkpoint and continues the next primary chunk without replaying a completed chunk or substituting a seed

#### Scenario: A second resume or evidence-driven retry is requested
- **WHEN** a second post-start resume, replacement identity, seed substitution, source change, estimator change, threshold change, tuning, or algorithm retry is requested
- **THEN** the request is rejected and the existing identity remains terminal

#### Scenario: The permitted resume is itself interrupted
- **WHEN** an infrastructure interruption occurs after the one post-start resume has been consumed
- **THEN** the runner charges the durable resource prefix, publishes one typed infrastructure failure, closes the identity as `experiment_failed_after_seed_access`, and grants no further resume

#### Scenario: Post-execution isolation differs
- **WHEN** the persisted post-isolation observation differs from the registered CommunicationMod or production-checkpoint identity
- **THEN** the runner preserves the observation and any typed failure witness but publishes no terminal intent, terminal, or manifest, and independent verification cannot classify the root as a valid bundle

#### Scenario: Active output is monitored
- **WHEN** the execution process is alive and holds its exclusive output lease
- **THEN** monitoring is limited to process liveness and does not read or mutate files below the active output root

#### Scenario: One stale lease is reclaimed for resume
- **WHEN** the sole permitted same-identity infrastructure resume proves that the recorded owner process is dead and validates the exact bootstrap, journal, resource prefix, complete checkpoints, and absence of an ambiguous temporary publication
- **THEN** it may atomically reclaim only that identity's stale lease before replaying the incomplete chunk

#### Scenario: Preexisting output cannot be reconstructed
- **WHEN** an output root, lease, journal, artifact, or temporary publication is unrelated, live, ambiguous, or differs from an exact source-bound setup, zero-debit bootstrap, checkpoint-publication recovery, terminal-publication recovery, or same-identity-resume inventory
- **THEN** the control plane fails closed without deleting, repairing, or replacing it

#### Scenario: Checkpoint and resource coordinates differ
- **WHEN** an incomplete chunk consumed episode accesses after the latest complete checkpoint
- **THEN** access-journal records, resource debits, and charged seconds remain monotonic, the checkpoint coordinate remains at the latest complete update, and resume cannot reclaim the consumed budget

## ADDED Requirements

### Requirement: Delegated approval is canonical and independently verifiable
The standard-library producer and independent verifier SHALL separately
reconstruct standing-delegation v1, delegated-approval v2, exact request, and
authorization identities without importing Torch, native, gameplay, or
CommunicationMod modules.

#### Scenario: Delegated approval is valid
- **WHEN** every delegation field, scope term, exclusion, provenance term, resolution field, request digest, and canonical body digest agrees
- **THEN** producer and independent verifier accept byte-equivalent normalized approval and authorization identities
- **AND** the authorization transitively binds the complete delegation without requiring an external terminal sidecar

#### Scenario: One delegated field is tampered
- **WHEN** any delegation, resolution, request, approval, or authorization field is changed while its surrounding digest is retained, or a closed scope or exact request binding is changed and surrounding digests are self-consistently recomputed
- **THEN** producer and independent verifier reject the artifact chain before dependency loading

#### Scenario: A different self-consistent grant is presented
- **WHEN** grant text, time, and provenance are replaced together and every dependent digest is recomputed without a cryptographic human identity or immutable published reference
- **THEN** validation treats it as a different syntactically valid delegation rather than claiming it can identify the original human author
- **AND** publication review and the source-bound authorization bytes remain responsible for selecting and preserving the accepted delegation

#### Scenario: Historical approval evidence is verified
- **WHEN** an existing v1 registration or terminal bundle contains its original exact external-human approval
- **THEN** producer and independent verifier continue to validate its historical schema without migration or reinterpretation as standing delegation

### Requirement: Delegated approval rendering remains source-only
Source-only commands SHALL validate a delegation against an exact registration,
render one delegated approval from canonical registration/request/delegation
inputs, and render the resulting authorization to stdout without publishing or
executing it.

#### Scenario: Source-only delegated controls are rendered
- **WHEN** valid canonical inputs and an explicit resolution timestamp are supplied
- **THEN** commands emit deterministic canonical JSON and leave Torch/native modules absent, the empirical output root unchanged, and all empirical operations unperformed

#### Scenario: Rendering input is invalid
- **WHEN** a registration, request, delegation, timestamp, approval, or digest differs
- **THEN** the source-only command fails without emitting a substitute artifact, loading dependencies, or invoking execution

#### Scenario: A later external human message revokes delegation
- **WHEN** the maintainer explicitly revokes the delegation before approval publication
- **THEN** publication orchestration rejects future delegated approvals even if source-only rendering previously produced valid candidate bytes
- **AND** the source-only renderer does not claim it can discover unrecorded conversation state or rewrite already published evidence

### Requirement: Changed delegation source requires fresh readiness
Any source or canonical-contract change implementing delegated approval SHALL
invalidate prior readiness as eligibility for a new empirical registration.

#### Scenario: Delegation implementation is pushed
- **WHEN** control-plane, independent-verifier, or canonical successor-contract bytes differ from a prior readiness source commit
- **THEN** that prior readiness remains historical evidence only
- **AND** a separately preregistered and independently verified fresh readiness identity is required before any new successor registration
