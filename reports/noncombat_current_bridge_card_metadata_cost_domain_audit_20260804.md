# Current Bridge Card Metadata Cost-Domain Audit

Date: 2026-08-04

## Decision

The `Injury` failure is one member of a closed card-metadata compatibility
class. The frozen exporter contains 29 card records with an empty `cost`.
Twenty-three records representing 20 stable native card IDs explicitly begin
their description with `Unplayable.`; the Current bridge rejects all 20 IDs as
`card_metadata_cost_invalid` because it accepts integers, `X`, `UNPLAYABLE`,
or `-`, but not the exporter's empty unplayable representation.

A separate narrow repair is justified. It should map only the closed 20-ID
set from exact empty-cost, explicitly unplayable metadata to SpireComm cost
`-2`. It must preserve numeric and `X` costs and continue to reject the other
three empty-cost native identities. This audit does not reopen or retry the
consumed Current baseline study.

## Evidence Identity

- Project commit: `33bd851438842f489731c3cd9e854f0b876b7aa1`.
- Bridge source: 98,600 bytes, SHA-256
  `8037c59a27cd52a562d9db0cf066346e0555875c69fbb5c8979462a38347a714`.
- Frozen metadata: 240,371 bytes, SHA-256
  `e23784ea8ed3092e3bfa9918240e162a9cbcb837badfb53c612eb0d83cc811dc`.
- Simulator commit:
  `7476a81954020087da31d41d16fddf475746ec2d`; `Cards.h` is clean,
  62,887 bytes, SHA-256
  `3492ca9ec6ff3e1098092127892529589be91cb338d3ef44b5fd8e979f52a7e0`.
- Prior card/relic identity audit: 6,196 bytes, SHA-256
  `4835936675f0a6c131ac0dcead73d4d91773a8c9215574a2fb83c150a5379b1a`.
- Terminal study journal and metrics remain bound to
  `card_metadata_cost_invalid` / `Injury`.

The audit parsed only tracked bridge/source text and the hash-bound metadata
JSON. It did not import a native module, construct an environment, access a
seed, run gameplay, or change any source.

## Complete Cost Domain

| Exported cost | Records | Current bridge behavior |
| --- | ---: | --- |
| Integer `0..5` | 672 | Accepted as the integer value. |
| `X` | 20 | Accepted as `-1`. |
| Empty string | 29 | Rejected as `card_metadata_cost_invalid`. |

The 29 empty records split cleanly:

| Class | Metadata records | Stable native IDs | Interpretation |
| --- | ---: | ---: | --- |
| Description starts `Unplayable.` | 23 | 20 | Closed compatibility defect. |
| No unplayable declaration | 6 | 3 | Keep fail closed. |

The explicitly unplayable native IDs are:

`ASCENDERS_BANE`, `BURN`, `CLUMSY`, `CURSE_OF_THE_BELL`, `DAZED`,
`DECAY`, `DEUS_EX_MACHINA`, `DOUBT`, `INJURY`, `NECRONOMICURSE`,
`NORMALITY`, `PAIN`, `PARASITE`, `REFLEX`, `REGRET`, `SHAME`,
`TACTICIAN`, `VOID`, `WOUND`, and `WRITHE`.

The three other empty-cost IDs are `BECOME_ALMIGHTY`,
`FAME_AND_FORTUNE`, and `LIVE_FOREVER`. They are Wish-generated special
options whose metadata does not declare `Unplayable.`; this audit does not
assign them a cost.

## Reachability

The defect is directly relevant to Ironclad A0 own trajectories. Twelve
persistent Curse IDs can enter the run deck under normal event, random-curse,
or relic paths: `CLUMSY`, `CURSE_OF_THE_BELL`, `DECAY`, `DOUBT`, `INJURY`,
`NECRONOMICURSE`, `NORMALITY`, `PAIN`, `PARASITE`, `REGRET`, `SHAME`, and
`WRITHE`. The simulator's Golden Idol branch explicitly obtains `INJURY`,
matching the study blocker. Prismatic Shard can also expose the cross-color
`REFLEX`, `TACTICIAN`, and `DEUS_EX_MACHINA` reward paths.

Combat-generated `BURN`, `DAZED`, `VOID`, and `WOUND` are not normally
persistent run-deck entries, but they belong to the same exact exported
unplayable representation.

## Read-Only POC

A production `MetadataCatalog` over the frozen exporter was called with
production-shaped source card records. All 20 explicitly unplayable IDs and
all three other empty-cost IDs raised `card_metadata_cost_invalid`.

Negative controls passed unchanged:

| ID | Type | Hydrated cost |
| --- | --- | ---: |
| `SLIMED` | Status | 1 |
| `PRIDE` | Curse | 1 |
| `WHIRLWIND` | Attack | -1 |

These controls show why neither a blanket empty-string rule nor a blanket
Curse/Status rule is acceptable.

## Minimal Repair Contract

The repair should be a stable-native-ID-bound table for exactly the 20 audited
IDs. Each entry should validate the exact native display name, empty metadata
cost, metadata type, and leading `Unplayable.` declaration before assigning
SpireComm cost `-2`. Upgraded `Reflex`, `Tactician`, and
`Deus Ex Machina` continue to use the same base native identity and existing
upgrade count.

Required reverse regressions should cover all 20 positive IDs plus:

- `SLIMED` and `PRIDE` retain numeric cost 1;
- `WHIRLWIND` retains `X -> -1`;
- the three Wish option IDs remain blocked;
- unknown IDs, changed names, non-empty drift, changed type, and a missing
  `Unplayable.` declaration remain fail closed;
- source card and metadata bytes remain unmodified.

The repair may improve future bridge compatibility only. It grants no native,
seed, baseline-floor, outcome-support, formal-RL, training, gameplay, model,
OPE, qualification, loading, or promotion authority, and it cannot reinterpret
the terminal baseline-study result.
