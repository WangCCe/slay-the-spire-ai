## ADDED Requirements

### Requirement: Immutable fresh evaluation support supplement

The system SHALL collect one native paired-return evaluation supplement from
the bound module, production-r16 simulator shadow, items export, source commit,
fresh seed partition, battle indices, bounds, and unchanged branch-return
recipe without collecting new training rows.

#### Scenario: Registered fresh evaluation supplement executes

- **WHEN** every source and input identity matches and the output path is absent
- **THEN** evaluation seeds `271000..272023` execute with battle indices
  `0,3,6,9`, at most two retained states per profile, target floors `0..22`,
  and no optimizer update

#### Scenario: Supplement binding differs

- **WHEN** any source, module, checkpoint, items, prior corpus, replay target,
  seed, battle-index, bound, return-recipe, output, or authority binding differs
- **THEN** execution stops before native environment construction or output
  publication

### Requirement: Evaluation-only append and training preservation

The system SHALL retain fresh supplement rows only at floors 0 through 22,
append them to the exact bound combined evaluation corpus, and preserve the
bound combined training corpus byte-for-byte.

#### Scenario: Eligible evaluation rows are appended

- **WHEN** a complete fresh supplement row has a canonical floor from 0 through
  22 and all tensor and metadata fields align
- **THEN** it appears exactly once in the augmented evaluation partition and
  records its fresh-supplement source component

#### Scenario: Row is outside the target floors

- **WHEN** a complete fresh supplement row has a floor above 22
- **THEN** it is excluded from the augmented evaluation partition and counted
  by floor and exclusion reason without changing any source artifact

#### Scenario: Training preservation is checked

- **WHEN** the output publication is validated
- **THEN** its training corpus bytes and SHA-256 exactly match the bound prior
  combined training corpus

#### Scenario: Append compatibility is invalid

- **WHEN** a source corpus is hash-mismatched, malformed, class-incomplete,
  dimension-incompatible, action-invalid, metadata-misaligned, or contains a
  seed from another bound partition
- **THEN** augmentation fails without publishing a combined corpus

### Requirement: Unchanged support re-evaluation

The system SHALL recompute partition-local exact-cell weights against the bound
complete r14 and r15 replay target and SHALL apply the existing context-support
gate thresholds without modification.

#### Scenario: Every unchanged support gate passes

- **WHEN** the preserved training and augmented fresh evaluation partitions
  satisfy every existing late-row, context-mass, floor-mass, effective-sample-
  size, maximum-weight, weighted-SMD, legality, finiteness, class, provenance,
  and seed-isolation condition
- **THEN** the decision is
  `corpus_support_ready_for_separate_weighted_fit`

#### Scenario: Any unchanged support gate fails

- **WHEN** one or more existing support conditions fail
- **THEN** the decision is
  `corpus_support_insufficient_close_without_fit` and no fitting, tuning,
  gameplay, qualification, or promotion starts

### Requirement: Atomic evaluation-supplement publication and authority

The system SHALL publish the preserved training corpus, augmented evaluation
corpus, recomputed weights, missing-cell evidence, support report, source
snapshots, and artifact hashes only after complete validation.

#### Scenario: Publication succeeds

- **WHEN** collection, filtering, append, weighting, determinism, provenance,
  size, and time validations complete
- **THEN** the immutable output binds every input and operation while granting
  corpus-generation and descriptive support authority only

#### Scenario: Publication fails or execution is interrupted

- **WHEN** an exception, interruption, timeout, identity drift, partial output,
  or validation failure occurs
- **THEN** no success report or training authority is published and the bound
  prior balanced-corpus output remains unchanged

#### Scenario: A downstream fit is proposed

- **WHEN** the support decision passes
- **THEN** model fitting still requires a separate committed registration or
  OpenSpec change that binds the exact augmented corpus and context-weight
  hashes
