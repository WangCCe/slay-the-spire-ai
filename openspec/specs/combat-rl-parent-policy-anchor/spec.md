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
The system SHALL freeze the starting checkpoint's online policy and add a weighted policy-distillation loss to each eligible TD update. By default, the anchor label SHALL be its greedy action under the replay transition's stored action mask. A transition explicitly marked to anchor to its executed action SHALL instead use that stored executed action, which MUST be valid under the stored action mask. Anchor parameters MUST NOT receive gradients or optimizer updates.

#### Scenario: Anchored training update
- **WHEN** a sampled transition has at least one valid stored action, no executed-action override, and the anchor weight is positive
- **THEN** the total loss equals TD loss plus the configured weight times masked frozen-parent-policy cross entropy

#### Scenario: Proxy-aware anchored training update
- **WHEN** a sampled transition has a valid executed-action override and the anchor weight is positive
- **THEN** parent-policy cross entropy uses the stored executed action as that row's label while other sampled rows retain their frozen-parent greedy labels

#### Scenario: Invalid actions remain excluded
- **WHEN** the frozen parent assigns its largest unmasked value to an action that is invalid in the stored mask
- **THEN** the default anchor label is selected only from valid actions

#### Scenario: Invalid executed-action override
- **WHEN** an executed-action override names an action that is invalid in the stored mask
- **THEN** the training update fails with an actionable invariant error before applying optimizer changes

### Requirement: Backward-compatible anchor override replay state
The RL v2 replay buffer SHALL persist an optional per-transition executed-action anchor override and SHALL preserve legacy replay behavior when the metadata is absent.

#### Scenario: Version 2 replay round trip
- **WHEN** replay containing both enabled and disabled anchor overrides is saved and loaded
- **THEN** each transition retains its original override value

#### Scenario: Version 1 replay load
- **WHEN** a legacy version 1 replay state without anchor override metadata is loaded
- **THEN** every restored transition has the override disabled

#### Scenario: Existing caller compatibility
- **WHEN** a caller stores a transition without specifying anchor override metadata
- **THEN** the replay buffer stores the override as disabled

### Requirement: Parent anchor override telemetry
The trainer SHALL expose the number of executed-action anchor overrides used by its latest training update separately from anchor loss and anchor weight.

#### Scenario: Mixed sampled batch
- **WHEN** an anchored training update samples both default and executed-action override rows
- **THEN** telemetry reports the count of sampled override rows used for anchor labels

#### Scenario: Anchor disabled
- **WHEN** parent anchor weight is zero
- **THEN** override usage telemetry is zero and no anchor network is evaluated

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
