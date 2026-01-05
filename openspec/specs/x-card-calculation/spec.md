# x-card-calculation Specification

## Purpose
TBD - created by archiving change implement-x-cards-simulation. Update Purpose after archive.
## Requirements
### Requirement: X-Damage Calculation

The combat simulation SHALL dynamically calculate damage for X-damage cards based on game state rather than using a fixed value. The system SHALL:

1. Detect X-damage cards by checking `card.card_id`
2. Calculate actual damage using game state (player_block, energy_available, max_energy)
3. Apply calculated damage in simulation (Strength, Vulnerable, Weak modifiers)
4. Return 0 only if the card truly has no value (e.g., 0 block for Body Slam)

**Supported Cards**:
- **Body Slam**: `damage = player_block`
- **Bludgeon**: `damage = min(30, 12 + player_block // 10)`
- **Whirlwind**: `damage = max_energy` (applied to each target in AOE)

#### Scenario: Body Slam with high block
- **GIVEN** player has 25 block
- **AND** player has Body Slam in hand
- **WHEN** simulating playing Body Slam
- **THEN** the simulated damage SHALL be 25
- **AND** the damage SHALL be applied to target monster
- **AND** beam search SHALL score Body Slam highly (25 > most Ironclad attacks)

#### Scenario: Body Slam with zero block
- **GIVEN** player has 0 block
- **AND** player has Body Slam in hand
- **WHEN** simulating playing Body Slam
- **THEN** the simulated damage SHALL be 0
- **AND** beam search SHALL score Body Slam low (0 damage is useless)

#### Scenario: Bludgeon scaling with block
- **GIVEN** player has 50 block
- **AND** player has Bludgeon in hand
- **WHEN** simulating playing Bludgeon
- **THEN** the simulated damage SHALL be 17 (12 + 50//10)
- **AND** the damage SHALL not exceed 30 cap

#### Scenario: Bludgeon cap at high block
- **GIVEN** player has 200 block
- **AND** player has Bludgeon in hand
- **WHEN** simulating playing Bludgeon
- **THEN** the simulated damage SHALL be 30 (capped at max)
- **AND** beam search SHALL prefer Bludgeon over basic attacks

#### Scenario: Whirlwind AOE multiplication
- **GIVEN** player has max_energy of 3
- **AND** there are 2 monsters alive
- **AND** player has Whirlwind in hand
- **WHEN** simulating playing Whirlwind
- **THEN** base_damage SHALL be 3 (equal to max_energy)
- **AND** damage SHALL be applied to both monsters (AOE)
- **AND** total damage SHALL be 6 (3 × 2 monsters)

#### Scenario: Weak debuff on X-damage
- **GIVEN** player has 25 block
- **AND** player has 2 Weak stacks
- **AND** player has Body Slam in hand
- **WHEN** simulating playing Body Slam
- **THEN** base damage SHALL be 25
- **AND** final damage SHALL be reduced by 25% (Weak modifier)
- **AND** simulated damage SHALL be ~19 (25 × 0.75)

---

### Requirement: X-Block Calculation

The combat simulation SHALL dynamically calculate block gain for X-block cards based on game state. The system SHALL:

1. Detect X-block cards by checking `card.card_id`
2. Calculate actual block using max_energy (NOT energy_available)
3. Apply calculated block to SimulationState
4. Apply Frail modifier if present (reduces block gain)

**Supported Cards**:
- **Rage**: `block = max_energy`

#### Scenario: Rage with 3 max energy
- **GIVEN** player has max_energy of 3
- **AND** player has 0 block currently
- **AND** player has Rage in hand
- **WHEN** simulating playing Rage
- **THEN** block gain SHALL be 3 (equal to max_energy)
- **AND** state.player_block SHALL be 3 after simulation

#### Scenario: Rage with 2 max energy
- **GIVEN** player has max_energy of 2
- **AND** player has Rage in hand
- **WHEN** simulating playing Rage
- **THEN** block gain SHALL be 2 (equal to max_energy)
- **AND** state.player_block SHALL increase by 2

#### Scenario: Frail reduces X-block
- **GIVEN** player has max_energy of 3
- **AND** player has 2 Frail stacks
- **AND** player has Rage in hand
- **WHEN** simulating playing Rage
- **THEN** base block gain SHALL be 3
- **AND** final block gain SHALL be reduced by 25% (Frail modifier)
- **AND** simulated block gain SHALL be ~2 (3 × 0.75)

#### Scenario: Rage stacks with existing block
- **GIVEN** player has 10 block currently
- **AND** player has max_energy of 3
- **AND** player has Rage in hand
- **WHEN** simulating playing Rage
- **THEN** block gain SHALL be 3
- **AND** state.player_block SHALL be 13 (10 + 3) after simulation

---

### Requirement: X-Card Detection in Simulation

The combat simulation SHALL detect X-cards and trigger dynamic calculation when:

1. The card has `is_x_damage=True` or `is_x_block=True` in CARD_METADATA
2. The card's base damage/block is 0 (Communication Mod doesn't provide these values)
3. The card is being evaluated for play in beam search

The simulation SHALL:
- Normalize card_id by removing '+' suffix (handle upgraded cards)
- Match against known X-card IDs
- Call appropriate calculation method
- Fall back to 0 if card is unrecognized

#### Scenario: Detect Body Slam (unupgraded)
- **GIVEN** a Card with card_id='Body Slam'
- **WHEN** checking if card is X-damage
- **THEN** system SHALL match 'Body Slam' in X-card list
- **AND** SHALL call `_calculate_x_damage()`
- **AND** SHALL return player_block value

#### Scenario: Detect Body Slam+ (upgraded)
- **GIVEN** a Card with card_id='Body Slam+'
- **WHEN** checking if card is X-damage
- **THEN** system SHALL normalize to 'Body Slam' (remove '+')
- **AND** SHALL match in X-card list
- **AND** SHALL treat same as unupgraded version

#### Scenario: Unknown card returns 0
- **GIVEN** a Card with card_id='UnknownCard'
- **AND** base_damage is 0
- **WHEN** checking if card is X-damage
- **THEN** system SHALL NOT match in X-card list
- **AND** SHALL return 0 (fallback behavior)
- **AND** SHALL NOT crash

---

### Requirement: Beam Search Integration

The beam search combat planner SHALL use dynamically calculated X-card values in both FastScore and FullSim evaluation.

**FastScore** (quick evaluation):
- Calculate X-card values for scoring
- Prioritize X-cards when conditions are favorable
- Example: Body Slam gets high FastScore when player_block > 15

**FullSim** (complete simulation):
- Use X-card calculations in state transitions
- Propagate X-card effects through multi-turn simulations
- Example: Rage increases block, which makes Body Slam stronger next turn

#### Scenario: FastScore prioritizes Body Slam
- **GIVEN** player has 25 block
- **AND** hand contains Body Slam (X-card) and Strike (6 damage)
- **WHEN** calculating FastScore for both cards
- **THEN** Body Slam score SHALL be higher (~50 for 25 damage)
- **AND** Strike score SHALL be lower (~12 for 6 damage)
- **AND** beam search SHALL prefer Body Slam

#### Scenario: FullSim simulates Rage chain
- **GIVEN** player has max_energy=3, 0 block
- **AND** hand contains Rage and Body Slam
- **WHEN** running FullSim for sequence [Rage, Body Slam]
- **THEN** Turn 1: Rage gains 3 block → player_block=3
- **AND** Turn 2: Body Slam deals 3 damage
- **AND** sequence score SHALL reflect the combo potential

#### Scenario: Whirlwind AOE in FastScore
- **GIVEN** player has max_energy=3
- **AND** there are 3 monsters
- **AND** hand contains Whirlwind
- **WHEN** calculating FastScore
- **THEN** Whirlwind base_damage SHALL be 3
- **AND** AOE multiplier SHALL apply (3 monsters × 3 damage = 9)
- **AND** Whirlwind SHALL score higher than single-target attacks

---

### Requirement: Upgraded Card Handling

The system SHALL handle upgraded versions of X-cards (cards with '+' suffix) correctly.

**Rules**:
1. Remove '+' suffix when matching card IDs
2. Use same calculation formula for base and upgraded versions
3. Note: Some X-cards have better scaling when upgraded (can add later)

#### Scenario: Body Slam+ same as Body Slam
- **GIVEN** card_id='Body Slam+'
- **WHEN** normalizing for calculation
- **THEN** system SHALL strip '+' to get 'Body Slam'
- **AND** SHALL use same formula: damage = player_block
- **AND** upgraded version SHALL NOT have different calculation (currently)

#### Scenario: Rage+ same as Rage
- **GIVEN** card_id='Rage+'
- **WHEN** normalizing for calculation
- **THEN** system SHALL strip '+' to get 'Rage'
- **AND** SHALL use same formula: block = max_energy

#### Scenario: Whirlwind+ same as Whirlwind
- **GIVEN** card_id='Whirlwind+'
- **WHEN** normalizing for calculation
- **THEN** system SHALL strip '+' to get 'Whirlwind'
- **AND** SHALL use same formula: damage = max_energy

---

### Requirement: Fallback Behavior

The system SHALL fail gracefully when encountering unrecognized or malformed X-cards.

**Fallback Rules**:
1. Return 0 for unknown cards (safe default)
2. Log warnings for cards with `is_x_damage=True` but no calculation logic
3. Never crash due to missing X-card logic
4. Allow game to continue (just with potentially suboptimal play)

#### Scenario: Unknown X-card returns 0
- **GIVEN** a card marked `is_x_damage=True` in CARD_METADATA
- **AND** no calculation logic exists for this card
- **WHEN** simulating this card
- **THEN** system SHALL return 0 for damage
- **AND** system SHALL log a warning (if in debug mode)
- **AND** game SHALL continue without crashing

#### Scenario: Missing game state returns 0
- **GIVEN** Body Slam calculation needs state.player_block
- **AND** state object is None or malformed
- **WHEN** attempting to calculate damage
- **THEN** system SHALL catch the error
- **AND** return 0 as safe fallback
- **AND** game SHALL continue

#### Scenario: Division by zero protection
- **GIVEN** a formula that divides by game state (e.g., block // 10)
- **AND** the divisor is 0
- **WHEN** performing calculation
- **THEN** system SHALL handle gracefully
- **AND** return a sensible default (e.g., base value)
- **AND** NOT crash with ZeroDivisionError

