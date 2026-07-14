## 1. Registration And Immutable Schedule

- [x] 1.1 Add failing registration tests in `tests/test_noncombat_outcome_evidence_expansion.py` for the exact 24-by-25 schedule, fixed session IDs and seeds, `card_reward=300`, `shop=1000`, two-attempt budget, executable-category boundary, canonical hash, duplicate slots, changed thresholds, and non-integer exact fields; run the focused file with Windows pytest and preserve the red result.
- [x] 1.2 Implement the versioned registration model, strict JSON loader, canonical renderer/hash, and deterministic slot table in `analysis_scripts/noncombat_outcome_evidence_expansion.py` without importing gameplay, Bottled, PyTorch, or checkpoint-loading modules; make the registration tests pass.
- [x] 1.3 Add failing tests for a tracked-dirty start, registration-byte tampering, unsupported Python path, command drift, source-file hash drift, CommunicationMod semantic drift, checkpoint drift, and two locks for one study.
- [x] 1.4 Implement atomic run-lock creation and validation in `analysis_scripts/noncombat_outcome_evidence_expansion.py`, binding the clean HEAD, registration bytes, hash-bound implementation files, exact eval command, Windows Python, CommunicationMod semantic snapshot, and checkpoint snapshot.

## 2. Fixed Runner And Append-Only Ledger

- [x] 2.1 Add failing runner tests in `tests/test_noncombat_outcome_evidence_runner.py` for ordered launch, `--max-games 25`, `--eval`, explicit exploration config forwarding, rejected `--train` or mutation flags, launch-at-most-once, out-of-order slots, unregistered IDs, and post-slot-24 extension.
- [x] 2.2 Implement `scripts/run_noncombat_outcome_evidence_expansion.py` with `start`, `dry-run`, `run-next`, `monitor`, and `finalize` subcommands, reusing the existing bounded batch command contract while leaving `scripts/run_training_batch.py` defaults unchanged.
- [x] 2.3 Add failing ledger tests for atomic append, duplicate lifecycle records, process start/exit accounting, normal completion, early interruption, crash recovery, source-lock mismatch, and refusal to restart or replace an interrupted slot.
- [x] 2.4 Implement the append-only study ledger and slot lifecycle state machine so only the next unlaunched registered slot can run and a global integrity stop prevents every later launch.

## 3. Blinded Structural Monitoring

- [x] 3.1 Add failing monitor tests using fixtures that contain victories, floors, killed-by values, target weights, ESS, estimates, bootstrap rows, influence rows, and comparison gates; assert that collection-phase JSON and Markdown contain none of those fields or values.
- [x] 3.2 Implement deterministic blinded monitor artifacts that report only registration/run-lock validity, slot lifecycle, process exit, artifact existence, manifest/config hashes, replay and confirmation counts, conservative run-join completeness, and isolation status.
- [x] 3.3 Add ordering, malformed-artifact, missing-launched-session, and global-stop tests; require identical monitor bytes under input reordering and fail closed without leaking outcome fields.
- [x] 3.4 Run the new runner in no-game `dry-run` mode and verify all 24 generated commands, configs, session IDs, seeds, paths, rates, budgets, and forbidden training flags without launching Slay the Spire.

## 4. Registered Pool And Evidence Gate

- [x] 4.1 Add failing all-slot pool tests for deterministic registration enumeration, mixed exact session propensities, individual slots below aggregate arm support, missing or extra sessions, duplicate trajectories, selective omission, conflicting outcomes, run-lock mismatch, and input-order invariance.
- [x] 4.2 Implement deterministic registered pooling in `analysis_scripts/noncombat_outcome_evidence_expansion.py` by reusing confirmed exploration export and conservative run joins, preserving every session and trajectory inclusion or exclusion reason.
- [x] 4.3 Add boundary regressions for 574 versus 575 complete trajectories, 49 versus 50 baseline/alternative decisions per category, deterministic-Current nonzero count just below and at one half, ESS fraction below and at 0.5, maximum normalized weight above and at 0.05, and two versus three distinct positive-weight victories.
- [x] 4.4 Implement `outcome_evidence_expansion_ready` and deterministic JSON/Markdown closeout rendering with every observed value, threshold, blocker, slot status, and authority-boundary boolean.
- [ ] 4.5 Integrate the existing deterministic-Current target, OPE readiness, validated estimator, 10,000-replicate bootstrap, influence, and policy-comparison pipeline without changing their implementation bytes or thresholds; add a regression that fails if the registered finalizer substitutes floor reached or authorizes training/promotion.

## 5. Independent Verification

- [ ] 5.1 Add failing tests in `tests/test_noncombat_outcome_evidence_verifier.py` for tampered registration, run lock, ledger, manifest, trace, pool membership, terminal outcome, target probability, readiness diagnostic, estimate, supported-victory count, and closeout gate.
- [ ] 5.2 Implement `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py` as a standalone verifier that does not import the study builder/finalizer and independently recomputes hashes, slot accounting, pool membership, exact support, deterministic-Current weights, ESS screens, supported victories, and readiness booleans.
- [ ] 5.3 Add static import-independence and deterministic replay tests, record the verifier implementation hash in its audit, and verify that source or verifier byte changes invalidate the audit.

## 6. Freeze The Pre-Registered Implementation

- [ ] 6.1 Generate `reports/noncombat_outcome_evidence_expansion_20260715_registration.json` and its review Markdown from the implemented canonical renderer; verify exactly 24 slots, 600 scheduled attempts, fixed rates/budget, thresholds, and no outcome-derived field.
- [ ] 6.2 Run focused Windows pytest for the new expansion, runner, exploration-evidence, OPE-readiness, estimator, and verifier tests using `-p no:cacheprovider --basetemp <writable-repo-path>`; fix only failures attributable to this change.
- [ ] 6.3 Run the full Windows pytest suite, `openspec validate --all --strict`, `git diff --check`, and registration byte/hash replay; preserve exact command results in the pre-collection report.
- [ ] 6.4 Obtain code and spec review, resolve accepted Critical or Important findings with red regressions, rerun focused/full verification, and commit the implementation plus registration before any registered game starts.
- [ ] 6.5 Confirm the committed source is tracked-clean and that no gameplay, report, or configuration artifact predates or differs from the committed registration; record the clean implementation commit as the only allowed run-lock HEAD.

## 7. Execute The Blinded 600-Attempt Schedule

- [ ] 7.1 Verify no stale Slay the Spire, Java, or production Python process is active; capture the pre-study CommunicationMod semantic configuration and checkpoint snapshot; confirm the live command uses `D:\anaconda\envs\stsai\python.exe`, `--eval`, and no `--train`; finish and commit all tracked pre-lock bookkeeping so the source is clean.
- [ ] 7.2 Create the immutable run lock from the tracked-clean registration commit, rerun no-game dry-run for all 24 slots, and independently verify the lock before launching slot 01.
- [ ] 7.3 Execute registered slots 01-04 in order; after each slot run only the blinded structural monitor, preserve logs and artifacts, and stop immediately on a global integrity blocker.
- [ ] 7.4 Execute registered slots 05-08 under the unchanged lock and repeat the per-slot blinded structural checks without reading or reporting outcomes.
- [ ] 7.5 Execute registered slots 09-12 under the unchanged lock and repeat the per-slot blinded structural checks without adapting schedule, rates, thresholds, or source.
- [ ] 7.6 Execute registered slots 13-16 under the unchanged lock and mark any early process exit interrupted without restarting or replacing its slot.
- [ ] 7.7 Execute registered slots 17-20 under the unchanged lock and repeat the per-slot blinded structural checks; do not generate target, OPE, bootstrap, influence, or comparison artifacts.
- [ ] 7.8 Execute registered slots 21-24 under the unchanged lock, then verify that every registered slot is terminal and that no unregistered or replacement slot was launched.

From the start of task 7.2 through completion of task 8.3, do not edit any tracked file, including this checklist. Record progress only in the append-only external study ledger and defer checkbox updates until the run-lock window closes.

## 8. Unblind Once And Close Out

- [ ] 8.1 After all slots are terminal, run finalization exactly once to build the all-slot canonical pool, deterministic-Current target, OPE readiness, 10,000-replicate estimate, influence diagnostics, evidence gate, and closeout artifacts.
- [ ] 8.2 Run the standalone verifier over every registration-through-closeout artifact and require exact replay of pool membership, target weights, ESS, supported victories, estimates, intervals, influence, hashes, and readiness booleans.
- [ ] 8.3 Capture the post-study CommunicationMod and checkpoint snapshot, compare it to the pre-study snapshot, and inspect fresh `ai_debug.log` plus `communication_mod_errors.log` for collection or protocol failures.
- [ ] 8.4 After the run-lock window closes, update deferred task checkboxes, then run focused and full Windows pytest, strict OpenSpec validation, Git whitespace and byte checks, and an independent final review; fix accepted issues only with regressions and never by altering registered evidence or thresholds.
- [ ] 8.5 Commit the deterministic closeout and state the result as ready, inconclusive, or blocked; keep causal uplift, formal non-combat RL, reward design, gameplay-policy edits, and live promotion unauthorized regardless of the observed comparison.
