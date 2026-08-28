# Action-Relative Conformal Margin Gate Closure

## Decision

Close `add-action-relative-conformal-margin-gate` without fresh LightSTS,
gameplay, qualification, promotion, retry, retraining, seed replacement, alpha
change, family change, threshold change, or sweep.

Production r16 remains authoritative.

## Execution evidence

The first registered execution, r1, stopped before holdout evaluation because
of a tensor/metadata row-filter defect. It produced no output. The failure is
preserved in
`reports/combat_rl_action_relative_conformal_margin_fit_20260829_r1_failure.md`
and r1 was not rerun.

After a focused regression and minimal row-alignment repair, one replacement
r2 execution completed with the original recipe, inputs, seed partitions,
alpha, action families, threshold, and offline gates unchanged.

- r2 source commit: `b881b29ab064c6768d7a3c813f4f0c095303ab0f`
- r2 registration commit: `7fb71ac5a`
- Artifact SHA-256: `8f570984643873779089ad0339869ba1b5ca48b30d87c0316b027967e065c67c`
- Report SHA-256: `b7a2d4403a4487d0c192e78899af83231e8ac8b606bd3f8ae55628a6420b272b`
- Card correction: `7.136387825012207`
- Potion correction: `2.1934895515441895`
- Holdout interventions: `0` (required at least `30`)
- Holdout precision: `0.0` (required at least `0.65`)
- Mean selected true advantage: `0.0` (required above `0.12269661575555801`)
- Mean policy regret: `3.452238082885742` (required below `3.2472479343414307`)
- Severe harms below `-0.5`: `0`
- Illegal selections: `0`
- Forbidden selections: `0`

The fixed 90% corrections achieved their marginal calibration coverage, but
the underlying ensemble raw scores were strongly negatively biased. Applying
the global family corrections therefore converted the candidate into complete
abstention rather than a useful selective policy.

## Authority

- Development artifact only: yes
- Fresh LightSTS gate: not authorized and not run
- Native module loading: not authorized and not run
- Gameplay or CommunicationMod: not started
- Production checkpoint loading or writing: not authorized
- Qualification or promotion: not authorized

## Follow-up boundary

Do not tune the conformal alpha, family corrections, intervention threshold,
or bootstrap multiplier against this holdout. A future candidate needs to
address the residual scorer's systematic calibration/representation error or
use a materially different selective objective before consuming fresh
simulator or real-game validation.
