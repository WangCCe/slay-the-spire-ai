# elite-aggressive-mode Specification

## Purpose
TBD - created by archiving change fix-over-defensive-elite-combat. Update Purpose after archive.
## Requirements
### Requirement: Combat Mode Enumeration

The system SHALL define a CombatMode enumeration with distinct weight profiles for different fight types:

1. **BALANCED mode**: Current weights (DAMAGE=2.0, BLOCK=1.5, W_DEATHRISK=8.0)
2. **AGGRESSIVE mode**: Elite/scaling weights (DAMAGE=5.0, BLOCK=0.5, W_DEATHRISK=4.0)
3. **SEMI_AGGRESSIVE mode**: Boss weights (DAMAGE=3.5, BLOCK=1.0, W_DEATHRISK=6.0)

Weight profiles SHALL be stored as constants accessible to the scoring system.

#### Scenario: Balanced mode uses current weights
- **GIVEN** CombatMode.BALANCED
- **WHEN** retrieving weight profile
- **THEN** DAMAGE_WEIGHT SHALL be 2.0
- **AND** BLOCK_WEIGHT SHALL be 1.5
- **AND** W_DEATHRISK SHALL be 8.0

#### Scenario: Aggressive mode heavily prioritizes damage
- **GIVEN** CombatMode.AGGRESSIVE
- **WHEN** retrieving weight profile
- **THEN** DAMAGE_WEIGHT SHALL be 5.0 (+150% vs balanced)
- **AND** BLOCK_WEIGHT SHALL be 0.5 (-67% vs balanced)
- **AND** W_DEATHRISK SHALL be 4.0 (-50% vs balanced)

#### Scenario: Semi-aggressive mode for bosses
- **GIVEN** CombatMode.SEMI_AGGRESSIVE
- **WHEN** retrieving weight profile
- **THEN** DAMAGE_WEIGHT SHALL be 3.5 (+75% vs balanced)
- **AND** BLOCK_WEIGHT SHALL be 1.0 (-33% vs balanced)
- **AND** W_DEATHRISK SHALL be 6.0 (-25% vs balanced)

#### Scenario: Mode enumeration accessible
- **GIVEN** the CombatMode enum
- **WHEN** iterating over modes
- **THEN** BALANCED, AGGRESSIVE, and SEMI_AGGRESSIVE SHALL all exist
- **AND** each SHALL have a corresponding weight profile

---

### Requirement: Mode-Based Weight Selection

The HeuristicCombatPlanner SHALL select and apply the appropriate weight profile based on the combat mode. The planner SHALL:

1. Accept a combat_mode parameter in __init__()
2. Store the selected mode as an instance variable
3. Use the mode's weight profile in calculate_outcome_score()
4. Default to BALANCED mode if no mode is specified

The weight profile SHALL be applied to all scoring calculations within the planner.

#### Scenario: Planner initialized with aggressive mode
- **GIVEN** elite fight detection
- **WHEN** creating HeuristicCombatPlanner with combat_mode=AGGRESSIVE
- **THEN** the planner SHALL use DAMAGE_WEIGHT=5.0 for all scoring
- **AND** SHALL use BLOCK_WEIGHT=0.5 for all scoring

#### Scenario: Planner defaults to balanced mode
- **GIVEN** regular fight (no elite detection)
- **WHEN** creating HeuristicCombatPlanner without specifying combat_mode
- **THEN** the planner SHALL default to BALANCED mode
- **AND** SHALL use DAMAGE_WEIGHT=2.0, BLOCK_WEIGHT=1.5

#### Scenario: Mode applied throughout beam search
- **GIVEN** HeuristicCombatPlanner in AGGRESSIVE mode
- **WHEN** running beam search over 100 candidate sequences
- **THEN** all 100 sequences SHALL be scored using AGGRESSIVE weights
- **AND** no sequence SHALL be scored with BALANCED weights

#### Scenario: Weight profile stored in planner
- **GIVEN** HeuristicCombatPlanner initialized with combat_mode=SEMI_AGGRESSIVE
- **WHEN** accessing planner.combat_mode
- **THEN** the value SHALL be CombatMode.SEMI_AGGRESSIVE
- **AND** planner.damage_weight SHALL be 3.5

---

### Requirement: Elite Fight Mode Selection

The combat mode selector SHALL automatically select AGGRESSIVE mode for elite fights. Detection SHALL be based on:

1. Monster name matching against elite list
2. Presence of elite-specific mechanics (e.g., multiple intents)
3. Room type detection (ELITE)

When elite fight is detected, the system SHALL use AGGRESSIVE weights for all combat decisions.

#### Scenario: Gremlin Nob triggers aggressive mode
- **GIVEN** combat with monster named "Gremlin Nob"
- **WHEN** selecting combat mode
- **THEN** CombatMode.AGGRESSIVE SHALL be selected
- **AND** damage SHALL be prioritized 10× over block (5.0 vs 0.5)

#### Scenario: Slavers trigger aggressive mode
- **GIVEN** combat with monsters including "Slaver"
- **WHEN** selecting combat mode
- **THEN** CombatMode.AGGRESSIVE SHALL be selected

#### Scenario: Sentry triggers aggressive mode
- **GIVEN** combat with "The Sentry" (or "Sentry")
- **WHEN** selecting combat mode
- **THEN** CombatMode.AGGRESSIVE SHALL be selected

#### Scenario: Non-elite fight uses balanced mode
- **GIVEN** combat with "Fungi Beast" or "Cultist"
- **WHEN** selecting combat mode
- **THEN** CombatMode.BALANCED SHALL be selected
- **AND** normal damage/block balance SHALL be used

---

### Requirement: Damage-to-Block Ratio Enforcement

The AGGRESSIVE mode SHALL create a 10:1 damage-to-block value ratio to strongly discourage defensive plays. Specifically:

- Damage value per point: 5.0
- Block value per point: 0.5
- **Ratio**: 10.0 (damage is 10× more valuable than block)

This ratio SHALL make defensive cards score significantly lower than attack cards in elite fights.

#### Scenario: Attack card outvalues defense card
- **GIVEN** AGGRESSIVE mode
- **AND** two cards: Defend_R (5 block) and Strike_R (6 damage)
- **WHEN** scoring both cards
- **THEN** Defend_R SHALL score 2.5 points (5 × 0.5)
- **AND** Strike_R SHALL score 30.0 points (6 × 5.0)
- **AND** Strike_R SHALL score 12× higher than Defend_R

#### Scenario: AOE attack strongly favored over defense
- **GIVEN** AGGRESSIVE mode in elite fight with 3 monsters
- **AND** cards: Cleave (8 damage to all) vs Iron Wave (5 block, 5 damage)
- **WHEN** scoring both cards
- **THEN** Cleave SHALL score 40.0 points (8 × 3 × 5.0 = 120 damage value)
- **AND** Iron Wave SHALL score 27.5 points (5 × 0.5 + 5 × 5.0)
- **AND** Cleave SHALL be strongly preferred

#### Scenario: Defensive play sequence penalized
- **GIVEN** AGGRESSIVE mode
- **AND** sequence A: Play 2 attack cards (20 damage total)
- **AND** sequence B: Play 1 attack, 1 defend (8 damage, 5 block)
- **WHEN** comparing scores
- **THEN** sequence A SHALL score 100.0 points (20 × 5.0)
- **AND** sequence B SHALL score 42.5 points (8 × 5.0 + 5 × 0.5)
- **AND** sequence A SHALL be preferred by 57.5 points

#### Scenario: High-cost attack still favored
- **GIVEN** AGGRESSIVE mode
- **AND** cards: Clothesline (12 damage, 2 energy) vs Defend + Defend (10 block, 2 energy)
- **WHEN** scoring both options
- **THEN** Clothesline SHALL score 60.0 points (12 × 5.0)
- **AND** Defend + Defend SHALL score 5.0 points (10 × 0.5)
- **AND** Clothesline SHALL be 12× higher value

---

### Requirement: Survival Penalty Reduction in Aggressive Mode

The AGGRESSIVE mode SHALL reduce the survival penalty (W_DEATHRISK) to 4.0 (half of BALANCED). This acknowledges that:

1. Fast kills reduce total incoming damage (less time for enemy to act)
2. Taking some damage is acceptable if it enables a faster kill
3. Over-prioritizing survival leads to the over-defensive problem

The reduced survival penalty SHALL allow risky high-damage sequences to score competitively.

#### Scenario: Risky high-damage sequence competitive
- **GIVEN** AGGRESSIVE mode (W_DEATHRISK=4.0)
- **AND** two sequences:
  - Sequence A (Safe): 15 damage, 5 expected HP loss
  - Sequence B (Risky): 30 damage, 15 expected HP loss
- **WHEN** scoring both
- **THEN** Sequence A: 15×5.0 - 5×4.0 = 75 - 20 = 55 points
- **AND** Sequence B: 30×5.0 - 15×4.0 = 150 - 60 = 90 points
- **AND** Sequence B SHALL be preferred (more damage justifies risk)

#### Scenario: Aggressive mode accepts more damage
- **GIVEN** AGGRESSIVE mode vs BALANCED mode
- **AND** same high-damage sequence with 12 expected HP loss
- **WHEN** scoring in both modes
- **THEN** BALANCED score penalty: -96 points (12 × 8.0)
- **AND** AGGRESSIVE score penalty: -48 points (12 × 4.0)
- **AND** AGGRESSIVE mode penalizes survival 50% less

#### Scenario: Lethal damage still avoided
- **GIVEN** AGGRESSIVE mode
- **AND** sequence that results in player death (HP loss >= current HP)
- **WHEN** scoring
- **THEN** score SHALL still be negative infinity (lethal always avoided)

#### Scenario: Moderate HP loss acceptable
- **GIVEN** AGGRESSIVE mode at A20
- **AND** player at 60 HP
- **AND** sequence deals 40 damage but takes 20 expected HP loss
- **WHEN** scoring
- **THEN** survival penalty SHALL be -80 points (20 × 4.0)
- **AND** damage bonus SHALL be +200 points (40 × 5.0)
- **AND** net score SHALL be +120 points (aggressive play rewarded)

---

### Requirement: Kill Bonus Doubling in Aggressive Mode

The AGGRESSIVE mode SHALL double the KILL_BONUS from 100 → 200 points per monster killed. This creates:

1. Strong incentive to eliminate monsters quickly
2. Extra reward for lethal damage sequences
3. Positive reinforcement for fast-kill strategies

The doubled kill bonus SHALL be applied in addition to the damage bonus.

#### Scenario: Kill bonus doubled
- **GIVEN** AGGRESSIVE mode
- **AND** a combat sequence that kills one elite (92 HP)
- **WHEN** calculating outcome score
- **THEN** kill bonus SHALL be +200 points
- **AND** damage bonus SHALL be +460 points (92 × 5.0)
- **AND** total kill value SHALL be 660 points

#### Scenario: Killing highest priority
- **GIVEN** AGGRESSIVE mode
- **AND** two sequences:
  - Sequence A: Deal 50 damage, no kills
  - Sequence B: Deal 30 damage, kill one monster
- **WHEN** comparing scores
- **THEN** Sequence A: 50 × 5.0 = 250 points
- **AND** Sequence B: 30 × 5.0 + 200 = 350 points
- **AND** Sequence B SHALL be preferred (kill prioritized)

#### Scenario: AOE kills rewarded highly
- **GIVEN** AGGRESSIVE mode
- **AND** Cleave that kills 3 gremlins (20 damage total)
- **WHEN** scoring
- **THEN** damage bonus: 20 × 5.0 = 100 points
- **AND** kill bonus: 3 × 200 = 600 points
- **AND** total value: 700 points (strongly incentivizes AOE)

#### Scenario: Regular fight uses normal kill bonus
- **GIVEN** BALANCED mode (regular fight)
- **AND** a combat sequence that kills one monster
- **WHEN** calculating outcome score
- **THEN** kill bonus SHALL be +100 points (baseline)
- **AND** not doubled

---

### Requirement: Backward Compatibility

The aggressive mode system SHALL maintain backward compatibility. Regular fights (non-elite) SHALL:

1. Use BALANCED mode by default
2. Experience no change in scoring behavior
3. Maintain current performance levels

No regression in regular fight performance SHALL occur.

#### Scenario: Regular fight unchanged
- **GIVEN** combat with "Cultist" or "Jaw Worm"
- **WHEN** selecting combat mode
- **THEN** BALANCED mode SHALL be selected
- **AND** scoring SHALL use original weights (DAMAGE=2.0, BLOCK=1.5)
- **AND** behavior SHALL match current implementation

#### Scenario: Optional mode parameter
- **GIVEN** existing code that creates HeuristicCombatPlanner without mode
- **WHEN** initializing
- **THEN** planner SHALL default to BALANCED mode
- **AND** existing code SHALL continue to work

#### Scenario: Explicit mode override
- **GIVEN** explicit combat_mode parameter passed to planner
- **WHEN** initializing
- **THEN** explicit mode SHALL take precedence
- **AND** detection logic can be bypassed for testing

