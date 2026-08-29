## ADDED Requirements

### Requirement: Source-bound targeted context supplement

The system SHALL register a separate first-successor context supplement that
binds the immutable consumed r2 corpora and report, exact collector sources,
native module, simulator-only r16 parent, items export, r14/r15 real replay,
partition-specific cohorts, unchanged collection recipe, resource limits,
output paths, and development-only authority before native loading.

#### Scenario: Supplement registration is valid
- **WHEN** every source, input hash, predecessor identity, cohort, recipe,
  resource, output, and authority field matches and every formal seed is absent
  from the action-relative successor lineage's prior registrations and r2 rows
- **THEN** the runner may load the registered native module and begin only the
  bounded supplemental corpus collection

#### Scenario: Preflight differs or a seed collides
- **WHEN** any bound value differs or any formal seed is already registered
- **THEN** execution stops before native loading, environment construction, or
  started-receipt publication

### Requirement: Fresh-heavy partition-specific collection

The system SHALL collect train seeds `283000..283383` only at battle index `3`,
fresh seeds `284000..285023` only at battle index `3`, and fresh seeds
`286000..287535` only at battle index `10`, using the unchanged r2 collection
semantics and retaining at most two source states per initialized profile.

#### Scenario: A registered profile produces complete pairs
- **WHEN** a profile reaches a replaced guard action with complete supported
  guard and candidate first successors
- **THEN** the supplement records the same source tensors, pair tensors,
  dispositions, rewards, continuation returns, metadata, and exclusions as the
  r2 corpus schema

#### Scenario: A profile is outside its registered slice
- **WHEN** a seed or battle index is outside the exact partition-specific cohort
- **THEN** the runner rejects the profile rather than collecting or relabeling it

### Requirement: Deterministic complete-corpus merge

The system SHALL merge the train supplement into the immutable r2 fit corpus,
preserve r2 calibration exactly, and merge both fresh supplements into the
immutable r2 fresh corpus while offsetting every pair source-row reference and
preserving stable source order.

#### Scenario: Supplement corpora are merged
- **WHEN** every predecessor and supplemental corpus passes schema, identity,
  provenance, and seed-isolation validation
- **THEN** the merged fit, calibration, and fresh corpora pass the existing
  successor-corpus validator and serialize with stable identities

#### Scenario: A merge input or row reference differs
- **WHEN** an input hash, partition, tensor inventory, pair reference, row order,
  or seed inventory differs from the registration
- **THEN** publication fails without replacing any consumed or production
  artifact

### Requirement: Unchanged merged support gate

The system SHALL compute real-context weights over merged fit plus unchanged
calibration and merged fresh source states against the exact r14/r15 replay, and
SHALL apply every existing coverage, ESS, concentration, floor-coverage,
weighted-balance, legality, provenance, and seed-isolation condition unchanged.

#### Scenario: Merged support passes
- **WHEN** every unchanged support and integrity condition passes
- **THEN** the report marks the merged corpus eligible only for a separately
  registered weighted paired fit

#### Scenario: Merged support fails
- **WHEN** any unchanged support or integrity condition fails
- **THEN** the supplement closes before optimizer construction, calibration,
  fresh policy evaluation, tuning, gameplay, qualification, or promotion

### Requirement: Immutable bounded supplement publication

The system SHALL atomically publish the registration, preflight, started
receipt, merged corpora, partition and delta summaries, support evidence,
source and input hashes, provenance, manifest, and development-only authority
under one execution identity that is never overwritten.

#### Scenario: Collection completes
- **WHEN** all registered slices, merge checks, support checks, round trips,
  wall-time limits, and storage limits complete
- **THEN** the runner publishes one immutable output whose manifest binds every
  artifact and whose authority grants no gameplay, training, policy evaluation,
  qualification, promotion, CommunicationMod, or production loading

#### Scenario: An execution requires correction
- **WHEN** validation fails before a started receipt or an execution fails after
  the receipt
- **THEN** pre-start source may be corrected before registration, while any
  post-start correction requires a new identity that binds the predecessor and
  does not silently change the cohort, recipe, gates, or authority
