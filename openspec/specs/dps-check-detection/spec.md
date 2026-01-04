# dps-check-detection Specification

## Purpose
TBD - created by archiving change fix-over-defensive-elite-combat. Update Purpose after archive.
## Requirements
### Requirement: Fast-Kill Calculation

The system SHALL calculate whether the current hand can kill all monsters in 1-2 turns. Calculation SHALL:

1. Sum current HP of all alive monsters
2. Calculate maximum damage output from playable cards
3. Include Vulnerable/Weak debuffs in damage calculation
4. Consider multi-hit attacks vs multiple monsters
5. Return: (can_kill: bool, turns_to_kill: int)

This enables the AI to recognize when lethal is achievable.

#### Scenario: One-turn kill detected
- **GIVEN** monsters with total 50 HP remaining
- **AND** hand can deal 60 damage this turn
- **WHEN** checking fast-kill
- **THEN** can_kill SHALL be True
- **AND** turns_to_kill SHALL be 1

#### Scenario: Two-turn kill detected
- **GIVEN** monsters with total 80 HP remaining
- **AND** hand can deal 50 damage this turn
- **WHEN** checking fast-kill
- **THEN** can_kill SHALL be True
- **AND** turns_to_kill SHALL be 2 (50 this turn + 50 next turn)

#### Scenario: Cannot fast kill
- **GIVEN** monsters with total 100 HP remaining
- **AND** hand can deal 30 damage this turn
- **WHEN** checking fast-kill
- **THEN** can_kill SHALL be False
- **AND** turns_to_kill SHALL be 999 (or similar sentinel value)

#### Scenario: Vulnerable increases damage
- **GIVEN** monster with 40 HP
- **AND** Bash played (applies Vulnerable)
- **AND** Heavy Blade can deal 20 base damage
- **WHEN** calculating damage with Vulnerable
- **THEN** effective damage SHALL be 30 (20 × 1.5)
- **AND** fast-kill calculation SHALL include this bonus

---

### Requirement: Lethal Sequence Bonus

When a fast-kill is detected (can_kill=True), beam search SHALL apply a **LETHAL_BONUS = 300 points** to sequences that achieve the kill. This bonus SHALL:

1. Only apply when kill is achievable in the sequence
2. Be added on top of normal damage/kill bonuses
3. Make lethal sequences score significantly higher than non-lethal
4. Prioritize finding the winning line

The lethal bonus helps beam search "see" the value of killing even if it requires risky plays.

#### Scenario: One-turn kill receives lethal bonus
- **GIVEN** fast-kill detected (1 turn)
- **AND** sequence deals lethal damage (kills all monsters)
- **WHEN** scoring the sequence
- **THEN** score SHALL include +300 LETHAL_BONUS
- **AND** sequence SHALL score significantly higher than non-lethal alternatives

#### Scenario: Non-lethal sequence no bonus
- **GIVEN** fast-kill detected in theory
- **BUT** sequence deals only 40% of monster HP
- **WHEN** scoring the sequence
- **THEN** score SHALL NOT include LETHAL_BONUS
- **AND** shall score lower than lethal sequences

#### Scenario: Lethal bonus outweighs defensive safety
- **GIVEN** two sequences:
  - Sequence A (Lethal): 50 damage, kills all, 20 expected HP loss
  - Sequence B (Safe): 20 damage, no kills, 5 expected HP loss
- **WHEN** scoring both with fast-kill detected
- **THEN** Sequence A: 50×5.0 - 20×4.0 + 300 = 250 - 80 + 300 = 470 points
- **AND** Sequence B: 20×5.0 - 5×4.0 = 100 - 20 = 80 points
- **AND** Sequence A SHALL be preferred (lethal bonus dominates)

#### Scenario: Two-turn kill bonus reduced
- **GIVEN** fast-kill detected (2 turns)
- **AND** sequence kills on turn 1 of 2
- **WHEN** scoring
- **THEN** LETHAL_BONUS SHALL be +150 (half of one-turn bonus)
- **AND** still strongly incentivizes progressing toward kill

---

### Requirement: Damage Potential Estimation

The system SHALL estimate maximum damage output from the current hand. Estimation SHALL:

1. Identify all playable attack cards
2. Calculate base damage for each attack
3. Apply debuffs (Vulnerable: 1.5×, Weak: 0.75×)
4. Consider Strength bonuses
5. Sum total potential damage
6. Return estimate as integer

This estimation is used for fast-kill detection.

#### Scenario: Simple damage calculation
- **GIVEN** hand: Strike (6), Strike (6), Bash (8)
- **AND** no debuffs/buffs active
- **WHEN** estimating damage potential
- **THEN** estimate SHALL be 20 (6 + 6 + 8)

#### Scenario: Vulnerable increases estimate
- **GIVEN** hand: Bash (8 + Vulnerable), Heavy Blade (14)
- **AND** Vulnerable is active on target (1.5× damage)
- **WHEN** estimating damage potential
- **THEN** Heavy Blade damage: 14 × 1.5 = 21
- **AND** total estimate: 8 + 21 = 29

#### Scenario: Strength increases estimate
- **GIVEN** hand: 3× Strike (6 each)
- **AND** player has 5 Strength
- **WHEN** estimating damage potential
- **THEN** each Strike: 6 + 5 = 11 damage
- **AND** total estimate: 11 × 3 = 33

#### Scenario: Energy limits considered
- **GIVEN** hand: 4× Strike (6 each), 3 energy available
- **WHEN** estimating damage potential
- **THEN** only 3× Strike SHALL be counted (18 damage)
- **AND** 4th Strike SHALL NOT be included (not playable this turn)

---

### Requirement: Multi-Target Kill Detection

Fast-kill detection SHALL properly handle multi-target scenarios. The system SHALL:

1. Check if total damage can kill all monsters combined
2. Consider AOE attacks (Cleave, Whirlwind)
3. Evaluate single-target focus fire vs AOE
4. Return True if ANY killing strategy is achievable

This ensures the AI recognizes when AOE can clear the board.

#### Scenario: AOE kill detected
- **GIVEN** 3 monsters with 20, 25, 30 HP (total 75)
- **AND** hand has Whirlwind with 10 energy (70 damage to all)
- **WHEN** checking fast-kill
- **THEN** can_kill SHALL be True (AOE kills all)
- **AND** turns_to_kill SHALL be 1

#### Scenario: Focus fire kill detected
- **GIVEN** 2 monsters with 40 HP each
- **AND** hand can deal 50 damage single target
- **WHEN** checking fast-kill
- **THEN** can_kill SHALL be True (kill one, other next turn)
- **AND** turns_to_kill SHALL be 2

#### Scenario: Cannot kill all
- **GIVEN** 3 monsters with 30 HP each (90 total)
- **AND** hand can deal 50 damage total
- **WHEN** checking fast-kill
- **THEN** can_kill SHALL be False
- **AND** turns_to_kill SHALL be >2

#### Scenario: Cleave kills weak monsters
- **GIVEN** 3 monsters with 10, 15, 60 HP
- **AND** hand has Cleave (8 damage to all) + attacks for 60 damage
- **WHEN** checking fast-kill
- **THEN** Cleave kills 2 weak monsters (10+15=25 HP)
- **AND** focus fire kills big monster
- **AND** can_kill SHALL be True (2 turns)

---

### Requirement: Kill Bonus Integration

The lethal bonus SHALL integrate with existing kill bonuses. The total kill reward SHALL be:

```
total_kill_bonus = (monsters_killed × KILL_BONUS) + LETHAL_BONUS (if applicable)
```

For AGGRESSIVE mode, KILL_BONUS=200, LETHAL_BONUS=300.

#### Scenario: Single monster kill + lethal
- **GIVEN** AGGRESSIVE mode
- **AND** sequence kills last monster (lethal)
- **WHEN** calculating kill bonus
- **THEN** total: 1×200 + 300 = 500 points

#### Scenario: Two monsters killed + lethal
- **GIVEN** AGGRESSIVE mode
- **AND** sequence kills 2 monsters (one lethal, one incidental)
- **WHEN** calculating kill bonus
- **THEN** total: 2×200 + 300 = 700 points

#### Scenario: No lethal, just kills
- **GIVEN** AGGRESSIVE mode
- **AND** sequence kills 1 monster but not all
- **WHEN** calculating kill bonus
- **THEN** total: 1×200 + 0 = 200 points (no LETHAL_BONUS)

---

### Requirement: Fast-Kill Caching

Fast-kill detection SHALL be cached per turn to avoid redundant calculation. The system SHALL:

1. Calculate fast-kill once at turn start
2. Store (can_kill, turns_to_kill) in DecisionContext
3. Reuse for all beam search candidates that turn
4. Recalculate when turn changes or hand changes

This maintains performance while providing accurate lethal detection.

#### Scenario: Fast-kill calculated once per turn
- **GIVEN** turn 1 with specific hand
- **WHEN** DecisionContext is created
- **THEN** fast-kill SHALL be calculated once
- **AND** cached in context.fast_kill_result

#### Scenario: Fast-kill reused in beam search
- **GIVEN** cached fast_kill = (True, 1)
- **WHEN** scoring 100 beam search candidates
- **THEN** all 100 SHALL use cached (True, 1)
- **AND** fast-kill SHALL NOT be recalculated for each candidate

#### Scenario: Recalculate on turn change
- **GIVEN** turn 1 fast_kill = (True, 1)
- **AND** turn advances to turn 2
- **WHEN** new beam search begins
- **THEN** fast-kill SHALL be recalculated with turn 2 hand
- **AND** cache SHALL be updated

#### Scenario: Recalculate on card draw
- **GIVEN** turn 1 fast_kill = (False, 999)
- **AND** player plays Battle Trance (draws 3 cards)
- **WHEN** hand changes mid-turn
- **THEN** fast-kill cache SHALL be invalidated
- **AND** SHALL be recalculated with new hand

---

### Requirement: Overkill Penalty Avoidance

The system SHALL not penalize overkill damage. When calculating if a sequence is lethal:

1. Stop counting damage once monster HP reaches 0
2. Excess damage is wasted but not penalized
3. Focus on "is lethal" not "efficient lethal"

This prevents the AI from avoiding lethal combos due to overkill.

#### Scenario: Overkill not penalized
- **GIVEN** monster with 10 HP
- **AND** attack deals 30 damage (20 overkill)
- **WHEN** scoring lethal sequence
- **THEN** overkill damage SHALL be ignored (10 effective)
- **AND** sequence still receives LETHAL_BONUS
- **AND** no penalty for wasting 20 damage

#### Scenario: Inefficient lethal still rewarded
- **GIVEN** two lethal sequences:
  - Sequence A: Perfect damage (kills with exactly 10 damage)
  - Sequence B: Overkill (kills with 30 damage)
- **WHEN** comparing scores
- **THEN** both SHALL receive LETHAL_BONUS
- **AND** Sequence B SHALL score slightly higher (more damage)
- **AND** neither SHALL be penalized for inefficiency

