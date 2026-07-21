## 1. Regression Coverage

- [ ] 1.1 Replace the irrelevant earlier-node propagation characterization with failing mid-act and floor-14 regressions proving one conservative fallback call, no repeated whole-map validation, preserved absolute history, `candidate_generation_failed`, and no pre-commit mutation.
- [ ] 1.2 Retain and extend regressions proving invalid active origin/history, conservative-builder exceptions, invalid fallback output, and unexpected selector errors propagate without retry, route/metadata mutation, or adaptive decision log.
- [ ] 1.3 Add failing construction tests that reject `rl` plus `adaptive` before the RL factory/model path while preserving adaptive propagation for `simple`, `optimized`, Ironclad `auto`, and `combat_rl` and preserving legacy full-RL startup.
- [ ] 1.4 Add failing outcome-specific log-schema tests for success, forced, unsupported, candidate-generation fallback, invalid state, exactly-one post-commit summary, and no summary on an uncommitted error.

## 2. Minimal Integration Fixes

- [ ] 2.1 Make the conservative recovery helper skip repeated strict whole-map validation, validate active origin/history and the one returned full conservative candidate, and return that candidate for route commit and observability without changing normal two-candidate selection.
- [ ] 2.2 Add centralized fail-fast compatibility validation for the exact full-RL/adaptive combination without changing RL constructors, action ownership, checkpoints, training, legacy modes, or supported heuristic map-owner paths.
- [ ] 2.3 Extend the parameterized `[ADAPTIVE_ROUTE]` record with outcome, state validity/history, candidate-pair availability, validated summaries, minimum/added elite counts, and fallback evidence while preserving commit ordering and exactly-one logging.
- [ ] 2.4 Correct touched constructor/help documentation to describe adaptive support and the explicit full-RL restriction without changing defaults or persistent live configuration.

## 3. Focused Verification And Task Review

- [ ] 3.1 Run the complete `tests/test_map_routing_safety.py` and `tests/test_main_runtime_errors.py` suites with `D:\anaconda\envs\stsai\python.exe`, cache disabled, and unique writable repository basetemps; preserve exact counts and durations.
- [ ] 3.2 Run strict `openspec validate harden-adaptive-route-integration-contracts` and `git diff --check`, confirm the diff contains no policy threshold, RL behavior, training, checkpoint, protocol, default, or live-config change, and obtain task-scoped read-only reviews with no unresolved Critical or Important finding.

## 4. Fresh Automated Qualification

- [ ] 4.1 After all task reviews are clean, run one host-permission `gameplay`, then `commit`, then `full` gate sequence, stopping at the first nonzero exit and never retrying; preserve each reached gate's raw terminal transcript at a separately named `reports/adaptive_route_integration_followup_*_20260721.txt` path.
- [ ] 4.2 Write `reports/adaptive_route_integration_followup_qualification_20260721.md` with exact commands, unique basetemps, counts, durations, exit codes, transcript hashes, and scope/static-validation results; any known stream-silence diagnosis remains attribution-only and a nonzero full gate remains failed.
- [ ] 4.3 Generate a complete review package from original adaptive proposal commit `e1a559f37` through the follow-up head and obtain a fresh highest-capability read-only review with no unresolved Critical or Important finding; preserve the verdict in `reports/adaptive_route_integration_followup_final_review_20260721.md`.
- [ ] 4.4 Only after every fresh gate exits `0`, final static checks pass, and the whole-range review is clean, mark the original `add-adaptive-elite-routing-baseline` task `4.4` satisfied and leave its bounded no-training live cohort as the next separate phase.
