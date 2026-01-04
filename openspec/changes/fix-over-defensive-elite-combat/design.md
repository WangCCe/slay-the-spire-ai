# Design: Aggressive Elite Combat Mode System

## Architecture Overview

This design introduces **context-aware combat modes** that switch between balanced and aggressive playstyles based on enemy threat level. The AI will prioritize fast kills in elite fights while maintaining sensible defensive play in regular combats.

### Current Architecture (Before)

```
Combat State
    ↓
HeuristicCombatPlanner (always BALANCED mode)
    ↓
SimulationState.evaluate_sequence()
    ↓
calculate_outcome_score() [FIXED WEIGHTS]
    ├── DAMAGE_WEIGHT = 2.0 (all fights)
    ├── BLOCK_WEIGHT = 1.5 (all fights)
    └── W_DEATHRISK = 8.0 (all fights)
```

**Problem**: Same weights for all fights → over-defensive in elite encounters

### Proposed Architecture (After)

```
Combat State
    ↓
Enemy Threat Profiler (analyze enemy type/scaling)
    ↓
Combat Mode Selector
    ├── ELITE mode → AGGRESSIVE weights
    ├── SCALING mode → AGGRESSIVE weights
    └── REGULAR mode → BALANCED weights
    ↓
HeuristicCombatPlanner (mode-aware)
    ↓
SimulationState.evaluate_sequence()
    ↓
calculate_outcome_score() [MODE-DEPENDENT WEIGHTS]
    ├── AGGRESSIVE: DAMAGE=5.0, BLOCK=0.5, W_DEATHRISK=4.0
    └── BALANCED: DAMAGE=2.0, BLOCK=1.5, W_DEATHRISK=8.0
```

**Solution**: Context-aware mode switching with drastically different weight profiles

## Component Design

### 1. Enemy Threat Profiler

**Location**: `spirecomm/ai/decision/base.py` - New class `EnemyThreatProfiler`

**Purpose**: Analyze enemy composition and determine threat category

**Threat Categories**:
```python
class ThreatCategory(Enum):
    REGULAR = 0      # Normal hallway fights
    ELITE = 1        # Act 1/2/3 elites
    BOSS = 2         # Act bosses
    SCALING = 3      # Enemies with dangerous scaling (strength gain, multihit)
    HIGH_DEFENSE = 4 # Enemies with high block/armor
```

**Detection Logic**:
```python
def analyze_threat(monsters: List[Monster]) -> ThreatCategory:
    # 1. Check for elites/bosses by name
    elite_names = ['Gremlin Nob', 'Slavers', 'Sentry', 'The Guardian',
                   'Reptomancer', 'The Collector', 'The Champ', 'The Automatron']
    if any(m.name in elite_names for m in monsters):
        return ThreatCategory.ELITE

    # 2. Check for scaling mechanics
    for m in monsters:
        if m.has_power('StrengthGain') or m.has_power('Ritual'):
            return ThreatCategory.SCALING

    # 3. Check for multihit/combos
    total_monsters = len(monsters)
    if total_monsters >= 3:  # Multi-enemy fights (e.g., 3 slavers)
        return ThreatCategory.SCALING

    return ThreatCategory.REGULAR
```

**Rationale**: Proactive threat detection enables pre-emptive strategy adjustment

### 2. Combat Mode Selector

**Location**: `spirecomm/ai/heuristics/simulation.py` - `HeuristicCombatPlanner` class

**Purpose**: Select appropriate weight profile based on threat category

**Mode Profiles**:

| Weight            | BALANCED Mode | AGGRESSIVE Mode | Change |
|-------------------|---------------|-----------------|--------|
| DAMAGE_WEIGHT     | 2.0           | 5.0             | +150%  |
| BLOCK_WEIGHT      | 1.5           | 0.5             | -67%   |
| W_DEATHRISK       | 8.0           | 4.0             | -50%   |
| KILL_BONUS        | 100           | 200             | +100%  |
| ENERGY_EFFICIENCY | 3.0           | 5.0             | +67%   |

**Selection Logic**:
```python
def select_combat_mode(threat: ThreatCategory, turn: int, enemy_hp_pct: float) -> CombatMode:
    if threat in [ThreatCategory.ELITE, ThreatCategory.SCALING]:
        return CombatMode.AGGRESSIVE

    if threat == ThreatCategory.BOSS:
        # Bosses: balanced but damage-focused
        return CombatMode.SEMI_AGGRESSIVE

    return CombatMode.BALANCED
```

**Rationale**: Elite/scaling fights require 10:1 damage:block ratio to prioritize DPS

### 3. Progressive Aggression System

**Location**: `spirecomm/ai/heuristics/simulation.py` - `calculate_outcome_score()` method

**Purpose**: Adjust aggression level based on fight progress

**Aggression Timeline**:
```
Turn 1-2 (Early): MAXIMUM AGGRESSION
  - Goal: Front-load as much damage as possible
  - Defense weight: 0.2 (almost zero)
  - Damage weight: 6.0 (very high)

Turn 3-4 (Mid): EVALUATIVE
  - Goal: Check if kill is achievable
  - If enemy_hp < 30%: Maintain aggression
  - If enemy_hp > 50%: Pivot to defense (rush failed)

Turn 5+ (Late): DESPERATION
  - Goal: Survival at all costs
  - Return to BALANCED mode
  - Accept that fight is going poorly
```

**Implementation**:
```python
def calculate_aggression_multiplier(turn: int, enemy_hp_pct: float) -> float:
    if turn <= 2:
        return 1.0  # Max aggression

    if turn == 3:
        if enemy_hp_pct < 0.3:
            return 1.0  # Enemy nearly dead, keep pressing
        elif enemy_hp_pct > 0.5:
            return 0.3  # Rush failed, pivot defensive

    return 0.5  # Mid-level aggression
```

**Rationale**: Early turns matter most for elite kills; late turns should accept losses

### 4. Fast-Kill Detection

**Location**: `spirecomm/ai/decision/base.py` - `EnemyThreatProfiler` class

**Purpose**: Detect when lethal damage is achievable in 1-2 turns

**Detection Algorithm**:
```python
def can_fast_kill(context: DecisionContext) -> Tuple[bool, int]:
    """
    Returns: (can_kill, turns_to_kill)
    """
    total_enemy_hp = sum(m.current_hp for m in context.monsters_alive)
    damage_potential = estimate_max_damage(context)

    if damage_potential >= total_enemy_hp:
        return True, 1  # Can kill this turn

    if damage_potential * 1.5 >= total_enemy_hp:
        return True, 2  # Can kill in 2 turns

    return False, 999
```

**Usage**:
- If `can_fast_kill()` returns True: Apply KILL_BONUS (200 points)
- This encourages beam search to find lethal sequences even if they're risky

**Rationale**: Positive reinforcement for finding winning lines

## Data Flow

### Elite Combat Decision Flow

```
1. Game State Update
   ↓
2. Create DecisionContext
   ↓
3. EnemyThreatProfiler.analyze_threat()
   - Detect: Gremlin Nob → ThreatCategory.ELITE
   ↓
4. CombatModeSelector.select_mode()
   - Elite → AGGRESSIVE mode
   ↓
5. HeuristicCombatPlanner.plan_turn()
   - Set weights: DAMAGE=5.0, BLOCK=0.5, W_DEATHRISK=4.0
   - Set KILL_BONUS=200 (doubled)
   ↓
6. FastKillDetector.can_fast_kill()
   - Check: Can we kill in 1-2 turns?
   - If yes: Add +200 bonus to lethal sequences
   ↓
7. Beam Search with AGGRESSIVE weights
   - Expand: Prioritize high-damage cards (Clothesline, Heavy Blade)
   - Prune: Deprioritize block cards (Iron Wave, Defend)
   ↓
8. Return best AGGRESSIVE sequence
   - Example: Clothesline + Bash + Strike (26 damage)
   - Instead of: Iron Wave + Defend + Strike (11 damage, 10 block)
```

## Scenario Analysis

### Scenario 1: Gremlin Nob (A20, 92 HP)

**Current (Balanced) Approach**:
```
Weights: DAMAGE=2.0, BLOCK=1.5

Turn 1 Evaluation:
- Iron Wave (5 dmg, 5 blk): Score = 5×2.0 + 5×1.5 = 17.5
- Strike (6 dmg):           Score = 6×2.0 = 12.0
- Clothesline (12 dmg):     Score = 12×2.0 = 24.0 ✓

AI chooses: Clothesline (best single card)
But then plays: Defend (safe) → Total Turn 1 damage = 12

Result: Nob gains strength → AOE → AI dies on turn 4
```

**Proposed (Aggressive) Approach**:
```
Weights: DAMAGE=5.0, BLOCK=0.5

Turn 1 Evaluation:
- Iron Wave (5 dmg, 5 blk):  Score = 5×5.0 + 5×0.5 = 27.5
- Strike (6 dmg):            Score = 6×5.0 = 30.0
- Clothesline (12 dmg):      Score = 12×5.0 = 60.0 ✓
- Bash (8 dmg + Vulnerable): Score = 8×5.0 + 20×vuln_bonus = 100.0 ✓✓

AI chooses: Bash + Clothesline (20 damage + Vulnerable)

Turn 2: (Vulnerable active)
- Heavy Blade (14 dmg × 1.5 = 21 dmg)
- Strike (6 dmg × 1.5 = 9 dmg)

Total: 50 damage in 2 turns → Nob at 42 HP (almost dead)

Result: Nob nearly dead, can't scale → AI wins
```

### Scenario 2: Three Slavers (A20, ~40 HP each)

**Current (Balanced) Approach**:
```
AI focuses on one slaver at a time with defensive cards
→ Slavers combo chain attacks → AI overwhelmed
```

**Proposed (Aggressive) Approach**:
```
AI recognizes SCALING threat (3 enemies)
→ Uses AOE (Cleave, Whirlwind) if available
→ Focus fires one slaver with maximum damage
→ Reduces enemy count quickly → Disables combo
```

### Scenario 3: Regular Fungi Beast (A20, ~60 HP)

**Current (Balanced) Approach**:
```
Uses BALANCED weights (DAMAGE=2.0, BLOCK=1.5)
→ Mix of attack and defense
→ Sensible play
```

**Proposed (Aggressive) Approach**:
```
Detects REGULAR threat → Still uses BALANCED weights
→ No change in behavior
→ Maintains sensible defensive play
```

## Weight Tuning Strategy

### Iterative Tuning Process

1. **Initial Values** (from proposal):
   - AGGRESSIVE: DAMAGE=5.0, BLOCK=0.5
   - BALANCED: DAMAGE=2.0, BLOCK=1.5 (unchanged)

2. **Testing Metrics**:
   - Elite win rate at A20
   - Average turns to kill elite
   - Damage taken in elite fights

3. **Adjustment Rules**:
   - If still losing elites: Increase DAMAGE_WEIGHT to 6.0-7.0
   - If taking too much damage: Increase BLOCK_WEIGHT to 0.8-1.0
   - If dying in regular fights: Check mode detection logic

### Fallback Mechanism

If aggressive mode consistently fails (e.g., 3+ elite losses in a run):
```python
def adaptive_mode_selection(success_history: List[bool]) -> CombatMode:
    recent_elite_wins = sum(success_history[-5:])  # Last 5 elites

    if recent_elite_wins <= 1:
        # Aggressive mode failing, try balanced
        return CombatMode.BALANCED

    return CombatMode.AGGRESSIVE
```

**Rationale**: Self-correcting system prevents persistent failure patterns

## Implementation Phases

### Phase 1: Enemy Detection (Foundation)
- Implement EnemyThreatProfiler
- Add elite/scaling detection
- Add threat categorization
- **Expected impact**: Can identify elite fights

### Phase 2: Mode Selection
- Implement CombatMode enum
- Add mode selection logic
- Implement aggressive weight profiles
- **Expected impact**: AI switches weights based on enemy type

### Phase 3: Progressive Aggression
- Implement turn-based aggression scaling
- Add fast-kill detection
- Add kill bonus system
- **Expected impact**: AI front-loads damage appropriately

### Phase 4: Tuning and Validation
- Test against all Act 1 elites (Nob, Slavers, Sentry)
- Test Act 2 elites (Gremlin Leader, shielded shapes)
- Test regular fights (no regression)
- **Expected impact**: Optimized weights for all scenarios

## Testing Strategy

### Unit Testing (Manual)
- Test threat detection for all elite types
- Verify aggressive weights are 2.5-3× more damage-focused
- Check mode switching logic

### Integration Testing (Live Game)
- Run 20 elite fights at A20
- Record: win rate, turns to kill, damage taken
- Compare against baseline (current balanced)

### Regression Testing
- Run 10 regular fights at A20
- Verify no change in behavior (should use BALANCED mode)
- Check HP expenditure is reasonable

## Future Enhancements

1. **Per-elite strategies**: Specific patterns for each elite (e.g., shielded Sentry)
2. **Deck-aware aggression**: Scale damage weight based on deck strength
3. **HP-aware aggression**: More desperate when at low HP
4. **Potion integration**: Use potions more aggressively in elite fights

These are left for future changes to keep scope focused on fixing over-defensive behavior.
