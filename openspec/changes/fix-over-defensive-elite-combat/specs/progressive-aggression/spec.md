# progressive-aggression Specification

## Purpose
Implement turn-based aggression scaling that front-loads maximum damage early in elite fights, then pivots to defensive play if the rush strategy fails.

## ADDED Requirements

### Requirement: Turn-Based Aggression Multiplier

The system SHALL apply an aggression multiplier that scales with turn number. Multiplier values SHALL be:

- **Turn 1-2**: 1.0 (maximum aggression)
- **Turn 3**: 0.6 (moderate aggression)
- **Turn 4**: 0.4 (reduced aggression)
- **Turn 5+**: 0.2 (minimal aggression, pivot to defense)

The multiplier SHALL scale the DAMAGE_WEIGHT in AGGRESSIVE mode, creating decreasing damage incentive over time.

#### Scenario: Turn 1 maximum aggression
- **GIVEN** AGGRESSIVE mode, turn 1
- **WHEN** scoring a 10-damage attack
- **THEN** base score: 10 × 5.0 = 50
- **AND** with multiplier 1.0: total = 50 × 1.0 = 50 points

#### Scenario: Turn 3 reduced aggression
- **GIVEN** AGGRESSIVE mode, turn 3
- **WHEN** scoring a 10-damage attack
- **THEN** base score: 10 × 5.0 = 50
- **AND** with multiplier 0.6: total = 50 × 0.6 = 30 points

#### Scenario: Turn 5 minimal aggression
- **GIVEN** AGGRESSIVE mode, turn 5
- **WHEN** scoring a 10-damage attack
- **THEN** base score: 10 × 5.0 = 50
- **AND** with multiplier 0.2: total = 50 × 0.2 = 10 points

#### Scenario: Block weight inversely scaled
- **GIVEN** AGGRESSIVE mode, turn 5 (low aggression)
- **WHEN** scoring 5 block
- **THEN** block weight effectively increases as damage multiplier decreases
- **AND** block SHALL score relatively higher compared to damage

---

### Requirement: Enemy HP Percentage Evaluation

The system SHALL evaluate enemy remaining HP percentage to determine if the rush strategy is succeeding. Evaluation SHALL:

1. Calculate total current HP of all monsters as percentage of max HP
2. If HP < 30%: Rush succeeding, maintain aggression
3. If HP 30-50%: Rush uncertain, moderate aggression
4. If HP > 50% after turn 3: Rush failing, pivot to defense

HP-awareness prevents blind aggression when the fight isn't going well.

#### Scenario: Low HP, maintain aggression
- **GIVEN** turn 3, enemy at 25% HP (almost dead)
- **WHEN** evaluating rush progress
- **THEN** aggression multiplier SHALL remain at 1.0 (keep pressing)
- **AND** SHALL NOT reduce despite being turn 3

#### Scenario: Medium HP, moderate aggression
- **GIVEN** turn 3, enemy at 40% HP
- **WHEN** evaluating rush progress
- **THEN** aggression multiplier SHALL be 0.6 (standard turn 3)
- **AND** slight reduction in damage priority

#### Scenario: High HP after turn 3, pivot defensive
- **GIVEN** turn 3, enemy at 60% HP (rush failing)
- **WHEN** evaluating rush progress
- **THEN** aggression multiplier SHALL drop to 0.2 (pivot to defense)
- **AND** damage SHALL be deprioritized significantly

#### Scenario: Turn 1 ignores HP
- **GIVEN** turn 1, any enemy HP %
- **WHEN** setting aggression
- **THEN** multiplier SHALL always be 1.0 (turn 1 always max aggression)

---

### Requirement: Defensive Pivot on Failed Rush

When the rush strategy is failing (enemy HP > 50% after turn 3), the system SHALL pivot to defensive play. The pivot SHALL:

1. Switch to BALANCED mode weights
2. Increase BLOCK_WEIGHT to 1.5 or higher
3. Decrease DAMAGE_WEIGHT to 2.0 or lower
4. Accept that the fight will be long, prioritize survival

This prevents the AI from suicidally continuing a failed rush.

#### Scenario: Failed rush triggers pivot
- **GIVEN** turn 3, enemy HP > 50%
- **WHEN** selecting combat mode
- **THEN** combat_mode SHALL switch from AGGRESSIVE to BALANCED
- **AND** DAMAGE_WEIGHT SHALL drop from 5.0 → 2.0
- **AND** BLOCK_WEIGHT SHALL rise from 0.5 → 1.5

#### Scenario: Pivot persists for remainder of fight
- **GIVEN** pivot triggered on turn 3
- **WHEN** turn advances to 4, 5, 6...
- **THEN** combat_mode SHALL remain BALANCED
- **AND** SHALL NOT revert to AGGRESSIVE

#### Scenario: Successful rush never pivots
- **GIVEN** enemy at 20% HP on turn 3
- **WHEN** evaluating progress
- **THEN** pivot SHALL NOT be triggered
- **AND** AGGRESSIVE mode SHALL continue until kill

#### Scenario: Pivot prevents suicide
- **GIVEN** turn 3, player at 15 HP, enemy at 70% HP
- **WHEN** pivot triggers
- **THEN** subsequent turns SHALL prioritize block
- **AND** AI SHALL try to survive despite losing the race

---

### Requirement: Kill Maintenance Bonus

If enemy HP drops below 30% at any point, the system SHALL apply a "finish them off" bonus that maintains maximum aggression until the kill. This bonus SHALL:

1. Override turn-based aggression reduction
2. Keep multiplier at 1.0 until enemy is dead
3. Prevent the AI from "letting up" when victory is close

This ensures the AI doesn't waste turns getting conservative when the enemy is almost dead.

#### Scenario: Low HP triggers kill maintenance
- **GIVEN** turn 4, enemy at 25% HP
- **WHEN** evaluating aggression
- **THEN** multiplier SHALL override turn 4 default (0.4)
- **AND** SHALL use 1.0 instead (kill maintenance)
- **AND** SHALL stay max aggressive until kill

#### Scenario: Kill maintenance persists
- **GIVEN** enemy at 25% HP on turn 4
- **AND** only deal 10% damage that turn (enemy at 15%)
- **WHEN** turn advances to 5
- **THEN** kill maintenance SHALL still be active
- **AND** multiplier SHALL remain 1.0

#### Scenario: Kill resets after death
- **GIVEN** kill maintenance active (enemy at 20%)
- **AND** sequence kills the monster
- **WHEN** next monster(s) remain
- **THEN** kill maintenance SHALL reset
- **AND** aggression SHALL follow normal turn-based rules

#### Scenario: High HP no kill maintenance
- **GIVEN** turn 4, enemy at 45% HP
- **WHEN** evaluating aggression
- **THEN** kill maintenance SHALL NOT trigger
- **AND** multiplier SHALL use turn 4 default (0.4)

---

### Requirement: Aggression State Tracking

The system SHALL track the current aggression state across turns. States SHALL be:

1. **RUSHING**: Turn 1-2, max aggression, ignore HP
2. **EVALUATING**: Turn 3-4, check HP%, adjust accordingly
3. **FINISHING**: HP < 30%, max aggression to secure kill
4. **FAILED_PIVOT**: HP > 50% after turn 3, switch to defensive

State transitions SHALL be deterministic based on turn number and enemy HP percentage.

#### Scenario: Initial state is RUSHING
- **GIVEN** combat starts (turn 1)
- **WHEN** determining aggression state
- **THEN** state SHALL be RUSHING
- **AND** multiplier SHALL be 1.0

#### Scenario: Transition to EVALUATING
- **GIVEN** turn 2 ends, turn 3 begins
- **WHEN** updating aggression state
- **THEN** state SHALL transition from RUSHING to EVALUATING
- **AND** HP% check SHALL determine next state

#### Scenario: Transition to FINISHING
- **GIVEN** EVALUATING state
- **AND** enemy HP drops below 30%
- **WHEN** updating aggression state
- **THEN** state SHALL transition to FINISHING
- **AND** multiplier SHALL lock at 1.0

#### Scenario: Transition to FAILED_PIVOT
- **GIVEN** EVALUATING state (turn 3)
- **AND** enemy HP > 50%
- **WHEN** updating aggression state
- **THEN** state SHALL transition to FAILED_PIVOT
- **AND** combat_mode SHALL switch to BALANCED

---

### Requirement: Multi-Monster HP Aggregation

For multi-monster fights, enemy HP percentage SHALL aggregate all monsters. Calculation SHALL:

1. Sum current HP of all monsters
2. Sum max HP of all monsters
3. Calculate percentage: current_max / total_max
4. Use aggregated % for state transitions

This ensures the AI recognizes progress in multi-enemy fights.

#### Scenario: Two monsters HP aggregation
- **GIVEN** 2 monsters: Monster A (20/50 HP), Monster B (30/50 HP)
- **WHEN** calculating aggregate HP%
- **THEN** total current: 20 + 30 = 50
- **AND** total max: 50 + 50 = 100
- **AND** HP%: 50/100 = 50%

#### Scenario: One low, one high
- **GIVEN** 2 monsters: Monster A (5/50 HP), Monster B (45/50 HP)
- **WHEN** calculating aggregate HP%
- **THEN** total current: 5 + 45 = 50
- **AND** total max: 50 + 50 = 100
- **AND** HP%: 50% (not FINISHING threshold)

#### Scenario: One dead, one healthy
- **GIVEN** 2 monsters: Monster A (0/50 HP, dead), Monster B (35/50 HP)
- **WHEN** calculating aggregate HP%
- **THEN** only alive monsters counted
- **AND** HP%: 35/50 = 70%
- **AND** FINISHING not triggered (one dead, but other healthy)

#### Scenario: All monsters low HP
- **GIVEN** 3 monsters: (8/40, 10/40, 12/40)
- **WHEN** calculating aggregate HP%
- **THEN** total current: 8 + 10 + 12 = 30
- **AND** total max: 40 + 40 + 40 = 120
- **AND** HP%: 30/120 = 25%
- **AND** FINISHING state SHALL be triggered

---

### Requirement: Turn Counter Integration

The progressive aggression system SHALL integrate with the existing turn counter in DecisionContext. The system SHALL:

1. Read current turn from context.turn
2. Calculate aggression multiplier based on turn
3. Apply multiplier to damage scoring
4. Log turn number and multiplier for debugging

Turn counter SHALL be 1-indexed (first combat turn is turn 1).

#### Scenario: Turn 1 from context
- **GIVEN** DecisionContext with turn=1
- **WHEN** calculating aggression multiplier
- **THEN** multiplier SHALL be 1.0 (turn 1 max aggression)

#### Scenario: Turn 3 from context
- **GIVEN** DecisionContext with turn=3
- **AND** enemy HP at 40% (EVALUATING state)
- **WHEN** calculating aggression multiplier
- **THEN** multiplier SHALL be 0.6 (turn 3 moderate)

#### Scenario: Turn counter increments
- **GIVEN** turn 1 ends, turn 2 begins
- **WHEN** context updates turn
- **THEN** turn SHALL be 2
- **AND** multiplier SHALL remain 1.0 (turn 2 still max aggression)

#### Scenario: Turn logging
- **GIVEN** any turn number
- **WHEN** applying aggression multiplier
- **THEN** logger SHALL output: "Turn {turn}, aggression multiplier: {mult}, state: {state}"
