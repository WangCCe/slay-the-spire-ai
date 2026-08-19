## ADDED Requirements

### Requirement: Frozen-parent top-legal-action margin guard
The simulator trainer SHALL optionally preserve the frozen parent's clipped positive best-legal-action-versus-best-alternative Q margin on replay states.

#### Scenario: Eligible replay row
- **WHEN** at least two actions are legal and the frozen parent's top-two legal Q values have a finite positive margin
- **THEN** the guard computes a hinge loss requiring the candidate to preserve that best-action margin up to the registered cap

#### Scenario: Parent EndTurn is best
- **WHEN** EndTurn is the frozen parent's best legal action with a positive margin
- **THEN** the row remains eligible and the guard protects EndTurn against the candidate's strongest legal alternative

#### Scenario: Candidate ranking violation
- **WHEN** the candidate ranks another legal action above the frozen parent's best legal action on an eligible row
- **THEN** the guard counts one ranking violation

#### Scenario: Zero eligible rows
- **WHEN** no row has two legal actions and a positive finite parent margin
- **THEN** the guard returns a finite differentiable zero with zero eligibility and violations

### Requirement: Top-action guard compatibility and evidence
The trainer SHALL keep the top-action guard disabled by default and SHALL bind every positive-weight run to an immutable warm-start parent.

#### Scenario: Default compatibility
- **WHEN** weight is `0.0`
- **THEN** existing training behavior remains unchanged apart from additive default-valued report fields

#### Scenario: Invalid configuration
- **WHEN** weight or cap is invalid, a positive weight has no positive cap, or no warm-start parent is available
- **THEN** the run fails before trajectory collection or fitting

#### Scenario: Guarded report
- **WHEN** positive-weight training completes
- **THEN** the report and simulator-only checkpoint bind weight, cap, finite loss summaries, positive eligibility, violations, and parent identity without production authority

### Requirement: Fresh guard-aware simulator gate
The first top-action guarded candidate SHALL use registered unused training and evaluation seeds and SHALL be evaluated through the same deployment guard proxy as every frozen control.

#### Scenario: Fresh gate fails
- **WHEN** any registered technical, reward, HP, victory, or battle-stratum guardrail fails
- **THEN** production r16 remains authoritative and no packaging or gameplay is authorized

#### Scenario: Fresh gate passes
- **WHEN** all registered guard-aware criteria pass
- **THEN** the result may authorize a separately registered larger frozen confirmation but SHALL NOT authorize packaging or gameplay
