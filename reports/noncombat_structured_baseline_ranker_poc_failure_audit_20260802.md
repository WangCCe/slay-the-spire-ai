# Structured Baseline-Ranker POC Failure Audit

## Conclusion

The registered train-only POC is a deterministic valid negative. The
structured candidate MUST NOT advance to a fresh simulator study: held-out
multi-candidate agreement fell from `70.00%` to `67.82%`, macro category
agreement fell by `7.89` percentage points, and mean cross entropy worsened by
`0.1924`. The primary and replay execution hashes are identical, no model was
selected, and every downstream authority remains false.

The negative aggregate result hides one useful but insufficient signal. The
structured route head improved agreement by `11.00` points on all 300 route
choices, and card reward improved by `2.32` points. Separate event and shop
heads regressed by `16.67` and `28.23` points respectively. A unified
structured replacement is therefore rejected; any later POC should preserve
the strong legacy event/shop behavior and test only a bounded residual or
hybrid correction on route/card.

## Bound Evidence

- Registration SHA-256:
  `3a9aca0175bec6dddbeb17b96044c405c8e8e3b3486fc0f46f1c3ff3e126b49a`
- Train dataset SHA-256:
  `86cf82f7833ca6b7d3f4e58967f5768ef7292a2297d06af01819b783526227d0`
- Primary/replay execution SHA-256:
  `c5c8294715c1006af285ff22a335c94e7ddd752608065561016b869d6617368b`
- Predictions SHA-256:
  `a29f00aa7b6ae4e43396796a5691ff77392f9cda4e0455592ab7915b97763005`
- Rows: 1,291 total, 870 multi-candidate, 421 singleton excluded from
  fitting and competence gates.
- Execution time: 121.61 seconds primary and 120.14 seconds replay, each below
  the registered 900-second bound.

No validation/final row, native module, new seed, policy rollout, live game,
checkpoint, reward, floor, victory, Current label, or Bottled label was used.

## Fold Stability

The canonical predictions retain each row's fold. Recomputing the registered
metrics from those rows gives:

| Fold | Rows | Overall delta | Macro delta | CE delta | Card delta | Event delta | Route delta | Shop delta |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 293 | +0.037543 | -0.018088 | +0.184609 | +0.128440 | -0.166667 | +0.101010 | -0.135135 |
| 1 | 177 | -0.045198 | -0.109375 | +0.208567 | +0.000000 | -0.193548 | +0.193548 | -0.437500 |
| 2 | 252 | -0.107143 | -0.148785 | +0.191549 | -0.113636 | -0.222222 | +0.010989 | -0.270270 |
| 3 | 148 | +0.033784 | -0.034340 | +0.189793 | +0.056604 | -0.068966 | +0.208333 | -0.333333 |

The structured candidate improved overall agreement in only two folds. More
importantly, macro agreement was lower and cross entropy was higher in every
fold. Route agreement improved in all four folds; event and shop agreement
regressed in all four. Card reward was mixed, with one material negative fold.
This pattern rules out treating the aggregate miss as one unlucky split.

## Error Shape

Correctness overlap further separates useful structure from head collapse:

| Category | Both correct | Legacy only | Structured only | Both wrong |
| --- | ---: | ---: | ---: | ---: |
| card_reward | 158 | 44 | 51 | 49 |
| event | 111 | 28 | 4 | 1 |
| route | 171 | 29 | 62 | 38 |
| shop | 33 | 35 | 0 | 56 |

The shop head predicted `leave` on all 124 held-out decisions. The teacher
targets were 44 card buys, 3 relic buys, 44 removals, and 33 leaves, so its
`26.61%` agreement is exactly the leave frequency. It recovered no decision
that the legacy control missed. The event head predicted option 0 on 134/144
rows versus 109/144 teacher targets and failed to predict any option 2 target.
These are category-head majority collapses, not evidence that structured shop
or event features are ready.

Route is materially different: structured recovered 62 rows missed by legacy
while losing 29 legacy-correct rows. Its accuracy improvement is stable, but
route cross entropy still worsened in every fold. Card reward has complementary
errors but less stable fold behavior and worse cross entropy. The current POC
therefore supports a route/card residual hypothesis, not direct category-head
promotion.

## Integrity Audit

- The 32 train seeds are partitioned once by sorted round-robin assignment; all
  decisions for a seed remain in its fold, and every fold covers all four
  categories.
- Legacy and structured predictions cover the same 870 unique
  `(seed, decision_index)` keys and preserve every candidate id in adapter order.
- Feature invariance, leakage exclusion, candidate integrity, deterministic
  model serialization, grouped folds, metric math, and atomic publication are
  covered by focused synthetic regressions.
- The structured projection used 825 unique feature keys in 690/2,048 bins,
  with a descriptive collision fraction of `16.36%`. This was observed only
  after registration and does not authorize a hash-width retry.
- The exact eight-file published inventory contains seven canonical files plus
  one noncanonical timing journal. `models.json` has only fold-model hashes;
  selected model and selected-model hash are null.
- The registration and canonical manifest keep DAgger, formal RL, native
  collection, simulator rollout, live gameplay/loading, OPE reinterpretation,
  qualification, and promotion authority false.

The v1 canonical report materializes aggregate and category metrics but omits
the per-fold table even though `predictions.json` records fold identity and the
execution computed fold metrics. This audit supplies the deterministic
reconstruction and records a reporting-completeness defect. It does not affect
the negative verdict because macro agreement and cross entropy fail in all four
folds. Do not mutate the canonical result or rerun the registered cohort to
repair presentation.

## Next Gate

Do not preregister a fresh policy-quality study and do not start formal RL. A
new OpenSpec may define at most one train-only residual/hybrid POC with these
boundaries:

1. Freeze legacy behavior for event and shop; no new category-specific
   replacement head may override those actions.
2. Treat the legacy candidate score as the base and learn a small route/card
   residual, preserving the complete candidate set and original tie behavior.
3. Require route and card agreement plus cross entropy to improve separately,
   and require every fold to avoid macro/CE regression; singleton rows remain
   excluded.
4. Use only the same already observed train corpus for implementation fit, make
   no quality claim, and permit no alternate retry after observation.
5. Only if that residual passes may a separate change preregister entirely new
   train/validation/final simulator cohorts. DAgger remains deferred until
   teacher-state multi-choice fit is credible but independent rollout fails.

If a bounded residual cannot pass, stop baseline imitation work and revisit the
simulator state/action representation or the role of SimpleAgent supervision
before spending fresh evidence.
