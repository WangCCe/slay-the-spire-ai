## 1. Evaluator Contract

- [x] 1.1 Add focused fake-environment regressions for immutable source cloning, every-legal-action coverage, formal reward accumulation, and native-only continuation
- [x] 1.2 Add regressions for exact fixed-branch replay, branch-budget enforcement, and fail-closed unsupported transitions
- [x] 1.3 Implement compact action-branch and source-state evidence models plus preregistered viability verdict logic

## 2. Bounded Runner

- [x] 2.1 Implement the consumed-seed `1000..1007` runner with two-source-per-seed and 64-branch hard bounds
- [x] 2.2 Bind native adapter inputs, protected-seed exclusions, production checkpoint metadata, and CommunicationMod metadata without loading a learned model
- [x] 2.3 Add focused runner tests for registration bindings, fixed limits, false downstream authority, and production-isolation failure

## 3. Empirical POC

- [x] 3.1 Run focused evaluator and runner tests with a fresh system-temp pytest child
- [ ] 3.2 Execute the POC once on the fixed consumed development support and publish compact source/action/return evidence
- [ ] 3.3 Inspect the determinism, complete-state, informative-state, unique-best, budget, and isolation gates and record the fixed viable/not-ready verdict

## 4. Closure

- [ ] 4.1 Re-run OpenSpec strict validation and document why no full gameplay test gate is required for isolated analysis-only code
- [ ] 4.2 Sync the accepted capability spec, archive the completed change, and commit the implementation and evidence without staging unrelated reports or local checkpoints
