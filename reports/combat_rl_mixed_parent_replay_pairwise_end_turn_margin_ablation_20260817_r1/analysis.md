# Mixed-Cohort Pairwise Margin Training

## Decision

Authorize one fresh matched zero-epsilon live gate for the mixed-replay
candidate. This is offline eligibility only and does not replace the promoted
parent.

## Training Evidence

The training input combines all 3,856 r1 transitions and 3,255 independently
collected r2 transitions. Each cohort contributes exactly 512 rows to the
1,024-row holdout; the remaining 6,087 rows form the training partition. No
source rows were truncated.

The coarse grid placed weight `0.05` just outside the strict cross-replicate
non-overlap rule. One bounded refinement selected the smallest eligible weight,
`0.055`; weights `0.06` and `0.065` also passed. No further tuning on this
holdout is allowed.

Across three held-out replicates, weight `0.055` met every fixed condition:

| Gate | Candidate | Required | Result |
| --- | ---: | ---: | --- |
| Parent agreement, minimum | 89.26% | at least 88% | pass |
| Positive-energy EndTurn, maximum | 64.92% | below baseline minimum 65.43% | pass |
| Executed-over-EndTurn intervention, minimum | 3.58% | above baseline maximum 3.40% | pass |
| Smooth L1, maximum | 4.494 | at most 110% of baseline max 4.580 | pass |

## Cross-Cohort Check

The final candidate was evaluated independently on both complete source
cohorts. Parent agreement remained 89.99% on r1 and 89.25% on r2. Its
positive-energy EndTurn share was 59.89% and 59.61%, compared with parent values
of 69.67% and 70.32%.

The mixed candidate also generalized better than the prior r1-only candidate:
executed-action agreement improved from 36.15% to 37.19% on r1 and from 32.41%
to 33.64% on r2. Executed-over-EndTurn intervention coverage improved from
5.09% to 7.64% on r1 and from 3.76% to 6.81% on r2. Smooth L1 increased by less
than 1% versus parent on each cohort.

The selected weights-only checkpoint has SHA-256
`5f7afe856eaa69be3e62c9b45a2ab6bc5f321f54ccd58a1de1c0f1d28c95fe63`
and loads through a real CPU `RLAgentV2` in evaluation mode.

## Next Step

Run one 20+20 matched live gate against the promoted parent using a fresh seed
pool. Require the candidate to win more floor pairs, preserve progression and
victory counts, reduce the aligned positive-energy raw-RL EndTurn share, and
complete both arms without runtime failures. Do not promote automatically.
