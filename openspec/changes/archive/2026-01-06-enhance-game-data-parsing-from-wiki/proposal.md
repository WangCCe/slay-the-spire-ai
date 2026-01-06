# Change: Enhance Game Data Parsing from Wiki Export

## Why

The current game data loader relies on 217 lines of hardcoded `CARD_METADATA` to extract combat statistics (damage, block, AOE) for complex cards that cannot be parsed from `items.json` descriptions. This creates maintenance burden:

1. **Manual updates required**: Adding new cards or updating values requires editing code
2. **Error-prone**: Hardcoded values can become outdated when game updates change card stats
3. **Incomplete coverage**: Only ~50 cards have metadata, limiting AI decision quality

The `wiki-card-data.txt` file (94KB, 3374 lines) exported by StSExporter contains structured card data with formatted upgrade values like `[8|10]` (base=8, upgraded=10) and `CostPlus` fields, providing a more reliable and comprehensive data source.

## What Changes

- **Add wiki-card-data.txt parser**: Parse Lua-formatted card data with upgrade value extraction
- **Enhance GameDataLoader**: Add new parsing stage that checks wiki data before falling back to CARD_METADATA
- **Reduce hardcoded metadata**: Remove entries that can be reliably extracted from wiki data
- **Add upgrade value support**: Extract both base and upgraded values for damage/block
- **Maintain backward compatibility**: Keep CARD_METADATA for truly complex cards (e.g., Whirlwind X-damage)

## Impact

- Affected specs:
  - `game-data-loading` (add wiki parsing stage)
  - `x-card-calculation` (reduce CARD_METADATA dependency)
- Affected code:
  - `spirecomm/data/loader.py` (add wiki parser, update parsing pipeline)
- Benefits:
  - More accurate card data (direct from game export)
  - Reduced maintenance (fewer hardcoded values)
  - Better upgrade detection (explicit `CostPlus` and `[base|upgraded]` format)
- Non-breaking:
  - Existing CARD_METADATA kept as fallback
  - No API changes to `GameDataLoader`
