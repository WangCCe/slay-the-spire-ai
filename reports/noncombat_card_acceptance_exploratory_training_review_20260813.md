# Card-Acceptance Exploratory Training Review

## Scope

This review covers five complete exploratory training chunks on the already
consumed development cohort `1000..1031` plus `2000..2031`. It does not use the
protected holdout, canary, qualification, promotion, gameplay, or production
loading authority.

## Result

- The vectorized cross-fitted baseline reduced real chunk update time from
  `1771.547s` in chunk 1 to `10.140s` in chunk 2, a `174.7x` reduction. The next
  two updates remained at `10.214s` and `9.803s`.
- Rollout collection is now the dominant cost at `508.6s` to `538.2s` per
  64-pair chunk. A complete chunk now takes about nine minutes instead of about
  38 minutes.
- Training reached five complete chunks, `320` pairs, `640` environment
  accesses, `10` optimizer steps, and `14,777` decisions with no unsupported
  episodes.
- The registered stop rule fired after chunk 4. Candidate greedy family counts
  changed from `333 take / 91 skip` in chunk 0 to `1800 take / 0 skip` across
  the trailing four chunks.

## Frozen Development-Cohort Comparison

The zero-step candidate and control were identical: mean floor progress
`0.223410`, with `352 take / 110 skip` card decisions and zero victories.

After training:

| Arm | Mean floor | Change from zero-step | Per-seed change | Card families |
| --- | ---: | ---: | --- | --- |
| Candidate | `0.253564` | `+0.030154` | 24 positive, 26 equal, 14 negative | 533 take, 0 skip |
| Control | `0.260965` | `+0.037555` | 28 positive, 25 equal, 11 negative | 544 take, 0 skip |

The final candidate-control paired mean floor difference was `-0.007401` on
the same development cohort. Both arms had zero victories and zero unsupported
episodes. Bootstrap bytes were unchanged by both frozen evaluations.

## Matched-State Diagnosis

A fixed zero-step candidate policy generated 108 card-reward source states over
16 consumed development seeds. On those exact states, zero-step candidate and
control mean take probability was `0.5011`, with `73 take / 35 skip` greedy
families. After the first update, candidate mean take probability was only
`0.5085`, but every greedy family was take. The final candidate mean was
`0.5146`, again with `108 take / 0 skip`.

The stop therefore detected a greedy decision-boundary collapse, not a
low-entropy probability collapse. Raising the entropy coefficient is not a
mechanism-backed response: the family distribution remained close to 50/50
while a small common margin shift changed every deterministic decision.

## Decision

The training loop is operational and its update throughput is no longer the
iteration bottleneck. The development cohort shows a positive training signal,
but the candidate architecture did not beat the control and both policies
collapsed to the `take` family. This is a no-go for holdout, qualification, or
promotion.

Keep the saturation boundary unchanged and do not spend a new holdout or
continue from the saturated checkpoint. The next pilot should replace random
non-card behavior with the native SimpleAgent baseline, use a card-policy warm
start, train only the card residual, and compare against a frozen native
SimpleAgent control. This directly tests card learning on competent trajectories
without treating SimpleAgent labels as reward or permanent ground truth.
