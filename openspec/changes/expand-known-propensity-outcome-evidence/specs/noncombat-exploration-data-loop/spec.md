## ADDED Requirements

### Requirement: Registered Multi-Session Exploration Pool
The system SHALL deterministically aggregate a pre-registered sequence of bounded exploration sessions without allowing per-session randomness or operator selection to redefine the study pool.

#### Scenario: Registered sessions are pooled
- **WHEN** a fixed study contains multiple bounded session slots with one shared run lock
- **THEN** the pool builder SHALL enumerate sessions from the registration, verify each session's configuration, manifest, trace, confirmation joins, canonical samples, and conservative run joins, and record every inclusion or exclusion reason
- **AND** aggregate hashes and evidence SHALL be independent of filesystem or argument ordering

#### Scenario: One operational session lacks aggregate arm support
- **WHEN** an individual registered slot has fewer than the study-level baseline or alternative count while its evidence remains exact and eligible
- **THEN** the slot's valid evidence SHALL remain in the registered pool
- **AND** category-arm thresholds SHALL be evaluated across the complete registered pool rather than by selectively excluding or replacing that slot

#### Scenario: Registered pool membership is incomplete or contaminated
- **WHEN** a launched registered session is omitted, an unregistered session is added, a trajectory appears more than once, or sessions do not share the exact run lock
- **THEN** pooled qualification SHALL fail with the exact membership or provenance reason
- **AND** no affected trajectory SHALL be silently reassigned to a compatible behavior policy

### Requirement: Registered Pool Exactness Gate
The system SHALL preserve the existing exact known-propensity evidence requirements when qualifying a multi-session registered pool.

#### Scenario: Included pooled evidence is exact
- **WHEN** a registered pool is evaluated for qualification
- **THEN** every included eligible decision SHALL be replay-valid, candidate-legal, transition-confirmed, joined to one complete trajectory outcome, and bound to its exact session behavior distribution
- **AND** any invalid decision or trajectory SHALL remain visible with a deterministic exclusion or blocking reason

#### Scenario: Aggregate support qualifies
- **WHEN** the registered outcome-evidence pool contains at least 50 confirmed baseline and 50 confirmed alternative decisions in each of `card_reward` and `shop`
- **THEN** its study-level category-arm support condition SHALL pass
- **AND** that condition SHALL NOT imply OPE comparison, causal uplift, formal training, or live promotion readiness
