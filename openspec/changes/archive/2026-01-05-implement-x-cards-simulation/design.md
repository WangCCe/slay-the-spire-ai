# implement-x-cards-simulation Design

## Architecture

### Current State (Broken)

```
Card Evaluation Flow:
├── _parse_card_damage(card_data)
│   ├── Check CARD_METADATA
│   ├── If is_x_damage=True → return 0  ❌
│   └── AI sees 0 damage, ignores card  ❌
```

### Target State

```
Card Evaluation Flow:
├── _parse_card_damage(card_data)
│   ├── Check CARD_METADATA
│   ├── If is_x_damage=True → return 0  (marker only)
│   └── AI sees 0 damage, checks for X-calculation  ✅
│
├── _apply_attack() / _apply_skill()
│   ├── Detect X-cards by card_id
│   ├── Calculate dynamic value based on state  ✅
│   │   ├── Body Slam: damage = player_block
│   │   ├── Rage: block = energy_available
│   │   ├── Whirlwind: damage = energy × monsters
│   │   └── Bludgeon: damage = min(12, block) up to 30
│   └── Use calculated value in simulation  ✅
```

## Key Design Decisions

### 1. Where to Calculate X-Values?

**Decision**: Calculate in `_apply_attack()` / `_apply_skill()` methods

**Rationale**:
- These methods already have access to `SimulationState` (block, energy, monsters)
- Keeps calculation logic close to where it's used
- Doesn't require changing the parser interface

**Alternative Rejected**: Calculate in `_parse_card_damage()`
- Would need to pass context/state to parser
- Parser should remain stateless (data → value)

### 2. Card Identification

**Decision**: Check `card.card_id` string

**Rationale**:
- Simple and direct
- No need to extend CARD_METADATA with calculation functions
- Easy to add new cards

**Implementation**:
```python
if card.card_id in ['Body Slam', 'Body Slam+']:
    damage = state.player_block
elif card.card_id in ['Rage', 'Rage+']:
    block = context.energy_available
```

### 3. Handling Upgraded Cards

**Decision**: Match both base and upgraded names

**Rationale**:
- Body Slam and Body Slam+ have same X-calculation logic
- Card IDs use '+' suffix for upgrades (Communication Mod convention)

**Implementation**:
```python
# Option 1: Explicit list
if card.card_id in ['Body Slam', 'Body Slam+']:
    damage = state.player_block

# Option 2: Normalize
card_name = card.card_id.replace('+', '')
if card_name == 'Body Slam':
    damage = state.player_block
```

### 4. AOE X-Cards (Whirlwind)

**Decision**: Calculate per-target damage, AOE multiplies automatically

**Current AOE flow**:
```python
if is_aoe:
    for monster in state.monsters:
        damage = base_damage + strength  # Applied to each monster
```

**With X-calculation**:
```python
if card.card_id == 'Whirlwind':
    base_damage = context.energy_available  # X = energy
# AOE logic applies base_damage to each monster
# Total damage = energy × num_monsters ✅
```

### 5. Bludgeon Edge Case

**Card**: Bludgeon costs 2 energy, damage = 12-30 based on current block

**Formula**: `damage = min(12, block) up to max 30`

**Implementation**:
```python
if card.card_id == 'Bludgeon':
    base_damage = min(30, max(12, state.player_block // 10))
```

Wait, let me check actual game formula...

**Actually**: According to game data, Bludgeon is "X damage where X = 12-30 based on current block"

**Real formula**: Each 10 block adds 1 damage, starting from 12, capped at 30
- 0 block: 12 damage
- 10 block: 13 damage
- 180+ block: 30 damage

```python
if card.card_id == 'Bludgeon':
    base_damage = min(30, 12 + state.player_block // 10)
```

## Implementation Approach

### Phase 1: Add X-Card Helper Methods

Create dedicated methods for X-card calculation:

```python
def _calculate_x_damage(self, card: Card, state: SimulationState, context: DecisionContext) -> int:
    """Calculate dynamic damage for X-damage cards."""
    card_name = card.card_id.replace('+', '')

    if card_name == 'Body Slam':
        return state.player_block
    elif card_name == 'Bludgeon':
        return min(30, 12 + state.player_block // 10)
    elif card_name == 'Whirlwind':
        return context.energy_available
    # ... other X-damage cards

    return 0  # Fallback
```

### Phase 2: Integrate into Simulation

Update `_apply_attack()` to use helper:

```python
def _apply_attack(self, state: SimulationState, card: Card, target, target_index):
    # Get base damage
    base_damage = getattr(card, 'damage', 0)

    # Check for X-damage cards
    if base_damage == 0:
        base_damage = self._calculate_x_damage(card, state, context)

    # ... rest of attack logic
```

### Phase 3: Update Beam Search Scoring

Ensure FastScore uses X-calculation too:

```python
def _fast_score_card(self, card, context):
    base_damage = getattr(card, 'damage', 0)
    if base_damage == 0 and is_x_card(card):
        base_damage = self._calculate_x_damage(card, state, context)
    # ... calculate score
```

## Data Flow

```
Combat Simulation State:
├── player_block: 20
├── player_energy: 3
├── monsters: [Monster1(30HP), Monster2(25HP)]
└── hand: [Body Slam, Rage, Whirlwind]

Card: Body Slam
├── _apply_attack()
├── _calculate_x_damage(Body Slam) → player_block (20)
├── Apply to target → 20 damage ✅
└── Score calculation → high score ✅

Card: Rage
├── _apply_skill()
├── _calculate_x_block(Rage) → energy_available (3)
├── state.player_block += 3 ✅
└── Score calculation → defensive bonus ✅

Card: Whirlwind (3 energy, 2 monsters)
├── _apply_attack()
├── _calculate_x_damage(Whirlwind) → energy (3)
├── is_aoe → apply to each monster
├── Monster1: 3 damage
├── Monster2: 3 damage
└── Total: 6 damage ✅
```

## Cards to Implement

### Priority 1: Ironclad X-Cards (Most Common)

| Card | Type | Formula | Metadata |
|------|------|---------|----------|
| Body Slam | Attack | damage = player_block | `is_x_damage: True` |
| Rage | Skill | block = energy | `is_x_block: True` |
| Whirlwind | Attack | damage = energy (AOE) | `is_x_damage: True, aoe: True` |
| Bludgeon | Attack | damage = min(30, 12 + block//10) | `is_x_damage: True` |

### Priority 2: Less Common (Future)

| Card | Type | Formula | Complexity |
|------|------|---------|------------|
| Reaper | Attack | damage = 3, heal = damage dealt | Needs post-calc |
| Pummel | Attack | damage = 3 × energy | Multi-hit |
| Tempest | Attack | damage = 4 × energy | Multi-hit |

## Edge Cases

### 1. Zero State

```python
# Body Slam with 0 block
damage = state.player_block  # = 0
# Card does nothing (correct behavior)

# Rage with 0 energy
block = context.energy_available  # = 0
# Can't play card anyway (costs 1)
```

### 2. High Values

```python
# Body Slam with 50 block
damage = 50  # Massive damage!
# AI should prioritize playing this

# Rage with 3 energy (but limited by card cost)
block = 3  # Only gain block for energy actually spent
# Correct: 1 energy = 3 block (costs 1, so 3-1=2 available? No, cost is separate)
```

Wait, **Rage formula clarification needed**:

Rage: "Gain X Block. X equals your Energy." (from card description)

**Interpretation**: X = **total** energy, not energy after playing card
- With 3 energy max: Play Rage (costs 1) → gain 3 block
- With 2 energy max: Play Rage (costs 1) → gain 2 block

```python
# Rage calculation
max_energy = context.max_energy  # Not energy_available
block = max_energy
```

### 3. AOE Multiplication

Whirlwind with 3 energy, 4 monsters:
- Per monster: 3 damage
- Total: 12 damage
- Score calculation should account for this

## Testing Strategy

### Unit Tests (Manual)

```python
# test_x_card_calculation.py

def test_body_slam_damage():
    state = SimulationState(player_block=20)
    card = Card('Body Slam')
    damage = _calculate_x_damage(card, state, context)
    assert damage == 20

def test_rage_block():
    context = DecisionContext(max_energy=3)
    card = Card('Rage')
    block = _calculate_x_block(card, state, context)
    assert block == 3

def test_whirlwind_aoe():
    state = SimulationState(monsters=[...])  # 3 monsters
    context = DecisionContext(energy_available=2, max_energy=3)
    card = Card('Whirlwind')
    damage = _calculate_x_damage(card, state, context)
    assert damage == 3
    # AOE should multiply: 3 × 3 = 9 total damage

def test_bludgeon_scaling():
    state = SimulationState(player_block=50)
    card = Card('Bludgeon')
    damage = _calculate_x_damage(card, state, context)
    assert damage == min(30, 12 + 50//10)  # = 17
```

### Integration Test

Play through actual combat with X-cards in deck, verify:
- AI plays Body Slam when has high block
- AI prioritizes Rage when needs defense
- AI uses Whirlwind against multiple monsters
- No crashes or errors

## Future Extensions

### Short Term
- Add more Ironclad X-cards (Pummel, Tempest)
- Add Silent X-cards (Cloak and Dagger, Deadly Poison)
- Add Defect X-cards (Focus, Loop)

### Long Term
- Generalize X-calculation system (register calculators per card)
- Add X-cards that depend on enemy state (e.g., "equal to enemy block")
- Add multi-hit X-cards (needs repeated attack simulation)
