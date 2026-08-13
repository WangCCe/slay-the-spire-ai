# Event Option Counterfactual Ranking Closeout

## Verdict

`event_counterfactual_ranker_ready_for_shadow_evaluation_proposal`

The fixed event ranker experiment passed every preregistered development gate.
This permits one disjoint, no-training shadow evaluation. It does not authorize
production policy loading, promotion, gameplay, or same-cohort tuning.

## Evidence

- Train: 245 complete sources, 106 informative sources, 25 event ids, and 11
  registered Courier censors from seeds `94100..94227`.
- Development: 59 complete sources, 23 informative sources, 19 event ids, and 1
  registered Courier censor from seeds `94228..94259`.
- Train-only selection chose epoch 1 and confidence threshold `0.50`.
- Current development mean/p95/max regret: `0.024383 / 0.263158 / 0.298246`.
- Learned development mean/p95/max regret: `0.014868 / 0.157895 / 0.298246`.
- Raw weighted pairwise accuracy improved from untrained `0.398907` to
  `0.726776`.
- The learned policy changed 37 of 59 decisions: 6 corrected and 5 worsened.

All ten fixed support, ranking, regret, and change gates passed. Improvements
were concentrated in Golden Idol, Golden Wing, and The Cleric. Regressions
included Shining Light and World of Goop and remain a shadow-evaluation risk.

## Confidence Limitation

The selected threshold does not provide a useful conservative fallback. All 37
learned disagreements had sigmoid score confidence between `0.500246` and
`0.506015`: threshold `0.50` accepts all of them, while every registered
threshold at or above `0.55` accepts none. The gated and raw policies were
therefore identical on development. Fresh evaluation should test the bound raw
policy as-is; confidence calibration requires a later design if the model
otherwise replicates.

## Integrity

- Development access count was exactly one.
- Six manifest-bound artifacts matched their byte sizes and SHA-256 identities.
- Train and development datasets round-tripped byte-for-byte.
- The selected model state restored and re-encoded exactly.
- Focused shared/event tests passed: `19 passed in 8.61s`.
- Strict OpenSpec validation passed.

## Next Step

Run one preregistered no-training shadow evaluation on a disjoint fresh seed
cohort. Require support and event diversity, mean-regret improvement, p95/max
noninferiority, at least one correction, and corrections not outnumbered by
regressions. A failed gate ends this model; it must not trigger tuning on the
fresh cohort.
