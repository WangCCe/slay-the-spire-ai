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

`spirecomm` - Python package for interfacing with *Slay the Spire* through [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod). Includes an autonomous AI bot.

**Communication Mod**: External mod that enables game-external process communication via stdin/stdout (JSON game state ↔ text commands).

## Development Commands

### Installation
```bash
python setup.py install
```

### Running the AI

**Via Communication Mod (production)**:
1. Install [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod)
2. Configure Communication Mod's `config.properties` (typically at `c:\Users\{USERNAME}\AppData\Local\ModTheSpire\CommunicationMod\config.properties`) to run `main.py`
3. AI cycles through Ironclad, Silent, Defect indefinitely

**Direct execution (testing)**:
```bash
python main.py                    # Optimized AI (auto-enabled for Ironclad)
python main.py --simple           # Force simple AI
python main.py --class IRONCLAD   # Set character class
```

### Testing

Integration tests (require live game):
```bash
python test_startup.py          # Communication integration
python test_combat_system.py    # Combat decisions
python test_tracking.py          # Statistics tracking
python test_optimized_ai.py      # Optimized agent
```

**Note**: No unit test framework - tests require running Slay the Spire instance.

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
└─────────────────────────────────────────────────────────────┘
```

### Key Components

**spirecomm/spire/** - Game State Models
- `game.py`: Core `Game` class (JSON → Python objects)
- `character.py`: `Player`, `Monster`, `Intent`, `PlayerClass` enums
- `card.py`: Card model with `cost_for_turn` (Snecko Eye support)
- `relic.py`, `potion.py`, `power.py`, `map.py`, `screen.py`

**spirecomm/communication/** - Communication Layer
- `coordinator.py`: `Coordinator` (bidirectional stdin/stdout, threads, action queue, callbacks)
- `action.py`: All action types (PlayCardAction, PotionAction, ChooseAction, etc.)

**spirecomm/ai/** - Decision Making
- `agent.py`: `SimpleAgent`, `OptimizedAgent` (main decision functions)
- `priorities.py`: Card priority lists, deck limits
- `heuristics/`: Combat planning, card evaluation, deck analysis, map routing
- `decision/base.py`: `DecisionContext` (game state wrapper)

### Communication Flow

```
Communication Mod → stdin → Coordinator.receive_game_state_update()
                                   ↓
                         state_change_callback → Agent.get_next_action_in_game()
                                                                   ↓
                                                         Action → action_queue
                                                                   ↓
                                   Coordinator.execute_next_action() → stdout
```

### State Machine

AI routing via `handle_screen()` in agent.py:

| Screen | Behavior |
|--------|----------|
| EVENT | Choose options (hardcoded logic) |
| CHEST | Open |
| SHOP_ROOM | Open menu |
| REST | REST if HP < 50%, else SMITH/LIFT/DIG |
| CARD_REWARD | Pick best card or skip |
| COMBAT_REWARD | Take gold/relics/potions |
| MAP | Dynamic programming for optimal path |
| BOSS_REWARD | Choose best boss relic |
| SHOP_SCREEN | Buy based on priorities/gold |
| GRID | Card selection (upgrade/transform/purge) |
| HAND_SELECT | Choose cards for effects |

### Combat Decision Systems

**SimpleAgent**: Priority-based (zero-cost → AOE → PLAY_PRIORITY_LIST → target lowest HP)

**OptimizedAgent** (Ironclad only): Beam search planning with lethal detection, accurate simulation (Strength/Vulnerable/Block/AOE), smart targeting, synergy detection

## Important Implementation Details

### Coordinator State Management

**CRITICAL**: Always use `coordinator.last_game_state` NOT `coordinator.game`

- `coordinator.game`: Deprecated, may not reflect current state
- `coordinator.last_game_state`: Most recent state from Communication Mod
- Common bug source, especially in shop interactions

### Card Cost Handling

For Snecko Eye relic:
- `card.cost`: Base cost
- `card.cost_for_turn`: Modified cost (set by Snecko Eye)
- Always use `cost_for_turn` when available

### Game Data Loading

Card/relic/creature metadata from `items.json` (StSExporter mod):

```python
from spirecomm.data.loader import game_data_loader

card_data = game_data_loader.get_card_data("Bash")
damage = game_data_loader._parse_card_damage(card_data)
is_aoe = game_data_loader._is_card_aoe(card_data)
```

**Location**: `spirecomm/data/loader.py`
**Path**: `D:\SteamLibrary\steamapps\common\SlayTheSpire\export\items.json`
**Override**: Set `SLAY_THE_SPIRE_EXPORT_PATH` environment variable
**Features**: Auto-initialization, WSL path conversion, 709 cards/178 relics/66 creatures, 3-stage parsing

### X-Card Calculation

X-cards have variable damage/block marked as "X" (Body Slam, Rage, Whirlwind, Bludgeon).

**Implementation**: `spirecomm/ai/heuristics/simulation.py:FastCombatSimulator`
- Methods: `_calculate_x_damage()`, `_calculate_x_block()`
- Integrated into beam search and full simulation
- Normalizes card IDs (removes '+' suffix for upgraded cards)

**Supported**: Ironclad X-cards only (Silent/Defect not implemented)

### Action Execution

Actions queued via `coordinator.add_action_to_queue(action)`, execute when `game_is_ready`:
1. Check `can_be_executed(coordinator)`
2. Implement `execute(coordinator)`
3. Handle validation errors (invalid actions crash to desktop)

### Beam Search Combat Planner

`spirecomm/ai/heuristics/simulation.py`:
- Explores card sequences using beam search (keeps top N candidates)
- Adapts search depth based on game complexity
- Returns complete action sequences
- Execution tracked via `current_action_sequence` and `current_action_index` in agent

### Map Routing

Dynamic programming to maximize node priority scores (different priorities per act, adapts by character class). See `AdaptiveMapRouter` class.

## Error Handling

- Use try/except in communication-critical paths
- Print errors to **stderr** (stdout reserved for Communication Mod)
- Fallback to safe actions (EndTurnAction, ProceedAction)
- All errors logged to `ai_debug.log` and `communication_mod_errors.log`

## Log Files and Debugging

**Important**: Log files use relative paths, written to **current working directory** (typically `D:\SteamLibrary\steamapps\common\SlayTheSpire\` when launched via CommunicationMod).

### Log Files (in game directory)

| File | Purpose |
|------|---------|
| `ai_game_stats.csv` | Game statistics (wins, losses, floor, class, etc.) |
| `ai_game_stats.jsonl` | Detailed game logs (JSONL format) |
| `ai_debug.log` | AI debugging and decision history (auto-rotates at 10MB, keeps 5 backups) |
| `communication_mod_errors.log` | Python exceptions and stack traces |

### Debugging Workflow

When debugging crashes:
1. Check `communication_mod_errors.log` - Python exceptions
2. Check `ai_debug.log` - game state tracking and decisions
3. Use `ai_game_stats.csv` - analyze win rates and trends

### Common Issues

**Shop crashes**: Often caused by using `coordinator.game` instead of `coordinator.last_game_state`

**Beam search errors**: Check tuple unpacking in combat planner

**Missing attributes**: Always use `coordinator.last_game_state`

**Snecko Eye costs**: Ensure `cost_for_turn` field is used

**Agent selection**:
- `SimpleAgent`: Priority-based AI (all characters)
- `OptimizedAgent`: Beam search AI (Ironclad only, auto-enabled)
- Use `--simple` flag to force SimpleAgent for Ironclad

## Code Conventions

### Naming
- Classes: `PascalCase` (e.g., `SimpleAgent`, `DecisionContext`)
- Functions/Methods: `snake_case` (e.g., `get_next_action_in_game`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_COPIES`)
- Private: Prefixed with underscore (e.g., `_calculate_block`)

### Imports
- Group: standard library → third-party → local
- Use `from X import Y` for common imports
- Wildcard imports (`*`) used selectively for action classes

### Error Handling
- try/except in communication-critical paths
- Print to stderr (stdout reserved for Communication Mod)
- Fallback to safe actions (EndTurnAction, ProceedAction)

## Performance Constraints

- **Response Time**: ~100ms to avoid game timeouts
- **Decision Complexity**: Beam search adapts depth based on complexity
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