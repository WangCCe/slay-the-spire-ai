# AI Combat Scoring - Multi-Monster Support

## ADDED Requirements

### Requirement: Monster Count Detection in Outcome Score

The `calculate_outcome_score()` function in `spirecomm/ai/heuristics/simulation.py` MUST detect the number of alive monsters in the initial combat state and apply adaptive damage weighting.

#### Scenario: Multi-monster combat with 3 enemies

**Given** a combat state with 3 alive monsters (e.g., 3 Slavers, Fungi Beast + 2 Fungi, etc.)
**When** calculating outcome score for a card sequence
**Then** the scoring system MUST:
- Detect `num_monsters = 3` from `initial_state.monsters`
- Apply `damage_multiplier = 1.8` to total damage
- Log `[OUTCOME_MULTIPLIER] Applied 1.8× damage weight`

#### Scenario: Single monster combat

**Given** a combat state with 1 alive monster
**When** calculating outcome score
**Then** the scoring system MUST apply `damage_multiplier = 1.0` (baseline)

**Implementation Details**:
- Count alive monsters from `initial_state.monsters` (filtering where `not m['is_gone']`)
- Apply damage multiplier based on count:
  - 1 monster: `damage_multiplier = 1.0`
  - 2 monsters: `damage_multiplier = 1.3`
  - 3+ monsters: `damage_multiplier = 1.8`

**Example**:
```python
num_monsters = len([m for m in initial_state.monsters if not m['is_gone']])

if num_monsters >= 3:
    damage_multiplier = 1.8
elif num_monsters == 2:
    damage_multiplier = 1.3
else:
    damage_multiplier = 1.0

score += total_damage * weights['DAMAGE_WEIGHT'] * damage_multiplier
```

**Rationale**: FastScore applies AOE multiplier but Outcome Score doesn't, causing defensive cards to outscore damage in multi-monster fights.

---

### Requirement: AOE Card Bonus in Multi-Monster Scenarios

When AOE cards are played in multi-monster fights, the scoring system MUST apply explicit bonus points.

#### Scenario: Playing Cleave against 3 Slavers

**Given** a combat state with 3 alive Slavers on Floor 6
**And** the beam search evaluates a sequence containing Cleave
**When** calculating the outcome score
**Then** the scoring system MUST:
- Detect Cleave as an AOE card
- Apply +40 bonus for 3-monster AOE usage
- Log `[OUTCOME_AOE] +40 for Cleave in 3-monster fight`

#### Scenario: Playing Whirlwind against 2 monsters

**Given** a combat state with 2 alive monsters
**And** the beam search evaluates a sequence containing Whirlwind
**When** calculating the outcome score
**Then** the scoring system MUST apply +20 bonus for 2-monster AOE usage

**Implementation Details**:
- Detect AOE cards: Cleave, Whirlwind, Thunderclap, Immolate
- Apply bonus based on monster count:
  - 2 monsters: +20 points per AOE card
  - 3+ monsters: +40 points per AOE card
- Add debug logging: `[OUTCOME_AOE] +{bonus} for {card_id} in {num_monsters}-monster fight`

**Example**:
```python
aoe_cards = ['Cleave', 'Whirlwind', 'Thunderclap', 'Immolate']

for action in sequence:
    if isinstance(action, PlayCardAction):
        card_id = action.card.card_id

        if card_id in aoe_cards and num_monsters >= 2:
            aoe_bonus = 40 if num_monsters >= 3 else 20
            score += aoe_bonus
            logger.info(f"[OUTCOME_AOE] +{aoe_bonus} for {card_id} in {num_monsters}-monster fight")
```

**Rationale**: AOE cards are critical for multi-monster survival but currently undervalued in final scoring.

---

### Requirement: Floor 6-7 Special AOE Priority

During Floors 6-7 (highest death floor), the scoring system MUST apply extra AOE priority to reduce death spike.

#### Scenario: Floor 6 combat with 3 Slavers

**Given** Floor 6 (highest death floor: 24.5%)
**And** 3 alive monsters (e.g., 3 Slavers)
**When** calculating outcome score
**Then** the scoring system MUST:
- Apply enhanced `damage_multiplier = 2.2` (base 1.8 + floor bonus 0.4)
- Log `[FLOOR6_AOE] Enhanced priority on Floor 6: 2.2×`

#### Scenario: Floor 7 combat with 2 monsters

**Given** Floor 7 (high death floor: 14.9%)
**And** 2 alive monsters
**When** calculating outcome score
**Then** the scoring system MUST apply `damage_multiplier = 1.5` (base 1.3 + floor bonus 0.2)

**Implementation Details**:
- Detect Floor 6-7 from `context.floor`
- Apply enhanced AOE multiplier:
  - Floor 6-7, 3+ monsters: `damage_multiplier = 2.2`
  - Floor 6-7, 2 monsters: `damage_multiplier = 1.5`
- Add debug logging: `[FLOOR6_AOE] Enhanced priority on Floor {context.floor}`

**Example**:
```python
# Base multiplier from R-OUTCOME-001
damage_multiplier = 1.0  # (from monster count logic)

# Floor 6-7 enhancement
if context.floor in [6, 7] and num_monsters >= 2:
    floor_bonus = 0.4 if num_monsters >= 3 else 0.2
    damage_multiplier += floor_bonus
    logger.info(f"[FLOOR6_AOE] Enhanced priority on Floor {context.floor}: {damage_multiplier}×")
```

**Rationale**: Floor 6 has 24.5% death rate (23/92 games), primarily due to lack of AOE prioritization when deck size is small (4-6 cards).

---

### Requirement: Scoring Consistency Logging

The scoring system MUST log all multi-monster adjustments for debugging and validation.

#### Scenario: Logging multi-monster score calculation

**Given** a combat state with 3 monsters on Floor 6
**When** calculating outcome score with multi-monster bonuses
**Then** the scoring system MUST log:
- `[OUTCOME_MONSTERS] Detected 3 alive monsters`
- `[OUTCOME_MULTIPLIER] Applied 2.2× damage weight (base: 2.0)`
- `[FLOOR6_AOE] Enhanced priority on Floor 6: 2.2×`

**Implementation Details**:
- Log monster count detection: `[OUTCOME_MONSTERS] Detected {num_monsters} alive monsters`
- Log damage multiplier: `[OUTCOME_MULTIPLIER] Applied {damage_multiplier}× damage weight`
- Log AOE bonuses: `[OUTCOME_AOE] +{bonus} for {card_id}`
- Log Floor 6-7 special handling: `[FLOOR6_AOE] Floor {floor} enhanced priority`

**Example**:
```python
logger.info(f"[OUTCOME_MONSTERS] Detected {num_monsters} alive monsters")
logger.info(f"[OUTCOME_MULTIPLIER] Applied {damage_multiplier}× damage weight (base: {weights['DAMAGE_WEIGHT']})")
```

**Rationale**: Enables validation that multi-monster scoring is working correctly during testing.

---

## MODIFIED Requirements

### Requirement: Outcome Score Calculation

The `calculate_outcome_score()` function in `simulation.py` MUST apply monster-count-aware damage weighting instead of flat damage scoring.

#### Scenario: Flat scoring before modification (v3.4.7)

**Given** a combat state with 3 monsters
**And** a card sequence dealing 20 damage total
**When** calculating outcome score with current implementation
**Then** the score contribution is:
- `score = 20 * 2.0 = 40` (flat 2.0× weight, no monster consideration)

#### Scenario: Adaptive scoring after modification (v3.5.1)

**Given** a combat state with 3 monsters on Floor 6
**And** a card sequence dealing 20 damage total
**When** calculating outcome score with new implementation
**Then** the score contribution is:
- `score = 20 * 2.0 * 2.2 = 88` (1.8× for 3 monsters + 0.4× Floor 6 bonus)

**BEFORE** (v3.4.7):
```python
# Line 679-682: Flat damage scoring
total_damage = sum(m['hp'] for m in initial_state.monsters) - \
              sum(m['hp'] for m in final_state.monsters)
score += total_damage * weights['DAMAGE_WEIGHT']
```

**AFTER** (v3.5.1):
```python
# Count alive monsters for adaptive scoring
num_monsters = len([m for m in initial_state.monsters if not m['is_gone']])

# Calculate damage with monster-count-aware multiplier
if context.floor in [6, 7] and num_monsters >= 3:
    damage_multiplier = 2.2
elif context.floor in [6, 7] and num_monsters == 2:
    damage_multiplier = 1.5
elif num_monsters >= 3:
    damage_multiplier = 1.8
elif num_monsters == 2:
    damage_multiplier = 1.3
else:
    damage_multiplier = 1.0

total_damage = sum(m['hp'] for m in initial_state.monsters) - \
              sum(m['hp'] for m in final_state.monsters)

score += total_damage * weights['DAMAGE_WEIGHT'] * damage_multiplier

logger.info(f"[OUTCOME_SCORE] Damage: {total_damage}, Monsters: {num_monsters}, "
           f"Multiplier: {damage_multiplier}×, Score: {total_damage * weights['DAMAGE_WEIGHT'] * damage_multiplier}")
```

**Rationale**: Brings Outcome Score in line with FastScore's multi-monster bonuses, fixing the scoring mismatch that causes defensive cards to outscore damage in multi-monster fights.

---

## DEPRECATED Requirements

None. This change adds new functionality without removing existing behavior.

---

## Success Metrics

### Primary Metric
- **Floor 6 Death Rate**: Decrease from 24.5% (23/92 games) to <15% after 50 validation games

### Secondary Metrics
- **AOE Card Usage**: AOE cards prioritized in >70% of 3-monster fights
- **Average HP Loss (Floor 6-7)**: Decrease from current baseline
- **Win Rate**: Target 5-10% (baseline: 0%)

### Validation Criteria
- No increase in Floors 1-3 death rate (ensure not over-aggressive early)
- AOE cards logged as prioritized in multi-monster fights
- Damage multiplier logged correctly in all multi-monster scenarios
