# Combat replay cohort gradient alignment

## Finding

The r1, r2, and r3 one-step TD gradients at the promoted parent are strongly
aligned. This rejects cohort-gradient conflict as the explanation for the r6
failure.

| stratum | r1-r2 cosine | r1-r3 cosine | r2-r3 cosine |
| --- | ---: | ---: | ---: |
| all rows | 0.994182 | 0.995601 | 0.993333 |
| terminal | 0.989324 | 0.991355 | 0.982558 |
| nonterminal | 0.993945 | 0.994992 | 0.993819 |

Every leave-one-cohort-out aggregate has positive cosine with its held-out
cohort. For all rows those cosines are `0.994841` to `0.996605`; terminal and
nonterminal strata also remain positive and above `0.9879`.

The full-gradient norms are similar across cohorts (`24.01` to `25.08`).
Terminal rows have larger mean SmoothL1 (`34.28` to `34.92`) and gradient norm
(`53.36` to `54.92`), but their directions still agree. There is no evidence
that one cohort's outcomes demand an update opposite to another cohort.

## Consequence

The r6 degradation is attributable to the optimizer path rather than the
first-order TD direction: four Adam steps apply coordinate-wise preconditioning
and move far enough that the aligned local descent signal no longer predicts
development behavior.

The next candidate experiment may use exactly one deterministic full-dataset
SGD step with a norm-bounded, preregistered step grid. It must retain the same
r3 development gate and reserve a new r4 replay for confirmation. This audit
does not fit or authorize a candidate and does not change the production model.
