## 1. Device Evidence And Contract

- [x] 1.1 Publish the fixed dual-device POC with checkpoint/artifact/corpus identities, 32 warmups, 256 measurements, latency distributions, cross-device parity, and diagnostic-only authority.
- [x] 1.2 Add schema-v2 CPU registration tests plus schema-v1 compatibility and fail-closed unsupported-device regressions.

## 2. CPU Shadow Isolation

- [x] 2.1 Add RED initialization regressions proving the CPU mirror is distinct, state-identical, CPU-resident, and leaves the production parent device, storage, state, and action path unchanged.
- [x] 2.2 Implement schema-v2 CPU mirror initialization and preserve schema-v1 inherited-device behavior.
- [x] 2.3 Include registration schema and inference device in readiness output without changing trace schema or readiness thresholds.

## 3. Source Validation

- [x] 3.1 Run focused live-shadow, summary, agent, and batch-env tests, Python compilation, strict OpenSpec validation, and diff checks.
- [x] 3.2 Run one repository commit gate with a new `--timing-report`; use that single run for correctness and queued slow-gate attribution, then commit and push source.

The timed gate passed `4304` tests with `26` skipped and `21` deselected in
`158.19s`. Attributed testcase time was `142.394s`; the four slowest files were
`8.886s`, `8.437s`, `6.311s`, and `5.633s`, so no further exclusion was made
while the complete commit profile remains below its 300-second target.

## 4. Fresh CPU Live Shadow

- [x] 4.1 Commit and push one source-bound schema-v2 CPU five-game registration with unchanged parent, artifact, 512-decision budget, 100-eligible floor, and 20ms p95 gate.

Registration SHA-256:
`b226bf564b20b2bbbd8ee26d1bd79d1b4d1ec7a2e3da99eb21f9096eee2a0538`.
The real-artifact preflight kept the production parent on CUDA with unchanged
state and created a state-identical CPU shadow without writing the trace.
- [ ] 4.2 Back up and temporarily update the production-r16 CommunicationMod command, run at most one five-game cohort, and restore the exact prior config after terminalization or failure.
- [ ] 4.3 Publish trace, run, log, sim-divergence, config, and fixed readiness evidence; retain zero candidate action authority unless every registered condition passes.

## 5. Closure

- [ ] 5.1 Sync the CPU shadow isolation requirement if source and live evidence pass, archive the change, and commit only scoped source, registration, timing, and compact report artifacts.
