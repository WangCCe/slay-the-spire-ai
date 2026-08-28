# Combat RL Candidate Callability Successor R1

## Decision

The fixed 64-update candidate is not eligible for a fresh holdout. Production
r16 remains authoritative, this corpus is closed to further fitting, and the
next architecture investigation is a residual or separate head.

## Technical Gates

- Validation SMDP TD improved from `7.601144` to `7.584513`.
- Overall parent disagreement was `62.41%`, above the `5%` materiality floor.
- Changed-proposal executed-label agreement improved from `0%` to `33.33%`,
  above the `10` percentage-point uplift floor.
- Positive-energy End Turn selections decreased by 69, so the safety delta
  passed.
- Direct parent disagreement was `21.67%`, above the fixed `10%` ceiling. This
  is the only failed technical condition.

## Integrity

- Exactly 64 optimizer updates ran on CPU.
- Every batch contained 64 direct and 64 changed-proposal spans; no
  no-proposal or unknown row was sampled independently.
- All 1,634 source rows and 632 candidate-decision spans reconciled, including
  29 settled bootstrap boundaries.
- Candidate serialization round-tripped exactly. The local candidate file hash
  is `42df9444c33d556811dc2bd11b8e465c30eac5f01801a582c2dc7aa81758c382`;
  it is marked production-incompatible and remains local-only.

## Authority

This result grants no gameplay, holdout, qualification, promotion, policy
quality, or production-loading authority. No second fit or recipe change is
allowed on this corpus.
