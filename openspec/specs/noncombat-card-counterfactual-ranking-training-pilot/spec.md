# noncombat-card-counterfactual-ranking-training-pilot Specification

## Purpose

Define bounded consumed-seed card-policy training from action-level
counterfactual rankings and disjoint held-out readiness gates.

## Requirements

### Requirement: Disjoint consumed-seed counterfactual partitions
The pilot SHALL collect complete action-return rows from train seeds `1000..1015`
and holdout seeds `1016..1023`. It MUST evaluate at most two card-reward states
per seed, at most 128 train action branches, and at most 64 holdout action
branches, and MUST stop before a partial source state. Only the registered
Courier restock simulator blocker MAY censor a seed, with at most two train
censors and one holdout censor, no replacement, and minimum support of 24 train
and 12 holdout complete source states.

#### Scenario: Partition labels are collected
- **WHEN** a seed reaches an eligible card-reward source within its state and branch bounds
- **THEN** every legal action is continued under native SimpleAgent and the complete row is assigned only to that seed's fixed partition

#### Scenario: Next source exceeds a branch budget
- **WHEN** all legal actions at the next source would exceed the partition branch budget
- **THEN** collection stops before that source without replacing seeds or changing the split

#### Scenario: Registered Courier blocker occurs
- **WHEN** a fixed seed reaches the registered Courier restock simulator blocker within the partition censor limit
- **THEN** the seed is recorded as censored without replacement and only its previously complete source rows remain eligible

#### Scenario: Unknown or excessive blocker occurs
- **WHEN** a blocker is unregistered or the fixed partition censor limit is exceeded
- **THEN** the pilot fails before training

### Requirement: Isolated entry model and optimizer
The pilot SHALL restore the tracked r7 card-policy model from
`checkpoint_004.json`, SHALL create a new registered candidate-card Adam
optimizer, and MUST keep frozen non-card and control parameters unchanged. It
MUST NOT load or modify a production checkpoint.

#### Scenario: Training initializes
- **WHEN** the entry checkpoint and counterfactual support gates pass
- **THEN** the pilot starts a fresh optimizer over only candidate card-policy parameters

### Requirement: Fixed pairwise ranking objective
The pilot SHALL perform exactly 32 full-batch optimizer steps using train rows
only. For every unequal-return action pair it SHALL apply logistic pairwise loss
that ranks the better joint hierarchical action log probability above the worse,
weighted by absolute return margin. Equal-return pairs MUST contribute no loss.

#### Scenario: One training step runs
- **WHEN** the train partition contains valid unequal-return action pairs
- **THEN** one full-batch loss is computed without holdout rows and one candidate-card optimizer step is applied

### Requirement: Preregistered held-out promotion gate
The pilot SHALL compare entry and trained models on the fixed holdout partition.
It SHALL pass only if train loss decreases, held-out mean top-action regret
decreases, weighted pairwise accuracy increases, unique-best top-1 accuracy does
not decrease, maximum regret does not increase, and at least one entry-wrong
held-out greedy action changes to a return-best action.

#### Scenario: All held-out gates pass
- **WHEN** every fixed fit and holdout condition passes
- **THEN** the result authorizes only a later bounded evidence-expansion proposal and does not authorize fresh evaluation or policy promotion

#### Scenario: Any held-out gate fails
- **WHEN** any fixed condition fails
- **THEN** the pilot reports not ready, retains r7/native rollback, and forbids tuning or rerunning against the same holdout result

### Requirement: Experiment-only artifacts and isolation
The runner SHALL bind source, entry checkpoint, native bytes, CommunicationMod
configuration, and production checkpoint metadata before execution and compare
production bindings afterward. It SHALL publish the fitted checkpoint only
inside the experiment output and MUST keep fresh seed, gameplay, OPE,
qualification, promotion, and policy-quality authority false.

#### Scenario: Training completes in isolation
- **WHEN** the bounded run finishes and production bindings are unchanged
- **THEN** the report includes partition, fit, held-out, model-change, and false downstream-authority evidence

#### Scenario: Production isolation changes
- **WHEN** a production binding differs during the run
- **THEN** the runner fails and grants no downstream authority
