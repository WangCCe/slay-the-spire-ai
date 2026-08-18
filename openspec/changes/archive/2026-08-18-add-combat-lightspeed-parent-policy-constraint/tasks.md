## 1. Regression Coverage

- [x] 1.1 Add zero-weight compatibility and positive-weight frozen-parent identity regressions.
- [x] 1.2 Add missing-parent, invalid-weight, finite positive anchor loss, and successor provenance regressions.

## 2. Implementation

- [x] 2.1 Wire optional parent-policy anchor weight through LightSTS config, trainer construction, and CLI.
- [x] 2.2 Freeze the loaded parent as anchor and report separate total, TD, and anchor objective summaries.

## 3. Training Evidence

- [x] 3.1 Run focused native tests and strict OpenSpec validation; record the full-suite disposition. The combined native training/interpolation/comparator gate passed `37` tests; the known roughly 30-minute full suite was intentionally omitted for this source-only runner extension.
- [x] 3.2 Register and run one fixed-weight r4 anchored mixed-battle training experiment on new seeds.
- [x] 3.3 Apply aggregate and per-index guardrails and decide whether one fresh simulator replication is justified. Aggregate HP and index 9 failed, so no replication is authorized.
