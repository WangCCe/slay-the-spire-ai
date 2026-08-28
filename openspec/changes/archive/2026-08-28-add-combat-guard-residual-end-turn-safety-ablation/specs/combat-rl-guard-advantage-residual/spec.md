## MODIFIED Requirements

### Requirement: Post-guard abstaining residual

The system SHALL keep the parent frozen and fit a development-only residual
whose inputs include frozen parent features, the guarded baseline action, and
the legal action mask. The residual SHALL default to the guarded action unless
its fixed hard gate opens, and its selected alternative SHALL be legal. When a
registered action-safety constraint excludes an alternative, the residual MUST
apply that exclusion before selection and MUST preserve the exact guarded action
if no allowed alternative remains.

#### Scenario: Gate remains closed
- **WHEN** the residual gate probability is below the registered threshold
- **THEN** the selected action exactly preserves the guarded baseline action

#### Scenario: Gate opens
- **WHEN** the residual gate opens on a supported state with an allowed alternative
- **THEN** the system selects a legal canonical alternative and records guard action, residual action, score, advantage label, final action, and active action constraints

#### Scenario: EndTurn safety constraint applies
- **WHEN** the wasteful-EndTurn guard has replaced raw parent `EndTurn` and the registered residual policy excludes `EndTurn`
- **THEN** the residual action candidate mask excludes RL action 90 before selection and the final residual intervention cannot be `EndTurn`

#### Scenario: Safety constraint removes every alternative
- **WHEN** no distinct canonical residual alternative remains after registered action constraints
- **THEN** the policy executes the exact guarded action and records a safety abstention without opening an intervention

### Requirement: Fresh simulator policy gate

The system SHALL evaluate the frozen residual and guarded baseline on identical
fresh LightSTS seeds and profiles. A registered action-safety ablation SHALL
also evaluate the unrestricted and constrained residual on the same cohort. It
SHALL publish candidate-only and control-only victories, paired reward and
player-HP deltas, intervention count, action-constraint telemetry, support
exclusions, latency, and all fixed gate results for both paired contrasts.

#### Scenario: Candidate passes every policy condition
- **WHEN** candidate-only victories are at least control-only victories, mean reward and mean HP deltas are non-negative, no nonterminal profiles are excluded, at least one residual intervention occurs, the unrestricted arm expresses at least one constrained-action treatment opportunity, every registered action constraint is satisfied, and a constrained arm has no direct-ablation nonterminal exclusions and is non-regressive versus its unrestricted arm on matched-only wins, reward, and HP
- **THEN** the system may retain the recipe for a separately registered offline follow-up but SHALL NOT authorize gameplay, qualification, promotion, or production loading

#### Scenario: Candidate fails a policy condition
- **WHEN** any fixed control-relative, action-constraint, or direct-ablation policy condition fails
- **THEN** the system closes the recipe without a seed, horizon, threshold, architecture, optimizer, or additional action-constraint sweep and leaves production r16 unchanged
