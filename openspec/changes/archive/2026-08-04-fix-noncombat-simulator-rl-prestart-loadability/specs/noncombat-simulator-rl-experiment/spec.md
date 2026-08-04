## ADDED Requirements

### Requirement: Pre-Start Native Runtime Compatibility Boundary
The experiment runner SHALL load and validate the registered native adapter
before importing or initializing PyTorch, and SHALL complete native/Torch
compatibility validation before creating fresh experiment output or appending a
started journal record.

#### Scenario: Fresh pre-start validation passes
- **WHEN** source and controls pass, the registered native module loads from its
  declared DLL directories, post-load provenance matches, and the pristine CPU
  training runtime initializes
- **THEN** the runner MAY atomically create the registered output and append the
  first started record
- **AND** the validated native module and pristine runtime SHALL be used by that
  same process without importing Torch first or recreating the runtime

#### Scenario: Fresh pre-start validation fails
- **WHEN** native loading, post-load provenance validation, or pristine CPU
  runtime initialization fails before output initialization
- **THEN** the command SHALL fail closed while the registered output remains
  absent and no journal, checkpoint, trajectory, model, metrics, report, or
  manifest is published
- **AND** repeating the same pre-start validation under unchanged controls SHALL
  NOT count as retrying an experiment because no environment or seed was
  accessed and no started record exists

#### Scenario: Resume compatibility validation fails
- **WHEN** an existing nonterminal logical execution acquires its lease but
  native loading, provenance validation, or Torch-state restoration fails before
  the next rollout
- **THEN** the runner SHALL preserve the last complete journal, checkpoint, and
  trajectory inventory without appending a terminal record
- **AND** later continuation SHALL remain the same logical attempt and SHALL
  still require all registered identities and resume checks to pass

#### Scenario: Execution fails after start
- **WHEN** the started journal exists and rollout, checkpoint-prefix replay, or
  evaluation reaches a registered terminal or fail-closed error
- **THEN** the existing one-shot terminal publication and no-retry rules SHALL
  apply at the exact reached coordinate
- **AND** the pre-start boundary SHALL NOT authorize seed replacement, attempt
  replacement, tuning, extension, or reinterpretation

#### Scenario: Historical terminal evidence is verified
- **WHEN** the archived `noncombat-simulator-rl-20260804-r1` artifacts are
  inspected after this repair
- **THEN** their bytes, `experiment_blocked` verdict, zero episode count, and
  consumed logical execution identity SHALL remain unchanged
- **AND** this repair SHALL grant no successor execution, training, live,
  qualification, loading, or promotion authority
