# Real-Context-Weighted Action-Relative Fit Postmortem

## Decision

Close the current-state item-semantic three-class classifier family. Do not
change its threshold, add an item blacklist, rerun its fit, or enter LightSTS
policy or real-game gates.

The next bounded experiment should test action-relative one-step successor
deltas as a materially different representation. It should compare the same
source state and action identities with versus without candidate-minus-guard
successor features on one new seed-disjoint corpus.

## Bound Evidence

- Fit report:
  `reports/combat_rl_real_context_weighted_action_relative_fit_20260829_r2/report.json`
- Artifact SHA-256:
  `7865b9641ac207c6ac2af5f02f8a37d2068331c697c05febdbea1adbb4e0fb1c`
- Fresh source rows: `10,688`
- Selection threshold: `2.805296`
- Raw interventions: `2,004`
- Raw severe harms: `481`
- Weighted precision: `0.364190`
- Weighted mean selected advantage: `-0.001950`
- Weighted mean regret: `2.789485`
- Gate decision: `offline_failed_close_without_fresh_gate_or_sweep`

The postmortem reloaded the frozen development artifact and already-consumed
fresh corpus, reproduced selection without optimizer updates, and grouped true
branch-minus-guard advantages. It did not fit, tune, run LightSTS policy, start
Slay the Spire or CommunicationMod, or change any artifact.

## Failure Distribution

| Group | Interventions | Severe | Beneficial | Precision | Mean advantage |
|---|---:|---:|---:|---:|---:|
| Card | 1,414 | 404 | 504 | 0.356 | -0.337 |
| Potion | 590 | 77 | 250 | 0.424 | 2.276 |
| Floors 0..10 | 505 | 151 | 215 | 0.426 | -0.479 |
| Floors 11..17 | 539 | 118 | 193 | 0.358 | 0.517 |
| Floors 18..22 | 468 | 103 | 175 | 0.374 | 1.001 |
| Floors 23..27 | 234 | 51 | 88 | 0.376 | 0.253 |
| Floors 28..34 | 258 | 58 | 83 | 0.322 | 1.170 |
| HP quartile 0 | 63 | 12 | 16 | 0.254 | 0.143 |
| HP quartile 1 | 234 | 55 | 84 | 0.359 | 0.035 |
| HP quartile 2 | 633 | 132 | 245 | 0.387 | 1.312 |
| HP quartile 3 | 1,074 | 282 | 409 | 0.381 | 0.017 |

Evidence margin also fails to isolate safety:

| Evidence above threshold | Interventions | Severe | Precision | Mean advantage |
|---|---:|---:|---:|---:|
| 0..1 | 632 | 170 | 0.367 | 0.371 |
| 1..3 | 742 | 177 | 0.367 | 0.170 |
| 3..6 | 475 | 113 | 0.377 | 0.487 |
| 6+ | 155 | 21 | 0.458 | 1.770 |

The largest item cluster is `Defend`: 499 interventions, 152 severe harms,
precision `0.373`, and mean advantage `-1.439`. It explains only 31.6% of all
severe harms, so an item veto cannot repair the family. Other negative clusters
include `Strike` (19 severe, mean `-3.456`), `Disarm` (11, `-3.091`), `Rage`
(10, `-2.567`), `Seeing Red` (8, `-2.582`), and `Havoc` (10, `-2.222`).

## Interpretation

Real-context weighting improves distribution alignment and lowers weighted
regret, but it does not make the current representation action-causal. The
model sees the frozen current-state latent and item/action identity; it does
not observe the state produced by playing the candidate relative to the state
produced by the guard action. Broad failures across floors, HP, item families,
and high evidence margins are consistent with that missing representation.

The next experiment should collect candidate and guard one-step successor
states alongside the existing paired continuation returns. A fixed ablation
can then test whether candidate-minus-guard successor latent, immediate reward,
and terminal disposition improve fresh severe-harm separation. Failure should
close learned post-guard takeover for this corpus family and return effort to
the parent combat policy or simulator mechanics rather than another residual
head.
