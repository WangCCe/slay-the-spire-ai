# noncombat-state-conditioned-ranker Specification

## Purpose

Define a versioned state-conditioned non-combat candidate scorer, strict tensor
and determinism boundaries, authority-free anti-collapse diagnostics, and
historical simulator-evidence isolation.

## Requirements

### Requirement: Versioned State-Conditioned Candidate Scoring
The system SHALL provide a versioned CPU-only candidate ranker that keeps one
state feature vector and the complete candidate feature matrix separate until
they are concatenated per candidate and passed through one affine hidden layer,
ReLU, and one scalar output layer.

#### Scenario: State-only change reverses candidate ordering
- **WHEN** two evaluations use byte-identical candidate feature rows and differ
  only in the shared state feature vector
- **THEN** a valid fixed model state SHALL be able to rank candidate A above B
  in one evaluation and B above A in the other
- **AND** the candidate set and model parameters SHALL remain unchanged

#### Scenario: Additive linear cancellation is rejected
- **WHEN** the versioned ranker boundary is inspected or constructed
- **THEN** it SHALL NOT reduce scoring to one affine function of
  `shared_state + candidate`
- **AND** changing shared state SHALL have a representable effect on relative
  candidate logits

### Requirement: Exact Tensor And Candidate Boundary
The ranker SHALL accept exactly one finite floating CPU state vector and one
nonempty finite floating CPU candidate matrix with matching feature widths,
and SHALL return one finite scalar score for every candidate row without
creating, dropping, masking, reordering, or silently casting candidates.

#### Scenario: Candidate order is permuted
- **WHEN** a caller permutes candidate rows while retaining the same state and
  model parameters
- **THEN** output scores SHALL be permuted in exactly the same way
- **AND** restoring candidate order SHALL restore byte-identical scores

#### Scenario: Tensor boundary is invalid
- **WHEN** state or candidate tensors have invalid rank, width, dtype, device,
  emptiness, or non-finite values
- **THEN** scoring SHALL fail before returning logits
- **AND** it SHALL NOT cast, repair, truncate, pad, or move the input implicitly

### Requirement: Deterministic Model Identity And Round Trip
The ranker SHALL expose a stable architecture id, input width, hidden width,
CPU device requirement, and ordinary deterministic state dict sufficient to
recreate identical scores under the same inputs.

#### Scenario: Scoring is repeated
- **WHEN** the same CPU model state, shared state vector, and candidate matrix
  are evaluated repeatedly
- **THEN** logits and greedy ordering SHALL be byte-identical

#### Scenario: State dict is restored
- **WHEN** a fresh matching ranker loads a copied state dict from another
  instance
- **THEN** both instances SHALL produce byte-identical logits for the same input
- **AND** an architecture-width mismatch SHALL fail closed

### Requirement: Deterministic Anti-Collapse Diagnostics
The system SHALL summarize complete normalized decision records by category and
candidate kind, including candidate opportunities, selected counts and rates,
distinct selected kinds, exact single-kind saturation, single-candidate rows,
and finite raw score-margin distributions.

#### Scenario: Card-reward selections saturate to take
- **WHEN** complete card-reward records contain both take and skip opportunities
  but every selected candidate kind is take
- **THEN** diagnostics SHALL report the take and skip opportunity counts, a take
  selection rate of `1.0`, zero skip selections, and exact single-kind
  saturation
- **AND** the summary SHALL NOT classify policy quality or authorize training

#### Scenario: Diagnostic order changes
- **WHEN** input decision rows or candidate records are permuted without
  changing their identities, selections, kinds, or action-id score mapping
- **THEN** the canonical diagnostic summary SHALL remain byte-identical

#### Scenario: Diagnostic record is incomplete
- **WHEN** a decision id is duplicated, candidates are empty or duplicate, the
  selected action is absent, kinds are empty, score keys differ from candidate
  ids, or a score is non-finite
- **THEN** diagnostics SHALL fail closed
- **AND** they SHALL NOT omit, synthesize, or repair a decision or candidate

### Requirement: Historical Isolation And No Authority
The new ranker and diagnostics SHALL remain development-only and SHALL leave
the source-bound r2 runner, verifier, linear model, artifacts, verdict, and all
production or live surfaces unchanged.

#### Scenario: Existing r2 evidence is verified
- **WHEN** the historical r2 independent verifier runs after this capability is
  added
- **THEN** its artifact inventory, checks, terminal verdict, and formal
  readiness verdict SHALL remain unchanged
- **AND** no r2-bound implementation file SHALL have changed

#### Scenario: Capability implementation completes
- **WHEN** the ranker, diagnostics, and regressions pass
- **THEN** experiment execution, new cohort access, training, replay, native
  loading, gameplay, CommunicationMod, model loading, formal RL, qualification,
  and promotion authority SHALL all remain false
