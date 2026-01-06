# intelligent-targeting Specification Delta

## Purpose

Enhance target selection logic to handle special monster mechanics (summoners, hibernation, phase changes, death splits) and improve AOE efficiency detection. This enables the AI to make strategic targeting decisions instead of simple lowest-HP targeting.

## ADDED Requirements

### Requirement: Special Mechanic Handling in Target Selection

The system SHALL implement `_choose_target_for_card_v2()` that handles special monster mechanics when selecting targets.

**Priority logic:**
1. Summoners: Determine whether to kill summoner or minions first based on strategy
2. Hibernation: Ignore hibernating monsters (deprioritize)
3. Phase changes: Prioritize during burst windows
4. Death splits: Prioritize AOE when efficient

#### Scenario: Reptomancer - Kill minions first
- **GIVEN** Reptomancer (95 HP) + 2 Daggers (12 HP each)
- **AND** Reptomancer enhanced data: `recommended_strategy.primary = "kill_minions_first"`
- **AND** `recommended_strategy.target_priority = "Daggers > Reptomancer"`
- **WHEN** playing Bash (10 damage, applies Vulnerable)
- **THEN** the AI SHALL target a Dagger (not Reptomancer)
- **AND** SHALL prioritize removing high-damage minions

#### Scenario: Cultist - Kill summoner first
- **GIVEN** 1 Cultist (44 HP)
- **AND** Cultist enhanced data: `recommended_strategy.primary = "kill_quickly"`
- **AND** `special_mechanics.summons = [{"turn": 3, "count": 1}]`
- **WHEN** playing an attack card
- **THEN** the AI SHALL target Cultist (kill before summon)
- **AND** SHALL prevent additional Cultists from appearing

#### Scenario: Lagavulin - Ignore while sleeping
- **GIVEN** Lagavulin (87 HP, intent = SLEEP) + Jaw Worm (12 HP)
- **AND** Lagavulin enhanced data: `special_mechanics.type = "hibernation"`
- **WHEN** playing a single-target attack
- **THEN** the AI SHALL target Jaw Worm (not Lagavulin)
- **AND** SHALL let Lagavulin sleep to avoid high-damage attacks

#### Scenario: Lagavulin - Prioritize when awake
- **GIVEN** Lagavulin (87 HP, intent = ATTACK, damage = 18) + Jaw Worm (12 HP)
- **WHEN** playing a single-target attack
- **THEN** the AI SHALL target Lagavulin (high threat when awake)
- **AND** SHALL prioritize removing high-damage source

#### Scenario: Hexaghost - Burst during phase change
- **GIVEN** Hexaghost (250 HP, at 55% HP)
- **AND** enhanced data: `special_mechanics.phases = [{"hp_threshold": 0.6, ...}]`
- **AND** current HP just crossed 60% threshold (entered new phase)
- **AND** `recommended_strategy.burst_windows = ["After Activate - high damage, no burn"]`
- **WHEN** playing high-damage attacks (18+ damage)
- **THEN** the AI SHALL prioritize Hexagghost during this vulnerable window
- **AND** SHALL front-load damage before burn accumulates

---

### Requirement: AOE Efficiency Detection

The system SHALL detect when AOE attacks are more efficient than single-target attacks based on monster composition.

**Efficiency criteria:**
- Death split monsters present (AOE very efficient)
- Multiple monsters with similar HP (HP variance < 100)
- 3+ monsters alive (AOE hits multiple targets)
- Summoner with minions present (kill all simultaneously)

#### Scenario: Slime Boss - AOE very efficient
- **GIVEN** Slime Boss (140 HP)
- **AND** enhanced data: `special_mechanics.type = "death_split"`
- **AND** splits into 2 Acid Slime (M), each splitting into 2 Acid Slime (S)
- **WHEN** deciding between Cleave (8 AOE damage) and Attack (12 single-target)
- **THEN** the AI SHALL prioritize Cleave
- **AND** reasoning: "AOE efficient - death split monster, total 5 monsters after death"

#### Scenario: Similar HP monsters - AOE efficient
- **GIVEN** 3 Jaw Worms (12, 13, 14 HP)
- **AND** HP variance = ((12-13)² + (13-13)² + (14-13)²) / 3 = 0.67 < 100
- **WHEN** deciding between Thunderclap (4 AOE) and 3× Strike (6 single-target each)
- **THEN** the AI SHALL prioritize Thunderclap
- **AND** SHALL hit all 3 monsters efficiently

#### Scenario: Dissimilar HP - Single-target better
- **GIVEN** monsters with HP: 50, 12, 8
- **AND** HP variance > 100
- **WHEN** deciding between AOE and single-target
- **THEN** the AI SHALL prioritize single-target attacks
- **AND** SHALL focus on killable low-HP monsters first

#### Scenario: Summoner with minions - AOE valuable
- **GIVEN** Reptomancer (95 HP) + 2 Daggers (12 HP each)
- **AND** Reptomancer enhanced data: `recommended_strategy.aoe_value = "very_high"`
- **WHEN** deciding between Cleave (8 AOE) and single-target attacks
- **THEN** the AI SHALL prioritize AOE if all monsters can be hit
- **AND** SHALL reduce total damage taken by removing all minions

---

### Requirement: Card-Specific Targeting

The system SHALL implement card-specific targeting logic for certain card types:

- **Bash**: Target highest HP + threat (maximize Vulnerable duration)
- **Body Slam**: Target lowest HP + threat (finish off low-HP monsters)
- **AOE attacks**: Use when AOE efficient (see above)
- **Heavy single-target**: Target highest threat monster

#### Scenario: Bash targeting
- **GIVEN** Monster A (20 HP, threat = 10) and Monster B (40 HP, threat = 25)
- **WHEN** playing Bash (applies 2 Vulnerable)
- **THEN** the AI SHALL target Monster B (higher HP + threat)
- **AND** reasoning: "Maximize Vulnerable benefit on high-threat, high-HP target"

#### Scenario: Body Slam targeting
- **GIVEN** Monster A (6 HP, threat = 5) and Monster B (15 HP, threat = 20)
- **AND** player has 20 block
- **WHEN** playing Body Slam (damage = block)
- **THEN** the AI SHALL target Monster A (lowest HP + threat consideration)
- **AND** SHALL prioritize finishing off low-HP monsters

#### Scenario: High-damage single-target
- **GIVEN** Heavy Blade (14-22 damage)
- **AND** Monster A (15 HP, threat = 10) and Monster B (30 HP, threat = 25)
- **WHEN** playing Heavy Blade
- **THEN** the AI SHALL target Monster B (highest threat)
- **AND** SHALL prioritize removing most dangerous monster

---

### Requirement: Killable Target Priority

The existing killable target logic SHALL be enhanced to use enhanced threat scores instead of just HP.

**Original logic** (from ai-combat spec):
1. Sort killable targets by threat (highest first)
2. If no killable targets, highest threat overall

**Enhanced logic:**
1. Use `compute_threat_v2()` for threat scores (includes future threat, scaling)
2. Sort killable targets by enhanced threat (highest first)
3. If no killable targets, highest enhanced threat overall

#### Scenario: Enhanced threat prioritization
- **GIVEN** Monster A (8 HP, reactive threat = 12, enhanced threat = 18)
- **AND** Monster B (15 HP, reactive threat = 25, enhanced threat = 35)
- **AND** playing attack for 10 damage
- **WHEN** selecting target
- **THEN** Monster A is killable (8 HP ≤ 10 damage)
- **AND** Monster B is not killable (15 HP > 10 damage)
- **AND** the AI SHALL target Monster A (killable, reduces incoming damage by 18)

#### Scenario: Both monsters killable - pick highest threat
- **GIVEN** Monster A (8 HP, enhanced threat = 18)
- **AND** Monster B (10 HP, enhanced threat = 35)
- **AND** playing attack for 12 damage
- **WHEN** both are killable
- **THEN** the AI SHALL target Monster B (higher threat: 35 > 18)
- **AND** SHALL prioritize removing most dangerous killable target

---

### Requirement: Target Selection Logging

The system SHALL log target selection reasoning at INFO level for monitoring.

**Log format:**
```
[TARGET] Card: {card_id}, Target: {monster_name}, Reason: {reason}
```

#### Scenario: Target selection logging
- **GIVEN** Reptomancer + 2 Daggers
- **AND** playing Bash
- **WHEN** selecting target
- **THEN** the system SHALL log: "[TARGET] Card: Bash, Target: Dagger, Reason: Kill minions first (strategy: Daggers > Reptomancer)"

#### Scenario: AOE selection logging
- **GIVEN** Slime Boss (140 HP)
- **AND** playing Cleave
- **WHEN** selecting AOE (no specific target)
- **THEN** the system SHALL log: "[TARGET] Card: Cleave, Target: None, Reason: AOE efficient - death split monster"

---

### Requirement: Performance Constraints

Target selection SHALL meet performance targets:

- **Per-card selection**: < 2ms (95th percentile)
- **Cache enhanced data lookups**: Access each monster's enhanced data once

#### Scenario: Performance target met
- **GIVEN** 4 monsters in combat
- **AND** 8 playable cards
- **WHEN** timing `_choose_target_for_card_v2()` calls
- **THEN** 95th percentile execution time SHALL be < 2ms

---

## Cross-References

This specification extends:
- **ai-combat** - Enhances Threat-Based Targeting requirement with special mechanics

This specification depends on:
- **monster-data-loading** - Requires special_mechanics and recommended_strategy data
- **enhanced-threat-assessment** - Uses compute_threat_v2() for enhanced threat scores

This specification enables:
- **combat-simulation-enhancement** - Provides intelligent targeting for beam search candidates
