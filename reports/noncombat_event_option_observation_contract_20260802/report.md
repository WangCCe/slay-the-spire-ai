# Non-Combat Event Option Observation Contract

This is a static Current-observation contract. It does not authorize a resolver, adapter change, simulator execution, gameplay, evaluation, model, or training.

| Canonical event | Upstream event id | Current event id | Rule | Options |
| --- | --- | --- | --- | --- |
| `Back to Basics` | `Back to Basics` | `Back to Basics` | `static` | 0:Elegance; 1:Simplicity |
| `Big Fish` | `Big Fish` | `Big Fish` | `static` | 0:Banana; 1:Donut; 2:Box |
| `Cursed Tome` | `Cursed Tome` | `Cursed Tome` | `cursed_tome_phase` | 0:Read; 1:Leave; 2:Continue; 3:Continue; 4:Continue; 5:Take; 6:Stop |
| `Dead Adventurer` | `Dead Adventurer` | `Dead Adventurer` | `static` | 0:Search; 1:Escape |
| `Drug Dealer` | `Drug Dealer` | `Drug Dealer` | `static` | 0:Test J.A.X; 1:Become Test Subject; 2:Ingest Mutagens |
| `Face Trader` | `Face Trader` | `Face Trader` | `static` | 0:Touch; 1:Trade; 2:Leave |
| `Forgotten Altar` | `Forgotten Altar` | `Forgotten Altar` | `static` | 0:Offer: Golden Idol; 1:Sacrifice; 2:Desecrate |
| `Ghosts` | `Ghosts` | `Ghosts` | `static` | 0:Accept; 1:Refuse |
| `Golden Idol` | `Golden Idol` | `Golden Idol` | `static` | 0:Take; 1:Leave; 2:Outrun; 3:Smash; 4:Hide |
| `Golden Shrine` | `Golden Shrine` | `Golden Shrine` | `static` | 0:Pray; 1:Desecrate; 2:Leave |
| `Knowing Skull` | `Knowing Skull` | `Knowing Skull` | `static` | 0:Riches?; 1:Success?; 2:A Pick Me Up?; 3:How do I leave? |
| `Liars Game` | `Liars Game` | `Liars Game` | `static` | 0:Agree; 1:Disagree |
| `Living Wall` | `Living Wall` | `Living Wall` | `static` | 0:Forget; 1:Change; 2:Grow |
| `Masked Bandits` | `Masked Bandits` | `Masked Bandits` | `static` | 0:Pay; 1:Fight! |
| `MindBloom` | `Mindbloom` | `MindBloom` | `static` | 0:I am War; 1:I am Awake; 2:I am Rich; 3:I am Healthy |
| `Mushrooms` | `Mushrooms` | `Mushrooms` | `static` | 0:Stomp; 1:Eat |
| `Mysterious Sphere` | `Mysterious Sphere` | `Mysterious Sphere` | `static` | 0:Open Sphere; 1:Leave |
| `N'loth` | `Nloth` | `N'loth` | `nloth_relic` | 0:Offer <relic>; 1:Offer <relic>; 2:Leave |
| `Note For Yourself` | `Note For Yourself` | `Note For Yourself` | `static` | 0:Take and Give; 1:Ignore |
| `Shining Light` | `Shining Light` | `Shining Light` | `static` | 0:Enter; 1:Leave |
| `The Cleric` | `The Cleric` | `The Cleric` | `static` | 0:Heal; 1:Purify; 2:Leave |
| `The Library` | `The Library` | `The Library` | `static` | 0:Read; 1:Sleep |
| `The Mausoleum` | `The Mausoleum` | `The Mausoleum` | `static` | 0:Open Coffin; 1:Leave |
| `Vampires` | `Vampires` | `Vampires` | `static` | 0:Offer; 1:Accept; 2:Refuse |
| `World of Goop` | `World of Goop` | `World of Goop` | `static` | 0:Gather Gold; 1:Leave It |

## Required Snapshot Extension

`N'loth` requires `state.decision_context.offered_relics` records for simulator choices 0 and 1, bound by relic slot, id, and name to `state.relics`.

Resolver and adapter readiness remain false.
