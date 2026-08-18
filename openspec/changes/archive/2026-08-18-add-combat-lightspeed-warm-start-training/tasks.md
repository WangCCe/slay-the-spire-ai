## 1. Regression Coverage

- [x] 1.1 Add regressions for valid simulator-only warm start, exact parent/control identity, and fresh-mode compatibility.
- [x] 1.2 Add pre-start rejection regressions for production-compatible, wrong-kind, missing-state, and incompatible checkpoints.

## 2. Implementation

- [x] 2.1 Add bound checkpoint loading and provenance to the LightSTS training runner.
- [x] 2.2 Load the parent into online and target networks, preserve it as control, and bind it into the successor checkpoint metadata.

## 3. Verification And Experiment

- [x] 3.1 Run focused pytest and strict OpenSpec validation.
- [x] 3.2 Record the repository pytest-gate disposition. The known roughly 30-minute full gate was intentionally not run for this source-only analysis-runner change under the agreed execution-heavy time budget; the native focused gate passed `16` tests.
- [x] 3.3 Register and execute one CPU-only r4 warm-start mixed-battle experiment on fresh train/evaluation seeds.
- [x] 3.4 Analyze aggregate and per-battle-index candidate-versus-r4 metrics and decide whether replication or live transfer is justified.
