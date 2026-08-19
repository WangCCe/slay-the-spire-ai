# Production r16 guarded encounter ablation

## Decision

Reject enum-v1 for this production-r16 successor recipe and retain production r16. Do not package or launch either arm.

The technical experiment passed: both arms completed 256 optimizer updates, used identical source and balanced transition counts, excluded the same two decision-bound training profiles, produced no unsupported transitions, and had no nonterminal held-out rows. The enum parent migration preserved all probe actions with maximum Q drift `7.63e-6` under the registered `1e-5` float32 tolerance.

## Matched result

| Comparison | Reward delta | HP delta | Left-only wins | Right-only wins | Battles 6+9 reward |
|---|---:|---:|---:|---:|---:|
| Guarded control vs parent | +2.128 | +1.838 | 65 | 44 | +0.662 |
| Enum vs guarded control | -2.593 | -1.871 | 19 | 48 | -2.438 |
| Enum vs parent | -0.465 | -0.034 | 50 | 58 | -1.776 |

All comparisons contain `856` terminal pairs and exclude zero nonterminal pairs. Enum loses to its matched control at every battle index; battle-9 reward delta is `-3.497`. It also fails five parent-relative criteria, including aggregate reward, victory exchange, late-battle reward, and the material per-battle floor.

## Follow-up

The guarded control is a stronger signal than the enum arm: it improves aggregate reward, HP, victory exchange, and combined battles 6+9 against r16. Under the registration's parent-relative thresholds, its only miss is battle-6 reward `-1.034`, which is `0.034` below the `-1.0` floor. Because this was an ablation control rather than a preregistered promotion candidate, treat it as promising but unconfirmed.

Next, freeze that exact control checkpoint and evaluate it once on a new LightSTS cohort against production r16. Do not retrain, package, or start gameplay before that confirmation.
