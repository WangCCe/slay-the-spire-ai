## ADDED Requirements

### Requirement: GRID selection honors remaining cardinality
The GRID screen handler SHALL subtract already selected cards from the total
required count and return exactly the remaining number of new cards when the
screen requires an exact count.

#### Scenario: Partial Astrolabe selection
- **GIVEN** a GRID requires three cards total
- **AND** two cards are already selected
- **WHEN** the agent handles the intermediate GRID state
- **THEN** it SHALL return a `CardSelectAction` containing exactly one new card
- **AND** that card SHALL NOT be either already selected card

#### Scenario: Initial selection is unchanged
- **GIVEN** a GRID requires three cards total
- **AND** no cards are selected
- **WHEN** the agent handles the GRID state
- **THEN** it SHALL return exactly three cards using the existing ranking policy

### Requirement: Reconstructed selected cards are excluded by multiplicity
The GRID screen handler SHALL match reconstructed selected cards by UUID when
available, otherwise by canonical card identity and upgrade count, and SHALL
remove one candidate occurrence per selected occurrence.

#### Scenario: Selected cards are distinct reconstructed objects
- **GIVEN** `cards` and `selected_cards` contain distinct Python objects with matching UUIDs
- **WHEN** remaining GRID candidates are built
- **THEN** the matching available occurrences SHALL be excluded

#### Scenario: Duplicate cards without UUIDs
- **GIVEN** a GRID contains two equivalent unupgraded Defends without UUIDs
- **AND** one equivalent Defend is already selected
- **WHEN** remaining GRID candidates are built
- **THEN** exactly one Defend occurrence SHALL remain eligible

### Requirement: Inconsistent GRID cardinality fails safely
The GRID screen handler SHALL NOT construct a `CardSelectAction` with fewer
cards than an exact remaining requirement when the parsed candidate set is
inconsistent.

#### Scenario: Too few unselected candidates
- **GIVEN** the exact remaining count exceeds the number of unselected candidates
- **WHEN** the agent handles the GRID state
- **THEN** it SHALL request refreshed state instead of emitting an invalid card selection

#### Scenario: Exact GRID is already over-selected
- **GIVEN** an exact-count GRID reports more selected cards than its required count
- **WHEN** the agent handles the GRID state
- **THEN** it SHALL request refreshed state instead of confirming or constructing an empty selection

#### Scenario: Timeout recovery preserves exact cardinality
- **GIVEN** an exact-count GRID reports more selected cards than its required count
- **WHEN** refreshed state times out and legacy GRID recovery evaluates the screen
- **THEN** it SHALL NOT emit `confirm`
- **AND** any-number GRID recovery SHALL retain its existing at-least-count behavior
