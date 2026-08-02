## ADDED Requirements

### Requirement: Immutable formal reward registration
The system SHALL require one versioned registration that binds the committed contract implementation, focused tests, existing simulator reward implementation and tests, governing specs, and prior readiness evidence by repository-relative path, SHA-256 digest, and byte size.

#### Scenario: Registered source is exact
- **WHEN** every registered path, commit, digest, size, schema, and no-authority value matches
- **THEN** the contract builder SHALL evaluate exactly those frozen inputs

#### Scenario: Registered source drifts
- **WHEN** any source, test, spec, readiness artifact, contract constant, implementation identity, or authority value differs
- **THEN** publication SHALL fail closed before producing a formal reward contract

### Requirement: Ordered terminal victory and floor progress channels
The formal reward contract SHALL define terminal victory as the primary objective and bounded floor progress as a separate secondary simulator shaping channel.

#### Scenario: Terminal victory is observed
- **WHEN** a successor is terminal with outcome `player_victory`
- **THEN** the terminal-victory channel SHALL equal one
- **AND** a non-terminal or non-victory successor SHALL produce zero terminal-victory value

#### Scenario: Floor advances
- **WHEN** a simulator transition advances from one finite floor to a later finite floor
- **THEN** floor progress SHALL equal the non-negative difference after capping both floors to `[0, 57]`, divided by 57
- **AND** the complete episode floor-progress contribution SHALL remain in `[0, 1]`

#### Scenario: Floor does not advance
- **WHEN** a successor floor repeats, regresses, or lies beyond a capped boundary
- **THEN** the floor-progress channel SHALL never become negative or exceed its registered bound

### Requirement: Victory-primary optimization constraint
The contract SHALL permit only lexicographic victory-first optimization or a scalarization that proves the terminal-victory weight is strictly greater than the maximum complete-episode floor-progress contribution.

#### Scenario: Lexicographic mode is proposed
- **WHEN** a future training proposal selects lexicographic optimization
- **THEN** terminal victory SHALL be the first objective and floor progress SHALL be only the second objective

#### Scenario: Scalar mode is proposed
- **WHEN** a future training proposal combines the channels into one scalar
- **THEN** it SHALL bind a victory weight strictly greater than the registered maximum shaping contribution and test the strict dominance invariant

#### Scenario: Smoke reward is inspected
- **WHEN** the existing simulator smoke's `victory_bonus=1.0` is compared with the maximum floor-progress contribution of 1.0
- **THEN** the contract SHALL record it as not automatically formal-compatible
- **AND** it SHALL NOT select a replacement weight

### Requirement: Reference and provenance isolation
The contract SHALL exclude Current, Bottled, SimpleAgent, teacher agreement, HP, gold, deck heuristics, behavior propensities, and OPE estimates from reward and SHALL distinguish simulator shaping from live/OPE outcomes.

#### Scenario: Auxiliary fields change
- **WHEN** excluded labels, resources, heuristics, probabilities, or estimates differ while transition floors and terminal outcome remain identical
- **THEN** both formal reward channels SHALL remain identical

#### Scenario: Live outcome is interpreted
- **WHEN** a live or OPE trajectory supplies victory and floor reached
- **THEN** victory SHALL remain the primary outcome and floor reached SHALL remain a separate diagnostic
- **AND** simulator floor shaping SHALL NOT be attributed to the live trajectory

### Requirement: Deterministic no-authority artifacts
The system SHALL publish a canonical contract, verification result, human-readable report, validated configuration, and manifest with exact byte identities and all execution or promotion authority false.

#### Scenario: Contract verification succeeds
- **WHEN** all source identities, fixed formula examples, bounds, terminal semantics, scalarization constraints, exclusions, and provenance checks pass
- **THEN** the contract verdict SHALL be `formal_reward_contract_ready`
- **AND** strict recomputation SHALL reproduce every canonical byte

#### Scenario: Contract verification fails
- **WHEN** any identity or semantic check fails
- **THEN** the builder SHALL fail without partially publishing a ready artifact

#### Scenario: Ready contract is consumed
- **WHEN** a downstream readiness audit consumes `formal_reward_contract_ready`
- **THEN** gameplay, simulator rollout, model fitting, formal RL, OPE reinterpretation, qualification, live loading, and promotion authority SHALL remain false

### Requirement: Readiness handoff changes only reward
The contract SHALL support one new immutable formal-RL readiness registration whose preregistered expected delta is limited to the reward domain.

#### Scenario: Formal reward handoff succeeds
- **WHEN** the new readiness registration differs from the prior registration only by its own identity and the added validated formal reward binding
- **THEN** reward SHALL change from blocked to passed
- **AND** state/action, reference isolation, baseline policy, outcome support, evaluation, overall verdict, and authority SHALL retain their preregistered values

#### Scenario: Another readiness result changes
- **WHEN** any non-reward domain, overall verdict, evidence binding, or authority value changes unexpectedly
- **THEN** the handoff SHALL fail closed and SHALL NOT reinterpret the new matrix
