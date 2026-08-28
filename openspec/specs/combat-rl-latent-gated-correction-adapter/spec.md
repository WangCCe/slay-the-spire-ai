# combat-rl-latent-gated-correction-adapter Specification

## Purpose

Define the development-only adapter contract for frozen-parent, latent-gated legal combat action correction.

## Requirements

### Requirement: Frozen parent identity and behavior
The adapter SHALL own an immutable evaluation-mode copy of the supplied RL v2 parent, SHALL disable gradients for every parent parameter, and SHALL preserve the exact parent state identity across correction training and action selection.

#### Scenario: Correction update leaves parent unchanged
- **WHEN** an optimizer update is applied to the gate and correction heads
- **THEN** the deterministic parent state hash before and after the update is identical and no parent parameter receives a gradient

### Requirement: Inventory-aware parent-latent intervention features
The adapter SHALL derive each intervention feature row from the frozen parent's card, potion, and relic embeddings, parent hidden representation, finite parent Q values, and legal-action mask without changing the parent network implementation.

#### Scenario: Discrete inventory changes reach the adapter feature
- **WHEN** two otherwise equal observations differ in a supported card, potion, or relic identity
- **THEN** the adapter feature extraction includes the corresponding parent embedding path and returns finite, shape-compatible features

### Requirement: Abstaining legal-action selection
The adapter SHALL return the exact masked parent action when the gate probability is below the configured threshold and SHALL select only a currently legal correction action when the gate is open.

#### Scenario: Closed gate preserves parent action
- **WHEN** the gate is closed for an observation with at least one legal action
- **THEN** the selected action exactly equals the frozen parent's masked greedy action regardless of correction logits

#### Scenario: Open gate rejects illegal correction maxima
- **WHEN** the highest unmasked correction logit belongs to an illegal action and the gate is open
- **THEN** the adapter selects the highest-logit legal correction action

#### Scenario: Empty legal mask fails closed
- **WHEN** an observation contains no legal action
- **THEN** feature extraction or action selection raises a validation error without returning an action

### Requirement: Separate gate and changed-action objectives
The training helpers SHALL compute binary gate loss over direct and changed provenance labels and SHALL compute masked action loss only for changed rows with legal executed actions.

#### Scenario: Direct rows do not train the correction action target
- **WHEN** a mixed direct/changed batch is evaluated
- **THEN** direct rows contribute to gate loss but only changed rows contribute to correction action cross-entropy

#### Scenario: Illegal executed label is rejected
- **WHEN** a changed row labels an action absent from its legal mask
- **THEN** the training helper raises a validation error before producing a loss

### Requirement: Versioned development artifact
The system SHALL serialize adapter configuration and correction parameters in a versioned artifact bound to exact parent checkpoint and state identities, and the artifact SHALL be marked non-production-compatible.

#### Scenario: Exact artifact round trip
- **WHEN** a valid artifact is restored against the exact parent and evaluated on fixed observations
- **THEN** gate probabilities, correction actions, selected actions, and telemetry are exactly equal to the pre-serialization values

#### Scenario: Parent identity mismatch fails closed
- **WHEN** artifact restoration receives a parent checkpoint or state hash different from the artifact binding
- **THEN** restoration raises a validation error and returns no adapter

#### Scenario: Malformed correction state fails closed
- **WHEN** an artifact contains missing, extra, shape-incompatible, or non-finite gate or correction tensors
- **THEN** restoration raises a validation error and returns no adapter

### Requirement: Development-only authority
The adapter artifact SHALL NOT be loadable as a production RL v2 checkpoint and this capability SHALL NOT modify CommunicationMod configuration, combat agent routing, or the production r16 checkpoint.

#### Scenario: Mechanism implementation completes
- **WHEN** all adapter and artifact tests pass
- **THEN** the result authorizes only a later candidate-training proposal and grants no gameplay, qualification, promotion, or policy-quality authority
