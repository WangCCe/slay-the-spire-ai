# Guard-aware bootstrap comparison result

## Verdict

`reject_guard_aware_bootstrap_current_guarded_three_step_recipe`

The deployment-guard bootstrap implementation worked as registered, but the
candidate was worse than both the raw-greedy n-step control and production r16.
Retain r16. Do not rerun, tune this cohort, start a larger simulator
confirmation, or enter gameplay on the strength of this result.

## Technical result

Both arms returned `technical_smoke_ready`. All six report, checkpoint, and
summary artifacts matched their manifest sizes and SHA-256 hashes. The arms had
the same 51,536 source transitions, 67,020 prepared replay rows, behavior
telemetry, replay preparation, initialized parent, and byte-equivalent parent
evaluation rows. Both performed 256 optimizer updates and produced 853 terminal
matched evaluation profiles with no unsupported states.

The guard-aware path was materially exercised:

- 51,536 target-policy actions with 23,680 deployment-guard replacements.
- 48,139 aligned bootstrap actions with 22,175 guard replacements.
- The target action identity was bound as
  `1c333ab804247cbf5a2049f1c0b1efd54ecc5c711f48f1eab05e3d9af5b205dc`.
- Raw-max minus guarded-action Q was finite and non-negative, with mean `0.8599`
  and maximum `6.6302`.
- Mean bootstrap value fell from `9.8086` in the raw control to `9.0138` in the
  guard candidate; mean transformed target reward fell from `12.3760` to
  `11.7572`.

## Policy result

| Comparison | Reward delta | HP delta | Candidate-only wins | Comparator-only wins | Battle 6+9 reward |
| --- | ---: | ---: | ---: | ---: | ---: |
| Raw n-step control vs r16 | +0.1495 | -0.1008 | 14 | 9 | n/a |
| Guard candidate vs raw control | -0.4222 | -0.1594 | 2 | 9 | -0.8941 |
| Guard candidate vs r16 | -0.2727 | -0.2603 | 8 | 10 | -0.6009 |

The guard candidate's reward delta versus the raw control was `-0.0120` at
battle 0, `-0.1668` at battle 3, `-0.8339` at battle 6, and `-0.9751` at battle
9. Against r16 it was `+0.1037`, `-0.1911`, `-0.5199`, and `-0.7098`
respectively. It failed aggregate reward, HP, victory, late-battle, and
no-severe-stratum criteria against both comparators.

## Decision

The hypothesized target-policy mismatch is real and large, but correcting it by
directly gathering the frozen parent's guarded action value degrades the later
battles under the current guarded, anchored, three-step recipe. This rules out a
larger confirmation of this candidate and further same-cohort target tuning.

The next investigation should leave this recipe: either improve the data or
state representation, or separately calibrate LightSTS against real-game combat
transitions to identify which simulator differences matter before another fit.
