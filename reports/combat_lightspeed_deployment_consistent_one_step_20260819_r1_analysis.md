# Deployment-Consistent One-Step Ablation

## Verdict

Retain production r16. One-step TD reduced training scale relative to full discounted returns but still failed the fresh parent gate. The target comparison is diagnostic only because r16 had one decision-bound truncation; it was not rerun.

## Training Evidence

The one-step run retained 51,802 complete-trajectory transitions, balanced them to 69,948 replay rows, and completed 256 optimizer updates. Parameter L2 movement was `1.1354`, mean TD loss was `2.5412`, and mean parent-anchor loss was `0.4895`. Collection recorded 46,603 parent branches, 5,127 exploration branches, and 21,383 guard replacements.

## Fresh Parent Gate

Across 877 matched terminal profiles, candidate-minus-r16 results were reward `-0.2166`, HP `-0.4880`, and candidate-only versus parent-only victories `10:13`. Battle reward deltas were `+0.1432`, `-0.4896`, `-0.4307`, and `-0.0710` for battle indices 0, 3, 6, and 9.

## Target Diagnostic

On the same fresh cohort, one-step exceeded full-return by `+0.2638` reward and `+0.0239` HP with one-step-only versus full-return-only victories `14:12`. This comparison remains diagnostic because r16 had one decision-bound truncation and the runner returned `comparison_not_ready`.

## Implication

Full returns were not the only cause of regression. A structural conflict remains: the parent cross-entropy objective favors the raw parent EndTurn while replay stores the guard-replaced card action on 21,383 rows. The next fresh experiment should isolate that anchor conflict rather than add another target horizon. Do not tune the observed cohorts or load either candidate in gameplay.
