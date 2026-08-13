# Card-Only Native-Baseline RL Pilot r7 Postmortem

## Decision

The pilot proved that the card-only optimizer can execute real updates against
the rollout-owning runtime, but it did not produce a measurable outcome change
on the consumed development cohort. Do not promote the checkpoint or launch a
fresh qualification from this result.

The next experiment should spend its budget on a longer, explicitly bounded
training schedule with behavior-sensitivity diagnostics. It should not repeat
r7, tune against the r7 comparison, or expand review and full-suite work.

## Executed Pilot

- Four candidate-only residual updates completed.
- Training attempted 256 paired episodes and retained 250 supported pairs.
- One or two pairs per chunk hit only the registered Courier-restock blocker.
- The run consumed 512 training and 128 frozen-comparison environment accesses.
- The fixed source-state probe stayed within the 5%-95% family-coverage bound.
- No production checkpoint, game process, or CommunicationMod state changed.

| Chunk | Supported pairs | Censored pairs | Candidate floor | Control floor |
| --- | ---: | ---: | ---: | ---: |
| 0 | 63 | 1 | 0.3570 | 0.3768 |
| 1 | 62 | 2 | 0.3673 | 0.3783 |
| 2 | 63 | 1 | 0.3528 | 0.3768 |
| 3 | 62 | 2 | 0.3463 | 0.3783 |

## Behavioral Result

The warm-start checkpoint and final checkpoint produced identical aggregate
outcomes on the same 64 attempted comparison seeds:

| Checkpoint | Candidate floor | Control floor | Candidate wins | Control wins | Take rate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Warm start | 0.363213 | 0.374178 | 1 | 0 | 0.465636 |
| After four RL updates | 0.363213 | 0.374178 | 1 | 0 | 0.472509 |

The update changed the aggregate greedy family count by four decisions out of
582 multi-family card decisions, but it changed neither floor progress nor
victories. This is insufficient behavioral movement, not evidence that RL
degraded the policy.

## Learning Signal Diagnostic

A no-update replay of the first training cohort retained 63 supported pairs and
566 candidate card decisions. It confirmed nonzero gradients and preserved the
input checkpoint byte-for-byte.

- Advantage mean: `0.037787`; population standard deviation: `0.206883`.
- Positive/negative decisions: `329 / 237`.
- Baseline predictions clipped at zero: `133 / 566` (`23.5%`).
- Total family-head gradient L2: `0.013334`.
- Total conditional-head gradient L2: `0.007102`.
- Seed-level mean card advantage versus paired floor difference correlation:
  `0.175992`.
- Bowl support was only four decisions and all four advantages were negative.

The estimator is producing usable, nonzero policy gradients, but the signal is
noisy, unevenly supported across families, and only weakly aligned with paired
candidate-control outcome differences. Four optimizer steps are too few to
establish a useful behavior change.

## Comparison Gate Defect

The r7 comparison classified any unsupported arm as a hard failure while the
registered cohort deterministically reaches the already-declared Courier
blocker. Training already censored the whole affected pair within a fixed
eight-pair bound. The old comparison gate was therefore structurally unable to
pass on its own registered cohort.

The corrected contract applies the same bounded pair-level censoring to the
frozen comparison, computes all metrics only over complete supported pairs, and
still fails closed for unknown blockers, more than eight censored pairs, or
fewer than 56 supported pairs. Historical r7 artifacts retain their original
schema and verdict; they are not retroactively reclassified.

## Next Experiment Requirements

1. Pre-register a longer candidate-only training schedule on development data,
   with no protected or fresh evaluation access.
2. Report action-flip count, policy KL, family support, advantage clipping, and
   supported paired outcome deltas at fixed checkpoints.
3. Require a meaningful but non-collapsed behavior change before spending a
   fresh cohort; unchanged outcomes after the longer schedule remain a no-go.
4. Keep native SimpleAgent as the rollback policy and keep all checkpoints out
   of production discovery.

## Evidence

- `reports/noncombat_card_only_native_baseline_rl_pilot_20260813_r7/`
- `reports/noncombat_card_only_advantage_diagnostic_20260813_r1.json`
  (`bb202a40afb988cf6f2301405620757853260bc8f906dc861a27fb0d229bd086`)
- `reports/noncombat_card_only_warm_start_frozen_comparison_20260813_r1.json`
  (`e863fa5aa13c20a5549316daaaf8b8390710eeab77138fe27d69070bab233b6f`)
