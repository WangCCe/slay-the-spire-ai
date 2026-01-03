<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `spirecomm` - a Python package for interfacing with the game *Slay the Spire* through the [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod). It includes an autonomous AI bot that can play the game.

**Communication Mod**: An external mod for Slay the Spire that enables communication between the game and external processes via stdin/stdout. The mod sends JSON game state and accepts text commands.

## Development Commands

### Installation
```bash
python setup.py install
```

### Running the AI

**Via Communication Mod (production)**:
1. Install and configure [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod) for Slay the Spire
2. Configure Communication Mod's `config.properties` (typically at `c:\Users\{USERNAME}\AppData\Local\ModTheSpire\CommunicationMod\config.properties`) to run `main.py`
3. The AI will cycle through all character classes (Ironclad, Silent, Defect) indefinitely

**Direct execution (testing)**:
```bash
# Run with optimized AI (auto-enabled for Ironclad)
python main.py

# Force simple AI
python main.py --simple

# Force optimized AI
python main.py --optimized

# Set player class
python main.py --class IRONCLAD
```

### Testing

Run individual test files (requires Communication Mod and running game):
```bash
python test_startup.py          # Communication integration tests
python test_combat_system.py    # Combat decision verification
python test_tracking.py          # Statistics tracking validation
python test_optimized_ai.py      # Optimized agent tests
```

**Note**: Tests are integration tests requiring a live Slay the Spire game instance. No automated unit test framework is used (no pytest/unittest).

## Architecture

### Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    spirecomm/spire/                         │
│                  Game State Data Models                     │
│  Game, Card, Monster, Player, Relic, Potion, Power, Map    │
└──────────────────────┬──────────────────────────────────────┘
                       │ JSON deserialization
┌──────────────────────▼──────────────────────────────────────┐
│              spirecomm/communication/                       │
│            Communication Layer (stdin/stdout)               │
│  Coordinator - threaded bidirectional communication         │
│  Action - command pattern with execute(coordinator)         │
└──────────────────────┬──────────────────────────────────────┘
                       │ Callbacks
┌──────────────────────▼──────────────────────────────────────┐
│                   spirecomm/ai/                             │
│                 Decision Making Layer                       │
│  SimpleAgent - priority-based decisions                     │
│  OptimizedAgent - beam search combat planning (Ironclad)    │
│  heuristics/ - specialized evaluators                       │
│  decision/ - context and planning systems                   │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**1. spirecomm/spire/** - Game State Models
- `game.py`: Core `Game` class that deserializes JSON from Communication Mod into Python objects
- `character.py`: `Player`, `Monster`, `Intent` enum, `PlayerClass` enum
- `card.py`: Card data model with `cost_for_turn` support (for Snecko Eye)
- `relic.py`, `potion.py`, `power.py`: Item/effect data models
- `map.py`: Map node structure
- `screen.py`: All screen types (Event, Rest, Shop, CombatReward, etc.)

**2. spirecomm/communication/** - Communication Layer
- `coordinator.py`: `Coordinator` class manages bidirectional stdin/stdout communication
  - Runs background threads for reading/writing
  - Maintains `action_queue` and `last_game_state`
  - Executes actions when `game_is_ready`
  - Provides callbacks: `state_change_callback`, `error_callback`, `out_of_game_callback`
- `action.py`: All action types (PlayCardAction, PotionAction, ChooseAction, etc.)
  - Each has `execute(coordinator)` and `can_be_executed()` methods

**3. spirecomm/ai/** - Decision Making
- `agent.py`: `SimpleAgent` and `OptimizedAgent` classes
  - `get_next_action_in_game()`: Main decision function
  - `get_play_card_action()`: Combat card selection
  - `handle_screen()`: Routes to screen-specific handlers
- `priorities.py`: `Priority`, `SilentPriority`, `IroncladPriority`, `DefectPowerPriority`
  - `CARD_PRIORITY_LIST`: Reward selection priorities
  - `PLAY_PRIORITY_LIST`: Combat card priorities
  - `MAX_COPIES`: Deck building limits
- `heuristics/`: Specialized evaluation modules
  - `card.py`: `SynergyCardEvaluator` - dynamic card valuation
  - `simulation.py`: `HeuristicCombatPlanner` - beam search combat planning
  - `deck.py`: `DeckAnalyzer` - archetype detection
  - `combat_ending.py`: Lethal detection and defense skipping
  - `map_routing.py`: `AdaptiveMapRouter` - path optimization
  - `ironclad_combat.py`: Ironclad-specific combat logic
  - `ironclad_archetype.py`: Ironclad archetype detection
  - `relic.py`: Relic evaluation
  - `monster_database.py`: Monster information
- `decision/base.py`: `DecisionContext` - wraps game state for AI decisions
- `statistics.py`: `GameStatistics` - win rate tracking
- `tracker.py`: `GameTracker` - game state tracking

### Communication Flow

```
Communication Mod → stdin → Coordinator.input_queue
                                   ↓
                         receive_game_state_update()
                                   ↓
                         state_change_callback → Agent.get_next_action_in_game()
                                                                   ↓
                                                         Action → action_queue
                                                                   ↓
                                   Coordinator.execute_next_action() → stdout
                                                                          ↓
                                                                 Communication Mod
```

### State Machine

The AI responds to different game screens via `handle_screen()` in agent.py:

| Screen Type | Handler Behavior |
|------------|------------------|
| **EVENT** | Choose event options (some hardcoded logic) |
| **CHEST** | Open chest |
| **SHOP_ROOM** | Open shopkeeper menu |
| **REST** | REST if HP < 50%, else SMITH, LIFT, or DIG |
| **CARD_REWARD** | Pick best card based on priorities or skip |
| **COMBAT_REWARD** | Take rewards (gold/relics/potions, skip potions if full) |
| **MAP** | Dynamic programming to find optimal path |
| **BOSS_REWARD** | Choose best boss relic |
| **SHOP_SCREEN** | Buy cards/relics/purge based on priorities and gold |
| **GRID** | Card selection (upgrade/transform/purge) |
| **HAND_SELECT** | Choose cards from hand for card effects |

### Combat Decision Systems

**SimpleAgent (original)**:
1. Separate zero-cost and nonzero-cost playable cards
2. Identify AOE and defensive cards
3. Skip defensive cards if already have enough block
4. Prioritize zero-cost non-attack cards
5. Play nonzero-cost cards by PLAY_PRIORITY_LIST
6. Use AOE attacks when multiple monsters alive
7. Target lowest HP for attacks, highest HP for non-attacks

**OptimizedAgent (Ironclad only)**:
1. **Beam Search Planning**: Evaluates sequences of cards, not just individual cards
2. **Lethal Detection**: Checks if monsters can be killed this turn
3. **Accurate Simulation**: Considers Strength, Vulnerable, Block, AOE
4. **Smart Targeting**: Bash applies Vulnerable to high-HP monsters, attacks target low-HP
5. **Synergy Detection**: Recognizes combos (Limit Break + high Strength, etc.)

## Important Implementation Details

### Coordinator State Management

**CRITICAL**: Always use `coordinator.last_game_state` NOT `coordinator.game`

- `coordinator.game`: Deprecated, may not reflect current state
- `coordinator.last_game_state`: Most recent game state from Communication Mod
- This is a common source of bugs, especially in shop interactions

### Card Cost Handling

For Snecko Eye relic support, cards have two cost fields:
- `card.cost`: Base cost from card definition
- `card.cost_for_turn`: Modified cost (set by Snecko Eye randomizer)
- Always use `cost_for_turn` when available

### Action Execution

Actions are queued via `coordinator.add_action_to_queue(action)` and execute when `game_is_ready`. Each action must:
1. Check `can_be_executed(coordinator)` before executing
2. Implement `execute(coordinator)` to send commands
3. Handle validation errors gracefully (invalid actions crash to desktop)

### Beam Search Combat Planner

Located in `spirecomm/ai/heuristics/simulation.py`:
- Explores card sequences using beam search (keeps top N candidates)
- Adapts search depth based on game complexity
- Returns complete action sequences, not single cards
- Execution tracked via `current_action_sequence` and `current_action_index` in agent

### Error Handling

- Use try/except in communication-critical paths
- Print errors to stderr, NOT stdout (stdout reserved for Communication Mod)
- Fallback to safe actions (EndTurnAction, ProceedAction) on errors
- All errors logged to `shop_error.log` and `communication_mod_errors.log`

### Map Routing

Uses dynamic programming to maximize node priority scores:
- Different priorities per act (e.g., prioritize Elites in Act 1)
- Adapts based on character class
- Considered in `AdaptiveMapRouter` class

## Log Files and Debugging

**Important**: Log files use relative paths and are written to the **current working directory** where the Python script runs.

**When launched via CommunicationMod**, the CWD is typically:
```
D:\SteamLibrary\steamapps\common\SlayTheSpire\
```

### Log Files (in game directory)

| File | Purpose |
|------|---------|
| `main_game_loop.log` | **Primary log** - game loop events, coordinator state, restart tracking |
| `ai_game_stats.csv` | Game statistics (wins, losses, floor reached, character class, etc.) |
| `ai_game_stats.jsonl` | Detailed game logs (JSONL format) |
| `ai_debug.log` | AI debugging and decision history |
| `shop_error.log` | Shop-specific errors and warnings |
| `communication_mod_errors.log` | Python exceptions and stack traces |

### Debugging Workflow

When debugging crashes or issues:
1. **Check `main_game_loop.log` first** - Shows game restart, coordinator state, and general flow
2. Check `communication_mod_errors.log` for Python exceptions and stack traces
3. Check `shop_error.log` for shop-related errors (if created)
4. Check `ai_debug.log` for game state tracking and decision history
5. Use `ai_game_stats.csv` for analyzing win rates and performance trends

### Common Issues

**Shop crashes**: Often caused by `coordinator.game` vs `coordinator.last_game_state` attribute confusion

**Beam search errors**: Check tuple unpacking in combat planner implementation

**Missing attributes**: Always use `coordinator.last_game_state` not `coordinator.game`

**Snecko Eye costs**: Ensure `cost_for_turn` field is being used

**Agent selection confusion**:
- `SimpleAgent`: Original priority-based AI (all characters)
- `OptimizedAgent`: Beam search AI (Ironclad only, auto-enabled)
- Use `--simple` flag to force SimpleAgent for Ironclad

## Code Conventions

### Naming
- Classes: `PascalCase` (e.g., `SimpleAgent`, `DecisionContext`)
- Functions/Methods: `snake_case` (e.g., `get_next_action_in_game`, `handle_screen`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_COPIES`, `CARD_PRIORITY_LIST`)
- Private/Internal: Prefixed with underscore (e.g., `_calculate_block`)

### Imports
- Group imports: standard library, third-party, local
- Use `from X import Y` for common imports
- Wildcard imports (`*`) used selectively for action classes

### Error Handling
- Use try/except in communication-critical paths
- Print errors to stderr to avoid interfering with Communication Mod protocol
- Fallback to safe actions (EndTurnAction, ProceedAction) on errors

## Dependencies

- **Python**: 3.7+ (no external packages - standard library only)
- **Communication Mod**: 0.7.0+ (https://github.com/ForgottenArbiter/CommunicationMod)
- **Slay the Spire**: Game with ModTheSpire mod loader installed

## Performance Constraints

- **Response Time**: AI must respond in ~100ms to avoid game timeouts
- **Decision Complexity**: Beam search adapts depth based on game complexity
- **Memory**: Stateless design - game state reconstructed from JSON each update
- **Threading**: Coordinator uses daemon threads for stdin/stdout

## Game Domain Knowledge

### Characters
- **Ironclad**: Strength-based warrior, block cards, self-damage synergies
- **Silent**: Shiv/dexterity focused, poison, deck cycling
- **Defect**: Orb-based powers, elemental spells, focus manipulation

### Combat Mechanics
- **Energy**: Limited resource (typically 3) to play cards
- **Block**: Damage reduction, decays each turn
- **Intents**: Monsters telegraph their next action (attack, defend, buff, debuff)
- **Powers**: Ongoing effects that modify game state
- **Relics**: Passive abilities that provide strategic advantages

### Map Nodes
- **M**: Monster room
- **?**: Event
- **$**: Shop
- **E**: Elite
- **Rest**: Rest site
- **Boss**: Boss fight
- **Treasure**: Chest

### AI Strategy Concepts
- **Archetypes**: Deck build patterns (e.g., Strength build, Shiv Silent, Poison deck)
- **Synergies**: Card combinations (e.g., Limit Break + high Strength)
- **Map Routing**: Choosing optimal path based on node priorities and character needs
- **Lethal Detection**: Checking if combat can end this turn to avoid over-defending