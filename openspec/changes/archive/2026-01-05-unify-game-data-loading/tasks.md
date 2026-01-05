# unify-game-data-loading Tasks

## Phase 1: Consolidate Loaders (Core Refactoring)

### 1.1 Move WSL path conversion function
- [x] Copy `convert_windows_path_to_wsl()` from `spirecomm/spire/data_loader.py` to `spirecomm/data/loader.py`
- [x] Add test in `test_wsl_path_conversion.py` to verify it still works
- [x] Verify it handles both D:\ and C:\ paths correctly

**Validation**: WSL path conversion produces `/mnt/d/path` for `D:\path`

### 1.2 Enhance GameDataLoader.__init__() with auto_load
- [x] Add `auto_load: bool = True` parameter to `__init__()`
- [x] Call `self.load_data()` at end of `__init__()` if `auto_load=True`
- [x] Update docstring to document auto_load behavior
- [x] Test that `GameDataLoader(path, auto_load=False)` doesn't load data

**Validation**: Initialization with auto_load=True loads data immediately

### 1.3 Add FileNotFoundError for missing items.json
- [x] Wrap `load_data()` file open in try/except
- [x] Raise `FileNotFoundError` with helpful message including tried path
- [x] Test that creating loader with bad path raises clear error

**Validation**: `GameDataLoader("/bad/path")` raises `FileNotFoundError: items.json not found at /bad/path/items.json`

### 1.4 Remove spirecomm/spire/data_loader.py
- [x] Verify no code imports from `spirecomm.spire.data_loader` (use grep)
- [x] Delete `spirecomm/spire/data_loader.py`
- [x] Update `spirecomm/spire/__init__.py` to remove old exports

**Validation**: `rg "spirecomm.spire.data_loader"` returns no results

---

## Phase 2: Fix Import Statements (Cleanup)

### 2.1 Update spirecomm/spire/__init__.py
- [x] Remove `GameDataLoader`, `game_data`, `initialize_game_data` from imports
- [x] Add `from spirecomm.data.loader import game_data_loader`
- [x] Re-export `game_data_loader` for backward compatibility

**Validation**: `from spirecomm.spire import game_data_loader` works

### 2.2 Fix repeated imports in simulation.py
- [x] Move `from spirecomm.data.loader import game_data_loader` to module top (line ~15)
- [x] Remove all inline imports from functions (lines 390, 403, 508, 555, 1233, 1326)
- [x] Verify no functionality changes (run tests)

**Validation**: Single import at top of file, no imports inside functions

### 2.3 Fix repeated imports in deck.py
- [x] Move `from spirecomm.data.loader import game_data_loader` to module top
- [x] Remove inline imports from functions if any
- [x] Test deck archetype detection still works

**Validation**: Single import at top, archetype detection works

### 2.4 Fix repeated imports in decision/base.py
- [x] Move `from spirecomm.data.loader import game_data_loader` to module top
- [x] Remove inline imports if any
- [x] Test decision context creation

**Validation**: Single import at top, context creation works

### 2.5 Fix repeated imports in relic.py
- [x] Move `from spirecomm.data.loader import game_data_loader` to module top
- [x] Remove inline imports if any
- [x] Test relic evaluator

**Validation**: Single import at top, relic evaluation works

---

## Phase 3: Improve Metadata Parsing (Core Functionality)

### 3.1 Add _parse_card_damage() method
- [x] Implement `_parse_card_damage(self, card_data: Dict) -> Optional[int]`
- [x] Stage 1: Check for structured 'damage' field (future-proof)
- [x] Stage 2: Parse description with regex `r'deal (\d+) damage'`
- [x] Stage 3: Check CARD_METADATA fallback
- [x] Handle edge cases: multi-hit, X-damage, dynamic damage
- [x] Add docstring with examples

**Validation**: Returns correct damage for Bash (8), Strike (6), Heavy Blade (14 from metadata)

### 3.2 Add _parse_card_block() method
- [x] Implement `_parse_card_block(self, card_data: Dict) -> Optional[int]`
- [x] Parse description with regex `r'gain (\d+) block'`
- [x] Check CARD_METADATA fallback
- [x] Handle "Gain X Block" (Iron Wave)

**Validation**: Returns correct block for Defend (5), Iron Wave (5)

### 3.3 Add _is_card_aoe() method
- [x] Implement `_is_card_aoe(self, card_data: Dict) -> bool`
- [x] Check description for 'all', 'every', 'each' keywords
- [x] Check CARD_METADATA fallback for known AOE cards
- [x] Return True for Cleave, Whirlwind, Immolate, Thunderclap, etc.

**Validation**: Returns True for Cleave, False for Strike

### 3.4 Create CARD_METADATA dictionary
- [x] Add hardcoded metadata for ~30-50 common Ironclad cards
- [x] Include fields: damage, block, aoe, is_x_damage, upgraded_damage
- [x] Focus on cards used in beam search simulation
- [x] Document why each card needs manual entry (e.g., "Heavy Blade: dynamic damage")

**Cards to include**:
- Attacks: Strike, Bash, Cleave, Heavy Blade, Iron Wave, Pommel Strike, etc.
- Skills: Defend, Armaments, Body Slam, etc.

**Validation**: Metadata matches actual game values

### 3.5 Update simulation.py to use new parsers
- [x] Replace `getattr(card, 'damage', 0)` with `game_data_loader._parse_card_damage(card_data)`
- [x] Replace regex-based damage parsing in `_apply_attack()`
- [x] Replace regex-based AOE detection with `_is_card_aoe()`
- [x] Test beam search produces same or better action sequences

**Validation**: Combat simulation uses accurate damage values

---

## Phase 4: Error Handling & Validation (Robustness)

### 4.1 Add JSONDecodeError handling
- [x] Wrap `json.load()` in try/except
- [x] Raise `ValueError` with helpful message if JSON is corrupted
- [x] Include line number from JSONDecodeError in message
- [x] Test with malformed JSON file

**Validation**: Corrupted items.json produces clear error message

### 4.2 Add warnings for uninitialized loader
- [x] In `get_card_data()`, check if `self._cards is None`
- [x] Log warning: "GameDataLoader not initialized, call load_data() first"
- [x] Return None consistently
- [x] Document this behavior in docstring

**Validation**: Using loader without load_data() logs warning

### 4.3 Log successful data load
- [x] After successful `load_data()`, log to stderr
- [x] Include counts: "Loaded 721 cards, 178 relics, 68 creatures"
- [x] Only log on first load (not on cached calls)
- [x] Use `print()` to stderr to avoid interfering with Communication Mod

**Validation**: Startup shows "Game data loaded: 721 cards, 178 relics, 68 creatures"

### 4.4 Add items.json version check (optional)
- [x] Check if items.json has expected top-level keys
- [x] Log warning if structure unexpected (might be new StSExporter version)
- [x] Document expected keys: cards, relics, potions, creatures, keywords

**Validation**: Warns if items.json structure changes

---

## Phase 5: Testing & Validation

### 5.1 Test WSL path conversion
- [x] Run `test_wsl_path_conversion.py`
- [x] Verify D:\ → /mnt/d/, C:\ → /mnt/c/
- [x] Test with path containing spaces
- [x] Test with forward slashes already

**Validation**: All test cases pass

### 5.2 Test data loading with real items.json
- [x] Run Python: `from spirecomm.data.loader import game_data_loader`
- [x] Verify loader initialized successfully
- [x] Check `len(game_data_loader._cards) == 721`
- [x] Check `len(game_data_loader._relics) == 178`
- [x] Verify specific cards: `game_data_loader.get_card_data("Bash")['name'] == "Bash"`

**Validation**: All data loads correctly

### 5.3 Test damage parsing
- [x] Create test script to parse damage for 50 common cards
- [x] Verify values match game reality
- [x] Check edge cases: Heavy Blade, Bludgeon, Cleave
- [x] Ensure None returned for cards without damage (Powers, Skills)

**Validation**: Damage parsing accurate for >95% of tested cards

### 5.4 Integration test with combat simulation
- [x] Run `test_optimized_ai.py` with live game
- [x] Monitor combat decisions
- [x] Verify beam search evaluates actions correctly
- [x] Check logs for damage calculation accuracy

**Validation**: Combat simulation works without errors

### 5.5 Test with missing items.json
- [x] Temporarily rename items.json
- [x] Try to create GameDataLoader with auto_load=True
- [x] Verify FileNotFoundError raised with helpful message
- [x] Restore items.json

**Validation**: Clear error message when file missing

---

## Phase 6: Documentation & Cleanup

### 6.1 Update CLAUDE.md
- [x] Add section on `spirecomm.data.loader` usage
- [x] Document GameDataLoader API
- [x] Add example: How to load custom items.json path
- [x] Remove references to old `spirecomm.spire.data_loader`

**Validation**: CLAUDE.md documents new loader correctly

### 6.2 Update docstrings
- [x] Add docstring to `GameDataLoader.__init__()` explaining auto_load
- [x] Add docstring to `load_data()` documenting raised exceptions
- [x] Add docstring to parser methods with examples
- [x] Document CARD_METADATA structure

**Validation**: All public methods have clear docstrings

### 6.3 Remove deprecated code
- [x] Search for any remaining references to old loader
- [x] Update imports in test files
- [x] Remove from `spirecomm/__init__.py` if present
- [x] Clean up comments mentioning old loader

**Validation**: No references to `spirecomm.spire.data_loader` remain

---

## Dependencies & Ordering

**Critical Path** (must be done in order):
1. Phase 1.1 → 1.2 → 1.3 → 1.4 (consolidate loaders first)
2. Phase 2.1 → 2.2 → 2.3 → 2.4 → 2.5 (fix all imports)
3. Phase 3.1 → 3.2 → 3.3 → 3.4 → 3.5 (add parsers, use them)
4. Phase 4.1 → 4.2 → 4.3 → 4.4 (add error handling)
5. Phase 5.1 → 5.2 → 5.3 → 5.4 → 5.5 (test everything)
6. Phase 6.1 → 6.2 → 6.3 (document and clean up)

**Parallelizable**:
- Tasks 2.2, 2.3, 2.4, 2.5 can be done in parallel (different files)
- Tasks 3.1, 3.2, 3.3 can be done in parallel (different methods)
- Tasks 4.1, 4.2, 4.4 can be done in parallel (different error cases)
- Tasks 5.1, 5.2, 5.3 can be done in parallel (different test scripts)

**Blocking**:
- Phase 3 blocks on Phase 1 (consolidate loader first)
- Phase 4 blocks on Phase 3 (error handling for new code)
- Phase 5 blocks on Phase 4 (test after error handling)
- Phase 6 blocks on Phase 5 (document working code)
