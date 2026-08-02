## MODIFIED Requirements

### Requirement: Episode-local state and bounded compatibility
Stateful evaluation SHALL retain one configured Current agent per registered episode and SHALL process decisions in monotonic episode order. Historical Stage 2 SHALL remain limited to its fixed reused-seed registration, while any API v3 total-event native compatibility run SHALL use an independent pushed registration and untouched fixed cohort without inheriting historical authorization.

#### Scenario: An episode has multiple decisions
- **WHEN** ordered snapshots from one episode are evaluated
- **THEN** route history, shop transition state, and other Current session state SHALL be retained within that episode
- **AND** no state SHALL leak to another episode or deterministic replay

#### Scenario: Historical Stage 2 is authorized
- **WHEN** its frozen Stage 1 passes and the Stage 2 registration names only its previously consumed seeds
- **THEN** one bounded deterministic own-trajectory compatibility run MAY execute under that historical registration
- **AND** it SHALL report legality and reproducibility without interpreting terminal policy quality

#### Scenario: API v3 total-event compatibility is requested
- **WHEN** the completed total event implementation is evaluated on native own trajectories
- **THEN** a separate registration SHALL bind the API v3 module, total observation identity, implementation, new fixed cohort, replay count, limits, publication contract, and all-false authority
- **AND** neither the historical Stage 1 verdict nor its consumed Stage 2 seeds SHALL grant or transfer execution authority

#### Scenario: A native event action is evaluated
- **WHEN** Current returns a position for an event observation during the registered API v3 cohort
- **THEN** the episode SHALL record the exact total-contract source, Current position, simulator choice index, and uniquely mapped legal action
- **AND** state SHALL remain episode-local across every event phase and follow-up decision

#### Scenario: Unregistered or previously reserved seed is requested
- **WHEN** execution contains an extra, changed, selected, consumed, training, validation, or reserved final-test seed
- **THEN** execution SHALL stop before simulator rollout
- **AND** the evaluator SHALL NOT substitute another seed
