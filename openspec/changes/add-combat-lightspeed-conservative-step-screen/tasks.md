## 1. Regression Coverage

- [x] 1.1 Add exact interpolation, deterministic publication, and frozen-comparator compatibility regressions.
- [x] 1.2 Add hash, authority, structure, dtype, and alpha rejection regressions.

## 2. Implementation

- [x] 2.1 Implement source-bound schema-0 LightSTS checkpoint interpolation and atomic output publication.
- [x] 2.2 Publish construction metadata and a manifest without ranking or live authority.

## 3. Evaluation

- [x] 3.1 Run focused tests and strict OpenSpec validation; record the full-suite disposition under the execution-heavy time budget. The combined interpolation/comparator gate passed `17` tests; the known roughly 30-minute full suite was intentionally omitted for this source-only utility.
- [x] 3.2 Generate preregistered alpha `0.25/0.5/0.75` candidates between r4 and the rejected full-step successor.
- [x] 3.3 Run one fresh frozen-comparison development cohort and apply aggregate and per-index guardrails.
- [x] 3.4 If eligible, run exactly one selected-alpha fresh confirmation; otherwise retain r4 and stop. No alpha was eligible, so the confirmation cohort was not accessed.
