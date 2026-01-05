# implement-x-cards-simulation Proposal

## Summary

Implement dynamic calculation logic for X-damage and X-block cards (Body Slam, Rage, Whirlwind, Bludgeon, etc.) in the combat simulation system so AI can accurately evaluate these powerful cards instead of treating them as 0-value.

## Why

Currently, the AI treats X-damage and X-block cards as having 0 value because the parser returns 0 when `is_x_damage=True` or `is_x_block=True`. This causes the AI to severely underestimate these powerful cards:

**Current behavior (broken)**:
```python
# Body Slam with 20 block
damage = game_data_loader._parse_card_damage(body_slam_data)  # Returns 0
score = calculate_score(0)  # AI thinks it's useless ❌

# Rage with 3 energy available
block = game_data_loader._parse_card_block(rage_data)  # Returns 0
score = calculate_score(0)  # AI thinks it's useless ❌
```

**Actual game effect**:
- Body Slam: 20 damage (equal to current block)
- Rage: 9 block (3 energy × 3)
- Whirlwind: Variable damage (energy × monsters)
- Bludgeon: 12-30 damage (based on current block)

This leads to suboptimal play where the AI ignores powerful cards in its deck.

## What Changes

Add dynamic calculation logic in `spirecomm/ai/heuristics/simulation.py` to compute actual values for X-cards based on game state:

### Modified Files
- `spirecomm/ai/heuristics/simulation.py` - Add X-card calculation in `_apply_attack()` and `_apply_skill()`

### New Logic
```python
# X-damage cards
if card.card_id == 'Body Slam':
    damage = state.player_block
elif card.card_id == 'Rage':
    block = context.energy_available  # Uses actual energy
elif card.card_id == 'Whirlwind':
    damage = context.energy_available  # Times number of targets
# ... etc
```

## Scope

### In Scope
- Implement X-calculation for Ironclad X-cards (Body Slam, Rage, Whirlwind, Bludgeon)
- Add dynamic value computation in combat simulation
- Ensure AOE X-cards (Whirlwind) multiply correctly
- Update beam search scoring to use dynamic values

### Out of Scope
- Silent/Defect X-cards (can be added later)
- Complex multipliers (e.g., Reaper healing, which needs post-damage calculation)
- Cards that depend on opponent's state (e.g., based on monster block)

## Impact

### Benefits
- **Accuracy**: AI will correctly evaluate X-cards based on actual game state
- **Power**: Body Slam + high block becomes a winning strategy
- **Flexibility**: Rage becomes viable for energy-to-defense conversion
- **AOE**: Whirlwind evaluated correctly against multiple monsters

### Risks
- **Complexity**: Adds special case logic to simulation
- **Edge Cases**: Must handle 0 energy, 0 block correctly
- **Performance**: Minimal impact (simple condition checks)

## Dependencies

- Requires `unify-game-data-loading` to be complete (provides `is_x_damage`, `is_x_block` markers)
- No new external dependencies

## Success Criteria

1. Body Slam damage equals player's block in simulation
2. Rage block equals available energy in simulation
3. Whirlwind damage equals energy × num_monsters
4. Beam search correctly prioritizes X-cards when conditions are favorable
5. No regressions in existing combat simulation
