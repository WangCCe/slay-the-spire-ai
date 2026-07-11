## ADDED Requirements

### Requirement: Validated Lethal Plan Guard Precedence

The Ironclad combat system SHALL preserve validated lethal-plan provenance from planning through action execution. A current action that belongs to an active validated lethal plan SHALL take precedence over end-turn pressure, setup, and filler heuristics after action legality and immediate player-death checks pass.

The system SHALL clear lethal-plan provenance whenever the cached plan is cleared, invalidated, replanned, or reset for a new turn or combat transition.

#### Scenario: Safe HP-loss lethal prefix bypasses end-turn pressure
- **GIVEN** the player has 3 HP and 2 energy against two living slimes
- **AND** the planner has validated a lethal sequence beginning with Hemokinesis and followed by Headbutt
- **AND** Hemokinesis costs less HP than the player currently has and has a legal target
- **WHEN** takeover arbitration evaluates the first action
- **THEN** it SHALL return the legal Hemokinesis action rather than replace it with `EndTurnAction`

#### Scenario: Immediate HP-cost death remains blocked
- **GIVEN** an action belongs to a damage plan but its HP cost is equal to or greater than current player HP
- **WHEN** takeover arbitration evaluates the action
- **THEN** the system SHALL reject the action before applying lethal-plan precedence

#### Scenario: Immediate reactive-damage death remains blocked
- **GIVEN** an attack belongs to a lethal plan
- **AND** known reactive damage would kill the player before the action resolves safely
- **WHEN** takeover arbitration evaluates the action
- **THEN** the system SHALL reject the attack before applying lethal-plan precedence

#### Scenario: Ordinary pressure-unsafe HP loss remains blocked
- **GIVEN** an HP-loss action does not belong to an active validated lethal plan
- **AND** playing it would expose the player to lethal end-turn damage
- **WHEN** takeover arbitration evaluates the action
- **THEN** the existing pressure guard SHALL reject or replace the action

#### Scenario: Stale lethal provenance cannot bypass guards
- **GIVEN** a previously validated lethal plan has been invalidated by a state change or replan
- **WHEN** the fallback agent returns an action from the new state
- **THEN** the old lethal provenance SHALL be cleared and SHALL NOT bypass normal guards

#### Scenario: Arbitration is observable
- **GIVEN** takeover arbitration passes through or rejects an action associated with lethal provenance
- **WHEN** the decision is logged
- **THEN** the log SHALL identify the plan kind and whether legality, immediate-death, or pressure arbitration determined the result
