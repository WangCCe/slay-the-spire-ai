# Action-Relative Uncertainty Ensemble Error Audit

## Scope

This read-only audit reloaded the committed r16 simulator shadow, the bound
evaluation corpus, and artifact
`6789aa2e00792b9001772aeb450f60bebbf1cb8b647f14b6fab4d9771ec5dc28`.
It did not fit a model, change a threshold, run LightSTS, or start gameplay.

## Findings

- The ensemble made 38 holdout interventions: 17 had true advantage at least
  0.5, 7 were in `[0, 0.5)`, 11 were in `[-0.5, 0)`, and 3 were below `-0.5`.
- True-advantage quantiles were: minimum `-5.999053`, p10 `-0.435722`, p25
  `-0.055755`, median `0.294913`, p75 `3.068334`, p90 `12.726595`, maximum
  `36.648155`.
- The binary precision failure is mostly a margin-calibration problem: 18 of
  the 21 sub-threshold interventions were within 0.5 return units of zero.
- The material tail failure was seed `263037`, Blue Slaver, floor 14, turn 0.
  The guard action was 19; the candidate selected action 66, which uses the
  second potion slot without a target. That slot contained Gambler's Brew. The
  ensemble mean was `1.309771`, sample standard deviation `0.639234`, and LCB
  `0.670538`, while the true relative advantage was `-5.999053`.
- Action 66 was selected 8 times with 0.50 precision and mean true advantage
  `2.051432`; action 18 was selected 3 times with zero precision and mean true
  advantage `-0.306008`. Errors are not isolated to one encounter or one
  action family.

## Decision

Bootstrap disagreement reduced intervention volume and improved aggregate
value, but `mean - sample_std` was not a calibrated lower bound. The next
candidate should not sweep its confidence multiplier. It should fit on a
seed-level subset of the existing training corpus, reserve a disjoint internal
calibration subset, and apply a fixed one-sided conformal correction separately
to card and potion alternatives before touching the existing evaluation
corpus. The future gate should preserve the prior coverage and precision
requirements and add zero severe harms below `-0.5`.
