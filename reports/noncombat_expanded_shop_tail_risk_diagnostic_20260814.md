# Expanded Shop Tail-Risk Diagnostic

## Evidence

- Frozen model SHA-256: `5310a7f41e6a2fef0f7db6469dca71c040cb9bd3eb014fd1a34a275fd7db60d0`
- OOF support/result: 496 sources, Current mean regret `0.182371`, gated mean regret `0.167374`, `122` corrected and `92` worsened
- Fresh support/result: 32 sources, Current mean regret `0.156250`, gated mean regret `0.242325`, `7` corrected and `7` worsened
- Fresh manifest: 8 artifacts, all size and SHA-256 checks passed
- Frozen model matched the preflight model byte-for-byte

The seven fresh corrections recovered `0.964912` total regret, while the seven harms added `3.719298`. Seed `95533` alone added `2.017544`: Current removed a card and won, leaving also won, while the unanimous model choice bought Anger and lost on floor 50.

Only `2/496` training sources have a winning Current branch with losing alternatives; the fresh cohort contains one such source. The training corpus therefore has inadequate support for preserving rare Current victories.

## Subsampling POC

Ten deterministic epoch-8 models each trained on a different 347-source subset of the 496-source corpus. On the consumed fresh cohort:

| Vote quorum | Mean regret | Corrected | Worsened | Overrides |
| ---: | ---: | ---: | ---: | ---: |
| 6/10 | 0.224232 | 7 | 6 | 21 |
| 8/10 | 0.226425 | 3 | 3 | 10 |
| 10/10 | 0.165570 | 0 | 1 | 2 |

Seed `95533` still received 9/10 votes for Anger, so data-subsampling uncertainty does not provide a useful safety gate.

## Decision

Stop candidate-only, state-conditioned, Current-relative, confidence-margin, initialization-ensemble, and subsampling-ensemble shop root-ranker variants on this evidence. Do not tune against the consumed fresh cohort or collect another uniform shop corpus for the same objective. The next learning proposal should operate on successor/trajectory transitions with conservative downside or victory-risk treatment, rather than fitting one terminal scalar directly to the root shop action.
