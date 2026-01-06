# Monster Data Extraction from Fandom Wiki

This directory contains scripts for extracting monster data from the Slay the Spire Fandom Wiki using Playwright MCP.

## Current Status

### ✅ Completed (2/22 monsters)
- **Cultist** (Normal) - Complete with Ritual mechanics
- **Lagavulin** (Elite) - Complete with hibernation mechanics

### 🔄 In Progress
Act 1 Elites/Bosses remaining (4):
- Slaver
- Gremlin Giant
- Guardian
- Slime Boss
- Hexaghost

### 📋 Pending (20 monsters)
- Act 2 Elites/Bosses (5): Gremlin Leader, Centurion, Champ, Reptomancer, Collector
- Act 3 Elites/Bosses (4): Sentry, Chosen, Time Eater, Donu & Deca
- High-Priority Normals (6): Jaw Worm, Fungi Beast, Shield & Spear, Sneaky Gremlin, Book of Stabbing, Spiker

## Scripts

### 1. `extract_from_playwright.py`
Main extraction script that processes Playwright browser_evaluate results.

**Usage:**
```bash
python extract_from_playwright.py --test
```

**Features:**
- Parses HP ranges (normal + ascension modifiers)
- Extracts moves table with damage/effects
- Identifies special mechanics (summoner, hibernation, phase_change, death_split)
- Generates threat profiles

### 2. `batch_extract_monsters.py`
Batch extraction script for processing multiple monsters.

**Usage:**
```bash
# List all monsters to extract
python batch_extract_monsters.py --list

# Import data from Playwright JSON
echo '<playwright_json>' | python batch_extract_monsters.py --import <monster_name>
```

## Extraction Workflow

### Manual Extraction with Playwright MCP:

1. **Navigate to monster page:**
   ```
   mcp__plugin_playwright_playwright__browser_navigate
   url: https://slay-the-spire.fandom.com/wiki/<Monster_Name>
   ```

2. **Extract data using JavaScript:**
   ```javascript
   () => {
     const hpSection = document.querySelector('.mw-parser-output');
     const allText = hpSection?.innerText || '';

     const movesTable = Array.from(document.querySelectorAll('table')).find(t =>
       t.querySelector('th')?.textContent.includes('Name')
     );

     let moves = [];
     if (movesTable) {
       const rows = Array.from(movesTable.querySelectorAll('tr')).slice(1);
       rows.forEach(row => {
         const cells = row.querySelectorAll('td');
         if (cells.length >= 3) {
           moves.push({
             name: cells[0].textContent.trim(),
             intent: cells[1].textContent.trim(),
             effect: cells[2].textContent.trim()
           });
         }
       });
     }

     const patternText = Array.from(document.querySelectorAll('h2, h3'))
       .filter(h => h.textContent.includes('Pattern'))
       .map(h => h.nextElementSibling?.textContent || '')[0] || '';

     return { allText, moves, patternText };
   }
   ```

3. **Process with extraction script:**
   ```bash
   echo '<json_result>' | python batch_extract_monsters.py --import <Monster_Name>
   ```

4. **Add to consolidated JSON file:**
   - `spirecomm/data/monster_wiki_data/act1_elites_bosses.json`
   - `spirecomm/data/monster_wiki_data/act2_elites_bosses.json`
   - `spirecomm/data/monster_wiki_data/act3_elites_bosses.json`
   - `spirecomm/data/monster_wiki_data/normal_monsters.json`

## Data Format

Each monster has the following structure:

```json
{
  "monster_id": "Unique_ID",
  "name": "Monster Name",
  "monster_type": "normal|elite|boss",
  "hp_ranges": {
    "normal": {"min": X, "max": Y},
    "ascension_N+": {"min": X, "max": Y}
  },
  "moves": [
    {
      "move_id": 0,
      "name": "Move Name",
      "intent": "ATTACK|BUFF|DEBUFF|DEFEND",
      "damage": null or number,
      "effect": "Description",
      "strength_gain": null or number,
      "ascension_modifiers": {...}
    }
  ],
  "pattern": {
    "description": "Text description of move pattern"
  },
  "special_mechanics": {
    "type": "summoner|hibernation|phase_change|death_split|none",
    "...": "additional fields based on type"
  },
  "threat_profile": {
    "base_threat": number,
    "scaling_threat": number,
    "hibernation_threat": number (if applicable),
    "awakened_threat": number (if applicable)
  }
}
```

## Next Steps

1. Complete extraction of remaining 20 priority monsters
2. Create enhanced monster database module (`spirecomm/ai/heuristics/enhanced_monster_database.py`)
3. Integrate with AI systems (threat calculation, targeting, combat modes)
4. Add unit tests for data validation
5. Profile performance of enhanced systems

## Notes

- All data needs manual review after extraction
- Ascension modifiers need careful handling (some monsters have A2+, A10+, A15+, A17+, A18+)
- Special mechanics may require game testing for verification
- Move patterns need to be translated into move_sequence arrays for prediction

## Integration with OpenSpec

This extraction work supports the `add-wiki-monster-data` change proposal:
- See: `openspec/changes/add-wiki-monster-data/`
- Spec deltas: monster-data-loading, enhanced-threat-assessment, intelligent-targeting, monster-aware-combat-modes, combat-simulation-enhancement
