## ADDED Requirements

### Requirement: Residual training uses candidate-only environment access
The continuation SHALL collect exactly 64 candidate arm trajectories per chunk,
use native SimpleAgent for every non-card action, and apply the existing
candidate card objective without constructing a control environment.

#### Scenario: Candidate-only chunk completes
- **WHEN** 56 to 64 supported candidate trajectories complete for one registered chunk
- **THEN** the runtime fits the existing four-fold candidate baseline and applies exactly one candidate Adam step
- **AND** the chunk charges 64 environment accesses and zero control accesses

#### Scenario: Candidate-only support is incomplete
- **WHEN** a trajectory hits the declared Courier-restock blocker
- **THEN** that seed is censored and reported without a replacement seed
- **AND** more than eight censors, fewer than 56 supported trajectories, or any unknown blocker stops before an optimizer step

#### Scenario: Candidate-only ownership differs
- **WHEN** rollout policy terms do not belong to the exact candidate model and optimizer receiving the update
- **THEN** the runtime restores the complete chunk-entry checkpoint and publishes no partial checkpoint

### Requirement: Continuation identity and schedule are fixed
The experiment SHALL restore the exact r7 `checkpoint_004`, preserve its model,
Adam moments, and RNG state, and execute at most 16 additional chunks numbered
4 through 19 on the registered consumed development seeds.

#### Scenario: Continuation starts
- **WHEN** source, r7 registration, checkpoint, native module, corpus, and probe bindings all validate
- **THEN** the runner records the entry model and fixed-probe predictions before environment access
- **AND** the first eligible optimizer step is chunk 4

#### Scenario: Continuation binding differs
- **WHEN** any bound input, source file, checkpoint coordinate, schedule, or production-isolation value differs
- **THEN** the runner stops before native environment construction or seed access

### Requirement: Complete-boundary resume is deterministic
The runner SHALL publish a canonical checkpoint after every complete chunk and
MAY resume from the last complete boundary after process or host interruption.

#### Scenario: Process stops during a chunk
- **WHEN** no complete checkpoint was published for the in-progress chunk
- **THEN** resume restores the chunk-entry model, optimizer, counters, and RNG
- **AND** reruns only the same registered chunk without partial gradient reuse, seed replacement, or parameter changes

#### Scenario: Process stops after a chunk
- **WHEN** the chunk checkpoint and journal were published completely
- **THEN** resume starts at the next chunk without repeating completed environment access

### Requirement: Behavior sensitivity and terminal comparison gate progression
The runner SHALL evaluate the fixed 175-row probe after every update and SHALL
run one 64-seed frozen candidate-versus-native-control comparison only after all
16 additional updates complete without a safety stop.

#### Scenario: Behavior probe remains valid
- **WHEN** one update completes
- **THEN** the runner reports exact-action flips, family flips, take rate, model identity, and parameter L2 distance from the r7 entry checkpoint
- **AND** no probe label or metric changes an optimizer step or selects a checkpoint

#### Scenario: Proposal gate passes
- **WHEN** the terminal comparison has valid bounded support, candidate mean floor and victories are non-inferior to control, take coverage remains between 0.05 and 0.95 inclusive, and at least four fixed-probe exact actions differ from entry
- **THEN** the verdict is `ready_to_propose_fresh_card_only_evaluation`
- **AND** no fresh evaluation or policy loading starts under this change

#### Scenario: Proposal gate fails
- **WHEN** training stops early or any support, outcome, coverage, or behavior-change condition fails
- **THEN** the verdict is `card_only_behavior_sensitivity_not_ready`
- **AND** native SimpleAgent remains the rollback policy without tuning or another terminal run

### Requirement: Execution remains exploratory and isolated
The experiment SHALL use at most 1,152 environment accesses and eight charged
hours, and every artifact SHALL deny formal, fresh-evaluation, gameplay,
promotion, and production-loading authority.

#### Scenario: Experiment executes
- **WHEN** preflight and all source-only bindings pass
- **THEN** only the registered native simulator, consumed development seeds, and exploratory checkpoint directory are accessed
- **AND** CommunicationMod, game processes, protected cohorts, and production checkpoints remain unchanged
