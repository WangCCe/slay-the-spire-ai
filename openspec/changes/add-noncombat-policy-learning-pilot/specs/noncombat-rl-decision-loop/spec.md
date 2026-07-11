## MODIFIED Requirements

### Requirement: Canonical Non-Combat Decision Samples
The system SHALL produce versioned, JSON-serializable decision samples for shop, event, route, and card-reward decisions. Policy-learning-capable samples SHALL also record a stable `trajectory_group_id`, `behavior_policy_id`, behavior-policy commit when known, `behavior_action_probability`, and an explicit probability status without fabricating missing provenance.

#### Scenario: Complete trace row becomes a trainable sample
- **WHEN** a decision trace row contains the selected action, screen context, player state, deck, relics, and category-specific options
- **THEN** the exporter records a sample with category, floor, act, state snapshot, candidate actions, current-policy label, Bottled-style reference label, evidence quality, and source metadata

#### Scenario: Partial trace row preserves limitations
- **WHEN** a decision trace row is missing context required for complete candidate actions or labels
- **THEN** the exporter still records the sample when possible and marks evidence quality and limitations so it is not treated as complete training evidence

#### Scenario: Unique run join supplies trajectory provenance
- **WHEN** a decision sample is matched to exactly one reliable AI run
- **THEN** the exporter records a stable trajectory group and behavior-policy provenance for grouped evaluation

#### Scenario: Unknown behavior probability remains unknown
- **WHEN** the exporter cannot prove the probability assigned to the selected action by the behavior policy
- **THEN** `behavior_action_probability` SHALL remain empty
- **AND** probability status SHALL be `unknown` rather than assuming zero, one, or a uniform distribution

### Requirement: Formal Non-Combat RL Training Guard
The system SHALL prevent formal non-combat RL training from being treated as ready until the decision loop is fully defined and verified. It SHALL allow a bounded offline supervised policy-learning pilot only when that pilot remains isolated from live gameplay, reward optimization, and policy promotion.

#### Scenario: Combat RL smoke remains allowed
- **WHEN** a developer runs a small combat RL smoke training or dry-run command
- **THEN** the report may use it as training-pipeline health evidence without marking formal non-combat RL training as ready

#### Scenario: Non-combat training remains blocked before readiness
- **WHEN** the state schema, action schema, reward definition, or evaluation gate lacks tests and report support
- **THEN** the system reports formal non-combat RL training as blocked

#### Scenario: Supervised pilot does not unlock formal RL
- **WHEN** an offline Current-imitation or Bottled-auxiliary pilot trains and evaluates successfully
- **THEN** the system SHALL continue to report formal non-combat RL and live-policy promotion as blocked
- **AND** the pilot result SHALL be treated only as training-pipeline and representation evidence
