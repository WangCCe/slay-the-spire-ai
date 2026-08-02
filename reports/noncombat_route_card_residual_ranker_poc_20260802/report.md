# Non-Combat Route/Card Residual-Ranker POC

- Verdict: `poc_valid_without_route_card_residual`
- Selected candidate: `None`
- Evidence class: `observed-train-only terminal implementation fit`
- Policy-quality claim: `false`
- Registration SHA-256: `eaf3e5f493d1686ca2cbff87571eee5ed1fa375c5e364a7d7d9cf7c568677676`
- Train dataset SHA-256: `86cf82f7833ca6b7d3f4e58967f5768ef7292a2297d06af01819b783526227d0`

## Multi-Candidate Held-Out Metrics

| Metric | Legacy control | Residual candidate | Delta |
| --- | ---: | ---: | ---: |
| Overall agreement | 0.700000 | 0.701149 | +0.001149 |
| Macro category agreement | 0.712301 | 0.713135 | +0.000833 |
| Overall cross entropy | 0.989680 | 0.988808 | -0.000872 |

## Category Metrics

| Category | Rows | Control agree | Candidate agree | Agree delta | CE delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| card_reward | 302 | 0.668874 | 0.668874 | +0.000000 | -0.001006 |
| event | 144 | 0.965278 | 0.965278 | +0.000000 | +0.000000 |
| route | 300 | 0.666667 | 0.670000 | +0.003333 | -0.001516 |
| shop | 124 | 0.548387 | 0.548387 | +0.000000 | +0.000000 |

## Per-Fold Gate Evidence

| Fold | Rows | Overall agree delta | Macro agree delta | Overall CE delta | Card agree delta | Card CE delta | Route agree delta | Route CE delta | Pass |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 293 | +0.003413 | +0.002525 | -0.000852 | +0.000000 | -0.001045 | +0.010101 | -0.001371 | pass |
| 1 | 177 | -0.005650 | -0.004032 | -0.000860 | +0.000000 | -0.000995 | -0.016129 | -0.001621 | fail |
| 2 | 252 | +0.000000 | +0.000000 | -0.000850 | +0.000000 | -0.000960 | +0.000000 | -0.001427 | pass |
| 3 | 148 | +0.006757 | +0.005208 | -0.000961 | +0.000000 | -0.001010 | +0.020833 | -0.001848 | pass |

## Terminal Checks

- aggregate_card_reward_agreement_improvement: `fail`
- aggregate_card_reward_cross_entropy_improvement: `fail`
- aggregate_route_agreement_improvement: `fail`
- aggregate_route_cross_entropy_improvement: `fail`
- all_fold_nonregression: `fail`
- base_immutable: `pass`
- event_shop_delegation_exact: `pass`
- macro_agreement_improvement: `fail`
- overall_agreement_improvement: `fail`
- replay_identity: `pass`
- residual_bound: `pass`

## Delegation And Residual

- Event/shop delegation exact: `true` across 268 rows
- Residual candidate logits: 1894
- Residual max absolute correction: 0.011595
- Residual mean absolute correction: 0.002253
- Residual RMS correction: 0.002917

## Data Strata

- Multi-candidate rows: 870
- Singleton rows excluded from fit/gate: 421
- Total train rows: 1291

## Boundaries

- No validation or final-test row contributed to features, fitting, thresholds, selection, or metrics.
- No native simulator, new seed, rollout, floor, victory, live game, checkpoint, outcome, or reward was used.
- Event and shop use exact shared-base outputs; all legal candidates remain available.
- A positive verdict authorizes only a separate fresh-study proposal.
- A valid negative ends model trials on this corpus.

## Authority

- dagger: `false`
- formal_noncombat_rl: `false`
- live_gameplay: `false`
- live_policy_loading: `false`
- native_evidence_collection: `false`
- ope_reinterpretation: `false`
- policy_promotion: `false`
- policy_quality: `false`
- qualification: `false`
- simulator_rollout: `false`
