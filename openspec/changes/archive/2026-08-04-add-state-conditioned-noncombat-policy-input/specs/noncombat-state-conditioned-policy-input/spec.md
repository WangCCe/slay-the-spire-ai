## ADDED Requirements

### Requirement: Exact API v3 inputs produce separate policy tensors
The system SHALL validate one non-terminal target decision through the existing
exact API v3 policy projection and SHALL produce one CPU float32 state tensor
and one CPU float32 candidate tensor matrix without adding the tensors together.

#### Scenario: Every target category is projected
- **WHEN** a valid route, shop, event, or card-reward snapshot and its complete legal candidate set are projected
- **THEN** the state tensor SHALL have shape `[hash_dim]` and the candidate matrix SHALL have shape `[candidate_count, hash_dim]`
- **AND** both tensors SHALL be finite CPU float32 values

#### Scenario: State alone changes
- **WHEN** two valid decisions have identical candidates and differ only in an allowed observable state value
- **THEN** their candidate matrices SHALL be exactly equal and their state tensors SHALL differ

#### Scenario: Candidates are reordered
- **WHEN** a valid candidate set is permuted without changing candidate content
- **THEN** the state tensor SHALL remain exactly equal and candidate rows SHALL follow only the same permutation

### Requirement: Projection is leakage controlled and fail closed
The system SHALL recursively remove the existing registered policy-leakage
fields, SHALL preserve source inputs byte-for-byte, and SHALL reject invalid,
terminal, unsupported, duplicate, empty, non-finite, or malformed decisions.

#### Scenario: Excluded fields change
- **WHEN** only outcome, reward, seed, teacher, baseline, terminal-result, or provenance fields change inside an otherwise valid input
- **THEN** the projected state and candidate tensors SHALL remain exactly equal

#### Scenario: Projection succeeds
- **WHEN** a valid snapshot and candidate set are projected repeatedly
- **THEN** every output tensor SHALL be exactly repeatable
- **AND** canonical source snapshot and candidate bytes SHALL remain unchanged

#### Scenario: Input is invalid
- **WHEN** the snapshot or candidate set violates exact API v3 validation or tensor-boundary requirements
- **THEN** projection SHALL fail before returning a partial policy input

### Requirement: Policy input identity is stable
The system SHALL expose stable metadata that binds the policy-input schema,
projection version, feature version, hash width, device, dtype, and
state-conditioned ranker architecture identity.

#### Scenario: Metadata is requested
- **WHEN** a caller requests policy-input metadata
- **THEN** the result SHALL be deterministic, JSON-compatible, and complete for every bound identity field
- **AND** it SHALL state that state and candidate channels are separate

### Requirement: Integrated ranking is state conditioned
The separate tensors SHALL be directly consumable by the versioned
`StateConditionedCandidateRanker` while preserving candidate-order equivariance.

#### Scenario: Only state changes candidate preference
- **WHEN** the same two candidates are projected under two valid observable states and scored by a fixed compatible ranker
- **THEN** the selected candidate ordering SHALL be able to reverse solely because the state tensor changed

#### Scenario: Candidate order changes
- **WHEN** projected candidates are permuted and scored under the same state
- **THEN** scores SHALL follow the same permutation without changing candidate identity or values

### Requirement: Scored decisions produce canonical diagnostics
The system SHALL validate and construct a canonical diagnostic row from one
decision ID, exact target category, legal candidates, finite score vector, and
selected candidate index.

#### Scenario: A valid scored decision is recorded
- **WHEN** every candidate has a unique action ID and kind, scores align with candidate order, and the selected index is valid
- **THEN** the row SHALL preserve exact action-score association and SHALL be accepted by the standard-library policy diagnostic summarizer

#### Scenario: Diagnostic inputs are inconsistent
- **WHEN** candidate identity, kind, score count, score finiteness, category, decision ID, or selected index is invalid
- **THEN** row construction SHALL fail without emitting a partial diagnostic row

### Requirement: Capability has no empirical or gameplay authority
The source-only capability SHALL NOT load native simulator or Communication Mod
modules, construct environments, access seeds, train or load a model, launch
gameplay, or authorize an experiment, policy-quality claim, formal RL,
qualification, or promotion.

#### Scenario: Source-only verification passes
- **WHEN** focused regressions, import isolation, the unchanged r2 verifier, the repository commit gate, and strict OpenSpec validation pass
- **THEN** the result SHALL establish only policy-input implementation capacity
- **AND** all experiment, gameplay, training, loading, formal-RL, qualification, and promotion authority SHALL remain false
