# Abstaining Residual Successor R1

## Decision

`fixed_residual_fit_failed_cohort_closed`

The fixed 128-update CPU fit completed, but the hard abstention gate never
opened on either the training or validation partition. The result is not
eligible for a fresh holdout. Production r16 remains authoritative, and this
cohort is closed to retry, threshold changes, extra updates, or tuning.

## Evidence

- Input checkpoint: `ba02c749e73caecae59469220abe30e40e826699e95ca910a8b18d7eaa1f5900`
- Runner source: `03eada0032b1cf1b2f1788bbc27c1916813d8c3a`
- Runner supplement: `bfdf10ff18b5ba3649c6ddbc093cec003dc64df3c8e3045865f8dd6df2d3026c`
- Optimizer updates: `128`; every batch contained exactly `32` direct and
  `32` changed-proposal decision spans.
- Frozen parent remained byte-identical and the adapter artifact round trip
  was exact.
- Validation parent/candidate SMDP TD: `5.845464706420898` /
  `5.845464706420898`.
- Validation action disagreement: `0.0`; direct disagreement: `0.0`.
- Validation direct/changed gate-open share: `0.0` / `0.0`.
- Validation gate probability maximum: `0.789802253246307`, below the fixed
  `0.90` threshold; training maximum was `0.813677668571472`.
- Changed-proposal executed-label agreement uplift: `0.0`.
- Positive-energy End Turn delta: `0`.
- Adapter SHA-256: `41dd133a39aec2959027fd9ffcb3b90fbe44f19d690b9d34276df42bd46e85c8`.
- Report SHA-256: `ebbf89033c501f5278d9e68ae12e6291b11def6b9d62f1a8a872e6592072305c`.

## Interpretation

The correction parameters moved and the gate/action training losses decreased,
but the registered recipe did not produce any callable hard-gated correction.
Because candidate behavior stayed identical to the parent, the result failed
validation TD improvement, material disagreement, changed gate coverage, and
changed-label uplift. These are policy-bearing failures, not serialization,
provenance, callability, or parent-integrity failures.

No fresh holdout, gameplay evaluation, qualification, promotion, production
loading, or policy-quality claim is authorized by this result.
