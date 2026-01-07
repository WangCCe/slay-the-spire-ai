# monster-data-loading Specification Delta

## Purpose

Extend the game data loading system to include comprehensive monster metadata extracted from the Slay the Spire Fandom Wiki. This enables the AI to make informed combat decisions based on detailed monster characteristics including move patterns, special mechanics, HP ranges, and status effect weaknesses.

## ADDED Requirements

### Requirement: Monster Data Storage

The system SHALL store monster metadata in JSON files under `spirecomm/data/monster_wiki_data/`. JSON files SHALL be organized by act and monster type:

- `act1_elites.json` - Act 1 elite and boss monsters
- `act2_elites.json` - Act 2 elite and boss monsters
- `act3_elites.json` - Act 3 elite and boss monsters
- `act1_normals.json` - Act 1 normal monsters
- `act2_normals.json` - Act 2 normal monsters
- `act3_normals.json` - Act 3 normal monsters

Each JSON file SHALL contain a dictionary mapping monster IDs to monster data dictionaries.

#### Scenario: Monster data file structure
- **GIVEN** the enhanced monster data loading system
- **WHEN** reading `spirecomm/data/monster_wiki_data/act1_elites.json`
- **THEN** the file SHALL contain valid JSON with structure:
```json
{
  "Cultist": {
    "monster_type": "normal",
    "act": 1,
    "hp_ranges": {"normal": {"min": 42, "max": 46}},
    "moves": [...],
    "move_sequence": [0, 1, 2, 1, 1],
    "special_mechanics": {...},
    "weaknesses": {...},
    "threat_profile": {...}
  }
}
```

#### Scenario: Lazy loading on first access
- **GIVEN** the application starts
- **AND** monster data has not been loaded yet
- **WHEN** `get_enhanced_monster_data("Cultist")` is called for the first time
- **THEN** the system SHALL load all monster JSON files
- **AND** cache the data in memory
- **AND** subsequent calls SHALL use the cached data (not reload files)

#### Scenario: Missing data file handling
- **GIVEN** `act1_elites.json` does not exist
- **WHEN** attempting to load monster data
- **THEN** the system SHALL log an info message: "Monster data not found at {path}"
- **AND** SHALL continue to function (empty dict for that file)
- **AND** SHALL NOT raise an exception

---

### Requirement: Monster Data Structure

Each monster entry SHALL contain the following fields:

**Required fields:**
- `monster_type`: String - "normal", "elite", or "boss"
- `act`: Integer - 1, 2, or 3
- `hp_ranges`: Dictionary - HP ranges by condition
- `moves`: Array of move objects
- `move_sequence`: Array of integers - turn-by-turn move pattern
- `special_mechanics`: Dictionary - special abilities

**Optional fields:**
- `weaknesses`: Dictionary - status effect effectiveness multipliers
- `resistances`: Dictionary - status effect resistance multipliers
- `threat_profile`: Dictionary - threat assessment parameters
- `recommended_strategy`: Dictionary - strategic recommendations
- `ascension_modifiers`: Dictionary - ascension-specific changes

#### Scenario: Minimal monster entry
- **GIVEN** a simple monster like "Jaw Worm"
- **THEN** the monster data SHALL include:
  - `monster_type`: "normal"
  - `act`: 1
  - `hp_ranges`: {"normal": {"min": 11, "max": 15}}
  - `moves`: Array with at least 1 move
  - `move_sequence`: Array with at least 2 move IDs
  - `special_mechanics`: {"type": "none"}

#### Scenario: Complex monster entry
- **GIVEN** a complex monster like "Hexaghost"
- **THEN** the monster data SHALL include:
  - `special_mechanics`: {"type": "phase_change", "phases": [...]}
  - `weaknesses`: {"weak": 2.0, "vulnerable": 1.5}
  - `threat_profile`: {"base_threat": 25, "scaling_threat": 2.0, "burn_threat": 15}
  - `recommended_strategy`: {"primary": "kill_quickly", "debuffs": ["weak"]}

#### Scenario: Move object structure
- **GIVEN** a monster move in the `moves` array
- **THEN** the move SHALL contain:
  - `move_id`: Integer - unique move identifier
  - `name`: String - move name (e.g., "Ritual", "Dark Strike")
  - `intent`: String - intent type (ATTACK, BUFF, DEFEND, etc.)
- **AND** MAY contain:
  - `damage`: Integer - base damage (for attacks)
  - `hits`: Integer - number of hits (default: 1)
  - `effect`: String - effect description (for buffs/debuffs)
  - `block`: Integer - block gained (for defends)

#### Scenario: Move sequence specification
- **GIVEN** a monster with move_sequence = [0, 1, 2, 1, 1]
- **AND** current turn = 1
- **WHEN** determining the current move
- **THEN** the system SHALL use move_id = 0 (first element)
- **AND** on turn 2, SHALL use move_id = 1
- **AND** on turn 3, SHALL use move_id = 2
- **AND** on turn 4, SHALL use move_id = 1
- **AND** on turn 5+, SHALL cycle through [1, 1] (repeat_from_1 pattern)

---

### Requirement: Special Mechanics Types

The `special_mechanics` field SHALL support the following types:

1. **"none"**: No special mechanics
   - `{"type": "none"}`

2. **"summoner"**: Summons other monsters
   - `{"type": "summoner", "summons": [{"turn": 3, "name": "Cultist", "count": 1}], "scaling": {...}}`

3. **"hibernation"**: Sleeps before attacking
   - `{"type": "hibernation", "sleep_turns": 1, "damage_scaling": "+6 per turn", "max_damage": 30}`

4. **"phase_change"**: Changes behavior at HP thresholds
   - `{"type": "phase_change", "phases": [{"hp_threshold": 0.6, "move_pool": [4, 5, 6], "pattern": [4, 5, 4, 6]}]}`

5. **"death_split"**: Splits into multiple monsters on death
   - `{"type": "death_split", "splits": [{"hp_threshold": 0, "splits_into": [{"name": "Acid Slime (M)", "count": 2}]}]}`

#### Scenario: Summoner mechanics
- **GIVEN** a Cultist with `special_mechanics.type = "summoner"`
- **AND** `summons = [{"turn": 3, "name": "Cultist", "count": 1}]`
- **WHEN** turn 3 is reached
- **THEN** the combat simulation SHALL add 1 new "Cultist" monster to the state
- **AND** the AI SHALL recognize this as summoning threat (+20)

#### Scenario: Hibernation mechanics
- **GIVEN** a Lagavulin with `special_mechanics.type = "hibernation"`
- **AND** `sleep_turns = 1`
- **AND** `damage_scaling = "+6 per turn"`
- **WHEN** the monster is sleeping (intent = SLEEP)
- **THEN** the AI SHALL deprioritize it as a target (threat = 5)
- **AND** WHEN it wakes up
- **THEN** the AI SHALL recognize high threat (threat = 30)
- **AND** the damage SHALL be calculated as `18 + (turns_slept × 6)`

#### Scenario: Phase change mechanics
- **GIVEN** a Hexaghost with `special_mechanics.type = "phase_change"`
- **AND** phases = [{"hp_threshold": 0.6, "move_pool": [4, 5, 6]}]
- **WHEN** HP drops from 70% to 55% (crosses 60% threshold)
- **THEN** the monster's move_pool SHALL change to [4, 5, 6]
- **AND** future move predictions SHALL use the new move_pool

#### Scenario: Death split mechanics
- **GIVEN** a Slime Boss with `special_mechanics.type = "death_split"`
- **AND** splits = [{"hp_threshold": 0, "splits_into": [{"name": "Acid Slime (M)", "count": 2}]}]
- **WHEN** the Slime Boss dies (HP ≤ 0)
- **THEN** the combat simulation SHALL add 2 "Acid Slime (M)" monsters to the state
- **AND** the AI SHALL recognize AOE efficiency (prioritize Cleave, etc.)

---

### Requirement: Weakness and Resistance Multipliers

The `weaknesses` and `resistances` fields SHALL specify status effect effectiveness as multipliers:

- **weaknesses**: Multiplier > 1.0 means the status is MORE effective
- **resistances**: Multiplier < 1.0 means the status is LESS effective

Supported status effects: "weak", "vulnerable", "poison", "frail"

#### Scenario: Weak monster is high priority
- **GIVEN** a monster with `weaknesses = {"weak": 2.0}`
- **AND** the AI has a card that applies Weak
- **WHEN** deciding whether to apply Weak
- **THEN** the AI SHALL prioritize applying Weak to this monster
- **AND** the threat reduction SHALL be calculated as `base_threat_reduction × 2.0`

#### Scenario: Resistant monster is low priority
- **GIVEN** a monster with `resistances = {"poison": 0.5}`
- **AND** the AI has a card that applies Poison
- **WHEN** deciding whether to apply Poison
- **THEN** the AI SHALL deprioritize applying Poison to this monster
- **AND** the damage SHALL be calculated as `base_poison_damage × 0.5`

#### Scenario: No status effect data
- **GIVEN** a monster without `weaknesses` or `resistances` fields
- **WHEN** evaluating status effect effectiveness
- **THEN** the AI SHALL assume normal effectiveness (multiplier = 1.0)

---

### Requirement: Threat Profile

The `threat_profile` field SHALL provide parameters for threat calculation:

- `base_threat`: Integer - base threat level (1-30 scale)
- `scaling_threat`: Float - threat growth per turn (e.g., +3.0 for Cultist Ritual)
- `summon_threat`: Integer - threat if allowed to summon (e.g., 20)
- `burn_threat`: Integer - threat from burn damage (e.g., 15 for Hexaghost)
- `hibernation_threat`: Integer - threat while sleeping (e.g., 5 for Lagavulin)
- `awakened_threat`: Integer - threat when awake (e.g., 30 for Lagavulin)
- `priority_target`: Boolean - whether this monster should be focus-fired

#### Scenario: Base threat calculation
- **GIVEN** a monster with `threat_profile.base_threat = 15`
- **WHEN** calculating immediate threat
- **THEN** the threat score SHALL start at 15
- **AND** additional components (damage, debuffs) SHALL be added to this base

#### Scenario: Scaling threat over time
- **GIVEN** a Cultist with `threat_profile.scaling_threat = 3.0`
- **AND** estimated turns to death = 4
- **WHEN** calculating future threat
- **THEN** the scaling threat SHALL be `3.0 × 4 = 12`
- **AND** this SHALL be added to the total threat score

#### Scenario: Priority target flag
- **GIVEN** a monster with `threat_profile.priority_target = True`
- **WHEN** selecting targets for attacks
- **THEN** the AI SHALL prioritize this monster above non-priority targets
- **AND** SHOULDN'T ignore it even if other monsters have lower HP

---

### Requirement: Ascension Modifiers

The `ascension_modifiers` field SHALL specify monster changes at specific ascension levels:

```json
{
  "ascension_modifiers": {
    "A10+": {
      "hp_ranges": {"min": 46, "max": 50}
    },
    "A15+": {
      "moves": [{"move_id": 0, "effect": "+5 Strength"}]  // Ritual stronger
    },
    "A18+": {
      "damage": "+20%"  // All attacks deal 20% more damage
    }
  }
}
```

#### Scenario: Ascension 10+ HP increase
- **GIVEN** a Cultist in ascension 12
- **AND** `ascension_modifiers.A10+.hp_ranges = {"min": 46, "max": 50}`
- **WHEN** loading monster data
- **THEN** the HP range SHALL be 46-50 (not the base 42-46)

#### Scenario: Ascension 15+ stronger effects
- **GIVEN** a Cultist in ascension 17
- **AND** `ascension_modifiers.A15+.moves[0].effect = "+5 Strength"`
- **WHEN** simulating the Ritual move
- **THEN** the monster SHALL gain +5 Strength (not +3)

#### Scenario: No ascension modifiers
- **GIVEN** a monster without `ascension_modifiers` field
- **WHEN** playing at ascension 15
- **THEN** the monster SHALL use base stats (no ascension-specific changes)

---

### Requirement: Monster Data Lookup API

The system SHALL provide helper functions for accessing monster data:

1. `get_enhanced_monster_data(monster_id: str) -> Optional[Dict]`
   - Returns full monster data dict
   - Returns None if monster not found

2. `get_move_pattern(monster_id: str, current_move_id: int) -> List[Dict]`
   - Returns array of move objects for the move sequence
   - Returns empty list if monster not found

3. `get_special_mechanics(monster_id: str) -> Dict`
   - Returns special_mechanics dict
   - Returns `{"type": "none"}` if monster not found

4. `get_threat_profile(monster_id: str) -> Dict`
   - Returns threat_profile dict
   - Returns default threat profile if monster not found

#### Scenario: Get enhanced monster data
- **GIVEN** monster_id = "Cultist"
- **AND** Cultist data exists in database
- **WHEN** calling `get_enhanced_monster_data("Cultist")`
- **THEN** the function SHALL return the complete Cultist data dict
- **AND** the dict SHALL contain all fields (hp_ranges, moves, special_mechanics, etc.)

#### Scenario: Get unknown monster data
- **GIVEN** monster_id = "UnknownMonster"
- **AND** UnknownMonster does not exist in database
- **WHEN** calling `get_enhanced_monster_data("UnknownMonster")`
- **THEN** the function SHALL return None
- **AND** SHALL NOT raise an exception

#### Scenario: Get move pattern
- **GIVEN** monster_id = "Cultist"
- **AND** current_move_id = 0 (Ritual)
- **AND** move_sequence = [0, 1, 2, 1, 1]
- **WHEN** calling `get_move_pattern("Cultist", 0)`
- **THEN** the function SHALL return array of move objects: [Ritual, Dark Strike, Incite, Dark Strike, Dark Strike]
- **AND** each move SHALL be a dict with move_id, name, intent, damage/effect

#### Scenario: Get special mechanics for unknown monster
- **GIVEN** monster_id = "UnknownMonster"
- **WHEN** calling `get_special_mechanics("UnknownMonster")`
- **THEN** the function SHALL return `{"type": "none"}`
- **AND** SHALL NOT raise an exception

---

### Requirement: Case-Insensitive Monster ID Lookup

All monster data lookup functions SHALL be case-insensitive and handle common ID variations:

- Remove '+' suffix from upgraded monster IDs
- Handle spaces vs underscores
- Handle "The" prefix variations

#### Scenario: Case-insensitive lookup
- **GIVEN** monster data exists for "Cultist"
- **WHEN** calling `get_enhanced_monster_data("cultist")` (lowercase)
- **THEN** the function SHALL return the Cultist data
- **AND** SHALL NOT be case-sensitive

#### Scenario: Upgraded monster lookup
- **GIVEN** monster data exists for "Cultist"
- **WHEN** calling `get_enhanced_monster_data("Cultist+")` (with + suffix)
- **THEN** the function SHALL return the Cultist data (same as base monster)
- **AND** SHALL NOT require separate entry for upgraded version

#### Scenario: Space vs underscore handling
- **GIVEN** monster data exists for "Gremlin Nob"
- **WHEN** calling `get_enhanced_monster_data("gremlin_nob")` (underscore)
- **THEN** the function SHALL return the Gremlin Nob data
- **AND** SHALL handle both space and underscore variants

---

### Requirement: Data Validation

The system SHALL validate monster data on load and log warnings for malformed entries:

**Validation checks:**
1. Required fields present (monster_type, act, hp_ranges, moves, move_sequence, special_mechanics)
2. move_sequence references valid move_ids (all IDs exist in moves array)
3. hp_ranges have min ≤ max
4. Multiplier fields (weaknesses, resistances) are positive numbers
5. threat_profile values are non-negative

#### Scenario: Valid monster data
- **GIVEN** a well-formed monster entry
- **WHEN** loading the data
- **THEN** the entry SHALL be loaded successfully
- **AND** SHALL be available for lookup

#### Scenario: Missing required field
- **GIVEN** a monster entry missing `hp_ranges`
- **WHEN** loading the data
- **THEN** the system SHALL log a warning: "Monster {id} missing required field: hp_ranges"
- **AND** SHALL skip this entry (not load it)
- **AND** SHALL continue loading other entries

#### Scenario: Invalid move sequence reference
- **GIVEN** a monster with move_sequence = [0, 1, 5]
- **AND** moves array only has 3 entries (IDs 0, 1, 2)
- **WHEN** loading the data
- **THEN** the system SHALL log a warning: "Monster {id} move_sequence references invalid move_id: 5"
- **AND** SHALL skip this entry

#### Scenario: Invalid HP range
- **GIVEN** a monster with hp_ranges = {"normal": {"min": 50, "max": 40}}
- **WHEN** min > max
- **THEN** the system SHALL log a warning: "Monster {id} has invalid HP range: min > max"
- **AND** SHALL skip this entry

#### Scenario: Empty JSON file
- **GIVEN** a JSON file that exists but is empty: `{}`
- **WHEN** loading the data
- **THEN** the system SHALL load it successfully (empty dict)
- **AND** SHALL NOT log warnings
- **AND** other JSON files SHALL still be loaded

---

## Cross-References

This specification enables:
- **enhanced-threat-assessment** - Provides monster data for predictive threat calculation
- **intelligent-targeting** - Provides special mechanics data for target prioritization
- **monster-aware-combat-modes** - Provides threat profiles for combat mode selection
- **combat-simulation-enhancement** - Provides move patterns for combat simulation

This specification extends:
- **game-data-loading** - Follows the same pattern as wiki card data loading (lazy loading, JSON files, error handling)
