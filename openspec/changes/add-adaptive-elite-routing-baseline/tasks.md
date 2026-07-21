## 1. Feasibility And Legacy Characterization

- [x] 1.1 Add characterization fixtures that lock conservative and aggressive chosen nodes, node priorities, elite tie breaks, forced one- and two-elite routes, and HP-drop replanning on identical inputs before shared planner refactoring.
- [x] 1.2 Build a read-only paired-route POC over every Task 1.1 fixture plus three versioned 15-layer, seven-column Act 1 fixtures with at least 35 reachable nodes and sparse, typical, and dense elite/rest placement, without adding adaptive gameplay behavior.
- [x] 1.3 On each full-height fixture exclude ten warm-up pairs, time 100 pairs from immediately before conservative generation through aggressive completion on identical separate-agent state using `perf_counter_ns` and normal logging, and report fixture JSON/SHA-256, command, interpreter, per-fixture and aggregate counts, median, p95, and maximum.
- [x] 1.4 Preserve the first failed qualification, complete and freeze the reviewed evidence harness without gameplay changes, and revise the proposal, design, and specification to permit one clean-source requalification under the unchanged gate.
- [x] 1.5 PASS: sole clean-source requalification completed with the production Windows interpreter across seven cases and 700 measured pairs. `reports/adaptive_route_candidate_poc_20260721_attempt-2_clean.json` records aggregate median `15.91075 ms`, p95 `26.9415 ms`, maximum `61.6691 ms`, and clean provenance at `0ddaf5520b25e722036ce5beab5c24ec068814a8`; its Markdown derivative preserves the unchanged thresholds and no-retry result.

## 2. Regression Coverage

- [x] 2.1 Add failing CLI and constructor tests for Ironclad `adaptive`, non-Ironclad `unsupported_character` conservative fallback, and unchanged legacy initialization.
- [x] 2.2 Add failing pure-policy tests for the exact deck-only score, potion allowlist/usability, relic allowlist/weights, local `node.y + 1` floor semantics, HP gates, support substitution, Act 2+ denial, malformed-state denial, and prior-exposure denial.
- [x] 2.3 Add failing selector fixtures for a prepared one-optional-elite choice, recovery denial and exception, two-added-elite denial, deterministic conservative tie, forced one- and two-elite selection, and incomplete-candidate fallback.
- [x] 2.4 Add failing agent tests for per-choice adaptive replanning, act reset, idempotent repeated-node/rest/elite tracking, and one structured decision log while retaining all Task 1 legacy characterizations.

## 3. Adaptive Policy And Selector

- [x] 3.1 Add immutable normalized route-state, candidate feature, and assessment result types plus named centralized baseline thresholds in the existing map-routing module.
- [x] 3.2 Implement independent deck-only readiness, potion support, relic support, fail-closed hard gates, and stable reason codes without changing the legacy aggressive readiness function or comparing legacy route scores.
- [x] 3.3 Refactor the existing route generator only enough to return complete conservative and aggressive candidates without changing either mode's selected path or side effects.
- [x] 3.4 Implement adaptive two-candidate selection that chooses aggressive only for the `0` versus `1` elite case after every hard gate passes, plus recovery feature extraction, deterministic conservative fallback for all other count pairs, and `candidate_generation_failed` handling.
- [x] 3.5 Add `adaptive` to CLI validation, help text, logging, and existing agent-construction paths without changing the default route mode.
- [x] 3.6 Track visited coordinates and latest rest idempotently by act, regenerate both candidates at every adaptive map choice, and emit one structured summary per decision.
- [x] 3.7 Confirm no combat, shop, event, card-reward, campfire, checkpoint, training, or Communication Mod protocol behavior changes in the implementation diff.

## 4. Automated Verification

- [x] 4.1 Run the focused CLI and map-routing regressions with the production Windows interpreter and a writable repository-local basetemp.
- [x] 4.2 Run `scripts/run_test_gate.py gameplay` and `scripts/run_test_gate.py commit`; preserve exact counts, durations, and any failure without retry.
- [x] 4.3 Run one unchanged `scripts/run_test_gate.py full`; record the exact result and separately diagnose at most the already-known timing-sensitive node without rewriting the full result.
- [x] 4.3a Preserve the canonical automated qualification report as immutable attempt-1 sandbox FAIL evidence and record the managed-sandbox ACL root cause without changing code, tests, or gate policy.
- [x] 4.3b Execute one host-permission sequence of unchanged `gameplay`, then `commit`, then `full` gates with generated unique basetemps, stopping immediately at the first nonzero result; if full's sole failure is the known stream-silence node, its one diagnostic run is attribution-only and the original full result remains nonzero/failed with no retry. Do not rerun focused verification and write only `reports/adaptive_elite_routing_automated_qualification_20260721_attempt-2-host.md`. Mark this task after execution evidence is preserved under that stop rule; qualification succeeds only if gameplay, commit, and full each exit `0`.
- [ ] 4.4 Only after successful all-three `4.3b` qualification, run `openspec validate add-adaptive-elite-routing-baseline` and `git diff --check`, then obtain a final read-only code review with no unresolved Critical or Important finding. Any Critical/Important finding blocks this qualification and requires a follow-up change and new evidence, not a same-attempt code fix or focused-test rerun.

## 5. Bounded Live Qualification

- [ ] 5.1 Capture the current Communication Mod configuration, latest AI run marker, debug/error log offsets, and decision/sim-divergence trace cutoffs; verify training is disabled and conservative is the rollback command.
- [ ] 5.2 Run one fresh ten-game Ironclad A0 adaptive cohort with `D:\anaconda\envs\stsai\python.exe`, stopping on a runtime error, repeated stall, or evidence-integrity failure.
- [ ] 5.3 Restore and attest the conservative Communication Mod configuration after completion or failure, and verify no training checkpoint was created or changed.
- [ ] 5.4 Write a dated report containing every run id; total `E` nodes; normalized final elite killers; elite death runs and fatality ratio; average/max floor; Act 2 boss reaches; victories; runtime errors; and fresh sim-divergence cluster keys against the preserved 2026-07-20 cohorts.
- [ ] 5.5 Mark the baseline eligible only for a larger validation when it has at least three elite encounters, at most two elite-death runs, elite fatality ratio at most 25 percent, average floor at least 24.2, at least three Act 2 boss reaches, no runtime error, and no repeated causal A-class cluster; otherwise retain conservative and do not tune and rerun the same cohort.
