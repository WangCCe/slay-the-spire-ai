## ADDED Requirements

### Requirement: Bound margin-controlled policy
The experiment SHALL restore the exact bound r7 checkpoint, freeze its existing
model parameters, divide both hierarchical base logits by fixed temperature
4.0, and add two zero-initialized bias-free residual projections.

#### Scenario: Scaled entry is constructed
- **WHEN** the bound r7 checkpoint is restored
- **THEN** full fixed-probe stage orderings and greedy actions match the unscaled policy and margins are divided by four

#### Scenario: Policy checkpoint is restored
- **WHEN** an experiment checkpoint is decoded
- **THEN** the base checkpoint, temperature, residual tensors, fresh optimizer, RNG, source, and schedule identities match exactly

### Requirement: Replay sensitivity gate
The experiment MUST pass one fixed lossless-replay mechanism gate before loading
the native simulator or accessing a training environment.

#### Scenario: Replay gate passes
- **WHEN** the compressed entry is finite and ordering-preserving and one residual-only update achieves mean joint total variation at least 0.00482559 without family collapse
- **THEN** bounded candidate-only training is permitted

#### Scenario: Replay gate fails
- **WHEN** any identity, gradient, movement, or coverage check is unmet
- **THEN** the experiment stops without environment access or alternate temperature

### Requirement: Bounded on-policy card training
The experiment SHALL train only the candidate residual card heads while
native SimpleAgent selects every non-card action on the fixed consumed schedule.

#### Scenario: Training chunk completes
- **WHEN** at least 56 of 64 trajectories are supported and all other invariants pass
- **THEN** exactly one candidate optimizer step and a restorable checkpoint are published

#### Scenario: Fixed training budget completes
- **WHEN** four complete chunks have executed
- **THEN** training stops and proceeds to the consumed-cohort terminal comparison

#### Scenario: Safety boundary fails
- **WHEN** coverage collapses, censor bounds fail, an unknown blocker occurs, or a checkpoint differs
- **THEN** the in-progress update is rolled back and training stops

### Requirement: Fixed terminal comparison
The experiment SHALL compare the frozen terminal candidate with native
SimpleAgent on the same consumed cohort under fixed support and behavior gates.

#### Scenario: Proposal gate passes
- **WHEN** all four chunks complete, at least two probe actions flip, floor and victories are noninferior, coverage remains valid, and support gates pass
- **THEN** only a separate fresh-evaluation proposal is authorized

#### Scenario: Proposal gate fails
- **WHEN** any terminal gate is unmet
- **THEN** native SimpleAgent remains the rollback and no further run is authorized

### Requirement: Offline isolation
The experiment MUST NOT access protected or fresh cohorts, launch gameplay or
CommunicationMod, load production checkpoints, tune, qualify, or promote.

#### Scenario: Experiment executes
- **WHEN** replay or training operations run
- **THEN** all artifacts remain outside production discovery and downstream authority remains false
