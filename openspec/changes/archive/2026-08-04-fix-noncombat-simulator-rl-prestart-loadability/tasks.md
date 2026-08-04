## 1. Freeze The Evidence And Boundary

- [x] 1.1 Publish the read-only Windows native loadability audit with the exact Torch-first failure, native-first success, effective DLL paths, missing exports, and immutable r1 identity.
- [x] 1.2 Add RED regressions proving native load and provenance validation precede Torch initialization and fresh output creation.
- [x] 1.3 Add RED regressions proving a fresh pre-start failure leaves output absent and can repeat validation without creating a journal or consuming an experiment attempt.
- [x] 1.4 Add RED regressions proving a resume-time native or restore failure preserves the last complete nonterminal journal and checkpoints without terminal publication.
- [x] 1.5 Preserve a regression proving a failure after the started boundary still publishes the exact terminal blocked result.
  - RED evidence: all three focused boundary tests failed against the released runner, including observed `output -> torch -> native` ordering and terminal publication for both fresh and resume native-load failures.

## 2. Move The Runtime Compatibility Boundary

- [x] 2.1 Refactor the runner to load native and validate post-load provenance before any fresh Torch runtime initialization or resume restoration.
- [x] 2.2 Reuse the validated pristine runtime for a fresh execution, then atomically initialize output and acquire the execution lease without recreating Torch state.
- [x] 2.3 Keep pre-rollout native, provenance, and restore failures outside terminal publication while preserving existing rollout, replay, evaluation, checkpoint, and wall-time failure behavior.
- [x] 2.4 Keep registration, authorization, artifact, verifier, model, reward, cohort, threshold, and authority schemas unchanged.

## 3. Verify And Close Out

- [x] 3.1 Run focused runner and terminal-artifact tests under a scoped system-temp pytest root; record infrastructure failures separately from test failures.
  - Evidence: the final experiment, policy-learning, and adapter focus passed `184` tests with `5` skips in `73.40s` under the scoped system-temp root. An earlier command named a nonexistent test file and collected zero tests; it was recorded as invocation error rather than test evidence.
- [x] 3.2 Independently verify the archived r1 terminal artifact set and prove its manifest, verdict, episode counts, and logical execution identity remain unchanged.
  - Evidence: the standalone verifier passed `173` checks with `experiment_blocked`; manifest SHA-256 remains `01fe28cd35c13dcdee305189a27488474edfebfb126ba79aa145ab56d08c8080`, and the artifact directory has no Git diff.
- [x] 3.3 Run Python compilation, `git diff --check`, strict validation of this change and the complete OpenSpec tree, and the repository commit gate exactly once; do not run gameplay because production entrypoints are unchanged.
  - Evidence: compilation and diff checks passed; strict validation passed the change and all `64` OpenSpec items; the sole elevated commit-gate invocation passed `3805` tests with `11` skips in `299.92s` (`302.99s` runner wall time).
- [x] 3.4 Update project direction with the corrected future start boundary while preserving r1 terminality and every successor, training, live, qualification, loading, and promotion prohibition.
- [x] 3.5 Sync the accepted delta, archive the completed change, commit and push only scoped files, and preserve unrelated untracked artifacts and pytest directories.
  - Evidence: the accepted delta was synced manually to the main spec, the change was archived as `2026-08-04-fix-noncombat-simulator-rl-prestart-loadability`, and post-archive strict validation passed all `63` active OpenSpec items. The scoped commit and push publish these files without staging unrelated artifacts.
