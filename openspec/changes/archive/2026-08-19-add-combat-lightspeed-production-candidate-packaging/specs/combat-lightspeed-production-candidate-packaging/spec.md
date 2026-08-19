## ADDED Requirements

### Requirement: Bind and validate every packaging input
The system SHALL require caller-supplied SHA-256 identities for one simulator-only candidate checkpoint, one production parent checkpoint, the current item vocabulary, and the fresh confirmation report before packaging.

#### Scenario: Valid inputs are accepted
- **WHEN** the candidate is a production-incompatible `simulator_training_smoke` checkpoint, the parent is a schema-v2 RL `weights` checkpoint, all declared hashes match, and the item vocabulary matches the parent metadata
- **THEN** the system proceeds to structural validation without mutating or rereading the bound inputs

#### Scenario: Misclassified or changed input fails closed
- **WHEN** any input hash, checkpoint classification, schema, metadata, vocabulary dimension, or confirmation identity differs from its registered value
- **THEN** the system fails before creating a published output directory

### Requirement: Preserve the confirmed candidate policy exactly
The system SHALL package only a finite 328-dimensional simulator candidate whose tensor keys, shapes, and dtypes exactly match the validated production RL v2 network contract.

#### Scenario: Candidate structure matches production
- **WHEN** every candidate tensor is finite and exactly matches the production parent's state-dict key, shape, and dtype
- **THEN** the packaged checkpoint uses cloned CPU candidate tensors as its online network state and uses the validated parent metadata as its production metadata

#### Scenario: Architecture or encounter expansion is rejected
- **WHEN** the candidate has missing or additional tensors, changed shapes or dtypes, non-finite values, or a continuous dimension other than 328
- **THEN** packaging fails without publishing a checkpoint

### Requirement: Publish a strict production weights checkpoint
The system SHALL stage a schema-v2 `weights` checkpoint with `rl_space_version=v2`, validated metadata, episode zero, and provenance binding the converter, source commit, candidate, parent, items, confirmation, and canonical parameter identities.

#### Scenario: Production payload is constructed
- **WHEN** all input and structure validation passes
- **THEN** the staged payload contains no simulator production-compatibility marker, optimizer state, replay state, target network, training authority, or implicit promotion claim

#### Scenario: Existing output is protected
- **WHEN** the requested output directory already exists or the unique staging directory cannot be created
- **THEN** the system refuses to replace or delete the existing directory

### Requirement: Prove production reload equivalence before publication
The system SHALL reload the staged checkpoint through the strict production checkpoint validator and compare it with the source simulator policy before atomically publishing the output directory.

#### Scenario: Exact policy round trip succeeds
- **WHEN** the reloaded checkpoint has the same canonical parameter SHA-256, zero finite valid-action Q delta, and zero greedy-action mismatches on deterministic registered probes
- **THEN** the system atomically publishes the checkpoint, report, summary, and manifest with verdict `production_candidate_packaging_ready`

#### Scenario: Reload or equivalence fails
- **WHEN** strict production loading, parameter identity, Q equivalence, action equivalence, or staged artifact verification fails
- **THEN** the system removes only its own newly created staging directory and publishes no output

### Requirement: Keep packaging isolated from production and gameplay
The system SHALL write only to a new explicit offline output directory and SHALL NOT modify the production parent, simulator candidate, item vocabulary, CommunicationMod configuration, game processes, or checkpoint discovery paths.

#### Scenario: Packaging completes
- **WHEN** a production-loadable candidate is published successfully
- **THEN** production r16 remains active and the report grants no gameplay, qualification, promotion, production replacement, training, or CommunicationMod authority
