# combat-rl-inventory-embedding-successor Specification

## Purpose
TBD - created by archiving change add-combat-rl-inventory-embedding-successor. Update Purpose after archive.
## Requirements
### Requirement: Inventory-only candidate fitting
The system SHALL fit a deterministic combat RL development candidate while
allowing updates only to observed nonzero potion and relic embedding rows.

#### Scenario: Fixed parameter isolation
- **WHEN** a valid parent and corrected replay are fitted
- **THEN** card embeddings, dense layers, output layers, value and advantage streams, zero inventory rows, and unobserved inventory rows remain tensor-exact to the parent

### Requirement: Stored one-step target semantics
The system MUST compute training and assessment targets from each transition's
stored successor tensors and terminal flag without inferring continuity from
adjacent replay rows.

#### Scenario: Sanitized boundary corpus
- **WHEN** the input replay has an exact invalid boundary row removed
- **THEN** fitting does not bootstrap or accumulate return through the following array row

### Requirement: Deterministic combat-group development split
The system SHALL allocate complete terminal-delimited combat groups to training
and validation using a recorded deterministic seed.

#### Scenario: Repeated input allocation
- **WHEN** the same replay, split fraction, and seed are supplied twice
- **THEN** the training and validation transition indices are identical

### Requirement: Inventory-stratified development evidence
The system SHALL report parent and candidate one-step loss, greedy action
agreement, positive-energy End Turn behavior, parameter movement, and action
drift for the full validation set and inventory-relevant strata.

#### Scenario: Completed development run
- **WHEN** fitting and validation finish successfully
- **THEN** the report includes potion-present versus potion-absent metrics, relic-count strata, changed embedding rows, exact unchanged-tensor checks, and fixed gate outcomes

### Requirement: Isolated candidate authority
The system SHALL preserve the trained artifact and report in a run-scoped output
directory while granting no production, gameplay, qualification, or promotion
authority.

#### Scenario: Development gates pass
- **WHEN** all fixed loss, materiality, drift, End Turn, and isolation conditions pass
- **THEN** the decision permits only a separately registered fresh holdout against the frozen candidate hash

#### Scenario: Development gates fail
- **WHEN** any fixed condition fails
- **THEN** production r16 remains authoritative and the output is retained only for offline diagnosis without same-corpus tuning

### Requirement: Fail-closed input validation
The system MUST reject empty, incompatible, non-finite, training-mutated, or
unbound replay inputs before writing a final candidate checkpoint.

#### Scenario: Invalid replay provenance
- **WHEN** the replay metadata, transition count, optimizer state, or expected source hash violates the requested contract
- **THEN** the run stops with an error and does not overwrite an existing output

