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
