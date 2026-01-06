## MODIFIED Requirements

### Requirement: X-Card Detection in Simulation

The combat simulation SHALL detect X-cards and trigger dynamic calculation when:

1. The card has `is_x_damage=True` or `is_x_block=True` in CARD_METADATA (reduced subset)
2. The card's base damage/block is 0 (Communication Mod doesn't provide these values)
3. The card is being evaluated for play in beam search

**Reduced CARD_METADATA Scope**:
- **Before**: ~50 cards (including static cards like Bash, Defend)
- **After**: ~20-30 cards (only dynamic formula cards like Body Slam, Whirlwind, Bludgeon, Rage)

The simulation SHALL:
- Normalize card_id by removing '+' suffix (handle upgraded cards)
- Match against known X-card IDs in reduced CARD_METADATA
- Call appropriate calculation method
- Fall back to 0 if card is unrecognized

#### Scenario: Detect Body Slam (X-card in reduced CARD_METADATA)
- **GIVEN** a Card with card_id='Body Slam'
- **AND** CARD_METADATA has been reduced (static cards removed)
- **WHEN** checking if card is X-damage
- **THEN** system SHALL match 'Body Slam' in X-card list
- **AND** SHALL call `_calculate_x_damage()`
- **AND** SHALL return player_block value
- **AND** CARD_METADATA entry SHALL have reason: "X-damage = player_block"

#### Scenario: Static card no longer in CARD_METADATA
- **GIVEN** a Card with card_id='Bash' (previously in CARD_METADATA)
- **AND** CARD_METADATA has been reduced (Bash removed)
- **WHEN** checking if card is X-damage
- **THEN** system SHALL NOT find 'bash' in CARD_METADATA
- **AND** SHALL NOT treat as X-card
- **AND** SHALL parse damage from wiki data: `[8|10]` → 8 or 10
- **AND** combat simulation SHALL use static value (not dynamic)

#### Scenario: X-card detection unchanged after reduction
- **GIVEN** the reduced CARD_METADATA (20-30 entries)
- **WHEN** iterating through X-card list
- **THEN** all entries SHALL have `is_x_damage=True` or `is_x_block=True`
- **AND** each entry SHALL have dynamic calculation logic (not static values)
- **AND** examples: Body Slam (damage=player_block), Rage (block=max_energy)

#### Scenario: Upgraded X-card normalization
- **GIVEN** a Card with card_id='Body Slam+' (upgraded)
- **AND** reduced CARD_METADATA entry: 'Body Slam' (unupgraded)
- **WHEN** checking if card is X-damage
- **THEN** system SHALL normalize to 'Body Slam' (remove '+')
- **AND** SHALL match in reduced CARD_METADATA
- **AND** SHALL treat same as unupgraded version (X-cards scale identically)

#### Scenario: Unknown card returns 0 (fallback behavior)
- **GIVEN** a Card with card_id='UnknownCard'
- **AND** card not in wiki data (or wiki parsing failed)
- **AND** card not in reduced CARD_METADATA
- **AND** base_damage is 0
- **WHEN** checking if card is X-damage
- **THEN** system SHALL NOT match in CARD_METADATA
- **AND** SHALL return 0 (fallback behavior)
- **AND** SHALL NOT crash

#### Scenario: CARD_METADATA entries have reason field
- **GIVEN** the reduced CARD_METADATA after static card removal
- **WHEN** inspecting X-card entries
- **THEN** each entry SHALL have a `reason` field
- **AND** the reason SHALL explain the dynamic formula
- **AND** examples: "X-damage = player_block", "X-block = max_energy", "Damage = min(30, 12 + block//10)"

---

### Requirement: Fallback Behavior

The system SHALL fail gracefully when encountering unrecognized or malformed X-cards, with enhanced fallback to wiki data parsing.

**Fallback Rules** (updated):
1. Check wiki-card-data.txt for static values (NEW)
2. Return 0 for unknown X-cards (safe default)
3. Log warnings for cards with `is_x_damage=True` but no calculation logic
4. Never crash due to missing X-card logic
5. Allow game to continue (just with potentially suboptimal play)

#### Scenario: Static card uses wiki data fallback
- **GIVEN** a card like 'Cleave' previously in CARD_METADATA with `{damage: 8, aoe: True}`
- **AND** CARD_METADATA no longer has 'cleave' entry
- **AND** wiki data has `Text = "Deal [8|11] damage to ALL enemies."`
- **WHEN** simulating this card
- **THEN** wiki parser SHALL extract damage=8 (or 11 for upgraded)
- **AND** AOE detection SHALL find "ALL enemies" in wiki Text
- **AND** simulation SHALL use wiki values (not CARD_METADATA)
- **AND** no warning SHALL be logged (wiki parsing successful)

#### Scenario: Wiki data unavailable falls back to CARD_METADATA
- **GIVEN** an X-card like 'Body Slam' with `is_x_damage=True`
- **AND** wiki-card-data.txt does not exist
- **WHEN** simulating this card
- **THEN** wiki parsing SHALL return None
- **AND** system SHALL check CARD_METADATA
- **AND** SHALL find Body Slam entry with `is_x_damage=True`
- **AND** SHALL calculate dynamic damage based on player_block

#### Scenario: Unknown X-card returns 0
- **GIVEN** a card marked `is_x_damage=True` in CARD_METADATA
- **AND** no calculation logic exists for this card (missing from implementation)
- **WHEN** simulating this card
- **THEN** system SHALL return 0 for damage
- **AND** system SHALL log a warning: "No calculation logic for X-card: {card_id}"
- **AND** game SHALL continue without crashing
- **AND** beam search SHALL score the card low (0 damage)

#### Scenario: Missing game state returns 0
- **GIVEN** Body Slam calculation needs state.player_block
- **AND** state object is None or malformed
- **WHEN** attempting to calculate damage
- **THEN** system SHALL catch the error (try/except)
- **AND** return 0 as safe fallback
- **AND** game SHALL continue
- **AND** log a warning: "Failed to calculate X-damage for {card_id}: {error}"

#### Scenario: Division by zero protection
- **GIVEN** a formula that divides by game state (e.g., Bludgeon: `block // 10`)
- **AND** the divisor is 0 (player_block=0)
- **WHEN** performing calculation
- **THEN** system SHALL handle `ZeroDivisionError` or check divisor
- **AND** return base value (12 for Bludgeon)
- **AND** NOT crash with ZeroDivisionError
- **AND** calculation SHALL work correctly when player_block > 0
