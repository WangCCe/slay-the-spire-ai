## MODIFIED Requirements

### Requirement: Frozen-parent bounded n-step replay targets
The system SHALL optionally transform complete simulator trajectories into bounded n-step replay targets that bootstrap from the immutable initialized simulator parent through either the default raw-greedy action or an explicitly selected frozen-parent deployment-guard action while preserving one-step TD as the default.

#### Scenario: Default target compatibility
- **WHEN** frozen-parent n-step targeting is not selected
- **THEN** the runner preserves the existing one-step TD and discounted complete-trajectory target behavior

#### Scenario: Default raw-greedy bootstrap compatibility
- **WHEN** frozen-parent n-step targeting is selected without an explicit bootstrap policy mode
- **THEN** each nonterminal bootstrap value remains the maximum legal next-state Q value from the frozen initialized parent

#### Scenario: Guard-aware nonterminal n-step target
- **WHEN** a complete contiguous trajectory has at least the configured positive horizon of rewards remaining and frozen-parent deployment-guard bootstrap is selected
- **THEN** the target equals the discounted reward sum over that horizon plus the correspondingly discounted frozen-parent Q value gathered at the aligned legal guarded target-policy action for the bootstrap state

#### Scenario: Terminal n-step target
- **WHEN** a complete contiguous trajectory terminates within the configured horizon
- **THEN** the target includes rewards only through termination and adds no parent bootstrap value or action

#### Scenario: Immutable parent bootstrap
- **WHEN** n-step bootstrap values are computed in either bootstrap policy mode
- **THEN** the runner uses the exact initialized parent parameters in evaluation mode without gradients and completes target preparation before optimizer updates

#### Scenario: Invalid guard-aware bootstrap action
- **WHEN** an aligned nonterminal guarded bootstrap action is missing, duplicated, outside the action range, or illegal under the stored next-state action mask
- **THEN** the runner fails before replay insertion or model fitting and publishes no candidate

#### Scenario: Invalid n-step corpus
- **WHEN** n-step mode receives an incomplete or noncontiguous trajectory, a non-positive horizon, an invalid parent identity, or a non-finite bootstrap value
- **THEN** the runner fails before replay insertion or model fitting and publishes no candidate

#### Scenario: N-step provenance
- **WHEN** an n-step report and simulator-only checkpoint are published
- **THEN** they bind the target mode, bootstrap policy mode, horizon, discount, parent parameter SHA-256, bootstrap count, target summaries, source and transformed transition identities, and guard-aware action identity and Q-gap summaries when applicable

#### Scenario: Production isolation
- **WHEN** n-step training completes successfully
- **THEN** it grants no production, gameplay, mechanics-equivalence, transfer, qualification, or promotion authority

