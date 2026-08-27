# Inventory Embedding Live Trace Audit

## Decision

Stop the inventory-only candidate line. The five seeds with different raw `RL returned` strings do not provide a positive training label for another near-neighbor candidate.

## Result

- Three seeds contain a deployed action difference from the same retained combat state.
- All three differences are locally neutral: the compared action sequences converge to the same turn result.
- Two seeds reflect trajectory drift without a preceding different deployed action in a shared state.
- Zero seeds show an attributable local outcome improvement or regression.

## Evidence classification

| Seed | Classification | Retained evidence |
| --- | --- | --- |
| `DB4B1E55CDB02` | Environment trajectory drift | Actions match through `Infernal Blade`; the generated card is then `Whirlwind` versus `Cleave`. This is the only pair with HP/damage run-record differences, but floor and death cause tie. |
| `A205DB5D43F62` | Environment trajectory drift | Per-turn deployed action sequences match. A later hand differs before the same `Pommel Strike+`; run records differ only in metadata. |
| `E502A513C4DE9` | Same-state, locally neutral | On floor 22 turn 4, card order differs but both arms leave Snecko at 38 HP with 1 energy and 5 block. An earlier raw potion difference is fully neutralized by `POTION_SAVE_GUARD`. |
| `A5ECC29C8587B` | Same-state, locally neutral | `Strike -> Bash+` versus `Bash+ -> Strike`; both kill the 18 HP Cultist that turn. |
| `B6CCD2000B0C1` | Same-state, locally neutral, guard-mediated | Candidate and `ENERGY_GUARD` choose different first Louse targets; both kill both enemies with three Strikes that turn. |

## Method and limits

The audit assigns trace rows to the most recent per-arm seed marker, compares complete combat state snapshots before deployed actions, and checks the paired `.run` records. `RL returned` is treated as model output, while the decision trace and `CALLBACK Got action` represent the action actually sent after guards.

This is a read-only postmortem of ten matched pairs. It can reject the claim that the observed raw differences demonstrate candidate benefit; it cannot estimate a general treatment effect or prove the source of environment trajectory drift.

## Next direction

Do not train on these raw mismatches as preferred-action labels. The next candidate should target repeated deployment-relevant errors visible in retained replay, such as guard interventions or boss-preparation failures, and must be materially different from the inventory-only update before another live cohort is spent.
