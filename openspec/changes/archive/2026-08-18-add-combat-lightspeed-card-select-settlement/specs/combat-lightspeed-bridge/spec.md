## ADDED Requirements

### Requirement: Bounded auxiliary combat card-selection settlement
The native combat environment SHALL deterministically settle implemented and natively enumerable `CARD_SELECT` states after an RL-visible legal action without changing the RL v2 observation or action dimensions.

#### Scenario: Enumerable card selection
- **WHEN** a legal combat action enters an allowlisted `CARD_SELECT` task with at least one valid native action
- **THEN** the environment applies the deterministic auxiliary native policy until it reaches player-normal input, a terminal outcome, another unsupported input state, or the settlement bound

#### Scenario: Settlement evidence
- **WHEN** one or more auxiliary card-selection actions are applied
- **THEN** the next status and snapshot report the ordered task identities and auxiliary action count while the RL-visible decision count increases only for the originating combat action

#### Scenario: Unsafe card selection
- **WHEN** a card-selection task is unimplemented, not allowlisted, has no enumerable action, makes no progress, or exceeds the settlement bound
- **THEN** the environment reports a stable unsupported reason and does not fabricate an RL v2 action or terminal outcome

#### Scenario: Deterministic clone successor
- **WHEN** the same legal action enters card selection on two clones of one source state
- **THEN** both clones produce identical settlement evidence, canonical successor state, and legal actions without mutating the source environment

#### Scenario: RL action-space isolation
- **WHEN** the bridge maps a successor after auxiliary settlement
- **THEN** it still returns 328 continuous features and a 133-element action mask containing only the existing card, potion, End Turn, and non-combat indices
