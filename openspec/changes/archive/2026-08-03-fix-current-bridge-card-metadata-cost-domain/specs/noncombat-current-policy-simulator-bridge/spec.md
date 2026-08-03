## ADDED Requirements

### Requirement: Closed Card Metadata Cost Compatibility
The bridge SHALL hydrate an empty metadata cost as SpireComm unplayable cost
`-2` only for this exact closed stable-native-ID set:
`ASCENDERS_BANE`, `BURN`, `CLUMSY`, `CURSE_OF_THE_BELL`, `DAZED`, `DECAY`,
`DEUS_EX_MACHINA`, `DOUBT`, `INJURY`, `NECRONOMICURSE`, `NORMALITY`, `PAIN`,
`PARASITE`, `REFLEX`, `REGRET`, `SHAME`, `TACTICIAN`, `VOID`, `WOUND`, and
`WRITHE`. Every listed identity MUST match its exact audited native display
name, metadata name, metadata type, empty cost, and leading `Unplayable.`
description. The bridge MUST NOT infer another identity by empty value, card
type, description alone, display-name normalization, fuzzy matching, or
upgraded-name synthesis.

#### Scenario: A registered empty-cost unplayable card is hydrated
- **WHEN** a source card has one listed stable ID and exact native name and its
  selected metadata record has the registered type, empty cost, and leading
  `Unplayable.` description
- **THEN** the bridge SHALL hydrate the typed card with cost and cost-for-turn
  `-2`
- **AND** stable ID, name, type, rarity, upgrades, misc, price, slot, source
  card, and metadata bytes SHALL otherwise remain unchanged

#### Scenario: A registered unplayable Skill is upgraded
- **WHEN** `REFLEX`, `TACTICIAN`, or `DEUS_EX_MACHINA` has a positive validated
  upgrade count under its exact base native identity
- **THEN** the bridge SHALL retain that upgrade count while hydrating cost
  `-2`
- **AND** it SHALL NOT require, synthesize, or select a `+`-suffixed source name

#### Scenario: A listed identity or metadata field drifts
- **WHEN** a listed stable ID has an unexpected source name, metadata name,
  metadata type, non-empty cost, or missing exact `Unplayable.` prefix
- **THEN** hydration SHALL fail with a field-specific structural blocker before
  Current executes
- **AND** the bridge SHALL NOT fall through to generic integer, `X`, alias, or
  description-only handling

#### Scenario: An unlisted card has empty cost
- **WHEN** an empty-cost metadata record belongs to an unknown ID or to
  `BECOME_ALMIGHTY`, `FAME_AND_FORTUNE`, or `LIVE_FOREVER`
- **THEN** the bridge SHALL preserve `card_metadata_cost_invalid`
- **AND** it SHALL NOT assign `-2` or another heuristic cost

#### Scenario: Existing numeric and X costs are hydrated
- **WHEN** an unlisted card has a valid integer cost or exact `X` cost,
  including numeric-cost `SLIMED` and `PRIDE`
- **THEN** the bridge SHALL preserve the existing integer or `X -> -1`
  behavior
- **AND** the closed unplayable table SHALL NOT change that card's identity or
  cost

### Requirement: Card Cost Repair Has No Empirical Authority
The closed card-cost compatibility repair SHALL be verified without native
module loading, environment construction, seed access, gameplay, policy
change, model fitting, reward work, OPE, formal RL, training, qualification,
loading, or promotion.

#### Scenario: Offline repair verification passes
- **WHEN** exhaustive positive, reverse, upgrade, production-shaped hydration,
  non-mutation, focused, and repository-gate checks pass
- **THEN** the repair MAY be recorded as implementation-level bridge
  compatibility
- **AND** it SHALL NOT establish a baseline floor or target-supported outcome

#### Scenario: A caller requests study retry or reinterpretation
- **WHEN** the repair is complete after the terminal Current baseline study
- **THEN** the archived registration, authorization, journal, rows, artifacts,
  blocked verdict, and readiness refresh SHALL remain immutable
- **AND** no canary continuation, replacement cohort, threshold change, retry,
  or partial-row promotion SHALL be authorized
