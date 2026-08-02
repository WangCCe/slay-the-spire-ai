# noncombat-rl-decision-loop Specification

## Purpose
TBD - created by archiving change add-noncombat-rl-decision-loop. Update Purpose after archive.
## Requirements
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

### Requirement: Bottled Policy Oracle Adapter
The system SHALL provide an offline-only adapter that evaluates Ironclad non-combat decision samples against the local Bottled `REQUESTED_STRIKE` policy.

#### Scenario: Native Bottled oracle evaluates a supported sample
- **GIVEN** a complete shop, card-reward, event, or route decision sample
- **AND** a readable local Bottled checkout containing the `REQUESTED_STRIKE` strategy
- **WHEN** the Bottled oracle adapter evaluates the sample
- **THEN** it returns a reference label, confidence, concise reason, raw Bottled command or decision payload where available, source metadata, and limitations
- **AND** it does not launch Slay the Spire, CommunicationMod, or a live gameplay process

#### Scenario: Missing or incompatible Bottled context is explicit
- **GIVEN** a sample that cannot be represented faithfully for a Bottled handler
- **OR** the Bottled checkout is missing, unreadable, or incompatible
- **WHEN** the adapter evaluates the sample
- **THEN** it returns an `unsupported`, `partial`, or `error` oracle result with limitations
- **AND** it SHALL NOT emit a native high-confidence Bottled label for that sample

#### Scenario: Combat remains feasibility-only
- **GIVEN** a combat decision sample or combat trace row
- **WHEN** the Bottled oracle adapter is requested to inspect combat support
- **THEN** it reports feasibility and missing context
- **AND** it SHALL NOT replace the current combat policy or mark combat replacement as ready

### Requirement: Bottled Oracle Labels In Samples And Reports
The system SHALL include native Bottled oracle evidence in non-combat samples and current-vs-Bottled disagreement reports.

#### Scenario: Oracle label maps to a normalized candidate action
- **GIVEN** a native Bottled oracle result for a complete supported sample
- **AND** the oracle label or command corresponds to one of the normalized candidate actions
- **WHEN** the sample is exported or reported
- **THEN** the Bottled label includes the mapped candidate action id, oracle source mode, strategy name, Bottled repo path, Bottled commit when available, confidence, reason, and limitations

#### Scenario: Unmapped oracle label remains auditable
- **GIVEN** a native Bottled oracle result whose label or command cannot be mapped to a normalized candidate action
- **WHEN** the sample is exported or reported
- **THEN** the raw oracle label or command is preserved
- **AND** the candidate action id is left empty with an explicit limitation

#### Scenario: Disagreement report separates oracle modes
- **GIVEN** a report that includes native Bottled oracle rows and Bottled-style fallback rows
- **WHEN** current-vs-Bottled agreement and mismatch summaries are rendered
- **THEN** the report distinguishes native Bottled oracle evidence from fallback evidence
- **AND** repeated high-confidence repair candidates are ranked only when evidence quality, oracle mode, and outcome coverage justify them

### Requirement: Live Gameplay And Training Guards Remain Intact
The system SHALL keep Bottled oracle evaluation read-only and SHALL preserve existing live gameplay and formal non-combat RL training guards.

#### Scenario: Oracle execution does not alter live configuration
- **GIVEN** a developer runs the Bottled oracle adapter or non-combat report command
- **WHEN** the command completes successfully or fails
- **THEN** it SHALL NOT modify CommunicationMod `config.properties`, checkpoints, live agent code paths, or run launcher defaults

#### Scenario: Formal non-combat RL training remains blocked
- **GIVEN** Bottled oracle labels are present in samples and reports
- **WHEN** the non-combat RL readiness gate is evaluated
- **THEN** formal non-combat RL training remains blocked unless the existing state, action, reward, and evaluation readiness requirements are all satisfied by tests and reports

### Requirement: Verified Known-Propensity Evidence
The system SHALL accept behavior probabilities as evaluation evidence only when they come from a confirmed, replay-valid exploration record with an exact candidate distribution.

#### Scenario: Confirmed exploration sample supplies behavior probability
- **WHEN** a canonical non-combat sample joins to a confirmed exploration decision and the validator reproduces its state hash, candidate distribution, draw, selected action, and selected-action probability
- **THEN** the sample SHALL record the verified behavior policy and known selected-action probability
- **AND** it SHALL preserve the exact candidate probabilities and exploration provenance

#### Scenario: Unverified probability remains unsupported
- **WHEN** an exploration record is missing, shadow-only, rejected, unresolved, ambiguous, or not replay-valid
- **THEN** the sample SHALL NOT treat its selected-action probability as verified behavior evidence
- **AND** it SHALL retain an explicit unsupported reason instead of inferring a probability

### Requirement: Exploration Data Does Not Unlock Policy Claims
The system SHALL keep known-propensity data qualification separate from outcome-contract, target-policy, overlap, estimator-validation, OPE, causal outcome, formal non-combat RL, and live-promotion readiness.

#### Scenario: Exploration data gate passes
- **WHEN** `known_propensity_exploration_data_ready` is true
- **THEN** the readiness report SHALL route the qualified dataset through the versioned trajectory, outcome, target-policy, overlap, effective-sample-size, and estimator-validation gates
- **AND** it SHALL NOT report causal uplift or authorize OPE, formal non-combat RL, or live promotion solely from the exploration-data result

#### Scenario: OPE readiness audit remains separate
- **WHEN** an offline readiness audit reconstructs valid trajectory weights and passes its minimum overlap screens
- **THEN** it SHALL report outcome-contract, target-policy, overlap, identity, and estimator-validation readiness separately
- **AND** OPE readiness SHALL remain false until an independently specified estimator-validation gate is implemented and passes

#### Scenario: Bottled or pilot labels join exploration rows
- **WHEN** offline Current, Bottled, or pilot-model labels are attached to known-propensity exploration samples
- **THEN** those labels SHALL remain auxiliary policy comparisons until converted into a complete versioned target-policy distribution
- **AND** they SHALL NOT change the recorded behavior distribution or become reward truth

### Requirement: Simulator Transitions Remain Separate Evidence
The non-combat decision loop SHALL distinguish simulator-generated transitions from live trace samples, known-propensity exploration evidence, and matched `.run` outcomes.

#### Scenario: Simulator transition is exported
- **WHEN** the offline adapter exports a route, shop, event, or card-reward transition
- **THEN** the row SHALL use a separate versioned schema and `source_type=sts_lightspeed_simulation`
- **AND** it SHALL preserve simulator and baseline provenance without claiming a live outcome join

#### Scenario: Simulator data enters readiness reporting
- **WHEN** a readiness report includes simulator transition counts or returns
- **THEN** it SHALL report them in a separate evidence class
- **AND** they SHALL NOT increase live known-propensity coverage, live OPE overlap, target-supported victory counts, or promotion evidence

#### Scenario: Future training combines evidence classes
- **WHEN** a future proposal seeks to train on both live and simulator data
- **THEN** it MUST separately define dataset weighting, simulator-divergence controls, reward semantics, and real-game holdout evaluation
- **AND** the adapter POC alone SHALL NOT satisfy that approval gate
