## ADDED Requirements

### Requirement: Candidate identities form deterministic action families
The system SHALL accept a nonempty sequence of unique candidate action IDs and
nonempty candidate kinds aligned one-to-one with a finite rank-1 CPU float32
score tensor. It SHALL use each candidate kind as its action-family identity,
sort family metadata by kind, and preserve candidate outputs in input order.

#### Scenario: Valid candidates are grouped
- **WHEN** aligned legal candidates contain repeated kinds and unique action IDs
- **THEN** every candidate SHALL map to exactly one family and every family SHALL contain every aligned candidate of that kind
- **AND** grouping SHALL NOT mutate, merge, drop, or reorder source candidates

#### Scenario: Candidate boundary is invalid
- **WHEN** scores or candidates are empty, misaligned, malformed, non-finite, on a non-CPU device, not float32, or contain duplicate action IDs or empty kinds
- **THEN** distribution construction SHALL fail before returning a partial result

### Requirement: Family probability is max-pooled and hierarchically factorized
For candidate score `z_i`, the system SHALL define each family logit as the
maximum score in that family, apply softmax across family logits, apply a
separate softmax within each family, and define each candidate probability as
its family probability multiplied by its conditional probability.

#### Scenario: Equal scores have unequal family cardinality
- **WHEN** three candidates in one family and one candidate in another family all have the same finite score
- **THEN** each family SHALL receive probability `0.5`
- **AND** the three-candidate family SHALL divide its `0.5` mass equally among its candidates

#### Scenario: A same-family score is duplicated by a distinct action
- **WHEN** a distinct legal action is added to a family with a score equal to any existing member while all other scores and families remain unchanged
- **THEN** every family logit and family probability SHALL remain unchanged
- **AND** only the affected family's conditional candidate distribution MAY change

#### Scenario: Candidate order is permuted
- **WHEN** candidates and their aligned scores are permuted together
- **THEN** family order, logits, probabilities, and entropies SHALL remain equal
- **AND** candidate-level outputs SHALL follow exactly the same permutation by action identity

#### Scenario: Only one family is present
- **WHEN** every candidate has the same kind
- **THEN** that family SHALL receive probability `1`
- **AND** candidate probabilities SHALL equal an ordinary softmax over the original score vector

### Requirement: Probability and entropy outputs are complete and differentiable
The system SHALL expose finite family logits, family log probabilities, family
probabilities, conditional candidate log probabilities, joint candidate log
probabilities, joint candidate probabilities, family entropy, expected
conditional entropy, and joint entropy while preserving the score tensor's
autograd graph. Every exposed distribution tensor SHALL be finite CPU float64,
while the aligned score input remains CPU float32.

#### Scenario: A multi-family distribution is constructed
- **WHEN** valid finite scores and candidates are provided
- **THEN** family probabilities and candidate probabilities SHALL each sum to `1` within numerical tolerance
- **AND** joint entropy SHALL equal family entropy plus expected conditional entropy within numerical tolerance

#### Scenario: A selected candidate log probability is differentiated
- **WHEN** a caller differentiates one returned joint candidate log probability together with finite entropy terms
- **THEN** every produced score gradient SHALL be finite
- **AND** equal maximum scores SHALL receive permutation-equivariant tie gradients from family max pooling

#### Scenario: Opposite finite float32 limits are scored
- **WHEN** one valid decision contains finite scores at both float32 limits
- **THEN** every exposed distribution value and hierarchical log-probability sum SHALL remain finite and exact in float64
- **AND** differentiating a selected joint log probability SHALL preserve finite, nonzero score gradients wherever the mathematical derivative is nonzero

### Requirement: Metadata and design evidence are deterministic and authority-free
The system SHALL expose stable JSON-compatible metadata binding the schema,
max-pooling rule, family identity field, entropy decomposition, device, dtype,
and an exact all-false authority map. It SHALL publish a deterministic design
report that separates reproduced invariants, trade-offs, alternatives, open
questions, and prohibited empirical claims.

#### Scenario: Metadata and report are reproduced
- **WHEN** the same source and synthetic inputs are evaluated repeatedly
- **THEN** metadata and report content SHALL be byte-identical
- **AND** they SHALL state that no training coefficient, experiment, seed, model, or runtime integration was selected

#### Scenario: Source-only verification passes
- **WHEN** focused regressions, the repository test gate, and strict OpenSpec validation pass
- **THEN** the result SHALL establish only an additive distribution capability
- **AND** all experiment execution, seed access, native loading, training, gameplay, model loading, formal-RL, qualification, and promotion authority SHALL remain false
