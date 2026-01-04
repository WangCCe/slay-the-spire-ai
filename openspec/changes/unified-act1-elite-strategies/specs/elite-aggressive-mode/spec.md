## ADDED Requirements

### Requirement: Unified Act 1 Elite Strategy Framework

The system SHALL implement a unified elite combat strategy framework that applies specialized tactics for all Act 1 elites based on their unique mechanics. The framework SHALL:

1. Detect elite type using `_detect_elite_type()` method
2. Apply elite-specific scoring modifiers via `_apply_elite_strategy_override()`
3. Preserve existing Gremlin Nob SKILL penalty (v3.3.1)
4. Implement progressive scaling for Lagavulin based on Siphon Soul count
5. Reward single-target focus against 3 Sentries
6. Prioritize AOE attacks against Slime Boss
7. Apply A20 early aggression rules for all elites (ascension >= 20)

This ensures AI uses optimal tactics for each elite rather than generic "elite" handling.

#### Scenario: Elite type detection identifies all 4 Act 1 elites
- **GIVEN** combat with any Act 1 elite
- **WHEN** calling `_detect_elite_type()`
- **THEN** Gremlin Nob SHALL return `EliteType.GREMLIN_NOB`
- **AND** Lagavulin SHALL return `EliteType.LAGAVULIN`
- **AND** 3 Sentries SHALL return `EliteType.THREE_SENTRIES`
- **AND** Slime Boss SHALL return `EliteType.SLIME_BOSS`
- **AND** Unknown monsters SHALL return `EliteType.UNKNOWN`

#### Scenario: Unified framework applies correct strategy
- **GIVEN** combat with Lagavulin on turn 9
- **WHEN** calling `_apply_elite_strategy_override()`
- **THEN** system SHALL detect `EliteType.LAGAVULIN`
- **AND** SHALL call `_apply_lagavulin_strategy()`
- **AND** SHALL NOT call strategies for other elite types
- **AND** score SHALL include progressive scaling modifiers

#### Scenario: Non-elite fights have no elite modifiers
- **GIVEN** combat with regular monster (Jaw Worm, Cultist)
- **WHEN** calling `_apply_elite_strategy_override()`
- **THEN** elite_type SHALL be `EliteType.UNKNOWN`
- **AND** no elite-specific modifiers SHALL be applied
- **AND** score SHALL match base scoring only

---

### Requirement: Lagavulin Progressive Difficulty Scaling

The system SHALL apply progressive damage weight scaling against Lagavulin to account for Siphon Soul (-1 Dex, -1 Str every 3 turns). The scaling SHALL:

1. Calculate siphon_count as `max(0, (turn - 6) // 3 + 1)` starting turn 6
2. Set damage_weight = `min(8.0, 4.0 + (siphon_count × 1.5))`
3. Apply -200 penalty for low damage (< 15 + siphon_count × 5) after turn 6
4. Apply +100 burst bonus for >30 damage on turns before Siphon Soul
5. Use damage_weight = 5.0 during hibernation (turns 1-5)

This ensures AI urgency increases exponentially as debuffs accumulate.

#### Scenario: Lagavulin damage weight scales progressively
- **GIVEN** combat with Lagavulin
- **WHEN** turn 5 (hibernating) → damage_weight SHALL be 5.0
- **AND** turn 6 (1st Siphon) → damage_weight SHALL be 5.5
- **AND** turn 9 (2nd Siphon) → damage_weight SHALL be 7.0
- **AND** turn 12 (3rd Siphon) → damage_weight SHALL be 8.0 (capped)

#### Scenario: Low-damage penalty after first Siphon
- **GIVEN** combat with Lagavulin on turn 7
- **AND** sequence deals 10 damage
- **WHEN** scoring
- **THEN** min_damage_needed SHALL be 20 (15 + 1×5)
- **AND** score SHALL include -200 penalty for damage < 20

#### Scenario: Pre-Siphon burst bonus incentivizes fast kills
- **GIVEN** combat with Lagavulin on turn 5
- **AND** sequence deals 35 damage
- **WHEN** scoring
- **THEN** next turn SHALL be Siphon Soul
- **AND** score SHALL include +100 burst bonus

---

### Requirement: 3 Sentries Single-Target Focus Bonus

The system SHALL reward concentrated damage on a single Sentry to eliminate one elite quickly before both stack Strength. The system SHALL:

1. Calculate damage concentration as `highest_damage / total_damage`
2. Apply +50 bonus if concentration >= 70%
3. Apply -30 penalty if concentration < 50% AND total_damage > 15
4. Log when bonuses/penalties are applied

This prevents spreading damage evenly across both elites, which prolongs the fight.

#### Scenario: Concentrated damage receives bonus
- **GIVEN** combat with 3 Sentries (2 alive)
- **AND** sequence deals 25 damage to Sentry A, 5 damage to Sentry B
- **WHEN** scoring
- **THEN** concentration SHALL be 83.3% (25/30)
- **AND** score SHALL include +50 single-target focus bonus

#### Scenario: Spread damage receives penalty
- **GIVEN** combat with 3 Sentries (2 alive)
- **AND** sequence deals 12 damage to Sentry A, 10 damage to Sentry B
- **WHEN** scoring
- **THEN** concentration SHALL be 54.5% (12/22)
- **AND** score SHALL NOT receive bonus (concentration < 70%)
- **AND** score SHALL NOT receive penalty (concentration >= 50%)

#### Scenario: Evenly spread damage penalized
- **GIVEN** combat with 3 Sentries (2 alive)
- **AND** sequence deals 10 damage to Sentry A, 10 damage to Sentry B
- **WHEN** scoring
- **THEN** concentration SHALL be 50% (10/20)
- **AND** score SHALL include -30 spread damage penalty

---

### Requirement: Slime Boss AOE Priority

The system SHALL prioritize AOE attacks against Slime Boss to maximize damage before and after split. The system SHALL:

1. Identify AOE cards: Cleave, Thunderclap, Whirlwind, Immolate
2. Apply ×1.5 multiplier to AOE damage based on monster count
3. Apply +30 bonus for high-damage attacks (>12 damage) when boss at 40-60% HP
4. Calculate bonus as `aoe_damage × monster_count × 1.5`

This encourages using AOE which hits boss before split and all slimes after.

#### Scenario: AOE card receives multiplier bonus
- **GIVEN** combat with Slime Boss (1 monster, 62 HP)
- **AND** sequence contains Cleave (8 damage AOE)
- **WHEN** scoring
- **THEN** aoe_damage SHALL be 8 (8 × 1 monster)
- **AND** bonus SHALL be +12 (8 × 1 × 1.5)
- **AND** score SHALL include +12 AOE multiplier

#### Scenario: AOE against split slimes scales with count
- **GIVEN** combat with Slime Boss aftermath (3 monsters: 2 Acid Slime M, 1 Slime S)
- **AND** sequence contains Cleave (8 damage AOE)
- **WHEN** scoring
- **THEN** aoe_damage SHALL be 24 (8 × 3 monsters)
- **AND** bonus SHALL be +36 (24 × 1.5)
- **AND** score SHALL include +36 AOE multiplier

#### Scenario: High damage near split threshold rewarded
- **GIVEN** combat with Slime Boss at 55% HP (near split)
- **AND** sequence contains Carnage (28 damage single-target)
- **WHEN** scoring
- **THEN** boss HP SHALL be 40-60% range
- **AND** damage SHALL be >12
- **AND** score SHALL include +30 burst bonus

#### Scenario: Single-target attacks have no AOE bonus
- **GIVEN** combat with Slime Boss
- **AND** sequence contains Strike_R (6 damage single-target)
- **WHEN** scoring
- **THEN** card SHALL not be in AOE list
- **AND** score SHALL NOT include AOE multiplier bonus

---

### Requirement: A20 Early Aggression for All Elites

The system SHALL apply early damage requirements for A20 elite fights to prevent passive "preparation" turns. At ascension >= 20, the system SHALL:

1. Require minimum 8 damage on turn 1 (-50 penalty if not)
2. Require minimum 15 damage on turn 2 (-100 penalty if not)
3. Require minimum 12 HP damage per turn average on turn 3+ (-150 penalty if not)
4. Only apply these rules when `context.ascension >= 20`
5. Log when early aggression penalties are applied

This ensures AI starts dealing damage immediately rather than waiting until turn 4-5.

#### Scenario: Turn 1 damage requirement enforced
- **GIVEN** A20 elite fight on turn 1
- **AND** sequence deals 5 damage
- **WHEN** scoring
- **THEN** min_damage (8) not met
- **AND** score SHALL include -50 early aggression penalty

#### Scenario: Turn 2 significant damage expected
- **GIVEN** A20 elite fight on turn 2
- **AND** sequence deals 10 damage
- **WHEN** scoring
- **THEN** min_damage (15) not met
- **AND** score SHALL include -100 early aggression penalty

#### Scenario: Turn 3+ kill pressure applied
- **GIVEN** A20 elite fight on turn 4
- **AND** total damage dealt so far is 30 HP
- **WHEN** scoring
- **THEN** expected damage SHALL be 48 (12 × 4 turns)
- **AND** damage (30) < expected (48)
- **AND** score SHALL include -150 falling behind penalty

#### Scenario: A0-A19 has no early aggression requirements
- **GIVEN** elite fight at ascension 15 on turn 1
- **AND** sequence deals 0 damage (all Powers/defends)
- **WHEN** scoring
- **THEN** ascension < 20
- **AND** no early aggression penalty SHALL be applied
- **AND** score SHALL be valid without penalty

#### Scenario: High damage sequences receive no penalty
- **GIVEN** A20 elite fight on turn 2
- **AND** sequence deals 25 damage
- **WHEN** scoring
- **THEN** min_damage (15) is met
- **AND** no early aggression penalty SHALL be applied

---
