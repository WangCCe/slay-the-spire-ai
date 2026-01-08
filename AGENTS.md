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

### Recent Performance Analysis

As of 2026-01-09, the latest Ironclad runs show:

1. **1767889744.run** - Died on floor 8 to Gremlin Nob (Elite)
   - Path: M→M→$→?→M→R→M→?
   - Purchased: Body Slam
   - Issues: Elite encounter on floor 8

2. **1767886025.run** - Died on floor 7 to Mushroom Lair event
   - Path: M→M→$→M→?→E→?
   - Purchased: Sever Soul
   - Issues: Risky event choice led to death

3. **1767885621.run** - Died on floor 16 to Slime Boss (Act 1 Boss)
   - Path: M→?→M→?→$→R→$→M→T→M→R→?→$→M→R→B
   - Best performance, reached Act 1 Boss
   - Purchased: Rampage, Nunchaku relic

### Common Failure Patterns

| Pattern | Indicator | Potential Cause |
|---------|-----------|-----------------|
| **Early Death** (Floor 1-10) | `floor_reached < 10` | Combat decisions, deck building issues |
| **Elite Death** | `killed_by` in ["Gremlin Nob", "Lagavulin"] | Over-defensive play, damage miscalculation |
| **Event Death** | Event choice causes death | Poor risk assessment, low HP |
| **Boss Death** | `path_taken[-1] == "B"` | Insufficient deck power, upgrade issues |

### Analysis Workflow

1. **Identify Failure Mode** from run records
2. **Check Logs** (ai_debug.log, ai_game_stats.jsonl) for decision details
3. **Locate Code** responsible for the decision
4. **Implement Fix** in scoring/decision logic
5. **Verify** by running new games

### Integration with Other Logs

- **ai_debug.log** - Detailed decision history (search for `play_id`)
- **ai_game_stats.csv** - Aggregate statistics
- **ai_game_stats.jsonl** - Per-game detailed logs

Use run records to find problematic games, then cross-reference with logs to understand the AI's reasoning.