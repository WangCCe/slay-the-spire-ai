## ADDED Requirements

### Requirement: Complete-trajectory discounted-return targets
The system SHALL optionally train the simulator-only combat smoke from
deterministic discounted returns over supported complete source trajectories
while preserving one-step TD as the default target mode.

#### Scenario: Default target compatibility
- **WHEN** the discounted-return target is not selected
- **THEN** replay rewards, terminal flags, trainer inputs, and default report behavior remain one-step TD compatible

#### Scenario: Complete source trajectory
- **WHEN** complete-trajectory collection is enabled and a profile reaches a supported terminal outcome
- **THEN** the runner retains every accepted transition in source order with its seed, battle index, and decision index identity

#### Scenario: Incomplete source trajectory
- **WHEN** a profile reaches the decision bound or an unsupported state before a supported terminal outcome in complete-trajectory mode
- **THEN** the runner excludes the entire profile prefix, records its reason and transition count, and does not fabricate a terminal reward

#### Scenario: Discounted return transformation
- **WHEN** discounted-episode-return mode receives a complete trajectory
- **THEN** each replay target equals the backward discounted sum of source rewards from that transition through terminal and disables additional trainer bootstrapping for that row

#### Scenario: Matched source identity
- **WHEN** one-step and discounted-return arms are compared
- **THEN** their reports bind identical eligible source-transition identities and differ only in registered target transformation and fitted outcomes

#### Scenario: Target evidence
- **WHEN** a target-mode run completes
- **THEN** its report and simulator-only checkpoint bind target mode, discount, source and target reward summaries, eligible trajectory counts, exclusion counts and reasons, and source-transition identity

#### Scenario: Production isolation
- **WHEN** discounted-return training publishes a candidate
- **THEN** the candidate remains production-incompatible and grants no gameplay, transfer, qualification, promotion, mechanics-equivalence, or live policy-quality authority
