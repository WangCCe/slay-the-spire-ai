## 1. Configuration And Projection

- [x] 1.1 Validate explicit source/model/output bindings and keep default startup inert
- [x] 1.2 Project eligible live card rewards into the documented best-effort API-v3 boundary

## 2. Shadow Runtime

- [x] 2.1 Restore frozen r7 and residual bytes once and compute deterministic shadow scores
- [x] 2.2 Wrap the final callback, preserve Current action identity, deduplicate decisions, and fail open after Current
- [x] 2.3 Persist canonical complete, ineligible, and error rows with latency and identity evidence

## 3. Wiring And Verification

- [x] 3.1 Add opt-in main startup wiring and batch-wrapper config forwarding
- [x] 3.2 Add focused regressions for inert startup, binding drift, eligibility, scoring, identity preservation, deduplication, and persistence failure
- [x] 3.3 Run focused and adjacent pytest, compilation, strict OpenSpec validation, and commit/push the implementation

## 4. Fresh Gameplay

- [x] 4.1 Register one at-most-five-game no-training shadow config and run the fresh cohort
- [x] 4.2 Analyze coverage, disagreements, latency, errors, and action-substitution evidence; archive and commit the result
