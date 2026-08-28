## ADDED Requirements

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
