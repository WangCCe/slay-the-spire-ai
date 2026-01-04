# scaling-threat-evaluation Specification

## Purpose
TBD - created by archiving change fix-over-defensive-elite-combat. Update Purpose after archive.
## Requirements
### Requirement: Scaling Mechanic Detection

The EnemyThreatProfiler SHALL detect enemies with dangerous scaling mechanics. Detection SHALL identify:

1. **Strength scaling**: Monsters that gain strength each turn (Gremlin Nob, Hexaghost)
2. **Ritual/Buff scaling**: Monsters with increasing power stacks
3. **Multi-enemy combos**: Fights with 3+ enemies that combo (Slavers, Gremlins)
4. **Multihit patterns**: Monsters with multiple attacks per turn

When scaling is detected, the threat SHALL be categorized as ThreatCategory.SCALING.

#### Scenario: Strength gain detected
- **GIVEN** monster with "Strength" power or "gain strength" intent
- **WHEN** analyzing threat
- **THEN** threat SHALL be ThreatCategory.SCALING
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Multi-enemy fight detected
- **GIVEN** 3 or more monsters in combat
- **WHEN** analyzing threat
- **THEN** threat SHALL be ThreatCategory.SCALING (combo threat)
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Ritual detected
- **GIVEN** monster with "Ritual" power (increases strength each turn)
- **WHEN** analyzing threat
- **THEN** threat SHALL be ThreatCategory.SCALING
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Regular monster no scaling
- **GIVEN** single "Fungi Beast" with no strength powers
- **WHEN** analyzing threat
- **THEN** threat SHALL be ThreatCategory.REGULAR
- **AND** BALANCED mode SHALL be used

---

### Requirement: Elite Monster Name Detection

The system SHALL maintain a list of elite monster names for fast identification. Elite detection SHALL be based on exact name matching.

**Elite names to detect**:
- Act 1: "Gremlin Nob", "Slavers", "The Sentry" (or "Sentry")
- Act 2: "The Guardian", "Gremlin Leader", "Hexaghost"
- Act 3: "Reptomancer", "The Collector", "The Champ", "The Automatron"

Detection SHALL be case-insensitive and substring-matching.

#### Scenario: Gremlin Nob detected
- **GIVEN** monster with name "Gremlin Nob"
- **WHEN** checking if elite
- **THEN** result SHALL be True
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Sentry detected (substring match)
- **GIVEN** monster with name "The Sentry"
- **WHEN** checking if elite
- **THEN** substring match "Sentry" SHALL detect as elite
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Case insensitive matching
- **GIVEN** monster with name "the collector" (lowercase)
- **WHEN** checking if elite
- **THEN** case-insensitive match SHALL detect as elite
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Non-elite not detected
- **GIVEN** monster with name "Cultist"
- **WHEN** checking if elite
- **THEN** result SHALL be False
- **AND** BALANCED mode SHALL be used

---

### Requirement: Urgency Bonus for Scaling Threats

When AGGRESSIVE mode is triggered by scaling detection, the system SHALL apply an additional "urgency bonus" to damage output. This bonus SHALL:

1. Add +50% damage score for the first 2 turns (front-load damage)
2. Decrease to +25% on turns 3-4
3. Return to 0% on turn 5+

The urgency bonus SHALL encourage killing scaling enemies before they become overwhelming.

#### Scenario: Turn 1 urgency bonus active
- **GIVEN** SCALING threat detected, turn 1
- **AND** AGGRESSIVE mode active
- **WHEN** scoring a 12-damage attack
- **THEN** base damage score: 12 × 5.0 = 60
- **AND** urgency bonus: 60 × 0.5 = 30
- **AND** total score: 90 points

#### Scenario: Turn 3 urgency bonus reduced
- **GIVEN** SCALING threat detected, turn 3
- **WHEN** scoring a 12-damage attack
- **THEN** base damage score: 60
- **AND** urgency bonus: 60 × 0.25 = 15
- **AND** total score: 75 points

#### Scenario: Turn 5 no urgency bonus
- **GIVEN** SCALING threat detected, turn 5
- **WHEN** scoring a 12-damage attack
- **THEN** base damage score: 60
- **AND** urgency bonus: 0 (expired)
- **AND** total score: 60 points

#### Scenario: Regular fight no urgency bonus
- **GIVEN** REGULAR threat (not elite/scaling)
- **WHEN** scoring damage
- **THEN** no urgency bonus SHALL be applied
- **AND** damage score SHALL use base weights only

---

### Requirement: Multi-Enemy Combo Threat Evaluation

Fights with 3+ enemies SHALL be classified as SCALING threat due to combo potential. The system SHALL:

1. Count total monsters in combat
2. If count >= 3, classify as SCALING
3. Trigger AGGRESSIVE mode
4. Prioritize AOE damage and single-target focus fire

This addresses threats like "3 Slavers" or "4 Gremlins" that combo together.

#### Scenario: Three Slavers detected
- **GIVEN** combat with 3 "Slaver" monsters
- **WHEN** analyzing threat
- **THEN** threat SHALL be ThreatCategory.SCALING
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Four Gremlins detected
- **GIVEN** combat with 4 "Gremlin" monsters
- **WHEN** analyzing threat
- **THEN** threat SHALL be ThreatCategory.SCALING
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Two monsters not scaling
- **GIVEN** combat with 2 "Fungi Beast" monsters
- **WHEN** analyzing threat
- **THEN** count = 2 (< 3 threshold)
- **AND** threat SHALL NOT be SCALING (unless other factors)
- **AND** BALANCED mode may be used

#### Scenario: Single elite plus adds
- **GIVEN** combat with "The Sentry" (2 parts) + "Shield Gremlin"
- **WHEN** analyzing threat
- **THEN** count = 3 entities
- **AND** threat SHALL be ThreatCategory.SCALING or ELITE (both trigger AGGRESSIVE)

---

### Requirement: Power-Based Threat Detection

The profiler SHALL examine monster powers to detect scaling threats. Powers indicating SCALING threat include:

1. "Strength" or "StrengthGain" power
2. "Ritual" power (increases each turn)
3. "Thorns" or similar retaliation
4. "Anger" or similar enrage mechanics

Detection SHALL be based on examining `monster.powers` list.

#### Scenario: Monster with Strength power
- **GIVEN** monster with powers containing "Strength" or "StrengthGain"
- **WHEN** analyzing threat
- **THEN** threat SHALL be ThreatCategory.SCALING
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Monster with Ritual power
- **GIVEN** monster with "Ritual" power (e.g., Awakened One)
- **WHEN** analyzing threat
- **THEN** threat SHALL be ThreatCategory.SCALING
- **AND** AGGRESSIVE mode SHALL be triggered

#### Scenario: Monster no dangerous powers
- **GIVEN** monster with no powers or only non-scaling powers
- **WHEN** analyzing threat
- **THEN** shall NOT classify as SCALING based on powers
- **AND** other factors (name, count) SHALL determine threat

---

### Requirement: Threat Caching for Performance

Threat analysis SHALL be cached per combat to avoid redundant computation. The system SHALL:

1. Analyze threat once on combat start
2. Store threat_category in DecisionContext
3. Reuse cached value for all scoring decisions
4. Invalidate cache when combat ends

This ensures threat detection doesn't impact beam search performance.

#### Scenario: Threat analyzed once
- **GIVEN** new combat with Gremlin Nob
- **WHEN** DecisionContext is created
- **THEN** threat SHALL be analyzed once
- **AND** threat_category SHALL be cached in context

#### Scenario: Threat reused in beam search
- **GIVEN** cached threat_category = ELITE
- **WHEN** running beam search over 100 candidates
- **THEN** threat SHALL NOT be re-analyzed for each candidate
- **AND** all 100 SHALL use cached ELITE classification

#### Scenario: Cache invalidated between combats
- **GIVEN** combat 1 with Gremlin Nob (threat = ELITE)
- **AND** combat 2 with Cultist (threat = REGULAR)
- **WHEN** transitioning between combats
- **THEN** cache SHALL be invalidated
- **AND** new combat SHALL re-analyze threat

