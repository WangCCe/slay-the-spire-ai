# Combat LightSTS Training Smoke Specification

## Purpose

Define a bounded, source-bound combat RL training smoke in LightSTS that proves the simulator transition, optimizer, checkpoint, and held-out evaluation path without granting live-game or production authority.
## Requirements
### Requirement: Source-only transition generation
The system SHALL generate bounded RL v2 combat transitions from fixed LightSTS `(seed, battle_index)` profiles using a deterministic network-independent behavior policy and explicit native reward definition.

#### Scenario: Supported successor
- **WHEN** a legal simulator action moves between two supported states
- **THEN** the runner stores the current observation, action, reward, next observation, terminal flag, and both legal-action masks in the existing replay contract

#### Scenario: Terminal successor
- **WHEN** a legal action ends the simulator combat
- **THEN** the runner stores a terminal transition with a classified outcome and no fabricated next-state features

#### Scenario: Unsupported successor
- **WHEN** a legal action reaches an unsupported native state
- **THEN** the runner excludes the pending transition, records the unsupported reason, and does not label the boundary terminal

#### Scenario: Naturally unreachable profile
- **WHEN** the declared native baseline loses or the run terminates before a requested positive battle index
- **THEN** the runner records a classified profile-coverage failure and does not create replay transitions or substitute another seed or battle

#### Scenario: Initialization integrity failure
- **WHEN** profile initialization fails for any reason other than classified baseline loss or run termination
- **THEN** the training smoke retains the evidence and reports a technical blocker

### Requirement: Disposable CPU training
The system SHALL fit either a fresh deterministic RL v2 network or an explicitly bound simulator-only parent network on CPU through the existing replay buffer and trainer without reading a production checkpoint.

#### Scenario: Fresh optimizer smoke succeeds
- **WHEN** no initial checkpoint is supplied and the registered transition cohort supplies enough accepted replay rows
- **THEN** training produces finite losses, at least one optimizer update, and a non-zero parameter delta from the initial network

#### Scenario: Warm-start optimizer smoke succeeds
- **WHEN** a valid simulator-only initial checkpoint is supplied and the registered transition cohort supplies enough accepted replay rows
- **THEN** the runner loads its online state into both trainer networks before transition collection and reports a non-zero post-training delta from that exact state

#### Scenario: Invalid warm-start checkpoint
- **WHEN** an initial checkpoint is production-compatible, has the wrong kind, omits its online state, or is structurally incompatible
- **THEN** the runner fails before collecting simulator transitions or publishing a candidate

#### Scenario: Simulator-only checkpoint
- **WHEN** the fitted candidate is saved
- **THEN** its metadata and path classify it as simulator-only, bind any parent checkpoint identity, and prevent it from satisfying production qualification or promotion inputs

### Requirement: Paired held-out simulator evaluation
The system SHALL evaluate the same deterministic initial policy before and after fitting on fixed `(seed, battle_index)` profiles disjoint from training, where the initial policy is either the seeded fresh network or the explicitly bound simulator-only parent.

#### Scenario: Evaluation completion
- **WHEN** both policies run on every reachable held-out profile within the decision bound
- **THEN** the report includes paired outcomes, player HP, decision counts, unsupported reasons, progression identities, and aggregate deltas

#### Scenario: Warm-start control identity
- **WHEN** training starts from a simulator-only parent checkpoint
- **THEN** the control evaluation uses the exact loaded parent parameters and the report binds their parameter hash

#### Scenario: Matching unreachable profile
- **WHEN** the baseline cannot reach a held-out profile identically for control and candidate evaluation
- **THEN** the report counts the classified profile-coverage failure and excludes that profile from paired policy metrics

#### Scenario: Initialization mismatch
- **WHEN** control and candidate differ on profile reachability or the classified failure reason
- **THEN** paired evaluation fails instead of attributing the difference to policy quality

#### Scenario: No uplift
- **WHEN** the fitted policy does not improve the held-out simulator metrics
- **THEN** the technical smoke may still complete, but the report SHALL not claim policy improvement or authorize a larger run without a separate decision

### Requirement: Production isolation
The training smoke SHALL not start the game, load or write production checkpoints, or grant mechanics-equivalence, transfer, qualification, promotion, or live policy-quality authority.

#### Scenario: Report authority
- **WHEN** a smoke report is published
- **THEN** simulator fitting authority is scoped to the registered run and all production, gameplay, transfer, qualification, and promotion authority flags are false

#### Scenario: Production import isolation
- **WHEN** the normal CommunicationMod agent imports
- **THEN** neither the LightSTS native module nor the simulator training runner is imported

### Requirement: Frozen parent-action constrained warm-start training
The system SHALL optionally add the existing masked parent-policy cross-entropy objective to simulator-only warm-start training while leaving its weight zero by default.

#### Scenario: Zero-weight compatibility
- **WHEN** parent-policy anchor weight is `0.0`
- **THEN** fresh and warm-start training preserve their existing initialization, optimization, evaluation, and checkpoint behavior without creating an anchor network

#### Scenario: Positive-weight initialization
- **WHEN** a finite positive parent-policy anchor weight and a valid simulator-only warm-start checkpoint are supplied
- **THEN** the runner freezes the exact loaded parent state as the trainer anchor before replay optimization and uses the same state for held-out control evaluation

#### Scenario: Positive weight without parent
- **WHEN** a positive parent-policy anchor weight is supplied without a valid warm-start checkpoint
- **THEN** the runner fails before transition collection or model fitting

#### Scenario: Constrained optimizer evidence
- **WHEN** positive-weight replay optimization completes
- **THEN** the report records the configured weight, frozen-anchor parameter hash, and separate finite total, TD, and positive anchor loss summaries

#### Scenario: Constrained successor checkpoint
- **WHEN** a constrained simulator candidate is saved
- **THEN** its source binding includes the parent checkpoint hash, parent parameter hash, and configured anchor weight while retaining false production compatibility and promotion authority

### Requirement: Optional battle-index stratified replay preparation
The system SHALL optionally prepare the simulator training replay so every configured battle-index stratum has equal transition representation while preserving default unstratified behavior.

#### Scenario: Source transition identity
- **WHEN** a transition is collected from a `(seed, battle_index)` profile
- **THEN** the runner retains the requested battle index as analysis metadata and reports source transition counts by stratum

#### Scenario: Default replay preparation
- **WHEN** battle-index stratification is disabled
- **THEN** every source transition is inserted exactly once, prepared counts equal source counts, and duplicate counts are zero

#### Scenario: Deterministic stratified preparation
- **WHEN** battle-index stratification is enabled and every configured stratum has at least one source transition
- **THEN** the runner retains every source transition once, deterministically repeats rows in smaller strata to the largest source-stratum count, interleaves strata, and binds the preparation seed

#### Scenario: Missing stratum
- **WHEN** a configured battle index has no source transitions in stratified mode
- **THEN** the runner fails before replay insertion or model fitting, identifies the missing stratum, and does not substitute another stratum

#### Scenario: Replay preparation evidence
- **WHEN** a training report is published
- **THEN** it records the preparation mode, source counts, prepared counts, duplicate counts, target count, and total inserted replay rows

#### Scenario: Production isolation
- **WHEN** stratified replay preparation is used
- **THEN** it remains confined to the simulator-only runner and grants no production, live transfer, qualification, or promotion authority

