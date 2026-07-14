## 1. Verified Estimator Input Boundary

- [x] 1.1 Add red tests requiring canonical sample, target, readiness, calibration, and implementation hashes plus a successful independent readiness replay.
- [ ] 1.2 Implement the estimator bundle loader with complete-trajectory, overlap-ready, calibration-ready, duplicate-key, and transactional failure guards.
- [ ] 1.3 Add regressions proving changed source bytes, stale calibration, blocked overlap, invalid outcomes, and zero required denominators fail closed without replacing prior artifacts.

## 2. Exact OIS And SNIS Accounting

- [x] 2.1 Add red tests for exact behavior, OIS, SNIS, and target-minus-behavior values on victory and floor channels, including zero and extreme trajectory weights.
- [x] 2.2 Implement `Fraction`-backed trajectory estimators with finite rendering, no clipping or smoothing, and one terminal observation per run.
- [x] 2.3 Add behavior-identity and OIS/SNIS direction diagnostics that remain separate from candidate-comparison readiness.

## 3. Deterministic Bootstrap And Influence

- [x] 3.1 Add red tests for SHA-256 trajectory draws, paired resampling, exact percentile endpoints, row-order invariance, and undefined-replicate blockers.
- [x] 3.2 Implement bounded whole-trajectory bootstrap with required seed, configurable replicate count, exact replicate estimates, and 95 percent paired intervals.
- [x] 3.3 Add red/green leave-one-trajectory-out diagnostics and the pre-specified primary interval, estimator-direction, and sign-stability comparison gate.

## 4. Synthetic Estimator Calibration

- [x] 4.1 Add red tests for identity exactness, balanced one-step and multi-decision known-truth fixtures, exact bootstrap enumeration, and deterministic ordering.
- [x] 4.2 Implement the versioned calibration runner and transactional JSON/Markdown artifact with every fixture, threshold, hash, and blocker recorded.
- [x] 4.3 Run the fixed 200-dataset by 200-trajectory by 500-bootstrap coverage experiment and require target/uplift coverage in `[0.90, 0.99]` plus absolute mean bias at most `0.02`.

## 5. Estimate Artifacts And Independent Replay

- [ ] 5.1 Add red tests for deterministic estimate JSON/Markdown, separated estimator/dataset/estimate/comparison/downstream gates, and no causal or training claim.
- [ ] 5.2 Implement the offline estimation CLI with 10,000 production bootstrap replicates, explicit output paths, atomic pair replacement, and no gameplay imports.
- [ ] 5.3 Implement an independent estimate verifier that recomputes source hashes, exact estimates, hash draws, intervals, influence rows, and gates without importing the main estimator module.
- [ ] 5.4 Add tamper regressions for calibration evidence, point estimates, bootstrap draws, interval endpoints, influence diagnostics, and downstream booleans.

## 6. B3-B7 Proof Of Concept And Closeout

- [ ] 6.1 Generate and independently replay the frozen full calibration artifact before processing real evidence.
- [ ] 6.2 Generate B3-B7 Current estimate artifacts bound to pool SHA-256 `aa61da25c93cdfa24ec57f787fbd41b5e4921c1a1a2bf9cb75f799133159b292` and preserve all one-victory limitations.
- [ ] 6.3 Confirm the proof of concept reconstructs 125 trajectories, 1,253 decisions, 87 nonzero weights, existing overlap metrics, and unmodified pre-specified comparison thresholds.
- [ ] 6.4 Run focused estimator/calibration/verifier tests, full Windows pytest, OpenSpec strict validation, Git whitespace/byte checks, and a completion code review.
- [ ] 6.5 Record live isolation, final gates, residual risks, and next evidence or policy-learning gate in a durable report; commit and push coherent milestones without starting training.
