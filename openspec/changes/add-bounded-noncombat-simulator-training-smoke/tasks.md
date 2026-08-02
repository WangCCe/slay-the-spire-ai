## 1. Contracts And Red Regressions

- [ ] 1.1 Add registration-schema regressions for complete provenance, exact algorithm/reward/config values, unique disjoint seed cohorts, hard resource caps, identity drift, and fail-before-rollout behavior.
- [ ] 1.2 Add feature/reward regressions for leakage-field removal, stable retained feature bytes, unique legal candidate masking, fresh-clone legality, the exact floor-progress/victory reward, and exclusion of Bottled/live/heuristic values.
- [ ] 1.3 Add trainer regressions for seeded candidate sampling, return-to-go normalization, finite full-batch REINFORCE updates, CPU-only execution, hard episode/update/time stops, and no checkpoint loading or resume path.
- [ ] 1.4 Add paired-holdout regressions for frozen initial/final greedy policies, zero holdout updates, deterministic bootstrap intervals, structural/quality verdict separation, and the no-tune/no-alternate-rerun rule.
- [ ] 1.5 Add artifact and isolation regressions for canonical tensor/model hashes, same-input replay identity, noncanonical timing separation, atomic rollback, all-false downstream authority, and absence from live imports/checkpoint discovery.

## 2. Offline Smoke Implementation

- [ ] 2.1 Implement the versioned registration parser and fail-closed validator that binds the archived fit evidence, simulator/adapter/module/runtime identities, implementation commit, exact cohorts, and finite limits.
- [ ] 2.2 Implement simulator-only policy projection, candidate masking, rollout collection, transition reward, return-to-go, and per-episode diagnostics on top of the optional adapter wrapper.
- [ ] 2.3 Implement the closed CandidateRanker REINFORCE smoke with seed 0, CPU Adam, one full-batch update per registered pass, numerical guards, and no general training/resume API.
- [ ] 2.4 Implement frozen initial/final paired holdout evaluation, deterministic percentile bootstrap, four-category/terminal/legality checks, and fail-closed structural and quality verdicts.
- [ ] 2.5 Implement canonical offline artifact serialization, hash-closed manifest validation, pair publication with rollback, same-input reproduction comparison, Markdown rendering, and an explicit CLI that has no live startup import.

## 3. Registered Simulator Smoke

- [ ] 3.1 Commit the reviewed implementation and freeze one input binding its exact commit plus the accepted adapter-fit identities, train seeds 1000..1063, holdout seeds 2000..2063, eight passes, 500 decisions per episode, 512 train episodes, and 900 seconds per execution.
- [ ] 3.2 Rebuild the optional native module from the registered identities, run focused pure and opt-in integration checks, then execute exactly one primary smoke and one identical reproduction without parameter changes, gameplay, Java, CommunicationMod, or live evidence collection.
- [ ] 3.3 Publish the resulting model/metrics/report/manifest and noncanonical execution journal; if blocked or quality is not demonstrated, record that result and stop without tuning or retrying.
- [ ] 3.4 Update project direction and simulator documentation with the observed structural verdict, paired holdout estimate, limitations, and the next separately reviewed go/no-go boundary while leaving every downstream authority false.

## 4. Verification And Closeout

- [ ] 4.1 Run focused regressions, opt-in native-adapter integration tests, canonical artifact rehash/replay checks, and Python compilation without launching a live game or formal training.
- [ ] 4.2 Run the registered commit gate, strict OpenSpec validation, scoped diff review, and process/CommunicationMod/checkpoint isolation checks; do not substitute an unregistered raw full-suite invocation.
- [ ] 4.3 Perform a read-only final audit of seed disjointness, no holdout updates, exact provenance, deterministic replay, reward exclusion, verdict math, authority flags, and managed artifact inventory.
- [ ] 4.4 Sync accepted delta specs, archive the completed change, commit only scoped files, push `master`, and preserve all unrelated local artifacts.
