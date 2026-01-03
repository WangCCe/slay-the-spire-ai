# Design Document: Improve Ironclad Act 1 Performance

## Overview

This document describes the technical approach for improving Ironclad's Act 1 performance through enabling the OptimizedAI by default and fixing critical bugs in the combat decision system.

## Architecture Background

### Current State

The codebase has two agent implementations:

1. **SimpleAgent** (legacy):
   - Greedy single-card selection
   - Static priority lists
   - No lookahead
   - Located in `spirecomm/ai/agent.py:29-304`

2. **OptimizedAgent** (enhanced):
   - Beam search combat planning
   - Synergy-based evaluation
   - Combat ending detection
   - Located in `spirecomm/ai/agent.py:306+`

### OptimizedAI Components

```
spirecomm/ai/
├── agent.py                  # SimpleAgent, OptimizedAgent
├── decision/
│   └── base.py              # DecisionContext, CombatPlanner (ABC)
├── heuristics/
│   ├── card.py              # SynergyCardEvaluator
│   ├── simulation.py        # FastCombatSimulator, SimulationState
│   ├── combat_ending.py     # CombatEndingDetector
│   ├── ironclad_combat.py   # IroncladCombatPlanner
│   ├── ironclad_archetype.py # IroncladDeckAnalyzer
│   ├── ironclad_evaluator.py # IroncladCardEvaluator
│   └── deck.py              # DeckAnalyzer
└── priorities.py            # Priority classes
```

## Design Decisions

### Decision 1: Enable OptimizedAgent by Default

**Option A**: Keep SimpleAgent as default, fix bugs in both
- ❌ Duplicates effort - OptimizedAgent already has better architecture
- ❌ Two code paths to maintain
- ✅ Lower risk (doesn't change default behavior)

**Option B**: Make OptimizedAgent the default for all characters
- ✅ Everyone benefits from improvements
- ❌ Higher risk - affects all characters
- ❌ May expose bugs in Silent/Defect paths

**Option C**: Make OptimizedAgent the default for Ironclad only (SELECTED)
- ✅ Targeted fix for the reported problem
- ✅ Can test on one character before expanding
- ✅ Lower risk for other characters
- ✅ Can expand to other characters after validation

**Implementation**:
```python
# main.py
def create_agent(use_optimized=None, player_class=None):
    # Auto-enable optimized for Ironclad
    if use_optimized is None and player_class == PlayerClass.IRONCLAD:
        use_optimized = True

    # Rest of logic...
```

### Decision 2: Fix Simulation Accuracy Before Tuning

**Approach**: Fix the foundation before optimizing the surface

1. First, ensure `FastCombatSimulator` produces accurate results:
   - Damage calculations (Strength, Vulnerable, block)
   - Energy tracking
   - State mutations (powers, debuffs)

2. Then, verify `IroncladCombatPlanner` finds good sequences:
   - Beam search explores enough candidates
   - Scoring function values correct outcomes
   - Targeting logic picks right monsters

3. Finally, tune priorities for Act 1:
   - Adjust card priorities
   - Add deck composition awareness
   - Implement HP-based thresholds

**Rationale**: Tuning priorities on top of a buggy simulation will produce misleading results.

### Decision 3: Adaptive Beam Search Parameters

**Problem**: Fixed beam width/depth is inefficient:
- Simple fights waste computation exploring too many options
- Complex fights don't explore enough options

**Solution**: Adaptive parameters based on complexity:

```python
def _get_adaptive_parameters(context, playable_cards):
    num_playable = len(playable_cards)
    num_monsters = len(context.monsters_alive)
    complexity = num_playable * num_monsters

    # Simple: 1-3 cards, 1-2 monsters
    if num_playable <= 3 and num_monsters <= 2:
        return 8, 3  # beam_width, max_depth

    # Medium: 4-6 cards, 2-3 monsters
    elif num_playable <= 6 and num_monsters <= 3:
        return 12, 4

    # Complex: 7+ cards or 4+ monsters
    else:
        return 15, 5
```

**Trade-offs**:
- ✅ Responsive to game state
- ✌️ Adds complexity
- ✅ Balances performance vs quality

### Decision 4: Combat Ending Detection

**Concept**: If lethal damage is available, don't defend - kill.

**Implementation**:
```python
class CombatEndingDetector:
    def can_kill_all(self, context):
        """Check if lethal damage is possible this turn."""
        # Simulate all-out offense
        # Check if total damage >= sum(monster.current_hp)

    def find_lethal_sequence(self, context):
        """Find card sequence that kills all monsters."""
        # Prioritize highest damage/energy cards
        # Ignore defense entirely
        # Return sequence if lethal found
```

**Benefits**:
- Prevents over-blocking when game is winnable
- Finds lethal lines that greedy selection misses
- Critical for elite fights (kill before they kill you)

### Decision 5: Deck Archetype Detection

**Purpose**: Adjust card rewards based on deck's direction.

**Ironclad Archetypes**:
1. **Strength Build**: Demon Form, Limit Break, Inflame
   - Prioritize: Strength gain, heavy attacks
   - Avoid: Low-impact attacks

2. **Block/Body Slam**: Metallicize, Entrench, high block cards
   - Prioritize: Block cards, Body Slam
   - Avoid: Low-block attacks

3. **Exhaust/Fiery Fire**: Corruption, Feel No Pain, Fiend Fire
   - Prioritize: Exhaust synergies, low-cost skills
   - Avoid: Cards that add to deck

**Implementation**:
```python
class IroncladDeckAnalyzer:
    def detect_archetype(self, deck):
        # Count key cards for each archetype
        # Return dominant archetype or 'general'
```

### Decision 6: HP-Based Decision Thresholds

**Concept**: Play style should change based on current HP.

**Thresholds**:
- **HP > 80%**: Aggressive - prioritize speed and damage
- **HP 50-80%**: Balanced - trade resources for HP
- **HP 30-50%**: Conservative - prioritize survival
- **HP < 30%**: Desperate - take any line that survives

**Implementation**:
```python
class DecisionContext:
    @property
    def risk_tolerance(self):
        if self.player_hp_pct > 0.8:
            return "aggressive"
        elif self.player_hp_pct > 0.5:
            return "balanced"
        elif self.player_hp_pct > 0.3:
            return "conservative"
        else:
            return "desperate"
```

## Technical Specifications

### SimulationState Updates

Current implementation in `simulation.py:17-68` needs:

1. **Accurate Debuff Tracking**:
   ```python
   self.vulnerable_stacks = {}  # monster_index -> stacks
   self.weak_stacks = {}  # monster_index -> stacks
   self.frail_stacks = {}  # monster_index -> stacks
   ```

2. **Turn Tracking**:
   ```python
   self.turn_number = context.turn
   self.cards_played_this_turn = []
   ```

3. **Energy Validation**:
   ```python
   def can_play_card(self, card, state):
       cost = self.get_real_cost(card)  # Account for Snecko Eye
       return state.player_energy >= cost
   ```

### Beam Search Algorithm

Current implementation in `ironclad_combat.py:52-74` needs:

1. **Candidate Generation**:
   ```python
   def generate_candidates(self, state, playable_cards):
       # Return list of (card, target, priority_score)
       # Sort by priority to explore best options first
   ```

2. **State Evaluation**:
   ```python
   def evaluate_state(self, state):
       score = 0
       # Damage dealt (positive)
       score += state.total_damage_dealt
       # Monsters killed (positive)
       score += state.monsters_killed * 50
       # Player HP lost (negative)
       score -= (self.initial_hp - state.player_hp) * 100
       # Block gained (small positive)
       score += state.player_block * 0.5
       # Energy efficiency (small positive)
       score += state.energy_spent * 2
       return score
   ```

3. **Beam Pruning**:
   ```python
   def prune_beam(self, candidates, beam_width):
       # Keep top beam_width candidates by score
       # Ensure diversity (don't keep 10 similar sequences)
   ```

### Priority List Updates

Current `IroncladPriority.CARD_PRIORITY_LIST` needs Act 1 adjustments:

**High Priority for Act 1** (move to front):
- Bash (Vulnerable is crucial early)
- Iron Wave (block + attack, efficient)
- Shrug It Off (block + draw, efficient)
- Pommel Strike (cheap, removes cards)
- Headbutt (returns useful cards)

**Lower Priority for Act 1** (move back):
- Demon Form (too slow, needs support)
- Limit Break (no Strength yet)
- Corruption (needs specific deck)
- Rag Veil (exhaust-focused build)

**New MAX_COPIES**:
```python
MAX_COPIES = {
    "Bash": 1,
    "Iron Wave": 2,
    "Shrug It Off": 2,
    "Strike_R": 4,  # Keep some strikes early
    "Defend_R": 4,  # Keep some defends early
    "Cleave": 1,
    "Perfected Strike": 1,
}
```

## Integration Points

### main.py Changes

```python
def create_agent(use_optimized=None, player_class=None):
    # Auto-detect character class if not provided
    if player_class is None:
        player_class = PlayerClass.IRONCLAD  # Default to Ironclad

    # Auto-enable optimized AI for Ironclad
    if use_optimized is None:
        if player_class == PlayerClass.IRONCLAD:
            use_optimized = True
        else:
            use_optimized = os.getenv("USE_OPTIMIZED_AI", "false").lower() == "true"

    # Create agent
    if use_optimized:
        if OPTIMIZED_AI_AVAILABLE:
            return OptimizedAgent(chosen_class=player_class)
        else:
            sys.stderr.write(f"OptimizedAI not available, using SimpleAgent\n")
            return SimpleAgent(chosen_class=player_class)
    else:
        return SimpleAgent(chosen_class=player_class)
```

### OptimizedAgent Integration

Ensure OptimizedAgent properly uses all components:

```python
class OptimizedAgent(SimpleAgent):
    def __init__(self, chosen_class=PlayerClass.THE_SILENT, ...):
        super().__init__(chosen_class)
        self.use_optimized_combat = use_optimized_combat
        self.use_optimized_card_selection = use_optimized_card_selection

        # Initialize heuristics
        from spirecomm.ai.heuristics.card import SynergyCardEvaluator
        from spirecomm.ai.heuristics.simulation import FastCombatSimulator
        from spirecomm.ai.heuristics.ironclad_combat import IroncladCombatPlanner

        self.card_evaluator = SynergyCardEvaluator()
        self.combat_planner = IroncladCombatPlanner(
            card_evaluator=self.card_evaluator,
            beam_width=10,
            max_depth=5
        )
```

## Performance Considerations

### Beam Search Cost

**Time Complexity**: O(beam_width × max_depth × branching_factor)

Where:
- `branching_factor` = number of playable cards × number of monsters

**Mitigation**:
- Adaptive beam width/depth based on complexity
- Prune obviously bad candidates early
- Cache simulation results for duplicate states

### Memory Usage

**Peak Memory**: O(beam_width × state_size)

**Mitigation**:
- Reuse SimulationState objects when possible
- Prune beam aggressively after each depth
- Limit max_depth in complex scenarios

### Real-Time Constraints

Communication Mod requires decisions within ~100ms.

**Target Budget**:
- Simple fights (1-3 cards): <50ms
- Medium fights (4-6 cards): <80ms
- Complex fights (7+ cards): <120ms (acceptable if rare)

**Fallback**:
If decision takes too long, fallback to greedy selection from SimpleAgent.

## Risk Mitigation

### Risk 1: OptimizedAI Has Critical Bugs

**Mitigation**:
- Extensive logging in Phase 1 (diagnostics)
- Start with SimpleAgent fallback enabled
- Test in low-stakes environments first
- Gradual rollout (Ironclad only → all characters)

### Risk 2: Performance Degradation

**Mitigation**:
- Adaptive parameters prevent worst-case scenarios
- Timeout protection (fallback after 100ms)
- Monitor decision times in statistics
- Optimize hot spots if needed

### Risk 3: Regression in Other Characters

**Mitigation**:
- Only change default for Ironclad initially
- Test Silent and Defect after Ironclad validated
- Keep SimpleAgent as working fallback
- Run comparison tests

## Testing Strategy

### Unit-Level Testing

1. **Simulation Accuracy**:
   - Test damage calculations with/without Strength
   - Test Vulnerable multiplier
   - Test block subtraction
   - Test energy tracking

2. **Beam Search**:
   - Test simple scenario (1 monster, 2 cards)
   - Test medium scenario (2 monsters, 4 cards)
   - Test complex scenario (3 monsters, 6 cards)
   - Verify lethal detection

3. **Archetype Detection**:
   - Test Strength deck
   - Test Block deck
   - Test Exhaust deck
   - Test general deck

### Integration Testing

1. **Full Combat Simulation**:
   - Simulate first encounter (Cultist/Jawbone Worm)
   - Simulate elite fight (Gremlin Gang/Gremlin Nob)
   - Simulate boss fight (Guardian/The Slaver)

2. **Card Reward Selection**:
   - Test with empty deck
   - Test with existing Strength cards
   - Test with existing Block cards

### Performance Testing

1. **Decision Time**:
   - Measure average decision time
   - Track p50, p95, p99 latencies
   - Ensure <100ms for 95% of decisions

2. **Win Rate**:
   - Run 20+ games at A20
   - Track Act 1 completion rate
   - Compare to baseline

## Success Criteria

### Must Have (P0):
- [ ] OptimizedAgent is default for Ironclad
- [ ] No critical crashes in combat
- [ ] Simulation is accurate (damage, energy, state)
- [ ] Beam search finds lethal when available
- [ ] Decision times <150ms for 99% of actions

### Should Have (P1):
- [ ] Act 1 completion rate >40% (up from current)
- [ ] Card rewards synergize with deck
- [ ] HP-based risk thresholds work correctly
- [ ] Elite fights show improvement

### Nice to Have (P2):
- [ ] Act 1 completion rate >60%
- [ ] Archetype detection works reliably
- [ ] Can expand improvements to Silent/Defect

## Future Enhancements

### Short-Term (After This Change):
1. Expand OptimizedAgent default to Silent
2. Expand OptimizedAgent default to Defect
3. Add more archetype-specific logic
4. Improve event selection

### Long-Term:
1. Machine learning for priority tuning
2. Monte Carlo Tree Search instead of beam search
3. Reinforcement learning for combat policy
4. Deck building recommendations

## References

- `IRONCLAD_IMPROVEMENTS.md` - Existing Ironclad-specific improvements
- `OPTIMIZED_AI_README.md` - OptimizedAI documentation
- `COMBAT_SYSTEM_IMPLEMENTATION_SUMMARY.md` - Combat system design
- Beam search: https://en.wikipedia.org/wiki/Beam_search
- Slay the Spire Wiki: https://slay-the-spire.fandom.com/wiki/Slay_the_Spire_Wiki
