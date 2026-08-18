# combat-rl-parent-policy-anchor Specification

## Purpose
TBD - created by archiving change add-combat-rl-parent-policy-anchor. Update Purpose after archive.
## Requirements
### Requirement: Optional parent policy anchor
The system SHALL support an optional non-negative parent policy anchor weight for RL v2 training continuations. A zero weight SHALL preserve existing training behavior without allocating or evaluating an anchor network.

#### Scenario: Anchor disabled
- **WHEN** RL v2 training starts with parent policy anchor weight `0.0`
- **THEN** the trainer uses only its existing TD loss and saves no frozen anchor state

#### Scenario: Invalid anchor configuration
- **WHEN** a positive parent policy anchor weight is requested outside RL v2 checkpoint continuation training
- **THEN** startup fails before gameplay with an actionable validation error

### Requirement: Frozen mask-aware parent policy loss
The system SHALL freeze the starting checkpoint's online policy and add a weighted policy-distillation loss to each eligible TD update. The parent label SHALL be its greedy action under the replay transition's stored action mask, and anchor parameters MUST NOT receive gradients or optimizer updates.

#### Scenario: Anchored training update
- **WHEN** a sampled transition has at least one valid stored action and the anchor weight is positive
- **THEN** the total loss equals TD loss plus the configured weight times masked parent-policy cross entropy

#### Scenario: Invalid actions remain excluded
- **WHEN** the frozen parent assigns its largest unmasked value to an action that is invalid in the stored mask
- **THEN** the anchor label is selected only from valid actions

### Requirement: Exact anchored checkpoint resume
The system SHALL persist the configured parent policy anchor weight and frozen anchor network state in anchored training checkpoints. A resumed anchored continuation SHALL restore the original frozen anchor rather than replacing it with the successor online policy.

#### Scenario: Resume anchored checkpoint
- **WHEN** an anchored training checkpoint is loaded with a positive anchor weight
- **THEN** the trainer restores the checkpoint's frozen anchor state and continues to keep it non-trainable

#### Scenario: Start from legacy unanchored parent
- **WHEN** a positive anchor weight loads an existing compatible training checkpoint without anchor state
- **THEN** the trainer freezes that checkpoint's online policy as the initial anchor

### Requirement: Evidence-gated use
The system SHALL log and report TD loss, anchor loss, and active anchor weight separately. An anchored checkpoint SHALL NOT be promoted from replay metrics or training-cohort outcomes alone.

#### Scenario: Bounded anchored smoke
- **WHEN** an anchored training smoke completes
- **THEN** its report includes finite checkpoint status, TD fit, anchor loss, parent greedy agreement, and an explicit fresh matched live-gate decision

