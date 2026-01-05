# unify-game-data-loading Proposal

## Summary

Consolidate duplicate game data loaders (`spirecomm/spire/data_loader.py` and `spirecomm/data/loader.py`) into a single, robust implementation with proper initialization, error handling, and reliable card metadata parsing.

## Why

Currently, the codebase has **two separate game data loaders** that both load `items.json` from the Slay the Spire export directory:

1. `spirecomm/spire/data_loader.py` - Loads items.json + markdown files, exports as `game_data`, supports WSL path conversion
2. `spirecomm/data/loader.py` - Loads only items.json, exports as `game_data_loader`, **actually used in production**

This creates several problems:

### Problem 1: Duplicate Implementation
Two loaders with overlapping functionality but different APIs, creating maintenance burden and confusion about which to use.

### Problem 2: Unreliable Damage Parsing
Combat simulation uses fragile regex-based parsing of card descriptions:
```python
damage_match = re.search(r'deal (\d+) damage', description)
```
This fails for:
- Dynamic damage (`!D!` syntax in Heavy Blade)
- Multi-hit cards ("Deal 5 damage twice")
- Conditional damage ("equal to your Block")
- X-damage cards ("Deal X damage")

### Problem 3: Silent Initialization Failures
The `GameDataLoader.__init__()` doesn't call `load_data()`, so if `items.json` is missing or path is wrong, the loader **silently fails** when first accessed, returning `None` for all lookups.

### Problem 4: Missing Card Metadata
Communication Mod's `Card` objects don't include `damage`/`block` fields, so AI **must** use `items.json` for accurate combat simulation. However, current parsing is unreliable.

### Problem 5: Repeated Imports
Functions in `simulation.py` repeatedly import `game_data_loader` instead of importing once at module top:
```python
# Line 390, 403, 508, 555, 1233, 1326
from spirecomm.data.loader import game_data_loader
```

## What Changes

This proposal consolidates the two loaders into `spirecomm/data/loader.py` with the following changes:

### Modified Files
- `spirecomm/data/loader.py` - Enhanced with WSL support, auto_load, error handling, parsers
- `spirecomm/spire/__init__.py` - Removed old loader exports
- `spirecomm/ai/heuristics/simulation.py` - Fixed imports, uses new parser methods
- `spirecomm/ai/heuristics/card.py` - Updated API from game_data to game_data_loader
- `test_wsl_path_conversion.py` - Updated import path
- `CLAUDE.md` - Added game data loading documentation

### Deleted Files
- `spirecomm/spire/data_loader.py` - Removed duplicate loader

### Key Additions
- `convert_windows_path_to_wsl()` - WSL path conversion
- `GameDataLoader(auto_load=True)` - Automatic initialization
- `_parse_card_damage()` - 3-stage damage parsing
- `_parse_card_block()` - Block value parsing
- `_is_card_aoe()` - AOE detection
- `CARD_METADATA` - 35+ hardcoded Ironclad cards

## Proposed Solution

1. **Single Loader**: Consolidate to one `GameDataLoader` with WSL path support
2. **Explicit Initialization**: Load data at initialization, fail loudly if file not found
3. **Robust Metadata Parsing**: Parse structured fields from items.json instead of regex on description
4. **Hardcoded Fallback**: Maintain accurate metadata for cards that can't be parsed
5. **Clean Imports**: Import once at module top, not inside functions

## Scope

### In Scope
- Unify the two loaders into `spirecomm/data/loader.py`
- Add proper initialization with error handling
- Improve damage/block parsing from items.json
- Fix repeated imports in simulation.py and other modules
- Add validation that data loaded successfully

### Out of Scope
- Modifying Communication Mod protocol
- Adding external dependencies
- Complete card metadata database (partial for critical cards only)

## Impact

### Benefits
- **Reliability**: Combat simulation will have accurate damage values
- **Maintainability**: Single source of truth for game data loading
- **Debuggability**: Clear errors if items.json is missing or corrupted
- **Consistency**: All modules use same loader with same API

### Risks
- **Breaking Change**: Modules importing from `spirecomm.spire.data_loader` will need updates
- **Path Compatibility**: Must ensure WSL path conversion works for all environments
- **Data Format**: StSExporter may change format (currently stable)

## Dependencies

- Must run on Slay the Spire with StSExporter mod installed
- Requires `items.json` at export path (Windows or WSL-compatible)
- No new Python dependencies (standard library only)

## Success Criteria

1. Only one `GameDataLoader` class exists in codebase
2. All imports use `spirecomm.data.loader`
3. Missing `items.json` raises clear error on startup
4. Combat simulation uses accurate damage values (not regex parsing)
5. No repeated imports in simulation.py
6. All existing functionality preserved (no regressions)
