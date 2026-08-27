## MODIFIED Requirements

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

## ADDED Requirements

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
