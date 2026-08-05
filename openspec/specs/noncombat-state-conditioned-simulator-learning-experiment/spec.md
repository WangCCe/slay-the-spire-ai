# Non-Combat State-Conditioned Simulator Learning Experiment Specification

## Purpose

Define the immutable registration, state-conditioned simulator policy,
anti-collapse gates, isolated one-attempt lifecycle, canonical evidence, and
no-downstream-authority boundary for the bounded successor experiment.

## Requirements

### Requirement: Immutable Successor Registration And Separate Authorization
The experiment SHALL require a pushed registration that binds the additive
successor implementation, every imported source and historical evidence byte,
state-conditioned model and input metadata, formal reward, optimizer and
exploration contracts, deterministic fresh cohorts, gates, limits, native and
runtime identities, output inventory, and all-false downstream authority
before a separate tracked authorization can permit one logical execution.

#### Scenario: Source-only registration is complete
- **WHEN** every source, evidence, cohort, algorithm, gate, limit, runtime,
  native, output, and authority identity reproduces exactly from a clean pushed
  implementation commit
- **THEN** the registration SHALL publish canonical bytes without loading
  native code, constructing an environment, accessing an empirical seed, or
  training
- **AND** registration alone SHALL NOT authorize execution

#### Scenario: Exact execution is separately authorized
- **WHEN** a tracked authorization names the pushed registration hash, commit,
  command, logical identity, cohort, module, output, resource limit, and
  one-attempt rules and every pre-start condition matches
- **THEN** only that logical simulator execution SHALL be permitted
- **AND** gameplay, CommunicationMod, formal RL, OPE, qualification, policy
  loading, and promotion SHALL remain unauthorized

#### Scenario: A bound identity drifts
- **WHEN** any source, evidence, cohort, algorithm, gate, runtime, module,
  output, authority, or authorization value differs
- **THEN** validation SHALL fail before native loading, environment
  construction, seed access, or a started journal
- **AND** no alternate value SHALL be discovered, substituted, or repaired at
  runtime

### Requirement: Exact State-Conditioned Candidate Policy
The experiment SHALL project every nonterminal target decision through exact
API v3 into one separate finite CPU float32 state tensor and one complete
finite CPU float32 candidate matrix, then score the unchanged candidate rows
with the versioned state-conditioned MLP ranker.

#### Scenario: A target decision is scored
- **WHEN** a valid route, shop, event, or card-reward snapshot and complete
  candidate set are observed
- **THEN** the ranker SHALL receive the state and candidate tensors as separate
  channels and return one finite score per candidate in original order
- **AND** the selected action SHALL belong to the validated candidate set

#### Scenario: Policy input is invalid
- **WHEN** API version, state, candidate identity, candidate order, tensor
  shape, dtype, device, finiteness, legality, or leakage exclusion is invalid
- **THEN** the experiment SHALL fail closed before selecting or applying an
  action
- **AND** it SHALL NOT cast, repair, mask, synthesize, add, drop, or reorder a
  candidate

#### Scenario: State conditioning is audited
- **WHEN** a scored multi-candidate decision is recorded
- **THEN** the experiment SHALL record the finite relative-score effect of the
  registered state counterfactual on the same candidates
- **AND** source snapshots, candidates, and model parameters SHALL remain
  unchanged by the diagnostic

### Requirement: Frozen Initialization Is Only A Learning Control
The experiment SHALL create one deterministic seeded initial model and compare
its frozen greedy policy with the frozen terminal trained policy on identical
evaluation seeds without treating either as policy-quality truth.

#### Scenario: Paired evaluation begins
- **WHEN** canary or conditional holdout evaluation starts
- **THEN** initial and trained policies SHALL each receive fresh independent
  environments for every identical registered seed and SHALL perform no update
- **AND** model, optimizer, and random states SHALL remain unchanged throughout
  evaluation

#### Scenario: An auxiliary reference is available
- **WHEN** Current, SimpleAgent, Bottled, teacher, OPE, or live-policy output is
  present in a consumed source or diagnostic artifact
- **THEN** it SHALL NOT enter policy input, reward, action selection,
  initialization, optimization, or a pass gate
- **AND** it SHALL NOT replace the seeded initialization control

#### Scenario: Control-relative evidence is positive
- **WHEN** trained outcomes exceed initialization under a registered paired
  metric
- **THEN** the result SHALL describe only learning relative to that frozen
  experimental control
- **AND** it SHALL NOT establish a credible baseline floor, policy quality,
  formal-RL readiness, live value, or promotion eligibility

### Requirement: Victory-Primary Bounded Training
The experiment SHALL use candidate-masked CPU REINFORCE with fixed Adam,
normalized returns, entropy, gradient ceiling, seed order, chunking,
checkpointing, and a reward whose terminal-victory weight is strictly greater
than the maximum complete-episode floor-progress contribution.

#### Scenario: One training chunk executes
- **WHEN** the next registered coordinates and exact runtime state validate
- **THEN** every episode SHALL use only the registered train seed and policy
  randomness, every selected action SHALL be legal, and exactly one finite
  bounded optimizer update SHALL consume the chunk
- **AND** reward, entropy, gradient, model, optimizer, and random-state values
  SHALL remain finite and checkpointed

#### Scenario: Training reaches an invalid boundary
- **WHEN** reward, return, entropy, loss, gradient, parameter, optimizer,
  checkpoint, action, transition, mutation, deadline, or coordinate validation
  fails
- **THEN** the chunk SHALL roll back to its last complete checkpoint and the
  logical execution SHALL fail closed at the exact coordinate
- **AND** no episode, update, seed, parameter, or limit SHALL be skipped,
  replaced, retried, or extended

#### Scenario: Only floor reward is observed
- **WHEN** no training episode reaches terminal victory
- **THEN** the report SHALL state that optimization observed only simulator
  floor shaping
- **AND** no floor change SHALL be interpreted as victory learning

### Requirement: Deterministic Anti-Collapse Diagnostics
The experiment SHALL publish canonical train and evaluation diagnostics by
cohort and target category for candidate opportunities, selected kinds and
rates, multi-candidate decisions, score margins, exact saturation, and
state-conditioned relative-score effects.

#### Scenario: Alternatives are available but one action family saturates
- **WHEN** a registered card-reward or shop cohort contains the minimum
  alternative opportunities and the trained policy exceeds its fixed maximum
  selected-kind rate or selects no registered alternative kind
- **THEN** the anti-collapse gate SHALL fail
- **AND** a positive paired floor result SHALL NOT override that failure

#### Scenario: State has no empirical relative-score effect
- **WHEN** the registered multi-candidate sample has no finite relative-order
  change or minimum relative-score effect under the state counterfactual
- **THEN** the state-conditioning gate SHALL fail
- **AND** candidate-local scoring alone SHALL NOT authorize holdout access or a
  positive learning verdict

#### Scenario: A category exposes one action kind
- **WHEN** route or event candidate schemas provide no registered multi-kind
  opportunity
- **THEN** the report SHALL retain opportunity and score diagnostics without
  inventing a multi-kind selection requirement
- **AND** the category SHALL still satisfy legality, coverage, replay, and
  state-effect requirements

### Requirement: Fresh Isolated Cohorts And Canary Stop
The registration SHALL select disjoint train, canary, and holdout cohorts by a
tracked deterministic exclusion inventory, and the experiment SHALL complete
paired canary evaluation before accessing any holdout seed.

#### Scenario: Fresh cohorts are materialized
- **WHEN** the clean pushed implementation and current tracked inventory are
  used to prepare the registration
- **THEN** every cohort seed SHALL equal the fixed algorithm output and SHALL
  be absent from every historical, consumed, selected, reserved,
  compatibility, diagnostic, training, evaluation, and holdout identity
- **AND** no caller-supplied seed or runtime override SHALL be accepted

#### Scenario: Canary passes
- **WHEN** all paired canary rows are retained and replay-identical, both
  policies have legal complete rows, support failures remain within the fixed
  ceiling, all four categories are covered, trained victories do not decline,
  the paired floor gate is positive, and every anti-collapse and state-effect
  gate passes
- **THEN** the one registered holdout MAY be accessed for initial and trained
  frozen policies
- **AND** no observed canary value SHALL change source, model, algorithm,
  cohort, threshold, limit, or authority

#### Scenario: Canary is negative or blocked
- **WHEN** any structural, replay, support, coverage, victory-noninferiority,
  paired floor, anti-collapse, state-effect, resource, or publication gate
  fails
- **THEN** the experiment SHALL stop before holdout as negative or blocked
- **AND** every holdout seed SHALL remain unaccessed

### Requirement: Distinct Holdout Learning Verdicts
The experiment SHALL classify a complete holdout with separate structural,
behavior, paired floor, and victory signals and SHALL never let floor progress
substitute for a victory signal.

#### Scenario: Holdout has a victory signal
- **WHEN** every structural, replay, support, coverage, anti-collapse,
  state-effect, and paired floor gate passes and trained victories exceed
  initialization
- **THEN** the verdict SHALL be
  `experiment_valid_with_victory_signal`
- **AND** it SHALL remain simulator-only evidence

#### Scenario: Holdout has only a bounded floor signal
- **WHEN** every structural, replay, support, coverage, anti-collapse,
  state-effect, and paired floor gate passes but trained victories do not
  exceed initialization
- **THEN** the verdict SHALL be
  `experiment_valid_with_floor_only_signal`
- **AND** the result SHALL explicitly state that victory learning and policy
  quality were not demonstrated

#### Scenario: Holdout lacks a valid learning signal
- **WHEN** all holdout rows are structurally valid but a behavior, state-effect,
  paired floor, or victory-noninferiority gate fails
- **THEN** the verdict SHALL be
  `experiment_valid_without_learning_signal`
- **AND** no parameter, threshold, cohort, algorithm, or model retry SHALL be
  authorized

### Requirement: Canonical Lifecycle And No Downstream Authority
The experiment SHALL preserve one bounded logical execution with durable
checkpoints and journal, atomically publish a fixed canonical terminal
inventory, and support independent verification without native loading,
PyTorch import, environment construction, or replay.

#### Scenario: Execution has not started
- **WHEN** preparation or source-only verification runs before a started
  journal exists
- **THEN** it SHALL be repeatable without consuming the logical experiment
- **AND** it SHALL not load native code, construct an environment, access an
  empirical seed, train, or create empirical output

#### Scenario: Execution is active on Windows
- **WHEN** the started journal exists and the execution process is alive
- **THEN** monitoring SHALL inspect process liveness only and SHALL NOT read a
  file under the active output root
- **AND** artifact inspection SHALL wait until process exit

#### Scenario: Terminal publication verifies
- **WHEN** execution reaches canary stop, complete holdout, interruption,
  resource stop, structural block, or publication failure
- **THEN** the last complete journal, checkpoints, rows, diagnostics, metrics,
  report, model, and manifest SHALL be preserved and independently classified
- **AND** every formal-RL, gameplay, CommunicationMod, live, OPE, causal,
  qualification, policy-loading, production-checkpoint, and promotion
  authority SHALL remain false

#### Scenario: Publication or verification is invalid
- **WHEN** a canonical artifact is missing, extra, partial, inconsistent,
  noncanonical, or fails independent recomputation
- **THEN** no positive experiment verdict SHALL be valid
- **AND** the logical identity SHALL remain consumed without repair, retry,
  replacement, or reinterpretation
