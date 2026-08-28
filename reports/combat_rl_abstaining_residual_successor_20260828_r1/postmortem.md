# Abstaining Residual Successor R1 Postmortem

## Scope

This is a read-only diagnostic of the closed R1 adapter. It does not refit the
adapter, change the fixed `0.90` gate threshold, authorize another attempt, or
turn the development cohort into a holdout.

## Gate Separation

The gate learned some direct-versus-changed separation, but not enough to make
the registered hard correction callable or reliably selective.

| Partition | Direct mean | Changed mean | Gate AUC | Direct max | Changed max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Training | 0.4398 | 0.5742 | 0.7860 | 0.7488 | 0.8137 |
| Validation | 0.5178 | 0.5932 | 0.7024 | 0.7017 | 0.7898 |

No row reached the fixed `0.90` threshold. The validation distributions also
overlap materially: the direct median was `0.5341`, while the changed first
quartile was `0.5433`.

## Forced-Open Diagnostic

Applying the learned residual to every row is not an alternative candidate; it
is only a diagnostic of what the correction head learned behind the closed
gate.

| Validation metric | Parent / hard gate | Forced open |
| --- | ---: | ---: |
| SMDP TD | 5.8455 | 5.7961 |
| Changed executed-action agreement | 0.0% | 41.4% |
| Direct action disagreement | 0.0% | 54.1% |
| Overall action disagreement | 0.0% | 82.6% |

The forced residual recovers part of the changed-proposal label signal and
slightly improves validation TD, but it also changes more than half of direct
decisions. On the training partition, forced-open TD slightly worsens from
`5.9311` to `5.9411`. The residual therefore lacks direct-policy selectivity;
the failure is not merely a high-threshold calibration issue.

## Decision

- Do not lower the threshold, add updates, or retry on this cohort.
- Do not advance the adapter to a fresh holdout or gameplay evaluation.
- Do not treat moderate gate AUC or forced-open changed agreement as policy
  quality evidence.
- Keep production r16 authoritative.

The next correction architecture should first demonstrate both gate
separability and direct-policy stability on a larger cheap offline source that
is independent of this closed cohort. A new live collection is premature until
that mechanism evidence exists.
