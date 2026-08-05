# noncombat-hierarchical-policy-objective-contract Specification

## Purpose

Define additive source-only selected-action log-probability and entropy terms
for the checked-in hierarchical action-family distribution, with explicit
score-greedy tie semantics and no loss, coefficient, training, or runtime
authority.

## Requirements

### Requirement: Selected action is validated by stable identity
The system SHALL accept a finite rank-1 CPU float32 score tensor, aligned
validated candidates, and one selected `action_id`. It SHALL delegate candidate
and family validation to the checked-in action-family distribution and SHALL
reject a missing, empty, duplicate, or non-candidate selected identity without
returning partial terms.

#### Scenario: Selected action is present
- **WHEN** one unique candidate action ID is supplied as the selected action
- **THEN** the system resolves its candidate index, family identity, and family index without reordering candidates

#### Scenario: Selected action is invalid
- **WHEN** the selected action ID is empty, malformed, or absent from the candidate set
- **THEN** the system fails before returning objective terms

### Requirement: Selected hierarchical log probability remains factorized
The system SHALL expose finite CPU float64 selected-family,
selected-conditional, and selected-joint log-probability tensors that preserve
the source score autograd graph. The selected joint term SHALL equal the sum of
the selected family and conditional terms exactly.

#### Scenario: Multi-family action is selected
- **WHEN** a selected candidate belongs to one of multiple action families
- **THEN** its joint log probability equals its family log probability plus its within-family conditional log probability
- **AND** differentiating that joint term produces finite score gradients

#### Scenario: Candidate and selected identity are permuted together
- **WHEN** candidates and aligned scores are permuted while preserving action identities
- **THEN** every selected scalar term remains equal and candidate metadata follows the selected identity

### Requirement: Entropy terms remain separate and complete
The system SHALL expose family entropy, expected conditional entropy, and joint
entropy as separate finite CPU float64 tensors. Joint entropy SHALL equal family
entropy plus expected conditional entropy within numerical tolerance. The
system SHALL NOT accept coefficients or return a combined entropy-regularized
loss.

#### Scenario: Caller inspects entropy terms
- **WHEN** valid multi-family terms are constructed
- **THEN** each entropy component remains separately addressable and differentiable
- **AND** no coefficient, reward, return, advantage, or loss is selected by the contract

#### Scenario: Only one family exists
- **WHEN** every candidate belongs to the same family
- **THEN** family entropy and selected family log probability are exactly zero
- **AND** selected joint log probability equals selected conditional log probability while conditional entropy remains observable

### Requirement: Deterministic evaluation uses max-score semantics
The system SHALL expose the lexicographically sorted action IDs tied at the
maximum raw score, a unique greedy action ID only when exactly one maximum
exists, and an independently reconstructed two-stage max-family-score then
max-within-family action set. The two score-derived sets SHALL be equal. The
system SHALL NOT expose joint-probability argmax as a deterministic selection
rule.

#### Scenario: Raw score maximum is unique
- **WHEN** exactly one candidate has the maximum score
- **THEN** the unique score-greedy action and unique two-stage score-greedy action are that candidate

#### Scenario: Raw score maximum is tied
- **WHEN** multiple candidates share the maximum score within or across families
- **THEN** all tied action IDs are reported in lexicographic order and the unique greedy action is absent
- **AND** candidate input order does not break the tie

### Requirement: Extreme values and gradients remain bounded
The system SHALL preserve finite objective and entropy terms for every finite
float32 score, including opposite float32 limits, and SHALL preserve finite
gradients wherever the underlying distribution derivative is defined.

#### Scenario: Opposite float32 limits are supplied
- **WHEN** a valid selected decision includes both finite float32 extremes
- **THEN** every exposed objective and entropy tensor remains finite
- **AND** backward evaluation does not create a non-finite score gradient

### Requirement: Metadata and design evidence grant no authority
The system SHALL expose stable JSON-compatible metadata that binds its schema,
dependency distribution schema, selected identity, score-greedy semantics,
entropy decomposition, device, dtype, absence of coefficient and loss APIs, and
an exact all-false authority map. It SHALL render deterministic synthetic design
evidence and SHALL remain absent from production and empirical execution imports.

#### Scenario: Metadata and report are reproduced
- **WHEN** the same checked-in implementation renders its metadata and design evidence twice
- **THEN** both outputs are identical and state that no training, model-loading, native-loading, seed-access, experiment, formal-RL, gameplay, qualification, or promotion authority is granted

#### Scenario: Existing runtime modules are imported
- **WHEN** the consumed experiment, runner, ranker, policy-input, or production modules are imported without explicitly importing this capability
- **THEN** the hierarchical objective module is not loaded as a side effect
