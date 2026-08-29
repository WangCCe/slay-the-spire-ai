# combat-rl-real-context-weighted-action-relative-fit Specification

## Purpose
TBD - created by archiving change add-real-context-weighted-action-relative-fit. Update Purpose after archive.
## Requirements
### Requirement: Source-bound weighted-fit evidence

The system SHALL bind the exact support-passing train corpus, base fresh
evaluation corpus, formal fresh supplement, support-gate report, r14/r15 real
replays, simulator-only r16 parent, items export, runner source, and fixed
recipe before fitting.

#### Scenario: Every evidence binding matches
- **WHEN** all registered paths, hashes, schemas, row counts, support decision,
  source commit, and authority fields match
- **THEN** the runner may prepare the deterministic training split without
  native loading, gameplay, or fresh-evaluation access

#### Scenario: An evidence binding differs
- **WHEN** any registered input, source, schema, row count, support decision, or
  authority binding differs
- **THEN** execution stops before optimizer construction or output publication

### Requirement: Seed-isolated weighted training split

The system SHALL assign even source seeds from the bound training corpus to fit
and odd source seeds to calibration before candidate-pair expansion, and SHALL
derive partition-local exact-cell state weights against the same complete real
replay target.

#### Scenario: Deterministic split is valid
- **WHEN** the 8,313-row training corpus is split
- **THEN** fit contains 4,100 source rows, calibration contains 4,213 source
  rows, the seed sets are disjoint, and each partition has finite non-negative
  weights, real-context overlap, all three classes, and ranking support

#### Scenario: Split or context support is invalid
- **WHEN** a seed occurs in both partitions, a row is outside the parity split,
  a weight is invalid, context overlap is empty, or class/ranking support is
  incomplete
- **THEN** fitting stops before any optimizer update

### Requirement: Context-weighted fixed classifier fit

The system SHALL reuse the item-semantic three-class architecture, labels,
Adam `0.001`, 4,096 updates, 128 samples per class per update, 128 ranking pairs
per update, and ranking coefficient `0.5`, while changing only deterministic
sampling probabilities to the registered context weights.

#### Scenario: Classification pairs are weighted
- **WHEN** a fit state has positive context weight and one or more supported
  candidate pairs
- **THEN** each pair receives state weight divided by supported-pair count,
  weights normalize independently within each class, and seeded replacement
  sampling draws the fixed per-class count

#### Scenario: Ranking pairs are weighted
- **WHEN** a fit state has positive context weight and one or more supported
  beneficial-versus-nonbeneficial ranking pairs
- **THEN** each ranking pair receives state weight divided by that state's
  ranking-pair count, weights normalize globally, and seeded replacement
  sampling draws the fixed ranking count

#### Scenario: Fixed recipe or sampling integrity differs
- **WHEN** architecture, labels, optimizer, update budget, sample counts, loss,
  random seeds, normalized weights, or realized sample-plan hashes differ
- **THEN** execution fails without publishing a candidate artifact

### Requirement: Weighted higher negative calibration

The system SHALL calibrate only on odd-seed training rows using candidate-pair
context weights and the registered higher 95th-percentile rule.

#### Scenario: Weighted threshold is frozen
- **WHEN** fitting completes and calibration non-beneficial evidence is finite
- **THEN** non-beneficial weights are normalized, evidence is stably sorted,
  and the threshold is the first value whose cumulative weight reaches
  `min(1, ceil((n + 1) * 0.95) / n)` before fresh evaluation is loaded

#### Scenario: Calibration is invalid
- **WHEN** calibration accesses a fit or fresh row, has no non-beneficial mass,
  contains invalid weights or evidence, or uses another quantile rule
- **THEN** execution closes without fresh evaluation or artifact publication

### Requirement: Raw-safety and weighted-value fresh decision

The system SHALL load the complete 10,688-row augmented fresh partition only
after model weights and threshold are frozen, and SHALL publish both raw and
real-context-weighted metrics.

#### Scenario: Fresh offline gates pass
- **WHEN** raw interventions are at least 30; weighted intervention precision
  is at least `0.65`; weighted mean selected true advantage exceeds
  `0.18881003558635712`; weighted mean policy regret is below
  `3.1811342239379883`; raw severe, illegal, and forbidden selections are zero;
  and every integrity check passes
- **THEN** the decision permits only a separately registered fresh matched
  LightSTS policy gate

#### Scenario: A fresh offline gate fails
- **WHEN** any raw safety, weighted value, split, provenance, roundtrip,
  finiteness, or evaluation-isolation condition fails
- **THEN** the recipe closes without retry, parameter change, LightSTS policy
  execution, gameplay, qualification, or promotion

### Requirement: Immutable development artifact and bounded authority

The system SHALL publish the classifier, weighted threshold, input and source
bindings, split identities, state/pair/ranking weights, sample-plan hashes, raw
and weighted metrics, and decision atomically with development-only authority.

#### Scenario: Publication succeeds
- **WHEN** the single registered CPU fit and every artifact roundtrip and report
  validation complete
- **THEN** the output grants no gameplay, CommunicationMod, production
  checkpoint, qualification, promotion, or production-loading authority

#### Scenario: Started execution fails
- **WHEN** execution fails after the started receipt exists or completes with a
  failed policy decision
- **THEN** that execution ID is never retried with another seed, path, weight,
  threshold, update count, or parameter

#### Scenario: Execution fails before fresh policy metrics
- **WHEN** the first execution fails after its started receipt but a committed
  failure report proves that no fresh policy metric or output was produced
- **THEN** at most one new corrective successor ID may bind that report and a
  source-only implementation fix while preserving every evidence input,
  recipe, seed, weight, threshold, gate, and authority boundary

#### Scenario: Corrective successor is ineligible
- **WHEN** any fresh policy metric was computed, the predecessor failure report
  is missing, a bound experiment value changes, or one corrective successor has
  already started
- **THEN** no successor execution is permitted under this change

