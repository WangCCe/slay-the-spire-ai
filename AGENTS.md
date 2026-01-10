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

---

# AI Agent Development Guide

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

1. **Identify Failure Mode** from run records
2. **Check Logs** (ai_debug.log in d/SteamLibrary/steamapps/common/SlayTheSpire) for decision details with game_id from ai_game_stats.csv
3. **Locate Code** responsible for the decision
4. **Implement Fix** in scoring/decision logic
5. **Verify** by running new games

### Integration with Other Logs

- **ai_debug.log** - Detailed decision history (search for `game_id`)
- **ai_game_stats.csv** - Aggregate statistics
- **ai_game_stats.jsonl** - Per-game detailed logs

Use run records to find problematic games, then cross-reference with logs to understand the AI's reasoning.