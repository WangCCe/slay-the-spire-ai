# Combat LightSTS Replay Distribution Calibration Specification

## Purpose

Define a source-bound, descriptive comparison between complete real combat RL
replay and frozen-parent LightSTS replay without granting mechanics, training,
evaluation, or promotion authority.

## Requirements

### Requirement: Source-bound real replay validation
The calibration system SHALL load each registered real-game checkpoint through
the safe weights-only checkpoint API and MUST accept only complete schema-v1 or
schema-v2 snapshots while rejecting missing, hash-mismatched, truncated,
dimension-incompatible, other-schema, or internally inconsistent replay
snapshots before native loading or simulator collection. The schema-v2
executed-action anchor flag SHALL NOT affect descriptive calibration fields.

#### Scenario: Complete registered replay inputs
- **WHEN** every real checkpoint hash matches and its schema-v1 or schema-v2 replay snapshot is complete, untruncated, shape-valid, and action-valid
- **THEN** the system records each checkpoint identity and includes its chronological transitions in the real source corpus

#### Scenario: Invalid real replay input
- **WHEN** a checkpoint or replay binding is missing, hash-mismatched, truncated, malformed, outside schema-v1/v2, dimension-incompatible, or inconsistent
- **THEN** the system fails before native loading, simulator environment construction, or output publication

### Requirement: Frozen zero-update LightSTS collection
The calibration system SHALL collect the registered LightSTS corpus through the
existing combat bridge using the immutable simulator shadow of production r16,
guarded-parent behavior, epsilon zero, fixed fresh seeds and battle indices, and
zero optimizer updates.

#### Scenario: Registered collection executes
- **WHEN** all source and parent bindings validate and the native module exposes the expected adapter contract
- **THEN** the system collects only the bounded registered simulator profiles, verifies the parent parameter identity before and after collection, and records zero optimizer steps

#### Scenario: Collection identity drifts
- **WHEN** the module, simulator source, parent parameters, behavior configuration, seeds, battle indices, or action bounds differ from registration
- **THEN** the system rejects the run before environment construction without substituting a path, cohort, parent, or behavior policy

### Requirement: Canonical progression-stratified summaries
The calibration system SHALL recover the encoded floor using the RL-v2 state
contract, assign every transition to one fixed canonical floor stratum, and
publish source-local semantic, reward, terminal, action-family, action-mask, and
discrete-ID support summaries.

#### Scenario: Transition is summarized
- **WHEN** a validated real or simulator transition is accepted
- **THEN** it contributes exactly once to its floor stratum and to the registered player-state, monster-count, inventory-occupancy, legal-action, reward, terminal, executed-action, and ID-support summaries

#### Scenario: Encoded floor is invalid
- **WHEN** a transition has a non-finite floor feature or a value outside the RL-v2 encoded floor contract
- **THEN** the system fails instead of silently assigning an invalid stratum

### Requirement: Descriptive cross-source comparison
The calibration system SHALL compare only common strata meeting the registered
minimum count, SHALL publish numeric mean deltas and standardized mean
differences plus categorical total-variation and support-overlap measures, and
MUST keep degenerate variance and unsupported strata explicit.

#### Scenario: Common strata exist
- **WHEN** at least two floor strata contain the registered minimum number of real and simulator transitions
- **THEN** the system ranks numeric and categorical mismatch signals separately and reports all source counts used by each comparison

#### Scenario: Coverage is insufficient
- **WHEN** fewer than two strata meet the common-support requirement
- **THEN** the report is technically incomplete and grants no follow-up experiment authority

### Requirement: Deterministic bounded publication
The calibration system SHALL atomically publish canonical JSON, a concise
Markdown summary, and a manifest that binds source identities, operations,
configuration, exclusions, comparison limitations, and artifact hashes within
registered time and size bounds.

#### Scenario: Successful publication
- **WHEN** all input, collection, comparison, determinism, and output-bound checks pass
- **THEN** the report verdict is `replay_distribution_calibration_ready` while gameplay, training, evaluation, OPE, policy-quality, mechanics-equivalence, qualification, and promotion authority remain false

#### Scenario: Repeated in-memory analysis
- **WHEN** identical validated real and simulator transition inputs are analyzed twice
- **THEN** canonical report content excluding publication timestamps is byte-identical

#### Scenario: Publication failure
- **WHEN** an input, native, collection, comparison, determinism, or output-bound check fails
- **THEN** the system publishes no partial success report and does not retry, tune, train, or start gameplay
