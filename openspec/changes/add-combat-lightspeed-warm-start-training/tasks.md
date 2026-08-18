## 1. Regression Coverage

- [x] 1.1 Add regressions for valid simulator-only warm start, exact parent/control identity, and fresh-mode compatibility.
- [x] 1.2 Add pre-start rejection regressions for production-compatible, wrong-kind, missing-state, and incompatible checkpoints.

## 2. Implementation

- [x] 2.1 Add bound checkpoint loading and provenance to the LightSTS training runner.
- [x] 2.2 Load the parent into online and target networks, preserve it as control, and bind it into the successor checkpoint metadata.

## 3. Verification And Experiment

- [x] 3.1 Run focused pytest and strict OpenSpec validation.
- [ ] 3.2 Run the repository pytest gate once and record timeout or infrastructure failures without retrying.
- [x] 3.3 Register and execute one CPU-only r4 warm-start mixed-battle experiment on fresh train/evaluation seeds.
- [x] 3.4 Analyze aggregate and per-battle-index candidate-versus-r4 metrics and decide whether replication or live transfer is justified.
