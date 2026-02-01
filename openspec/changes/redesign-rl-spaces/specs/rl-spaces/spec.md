## ADDED Requirements

### Requirement: RL action space layout (v2)
The system SHALL expose an action space of size 133 with fixed index ranges and formulas.

Action groups:
- PLAY_CARD: 60 actions, indices 0-59 (10 card slots x 6 targets).
- USE_POTION: 30 actions, indices 60-89 (5 potion slots x 6 targets).
- END_TURN: 1 action, index 90.
- REWARD: 5 actions, indices 91-95 (choice index 0-4).
- MAP: 6 actions, indices 96-101 (choice index 0-5).
- EVENT: 6 actions, indices 102-107 (choice index 0-5).
- SHOP: 15 actions, indices 108-122 (choice index 0-14).
- REST: 6 actions, indices 123-128 (fixed rest options).
- SYSTEM: 4 actions, indices 129-132 (Confirm, Cancel, Leave, Proceed).

Index formulas:
- PLAY_CARD: index = (card_slot * 6) + target_index
- USE_POTION: index = 60 + (potion_slot * 6) + target_index

#### Scenario: Encode a card action
- **WHEN** card_slot=3 and target_index=5
- **THEN** the encoded action index is 23

#### Scenario: Encode a potion action
- **WHEN** potion_slot=2 and target_index=1
- **THEN** the encoded action index is 73

### Requirement: Target index semantics
The system SHALL interpret target_index values as follows:
- 0: no target, self target, or all-enemies target
- 1-5: monster targets ordered left-to-right as provided by the game state

Invalid targets (missing or dead monsters) SHALL be masked.

#### Scenario: Mask missing targets
- **WHEN** only two monsters are alive
- **THEN** target_index values 3-5 are masked for PLAY_CARD and USE_POTION

### Requirement: Action masking by screen context
The system SHALL generate an action mask using screen_type, available_commands, and choice_list.

Rules:
- COMBAT (screen_type NONE and in_combat True): enable PLAY_CARD, USE_POTION, END_TURN; enable SYSTEM actions if their commands are available.
- CARD_REWARD/COMBAT_REWARD/CHEST: enable REWARD (choices 0-4) and SYSTEM actions that are available. COMBAT_REWARD SHALL allow repeated REWARD selections followed by SYSTEM Proceed.
- MAP: enable MAP (choices 0-5) and SYSTEM actions that are available.
- EVENT: enable EVENT (choices 0-5) and SYSTEM actions that are available.
- SHOP_SCREEN/SHOP_ROOM: enable SHOP (choices 0-14) and SYSTEM actions that are available.
- REST: enable REST (fixed options) and SYSTEM actions that are available.
- HAND_SELECT/GRID: enable REWARD (choices 0-4) and SYSTEM Confirm/Cancel when available.

If the number of available choices is less than the group capacity, the excess actions SHALL be masked. If the number of choices exceeds capacity, only the first N choices SHALL be enabled.

#### Scenario: Mask excess map choices
- **WHEN** screen_type is MAP with 3 choices
- **THEN** only indices 96-98 are enabled for the MAP group

### Requirement: Observation space layout
The system SHALL expose a fixed observation layout of approximately 328 continuous features composed of:
- PLAYER: 33 features
- MONSTERS: 150 features (5 slots x 30)
- HAND: 140 features (10 slots x 14)
- CONTEXT: 5 features

In addition, the system SHALL expose categorical ID inputs for embeddings:
- card_id slots: 10 (one per hand slot)
- potion_id slots: 5 (one per potion slot)
- relic_id slots: 40 (one per relic slot, acquisition order)

Slot ordering SHALL be stable: monsters ordered left-to-right; hand ordered by in-hand index. Empty slots SHALL be zero-filled.

#### Scenario: Zero-fill missing monsters
- **WHEN** only three monsters exist
- **THEN** monster slots 4-5 are all zeros

### Requirement: Observation feature definitions and normalization
The system SHALL use the following feature definitions and normalization rules.

Player features (33):
- Scalars (4): hp_ratio, energy_ratio, block_ratio=min(block,100)/100, floor_ratio=min(floor,50)/50
- Keywords (16): Strength, Dexterity, Vulnerable, Weak, Frail, Thorns, Artifact, Intangible, Poison, Regen, Ritual, Vigor, Mantra, Confused, PlatedArmor, Metallicize
  (keyword list is derived from `export/items.json` keywords and extended with PlatedArmor and Metallicize)
- Deck stats (4): draw_pile_count, discard_count, exhaust_count, hand_count (each min(x,100)/100)
- Class (9): one-hot for 4 base classes + 5 reserved mod classes

Monster slot features (30 each):
- Base (3): is_alive, hp_ratio, block_ratio=min(block,100)/100
- Intent (9): one-hot for ATTACK, ATTACK_BUFF, ATTACK_DEBUFF, ATTACK_DEFEND, BUFF, DEBUFF, DEFEND, DEFEND_BUFF, DEFEND_DEBUFF
- Intent values (2): intent_damage=tanh(dmg/50), intent_hits=min(hits,10)/10
- Keywords (16): Strength, Dexterity, Vulnerable, Weak, Frail, Thorns, Artifact, Intangible, Poison, Regen, Ritual, Vigor, Mantra, Confused, PlatedArmor, Metallicize
  (keyword list is derived from `export/items.json` keywords and extended with PlatedArmor and Metallicize)

Hand slot features (14 each):
- Upgrade (1): is_upgraded
- Cost (1): cost_for_turn normalized as min(max(cost,0),5)/5; X-cost treated as 1.0
- Playable (1): is_playable
- Type (4): one-hot for Attack, Skill, Power, Status/Curse
- Tags (7): AOE, Draw, Energy, Exhaust, Ethereal, Retain, Innate

Context features (5):
- Screen (5): one-hot for COMBAT, MAP, SHOP, REWARD, REST; other screens map to all zeros

Normalization:
- Non-negative stack values use min(x,20)/20 unless specified otherwise.
- Signed values (Strength, Dexterity) use tanh(x/10).

#### Scenario: Normalize block and floor
- **WHEN** block=120 and floor=60
- **THEN** block_ratio=1.0 and floor_ratio=1.0

### Requirement: Stable categorical ID mappings
The system SHALL map card_id, potion_id, and relic_id strings to stable integer IDs. The mapping SHALL be deterministic and consistent across runs; unknown IDs SHALL map to 0. These IDs SHALL be provided as separate categorical inputs for embeddings.

#### Scenario: Unknown card ID
- **WHEN** a card_id is not present in the mapping
- **THEN** the card_id feature is 0

#### Scenario: Unknown relic ID
- **WHEN** a relic_id is not present in the mapping
- **THEN** the relic_id feature is 0
