## ADDED Requirements

### Requirement: Reusable counterfactual feature datasets
The pilot SHALL encode complete source rows with source identity, candidates,
formal action returns, and CPU float32 state/candidate feature tensors in a
canonical round-trippable artifact. Reconstructed train `1000..1015` and
development `1016..1023` compact identities MUST match the completed full-model
r2 evidence before fitting.

#### Scenario: Dataset round trip succeeds
- **WHEN** a complete partition is encoded and restored
- **THEN** the canonical bytes and every source, candidate, return, and feature tensor are identical

#### Scenario: Prior compact identity differs
- **WHEN** reconstructed train or development evidence differs from the bound r2 compact identity
- **THEN** the pilot stops before optimizer construction

### Requirement: Scorer-weight-only fitting
The pilot SHALL restore the tracked r7 entry model and SHALL train exactly the
two `scorer.weight` tensors for 32 full-batch pairwise ranking steps with fresh
Adam state. All hidden tensors, both scorer biases, non-card parameters, control
parameters, and generators MUST remain byte-identical.

#### Scenario: Optimizer ownership is valid
- **WHEN** training starts
- **THEN** the optimizer owns exactly 128 scalar scorer-weight parameters and no other model state can receive gradients

#### Scenario: Frozen state changes
- **WHEN** any non-owned tensor or generator differs after fitting
- **THEN** the pilot fails and discards the experiment model

### Requirement: Development-before-audit access gate
The pilot SHALL evaluate the fitted scorer-weight model on exposed development
support before constructing any audit environment. Audit access SHALL occur only
if train loss decreases, development mean regret decreases, development weighted
pairwise accuracy increases, development unique-best accuracy does not decrease,
development maximum regret does not increase, and at least one wrong development
action changes to a best action.

#### Scenario: Development gate fails
- **WHEN** any fixed development condition fails
- **THEN** the runner terminates without accessing seeds `1024..1031`

#### Scenario: Development gate passes
- **WHEN** every fixed development condition passes
- **THEN** the runner may collect one bounded audit partition without further fitting

### Requirement: Independent consumed audit gate
The audit SHALL use only seeds `1024..1031`, at most two source states per seed,
at most 64 action branches, at most one registered Courier censor, and at least
12 complete source states. It SHALL pass only if mean regret and weighted
pairwise accuracy improve, unique-best accuracy and maximum regret do not
regress, and at least one wrong audit action changes to a best action.

#### Scenario: Audit passes
- **WHEN** all fixed audit support and metric gates pass
- **THEN** the result authorizes only a later fresh-evaluation proposal and does not authorize promotion

#### Scenario: Audit fails
- **WHEN** any fixed audit support or metric gate fails
- **THEN** the result reports not ready without rerunning, tuning, or additional model fitting

### Requirement: Experiment and production isolation
The runner SHALL keep datasets and the fitted model under the experiment output,
bind and compare production checkpoint and CommunicationMod metadata, and keep
gameplay, fresh evaluation, OPE, qualification, promotion, and policy-quality
authority false.

#### Scenario: Production isolation holds
- **WHEN** the staged run terminates
- **THEN** production bindings are unchanged and all downstream authority remains false
