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

The loader SHALL provide accurate extraction of card combat statistics (damage, block, AOE status) using a **4-stage approach**:

1. **Stage 1 - Structured field**: Check for direct `damage`/`block` fields (future-proof for StSExporter updates)
2. **Stage 2 - Wiki data parsing**: Parse wiki-card-data.txt for `[base|upgraded]` values (NEW)
3. **Stage 3 - Description parsing**: Use regex to extract values from description text
4. **Stage 4 - Hardcoded fallback**: Consult CARD_METADATA dictionary for complex cards

The loader SHALL implement:
- `_parse_card_damage(card_data) -> Optional[int]`: Extract base damage value
- `_parse_card_block(card_data) -> Optional[int]`: Extract base block value
- `_is_card_aoe(card_data) -> bool`: Detect multi-target attacks
- `_load_wiki_data() -> None`: Lazy-load wiki card data
- `_parse_text_field_for_upgrade_values(text: str) -> Tuple[Optional[int], Optional[int]]`: Extract upgrade pairs

#### Scenario: Simple damage parsed from wiki data
- **GIVEN** a Bash card with wiki entry `Text = "Deal [8|10] damage. Apply [2|3] #Vulnerable."`
- **WHEN** `_parse_card_damage()` is called for unupgraded Bash
- **THEN** Stage 1 (structured field) SHALL return None
- **AND** Stage 2 (wiki data) SHALL return `8`
- **AND** parsing SHALL complete successfully (Stage 3/4 skipped)

#### Scenario: Upgraded card damage from wiki
- **GIVEN** a Bash+ card with `card_id='Bash+'`
- **AND** wiki entry `Text = "Deal [8|10] damage."`
- **WHEN** `_parse_card_damage()` is called
- **THEN** Stage 2 (wiki data) SHALL detect upgraded status
- **AND** SHALL return `10` (upgraded value)
- **AND** CARD_METADATA entry for 'bash' SHALL NOT be consulted

#### Scenario: X-damage card bypasses wiki parsing
- **GIVEN** a Body Slam card with wiki entry `Text = "Deal damage equal to your #Block."`
- **WHEN** `_parse_card_damage()` is called
- **THEN** Stage 2 (wiki data) SHALL return None (no `[base|upgraded]` pattern)
- **AND** Stage 3 (regex) SHALL return None (no "Deal X damage" pattern)
- **AND** Stage 4 (CARD_METADATA) SHALL return 0 with `is_x_damage=True`
- **AND** combat simulation SHALL calculate dynamic damage based on player_block

#### Scenario: Wiki data unavailable falls back to regex
- **GIVEN** a card with description "Deal 12 damage." (no wiki data available)
- **WHEN** `_parse_card_damage()` is called
- **THEN** Stage 1 SHALL return None
- **AND** Stage 2 SHALL return None (wiki data missing/unparseable)
- **AND** Stage 3 (regex) SHALL match "Deal 12 damage"
- **AND** SHALL return `12`

#### Scenario: Complex card uses CARD_METADATA
- **GIVEN** a Heavy Blade card with description "Deal !D! damage. !D! = 5 + times_str**"
- **WHEN** `_parse_card_damage()` is called
- **THEN** Stage 1 SHALL return None (no structured field)
- **AND** Stage 2 SHALL return None (wiki data has no static value)
- **AND** Stage 3 SHALL return None (regex can't parse !D!)
- **AND** Stage 4 (CARD_METADATA) SHALL return `14`
- **AND** the `reason` field SHALL explain: "Dynamic damage formula"

#### Scenario: AOE detection enhanced with wiki data
- **GIVEN** a Cleave card with wiki entry `Text = "Deal [8|11] damage to ALL enemies."`
- **WHEN** `_is_card_aoe()` is called
- **THEN** wiki parser SHALL check `Text` field for "ALL enemies"
- **AND** SHALL return `True`
- **AND** CARD_METADATA entry MAY be removed (wiki parsing sufficient)

#### Scenario: Block parsing from wiki data
- **GIVEN** a Defend card with wiki entry `Text = "Gain [5|8] #Block."`
- **WHEN** `_parse_card_block()` is called for unupgraded Defend
- **THEN** Stage 1 (structured field) SHALL return None
- **AND** Stage 2 (wiki data) SHALL extract `[5|8]` pattern
- **AND** SHALL return `5` (base value)
- **AND** for Defend+, SHALL return `8` (upgraded value)

#### Scenario: Wiki parser handles missing Text field
- **GIVEN** a wiki entry without `Text` field (malformed)
- **WHEN** attempting to parse for damage/block
- **THEN** Stage 2 SHALL return None
- **AND** execution SHALL proceed to Stage 3 (regex)
- **AND** a warning SHALL be logged: "Wiki entry missing Text field for {card_name}"

---

### Requirement: Hardcoded Card Metadata

The loader SHALL maintain a `CARD_METADATA` dictionary containing accurate combat statistics for **20-30 truly complex cards** that cannot be reliably parsed from wiki data or descriptions. The metadata SHALL include:

1. **Card ID**: Lowercase card name (e.g., 'body slam')
2. **Base values**: damage, block for unupgraded version (if static)
3. **Upgraded values**: Separate values for '+' version if different
4. **Special flags**: is_x_damage, is_x_block, aoe, multi_hit
5. **Reason**: Comment explaining why manual entry required

**Scope Reduction**:
- **Before**: ~50 cards covering both static and dynamic values
- **After**: ~20-30 cards with dynamic formulas or unparseable mechanics

**Cards to Keep in CARD_METADATA**:
- X-damage cards: Body Slam, Bludgeon, Whirlwind
- X-block cards: Rage
- Dynamic formula cards: Heavy Blade, Pommel Strike (multi-hit)
- Complex scaling: Reaper (healing based on unblocked damage)

**Cards to Remove from CARD_METADATA**:
- Static damage cards with upgrade values: Bash, Strike, Cleave, Iron Wave, Clothesline, etc.
- Static block cards: Defend, Armaments, Shrug It Off, etc.
- Simple AOE cards: Thunderclap, Immolate, Cleaver (use wiki "ALL enemies" detection)

#### Scenario: CARD_METADATA reduced to dynamic cards only
- **GIVEN** the updated CARD_METADATA after wiki parser integration
- **WHEN** counting entries
- **THEN** total entries SHALL be 20-30 (reduced from ~50)
- **AND** each entry SHALL have `reason` field explaining necessity
- **AND** entries with static values (e.g., Bash: damage=8) SHALL be removed

#### Scenario: Static card removed from CARD_METADATA
- **GIVEN** Bash card previously had CARD_METADATA entry: `{damage: 8, upgraded_damage: 10}`
- **AND** wiki data contains: `Text = "Deal [8|10] damage."`
- **WHEN** `_parse_card_damage()` is called for Bash
- **THEN** Stage 2 (wiki parser) SHALL return `8` or `10`
- **AND** CARD_METADATA entry for 'bash' SHALL be removed
- **AND** parsing SHALL work correctly without hardcoded value

#### Scenario: X-card remains in CARD_METADATA
- **GIVEN** Body Slam card with dynamic damage formula
- **AND** wiki data contains: `Text = "Deal damage equal to your #Block."`
- **WHEN** `_parse_card_damage()` is called
- **THEN** Stage 2 (wiki) SHALL return None (no static value)
- **AND** Stage 4 (CARD_METADATA) SHALL return entry with `is_x_damage=True`
- **AND** entry SHALL remain in CARD_METADATA with reason: "Damage = player_block"

#### Scenario: Complex formula card remains in CARD_METADATA
- **GIVEN** Heavy Blade card with damage scaling: "Deal !D! damage. !D! = 5 + times_str**"
- **WHEN** `_parse_card_damage()` is called
- **THEN** wiki parsing SHALL fail (no static value in Text)
- **AND** CARD_METADATA entry SHALL remain: `{damage: 14, upgraded_damage: 22, reason: "Strength scaling formula"}`
- **AND** combat simulation SHALL use CARD_METADATA value

#### Scenario: All kept entries have reason field
- **GIVEN** the reduced CARD_METADATA
- **WHEN** iterating through all entries
- **THEN** each entry SHALL have a `reason` key
- **AND** the reason SHALL explain why manual entry is required
- **AND** examples: "X-damage = player_block", "Strength scaling", "AOE with complex targeting"

#### Scenario: Migration validation
- **GIVEN** the list of cards removed from CARD_METADATA
- **WHEN** testing wiki parser on these cards
- **THEN** all removed cards SHALL successfully parse from wiki data
- **AND** extracted values SHALL match previous CARD_METADATA values
- **AND** discrepancies SHALL be logged for manual review

---

### Requirement: Error Handling and Initialization

The loader SHALL provide clear error handling for all failure modes including wiki data parsing failures. The loader SHALL maintain consistent behavior whether wiki data is available or not.

**Error modes**:
1. **Missing wiki file**: Info message logged, fall back to Stage 3/4
2. **Malformed wiki entry**: Warning logged, skip entry, use Stage 3/4
3. **Uninitialized wiki data**: Lazy load on first access
4. **Wiki parse failure**: Return None, proceed to next stage
5. **Missing items.json**: FileNotFoundError with path details (existing)
6. **Corrupted JSON**: ValueError with parse error details (existing)

#### Scenario: Wiki data file not found
- **GIVEN** wiki-card-data.txt does not exist at the expected path
- **WHEN** `_load_wiki_data()` is called
- **THEN** no exception SHALL be raised
- **AND** an info message SHALL be logged: "Wiki data not found at {path}, using fallback parsing"
- **AND** `self._wiki_data` SHALL remain None or empty dict
- **AND** Stage 3/4 parsing SHALL work normally

#### Scenario: Wiki data has malformed entry
- **GIVEN** wiki-card-data.txt contains an entry with missing `Text` field
- **WHEN** parsing the malformed entry
- **THEN** a warning SHALL be logged: "Failed to parse wiki card: {card_name} - missing Text field"
- **AND** the entry SHALL be skipped (not added to cache)
- **AND** other valid entries SHALL be parsed successfully
- **AND** the skipped card SHALL fall back to Stage 3/4

#### Scenario: Lazy initialization on first access
- **GIVEN** GameDataLoader is created with `auto_load=False`
- **AND** `load_data()` has not been called
- **AND** wiki data has not been loaded
- **WHEN** `get_card_data("Bash")` is called
- **THEN** the loader SHALL initialize normally
- **AND** wiki data SHALL NOT be loaded yet (lazy)
- **AND** wiki data SHALL load only when `_parse_card_damage()` is first called

#### Scenario: Wiki data loading failure is non-fatal
- **GIVEN** wiki-card-data.txt exists but has corrupt data
- **WHEN** `_load_wiki_data()` attempts to parse
- **THEN** the function SHALL catch parsing errors
- **AND** log a warning: "Failed to load wiki data: {error}"
- **AND** set `self._wiki_data` to empty dict
- **AND** GameDataLoader SHALL continue to function with Stage 3/4
- **AND** no exception SHALL propagate to caller

#### Scenario: Successful load logging includes wiki data
- **GIVEN** items.json exists and is valid
- **AND** wiki-card-data.txt exists and is valid
- **WHEN** `load_data()` completes successfully
- **THEN** a message SHALL be printed to stderr
- **AND** the message SHALL include: "Loaded wiki data for X cards"
- **AND** the message SHALL appear after the items.json load message

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

### Requirement: Wiki Card Data Parsing

The loader SHALL provide an additional parsing stage that extracts combat statistics from wiki-card-data.txt before falling back to CARD_METADATA. The wiki parser SHALL:

1. Load wiki-card-data.txt on-demand (lazy loading)
2. Parse Lua-formatted card entries with regex
3. Extract `Text` field containing `[base|upgraded]` upgrade values
4. Extract `CostPlus` field for upgraded cost detection
5. Cache parsed data in memory for subsequent lookups

**Parsing Pipeline** (4 stages):
- **Stage 1**: Check structured `damage`/`block` fields in items.json
- **Stage 2**: Parse wiki-card-data.txt for upgrade values (NEW)
- **Stage 3**: Parse description text with regex (existing)
- **Stage 4**: Consult CARD_METADATA for complex cards (existing)

#### Scenario: Load wiki data on first access
- **GIVEN** GameDataLoader is initialized
- **AND** wiki-card-data.txt exists at `D:\SteamLibrary\steamapps\common\SlayTheSpire\export\wiki-card-data.txt`
- **WHEN** `_parse_card_damage()` is called for the first time
- **THEN** `_load_wiki_data()` SHALL be invoked automatically
- **AND** the file SHALL be loaded and parsed
- **AND** parsed data SHALL be cached in `self._wiki_data`
- **AND** subsequent calls SHALL use cached data (not reload file)

#### Scenario: Extract upgrade values from Text field
- **GIVEN** a wiki entry with `Text = "Deal [8|10] damage. Apply [2|3] #Vulnerable."` (Bash)
- **WHEN** parsing with `_parse_text_field_for_upgrade_values()`
- **THEN** the function SHALL extract base_damage=8, upgraded_damage=10
- **AND** extract base_vulnerable=2, upgraded_vulnerable=3
- **AND** return tuple: (8, 10) for damage

#### Scenario: Return appropriate value based on upgrade status
- **GIVEN** a card with `card_id='Bash+'` (upgraded)
- **AND** wiki data contains `Text = "Deal [8|10] damage."`
- **WHEN** `_parse_card_damage(card_data)` is called
- **THEN** the function SHALL detect `card_id.endswith('+')`
- **AND** SHALL return `10` (upgraded value)
- **AND** for `card_id='Bash'` (unupgraded), SHALL return `8`

#### Scenario: Extract CostPlus for upgraded cost
- **GIVEN** a wiki entry with `Cost = 1` and `CostPlus = 0` (Havoc)
- **WHEN** parsing wiki data
- **THEN** the parser SHALL extract both Cost and CostPlus
- **AND** store them in `self._wiki_data['havoc']['cost']` and `['cost_plus']`
- **AND** allow cost comparison between base and upgraded versions

#### Scenario: Wiki data missing falls back gracefully
- **GIVEN** wiki-card-data.txt does not exist
- **WHEN** `_parse_card_damage()` is called
- **THEN** wiki parsing stage SHALL return None
- **AND** execution SHALL fall back to Stage 3 (regex)
- **AND** then to Stage 4 (CARD_METADATA) if needed
- **AND** an info message SHALL be logged: "Wiki data not found, using fallback parsing"

#### Scenario: Lazy loading performance
- **GIVEN** GameDataLoader is initialized
- **AND** no card data lookups have occurred
- **WHEN** checking `self._wiki_data`
- **THEN** it SHALL be None (not loaded)
- **AND** startup time SHALL not include wiki file loading
- **AND** wiki file SHALL load only on first `_parse_card_damage()` call

#### Scenario: Malformed wiki entry skipped
- **GIVEN** a wiki entry missing the `Text` field
- **WHEN** parsing the entry
- **THEN** the parser SHALL skip this card
- **AND** log a warning: "Failed to parse wiki card: {card_name} - missing Text field"
- **AND** fall back to Stage 3/4 for this card
- **AND** NOT crash or raise exception

---

