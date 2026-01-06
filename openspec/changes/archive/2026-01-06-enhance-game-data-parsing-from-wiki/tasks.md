## 1. Implementation

- [ ] 1.1 Create `WikiDataLoader` class in `spirecomm/data/loader.py` to parse wiki-card-data.txt
  - Add `_load_wiki_data()` method with lazy loading
  - Implement `_parse_text_field_for_upgrade_values(text: str) -> Tuple[Optional[int], Optional[int]]`
  - Extract `Text` and `CostPlus` fields using regex
  - Cache parsed data in `self._wiki_data: Dict[str, Dict]`

- [ ] 1.2 Update `GameDataLoader.__init__()` to support wiki data path
  - Add `wiki_data_path: Optional[str] = None` parameter
  - Default to `os.path.join(data_path, "wiki-card-data.txt")`
  - Initialize `self._wiki_data: Optional[Dict] = None`

- [ ] 1.3 Integrate wiki parsing into `GameDataLoader._parse_card_damage()`
  - Insert wiki parsing as Stage 2 (before regex)
  - Call `_load_wiki_data()` if not already loaded
  - Extract base_damage and upgraded_damage from `Text` field pattern `[base|upgraded]`
  - Return base_damage for unupgraded cards, upgraded_damage for `card_id.endswith('+')`

- [ ] 1.4 Integrate wiki parsing into `GameDataLoader._parse_card_block()`
  - Insert wiki parsing as Stage 2
  - Extract base_block and upgraded_block from `Text` field
  - Return appropriate value based on card upgrade status

- [ ] 1.5 Add `CostPlus` field extraction for upgraded cost detection
  - Extract `CostPlus` field from wiki data
  - Support cards with different costs when upgraded (e.g., Havoc: Cost=1, CostPlus=0)

- [ ] 1.6 Update `_is_card_aoe()` to use wiki data
  - Check wiki data for AOE indicators in `Text` field (e.g., "ALL enemies")
  - Keep existing description parsing as fallback

## 2. CARD_METADATA Cleanup

- [ ] 2.1 Identify cards safe to remove from CARD_METADATA
  - Compare wiki-extracted values with CARD_METADATA entries
  - Flag entries where wiki matches hardcoded values
  - Keep dynamic formula cards (Body Slam, Whirlwind, Bludgeon, Rage, Reaper)

- [ ] 2.2 Remove static card entries from CARD_METADATA
  - Remove Bash, Defend, Strike, Cleave, Iron Wave, etc.
  - Keep entries with `is_x_damage=True` or `is_x_block=True`
  - Keep entries with dynamic calculation notes (e.g., "Damage = player_block")

- [ ] 2.3 Verify CARD_METADATA reduction
  - Count remaining entries (target: ~20-30 from current ~50)
  - Ensure all kept entries have `reason` field explaining necessity

## 3. Validation and Testing

- [ ] 3.1 Test wiki parser on sample cards
  - Test Bash: `[8|10]` → base=8, upgraded=10
  - Test Defend: `[5|8]` → base=5, upgraded=8
  - Test Body Slam: returns None (X-card, use CARD_METADATA)
  - Test Whirlwind: returns None (X-card, use CARD_METADATA)

- [ ] 3.2 Validate against all 709 cards
  - Iterate through `game_data_loader.get_all_cards()`
  - Extract values from wiki data for each
  - Log cards where extraction fails
  - Verify failure cards are in CARD_METADATA

- [ ] 3.3 Performance testing
  - Measure startup time with wiki loading
  - Target: < 100ms for `GameDataLoader` initialization
  - Test lazy loading (wiki data loads only on first access)

- [ ] 3.4 Cross-validation with CARD_METADATA
  - Compare wiki-extracted values with CARD_METADATA for overlapping cards
  - Log discrepancies (e.g., wiki says 8 damage, CARD_METADATA says 9)
  - Manually review discrepancies and update wiki parser or CARD_METADATA

## 4. Documentation and Logging

- [ ] 4.1 Update docstrings in `GameDataLoader`
  - Document new Stage 2 (wiki parsing)
  - Update `_parse_card_damage()` docstring with 4-stage approach
  - Update `_parse_card_block()` docstring

- [ ] 4.2 Add logging for wiki data loading
  - Log "Loaded wiki data for 709 cards" on successful load
  - Log "Wiki data not found, falling back to CARD_METADATA" if file missing
  - Log "Failed to parse wiki card: {card_name}" for parsing errors

- [ ] 4.3 Update CLAUDE.md
  - Add wiki-card-data.txt to exported files section
  - Document 4-stage parsing approach
  - Update CARD_METADATA description (reduced scope)

## 5. Error Handling and Edge Cases

- [ ] 5.1 Handle missing wiki-card-data.txt file
  - Return None from wiki parsing stage
  - Fall back to Stage 3 (regex) and Stage 4 (CARD_METADATA)
  - Log info message (not error) - wiki data is optional enhancement

- [ ] 5.2 Handle malformed wiki entries
  - Skip cards with missing `Text` field
  - Skip cards with unparseable upgrade values
  - Log warnings for skipped cards

- [ ] 5.3 Handle upgraded card detection
  - Check `card.card_id.endswith('+')` for upgraded status
  - Return `upgraded_damage` or `upgraded_block` for upgraded cards
  - Normalize card_id by stripping '+' when looking up in wiki data

- [ ] 5.4 Ensure backward compatibility
  - Verify existing code paths still work without wiki data
  - Test with wiki file deleted (graceful degradation)
  - Ensure no API changes to public methods

## 6. Code Review and Cleanup

- [ ] 6.1 Remove unused imports after refactoring
  - Check for regex imports used only in removed code
  - Verify all imports are still necessary

- [ ] 6.2 Add inline comments for complex parsing logic
  - Explain regex patterns for wiki data extraction
  - Document upgrade value format `[base|upgraded]`

- [ ] 6.3 Run validation
  - Execute `openspec validate enhance-game-data-parsing-from-wiki --strict`
  - Fix all validation errors before requesting approval
