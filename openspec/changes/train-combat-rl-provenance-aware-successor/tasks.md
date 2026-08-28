## 1. Runner Contract

- [x] 1.1 Add RED tests for immutable checkpoint validation, deterministic combat-group splitting, provenance-aware label metrics, and exact repeated candidate fitting.
- [x] 1.2 Implement the bounded offline full-network successor runner with the fixed recipe and atomic development-only artifacts.
- [x] 1.3 Add fixed eligibility checks for finite execution, validation fit, label agreement, material drift, End Turn drift, and candidate round-trip identity.

## 2. Verification

- [x] 2.1 Run the focused successor and RL v2 trainer tests using a fresh system-temp pytest base.
- [x] 2.2 Run strict OpenSpec validation and the qualified commit test gate once at the completed capability boundary.

## 3. Bounded Training

- [ ] 3.1 Execute the registered recipe exactly once against checkpoint SHA-256 `302a7350a7e216ea548025ac4cb588c1ea77872328ccef977f94feab65e03fb4`.
- [ ] 3.2 Audit the immutable report and candidate hashes, record the gate decision, and forbid same-corpus recipe changes.
- [ ] 3.3 Commit and push the cohesive change; register a separate fresh holdout only if every eligibility condition passes.
