## ADDED Requirements
### Requirement: Power Card Baseline Scoring
The combat scorer SHALL assign a baseline bonus for POWER cards to reflect long-term strategic value, even when the power produces no immediate damage or block.

#### Scenario: Power-only hand should not tie with empty sequence
- **GIVEN** a hand with only Corruption (0 cost) and no attacks or skills
- **WHEN** evaluating sequences in the same turn
- **THEN** the sequence that plays Corruption SHALL score higher than the empty sequence

#### Scenario: Early-turn power preference
- **GIVEN** a POWER card is playable on turn 1 and again on turn 4
- **WHEN** evaluating otherwise equal sequences
- **THEN** the turn 1 sequence SHALL receive a higher bonus than the turn 4 sequence

#### Scenario: Power bonus applies regardless of damage
- **GIVEN** a POWER card that deals no damage and grants no block
- **WHEN** scoring the sequence
- **THEN** the scorer SHALL still apply the baseline POWER bonus

## MODIFIED Requirements
### Requirement: Two-Stage Action Expansion
The beam search algorithm SHALL use a two-stage action expansion strategy to efficiently prune low-value actions. Stage 1 (FastScore) SHALL:

1. Compute a lightweight score for each playable action without full simulation
2. Prioritize: zero-cost cards (+20), attacks when monsters alive (+10), block at low HP (+15), base damage estimate (+2 per damage), and POWER cards (baseline bonus)
3. Sort actions by FastScore in descending order
4. Select only the top M actions for Stage 2, where M decreases with search depth (Progressive Widening)

Stage 2 (FullSim) SHALL run full simulation and evaluation only on the top M actions from Stage 1.

Progressive widening parameters: Depth 0→M=12, Depth 1→M=10, Depth 2→M=7, Depth 3→M=5, Depth 4→M=4.

#### Scenario: Action pruning at depth 0
- **GIVEN** 8 playable cards at depth 0
- **WHEN** running FastScore evaluation
- **THEN** only the top 12 cards (or all if fewer than 12) SHALL proceed to FullSim simulation

#### Scenario: Progressive narrowing
- **GIVEN** 10 playable cards at depth 3
- **WHEN** running FastScore evaluation
- **THEN** only the top 5 cards SHALL proceed to FullSim simulation (M=5 at depth 3)

#### Scenario: Zero-cost prioritization
- **GIVEN** actions: [Clothesline (2 cost, 14 damage), Apex (0 cost, 5 damage), Bash (1 cost, 8 damage)]
- **WHEN** computing FastScore
- **THEN** Apex SHALL receive the highest FastScore due to zero-cost bonus (+20), prioritizing it for simulation

#### Scenario: Block-at-low-HP prioritization
- **GIVEN** player at 18 HP with actions: [Iron Wave (5 block, 5 damage), Heavy Blade (14 damage)]
- **WHEN** computing FastScore
- **THEN** Iron Wave SHALL receive a +15 bonus for block at low HP, potentially outranking Heavy Blade

#### Scenario: Power card FastScore inclusion
- **GIVEN** a POWER card with no immediate damage or block and a low-damage attack
- **WHEN** computing FastScore
- **THEN** the POWER card SHALL receive a baseline bonus so it can be considered for FullSim
