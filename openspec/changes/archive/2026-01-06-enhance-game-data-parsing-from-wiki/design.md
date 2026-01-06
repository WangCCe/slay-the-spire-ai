## Context

The Slay the Spire AI requires accurate card metadata (damage, block, AOE status) for combat decision-making. The current implementation uses a 3-stage parsing approach:

1. **Stage 1**: Check structured `damage`/`block` fields in items.json (currently empty)
2. **Stage 2**: Parse description text with regex (works for simple cards like "Deal 8 damage")
3. **Stage 3**: Consult CARD_METADATA for complex cards (~50 entries, 217 lines)

**Problem**: Stage 3 requires manual maintenance and has incomplete coverage.

**Opportunity**: The `wiki-card-data.txt` file contains Lua-formatted card data with:
- Structured upgrade values: `[8|10]` format (base=8, upgraded=10)
- Explicit upgrade cost fields: `CostPlus = 0`
- Complete card coverage: All 709 cards with metadata

## Goals / Non-Goals

**Goals**:
- Extract base and upgraded combat values from wiki-card-data.txt
- Reduce CARD_METADATA to truly complex cards only (X-damage, dynamic formulas)
- Maintain backward compatibility (fallback to CARD_METADATA)
- Keep parsing under 100ms on startup

**Non-Goals**:
- Replace CARD_METADATA entirely (still needed for X-cards like Whirlwind)
- Parse all wiki data fields (only damage/block/AOE needed)
- Create new API (extend existing GameDataLoader)

## Decisions

### Decision 1: Add Wiki Parsing as New Stage 2

**What**: Insert wiki parsing between description regex and CARD_METADATA:
- **Stage 1**: Structured fields (future-proof)
- **Stage 2**: Wiki data parser (NEW)
- **Stage 3**: Description regex (existing)
- **Stage 4**: CARD_METADATA fallback (existing)

**Why**:
- Wiki data is more structured than description text
- Explicit upgrade values avoid regex ambiguity
- Keeps regex and CARD_METADATA as fallbacks

**Alternatives considered**:
- **Replace regex entirely**: Rejected - regex works for simple cards and is faster
- **Replace CARD_METADATA entirely**: Rejected - wiki data doesn't have dynamic formulas (e.g., Body Slam damage = player_block)

### Decision 2: Parse Wiki Data on-Demand

**What**: Load wiki-card-data.txt only when needed (lazy loading), not during `load_data()`.

**Why**:
- Wiki file is 94KB (larger than items.json)
- Not all queries need wiki data (e.g., card name lookup)
- Avoids unnecessary startup time

**Implementation**:
- Load wiki data on first call to `_parse_card_damage()` or `_parse_card_block()`
- Cache parsed data in memory for subsequent calls
- Use `self._wiki_data: Optional[Dict] = None`

### Decision 3: Minimal Lua Parser

**What**: Use regex-based extraction, not full Lua parser.

**Why**:
- Python standard library only (no external dependencies like `lua51`)
- Wiki format is predictable (field = value)
- Only need 3 fields: `Text` (description with `[base|upgraded]`), `CostPlus`, `Name`

**Alternatives considered**:
- **Full Lua parser**: Rejected - adds external dependency, overkill for simple extraction
- **Use items.json only**: Rejected - doesn't have upgrade values in structured format

**Parser approach**:
```python
# Extract Text field with upgrade values
text_pattern = r'Text = "(.*?)"'
match = re.search(text_pattern, wiki_entry)

# Extract [base|upgraded] values
upgrade_pattern = r'\[(\d+)\|(\d+)\]'
base_value, upgraded_value = match.groups()
```

### Decision 4: Keep CARD_METADATA for True X-Cards

**What**: Maintain CARD_METADATA for cards with dynamic formulas (Body Slam, Whirlwind, Bludgeon).

**Why**:
- Wiki data contains static values only
- X-cards require runtime calculation based on game state
- Formula logic belongs in code, not data files

**CARD_METADATA scope after change**:
- **Keep**: Body Slam, Whirlwind, Bludgeon, Rage, Reaper (dynamic cards)
- **Remove**: Bash, Defend, Cleave, Iron Wave, etc. (static cards with upgrade values)

## Risks / Trade-offs

### Risk 1: Wiki Data Format Changes

**Risk**: StSExporter may change wiki-card-data.txt format, breaking parser.

**Mitigation**:
- Keep CARD_METADATA and regex as fallbacks
- Log warnings if wiki parsing fails
- Graceful degradation to Stage 3/4

### Risk 2: Startup Performance

**Risk**: Loading 94KB wiki file increases startup time.

**Mitigation**:
- Lazy loading (only load when needed)
- Cache parsed data after first load
- Monitor startup time (target < 100ms)

### Trade-off: Parser Complexity vs Coverage

**Choice**: Use regex parser (simpler) vs full Lua parser (more robust).

**Rationale**:
- Wiki format is stable (hasn't changed in years)
- Regex sufficient for needed fields
- Avoids external dependency

## Migration Plan

**Steps**:

1. **Add wiki data loader** (non-breaking)
   - Add `_load_wiki_data()` method to GameDataLoader
   - Add `self._wiki_data` cache
   - Parse Text and CostPlus fields

2. **Update parsing pipeline** (non-breaking)
   - Insert wiki parsing as Stage 2
   - Keep existing stages as fallbacks

3. **Reduce CARD_METADATA** (safe)
   - Remove entries with static values (e.g., Bash: damage=8, upgraded_damage=10)
   - Keep dynamic entries (Body Slam, Whirlwind)
   - Verify with tests

4. **Validation** (required)
   - Test parser on all 709 cards
   - Compare extracted values with CARD_METADATA
   - Log discrepancies for manual review

**Rollback**:
- Revert commits to remove CARD_METADATA entries
- Wiki parser can remain (non-functional fallback)

## Open Questions

1. **Should we parse all wiki fields now or defer?**
   - **Recommendation**: Defer - only parse damage/block/AOE needed for current use case

2. **Should we add validation to ensure wiki data matches items.json?**
   - **Recommendation**: Yes - log warnings if card names don't match between files

3. **Should we support both Red/Silent/Defect cards from day 1?**
   - **Recommendation**: Yes - parser should be color-agnostic
