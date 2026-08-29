# Combat RL Action-Relative Successor Delta Ablation Specification

## Purpose

Define source-bound first-successor corpus collection, real-context support
gating, and a development-only paired representation ablation for action-relative
combat decisions.

## Requirements

### Requirement: Source-bound successor evidence registration

The system SHALL bind the exact source commit, runner sources, native module,
simulator-only r16 parent, items export, r14/r15 real replay target, corpus
schema, seed partitions, battle indices, retention limit, resource limits,
output paths, fixed fit recipe, decision gates, and development-only authority
before collecting formal successor evidence.

#### Scenario: Registration matches every bound input
- **WHEN** every registered path, hash, source, schema, cohort, recipe, limit,
  and authority field matches
- **THEN** the runner may load the registered native module and begin the
  development-only corpus collection

#### Scenario: Registration or native identity differs
- **WHEN** any registered source, path, hash, schema, cohort, recipe, limit, or
  authority field differs
- **THEN** execution stops before native loading, environment construction, or
  output publication

### Requirement: Deterministic paired first-successor corpus

The system SHALL collect fit seeds `275000..275767`, calibration seeds
`275768..276023`, and fresh seeds `277000..277255` at battle indices
`0,3,6,9,10`, retaining at most two source states per initialized profile and
recording one source state plus one pair for every complete supported candidate
relative to the canonical guard.

#### Scenario: Ordinary paired successors are captured
- **WHEN** guard and candidate first steps both produce supported mapped
  successors
- **THEN** the pair records stable source, guard, and candidate identities;
  both successor tensor inventories; both immediate rewards; both dispositions;
  both continuation returns; and target advantage

#### Scenario: A first step is terminal
- **WHEN** a guard or candidate first step terminates the combat
- **THEN** the pair records zero-filled successor tensors together with an
  explicit terminal disposition and outcome that distinguish it from an
  ordinary zero-valued successor

#### Scenario: A first successor is unsupported
- **WHEN** a guard or candidate first step has an excluded or unmappable
  disposition
- **THEN** the pair is excluded with a named reason and is not replaced by the
  source state or an unmarked zero successor

#### Scenario: Collection is repeated from identical inputs
- **WHEN** the same source-only smoke or formal registration is replayed in a
  clean output path for determinism verification
- **THEN** row identities, tensor hashes, metadata hashes, exclusion counts,
  and partition summaries match exactly

### Requirement: Strict partition and evidence isolation

The system SHALL keep fit, calibration, fresh evaluation, and source-only smoke
seeds disjoint, SHALL exclude smoke rows from formal evidence, and SHALL defer
fresh tensor and metadata access until both arms and thresholds are frozen.

#### Scenario: Formal partitions are valid
- **WHEN** the formal corpus is sealed
- **THEN** every row belongs to exactly one registered seed partition, all pair
  members share a source identity, and no smoke or foreign seed is present

#### Scenario: Fresh evidence is requested early
- **WHEN** either arm, either threshold, or the frozen-parent hash has not been
  finalized
- **THEN** the runner rejects fresh corpus loading and records no fresh policy
  metric

### Requirement: Real-context support before fitting

The system SHALL derive source-state context weights against the registered
fresh parent-only live guard-replacement opportunity target and SHALL apply the
unchanged coverage, effective sample size, maximum concentration, floor
coverage, weighted balance, legality, provenance, and seed-isolation gates
before constructing an optimizer.

#### Scenario: Aligned corpus support passes
- **WHEN** the merged fit, unchanged calibration, and merged fresh source states
  satisfy every unchanged context-support condition against the complete fresh
  live-opportunity target
- **THEN** the runner may derive pair and ranking weights and execute the
  existing registered paired control/successor fit exactly once

#### Scenario: Aligned corpus support fails
- **WHEN** any target sufficiency, coverage, concentration, balance, legality,
  provenance, or isolation condition fails
- **THEN** the experiment closes before optimizer construction, model fitting,
  calibration, fresh policy evaluation, additional gameplay, or tuning

### Requirement: Aligned target and fit registration

The system SHALL bind the immutable live target, merged successor corpora and
their support report, frozen r16 parent, fixed arm recipe, calibration rule,
deferred fresh evaluation, policy gates, resource limits, output paths, and
development-only authority before aligned support is evaluated.

#### Scenario: Every aligned input matches
- **WHEN** the target, corpora, parent, source, recipe, gate, resource, output,
  and authority hashes match the registration
- **THEN** the runner may evaluate support and conditionally execute the fixed
  paired fit without changing either arm

#### Scenario: Any aligned input differs
- **WHEN** a target row, corpus identity, parent byte, source, recipe, gate,
  resource, output, or authority field differs
- **THEN** execution stops before support evaluation or optimizer construction

### Requirement: One conditional paired execution

The system SHALL use identical context weights, source and pair rows, labels,
class/ranking samples, arm seeds, Adam `0.001`, 4,096 updates, calibration
procedure, and fresh rows for the current-state control and successor-delta arm.

#### Scenario: Aligned support passes
- **WHEN** the target and every unchanged support and integrity condition pass
- **THEN** both arms are fitted, frozen, calibrated, and evaluated once under
  the existing hard policy and descriptive paired-control decisions

#### Scenario: Fit or evaluation closes
- **WHEN** support fails or the conditional execution publishes a terminal
  decision
- **THEN** no additional target run, fit retry, seed substitution, threshold
  change, tuning, live candidate takeover, qualification, or promotion occurs

### Requirement: Fixed paired representation ablation

The system SHALL fit one current-state item-semantic control and one
successor-delta candidate on identical source rows, labels, context weights,
class and ranking samples, optimizer settings, update counts, loss recipe, and
random seeds while keeping the parent encoder frozen.

#### Scenario: Control arm inputs are constructed
- **WHEN** a supported candidate pair is prepared for the control arm
- **THEN** the input contains only the source latent and registered guard and
  candidate item semantics

#### Scenario: Successor arm inputs are constructed
- **WHEN** the same supported candidate pair is prepared for the successor arm
- **THEN** the input contains the complete control input plus frozen candidate
  successor latent minus frozen guard successor latent, immediate-reward
  difference, and explicit guard and candidate disposition/outcome features

#### Scenario: Fit recipe or row identity differs between arms
- **WHEN** labels, source rows, context weights, sample identities, Adam
  `0.001`, 4,096 updates, per-class count 128, ranking count 128, ranking
  coefficient `0.5`, random seeds, or frozen-parent bytes differ
- **THEN** neither arm is eligible for fresh evaluation

### Requirement: Weighted calibration and deferred fresh evaluation

The system SHALL calibrate each arm on only the registered calibration seeds
using the weighted higher 95th-percentile non-beneficial evidence rule and
SHALL evaluate both frozen arms once on the same registered fresh rows.

#### Scenario: Both thresholds are frozen
- **WHEN** both fits complete with finite outputs and unchanged parent bytes
- **THEN** each arm derives its threshold from calibration only, publishes the
  threshold and calibration hash, and becomes eligible for deferred fresh
  loading

#### Scenario: Fresh paired evaluation runs
- **WHEN** both artifacts and thresholds are frozen and all support and
  integrity checks pass
- **THEN** the runner loads fresh evidence once and reports raw safety and
  real-context-weighted value metrics for both arms on identical row identities

### Requirement: Hard policy gate and descriptive signal decision

The system SHALL separate the successor arm's hard offline policy gate from
its descriptive improvement relative to the paired control.

#### Scenario: Successor arm hard-passes
- **WHEN** it has at least 30 raw interventions, weighted precision at least
  `0.65`, weighted mean selected advantage above `0.18881003558635712`,
  weighted regret below `3.1811342239379883`, zero raw severe selections, zero
  illegal selections, zero forbidden selections, and all integrity checks pass
- **THEN** the result permits only a separately proposed and registered fresh
  matched LightSTS policy gate

#### Scenario: Only the secondary signal passes
- **WHEN** the hard gate fails but successor weighted precision and weighted
  mean selected advantage each exceed control by at least `0.10`, and successor
  raw severe-harm rate is at most half the control rate
- **THEN** the report records descriptive successor representation evidence
  without policy execution, gameplay, training, qualification, promotion, or
  production-loading authority

#### Scenario: Neither decision passes
- **WHEN** the successor arm fails the hard gate and the secondary signal
  conditions
- **THEN** the representation recipe closes without a retry, threshold change,
  seed substitution, LightSTS policy gate, or production authority

### Requirement: Immutable publication and bounded corrective successor

The system SHALL atomically publish corpus and model manifests, source and
input hashes, split and row identities, tensor inventories, exclusion counts,
support evidence, frozen-parent checks, sampling-plan hashes, arm artifacts,
thresholds, fresh metrics, and the authority decision.

#### Scenario: Execution completes
- **WHEN** the registered collection and paired fit finish with valid
  roundtrips and reports
- **THEN** immutable artifacts are published with development-only authority
  and the execution ID cannot be reused

#### Scenario: Execution fails before fresh policy metrics
- **WHEN** a started execution fails deterministically and a committed failure
  report proves no fresh policy metric was accessed or published
- **THEN** at most one new corrective successor may bind that report and a
  source-only implementation fix while preserving every cohort, evidence,
  recipe, threshold, gate, and authority field

#### Scenario: Corrective successor is ineligible
- **WHEN** any fresh policy metric was accessed, a bound experiment field would
  change, the failure report is absent, or one corrective successor has already
  started
- **THEN** no successor execution is permitted under this change

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
