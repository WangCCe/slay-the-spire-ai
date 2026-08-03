## 1. Freeze The Source-Only Contract

- [x] 1.1 Add a source-only experiment module with closed enums and constants for the feature, algorithm, reward, cohort, blocker, resource, artifact, verdict, and authority contracts.
- [x] 1.2 Add canonical registration and execution-authorization schemas that reject unknown fields, noncanonical encodings, changed identities, permissive authority, and execution before a pushed registration.
- [x] 1.3 Add red contract tests for the exact train `50000..51023`, canary `51024..51151`, and holdout `51152..51663` ranges, four train passes, 64-episode chunks, 4,096 primary episodes, and 28,800-second cumulative wall limit.
- [x] 1.4 Add negative tests proving source-only validation does not import `sts_lightspeed`, construct an environment, consume a registered seed, import Communication Mod code, or discover production checkpoints.
- [x] 1.5 Bind the frozen simulator smoke, formal reward, API v3 adapter, readiness, and source-inventory inputs by canonical path and digest without rewriting their artifacts or verdicts.

## 2. Implement Features And Reward

- [x] 2.1 Implement `noncombat-simulator-policy-features-v2` as a deterministic API v3 snapshot-and-candidate projection with fixed ordering, hashing, float encoding, and 1,024-dimensional output.
- [x] 2.2 Reject duplicate or empty candidates, unknown candidate categories, non-finite inputs, malformed snapshots, source mutation, and any seed, outcome, provenance, baseline-history, or terminal-label feature leakage.
- [x] 2.3 Add projector regressions for all four decision categories, stable candidate reordering, source nonmutation, collision accumulation, finite output, and forbidden-field invariance.
- [x] 2.4 Implement the formal scalar reward as capped nonnegative floor advancement divided by 57 plus exactly `2.0` for terminal `player_victory`, with discount `1.0`.
- [x] 2.5 Add exhaustive reward-boundary and strict-dominance tests, including regressions proving Current, Bottled, SimpleAgent, resource heuristics, live outcomes, and OPE values cannot alter reward.
- [x] 2.6 Preserve the frozen v1 projector, training-smoke behavior, and historical smoke artifacts byte-for-byte.

## 3. Implement The Chunked Training Engine

- [x] 3.1 Implement the registered CPU-only linear `CandidateRanker` initialization and candidate-masked sampling with model seed `0`, PyTorch threads `1`, deterministic algorithms, and CUDA rejection.
- [x] 3.2 Implement one candidate-masked REINFORCE update per 64 retained episodes using within-chunk standardized return-to-go, Adam `0.001`, and discount `1.0`.
- [x] 3.3 Enforce ascending seed order, four deterministic train passes, exact next-coordinate accounting, one update per complete chunk, and no shuffle, replacement, tuning, or partial-chunk update.
- [x] 3.4 Retain exact registered support blockers as non-victories at their last supported floor and include them in every applicable denominator and category aggregate.
- [x] 3.5 Fail the whole experiment at the exact coordinate for an unknown blocker, illegal action, invalid candidate set, mutation, exception, or non-finite probability, return, loss, gradient, optimizer, or model value.
- [x] 3.6 Add fake-environment tests for legal masking, deterministic sampling, update counts, conservative blocker accounting, terminal coordinates, and every fail-closed path without native imports.

## 4. Implement Canonical Checkpoint And Resume

- [x] 4.1 Implement canonical JSON encoding and decoding for the deterministic model, Adam, Python, PyTorch, and action-generator state payload with explicit dtype, shape, little-endian contiguous bytes, and base64 payloads.
- [x] 4.2 Record registration and implementation identities, logical execution id, completed pass/seed/chunk coordinates, state-payload digest, cumulative bounded runtime, previous checkpoint digest, and next coordinate in every checkpoint envelope.
- [x] 4.3 Implement atomic checkpoint publication, append-only started/continued/terminal journal records, a single-process lease, and full hash-chain and output-inventory validation before resume.
- [x] 4.4 Make resume continue only the original logical attempt and reject changed source/runtime/native identities, missing or extra checkpoints, broken chains, invalid coordinates, concurrent leases, terminal journals, and exhausted cumulative time.
- [x] 4.5 Implement an independent initialization-to-checkpoint-2 prefix replay and require byte-for-byte equality of the deterministic state payload, excluding measured wall time and the replay envelope chain, before canary access.
- [x] 4.6 Add interruption-at-each-boundary, tamper, partial-write, lease, terminal-resume, wall-budget, tensor-codec, and two-chunk byte-replay regressions.

## 5. Implement Isolated Evaluation

- [x] 5.1 Freeze independent initialization and trained model snapshots before evaluation and prohibit optimizer steps or policy updates from canary and holdout transitions.
- [x] 5.2 Run paired initialization-versus-trained canary evaluation once per registered seed with legal terminal rows, conservative blockers, and complete four-category coverage accounting.
- [x] 5.3 Implement the fixed canary gate: unsupported rate at most 10%, trained victories not below initialization, and a deterministic 95% paired terminal-floor bootstrap lower bound above zero.
- [x] 5.4 Keep all holdout seeds untouched when any canary structural or learning gate fails and classify the terminal result as `experiment_stopped_at_canary`.
- [x] 5.5 When canary passes, evaluate both frozen policies once on all 512 holdout seeds and classify learning signal only when trained victories exceed initialization and the paired floor lower bound is positive.
- [x] 5.6 Add deterministic bootstrap, cohort-isolation, denominator, untouched-holdout, victory-primary ordering, and all terminal-verdict regressions.

## 6. Implement Atomic Publication And Verification

- [x] 6.1 Define canonical configuration, journal, checkpoint, trajectory-summary, reached-evaluation, metrics, final-model, report, and manifest schemas plus exact required and forbidden inventories for each terminal state.
- [x] 6.2 Publish artifacts through temporary files and atomic replacement while preserving the last complete checkpoint and journal on interruption or publication failure.
- [x] 6.3 Implement a standalone verifier that uses only the Python standard library to recompute identities, canonical bytes, hash chains, coordinates, cohort counts, gates, artifact inventory, and terminal verdict.
- [x] 6.4 Reject missing, extra, partial, noncanonical, mismatched, post-terminal, live-checkpoint-discoverable, or authority-escalating artifacts without replacing the terminal evidence.
- [x] 6.5 Add verifier fixture tests for every valid terminal verdict and focused tampering of each artifact class, with explicit assertions that native code and PyTorch remain unimported.
- [x] 6.6 Ensure every report states that formal readiness remains `not_ready_for_bounded_training_proposal` and grants no Current, live, OPE, causal, qualification, loading, or promotion authority.

## 7. Verify And Publish The Source Implementation

- [x] 7.1 Run focused source-only experiment tests plus adjacent adapter, training-smoke, formal-reward, and formal-readiness regressions under a fresh writable pytest temp root.
- [x] 7.2 Run Python compilation, standalone-verifier fresh-process checks, `git diff --check`, and strict validation of this change and the complete OpenSpec tree.
- [x] 7.3 Run the repository commit gate exactly once instead of repeatedly invoking the raw full pytest suite; record duration and result without broad test-architecture changes.
  - Evidence: the sole gate-runner invocation exited `1` after `693.77s` because its nested pytest process lost access to the fresh `.pytest_gates` basetemp (`WinError 5`). The documented direct-pytest rollback with the identical commit-profile exclusions then passed `3796` tests with `11` skips in `332.80s`; the gate runner was not retried or changed.
- [x] 7.4 Review the diff for production entrypoint, Communication Mod, live checkpoint, historical artifact, frozen smoke, and unrelated-worktree isolation; do not run fresh gameplay because this source-only capability cannot affect a live run.
- [x] 7.5 Update project direction only to mark the bounded simulator experiment implementation ready for preregistration, while preserving both formal readiness blockers.
- [x] 7.6 Commit and push the reviewed source-only implementation before generating any registration, loading native code, constructing environments, using registered seeds, or training.

## 8. Preregister The Exact Experiment

- [x] 8.1 Scan canonical prior registered simulator cohort inputs and publish a source-only inventory proof that every value in `50000..51663` is collision-free; block without choosing a replacement range if any collision exists.
- [x] 8.2 Generate a canonical preregistration binding the pushed source commit, API v3 adapter, physical `sts_lightspeed` source and module identities, Windows runtime, formal reward artifact, fixed constants, cohorts, support blockers, limits, outputs, and all-false authority.
- [x] 8.3 Verify the preregistration twice in independent fresh processes and prove both runs are byte-identical and perform no native import, environment construction, seed use, training, or output-directory creation.
  - Evidence: both source-tree recomputations produced byte-identical verification output `dea99f28a27d0c0b49e86a0274a3d043b53925d7cde4425ec2c98a03e36a9056`; inventory `b800b633976ded015864c3b7dd88c3cdb4a64828f1bd14054fe6ff70fcbb2de0` and registration `cf30c2a2e1c10681968ef6f0191e33b272af047c496e811d7ae5aa24205fa452` remained all-false and output-absent.
- [x] 8.4 Review the preregistration against the proposal, design, specs, source implementation, seed inventory, and immutable historical evidence.
- [x] 8.5 Commit and push the preregistration and inventory proof while keeping `experiment_execution=false` and every live, OPE, formal-RL, qualification, loading, and promotion flag false.

## 9. Authorize And Preflight One Logical Execution

- [x] 9.1 Create a separate canonical one-shot execution authorization only after the pushed preregistration is exact, binding one unused logical execution id and changing only `experiment_execution` to true.
- [ ] 9.2 Add and run preflight checks for exact pushed source, runtime, native module, physical simulator source, registration, authorization, absent output, free lease, cumulative budget, and immutable production checkpoint inventory.
- [ ] 9.3 Prove preflight neither starts nor contacts Communication Mod, changes its configuration, discovers a live policy artifact, launches gameplay, or mutates production checkpoints.
- [x] 9.4 Commit and push the authorization before any native loading, environment construction, registered seed use, training, canary access, or holdout access.
- [ ] 9.5 Stop before execution if any identity, absence, authority, lease, or resource boundary differs; do not repair it by substituting a path, seed, runtime, module, threshold, or parameter.

## 10. Execute The Single Bounded Experiment

- [ ] 10.1 Start or resume exactly one logical experiment under its authorization, append the started journal, and retain every selected episode under the cumulative 28,800-second wall limit.
- [ ] 10.2 Complete and independently verify the first-two-chunk byte replay before continuing to the remaining registered train coordinates.
- [ ] 10.3 Complete all reachable training chunks with canonical checkpoints, or publish the exact bounded or blocked terminal state without retrying or replacing any episode.
- [ ] 10.4 Evaluate canary once for both frozen policies and access holdout only if every fixed canary gate passes.
- [ ] 10.5 Publish the reached terminal verdict, untouched-cohort state, full canonical artifact set, and standalone-verifier result; treat absence of learning signal as a valid terminal negative.
- [ ] 10.6 Do not rerun, tune, sweep, extend, reinterpret, or promote from the result under this change.

## 11. Close Out The Change

- [ ] 11.1 Re-run focused artifact and verifier tests after result publication; run the full commit gate again only if source code changed after the implementation release.
- [ ] 11.2 Update project direction with the exact simulator-only result, resource use, learning-signal verdict, preserved readiness blockers, and prohibited claims.
- [ ] 11.3 Sync the accepted capability deltas to the main specs, archive the completed change, and run strict change and repository-wide OpenSpec validation.
- [ ] 11.4 Commit and push the terminal evidence, direction update, synced specs, and archive while preserving all prior evidence and unrelated untracked files.
