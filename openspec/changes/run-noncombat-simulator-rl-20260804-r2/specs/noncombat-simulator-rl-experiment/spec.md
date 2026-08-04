## ADDED Requirements

### Requirement: Authorized R2 Logical Execution
The experiment runner SHALL execute at most one logical r2 attempt under the
user-approved pushed controls and SHALL preserve every existing simulator-only,
isolation, resource, evaluation, terminal, and authority boundary.

#### Scenario: R2 authorization is published
- **WHEN** registration SHA-256
  `8e0576bbf86b2334ccce67ac809410a02dcbfa6419f075211bbe48d0164f8549`
  is present at pushed commit `3bdd870d836b1f6a1dc3cb42dc0c2e0b57779eb4`
- **THEN** one canonical authorization SHALL bind logical identity
  `noncombat-simulator-rl-20260804-r2` and output
  `reports/noncombat_simulator_rl_experiment_20260804_r2`
- **AND** only experiment execution SHALL be true; all formal-RL, live, OPE,
  causal, qualification, loading, and promotion authority SHALL remain false

#### Scenario: Source-only preflight passes
- **WHEN** pushed controls, repaired source, Windows runtime, module bytes,
  physical simulator, absent output, free lease, process isolation,
  CommunicationMod configuration, and production checkpoints all match
- **THEN** a canonical preflight report SHALL authorize entry only into the
  registered native pre-start validation
- **AND** preflight SHALL import neither native nor Torch, construct no
  environment, access no seed, and start no training or gameplay

#### Scenario: Pre-start validation fails
- **WHEN** native loading, post-load provenance, or pristine CPU runtime
  initialization fails before output and the started journal exist
- **THEN** execution SHALL stop with r2 output absent and no registered seed
  accessed
- **AND** it SHALL NOT automatically retry, repair, substitute, tune, or create
  a replacement authorization

#### Scenario: R2 execution starts
- **WHEN** source-only preflight and native pre-start validation both pass
- **THEN** the runner SHALL create the registered output, append the started
  journal, and execute or resume only the same logical identity on CPU
- **AND** cumulative execution SHALL remain within `28,800` seconds and `5,504`
  total registered train, replay, canary, and conditional holdout episodes

#### Scenario: R2 reaches a terminal state
- **WHEN** training, prefix replay, canary, conditional holdout, publication, or
  a fail-closed error reaches a registered terminal boundary
- **THEN** the runner SHALL publish the exact canonical terminal artifact set
  and a fresh standard-library process SHALL verify it
- **AND** no retry, seed replacement, tuning, extension, live loading, gameplay,
  qualification, or promotion SHALL follow from that result

#### Scenario: Isolation is preserved
- **WHEN** authorization, preflight, execution, and closeout are compared
- **THEN** Slay the Spire and CommunicationMod SHALL remain unstarted and
  uncontacted, production checkpoints SHALL remain unloaded and byte-unchanged,
  and r1 evidence SHALL remain byte-unchanged
- **AND** every result SHALL preserve
  `not_ready_for_bounded_training_proposal` unless a separate future proposal
  closes the baseline and target-supported-outcome blockers
