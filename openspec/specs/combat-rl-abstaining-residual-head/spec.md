# combat-rl-abstaining-residual-head Specification

## Purpose

Define frozen-parent combat RL correction-head construction, abstaining
inference, residual-only mechanism training, artifact identity, and fresh
evidence authority.

## Requirements

### Requirement: Frozen-parent abstaining adapter
The experiment SHALL compose an immutable parent DQN with a zero-initialized,
low-capacity correction head. The correction head MUST use only information
available before the wrapper processes the proposal, and a closed gate MUST
return the exact frozen-parent Q values and greedy legal action.

#### Scenario: Adapter enters at parent equivalence
- **WHEN** an adapter is constructed from a bound parent state dictionary
- **THEN** every legal probe action and Q value matches the parent exactly and every parent parameter is frozen

#### Scenario: Gate abstains
- **WHEN** correction confidence is below the fixed threshold
- **THEN** the adapter returns the exact parent proposal without applying a residual

#### Scenario: Gate opens
- **WHEN** correction confidence reaches the fixed threshold
- **THEN** the adapter applies only finite bounded residuals and still masks every illegal action

### Requirement: Residual-only deterministic training mechanism
The mechanism runner SHALL optimize only correction-head parameters with fixed
seeds and settings. It MUST train abstention from direct rows and correction
from changed-proposal candidate-decision spans without sampling no-proposal or
unknown rows independently.

#### Scenario: Synthetic mechanism smoke completes
- **WHEN** deterministic separable direct and changed spans are supplied
- **THEN** both gate classes are exercised, at least one bounded correction is callable, parent bytes remain exact, and repeated runs publish identical correction state

#### Scenario: Frozen parent receives a gradient or changes
- **WHEN** any parent parameter has a gradient, changes bytes, or enters the optimizer
- **THEN** the mechanism fails before publishing a final artifact

### Requirement: Restorable non-production artifact
The experiment SHALL bind parent identity, adapter configuration, correction
state, optimizer state, seed, update count, and mechanism telemetry in a
restorable artifact marked non-production-compatible.

#### Scenario: Artifact round trips
- **WHEN** a published mechanism artifact is restored against the bound parent
- **THEN** gate probabilities, corrected Q values, greedy actions, correction parameters, and optimizer state match exactly

#### Scenario: Production loading is attempted
- **WHEN** the experiment artifact is supplied to an existing production DQN loader
- **THEN** loading is rejected without changing production checkpoint discovery or r16

### Requirement: Fresh evidence boundary
The system MUST keep the failed R1 corpus closed to alternate fitting. Any
policy-bearing residual fit SHALL require a separately registered fresh
callability-complete cohort and SHALL retain the existing technical and policy
stability gates.

#### Scenario: Closed corpus is supplied for residual fitting
- **WHEN** the failed R1 replay is requested as optimizer input
- **THEN** fitting is rejected before an optimizer update

#### Scenario: Mechanism smoke passes
- **WHEN** every synthetic mechanism invariant passes
- **THEN** the result authorizes only creation of a separate fresh-cohort registration and grants no gameplay, policy-quality, qualification, promotion, or production authority

### Requirement: Registered residual development fit
The system SHALL fit the abstaining residual adapter only from the immutable
qualified fresh replay, exact frozen-parent checkpoint, exact collection
report, and preregistered fixed recipe. It MUST execute exactly the registered
balanced update schedule on CPU and MUST optimize only correction-head
parameters.

#### Scenario: Bound development input is valid
- **WHEN** the checkpoint, collection report, runner binding, source hashes, replay invariants, fixed recipe, and both candidate-callable strata match the registration
- **THEN** the runner performs exactly 128 updates with 32 direct and 32 changed-proposal spans per batch using the registered SMDP targets and seeds

#### Scenario: Bound input or recipe differs
- **WHEN** any input identity, source binding, recipe field, threshold, seed, cohort, callability invariant, or candidate stratum differs
- **THEN** the runner fails before an optimizer update and publishes no final adapter artifact

### Requirement: Partitioned residual evidence
The system SHALL report parent and hard-gated adapter SMDP TD loss, action
disagreement, executed-label agreement, gate-open share, and positive-energy
End Turn behavior for training and validation partitions and for direct and
changed-proposal validation strata. It MUST also prove finite objectives,
immutable parent state, balanced callable batches, and exact serialization
round trip.

#### Scenario: Fixed fitting completes
- **WHEN** every registered optimizer update completes
- **THEN** the report binds all partitioned metrics, integrity checks, recipe identity, adapter hash, parent hash, span reconciliation, and development-only authority to the immutable inputs

#### Scenario: Parent or artifact integrity fails
- **WHEN** a parent parameter changes, enters the optimizer, receives a gradient, or the adapter fails exact round-trip restoration
- **THEN** the result is ineligible and no final development artifact is published

### Requirement: One-shot residual authority
The system MUST execute the source-bound fit at most once. A passing result
SHALL authorize only a separately registered fresh holdout, while a failed or
interrupted started attempt SHALL close the cohort without retry, tuning,
promotion, production loading, or policy-quality claims.

#### Scenario: Every fixed technical gate passes
- **WHEN** validation TD improves, material disagreement and direct stability gates pass, gate coverage gates pass, changed executed-label agreement improves, End Turn behavior is bounded, both validation strata are nonempty, and every integrity check passes
- **THEN** the immutable adapter is eligible only for a separately registered fresh holdout

#### Scenario: Any fixed technical gate fails
- **WHEN** one or more preregistered checks fail
- **THEN** production r16 remains authoritative and no alternate residual fit is run on the cohort
