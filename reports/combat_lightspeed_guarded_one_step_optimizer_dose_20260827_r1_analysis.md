# Guarded one-step optimizer dose result

## Verdict

`no_eligible_arm_stop_current_guarded_one_step_recipe`

Reducing the optimizer budget did reduce parameter drift, but it did not make a
candidate eligible against production r16. The 256-update arm was stronger than
both shorter-dose arms on matched reward, so the recurrent weakness is not
explained by 256-update overtraining alone.

## Technical result

All three arms returned `technical_smoke_ready`. They used the same 51,560 source
transitions, 70,276 prepared replay rows, 848 terminal paired evaluation profiles,
behavior telemetry, replay preparation, and byte-equivalent parent evaluation
rows. Every report, checkpoint, and summary matched its manifest hash.

| Updates | Parameter L2 | Reward vs r16 | HP vs r16 | Candidate-only wins | r16-only wins | Eligible |
| ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 64 | 0.5083 | -0.1528 | -0.5425 | 15 | 21 | No |
| 128 | 0.7791 | -0.1007 | -0.0767 | 9 | 14 | No |
| 256 | 1.2011 | +0.2513 | -0.2099 | 14 | 13 | No |

The 256-update arm passed five of six policy criteria. It failed the required
non-negative HP delta (`-0.2099`). The 64- and 128-update arms failed multiple
aggregate, victory, and late-battle criteria.

## Dose comparison

On the same 848 terminal profiles:

- 128 minus 64: reward `+0.0521`, HP `+0.4658`, victories `13:12`.
- 256 minus 64: reward `+0.4041`, HP `+0.3325`, victories `16:9`.
- 256 minus 128: reward `+0.3520`, HP `-0.1333`, victories `11:5`.

Shorter training preserved the parent parameters more closely, but that smaller
distance did not translate into better held-out decisions. The late-battle
reward delta versus r16 was `-0.2424` at 64 updates, `-0.3869` at 128, and
`+0.5465` at 256.

## Decision

Retain production r16. Do not select an arm, rerun this cohort, tune the update
count, or start gameplay. Stop extending the current guarded one-step recipe;
the next investigation should isolate upstream replay behavior and target-design
interactions before another fit is preregistered.
