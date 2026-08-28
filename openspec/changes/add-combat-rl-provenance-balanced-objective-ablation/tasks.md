## 1. Immutable Ablation Registration

- [x] 1.1 Bind the R2 replay/reference hashes, fixed two-arm matrix, deterministic recipe, technical gates, tie-break, retry boundary, and no-authority limits before implementation.
- [x] 1.2 Strictly validate, commit, and push the complete OpenSpec change and registration.

## 2. Provenance-Balanced Trainer Objective

- [ ] 2.1 Add RED unit coverage for equal-stratum anchor aggregation, per-stratum telemetry, and unchanged default global-mean behavior.
- [ ] 2.2 Implement the optional provenance-balanced anchor objective without changing existing callers.
- [ ] 2.3 Add RED coverage for direct-only top-action margin eligibility and override exclusion.
- [ ] 2.4 Implement direct-only margin filtering and telemetry while preserving existing all-row behavior.

## 3. Deterministic Offline Ablation Runner

- [ ] 3.1 Add RED coverage for immutable input checks, exact two-arm recipes, technical gates, and objective-only tie-break behavior.
- [ ] 3.2 Implement atomic execution and reporting for the balanced-only and balanced-plus-direct-margin arms, with the existing R2 result as an unfitted reference.
- [ ] 3.3 Run focused tests, strict OpenSpec validation, and one optimized commit gate; commit and push the immutable runner source.

## 4. Bounded Objective Experiment

- [ ] 4.1 Execute both registered 64-update CPU arms and publish deterministic checkpoints and telemetry.
- [ ] 4.2 Audit every hash, technical gate, tie-break, and authority field without changing the arm matrix or thresholds.
- [ ] 4.3 Commit and push the result, sync the delta specs, and archive the completed change.
