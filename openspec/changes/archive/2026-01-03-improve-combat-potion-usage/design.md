# Design: Combat Potion Usage Enhancement

## Architecture Overview

The current architecture has a critical gap: potions are only considered during the `get_next_action_in_game()` flow, but not in the `beam_search_plan()` used by OptimizedAgent. This means potions are evaluated independently of card sequences, missing synergies and optimal timing.

### Current Flow (Simplified)
```
OptimizedAgent.get_play_card_action()
  └─> HeuristicCombatPlanner.plan_turn()
      └─> _beam_search_plan()
          └─> Only expands card actions (lines 788-819)
```

### Target Flow
```
OptimizedAgent.get_play_card_action()
  └─> HeuristicCombatPlanner.plan_turn()
      └─> _beam_search_plan()
          ├─> Expand card actions
          └─> Expand potion actions (NEW)
```

## Component Changes

### 1. Potion Action Generation in Beam Search

**File**: `spirecomm/ai/heuristics/simulation.py`

Add a method to `HeuristicCombatPlanner`:

```python
def _get_potion_actions(self, context: DecisionContext, state: SimulationState) -> List[Tuple]:
    """
    Generate potion actions for beam search expansion.

    Returns: List of (potion, target_monster, energy_cost, priority_score) tuples
    """
    potions = context.game.get_real_potions()
    potion_actions = []

    for potion in potions:
        if not potion.can_use:
            continue

        # Calculate priority score based on potion type and game state
        priority = self._score_potion(potion, context, state)

        # Determine target if needed
        target = None
        if potion.requires_target:
            target = self._find_best_potion_target(potion, context)

        potion_actions.append((potion, target, 0, priority))  # Potions cost 0 energy

    return potion_actions
```

### 2. Potion Scoring Function

Evaluate potions based on combat context:

```python
def _score_potion(self, potion, context, state) -> float:
    """Score a potion based on current situation."""
    score = 0.0
    hp_pct = state.player_hp / max(state.player_max_hp, 1)
    incoming_damage = self._get_incoming_damage(context)
    alive_monsters = [m for m in context.game.monsters if not m.is_gone]

    # Healing potions: high value when HP low
    if self._is_healing_potion(potion):
        if hp_pct < 0.3:
            score += 50  # Critical HP
        elif hp_pct < 0.5 and incoming_damage > state.player_hp * 0.3:
            score += 30  # In danger

    # Damage potions: high value for lethal or high-threat targets
    elif self._is_damage_potion(potion):
        if alive_monsters and incoming_damage > 0:
            # Bonus for elites/bosses
            if 'Elite' in context.game.room_type or 'Boss' in context.game.room_type:
                score += 40
            # Bonus for multiple monsters (AOE)
            if len(alive_monsters) >= 2:
                score += 25
            # Bonus when close to lethal
            total_monster_hp = sum(m.current_hp for m in alive_monsters)
            if total_monster_hp < 50:
                score += 20

    # Block potions: high value when incoming damage is high
    elif self._is_block_potion(potion):
        if incoming_damage > state.player_hp * 0.4:
            score += 35  # High incoming damage

    # Utility potions: baseline value in dangerous fights
    else:
        if incoming_damage > state.player_hp * 0.3:
            score += 20

    return score
```

### 3. Beam Search Integration

Modify `_beam_search_plan()` to include potions in action expansion (around line 788):

```python
# Current: only card actions
playable_actions = []
for card in context.playable_cards:
    # ... card logic ...

# NEW: Add potion actions (limited to 1 per turn to prevent spam)
potion_actions = []
if depth == 0:  # Only consider potions at root of beam search
    potion_actions = self._get_potion_actions(context, state)
    # Limit to highest priority potion
    if potion_actions:
        potion_actions.sort(key=lambda x: x[3], reverse=True)
        potion_actions = [potion_actions[0]]  # Best potion only

# Combine cards and potions for evaluation
all_actions = playable_actions + potion_actions
```

### 4. Potion Simulation

Add simulation methods to `CombatSimulator`:

```python
def simulate_potion_use(self, state: SimulationState, potion, target_monster) -> SimulationState:
    """Simulate the effect of using a potion."""
    new_state = copy.deepcopy(state)

    if self._is_damage_potion(potion):
        if target_monster:
            damage = self._get_potion_damage(potion)
            new_state = self._apply_damage(new_state, target_monster, damage)

    elif self._is_block_potion(potion):
        block = self._get_potion_block(potion)
        new_state.player_block += block

    elif self._is_healing_potion(potion):
        heal = self._get_potion_heal_amount(potion)
        new_state.player_hp = min(new_state.player_hp + heal, new_state.player_max_hp)

    # Track potion use
    new_state.potions_used += 1

    return new_state
```

### 5. Agent Integration

**File**: `spirecomm/ai/agent.py`

Remove the boss-only restriction (line 82):

```python
# OLD: only in boss rooms
if self.game.room_type == "MonsterRoomBoss" and len(self.game.get_real_potions()) > 0:
    potion_action = self.use_next_potion()

# NEW: check if potion improves beam search score
if len(self.game.get_real_potions()) > 0:
    # Let beam search decide if potion is worthwhile
    # (potion actions are now part of beam search expansion)
    pass
```

Add a fallback potion usage for dangerous situations:

```python
def _should_use_potion_outside_combat(self) -> bool:
    """Check if potion should be used even without beam search recommendation."""
    danger_level = self._evaluate_combat_danger(None)

    # Use potions in high-danger situations regardless of room type
    return danger_level > 0.6 or 'Elite' in self.game.room_type or 'Boss' in self.game.room_type
```

## Data Flow

```
Game State Update
    │
    ▼
OptimizedAgent.get_next_action_in_game()
    │
    ▼
get_play_card_action()
    │
    ├──> Check: Are we in danger? (>0.6)
    │         └─> Yes: use_next_potion() (legacy fallback)
    │
    └─> HeuristicCombatPlanner.plan_turn()
            │
            ▼
        _beam_search_plan()
            │
            ├─> Collect card actions
            │
            ├─> Collect potion actions (NEW, depth=0 only)
            │   └─> _get_potion_actions()
            │       ├─> Filter usable potions
            │       ├─> Score each potion
            │       └─> Select best one
            │
            ├─> FastScore evaluation (cards + potions)
            │
            ├─> Top-M selection
            │
            └─> Full simulation (cards + potions)
                └─> simulate_potion_use() (NEW)
```

## Trade-offs

### Simplicity vs Intelligence
- **Chosen**: Intelligent integration with beam search
- **Alternative**: Simple threshold-based usage
- **Rationale**: The beam search infrastructure exists; using it for potions provides synergies

### Potion Conservation vs Aggressive Usage
- **Chosen**: Use potions when beam search indicates value
- **Risk**: Potions used too early in dungeon
- **Mitigation**: Score potions higher in elite/boss fights, lower in easy fights

### Performance
- **Impact**: Adding potions increases beam width by ~5-10 actions
- **Mitigation**: Limit to 1 potion per turn, only consider at depth=0
- **Expected**: <10ms additional computation (negligible within 100ms budget)

## Testing Strategy

1. **Unit tests**: Verify potion scoring logic (healing potions score high at low HP, etc.)
2. **Integration tests**: Run beam search with known potions, verify they're included in action space
3. **Regression tests**: Ensure win rate doesn't decrease in easy fights (potion conservation)
4. **Scenario tests**: Create specific combat states (low HP, dangerous elite) and verify potion usage

## Implementation Notes

1. **Potion damage/heal amounts**: These are hardcoded in Slay the Spire and need to be added to the Potion class or a lookup table
2. **Target selection**: Damage potions should target highest-threat monsters (consistent with threat-based targeting requirement)
3. **Energy cost**: Potions cost 0 energy but have an opportunity cost (using a potion slot)
4. **Potion limits**: Can only use 1 potion per turn normally (game mechanic)
