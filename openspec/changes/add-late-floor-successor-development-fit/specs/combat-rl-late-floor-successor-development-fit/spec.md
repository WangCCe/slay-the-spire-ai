## ADDED Requirements

### Requirement: Source-bound late-floor development registration

The system SHALL bind the exact source commit, collector and fit sources,
immutable native module, frozen r16 parent, items export, predecessor corpora,
development live target, contamination inventory, fixed cohorts, recipe,
resource limits, output paths, and development-only authority before native
loading, collection, support evaluation, or fitting.

#### Scenario: Every collection input matches
- **WHEN** every source, binary, parent, input, target, cohort, recipe, limit,
  output, and authority field matches the committed registration
- **THEN** the collector may load the registered development dependencies and
  collect only the fixed late-floor cohorts

#### Scenario: A bound input differs
- **WHEN** any bound field, prior artifact hash, seed inventory, output path, or
  authority value differs
- **THEN** execution stops before native loading, environment construction,
  support evaluation, or optimizer construction

### Requirement: Fixed lineage-disjoint battle-index-10 acquisition

The system SHALL collect fit seeds `288000..290047`, calibration seeds
`290048..290559`, and fresh seeds `291000..292023` only at battle index 10,
using the unchanged first-successor collection semantics and retaining at most
two source states per initialized profile.

#### Scenario: A registered profile yields complete successors
- **WHEN** the parent guard is replaced and guard and candidate first
  successors are complete and supported
- **THEN** the collector records the existing source, pair, reward,
  disposition, continuation-return, metadata, and exclusion schema

#### Scenario: A profile is outside the fixed cohort
- **WHEN** a seed or battle index is outside its exact registered partition
- **THEN** the collector rejects it and does not substitute, extend, or search
  seeds based on observed context coverage

### Requirement: Deterministic merge and development support decision

The system SHALL append the new fit and calibration rows to their immutable
predecessor partitions, keep the new fresh partition separate, validate all
row references and seed isolation, and apply every existing context support
and integrity threshold unchanged against the sealed development target.

#### Scenario: Development support passes
- **WHEN** merged fit plus calibration and the new fresh context projection
  satisfy every unchanged support and integrity condition
- **THEN** the sealed corpus package is eligible only for the registered
  development paired fit

#### Scenario: Development support fails
- **WHEN** any coverage, concentration, balance, legality, provenance,
  isolation, or manifest condition fails
- **THEN** the experiment closes without more seeds, threshold changes,
  optimizer construction, gameplay, or tuning

### Requirement: Context-only fresh access before arm freezing

The system SHALL publish a canonical context-only projection for the new fresh
partition and SHALL prevent deserialization of the label-bearing fresh corpus
until both paired arms and their calibration thresholds are frozen.

#### Scenario: Support is evaluated before fitting
- **WHEN** the runner computes fresh context coverage for the pre-optimizer gate
- **THEN** it reads only the registered context projection and records that no
  fresh policy label or metric was accessed

#### Scenario: Fresh labels are requested early
- **WHEN** either arm or either calibration threshold is not frozen
- **THEN** the runner rejects fresh corpus loading and publishes no fresh policy
  metric

### Requirement: One fixed paired development fit

The system SHALL fit the current-state control and successor-delta arm once
with identical registered rows, context weights, labels, class and ranking
samples, arm seeds, Adam `0.001`, 4,096 updates, calibration procedure, and new
fresh evaluation rows while keeping the parent immutable.

#### Scenario: Registered support passes
- **WHEN** the sealed development support gate passes and all fit inputs match
- **THEN** both arms are fitted, frozen, calibrated, round-trip validated, and
  evaluated once on the new fresh partition

#### Scenario: The paired execution closes
- **WHEN** the runner publishes the hard-policy and descriptive paired-control
  decisions or encounters a terminal registered failure
- **THEN** no fit retry, seed substitution, threshold change, hyperparameter
  tuning, or model promotion occurs

### Requirement: Terminal development authority

The system SHALL label the live target, prior fresh corpus, new support result,
and paired model result as development-only and SHALL grant no gameplay,
candidate takeover, qualification, promotion, or production authority.

#### Scenario: Successor evidence is positive
- **WHEN** the successor arm passes the existing hard policy gate or the
  descriptive paired-control signal
- **THEN** the result permits only a separate OpenSpec proposal for independent
  real-game confirmation with run-cluster sufficiency

#### Scenario: Successor evidence is not positive
- **WHEN** neither existing successor decision passes
- **THEN** the successor-delta recipe closes without another development fit or
  confirmatory live collection
