## 1. Parity-Preserving Selection

- [x] 1.1 Add repeated-state reference regressions covering multi-candidate and multi-row masks, forbidden actions, threshold abstention, predictions, actions, gates, and telemetry.
- [x] 1.2 Refactor action-relative selection to compute one frozen parent latent per original state row and reuse it for candidate-pair scoring without changing the public single-pair scorer.

## 2. Source And Offline Performance Gates

- [x] 2.1 Add the fixed production-r16 CPU microbenchmark with 32 warmups, 256 deterministic held-out measurements, exact parity checks, 2x p50 speedup, and 15ms optimized p95 gates.
- [x] 2.2 Run focused and adjacent tests, strict OpenSpec validation, and one repository commit gate; commit and push the source-only optimization.
- [x] 2.3 Commit and execute one immutable offline benchmark registration; stop without live gameplay if any fixed condition fails.

The only execution stopped during the first warmup parity comparison with
`RuntimeError: action-relative latency prediction parity failed`. No benchmark
output or staging directory was created, and the runtime optimization was
rolled back rather than changing tolerance or retrying.

## 3. Fresh Live Requalification

- [x] 3.1 If the offline gate passes, commit and push one new five-game behavior-neutral live registration with unchanged artifact, parent, budget, support, and latency conditions. Skipped because the offline gate failed.
- [x] 3.2 Back up and temporarily update the production-r16 CommunicationMod command, complete at most one fresh five-game r2 batch, and restore the exact prior config after terminalization or failure. Skipped before config access because the offline gate failed.
- [x] 3.3 Publish trace, run, log, sim-divergence, config, and fixed readiness evidence; do not grant candidate action authority unless every registered condition passes. No live evidence exists because r2 was not authorized; the terminal offline failure is published instead.

## 4. Closure

- [x] 4.1 Do not sync the failed residual requirement; archive the OpenSpec change and commit only scoped rollback, registration, and compact failure artifacts.
