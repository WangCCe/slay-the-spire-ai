## 1. Runtime Contract

- [x] 1.1 Add RED regressions for default-off behavior, tracked registration validation, exact candidate and parent binding, and inference-only eligibility.
- [x] 1.2 Implement the compact registration loader and post-checkpoint latent-gated shadow initialization.

## 2. Behavior-Neutral Observation

- [x] 2.1 Add RED regressions proving candidate disagreement cannot replace the parent action, candidate actions remain legal, and parent parity failures preserve gameplay.
- [x] 2.2 Implement bounded per-decision shadow inference, structured JSONL events, failure isolation, and event-budget shutdown.

## 3. Readiness Reporting

- [x] 3.1 Add RED regressions for trace identity, sequence continuity, minimum count, parity, legality, error, budget, and p95 latency checks.
- [x] 3.2 Implement the read-only live-shadow summarizer and machine-readable readiness report.

## 4. Verification And Fresh Evidence

- [x] 4.1 Run focused runtime/summarizer tests, adjacent RL v2 tests, and strict OpenSpec validation.
- [x] 4.2 Run one optimized commit gate at the completed capability boundary and record its duration for the queued gate-performance work (4190 passed, 26 skipped; 318.74s total).
- [x] 4.3 Commit a bounded production-r16 shadow registration, run a fresh live cohort, reconcile trace, `.run`, `ai_debug.log`, and `communication_mod_errors.log`, and publish a matched-gate go/no-go report.
- [ ] 4.4 Sync and archive the completed OpenSpec change without granting candidate action authority.
