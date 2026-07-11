
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`spirecomm` - Python package for interfacing with *Slay the Spire* through [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod). Includes an autonomous AI bot.

**Communication Mod**: External mod that enables game-external process communication via stdin/stdout (JSON game state ↔ text commands).

## Development Commands

### Python Environments

This project uses two separate Python environments:

**Windows Environment (Production)**:
- Path: `D:\anaconda\envs\stsai\python.exe`
- Purpose: Running the AI with Communication Mod (real gameplay)
- Used by: Communication Mod's `config.properties`
- Contains: All dependencies including PyTorch 2.x with CUDA support
- Why: Native Windows performance, no WSL overhead

**WSL Environment (Development)**:
- Path: `/home/wangce/miniconda3/envs/minimind310/bin/python`
- Purpose: Development, testing, debugging
- Used by: Development commands, test scripts
- Contains: PyTorch 2.3.0, CUDA 12.1, development tools
- Why: Access to Linux tools, git, development workflow

**Important**: Always use the Windows environment when running through Communication Mod. The WSL environment has significant performance overhead (~7-38x slower) due to Windows/WSL process boundary.

### Running the AI

**Via Communication Mod (production)**:
1. Install [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod)
2. Configure Communication Mod's `config.properties` (typically at `c:\Users\{USERNAME}\AppData\Local\ModTheSpire\CommunicationMod\config.properties`) to run `main.py`
3. Use Windows Python path: `D:\anaconda\envs\stsai\python.exe`

### Testing

Integration tests (require live game):
```bash
python test_startup.py          # Communication integration
python test_combat_system.py    # Combat decisions
python test_tracking.py          # Statistics tracking
python test_optimized_ai.py      # Optimized agent
```

**Note**: No unit test framework - tests require running Slay the Spire instance.

### Communication Mod Source Code

**Location**: `D:\IdeaProjects\CommunicationMod`

The Communication Mod source code is available locally for reference when debugging protocol issues or understanding game state format.

**Key areas**:
- Protocol implementation and command handling
- Game state serialization format
- Available commands and their parameters
- Message types and validation

**Use cases**:
- Understanding why certain actions are rejected
- Verifying JSON field names and structures
- Checking available commands for specific game states
- Debugging communication protocol issues

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

### 📁 Important Paths

**Game Directory** (logs and checkpoints):
```
D:\SteamLibrary\steamapps\common\SlayTheSpire\
```

**Log Files** (in game directory):
```
D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log
D:\SteamLibrary\steamapps\common\SlayTheSpire\communication_mod_errors.log
```

**AI Game Marking** (in game directory):
```
D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\
  └── ai_games.txt  (one timestamp per line, marks AI games)
```

**RL Checkpoints** (in game directory):
```
D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints\
  ├── rl_combat_model_ep1.pth
  ├── rl_combat_model_ep2.pth
  └── ... (keeps latest 5 checkpoints)
```

**Game Run Records** (in game directory):
```
D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\
  ├── IRONCLAD/
  ├── THE_SILENT/
  ├── DEFECT/
  └── WATCHER/
```

### Log Files (in game directory)

| File                           | Purpose                                                                                                       |
|--------------------------------|---------------------------------------------------------------------------------------------------------------|
| `ai_debug.log`                 | AI debugging and decision history (auto-rotates at 10MB, keeps 5 backups)                                      |
| `communication_mod_errors.log` | Python exceptions and stack traces                                                                            |

### AI Game Marking (in game directory)

**Location**: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\ai_games.txt`

**Format**: One Unix timestamp per line, marking games played by AI:
```
1769332451
1769332482
1769332514
```

**Purpose**: Distinguish AI games from user-played games. Each timestamp corresponds to a `.run` file in `runs/IRONCLAD/`.

**Analysis**: Use `analysis_scripts/analyze_ai_runs.py` to view statistics:
```bash
cd D:\SteamLibrary\steamapps\common\SlayTheSpire
python D:\PycharmProjects\slay-the-spire-ai\analysis_scripts\analyze_ai_runs.py
```

### Game Run Records (in game directory)

**Location**: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\`

The game automatically saves detailed JSON records for each run, organized by character class:

```
runs/
├── IRONCLAD/          # Ironclad runs
├── THE_SILENT/        # Silent runs
├── DEFECT/            # Defect runs
├── WATCHER/           # Watcher runs
└── DAILY/             # Daily runs
```

**File Format**: Each file is named `{timestamp}.run` and contains a JSON object with:
- **Path Taken**: Node-by-node progression (M=Monster, $=Shop, ?=Event, R=Rest, E=Elite, T=Treasure, B=Boss)
- **Deck Build**: Full deck list with upgrades, cards purged, cards purchased
- **Combat Performance**: Damage taken per encounter, turns per combat
- **Event Choices**: All event decisions and outcomes
- **Relics/Potions**: Complete acquisition history
- **Neow Bonus**: Initial run blessing
- **Ascension Level**: Difficulty setting

**Use Cases**:
- **Post-Mortem Analysis**: Identify specific failure points (e.g., died to elite on floor 8)
- **Deck Building Patterns**: Understand what cards are frequently purchased/skipped
- **Performance Tracking**: Compare win rates across different builds
- **Decision Validation**: Verify AI is making optimal choices at events/shops
- **Regression Testing**: Detect if recent changes negatively impact performance

**Example Analysis**:
```bash
# View latest Ironclad runs
ls -lht "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs/IRONCLAD" | head -10

# Extract key stats from run file
jq '{floor: .floor_reached, victory: .victory, killed_by: .killed_by, path: .path_taken}' *.run
```

### Debugging Workflow

When debugging crashes:
1. Check `communication_mod_errors.log` - Python exceptions
2. Check `ai_debug.log` - game state tracking and decisions
3. Check `runs/ai_games.txt` - verify AI games are being marked
4. Use `analysis_scripts/analyze_ai_runs.py` - analyze AI performance

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