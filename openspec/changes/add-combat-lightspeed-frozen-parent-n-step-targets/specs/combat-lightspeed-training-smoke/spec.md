## ADDED Requirements

### Requirement: Frozen-parent bounded n-step replay targets
The system SHALL optionally transform complete simulator trajectories into
bounded n-step replay targets that bootstrap from the immutable initialized
simulator parent while preserving one-step TD as the default.

#### Scenario: Default target compatibility
- **WHEN** frozen-parent n-step targeting is not selected
- **THEN** the runner preserves the existing one-step TD and discounted complete-trajectory target behavior

#### Scenario: Nonterminal n-step target
- **WHEN** a complete contiguous trajectory has at least the configured positive horizon of rewards remaining before termination
- **THEN** the target equals the discounted reward sum over that horizon plus the correspondingly discounted maximum legal next-state Q value from the frozen initialized parent

#### Scenario: Terminal n-step target
- **WHEN** a complete contiguous trajectory terminates within the configured horizon
- **THEN** the target includes rewards only through termination and adds no parent bootstrap value

#### Scenario: Immutable parent bootstrap
- **WHEN** n-step bootstrap values are computed
- **THEN** the runner uses the exact initialized parent parameters in evaluation mode without gradients and completes target preparation before optimizer updates

#### Scenario: Invalid n-step corpus
- **WHEN** n-step mode receives an incomplete or noncontiguous trajectory, a non-positive horizon, an invalid parent identity, or a non-finite bootstrap value
- **THEN** the runner fails before replay insertion or model fitting and publishes no candidate

#### Scenario: N-step provenance
- **WHEN** an n-step report and simulator-only checkpoint are published
- **THEN** they bind the target mode, horizon, discount, parent parameter SHA-256, bootstrap count, target summaries, and source and transformed transition identities

#### Scenario: Production isolation
- **WHEN** n-step training completes successfully
- **THEN** it grants no production, gameplay, mechanics-equivalence, transfer, qualification, or promotion authority
