## ADDED Requirements

### Requirement: Immutable late-progression supplement

The system SHALL collect one native paired-return supplement from the bound
module, production-r16 simulator shadow, items export, source commit, runner,
seed partitions, battle indices, bounds, and unchanged branch-return recipe.

#### Scenario: Registered supplement executes

- **WHEN** every source and input identity matches and the output path is absent
- **THEN** training seeds `268000..269023` and evaluation seeds
  `270000..270511` execute with battle indices `10..14`, at most two retained
  states per profile, and no optimizer update

#### Scenario: Supplement binding differs

- **WHEN** any source, module, checkpoint, items, seed, battle-index, bound,
  return-recipe, or output binding differs
- **THEN** execution stops before native environment construction or output
  publication

### Requirement: Targeted floor filtering and compatible concatenation

The system SHALL retain supplement rows only at floors 23 through 34 and SHALL
concatenate them with the exact bound expanded-corpus partition while preserving
the existing tensor schema, row alignment, metadata, and source-component
identity.

#### Scenario: Eligible supplement rows are combined

- **WHEN** a complete paired-return supplement row has a canonical floor from
  23 through 34 and all tensor and metadata fields align
- **THEN** it appears exactly once in the corresponding combined partition and
  records its supplement source component

#### Scenario: Row is outside the target floors

- **WHEN** a complete supplement row has a floor below 23 or above 34
- **THEN** it is excluded from the combined partition and counted by floor and
  exclusion reason without changing the source artifact

#### Scenario: Corpus alignment is invalid

- **WHEN** a source corpus is hash-mismatched, malformed, class-incomplete,
  dimension-incompatible, action-invalid, or metadata-misaligned
- **THEN** concatenation fails without publishing a combined corpus

### Requirement: Deterministic real-context post-stratification

The system SHALL validate the bound complete r14 and r15 replay checkpoints,
assign real and simulator rows to exact cells of floor stratum, potion
occupancy, relic occupancy, and player-HP quartile, and derive deterministic
partition-local density-ratio weights.

#### Scenario: Shared context cell is weighted

- **WHEN** a simulator context cell is present in the real replay target
- **THEN** every row in that cell receives the same non-negative
  real-to-simulator density ratio and the normalized partition weights sum to
  one

#### Scenario: Simulator-only context cell is retained for audit

- **WHEN** a simulator context cell is absent from real replay
- **THEN** its rows remain in the immutable combined corpus, receive zero
  context weight, and contribute to unmatched-support counts

#### Scenario: Real replay target is invalid

- **WHEN** either replay checkpoint is missing, hash-mismatched, truncated,
  dimension-incompatible, internally inconsistent, or outside the accepted
  replay schemas
- **THEN** weighting stops before native loading or output publication

### Requirement: Context-support gate

The system SHALL evaluate the registered late-floor count, context-mass,
effective-sample-size, maximum-weight, weighted-SMD, legality, finiteness,
class, provenance, and seed-isolation gates independently for train and fresh
evaluation partitions.

#### Scenario: Support gates pass

- **WHEN** fresh evaluation contains at least 256 rows at floors 23..34, each
  partition covers at least 90% overall real context mass, at least 80% of
  floors 23..27 context mass, and at least 60% of floors 28..34 context mass,
  train ESS is at least 750, evaluation ESS is at least 400, maximum row weight
  is at most 1.5%, weighted absolute SMD is at most 0.20 for player HP, potion
  occupancy, and relic occupancy and at most 0.30 for floor ratio, and every
  alignment, legality, finiteness, class, provenance, and seed-isolation check
  passes
- **THEN** the decision is
  `corpus_support_ready_for_separate_weighted_fit`

#### Scenario: Any support gate fails

- **WHEN** one or more registered support conditions fail
- **THEN** the decision is
  `corpus_support_insufficient_close_without_fit` and no fitting, tuning,
  gameplay, qualification, or promotion starts

### Requirement: Atomic bounded publication and authority

The system SHALL publish canonical combined train and evaluation corpora,
partition-local context weights, a machine-readable support report, a concise
summary, source snapshots, and artifact hashes only after complete validation.

#### Scenario: Publication succeeds

- **WHEN** collection, filtering, concatenation, weighting, determinism,
  provenance, size, and time validations complete
- **THEN** the immutable output binds every input and operation while granting
  corpus-generation and descriptive support authority only

#### Scenario: Publication fails or execution is interrupted

- **WHEN** an exception, interruption, timeout, identity drift, partial output,
  or validation failure occurs
- **THEN** no success report or training authority is published and the bound
  existing expanded corpus remains unchanged

#### Scenario: A downstream fit is proposed

- **WHEN** the support decision passes
- **THEN** model fitting still requires a separate committed registration or
  OpenSpec change that binds the exact combined corpus and context-weight hashes
