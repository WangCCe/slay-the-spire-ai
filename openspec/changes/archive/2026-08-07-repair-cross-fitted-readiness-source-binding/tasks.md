## 1. RED Source Contracts

- [x] 1.1 Replace the synthetic five-field consumed-schedule fixture with the exact production-shaped eight-field identity and prove the current auditor and verifier reject it.
- [x] 1.2 Add negative regressions for missing, extra, malformed, and drifted consumed provenance in both independent validation paths.
- [x] 1.3 Add a regression that every declared source-bound path exists at the tested tree and that the canonical readiness main spec replaces the retired active-change path.

## 2. Minimal Source Repair

- [x] 2.1 Update the auditor to require the exact eight-field consumed schedule and fixed provenance values while preserving its normalized candidate artifact schema.
- [x] 2.2 Apply the same contract independently in the standard-library verifier without importing the auditor.
- [x] 2.3 Move both readiness contract bindings to the canonical main spec, sync the modified requirements into it, and preserve all-false authority, retry, budget, rehearsal, cohort, and publication behavior.

## 3. Verification And Publication

- [x] 3.1 Run the focused source-only regression suite with isolated pytest temp storage and no native, Torch, environment, model, seed-outcome, game, or CommunicationMod access.
- [x] 3.2 Strictly validate the OpenSpec change and obtain an independent source review; resolve accepted findings with RED regressions.
- [x] 3.3 Run the repository commit gate exactly once, record any unrelated existing failures without rerunning, and confirm the staged diff is source-only.
- [x] 3.4 Commit and push the correction as a new source identity without creating, registering, or invoking another readiness attempt.
