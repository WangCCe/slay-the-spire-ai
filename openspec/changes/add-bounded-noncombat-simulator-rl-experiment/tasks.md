## 1. Freeze The Source-Only Contract

- [ ] 1.1 Add a source-only experiment module with closed enums and constants for the feature, algorithm, reward, cohort, blocker, resource, artifact, verdict, and authority contracts.
- [ ] 1.2 Add canonical registration and execution-authorization schemas that reject unknown fields, noncanonical encodings, changed identities, permissive authority, and execution before a pushed registration.
- [ ] 1.3 Add red contract tests for the exact train `50000..51023`, canary `51024..51151`, and holdout `51152..51663` ranges, four train passes, 64-episode chunks, 4,096 primary episodes, and 28,800-second cumulative wall limit.
- [ ] 1.4 Add negative tests proving source-only validation does not import `sts_lightspeed`, construct an environment, consume a registered seed, import Communication Mod code, or discover production checkpoints.
- [ ] 1.5 Bind the frozen simulator smoke, formal reward, API v3 adapter, readiness, and source-inventory inputs by canonical path and digest without rewriting their artifacts or verdicts.

## 2. Implement Features And Reward

- [ ] 2.1 Implement `noncombat-simulator-policy-features-v2` as a deterministic API v3 snapshot-and-candidate projection with fixed ordering, hashing, float encoding, and 1,024-dimensional output.
- [ ] 2.2 Reject duplicate or empty candidates, unknown candidate categories, non-finite inputs, malformed snapshots, source mutation, and any seed, outcome, provenance, baseline-history, or terminal-label feature leakage.
- [ ] 2.3 Add projector regressions for all four decision categories, stable candidate reordering, source nonmutation, collision accumulation, finite output, and forbidden-field invariance.
- [ ] 2.4 Implement the formal scalar reward as capped nonnegative floor advancement divided by 57 plus exactly `2.0` for terminal `player_victory`, with discount `1.0`.
- [ ] 2.5 Add exhaustive reward-boundary and strict-dominance tests, including regressions proving Current, Bottled, SimpleAgent, resource heuristics, live outcomes, and OPE values cannot alter reward.
- [ ] 2.6 Preserve the frozen v1 projector, training-smoke behavior, and historical smoke artifacts byte-for-byte.

## 3. Implement The Chunked Training Engine

- [ ] 3.1 Implement the registered CPU-only linear `CandidateRanker` initialization and candidate-masked sampling with model seed `0`, PyTorch threads `1`, deterministic algorithms, and CUDA rejection.
- [ ] 3.2 Implement one candidate-masked REINFORCE update per 64 retained episodes using within-chunk standardized return-to-go, Adam `0.001`, and discount `1.0`.
- [ ] 3.3 Enforce ascending seed order, four deterministic train passes, exact next-coordinate accounting, one update per complete chunk, and no shuffle, replacement, tuning, or partial-chunk update.
- [ ] 3.4 Retain exact registered support blockers as non-victories at their last supported floor and include them in every applicable denominator and category aggregate.
- [ ] 3.5 Fail the whole experiment at the exact coordinate for an unknown blocker, illegal action, invalid candidate set, mutation, exception, or non-finite probability, return, loss, gradient, optimizer, or model value.
- [ ] 3.6 Add fake-environment tests for legal masking, deterministic sampling, update counts, conservative blocker accounting, terminal coordinates, and every fail-closed path without native imports.

## 4. Implement Canonical Checkpoint And Resume

- [ ] 4.1 Implement canonical JSON encoding and decoding for model, Adam, Python, PyTorch, and action-generator states with explicit dtype, shape, little-endian contiguous bytes, and base64 payloads.
- [ ] 4.2 Record registration and implementation identities, logical execution id, completed pass/seed/chunk coordinates, cumulative bounded runtime, previous checkpoint digest, and next coordinate in every checkpoint.
- [ ] 4.3 Implement atomic checkpoint publication, append-only started/continued/terminal journal records, a single-process lease, and full hash-chain and output-inventory validation before resume.
- [ ] 4.4 Make resume continue only the original logical attempt and reject changed source/runtime/native identities, missing or extra checkpoints, broken chains, invalid coordinates, concurrent leases, terminal journals, and exhausted cumulative time.
- [ ] 4.5 Implement an independent initialization-to-checkpoint-2 prefix replay and require byte-for-byte equality with the primary second checkpoint before canary access.
- [ ] 4.6 Add interruption-at-each-boundary, tamper, partial-write, lease, terminal-resume, wall-budget, tensor-codec, and two-chunk byte-replay regressions.

## 5. Implement Isolated Evaluation

- [ ] 5.1 Freeze independent initialization and trained model snapshots before evaluation and prohibit optimizer steps or policy updates from canary and holdout transitions.
- [ ] 5.2 Run paired initialization-versus-trained canary evaluation once per registered seed with legal terminal rows, conservative blockers, and complete four-category coverage accounting.
- [ ] 5.3 Implement the fixed canary gate: unsupported rate at most 10%, trained victories not below initialization, and a deterministic 95% paired terminal-floor bootstrap lower bound above zero.
- [ ] 5.4 Keep all holdout seeds untouched when any canary structural or learning gate fails and classify the terminal result as `experiment_stopped_at_canary`.
- [ ] 5.5 When canary passes, evaluate both frozen policies once on all 512 holdout seeds and classify learning signal only when trained victories exceed initialization and the paired floor lower bound is positive.
- [ ] 5.6 Add deterministic bootstrap, cohort-isolation, denominator, untouched-holdout, victory-primary ordering, and all terminal-verdict regressions.

## 6. Implement Atomic Publication And Verification

- [ ] 6.1 Define canonical configuration, journal, checkpoint, trajectory-summary, reached-evaluation, metrics, final-model, report, and manifest schemas plus exact required and forbidden inventories for each terminal state.
- [ ] 6.2 Publish artifacts through temporary files and atomic replacement while preserving the last complete checkpoint and journal on interruption or publication failure.
- [ ] 6.3 Implement a standalone verifier that uses only the Python standard library to recompute identities, canonical bytes, hash chains, coordinates, cohort counts, gates, artifact inventory, and terminal verdict.
- [ ] 6.4 Reject missing, extra, partial, noncanonical, mismatched, post-terminal, live-checkpoint-discoverable, or authority-escalating artifacts without replacing the terminal evidence.
- [ ] 6.5 Add verifier fixture tests for every valid terminal verdict and focused tampering of each artifact class, with explicit assertions that native code and PyTorch remain unimported.
- [ ] 6.6 Ensure every report states that formal readiness remains `not_ready_for_bounded_training_proposal` and grants no Current, live, OPE, causal, qualification, loading, or promotion authority.

## 7. Verify And Publish The Source Implementation

- [ ] 7.1 Run focused source-only experiment tests plus adjacent adapter, training-smoke, formal-reward, and formal-readiness regressions under a fresh writable pytest temp root.
- [ ] 7.2 Run Python compilation, standalone-verifier fresh-process checks, `git diff --check`, and strict validation of this change and the complete OpenSpec tree.
- [ ] 7.3 Run the repository commit gate exactly once instead of repeatedly invoking the raw full pytest suite; record duration and result without broad test-architecture changes.
- [ ] 7.4 Review the diff for production entrypoint, Communication Mod, live checkpoint, historical artifact, frozen smoke, and unrelated-worktree isolation; do not run fresh gameplay because this source-only capability cannot affect a live run.
- [ ] 7.5 Update project direction only to mark the bounded simulator experiment implementation ready for preregistration, while preserving both formal readiness blockers.
- [ ] 7.6 Commit and push the reviewed source-only implementation before generating any registration, loading native code, constructing environments, using registered seeds, or training.

## 8. Preregister The Exact Experiment

- [ ] 8.1 Scan canonical prior registered simulator cohort inputs and publish a source-only inventory proof that every value in `50000..51663` is collision-free; block without choosing a replacement range if any collision exists.
- [ ] 8.2 Generate a canonical preregistration binding the pushed source commit, API v3 adapter, physical `sts_lightspeed` source and module identities, Windows runtime, formal reward artifact, fixed constants, cohorts, support blockers, limits, outputs, and all-false authority.
- [ ] 8.3 Verify the preregistration twice in independent fresh processes and prove both runs are byte-identical and perform no native import, environment construction, seed use, training, or output-directory creation.
- [ ] 8.4 Review the preregistration against the proposal, design, specs, source implementation, seed inventory, and immutable historical evidence.
- [ ] 8.5 Commit and push the preregistration and inventory proof while keeping `experiment_execution=false` and every live, OPE, formal-RL, qualification, loading, and promotion flag false.

## 9. Authorize And Preflight One Logical Execution

- [ ] 9.1 Create a separate canonical one-shot execution authorization only after the pushed preregistration is exact, binding one unused logical execution id and changing only `experiment_execution` to true.
- [ ] 9.2 Add and run preflight checks for exact pushed source, runtime, native module, physical simulator source, registration, authorization, absent output, free lease, cumulative budget, and immutable production checkpoint inventory.
- [ ] 9.3 Prove preflight neither starts nor contacts Communication Mod, changes its configuration, discovers a live policy artifact, launches gameplay, or mutates production checkpoints.
- [ ] 9.4 Commit and push the authorization before any native loading, environment construction, registered seed use, training, canary access, or holdout access.
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
