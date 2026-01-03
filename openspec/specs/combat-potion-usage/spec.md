# combat-potion-usage Specification

## Purpose
TBD - created by archiving change improve-combat-potion-usage. Update Purpose after archive.
## Requirements
### Requirement: Potion Action Expansion
The beam search combat planner SHALL include usable potions in its action expansion at depth 0. The planner SHALL:

1. Collect all usable potions from the player's inventory (can_use=True)
2. Score each potion based on its expected value in the current combat situation
3. Select the highest-scored potion for inclusion in the beam search action space
4. Limit potion actions to depth=0 only (first action of the turn) to prevent exponential search growth
5. Limit to maximum 1 potion action per turn (consistent with game mechanics)

Potion actions SHALL be evaluated alongside card actions in the two-stage expansion (FastScore → FullSim).

#### Scenario: Potion in dangerous elite fight
- **GIVEN** an elite fight with player at 40% HP and 2 monsters dealing 25 total damage
- **WHEN** the player has a Block Potion in inventory
- **THEN** the beam search SHALL include PotionAction in its action space at depth 0
- **AND** the potion SHALL receive a high FastScore (>30) due to danger level

#### Scenario: Multiple potions filtered to best
- **GIVEN** player has Healing Potion (score 50), Fire Potion (score 40), and Energy Potion (score 20)
- **WHEN** beam search expands actions at depth 0
- **THEN** only Healing Potion SHALL be included in the action space (highest score)

#### Scenario: No potions available
- **GIVEN** player has 0 potions in inventory
- **WHEN** beam search expands actions
- **THEN** the action space SHALL contain only card actions (no potion actions)

#### Scenario: Potion at depth > 0
- **GIVEN** beam search is expanding at depth 2 (second action in sequence)
- **WHEN** collecting actions for expansion
- **THEN** potions SHALL NOT be included (only at depth 0)

---

### Requirement: Potion Value Scoring
The combat planner SHALL score potions based on their expected impact on the combat outcome. Scoring SHALL consider:

1. **Potion type**: Healing, damage, block, or utility
2. **Player HP percentage**: Higher priority for healing when HP is low
3. **Incoming damage**: Higher priority for block/healing when damage is high
4. **Monster count and threat**: Higher priority for AOE/damage in multi-monster fights
5. **Room type**: Bonus for elite/boss fights (+15-25 points)

Scoring categories:
- **Healing potions**: +50 at HP<30%, +30 at HP<50% with high incoming damage
- **Damage potions**: +40 in elite/boss, +25 with ≥2 monsters, +20 when close to lethal
- **Block potions**: +35 when incoming damage > 40% of max HP
- **Utility potions**: +20 baseline in dangerous fights

#### Scenario: Healing potion at critical HP
- **GIVEN** player at 15 HP out of 80 max HP (18.75%)
- **WHEN** scoring a Healing Potion
- **THEN** the potion SHALL receive a score of at least 50 (critical HP threshold)

#### Scenario: Damage potion in elite fight
- **GIVEN** an elite fight with 3 monsters totaling 60 HP
- **WHEN** scoring a Fire Potion (20 damage)
- **AND** player has 70% HP
- **THEN** the potion SHALL receive a score of at least 65 (40 elite bonus + 25 multi-monster bonus)

#### Scenario: Block potion prevents lethal
- **GIVEN** player at 30 HP with 35 incoming damage this turn
- **WHEN** scoring a Block Potion (12 block)
- **THEN** the potion SHALL receive a score of at least 35 (prevents lethal damage)

#### Scenario: Utility potion in safe fight
- **GIVEN** a regular fight with 1 weak monster, player at 90% HP
- **WHEN** scoring an Entropy Potion (utility)
- **THEN** the potion SHALL receive a score of 0 or close to 0 (not worth using)

---

### Requirement: Potion Simulation
The combat simulator SHALL accurately simulate the effects of potion usage when evaluating action sequences. Simulation SHALL:

1. Apply damage potions: reduce target monster HP by potion's damage value
2. Apply block potions: increase player block by potion's block value
3. Apply healing potions: increase player HP by potion's heal value (capped at max_hp)
4. Apply special effects: Strength potions increase player_strength, etc.
5. Track potion usage in SimulationState (potions_used counter)
6. Apply debuffs/buffs if potion includes them (e.g., Weak potion)

The simulation SHALL be consistent with card effect simulation (same state modification pattern).

#### Scenario: Damage potion simulation
- **GIVEN** a monster with 45 HP and player uses Fire Potion (20 damage)
- **WHEN** simulating the potion action
- **THEN** the monster's HP in SimulationState SHALL be 25 (45 - 20)
- **AND** potions_used counter SHALL increment by 1

#### Scenario: Block potion simulation
- **GIVEN** player has 8 block and uses Block Potion (12 block)
- **WHEN** simulating the potion action
- **THEN** player_block in SimulationState SHALL be 20 (8 + 12)

#### Scenario: Healing potion capped at max
- **GIVEN** player at 70 HP out of 80 max HP and uses Strawberry (10 heal)
- **WHEN** simulating the potion action
- **THEN** player_hp in SimulationState SHALL be 80 (capped at max, not 80)

#### Scenario: Strength potion persists
- **GIVEN** player has 3 strength and uses Strength Potion (+2 strength)
- **WHEN** simulating the potion action
- **THEN** player_strength in SimulationState SHALL be 5 (3 + 2)
- **AND** the strength bonus SHALL persist through subsequent card simulations in the turn

---

### Requirement: Potion Targeting
For potions that require targeting (damage, debuff, etc.), the planner SHALL select targets consistent with threat-based targeting from the ai-combat spec:

1. **Damage potions**: Target highest-threat monster (considering damage intent, buffs, scaling)
2. **Debuff potions (Weak, Vulnerable)**: Target high-HP monsters to maximize debuff value
3. **Special-case potions**: Use logic appropriate to effect (e.g., Berserk for self-target)

Target selection SHALL use the same `_find_best_target()` logic as attack cards for consistency.

#### Scenario: Damage potion targets high-threat
- **GIVEN** Monster A intends 18 damage with 40 HP, Monster B intends 8 damage with 15 HP
- **WHEN** using a damage potion
- **THEN** the potion SHALL target Monster A (higher threat despite higher HP)

#### Scenario: AOE damage potion
- **GIVEN** an AOE damage potion (e.g., Explosive Potion)
- **WHEN** simulating the potion action
- **THEN** damage SHALL be applied to all monsters in SimulationState

#### Scenario: Debuff potion targets high-HP
- **GIVEN** a Vulnerable Potion and two monsters: Monster X (50 HP, 12 damage intent), Monster Y (20 HP, 15 damage intent)
- **WHEN** using the potion
- **THEN** the potion SHALL target Monster X (higher HP to maximize Vulnerable value)

---

### Requirement: Fallback Potion Usage
The OptimizedAgent SHALL include a fallback potion usage mechanism outside of beam search for situations where:

1. Beam search is not available (SimpleAgent mode, errors)
2. Combat danger level exceeds 0.6 (high danger threshold)
3. Room is an elite or boss fight (always consider potions)

The fallback `use_next_potion()` method SHALL be invoked when:
- Danger level > 0.6 regardless of room type
- OR room is Elite/Boss
- AND at least one usable potion is available

This ensures potions are used even if beam search fails or times out.

#### Scenario: Fallback in dangerous regular fight
- **GIVEN** a regular fight with danger level 0.75 (low HP, multiple monsters)
- **WHEN** beam search is unavailable or fails
- **THEN** the agent SHALL invoke `use_next_potion()` and use the highest-priority available potion

#### Scenario: No fallback in safe fight
- **GIVEN** a regular fight with danger level 0.3 (high HP, single weak monster)
- **WHEN** evaluating whether to use a potion
- **THEN** the agent SHALL NOT invoke `use_next_potion()` (danger threshold not met)

#### Scenario: Fallback in elite fight
- **GIVEN** an elite fight regardless of danger level
- **WHEN** the agent has usable potions
- **THEN** the agent SHALL invoke `use_next_potion()` (elite priority)

---

### Requirement: Potion Metadata
The Potion class SHALL include effect metadata needed for simulation and scoring:

1. **effect_type**: One of 'damage', 'heal', 'block', 'buff', 'debuff', 'utility'
2. **effect_value**: Numeric magnitude (e.g., 20 for Fire Potion)
3. **target_type**: One of 'monster', 'self', 'all_monsters', 'none'

If Communication Mod does not provide this data, the implementation SHALL include a lookup table mapping potion IDs to their effects.

#### Scenario: Potion metadata lookup
- **GIVEN** a potion with name "Fire Potion" and potion_id "FIRE_POTION"
- **WHEN** querying effect metadata
- **THEN** effect_type SHALL be 'damage'
- **AND** effect_value SHALL be 20
- **AND** target_type SHALL be 'monster'

#### Scenario: Metadata from Communication Mod
- **GIVEN** Communication Mod provides potion data with effect fields
- **WHEN** deserializing potion from JSON
- **THEN** Potion object SHALL include effect_type and effect_value from JSON

#### Scenario: Fallback lookup table
- **GIVEN** Communication Mod does not provide effect data
- **WHEN** creating Potion object from JSON
- **THEN** the implementation SHALL use a hardcoded lookup table to populate effect metadata

---

### Requirement: Conservation Incentive
The scoring function SHALL include a small penalty for using potions to prevent over-consumption in easy fights. This penalty SHALL:

1. Subtract 5-10 points from the action score for using any potion
2. Be overridden by the high bonus scores in dangerous situations (healing at low HP, elite fights, etc.)
3. Ensure potions are used when they provide clear value (>15-20 point net benefit)

The penalty creates a bias toward saving potions for later fights unless the current situation clearly warrants usage.

#### Scenario: Easy fight with potion
- **GIVEN** a safe fight with danger level 0.2, player at 90% HP, 1 weak monster
- **WHEN** beam search evaluates using a damage potion (base score 15)
- **THEN** the final score SHALL be ≤10 (15 - 5 conservation penalty)
- **AND** the potion action SHALL rank below most card actions

#### Scenario: Dangerous fight overrides penalty
- **GIVEN** a dangerous fight with player at 25% HP, incoming damage lethal
- **WHEN** beam search evaluates using a Healing Potion (base score 50)
- **THEN** the final score SHALL be ≥45 (50 - 5 conservation penalty)
- **AND** the potion action SHALL rank highly due to survival priority

#### Scenario: Elite fight overrides penalty
- **GIVEN** an elite fight with 3 monsters, damage potion base score 65
- **WHEN** evaluating the potion action
- **THEN** the final score SHALL be ≥60 (65 - 5 conservation penalty)
- **AND** the potion SHALL be selected for use

---

