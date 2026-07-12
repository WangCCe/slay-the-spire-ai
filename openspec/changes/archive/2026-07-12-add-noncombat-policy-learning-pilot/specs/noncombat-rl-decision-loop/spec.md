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

### Requirement: Candidate Action Normalization
The system SHALL normalize candidate actions across shop, event, route, and card-reward decisions into a shared action shape. Every available candidate SHALL have a unique action id within its sample.

#### Scenario: Category candidates are normalized
- **WHEN** the exporter processes any supported non-combat category
- **THEN** each candidate action includes a stable action id, kind, label, availability flag, and raw source payload where available

#### Scenario: Selected action maps to a candidate
- **WHEN** the selected current-policy action is present unambiguously among normalized candidates
- **THEN** the sample records the selected action id and preserves the current-policy choice label

#### Scenario: Duplicate shop offers keep distinct identities
- **WHEN** a shop screen contains multiple offers with the same normalized item name
- **THEN** the exporter SHALL assign distinct stable action ids using the source inventory and slot identity
- **AND** a name-only Current or Bottled label that cannot distinguish those slots SHALL remain unmapped rather than selecting the first match

### Requirement: Conservative Live Outcome Join
The system SHALL attach live outcome data to decision samples only when the sample can be matched to exactly one reliable run record.

#### Scenario: Unique run match attaches outcome
- **WHEN** a sample trace timestamp can be matched to exactly one AI-marked `.run` record within the accepted run timestamp and playtime window
- **THEN** the sample records outcome fields including victory, floor reached, killed-by, playtime, and outcome join status `matched`

#### Scenario: Missing or ambiguous run match is explicit
- **WHEN** no reliable run match exists or multiple run records could match the sample
- **THEN** the sample records outcome join status `missing` or `ambiguous` and the evaluator excludes that sample from matched live-outcome diagnostics

### Requirement: Offline Evaluation And Export Evidence Gate
The system SHALL produce a deterministic offline report and export evidence-presence gate for non-combat policy-learning evidence. Passing this gate SHALL mean only that required audit fields are present; it SHALL NOT authorize policy promotion, formal non-combat RL, or causal outcome claims.

#### Scenario: Gate blocks incomplete export evidence
- **WHEN** state, action, reward-contract, or evaluation audit fields are missing tests or report coverage
- **THEN** the export evidence-presence gate reports `blocked` and lists the missing evidence areas

#### Scenario: Gate summarizes fresh eval evidence without promotion authority
- **WHEN** a bounded fresh eval has decision samples and matched live outcomes
- **THEN** the report includes sample counts by category, evidence quality, candidate coverage, Bottled agreement, repeated high-confidence gaps, and live outcome diagnostics
- **AND** it reports the export evidence-presence result separately from permanent formal-RL, OPE, and live-promotion boundaries

### Requirement: Non-Combat Reward Readiness Contract
The system SHALL define the reward-readiness contract needed before formal non-combat RL training can begin.

#### Scenario: Reward contract is reported
- **WHEN** the offline evaluator renders non-combat RL readiness
- **THEN** it reports the reward components, required outcome fields, exclusions, and unresolved reward gaps used by the training guard

#### Scenario: Missing reward contract blocks training
- **WHEN** reward components or required outcome fields are not defined or tested
- **THEN** the readiness report keeps formal non-combat RL training blocked by reward readiness

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

## RENAMED Requirements

- FROM: `### Requirement: Offline Evaluation And Promotion Gate`
- TO: `### Requirement: Offline Evaluation And Export Evidence Gate`
