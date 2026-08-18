## 1. Regression Coverage

- [x] 1.1 Add transition-stratum identity, default compatibility, deterministic balancing, and count-report regressions.
- [x] 1.2 Add missing-stratum and invalid-seed/config rejection regressions.

## 2. Implementation

- [x] 2.1 Add runner-local battle-index metadata and source transition counts.
- [x] 2.2 Add opt-in deterministic oversampling/interleaving and prepared replay provenance.

## 3. Training Evidence

- [x] 3.1 Run focused native tests and strict OpenSpec validation; record the full-suite disposition. The combined native LightSTS gate passed `40` tests; the known roughly 30-minute full suite was intentionally omitted for this simulator-only runner change.
- [ ] 3.2 Register and run one r4 anchored stratified-replay experiment on new seeds.
- [ ] 3.3 Apply aggregate and per-index guardrails and decide whether one fresh simulator replication is justified.
