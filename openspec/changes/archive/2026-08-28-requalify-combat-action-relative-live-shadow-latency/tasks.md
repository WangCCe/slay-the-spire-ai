## 1. Numeric Contract

- [x] 1.1 Publish the fixed 288-row post-failure numeric audit with exact input identities, schedule, margins, mismatch counts, diagnostic-only authority, and no live authorization.
- [x] 1.2 Add regressions proving `1e-5` float32 prediction tolerance, exact action/gate/telemetry equivalence, and fail-closed behavior outside either numerical or behavioral bounds.

## 2. State-Unique Selection

- [x] 2.1 Reapply one parent-latent computation per original state row and prove the runtime selection diff is byte-equivalent to the already-gated `d074bb170` implementation.
- [x] 2.2 Revise the CPU preflight to a new experiment identity and fixed `1e-5` tolerance while retaining 32 warmups, 256 measurements, 2x p50 speedup, 15ms p95, input bindings, and environment isolation.
- [x] 2.3 Run focused and adjacent tests, Python compilation, strict OpenSpec validation, and diff checks; reuse the `d074bb170` commit-gate result only if runtime bytes are equivalent, otherwise run one new commit gate, then commit and push source.

Runtime and runtime-test blobs exactly match `d074bb170`; its commit gate passed
`4295` tests with `26` skipped and `21` deselected in `162.89s`. The revised
numeric runner and adjacent surfaces passed `55` focused tests in `9.60s`.

## 3. New Offline Preflight

- [x] 3.1 Commit and push one immutable r2 CPU preflight registration with unchanged parent, artifact, corpus, deterministic schedule, and speed limits.

Registration SHA-256:
`a158868b984b36f8ce3115c62381c5b87a020a30aee72f32fb3afcc1b756f2f5`.
- [x] 3.2 Execute the r2 registration once and publish parity, latency, provenance, and terminal decision; do not change or retry the registration after execution.

The immutable run passed prediction parity and the 15ms optimized p95 ceiling
but failed the 2x p50 speedup gate: reference p50 `1.622100ms`, optimized p50
`1.699700ms`, optimized p95 `2.330625ms`, and speedup `0.954345x`. The runtime
optimization was rolled back and the registration was not retried.

## 4. Fresh Live Shadow

- [x] 4.1 Only if r2 offline passes, commit and push one new five-game behavior-neutral live registration with unchanged artifact, parent, 512-decision budget, 100-eligible floor, and 20ms p95 gate. Skipped because r2 offline failed.
- [x] 4.2 Back up and temporarily update the production-r16 CommunicationMod command, complete at most one five-game live batch, and restore the exact prior config after terminalization or failure. Skipped before config access.
- [x] 4.3 Publish trace, run, log, sim-divergence, config, and readiness evidence; retain zero candidate action authority unless every registered condition passes. No live evidence exists; the offline report is terminal.

## 5. Closure

- [x] 5.1 Do not sync the failed float32-equivalence optimization requirement; archive the change and commit only scoped rollback, registration, and compact report artifacts.
