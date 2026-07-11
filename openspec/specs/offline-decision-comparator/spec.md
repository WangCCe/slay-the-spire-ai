# offline-decision-comparator Specification

## Purpose
Define read-only normalization, reference comparison, reporting, and evidence gates for non-combat operating decisions.

## Requirements

### Requirement: Read-Only Decision Sample Normalization
The system SHALL provide an offline way to normalize operating-decision samples for shop, event, route, and card-reward decisions from local `.run` records, decision trace JSONL rows, or constructed fixtures. Decision trace rows that contain decision-time screen snapshots SHALL be normalized into complete samples when the category-specific context is present.

#### Scenario: Normalize mixed local sources
- **GIVEN** a local `.run` record with card choices and path outcomes
- **AND** a fixture containing a shop or route screen state
- **WHEN** the comparator loads those inputs
- **THEN** it SHALL produce decision samples with category, floor, act, options, our choice, source, and evidence-quality fields
- **AND** it SHALL NOT launch gameplay or require Communication Mod to be running

#### Scenario: Mark incomplete evidence
- **GIVEN** a `.run` record that records an item purchase but does not include the full shop offer and prices
- **WHEN** the comparator creates a shop sample from that record
- **THEN** it SHALL mark the sample as partial evidence
- **AND** it SHALL avoid treating the row as a high-confidence disagreement without a fixture or trace row that contains the missing offer context

#### Scenario: Normalize enriched trace evidence
- **GIVEN** a decision trace row with a shop, event, route, or card-reward screen snapshot
- **WHEN** the comparator loads the trace
- **THEN** it SHALL extract the relevant options, selected action, deck, relics, gold, HP, and source metadata
- **AND** it SHALL mark the sample complete only when the Bottled-style adapter has the context it requires for a high-confidence comparison

### Requirement: Bottled-Style Reference Adapters
The system SHALL compare each normalized sample against a Bottled-style reference choice derived from the local `C:\Users\20571\Documents\bottled_ai` strategy and handler behavior, without importing or vendoring Bottled into the live agent.

#### Scenario: Compare Ironclad card reward
- **GIVEN** an Ironclad card-reward sample with offered cards, current deck, and our selected card
- **WHEN** the reference adapter evaluates the sample
- **THEN** it SHALL use the Bottled `REQUESTED_STRIKE` desired-card counts as the default Ironclad card-reward reference
- **AND** it SHALL return the reference choice, match status, confidence, and a concise reason

#### Scenario: Compare shop choice
- **GIVEN** a shop sample with gold, purge availability, deck, cards, relics, potions, and our selected action
- **WHEN** the reference adapter evaluates the sample
- **THEN** it SHALL apply the Bottled-style priority order for Ironclad shops
- **AND** it SHALL explain whether the reference preferred purge, Perfected Strike, Membership Card, listed relic, listed card, or leaving the shop

#### Scenario: Compare route choice
- **GIVEN** a route sample with map candidates, current position, act, floor, HP, gold, and relic context
- **WHEN** the reference adapter evaluates the sample
- **THEN** it SHALL score routes using the Bottled common reward-to-survivability model
- **AND** it SHALL return the reference next-node choice and the dominant scoring reason

### Requirement: Difference Report And Repair Gate
The system SHALL generate a readable difference report that shows our current choice, Bottled-style reference choice, difference reason, confidence, and ranked follow-up issues, while preserving the no-repair-first boundary until evidence supports a targeted gameplay fix.

#### Scenario: Generate readable report
- **GIVEN** normalized samples across shop, event, route, and card-reward categories
- **WHEN** the comparator runs
- **THEN** it SHALL output a report with summary counts, comparison rows, and a ranked "Most Worth Fixing" section
- **AND** the ranked section SHALL include 3-5 issues when supported by repeated non-fixture high-confidence evidence, or explicitly state why fewer are justified

#### Scenario: Enforce repair gate
- **GIVEN** the report contains only fixture, partial-evidence, low-confidence, isolated, or combat-play differences
- **WHEN** the report is generated
- **THEN** it SHALL state that no gameplay-code fix is recommended yet
- **AND** it SHALL NOT modify gameplay strategy code, train models, tune parameters, or alter live gameplay configuration

#### Scenario: Permit one minimal strategy repair
- **GIVEN** the report contains a repeated high-confidence non-fixture operating-decision mismatch relevant to the first Ironclad win objective
- **WHEN** the mismatch is selected for repair
- **THEN** the implementation SHALL add a failing regression for that specific decision first
- **AND** it SHALL apply only the minimal gameplay decision change needed for that proven mismatch
