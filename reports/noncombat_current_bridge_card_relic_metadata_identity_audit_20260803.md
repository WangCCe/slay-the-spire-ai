# Current Bridge Card And Relic Metadata Identity Audit

Date: 2026-08-03

## Decision

The remaining static item-hydration surface has no card display-name gap and one
bounded relic compatibility gap. All 370 non-invalid upstream card display
names occur in the frozen Communication Mod metadata. Of 180 non-invalid
upstream relic identities, 163 display names match directly, 15 require exact
stable-ID-bound canonical aliases, and two simulator fallback relics are absent
from metadata.

The relic gap should be repaired through one closed 17-entry table. This audit
does not justify generic punctuation normalization, card changes, another
diagnostic execution, or training.

## Evidence Identity

- Upstream repository commit:
  `7476a81954020087da31d41d16fddf475746ec2d`.
- Card source: `D:\CLionProjects\sts_lightspeed\include\constants\Cards.h`,
  clean at that path, 62,887 bytes, SHA-256
  `3492ca9ec6ff3e1098092127892529589be91cb338d3ef44b5fd8e979f52a7e0`.
- Relic source: `D:\CLionProjects\sts_lightspeed\include\constants\Relics.h`,
  clean at that path, 16,831 bytes, SHA-256
  `092473d34e953ec4e9328d602250b67cb2d12c6df0be9b7bbaf435de47aa88d0`.
- Frozen metadata:
  `D:\SteamLibrary\steamapps\common\SlayTheSpire\export\items.json`, 240,371
  bytes, SHA-256
  `e23784ea8ed3092e3bfa9918240e162a9cbcb837badfb53c612eb0d83cc811dc`.
- Native adapter behavior: card and relic snapshots use enum-style stable IDs
  and upstream display names from the indexed constant arrays.
- Bridge behavior before repair: cards and relics require display names in
  case-insensitive metadata indexes; card duplicates are then disambiguated by
  color, while relic metadata supplies no additional hydrated field.

## Method

The audit parsed `cardNames[]`, `relicEnumNames[]`, and `relicNames[]`, excluded
their invalid sentinels, and compared upstream display names with unmodded
metadata names using ordinal case-insensitive equality. It also inspected the
simulator fallback call sites for metadata-absent relics. No native module,
environment, seed, gameplay process, model, or policy was loaded.

## Card Result

| Measure | Count |
|---|---:|
| Upstream non-invalid card identities | 370 |
| Unmodded metadata card records, including upgraded forms | 721 |
| Upstream display names absent from metadata | 0 |

The existing card duplicate-name/color branch remains necessary for names such
as `Strike` and `Defend`, but the complete upstream display-name set needs no
new alias or fallback.

## Relic Result

| Measure | Count |
|---|---:|
| Upstream non-invalid relic identities | 180 |
| Unmodded metadata relic records | 178 |
| Direct case-insensitive matches | 163 |
| Stable-ID-bound metadata aliases | 15 |
| Audited metadata-absent fallbacks | 2 |

The complete alias set is:

| Stable native ID | Native display name | Canonical metadata name |
|---|---|---|
| `BIRD_FACED_URN` | `Bird Faced Urn` | `Bird-Faced Urn` |
| `CAPTAINS_WHEEL` | `Captains Wheel` | `Captain's Wheel` |
| `CHARONS_ASHES` | `Charons Ashes` | `Charon's Ashes` |
| `NILRYS_CODEX` | `Nilrys Codex` | `Nilry's Codex` |
| `PHILOSOPHERS_STONE` | `Philosophers Stone` | `Philosopher's Stone` |
| `SELF_FORMING_CLAY` | `Self Forming Clay` | `Self-Forming Clay` |
| `DU_VU_DOLL` | `Du Vu Doll` | `Du-Vu Doll` |
| `GOLD_PLATED_CABLES` | `Goldplated Cables` | `Gold-Plated Cables` |
| `NEOWS_LAMENT` | `Neows Lament` | `Neow's Lament` |
| `SLAVERS_COLLAR` | `Slavers Collar` | `Slaver's Collar` |
| `DOLLYS_MIRROR` | `Dollys Mirror` | `Dolly's Mirror` |
| `LEES_WAFFLE` | `Lees Waffle` | `Lee's Waffle` |
| `NLOTHS_GIFT` | `Nloths Gift` | `N'loth's Gift` |
| `NLOTHS_HUNGRY_FACE` | `Nloths Hungry Face` | `N'loth's Hungry Face` |
| `PANDORAS_BOX` | `Pandoras Box` | `Pandora's Box` |

The exact metadata-absent identities are:

| Stable native ID | Native display name | Reachability source |
|---|---|---|
| `CIRCLET` | `Circlet` | General/rare relic pool fallback |
| `RED_CIRCLET` | `Red Circlet` | Boss relic pool fallback |

`Game.cpp` adds `CIRCLET` when a shuffled relic tier has no candidate.
`GameContext.cpp` returns `CIRCLET` for an empty rare pool and `RED_CIRCLET` for
an empty boss pool. The frozen exporter contains neither display name.

## Red Regression

The focused pre-implementation selection returned
`19 failed, 6 passed, 75 deselected` in 3.70 seconds. All 15 aliases, both
metadata exemptions, the mapped-ID/direct-name bypass case, and the shop-level
Pandora's Box case failed. The remaining inconsistent-identity cases and the
direct exact-name case passed before production code changed.

## Repair And Authority Boundary

The minimal repair is one closed mapping keyed by stable native ID. Each entry
binds the exact expected upstream name and either a canonical metadata name or
`None` only for the two fallback identities. Listed IDs must be validated before
the direct metadata path so another valid metadata name cannot bypass the
contract. Aliases hydrate with canonical names; fallbacks and direct matches
retain their incoming names. ID, slot, counter, price, snapshots, and candidates
remain unchanged.

Unknown IDs, changed names, missing alias targets, and any third metadata
exemption remain `relic_metadata_missing`. This audit and repair do not
authorize retrying either diagnostic, preparing r3, fresh evidence, a baseline
floor, gameplay, OPE, model fitting, reward changes, formal RL, training,
qualification, policy/model loading, or promotion.

## Focused Verification

- Targeted relic identity regressions: `25 passed, 75 deselected` in 0.81
  seconds.
- Bridge, simulator-adapter, reachable-event-semantics, and relic-evaluator
  selection: `144 passed, 5 skipped` in 9.59 seconds.
- Python bytecode compilation passed for the changed bridge and test module.
- `git diff --check` passed; Git reported only the repository's existing
  LF-to-CRLF checkout warnings.
- Strict validation passed for
  `fix-current-bridge-relic-metadata-identity` and for all 62 OpenSpec items.

The repository `commit` gate passed with `3607 passed, 11 skipped` in 247.19
seconds (250.08 seconds including gate orchestration). No raw full pytest suite
was required or authorized for this repair.
