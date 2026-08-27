## ADDED Requirements

### Requirement: Frozen-parent guarded target-action provenance
The LightSTS runner SHALL optionally retain the deterministic frozen-parent deployment-guard action for every accepted complete-trajectory state independently of the action selected by epsilon behavior exploration.

#### Scenario: Parent behavior branch
- **WHEN** guarded-parent behavior selects the parent branch below the action-per-turn cap
- **THEN** the stored target-policy action equals the guarded parent action and the executed behavior action uses that same action

#### Scenario: Exploration behavior branch
- **WHEN** guarded-parent behavior selects the epsilon exploration branch
- **THEN** the runner still computes and stores the deterministic guarded parent target-policy action while executing the independently seeded exploration action

#### Scenario: Forced action bound
- **WHEN** the action-per-turn bound forces EndTurn
- **THEN** the stored target-policy action and executed behavior action are EndTurn and no target-policy guard replacement is recorded

#### Scenario: Target-action evidence
- **WHEN** target-action provenance is enabled and collection completes
- **THEN** the report binds target-policy action counts, target guard replacement counts, behavior branch counts, and a canonical target-policy action identity without changing the existing source-transition identity contract

### Requirement: Guard-aware target-action configuration integrity
The LightSTS runner MUST require guarded-parent behavior, an immutable warm-start parent, complete trajectories, and the registered deployment guard whenever frozen-parent guard-aware bootstrap provenance is selected.

#### Scenario: Compatible guard-aware configuration
- **WHEN** guard-aware bootstrap is selected with guarded-parent behavior, a valid immutable parent, complete-trajectory collection, and the registered deployment guard
- **THEN** target-action collection and target preparation may proceed

#### Scenario: Incompatible guard-aware configuration
- **WHEN** any required parent, behavior, trajectory, or guard condition is absent
- **THEN** the runner fails before native trajectory collection or fitting

#### Scenario: Default compatibility
- **WHEN** raw-greedy bootstrap or a non-n-step target mode is used without guard-aware bootstrap
- **THEN** target-policy action provenance is not required and existing behavior selection remains unchanged

