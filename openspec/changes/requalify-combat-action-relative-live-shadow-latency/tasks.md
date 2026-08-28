## 1. Numeric Contract

- [ ] 1.1 Publish the fixed 288-row post-failure numeric audit with exact input identities, schedule, margins, mismatch counts, diagnostic-only authority, and no live authorization.
- [ ] 1.2 Add regressions proving `1e-5` float32 prediction tolerance, exact action/gate/telemetry equivalence, and fail-closed behavior outside either numerical or behavioral bounds.

## 2. State-Unique Selection

- [ ] 2.1 Reapply one parent-latent computation per original state row and prove the runtime selection diff is byte-equivalent to the already-gated `d074bb170` implementation.
- [ ] 2.2 Revise the CPU preflight to a new experiment identity and fixed `1e-5` tolerance while retaining 32 warmups, 256 measurements, 2x p50 speedup, 15ms p95, input bindings, and environment isolation.
- [ ] 2.3 Run focused and adjacent tests, Python compilation, strict OpenSpec validation, and diff checks; reuse the `d074bb170` commit-gate result only if runtime bytes are equivalent, otherwise run one new commit gate, then commit and push source.

## 3. New Offline Preflight

- [ ] 3.1 Commit and push one immutable r2 CPU preflight registration with unchanged parent, artifact, corpus, deterministic schedule, and speed limits.
- [ ] 3.2 Execute the r2 registration once and publish parity, latency, provenance, and terminal decision; do not change or retry the registration after execution.

## 4. Fresh Live Shadow

- [ ] 4.1 Only if r2 offline passes, commit and push one new five-game behavior-neutral live registration with unchanged artifact, parent, 512-decision budget, 100-eligible floor, and 20ms p95 gate.
- [ ] 4.2 Back up and temporarily update the production-r16 CommunicationMod command, complete at most one five-game live batch, and restore the exact prior config after terminalization or failure.
- [ ] 4.3 Publish trace, run, log, sim-divergence, config, and readiness evidence; retain zero candidate action authority unless every registered condition passes.

## 5. Closure

- [ ] 5.1 Sync the accepted float32-equivalence requirement only if the offline preflight passes, archive the change, and commit only scoped source, registrations, and compact reports.
