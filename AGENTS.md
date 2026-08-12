
---

## 🐍 Python Environments

This project uses two separate Python environments for different purposes:

### Windows Environment (Production)

**Path**: `D:\anaconda\envs\stsai\python.exe`

**Purpose**: Running the AI with Communication Mod during actual gameplay

**Configuration**:
- Used in: `C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties`
- Example command:
  ```properties
  command="D\:/anaconda/envs/stsai/python.exe" "D\:/PycharmProjects/slay-the-spire-ai/main.py" -a 20 --agent optimized
  ```

**Dependencies**:
- PyTorch 2.x with CUDA support
- All spirecomm dependencies
- Communication Mod compatible

**Performance**: Native Windows execution, minimal overhead (~100-200ms per decision)

### WSL Environment (Development)

**Path**: `/home/wangce/miniconda3/envs/minimind310/bin/python`

**Purpose**: Development, testing, and debugging only

**Used by**:
- Development commands in terminal
- Test scripts (`test_*.py`)
- Code debugging and experimentation

**Dependencies**:
- PyTorch 2.3.0
- CUDA 12.1
- Development tools (git, vim, etc.)

**Performance Warning**: ⚠️ **Do NOT use for actual gameplay**
- WSL has ~7-38x slower decision times (0.7-3.8s vs 100-200ms)
- Windows/WSL process boundary creates significant overhead
- Only suitable for development/testing, not production games

### Quick Reference

| Environment | Path | Purpose | Performance |
|-------------|------|---------|-------------|
| **Windows** | `D:\anaconda\envs\stsai\python.exe` | Production gameplay | ✅ Fast (~100-200ms) |
| **WSL** | `/home/wangce/miniconda3/envs/minimind310/bin/python` | Development only | ❌ Slow (0.7-3.8s) |

### Important Notes

1. **Always use Windows Python for Communication Mod**
   - Edit `config.properties` to use `D:\anaconda\envs\stsai\python.exe`
   - Never use WSL paths in `config.properties`

2. **WSL is for development workflow**
   - Writing code
   - Running tests
   - Debugging
   - Git operations

3. **Performance comparison** (from actual testing):
   ```
   Windows Python:  14:08:04 → 14:08:04  (~100ms)  ✅
   WSL Python:      14:08:04 → 14:08:07  (~3s)     ❌
   ```

### Pytest Temp Directories On Windows

Use a pre-created parent under the system temp directory for direct Codex pytest
invocations. Do not create new `.pytest_*` or `.codex_pytest` roots in the
repository.

```powershell
$pytestRoot = Join-Path $env:TEMP "codex-pytest-stsai"
New-Item -ItemType Directory -Path $pytestRoot -Force
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider `
  --basetemp (Join-Path $pytestRoot "<unique-scope>") <test-paths>
```

- Pytest can create and reuse the scoped child directory once its parent exists.
- A sandboxed `Remove-Item -Recurse` may be denied even after pytest succeeds;
  that cleanup denial is not a test failure.
- Do not retry the test merely to clean its basetemp. At a maintenance boundary,
  resolve the exact absolute child path and remove only that path with the
  required elevated filesystem permission. Never use a wildcard or broad
  repository cleanup.
- If pytest itself reports a setup or cleanup `PermissionError`, record the run
  as infrastructure failure rather than RED/GREEN test evidence, then rerun once
  with a fresh scoped child under the system-temp parent.
- `scripts/run_test_gate.py` currently owns its unique basetemp under the
  ignored repository `.pytest_gates/` root. In a managed Codex sandbox, run that
  gate once with the exact elevated command permission it needs; do not first
  launch a non-elevated gate that may fail only during nested pytest cleanup.

### Native Build Artifact Directories

Treat an ignored native module path as immutable once a committed registration,
manifest, or preimplementation artifact binds its hash. Never reconfigure or
rebuild an existing `.sts_lightspeed*_build` directory for a later experiment.
Use a new run-scoped build directory, verify its module hash, and bind that new
path in the new registration. This keeps historical source-only checks from
depending on mutually incompatible bytes at one mutable path.

---

# AI Agent Development Guide

## 📁 Log Files and Checkpoints

### Game Directory

**Important**: All logs and checkpoints are written to the Slay the Spire game directory (not the project directory).

```
D:\SteamLibrary\steamapps\common\SlayTheSpire\
```

### Log Files

| File | Path | Purpose |
|------|------|---------|
| **AI Debug Log** | `D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log` | AI decisions, game state tracking, map routing choices (auto-rotates at 10MB) |
| **Error Log** | `D:\SteamLibrary\steamapps\common\SlayTheSpire\communication_mod_errors.log` | Python exceptions and stack traces |
| **AI Game Marking** | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\ai_games.txt` | One Unix timestamp per line, marks AI-played games |

### AI Game Marking

**Location**: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\ai_games.txt`

**Format**: Simple text file, one timestamp per line:
```
1769332451
1769332482
1769332514
```

**Purpose**: Distinguish AI games from user-played games. Each timestamp matches a `.run` file in `runs/IRONCLAD/`.

**Analysis Script**: `analysis_scripts/analyze_ai_runs.py` provides statistics and insights.

### RL Training Checkpoints

**Location**: `D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints\`

```
checkpoints/
├── rl_combat_model_ep1.pth
├── rl_combat_model_ep2.pth
├── rl_combat_model_ep3.pth
├── rl_combat_model_ep4.pth
└── rl_combat_model_ep5.pth  (keeps latest 5)
```

**Auto-loading**: When running with `--train`, the agent automatically loads the latest checkpoint for continued training.

### Game Run Records

**Location**: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\`

Organized by character class:
```
runs/
├── IRONCLAD/
├── THE_SILENT/
├── DEFECT/
├── WATCHER/
└── DAILY/
```

Each file is `{timestamp}.run` containing:
- Path taken (M/$/?/R/E/T/B notation)
- Deck build (cards, upgrades, purges)
- Combat performance (damage, turns)
- Event choices
- Relics/potions acquired
- Ascension level

### Quick Commands

```bash
# View latest AI decisions
tail -100 "D:\SteamLibrary\steamapps\common\SlayTheSpire\ai_debug.log"

# Check AI game marking
cat "D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\ai_games.txt"

# Analyze AI performance
cd "D:\SteamLibrary\steamapps\common\SlayTheSpire"
python "D:\PycharmProjects\slay-the-spire-ai\analysis_scripts\analyze_ai_runs.py"

# List checkpoints
ls -lh "D:\SteamLibrary\steamapps\common\SlayTheSpire\checkpoints/"

# View latest Ironclad runs
ls -lht "D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD" | head -10
```

---

## 📊 Game Run Records Analysis

### Overview

Slay the Spire automatically saves detailed JSON records for each run, providing valuable data for AI agent analysis and optimization.

### Location

```
D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\
├── IRONCLAD/          # Ironclad runs
├── THE_SILENT/        # Silent runs
├── DEFECT/            # Defect runs
├── WATCHER/           # Watcher runs
└── DAILY/             # Daily runs
```

### File Format

Each file is named `{timestamp}.run` and contains a JSON object with:

- **Path Taken**: Node-by-node progression (M=Monster, $=Shop, ?=Event, R=Rest, E=Elite, T=Treasure, B=Boss)
- **Deck Build**: Full deck list with upgrades, cards purged, cards purchased
- **Combat Performance**: Damage taken per encounter, turns per combat
- **Event Choices**: All event decisions and outcomes
- **Relics/Potions**: Complete acquisition history
- **Neow Bonus**: Initial run blessing
- **Ascension Level**: Difficulty setting

### Quick Start

```bash
# View latest Ironclad runs
ls -lht "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs/IRONCLAD" | head -10

# Read a specific run
cat "/mnt/d/SteamLibrary/steamapps/common/SlayTheSpire/runs/IRONCLAD/1767889744.run" | jq

# Extract key stats
jq '{floor: .floor_reached, victory: .victory, killed_by: .killed_by, path: .path_taken}' *.run
```

### Analysis Workflow

1. **Identify Failure Mode** from run records (`runs/IRONCLAD/*.run`)
2. **Check AI Marking** (`runs/ai_games.txt`) to confirm it was an AI game
3. **Check Logs** (`ai_debug.log`) for decision details
4. **Locate Code** responsible for the decision
5. **Implement Fix** in scoring/decision logic
6. **Verify** by running new games

### Integration with Other Logs

- **ai_debug.log** - Detailed decision history
- **runs/ai_games.txt** - AI game marking (timestamps)
- **runs/IRONCLAD/*.run** - Complete game records (JSON)

Use run records to find problematic games, then cross-reference with logs to understand the AI's reasoning.

---

## 🔌 Communication Mod Reference

### Source Code Location

**Path**: `D:\IdeaProjects\CommunicationMod`

The Communication Mod source code is available locally for deep-dive debugging and protocol understanding.

### When to Reference the Source Code

Consult the Communication Mod source when:

1. **Debugging Protocol Issues**
   - Actions being rejected without clear error messages
   - Unexpected game state transitions
   - Missing or malformed JSON fields

2. **Understanding Command Behavior**
   - Exact parameter requirements for actions
   - Preconditions for valid commands
   - Side effects of specific actions

3. **Extending Functionality**
   - Adding support for new game features
   - Handling edge cases in game states
   - Implementing new action types

4. **Performance Optimization**
   - Understanding message overhead
   - Identifying bottlenecks in state transmission
   - Optimizing action sequences

### Key Areas to Explore

- **Protocol Handlers**: How stdin/stdout messages are parsed and executed
- **State Serialization**: JSON structure for game objects
- **Command Validation**: What makes an action valid/invalid
- **Event System**: How game events trigger state updates

### Integration with spirecomm

The `spirecomm` package (`spirecomm/communication/coordinator.py`) handles the Python side of this protocol:

```
Communication Mod (Java)
    ↓ stdin: JSON game state
Coordinator.receive_game_state_update()
    ↓ callbacks
Agent.get_next_action_in_game()
    ↓
Action → action_queue
    ↓ stdout: text commands
Communication Mod executes action
```
