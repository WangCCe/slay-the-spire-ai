# Design: Wiki Monster Data Integration

## Overview

This document describes the architectural design for integrating wiki monster data into the AI combat system. The design follows the existing pattern established by `game-data-loading` (wiki card data parsing) and extends the current threat evaluation system.

## Current Architecture

### Monster Data Flow
```
Game State (JSON) → Monster.from_json() → Monster Object
                                         → DecisionContext.monsters_alive
                                         → compute_threat(monster)
                                         → Target Selection / Combat Mode
```

### Current Threat Calculation
- **File**: `spirecomm/ai/decision/base.py:189-273`
- **Method**: `compute_threat(monster)`
- **Components**:
  1. Expected damage (move_adjusted_damage × hits)
  2. Debuff threat (+10 for Weak/Vulnerable)
  3. Scaling threat (+15 for elite/boss monsters)
  4. AOE threat (+8 for buffing allies)
  5. High HP threat (+5 for >50% HP)

### Current Monster Database
- **File**: `spirecomm/ai/heuristics/monster_database.py`
- **Structure**: Simple dict with threat_level, attacks, special_abilities, recommended_strategy
- **Coverage**: ~30 monsters
- **Limitation**: No move patterns, no detailed mechanics, no predictive capabilities

## Proposed Architecture

### Enhanced Data Flow
```
Wiki Data (JSON) → Enhanced Monster Database → compute_threat_v2()
                                            → Target Selection v2
                                            → Combat Mode Selection
                                            → Combat Simulation
```

### Data Structure Design

#### Enhanced Monster Database
**File**: `spirecomm/ai/heuristics/enhanced_monster_database.py`

```python
ENHANCED_MONSTER_DATABASE = {
    "Cultist": {
        # Basic Info
        "monster_type": "normal",  # normal/elite/boss
        "act": 1,

        # HP Data
        "hp_ranges": {
            "normal": {"min": 42, "max": 46},
            "ascension_10+": {"min": 44, "max": 48}
        },

        # Move Patterns
        "moves": [
            {"move_id": 0, "name": "Ritual", "intent": "BUFF", "effect": "+3 Strength"},
            {"move_id": 1, "name": "Dark Strike", "intent": "ATTACK", "damage": 6},
            {"move_id": 2, "name": "Incite", "intent": "BUFF", "effect": "Summon 1 Cultist"}
        ],
        "move_sequence": [0, 1, 2, 1, 1],  # Turn-by-turn pattern
        "move_cycle": "repeat_from_1",       # After move 2, cycle [1, 2]

        # Special Mechanics
        "special_mechanics": {
            "type": "summoner",
            "summons": [{"turn": 3, "name": "Cultist", "count": 1}],
            "scaling": {"type": "strength_scaling", "rate": "+3/turn", "threat_growth": 3.0}
        },

        # Weaknesses/Resistances
        "weaknesses": {"weak": 2.0, "vulnerable": 1.5},  # Multiplier
        "resistances": {"frail": 0.5},

        # Threat Profile
        "threat_profile": {
            "base_threat": 15,
            "scaling_threat": 3.0,      # Per turn
            "summon_threat": 20,
            "priority_target": True
        },

        # Strategy
        "recommended_strategy": {
            "primary": "kill_quickly",
            "reason": "Ritual gives +3 Strength, doubling damage each turn",
            "debuffs": ["weak", "vulnerable"],
            "ideal_turns_to_kill": 4
        }
    },

    "Lagavulin": {
        "special_mechanics": {
            "type": "hibernation",
            "sleep_turns": 1,
            "damage_scaling": "+6 per turn slept",
            "max_damage": 30
        },
        "threat_profile": {
            "hibernation_threat": 5,    # Low while sleeping
            "awakened_threat": 30,      # High after waking
            "priority_target": False     # Let it sleep
        }
    }
}
```

#### Data Loading Pattern
Following `game-data-loading` specification:

```python
class GameDataLoader:
    # Existing: _load_wiki_data() for cards
    # New: _load_monster_data() for monsters

    def _load_monster_data(self):
        """Load monster data from JSON files."""
        monster_data = {}
        data_files = [
            'spirecomm/data/monster_wiki_data/act1_elites.json',
            'spirecomm/data/monster_wiki_data/act2_elites.json',
            # ...
        ]
        for file_path in data_files:
            try:
                with open(file_path, 'r') as f:
                    monster_data.update(json.load(f))
            except FileNotFoundError:
                logger.info(f"Monster data not found at {file_path}")
        return monster_data
```

### Integration Points

#### 1. Enhanced Threat Calculation
**File**: `spirecomm/ai/decision/base.py`

**New Method**: `compute_threat_v2(monster)`

**Algorithm**:
```python
def compute_threat_v2(self, monster):
    enhanced_data = ENHANCED_MONSTER_DATABASE.get(monster.monster_id)
    if not enhanced_data:
        return self.compute_threat(monster)  # Fallback

    threat = 0

    # Component 1: Immediate threat (current intent)
    threat += monster.move_adjusted_damage * hits

    # Component 2: Future threat (predict next 2-3 moves)
    current_move_id = monster.move_id
    move_sequence = enhanced_data['move_sequence']
    current_idx = move_sequence.index(current_move_id)
    future_moves = move_sequence[current_idx+1:current_idx+4]

    for move_id in future_moves:
        move_data = find_move(enhanced_data['moves'], move_id)
        threat += move_data['damage'] * 0.8  # Discount future
        if 'summon' in move_data:
            threat += 20
        if 'Strength' in move_data.get('effect', ''):
            threat += 15

    # Component 3: Scaling threat (from database)
    scaling_rate = enhanced_data['threat_profile']['scaling_threat']
    estimated_ttd = monster.current_hp // 20
    threat += scaling_rate * estimated_ttd

    # Component 4: Special ability threat
    mechanics = enhanced_data['special_mechanics']
    if mechanics['type'] == 'summoner':
        threat += 20
    if mechanics['type'] == 'death_split':
        threat += 8 * len(mechanics['splits'])

    # Component 5: Composition threat (minions)
    for summon in mechanics.get('summons', []):
        threat += summon['count'] * 10

    return threat
```

**Backward Compatibility**:
- Keep existing `compute_threat()` unchanged
- New `compute_threat_v2()` calls `compute_threat()` if enhanced data missing
- Allows gradual migration, testing, rollback

#### 2. Enhanced Target Selection
**File**: `spirecomm/ai/heuristics/ironclad_combat.py`

**New Method**: `_choose_target_for_card_v2(card, context, state)`

**Priority Logic**:
```python
def _choose_target_for_card_v2(self, card, context, state):
    # Rule 1: Special mechanics handling
    for monster in monsters:
        enhanced_data = ENHANCED_MONSTER_DATABASE.get(monster.monster_id)
        if not enhanced_data:
            continue

        mechanics = enhanced_data['special_mechanics']

        # Summoner handling
        if mechanics['type'] == 'summoner':
            strategy = enhanced_data['recommended_strategy']
            if strategy['primary'] == 'kill_minions_first':
                # Prioritize minions (Reptomancer)
                return highest_threat_minion
            else:
                # Prioritize summoner (Cultist)
                return summoner

        # Hibernation handling
        if mechanics['type'] == 'hibernation':
            if monster.intent == Intent.SLEEP:
                # Deprioritize (remove from consideration)
                continue

        # Phase change handling
        if mechanics['type'] == 'phase_change':
            if in_burst_window(monster):
                # Prioritize during vulnerable phase
                return monster

    # Rule 2: AOE efficiency
    if card.is_aoe:
        if has_death_split_monsters(monsters):
            # AOE very efficient (Slime Boss)
            return None  # Use AOE
        if similar_hp(monsters):
            # AOE efficient
            return None  # Use AOE

    # Rule 3: Enhanced threat scoring
    threats = [(m, compute_threat_v2(m)) for m in monsters]
    return highest_threat_monster
```

#### 3. Combat Mode Selection
**File**: `spirecomm/ai/agent.py`

**New Function**: `select_combat_mode_with_monster_data(context)`

```python
def select_combat_mode_with_monster_data(context):
    # Analyze monster composition
    has_summoner = False
    has_phase_change = False
    has_hibernating = False
    total_scaling_threat = 0

    for monster in context.monsters_alive:
        enhanced_data = ENHANCED_MONSTER_DATABASE.get(monster.monster_id)
        if not enhanced_data:
            continue

        mechanics = enhanced_data['special_mechanics']
        threat_profile = enhanced_data['threat_profile']

        if mechanics['type'] == 'summoner':
            has_summoner = True
        if mechanics['type'] == 'phase_change':
            has_phase_change = True
        if mechanics['type'] == 'hibernation':
            has_hibernating = True

        total_scaling_threat += threat_profile.get('scaling_threat', 0)

    # Mode selection
    if has_summoner or (has_phase_change and has_boss):
        return CombatMode.AGGRESSIVE
    if has_elite or has_hibernating:
        return CombatMode.SEMI_AGGRESSIVE
    return CombatMode.BALANCED
```

#### 4. Combat Simulation Enhancement
**File**: `spirecomm/ai/heuristics/simulation.py`

**New Methods**:
```python
def predict_monster_moves(self, monster, look_ahead=2):
    """Predict next N moves from move sequence."""
    enhanced_data = ENHANCED_MONSTER_DATABASE.get(monster.monster_id)
    if not enhanced_data:
        return [current_move]

    move_sequence = enhanced_data['move_sequence']
    current_idx = move_sequence.index(monster.move_id)

    predicted = []
    for i in range(1, look_ahead + 1):
        next_idx = (current_idx + i) % len(move_sequence)
        next_move_id = move_sequence[next_idx]
        move_data = find_move(enhanced_data['moves'], next_move_id)
        predicted.append(move_data)

    return predicted

def simulate_card_play(self, state, card, target):
    # ... existing simulation ...

    # NEW: Handle death splits
    for monster in dead_monsters:
        enhanced_data = ENHANCED_MONSTER_DATABASE.get(monster.monster_id)
        if enhanced_data:
            mechanics = enhanced_data['special_mechanics']
            if mechanics['type'] == 'death_split':
                # Add split monsters to state
                for split in mechanics['splits']:
                    add_monsters(split['splits_into'])

    # NEW: Handle phase changes
    for monster in state.monsters:
        enhanced_data = ENHANCED_MONSTER_DATABASE.get(monster.monster_id)
        if enhanced_data:
            mechanics = enhanced_data['special_mechanics']
            if mechanics['type'] == 'phase_change':
                # Check HP thresholds
                hp_ratio = monster['hp'] / monster['max_hp']
                for phase in mechanics['phases']:
                    if hp_ratio <= phase['hp_threshold']:
                        # Change move pool
                        monster['move_pool'] = phase['move_pool']
                        break

    return new_state
```

## Trade-offs and Decisions

### Trade-off 1: Hardcoded vs JSON Storage
**Decision**: JSON files (like wiki-card-data.txt)

**Rationale**:
- Maintains consistency with existing pattern
- Easier to update without code changes
- Supports lazy loading (performance)
- Enables external tooling for validation

**Trade-offs**:
- Hardcoded would be faster (no file I/O)
- JSON requires path management
- JSON needs error handling for missing files

### Trade-off 2: Separate Enhanced Database vs Extend Current
**Decision**: Separate `ENHANCED_MONSTER_DATABASE`

**Rationale**:
- Current database is simple (threat_level, attacks)
- Enhanced database is complex (move patterns, mechanics)
- Allows gradual migration (fallback to old database)
- Cleaner separation of concerns

**Trade-offs**:
- More files to maintain
- Data duplication (some monsters in both)
- Need to keep in sync eventually

### Trade-off 3: Predictive Threat vs Reactive Threat
**Decision**: Implement both, use predictive when data available

**Rationale**:
- Backward compatibility (fallback to reactive)
- Performance (skip prediction for unknown monsters)
- Testing (compare old vs new threat scores)

**Trade-offs**:
- More complex code path
- Need to maintain both implementations
- Potential inconsistency between old and new

### Trade-off 4: Special Mechanic Handling in Target Selection
**Decision**: Explicit rules in `_choose_target_for_card_v2()`

**Rationale**:
- Clear, debuggable logic
- Easy to add new mechanic types
- Aligns with existing pattern (threat-based targeting)

**Trade-offs**:
- Hardcoded rules (not data-driven)
- Requires code changes for new mechanics
- Less flexible than learning-based approach

## Performance Considerations

### Threat Calculation Performance
**Target**: < 5ms per monster

**Optimizations**:
1. Lazy load enhanced database (only on first access)
2. Cache move pattern predictions
3. Early fallback to `compute_threat()` if data missing
4. Minimize dict lookups (access `enhanced_data` once)

**Profiling Plan**:
```python
import time

for monster in monsters:
    start = time.perf_counter()
    threat = compute_threat_v2(monster)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.005  # < 5ms
```

### Beam Search Impact
**Target**: Maintain < 100ms (95th percentile)

**Risk**: Enhanced threat calculation is called for each beam candidate (~100-200 times per turn)

**Mitigation**:
1. Cache threat scores per monster per turn (invalidate on state change)
2. Use simpler `compute_threat()` for beam search, `compute_threat_v2()` for final selection
3. Adaptive complexity: Use full prediction for elites/bosses, basic for normal monsters

### Memory Overhead
**Target**: < 50MB for enhanced database

**Calculation**:
- 62 monsters × ~2KB data per monster = ~124KB
- Python dict overhead: ~10× = ~1.2MB
- Well within budget

## Testing Strategy

### Unit Tests
```python
def test_threat_calculation_cultist():
    cultist = Monster(name="Cultist", monster_id="Cultist", hp=44)
    context = DecisionContext()
    context.turn = 1

    # Turn 1: After first Ritual
    threat = compute_threat_v2(cultist)
    assert threat == 21  # 15 base + 3 (Ritual scaling) + 3 (future damage)

    # Turn 2: After second Ritual
    context.turn = 2
    threat = compute_threat_v2(cultist)
    assert threat == 24  # 15 base + 6 (2× Ritual) + 3 (future damage)

def test_target_selection_reptomancer():
    # Reptomancer + 2 Daggers
    reptomancer = Monster(name="Reptomancer", hp=95)
    dagger1 = Monster(name="Dagger", hp=12)
    dagger2 = Monster(name="Dagger", hp=12)

    context = DecisionContext()
    context.monsters_alive = [reptomancer, dagger1, dagger2]

    # Play single-target attack (10 damage)
    card = Card(card_id="Strike", damage=6)
    target = _choose_target_for_card_v2(card, context, state)

    # Should target Dagger (kill minions first per strategy)
    assert target.name in ["Dagger", "Dagger"]

def test_hibernation_handling():
    lagavulin = Monster(name="Lagavulin", hp=87, intent=Intent.SLEEP)
    jaw_worm = Monster(name="Jaw Worm", hp=12, intent=Intent.ATTACK_DEFEND)

    context = DecisionContext()
    context.monsters_alive = [lagavulin, jaw_worm]

    card = Card(card_id="Strike", damage=6)
    target = _choose_target_for_card_v2(card, context, state)

    # Should ignore Lagavulin, target Jaw Worm
    assert target.name == "Jaw Worm"
```

### Integration Tests
```python
def test_cultist_combat_aggressive_mode():
    # Combat: 1 Cultist
    # Expected: AGGRESSIVE mode, kill before turn 3
    game_state = GameState(monsters=[cultist])
    context = DecisionContext(game_state)

    mode = select_combat_mode_with_monster_data(context)
    assert mode == CombatMode.AGGRESSIVE

    # Verify high-damage cards prioritized
    plan = beam_search(context)
    assert has_high_damage_cards(plan)

def test_lagavulin_ignored_while_sleeping():
    # Combat: Lagavulin (sleeping) + Jaw Worm
    # Expected: Target Jaw Worm first
    context = DecisionContext(game_state)

    target = _choose_target_for_card_v2(strike, context, state)
    assert target.monster_id != "Lagavulin"
```

### Performance Tests
```python
def test_beam_search_performance():
    # Complex combat: 4 monsters, 8 playable cards
    context = create_complex_combat()

    start = time.perf_counter()
    plan = beam_search(context)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.100  # < 100ms
```

## Error Handling

### Missing Enhanced Data
```python
def compute_threat_v2(self, monster):
    enhanced_data = ENHANCED_MONSTER_DATABASE.get(monster.monster_id)
    if not enhanced_data:
        # Graceful degradation
        logger.debug(f"Enhanced data missing for {monster.monster_id}, using fallback")
        return self.compute_threat(monster)
    # ...
```

### Malformed Move Sequence
```python
def predict_monster_moves(self, monster):
    enhanced_data = ENHANCED_MONSTER_DATABASE.get(monster.monster_id)
    if not enhanced_data:
        return [current_move]

    move_sequence = enhanced_data.get('move_sequence', [])
    if not move_sequence:
        logger.warning(f"No move_sequence for {monster.monster_id}")
        return [current_move]

    try:
        current_idx = move_sequence.index(monster.move_id)
    except ValueError:
        logger.warning(f"Current move {monster.move_id} not in sequence for {monster.monster_id}")
        return [current_move]
    # ...
```

### JSON Load Failure
```python
def _load_monster_data(self):
    monster_data = {}
    for file_path in data_files:
        try:
            with open(file_path, 'r') as f:
                monster_data.update(json.load(f))
        except FileNotFoundError:
            logger.info(f"Monster data not found at {file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {file_path}: {e}")
    return monster_data
```

## Migration Path

### Phase 1: Foundation (Days 1-4)
- Extract data for 22 priority monsters
- Create enhanced database structure
- Implement helper functions

### Phase 2: Integration (Days 5-9)
- Add `compute_threat_v2()`
- Add `_choose_target_for_card_v2()`
- Add `select_combat_mode_with_monster_data()`
- Enhance combat simulation

### Phase 3: Completion (Days 10-12)
- Extract remaining 40+ monsters
- Add ascension modifiers

### Phase 4: Validation (Days 13-15)
- Testing, benchmarking, documentation

### Rollback Strategy
- Keep existing `compute_threat()` unchanged
- Feature flag: Use enhanced data only if available
- Compare old vs new decisions in logs
- A/B testing: Run both systems, log differences

## Future Enhancements

1. **Machine Learning**: Learn optimal targeting from game data
2. **Player-Specific Strategies**: Adapt to player deck/archetype
3. **Real-Time Wiki Updates**: Auto-sync with Fandom Wiki changes
4. **Community Contributions**: Web UI for adding/editing monster data
5. **Advanced Simulations**: Model status effect interactions (Weak + Vulnerable)
