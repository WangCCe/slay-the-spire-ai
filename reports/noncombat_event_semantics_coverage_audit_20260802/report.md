# Current Event Semantics Source Coverage Audit

This is read-only source coverage evidence. It is not resolver readiness, policy quality, simulator compatibility, or training authority.

## Summary

- Canonical Current events: 25
- Source-complete: 24
- Source-partial: 1
- Resolver ready: false

## Inventory

| Current event | Upstream enum | Branch | Label-sensitive | Legal indices | Display indices | Phase-sensitive | Status | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Back to Basics` | `ANCIENT_WRITING` | `explicit` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `Big Fish` | `BIG_FISH` | `explicit` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `Cursed Tome` | `CURSED_TOME` | `explicit` | true | 0, 1 | 0, 1, 5, 6 | true | `source_partial` | legal_return_dynamic:0x1 << (gc.info.eventData+1), legal_return_dynamic:0x3 << (gc.info.eventData+1) |
| `Dead Adventurer` | `DEAD_ADVENTURER` | `risky_fallback` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `Drug Dealer` | `AUGMENTER` | `risky_fallback` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `Face Trader` | `FACE_TRADER` | `explicit` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `Forgotten Altar` | `FORGOTTEN_ALTAR` | `explicit` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `Ghosts` | `GHOSTS` | `explicit` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `Golden Idol` | `GOLDEN_IDOL` | `explicit` | true | 0, 1, 2, 3, 4 | 0, 1, 2, 3, 4 | false | `source_complete` | none |
| `Golden Shrine` | `GOLDEN_SHRINE` | `explicit` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `Knowing Skull` | `KNOWING_SKULL` | `risky_fallback` | true | 0, 1, 2, 3 | 0, 1, 2, 3 | false | `source_complete` | none |
| `Liars Game` | `THE_SSSSSERPENT` | `risky_fallback` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `Living Wall` | `LIVING_WALL` | `explicit` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `Masked Bandits` | `MASKED_BANDITS` | `explicit` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `MindBloom` | `MINDBLOOM` | `explicit` | true | 0, 1, 2, 3 | 0, 1, 2, 3 | false | `source_complete` | none |
| `Mushrooms` | `HYPNOTIZING_COLORED_MUSHROOMS` | `explicit` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `Mysterious Sphere` | `MYSTERIOUS_SPHERE` | `explicit` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `N'loth` | `NLOTH` | `explicit` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `Note For Yourself` | `NOTE_FOR_YOURSELF` | `risky_fallback` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `Shining Light` | `SHINING_LIGHT` | `explicit` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `The Cleric` | `THE_CLERIC` | `explicit` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `The Library` | `THE_LIBRARY` | `risky_fallback` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `The Mausoleum` | `THE_MAUSOLEUM` | `risky_fallback` | true | 0, 1 | 0, 1 | false | `source_complete` | none |
| `Vampires` | `VAMPIRES` | `risky_fallback` | true | 0, 1, 2 | 0, 1, 2 | false | `source_complete` | none |
| `World of Goop` | `WORLD_OF_GOOP` | `explicit` | true | 0, 1 | 0, 1 | false | `source_complete` | none |

## Authority

- `formal_rl_readiness_authorized`: `false`
- `gameplay_authorized`: `false`
- `model_fitting_authorized`: `false`
- `promotion_authorized`: `false`
- `resolver_extension_authorized`: `false`
- `reward_authorized`: `false`
- `seed_use_authorized`: `false`
- `simulator_execution_authorized`: `false`
- `training_authorized`: `false`

A separate reviewed adapter-contract change is required before resolver extension or another compatibility evaluation.
