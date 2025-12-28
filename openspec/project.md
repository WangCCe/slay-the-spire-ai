# Project Context

## Purpose

**spirecomm** is a Python package that enables programmatic interaction with the video game *Slay the Spire* through the [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod). The project includes:

- **Communication Layer**: Bidirectional stdin/stdout protocol for exchanging JSON messages with the game
- **Game State Models**: Complete deserialization of game state into Python objects
- **Autonomous AI Bot**: Plays the game autonomously, making decisions for combat, card selection, map routing, events, shops, and more
- **Extensible AI System**: Modular decision-making architecture with heuristic-based combat planning, deck analysis, and character-specific strategies

The goal is to create an AI that can consistently beat Slay the Spire at high ascension levels (A20+) across all character classes (Ironclad, Silent, Defect).

## Tech Stack

- **Language**: Python 3.7+
- **Core Dependencies**: None (standard library only - no external Python packages required)
- **External System**: [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod) (Java mod for Slay the Spire)
- **Communication Protocol**: stdin/stdout with JSON message format
- **Package Manager**: setuptools (via `setup.py`)
- **Version**: 0.6.0

## Project Conventions

### Code Style

- **Naming Conventions**:
  - Classes: `PascalCase` (e.g., `SimpleAgent`, `DecisionContext`)
  - Functions/Methods: `snake_case` (e.g., `get_next_action_in_game`, `handle_screen`)
  - Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_COPIES`, `CARD_PRIORITY_LIST`)
  - Private/Internal: Prefixed with underscore (e.g., `_calculate_block`)

- **Import Style**:
  - Group imports: standard library, third-party, local
  - Use `from X import Y` for common imports
  - Wildcard imports (`*`) used selectively for action classes

- **Code Organization**:
  - Maximum line length: ~120 characters (practical, not strict)
  - Docstrings: Minimal, relying on descriptive names
  - Comments: Used for complex logic or game-specific explanations

- **Error Handling**:
  - Use try/except in communication-critical paths
  - Print errors to stderr to avoid interfering with Communication Mod protocol
  - Fallback to safe actions (EndTurnAction, ProceedAction) on errors

### Architecture Patterns

The project follows a **three-layer architecture**:

1. **spirecomm/spire/** - Data Models Layer
   - Pure data classes representing game state
   - JSON deserialization via `from_json()` classmethods
   - No business logic, only state representation

2. **spirecomm/communication/** - Communication Layer
   - `Coordinator`: Threaded bidirectional communication via stdin/stdout
   - `Action`: Command pattern with `execute(coordinator)` methods
   - Callback-based architecture for game state changes

3. **spirecomm/ai/** - Decision Making Layer
   - `SimpleAgent`: Main agent class with screen handlers
   - `heuristics/`: Specialized evaluation modules (combat, deck, map, cards)
   - `decision/`: Decision context and planning systems
   - `statistics.py`: Game tracking and performance metrics

**Key Patterns**:
- **Callback Architecture**: Register callbacks for state changes, errors, and out-of-game events
- **Action Queue**: Commands queue and execute only when `game_is_ready`
- **Screen Polymorphism**: Each screen type has dedicated handler methods
- **Priority-Based AI**: Decisions driven by character-specific priority lists
- **Heuristic Evaluation**: Beam search combat planning with card synergy scoring

### Testing Strategy

- **Test Files**: Located in project root (`test_*.py`)
  - `test_startup.py`: Communication integration tests
  - `test_combat_system.py`: Combat decision verification
  - `test_tracking.py`: Statistics tracking validation
  - `test_optimized_ai.py`: Optimized agent tests

- **Testing Approach**:
  - Manual/integration testing with live Slay the Spire game
  - No automated unit test framework (no pytest/unittest dependencies)
  - Tests require Communication Mod and running game instance

- **Validation**:
  - Win rate tracking via CSV logging (`ai_game_stats.csv`)
  - Performance metrics per character class and ascension level

### Git Workflow

- **Branching**:
  - `master` is the main branch
  - Feature development typically on `master` for this project

- **Commit Convention**:
  - Use **Conventional Commits** format:
    - `feat:` - New features
    - `fix:` - Bug fixes
    - `docs:` - Documentation changes
    - `refactor:` - Code refactoring
  - Examples:
    - `feat: Add comprehensive game statistics tracking system`
    - `feat: Complete combat decision system rewrite with beam search`

- **Commit Message Style**:
  - Imperative mood ("Add" not "Added" or "Adds")
  - Concise summary (50-72 chars)
  - Detailed body for complex changes

## Domain Context

### Slay the Spire Game Concepts

**Characters (Player Classes)**:
- **Ironclad**: Strength-based warrior, block cards, self-damage synergies
- **Silent**: Shiv/dexterity focused, poison, deck cycling
- **Defect**: Orb-based powers, elemental spells, focus manipulation

**Game Flow**:
1. **Map Navigation**: Choose path through nodes (Monster, Elite, Event, Rest, Shop, Treasure, Boss)
2. **Combat**: Play cards, use potions, manage block/HP against monsters
3. **Rewards**: Choose cards/relics/gold after combat
4. **Events**: Make choices that affect game state
5. **Shops**: Buy cards, relics, or card removal services
6. **Rest**: Recover HP, upgrade cards, or lift (copy a card)

**Combat Mechanics**:
- **Energy**: Limited resource (typically 3) to play cards
- **Block**: Damage reduction, decays each turn
- **Intents**: Monsters telegraph their next action (attack, defend, buff, debuff)
- **Powers**: Ongoing effects that modify game state
- **Relics**: Passive abilities that provide strategic advantages

**AI Strategies**:
- **Card Priorities**: Class-specific lists ranking card value for rewards
- **Play Priorities**: Combat-specific card selection ordering
- **Deck Archetypes**: Synergy detection (e.g., Ironclad Strength build, Shiv Silent)
- **Map Routing**: Dynamic programming to optimize path based on node priorities

### Communication Mod Protocol

- **Direction**: Game → AI (JSON via stdin), AI → Game (commands via stdout)
- **Game State**: Complete JSON snapshot transmitted on each state change
- **Commands**: Simple text commands (e.g., "play 0", "choose 1", "proceed")
- **Ready Detection**: Game sends "Ready for input" marker when accepting commands

## Important Constraints

- **Dependency-Free**: No external Python packages - must work with standard library only
- **Real-Time Decisions**: AI must respond quickly (~100ms) to avoid game timeouts
- **Stateless Design**: Game state reconstructed from JSON each update (no mutation between updates)
- **Communication Compatibility**: Must match Communication Mod's expected protocol exactly
- **Error Resilience**: Invalid actions crash to desktop; must validate before sending
- **Cross-Platform**: Works on Windows, macOS, Linux (Communication Mod limitation)
- **Single Instance**: Only one game/agent pair can run simultaneously

## External Dependencies

### Communication Mod
- **Repository**: https://github.com/ForgottenArbiter/CommunicationMod
- **Purpose**: Slay the Spire mod that enables external program communication
- **Protocol**: stdin/stdout JSON exchange
- **Version Compatibility**: spirecomm 0.6.0 targets Communication Mod 0.7.0+
- **Configuration**: Requires `config.properties` setup to launch Python agent
- **Install Location**: `c:\Users\{USERNAME}\AppData\Local\ModTheSpire\CommunicationMod\`

### Slay the Spire
- **Required**: Game installation with ModTheSpire mod loader
- **Platforms**: Windows, macOS, Linux
- **Version**: Works with current game versions (updated via Communication Mod)

### Data Files
- **Statistics CSV**: `ai_game_stats.csv` - tracks game outcomes and metrics
- **No External Data**: AI requires no pre-trained models or external databases
