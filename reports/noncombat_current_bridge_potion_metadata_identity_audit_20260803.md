# Current Bridge Potion Metadata Identity Audit

Date: 2026-08-03

## Decision

The Current-policy simulator bridge has one deterministic, bounded potion
metadata compatibility defect. The upstream simulator and frozen Communication
Mod metadata each expose 42 non-empty base-game potions. Thirty-nine upstream
display names match metadata case-insensitively. Exactly three stable-ID/name
triples require an explicit compatibility mapping.

The repair may use only those three complete triples. Broad normalization,
display-name-only aliases, native adapter changes, and another diagnostic
execution are not justified.

## Evidence Identity

- Consumed r2 result: `current_bridge_diagnostic_failed` with
  `potion_metadata_missing`, detail `Elixir Potion`, and zero retained rows.
- R2 closeout:
  `reports/noncombat_current_bridge_diagnostic_smoke_20260803_r2_closeout.md`.
- Upstream repository commit:
  `7476a81954020087da31d41d16fddf475746ec2d`.
- Upstream source:
  `D:\CLionProjects\sts_lightspeed\include\constants\Potions.h`, clean at that
  path, 11,798 bytes, SHA-256
  `d16d41c0b95028d7338b05f455511c266907e5ec31be711a705ceeb077ea1938`.
- Frozen metadata:
  `D:\SteamLibrary\steamapps\common\SlayTheSpire\export\items.json`, 240,371
  bytes, SHA-256
  `e23784ea8ed3092e3bfa9918240e162a9cbcb837badfb53c612eb0d83cc811dc`.
- Native adapter behavior: potion snapshots serialize
  `potionEnumNames[index]` as `id` and `getPotionName(index)` as `name`.
- Bridge behavior before repair: `MetadataCatalog` indexes metadata by
  `name.casefold()` and rejects a non-empty potion when the native display name
  is not an index key.

## Method

The audit parsed the upstream `potionNames[]` array, excluded `INVALID` and
`EMPTY_POTION_SLOT`, and compared the remaining display names with unmodded
metadata potion names using ordinal case-insensitive equality. Stable native IDs
were taken from the same indexed `potionEnumNames[]` table. No native module,
environment, seed, gameplay process, model, or policy was loaded.

## Complete Result

| Measure | Count |
|---|---:|
| Upstream non-empty potion names | 42 |
| Unmodded metadata potion names | 42 |
| Direct case-insensitive matches | 39 |
| Native names absent from metadata | 3 |
| Metadata names absent from native display names | 3 |

The complete mismatch set is:

| Stable native ID | Native display name | Canonical metadata name |
|---|---|---|
| `ELIXIR_POTION` | `Elixir Potion` | `Elixir` |
| `FAIRY_POTION` | `Fairy Potion` | `Fairy in a Bottle` |
| `GAMBLERS_BREW` | `Gamblers Brew` | `Gambler's Brew` |

The 39 direct matches are:

`Ambrosia`, `Ancient Potion`, `Attack Potion`, `Blessing Of The Forge`,
`Block Potion`, `Blood Potion`, `Bottled Miracle`, `Colorless Potion`,
`Cultist Potion`, `Cunning Potion`, `Dexterity Potion`, `Distilled Chaos`,
`Duplication Potion`, `Energy Potion`, `Entropic Brew`, `Essence Of Darkness`,
`Essence Of Steel`, `Explosive Potion`, `Fear Potion`, `Fire Potion`,
`Flex Potion`, `Focus Potion`, `Fruit Juice`, `Ghost In A Jar`,
`Heart Of Iron`, `Liquid Bronze`, `Liquid Memories`, `Poison Potion`,
`Potion Of Capacity`, `Power Potion`, `Regen Potion`, `Skill Potion`,
`Smoke Bomb`, `Snecko Oil`, `Speed Potion`, `Stance Potion`,
`Strength Potion`, `Swift Potion`, and `Weak Potion`.

Capitalization differences inside that list are already accepted by the
existing case-insensitive exact-name path and require no alias.

## Red Regression

The final focused red run selected the new alias, negative-identity, exact-name,
and shop-hydration regressions. It returned
`5 failed, 4 passed, 66 deselected`. The three direct alias cases and the
shop-level Elixir case failed at the existing `potion_metadata_missing` line.
The mapped Elixir ID paired with the otherwise valid `Attack Potion` metadata
name failed because the old direct-name path did not raise. The other
inconsistent-identity cases and the exact-name compatibility case passed before
production code changed.

## Repair And Authority Boundary

The minimal repair is one closed mapping keyed by stable native ID with both
the expected native display name and canonical metadata name. An alias is valid
only when direct lookup failed, both names match their registered values, and
the canonical metadata entry exists. The hydrated typed potion should retain
native ID, source slot, and price while using the canonical metadata name so
existing potion effect metadata remains accurate.

Unknown IDs, changed upstream names, absent canonical metadata, and any fourth
display difference remain `potion_metadata_missing`. This audit and repair do
not authorize retrying r2, preparing r3, fresh evidence, a baseline floor,
gameplay, OPE, model fitting, reward changes, formal RL, training,
qualification, policy/model loading, or promotion.

## Focused Verification

After the repair, the nine selected positive, negative, exact-name, and
shop-hydration regressions passed. The complete bridge, simulator-adapter,
reachable-event-option, and potion-mechanics focused set then returned
`113 passed, 5 skipped` in 8.57 seconds. Both modified Python files passed
`py_compile`; `git diff --check`, strict change validation, and strict global
OpenSpec validation also passed.

The registered partitioned `commit` gate then passed with
`3582 passed, 11 skipped` in 239.01 seconds and 242.08 seconds total. No raw
unpartitioned full suite, native environment, seed, gameplay, model, reward,
OPE, formal-RL, training, qualification, loading, or promotion ran.
