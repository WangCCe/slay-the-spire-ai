# unify-game-data-loading Design

## Architecture

### Current State

```
spirecomm/spire/data_loader.py          spirecomm/data/loader.py
├── GameDataLoader                      ├── GameDataLoader
├── game_data (global)                  ├── game_data_loader (global)
├── initialize_game_data()              ├── load_data()
├── convert_windows_path_to_wsl()       └── No WSL support
├── Loads: items.json + *.md
└── Exports to spirecomm.spire.__init__ └── Used by: heuristics/

Used by: Almost nothing                  Used by: decision/, heuristics/
```

### Target State

```
spirecomm/data/loader.py (UNIFIED)
├── convert_windows_path_to_wsl()  [from spire/data_loader.py]
├── GameDataLoader (enhanced)
│   ├── __init__(export_path, auto_load=True)
│   ├── load_data() - called by __init__
│   ├── get_card_data(card_name)
│   ├── get_relic_data(relic_name)
│   ├── get_creature_data(creature_name)
│   ├── get_keyword_data(keyword)
│   ├── _parse_card_damage(card_data) - NEW
│   ├── _parse_card_block(card_data) - NEW
│   └── _is_card_aoe(card_data) - NEW
├── game_data_loader (global, auto-initialized)
└── CARD_METADATA (hardcoded fallback for critical cards)

Exports:
└── spirecomm.data.loader (ONLY export point)
```

## Key Design Decisions

### 1. Single Export Point

**Decision**: All game data loading goes through `spirecomm.data.loader`

**Rationale**:
- Clear single source of truth
- Easier to maintain and extend
- No confusion about which loader to use

**Migration**:
```python
# OLD (deprecated)
from spirecomm.spire.data_loader import game_data
from spirecomm.spire import initialize_game_data

# NEW (unified)
from spirecomm.data.loader import game_data_loader
```

### 2. Explicit Initialization

**Decision**: Load data immediately in `__init__`, fail loudly if file not found

**Rationale**:
- Fail fast instead of silent None returns
- Clear error messages for missing items.json
- Detects configuration problems early

**Implementation**:
```python
def __init__(self, data_path: str = DEFAULT_EXPORT_PATH, auto_load: bool = True):
    self.data_path = convert_windows_path_to_wsl(data_path)
    self._cards = None
    self._relics = None
    # ... other fields

    if auto_load:
        self.load_data()  # Raises FileNotFoundError if missing
```

### 3. Improved Damage Parsing

**Decision**: Multi-stage damage resolution

1. **Check structured fields** (if StSExporter adds them in future)
2. **Parse description** with improved regex handling edge cases
3. **Fallback to hardcoded metadata** for critical cards

**Rationale**:
- Current regex fails on dynamic damage (!D!)
- Hardcoded fallback ensures accuracy for common cards
- Extensible for future StSExporter improvements

**Implementation**:
```python
def _parse_card_damage(self, card_data: Dict[str, Any]) -> Optional[int]:
    """Extract base damage from card data."""
    # Stage 1: Check structured field (future-proof)
    if 'damage' in card_data:
        return card_data['damage']

    # Stage 2: Parse description
    description = card_data.get('description', '').lower()
    card_name = card_data.get('name', '').lower()

    # Stage 3: Hardcoded fallback
    if card_name in self.CARD_METADATA:
        return self.CARD_METADATA[card_name].get('damage')

    # Stage 2: Improved regex
    match = re.search(r'deal (\d+) damage', description)
    if match:
        return int(match.group(1))

    return None
```

### 4. Hardcoded Metadata Fallback

**Decision**: Maintain `CARD_METADATA` for cards with complex damage formulas

**Rationale**:
- Heavy Blade: "Deal !D! damage. !D! = 5 + times_str**" → needs manual entry
- Multi-hit cards: "Deal 5 damage twice" → regex sees only first number
- X-damage cards: "Deal X damage" → regex can't parse
- Ensures combat simulation accuracy

**Scope**: Only critical cards used in beam search simulation
```python
CARD_METADATA = {
    'heavy blade': {'damage': 14, 'upgraded_damage': 22},
    'bludgeon': {'damage': 0, 'is_x_damage': True},  # X = 12-30 based on block
    'cleave': {'damage': 8, 'aoe': True},
    'whirlwind': {'damage': 0, 'is_x_damage': True},  # X = energy
    # ... ~30-50 most common cards
}
```

### 5. WSL Path Conversion

**Decision**: Import `convert_windows_path_to_wsl()` from old loader

**Rationale**:
- Essential for WSL development environment
- Already battle-tested in `spirecomm/spire/data_loader.py`
- Minimal code duplication

**Implementation**:
```python
# At module top
try:
    export_path = os.environ.get('SLAY_THE_SPIRE_EXPORT_PATH',
                                  convert_windows_path_to_wsl(DEFAULT_PATH))
    game_data_loader = GameDataLoader(export_path, auto_load=True)
except FileNotFoundError as e:
    # Fallback to non-initialized loader (warns on first use)
    game_data_loader = GameDataLoader(auto_load=False)
    warnings.warn(f"items.json not found: {e}")
```

## Implementation Phases

### Phase 1: Consolidate Loaders
1. Move `convert_windows_path_to_wsl()` to `spirecomm/data/loader.py`
2. Enhance `GameDataLoader.__init__()` with auto_load parameter
3. Add `load_data()` call in `__init__()`
4. Remove `spirecomm/spire/data_loader.py`

### Phase 2: Fix Imports
1. Update `spirecomm/spire/__init__.py` to import from `spirecomm.data.loader`
2. Fix repeated imports in `simulation.py` (move to module top)
3. Update all `from spirecomm.spire.data_loader import ...` statements

### Phase 3: Improve Metadata Parsing
1. Add `_parse_card_damage()` method
2. Add `_parse_card_block()` method
3. Add `_is_card_aoe()` method
4. Create `CARD_METADATA` fallback dictionary
5. Update simulation.py to use new parsers

### Phase 4: Error Handling
1. Raise `FileNotFoundError` if items.json missing
2. Add `JSONDecodeError` handling for corrupted files
3. Add warnings when using non-initialized loader
4. Log successful data load with card/relic counts

## Data Flow

```
Application Startup
         ↓
game_data_loader = GameDataLoader(export_path, auto_load=True)
         ↓
convert_windows_path_to_wsl() → /mnt/d/.../export
         ↓
load_data()
         ↓
┌─────────────────────────────────────────┐
│ items.json                              │
│ ├── cards (721)                         │
│ ├── relics (178)                        │
│ ├── creatures (68)                      │
│ ├── keywords (52)                       │
│ └── potions (42)                        │
└─────────────────────────────────────────┘
         ↓
Parse into _cards, _relics, _creatures, etc.
         ↓
Combat Simulation
         ↓
card_data = game_data_loader.get_card_data("Bash")
         ↓
_parse_card_damage(card_data)
         ↓
├── Structured field? → 8
├── Regex parse? → 8
└── Hardcoded fallback? → 8
         ↓
Use damage value in beam search
```

## Error Handling Strategy

### Missing items.json
```python
# Startup (auto_load=True)
GameDataLoader("/bad/path")
→ Raises: FileNotFoundError with clear message
→ Action: User must install StSExporter or fix path

# Runtime (auto_load=False)
game_data_loader.get_card_data("Bash")
→ Returns: None
→ Logs: Warning about uninitialized loader
→ Fallback: Communication Mod card data (limited)
```

### Corrupted items.json
```python
load_data()
→ Raises: JSONDecodeError with line number
→ Action: User must reinstall StSExporter or manually fix file
```

### Card Not Found
```python
game_data_loader.get_card_data("UnknownCard")
→ Returns: None (current behavior)
→ Caller handles: Falls back to Communication Mod data
```

## Testing Strategy

### Unit Tests (manual, no pytest)
```python
# test_game_data_loading.py
def test_load_items_json():
    loader = GameDataLoader(EXPORT_PATH)
    assert len(loader._cards) == 721
    assert len(loader._relics) == 178

def test_get_card_data():
    data = game_data_loader.get_card_data("Bash")
    assert data is not None
    assert data['name'] == "Bash"
    assert _parse_card_damage(data) == 8

def test_wsl_path_conversion():
    path = convert_windows_path_to_wsl("D:\\path\\to\\file")
    assert path == "/mnt/d/path/to/file"

def test_missing_items_json():
    with pytest.raises(FileNotFoundError):
        GameDataLoader("/bad/path", auto_load=True)
```

### Integration Test
```python
# test_combat_with_game_data.py
def test_beam_search_uses_card_damage():
    context = create_test_context()
    context.hand = [Card("Heavy Blade")]
    damage = _parse_card_damage(get_card_data("Heavy Blade"))
    assert damage == 14  # From hardcoded metadata
```

## Backward Compatibility

### Breaking Changes
1. `spirecomm.spire.data_loader` module removed
2. `game_data` global variable removed
3. `initialize_game_data()` function removed

### Migration Guide
```python
# BEFORE
from spirecomm.spire.data_loader import game_data, initialize_game_data
initialize_game_data("/custom/path")
card = game_data.get_card_by_name("Bash")

# AFTER
from spirecomm.data.loader import game_data_loader
loader = GameDataLoader("/custom/path")
card = game_data_loader.get_card_data("Bash")
```

### Deprecation Path
1. Phase 1-4: Keep old loader with deprecation warnings
2. Archive change: Remove old loader entirely
3. Update documentation to reference new import path

## Future Extensions

### Short Term
1. Add `get_all_cards_by_type()` for filtering
2. Cache parsed damage values to avoid repeated regex
3. Add validation for items.json version

### Long Term
1. Contribute damage/block fields to StSExporter
2. Auto-generate CARD_METADATA from items.json
3. Add card description localization support
