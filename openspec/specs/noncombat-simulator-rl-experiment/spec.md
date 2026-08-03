# noncombat-simulator-rl-experiment Specification

## Purpose

Define a provenance-bound, bounded, resumable simulator-only non-combat RL
experiment with isolated evaluation, fail-closed publication, and no live or
promotion authority.

## Requirements

### Requirement: Immutable Experiment Registration And Authorization
The system SHALL require a pushed preregistration that binds the exact source,
runtime, current API v3 adapter and physical simulator identities, formal
reward artifact, feature and algorithm contracts, cohorts, limits, support
blockers, expected outputs, and all-false authority before a separate execution
authorization can permit one logical experiment.

#### Scenario: Source-only registration is prepared
- **WHEN** implementation and verification pass without native loading,
  environment construction, seed rollout, or training
- **THEN** the registration SHALL bind their pushed commit and canonical bytes
- **AND** experiment execution, live use, formal RL, and promotion SHALL remain
  false

#### Scenario: One-shot execution is authorized
- **WHEN** a separately committed authorization matches the registration,
  pushed commit, absent output, exact preflight identities, and one unused
  logical execution id
- **THEN** only `experiment_execution` MAY become true for that logical run
- **AND** every live, OPE, qualification, formal-RL, and promotion authority
  SHALL remain false

#### Scenario: A registered identity or output boundary drifts
- **WHEN** any bound byte, value, cohort, runtime, native identity, output
  absence, authority flag, or execution id differs
- **THEN** execution SHALL stop before constructing an environment
- **AND** it SHALL NOT substitute another source, seed, path, or parameter

### Requirement: Fixed Candidate-Masked Training Contract
The experiment SHALL use the registered CPU-only linear candidate ranker,
API v3 feature projection, candidate-masked REINFORCE algorithm, Adam settings,
deterministic runtime, seed order, 64-episode chunks, four passes, and exactly
4,096 primary training episodes.

#### Scenario: A training chunk executes
- **WHEN** the next registered train coordinates and exact checkpoint state are
  valid
- **THEN** every selected action SHALL belong to the unique adapter-reported
  candidate set and one finite optimizer update SHALL consume that chunk
- **AND** no Current, Bottled, SimpleAgent, live, OPE, or terminal-label feature
  SHALL enter policy input or action selection

#### Scenario: Training input is illegal or non-finite
- **WHEN** candidates are empty or duplicate, an action is illegal, a source is
  mutated, or any probability, return, loss, gradient, optimizer, or model value
  is non-finite
- **THEN** the experiment SHALL terminate as blocked at the exact coordinate
- **AND** it SHALL NOT synthesize an action, skip an update, or retry the episode

### Requirement: Strict Victory-Primary Reward
The experiment SHALL compute scalar simulator reward as bounded nonnegative
floor advancement divided by 57 plus `2.0` only for terminal simulator victory,
with discount `1.0`, so one victory strictly dominates the maximum complete
episode shaping contribution.

#### Scenario: A transition advances without victory
- **WHEN** successor floor exceeds source floor and the successor is not a
  terminal victory
- **THEN** reward SHALL contain only capped floor progress in `[0, 1]`
- **AND** no reference label, resource heuristic, live outcome, or OPE value
  SHALL affect it

#### Scenario: A terminal victory occurs
- **WHEN** the simulator successor is terminal with outcome `player_victory`
- **THEN** reward SHALL add exactly `2.0` to bounded floor progress
- **AND** the registered strict-primary-dominance invariant SHALL hold

### Requirement: Deterministic Checkpoint And Resume
The experiment SHALL write a canonical hash-chained checkpoint after every
optimizer update and SHALL resume only the same logical execution from the
unique validated next coordinate under the cumulative wall-time bound.

#### Scenario: A checkpoint is published
- **WHEN** one training chunk commits successfully
- **THEN** canonical model, optimizer, random-generator, coordinate,
  registration, and implementation state SHALL be recorded in a deterministic
  state payload, while measured runtime and prior-checkpoint identity SHALL be
  recorded in its atomic envelope
- **AND** one canonical pending record SHALL make checkpoint, trajectory
  summary, and journal publication idempotently recoverable as one coordinate
- **AND** a partial or unchained checkpoint SHALL NOT replace the last valid one

#### Scenario: A process resumes after interruption
- **WHEN** the exact started journal, full checkpoint chain, source/runtime/native
  identities, output inventory, and unused single-process lease all validate
- **THEN** execution SHALL continue at the recorded next coordinate within the
  remaining cumulative 28,800-second budget
- **AND** it SHALL remain the original logical attempt rather than a retry

#### Scenario: Checkpoint-prefix replay is verified
- **WHEN** the registered independent replay executes the first two chunks from
  initialization
- **THEN** its second deterministic state payload SHALL match the primary
  checkpoint's state payload byte-for-byte
- **AND** measured wall time and the separate replay publication chain SHALL NOT
  enter the compared payload
- **AND** replay wall time SHALL be recorded outside that payload and restored
  across interruption before the next checkpoint
- **AND** a mismatch SHALL block canary and holdout evaluation

### Requirement: Conservative Episode Accounting
The experiment SHALL retain every selected train, canary, and holdout episode
in its registered denominator and SHALL treat only exact registered adapter
support blockers as non-victories at the last supported floor.

#### Scenario: A registered support blocker is reached
- **WHEN** an episode stops for one exact support-envelope reason listed in the
  registration
- **THEN** its seed, reason, last floor, non-victory, category coverage, and
  disposition SHALL remain in all applicable aggregates
- **AND** the episode SHALL NOT be dropped, replaced, or rerun

#### Scenario: An unregistered blocker is reached
- **WHEN** execution raises a reason not present in the closed support list
- **THEN** the complete experiment SHALL fail closed
- **AND** later cohorts SHALL remain untouched

### Requirement: Isolated Canary And Holdout Evaluation
The experiment SHALL bind disjoint train `50000..51023`, canary
`51024..51151`, and holdout `51152..51663` cohorts, and SHALL access holdout only
after the frozen initial and trained policies pass every registered canary gate.

#### Scenario: Canary passes
- **WHEN** both policies produce legal terminal rows with four-category
  coverage, unsupported policy-episode rate at most 10% across the 256 initial
  and trained canary episodes, trained victories not below initial, and a
  positive 95% paired floor-difference lower bound
- **THEN** the one fixed holdout MAY be accessed once for both frozen policies
- **AND** neither policy SHALL update from canary or holdout transitions

#### Scenario: Canary fails
- **WHEN** any structural, support, victory-noninferiority, or paired-floor gate
  fails
- **THEN** the verdict SHALL be `experiment_stopped_at_canary`
- **AND** every holdout seed SHALL remain untouched

#### Scenario: Holdout learning signal is evaluated
- **WHEN** all 512 paired holdout rows complete
- **THEN** `experiment_valid_with_learning_signal` SHALL require trained
  victories greater than initialization and a positive 95% paired terminal-floor
  lower bound
- **AND** any other valid result SHALL be
  `experiment_valid_without_learning_signal`

### Requirement: Atomic Publication And Independent Verification
The experiment SHALL atomically publish canonical configuration, append-only
journal, checkpoint chain, trajectory summaries, reached evaluation rows,
metrics, final model, report, and manifest, and a standalone verifier SHALL
validate them without native loading, PyTorch import, or training replay.

#### Scenario: Terminal publication verifies
- **WHEN** execution reaches a terminal verdict
- **THEN** the manifest SHALL bind every canonical artifact, registration,
  authorization, source identity, count, gate, and verdict by hash and size
- **AND** independent verification SHALL reproduce the classification and
  artifact inventory exactly

#### Scenario: Publication or verification fails
- **WHEN** an artifact is partial, missing, extra, inconsistent, noncanonical,
  or fails independent recomputation
- **THEN** no positive experiment verdict SHALL be published
- **AND** the last complete checkpoint and journal SHALL remain preserved

### Requirement: Experiment Has No Policy-Quality Or Live Authority
Every experiment verdict SHALL remain simulator-only and SHALL preserve the
formal readiness verdict, Current baseline blocker, target-supported outcome
blocker, and all live, OPE, qualification, loading, and promotion prohibitions.

#### Scenario: The learning signal gate passes
- **WHEN** the experiment publishes
  `experiment_valid_with_learning_signal`
- **THEN** the result SHALL mean only that the registered simulator experiment
  improved its frozen initialization under its simulator metrics
- **AND** it SHALL NOT establish Current superiority, live value, formal-RL
  readiness, causal uplift, or promotion eligibility

#### Scenario: The experiment is negative or blocked
- **WHEN** canary stops, learning signal is absent, a bound is reached, or
  execution blocks
- **THEN** the exact terminal result and untouched-cohort state SHALL be
  preserved
- **AND** no algorithm, model, reward, cohort, threshold, support ceiling, or
  resource retry SHALL occur under this change
