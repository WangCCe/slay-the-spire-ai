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

This is `spirecomm` - a Python package for interfacing with the game *Slay the Spire* through the [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod). It includes a simple AI bot that can play the game autonomously.

**Communication Mod**: An external mod for Slay the Spire that enables communication between the game and external processes via stdin/stdout. The mod sends JSON game state and accepts text commands.

## Installation and Setup

### Installing the package
```bash
python setup.py install
```

### Running the AI
1. Install and configure [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod) for Slay the Spire
2. Configure Communication Mod's `config.properties` (typically at `c:\Users\{USERNAME}\AppData\Local\ModTheSpire\CommunicationMod\config.properties`) to run `main.py` from this repository
3. The AI will cycle through all character classes (Ironclad, Silent, Defect) indefinitely

## Architecture

### Three-Layer Architecture

The codebase is organized into three main layers:

1. **spirecomm/spire/** - Game state data models
   - `game.py`: Core `Game` class that deserializes JSON from Communication Mod into Python objects
   - `character.py`: `Player`, `Monster`, `Intent` enum, `PlayerClass` enum
   - `card.py`: Card data model
   - `relic.py`: Relic data model
   - `potion.py`: Potion data model
   - `power.py`: Power/buff data model
   - `map.py`: Map node structure
   - `screen.py`: All screen types (Event, Rest, Shop, CombatReward, etc.)

2. **spirecomm/communication/** - Communication layer with the game
   - `coordinator.py`: `Coordinator` class manages bidirectional stdin/stdout communication
     - Runs background threads for reading/writing
     - Maintains game state and action queues
     - Executes actions when game is ready
     - Provides callbacks for state changes, errors, and out-of-game events
   - `action.py`: All action types (PlayCardAction, PotionAction, ChooseAction, etc.)
     - Each action has an `execute(coordinator)` method
     - Actions validate they can be executed via `can_be_executed()`

3. **spirecomm/ai/** - AI decision making
   - `agent.py`: `SimpleAgent` class that makes all gameplay decisions
     - `get_next_action_in_game()`: Main decision function called during gameplay
     - `get_play_card_action()`: Combat card selection logic
     - `handle_screen()`: Route to appropriate screen handler (map, rewards, events, etc.)
     - `choose_card_reward()`: Card reward selection based on priorities
   - `priorities.py`: Class-specific priority systems
     - `Priority` (base class), `SilentPriority`, `IroncladPriority`, `DefectPowerPriority`
     - Each class has lists for CARD_PRIORITY_LIST (rewards), PLAY_PRIORITY_LIST (combat), AOE_CARDS, DEFENSIVE_CARDS
     - `MAX_COPIES` dict limits how many of each card to add to deck
     - Map routing priorities by act (prioritize Rest/$/?/M/Elite nodes differently)

### Communication Flow

```
Communication Mod → stdin → Coordinator.input_queue → Coordinator.receive_game_state_update()
                                                                  ↓
                                                          Callback to SimpleAgent
                                                                  ↓
                                                          Returns Action → action_queue
                                                                  ↓
                                          Coordinator.execute_next_action() → stdout → Communication Mod
```

### State Machine

The AI responds to different game screens via `handle_screen()` in agent.py:
- **EVENT**: Choose event options (some hardcoded logic)
- **CHEST**: Open chest
- **SHOP_ROOM**: Open shopkeeper menu
- **REST**: Choose rest option (REST if HP < 50%, SMITH, LIFT, or DIG)
- **CARD_REWARD**: Pick best card based on priorities or skip
- **COMBAT_REWARD**: Take rewards (gold/relics/potions, skip potions if full)
- **MAP**: Dynamic programming to find optimal path through the map
- **BOSS_REWARD**: Choose best boss relic
- **SHOP_SCREEN**: Buy cards/relics/purge based on priorities and gold
- **GRID**: Card selection (upgrade/transform/purge)
- **HAND_SELECT**: Choose cards from hand for card effects

### Combat Logic

The AI's combat decision flow in `get_play_card_action()`:
1. Separate zero-cost and nonzero-cost playable cards
2. Identify AOE cards and defensive cards
3. Skip defensive cards if already have enough block
4. Prioritize zero-cost non-attack cards first
5. Then nonzero-cost cards (prioritized by PLAY_PRIORITY_LIST)
6. Use AOE attacks when multiple monsters alive
7. Fall back to zero-cost attacks
8. Target lowest HP for attacks, highest HP for non-attacks

## Key Design Patterns

- **Callback architecture**: Register callbacks for state changes, errors, and menu navigation
- **Action queue**: Actions are queued and execute only when `game_is_ready` (Communication Mod is ready for commands)
- **Screen polymorphism**: Each screen type has its own class with `SCREEN_TYPE` and `from_json()` classmethod
- **Priority-based AI**: All decisions are based on hardcoded priority lists per character class

## Development Notes

- The package version is in `setup.py` (currently 0.6.0)
- Game state is completely reconstructed from JSON on each update (no state mutation between updates)
- Monster intent analysis is available for combat decisions
- The coordinator can run games continuously via `play_one_game()` which returns True for victory
- Map routing uses dynamic programming to maximize node priority scores
- Card IDs and Relic IDs come from Communication Mod's Java class names

## Reminder

### File Locations

**Game Directory**: `D:\SteamLibrary\steamapps\common\SlayTheSpire\`
- Statistical csv file: `ai_game_stats.csv`
- AI debug log: `ai_debug.log`
- Shop error log: `shop_error.log` (custom logging for shop crashes)
- CommunicationMod error log: `communication_mod_errors.log` (~18MB, contains detailed Python tracebacks)

**CommunicationMod Config**: `C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties`

### Debugging Tips

When debugging crashes or issues:
1. Check `communication_mod_errors.log` for Python exceptions and stack traces
2. Check `shop_error.log` for shop-related errors (if created)
3. Check `ai_debug.log` for game state tracking and decision history
4. Use `ai_game_stats.csv` for analyzing win rates and performance trends

**Common Issues**:
- Shop crash: Often caused by `coordinator.game` vs `coordinator.last_game_state` attribute confusion
- Beam search errors: Check combat planner implementation for tuple unpacking issues
- Missing attributes: Always use `coordinator.last_game_state` not `coordinator.game`