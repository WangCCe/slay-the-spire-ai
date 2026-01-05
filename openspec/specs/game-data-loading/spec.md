# game-data-loading Specification

## Purpose
TBD - created by archiving change unify-game-data-loading. Update Purpose after archive.
## Requirements
### Requirement: Unified Game Data Loader

The system SHALL provide a single `GameDataLoader` class in `spirecomm.data.loader` that loads card, relic, creature, and keyword metadata from items.json. The loader SHALL:

1. Support automatic data loading on initialization via `auto_load=True` parameter
2. Convert Windows paths to WSL-compatible paths automatically
3. Raise `FileNotFoundError` with clear message if items.json not found
4. Parse all 5 data categories: cards (721), relics (178), creatures (68), keywords (52), potions (42)
5. Provide case-insensitive lookup via `get_card_data()`, `get_relic_data()`, `get_creature_data()`, `get_keyword_data()`
6. Return `None` for missing entries (not exceptions)

#### Scenario: Load game data on startup
- **GIVEN** the Slay the Spire export directory at `D:\SteamLibrary\steamapps\common\SlayTheSpire\export\items.json`
- **WHEN** the application starts and creates `game_data_loader = GameDataLoader()`
- **THEN** the loader SHALL load all 721 cards, 178 relics, 68 creatures, 52 keywords, 42 potions
- **AND** the operation SHALL complete in < 100ms
- **AND** a success message SHALL be logged: "Game data loaded: 721 cards, 178 relics, 68 creatures"

#### Scenario: WSL path conversion
- **GIVEN** the code is running in WSL on Linux
- **AND** the default export path is `D:\SteamLibrary\steamapps\common\SlayTheSpire\export`
- **WHEN** GameDataLoader is initialized with default path
- **THEN** the path SHALL be converted to `/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/export`
- **AND** items.json SHALL be successfully loaded from the WSL path

#### Scenario: Missing items.json
- **GIVEN** items.json does not exist at the specified path
- **WHEN** GameDataLoader is created with `auto_load=True`
- **THEN** a `FileNotFoundError` SHALL be raised
- **AND** the error message SHALL include the full path that was tried
- **AND** the error message SHALL suggest installing StSExporter mod

#### Scenario: Case-insensitive card lookup
- **GIVEN** the loader is initialized with game data
- **WHEN** calling `get_card_data("bash")` or `get_card_data("BASH")` or `get_card_data("Bash")`
- **THEN** all three calls SHALL return the same card data dictionary
- **AND** the dictionary SHALL contain keys: name, color, rarity, type, cost, description

---

### Requirement: Card Metadata Parsing

The loader SHALL provide accurate extraction of card combat statistics (damage, block, AOE status) from items.json data. Parsing SHALL use a multi-stage approach:

1. **Stage 1 - Structured field**: Check for direct `damage`/`block` fields (future-proof for StSExporter updates)
2. **Stage 2 - Description parsing**: Use regex to extract values from description text
3. **Stage 3 - Hardcoded fallback**: Consult CARD_METADATA dictionary for complex cards

The loader SHALL implement:
- `_parse_card_damage(card_data) -> Optional[int]`: Extract base damage value
- `_parse_card_block(card_data) -> Optional[int]`: Extract base block value
- `_is_card_aoe(card_data) -> bool`: Detect multi-target attacks

#### Scenario: Simple damage parsing from description
- **GIVEN** a card with description "Deal 8 damage. Apply 2 Vulnerable." (Bash)
- **WHEN** `_parse_card_damage()` is called
- **THEN** it SHALL return `8`
- **AND** the regex SHALL match "deal 8 damage" case-insensitively

#### Scenario: Dynamic damage card with hardcoded fallback
- **GIVEN** Heavy Blade card with description "Deal !D! damage. !D! = 5 + times_str**"
- **WHEN** `_parse_card_damage()` is called
- **THEN** Stage 1 (structured field) SHALL return None
- **AND** Stage 2 (regex) SHALL return None (can't parse !D!)
- **AND** Stage 3 (hardcoded) SHALL return `14` from CARD_METADATA

#### Scenario: AOE detection
- **GIVEN** a Cleave card with description "Deal 8 damage to ALL enemies"
- **WHEN** `_is_card_aoe()` is called
- **THEN** it SHALL return `True`
- **AND** the detection SHALL use keywords: 'all', 'every', 'each' in description
- **OR** check CARD_METADATA for known AOE cards

#### Scenario: Block parsing
- **GIVEN** a Defend card with description "Gain 5 Block."
- **WHEN** `_parse_card_block()` is called
- **THEN** it SHALL return `5`
- **AND** the regex SHALL match "gain 5 block" case-insensitively

#### Scenario: X-damage card
- **GIVEN** a Bludgeon card with description "Deal X damage where X equals your Block"
- **WHEN** `_parse_card_damage()` is called
- **THEN** it SHALL return `None` or `0` (can't determine X)
- **AND** CARD_METADATA SHALL mark it as `is_x_damage: True`

#### Scenario: Upgraded card damage
- **GIVEN** a Bash+ card with description "Deal 10 damage. Apply 3 Vulnerable."
- **WHEN** `_parse_card_damage()` is called
- **THEN** it SHALL return `10` (upgraded value)
- **AND** CARD_METADATA entry for 'bash' SHALL have separate 'upgraded_damage' field

---

### Requirement: Hardcoded Card Metadata

The loader SHALL maintain a `CARD_METADATA` dictionary containing accurate combat statistics for ~30-50 frequently-used cards that cannot be reliably parsed from descriptions. The metadata SHALL include:

1. **Card ID**: Lowercase card name (e.g., 'heavy blade')
2. **Base values**: damage, block for unupgraded version
3. **Upgraded values**: Separate values for '+' version if different
4. **Special flags**: is_x_damage, aoe, multi_hit
5. **Reason**: Comment explaining why manual entry required

#### Scenario: Heavy Blade metadata entry
- **GIVEN** CARD_METADATA dictionary
- **WHEN** looking up 'heavy blade'
- **THEN** entry SHALL contain:
  - damage: 14 (unupgraded)
  - upgraded_damage: 22 (upgraded)
  - is_x_damage: False (uses Strength scaling, not X)
  - reason: "Dynamic damage formula: !D! = 5 + times_str**"
- **AND** parser SHALL use these values instead of regex

#### Scenario: Cleave AOE metadata
- **GIVEN** CARD_METADATA dictionary
- **WHEN** looking up 'cleave'
- **THEN** entry SHALL contain:
  - damage: 8
  - aoe: True
  - reason: "AOE attack affecting all enemies"

#### Scenario: Whirlwind X-damage
- **GIVEN** CARD_METADATA dictionary
- **WHEN** looking up 'whirlwind'
- **THEN** entry SHALL contain:
  - damage: 0
  - is_x_damage: True
  - reason: "X = energy spent, variable damage"

#### Scenario: Incomplete metadata is acceptable
- **GIVEN** a card with complex mechanics (e.g., Limit Break)
- **WHEN** metadata entry exists but has damage: None
- **THEN** parser SHALL accept None and skip this card in combat calculations
- **AND** no error SHALL be raised

---

### Requirement: Error Handling and Initialization

The loader SHALL provide clear error handling for all failure modes and maintain consistent behavior whether auto-loaded or manually loaded.

**Error modes**:
1. **Missing file**: FileNotFoundError with path details
2. **Corrupted JSON**: ValueError with parse error details
3. **Uninitialized access**: Warning logged, returns None
4. **Missing entry**: Returns None (not exception)

#### Scenario: Corrupted items.json
- **GIVEN** items.json contains invalid JSON syntax
- **WHEN** `load_data()` is called
- **THEN** a `ValueError` SHALL be raised
- **AND** the error message SHALL include the line number of JSON syntax error
- **AND** the error message SHALL suggest reinstalling StSExporter

#### Scenario: Access before initialization
- **GIVEN** GameDataLoader created with `auto_load=False`
- **AND** `load_data()` has not been called
- **WHEN** `get_card_data("Bash")` is called
- **THEN** a warning SHALL be logged to stderr
- **AND** the function SHALL return `None`
- **AND** no exception SHALL be raised

#### Scenario: Missing card entry
- **GIVEN** the loader is initialized
- **AND** items.json does not contain a card named "FakeCard"
- **WHEN** `get_card_data("FakeCard")` is called
- **THEN** the function SHALL return `None`
- **AND** no warning or error SHALL be logged
- **AND** the caller SHALL handle None gracefully

#### Scenario: Successful load logging
- **GIVEN** items.json exists and is valid
- **WHEN** `load_data()` completes successfully
- **THEN** a message SHALL be printed to stderr
- **AND** the message SHALL include counts: "Loaded 721 cards, 178 relics, 68 creatures, 52 keywords, 42 potions"
- **AND** the message SHALL only appear once (not on subsequent calls)

---

### Requirement: Import Statement Cleanup

All modules that use game data SHALL import the loader once at module top, not inside functions. Repeated inline imports SHALL be eliminated.

**Files to update**:
- `spirecomm/ai/heuristics/simulation.py`
- `spirecomm/ai/heuristics/deck.py`
- `spirecomm/ai/decision/base.py`
- `spirecomm/ai/heuristics/relic.py`

#### Scenario: Single import at module top
- **GIVEN** simulation.py module
- **WHEN** the module is loaded
- **THEN** line 15 (or similar) SHALL contain: `from spirecomm.data.loader import game_data_loader`
- **AND** no function in the module SHALL contain this import statement
- **AND** all functions SHALL reference the imported `game_data_loader` directly

#### Scenario: No inline imports in deck.py
- **GIVEN** deck.py module
- **WHEN** searching for `from spirecomm.data.loader import`
- **THEN** exactly one match SHALL be found at module top
- **AND** zero matches SHALL be found inside function definitions

#### Scenario: No inline imports in decision/base.py
- **GIVEN** decision/base.py module
- **WHEN** searching for `from spirecomm.data.loader import`
- **THEN** exactly one match SHALL be found at module top
- **AND** zero matches SHALL be found inside function definitions

#### Scenario: No inline imports in relic.py
- **GIVEN** relic.py module
- **WHEN** searching for `from spirecomm.data.loader import`
- **THEN** exactly one match SHALL be found at module top
- **AND** zero matches SHALL be found inside function definitions

---

### Requirement: Backward Compatibility Migration

The system SHALL provide a migration path from the old `spirecomm.spire.data_loader` to the new unified loader. Migration SHALL:

1. Re-export `game_data_loader` from `spirecomm.spire` for backward compatibility
2. Remove deprecated `spirecomm/spire/data_loader.py` file
3. Update all imports in codebase to use new location
4. Document old → new import mapping

#### Scenario: Old import still works temporarily
- **GIVEN** existing code with `from spirecomm.spire.data_loader import game_data`
- **WHEN** the code is run after Phase 1 (consolidation)
- **THEN** the import SHALL work via re-export in spirecomm/__init__.py
- **AND** a deprecation warning MAY be logged

#### Scenario: New import pattern
- **GIVEN** new code or updated imports
- **WHEN** using `from spirecomm.data.loader import game_data_loader`
- **THEN** the import SHALL work without warnings
- **AND** direct access to GameDataLoader class SHALL be available

#### Scenario: All old imports removed
- **GIVEN** the codebase after Phase 2 (import cleanup)
- **WHEN** searching for `from spirecomm.spire.data_loader import`
- **THEN** zero results SHALL be found in all Python files
- **AND** `spirecomm/spire/data_loader.py` file SHALL not exist

#### Scenario: Documentation updated
- **GIVEN** CLAUDE.md documentation
- **WHEN** searching for `spirecomm.spire.data_loader`
- **THEN** only references SHALL be in migration/deprecation sections
- **AND** new code examples SHALL use `spirecomm.data.loader`

