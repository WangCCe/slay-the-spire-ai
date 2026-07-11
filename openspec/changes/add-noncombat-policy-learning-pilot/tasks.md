## 1. Preserve The Current Boundary As Regressions

- [x] 1.1 Add fixture coverage for `noncombat_rl_decision_samples_20260710_post_exec_command_fixes_25_bottled.jsonl` (SHA-256 `77DA5265ACF7A447C2C76321BED66F0D65C7A5C6614188C42505381D32C7E186`), including 373 samples, 216 matched rows, 6 unique matched trajectories, 0 victory trajectories, and category-specific support counts.
- [ ] 1.2 Add schema regressions proving legacy v1 samples remain readable but are excluded from pilot train/evaluation when trajectory or behavior provenance cannot be resolved.
- [ ] 1.3 Add guard tests proving the pilot cannot modify CommunicationMod configuration, launcher defaults, live policy imports, production checkpoints, or existing checkpoint discovery.
- [ ] 1.4 Record the frozen behavior candidate, source report hashes, current git commit, and explicit no-formal-RL/no-live-promotion boundary in the pilot manifest fixtures.

## 2. Add Policy-Learning Provenance And Dataset Manifests

- [x] 2.1 Extend canonical sample export with additive trajectory-group, behavior-policy, behavior-commit, action-probability, and probability-status fields.
- [x] 2.2 Populate trajectory groups only from unique reliable run joins and leave unknown behavior probabilities null with an explicit `unknown` status.
- [ ] 2.3 Build a versioned dataset manifest that records input hashes, schema versions, eligible rows, exclusions by reason, label-mode coverage, trajectory counts, outcomes, and action support.
- [ ] 2.4 Add focused tests for unique joins, ambiguous or missing joins, known deterministic provenance, unknown probability handling, and idempotent manifest generation.

## 3. Implement Deterministic Trajectory Splits

- [ ] 3.1 Implement stable seeded trajectory hashing and whole-trajectory train, validation, and test assignment.
- [ ] 3.2 Enforce disjoint group sets and keep every decision from one trajectory in one split.
- [ ] 3.3 Add the structural support gate: at least 10 eligible trajectories overall, non-empty train/validation/test splits, and at least two train plus one held-out trajectory for an evaluable category.
- [ ] 3.4 Add regressions for row-order independence, repeatable split hashes, empty or undersupported splits, category-specific blocking, and zero leakage.

## 4. Implement The Offline Candidate Ranker

- [ ] 4.1 Add deterministic numeric and hashed categorical feature extraction for normalized state/candidate pairs with a versioned feature configuration.
- [ ] 4.2 Implement a small CPU PyTorch candidate scorer that computes loss and predictions only over each sample's available candidates.
- [ ] 4.3 Implement separate Current-imitation and Bottled-auxiliary dataset modes; require mapped native high-confidence Bottled labels and never blend label sources.
- [ ] 4.4 Add finite epoch, seed, output-directory, and deterministic-order controls plus artifact manifests that mark formal RL and live promotion false.
- [ ] 4.5 Add regressions for 100 percent candidate-legal prediction, target-mapping exclusions, label isolation, bounded execution, and repeatable predictions/metrics within tolerance.

## 5. Add Evaluation, Baselines, And Reporting

- [ ] 5.1 Add a category-frequency prediction baseline and separate Current/Bottled label-reference agreement metrics without treating either label source as outcome reward.
- [ ] 5.2 Report split trajectory/sample counts, per-category coverage, exclusions, top-1 agreement, loss, calibration, candidate legality, and comparisons with trivial baselines.
- [ ] 5.3 Report run outcomes as diagnostics only and mark off-policy evaluation unsupported when propensities or alternative-action support are missing.
- [ ] 5.4 Add a CLI that can run support-only inspection or bounded training/evaluation and writes deterministic JSON, Markdown, split, and model artifacts to an explicit offline output directory.
- [ ] 5.5 Add report snapshot tests for allowed and blocked pilot states, including a successful supervised pilot that still leaves formal non-combat RL and live promotion blocked.

## 6. Run The Frozen-Baseline Pilot

- [ ] 6.1 Re-export a separately named v2 sample set only from candidate `f321cb05` Batch 2 Retry 1, bounded to `1783787478..1783790134` and the report's 25 explicit run files, without launching gameplay.
- [ ] 6.2 Run the support-only command first and preserve source cutoffs, run joins, input hashes, and all blocked categories in a durable report.
- [ ] 6.3 If the structural gate passes, run bounded Current-imitation and Bottled-auxiliary CPU pilots; otherwise preserve the blocked report and do not lower thresholds or fabricate groups.
- [ ] 6.4 Independently review the dataset/split manifests and evaluation report for leakage, overstated support, label mixing, or outcome-uplift claims, then correct every accepted finding.

## 7. Verify And Commit

- [ ] 7.1 Run focused pytest for the decision-loop exporter and new policy-learning module with cache disabled and a writable repository-local basetemp.
- [ ] 7.2 Run the full pytest suite and confirm existing live gameplay, combat RL, and non-combat readiness guards remain green.
- [ ] 7.3 Run `openspec validate add-noncombat-policy-learning-pilot --strict`, `openspec validate --all --strict`, and `git diff --check`.
- [ ] 7.4 Recheck live configuration and production checkpoint hashes or metadata to prove the offline pilot changed neither.
- [ ] 7.5 Commit cohesive units for provenance/dataset support, model/evaluation behavior, and reviewed pilot evidence without staging unrelated historical reports.
